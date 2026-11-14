import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'ops/container-reconcile'
sys.path.insert(0, str(SOURCE))
spec = importlib.util.spec_from_file_location('deploy_guard', SOURCE / 'deploy-guard.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def entry(name='app', project='test'):
    return {'name': name, 'project': project, 'image_id': 'before'}


class FixtureGuard(g.Guard):
    def ready(self, names):
        return True

    def capture(self, names):
        return {'containers': [dict(entry(), image_id='after')]}


class DeploymentGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.guard = FixtureGuard(self.root, ready_timeout=0)
        g.atomic_json(self.guard.inventory, {'containers': [entry(), entry('other', 'other')]})
        self.before = self.guard.inventory.read_bytes()

    def holds(self):
        return g.load_json(self.guard.holds, {})

    def test_success_refreshes_only_target_and_clears_hold(self):
        self.assertEqual(self.guard.execute('test', ['/bin/sh', '-c', 'exit 0']), 0)
        data = g.load_json(self.guard.inventory, {})
        self.assertEqual(data['containers'], [entry('other', 'other'), dict(entry(), image_id='after')])
        self.assertEqual(self.holds(), {})
        self.assertFalse(self.guard.maintenance.exists())

    def test_failure_preserves_inventory_and_resumes_monitoring_without_repair(self):
        self.assertEqual(self.guard.execute('test', ['/bin/sh', '-c', 'exit 23']), 23)
        self.assertEqual(self.guard.inventory.read_bytes(), self.before)
        self.assertEqual(self.holds()['test']['phase'], 'failed')
        self.assertFalse(self.guard.maintenance.exists())

    def test_readiness_failure_does_not_adopt_candidate(self):
        self.guard.ready = lambda names: False
        self.assertEqual(self.guard.execute('test', [sys.executable, '-c', 'pass']), 1)
        self.assertEqual(self.guard.inventory.read_bytes(), self.before)
        self.assertEqual(self.holds()['test']['phase'], 'failed')

    def test_capture_failure_does_not_adopt_candidate(self):
        def fail(names): raise RuntimeError('capture failed')
        self.guard.capture = fail
        self.assertEqual(self.guard.execute('test', [sys.executable, '-c', 'pass']), 1)
        self.assertEqual(self.guard.inventory.read_bytes(), self.before)
        self.assertEqual(self.holds()['test']['phase'], 'failed')

    def test_timeout_terminates_child_and_retains_failure_hold(self):
        self.assertEqual(self.guard.execute('test', ['/bin/sleep', '10'], timeout=0.05), 1)
        self.assertEqual(self.holds()['test']['phase'], 'failed')
        self.assertEqual(self.guard.inventory.read_bytes(), self.before)

    def test_manual_maintenance_is_preserved_and_command_never_runs(self):
        self.guard.maintenance.parent.mkdir(parents=True, exist_ok=True)
        self.guard.maintenance.write_text('operator')
        marker = self.root / 'should-not-exist'
        with self.assertRaises(RuntimeError):
            self.guard.execute('test', ['/bin/sh', '-c', 'touch "$1"', 'sh', str(marker)])
        self.assertFalse(marker.exists())
        self.assertEqual(self.guard.maintenance.read_text(), 'operator')
        self.assertEqual(self.holds(), {})

    def test_project_outside_inventory_is_rejected(self):
        with self.assertRaises(RuntimeError): self.guard.execute('unknown', [sys.executable, '-c', 'pass'])
        self.assertEqual(self.holds(), {})

    def test_nested_deployment_requires_live_matching_token(self):
        self.guard.begin('test', 'valid')
        with patch.dict(os.environ, {'CONTAINER_DEPLOY_GUARD_TOKEN': 'valid'}):
            self.guard.verify_nested('test')
        with patch.dict(os.environ, {'CONTAINER_DEPLOY_GUARD_TOKEN': 'wrong'}):
            with self.assertRaises(RuntimeError): self.guard.verify_nested('test')

    def test_verified_retry_clears_previous_failure_hold(self):
        self.guard.execute('test', [sys.executable, '-c', 'raise SystemExit(1)'])
        self.assertEqual(self.guard.execute('test', [sys.executable, '-c', 'pass']), 0)
        self.assertEqual(self.holds(), {})

    def test_timer_is_never_stopped_disabled_or_restarted(self):
        commands = []
        original = g.subprocess.Popen
        def start(args, **kwargs):
            commands.append(args)
            return original(args, **kwargs)
        with patch.object(g.subprocess, 'Popen', side_effect=start):
            self.guard.execute('test', [sys.executable, '-c', 'pass'])
        self.assertEqual(commands, [[sys.executable, '-c', 'pass']])

    def test_foreign_hold_is_not_cleared(self):
        self.guard.begin('test', 'owner')
        with self.assertRaises(RuntimeError): self.guard.finish('test', 'foreign', False)
        self.assertEqual(self.holds()['test']['token'], 'owner')

    def test_changed_required_set_cannot_be_adopted(self):
        self.guard.begin('test', 'owner')
        with self.assertRaises(RuntimeError):
            self.guard.finish('test', 'owner', True, {'containers': [entry('unexpected')]})
        self.assertEqual(self.guard.inventory.read_bytes(), self.before)

    def test_owner_pid_identity_is_not_just_pid_existence(self):
        owner = g.process_identity(os.getpid())
        self.assertTrue(g.owner_alive(owner))
        owner['boot'] = 'different-boot'
        self.assertFalse(g.owner_alive(owner))

    def test_running_recovery_counters_reset_only_after_success(self):
        state = self.root / 'var/lib/container-reconcile/state.json'
        g.atomic_json(state, {'items': {'app': {'attempts': [1]}, 'other': {'attempts': [2]}}})
        self.guard.execute('test', [sys.executable, '-c', 'raise SystemExit(1)'])
        self.assertIn('app', g.load_json(state, {})['items'])
        self.guard.execute('test', [sys.executable, '-c', 'pass'])
        self.assertEqual(g.load_json(state, {})['items'], {'other': {'attempts': [2]}})


class WorkflowIntegrationTests(unittest.TestCase):
    def test_both_workflows_wrap_entire_remote_script(self):
        root = SOURCE.parents[1]
        for name in ('deploy-backend.yml', 'deploy-semantic-search.yml'):
            body = (root / '.github/workflows' / name).read_text()
            self.assertIn('ssh deploy-target /usr/local/sbin/container-deploy-guard.py --project lawcast -- bash -s', body)
            self.assertIn('.github/scripts/deploy-change-guard.sh record', body)
        self.assertIn('--verify-nested', (root / 'deploy.sh').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
