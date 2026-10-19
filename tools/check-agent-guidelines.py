#!/usr/bin/env python3
"""Fail when source files violate the LawCast agent guidelines (AGENTS.md).

Checks implemented (all machine-checkable from the repo root):

  C1 -- Comment language (AGENTS.md section 4/5/6):
        every `//`, `/* */`, `/** */`, `#`, HTML/Svelte, CSS, YAML/shell
        comment and Python docstring MUST be English. Korean (or any other
        non-ASCII prose) may appear only as a quoted literal copied verbatim
        from the code, the data or the UI (`` `제안이유` ``, `"안건정보가 없습니다"`).
  T1 -- Test descriptions (AGENTS.md section 4/5/6):
        every `describe(...)` / `it(...)` / `test(...)` title across backend
        Jest specs, frontend Playwright specs and Python tests MUST be
        English. Korean is allowed only as a quoted literal naming the exact
        UI string, DB value or fixture under test, e.g.
        `test('shows "기록 없음" when the engine has no recorded update times')`.
        A fully Korean title is a violation.
  E1 -- No emojis in comments (AGENTS.md section 6):
        never use emojis in code comments, docstrings, commit messages,
        documentation or PR descriptions. Emoji code points inside comment
        text are violations. User-facing message strings (e.g. Discord embed
        titles with chart/pictograph icons) are product copy, not comments,
        and are deliberately NOT flagged.

Out of scope by design (same as tools/check-comment-language.py):
prose documentation (`README.md`, `.env.example`, `agent_memories/` notes and
other Markdown) keeps the language its readers use and is never scanned.
Fixture data, request payloads and `expect(...)` values keep their original
language; only the description/title above them is checked.

Usage:
    python3 tools/check-agent-guidelines.py [paths...] [--all]
                                            --all also lists cited literals
    python3 tools/check-agent-guidelines.py --only C1,T1,E1 backend frontend
    Exit 1 when any violation is found, otherwise exit 0.
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
POSSESSIVE = re.compile(r"(?<=[A-Za-z])'(?=[A-Za-z])")
# Pictographic emoji live in the Supplementary Multilingual Plane
# (U+1F000-U+1FAFF, including flags U+1F1E6-U+1F1FF). BMP symbols such as
# arrows (`→`), checkmarks, bullets and math operators are legitimate code
# text and MUST NOT be flagged, so they are deliberately excluded here.
EMOJI = re.compile('[\U0001F000-\U0001FAFF]')
# A test title call: describe(...), it(...), test(...), test.describe(...).
# The first string literal argument is the description under test.
TEST_TITLE = re.compile(
    r'(?:\bdescribe|\bit|\btest)(?:\.\w+)?\s*\(\s*(?P<q>[\'"`])(?P<title>.*?)(?P=q)',
    re.DOTALL,
)
PY_TEST_DEF = re.compile(r'^\s*def\s+(?P<name>test_\w*)\s*\(')


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
    """Yield (line_no, line_text) for every line of a Python comment/docstring."""
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


def check_comments(path: str, text: str, show_all: bool):
    """Check C1. Return (violations, literals, messages)."""
    violations, literals, messages = 0, 0, []
    if not HANGUL.search(text):
        return violations, literals, messages
    scanner = scan_python if path.endswith('.py') else scan_clike
    for line_no, line in scanner(text):
        if not HANGUL.search(line):
            continue
        if HANGUL.search(ascii_prose_left(line)):
            violations += 1
            messages.append(f'C1 {path}:{line_no}: {line.strip()[:160]}')
        else:
            literals += 1
            if show_all:
                messages.append(f'C1 {path}:{line_no}: [cited literal] {line.strip()[:160]}')
    return violations, literals, messages


def check_test_titles(path: str, text: str):
    """Check T1. Return (violations, messages)."""
    violations, messages = 0, []
    if not HANGUL.search(text):
        return violations, messages
    if path.endswith('.py'):
        for i, line in enumerate(text.splitlines(), start=1):
            match = PY_TEST_DEF.search(line)
            if match and HANGUL.search(match.group('name')):
                violations += 1
                messages.append(f'T1 {path}:{i}: {line.strip()[:160]}')
        return violations, messages
    for match in TEST_TITLE.finditer(text):
        title = match.group('title')
        if not HANGUL.search(title):
            continue
        if HANGUL.search(ascii_prose_left(title)):
            line_no = text.count('\n', 0, match.start()) + 1
            violations += 1
            messages.append(f'T1 {path}:{line_no}: {title.strip()[:160]}')
    return violations, messages


def check_emoji(path: str, text: str):
    """Check E1 over comment text only. Return (violations, messages)."""
    violations, messages = 0, []
    scanner = scan_python if path.endswith('.py') else scan_clike
    try:
        lines = list(scanner(text))
    except Exception:
        return violations, messages
    for line_no, line in lines:
        if EMOJI.search(line):
            violations += 1
            messages.append(f'E1 {path}:{line_no}: {line.strip()[:160]}')
    return violations, messages


def main() -> int:
    args = sys.argv[1:]
    show_all = '--all' in args
    only = set()
    for arg in args:
        if arg.startswith('--only='):
            only = {item.strip() for item in arg[len('--only='):].split(',') if item.strip()}
        elif arg.startswith('--only'):
            # Accept "--only C1,T1" (space separated) as well.
            idx = args.index(arg)
            if idx + 1 < len(args):
                only = {item.strip() for item in args[idx + 1].split(',') if item.strip()}
    paths = [a for a in args if not a.startswith('--') and a != ',']
    # Remove the value token consumed by "--only <value>".
    if any(a == '--only' for a in args):
        idx = args.index('--only')
        if idx + 1 < len(args) and args[idx + 1] in paths:
            paths.remove(args[idx + 1])
    if not paths:
        paths = ['.']
    run_c1 = not only or 'C1' in only
    run_t1 = not only or 'T1' in only
    run_e1 = not only or 'E1' in only

    total_violations = 0
    literal_count = 0
    for path in sorted(iter_files(paths)):
        try:
            text = open(path, encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue
        if run_c1:
            c1_violations, literals, c1_messages = check_comments(path, text, show_all)
            total_violations += c1_violations
            literal_count += literals
            for message in c1_messages:
                if not message.startswith('C1 ') or 'cited literal' not in message:
                    print(message)
                elif show_all:
                    print(message)
        if run_t1:
            t1_violations, t1_messages = check_test_titles(path, text)
            total_violations += t1_violations
            for message in t1_messages:
                print(message)
        if run_e1 and os.path.splitext(path)[1] in CODE_EXT:
            e1_violations, e1_messages = check_emoji(path, text)
            total_violations += e1_violations
            for message in e1_messages:
                print(message)
    if show_all:
        print(f'\ncited Korean literals: {literal_count}', file=sys.stderr)
    print(f'agent-guideline violations: {total_violations}', file=sys.stderr)
    return 1 if total_violations else 0


if __name__ == '__main__':
    raise SystemExit(main())
