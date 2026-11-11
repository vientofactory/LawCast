import argparse
import datetime
import json
import pathlib
import subprocess
import time
import urllib.parse
import urllib.request

p = argparse.ArgumentParser()
p.add_argument('--arm', required=True)
p.add_argument('--out', required=True)
a = p.parse_args()
out = pathlib.Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
container = 'lawcast-semantic-search'


def command(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def stamp():
    return datetime.datetime.now(datetime.UTC).isoformat()


def logs(since):
    return command('docker', 'logs', '--timestamps', '--since', since, container)


def health():
    with urllib.request.urlopen('http://127.0.0.1:8300/health', timeout=10) as r:
        return json.load(r)


def pid():
    for line in command('docker', 'top', container, '-eo', 'pid,comm,args').splitlines()[1:]:
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[1] == 'python' and 'uvicorn service.app:app' in parts[2]:
            return parts[0]
    raise RuntimeError('uvicorn PID not found')


def snapshot():
    d = pathlib.Path('/proc') / pid()
    f = (d / 'stat').read_text().split(') ', 1)[1].split()
    status = {
        line.split(':')[0]: line.split(':', 1)[1].strip()
        for line in (d / 'status').read_text().splitlines()
        if ':' in line
    }
    io = {
        line.split(':')[0]: int(line.split(':', 1)[1])
        for line in (d / 'io').read_text().splitlines()
    }
    return {
        'pid': d.name,
        'minflt': int(f[7]),
        'majflt': int(f[9]),
        'read_bytes': io['read_bytes'],
        'VmRSS': status['VmRSS'],
        'VmSwap': status['VmSwap'],
        'host_pressure': pathlib.Path('/proc/pressure/memory').read_text().strip(),
    }


def origin(q):
    url = 'http://127.0.0.1:3001/api/notices/semantic-search?' + urllib.parse.urlencode(
        {'query': q, 'k': 10}
    )
    t = time.perf_counter()
    with urllib.request.urlopen(url, timeout=65) as r:
        body = json.load(r)
        status = r.status
    data = body['data']
    return {
        'wall_ms': (time.perf_counter() - t) * 1000,
        'status': status,
        'mode': data.get('mode'),
        'ids': [x['noticeNum'] for x in data['results']],
        'weakIds': [x['noticeNum'] for x in data.get('weakResults', [])],
    }


def companion(q):
    code = """
import grpc, json, time, sys
from google.protobuf.json_format import MessageToDict
from service import semantic_search_pb2 as pb

channel = grpc.insecure_channel('127.0.0.1:8301')
call = channel.unary_unary(
    '/lawcast.semantic.v1.SemanticSearch/Search',
    request_serializer=pb.SearchRequest.SerializeToString,
    response_deserializer=pb.SearchResponse.FromString,
)
t = time.perf_counter()
reply = call(pb.SearchRequest(query=sys.argv[1], k=20), timeout=60)
print(
    json.dumps(
        {
            'wall_ms': (time.perf_counter() - t) * 1000,
            'timings': MessageToDict(reply.timings),
            'ids': [x.chunkId for x in reply.results],
            'weakIds': [x.chunkId for x in reply.weakResults],
        }
    )
)
channel.close()
"""
    return json.loads(command('docker', 'exec', container, 'python', '-c', code, q))


records = []


def record(row):
    row = {'arm': a.arm, 'at': stamp(), **row}
    records.append(row)
    out.write_text(json.dumps(records, ensure_ascii=False, indent=2))
    print(json.dumps(row, ensure_ascii=False), flush=True)


identity = command(
    'docker', 'inspect', '--format', '{{.Image}} {{.State.StartedAt}} {{.RestartCount}}', container
).strip()
record({'event': 'start', 'container': identity, 'health': health(), 'memory': snapshot()})
record({'event': 'seed', 'response': origin('학교 급식 시설 위생 관리와 학생 건강 지원')})
for seconds, q in [
    (180, '농촌 응급의료 인력 확충과 야간 진료 지원 체계'),
    (600, '전기차 충전 시설 배터리 화재 예방과 입주민 피해 보상'),
]:
    cursor = stamp()
    started = time.monotonic()
    quiet = started
    interruptions = []
    all_lines = []
    while time.monotonic() - quiet < seconds:
        remaining = seconds - (time.monotonic() - quiet)
        time.sleep(min(15, remaining))
        next_cursor = stamp()
        chunk = logs(cursor)
        cursor = next_cursor
        lines = chunk.splitlines()
        all_lines.extend(lines)
        searches = [s for s in lines if 'search-timing ' in s]
        if searches:
            interruptions.extend(searches)
            quiet = time.monotonic()
        if time.monotonic() - started > seconds * 3:
            raise RuntimeError(
                'public search traffic prevented a full quiet window; no traffic was blocked'
            )
    before = snapshot()
    h = health()
    request_start = stamp()
    first = origin(q)
    after = snapshot()
    request_logs = logs(request_start)
    repeat = origin(q)
    grpc_reply = companion(q)
    control_start = stamp()
    warm_control = origin(q + ' 관련 제도 개선')
    control_logs = logs(control_start)
    assert (
        command(
            'docker',
            'inspect',
            '--format',
            '{{.Image}} {{.State.StartedAt}} {{.RestartCount}}',
            container,
        ).strip()
        == identity
    ), 'container changed mid-experiment'
    record(
        {
            'event': 'idle_result',
            'idle_seconds': seconds,
            'actual_wait_seconds': time.monotonic() - started,
            'quiet_user_search_interruptions': interruptions,
            'quiet_search_count': 0,
            'update_events': [s for s in all_lines if 'update tick' in s or 'index update:' in s],
            'native_warmups': len([s for s in all_lines if 'idle warmup completed' in s]),
            'query': q,
            'first_origin': first,
            'repeat_origin': repeat,
            'fresh_warm_control': warm_control,
            'fresh_warm_control_logs': control_logs,
            'grpc_companion_after_origin': grpc_reply,
            'before': before,
            'after': after,
            'delta': {k: after[k] - before[k] for k in ('minflt', 'majflt', 'read_bytes')},
            'health_before': h,
            'first_request_logs': request_logs,
        }
    )
record({'event': 'finish', 'container': identity, 'health': health(), 'memory': snapshot()})
