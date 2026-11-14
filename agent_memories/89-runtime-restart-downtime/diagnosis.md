# Runtime Restart Downtime — 2026-11-14

## Conclusion

The outage was initiated by unattended libc security updates and the ensuing service restart transaction, not an observed OOM kill or a host reboot at onset. needrestart explicitly restarted containerd and nginx. Docker was deliberately deferred by needrestart, but its local systemd drop-in requires nginx, allowing nginx's restart to propagate into Docker. Docker stopped at 06:10:25 and completed startup at 06:10:59, yet the container workloads did not recover. All times below are UTC+09:00.

Confidence: high for the update/service-stop chain and persistent workload outage; incomplete for the precise historical restart-policy/state decision.

## Timeline and sources

- 06:09:40: journal starts apt-daily-upgrade.service.
- 06:09:43: unattended-upgrades starts; 06:09:59 selects libc and other security updates.
- 06:10:00–06:10:47: dpkg transaction upgrades libc6/libc-bin and related packages from 2.39-0ubuntu8.9 to 2.39-0ubuntu8.12.
- 06:10:25: needrestart restarts containerd and other services; Docker receives SIGTERM and logs stopping restart-manager for 14 historical container IDs.
- 06:10:40: Docker logs Force shutdown daemon, then shutdown complete. containerd had been unavailable during Docker shutdown.
- 06:10:41: nginx stops/starts; containerd starts; Docker startup begins.
- 06:10:42–06:10:53: Docker restore stops historical container tasks, logs task-delete events, and forcibly terminates three tasks after their 10-second SIGTERM timeout.
- 06:10:56–06:10:59: Docker removes 14 stale sandboxes and completes initialization. No later Docker journal entries occur before the recovery shutdown at 12:05:46.
- 06:12:57: UptimeRobot first detects LawCast Backend HTTP 502; 06:13:42 confirms incident.
- 06:20:15: sysstat reports host memory used 4.73%, down from 58.97% at 06:10:00; host remains alive throughout the outage.
- 12:05:49: orderly shutdown; 12:06:08: host boots. This is the recovery phase, not the initial cause.
- 12:08:33–12:10:28: current 14 containers are newly created. LawCast backend starts at 12:08:39.
- 12:09:40: UptimeRobot resolves LawCast Backend incident; measured downtime is 5h 55m 58s with five-minute checks.
- Final readback: all 14 containers run; all 13 healthchecked containers report healthy, Ollama has no displayed health status.

UptimeRobot incident: https://dashboard.uptimerobot.com/incidents/379740633776157618

Netdata's already-open 06:04–06:19 view shows chart data ending near the restart period and subsequent No data. Its monitoring container was affected too; an empty/zero chart endpoint is not proof of zero host RAM or host shutdown. Use persistent host sysstat and journal records to bridge the monitoring gap.

## Configuration and causal interpretation

`/etc/systemd/system/docker.service.d/override.conf` (mtime 2026-05-22):

```ini
[Unit]
After=nginx.service
Requires=nginx.service
```

`/var/log/unattended-upgrades/unattended-upgrades-dpkg.log` explicitly prints containerd.service and nginx.service in its systemctl restart command. Docker appears in Service restarts being deferred, not in that direct restart command. nginx's Requires dependency is therefore the strongly supported indirect Docker restart path. containerd's parallel restart disrupts Docker's runtime connection and contributes to the unclean restore sequence.

`/etc/docker/daemon.json` (mtime 2026-04-28) has user namespace remapping and log rotation, but no live-restore option. Current docker info confirms liveRestore=false. Current Docker is 29.9.3; the day's dpkg log shows libc, firmware and apache2-utils upgrades, NOT a Docker package upgrade. Do not confuse an older apt history entry for Docker upgrades with today's trigger.

The daemon's successful startup did not restore application availability. The restore logs show task termination and sandbox removal, and sysstat shows the workload memory disappears for the ensuing hours. This is a persistent recovery failure, not a six-hour Docker startup.

All CURRENT containers have restartpolicy=unless-stopped, restarts=0, oom=false. However they were newly created during recovery, and the old metadata is gone (only 14 current config.v2.json files remain). Their counters do not establish historical OOM status or the old containers' policies. No OOM-kill, out-of-memory or kernel panic entries occur in the previous boot's kernel journal for the relevant interval. At 06:10:00, sysstat records 2,783,836 KiB available RAM, 58.97% used RAM, 39.70% used swap and 53.45% idle CPU. These are ten-minute samples, not a guarantee against every brief pressure spike, but together with explicit service-stop logs they argue against OOM as the initiating cause.

The precise old restart-policy/manual-stop/restore-state branch is unproven after container recreation. Do not assert that unless-stopped alone caused this incident or that changing every policy to always is a verified fix. No explicit historical auto-start failure error was found. No dedicated systemd application/Compose units were found in the current unit inventory.

## Recommended remediation order — not applied

1. Review the Docker-to-nginx hard dependency. Remove the stop-propagating requirement if there is no operational necessity; retain only appropriate startup ordering or a weak dependency after checking why it was introduced.
2. Exclude BOTH containerd and Docker from unattended needrestart restarts, preserving security updates and doing runtime restarts in a supervised maintenance window. Excluding Docker alone did not protect this deployment; nginx dependency propagation must also be addressed.
3. Evaluate Docker live-restore for supported runtime maintenance, including current userns-remap/network configuration. It is not a guarantee against host reboot or every containerd failure.
4. Add externally observable workload reconciliation after runtime restart, with explicit desired-container inventory and bounded recovery. Docker active and container RestartCount=0 are insufficient health gates.
5. Keep an external host/container monitor so a stopped Netdata container does not erase incident visibility. UptimeRobot recorded successful email/Discord/one push delivery at onset, while several other device pushes failed; audit alert routing separately.
6. Reproduce the restart sequence on an isolated replica before claiming a permanent fix. Preserve old container metadata and Docker events before any future recreation.

## Evidence and verification

Raw read-only SSH transcripts live in ignored `_workspace/downtime-20261114/`:
- `server-initial.txt`: boot list, last -x, current container inspect, previous boot tail.
- `server-onset.txt`: onset journal, Docker/containerd journal, apt/dpkg and unattended upgrade logs.
- `restart-detail.txt`: needrestart output, daemon configuration and Docker unit dependencies.
- `causal-detail.txt`: nginx timing, current create times, recovery daemon startup, sysstat and kernel evidence.
- `final-checks.txt`: effective dependency/flags, old drop-in mtimes, outage host metrics, current running status.
- `corroboration.txt`: surviving metadata count and host heartbeat during outage.

All SSH operations were reads. No production restart, configuration edit, package action or deployment was executed. Browser observations used the user's existing Netdata and UptimeRobot Chrome tabs. No source code was modified, no commit or release was created.

Reference semantics:
- https://www.freedesktop.org/software/systemd/man/latest/systemd.unit (Requires stop/restart propagation)
- https://docs.docker.com/engine/daemon/live-restore/ (daemon restart versus container continuity)
- https://docs.docker.com/engine/containers/start-containers-automatically/ (restart policies and stopped state)

## Approved prevention follow-up

The user subsequently approved the two targeted production settings. See [production application and verification](prevention.md) for the metadata-only reload, unchanged service identities, HTTP observations and copy-only rollback. The earlier read-only status describes the diagnosis phase only.
