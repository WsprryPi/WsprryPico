import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_phase11_4_d2_shutdown import shutdown_window, completed_shutdown_marks
from phase11_4_loop_common import DEVICE

BOOT = 'a' * 32
REVISION = 'candidate'


def fixture():
    rows = []
    for second in range(158):
        enabled = second < 3 or second >= 153
        info = {'device_id': DEVICE, 'revision': REVISION, 'deployment_identity_matches': True,
                'recovery_boot': False, 'fault_stage': 0,
                'status': {'boot_id': BOOT, 'engine': 'inhibited-standalone-simulator',
                           'output_active': False, 'enabled': False, 'storage_healthy': True,
                           'state': 'empty', 'station': {}, 'schedules': [], 'watermark_utc_ns': '0',
                           'expires_utc_s': 0, 'suspended': False},
                'network': {'enabled': enabled, 'advertised_hostname': 'name.local' if enabled else ''}}
        rows.append({'epoch_ns': second * 10**9, 'monotonic_ns': second * 10**9,
                     'kind': 'console INFO', 'value': info})
    for second, kind, value in [(2.1, 'off_begin', {}), (2.2, 'console WIFI OFF', {'ok': True}),
                                (152.2, 'on_begin', {}), (152.3, 'console WIFI ON', {'ok': True})]:
        rows.append({'epoch_ns': int(second * 10**9), 'monotonic_ns': int(second * 10**9),
                     'kind': kind, 'value': value})
    return sorted(rows, key=lambda row: row['epoch_ns'])


class ShutdownAuditTests(unittest.TestCase):
    def test_old_ring_context_cannot_supply_current_disable(self):
        old = [{'kind': 3, 'result': code, 'seq': code, 'us': code} for code in (2, 3, 4, 5)]
        current = [{'kind': 3, 'result': code, 'seq': code + 10, 'us': code + 100} for code in (2, 3, 4, 5)]
        start, end, entering, disabled = completed_shutdown_marks(old + current, 100, 200)
        self.assertEqual([start['seq'], end['seq'], entering['seq'], disabled['seq']], [12, 13, 14, 15])
        with self.assertRaises(ValueError):
            completed_shutdown_marks(old + current[:-1], 100, 200)
        with self.assertRaises(ValueError):
            completed_shutdown_marks(old, 100, 200)

    def test_reversed_marker_time_is_rejected(self):
        events = [{'kind': 3, 'result': code, 'seq': code, 'us': 110 - code}
                  for code in (2, 3, 4, 5)]
        with self.assertRaisesRegex(ValueError, 'nonmonotonic'):
            completed_shutdown_marks(events, 100, 200)

    def test_network_failure_does_not_erase_valid_shutdown_observation(self):
        rows = fixture()
        rows.append({'kind': 'BASELINE_FAILURE', 'value': {'message': 'TCP timeout'}})
        rows.append({'kind': 'CASE_FAILURE', 'value': {'message': 'Recovery failed'}})
        result = shutdown_window(rows, BOOT, REVISION)
        self.assertEqual(result['result'], 'NO_WATCHDOG_IN_OBSERVED_WINDOW')
        self.assertNotIn('full_D2', result)

    def test_watchdog_cannot_be_hidden_by_eventual_recovery(self):
        rows = fixture()
        info = next(r['value'] for r in rows if r['kind'] == 'console INFO' and r['epoch_ns'] == 10**10)
        info.update(recovery_boot=True, fault_stage=16)
        info['status']['boot_id'] = 'b' * 32
        result = shutdown_window(rows, BOOT, REVISION)
        self.assertEqual(result['result'], 'FAIL_BOOT_CHANGED')
        self.assertEqual(result['fault_stage'], 16)

    def test_wrong_device_is_not_classified_as_subject_watchdog(self):
        rows = fixture()
        rows[-1]['value']['device_id'] = 'other'
        rows[-1]['value']['recovery_boot'] = True
        with self.assertRaisesRegex(ValueError, 'another device'):
            shutdown_window(rows, BOOT, REVISION)

    def test_missing_coverage_and_unsafe_state_are_rejected(self):
        base = fixture()
        variants = []
        variants.append([r for r in base if r['kind'] != 'console INFO' or not 10 <= r['epoch_ns']/1e9 < 17])
        unsafe = copy.deepcopy(base)
        unsafe[-1]['value']['status']['output_active'] = True
        variants.append(unsafe)
        changed = copy.deepcopy(base)
        changed[-1]['value']['status']['watermark_utc_ns'] = '1'
        variants.append(changed)
        extra = copy.deepcopy(base)
        extra.append({'kind': 'console REBOOT', 'value': {'ok': True}})
        variants.append(extra)
        short = copy.deepcopy(base)
        next(r for r in short if r['kind'] == 'on_begin')['monotonic_ns'] = 100 * 10**9
        variants.append(short)
        misplaced = copy.deepcopy(base)
        next(r for r in misplaced if r['kind'] == 'console WIFI OFF')['epoch_ns'] = 155 * 10**9
        variants.append(misplaced)
        for rows in variants:
            with self.subTest(rows=variants.index(rows)), self.assertRaises(ValueError):
                shutdown_window(rows, BOOT, REVISION)


if __name__ == '__main__':
    unittest.main()
