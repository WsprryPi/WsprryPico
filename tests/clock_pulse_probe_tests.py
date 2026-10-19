"""Synthetic physical-event failure paths; does not open a device."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import time
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from clock_pulse_probe import identify_usb_parent, validate_edges
from clock_probe_context import InputAudit, validate_idle


class Tests(unittest.TestCase):
    def test_fault_context_is_retained_before_idle_refusal(self):
        audit = InputAudit.__new__(InputAudit)
        audit.request = SimpleNamespace(get_values=lambda _: [
            SimpleNamespace(name='INACTIVE'), SimpleNamespace(name='ACTIVE')])
        audit.memory = bytearray(0x30000)
        audit.power_at, audit.power = time.monotonic(), 0x50000
        audit.power_error = audit.power_text = None
        audit.stream = io.StringIO()
        audit.baseline = dict(levels=['INACTIVE', 'INACTIVE'], power_flags=0x50000,
                              registers={n: dict(ctrl=0, pad=0) for n in ('22', '23')})
        with self.assertRaisesRegex(ValueError, 'idle low'):
            audit.idle()
        saved = json.loads(audit.stream.getvalue())
        self.assertEqual(saved['levels'], ['INACTIVE', 'ACTIVE'])
        self.assertEqual(saved['power_flags'], 0x50000)
        self.assertFalse('events' in saved)
        audit.stream = io.StringIO()
        audit.power_at = -float('inf')
        audit.request = SimpleNamespace(get_values=lambda _: [
            SimpleNamespace(name='INACTIVE'), SimpleNamespace(name='INACTIVE')])
        with patch('clock_probe_context.subprocess.check_output', return_value='broken power reply'):
            with self.assertRaisesRegex(ValueError, 'power receipt'):
                audit.idle()
        saved = json.loads(audit.stream.getvalue())
        self.assertEqual(saved['power_text'], 'broken power reply')
        self.assertIsNone(saved['power_flags'])

    def test_idle_context_distinguishes_historical_power_flags_from_current_fault(self):
        baseline = dict(levels=['INACTIVE', 'INACTIVE'], power_flags=0x50000,
                        registers={n: dict(ctrl=5, pad=86) for n in ('22', '23')})
        validate_idle(baseline, baseline)
        for change in ['current_power', 'high', 'control', 'pad']:
            state = copy.deepcopy(baseline)
            if change == 'current_power':
                state['power_flags'] |= 1
            elif change == 'high':
                state['levels'][1] = 'ACTIVE'
            else:
                state['registers']['22']['ctrl' if change == 'control' else 'pad'] ^= 1
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_idle(state, baseline)

    def test_usb_root_hub_serial_does_not_obscure_nearest_device(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory)
            board = hub/'3-1.2'
            interface = board/'3-1.2:1.0'
            interface.mkdir(parents=True)
            for device, serial, vendor, product in [
                    (hub, 'xhci-platform', '1d6b', '0002'),
                    (board, 'CDDBF8767C506C07', 'cafe', '4012')]:
                for key, value in [('serial', serial), ('idVendor', vendor), ('idProduct', product)]:
                    (device/key).write_text(value+'\n')
            result = identify_usb_parent(interface, 'CDDBF8767C506C07')
            self.assertEqual(result['path'], str(board))
            # Matching an ancestor is insufficient if the nearest device is
            # wrong, even when its hub happens to carry the expected identity.
            (hub/'serial').write_text('CDDBF8767C506C07\n')
            (hub/'idVendor').write_text('cafe\n')
            (hub/'idProduct').write_text('4012\n')
            (board/'serial').write_text('0BF4B4AEC9FFB344\n')
            with self.assertRaises(ValueError):
                identify_usb_parent(interface, 'CDDBF8767C506C07')
            (board/'serial').write_text('CDDBF8767C506C07\n')
            (board/'idVendor').write_text('2e8a\n')
            with self.assertRaises(ValueError):
                identify_usb_parent(interface, 'CDDBF8767C506C07')
            (board/'idVendor').write_text('cafe\n')
            (board/'serial').unlink()
            with self.assertRaises(ValueError):
                identify_usb_parent(interface, 'CDDBF8767C506C07')

    def setUp(self):
        self.record = {'ok': True, 'schema': 'pico-clock-probe/1', 'gpio': 22,
                       'pin_restored': True, 'high_readback': True, 'low_readback': True,
                       'clock_valid': True, 'raw_resolution_ns': 1000,
                       'rise_raw_lower_ns': '1000000', 'rise_raw_upper_ns': '1003000',
                       'rise_before': {'monotonic_now_ns': '1000000'},
                       'rise_after': {'monotonic_now_ns': '1002000'},
                       'fall_before_ns': '2002000', 'fall_after_ns': '2003000'}
        self.events = [{'line': 22, 'timestamp_ns': 10**9, 'edge': 'RISING_EDGE', 'sequence': 8},
                       {'line': 22, 'timestamp_ns': 10**9+1_003_000,
                        'edge': 'FALLING_EDGE', 'sequence': 9}]

    def test_real_edge_and_bracket_are_retained_without_absolute_accuracy_claim(self):
        r = validate_edges(self.record, self.events, 22, 7)
        self.assertEqual(r['pulse_width_ns'], 1_003_000)
        self.assertEqual(r['pico_edge_bracket_ns'], 3000)
        self.assertFalse(r['absolute_timestamp_delay_qualified'])

    def test_crossed_shortened_extra_or_lost_events_refuse(self):
        variants = [self.events[:1], self.events+self.events,
                    [dict(e, line=23) for e in self.events],
                    [self.events[0], dict(self.events[1], sequence=10)],
                    [dict(self.events[0], edge='FALLING_EDGE'), self.events[1]],
                    [self.events[0], dict(self.events[1], timestamp_ns=10**9-1)],
                    [self.events[0], dict(self.events[1], timestamp_ns=10**9+20_000_000)]]
        for events in variants:
            with self.subTest(events=events), self.assertRaises(ValueError):
                validate_edges(self.record, events, 22, 7)

    def test_hardware_and_timestamp_failures_refuse(self):
        for field in ['ok', 'pin_restored', 'high_readback', 'low_readback']:
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_edges(dict(self.record, **{field: False}), self.events, 22, 7)
        bad = copy.deepcopy(self.record)
        bad['rise_after']['monotonic_now_ns'] = '1100000'
        with self.assertRaises(ValueError):
            validate_edges(bad, self.events, 22, 7)

    def test_unsynchronized_clock_can_test_wiring_but_cannot_validate_utc(self):
        r = validate_edges(dict(self.record, clock_valid=False), self.events, 22, 7)
        self.assertFalse(r['clock_valid'])
        self.assertFalse(r['absolute_timestamp_delay_qualified'])


if __name__ == '__main__':
    unittest.main()
