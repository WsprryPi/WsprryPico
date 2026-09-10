#!/usr/bin/env python3
"""Hardware-free failure-retention, authority, framing and real cleanup tests."""
import copy
import json
from pathlib import Path
import signal
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_4_loop_common import campaign_decision, stop_process, validate_info, validate_host, DEVICE, captured_baseline, ADDRESS, NAME
from phase11_4_loop_audit import strict_usb, validate_completed_observers, clock_gate_evidence, shutdown_reset
from validate_wtp_contract import frame


class HarnessTests(unittest.TestCase):
    def test_packet_baseline_identity_and_ttl(self):
        record = {'type': 1, 'name': NAME, 'address': ADDRESS, 'ttl': 120, 'cls': 0x8001}
        packet = {'source': ADDRESS, 'source_mac': '88:a2:9e:0a:60:df', 'sport': 5353,
                  'dport': 5353, 'ttl': 255, 'dns': {'flags': 0x8400, 'records': [record]}}
        self.assertTrue(captured_baseline([packet]))
        self.assertFalse(captured_baseline([]))
        for key, value in [('source', '192.168.1.99'), ('source_mac', '00:00:00:00:00:00'), ('ttl', 1)]:
            changed = copy.deepcopy(packet); changed[key] = value
            self.assertFalse(captured_baseline([changed]))
        for key, value in [('name', 'wrong.local'), ('address', '192.168.1.99'), ('ttl', 0), ('cls', 1)]:
            changed = copy.deepcopy(packet); changed['dns']['records'][0][key] = value
            self.assertFalse(captured_baseline([changed]))

    def test_watchdog_marker_identity_and_fault_refusal(self):
        value = {'device_id':DEVICE, 'revision':'candidate', 'recovery_boot':True,
                 'fault_stage':24, 'fault_hash':0, 'fault_pc':0, 'fault_status':0,
                 'status':{'boot_id':'new', 'engine':'inhibited-standalone-simulator','output_active':False}}
        self.assertEqual(shutdown_reset(value,'old','candidate'),'watchdog during multicast filter programming')
        self.assertEqual(shutdown_reset(dict(value,fault_stage=15),'old','candidate'),
                         'watchdog at shared mDNS-removal/Wi-Fi-connect marker')
        for stage in (15,16,20,21,22,23,24,25):
            self.assertIsNotNone(shutdown_reset(dict(value,fault_stage=stage),'old','candidate'))
        for key, bad in [('device_id','wrong'),('revision','wrong'),('recovery_boot',False),
                         ('fault_stage',99),('fault_hash',1),('fault_pc',123),('fault_status',1)]:
            self.assertIsNone(shutdown_reset(dict(value,**{key:bad}),'old','candidate'))
        for key,bad in [('boot_id','old'),('engine','rf'),('output_active',True)]:
            changed=copy.deepcopy(value);changed['status'][key]=bad
            self.assertIsNone(shutdown_reset(changed,'old','candidate'))

    def test_clean_threshold(self):
        clean = {'result': 'PASS'}
        self.assertEqual(campaign_decision([clean] * 7), 'CONTINUE')
        self.assertEqual(campaign_decision([clean] * 8), 'NOT_REPRODUCED_IN_BOUNDED_CAMPAIGN')

    def test_failure_is_never_erased(self):
        attempts = [{'result': 'FAIL'}] + [{'result': 'PASS'}] * 8
        self.assertEqual(campaign_decision(attempts), 'CONTINUE')
        self.assertEqual(campaign_decision([{'result': 'FAIL'}] * 3), 'HARNESS_INEFFECTIVE')

    def test_incomplete_observer_blocks_localization(self):
        self.assertEqual(campaign_decision([{'result': 'FAIL', 'observer_failure': True,
                                            'failure_point': 'claimed cause'}]), 'HARNESS_INEFFECTIVE')
        self.assertEqual(campaign_decision([{'result': 'FAIL', 'failure_point': 'watchdog during station disable'}]),
                         'FAILURE_POINT_DETECTED')

    def test_authority_mutations(self):
        v = {'device_id': DEVICE, 'revision': 'e4ff40a56180-dirty',
             'deployment_identity_matches': True, 'recovery_boot': False,
             'status': {'boot_id': 'a' * 32, 'engine': 'inhibited-standalone-simulator',
                        'enabled': False, 'output_active': False, 'storage_healthy': True}}
        validate_info(v, 'a' * 32)
        for key, value in [('device_id', 'wrong'), ('revision', 'wrong'),
                           ('deployment_identity_matches', False), ('recovery_boot', True)]:
            bad = copy.deepcopy(v)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_info(bad, 'a' * 32)
        for key, value in [('boot_id', 'b' * 32), ('engine', 'rf'), ('enabled', True),
                           ('output_active', True), ('storage_healthy', False)]:
            bad = copy.deepcopy(v)
            bad['status'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_info(bad, 'a' * 32)

    def test_host_metadata_without_mac_in_ip4_output(self):
        value = {'mac': '90:de:80:47:b9:da',
                 'address': json.dumps([{'ifname': 'wlan1', 'addr_info': [
                     {'family': 'inet', 'local': '192.168.1.117'}]}]),
                 'link': 'Connected to 6c:cd:d6:f2:f6:c6 (on wlan1)\n\tSSID: Bohica\n\tfreq: 5200.0',
                 'profile': '921301fe-cdfd-4965-8ac7-c96e9d908ea6',
                 'recovery_active': 'active', 'recovery_enabled': 'enabled'}
        validate_host(value)
        iot = dict(value, profile='temporary', recovery_active='inactive',
                   link=value['link'].replace('SSID: Bohica', 'SSID: Bohica-IoT'))
        validate_host(iot, profile='temporary', ssid='Bohica-IoT', recovery_active='inactive')
        with self.assertRaises(ValueError):validate_host(iot)
        for key in ('profile', 'link', 'recovery_active', 'recovery_enabled'):
            changed=dict(iot);changed[key]='wrong'
            with self.assertRaises(ValueError):
                validate_host(changed, profile='temporary', ssid='Bohica-IoT', recovery_active='inactive')
        for key in value:
            bad = dict(value)
            bad[key] = '[]' if key == 'address' else 'wrong'
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_host(bad)

    def test_raw_usb_does_not_resynchronize(self):
        v = {'ok': True}
        data = frame(json.dumps(v).encode())
        self.assertEqual(strict_usb(data, [v]), 1)
        for bad in [b'x' + data, data[:-1], data + b'x', data[:16] + b'bad payload',
                    data[:8] + b'\xff' * 4 + data[12:]]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                strict_usb(bad, [v])
        with self.assertRaises(ValueError):
            strict_usb(data, [])

    def test_pass_marker_cannot_hide_observer_failure(self):
        state = ['Result=success', 'ExecMainStatus=0']
        mac = [{'started_ns': t * 10**9, 'dns_ok': True, 'https_ok': True} for t in [10, 20]]
        self.assertEqual(validate_completed_observers(state, mac, 0), 2)
        with self.assertRaises(ValueError):
            validate_completed_observers(['Result=exit-code', 'ExecMainStatus=1'], mac, 0)
        with self.assertRaises(ValueError):
            validate_completed_observers(state, mac[:1], 0)
        bad = copy.deepcopy(mac)
        bad[1]['https_ok'] = False
        with self.assertRaises(ValueError):
            validate_completed_observers(state, bad, 0)
        bad[1]['https_ok'] = True
        bad[1]['dns_ok'] = False
        with self.assertRaises(ValueError):
            validate_completed_observers(state, bad, 0)

    def test_clock_gate_annotation_needs_packets_and_bracketing_samples(self):
        rows = [
            {'kind': 'console INFO', 'epoch_ns': 900_000_000,
             'value': {'status': {'clock_state': 'unsynchronized'}, 'network': {'accepted': 3}}},
            {'kind': 'https_failure', 'epoch_ns': 1_010_000_000,
             'value': {'type': 'ConnectionResetError'}},
            {'kind': 'console INFO', 'epoch_ns': 1_100_000_000,
             'value': {'status': {'clock_state': 'unsynchronized'}, 'network': {'accepted': 3}}},
        ]
        packets = [{'protocol': 'TCP', 'source': '192.168.1.47', 'target': '192.168.1.117',
                    'source_mac': '88:a2:9e:0a:60:df', 'sport': 18443, 'flags': 20,
                    'epoch_ns': 1_000_000_000}]
        self.assertEqual(len(clock_gate_evidence(rows, packets)), 1)
        self.assertEqual(clock_gate_evidence(rows, []), [])
        self.assertEqual(clock_gate_evidence(rows[:2], packets), [])
        changed = copy.deepcopy(rows)
        changed[-1]['value']['status']['clock_state'] = 'synchronized'
        self.assertEqual(clock_gate_evidence(changed, packets), [])
        changed = copy.deepcopy(rows)
        changed[-1]['value']['network']['accepted'] = 4
        self.assertEqual(clock_gate_evidence(changed, packets), [])
        changed = copy.deepcopy(packets)
        changed[0]['source_mac'] = 'wrong'
        self.assertEqual(clock_gate_evidence(rows, changed), [])

    def test_stubborn_child_cleanup(self):
        script = ('import signal,time;signal.signal(signal.SIGINT,signal.SIG_IGN);'
                  'signal.signal(signal.SIGTERM,signal.SIG_IGN);print("ready",flush=True);time.sleep(60)')
        child = subprocess.Popen([sys.executable, '-c', script], stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'ready')
            result = stop_process(child, grace=.05)
            self.assertEqual(result['exit'], -signal.SIGKILL)
            self.assertEqual(result['signals'], ['SIGINT', 'SIGTERM', 'SIGKILL'])
            self.assertLess(result['seconds'], 2)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=2)
            child.stdout.close()

    def test_idle_mode_requires_trace_before_staging(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/phase11_4_loop.py'
        r = subprocess.run([sys.executable, str(script), '--run', '--idle-clients',
                            '--output', '/not-created-by-harness-test', '--boot', 'a' * 32,
                            '--credentials', '/not-read-by-harness-test'], capture_output=True, text=True, timeout=3)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('requires --trace', r.stderr)

    def test_iot_override_refused_for_control(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/phase11_4_loop_target.py'
        r = subprocess.run([sys.executable, str(script), 'orderly', '--run',
                            '--output', '/not-created-by-harness-test', '--boot', 'a' * 32,
                            '--diagnostic-iot-profile', 'temporary'], capture_output=True, text=True, timeout=3)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('read-only diagnostic only', r.stderr)

    def test_no_optimization_bypass(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/phase11_4_loop_target.py'
        r = subprocess.run([sys.executable, '-O', str(script), 'orderly', '--run',
                            '--output', '/not-created-by-harness-test', '--boot', 'a' * 32],
                           capture_output=True, text=True, timeout=3)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('nonoptimized Python required', r.stderr)


if __name__ == '__main__':
    unittest.main()
