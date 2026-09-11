import copy
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_inventory import validate_inventory


class InventoryTests(unittest.TestCase):
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
