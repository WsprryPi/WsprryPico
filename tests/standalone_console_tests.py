import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import standalone_console


class ConsoleTests(unittest.TestCase):
    def test_access_commands_are_exact_and_device_bound(self):
        self.assertEqual(standalone_console.command_for('access-status', 'device'), 'ACCESS STATUS')
        self.assertEqual(standalone_console.command_for('ble-status', 'device'), 'BLE STATUS')
        self.assertEqual(standalone_console.command_for('softap', '0123'), 'ACCESS SOFTAP 0123')
        self.assertEqual(standalone_console.command_for('identify', 'abcd'), 'IDENTIFY abcd')
        self.assertEqual(standalone_console.command_for('gp14-flash', 'abcd'), 'GP14 FLASH abcd')

    def test_no_device_io_without_opt_in(self):
        for action in ('info', 'storage', 'netlink', 'access-status', 'ble-status',
                       'softap', 'identify', 'gp14-flash'):
            with self.subTest(action=action):
                result = subprocess.run([sys.executable, standalone_console.__file__, action,
                                         '--port', '/missing-device', '--device-id', 'test'],
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn('--run is required', result.stderr)
                self.assertNotIn('Traceback', result.stderr)

    def test_flash_probe_needs_exact_test_variant(self):
        result = subprocess.run([sys.executable, standalone_console.__file__, 'gp14-flash',
            '--port', '/missing-device', '--device-id', 'test', '--run'],text=True,capture_output=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('requires --revision',result.stderr)
        good = dict(gp14_flash_probe=True,gp14_flash_probe_failed=False,gp14_capture_fault=False,
                    recovery_boot=False,status={'engine':'inhibited-standalone-simulator','output_active':False})
        self.assertTrue(standalone_console.flash_probe_ready(good))
        for field in ('gp14_flash_probe','gp14_flash_probe_failed','gp14_capture_fault','recovery_boot','status'):
            bad=good.copy(); del bad[field]
            self.assertFalse(standalone_console.flash_probe_ready(bad))
        self.assertFalse(standalone_console.flash_probe_ready(good | {'gp14_flash_probe_failed':True}))
        self.assertFalse(standalone_console.flash_probe_ready(good | {'status':{'engine':'physical-rf','output_active':False}}))

    def test_private_configuration_gate_and_redaction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'private.json'
            value = dict(enabled=True, expires_utc_s=1200, wifi=dict(password='PRIVATE-SENTINEL'))
            path.write_text(json.dumps(value))
            self.assertTrue(standalone_console.configuration(path, True, 1000).startswith('CONFIG '))
            for enabled, now in [(False, 1000), (True, 1200), (True, 0)]:
                if now == 0:
                    value['expires_utc_s'] = 4000
                    path.write_text(json.dumps(value))
                with self.assertRaises(ValueError) as error:
                    standalone_console.configuration(path, enabled, now)
                self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))
            path.write_text('{ "password": "PRIVATE-SENTINEL", malformed')
            with self.assertRaises(ValueError) as error:
                standalone_console.configuration(path, True, 1000)
            self.assertNotIn('PRIVATE-SENTINEL', str(error.exception))
            path.write_text(json.dumps(dict(enabled=False)))
            self.assertIn('false', standalone_console.configuration(path, False, 1000))


if __name__ == '__main__':
    unittest.main()
