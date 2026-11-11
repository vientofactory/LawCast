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

## Deployment bootstrap and release outcome

The initial root main deployment failed before any SSH/container replacement:
the Ubuntu runner could not resolve `security.ubuntu.com` while installing
WireGuard. An isolated signed Ubuntu archive alternative also failed its new
required PR preflight because `archive.ubuntu.com` DNS failed. That attempted
APT implementation was never deployed.

Root PR 49 uses a shared installer for both deploy workflows. It builds the
official WireGuard `v1.0.20250521` source with the runner's existing C toolchain,
verifies immutable commit `e2ecaaa739144997ccff89d6ad6ec81698ea6ced` before
build execution, and installs only `wg` and upstream Linux `wg-quick`.
TLS verification and immutable source identity remain enabled. No unsigned
prebuilt binary or Ubuntu mirror is used. systemd's documented `resolvconf`
compatibility entry point is linked only when necessary and available as
`resolvectl`. The VPN profile stays private; ping/SSH checks remain mandatory.

The required deployment-tools PR job performs the REAL source build on Ubuntu,
checks `wg`/`wg-quick`, and compiles the finite measurement script. CI gate
requires this job in addition to all existing backend, frontend and sidecar
checks. Local fixtures also reject a mismatched source revision before make.
No application assertions or index-capability checks were bypassed.

- Sidecar PR 25: release `semantic-search-v3.1.1`, commit
  `ce9346aa1697748a9ccde158c6a2d232264014b3`.
- Root PR 48: records released sidecar pointer and real Redis migration CI.
- Root PR 49: deployment bootstrap and finite manual idle measurement transport.
- Root main commit `3e64ddd328edc8a5b02c59fa6771126553b1f596`.
- Required PR CI run `43042490806`: all gates pass, including Node 22 and 24.
- Main CI/deploy run `43043350946`: all checks and BOTH deploy jobs pass.
- Semantic HTTP ready at `2026-11-11T15:01:10Z`; gRPC ready, maxK 20.
- Capability guard baseline/candidate: 121546 chunks, 22294 indexed notices;
  literal `capability deltas   : none`, `release check       : OK — no capability class lost`.
  The break-glass input remains false.
- Backend and frontend source versions unchanged at 3.1.2 and 3.1.1.
- Local backend/frontend remain on clean dev, sidecar on clean main; released
  sidecar tag and root gitlinks match these exact source commits.

## Production idle measurement method

Before deployment, the old container completed both real quiet windows.
The first requests reached the loopback BACKEND origin API, not the CDN or a
standalone embedding benchmark. Each query was previously unseen in that
process. HTTP 200 and semantic mode were required. Sidecar timing logs, actual
major faults/read bytes, image/start/restart identity, index generation and
foreground search interruptions were recorded. Health/log polling performs no
inference. No public traffic was blocked and no cache/swap was flushed.

The finite manual `measure-idle-search.yml` workflow uses the existing deploy
VPN because local private-host SSH began timing out. It shares the deploy
concurrency group, starts only from main, and stops after 180/600 second windows.
It is NOT a scheduled automation. Public search traffic resets the quiet timer;
a bounded timeout fails rather than describing an interrupted window as idle.
A repeat/cache-hit and an extra novel warm-control request occur AFTER each
first request. The warm control was added for postdeploy diagnostics and is not
part of the paired baseline comparison.

Raw evidence: `_workspace/idle-search-release-20261111/production-baseline.json`,
`production-deploy-log.txt`, `backend-deploy-log.txt`, and manual measurement
run `43044601474`. The paired baseline first-request values are 382.501438ms
(180s) and 750.936258ms (600s); seed/startup traffic is not a fixed-idle sample.

## Paired production results

The manual run `43044601474` succeeded. New image:
`sha256:358b54a548bf28afd21060b276065d54902cb87143d5f7ddb4388a0eb58de338`,
started `2026-11-11T15:00:22.645575742Z`, restart count 0 throughout measurement.
All five compose/env hashes exactly match the predeploy backup. Both first
requests had positive model execution, HTTP 200, semantic mode, identical
ordered notice IDs to baseline, unchanged indexed chunks/lastUpdateAt, and no
index update during either measured window.

- 180 seconds: origin API **382.501 → 462.663 ms (+20.96%, NOT improved)**.
  Sidecar total 356.6 → 344.7 ms (-3.34%). Major faults 186 → 14.
  17 native warmups occurred, with no intervening public search.
- 600 seconds: origin API **750.936 → 315.249 ms (-58.02%)**.
  Sidecar total 445.9 → 286.8 ms (-35.68%). Major faults 164 → 10.
  68 native warmups occurred during the complete wait. Six public requests
  initially interrupted this interval; the probe RESET its quiet timer and
  then observed a full final 600 seconds without a foreground search.
  Total wait was 738.45 seconds, not a falsely labelled interrupted 600s gap.
- Fresh, different warm-control origin requests after the two first samples
  took 594.731 and 965.053 ms (sidecar totals 368.5 and 282.2 ms). This exposes
  substantial variation OUTSIDE the sidecar timed section. It does not isolate
  whether backend DB hydration, transport or scheduling is responsible.
- Repeat requests used the embedding cache and are NOT comparable fresh-model
  controls; the first samples above did not use cached embeddings.

**The production improvement is partial, not a two-window success.** There is
one paired observation per window, not a distribution or p95 claim. The two
arms are time-separated, not concurrent randomized runs. The 3-minute origin
latency regressed despite slightly lower engine time, and first requests still
incur major faults. The next diagnostic priority is request-correlated backend
phase/DB/transport timing plus repeated novel-query quiet windows; do not label
this release as eliminating all perceived first-request delay.

Raw final result: `_workspace/idle-search-release-20261111/production-deployed.json`.
Full command/result, original/modified hashes, operational rollback fixture,
and four artifact paths are recorded in the adjacent `VERIFICATION.txt`.
The operational rollback script was tested on an INDEPENDENT recording-Docker
fixture: old image arguments, deploy marker and compose preservation passed.
Production was NOT rolled back; it remains on the new image. Earlier independent
source rollback restored 94 original hashes and 387 passed / 3 skipped tests.
