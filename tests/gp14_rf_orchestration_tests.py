#!/usr/bin/env python3
"""Hardware-free operator pause, accounting and historical resolution tests."""
import contextlib
import copy
import io
import json
import hashlib
import struct
import subprocess
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase12_gp14_rf as p


def write_json(path, value):
    path.write_text(json.dumps(value) + '\n')


def historical_packet():
    return dict(schema='phase12-gp14-rf-v1', serial=p.SERIAL, device_id=p.DEVICE,
                source_revision=p.HISTORICAL_SOURCE, revision=p.HISTORICAL_SOURCE[:12],
                address='192.168.1.53', port=31417, engine='pio-dma-gp2',
                system_clock_hz=138000000, attenuation_db=60, receiver_serial='2404058C60',
                uf2='/unavailable/controller-only.uf2', uf2_sha256=p.HISTORICAL_IMAGE,
                capture_helper='/unavailable/controller-only-capture')


def uf2(payload=66):
    raw = bytearray(512)
    struct.pack_into('<8I', raw, 0, 0x0A324655, 0x9E5D5157, 0x2000,
                     0x10000000, 256, 0, 1, 0xE48BFF59)
    raw[32:288] = bytes([payload])*256
    struct.pack_into('<I', raw, 508, 0x0AB16F30)
    return bytes(raw)


