# Search Degradation Patch Release

## Release sequence

The user requested production rollout after the patch verification. Backend
3.1.1 releases the native-channel regression tests and patch version metadata;
its runtime behavior is unchanged. Frontend 3.1.1 releases the nonblocking
health notice and retains the existing gRPC/public search contract.

1. Backend PR 239 merged as `1a1662ef7168b1ef15bb54f43515c482b142b198`,
   tagged `backend-v3.1.1`. The explicit GPG-signed feature commit was
   `e303ebf319cd9b5d01dc73e4b79f2781459b969a`. Local dev was fast-forwarded,
   a real npm 11.13.0 install left no lockfile diff, and origin/dev was updated.
2. The initial root pointer PR must pass the complete Node/Python matrix;
   only its successful main deployment may unblock frontend merging.
3. Frontend PR 204 remains unmerged until the backend is live and its
   deployed-code probes pass. Main merging triggers production Pages.
4. Verify exact Pages commit identity, public browser interactions and the
   final root gitlinks. Return local and production submodules to dev/dev/main.

## Preconditions verified

- Backend lint/type checks/build: pass; 95 suites and 1,335 tests pass.
- Frontend lint/type/native checks/Cloudflare build: pass; 59 search UI cases pass.
- Unchanged sidecar: ruff and 390 tests pass; local index integrity report passes.
- Initial sandbox-only loopback socket denials were rerun with networking
  enabled. No test or assertion was removed to accommodate the environment.
- Operational environment is unchanged: gRPC target `semantic-search:8301`,
  ONNX bundle path retained, query-vector cache size 256, no host gRPC port.
- Original project config and the previous backend image are preserved under
  `/root/lawcast/_workspace/degradation-release-20261111`. Copy-only rollback
  verifies the old-image tag/no-build restart commands without a production restart.
- Before release, an isolated probe inside the deployed 3.1.0 backend image
  verified native gRPC UNAVAILABLE -> real read-only keyword API rows; a
  controlled ranked/weak/cache-only fixture verified continuation/dedup across
  pages. A separate live gRPC call retained the known five-notice order. The
  production engine, environment and database were not altered for fault injection.

## Evidence

Project-local release evidence: `_workspace/degradation-release-20261111`.
Patch causality and historical contracts: [patch verification](verification.md).
Operational failures are simulated only in an isolated native gRPC listener;
real production traffic is never redirected to that listener. Cache-only
repository rows in that isolated probe are controlled fixtures, not inserted
production records. Public-site smoke tests are separate live evidence.

## Additional production finding before rollout

A bounded read-only live sample found query `게임 과몰입 방지` returning six
clear notices and eight weak notices, including `2212617` in both bands.
The sidecar tiers chunks, so different chunks of the same notice can land
in different bands. The calibrated backend path already removed this
cross-tier notice overlap; the legacy cosine path did not.

Backend PR 240 fixes the cosine response assembly for off/shadow/enforced
lexical gates. It excludes notices present in the *served* clear set before
limiting the weak band, so duplicates do not consume continuation slots.
A weak candidate remains valid when its clear candidate was rejected by the
lexical gate. Ranking, thresholds, Top-K, gRPC and the engine are unchanged.

Three HTTP gate-mode cases and one real-channel gRPC case fail on the old
runtime and pass after the change. The separate deployed-image probe also
reproduces the old overlap with controlled native RPC rows. Full backend
lint/typecheck/build and all 1,340 tests pass. Independent modified source
copies pass 57 focused HTTP/gRPC tests before the rollback control.

The test-only backend 3.1.1 tag remains recorded but was not deployed.
It is superseded for this rollout by `backend-v3.1.2`, PR 240, commit
`f57c8f9a1fe7240f5815d96c1b3d6c5fb00de865`. Its GPG-signed feature commit
is `2e858fe`; local/origin dev and the release tag are synchronized. The
initial root deployment PR is updated to this exact 3.1.2 commit before
merging. Frontend PR 204 is still the 3.1.1 frontend patch release.
