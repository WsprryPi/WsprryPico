"""Failure injection for reference cleanup; no device or network access."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
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
    def test_warmup_failure_prevents_measured_frame_and_disables_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / 'image.uf2'
            image.write_bytes(b'fixture')
            argv = ['capture_rf_bench.py', '--port', 'fake', '--serial', 'fake',
                    '--revision', 'test', '--firmware', str(image), '--output', str(root/'out'),
                    '--attenuation-db', '60', '--gpsdo-reference', '--wspr', 'AA0NT', 'EM18', '20', '--rf-warmup']
            calls = []
            with patch.object(sys, 'argv', argv), patch.object(capture_rf_bench, 'remote',
                    side_effect=lambda host, args, **kwargs: calls.append(args)), \
                    patch.object(capture_rf_bench.subprocess, 'run', return_value=SimpleNamespace(returncode=1)) as run, \
                    patch.object(capture_rf_bench.subprocess, 'Popen') as capture:
                with self.assertRaisesRegex(RuntimeError, 'RF warmup failed'):
                    capture_rf_bench.main()
                capture.assert_not_called()
                self.assertIn('wspr', run.call_args.args[0])
                self.assertIn(str(root/'out'/'warmup'), run.call_args.args[0])
            self.assertEqual(sum('--disable1' in c for c in calls), 1)

    def test_disk_check_failure_prevents_device_work(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory)/'image.uf2'
            image.write_bytes(b'fixture')
            argv = ['capture_rf_bench.py', '--port', 'fake', '--serial', 'fake',
                    '--revision', 'test', '--firmware', str(image), '--output', str(Path(directory)/'out'),
                    '--attenuation-db', '60', '--gpsdo-reference']
            calls = []
            def remote(host, args, **kwargs):
                calls.append(args)
                if args[0] == 'python3':
                    raise RuntimeError('Insufficient capture disk space')
            with patch.object(sys, 'argv', argv), patch.object(capture_rf_bench, 'remote', remote), \
                    patch.object(capture_rf_bench.subprocess, 'Popen') as capture:
                with self.assertRaises(RuntimeError):
                    capture_rf_bench.main()
                capture.assert_not_called()
            self.assertFalse(any('--enable1' in c for c in calls))

    def test_receive_only_conflicts_rejected_before_io(self):
        argv = ['capture_rf_bench.py', '--port', 'fake', '--serial', 'fake',
                '--revision', 'test', '--firmware', 'missing', '--output', 'unused',
                '--attenuation-db', '60', '--receive-only']
        for extra in (['--frame'], ['--wspr', 'AA0NT', 'EM18', '20'], ['--abort-after-ms', '100']):
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