def current_info(value):
    info = dict(device_id=p.DEVICE, revision=value['revision'], firmware='0.0.0-devel',
                system_clock_hz=138000000, gp14_rf_acceptance=True, gp14_samples='100',
                gp14_held=False, gp14_capture_fault=False, recovery_boot=False,
                gp14_output_inhibited=False, rf_safety_inhibited=False, gp14_rf_busy_used=0,
                gp14_rf_cue_supported=True, core0_stack_guard_valid=1, core1_stack_guard_valid=1,
                allocator_failures='0', saved_consumer_profile={}, access_state='healthy',
                access_generation=1, access_default_password=False, provisioning_source='consumer_preclock',
                provisioning_generation=5, lan_wtp_ready=True,
                network=dict(link_status=3, ipv4='192.168.1.77'),
                status=dict(boot_id='b'*32, engine='pio-dma-gp2', state='empty', clock_state='synchronized',
                            enabled=False, storage_healthy=True, output_active=False, reboot_required=False),
                gp14_stop_verified=False, gp14_softap_manual_lease_active=False)
    for key in ('fault_stage', 'fault_hash', 'fault_pc', 'fault_status', 'provisioning_fault',
                'core0_stack_fault_status', 'core1_stack_fault_status', 'dma_errors',
                'gp14_stop_events', 'gp14_reset_events', 'gp14_ap_events', 'gp14_ap_request_attempts',
                'gp14_ap_request_accepts'): info[key] = 0
    return info


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, content in [('rf.uf2', uf2()), ('restore.uf2', uf2(67)),
                              ('capture-tool', b'capture-test'), ('inspector', b'inspector-test')]:
            (self.root/name).write_bytes(content)
        self.patch('HELPER_SHA256', p.digest(self.root/'capture-tool'))
        source = 'ec0f68facb5041e9e1426d20e3c8326567272bb9'
        candidates = [dict(role=role, firmware='0.0.0-devel', revision=source[:12],
                           target=target, gp14=gp14, fault_stage=0, session_deadline_fixture=False,
                           lan_mode='plain', uf2=dict(path=name, bytes=512, sha256=p.digest(self.root/name)))
                      for role, target, gp14, name in [('rf_ap', 'WsprryPico-StandaloneRF', True, 'rf.uf2'),
                                                       ('restore', 'WsprryPico', False, 'restore.uf2')]]
        self.manifest = dict(schema='phase12-candidates/1', authority='NONE_PREPARATION_ONLY',
                             source_commit=source, sdk_commit='079c6f39023649b154152db30f1d781e884879bc',
                             toolchain='GNU Arm 15.3.1', candidates=candidates)
        write_json(self.root/'manifest.json', self.manifest)
        self.packet = p.create_packet(self.root/'manifest.json', self.root, self.root,
                                     self.root/'capture-tool', self.root/'inspector', p.digest(self.root/'inspector'))
        write_json(self.root/'packet.json', self.packet)
        rows = []
        for index in range(15):
            root = self.root / f'run-{index:032x}'; root.mkdir()
            write_json(root/'attempt.json', dict(case='active_stop', charged_jobs=int(index < 10)))
            write_json(root/'analysis.json', dict(independent_rf_pass=True,
                                                 attempt_sha256=p.digest(root/'attempt.json')))
            rows.append(dict(run=root.name, attempt_sha256=p.digest(root/'attempt.json'),
                             analysis_sha256=p.digest(root/'analysis.json')))
        write_json(self.root/'ledger-after-quick-reset-15.json', dict(attempts=15, charged_jobs=10, rows=rows))
        self.patch('CHECKPOINT_SHA256', p.digest(self.root/'ledger-after-quick-reset-15.json'))
        accepted = self.root/p.ACCEPTED_RESET_RUN; accepted.mkdir()
        write_json(accepted/'attempt.json', dict(case='quick_reset', charged_jobs=1))
        write_json(accepted/'analysis.json', dict(independent_rf_pass=True,
                                                attempt_sha256=p.digest(accepted/'attempt.json')))
        self.patch('ACCEPTED_RESET_ATTEMPT', p.digest(accepted/'attempt.json'))
        self.patch('ACCEPTED_RESET_ANALYSIS', p.digest(accepted/'analysis.json'))
        self.info = current_info(self.packet)
        write_json(self.root/'post-flash-info.json', self.info)
        self.prior = dict(device_id=p.DEVICE, status=dict(boot_id='a'*32, output_active=False, enabled=False))
        write_json(self.root/'prior-info.json', self.prior)
        self.flash = bytes([66])*256+bytes([255])*(4194304-256)
        (self.root/'post-flash-readback.bin').write_bytes(self.flash)
        self.native = dict(operational_healthy=True, profile_healthy=True,
                           config=dict(enabled=False, pins=copy.deepcopy(p.PINS)))

    def patch(self, name, value):
        change = patch.object(p, name, value); change.start(); self.addCleanup(change.stop)

    def ready(self):
        previous, charges = p.campaign_budget(self.root)
        return p.acknowledge_ready(self.root, 'long_ap', (self.root/'packet.json').read_bytes(),
                                   previous, charges, setup_approved=True), previous, charges

    def consume(self, ready, previous, charges, **kwargs):
        return p.consume_ready(ready, self.root, 'long_ap',
                               (self.root/'packet.json').read_bytes(), previous, charges, **kwargs)

    def bind(self, ready):
        with patch.object(p.subprocess, 'run', return_value=subprocess.CompletedProcess(
                ['mock-inspector'], 0, stdout=json.dumps(self.native).encode(), stderr=b'')) as native:
            path = p.bind_preflight(self.packet, (self.root/'packet.json').read_bytes(), ready, self.root,
                                    self.root/'post-flash-info.json', self.root/'post-flash-readback.bin',
                                    self.root/'prior-info.json')
        native.assert_called_once()
        self.assertEqual(native.call_args.args[0][1],
                         str(path.with_suffix('')/'readback.bin'))
        return path

    def execute(self, ready, receipt):
        return p.acquire(self.packet, 'long_ap', self.root, led_cue=True, ready_file=ready,
                         preflight_file=receipt)

    def test_prepare_default_never_accesses_hardware_or_creates_ready(self):
        before = set(self.root.iterdir())
        with patch.object(sys, 'argv', ['runner', str(self.root), '--case', 'long_ap']), \
                patch.object(p, 'console') as usb, patch.object(p.socket, 'create_connection') as lan, \
                patch.object(p.subprocess, 'Popen') as receiver, contextlib.redirect_stdout(io.StringIO()) as out:
            p.main()
        result = json.loads(out.getvalue())
        self.assertEqual(result['status'], 'WAITING_FOR_CURRENT_SETUP_APPROVAL_AND_OPERATOR_READY')
        self.assertEqual((result['attempts'], result['charged_jobs']), (16, 11))
        self.assertFalse(result['hardware_accessed']); self.assertFalse(result['image_files_verified'])
        usb.assert_not_called(); lan.assert_not_called(); receiver.assert_not_called()
        self.assertEqual(set(self.root.iterdir()), before)

    def test_missing_ready_refuses_before_io_or_charge(self):
        with patch.object(p, 'console') as usb, patch.object(p.subprocess, 'Popen') as receiver:
            with self.assertRaises(RuntimeError): p.acquire(self.packet, 'long_ap', self.root, led_cue=True)
        usb.assert_not_called(); receiver.assert_not_called()
        self.assertEqual(len(list(self.root.glob('run-*/attempt.json'))), 16)

    def test_ready_requires_actual_current_setup_approval(self):
        previous, charges = p.campaign_budget(self.root)
        with self.assertRaises(RuntimeError):
            p.acknowledge_ready(self.root, 'long_ap', (self.root/'packet.json').read_bytes(), previous, charges)
        self.assertEqual(list(self.root.glob('ready-*.json')), [])

    def test_ready_is_one_use_and_not_previous_done(self):
        ready, previous, charges = self.ready()
        self.assertEqual(self.consume(ready, previous, charges)['case'], 'long_ap')
        with self.assertRaises(RuntimeError): self.consume(ready, previous, charges)
        bad = self.root/'done.json'; write_json(bad, dict(status='Done'))
        with self.assertRaises(RuntimeError): self.consume(bad, previous, charges)

    def test_ready_rejects_stale_future_case_packet_accounting_and_source(self):
        for key, value in [('case', 'quick_reset'), ('serial', 'other'), ('device_id', 'f'*32),
                           ('packet_sha256', '0'*64), ('attempts', 15), ('charged_jobs', True),
                           ('attempt_limit', 18), ('runner_sha256', '0'*64),
                           ('setup_approved', False), ('physical_bench_ready', False)]:
            ready, previous, charges = self.ready()
            body = json.loads(ready.read_text()); body[key] = value; write_json(ready, body)
            with self.assertRaises(RuntimeError, msg=key): self.consume(ready, previous, charges)
            self.assertFalse(Path(str(ready)+'.consumed').exists())
        for age in [-1, 301]:
            ready, previous, charges = self.ready()
            stamp = json.loads(ready.read_text())['acknowledged_utc_s']
            with self.assertRaises(RuntimeError): self.consume(ready, previous, charges, now=stamp+age)

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
                contextlib.redirect_stdout(io.StringIO()): p.main()

    def test_partial_mirror_modified_history_and_incomplete_attempt_refuse(self):
        first = sorted(self.root.glob('run-*/attempt.json'))[0]
        first.rename(first.with_name('missing.json'))
        with self.assertRaises((RuntimeError, FileNotFoundError)): p.campaign_budget(self.root)
        first.with_name('missing.json').rename(first); first.write_text('{}')
        with self.assertRaises(RuntimeError): p.campaign_budget(self.root)

    def test_missing_sixteenth_accepted_reset_refuses_current_packet(self):
        accepted = self.root/p.ACCEPTED_RESET_RUN
        for path in accepted.iterdir(): path.unlink()
        accepted.rmdir()
        previous, charges = p.campaign_budget(self.root)
        self.assertEqual((len(previous), charges), (15, 10))
        with self.assertRaises(RuntimeError): p.remaining_campaign(self.root, previous, charges)
        with patch.object(p, 'console') as usb:
            with self.assertRaises(RuntimeError): p.acquire(self.packet, 'long_ap', self.root, led_cue=True,
                                                           ready_file=self.root/'unavailable')
        usb.assert_not_called()

    def test_cumulative_limits_charge_ambiguous_arm(self):
        previous, charges = p.campaign_budget(self.root)
        self.assertEqual((len(previous), charges), (16, 11))
        root = self.root/f'run-{16:032x}'; root.mkdir()
        write_json(root/'attempt.json', dict(case='long_ap', charged_jobs=1, status='ARM_PENDING'))
        with self.assertRaises(RuntimeError): p.campaign_budget(self.root)

    def test_failed_new_assessment_cannot_be_ignored(self):
        root = self.root/p.ACCEPTED_RESET_RUN
        write_json(root/'analysis.json', dict(independent_rf_pass=False, attempt_sha256=p.digest(root/'attempt.json')))
        previous, _ = p.campaign_budget(self.root)
        with self.assertRaises(RuntimeError): p.review_campaign(self.root, previous)

    def test_concurrent_acquisition_is_refused_not_queued(self):
        ready, _, _ = self.ready()
        with p.campaign_lock(self.root), patch.object(p, 'console') as usb:
            with self.assertRaises(BlockingIOError): self.execute(ready, None)
        usb.assert_not_called(); self.assertFalse(Path(str(ready)+'.consumed').exists())

    def test_failed_start_consumes_ready_and_attempt_but_not_rf_job(self):
        ready, _, _ = self.ready(); receipt = self.bind(ready)
        with patch.object(p, 'console', side_effect=RuntimeError('inactive preflight unavailable')), \
                patch.object(p.subprocess, 'Popen') as receiver:
            with self.assertRaises(RuntimeError): self.execute(ready, receipt)
        receiver.assert_not_called(); self.assertTrue(Path(str(ready)+'.consumed').exists())
        attempts = [json.loads(path.read_text()) for path in self.root.glob('run-*/attempt.json')]
        self.assertEqual((len(attempts), sum(a['charged_jobs'] for a in attempts)), (17, 11))
        self.assertEqual(attempts.count(next(a for a in attempts if a.get('status') == 'FAILED_STOP_CAMPAIGN')), 1)
        with self.assertRaises(RuntimeError): p.campaign_budget(self.root)

    def test_stale_image_wrong_case_and_preparation_mixed_with_run_refuse(self):
        bad = copy.deepcopy(self.packet); bad['source_revision'] = '6'*40; bad['revision'] = '6'*12
        with self.assertRaises(RuntimeError): p.validate_packet(bad, verify_files=False)
        with patch.object(sys, 'argv', ['runner', str(self.root), '--case', 'long_ap', '--prepare', '--led-cue']):
            with self.assertRaises(RuntimeError): p.main()
        ready, _, _ = self.ready()
        for case in ('quick_reset', 'active_stop', 'armed_busy'):
            with self.assertRaises(RuntimeError): p.acquire(self.packet, case, self.root, led_cue=True, ready_file=ready)
        self.assertFalse(Path(str(ready)+'.consumed').exists())

    def test_historical_packet_cannot_be_acknowledged_or_run(self):
        previous, charges = p.campaign_budget(self.root)
        with self.assertRaises(RuntimeError):
            p.acknowledge_ready(self.root, 'long_ap', json.dumps(historical_packet()).encode(),
                                previous, charges, setup_approved=True)
        with self.assertRaises(RuntimeError): p.validate_packet(historical_packet(), verify_files=False)

    def test_packet_plans_current_files_without_future_boot_or_address(self):
        p.validate_packet(self.packet)
        self.assertNotIn('boot_id', self.packet); self.assertNotIn('address', self.packet)
        self.assertEqual(self.packet['pins']['button_gp'], 14); self.assertEqual(self.packet['pins']['rf_gp'], 2)
        for key, value in [('uf2_sha256', '0'*64), ('restore_uf2_sha256', '0'*64),
                           ('manifest_sha256', '0'*64), ('start_attempts', 15), ('case', 'quick_reset'),
                           ('capture_samples', 20000000), ('ap_proof_seconds', 91)]:
            bad = copy.deepcopy(self.packet); bad[key] = value
            with self.assertRaises(RuntimeError, msg=key): p.validate_packet(bad, verify_files=False)

    def test_one_ready_binds_offline_native_originals_without_io(self):
        ready, previous, charges = self.ready(); original_packet = (self.root/'packet.json').read_bytes()
        with patch.object(p, 'console') as usb, patch.object(p.subprocess, 'Popen') as receiver:
            receipt = self.bind(ready)
            binding = p.check_preflight(receipt, original_packet, json.loads(ready.read_text()), self.root)
        self.assertEqual(binding['boot_id'], 'b'*32); self.assertEqual(binding['address'], '192.168.1.77')
        self.assertEqual(binding['prior_boot_id'], 'a'*32)
        self.assertEqual(original_packet, (self.root/'packet.json').read_bytes())
        self.assertEqual(len(list(self.root.glob('ready-*.json'))), 1)
        self.assertFalse(Path(str(ready)+'.consumed').exists()); usb.assert_not_called(); receiver.assert_not_called()

    def test_wrong_pin_enabled_or_unhealthy_native_plan_cannot_bind(self):
        original = copy.deepcopy(self.native)
        for changes in [('button_gp', 13), ('rf_gp', 3), ('amplifier_gp', 15), ('indicator_gp', 0)]:
            self.native = copy.deepcopy(original); self.native['config']['pins'][changes[0]] = changes[1]
            ready, _, _ = self.ready()
            with self.assertRaises(RuntimeError, msg=str(changes)): self.bind(ready)
        for bad in [dict(operational_healthy=False, profile_healthy=True, config=None),
                    dict(operational_healthy=True, profile_healthy=False, config=None),
                    dict(operational_healthy=True, profile_healthy=True, config=dict(enabled=True, pins=p.PINS))]:
            self.native = bad; ready, _, _ = self.ready()
            with self.assertRaises(RuntimeError): self.bind(ready)
        self.assertEqual(list(self.root.glob('preflight-*.json')), [])

    def test_default_legacy_native_pin_plan_is_effective_default(self):
        self.native['config'] = None; ready, _, _ = self.ready()
        self.bind(ready)

    def test_pending_wrong_identity_same_old_boot_or_bad_address_cannot_bind(self):
        for field, value in [('reboot_required', True), ('boot_id', 'a'*32), ('output_active', True)]:
            bad = copy.deepcopy(self.info); bad['status'][field] = value
            write_json(self.root/'post-flash-info.json', bad); ready, _, _ = self.ready()
            with self.assertRaises(RuntimeError, msg=field): self.bind(ready)
        for address in ('0.0.0.0', '127.0.0.1', '224.0.0.1'):
            bad = copy.deepcopy(self.info); bad['network']['ipv4'] = address
            write_json(self.root/'post-flash-info.json', bad); ready, _, _ = self.ready()
            with self.assertRaises(RuntimeError, msg=address): self.bind(ready)
        bad = copy.deepcopy(self.info); bad['device_id'] = 'f'*32
        write_json(self.root/'post-flash-info.json', bad); ready, _, _ = self.ready()
        with self.assertRaises(RuntimeError): self.bind(ready)

    def test_native_image_mismatch_and_changed_inspector_refuse(self):
        ready, _, _ = self.ready()
        (self.root/'post-flash-readback.bin').write_bytes(bytes(4194304))
        with self.assertRaises(ValueError): self.bind(ready)
        (self.root/'post-flash-readback.bin').write_bytes(self.flash)
        (self.root/'inspector').write_bytes(b'changed')
        with self.assertRaises(RuntimeError): self.bind(ready)

    def test_preflight_orphan_changed_inline_or_original_refuses_before_consumption(self):
        ready, _, _ = self.ready(); receipt = self.bind(ready)
        originals = receipt.with_suffix('')
        raw_receipt = receipt.read_bytes()
        with patch.object(p, 'console') as usb, patch.object(p.subprocess, 'Popen') as receiver:
            for name in ('info.json', 'readback.bin', 'native.json', 'prior-info.json'):
                path = originals/name; data = path.read_bytes(); path.write_bytes(data+b' ')
                with self.assertRaises(RuntimeError, msg=name): self.execute(ready, receipt)
                path.write_bytes(data)
            body = json.loads(raw_receipt); body['info']['network']['ipv4'] = '192.168.1.78'
            body['address'] = '192.168.1.78'; write_json(receipt, body)
            with self.assertRaises(RuntimeError): self.execute(ready, receipt)
            receipt.write_bytes(raw_receipt)
            moved = self.root/'other.json'; moved.write_bytes(raw_receipt)
            with self.assertRaises(RuntimeError): self.execute(ready, moved)
        usb.assert_not_called(); receiver.assert_not_called()
        self.assertFalse(Path(str(ready)+'.consumed').exists())

    def test_preflight_elapsed_uses_same_ready_no_new_timer(self):
        ready, _, _ = self.ready()
        stamp = json.loads(ready.read_text())['acknowledged_utc_s']
        with patch.object(p.time, 'time', return_value=stamp+301), patch.object(p.subprocess, 'run') as native:
            with self.assertRaises(RuntimeError): self.bind(ready)
        native.assert_not_called(); self.assertFalse(Path(str(ready)+'.consumed').exists())

    def test_native_inspection_time_cannot_extend_actual_ready_deadline(self):
        ready, _, _ = self.ready()
        stamp = json.loads(ready.read_text())['acknowledged_utc_s']
        with patch.object(p.time, 'time', side_effect=[stamp+299, stamp+301, stamp+301]):
            with self.assertRaises(RuntimeError): self.bind(ready)
        self.assertEqual(list(self.root.glob('preflight-*.json')), [])
        self.assertFalse(Path(str(ready)+'.consumed').exists())

    def test_runtime_deadline_expired_after_usb_preflight_stops_before_receiver(self):
        ready, _, _ = self.ready(); receipt = self.bind(ready)
        with patch.object(p.time, 'monotonic', side_effect=[100, 401]), \
                patch.object(p, 'console', return_value=self.info), \
                patch.object(p.subprocess, 'Popen') as receiver, patch.object(p, 'Peer') as peer:
            with self.assertRaisesRegex(RuntimeError, 'deadline expired before receiver'):
                self.execute(ready, receipt)
        receiver.assert_not_called(); peer.assert_not_called()
        self.assertTrue(Path(str(ready)+'.consumed').exists())

    def test_new_committed_source_is_parameterized_and_manifest_bound(self):
        manifest = copy.deepcopy(self.manifest); manifest['source_commit'] = 'd'*40
        for candidate in manifest['candidates']: candidate['revision'] = 'd'*12
        write_json(self.root/'manifest.json', manifest)
        value = p.create_packet(self.root/'manifest.json', self.root, self.root,
                                self.root/'capture-tool', self.root/'inspector', p.digest(self.root/'inspector'))
        self.assertEqual(value['source_revision'], 'd'*40)
        info = current_info(value); p.check_info(info, value)
        with self.assertRaises(RuntimeError): p.check_info(self.info, value)

    def test_runtime_new_boot_or_address_stops_before_receiver_claim(self):
        for change in ('boot', 'address', 'settings'):
            ready, _, _ = self.ready(); receipt = self.bind(ready)
            info = copy.deepcopy(self.info)
            if change == 'boot': info['status']['boot_id'] = 'c'*32
            elif change == 'address': info['network']['ipv4'] = '192.168.1.78'
            else: info['provisioning_generation'] += 1
            with patch.object(p, 'console', return_value=info), patch.object(p.subprocess, 'Popen') as receiver, \
                    patch.object(p.socket, 'create_connection') as lan:
                with self.assertRaises(RuntimeError, msg=change): self.execute(ready, receipt)
            receiver.assert_not_called(); lan.assert_not_called()
            # Each failed start exhausts the one remaining slot; remove ONLY our
            # synthetic test run to inspect the next independent negative.
            for root in self.root.glob('run-*'):
                attempt = json.loads((root/'attempt.json').read_text())
                if attempt.get('status') == 'FAILED_STOP_CAMPAIGN':
                    for file in root.iterdir(): file.unlink()
                    root.rmdir()

    def test_bounded_long_ap_uses_fresh_ip_one_job_and_leaves_independent_proofs_pending(self):
        ready, _, _ = self.ready(); receipt = self.bind(ready)
        peer = Mock()
        def request(op, body, expected_error=None):
            if op == 'HELLO': return dict(device_id=p.DEVICE, boot_id='b'*32)
            if op == 'CAPS': return dict(engine='pio-dma-gp2')
            if op == 'STATUS': return dict(boot_id='b'*32, state='empty', owner_id=None,
                                          job_id=None, output_active=False)
            if op == 'LOAD': return dict(job_id=body['job_id'], adjustments=[dict(
                requested_frequency_nhz='3570100000000000', realized_frequency_nhz='3570100000000000')])
            if op == 'GET_CLOCK': return dict(state='synchronized', leap='normal',
                                              uncertainty_ns='1000', utc_now_ns='1000000000000')
            return {}
        peer.request.side_effect = request
        capture = Mock(); capture.poll.return_value = 0; capture.wait.return_value = 0
        def start_capture(argv, **kwargs):
            root = Path(argv[-2]).parent
            with (root/'capture.cf32').open('wb') as out: out.truncate(80000000)
            with (root/'capture.cf32.incomplete').open('wb') as out: out.truncate(65536)
            write_json(root/'capture.json', dict(actual_settings=p.SETTINGS,
                resolved_device=dict(driver='sdrplay', serial='2404058C60'), overflow_count=0,
                timeout_count=0, clipping=dict(sample_count=0), cleanup=dict(outcome='verified'),
                primary_outcome='success', retained_sample_count=10000000,
                output=dict(complete=True, size_bytes=80000000, sha256=p.digest(root/'capture.cf32'))))
            return capture
        active = copy.deepcopy(self.info); active['status']['output_active'] = True
        held = copy.deepcopy(self.info); held['gp14_held'] = True
        final = copy.deepcopy(self.info)
        final.update(gp14_stop_verified=True, gp14_output_inhibited=True, rf_safety_inhibited=True,
                     rf_safety_input_fault=0, gp14_last_duration_us='13000000', gp14_stop_events=1,
                     gp14_ap_events=1, gp14_ap_request_attempts=1, gp14_ap_request_accepts=1,
                     gp14_softap_service_ready=True, rf_safety_requested_ns='100000000',
                     rf_safety_stopped_ns='101000000')
        replies = [self.info, dict(ready=True), active, dict(cue=True), held, final, final]
        original_read_text = Path.read_text
        def read_text(path, *args, **kwargs):
            if str(path) == '/proc/sys/kernel/random/boot_id': return 'host-boot'
            return original_read_text(path, *args, **kwargs)
        with patch.object(p, 'console', side_effect=replies), patch.object(p, 'Peer', return_value=peer), \
                patch.object(p.socket, 'create_connection') as lan, \
                patch.object(p.subprocess, 'Popen', side_effect=start_capture) as receiver, \
                patch.object(Path, 'read_text', read_text), contextlib.redirect_stdout(io.StringIO()):
            self.execute(ready, receipt)
        lan.assert_called_once_with(('192.168.1.77', 31417), timeout=5)
        receiver.assert_called_once()
        operations = [call.args[0] for call in peer.request.call_args_list]
        self.assertEqual(operations, ['HELLO', 'CAPS', 'STATUS', 'CLAIM', 'LOAD', 'GET_CLOCK',
                                      'ARM', 'STATUS', 'CLAIM'])
        loaded = next(call.args[1] for call in peer.request.call_args_list if call.args[0] == 'LOAD')
        self.assertEqual(loaded['events'][0]['duration_ns'], '20000000000')
        self.assertEqual(peer.request.call_args_list[-1].kwargs, dict(expected_error='BUSY'))
        attempts = [json.loads(path.read_text()) for path in self.root.glob('run-*/attempt.json')]
        self.assertEqual((len(attempts), sum(a['charged_jobs'] for a in attempts)), (17, 12))
        attempt = next(a for a in attempts if 'operator_ready' in a)
        self.assertEqual(attempt['status'], 'CAPTURED_RF_AND_AP_INTERFACE_ASSESSMENT_PENDING')
        self.assertIs(attempt['target_checks_passed'], False)
        self.assertIs(attempt['independent_rf_pass'], False)
        self.assertEqual((attempt['ap_interface_proof'], attempt['phone_observation']), ('PENDING', 'PENDING'))


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
        write_json(self.root/'packet.json', historical_packet())
        self.attempt = dict(case='quick_reset', charged_jobs=1, status='FAILED_STOP_CAMPAIGN',
                            error='RuntimeError: physical action timeout', cleanup_verified=True,
                            boot_id='boot', job_id='1'*32, duration_ns='20000000000',
                            receiver_completion_after_target_failure=0,
                            packet_sha256=p.digest(self.root/'packet.json'))
        write_json(self.path, self.attempt)
        info = dict(device_id=p.DEVICE, revision=p.HISTORICAL_SOURCE[:12], system_clock_hz=138000000,
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
