"""Failure injection for reference cleanup; no device or network access."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import capture_rf_bench

class Tests(unittest.TestCase):
    def exercise_failure(self, fail_final_status):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / 'image.uf2'
            image.write_bytes(b'test fixture')
            output = root / 'evidence'
            calls = []
            def remote(host, args, **kwargs):
                calls.append(args)
                if fail_final_status and args[0] == 'sudo' and args[4] == 'detail':
                    if len([c for c in calls if c[0] == 'sudo' and c[4] == 'detail']) == 3:
                        raise RuntimeError('lost final status')
            argv = ['capture_rf_bench.py', '--port', 'fake', '--serial', 'fake',
                    '--revision', 'test', '--firmware', str(image), '--output', str(output),
                    '--attenuation-db', '60', '--gpsdo-reference']
            with patch.object(sys, 'argv', argv), patch.object(capture_rf_bench, 'remote', remote), \
                    patch.object(capture_rf_bench.subprocess, 'Popen', side_effect=RuntimeError('capture failed')):
                with self.assertRaises(RuntimeError):
                    capture_rf_bench.main()
            self.assertEqual(sum('--enable1' in c for c in calls), 1)
            self.assertEqual(sum('--disable1' in c for c in calls), 1)
            manifest = json.loads((output / 'session.json').read_text())
            self.assertFalse(manifest['capture_success'])
            self.assertEqual(manifest['reference_disable_verified_by_cli'], not fail_final_status)
    def test_receive_only_conflicts_rejected_before_io(self):
        argv = ['capture_rf_bench.py', '--port', 'fake', '--serial', 'fake',
                '--revision', 'test', '--firmware', 'missing', '--output', 'unused',
                '--attenuation-db', '60', '--receive-only']
        for extra in (['--frame'], ['--abort-after-ms', '100']):
            with patch.object(sys, 'argv', argv + extra), patch.object(capture_rf_bench, 'remote') as remote:
                with self.assertRaises(SystemExit):
                    capture_rf_bench.main()
                remote.assert_not_called()

    def test_capture_failure_disables_reference(self):
        self.exercise_failure(False)
    def test_status_failure_still_disables_reference(self):
        self.exercise_failure(True)

if __name__ == '__main__':
    unittest.main()
