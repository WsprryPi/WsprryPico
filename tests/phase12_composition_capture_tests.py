#!/usr/bin/env python3
import json
import hashlib
import datetime
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase12_composition_capture import capture, check_info, check_approval
from phase12_composition_audit_tests import fixture


def info(p):
    return dict(ok=True, device_id=p['device_id'], revision=p['source_commit'][:12],
                firmware=p['firmware'], softap_session_inactivity_ms=900000,
                softap_session_absolute_ms=43200000, resource_schema=1, lan_wtp_mode='plain',
                core0_stack_guard_valid=1, core0_stack_fault_status=0,
                fault_stage=0, fault_hash=0, fault_pc=0, fault_status=0,
                tls_allocation_failures=0, allocator_failures=0, provisioning_fault=0,
                flash_read_failures=0, flash_erase_failures=0, flash_program_failures=0,
                btstack_pool_occupancy_measured=True, btstack_pools={k: dict(used=0,
                capacity=4, peak=0, failures=0, faults=0) for k in
                ('hci_connections', 'l2cap_channels', 'l2cap_services', 'sm_lookup', 'whitelist')},
                access_state='healthy', deployment_identity_matches=True,
                radio_identity_valid=True, provisioning_source='provisioned', network={'memory': {'statistics_enabled': True, 'heap': None,
                    **{k: dict(used=0, capacity=8, peak=0, errors=0) for k in
                    ('tcp_pcbs', 'tcp_listeners', 'udp_pcbs', 'timeouts',
                     'igmp_groups', 'tcp_segments', 'packet_pool')}}},
                bootstrap_connected=False, bootstrap_setup_pending=False, bootstrap_reset_pending=False,
                ble_indication_pending=False, network_active_connections=0,
                network_pending_connections=0, network_buffered_rx_bytes=0, network_pending_tcp_bytes=0,
                bootstrap_pending_tcp_bytes=0, ble_active_connections=0, ble_inbound_bytes=0,
                ble_outbound_bytes=0, ble_outbound_frames=0,
                status=dict(state='empty', owner_id=None, job_id=None, boot_id=p['boot_id'], engine=p['engine'], enabled=False,
                            output_active=False))


class CaptureTests(unittest.TestCase):
    def test_exact_gates(self):
        p, _ = fixture()
        for key, value in [('device_id', '0'*32), ('revision', 'dirty'),
                           ('firmware', 'other'), ('lan_wtp_mode', 'tls'),
                           ('fault_stage', 1), ('core0_stack_guard_valid', 0),
                           ('tls_allocation_failures', 1)]:
            sample = info(p)
            sample[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                check_info(p, sample)
        sample = info(p)
        sample['status']['engine'] = 'pio-dma-gp2'
        with self.assertRaises(ValueError):
            check_info(p, sample)

    def test_pool_schema_and_ordinary_limits(self):
        p, _ = fixture()
        for mutation in (lambda v: v['network']['memory'].pop('timeouts'),
                         lambda v: v['network']['memory'].update(tcp_pcbs=None),
                         lambda v: v.update(softap_session_absolute_ms=60000),
                         lambda v: v.update(phase12_fault_stage=1)):
            sample = info(p)
            mutation(sample)
            with self.assertRaises((ValueError, KeyError)):
                check_info(p, sample)

    def test_approval_binding_expiry(self):
        p, _ = fixture()
        approval = dict(schema='phase12-observer-approval/1', approved=True,
            operation='composition-info-only', console='console',
            source_commit=p['source_commit'], image_sha256=p['image_sha256'],
            plan_sha256=hashlib.sha256(json.dumps(p, sort_keys=True,
                separators=(',', ':')).encode()).hexdigest(), expires_utc='2099-01-01T00:00:00Z')
        check_approval(p, approval, 'console')
        for field, value in [('approved', False), ('console', 'other'),
                             ('plan_sha256', '0'*64),
                             ('expires_utc', (datetime.datetime.now(datetime.timezone.utc) +
                               datetime.timedelta(seconds=1)).isoformat()),
                             ('expires_utc', '2020-01-01T00:00:00Z')]:
            changed = dict(approval, **{field: value})
            with self.assertRaises(ValueError):
                check_approval(p, changed, 'console')

    def test_clock_pause_stops_before_read(self):
        p, _ = fixture()
        now, calls = [0.0], [0]
        def observer():
            calls[0] += 1
            return info(p)
        def sleeper(seconds):
            now[0] += seconds + (60 if calls[0] else 0)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                capture(p, '/dev/serial/by-id/usb-WsprryPi_WsprryPico_TEST-if00',
                    Path(d) / 'capture.jsonl', clock=lambda: now[0], sleeper=sleeper,
                    observer=observer)
        self.assertEqual(calls[0], 1)

    def test_full_capture_no_acceptance(self):
        p, _ = fixture()
        now = [0.0]
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'capture.jsonl'
            capture(p, '/dev/serial/by-id/usb-WsprryPi_WsprryPico_TEST-if00', output,
                    clock=lambda: now[0], sleeper=lambda n: now.__setitem__(0, now[0]+n),
                    observer=lambda: info(p))
            records = [json.loads(s) for s in output.read_text().splitlines()]
            self.assertEqual(len(records), 243)
            self.assertFalse(records[-1]['physical_acceptance'])
            self.assertEqual(now[0], 7200)
            with self.assertRaises(FileExistsError):
                capture(p, '/dev/serial/by-id/usb-WsprryPi_WsprryPico_TEST-if00', output,
                        observer=lambda: self.fail('observer must not run'))

    def test_failure_preserves_raw_then_stops(self):
        p, _ = fixture()
        broken = info(p)
        broken['fault_stage'] = 1
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'capture.jsonl'
            with self.assertRaises(ValueError):
                capture(p, '/dev/serial/by-id/usb-WsprryPi_WsprryPico_TEST-if00', output,
                        observer=lambda: broken)
            records = [json.loads(s) for s in output.read_text().splitlines()]
            self.assertEqual(records[-1]['kind'], 'failed')
            self.assertEqual(records[-2]['info']['fault_stage'], 1)


if __name__ == '__main__':
    unittest.main()
