"""Run Linux host fault tests against one isolated disposable Compose service."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

BASE = Path('/root/lawcast-ops/deploy-integration-20261114')
SOURCE = BASE / 'source/ops/container-reconcile'
LAB = BASE / 'isolated-test'
NAME = 'ops-deploy-guard-proof-20261114'
PROJECT = 'ops-deploy-guard-proof'
LAB.mkdir(exist_ok=False)
ROOT = LAB / 'root'
INVENTORY = ROOT / 'etc/container-reconcile/inventory.json'
HOLDS = ROOT / 'var/lib/container-reconcile/deployment-holds.json'
STATE = ROOT / 'var/lib/container-reconcile/state.json'
COMPOSE = LAB / 'compose.json'


def run(args, expected=0, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, timeout=90, **kwargs)
    print(result.stdout, end='', flush=True)
    if result.returncode != expected:
        raise RuntimeError(str(args) + ' exit=' + str(result.returncode) + ' ' + result.stderr)
    return result.stdout


def inspect():
    return json.loads(subprocess.check_output(['docker', 'inspect', NAME], text=True))[0]


def guard(command, **options):
    args = [sys.executable, str(SOURCE / 'deploy-guard.py'), '--root', str(ROOT),
            '--project', PROJECT, '--ready-timeout', '2']
    for key, value in options.items():
        args += ['--' + key, str(value)]
    return args + ['--', *command]


def holds():
    return json.loads(HOLDS.read_text()) if HOLDS.exists() else {}


def reconcile(expected=0):
    return run([sys.executable, str(SOURCE / 'reconcile.py'), '--inventory', str(INVENTORY),
                '--state', str(STATE), '--lock', str(ROOT / 'run/container-reconcile.lock'),
                '--maintenance', str(ROOT / 'run/container-reconcile.maintenance'),
                '--holds', str(HOLDS)], expected)


def wait_path(path):
    end = time.monotonic() + 10
    while not path.exists():
        if time.monotonic() > end:
            raise RuntimeError('test process did not become ready')
        time.sleep(.05)


created = False
try:
    run(['docker', 'inspect', NAME], 1)
    image = subprocess.check_output(['docker', 'inspect', 'lawcast-redis-1', '--format', '{{.Config.Image}}'], text=True).strip()
    data = {'services': {'backend': {'image': image, 'container_name': NAME,
            'entrypoint': ['/bin/sh', '-c'], 'command': ['exec sleep 3600'],
            'environment': {'APP_VERSION': '${APP_VERSION:-}'}, 'network_mode': 'none',
            'read_only': True, 'tmpfs': ['/data', '/tmp'], 'user': '65534:65534',
            'cap_drop': ['ALL'], 'pids_limit': 16, 'mem_limit': '32m', 'cpus': .1}}}
    COMPOSE.write_text(json.dumps(data))
    compose = ['docker', 'compose', '--project-directory', str(LAB), '-p', PROJECT, '-f', str(COMPOSE)]
    up = compose + ['up', '-d', '--no-build', '--pull', 'never', 'backend']
    run(up, env=dict(os.environ, APP_VERSION='1.0.0'))
    created = True
    INVENTORY.parent.mkdir(parents=True)
    run([sys.executable, str(SOURCE / 'capture-inventory.py'), '--names', NAME, '--output', str(INVENTORY)])
    inventory = json.loads(INVENTORY.read_text()); inventory['grace_seconds'] = 0
    INVENTORY.write_text(json.dumps(inventory))
    assert inventory['containers'][0]['compose_env'] == {'APP_VERSION': '1.0.0'}
    initial = inspect()['Id']
    run(guard(['/bin/true']))
    assert not holds() and inspect()['Id'] == initial
    print('PASS guarded success refreshed inventory without replacing live container')
    before = INVENTORY.read_bytes()
    run(guard(['/bin/sh', '-c', 'exit 23']), 23)
    assert INVENTORY.read_bytes() == before and holds()[PROJECT]['phase'] == 'failed'
    assert inspect()['Id'] == initial
    print('PASS exit 23 preserved exit code and inventory; no global maintenance/timer changes')
    run(guard(['/bin/sh', '-c', 'docker rm -f "$1" >/dev/null; exit 23', 'sh', NAME]), 23)
    for _ in range(2):
        output = reconcile(1)
        assert 'deployment hold prevents repair' in output
    run(['docker', 'inspect', NAME], 1)
    print('PASS failed deployment with a missing target did not trigger unintended recreation')
    command = ['env', 'APP_VERSION=1.1.0', *up]
    run(guard(command))
    assert not holds()
    adopted = json.loads(INVENTORY.read_text())
    assert adopted['containers'][0]['compose_env'] == {'APP_VERSION': '1.1.0'}
    print('PASS successful retry adopted actual deployed APP_VERSION and cleared target hold')
    run(['docker', 'rm', '-f', NAME])
    reconcile(1); reconcile()
    env = inspect()['Config']['Env']
    assert 'APP_VERSION=1.1.0' in env
    print('PASS subsequent missing-container recovery preserved deployed interpolation')
    run(guard(['/bin/sleep', '30'], timeout=1), 1)
    assert holds()[PROJECT]['phase'] == 'failed'
    run(guard(['/bin/true']))
    print('PASS timeout finalized failure hold; verified retry resumed repair')
    for kill_signal in (signal.SIGTERM, signal.SIGKILL):
        pidfile = LAB / ('child-' + str(kill_signal))
        child_command = ['/bin/sh', '-c', 'docker rm -f "$1" >/dev/null; echo $$ > "$2"; exec sleep 100', 'sh', NAME, str(pidfile)]
        process = subprocess.Popen(guard(child_command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        wait_path(pidfile)
        child_pid = int(pidfile.read_text().strip())
        os.kill(process.pid, kill_signal)
        process.wait(timeout=15)
        assert process.returncode == (143 if kill_signal == signal.SIGTERM else -9)
        if kill_signal == signal.SIGKILL:
            # The orphan retains the deployment lock, so no new deployment can race it.
            sys.path.insert(0, str(SOURCE))
            from container_reconcile_runtime import lock_file
            try:
                with lock_file(ROOT / 'run/container-deploy.lock', timeout=.1):
                    raise AssertionError('orphan deployment lost its serialization lock')
            except RuntimeError:
                pass
            os.killpg(child_pid, signal.SIGKILL)
        output, errors = process.communicate(timeout=15)
        print(output, end='')
        for _ in range(2):
            output = reconcile(1)
            assert 'deployment hold prevents repair' in output
        run(['docker', 'inspect', NAME], 1)
        assert holds()[PROJECT]['phase'] in ('failed', 'aborted')
        assert not (ROOT / 'run/container-reconcile.maintenance').exists()
        run(guard(command))
        assert not holds()
        print('PASS signal ' + str(kill_signal) + ': monitor active, no orphan recreation, verified recovery')
    output = run(guard(['bash', '-s']), input='printf "HEREDOC_PRESERVED\\n"\n')
    assert 'HEREDOC_PRESERVED' in output
    print('PASS SSH-style heredoc stdin survives supervisor')
    print('PASS isolated deployment integration fault suite')
finally:
    if created:
        subprocess.run(['docker', 'rm', '-f', NAME], capture_output=True)
        print('CLEANUP disposable proof container removed')
