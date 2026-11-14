# Deployment and Reconciliation Integration

## Scope

LawCast's manual deploy.sh and both backend/semantic-search GitHub Actions remote sessions use a host-installed deployment supervisor. The workflow wrapper covers git synchronization and ALL post-deploy health, runtime, gRPC and capability gates, not just docker compose up. A nested manual deploy verifies its live parent token and does not prematurely end the transaction. Host helpers live outside the checkout, surviving git reset/clean. Other projects' deploy scripts are unchanged, though the generic guard can be adopted explicitly.

## Failure semantics

The timer is NEVER stopped or disabled by deployment automation. An in-flight reconciliation pass drains under its lock before a project-scoped repair hold is published. The timer continues monitoring all projects and can still repair unaffected projects. Only the deploying project's automatic starts/creates are paused.

The child process inherits a host deployment lock. Successful exit, healthy running target containers and a valid same-name inventory capture are all required before atomically publishing new project fingerprints, clearing retry counters and resuming repair. Existing target names remain mandatory. APP_VERSION interpolation comes from the running backend, not the supervisor's possibly stale/missing environment. Unaffected project inventory entries remain untouched.

On nonzero exit, readiness/capture error, cancellation or timeout, keep the original inventory and a failed target-project repair hold. Do not resurrect an old/partial release. SIGTERM/HUP/INT and timeout terminate the child process group before finalization. After SIGKILL/reboot, the timer recognizes dead/zombie/reused owners through PID/start ticks/boot ID and marks the hold aborted. No global maintenance marker or disabled timer remains. A verified retry or an explicit healthy-release verification-only guarded command clears the target hold. This is monitored failure isolation, not an automatic application/data rollback.

## Verification and production application

- 35 unit regressions, including prior reconciliation invariants, passed locally and on Linux.
- Real fault suite on an isolated disposable container passed success, exit 23, missing-target failed deploy, successful retry, interpolation-preserving recreation, timeout, SIGTERM, SIGKILL/orphan-lock retention and SSH heredoc input preservation.
- The first SIGKILL test exposed an inherited stdout-pipe test-harness wait: corrected collection to wait for supervisor exit, verify the orphan lock, then kill the test orphan before collecting EOF. This was a harness ordering defect; raw first-run evidence is retained.
- Installed on production at 2026-11-14 15:17:39 UTC+09:00. A no-service-change exit-23 smoke kept the inventory unchanged and timer active; a verified nested/list-only success refreshed fingerprints and cleared the hold.
- All original 14 containers retained identity/PID/start/restart/health/network state and Docker/containerd/nginx activation; liveRestore=true remained set. No production service was deliberately stopped for fault injection.

## Operational references

Versioned instructions and source: ops/container-reconcile/README.md. Failure-hold state: /var/lib/container-reconcile/deployment-holds.json. Resolve by fixing/retrying the guarded deployment; after a manually restored known-good healthy release, run `/usr/local/sbin/container-deploy-guard.py --project lawcast -- /bin/true` to verify/capture/clear without redeployment.

Raw manifests, backups, diffs, rollback and transcripts: ignored _workspace/downtime-20261114/deploy-integration/ and /root/lawcast-ops/deploy-integration-20261114/. Host-file rollback must be paired with a repository workflow revert after the workflow integration is merged, since the workflow explicitly invokes the installed guard.
