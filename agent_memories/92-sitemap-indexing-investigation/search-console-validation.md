# Search Console Revalidation — 2026-11-24

## Completed actions

Property: `sc-domain:law.viento.me`. The Page indexing report still identifies its metric snapshot as November 16, 2026; validation requests below were accepted on November 24. No application code, robots policy, canonical policy, security setting, or production deployment was changed in this follow-up.

All nine exclusion-reason groups were reviewed. The UI/CSV provided **4,091 example URL rows**, all of which were extracted and compared with current routes and the complete metadata snapshot. All referenced numeric notice IDs exist. This is **not** a claim that 8,294 URLs were individually live-fetched:403 and discovered-not-indexed reports expose at most 1,000 examples each. All 18 historical404 URLs and all 6 historical5xx URLs were live-fetched, returning200 with indexing allowed and the correct canonical. Representative URLs from the other groups were also checked, along with current SEO route rules. Heavy parallel fetching was avoided so legitimate per-visitor limits were not treated as production failures.

## Validation requests accepted

The final refreshed overview displays `시작됨` for seven groups, covering **7,591 affected URL rows in the report**:

- 403 blocked:2,900. Reviewed 1,000 provided examples (982 notice-detail URLs; 18 other public pages). Every notice ID exists; representative query-bearing and canonical detail URLs return 200/index-follow. Group validation started.
- 404 not found:18. All 18 return 200/index-follow now. The old October18 validation had failed on November7. A **new validation** was started on November 24; its initial detail shows 18 pending and 0 failed.
- Server5xx:6. All6 return 200/index-follow now. Group validation started.
- NOINDEX:526. All526 provided examples reviewed (5 detail URLs;521 notice-list URLs). Current route policy and representative responses allow indexing, including ordinary paginated lists; technical noindex errors are no longer present in those checks. Group validation started. No tag was blindly removed in this session.
- Discovered, currently not indexed:3,303. Reviewed the maximum 1,000 provided examples; all are canonical numeric detail URLs present in the current snapshot. Group validation started to request Google's reassessment, not to guarantee inclusion.
- Crawled, currently not indexed:792. All 792 provided examples reviewed (503 detail URL variants;289 list URLs), with representative current200/index-follow and canonical checks. Group validation started; Google may correctly classify some query variants as canonical alternatives instead of indexing duplicates.
- Duplicate, Google chose a different canonical:46. All 46 are notice-list pagination URLs. Current representative responses return 200 and declare their normalized pagination canonicals. Group validation started to request a fresh canonical assessment; Google's selection remains its decision.

## Expected exclusions preserved

- Appropriate canonical alternative:702. Reviewed all 702 provided examples (667 notice-detail query variants;35 list variants). Canonical targets exist and normalization is deliberate; this is not an error requiring every duplicate to be indexed. Validation was not falsely started as if canonical alternatives must disappear.
- Blocked by robots.txt:1, `/webhook`. Current `robots.txt` explicitly disallows this settings route. The intentional exclusion was preserved; no crawl protection was removed.

These two groups total 703 URL rows. They remain `시작되지 않음`, intentionally.

## Google sitemap processing confirmed

Search Console now reports **successful processing**, last read November 24, for the parent `https://law.viento.me/sitemap.xml`. Its complete child table was expanded and read:

- 47 child files, **all 47 `성공`**.
- `main.xml`:8 URLs.
- 46 notice chunks:22,740 URLs in total; chunk45 contains240.
- **22,748 discovered URLs** in Google's own report.

This is evidence that Google followed the split sitemap structure. It is **discovery/processing**, not a claim that 22,748 URLs are already indexed. The existing successful submission was not redundantly resubmitted. No individual indexing API was used and no individual URL indexing request was spammed.

## Evidence and limits

Ignored local evidence: `_workspace/gsc-validation-20261124/`.

- `summary.json` and `final-validation-rows.json`: all nine reasons and accepted states; assertions verify 7 started / 7,591 rows.
- `google-sitemap-cells.json`: all 47 child statuses and exact 22,748 URL sum.
- `403.zip` and extracted CSV:1,000 provided examples; other complete example lists were read through visible UI pagination into `*-urls.json`.
- `404-review.json`, `5xx-review.json`, and other `*-review.json`: metadata/HTTP/canonical/robots review results.
- `validation-started.jpg`: final refreshed overview showing all seven started validations.
- `sitemap-success.jpg`, `404-started.jpg`, `5xx-started.jpg`: supporting screenshots.

Validation start is not validation pass or a guaranteed indexing decision. Google performs the remaining asynchronous processing. The metric report's stale indexed count should not be confused with today's accepted requests or sitemap discovery total. The browser was left on the refreshed validation overview for user verification.
