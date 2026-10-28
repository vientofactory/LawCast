# Production PWA Launch Verification

## Verdict

**HIGH**: frontend 1.25.6 removes the initial blank screen for a controlled, cached PWA entry, but does not preserve continuous loader animation across a full-document navigation when home CSS must be downloaded. Two production runs reproduced approximately 11.3 seconds of a retained, frozen loader surface before home first contentful paint. Both eventually loaded the home page successfully.

This is a verification finding only. No application code or production configuration was changed during this investigation.

## Environment and method

- Date: 2026-10-29, Asia/Tokyo.
- Real production origin: `https://law.viento.me`; frontend release `frontend-v1.25.6`, worker cache `lawcast-pwa-v5`.
- Chrome 156.0.8078.48 on macOS, connected to the owner's port 9222 using the browser-harness skill.
- Visible browser tab, CSS mobile viewport 390 by 844, reduced motion disabled. A hidden-tab control produced zero requestAnimationFrame callbacks over 500 ms, so the test tab was made visible before measurement.
- Navigated to the real manifest start URL `/pwa-start`, using the real installed service worker and cached production document. Responses and assets were not replaced, proxied or mocked.
- Applied CDP network throttling to both the page and worker sessions: 8,000 ms latency, 51,200 bytes/s download and 25,600 bytes/s upload. This is deliberately severe latency with approximately 400 Kbps download, not a claim about a particular carrier profile.
- Compared normal HTTP asset caching with per-session `Network.setCacheDisabled(true)`. The latter bypassed HTTP cache without deleting the owner's existing cache; Cache Storage remained available for the launch document.
- Collected CDP document responses, navigation commits, lifecycle paint events and compositor screencast frames. Captures update when the surface changes; the designed assembled-symbol hold produces approximately 0.7-second gaps even in passing runs.
- Some mobile screencast frames are scaled into the browser surface and have different dimensions from the CSS viewport. Animation-change counts use the full frame rather than a fixed central crop. The first exploratory warm run was excluded from the saved summary; the corrected warm repeat and both uncached-asset runs are preserved.
- Restored network/cache overrides, device metrics and emulated media, returned the reused blank tab to `about:blank`, and restored the owner's original home tab.

## Observations

The normal-cache repeat returned the launch document from the service worker in approximately 16 ms. Its first contentful paint event arrived at 79 ms. Home committed at 8.165 seconds and painted at 8.223 seconds, a 57 ms interval. The largest frame gap was 0.700 seconds, consistent with the intentional assembled-logo hold; the symbol changed over successive loop periods and transitioned into the real home page.

With HTTP asset cache bypassed, the launch document still came from Cache Storage in 14–17 ms. Launch FCP events arrived at 47–93 ms. The two runs committed home at 8.257 and 8.137 seconds, then reported home FCP at 19.543 and 19.438 seconds. Commit-to-paint delays were **11.287 and 11.301 seconds**. The longest compositor frame gaps were 11.925 and 11.850 seconds, encompassing the prior intentional hold and the subsequent retained frame.

In the first uncached run, the four home CSS responses arrived at 16.335–16.412 seconds, after the home HTML commit. The loader surface stopped updating while the new document waited for its render-blocking assets. No sampled frame in the three saved runs was over 99% near-white pixels (all RGB channels at least 253). This supports “no blank-white frame observed”; it is not an all-platform guarantee about unsampled display frames.

## Cause and regression-test gap

`frontend/static/pwa-start.html:74–77` in frontend 1.25.6 starts a full-document replacement:

```javascript
const launch = () => {
  if (started) return;
  started = true;
  location.replace(destination);
};
```

The replacement preserves a visible previous surface while waiting for the new page, but that does not guarantee that the old document's CSS animation continues after navigation commits. The observed freeze aligns with the home commit and subsequent CSS loading. **Do not equate delayed HTML-header tests with a complete slow-network launch test.** Existing local coverage delays the home response but normally serves its CSS quickly; it verifies animation before commit and does not cover this render-blocking interval.

A follow-up implementation should keep an active loading surface until the replacement content and required styles can render, and add a regression that delays the home stylesheet responses as well as HTML. A CSS loop-timing adjustment alone does not address this navigation boundary. This note records the required behavior, not an approved implementation design.

## Evidence and scope

- [Sanitized measurements](measurements.json) contain timings and conditions without request headers, cookies or browser extension inventory.
- [Warm loading frame](warm-3g-repeat-loading.jpg) and [warm home frame](warm-3g-repeat-home.jpg).
- [Uncached loading surface before the long gap](uncached-assets-3g-repeat-before-transition.jpg) and [eventual home frame](uncached-assets-3g-repeat-home.jpg).

This checks the actual deployed start document and worker inside Chrome. It does **not** verify an OS-launched Android/iOS standalone PWA, browser manifest-refresh timing for older installations, or a first-ever visit with no service worker. The initial loader also has a short intentionally transparent assembly start; its retry control paints before all symbol parts appear.

Related context: [PWA architecture and release](../50-pwa-installation/architecture-and-implementation.md), [frontend browser-testing notes](../repo/frontend-notes.md).
