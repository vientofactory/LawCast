# Required Container Reconciliation

## Production configuration

Installed after the user explicitly requested recovery of missing/stopped required containers without interrupting existing services. The fixed inventory covers all 14 previously observed containers across LawCast, Hashguard, FlowAuth, Gatekeeper and Netdata, using their Compose ownership labels. It contains paths, service/image identities, data prerequisites and SHA256 fingerprints, not expanded environment values.

- `/usr/local/sbin/container-reconcile.py`: Python-standard-library-only reconciler.
- `/etc/container-reconcile/inventory.json`: root-only explicit required-container inventory.
- `/etc/systemd/system/container-reconcile.service`: bounded oneshot, ordered after Docker but does not start/restart it, timeout 240 seconds.
- `/etc/systemd/system/container-reconcile.timer`: enabled persistent boot activation; first active check after 15 seconds, boot check after 120 seconds, then 60 seconds after each completed pass.
- `/var/lib/container-reconcile/state.json`: confirmation/retry counters and latest degraded count.
- `/run/container-reconcile.maintenance`: maintenance inhibit marker; `/run/container-reconcile.lock`: exclusive concurrency lock.

## Recovery invariants

Missing/exited/created state needs at least two observations and 60 seconds. Existing exited/created containers start by their current ID, without replacement. Missing containers recover through their recorded Compose project/service using `up -d --no-deps --no-recreate --no-build --pull never`.

Creation requires unchanged normalized Compose config and local image ID, all captured named volumes/networks, and existing bind sources. A missing data volume must not silently produce an empty DB. Dependencies must be running and not starting/unhealthy. Identity conflicts, alternate-name instances, concurrent state changes, paused/dead/removing/restarting containers and running unhealthy containers are reported without mutation. Running containers are never stopped/restarted. Each mutation rechecks ownership, current state, dependencies and maintenance first.

At most three action/preflight attempts per pass and three per container per rolling hour; retry backoff is 5/10 minutes before attempts two/three. State checkpoints precede start/create calls. Docker API failure is reported without daemon restart. Degraded passes exit 1 and journal the reason; healthy passes exit 0. No external notification destination was added.

## Validation

- Original installed paths were absent; original-state.json and manifest preserve that baseline.
- 19 unit tests cover positive recovery, grace, budgets, retries, data/config guards, health/identity/maintenance/dependency handling and races.
- An isolated disposable container used the existing Redis image, no network/ports/persistent data, read-only filesystem, dropped capabilities and bounded memory/CPU/PIDs. Real tests stopped/restarted it with the same ID, deleted/recreated it from Compose, validated maintenance/lock behavior, and blocked creation on changed config and a missing required data volume. The test container was removed afterwards.
- All 14 production container IDs/PIDs/StartedAt/RestartCount/health/network sandboxes and Docker/containerd/nginx PID/activation timestamps remained identical through fault tests and installation. liveRestore=true and prior prevention settings remain in place.
- Independent rollback-fixture validation removed only the four new files and restored their originally absent state; production remains installed.
- Initial systemd run reports `summary: required=14 actions=0 degraded=0`; timer is enabled and active. Final timer/journal/HTTP observation evidence is recorded in local VERIFICATION.txt.

## Maintenance and deployment contract

Before intentionally stopping/removing a required service, create the maintenance marker, stop the timer and wait for an active pass to finish. This prevents the reconciler from undoing an intentional stop. The marker clears across reboot; disable the timer for persistent suspension.

A Compose/config/image-changing deployment must refresh the inventory fingerprints after healthy rollout, using the SAME explicit container names. Capture the new inventory to a temporary file, review it and atomically replace the active file before resuming. Otherwise missing-container creation deliberately defers instead of deploying an unexpected config/image. Existing stopped containers can still start by their own ID.

Complete commands, check-only validation, status/journal usage, inventory refresh and rollback are in `/root/lawcast-ops/container-reconcile-20261114/OPERATIONS.md`; the same document lives in ignored `_workspace/downtime-20261114/reconcile/OPERATIONS.md`.

## Rollback and evidence

`bash /root/lawcast-ops/container-reconcile-20261114/ROLLBACK.sh --production` verifies all installed file hashes, disables the timer, waits for any active pass, removes only the four new installed files and reloads systemd metadata. It does not stop Docker/containers or undo needrestart/live-restore settings; logs/state remain. After inventory/code changes, review manifest divergence rather than bypassing the rollback hash guard.

Raw evidence stays in ignored `_workspace/downtime-20261114/reconcile/`, with an on-server copy under `/root/lawcast-ops/container-reconcile-20261114/`. No production Docker restart or intentional stop of any existing service was performed.

See [initial diagnosis](diagnosis.md), [dependency/needrestart prevention](prevention.md), and [live-restore](live-restore.md).

## Final observed result

Timer installation completed at 14:47:23 UTC+09:00. Automatic invocations and final service Result=success/ExecMainStatus=0 were observed. All passes had actions=0/degraded=0 with the original 14 containers intact. Public HTTP observations from 14:46:57 to 14:48:35 returned 45/45 HTTP 200, each curl exit 0. Production lifecycle-event filtering excludes the disposable proof container and finds zero required-container start/stop/die/restart events.
