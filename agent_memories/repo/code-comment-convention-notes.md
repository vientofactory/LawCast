# Code and Comment Convention Compliance Notes

Repo-wide convention audit and refactor performed 2026-10-07 (backend + frontend).
Records the judgment calls so future agents do not re-litigate them.

## What Was Refactored

- **English-only comment rule (`AGENTS.md` §4/§5)**: translated every pure-Korean
  comment prose block to English across both submodules (~40 files), including
  `backend/src/utils/api-response.utils.ts`,
  `backend/src/modules/discussions/controllers/discussions.controller.ts`,
  `backend/src/controllers/api-isolation.spec.ts`,
  `backend/src/modules/shared/non-blocking-verification.spec.ts`,
  `frontend/src/lib/api/client.ts`, `frontend/src/lib/utils/helpers.ts`,
  `frontend/src/lib/types/api.ts`, `frontend/src/lib/components/Header.svelte`,
  HTML section comments in `routes/{proposals,license,crawling-transparency}/+page.svelte`,
  and inline comments in `routes/{sitemap.xml,notices/changes,notices/[num]}` server loaders.
- **`lc-` prefix rule for global CSS classes**: renamed the four non-prefixed
  global classes in `frontend/src/app.css` and every usage across route/component
  templates: `page-shell` -> `lc-page-shell`, `animate-fade-in` ->
  `lc-animate-fade-in`, `hover-lift` -> `lc-hover-lift`, `loading-slide` ->
  `lc-loading-slide`. Verified with a negative-lookbehind scan
  (`(?<!lc-)\b(page-shell|...)\b`) returning zero stragglers project-wide.

## Judgment Criteria (do not re-litigate)

- **Korean identifiers, data literals and proper nouns inside English prose are
  COMPLIANT.** Comments must be written in English, but quoting the Korean
  contract surface they document is unavoidable and required: Notion property
  names (`제목`/`공개 여부`/`노출 순서`/`긴급`), parser examples in
  `proposer.utils.ts`/`proposer.ts` (`"윤한홍의원 등 10인"`), UI strings quoted in
  `notice-deadline.util.ts`/`status/+page.svelte`, mock search keywords in
  `semantic-search-mock.ts`, site names (`국민참여입법센터`). The remaining hits
  from a Korean-in-comment scan are all this class — leave them alone.
- **Emoji ban applies to comments/docs, NOT product strings** (maintainer decision
  2026-10-07): Discord bridge embeds (`💀 [FATAL]`, `❌`, `✅`, log-level dots) and
  the `⚙️` in `WebhookGuide.svelte` are shipped product presentation asserted by
  specs (e.g. `discord-bridge.service.spec.ts`); changing them is a product
  change, not a convention fix. No emoji exist in any comment.
- **Svelte-scoped component styles keep their short names** (`.spark`,
  `.wand-*`, `.chart-container`): Svelte's scoping already namespaces them, so
  the `lc-` prefix targets global stylesheet classes only. Expanding the rename
  is optional polish with regression risk.
- **Known unresolved conflict**: `AGENTS.md` names utility files
  `{name}.util.ts` (example `ip-masking.util.ts`) but the dominant repo pattern
  is `{name}.utils.ts` (6+ files). Not renamed — file renames would invalidate
  memory cross-references and git history for zero runtime value. Resolve by
  updating the AGENTS.md wording or doing a dedicated rename pass, not ad hoc.

## Verification Gates

Comment/class refactors are still code changes; rerun in both submodules:

- Backend: `npm run lint && npx tsc --noEmit && npm run build && npm test`
  (passed: 68 suites / 877 tests).
- Frontend: `npm run lint && npm run check && npm run build`
  (passed: 0 errors/warnings).
- Class renames touch markup on nearly every page: rerun the full mock e2e
  (`DIFFCHAIN_UI_MOCK=1` dev server + playwright config; passed: 253 / 45 skipped
  / 0 failed), then clean `frontend/test-results/`.

## Pitfalls Encountered

- macOS `grep` has no `--pcre2`/`-P` and `cat -A`; use `rg` (with `-P` for
  lookbehind) or `perl -ne` for whitespace/unicode inspection. A failed `grep`
  exits 0 in some pipelines — check the error text before trusting "clean".
- Bulk comment translation: apply phrase substitutions only on comment lines
  (`/<!--/` or `^\s*//` guards in `perl -i -pe`) so Korean UI strings in the
  same files are never touched; diff every file afterwards
  (`git diff -U1 | grep -E '^[+-][^+-]'`) to confirm only comment lines changed.
