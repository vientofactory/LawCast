import copy
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
import sys

path = Path(__file__).resolve().parents[2] / 'ops/container-reconcile/reconcile.py'
sys.path.insert(0, str(path.parent))
loader = importlib.machinery.SourceFileLoader('reconciler', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


def item(name='app'):
    return {'name': name, 'project': 'test', 'service': name, 'dependencies': []}


def row(name='app', status='running', health='healthy'):
    return {'Name': '/' + name, 'Id': name + '-id', 'State': {'Running': status == 'running',
            'Status': status, 'Health': {'Status': health}},
            'Config': {'Labels': {'com.docker.compose.project': 'test',
                                  'com.docker.compose.service': name}}}


class FakeDocker:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.preflight_error = False
        self.recover_error = False
        self.scan_count = 0
        self.race = None

    def containers(self):
        self.scan_count += 1
        if self.race and self.scan_count == 2:
            self.rows = self.race
        return copy.deepcopy(self.rows)

    def prepare_missing(self, entry):
        if self.preflight_error:
            raise RuntimeError('required data prerequisite missing')

    def recover(self, entry, existing):
        self.calls.append(('start' if existing else 'create', entry['name']))
        if self.recover_error:
            raise RuntimeError('start failed')
        self.rows = [r for r in self.rows if r['Name'] != '/' + entry['name']]
        self.rows.append(row(entry['name']))


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.config = {'confirmations': 2, 'grace_seconds': 60, 'max_actions': 3,
                       'containers': [item()]}
        self.state = {}
        self.logs = []

    def run_at(self, docker, now=100, maintenance=False, check=False):
        return m.reconcile(self.config, self.state, docker, lambda: maintenance,
                           now, check, self.logs.append)

    def prime(self, docker):
        self.run_at(docker)
        return self.run_at(docker, 161)

    def test_running_container_is_untouched(self):
        d = FakeDocker([row()]); self.assertEqual(self.run_at(d), 0); self.assertEqual(d.calls, [])

    def test_missing_container_requires_two_observations_and_grace(self):
        d = FakeDocker([]); self.run_at(d); self.run_at(d, 120)
        self.assertEqual(d.calls, []); self.run_at(d, 161)
        self.assertEqual(d.calls, [('create', 'app')])

    def test_exited_container_starts_without_recreation(self):
        d = FakeDocker([row(status='exited')]); self.assertEqual(self.prime(d), 0)
        self.assertEqual(d.calls, [('start', 'app')])

    def test_created_container_is_started(self):
        d = FakeDocker([row(status='created')]); self.prime(d)
        self.assertEqual(d.calls, [('start', 'app')])

    def test_unhealthy_running_container_is_reported_not_restarted(self):
        d = FakeDocker([row(health='unhealthy')]); self.assertEqual(self.prime(d), 1)
        self.assertEqual(d.calls, [])

    def test_paused_dead_or_restarting_container_is_not_mutated(self):
        for status in ('paused', 'dead', 'restarting', 'removing'):
            d = FakeDocker([row(status=status)]); self.prime(d); self.assertEqual(d.calls, [])

    def test_maintenance_blocks_recovery_and_clears_confirmation(self):
        d = FakeDocker([]); self.run_at(d); self.run_at(d, 161, maintenance=True)
        self.assertEqual(d.calls, []); self.run_at(d, 162); self.assertEqual(d.calls, [])

    def test_check_mode_never_mutates_containers(self):
        d = FakeDocker([]); self.run_at(d, check=True); self.run_at(d, 200, check=True)
        self.assertEqual(d.calls, [])

    def test_identity_conflict_is_not_started(self):
        wrong = row(status='exited'); wrong['Config']['Labels']['com.docker.compose.project'] = 'other'
        d = FakeDocker([wrong]); self.prime(d); self.assertEqual(d.calls, [])

    def test_alternate_name_for_same_service_prevents_duplicate(self):
        other = row(); other['Name'] = '/other'
        d = FakeDocker([other]); self.prime(d); self.assertEqual(d.calls, [])

    def test_missing_data_or_changed_configuration_blocks_creation(self):
        d = FakeDocker([]); d.preflight_error = True; self.prime(d); self.assertEqual(d.calls, [])
        self.assertEqual(len(self.state['items']['app']['attempts']), 1)

    def test_dependency_health_gates_recovery(self):
        self.config['containers'][0]['dependencies'] = ['db']
        d = FakeDocker([row('db', health='starting')]); self.prime(d); self.assertEqual(d.calls, [])

    def test_failure_cooldown_and_three_attempt_hourly_cap(self):
        d = FakeDocker([row(status='exited')]); d.recover_error = True
        self.prime(d); self.run_at(d, 200); self.assertEqual(len(d.calls), 1)
        self.run_at(d, 462); self.run_at(d, 1063); self.run_at(d, 3000)
        self.assertEqual(len(d.calls), 3)

    def test_action_budget_bounds_work_per_pass(self):
        self.config['containers'] = [item('app' + str(i)) for i in range(5)]
        d = FakeDocker([]); self.prime(d); self.assertEqual(len(d.calls), 3)

    def test_newly_running_container_during_recheck_is_untouched(self):
        d = FakeDocker([]); self.run_at(d); d.scan_count = 0; d.race = [row()]
        self.run_at(d, 161); self.assertEqual(d.calls, [])

    def test_disappeared_existing_container_is_not_created_without_preflight(self):
        d = FakeDocker([row(status='exited')]); self.run_at(d); d.scan_count = 0; d.race = []
        # An empty race list is handled explicitly by this fixture callback.
        def scanning():
            d.scan_count += 1
            return [row(status='exited')] if d.scan_count == 1 else []
        d.containers = scanning
        self.run_at(d, 161); self.assertEqual(d.calls, [])

    def test_checkpoint_is_written_before_start(self):
        d = FakeDocker([row(status='exited')]); checkpoints = []
        self.state['_checkpoint'] = lambda: checkpoints.append(len(self.state['items']['app']['attempts']))
        self.prime(d); self.assertEqual(checkpoints, [1])

    def test_deployment_hold_blocks_only_affected_project(self):
        self.config['blocked_projects'] = {'test': {'phase': 'failed'}}
        other = item('other'); other['project'] = 'other'
        self.config['containers'].append(other)
        other_row = row('other', status='exited')
        other_row['Config']['Labels']['com.docker.compose.project'] = 'other'
        d = FakeDocker([row(status='exited'), other_row])
        self.prime(d)
        self.assertEqual(d.calls, [('start', 'other')])

    def test_unavailable_daemon_raises_without_recovery(self):
        d = FakeDocker([])
        def unavailable(): raise RuntimeError('daemon unavailable')
        d.containers = unavailable
        with self.assertRaises(RuntimeError): self.run_at(d)
        self.assertEqual(d.calls, [])

    def test_dependency_stopping_during_recheck_blocks_start(self):
        self.config['containers'][0]['dependencies'] = ['db']
        d = FakeDocker([row('db'), row(status='exited')]); self.run_at(d)
        d.scan_count = 0; d.race = [row('db', status='exited'), row(status='exited')]
        self.run_at(d, 161); self.assertEqual(d.calls, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
