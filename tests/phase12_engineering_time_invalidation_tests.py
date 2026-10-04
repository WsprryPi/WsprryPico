#!/usr/bin/env python3
import ast
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase12_engineering_time_invalidation as runner
import phase12_engineering_orchestrator as parent
import phase12_engineering_time_dispatch as dispatch
from inhibited_network_acceptance import FREQUENCY

EPOCH = 1_791_074_000_000_000_000


class Evidence:
    def __init__(self):
        self.rows = []

    def record(self, kind, **value):
        self.rows.append((kind, copy.deepcopy(value)))


class Peer:
    """Independent scripted transport with clock-driven job and time replies."""
    authorized = True
    expected_device_id = runner.DEVICE
    field_session = 'authenticated-field'
    wtp_session = 'wtp'
    generation = 7

    def __init__(self, evidence, now, fault=None):
        self.evidence, self.now, self.fault = evidence, now, fault
        self.backend = object()
        self.timeout = 5
        self.last_response = None
        self.calls, self.submissions, self.challenges = [], [], []
        self.owner = self.job = None
        self.state, self.source = 'empty', 'none'
        self.disagreement = False
        self.recovery = 0
        self.start = self.duration = 0
        self.records = []
        self.loaded_jobs = 0
        self.query_timeouts = []

    def advance(self, operation):
        self.query_timeouts.append(self.timeout)
        self.now[0] += .05
        if self.fault == 'late_' + operation:
            self.now[0] += 180

    def poll(self):
        if self.fault == 'never_terminal':
            return
        if self.state == 'armed' and self.now[0] >= self.start:
            if self.disagreement and self.fault not in ('armed_runs_invalid', 'uncertain_ABORT'):
                self.state = 'missed'
                self.records.insert(0, dict(job_id=self.job, state='missed', output_active=False,
                    ended_monotonic_ns=str(int(self.start * 1e9)), error={'code': 'MISSED_START'}))
            else:
                self.state = 'running'
        if self.state == 'running' and self.now[0] >= self.start + self.duration:
            self.state = 'complete'
            self.records.insert(0, dict(job_id=self.job, state='complete', output_active=False,
                ended_monotonic_ns=str(int((self.start + self.duration) * 1e9) + 50_000)))

    def field_status(self):
        self.advance('field_status')
        return dict(time_source=self.source, time_disagreement=self.disagreement)

    def wtp_status(self, boot):
        self.advance('STATUS')
        self.calls.append(('STATUS', {}))
        self.poll()
        return dict(boot_id='bad' if self.fault == 'status_boot' else boot,
                    state=self.state, owner_id=self.owner, job_id=self.job,
                    output_active=self.fault == 'active_output', terminal_records=copy.deepcopy(self.records))

    def clock_value(self):
        return dict(state='synchronized' if self.source == 'controller' else 'unsynchronized',
            leap='normal', monotonic_now_ns=str(int(self.now[0] * 1e9)),
            utc_now_ns=str(EPOCH + int(self.now[0] * 1e9)), sync_age_ns='100000000',
            uncertainty_ns='1000000')

    def wtp_exchange(self, operation, body):
        self.advance(operation)
        self.calls.append((operation, copy.deepcopy(body)))
        self.poll()
        if operation == 'CAPS':
            return dict(engine='inhibited-standalone-simulator', modes=['tone'], profiles=['rf-events/1'],
                max_events=512, max_job_duration_ns='3600000000000', minimum_arm_lead_ns='100000000',
                maximum_arm_ahead_ns='604800000000000', maximum_arm_uncertainty_ns='500000000',
                minimum_lease_ms=5000, maximum_lease_ms=60000,
                frequency_ranges=[dict(minimum_nhz=str(FREQUENCY), maximum_nhz=str(FREQUENCY))])
        if operation == 'GET_CLOCK':
            return self.clock_value()
        if operation == 'CLAIM':
            self.owner = body['owner_id']
            result = dict(owner_id=self.owner)
        elif operation == 'LOAD':
            self.loaded_jobs += 1
            self.job, self.state = body['job_id'], 'loaded'
            self.duration = int(body['total_duration_ns']) / 1e9
            result = dict(job_id=self.job, state='loaded')
        elif operation == 'ARM':
            self.start = (int(body['start_utc_ns']) - EPOCH) / 1e9
            self.state = 'armed'
            result = dict(job_id=self.job, state='armed', start_utc_ns=body['start_utc_ns'],
                          start_monotonic_ns=str(int(self.start * 1e9)), clock=self.clock_value())
        elif operation == 'ABORT':
            if self.fault == 'uncertain_ABORT':
                raise TimeoutError('uncertain ABORT')
            self.state = 'aborted'
            result = {}
        elif operation == 'RELEASE':
            self.state, self.owner, self.job = 'empty', None, None
            result = {}
        else:
            raise AssertionError(operation)
        if self.fault == 'uncertain_' + operation:
            raise TimeoutError('uncertain ' + operation)
        return result

    def _field(self, operation, **body):
        self.advance(operation)
        if operation == 'time_challenge':
            self.challenges.append(body['nonce'])
            return dict(nonce='different' if self.fault == 'nonce' else body['nonce'])
        self.submissions.append(copy.deepcopy(body))
        if self.fault == 'late_submission':
            self.now[0] += 180
        offset = int(body['utc_ns']) - (EPOCH + int(self.now[0] * 1e9))
        if offset > 30_000_000_000 or (self.fault == 'force_conflict' and self.loaded_jobs):
            self.disagreement, self.source = True, 'disagreement'
            self.recovery = 0
            if self.loaded_jobs == 2 and self.fault == 'running_reschedule':
                self.start += 60
            if self.loaded_jobs == 2 and self.fault == 'running_early_complete':
                self.duration = 0
                self.poll()
            if self.loaded_jobs == 2 and self.fault == 'running_unlatch':
                self.disagreement, self.source = False, 'controller'
            self.last_response = dict(ok=False, error='conflict')
            raise runner.ClientError('conflict')
        if self.disagreement:
            self.recovery += 1
            if self.recovery == 1:
                self.last_response = dict(ok=False, error='conflict')
                raise runner.ClientError('conflict')
        self.disagreement, self.source = False, 'controller'
        return dict(accepted=True)


