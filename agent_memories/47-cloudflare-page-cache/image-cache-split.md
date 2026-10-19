# Image Cache Split (2026-10-18 JST follow-up)

Scope approved by owner: screenshot/OG split only.

## Dashboard changes (applied live via dashboard UI)

1. Edited `LawCast public pages - 120 seconds` (`be60b4d038f34dbda98de7034e9f672d`):
   removed `http.request.uri.path wildcard "/notices/*/og.png"` and
   `http.request.uri.path wildcard "/api/notices/*/screenshot"` from the
   expression. Everything else unchanged.
2. Created `LawCast public images - 2 hours` (appended last, after the bypass
   rule — order is safe: anonymous image GETs never match the bypass rule,
   cookie/auth image requests match bypass first and stay DYNAMIC):
   - Expression: host `law.viento.me`, GET/HEAD, no Authorization, no Cookie,
     path wildcard `/notices/*/og.png` or `/api/notices/*/screenshot`.
   - Eligible; Edge TTL base bypass-if-absent + Status code TTL
     `200 -> 2 hours`, `>=201 -> No store` (mirrors Rule 5).
   - Browser TTL: Respect origin (screenshot keeps `public, max-age=86400`,
     OG keeps `public, max-age=300`; the old appended `no-store` is gone).
   - Intended 1 hour was unavailable: the duration picker floor is 2 hours
     (list starts at 2 hours; no 1 hour option). Rule named accordingly.

Final state: 7 active Cache Rules, 0 Cache Response Rules.

## Measured results (curl, KIX edge)

- Baseline (before): OG/screenshot MISS -> HIT with 120s edge and appended
  `no-store`.
- After (fresh keys): MISS -> HIT (Age 0), `no-store` gone on both.
- Cookie image request: DYNAMIC (bypass holds). Note: the DYNAMIC response
  carried `Age: 2`; status is authoritative (not served/stored), kept as observation.
- Regressions pass: `/proposals` EXPIRED + `no-store` (120s HTML intact),
  `/notices` and `__data.json` DYNAMIC + `private, no-cache`.
- 2h proof: same OG and screenshot keys returned HIT at Age 153s
  (~145s after fill). Under the old 120s rule they would be EXPIRED.

Raw evidence: [image-split-measurements.jsonl](image-split-measurements.jsonl).

## Known tradeoffs

- Non-200 image responses (e.g. missing-screenshot 404) now fall under the
  image rule's `>=201 -> No store` row, same guard as Rule 5. No behavior gap.
- OG edge is 2h while HTML detail is 120s: social previews may lag bill
  revisions by up to 2h. Accepted as low-risk (revisions are infrequent).
- Full 2h expiry was not awaited; TTL is proven only past the 120s boundary.
