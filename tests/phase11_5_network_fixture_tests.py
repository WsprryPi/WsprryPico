#!/usr/bin/env python3
"""Hardware-free ownership, deadline and restoration tests for the opt-in fixture."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase11_5_network_fixture as fixture


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.subject = fixture.Fixture(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_invocation_has_no_host_access(self):
        with patch.object(sys, 'argv', ['fixture', 'setup', '--root', '/absent']), \
                patch.object(fixture.os, 'geteuid', side_effect=AssertionError('host accessed')), \
                patch.object(fixture.subprocess, 'run', side_effect=AssertionError('command')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            fixture.main()
        self.assertIn('Plan only', output.getvalue())

    def test_foreign_unit_cannot_be_stopped(self):
        self.subject.state = {'token': 'ours'}
        with patch.object(self.subject, 'value', side_effect=['loaded', 'theirs']), \
                patch.object(self.subject, 'cmd') as command:
            with self.assertRaisesRegex(ValueError, 'changed ownership'):
                self.subject.stop_owned('phase115-closure-client.service')
        command.assert_not_called()

    def test_absent_and_owned_units(self):
        self.subject.state = {'token': 'ours'}
        with patch.object(self.subject, 'value', return_value='not-found'), \
                patch.object(self.subject, 'cmd') as command:
            self.subject.stop_owned('phase115-closure-client.service')
        command.assert_not_called()
        with patch.object(self.subject, 'value', side_effect=['loaded', 'ours']), \
                patch.object(self.subject, 'cmd') as command:
            self.subject.stop_owned('phase115-closure-client.service')
        command.assert_called_once_with(['systemctl', 'stop', 'phase115-closure-client.service'])

    def test_no_state_means_no_cleanup_commands(self):
        with patch.object(self.subject, 'cmd') as command:
            self.subject.cleanup()
        command.assert_not_called()

    def test_deadline_prevents_another_command(self):
        self.subject.deadline = 1
        with patch.object(fixture.time, 'monotonic', return_value=2), \
                patch.object(fixture.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'deadline'):
                self.subject.cmd(['nmcli', 'secret-argument'])
        run.assert_not_called()

    def test_command_failure_does_not_expose_credentials(self):
        for failure in (subprocess.CompletedProcess([], 1, 'secret-PSK', 'secret-PSK'),
                        subprocess.TimeoutExpired(['nmcli', 'secret-PSK'], 1)):
            with self.subTest(failure=type(failure).__name__):
                mock = {'side_effect': failure} if isinstance(failure, Exception) else {'return_value': failure}
                with patch.object(fixture.subprocess, 'run', **mock):
                    with self.assertRaises((RuntimeError, TimeoutError)) as raised:
                        self.subject.cmd(['nmcli', 'secret-PSK'])
                self.assertNotIn('secret-PSK', str(raised.exception))
                self.assertNotIn('secret-PSK', (self.root / 'fixture.jsonl').read_text())

    def test_cleanup_is_armed_and_intent_durable_before_first_mutation(self):
        commands = []
        def command(args, **kwargs):
            commands.append(args)
            if args[:2] == ['systemctl', 'stop']:
                state = json.loads(self.subject.state_path.read_text())
                self.assertTrue(state['cleanup_armed'])
                self.assertTrue(state['timer_paused'])
                self.assertEqual(len(commands), 2)
                self.assertEqual(commands[0][0], 'systemd-run')
                self.assertIn('--on-active=21000s', commands[0])
                raise RuntimeError('injected ambiguous timer stop')
            return subprocess.CompletedProcess(args, 0, '', '')
        with patch.object(self.subject, 'preflight', return_value=({'installed_pid': '1957'}, {})), \
                patch.object(self.subject, 'cmd', side_effect=command):
            with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
                self.subject.setup()
        self.assertFalse(self.subject.state.get('ap_profile', False))

    def test_failed_preflight_cannot_arm_or_mutate(self):
        with patch.object(self.subject, 'preflight', side_effect=ValueError('collision')), \
                patch.object(self.subject, 'cmd') as command:
            with self.assertRaisesRegex(ValueError, 'collision'):
                self.subject.setup()
        command.assert_not_called()
        self.assertFalse(self.subject.state_path.exists())

    def test_units_have_durable_ownership_before_launch(self):
        self.subject.state = {'token': 'ours', 'units': []}
        def command(args, **kwargs):
            state = json.loads(self.subject.state_path.read_text())
            self.assertEqual(state['units'], ['phase115-closure-dhcp.service'])
            self.assertIn('--description=ours', args)
            raise TimeoutError('ambiguous start')
        with patch.object(self.subject, 'cmd', side_effect=command):
            with self.assertRaises(TimeoutError):
                self.subject.unit('dhcp', ['dnsmasq'])
        with patch.object(self.subject, 'cmd') as command:
            with self.assertRaises(ValueError):
                self.subject.unit('unlisted', ['some-process'])
        command.assert_not_called()

    def test_namespace_enumeration_failure_still_restores_recovery_timer(self):
        self.subject.state = {'token': 'ours', 'host_boot': fixture.HOST_BOOT,
            'before': {'installed_pid': '1957'}, 'units': [], 'radio': {},
            'namespace': True, 'timer_paused': True, 'cleanup_armed': True}
        def value(*args):
            if args == ('ip', 'netns', 'list'):
                raise RuntimeError('injected namespace listing failure')
            return 'Access denied'
        with patch.object(Path, 'read_text', return_value=fixture.HOST_BOOT), \
                patch.object(self.subject, 'value', side_effect=value), \
                patch.object(self.subject, 'host', return_value={'installed_pid': '1957',
                    'interfaces': '', 'routes': ''}), \
                patch.object(self.subject, 'cmd') as command:
            with self.assertRaisesRegex(ValueError, 'cleanup incomplete'):
                self.subject.cleanup()
        command.assert_any_call(['systemctl', 'start', 'pi-wifi-recover.timer'])
        self.assertFalse(self.subject.state.get('restored', False))


if __name__ == '__main__':
    unittest.main()
