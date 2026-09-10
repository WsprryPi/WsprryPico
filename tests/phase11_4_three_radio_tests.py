#!/usr/bin/env python3
"""Hardware-free refusal checks for the opt-in controlled radio fixture."""
import copy
from pathlib import Path
import subprocess
import sys
import unittest
import json
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase11_4_three_radio as fixture
import inhibited_network_acceptance as network
from phase11_4_three_radio_audit import has_answer, NAME, ADDRESS


class Tests(unittest.TestCase):
    def test_reconnect_resumes_client_session_before_hello(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            session = '1234567890abcdef' * 2
            (root / 'peer.json').write_text(json.dumps(dict(credentials=folder,
                fingerprint='test', session_id=session)))
            with patch.object(fixture.h, 'ROOT', root), patch.object(fixture.h.socket, 'getaddrinfo',
                    return_value=[(2,1,6,'',('10.77.14.10',18443))]), patch.object(network, 'Peer') as peer:
                peer.return_value.open.side_effect = RuntimeError('stop before transport')
                for _ in range(2):
                    with self.assertRaisesRegex(RuntimeError, 'stop before transport'):
                        fixture.h.probe('10.77.14.10', 'boot')
                    self.assertEqual(peer.return_value.session, session)
                self.assertEqual(peer.return_value.close.call_count, 2)
                (root / 'peer.json').write_text(json.dumps(dict(credentials=folder,
                    fingerprint='test', session_id='invalid')))
                with self.assertRaisesRegex(ValueError, 'session identity'):
                    fixture.h.probe('10.77.14.10', 'boot')
                self.assertEqual(peer.return_value.open.call_count, 2)

    def test_optimized_execution_is_refused_before_io(self):
        result = subprocess.run([sys.executable, '-O', str(Path(fixture.__file__)), 'setup',
                                 '--root', '/nonexistent', '--run'], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('enabled Python assertions', result.stderr)

    def test_no_run_is_read_only(self):
        result = subprocess.run([sys.executable, str(Path(fixture.__file__)), 'setup',
                                 '--root', '/nonexistent'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Plan only', result.stdout)

    def test_mutation_rejects_wrong_firmware_before_command(self):
        value = dict(device_id=fixture.h.DEVICE, revision='other', deployment_identity_matches=True,
                     recovery_boot=False, status={'boot_id': 'boot'})
        with patch.object(fixture, 'BASE_CONSOLE', return_value=value) as call:
            with self.assertRaisesRegex(ValueError, 'revision'):
                fixture.console('WIFI OFF', 'boot')
            call.assert_called_once_with()

    def test_mutation_rejects_recovery_boot(self):
        value = dict(device_id=fixture.h.DEVICE, revision=fixture.REVISION,
                     deployment_identity_matches=True, recovery_boot=True)
        with patch.object(fixture, 'BASE_CONSOLE', return_value=value) as call:
            with self.assertRaisesRegex(ValueError, 'recovery'):
                fixture.console('WIFI ON', 'boot')
            call.assert_called_once_with()

    def test_actual_answer_identity(self):
        p = dict(source=ADDRESS, source_mac='88:a2:9e:0a:60:df', ttl=255, sport=5353, dport=5353,
                 dns=dict(flags=0x8400, records=[dict(name=NAME, type=1, address=ADDRESS, ttl=0, cls=0x8001)]))
        self.assertTrue(has_answer(p, 0))
        changes = [('source', '10.77.14.2'), ('source_mac', '00:00:00:00:00:00'), ('ttl', 64),
                   ('sport', 1234), ('dport', 1234)]
        for key, value in changes:
            with self.subTest(key=key):
                wrong = copy.deepcopy(p)
                wrong[key] = value
                self.assertFalse(has_answer(wrong, 0))
        for key, value in [('name', 'other.local'), ('address', '10.77.14.20'), ('ttl', 120), ('cls', 1)]:
            with self.subTest(key=key):
                wrong = copy.deepcopy(p)
                wrong['dns']['records'][0][key] = value
                self.assertFalse(has_answer(wrong, 0))


if __name__ == '__main__':
    unittest.main()
