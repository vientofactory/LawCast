#!/usr/bin/env python3
"""Fail when a code comment or docstring contains non-English prose.

The repository rule (AGENTS.md §4/§5) is that comments and docstrings are
written in English. Korean (or any other non-English text) may appear only as a
quoted literal that exists verbatim in the code, data or UI: an identifier, a
DB value, a Notion property name, a corpus sample, or a user-facing label.
Quoting it — `backticks` or "quotes" — is what marks it as data instead of
prose, and this checker uses exactly that distinction:

  * a comment line still holding non-ASCII text after every quoted span and URL
    is removed counts as Korean prose -> violation, exit 1;
  * a comment line whose non-ASCII text sits inside quotes/backticks is a
    cited literal -> allowed.

Comments are located by a small state machine over the source, so Korean inside
string literals, template strings or Svelte markup (user-facing copy, fixtures)
is never reported — that text is not a comment.

Out of scope by design: prose documentation, which is not a code comment and
keeps the language its readers use — `README.md`, `.env.example`,
`agent_memories/` notes and other Markdown. Only files with a source-code
extension are scanned.

Usage:
    python3 tools/check-comment-language.py [paths...] [--all]
                                              --all also lists cited literals
"""

from __future__ import annotations

import os
import re
import sys

HANGUL = re.compile(r'[\uac00-\ud7a3\u3131-\u318e]')
SKIP_DIRS = {
    'node_modules', '.git', 'dist', 'build', '.svelte-kit', 'venv', '.venv',
    'coverage', '__pycache__', 'artifacts', '_workspace', 'embedding-map',
}
CODE_EXT = {'.ts', '.js', '.mjs', '.cjs', '.svelte', '.py', '.css', '.sh', '.yml', '.yaml'}
# Quoted spans may be delimited by quotes, backticks or CJK corner brackets.
QUOTED = re.compile(
    r'"[^"\n]*"|\'[^\'\n]*\'|`[^`\n]*`|\u300c[^\u300d\n]*\u300d|\u300e[^\u300f\n]*\u300f'
)
URL = re.compile(r'https?://\S+')
POSSESSIVE = re.compile(r'(?<=[A-Za-z])\'(?=[A-Za-z])')


def ascii_prose_left(line: str) -> str:
    """Return the line with cited literals, URLs and possessives removed."""
    stripped = POSSESSIVE.sub('', line)
    stripped = URL.sub(' ', stripped)
    return QUOTED.sub(' ', stripped)


def scan_clike(text: str):
    """Yield (line_no, line_text) for every line of a C-like comment."""
    i, n = 0, len(text)
    line = 1
    state = 'code'  # code | line | block | sq | dq | tpl
    start_line = 1
    buf: list[str] = []
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ''
        if ch == '\n':
            if state == 'line':
                yield start_line, ''.join(buf)
                state, buf = 'code', []
            elif state == 'block':
                buf.append(ch)
            line += 1
            i += 1
            continue
        if state == 'code':
            if ch == '/' and nxt == '/':
                state, buf, start_line = 'line', [], line
                i += 2
                continue
            if ch == '/' and nxt == '*':
                state, buf, start_line = 'block', [], line
                i += 2
                continue
            if text[i:i + 4] == '<!--':
                state, buf, start_line = 'block', [], line
                i += 4
                continue
            if ch in '\'"`':
                state = {'\'': 'sq', '"': 'dq', '`': 'tpl'}[ch]
            i += 1
            continue
        if state in ('sq', 'dq'):
            if ch == '\\':
                i += 2
                continue
            if (ch == "'" and state == 'sq') or (ch == '"' and state == 'dq'):
                state = 'code'
            i += 1
            continue
        if state == 'tpl':
            if ch == '\\':
                i += 2
                continue
            if ch == '`':
                state = 'code'
            i += 1
            continue
        if state == 'line':
            buf.append(ch)
            i += 1
            continue
        # block comment
        if (ch == '*' and nxt == '/') or text[i:i + 3] == '-->':
            width = 2 if (ch == '*' and nxt == '/') else 3
            yield start_line, ''.join(buf)
            state, buf = 'code', []
            i += width
            continue
        buf.append(ch)
        i += 1
    if buf:
        yield start_line, ''.join(buf)


def scan_python(text: str):
    """Yield (line_no, line_text) for every line of a Python comment or docstring."""
    import io
    import tokenize

    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            yield tok.start[0], tok.string
        elif tok.type == tokenize.STRING and tok.string.lstrip('rbfuRBFU')[:3] in ('"""', "'''"):
            for offset, line in enumerate(tok.string.splitlines()):
                yield tok.start[0] + offset, line


def iter_files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                if os.path.splitext(fn)[1] in CODE_EXT:
                    yield os.path.join(dirpath, fn)


def main() -> int:
    args = sys.argv[1:]
    show_all = '--all' in args
    paths = [a for a in args if not a.startswith('--')] or ['.']
    violations = 0
    literals = 0
    for path in sorted(iter_files(paths)):
        try:
            text = open(path, encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue
        if not HANGUL.search(text):
            continue
        scanner = scan_python if path.endswith('.py') else scan_clike
        for line_no, line in scanner(text):
            if not HANGUL.search(line):
                continue
            if HANGUL.search(ascii_prose_left(line)):
                violations += 1
                print(f'{path}:{line_no}: {line.strip()[:160]}')
            else:
                literals += 1
                if show_all:
                    print(f'{path}:{line_no}: [cited literal] {line.strip()[:160]}')
    if show_all:
        print(f'\ncited Korean literals: {literals}', file=sys.stderr)
    print(f'korean-prose comment lines: {violations}', file=sys.stderr)
    return 1 if violations else 0


if __name__ == '__main__':
    raise SystemExit(main())
