# Idle Search Latency Release

## Release decision

The user explicitly requested deployment and production 180/600-second idle
measurements after the local verification. Only semantic-search runtime changes;
backend 3.1.2 and frontend 3.1.1 remain unchanged.

- Semantic-search PR 25 is merged as `ce9346aa1697748a9ccde158c6a2d232264014b3`,
  version/tag `semantic-search-v3.1.1`. The explicitly GPG-signed feature
  commit is `36aa03cced3b7fc923062fce56512c2d6b1b473b`; GitHub verifies both
  signatures as valid. The matching GitHub Release exists.
- Local ruff check/format and all 414 sidecar tests pass. Metadata version
  checks pass. The local capability report validates 122700 rows, the row map
  and fingerprint, with 22259 notices indexed. Agent guidelines report zero
  violations.
- Backend lint, TypeScript, build and all 1340 tests pass. The initial
  unchanged-backend test expected exactly 10000 ms but observed 9999 ms at
  `semantic-search.service.spec.ts:157`. The full rerun passes without any
  source/test modification; retain the first failure as a clock-boundary flake.
- Frontend lint/check pass with zero errors and warnings. Both dev branches
  are synchronized by fast-forward and real npm 11.13.0 installs preserve
  the lockfiles. The sidecar returns to main.

## Deployment and rollback controls

The root feature PR records the release-reachable sidecar main commit. Its
canonical CI and main deployment must pass the mandatory capability comparison,
HTTP readiness and internal gRPC readiness. No capability-loss override is used.

Project-local evidence lives under `_workspace/idle-search-release-20261111`
locally and under `/root/lawcast` on the deployment host. Before any build,
the original image was retained as
`lawcast-semantic-search:idle-rollback-3.1.0-20261111`. Original Compose/env
bytes and the sidecar deployment marker were copied into the private evidence
folder. Environment values and model/index settings remain unchanged.

The executable rollback uses that retained image with a Compose override and
restores the original deployment marker. A separate local fixture and recording
Docker shim verify image selection, no-build/no-dependencies restart arguments,
marker restoration and unchanged configuration. Production was not restarted
for this rollback test.

## Production experiment

The baseline and deployed arms use the same origin HTTP API, k=10 notices,
with native gRPC k=20 companion readback only AFTER the first origin request.
The companion validates vector reuse but is not mislabeled as a cold request.
Both novel query strings are shared between arms; the deployed container starts
with an empty vector LRU. No cache disable or forced memory pressure is applied
to production.

The host-side finite probe waits for 180 and 600 seconds without foreground
sidecar search completions. Public traffic is never blocked; an observed
search resets the quiet timer. It records update events, intended native
upkeep, image/start identity, process faults/read bytes, memory, origin mode,
ordered result IDs and exact sidecar logs for each first request.

The SSH streaming connection ended during the baseline's long wait, but the
finite host process completed and wrote both results. A separate short SSH read
retrieved the complete start/seed/180/600/finish JSON. Future measurements run
with detached finite host execution and explicit readback rather than relying
on a continuously open SSH session.

Before release, uncontaminated 180/600-second windows returned origin first
requests in **382.50/750.94 ms**. The old image/start identity is unchanged
throughout, with zero native upkeep passes. These are contemporary paired
baseline samples, not a reinterpretation of the historical 9–11-second tails.

## CI infrastructure correction

Root PR 48's initial CI run `43032859603` and its unchanged-code retry both
passed application unit tests but failed Redis installation: Ubuntu's
`security.ubuntu.com` could not be resolved during APT update/package fetch.
Logs from both attempts are preserved in the release workspace. No failed
application assertion was deleted or changed.

The root CI now uses `.github/scripts/ci-redis-server.sh` via the migration
probe's existing `REDIS_SERVER` interface. It runs the official `redis:8.8.0`
image, matching production, in foreground with host networking, loopback binding
and the dynamically reserved test port. The original Node migration command
and every legacy-envelope/namespace/TTL/wrap/clear assertion remain unchanged.
Docker forwards readiness output and shutdown, and `--rm` removes the isolated
server. This avoids the unrelated Ubuntu package mirror dependency rather than
skipping Redis verification. Local shell syntax, YAML/probe-preservation and
exact-argument/empty-save-value fixture checks pass; canonical CI validates the
real Redis server before deployment.

## Deployment bootstrap mirror isolation

The first main deployment reached WireGuard setup, which still used the same
runner APT mirror list. The release adds a common installer for both deployment
workflows: use already installed tools when present; otherwise install from
isolated HTTPS `archive.ubuntu.com` sources for the runner's base, updates and
security suites. Ubuntu's installed archive keyring still verifies repository
signatures and package hashes; no authentication or TLS check is disabled.
Acquisition retries/timeouts are bounded, and the runner's global APT sources
are not rewritten. The VPN configuration remains private and the original
interface-up/ping/SSH checks remain mandatory.

Local tests cover shell syntax, source/suite/keyring selection, bounded APT
options and the already-installed fast path with recording shims. Actual
package installation, VPN connectivity and deployment are verified by the
subsequent main workflow, not claimed from these fixtures. Application commits
and semantic-search version remain unchanged.
