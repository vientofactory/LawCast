# Scoped Cloudflare Script Timing Change

## Scope and outcome

The owner explicitly requested a Cloudflare-side fix and production Lighthouse verification on 2026-10-28 JST. **Verdict: partial remediation only.** Rocket Loader's extra script and JavaScript rewriting are removed from LawCast production. The deprecated APIs in Cloudflare's bot-detection code and legacy/polyfill/cache diagnostics in vendor scripts remain. Best Practices scores did not improve, and the small timing shifts do not demonstrate a consistent performance improvement.

This is independent of [frontend PR 172](https://github.com/vientofactory/LawCast-Frontend/pull/172), which remains unmerged. Production continued to serve frontend v1.25.1 throughout the comparison. No application deployment, new credential, analytics removal or security relaxation was performed.

## Configuration evidence

- The `viento.me` zone had Rocket Loader enabled, Bot Fight Mode enabled, JavaScript Detections enabled and `using_latest_model=true`. There was no zone configuration ruleset in `http_config_settings` (GET entrypoint returned 404).
- The Cloudflare skill was used to inspect live settings, current official documentation and OpenAPI schemas. A dry-run create succeeded before the real mutation.
- Created ruleset `41301b5f5d0840c2b07fd2bde8187953`, phase `http_config_settings`, with exactly one enabled rule `e217a7b217fe4bd2bb875f3b37f1244e`:

```json
{
  "action": "set_config",
  "action_parameters": { "rocket_loader": false },
  "expression": "http.host eq \"law.viento.me\"",
  "ref": "lawcast_native_script_timing"
}
```

- Applied at `2026-10-28T01:14:51.691742Z` (10:14:51 JST). The global Rocket Loader setting remains `on`, so other hosts retain their previous behavior.
- Bot Fight Mode and JavaScript Detections remain enabled and their full configuration matches the saved baseline. Browser integrity/security settings, analytics installation and cache rules were not mutated.
- Firewall custom ruleset remains version 4 (last changed 2026-08-15). Request-cache ruleset remains version 44 with seven rules (last changed 2026-10-18). The empty response-cache ruleset remains version 4. These checks establish that the new configuration rule did not overwrite those phases.
- Rollback: PATCH the above rule's `/zones/f507facb1b932879d096647c2faa818e/rulesets/41301b5f5d0840c2b07fd2bde8187953/rules/e217a7b217fe4bd2bb875f3b37f1244e` endpoint with `{"enabled":false}`. Disabling only this rule avoids deleting any future neighboring rules.

Backups: [before](config-before.json), [applied change](config-change.json), [after](config-after.json).

## Production measurements

Lighthouse 13.6.0, Chrome 156, mobile default simulated throttling, three sequential cold runs per URL before and after. No other browser tests ran concurrently. Live backend data, network routes, cache and vendor execution can vary; these are small lab samples, not CrUX percentiles or causal proof of a speed gain.

- Home: median Performance **93 → 95**, LCP **2438 → 2317 ms**, TBT **4.5 → 6 ms**, CLS **0 → 0**.
- Webhook settings: median Performance **97 → 98**, LCP **1795 → 1674 ms**, TBT **27 → 3.5 ms**, CLS **0 → 0**.
- Crawling transparency: median Performance **99 → 98**, LCP **1625 → 1734 ms**, TBT **2 → 12.5 ms**, CLS **0 → 0**.
- After-only desktop checks: Performance **100 / 100 / 99** for home/webhook/transparency; LCP **562 / 565 / 758 ms**, CLS 0. These are verification checks, not desktop A/B evidence.
- Rocket Loader network requests: **one → zero in all nine paired mobile page loads**; roughly **4.3 KiB** transfer eliminated each time. Its cache-lifetime diagnostic also disappeared. It no longer rewrites script execution or inserts its loader on the target hostname.
- Cloudflare's RUM beacon and JavaScript Detections still load in every after run. All three deprecated API warnings remain. Best Practices stays **58 on home, 81 on webhook/transparency**. Home's Discord third-party-cookie issue belongs to the unmerged frontend patch, not this Cloudflare setting.
- The beacon still triggers the legacy-JavaScript diagnostic and Cloudflare-owned security/beacon scripts still trigger cache-lifetime diagnostics. No cache override was applied to challenge scripts; no diagnostic was hidden by turning off RUM or bot protection.

Full numeric/audit evidence: [measurements.json](measurements.json). Original reports are under ignored `frontend/lighthouse-reports/cloudflare-before`, `cloudflare-after`, and `cloudflare-after-desktop`.

## Production browser smoke test

Playwright tested real desktop and Pixel 7 contexts after the change:

- First consent command defaults analytics and advertising to denied before GTM; GTM and RUM still load.
- Declining consent hides the banner normally.
- Theme switch changes the actual document theme to dark.
- Header/mobile-menu navigation reaches `/notices` without replacing the document (SPA hydration is working).
- No Rocket Loader network request and no uncaught page error in either context.

Evidence: [production-smoke.json](production-smoke.json). These checks perform public reads and local consent/theme changes, not real subscriptions or discussion writes.

## Residual limits and documentation

- Cloudflare's current documentation recommends disabling Rocket Loader and retesting when it causes JavaScript issues: [Rocket Loader](https://developers.cloudflare.com/speed/optimization/content/rocket-loader/), [hostname configuration settings](https://developers.cloudflare.com/rules/configuration-rules/settings/), [configuration rule API](https://developers.cloudflare.com/rules/configuration-rules/create-api/).
- The Free-plan Bot Fight Mode does not participate in the Ruleset Engine and cannot be skipped per hostname with WAF/Page Rules: [Bot Fight Mode limitations](https://developers.cloudflare.com/bots/get-started/bot-fight-mode/#limitations). Disabling it zone-wide would affect other `viento.me` services; this was not done to remove a Lighthouse warning.
- The Bot Management configuration reports `using_latest_model=true`, but this is not a selectable JavaScript-script version. The shipped deprecated API calls cannot be patched from this application. Cloudflare owns the script and updates. [JavaScript Detections](https://developers.cloudflare.com/cloudflare-challenges/challenge-types/javascript-detections/).
- RUM is intentionally retained because it collects real visitor performance data. The injected beacon is Cloudflare-owned: [RUM beacon](https://developers.cloudflare.com/speed/observatory/rum-beacon/).
