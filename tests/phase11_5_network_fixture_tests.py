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
    def test_join_capture_is_ready_before_ap_activation(self):
        from phase11_5_join_diagnostics import POLICY, CAPTURE_FILTER
        p=dict(schema='phase11.5-r3-retained-fixture-v1',family='R3',configuration_writes=0,
               network_join_diagnostics=POLICY,network_runtime_seconds=1800)
        (self.root/'packet.json').write_text(json.dumps(p))
        actions=[]
        def unit(label,args):
            actions.append(('capture',label,args))
            (self.root/'capture-ap.pcap').write_bytes(b'capture header')
        def command(args,**kwargs):
            actions.append(('command',args))
            if args[:6]==['nmcli','--wait','25','connection','up',fixture.PROFILE]:
                self.assertTrue(self.subject.state['cleanup_armed'])
                self.assertTrue((self.root/'capture-ap.pcap').exists())
                self.assertTrue(any(a[0]=='capture' and a[1]=='capture-ap' and a[2][-1]==CAPTURE_FILTER for a in actions))
                raise RuntimeError('stop before AP activation')
            return subprocess.CompletedProcess(args,0,'active\n' if list(args[:2])==['systemctl','is-active'] else '','')
        with patch.object(self.subject,'preflight',return_value=({'installed_pid':'1957'},{})), \
             patch.object(self.subject,'cmd',side_effect=command),patch.object(self.subject,'unit',side_effect=unit):
            with self.assertRaisesRegex(RuntimeError,'before AP activation'):self.subject.setup()

    def test_dead_diagnostic_capture_is_rejected(self):
        with patch.object(self.subject, 'value', return_value='inactive'):
            with self.assertRaisesRegex(ValueError, 'capture is not active'):
                self.subject.verify_join_capture()

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
        (self.root / 'packet.json').write_text('{}')
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

    def test_continuation_cannot_extend_original_window(self):
        for packet in ({'network_runtime_seconds':21001},
                       {'network_runtime_seconds':True},
                       {'network_runtime_seconds':18000,'absolute_host_deadline_monotonic_ns':100}):
            (self.root/'packet.json').write_text(json.dumps(packet))
            with patch.object(self.subject,'preflight',return_value=({},{})), \
                 patch.object(self.subject,'cmd') as command:
                with self.assertRaises(ValueError):self.subject.setup()
                command.assert_not_called()
                self.assertFalse(self.subject.state_path.exists())

    def test_shorter_runtime_reaches_the_independent_cleanup_timer(self):
        (self.root/'packet.json').write_text(json.dumps({'network_runtime_seconds':18900}))
        with patch.object(self.subject,'preflight',return_value=({},{})), \
             patch.object(self.subject,'cmd',side_effect=RuntimeError('stop before mutation')) as command:
            with self.assertRaises(RuntimeError):self.subject.setup()
            self.assertIn('--on-active=18900s',command.call_args.args[0])
            self.assertEqual(self.subject.state['runtime_seconds'],18900)

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

    def test_network_manager_convergence_does_not_replay_mutations(self):
        with patch.object(fixture.time, 'monotonic', side_effect=[0,1,2]), \
                patch.object(fixture.time, 'sleep') as sleep, \
                patch.object(self.subject, 'cmd') as command:
            observations = iter([False,False,True])
            self.subject.settle(lambda: next(observations), 'not restored')
        self.assertEqual(sleep.call_count,2)
        command.assert_not_called()

    def test_failed_convergence_has_a_deadline(self):
        with patch.object(fixture.time, 'monotonic', side_effect=[0,21]), \
                patch.object(fixture.time, 'sleep') as sleep:
            with self.assertRaisesRegex(ValueError,'not restored'):
                self.subject.settle(lambda: False, 'not restored')
        sleep.assert_not_called()

    def test_dns_requires_opt_in_and_has_no_upstream_or_lan_route(self):
        for enabled in (False,True):
            with self.subTest(enabled=enabled),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);(root/'packet.json').write_text(json.dumps({'time_server_dns':enabled}))
                subject=fixture.Fixture(root)
                with patch.object(subject,'preflight',return_value=({'installed_pid':'1957'},{})), \
                     patch.object(subject,'cmd',return_value=subprocess.CompletedProcess([],0,'','')), \
                     patch.object(subject,'unit',side_effect=RuntimeError('stop before daemon activation')):
                    with self.assertRaisesRegex(RuntimeError,'before daemon'):subject.setup()
                lines=(root/'dnsmasq.conf').read_text().splitlines()
                wifi=json.loads((root/'pico-wifi.json').read_text())
                self.assertIn('dhcp-option=3',lines)
                if enabled:
                    self.assertIn('port=53',lines)
                    self.assertIn('dhcp-option=6,10.77.15.1',lines)
                    self.assertIn('no-hosts',lines);self.assertIn('no-resolv',lines)
                    self.assertIn('except-interface=lo',lines)
                    self.assertIn('address=/clock.phase115.test/10.77.15.1',lines)
                    self.assertEqual(wifi['ntp_ipv4'],'clock.phase115.test')
                else:
                    self.assertIn('port=0',lines);self.assertIn('dhcp-option=6',lines)
                    self.assertNotIn('no-resolv',lines)
                    self.assertEqual(wifi['ntp_ipv4'],'10.77.15.1')

    def test_dns_flag_must_be_boolean_before_first_mutation(self):
        (self.root/'packet.json').write_text('{"time_server_dns":"yes"}')
        with patch.object(self.subject,'preflight',return_value=({},{})), \
             patch.object(self.subject,'cmd') as command:
            with self.assertRaises(ValueError):self.subject.setup()
            command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
