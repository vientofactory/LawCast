# Cross-browser CI dependency caches

## Baseline and requested scope

The owner requested a separate frontend PR that improves slow browser dependency installation, validates appropriate caches in the cross-browser jobs without skipping tests, and remains unmerged.

The preceding frontend 1.28.0 postmerge run `42158276328` exhausted the notifications job's 25-minute budget while downloading Ubuntu packages from `azure.archive.ubuntu.com`, before any test started. A same-SHA retry passed all 46 notification cases. The existing Chromium-only APT cache did not apply to the cross-engine matrix. Original logs are retained in `/private/tmp/lawcast-v1.28.0-release/notifications-install-attempt1.log`.

## Implementation

Frontend feature branch: `codex/cross-browser-ci-cache`, based on released main `f35595f`. PR: [185](https://github.com/vientofactory/LawCast-Frontend/pull/185). Signed feature commits: `baea37e`, `00eef6c`. The initial request stopped before merging. The owner subsequently authorized merge, release and deployment; see [release verification](release-verification.md).

- `.github/actions/setup-playwright/action.yml` centralizes download restoration, unconditional installation/validation, early cache saving and job summaries.
- `.github/scripts/install-browser-deps.sh` accepts validated Chromium/Firefox/WebKit arguments, retains only APT package archives and preserves signature/checksum verification. The original Chromium script remains a compatibility wrapper.
- `.github/scripts/playwright-cache-key.mjs` derives stable identities from installed Playwright, OS, architecture, image platform and normalized browser set. APT keys additionally include the runner image version and installer/action digest. Broad restore prefixes are intentionally absent.
- One `prepare-shared-browsers` job warms the cross-engine caches before the three matrix jobs, avoiding simultaneous cold package downloads/cache-save races. Each consumer still installs its own system libraries and verifies all requested browser binaries; caches do not represent installed runner state.
- npm package downloads remain separately cached and `npm ci --prefer-offline` always executes. No `node_modules`, dpkg state or installed system libraries are cached.
- Existing test commands, one-worker execution, failure propagation and 25-minute budgets remain intact. No application source, E2E test or Playwright project configuration changes were made.
- Patch version 1.28.1 was prepared for this PR. Actual npm 11.13.0 install changed only the package/lockfile version fields, not the dependency tree.

## Verification

Local lint, Svelte check (zero errors/warnings), Cloudflare production build, actionlint, agent guidelines and all 23 script unit tests passed. The three cross-browser suites still discover exactly 46/53/48 cases. The existing baseline CI tests pass 8/8; the new cache-contract probe fails 13 of 16 checks against the old setup and passes all 16 against the modified setup. These contract failures indicate missing new cache infrastructure, not thirteen application bugs.

An independent rollback copy restored five original files and removed three new files, with every original hash matching. The same new probe returned to the baseline result while active source remained changed. Four primary artifacts and literal commands/results live under `/private/tmp/lawcast-cross-browser-cache/`: `MODIFIED_FILE.tar`, `DIFF_FILE.patch`, `VERIFICATION.txt`, executable `ROLLBACK.sh`.

The final-head cold run completed successfully: all 483 browser cases passed (336 Chromium cases plus 147 cross-engine cases), without test/configuration changes. Final-head cold CI run: [42174375871](https://github.com/vientofactory/LawCast-Frontend/actions/runs/42174375871). An earlier trial was superseded by the cache-key boundary fix before final qualification.

**Primary-key prefix matching:** GitHub can attempt prefix matches even when restore-keys is absent. Browser keys therefore have an explicit terminal marker, and tests assert that single-engine/multi-engine keys cannot prefix-match in either direction. See [the official cache matching reference](https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching#cache-key-matching).

Initial final-head cold preparation is verified from the completed job API log: both cache namespaces missed, APT downloaded 114 MB and retained 181 package archives, and both archives were saved before matrix tests. The terminal browser-key marker also kept the Chromium-only binary archive (281,680,014 bytes) separate from the full engine archive (489,628,965 bytes); these are compressed cache sizes, not installed sizes. The preparation action took 73 seconds including cache I/O. A same-SHA job-only rerun of preparation and its dependent cross-engine suites restored both caches: APT downloaded 0 B of 114 MB, and preparation took 30 seconds. The existing Chromium result is retained on this rerun, not rerun; all 147 cross-engine cases passed again (46/53/48), with both cache hits and zero APT archive download in every consumer. Both run attempts succeeded at signed head `00eef6c`. The PR remained open without auto-merge until the subsequent explicit release authorization. These are observed step timings, not a general whole-CI benchmark.
