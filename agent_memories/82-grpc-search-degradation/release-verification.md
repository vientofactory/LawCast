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
