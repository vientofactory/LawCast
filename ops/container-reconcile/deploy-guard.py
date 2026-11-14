#!/usr/bin/env python3
"""Pause target-project repair around a complete deployment, without stopping monitoring."""
import argparse
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

from container_reconcile_runtime import atomic_json, load_json, lock_file, owner_alive, process_identity


class Guard:
    def __init__(self, root=Path('/'), capture=None, ready_timeout=300):
        self.root = Path(root)
        self.inventory = self.root / 'etc/container-reconcile/inventory.json'
        self.holds = self.root / 'var/lib/container-reconcile/deployment-holds.json'
        self.reconcile_lock = self.root / 'run/container-reconcile.lock'
        self.deploy_lock = self.root / 'run/container-deploy.lock'
        self.maintenance = self.root / 'run/container-reconcile.maintenance'
        self.capture_path = capture or Path(__file__).with_name('container-reconcile-capture.py')
        if not self.capture_path.exists():
            self.capture_path = Path(__file__).with_name('capture-inventory.py')
        self.ready_timeout = ready_timeout

    def verify_nested(self, project):
        hold = load_json(self.holds, {}).get(project)
        token = os.environ.get('CONTAINER_DEPLOY_GUARD_TOKEN')
        if not hold or not token or hold['token'] != token or hold['phase'] != 'deploying' or not owner_alive(hold['owner']):
            raise RuntimeError('nested deployment has no live parent guard')

    def capture(self, names):
        spec = importlib.util.spec_from_file_location('inventory_capture', self.capture_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.capture(names)

    def ready(self, names):
        result = subprocess.run(['docker', 'inspect', *names], text=True, capture_output=True, timeout=30)
        if result.returncode:
            return False
        import json
        rows = json.loads(result.stdout)
        return len(rows) == len(names) and all(r['State']['Running'] and
               r['State'].get('Health', {}).get('Status') not in ('starting', 'unhealthy') for r in rows)

    def begin(self, project, token):
        with lock_file(self.reconcile_lock):
            if self.maintenance.exists():
                raise RuntimeError('manual maintenance is active; deployment not started')
            inventory = load_json(self.inventory, None)
            names = [i['name'] for i in inventory['containers'] if i['project'] == project]
            if not names:
                raise RuntimeError('project is outside the explicit required inventory')
            holds = load_json(self.holds, {})
            old = holds.get(project)
            if old and old['phase'] == 'deploying' and owner_alive(old['owner']):
                raise RuntimeError('another deployment owns the project')
            holds[project] = {'token': token, 'phase': 'deploying', 'owner': process_identity(os.getpid()),
                              'since': time.time(), 'reason': 'deployment in progress'}
            atomic_json(self.holds, holds)
            print('guard: target repair paused; monitoring timer unchanged', flush=True)
            return names

    def finish(self, project, token, success, captured=None):
        with lock_file(self.reconcile_lock):
            holds = load_json(self.holds, {})
            if holds.get(project, {}).get('token') != token:
                raise RuntimeError('deployment hold ownership changed')
            if success:
                inventory = load_json(self.inventory, None)
                expected = {i['name'] for i in inventory['containers'] if i['project'] == project}
                if {i['name'] for i in captured['containers']} != expected:
                    raise RuntimeError('required container set changed during deployment')
                untouched = [i for i in inventory['containers'] if i['project'] != project]
                inventory['containers'] = untouched + captured['containers']
                # Publish fingerprints before enabling any automatic repair.
                atomic_json(self.inventory, inventory)
                state_path = self.root / 'var/lib/container-reconcile/state.json'
                state = load_json(state_path, {})
                for name in expected:
                    state.get('items', {}).pop(name, None)
                atomic_json(state_path, state)
                del holds[project]
                print('guard: target inventory refreshed; automatic repair resumed', flush=True)
            else:
                holds[project]['phase'] = 'failed'
                holds[project]['reason'] = 'deployment failed; monitor only until verified deployment'
                print('guard: deployment failed; monitoring active, target repair held', flush=True)
            atomic_json(self.holds, holds)

    def execute(self, project, command, timeout=2100):
        token = uuid.uuid4().hex
        with lock_file(self.deploy_lock) as deployment_lock:
            names = self.begin(project, token)
            child = None
            success = False
            code = 1
            captured = None
            def interrupted(signum, _frame):
                raise InterruptedError(signum)
            previous = {s: signal.signal(s, interrupted) for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)}
            try:
                environment = dict(os.environ, CONTAINER_DEPLOY_GUARD_TOKEN=token)
                # Descendants retain the deployment lock even if this supervisor is killed.
                child = subprocess.Popen(command, env=environment, start_new_session=True,
                                         pass_fds=(deployment_lock.fileno(),))
                code = child.wait(timeout=timeout)
                if code == 0:
                    deadline = time.monotonic() + self.ready_timeout
                    while not self.ready(names):
                        if time.monotonic() >= deadline:
                            raise RuntimeError('post-deployment readiness timeout')
                        time.sleep(2)
                    captured = self.capture(names)
                    # Validate capture ownership before publishing any new inventory.
                    if any(i['project'] != project for i in captured['containers']):
                        raise RuntimeError('capture project mismatch')
                    success = True
            except (RuntimeError, subprocess.SubprocessError, InterruptedError, OSError) as error:
                print('guard: ' + type(error).__name__ + '; deployment not adopted', flush=True)
                code = 128 + error.args[0] if isinstance(error, InterruptedError) else 1
            finally:
                # A failed/timed-out child must not keep mutating after the hold is finalized.
                for s in previous:
                    signal.signal(s, signal.SIG_IGN)
                if child is not None:
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL)
                        child.wait()
                try:
                    self.finish(project, token, success, captured)
                except Exception:
                    # Leave the durable hold in place if publication/cleanup failed.
                    success = False
                    code = 1
                    print('guard: finalization failed; target remains monitor-only', flush=True)
                for s, handler in previous.items():
                    signal.signal(s, handler)
            return code if code else (0 if success else 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--verify-nested', action='store_true')
    parser.add_argument('--root', type=Path, default=Path('/'))
    parser.add_argument('--capture', type=Path)
    parser.add_argument('--timeout', type=int, default=2100)
    parser.add_argument('--ready-timeout', type=int, default=300)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    guard = Guard(args.root, args.capture, args.ready_timeout)
    if args.verify_nested:
        guard.verify_nested(args.project)
        return 0
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('deployment command required after --')
    return guard.execute(args.project, command, args.timeout)


if __name__ == '__main__':
    raise SystemExit(main())
