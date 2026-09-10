#!/usr/bin/env python3
"""Adversarial evidence checks; no network or Pico access."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import audit_phase11_4_hotspot as audit
import phase11_4_hotspot as fixture


class HotspotAuditTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {'epoch_ns': 10, 'kind': 'CLIENT_PASS', 'value': {
                'address': '10.77.14.10', 'boot': 'boot-a', 'fingerprint': 'cert-a'}},
            {'epoch_ns': 20, 'kind': 'DHCP_BINDING_CHANGE', 'value': {'boot': 'boot-a'}},
            {'epoch_ns': 40, 'kind': 'INFO', 'value': {
                'device_id': 'fd6127d11d6aca42a9905fa3fb1bf1d5',
                'status': {'boot_id': 'boot-a', 'engine': 'inhibited-standalone-simulator',
                           'output_active': False, 'enabled': False}, 'network': {'ipv4': '10.77.14.20'}}},
            {'epoch_ns': 45, 'kind': 'client_native_dns', 'value': {'addresses': ['10.77.14.20']}},
            {'epoch_ns': 60, 'kind': 'CONFIG', 'value': {}}]
        self.parsed = {'dhcp': [
            {'epoch_ns': 25, 'type': 3, 'xid': 'abcd', 'requested': '10.77.14.20',
             'yiaddr': '0.0.0.0', 'source_mac': audit.MAC},
            {'epoch_ns': 30, 'type': 5, 'xid': 'abcd', 'yiaddr': '10.77.14.20',
             'source': '10.77.14.1', 'source_mac': '2c:cf:67:62:76:66'}],
            'a_records': [{'epoch_ns': 35, 'address': '10.77.14.20', 'ttl': 120, 'cls': 0x8001}]}

    def assess(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(audit, 'packets', return_value=self.parsed):
            root = Path(temp)
            (root / 'events.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in self.rows))
            return audit.assess(root)

    def test_dhcp_does_not_imply_authenticated_recovery(self):
        case = self.assess()['cases'][0]
        self.assertTrue(case['real_dhcp_change'])
        self.assertFalse(case['independent_client_complete'])

    def test_missing_ack(self):
        self.parsed['dhcp'].pop()
        with self.assertRaisesRegex(AssertionError, 'No captured'):
            self.assess()

    def test_transaction_mismatch(self):
        self.parsed['dhcp'][0]['xid'] = 'ffff'
        with self.assertRaisesRegex(AssertionError, 'matching Pico'):
            self.assess()

    def test_wrong_server_mac(self):
        self.parsed['dhcp'][1]['source_mac'] = audit.MAC
        with self.assertRaisesRegex(AssertionError, 'server MAC'):
            self.assess()

    def test_changed_boot(self):
        self.rows[2]['value']['status']['boot_id'] = 'boot-b'
        with self.assertRaises(AssertionError):
            self.assess()

    def test_wrong_pico_identity(self):
        self.rows[2]['value']['device_id'] = 'another-pico'
        with self.assertRaises(AssertionError):
            self.assess()

    def test_active_output_refused(self):
        self.rows[2]['value']['status']['output_active'] = True
        with self.assertRaises(AssertionError):
            self.assess()

    def test_wrong_baseline_boot(self):
        self.rows[0]['value']['boot'] = 'boot-b'
        with self.assertRaises(AssertionError):
            self.assess()

    def test_stale_positive_address(self):
        stale = copy.deepcopy(self.parsed['a_records'][0])
        stale['address'] = '10.77.14.10'
        self.parsed['a_records'].append(stale)
        with self.assertRaises(AssertionError):
            self.assess()

    def test_native_resolver_stale(self):
        self.rows[3]['value']['addresses'] = ['10.77.14.10']
        with self.assertRaisesRegex(AssertionError, 'resolver'):
            self.assess()

    def test_post_cleanup_ack_cannot_close_transition(self):
        self.parsed['dhcp'][1]['epoch_ns'] = 70
        with self.assertRaisesRegex(AssertionError, 'No captured'):
            self.assess()

    def test_post_cleanup_success_not_promoted(self):
        self.rows.append({'epoch_ns': 70, 'kind': 'CLIENT_PASS', 'value': {
            'address': '10.77.14.20', 'boot': 'boot-a', 'fingerprint': 'cert-a'}})
        self.assertFalse(self.assess()['cases'][0]['independent_client_complete'])

    def test_certificate_change_rejected(self):
        self.rows.insert(-1, {'epoch_ns': 50, 'kind': 'CLIENT_PASS', 'value': {
            'address': '10.77.14.20', 'boot': 'boot-a', 'fingerprint': 'cert-b'}})
        with self.assertRaises(AssertionError):
            self.assess()


class FixtureRefusalTests(unittest.TestCase):
    def test_timeout_never_exposes_command_password(self):
        secret = 'temporary-test-password'
        with patch.object(fixture.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['nmcli', secret], 1)), patch.object(fixture, 'note') as note:
            with self.assertRaises(TimeoutError) as error:
                fixture.cmd(['nmcli', secret], timeout=1)
            self.assertNotIn(secret, str(error.exception))
            self.assertNotIn(secret, repr(note.call_args))

    def test_no_setup_marker_no_cleanup_mutation(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(fixture, 'ROOT', Path(temp)), patch.object(fixture, 'cmd') as cmd:
            fixture.cleanup()
            cmd.assert_not_called()

    def test_optimized_execution_refused_before_any_mutation(self):
        result = subprocess.run([sys.executable, '-O', str(Path(fixture.__file__)),
                                 'cleanup', '--root', '/nonexistent', '--run'],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('enabled Python assertions', result.stderr)


if __name__ == '__main__':
    unittest.main()
