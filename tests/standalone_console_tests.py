import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import standalone_console


class ConsoleTests(unittest.TestCase):
    def test_no_device_io_without_opt_in(self):
        result = subprocess.run([sys.executable, standalone_console.__file__, 'info',
                                 '--port', '/missing-device', '--device-id', 'test'],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--run is required', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

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
