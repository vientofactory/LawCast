# Clearance-Only Public HTML Cache Rollout

## Production change

At 2026-11-13 01:04:07 JST, Cloudflare request cache ruleset `511d814cdaa047b4b331cd92edc02220` changed from version 44 to 45 through one atomic ruleset PUT. Only expressions of public HTML rule `be60b4d038f34dbda98de7034e9f672d` and later private-bypass rule `335a264844564074bdd59a678400bcd3` changed. Every action parameter, TTL, rule order, other rule and route scope stayed intact. Public successful HTML still has edge TTL 120 seconds, browser bypass, and status 201+ no-store. No frontend release, backend change, purge, WAF change, key normalization or TTL change occurred.

The exception permits exactly one nonempty, case-sensitive `cf_clearance` Cookie, in one Cookie header, whose raw string exactly equals the parsed cookie reconstructed with its name. Explicit delimiter/whitespace/quote/backslash exclusions fail closed for malformed or ambiguous values. A trailing semicolon, duplicate Cookie or any additional application Cookie bypasses. This is cache eligibility, not a substitute for Cloudflare clearance validation or application authentication.

The public rule permits that exception. The subsequent bypass rule excludes it ONLY within the existing public HTML GET/HEAD scope with no nonempty Authorization. API, data, private route, other Cookie and Authorization branches remain bypassed; image Cookie rules were not broadened.

## Validation and evidence

All raw configuration copies, runnable probes, diffs and results live in ignored `verification-artifacts/clearance-cookie/`. Original fixture SHA256 is `88a7a03659ab9fd9019f3a8c14cae9d6c7a2bea61cc9b754206367fa6b491e1d`.

- Candidate ruleset validation through Cloudflare `dry_run=true` succeeded before applying. One intermediate dry run rejected unsupported string escaping; the corrected candidate uses platform-validated hexadecimal character constants. Invalid dry runs did not persist a new version.
- Local classification/scope models and exact structural invariants pass. This local model is not a rules-engine emulator; Cloudflare Trace and live requests provide authoritative behavior evidence.
- Cloudflare Trace passed 23/23 cases: public anonymous/clearance matching, session-only, mixed order, unknown cookies, duplicate cookies, comma, empty value, trailing delimiter, case mismatch, Authorization, urgent/push/discussion API, data URLs, discussion/status pages, POST and image exclusion. Trace cannot accept HEAD; real HEAD was tested instead. Trace skipped origin responses; POST did not execute an application write.
- Real browser received its own clearance Cookie. Before: 16/16 home/detail requests DYNAMIC, zero HIT. After: 15/16 HIT, one EXPIRED at the start of detail reads. Cookie values were never persisted.
- Live regression: 26/26 assertions passed, including session-Cookie mix and unknown Cookie DYNAMIC, Authorization DYNAMIC, real-time API/data bypass, repeated HTTP 400/404 no-store and HEAD HIT. Session/Authorization fixtures verify cache isolation, not application login validity.
- Baseline and post-change WAF custom/managed Trace phase trees for the same request are identical. Response-cache v4 and configuration v1 objects equal the preceding audit snapshot. The managed-WAF entrypoint GET returns 404 (the managed ruleset is present in Trace); no successful complete managed-entrypoint snapshot is claimed.
- Rollback restored an independent modified fixture byte-for-byte to original v44; baseline trace and live results document restored Cookie-bypass behavior. Production rollback payload also passed Cloudflare dry-run validation. Production remains v45: an actual production rollback was not performed. Executable ROLLBACK.sh supports guarded local-copy restoration and an explicit token-provided production mode; its production HTTP branch was not executed.

## Matched browser measurements

One workstation, Chromium, KIX, service workers blocked, browser-issued `cf_clearance` only, same routes, eight sequential fresh-page navigations per route in each stage. Existing connections can be reused. These results must not be compared directly against the previous audit's new-process curl timings or presented as global field percentiles.

- Home: HIT 0/8 to 8/8; TTFB median 204.45ms to 189.85ms (7.1% lower); nearest-rank p95 450.10ms to 258.60ms.
- Notice 2222755: HIT 0/8 to 7/8 (87.5%); TTFB median 136.45ms to 163.65ms (19.9% higher); nearest-rank p95 359.40ms to 385.80ms. The first post-change read EXPIRED, and the sample is small with substantial network variation. Do not claim consistent speed improvement from these measurements.
- Eligibility and origin avoidance improved in the tested Cookie cohort; median latency improvement was not consistent. No pure-human or global latency cohort was available.

A short GraphQL snapshot uses 2026-11-13 01:00:07–01:04:07 JST before and 01:04:08–01:08:08 after. HTTP 200 home counts: before 13 with zero HIT; after 32 with nine HIT (28.1%). Detail counts: before four with zero HIT; after 16 with eight HIT (50%). Counts are adaptive estimates and recent data may still lag. Browser checks, negative regression fixtures and potentially tracing traffic contaminate these tiny windows; they are not an independent organic-traffic comparison or a causal release effect. More representative evaluation needs 24–48 hours, excluding verification traffic where possible.

## Next validation, without further configuration changes

Keep 120-second TTL and existing private/error bypasses. Compare route/PoP-specific eligible HIT/EXPIRED/MISS, origin requests and freshness using a longer organic window. Do not broaden the allowed Cookie list or ignore all query parameters. Existing SSR response failure status semantics remain essential to prevent HTTP-200 fallback storage under the unchanged status-code TTL.
