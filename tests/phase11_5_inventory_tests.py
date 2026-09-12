import copy
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_inventory import validate_inventory, loads_console, exchange
from validate_wtp_contract import frame


class InventoryTests(unittest.TestCase):
    def test_console_native_integer_boundaries(self):
        for value in (2844794185, 2**32-1, 2**64-1, -(2**63)):
            self.assertEqual(loads_console('{"value":'+str(value)+'}'), {'value': value})
        for value in (2**64, -(2**63)-1):
            with self.assertRaisesRegex(ValueError, '64-bit range'):
                loads_console(str(value))

    def test_console_retains_json_integrity_checks(self):
        for source in ('{"hash":0,"hash":1}', 'NaN', 'Infinity', '1.0', '1e2',
                       '"\\ud800"', '['*17+'0'+']'*17):
            with self.subTest(source=source), self.assertRaises(ValueError):
                loads_console(source)

    def test_exchange_separates_console_and_wtp_integer_rules(self):
        # Exact unsigned hash that stopped N1w before its production load began.
        payload = b'{"hash":2844794185}'
        def receive(framed):
            wire = frame(payload) if framed else payload+b'\n'
            with patch('phase11_5_inventory.select.select', return_value=([7], [7], [])), \
                 patch('phase11_5_inventory.os.write', side_effect=lambda fd, data: len(data)), \
                 patch('phase11_5_inventory.os.read', return_value=wire), \
                 patch('phase11_5_inventory.time.monotonic', return_value=0):
                return exchange(7, b'request', 1, lambda *args: None, framed)
        self.assertEqual(receive(False), {'hash':2844794185})
        with self.assertRaisesRegex(ValueError, 'WTP/1 range'):
            receive(True)

    def test_refuses_before_io(self):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] /
                                'scripts/phase11_5_inventory.py'), '--serial', 'missing',
                                 '--device-id', 'missing'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--run requires', result.stderr)

    def test_records_activity_without_claiming_idle(self):
        info = {'ok': True, 'device_id': 'a', 'status': {'boot_id': 'b', 'engine': 'physical',
                                                       'output_active': True}}
        responses = {'HELLO': {'device_id': 'a', 'boot_id': 'b'},
                     'CAPS': {'engine': 'physical'}, 'STATUS': {'boot_id': 'b', 'output_active': True},
                     'GET_CLOCK': {}, 'PING': {}}
        validate_inventory(info, responses, 'a')
        for path, value in [(('HELLO', 'device_id'), 'wrong'), (('STATUS', 'boot_id'), 'changed'),
                            (('CAPS', 'engine'), 'simulated'), (('STATUS', 'output_active'), 0)]:
            with self.subTest(path=path):
                bad = copy.deepcopy(responses)
                bad[path[0]][path[1]] = value
                with self.assertRaises(ValueError):
                    validate_inventory(info, bad, 'a')
        del responses['PING']
        with self.assertRaises(ValueError):
            validate_inventory(info, responses, 'a')


if __name__ == '__main__':
    unittest.main()
