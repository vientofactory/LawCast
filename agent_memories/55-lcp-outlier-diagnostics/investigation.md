# Production LCP Outliers and Browser Presentation Timing

## Scope and verdict

On 2026-10-28 JST, the initial investigation measured frontend v1.25.2. We collected **24 new cold Lighthouse navigations** sequentially, retaining reports, network logs and compositor/Viz traces. During those measurements no production application, Cloudflare configuration, bot protection, RUM or GTM changes were made. No third-party requests were blocked or substituted in these production measurements. Any subsequent patch rollout and remeasurement are recorded separately below.

The newly reproduced approximately one-second presentation stalls respond to a **single browser-launcher feature change**, with unchanged application code and native Cloudflare scripts. The measured delay is predominantly in the browser presentation pipeline, after application Paint, rather than a multi-second Cloudflare or SSR response. This identifies a measurement-environment issue, not a justified application optimization or security-setting change.

The four earlier simulated 3-second LCP values did not recur in the new samples. Their original reports contain no compositor trace, so this investigation cannot prove the precise causal chain of every earlier outlier or claim that all future outliers are eliminated. These are local lab samples, not production-user/CrUX percentiles.

## Earlier reports: simulation versus observation

[Original outliers](original-outliers.json) extracts all four previous mobile LCP budget violations. Simulated LCP was 3193–3550 ms, whereas observed LCP was 1539–2656 ms. Server-response-time was only 101–189 ms. The license report with simulated LCP 3550 ms had observed LCP 1539 ms; its next report had simulated LCP 1028 ms but almost identical observed LCP 1535 ms. The original simulated score is therefore not interchangeable with a direct 3.5-second browser observation.

Lighthouse's default [simulated throttling](https://github.com/GoogleChrome/lighthouse/blob/main/docs/throttling.md) gathers a trace and models network/CPU restrictions. A `devtools` run actually applies restrictions while recording. Their metrics and scores must be labeled separately.

## Interleaved browser feature isolation

Six paired navigations alternated `/license` and `/status`; the arm order reversed every pair. Every navigation launched a fresh isolated Chrome 156 process. Both arms used Lighthouse 13.6.0 performance auditing, simulated mobile throttling and identical added trace categories. The stock arm retained chrome-launcher 1.2.2 defaults. The control removed **only `RenderDocument`** from the launcher's `--disable-features` list, retaining every other default via `ignoreDefaultFlags: true`. We did not remove the complete default feature list or force arbitrary performance flags.

[Effective browser arguments](browser-arguments.json) were read back from trace metadata, normalized for temporary profile paths and argument order, and confirm the single logical difference. [All twelve results and derived trace evidence](interleaved-lighthouse.json) preserve successes and stalls.

- Stock observed LCP: 332–2585 ms; 3/6 had approximately one-second Paint-to-presentation waits.
- Control observed LCP: 412–620 ms; 0/6 had that wait.
- Stock `/status` examples: main-frame Paint at 532.316 ms and FCP/LCP at 1530.960 ms (998.644 ms gap); another at 507.506 → 1530.283 ms (1022.777 ms gap). Renderer-main RunTask intervals overlap only 86.312/105.271 ms of those waits. These are recorded task-scope overlaps, not proof of total CPU/GPU idleness.
- Stock `/license`: Paint 1540.569 → FCP/LCP 2584.986 ms (1044.417 ms gap), with 16.593 ms of renderer-main RunTask overlap. This sample also had an earlier pre-Paint wait; the presentation gap does not describe its entire load.
- Control main-frame Paint-to-presentation gaps: 18.517–24.123 ms. For comparison, Paint selection excludes initial blank paints in the first 100 ms of navigation and uses the first subsequent main-frame Paint. It is not an LCP-element-specific Paint attribution.
- Cloudflare `Server-Timing` in these twelve responses: `cfEdge` 2–14 ms and `cfOrigin` 0–223 ms. Cache outcomes included HIT, EXPIRED and DYNAMIC; the stall also recurred on dynamic `/status` responses. Cache status alone is not an origin/Worker latency attribution.
- Every arm retained native challenge-platform JSD, Cloudflare RUM and GTM requests. Aggregate Viz `ThrottleUndrawnFrames` decisions occur in delayed traces, but the events omit sink identity; their counts cannot prove which sink was refused or the distinct `ThrottleUnresponsiveClient` branch.

