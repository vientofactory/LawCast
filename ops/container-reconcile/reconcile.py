#!/usr/bin/env python3
"""Reconcile an explicit standalone-container inventory without replacing live work."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from container_reconcile_runtime import load_json, owner_alive


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


class Docker:
    def run(self, args, cwd=None, env=None):
        result = subprocess.run(['docker', *args], cwd=cwd, text=True,
                                capture_output=True, timeout=45,
                                env=dict(os.environ, **(env or {})))
        if result.returncode:
            # Do not expose Compose-expanded configuration or environment values.
            raise RuntimeError('docker command failed: ' + args[0] +
                               ' exit=' + str(result.returncode))
        return result.stdout

    def containers(self):
        ids = self.run(['ps', '-aq']).split()
        return json.loads(self.run(['inspect', *ids])) if ids else []

    def compose(self, item):
        args = ['compose', '--project-directory', item['workdir'], '-p', item['project']]
        for name in item['files']:
            args += ['-f', name]
        return args

    def prepare_missing(self, item):
        args = self.compose(item)
        config = json.loads(self.run(args + ['config', '--format', 'json'], item['workdir'],
                                     item.get('compose_env', {})))
        canonical = json.dumps(config, sort_keys=True, separators=(',', ':')).encode()
        if hashlib.sha256(canonical).hexdigest() != item['config_sha256']:
            raise RuntimeError('compose configuration changed; refresh inventory during maintenance')
        image = json.loads(self.run(['image', 'inspect', item['image_ref']]))[0]
        if image['Id'] != item['image_id']:
            raise RuntimeError('local image changed; refresh inventory during maintenance')
        for name in item['volumes']:
            self.run(['volume', 'inspect', name])
        for name in item['networks']:
            self.run(['network', 'inspect', name])
        for name in item['binds']:
            if not Path(name).exists():
                raise RuntimeError('required bind source missing')

    def recover(self, item, existing):
        if existing:
            self.run(['start', existing['Id']])
        else:
            self.run(self.compose(item) + ['up', '-d', '--no-deps', '--no-recreate',
                     '--no-build', '--pull', 'never', item['service']], item['workdir'],
                     item.get('compose_env', {}))


def labels_match(row, item):
    labels = row.get('Config', {}).get('Labels') or {}
    return (labels.get('com.docker.compose.project') == item['project'] and
            labels.get('com.docker.compose.service') == item['service'])


def reconcile(config, state, docker, maintenance, now, check=False, emit=print):
    if maintenance():
        # Do not count maintenance observations towards a recovery decision.
        for value in state.get('items', {}).values():
            value.pop('first_bad', None)
            value['observations'] = 0
        emit('maintenance: no recovery actions')
        return 0
    rows = docker.containers()
    by_name = {r['Name'].lstrip('/'): r for r in rows}
    names = {i['name']: i for i in config['containers']}
    records = state.setdefault('items', {})
    actions = 0
    degraded = 0
    blocked = config.get('blocked_projects', {})
    for project, hold in blocked.items():
        emit(project + ': deployment ' + hold['phase'] + '; monitor-only, automatic repair held')
    for item in config['containers']:
        name = item['name']
        row = by_name.get(name)
        record = records.setdefault(name, {})
        record['attempts'] = [t for t in record.get('attempts', []) if now - 3600 < t <= now]
        if row and not labels_match(row, item):
            degraded += 1
            emit(name + ': identity conflict; no action')
            continue
        if row and row['State']['Running']:
            record.pop('first_bad', None)
            record['observations'] = 0
            health = row['State'].get('Health', {}).get('Status')
            if health == 'unhealthy':
                degraded += 1
                emit(name + ': unhealthy; report only, no restart')
            continue
        degraded += 1
        status = row['State']['Status'] if row else 'missing'
        if item['project'] in blocked:
            record.pop('first_bad', None)
            record['observations'] = 0
            emit(name + ': ' + status + '; deployment hold prevents repair')
            continue
        if row and status not in ('exited', 'created'):
            emit(name + ': ' + status + '; no action')
            continue
        if not row and any(labels_match(r, item) for r in rows):
            emit(name + ': service exists under another name; no action')
            continue
        if check:
            emit(name + ': ' + status + '; check-only')
            continue
        if record.get('first_bad', now) > now:
            record.pop('first_bad', None)
            record['observations'] = 0
        record.setdefault('first_bad', now)
        record['observations'] = record.get('observations', 0) + 1
        if (record['observations'] < config['confirmations'] or
                now - record['first_bad'] < config['grace_seconds']):
            emit(name + ': ' + status + '; awaiting confirmation')
            continue
        attempts = record['attempts']
        cooldown = min(1800, 300 * (2 ** max(0, len(attempts) - 1)))
        if len(attempts) >= 3 or (attempts and now - attempts[-1] < cooldown):
            emit(name + ': retry limited; manual review required')
            continue
        dependencies = [by_name.get(d) for d in item['dependencies']]
        if any(not d or not d['State']['Running'] or
               d['State'].get('Health', {}).get('Status') in ('starting', 'unhealthy')
               for d in dependencies):
            emit(name + ': waiting for dependencies')
            continue
        if actions >= config['max_actions']:
            emit(name + ': per-run action budget reached')
            continue
        actions += 1
        try:
            if not row:
                docker.prepare_missing(item)
            # Recheck immediately before mutation to reduce deployment races.
            current = docker.containers()
            latest = next((r for r in current if r['Name'].lstrip('/') == name), None)
            if maintenance():
                emit(name + ': maintenance enabled; no action')
                continue
            if latest and (not labels_match(latest, item) or latest['State']['Running']):
                emit(name + ': state changed; no action')
                continue
            if latest and (not row or latest['Id'] != row['Id'] or
                           latest['State']['Status'] not in ('exited', 'created')):
                emit(name + ': identity/state changed; no action')
                continue
            if row and not latest:
                emit(name + ": disappeared during scan; no action")
                continue
            current_names = {r["Name"].lstrip("/"): r for r in current}
            if any(not current_names.get(d) or not current_names[d]["State"]["Running"] or
                   current_names[d]["State"].get("Health", {}).get("Status") in ("starting", "unhealthy")
                   for d in item["dependencies"]):
                emit(name + ": dependency state changed; no action")
                continue
            if not latest and any(labels_match(r, item) for r in current):
                emit(name + ': service moved; no action')
                continue
            attempts.append(now)
            if '_checkpoint' in state:
                state['_checkpoint']()
            docker.recover(item, latest)
            restored = next((r for r in docker.containers()
                             if r['Name'].lstrip('/') == name), None)
            if restored and labels_match(restored, item) and restored['State']['Running']:
                degraded -= 1
                record.pop('first_bad', None)
                record['observations'] = 0
                emit(name + ': recovered ' + status + '; running')
            else:
                emit(name + ': recovery did not reach running state')
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            # Throttle preflight failures as well as failed start attempts.
            if not attempts or attempts[-1] != now:
                attempts.append(now)
            emit(name + ': recovery deferred: ' + str(error))
    state['last_run'] = now
    state['degraded'] = degraded
    emit('summary: required=' + str(len(names)) + ' actions=' + str(actions) +
         ' degraded=' + str(degraded))
    return int(degraded > 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory', default='/etc/container-reconcile/inventory.json')
    parser.add_argument('--state', default='/var/lib/container-reconcile/state.json')
    parser.add_argument('--lock', default='/run/container-reconcile.lock')
    parser.add_argument('--maintenance', default='/run/container-reconcile.maintenance')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--holds', default='/var/lib/container-reconcile/deployment-holds.json')
    args = parser.parse_args()
    with open(args.lock, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('locked: another reconciliation is active')
            return 0
        config = json.loads(Path(args.inventory).read_text())
        holds = load_json(args.holds, {})
        stale = False
        for hold in holds.values():
            if hold['phase'] == 'deploying' and not owner_alive(hold['owner']):
                hold['phase'] = 'aborted'
                hold['reason'] = 'deployment owner exited; monitor-only until verified deployment'
                stale = True
        if stale and not args.check:
            atomic_json(args.holds, holds)
        config['blocked_projects'] = holds
        state_path = Path(args.state)
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        def checkpoint():
            atomic_json(state_path, {k: v for k, v in state.items() if k != '_checkpoint'})
        if not args.check:
            state['_checkpoint'] = checkpoint
        try:
            result = reconcile(config, state, Docker(), lambda: Path(args.maintenance).exists(),
                               time.time(), args.check)
        except (RuntimeError, subprocess.TimeoutExpired) as error:
            print('docker unavailable or scan failed; no daemon restart: ' + str(error))
            return 1
        if not args.check:
            checkpoint()
        return result


if __name__ == '__main__':
    raise SystemExit(main())
