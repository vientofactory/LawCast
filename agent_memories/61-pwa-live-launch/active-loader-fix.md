# Active Loader Navigation Handoff

## Problem and approach

The [production investigation](verification.md) reproduced a retained but frozen loader after home navigation committed and before uncached CSS allowed home first paint. The fix keeps the launch document active while fetching the home document and its Vite stylesheet bundles. Navigation begins only after their complete bodies are available to the service worker.

The launch document uses a MessageChannel to request preparation from its controlling worker. The worker acknowledges immediately, fetches fresh home HTML and same-origin immutable CSS bundles, then signals readiness. The next navigation from that client consumes the prepared HTML once. The CSS responses transfer to the resulting client ID and are consumed once by that document's stylesheet requests. No inline CSS replacement, iframe shell, second HTML fetch, query ticket or document rewriting is involved.

The URL, including its original search and fragment, remains the real home URL. The worker ignores the fragment when matching a prepared request because fragments do not identify different HTTP resources. HTTP status and security headers are retained; decoded response bodies have their obsolete transfer encoding and length headers removed.

## Bounds and failures

- Preparation is accepted only from the same-origin launch document, for a target at the same origin's root path. Other documents cannot initiate this transfer.
- Transfers are scoped to the source window and then its resulting navigation client, with a two-minute lifetime and at most four entries per stage. Home bodies are limited to 1 MiB, styles to 512 KiB each and at most 16 bundles. Work is aborted after 90 seconds or when superseded by retry.
- These are temporary in-memory navigation transfers, not offline storage. SSR, errors and stylesheet responses are never written to Cache Storage; API interception remains unchanged. Cache version v6 refreshes the launch document and worker protocol.
- Failed HTML networking uses the existing offline document. A missing/failed stylesheet leaves the animated launch document active and makes retry available; it does not intentionally navigate to a partly styled home.
- Redirects use a normal browser navigation so their original redirect behavior is preserved. Older workers without the message protocol and browsers without a controlling worker retain normal navigation as a compatibility fallback.
- If a worker is terminated after preparation, its in-memory transfer can be lost. Ordinary network navigation remains the fallback; this design does not persist user-specific HTML to cover worker termination. Tests and live measurements must distinguish that fallback from the supported handoff path.

## Regression coverage

The local production proxy can delay CSS separately from HTML without replacing application responses. The new regression clears the isolated test browser's HTTP cache, disables normal HTTP-cache use, and delays stylesheet responses. It asserts that the launch document remains active and animating while CSS is in flight, that home commits after all styles finish, and that HTML/styles are fetched once rather than re-fetched after commit.

Additional checks cover stylesheet failure and retry, original HTTP error status and CSP headers, original redirects, simultaneous launches in separate windows, rejection of messages from ordinary application pages, and unchanged offline recovery and persistent-cache bounds. Both the Node and Cloudflare Pages production runtimes are required.

## Local release validation

Frontend lint and type check passed with zero Svelte errors or warnings; the root agent-guideline checker reported zero violations. All 28 PWA tests passed against both production runtimes. `npm install` synchronized package and lockfile versions to 1.25.7 without changing the resolved dependency tree.

