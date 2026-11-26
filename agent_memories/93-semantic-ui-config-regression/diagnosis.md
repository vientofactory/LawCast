# Semantic Search UI Configuration Regression

## Conclusion

**HIGH confidence:** the sidecar and backend search path work. The production frontend disables its semantic-search experience because its effective `PUBLIC_SEMANTIC_SEARCH_ENABLED` runtime value is empty. The regression was introduced in the Pages configuration update accompanying the authenticated-origin/sitemap rollout, not in semantic search code or gRPC.

Investigation: November 24, 2026, approximately 23:09–23:18 JST. Production operations were read-only: SSH inspection, GET probes, and Cloudflare configuration/audit reads. No restart, deployment, configuration write, or product-source edit was performed.

## Observed End-to-End Proof

- SSH to `root@10.20.0.1`: `lawcast-semantic-search` is healthy, running for ten days; backend healthy, running for seventeen hours.
- Backend 3.2.6 environment: `SEMANTIC_SEARCH_ENABLED=true`, HTTP target `http://semantic-search:8300`, gRPC target `semantic-search:8301`, timeouts 30000 ms.
- `curl -sS --max-time 20 -w '\nHTTP %{http_code}\n' http://127.0.0.1:3001/api/notices/semantic-search/health` over SSH returns HTTP 200, `success:true`, `status:"ready"`, `indexedChunks:123693`.
- Loopback semantic search for `전세사기`, k=3: HTTP 200, `mode:"semantic"`, `fallbackReason:null`, three results. This verifies inference/retrieval, not just container liveness.
- Public `https://law.viento.me/api/notices/semantic-search/health`: same ready/indexed state, HTTP 200.
- Public `https://law.viento.me/api/notices/semantic-search?query=%EC%A0%84%EC%84%B8%EC%82%AC%EA%B8%B0&k=3`: HTTP 200, `mode:"semantic"`, `fallbackReason:null`, three results. The Pages-to-authenticated-origin path works too.
- Public `https://law.viento.me/notices/semantic-search?search=%EC%A0%84%EC%84%B8%EC%82%AC%EA%B8%B0`: HTTP 303, `location: /notices`, `cf-cache-status: DYNAMIC`.
- Current `/notices` SSR HTML serializes `PUBLIC_SEMANTIC_SEARCH_ENABLED:""` and contains no semantic-search entry. This is actual runtime evidence, independent of API secret redaction.
- All corrected network probes exited 0. Initial sandbox-restricted SSH/DNS probes failed before escalation; they are not production outages.

## Exact Behavioral Chain

1. `frontend/src/env.ts:13` defaults this optional public variable to an empty string.
2. `frontend/src/lib/utils/semantic-search.ts:160–161` accepts only enabled literals; empty means false.
3. `frontend/src/routes/notices/+page.svelte:76,886,1482` gates search-mode controls and the engine-status widget on that flag. Example chips and semantic entry points use the same flag.
4. `frontend/src/routes/notices/+page.server.ts:75–83` derives the default board mode from it. `normalizeBoardSearchMode` at `semantic-search.ts:28–36` defaults to keyword when false. An explicit valid URL mode remains accepted; this is not a backend search shutdown.
5. `frontend/src/routes/notices/semantic-search/+page.server.ts:21–22` redirects to `/notices` when false, before any search call.

Consequently a perfectly healthy engine cannot cause these UI elements to reappear: their controlling state is deployment configuration, not the engine health response.

## Configuration Change and Release Timeline

Times are JST (UTC+09:00).

- **05:17:28.590:** Cloudflare audit entry `01a20a0e-720e-7ca9-87ae-3b01e010a665` records a successful MCP `PATCH /accounts/16d414a46006317b8bdb436aefc6a292/pages/projects/lawcast-frontend`. The request adds `API_SERVICE_URL` / `API_SERVICE_TOKEN` but also resubmits every existing encrypted environment binding, including `PUBLIC_SEMANTIC_SEARCH_ENABLED`, Discord configuration, Hashguard URL, and the attack-reload flag.
- **05:27:39:** preserved predeployment production HTML contains semantic flag `"true"`, attack-reload flag `"true"`, populated Discord settings and Hashguard URL. The timestamp is the local evidence file mtime, not a server audit timestamp.
- **05:32:56:** Pages deploy `a77a3441-601e-485e-a239-1b8a6fd72ed3`, frontend 3.2.1, commit `59060d116607771dc8f2c1c277d649fc99d284e7` (PR217), activates the updated configuration. Preserved production HTML `production-detail-final.html`, captured at 05:35:59, reports frontend 3.2.1 and empty public runtime values. The capture time is a local file mtime. The separate `authenticated-production-ssr.html` file is a local workerd probe and is not used as production before/after evidence.
- **06:05:35:** frontend 3.2.2 deployment `ab4dd531-76df-414a-b019-3e3477582f67` retains the configuration.
- **07:22:21:** frontend 3.2.3 deployment `124c3c61-dc54-414a-923e-6de8b742016c`, commit `947c0ae19f704ee8b210e3d136e2762eced0a848` (PR219), is the current canonical deployment; the current runtime values remain empty.

`git -C frontend diff ad945b8..947c0ae -- src/lib/utils/semantic-search.ts src/routes/notices/+page.svelte src/routes/notices/+page.server.ts src/routes/notices/semantic-search/+page.server.ts` produces zero lines. PR217 adds two private env definitions, not a new semantic feature gate. Its package change is version-only, not an adapter/framework upgrade.

**Evidence limit:** Cloudflare GET responses return `value:""` for `secret_text` even for older deployments known to have populated runtime values. That GET output alone does not establish erased secrets. Audit logs also redact secret values. The combination of the all-bindings PATCH and the actual before/after SSR values establishes the configuration regression. Reusing GET-redacted empty values in a PATCH is the strongly supported failure mechanism, but the exact submitted secret bytes are not visible in the audit record. Do not claim that the audit log exposes those bytes.

## Collateral Impact and Remediation Direction

The same actual SSR comparison shows `PUBLIC_HASHGUARD_URL`, Discord URL/ID, and `PUBLIC_CF_UNDER_ATTACK_RELOAD_ENABLED` also becoming empty. This is a multi-binding configuration preservation failure, not a semantic-search-only incident. User-visible consequences beyond search have not been independently exercised here. GTM is static/build-time and must be assessed separately.

Restore the intended public runtime values from a trusted source, preserving current private origin credentials, then redeploy Pages and verify actual runtime values/UI plus search results. Do not restart/rebuild the sidecar as the remedy. Do not blindly replay GET-returned secret objects as write input. Preserve untouched secrets through documented partial-update semantics or explicitly supply verified real values when replacing the binding map.

Add release smoke checks for effective semantic flag, a nonredirecting semantic page, search-mode controls, and a real semantic API response. Merely counting encrypted binding names (as the previous sitemap release verification did) does not verify retained values. Local workerd tests using manually populated bindings also do not prove deployed binding preservation.

No remediation was applied; this task requested diagnosis.

## Evidence Files

- `evidence/runtime-comparison.json`: before/new-release/current serialized public values and SHA-256 source hashes.
- `evidence/semantic-page.headers`: current dedicated-page redirect headers.
- `evidence/public-search.json`: current public semantic API response.
- Prior raw HTML remains in ignored `_workspace/sitemap-recovery/` as referenced in the comparison file.

Related: [prior sitemap rollout](../92-sitemap-indexing-investigation/findings.md), [historical independent-health UI bug](../82-grpc-search-degradation/verification.md). The latter issue is distinct: current API health is ready, while this incident is an empty deployment feature flag.
