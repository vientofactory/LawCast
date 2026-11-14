#!/usr/bin/env python3
"""Capture explicit Compose ownership and data prerequisites without logging secrets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def run(args, cwd=None, env=None):
    result = subprocess.run(['docker', *args], cwd=cwd, text=True, capture_output=True, timeout=45,
                            env=dict(os.environ, **(env or {})))
    if result.returncode:
        raise RuntimeError('Docker inventory command failed: ' + args[0])
    return result.stdout


def capture(names=None):
    rows = json.loads(run(['inspect', *run(['ps', '-aq']).split()]))
    if names:
        rows = [r for r in rows if r['Name'].lstrip('/') in names]
        assert len(rows) == len(names), 'Requested container missing'
    compose_envs = {}
    for row in rows:
        labels = row["Config"].get("Labels") or {}
        if labels.get("com.docker.compose.service") == "backend":
            values = dict(value.split("=", 1) for value in row["Config"].get("Env", []) if "=" in value)
            if "APP_VERSION" in values:
                compose_envs[labels.get("com.docker.compose.project")] = {"APP_VERSION": values["APP_VERSION"]}
    configs = {}
    items = []
    for row in rows:
        assert row['State']['Running'], 'Capture requires all selected containers running'
        labels = row['Config']['Labels'] or {}
        project = labels['com.docker.compose.project']
        service = labels['com.docker.compose.service']
        workdir = labels['com.docker.compose.project.working_dir']
        files = labels['com.docker.compose.project.config_files'].split(',')
        assert all(Path(f).is_file() for f in files)
        key = (project, workdir, tuple(files))
        if key not in configs:
            args = ['compose', '--project-directory', workdir, '-p', project]
            for f in files:
                args += ['-f', f]
            configs[key] = json.loads(run(args + ['config', '--format', 'json'], workdir,
                                           compose_envs.get(project, {})))
        config = configs[key]
        assert service in config['services']
        assert not any(m['Type'] == 'volume' and not m.get('Name') for m in row['Mounts'])
        items.append({'name': row['Name'].lstrip('/'), 'project': project, 'service': service,
                      'workdir': workdir, 'files': files, 'compose_env': compose_envs.get(project, {}),
                      'image_ref': row['Config']['Image'], 'image_id': row['Image'],
                      'config_sha256': hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                      'volumes': [m['Name'] for m in row['Mounts'] if m['Type'] == 'volume'],
                      'binds': [m['Source'] for m in row['Mounts'] if m['Type'] == 'bind'],
                      'networks': list(row['NetworkSettings']['Networks']),
                      'dependency_services': list(config['services'][service].get('depends_on', {}))})
    lookup = {(i['project'], i['service']): i['name'] for i in items}
    for item in items:
        item['dependencies'] = [lookup[(item['project'], d)] for d in item.pop('dependency_services')
                                if (item['project'], d) in lookup]
    ordered = []
    while items:
        ready = [i for i in items if all(d in {j['name'] for j in ordered} for d in i['dependencies'])]
        assert ready, 'Dependency cycle'
        for item in ready:
            ordered.append(item)
            items.remove(item)
    return {'confirmations': 2, 'grace_seconds': 60, 'max_actions': 3, 'containers': ordered}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--names', nargs='+')
    args = parser.parse_args()
    data = capture(args.names)
    path = Path(args.output)
    path.write_text(json.dumps(data, indent=2) + '\n')
    path.chmod(0o600)
    print('Captured required containers: ' + str(len(data['containers'])))
