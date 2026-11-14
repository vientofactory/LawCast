# Docker Live Restore — Reload-Only Activation

## Scope and compatibility

The user explicitly requested checking and, if possible, activating live-restore without interrupting current containers. The production engine reports Linux, Docker 29.9.3, overlay2, inactive Swarm and standalone containers. Its systemd ExecReload sends SIGHUP to dockerd. Docker's official live-restore documentation supports enabling the field through daemon reload on Linux.

Preserved existing userns-remap=default, json-file logging and rotation. The only daemon.json semantic change is live-restore=true. No runtime restart, container recreation, package update, storage/network change or policy change was requested or executed.

## Application and verification

- Backed up the original daemon.json and SHA256 under `/root/lawcast-ops/live-restore-20261114/`.
- Validated original, modified and independently reverted-copy configuration through `dockerd --validate --config-file`; all exited 0.
- Applied the modified file atomically while retaining root ownership and 0644 permissions; executed `systemctl reload docker` only.
- Confirmed actual `docker info` LiveRestoreEnabled=true, not merely the persisted JSON field.
- Compared all 14 container IDs, host PIDs, StartedAt, RestartCount, running/health states, network sandbox IDs and image IDs before/after. All remained identical.
- Docker/containerd/nginx MainPID and activation timestamps remained identical. Previous nginx weak-dependency and needrestart deferral settings remained unchanged.
- Checked Docker reload journal and container start/stop/die/restart events. Full evidence and final HTTP sample totals are in the local VERIFICATION.txt.

## Rollback and limitations

`bash /root/lawcast-ops/live-restore-20261114/ROLLBACK.sh --production` is an explicitly invoked rollback: verify current/backup hashes, atomically restore the original file and reload Docker, then require LiveRestoreEnabled=false. It does not restart Docker. This rollback was exercised on an independent file copy only, restoring the original bytes/hash; production remains enabled.

Live-restore is not protection against host reboot, every containerd failure, major engine upgrades, changed daemon storage/network options, or log-buffer exhaustion during prolonged daemon unavailability. The work verifies activation and preservation during reload, not crash survival; no disruptive daemon-stop test was performed on production. Supervised maintenance and the earlier needrestart deferrals remain necessary.

Local evidence lives in ignored `_workspace/downtime-20261114/live-restore/`: original.json, MODIFIED_FILE, DIFF_FILE, manifest.json, ROLLBACK.sh, apply.py, before.json, after.json, apply-output.txt, live-final-checks.txt, http-observation.jsonl and VERIFICATION.txt.

References: https://docs.docker.com/engine/daemon/live-restore/ and [previous prevention settings](prevention.md).

## Final observation

Applied at 14:36:08 UTC+09:00. All 30 public health checks from 14:35:59 to 14:37:02 returned HTTP 200 with curl exit 0. Settled-state readback again retained all 14 container identities, process activation and liveRestore=true; the inspected container lifecycle event count was zero.
