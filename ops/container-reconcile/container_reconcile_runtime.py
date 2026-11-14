"""Shared deployment leases and atomic local state for container reconciliation."""
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default


def process_identity(pid):
    try:
        text = Path('/proc/' + str(pid) + '/stat').read_text()
        # Fields after the final parenthesis start at process state, field 3.
        fields = text.rsplit(')', 1)[1].split()
        return {'pid': pid, 'ticks': fields[19],
                'boot': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'state': fields[0]}
    except FileNotFoundError:
        if Path('/proc').exists():
            return None
        try:
            os.kill(pid, 0)
            return {'pid': pid, 'ticks': None, 'boot': 'non-linux', 'state': 'R'}
        except ProcessLookupError:
            return None


def owner_alive(owner):
    current = process_identity(owner['pid'])
    return bool(current and current['state'] != 'Z' and
                all(current[k] == owner[k] for k in ('pid', 'ticks', 'boot')))


def lock_file(path, timeout=60):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open('a')
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return stream
        except BlockingIOError:
            if time.monotonic() >= deadline:
                stream.close()
                raise RuntimeError('deployment/reconciliation lock timeout')
            time.sleep(0.1)