class Tests(unittest.TestCase):
    def exercise(self, fault=None, info_fault=None, success=False, cleanup_fault=False, evidence_fault=None):
        now = [0.0]
        evidence = Evidence()
        record = evidence.record
        def recorded(kind, **value):
            if kind == evidence_fault:
                raise OSError('private evidence disk error')
            record(kind, **value)
        evidence.record = recorded
        peer = Peer(evidence, now, fault)
        original = peer.backend
        info = dict(device_id=runner.DEVICE, revision='b' * 12, provisioning_generation='7',
            access_generation='4', saved_consumer_profile={'pins': {'rf': 3, 'button': 22}},
            provisioning_source='provisioned', access_state='healthy', status=dict(boot_id='a' * 32,
            engine='inhibited-standalone-simulator', enabled=False, configured=True, output_active=False,
            storage_healthy=True, station={'callsign': 'W1AW'}, schedules=[], watermark_utc_ns='99',
            expires_utc_s='2000000000', schedule_base_frequency_nhz='3570100000000000'))
        info['config'] = {'expires_utc_s': '2000000000', 'enabled': False}
        info['status']['config'] = {'expires_utc_s': '2000000000', 'enabled': False}
        observations = []
        def observe():
            if info_fault == 'late':
                now[0] += 180
            else:
                now[0] += .01
            value = copy.deepcopy(info)
            if info_fault == 'boot':
                value['status']['boot_id'] = 'c' * 32
            if info_fault == 'raw':
                return value, b'{}'
            if info_fault == 'saved_pin' and peer.disagreement:
                value['saved_consumer_profile']['pins']['rf'] = 4
            if info_fault == 'watermark' and peer.disagreement:
                value['status']['watermark_utc_ns'] = '100'
            if info_fault == 'config' and peer.disagreement:
                value['config']['expires_utc_s'] = '2000000001'
            if info_fault == 'status_config' and peer.disagreement:
                value['status']['config']['expires_utc_s'] = '2000000001'
            observations.append(value)
            return value, json.dumps(value).encode()
        off_calls = []
        def off():
            off_calls.append(True)
            if cleanup_fault and len(off_calls) == 2:
                raise RuntimeError('owned responder cleanup failure')
        def execute():
            with patch.object(runner, 'resource_health'):
                return runner.run(peer, observe, 'b' * 40, 'a' * 32, evidence,
                    lambda: self.fail('continuation must never enable SNTP'), off,
                    clock=lambda: now[0], sleeper=lambda seconds: now.__setitem__(0, now[0] + seconds),
                    utc=lambda: EPOCH + int(now[0] * 1e9))
        if success:
            result = execute()
            self.assertEqual((result['simulator_jobs'], result['completed_cases'], result['rf_jobs']), (2, 2, 0))
            self.assertFalse(result['physical_acceptance'])
            self.assertLess(now[0], 180)
            self.assertTrue(all(count <= 32 for count in result['status_counts'].values()))
            self.assertIsNone(peer.owner)
            self.assertEqual(len(observations), 7)
            self.assertEqual(len(off_calls), 2)
        else:
            with self.assertRaises((ValueError, TimeoutError, RuntimeError)) as stopped:
                execute()
            peer.error = stopped.exception
            if fault == 'nonce':
                self.assertIs(type(stopped.exception), ValueError)
                self.assertIn('field challenge nonce', str(stopped.exception))
        self.assertIs(peer.backend, original)
        self.assertEqual(peer.timeout, 5)
        self.assertIn(len(off_calls), (1, 2))
        self.assertTrue(all(0 < timeout <= 5 for timeout in peer.query_timeouts))
        return peer, evidence

    def test_two_jobs_exact_policy_stimuli_and_no_old_expiry_repeat(self):
        peer, evidence = self.exercise(success=True)
        counts = {operation: sum(op == operation for op, _ in peer.calls)
                  for operation in ('CLAIM', 'LOAD', 'ARM', 'ABORT', 'RELEASE')}
        self.assertEqual(counts, dict(CLAIM=2, LOAD=2, ARM=2, ABORT=0, RELEASE=2))
        self.assertEqual(len(peer.submissions), 5)
        self.assertEqual(len(set(peer.challenges)), 5)
        self.assertEqual([value['expected'] for kind, value in evidence.rows if kind == 'field_submission'],
                         ['accepted', 'conflict', 'conflict', 'accepted', 'conflict'])
        self.assertEqual([value['case'] for kind, value in evidence.rows if kind == 'time_invalidation_case_complete'],
                         ['armed_clock_invalidation_missed', 'running_clock_invalidation_monotonic_completion'])
        charges = [value for kind, value in evidence.rows if kind == 'simulator_job_charge']
        self.assertEqual(len(charges), 2)

    def test_armed_launch_with_invalid_clock_is_rejected(self):
        peer, _ = self.exercise('armed_runs_invalid')
        self.assertEqual(sum(op == 'LOAD' for op, _ in peer.calls), 1)
        self.assertEqual(sum(op == 'ABORT' for op, _ in peer.calls), 1)

    def test_running_schedule_shift_and_early_completion_are_rejected(self):
        for fault in ('running_reschedule', 'running_early_complete', 'running_unlatch'):
            with self.subTest(fault=fault):
                peer, evidence = self.exercise(fault)
                self.assertEqual(sum(op == 'LOAD' for op, _ in peer.calls), 2)
                self.assertEqual(sum(kind == 'time_invalidation_case_complete' for kind, _ in evidence.rows), 1)

    def test_info_byte_boot_and_saved_projection_fail_closed(self):
        for fault in ('raw', 'boot', 'saved_pin', 'watermark', 'config', 'status_config'):
            with self.subTest(fault=fault):
                peer, _ = self.exercise(info_fault=fault)
                self.assertLessEqual(sum(op == 'LOAD' for op, _ in peer.calls), 1)

    def test_deadline_rejects_late_original_info_and_submission_without_replay(self):
        peer, _ = self.exercise(info_fault='late')
        self.assertEqual(peer.calls, [])
        peer, _ = self.exercise('late_submission')
        self.assertEqual(len(peer.submissions), 1)
        self.assertEqual(sum(op == 'LOAD' for op, _ in peer.calls), 0)

    def test_late_mutation_response_cannot_resume_or_replay(self):
        peer, evidence = self.exercise('late_ARM')
        self.assertEqual(sum(op == 'ARM' for op, _ in peer.calls), 1)
        self.assertEqual(sum(op == 'LOAD' for op, _ in peer.calls), 1)
        self.assertFalse(any(kind == 'time_invalidation_case_complete' for kind, _ in evidence.rows))

    def test_bad_challenge_binding_never_submits(self):
        peer, _ = self.exercise('nonce')
        self.assertEqual(peer.submissions, [])

    def test_uncertain_mutating_requests_are_never_replayed(self):
        for operation in ('CLAIM', 'LOAD', 'ARM', 'RELEASE'):
            with self.subTest(operation=operation):
                peer, _ = self.exercise('uncertain_' + operation)
                self.assertEqual(sum(op == operation for op, _ in peer.calls), 1)
                self.assertLessEqual(sum(op == 'ABORT' for op, _ in peer.calls), 1)

    def test_status_poll_budget_reserves_bounded_once_cleanup(self):
        peer, evidence = self.exercise('never_terminal')
        case_rows = [value for kind, value in evidence.rows if kind == 'authority' and value['case'] != 'setup']
        self.assertLessEqual(len(case_rows), 32)
        self.assertEqual(sum(op == 'ABORT' for op, _ in peer.calls), 1)
        self.assertTrue(any(kind == 'cleanup_confirmed' for kind, _ in evidence.rows))

    def test_uncertain_abort_is_charged_once_and_cleanup_is_not_invented(self):
        peer, evidence = self.exercise('uncertain_ABORT')
        self.assertEqual(sum(op == 'ABORT' for op, _ in peer.calls), 1)
        self.assertEqual(sum(op == 'RELEASE' for op, _ in peer.calls), 0)
        self.assertTrue(any(kind == 'cleanup_failed' for kind, _ in evidence.rows))

    def test_nonoverlap_must_be_proven_by_original_clock_bracket(self):
        with patch.object(runner, 'CONFLICT_OFFSET_NS', 500_000_000):
            peer, evidence = self.exercise('force_conflict')
        self.assertEqual(sum(op == 'LOAD' for op, _ in peer.calls), 1)
        bound = next(value for kind, value in evidence.rows if kind == 'nonoverlap_bound')
        self.assertLessEqual(int(bound['difference_ns']), int(bound['uncertainty_and_bracket_ns']))

    def test_output_and_authority_boot_fault_stop_before_load(self):
        for fault in ('active_output', 'status_boot'):
            with self.subTest(fault=fault):
                peer, _ = self.exercise(fault)
                self.assertEqual(sum(op == 'LOAD' for op, _ in peer.calls), 0)

    def test_owned_fixture_cleanup_failure_is_not_success_or_error_mask(self):
        _, evidence = self.exercise(cleanup_fault=True)
        self.assertTrue(any(kind == 'fixture_cleanup_failed' for kind, _ in evidence.rows))
        _, evidence = self.exercise('nonce', cleanup_fault=True)
        self.assertTrue(any(kind == 'fixture_cleanup_failed' for kind, _ in evidence.rows))

    def test_error_log_failures_preserve_body_or_original_cleanup_exception(self):
        peer, _ = self.exercise('uncertain_ABORT', evidence_fault='cleanup_failed')
        self.assertIs(type(peer.error), ValueError)
        self.assertEqual(str(peer.error), 'unexpected local time-policy transition')
        peer, _ = self.exercise('nonce', cleanup_fault=True, evidence_fault='fixture_cleanup_failed')
        self.assertIs(type(peer.error), ValueError)
        self.assertEqual(str(peer.error), 'field challenge nonce')
        peer, _ = self.exercise(cleanup_fault=True, evidence_fault='fixture_cleanup_failed')
        self.assertIs(type(peer.error), RuntimeError)
        self.assertEqual(str(peer.error), 'owned responder cleanup failure')


