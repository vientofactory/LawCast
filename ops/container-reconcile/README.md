# Deployment-aware container reconciliation

Production uses `/usr/local/sbin/container-reconcile.py`, `/usr/local/sbin/container-deploy-guard.py`, `/usr/local/sbin/container-reconcile-capture.py` and `/usr/local/sbin/container_reconcile_runtime.py`. The fixed inventory is `/etc/container-reconcile/inventory.json`.

## Deployment entry points

Both LawCast Actions workflows wrap the ENTIRE remote Bash session:

```sh
/usr/local/sbin/container-deploy-guard.py --project lawcast -- bash -s
```

This includes git synchronization, build, health/version/runtime checks, gRPC readiness and the semantic index-capability release gate. Direct `./deploy.sh [service]` automatically enters the same guard. Nested invocations verify the parent's live token rather than ending a second transaction early. `./deploy.sh list` remains read-only.

Other projects may opt into the generic guard explicitly, but their deployment scripts are not changed by the LawCast integration.

## Success and failure semantics

The guard holds a host deployment lock, drains any in-flight reconciliation pass and publishes a durable PROJECT-SCOPED repair hold before starting the deployment child. The timer is never stopped/disabled: it continues detecting failures, repairs unaffected projects, and reports held-project failures without creating/starting those containers. The global manual-maintenance marker is never created, removed or overridden by deployment automation.

Success means the complete child script exits zero, all required target containers are running with healthy healthchecks where present, and inventory capture succeeds. Only then does the guard atomically replace target-project fingerprints (keeping the same required names), reset target retry/confirmation state and clear that project's hold. Other projects are not recaptured. `APP_VERSION` interpolation is recovered from the actual running backend so a parent shell's missing/stale variable cannot corrupt recreation fingerprints.

Failure, cancellation, readiness/capture errors and timeouts retain the old inventory and a target-only monitor/repair hold. The original child exit code is preserved. SIGTERM/HUP/INT and timeout handling terminate the deployment process group before finalizing. The deployment lock is inherited by children to prevent a killed supervisor from permitting an overlapping orphan deployment.

SIGKILL/reboot cannot run a trap. The next timer pass recognizes a dead/reused/zombie owner through PID, Linux process start ticks and boot ID and marks its hold `aborted`. Monitoring remains active; affected-project repair stays held until a verified deployment. This deliberately avoids resurrecting an old or partially deployed image after a failed release. No automatic application/data rollback is attempted.

## Inspect and resolve a failed release

```sh
systemctl is-active container-reconcile.timer
journalctl -u container-reconcile.service --since '1 hour ago'
cat /var/lib/container-reconcile/deployment-holds.json
```

Fix/retry the deployment through the same guard. After an operator has restored a known-good healthy release, the following verification-only guarded command refreshes fingerprints and clears the target hold WITHOUT redeploying containers:

```sh
/usr/local/sbin/container-deploy-guard.py --project lawcast -- /bin/true
```

Manual maintenance still uses the existing `/run/container-reconcile.maintenance` procedure. Do not edit/remove a failed-release hold merely to trigger old-image recreation. The timer may report healthy running containers while also reporting a held project; monitoring is active even when automatic repair of that project is deliberately suppressed.

## Tests

```sh
python3 -m unittest discover -s tests/ops -v
python3 -m py_compile ops/container-reconcile/*.py
bash -n deploy.sh
python3 tools/check-agent-guidelines.py
```

Host fault validation uses an isolated disposable container and separate inventory/hold/lock directories; it does not stop/recreate any of the 14 production containers. Evidence is retained under ignored `_workspace/downtime-20261114/deploy-integration/` and `/root/lawcast-ops/deploy-integration-20261114/`.
