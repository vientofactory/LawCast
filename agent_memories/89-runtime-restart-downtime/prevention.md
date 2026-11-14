# Runtime Restart Prevention — Production Application

## Applied settings

Explicit user approval covered these two settings and a metadata-only systemd reload. Applied on 2026-11-14 at 14:22:44 UTC+09:00.

- `/etc/systemd/system/docker.service.d/override.conf`: replaced `Requires=nginx.service` with `Wants=nginx.service`, retaining `After=nginx.service`. This removes stop propagation from nginx while retaining weak startup activation/order. The vendor dependency on docker.socket and the hardened allocator drop-in remain unchanged.
- `/etc/needrestart/conf.d/99-lawcast-runtime-maintenance.conf`: appended a zero-valued override for `^(docker|containerd|nginx)\.service$`. These services remain visible as deferred restart candidates; they are not blacklisted. Other services keep their existing selection policy.
- Ran `systemctl daemon-reload`, not restart/reload of Docker, containerd or nginx. No packages, live-restore setting, container restart policy or APT security-update configuration were changed.

## Verification

- `systemd-analyze verify docker.service` exited 0, without diagnostics.
- Effective Docker Requires excludes nginx and retains docker.socket; Wants and After include nginx; NeedDaemonReload=no.
- Loaded actual needrestart configuration through its Perl evaluator and the installed service-selection algorithm: Docker/containerd/nginx deferred; cron remains automatic. Baseline and modified fixtures both pass.
- `needrestart -r l -m u` exited 0 and reported no currently outdated services or containers. This was list-only, not an induced update or restart.
- All 14 containers retained IDs, host PIDs, StartedAt, RestartCount, running state and health state. Docker/containerd/nginx retained MainPID and activation timestamp.
- No container start, stop, die or restart events appeared in the inspected application window.
- 30 public HEAD health checks spanning 14:22:23–14:23:27 all returned HTTP 200 with curl exit 0.
- An independent copy was reverted using executable, hash-guarded ROLLBACK.sh. The original Docker override SHA256 and baseline selection behavior were restored on the copy. Production remains modified.

## Operations and rollback

Production backup, manifest, modified files, apply transcript, before/after snapshots and rollback script: `/root/lawcast-ops/downtime-20261114-prevention/`.

Original Docker override SHA256: `15d1d35f743b755631855820d3dd11564f578b1c74afc59a18f88403505771b7`.

An explicitly requested production rollback can run `bash /root/lawcast-ops/downtime-20261114-prevention/ROLLBACK.sh --production`. It checks modified-file hashes before restoring the original override, removing the newly added needrestart snippet and reloading systemd metadata. It deliberately does not restart services. A diverged file causes rollback to stop rather than overwrite later changes.

Security package installation remains enabled. Docker/containerd/nginx must be restarted during supervised maintenance to activate any subsequently installed process-level fixes. Package maintainer actions outside needrestart and host reboots are not prevented. No disruptive replay of the incident was performed on production; live-restore and workload reconciliation remain separate follow-ups.

Local raw evidence: ignored `_workspace/downtime-20261114/prevention/VERIFICATION.txt`, `DIFF_FILE`, `manifest.json`, `before.json`, `after.json`, `live-final-checks.txt` and `http-application.jsonl`.

See [incident diagnosis](diagnosis.md) for the historical causal evidence and metadata limitations.
