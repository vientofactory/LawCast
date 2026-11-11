# Search Degradation and Continuation

## Historical contract

- Backend `716db0b` (PR 180) explicitly removed keyword substitution for an
  empty semantic result. Keyword fallback remains for a disabled or unreachable
  engine, not for a legitimate empty semantic response. This predates gRPC.
- Board `9361a8f` (PR 195), the first board-mode implementation, appended
  keyword-matching **cache-only, not-yet-archived notices** after ranked archive
  notices. It did not append every keyword-matching archived notice. Current
  `notices-hybrid-search.service.ts:397-434` preserves that rule, deduplication,
  date/ended-notice exclusions and combined pagination.
- The sidecar's `weakResults` tier is semantic data, not keyword data. Frontend
  `955fd7c` (3.1.0) introduced `WeakSearchResultsTail` after nonempty primary
  results; older UI already offered the weak tier when primary results were
  empty. The normal tail is opt-in, shown after the last primary board page,
  and pages the returned weak band in batches of ten.
- The public 20-notice ceiling was already released in backend `98a551a` and
  frontend `9ccbaf6` (3.0.0), before gRPC. This patch changes neither Top-K nor
  thresholds, window limits, retrieval ranking, protocol or keyword policy.

## Reproduced cause

The pre-patch dedicated semantic page used its independent health probe to
set `searchUnavailable` and apply `inert` to the search form and all results.
`SemanticSearchUnavailableOverlay` also covered and blurred this region.
That gate existed before gRPC (`9ccbaf6`), so the temporal association is not
proof of a gRPC transport failure.

A failed health request could therefore disable:

1. A successful API keyword fallback, including its result links and next search.
2. Already-returned semantic Top-K/weak results, including disclosure and paging.

Two browser regressions reproduce the issue with a 503 health response:
`Expected: focused; Received: inactive`, both failing before the patch. The
search payload itself is successful in each fixture. Native loopback gRPC
checks independently show that unavailable/deadline/connection-loss errors
still select keyword fallback and that weak results survive serialization.

## Patch

`frontend/src/routes/notices/semantic-search/+page.svelte:74-92` treats health
as advisory rather than an authority over the search response. The form and
results no longer become inert. The covering overlay is replaced with
`SemanticSearchUnavailableNotice.svelte`, a nonblocking status message that
explains keyword degradation without hiding results. The existing corner
health widget and its amber/red/green semantics are retained. Search request
errors and the explicit HTTP 429 cooldown remain independent and unchanged.

The backend runtime is unchanged. Five new real-channel gRPC regressions cover
keyword rows, health-only failures, connection loss, weak-tier separation,
and cache-only keyword continuation/deduplication across pages. Database
repositories are controlled fixtures; no live production failure was injected.

## Verification

- Full backend lint, type checks, production build: pass.
- Full backend Jest: 95 suites / 1,335 tests pass.
- Full development search UI: 59 cases pass, including HTTP/gRPC timing,
  history reopen/comparison, loading, fallback, weak-tail paging and 429 retry.
- Production Node build: six targeted health/fallback/continuation cases pass.
- Independent source copy: the two regressions pass with the patch, then both
  fail again after restoring original runtime files and their SHA-256 hashes.
  The active workspace remains patched.
- Frontend lint, check and Cloudflare production build pass. Guideline checker
  reports zero violations. Executable copy-only rollback and evidence live in
  `_workspace/grpc-fallback-fix-20261111`.
- No production deployment, environment edit, model/cache change or index
  mutation is part of this patch.

## Subsequent release

The user subsequently requested deployment. See [release verification](release-verification.md)
for the ordered 3.1.1 rollout and the distinction between live requests and
isolated deployed-code failure probes.
