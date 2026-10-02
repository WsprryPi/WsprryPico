#!/usr/bin/env python3
"""Hardware-free operator pause, accounting and historical resolution tests."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase12_gp14_rf as p


def write_json(path, value):
    path.write_text(json.dumps(value) + '\n')


def packet():
    return dict(schema='phase12-gp14-rf-v1', serial=p.SERIAL, device_id=p.DEVICE,
                source_revision=p.SOURCE_REVISION, revision=p.SOURCE_REVISION[:12],
                address='192.168.1.53', port=31417, engine='pio-dma-gp2',
                system_clock_hz=138000000, attenuation_db=60, receiver_serial='2404058C60',
                uf2='/unavailable/controller-only.uf2', uf2_sha256=p.IMAGE_SHA256,
                capture_helper='/unavailable/controller-only-capture')


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        write_json(self.root/'packet.json', packet())
        rows = []
        for index in range(15):
            root = self.root / f'run-{index:032x}'
            root.mkdir()
            write_json(root/'attempt.json', dict(case='active_stop', charged_jobs=int(index < 10)))
            write_json(root/'analysis.json', dict(independent_rf_pass=True,
                                                 attempt_sha256=p.digest(root/'attempt.json')))
            rows.append(dict(run=root.name, attempt_sha256=p.digest(root/'attempt.json'),
                             analysis_sha256=p.digest(root/'analysis.json')))
        write_json(self.root/'ledger-after-quick-reset-15.json',
                   dict(attempts=15, charged_jobs=10, rows=rows))
        self.anchor = patch.object(p, 'CHECKPOINT_SHA256',
                                   p.digest(self.root/'ledger-after-quick-reset-15.json'))
        self.anchor.start()
        self.addCleanup(self.anchor.stop)

    def ready(self):
        previous, charges = p.campaign_budget(self.root)
        return p.acknowledge_ready(self.root, 'quick_reset', (self.root/'packet.json').read_bytes(),
                                   previous, charges), previous, charges

    def consume(self, ready, previous, charges, **kwargs):
        return p.consume_ready(ready, self.root, 'quick_reset',
                               (self.root/'packet.json').read_bytes(), previous, charges, **kwargs)

    def test_prepare_never_accesses_hardware_or_creates_ready(self):
        before = set(self.root.iterdir())
        with patch.object(sys, 'argv', ['runner', str(self.root), '--case', 'quick_reset', '--prepare']), \
                patch.object(p, 'console') as usb, patch.object(p.socket, 'create_connection') as lan, \
                patch.object(p.subprocess, 'Popen') as receiver, contextlib.redirect_stdout(io.StringIO()) as out:
            p.main()
        result = json.loads(out.getvalue())
        self.assertEqual(result['status'], 'WAITING_FOR_OPERATOR_READY')
        self.assertEqual((result['attempts'], result['charged_jobs']), (15, 10))
        self.assertFalse(result['hardware_accessed'])
        self.assertFalse(result['image_files_verified'])
        usb.assert_not_called(); lan.assert_not_called(); receiver.assert_not_called()
        self.assertEqual(set(self.root.iterdir()), before)

    def test_missing_ready_refuses_before_io_or_charge(self):
        with patch.object(p, 'console') as usb, patch.object(p.socket, 'create_connection') as lan, \
                patch.object(p.subprocess, 'Popen') as receiver:
            with self.assertRaises(RuntimeError):
                p.acquire(packet(), 'quick_reset', self.root, led_cue=True)
        usb.assert_not_called(); lan.assert_not_called(); receiver.assert_not_called()
        self.assertEqual(len(list(self.root.glob('run-*/attempt.json'))), 15)

    def test_ready_is_one_use_and_not_previous_done(self):
        ready, previous, charges = self.ready()
        value = self.consume(ready, previous, charges)
        self.assertEqual(value['case'], 'quick_reset')
        with self.assertRaises(FileExistsError):
            self.consume(ready, previous, charges)
        bad = self.root/'done.json'; write_json(bad, dict(status='Done'))
        with self.assertRaises(RuntimeError):
            self.consume(bad, previous, charges)

    def test_ready_rejects_stale_future_case_packet_accounting_and_source(self):
        for key, value in [('case', 'long_ap'), ('serial', 'other'), ('device_id', 'f'*32),
                           ('packet_sha256', '0'*64), ('attempts', 14), ('charged_jobs', True),
                           ('attempt_limit', 18), ('runner_sha256', '0'*64)]:
            ready, previous, charges = self.ready()
            body = json.loads(ready.read_text()); body[key] = value; write_json(ready, body)
            with self.assertRaises(RuntimeError, msg=key): self.consume(ready, previous, charges)
            self.assertFalse(Path(str(ready)+'.consumed').exists())
        for age in [-1, 301]:
            ready, previous, charges = self.ready()
            stamp = json.loads(ready.read_text())['acknowledged_utc_s']
            with self.assertRaises(RuntimeError):
                self.consume(ready, previous, charges, now=stamp+age)

    def test_ready_rejects_cross_campaign_and_symlink(self):
        ready, previous, charges = self.ready()
        link = self.root/'ready-link.json'; link.symlink_to(ready)
        with self.assertRaises(RuntimeError): self.consume(link, previous, charges)
        with TemporaryDirectory() as other:
            moved = Path(other)/ready.name; moved.write_bytes(ready.read_bytes())
            with self.assertRaises(RuntimeError): self.consume(moved, previous, charges)

    def test_no_ready_wait_timer_exists_in_prepare(self):
        with patch.object(sys, 'argv', ['runner', str(self.root), '--case', 'long_ap', '--prepare']), \
                patch.object(p.time, 'time', side_effect=AssertionError('no acknowledgement clock yet')), \
                contextlib.redirect_stdout(io.StringIO()):
            p.main()

    def test_partial_mirror_modified_history_and_incomplete_attempt_refuse(self):
        first = sorted(self.root.glob('run-*/attempt.json'))[0]
        first.rename(first.with_name('missing.json'))
        with self.assertRaises((RuntimeError, FileNotFoundError)): p.campaign_budget(self.root)
        first.with_name('missing.json').rename(first)
        first.write_text('{}')
        with self.assertRaises(RuntimeError): p.campaign_budget(self.root)

    def test_cumulative_limits_charge_ambiguous_arm(self):
        for index in (15, 16):
            root = self.root/f'run-{index:032x}'; root.mkdir()
            write_json(root/'attempt.json', dict(case='quick_reset', charged_jobs=1, status='ARM_PENDING'))
            if index == 15:
                previous, charges = p.campaign_budget(self.root)
                self.assertEqual((len(previous), charges), (16, 11))
        with self.assertRaises(RuntimeError): p.campaign_budget(self.root)

    def test_failed_new_assessment_cannot_be_ignored(self):
        root = self.root/f'run-{15:032x}'; root.mkdir()
        write_json(root/'attempt.json', dict(case='quick_reset', charged_jobs=1))
        write_json(root/'analysis.json', dict(independent_rf_pass=False,
                                            attempt_sha256=p.digest(root/'attempt.json')))
        previous, _ = p.campaign_budget(self.root)
        with self.assertRaises(RuntimeError): p.review_campaign(self.root, previous)

    def test_concurrent_acquisition_is_refused_not_queued(self):
        ready, _, _ = self.ready()
        with p.campaign_lock(self.root), patch.object(p, 'console') as usb:
            with self.assertRaises(BlockingIOError):
                p.acquire(packet(), 'quick_reset', self.root, led_cue=True, ready_file=ready)
        usb.assert_not_called()
        self.assertFalse(Path(str(ready)+'.consumed').exists())

    def test_failed_start_consumes_ready_and_attempt_but_not_rf_job(self):
        ready, _, _ = self.ready()
        with patch.object(p, 'console', side_effect=RuntimeError('inactive preflight unavailable')), \
                patch.object(p.subprocess, 'Popen') as receiver:
            with self.assertRaises(RuntimeError):
                p.acquire(packet(), 'quick_reset', self.root, led_cue=True, ready_file=ready)
        receiver.assert_not_called()
        self.assertTrue(Path(str(ready)+'.consumed').exists())
        previous, charges = p.campaign_budget(self.root)
        self.assertEqual((len(previous), charges), (16, 10))
        with self.assertRaises(RuntimeError): p.review_campaign(self.root, previous)

    def test_stale_image_and_preparation_mixed_with_run_refuse(self):
        value = packet(); value['source_revision'] = '6'*40; value['revision'] = '6'*12
        with self.assertRaises(RuntimeError): p.validate_packet(value, verify_files=False)
        with patch.object(sys, 'argv', ['runner', str(self.root), '--case', 'quick_reset',
                                        '--prepare', '--led-cue']):
            with self.assertRaises(RuntimeError): p.main()
        ready, _, _ = self.ready()
        with self.assertRaises(RuntimeError):
            p.acquire(packet(), 'active_stop', self.root, led_cue=True, ready_file=ready)
        self.assertFalse(Path(str(ready)+'.consumed').exists())


class LongApTests(unittest.TestCase):
    def final(self):
        return dict(gp14_held=False, status=dict(output_active=False),
                    gp14_stop_verified=True, rf_safety_inhibited=True,
                    gp14_output_inhibited=True, rf_safety_input_fault=0,
                    gp14_last_duration_us='13000000', gp14_stop_events=1,
                    gp14_reset_events=0, gp14_ap_events=1, gp14_ap_request_attempts=1,
                    gp14_ap_request_accepts=1, gp14_softap_service_ready=True)

    def test_only_12_to_15_second_released_gesture_passes(self):
        for duration in (12000000, 13000000, 15000000):
            info = self.final(); info['gp14_last_duration_us'] = str(duration)
            p.check_long_ap_final(info)
        for duration in (9000000, 11999999, 15000001):
            info = self.final(); info['gp14_last_duration_us'] = str(duration)
            with self.assertRaises(RuntimeError): p.check_long_ap_final(info)

    def test_repeated_actions_carrier_return_held_input_and_missing_latch_refuse(self):
        for key, value in [('gp14_stop_events', 2), ('gp14_reset_events', 1),
                           ('gp14_ap_events', 2), ('gp14_ap_request_attempts', 2),
                           ('gp14_ap_request_accepts', True), ('gp14_held', True),
                           ('gp14_stop_verified', False), ('gp14_output_inhibited', False),
                           ('rf_safety_inhibited', False), ('rf_safety_input_fault', 1),
                           ('gp14_softap_service_ready', False),
                           ('status', dict(output_active=True))]:
            info = self.final(); info[key] = value
            with self.assertRaises(RuntimeError, msg=key): p.check_long_ap_final(info)

    def test_prior_actions_and_manual_lease_refuse_fresh_boot_admission(self):
        info = dict(gp14_stop_events=0, gp14_reset_events=0, gp14_ap_events=0,
                    gp14_ap_request_attempts=0, gp14_ap_request_accepts=0,
                    gp14_stop_verified=False, gp14_softap_manual_lease_active=False)
        p.check_long_ap_initial(info)
        for key in info:
            bad = dict(info); bad[key] = True if isinstance(info[key], bool) else 1
            with self.assertRaises(RuntimeError, msg=key): p.check_long_ap_initial(bad)

    def test_latch_probe_only_claims_and_never_loads_or_arms(self):
        from unittest.mock import Mock
        peer = Mock()
        peer.request.return_value = dict(boot_id='boot', output_active=False,
                                         owner_id=None, job_id=None, state='empty')
        p.check_latched_refusal(peer, 'boot')
        self.assertEqual([call.args[0] for call in peer.request.call_args_list], ['STATUS', 'CLAIM'])
        self.assertEqual(peer.request.call_args_list[-1].kwargs, dict(expected_error='BUSY'))
        for key, value in [('boot_id', 'other'), ('output_active', True),
                           ('owner_id', 'foreign'), ('job_id', 'old'), ('state', 'complete')]:
            peer.reset_mock()
            peer.request.return_value = dict(boot_id='boot', output_active=False,
                                             owner_id=None, job_id=None, state='empty')
            peer.request.return_value[key] = value
            with self.assertRaises(RuntimeError, msg=key): p.check_latched_refusal(peer, 'boot')
            self.assertEqual(peer.request.call_count, 1)


class HistoricalResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'run-986b41d58b2e46569d7aa24ae2dd84e4'; self.root.mkdir()
        self.path = self.root/'attempt.json'
        write_json(self.root/'packet.json', packet())
        self.attempt = dict(case='quick_reset', charged_jobs=1, status='FAILED_STOP_CAMPAIGN',
                            error='RuntimeError: physical action timeout', cleanup_verified=True,
                            boot_id='boot', job_id='1'*32, duration_ns='20000000000',
                            receiver_completion_after_target_failure=0,
                            packet_sha256=p.digest(self.root/'packet.json'))
        write_json(self.path, self.attempt)
        info = dict(device_id=p.DEVICE, revision=p.SOURCE_REVISION[:12], system_clock_hz=138000000,
                    gp14_rf_acceptance=True, gp14_samples='100', gp14_held=False,
                    gp14_capture_fault=False, gp14_stop_events=0, gp14_reset_events=0, gp14_ap_events=0,
                    rf_safety_inhibited=False, rf_safety_input_fault=0, rf_safety_requested_ns='0',
                    recovery_boot=False, core0_stack_guard_valid=1, core1_stack_guard_valid=1,
                    allocator_failures='0', saved_consumer_profile={}, access_state='healthy',
                    access_generation=1, access_default_password=False,
                    provisioning_source='consumer_preclock', provisioning_generation=5,
                    status=dict(boot_id='boot', output_active=True,
                                engine='pio-dma-gp2', enabled=False, storage_healthy=True))
        for key in ('fault_stage', 'fault_hash', 'fault_pc', 'fault_status', 'provisioning_fault',
                    'core0_stack_fault_status', 'core1_stack_fault_status', 'dma_errors'): info[key] = 0
        final = dict(boot_id='boot', state='empty', owner_id=None, job_id=None, output_active=False,
                     terminal_records=[dict(job_id='1'*32, state='complete', output_active=False)])
        self.events = [dict(kind='initial_info', value=copy.deepcopy(info)),
                       dict(kind='action_info', value=info),
                       dict(kind='received', value=dict(type='response',op='LOAD',ok=True,body=dict(job_id='1'*32))),
                       dict(kind='received', value=dict(type='response',op='ARM',ok=True,body=dict(job_id='1'*32))),
                       dict(kind='received', value=dict(
                           type='response', op='STATUS', ok=True, body=final))]
        with (self.root/'capture.cf32').open('wb') as out: out.truncate(80000000)
        self.meta = dict(actual_settings=p.SETTINGS, resolved_device=dict(driver='sdrplay',serial='2404058C60'),
                         overflow_count=0, timeout_count=0, clipping=dict(sample_count=0),
                         cleanup=dict(outcome='verified'), primary_outcome='success',
                         retained_sample_count=10000000, output=dict(complete=True,size_bytes=80000000,
                         sha256=p.digest(self.root/'capture.cf32')))
        self.save()

    def save(self):
        (self.root/'events.jsonl').write_text('\n'.join(json.dumps(v) for v in self.events)+'\n')
        write_json(self.root/'capture.json', self.meta)

    def test_resolution_preserves_nonqualification_and_hash_binding(self):
        result = p.review_quick_reset_no_input(self.path)
        self.assertIs(result['independent_rf_pass'], False)
        self.assertEqual(result['attempt_sha256'], p.digest(self.path))
        with self.assertRaises(RuntimeError): p.review_no_input_retry(self.path)

    def test_observed_input_fault_settings_or_foreign_job_refuse(self):
        original = copy.deepcopy(self.events)
        for key, value in [('gp14_ap_events', 1), ('gp14_reset_events', 1), ('gp14_held', True),
                           ('rf_safety_input_fault', 1), ('fault_stage', 1), ('provisioning_generation', 6)]:
            self.events = copy.deepcopy(original); self.events[1]['value'][key] = value; self.save()
            with self.assertRaises(RuntimeError, msg=key): p.review_quick_reset_no_input(self.path)
        self.events = copy.deepcopy(original); self.events[3]['value']['body']['job_id'] = 'f'*32; self.save()
        with self.assertRaises(RuntimeError): p.review_quick_reset_no_input(self.path)

    def test_absent_cleanup_and_bad_receiver_refuse(self):
        original = copy.deepcopy(self.events)
        self.events.pop(); self.save()
        with self.assertRaises(RuntimeError): p.review_quick_reset_no_input(self.path)
        self.events = original
        self.meta['timeout_count'] = 1; self.save()
        with self.assertRaises(RuntimeError): p.review_quick_reset_no_input(self.path)


if __name__ == '__main__':
    unittest.main()