The browser behavior is consistent with reports in [GoogleChrome/lighthouse issue 17148](https://github.com/GoogleChrome/lighthouse/issues/17148). The local isolation is the evidence for this site; the issue is supporting context, not an upstream confirmation of every local mechanism.

## Independent throttling and default-profile recheck

- [Actual DevTools-throttled mobile results](devtools-lighthouse.json): three `/license` and three `/status` cold runs in the control profile. LCP 2142–2383 ms, all six <=2500 ms; performance 95–97, CLS <=0.000034. LCP agrees with the observed metric because these are actually throttled recordings. The control remains explicitly labeled; these are not default-profile PSI scores.
- [Default-profile recheck](stock-recheck.json): three `/notices/changes` and three `/status` cold runs using the patched audit CLI with stock flags, simulated throttling, trace saving and individual-run assertions. Simulated LCP 805–1081 ms, all six budgets passed. Observed LCP still reached 2549 ms in stock Chrome; the browser issue has not been claimed fixed for arbitrary stock runs. Cloudflare `cfEdge` was 3–10 ms in this series.
- Raw reports and traces remain in ignored `frontend/lighthouse-reports/lcp-investigation/`, `lcp-devtools/` and `lcp-stock-recheck/`. Each trace has its matching DevTools network log. Full trace categories add overhead; comparisons within an arm pair use matching categories.

## Patch and regression coverage

`scripts/lighthouse-audit.mjs` retains stock flags by default and adds labeled diagnostic profile and throttling options, trace/network retention, actual timing/Cloudflare header metadata, per-metric median/p75/max/over-budget counts and opt-in individual-run budget failure. Even-sized medians are corrected. Missing observations and failed navigations remain failures.

Three Node regression tests cover a slow tail concealed by a median, inclusive budget boundaries, even/single sample statistics and invalid observations. The frontend CI now runs them. Playwright blocks hydration and GTM requests locally and verifies SSR LCP occurs while those requests remain pending. Actual primary-action reveal/theme contrast is checked separately from full-DOM accessibility scans: the latter explicitly expand deferred subtrees and wait two animation frames so skipped-style recomputation is not mistaken for stable rendered color.

**Separate application defect found by repetition:** the first full run passed 59/60 with an offscreen primary-button contrast failure; a subsequent full run passed 62/62, but five repeated native-reveal checks reproduced **2/5 mobile failures at 1.1499:1**. This was therefore not dismissed as an axe-only race. In `frontend/src/app.css`, `.lc-button-primary` transitioned `background-color` for 180 ms. Its first style resolution inside a deferred subtree could start from the UA gray button background while foreground text was already white. The patch removes only the background-color transition, preserving transform animation and the existing accessible light/dark/hover colors. This is an actual brief-contrast fix, not an asserted LCP improvement. The repeated checks retain immediate contrast assertions and do not wait for the faulty color transition to finish.

Source evidence: `frontend/src/app.css:803` explains the fix and line 804 now has `transition: transform 180ms ease;`. `frontend/e2e/web-vitals.spec.ts:158` asserts >=4.5:1 immediately on native reveal and theme change. `frontend/scripts/lighthouse-audit.mjs:101` validates numeric metrics before preserving observed and document timing metadata.

Local validation: lint and Svelte checks passed with zero errors/warnings; agent-guideline checks found zero violations; all three Node tests passed. After the CSS fix, focused repeats passed **30/30**, followed by the complete production-build suite **62/62**. Full `npm install` synchronized v1.25.3 and changed only lockfile version metadata. Signed frontend commit: `8324282`; [PR 173](https://github.com/vientofactory/LawCast-Frontend/pull/173).

The live v1.25.2 baseline also received ten native Playwright checks (five mobile/five desktop): all had zero uncaught page errors and light/dark immediate button contrast 6.7016:1. This live sample did not reproduce the intermittent contrast defect; the pre-patch reproduction is specifically the isolated production-build mobile repeat series. [Baseline evidence](baseline-production-contrast.json).

## Patch release and production recheck

- PR 173 passed [pre-merge CI](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40638531844) and merged at `2026-10-28T05:38:56Z` as `5888b7d501fc99f5aed4b167585fcb3c4b49b56d`.
- [frontend-v1.25.3](https://github.com/vientofactory/LawCast-Frontend/releases/tag/frontend-v1.25.3) targets that exact commit. Frontend `dev` was fast-forwarded to it; full `npm install` left the lockfile unchanged and `origin/dev` was pushed without a merge commit.
- [Pages deployment Actions](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40639217772) passed lint/type/build/upload. Cloudflare API readback confirmed production/main deployment `68d912a6-2c19-43d1-a301-089c02f4c52e`, exact release SHA, success at `2026-10-28T05:40:03.49277Z`.
- The host-scoped Rocket Loader rule was read back unchanged: enabled `set_config`, expression `http.host eq "law.viento.me"`, `rocket_loader: false`. No security or telemetry setting was changed during this investigation/release.
- [Released production smoke](released-production-smoke.json): ten fresh Playwright contexts (five mobile/five desktop), each verifying footer v1.25.3, immediate primary-button reveal contrast and immediate dark-mode contrast, no automatic Discord iframe and zero uncaught page errors. Light contrast was 6.7016:1 and dark contrast 5.3578:1.
- [Released stock-profile Lighthouse](released-stock.json): home/license/status, three runs each; **all nine LCP observations passed** the modeled 2500 ms budget (814–1137 ms). CLS was zero. Home had one simulated TBT outlier **361.5 ms**, so the strict individual-run command correctly exited 1; this is not described as an all-budget pass. Home median TBT was 49 ms; license/status maxima were 5/51 ms. The failed gate and original report were retained without rerunning until green.
- [Released actual DevTools-throttled control](released-devtools.json): license/status, three runs each; **all six LCP/TBT/CLS individual budgets passed**. LCP 2099–2350 ms, TBT <=60.1 ms and CLS <=0.000035. Together with the initial 24, this is **39 new production Lighthouse runs**.
- [TBT outlier trace extract](released-tbt-outlier.json): the large unattributed modeled task corresponds to an actual renderer-main RunTask of 84.727 ms at 325.179–409.906 ms, around observed FCP 409.866 ms. It contains module evaluation (30.628 ms) and microtasks (47.715 ms), with no subsequent renderer-main task over 50 ms in the retained trace. This is not proof of Cloudflare-only attribution or a 361 ms real-user interaction. The unrelated CF JSD task, GTM and application tasks remain in the original report. No further bundle/analytics/security change was justified by a single simulated TBT sample in this LCP investigation.
- Final release pointer: frontend `5888b7d501fc99f5aed4b167585fcb3c4b49b56d`, matching `origin/dev`, `origin/main` and `frontend-v1.25.3`. Backend stays on `dev` with its pre-existing one-line deletion preserved, and semantic-search stays on `main`. The root release record includes only the changed frontend gitlink and this investigation's notes. [Main-push frontend regression run](https://github.com/vientofactory/LawCast-Frontend/actions/runs/40639217687).

## Reproduction

From `frontend/`, run comparisons sequentially with separate output folders:

```bash
node scripts/lighthouse-audit.mjs --routes /license,/status --runs 3 --save-assets --assert-every-run --output-dir lighthouse-reports/stock
node scripts/lighthouse-audit.mjs --routes /license,/status --runs 3 --save-assets --browser-profile render-document --output-dir lighthouse-reports/control
node scripts/lighthouse-audit.mjs --routes /license,/status --runs 3 --save-assets --browser-profile render-document --throttling-method devtools --output-dir lighthouse-reports/devtools
node --test scripts/lighthouse-summary.test.mjs
npm run test:e2e:web-vitals
```

Do not compare a simulated result with an actual-throttled result as a before/after website improvement. For Cloudflare timing interpretation, see [Server-Timing](https://developers.cloudflare.com/changelog/post/2026-02-18-cfworker-server-timing/) and [cache status semantics](https://developers.cloudflare.com/cache/concepts/cache-responses/). Related production rollout: [session 53](../53-frontend-web-vitals/audit-and-regressions.md) and [host-scoped Rocket Loader change](../54-cloudflare-script-timing/verification.md).