[Frontend PR 177](https://github.com/vientofactory/LawCast-Frontend/pull/177) contains feature commit `a155e35a76435e6f98f50d4e9937072f7b068d30`, explicitly GPG-signed and verified locally and by GitHub.

## Production release and repeated slow-network verification

[PR 177](https://github.com/vientofactory/LawCast-Frontend/pull/177) passed its [Web Vitals CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40749038445) and GitGuardian checks, then merged as `5ecc2b504718f9b18304a71a0cb784920a8bdf72`. [Release frontend-v1.25.7](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.25.7) targets that exact commit. [Production Pages deployment](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40749612691) succeeded, and Cloudflare deployment `a44000cf-480a-454a-a144-7aa692a0f9d8` reports the same commit. [Post-merge Web Vitals](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40749612694) also passed.

The real production origin was retested in the same visible Chrome 156 tab and 390-by-844 CSS viewport used for the original reproduction. Both the page and worker sessions retained the same 8,000 ms latency, 51,200 bytes/s download and 25,600 bytes/s upload limits, with HTTP cache disabled. The worker's actual `CACHE_NAME` was inspected to confirm v6 rather than relying on a script URL shared with an older worker.

Two runs showed launch FCP events at 70 and 99 ms. Home committed at 16.921 and 16.957 seconds, after complete HTML/CSS preparation, and painted at 16.950 and 16.984 seconds. The post-commit interval shrank from the original **11.287–11.301 seconds to 27–29 ms**. The longest compositor gaps were 0.700 and 0.708 seconds, matching the existing intentional assembled-symbol hold rather than an additional navigation freeze. Every three-second period before the home commit contained changing symbol frames; the runs contained 644 captured frames each. No sampled frame exceeded 99% near-white pixels.

In the first run, the four real network CSS responses arrived at 16.478–16.563 seconds, before the home commit. The following page stylesheet responses came from the worker at 16.921 seconds. Cache Storage still contained only the launch/offline documents and the three existing brand assets after the runs; no home HTML or compiled stylesheet was persisted.

A third run retained the same network/cache restrictions through the home window load event at 31.595 seconds, rather than removing throttling shortly after first paint. Home commit-to-paint was 26 ms, no runtime exceptions were recorded, and the home document reached `readyState: complete`. The mobile menu opened successfully afterward. Long static-frame gaps after the completed home intro are not loader freezes; `largest_launch_to_home_frame_gap_seconds` isolates the relevant interval in the measurements. The browser's original tab and all test overrides were restored after verification.

See [sanitized fixed measurements](fixed-measurements.json), [loader just before home transition](fixed-uncached-assets-3g-2-before-transition.jpg), and [resulting home screen](fixed-uncached-assets-3g-2-home.jpg). The original negative measurements remain in [the initial investigation](verification.md) for comparison. This verifies the deployed start URL and real worker in Chrome, not an OS-launched Android/iOS standalone app.

## Repository synchronization

Frontend `dev`, `origin/dev`, `origin/main` and `frontend-v1.25.7` all resolve to `5ecc2b504718f9b18304a71a0cb784920a8bdf72`. Dependencies were reinstalled after fast-forwarding with no lockfile diff. Backend remained on its unchanged `dev` commit and semantic-search on its unchanged `main` commit. The root release records the exact frontend release pointer along with this sanitized investigation and verification evidence.

## Delayed retry visibility follow-up

Frontend 1.25.8 hides the retry control for the first 15 seconds of the launch document. A zero-duration CSS animation reveals it afterward, including with reduced motion or JavaScript disabled. `visibility` preserves its layout space and removes the hidden link from focus/accessibility navigation, so the symbol does not move when the control appears. A fast home transition removes the launch document before the control is revealed; retry after a preparation failure follows the same delay.

Static asset cache v7 refreshes this document without changing the v6 preparation protocol. This supersedes the earlier always-visible retry guidance now that preparation keeps the launch document active.

Validation: lint, type check and agent-guideline checks passed; all 28 PWA tests passed on both Node and Cloudflare Pages. Coverage verifies the 14,999/15,000 ms boundary with reduced motion, stable symbol position, no visible/accessibility link before the threshold, real delayed reveal and absence after a faster home transition. The proxy records `Sec-Fetch-Mode` so document reload assertions distinguish navigation from auxiliary browser `no-cors` requests.

[PR 178](https://github.com/vientofactory/LawCast-Frontend/pull/178) contains explicitly GPG-signed feature commit `76ca1d0029b09be7c87c31bc6c200ce0f4a24257`, verified locally and by GitHub. Its [Web Vitals CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40757240956) and GitGuardian passed. Squash merge `0f402df446e208a8387cfd5794d6b3170f687ea5` is the target of [release frontend-v1.25.8](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.25.8), frontend `dev`, `origin/dev` and the root release pointer. `npm install` after fast-forwarding left the lockfile unchanged.

[Production deployment](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40758033721) and [post-merge Web Vitals](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40758033843) passed. Cloudflare deployment `34fa8049-0761-46f6-9c37-d0e6192e69ee` reports the same release commit.

The actual production origin was checked in visible Chrome on port 9222 with 8,000 ms latency, 51,200 bytes/s download, 25,600 bytes/s upload and HTTP cache disabled on the page and v7 worker. The retry link was hidden at 0.417 and 14.509 seconds, then visible at 15.307 seconds while still at `/pwa-start`. The symbol bounding box remained exactly `[154.9921875, 341, 80, 80]` before and after reveal. Home first paint was observed at approximately 17 seconds, and the home document subsequently reached `readyState: complete`. Test overrides were removed and the original browser tab restored. See [sanitized retry visibility measurements](retry-visibility-measurements.json).