class SelectionTests(unittest.TestCase):
    def test_body_timer_interrupts_then_restores_before_external_cleanup(self):
        handlers, calls = [], []
        original = object()
        def installed(kind, handler):
            handlers.append(handler)
        with patch.object(dispatch.signal, 'getitimer', return_value=(0.0, 0.0)), \
             patch.object(dispatch.signal, 'getsignal', return_value=original), \
             patch.object(dispatch.signal, 'signal', side_effect=installed), \
             patch.object(dispatch.signal, 'setitimer', side_effect=lambda *args: calls.append(args)):
            with self.assertRaisesRegex(TimeoutError, 'whole time continuation body deadline'):
                with dispatch.body_deadline(180):
                    handlers[0]()
            self.assertEqual(handlers[-1], original)
            self.assertEqual([value[1] for value in calls], [180, 0])
        with patch.object(dispatch.signal, 'getitimer', return_value=(1.0, 0.0)), \
             patch.object(dispatch.signal, 'setitimer') as timer:
            with self.assertRaisesRegex(ValueError, 'existing process timer'):
                with dispatch.body_deadline(180):
                    self.fail('timer replacement admitted')
            timer.assert_not_called()

    def test_new_dependency_is_explicit_and_missing_before_backend(self):
        self.assertIn('time-jobs-invalidation', parent.SCOPES)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            credentials, manifest = root / 'credentials', root / 'manifest.json'
            own = root / 'scripts' / 'phase12_engineering_orchestrator.py'
            with patch.object(parent, '__file__', str(own)):
                for path in parent.staging_inputs('time-jobs-invalidation', manifest, credentials):
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b'private test input')
                target = root / 'scripts' / 'phase12_engineering_time_invalidation.py'
                self.assertNotIn(target, parent.staging_inputs('time-jobs', manifest, credentials))
                self.assertNotIn(target, parent.staging_inputs('all', manifest, credentials))
                parent.preflight_staging('time-jobs-invalidation', manifest, credentials)
                target.unlink()
                with self.assertRaisesRegex(ValueError, 'scope staging input'):
                    parent.preflight_staging('time-jobs-invalidation', manifest, credentials)
                argv = ['program', '--run', '--scope', 'time-jobs-invalidation', '--native', str(root / 'native')]
                for name, path in (('manifest', manifest), ('artifact-root', root),
                    ('preparation-manifest', manifest), ('preparation-artifact-root', root),
                    ('campaign', root / 'new-campaign'), ('inspector', root / 'inspector'),
                    ('credential-root', credentials)):
                    argv.extend(('--' + name, str(path)))
                with patch.object(sys, 'argv', argv), patch.object(parent, 'read_json', return_value={}), \
                     patch.object(parent, 'verify'), \
                     patch.object(parent, 'RemoteAdapters', side_effect=AssertionError('host access')), \
                     patch.object(parent, 'credential_config', side_effect=AssertionError('private input use')):
                    with self.assertRaisesRegex(ValueError, 'scope staging input'):
                        parent.main()
                self.assertFalse((root / 'new-campaign').exists())

    def test_actual_new_dispatch_imports_from_only_declared_staged_closure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = [path for path in parent.staging_inputs('time-jobs-invalidation', root / 'manifest', root)
                     if path.parent == Path(parent.__file__).parent]
            for source in names:
                shutil.copyfile(source, root / source.name)
            code = ('import sys;sys.path.insert(0,sys.argv[1]);'
                    'import phase12_engineering_time_dispatch as dispatch;'
                    '\ntry: dispatch.run(dict(time_selection="invalidation",authority="refused"))'
                    '\nexcept ValueError as e: assert str(e)=="authority"'
                    '\nelse: raise AssertionError("authority admitted")')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(root)],
                                    cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            (root / 'phase12_engineering_time_invalidation.py').unlink()
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(root)],
                                    cwd=root, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('phase12_engineering_time_invalidation', result.stderr)

    def test_actual_parent_branch_selects_one_new_dispatch_without_old_cases(self):
        tree = ast.parse(Path(parent.__file__).read_text())
        callback = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == 'accelerated')
        calls = []
        class Remote:
            def fixture(self, action, value):
                calls.append(('fixture', action))
            def stage(self, path, name):
                calls.append(('stage', name))
                return 'a' * 64
            def invoke(self, name, payload, **kwargs):
                calls.append(('invoke', name, payload, kwargs))
            def collect(self, names):
                calls.append(('collect', names))
        info = dict(status={'boot_id': 'a' * 32}, provisioning_generation='7')
        class Backend:
            remote = '/private/no-access'
            def snapshot(self, name):
                calls.append(('snapshot', name))
                return dict(inspection={'profile_source': 1, 'profile_healthy': True})
            def deploy(self, role, saved, name):
                calls.append(('deploy', role, name))
                return dict(info=info)
        env = dict(a=SimpleNamespace(scope='time-jobs-invalidation', preparation_manifest=Path('unused')),
            remote=Remote(), Path=Path, __file__=parent.__file__, require=runner.require,
            private_write=lambda *args: None, accelerated_helpers=parent.accelerated_helpers,
            preparation={'source_commit': 'b' * 40, 'candidates': [{'role': 'engineering', 'uf2': {'sha256': 'c' * 64}}]},
            AUTHORITY='authorized', sha=lambda *args: 'd' * 64, counter=lambda x, *args: int(x), server_sha256='e' * 64)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[callback], type_ignores=[])), 'actual-parent', 'exec'), env)
        env['accelerated'](dict(backend=Backend(), root=Path('unused'), profile_path='profile', ble_address='bound'))
        invocations = [value for value in calls if value[0] == 'invoke']
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0][2]['time_selection'], 'invalidation')
        self.assertEqual(invocations[0][3], dict(timeout=220, keepalive=True))
        self.assertIn(('stage', 'phase12_engineering_time_invalidation.py'), calls)
        self.assertIn(('snapshot', 'before-time-invalidation.bin'), calls)
        self.assertIn(('collect', ('time-invalidation-wire.jsonl', 'time-invalidation-result.json')), calls)
        calls.clear()
        env['a'].scope = 'time-jobs-sntp'
        env['accelerated'](dict(backend=Backend(), root=Path('unused'), profile_path='profile', ble_address='bound'))
        invocations = [value for value in calls if value[0] == 'invoke']
        self.assertEqual(len(invocations), 1)
        self.assertEqual(invocations[0][2]['time_selection'], 'sntp')
        self.assertEqual(invocations[0][3], dict(timeout=160, keepalive=True))
        self.assertNotIn(('stage', 'phase12_engineering_time_invalidation.py'), calls)
        self.assertIn(('snapshot', 'before-time-sntp.bin'), calls)
        self.assertIn(('collect', ('time-sntp-wire.jsonl', 'time-sntp-result.json')), calls)

    def test_dispatch_unknown_selection_refused_before_observer(self):
        with patch.object(dispatch, 'Observer', side_effect=AssertionError('target access')):
            with self.assertRaisesRegex(ValueError, 'explicit time selection'):
                dispatch.run({'time_selection': 'all'})


if __name__ == '__main__':
    unittest.main()
