# CI installation caches and intentional failure logs

## Baseline evidence

PR 184, commit `2ee5b8f`, workflow run `42093342776` attempt 1 completed all 336 browser assertions but hit the 25-minute job limit immediately after the final suite. Chromium setup took 450 seconds: apt fetched 21.1 MB in 7 minutes 7 seconds at 49.4 kB/s. Attempt 2 used the same code and succeeded in 15m11s, with Chromium setup taking 18 seconds. The tail risk was OS-package mirror latency, not only Chromium binary download.

The passing attempt contained 30 `status: 429` log lines and 30 associated messages, all under `Test request failure recovery`. There are 10 intentionally rate-limited browser cases across desktop/mobile. Their local HTTP fixture emits JSON/HTML/malformed-JSON HTTP 429 or transitions 429 to 503 to healthy. Repeated application layers log one failure more than once; these are not 30 failed tests. Matches such as `(429ms)` elsewhere are durations, not status errors.

## Implementation

- Keep the existing npm download cache and always execute `npm ci --prefer-offline`; do not cache or skip `node_modules` installation.
- Pin the runner to Ubuntu 24.04 (the existing Noble platform) and derive cache identity from the installed Playwright version and runner image. Browser keys include OS/architecture/platform/version; APT keys additionally include image version and installer hash.
- Cache only downloaded APT `.deb` archives, never installed libraries or dpkg state. Root Playwright dependency installation always runs with a temporary APT configuration, preserving normal signature/checksum verification, and returns archive ownership to the runner afterward.
- Cache Chromium binaries separately and still run the browser installer on cache hits to verify required components exist. Restore/save actions are pinned to official actions/cache v5 commit `caa296126883cff596d87d8935842f9db880ef25` (Node 24).
- Save setup caches immediately, before browser tests, so a later assertion failure or timeout does not discard successfully prepared downloads. Keep the original five browser suites, one-worker isolation and 25-minute job timeout unchanged.
- Add an explicit CI notice and fixture markers identifying intentional HTTP 429 injection. Tests additionally assert that the local fixture actually completed 429 responses. No application error logs are hidden.

## Verification

Six native CI guards cover unchanged test commands/failure propagation, compatible cache separation, privileged installer argument/config handling, failure exit propagation and configuration cleanup and visible fixture markers without suppressing application stderr. Local shell tests use mock executables; actual Linux installation/cache behavior must be checked in GitHub Actions.

An independent test-copy negative control changed the rate-limit overlay assertion to the opposite expectation: Playwright reported one failed test and exited 1. The positive counterpart restored the real assertion and passed all 10 intentional rate-limit cases. No `continue-on-error`, swallowed Playwright exits, test skips or retries were added to make failures pass.

Current-task evidence: `/private/tmp/lawcast-ci-cache/VERIFICATION.txt`. Cold run `42103333588` (commit `15078da`) completed all 336 browser cases in 16m6s; warm run `42106241787` (commit `5d847aa`) completed all 336 in 15m34s. Both APT and browser caches hit in the warm run; apt reported `Need to get 0 B/21.1 MB of archives`. OS/browser setup including cache restore/save was 24s cold versus 14s warm: cold APT restore/install/save 1/10/1s and browser restore/install/save 0/9/3s; warm 1/10/0s and 3/0/0s. npm ci took 10s/12s, so no npm-install speedup is claimed. Total-job differences include browser-test timing variance and should not all be attributed to cache.

The cold/warm cache installer and keys were identical; the warm commit only added visible fixture stdout and its guard. Warm logs contain 10 explicit intentional-429 markers and the same 30 status-429 lines, all in the failure-recovery suite. Six CI-install/logging guards plus four classification unit tests pass. An initial runner-context expression validation failure was corrected by setting the browser path via GITHUB_ENV in a step; actionlint reproduced the invalid definition and passes on the final one. Latest head signatures are verified and PR 184 remains OPEN with auto-merge disabled. The feature remains v1.28.0 and the PR must stay unmerged.


## Cross-engine postrelease installation tail (2026-11-06)

The frontend 1.28.0 postmerge run `42158276328` passed the original Chromium job, screenshot-modal and theme-states, but its independent notifications job exhausted the 25-minute budget during OS dependency downloads from `azure.archive.ubuntu.com`, before running any tests. Logs show sequential slow downloads through `libflite1` (13.6 MB), not a failing notification assertion. The shared cross-engine matrix installs Firefox/WebKit dependencies in addition to Chromium and does not currently reuse the original Chromium-only job's APT cache. Do not count that existing cache as protection for these new jobs. The affected job was rerun alone at the exact released SHA; evidence is under `/private/tmp/lawcast-v1.28.0-release/`. No tests were skipped, failure handling was not relaxed, and the production deployment was already successful.

The isolated notifications retry completed successfully with all 46 cases in 1.8 minutes of test execution. Postmerge run `42158276328` attempt 2 is successful overall; 483 distinct browser cases passed across the retained original jobs and the retried notification job.
