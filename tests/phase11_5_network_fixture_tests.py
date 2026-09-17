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
             patch.object(self.subject,'rebind_sdio_radio'), \
             patch.object(self.subject,'rebind_usb_radio'), \
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

    def test_package7_runtime_is_bounded_and_authorized(self):
        packet = dict(schema='phase11.5-package7-fixture-v1', family='R4',
                      configuration_writes=0,
                      standing_authority='PHASE11.5-COMPLETION-20260915',
                      network_runtime_seconds=7200,
                      network_restoration_seconds=900)
        self.assertEqual(fixture.runtime_budget(packet), (7200, 900))
        for key, value in (('network_runtime_seconds', 7201),
                           ('network_restoration_seconds', 901),
                           ('configuration_writes', 1),
                           ('family', 'R3'),
                           ('standing_authority', 'wrong')):
            altered = dict(packet)
            altered[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                fixture.runtime_budget(altered)

    def test_package8_runtime_and_write_count_are_bounded(self):
        packet = dict(schema='phase11.5-package8-fixture-v1', family='R5',
                      configuration_writes=2,
                      standing_authority='PHASE11.5-COMPLETION-20260915',
                      network_runtime_seconds=7200,
                      network_restoration_seconds=900)
        self.assertEqual(fixture.runtime_budget(packet), (7200, 900))
        for key, value in (('network_runtime_seconds', 7201),
                           ('network_restoration_seconds', 901),
                           ('configuration_writes', 0),
                           ('configuration_writes', 4),
                           ('family', 'R4'),
                           ('standing_authority', 'wrong')):
            altered = dict(packet)
            altered[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                fixture.runtime_budget(altered)

    def test_package9_runtime_is_bounded_and_read_only(self):
        packet = dict(schema='phase11.5-package9-fixture-v1', family='R6',
                      configuration_writes=0,
                      standing_authority='PHASE11.5-COMPLETION-20260915',
                      network_runtime_seconds=5400,
                      network_restoration_seconds=900)
        self.assertEqual(fixture.runtime_budget(packet), (5400, 900))
        for key, value in (('network_runtime_seconds', 5401),
                           ('network_restoration_seconds', 901),
                           ('configuration_writes', 1),
                           ('family', 'R5'),
                           ('standing_authority', 'wrong')):
            altered = dict(packet)
            altered[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                fixture.runtime_budget(altered)

    def test_package10_runtime_is_bounded_to_authorized_packet(self):
        packet = dict(schema='phase11.5-package10-fixture-v1', family='R6',
                      configuration_writes=0, authorization='PACKAGE10-480-RF-SECONDS',
                      rf_jobs=16, rf_duration_ns=356800000000,
                      network_runtime_seconds=5400, network_restoration_seconds=900)
        self.assertEqual(fixture.runtime_budget(packet), (5400, 900))
        for key, value in (('network_runtime_seconds', 5401),
                           ('network_restoration_seconds', 901),
                           ('configuration_writes', 1), ('family', 'R5'),
                           ('authorization', 'wrong'), ('rf_jobs', 17),
                           ('rf_duration_ns', 356800000001)):
            altered = dict(packet)
            altered[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                fixture.runtime_budget(altered)

    def test_package10_v2_charges_stopped_attempt_inside_same_authorization(self):
        packet = dict(schema='phase11.5-package10-fixture-v2', family='R6',
                      configuration_writes=0, authorization='PACKAGE10-480-RF-SECONDS',
                      rf_jobs=16, rf_duration_ns=356800000000,
                      cumulative_rf_jobs=20, cumulative_rf_duration_ns=360800000000,
                      network_runtime_seconds=5400, network_restoration_seconds=900)
        self.assertEqual(fixture.runtime_budget(packet), (5400, 900))
        for key, value in (('cumulative_rf_jobs', 19),
                           ('cumulative_rf_duration_ns', 360799999999),
                           ('authorization', 'wrong')):
            altered = dict(packet)
            altered[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                fixture.runtime_budget(altered)

    def test_service_restoration_accepts_a_new_active_pid(self):
        self.assertIsNone(fixture.service_activity_restored('1957', '861234'))
        for before, after in (('0', '861234'), ('1957', '0'), ('bad', '861234')):
            with self.subTest(before=before, after=after), self.assertRaises(ValueError):
                fixture.service_activity_restored(before, after)

    def test_client_join_is_constrained_to_qualified_ap(self):
        value = fixture.client_wpa_config('test-ssid', 'a' * 32, qualified=True)
        self.assertIn('bssid=' + fixture.RADIOS[fixture.AP_IF] + '\n', value)
        self.assertIn('scan_freq=2462\n', value)
        self.assertIn('ssid="test-ssid"\n', value)

    def test_client_join_binding_is_package10_only(self):
        value = fixture.client_wpa_config('test-ssid', 'a' * 32)
        self.assertNotIn('bssid=', value)
        self.assertNotIn('scan_freq=', value)
        self.assertTrue(fixture.package10_fixture(
            {'schema': 'phase11.5-package10-fixture-v2'}))
        self.assertFalse(fixture.package10_fixture(
            {'schema': 'phase11.5-package9-fixture-v1'}))

    def test_usb_radio_rebind_requires_exact_driver(self):
        sysfs = self.root / 'usb'
        driver = sysfs / 'drivers' / fixture.CLIENT_USB_DRIVER
        device = sysfs / 'devices' / fixture.CLIENT_USB_DEVICE
        driver.mkdir(parents=True)
        device.mkdir(parents=True)
        (driver / 'unbind').write_text('')
        (driver / 'bind').write_text('')
        (device / 'driver').symlink_to(driver, target_is_directory=True)
        net = self.root / 'net' / 'wlan2'
        net.mkdir(parents=True)
        (net / 'address').write_text(fixture.RADIOS['wlan2'])
        with patch.object(fixture, 'USB_SYSFS', sysfs), \
                patch.object(fixture, 'NET_SYSFS', self.root / 'net'), \
                patch.object(fixture.time, 'sleep'), \
                patch.object(self.subject, 'note') as note:
            self.subject.rebind_usb_radio()
        self.assertEqual((driver / 'unbind').read_text(), fixture.CLIENT_USB_DEVICE)
        self.assertEqual((driver / 'bind').read_text(), fixture.CLIENT_USB_DEVICE)
        note.assert_called_once()

    def test_sdio_radio_rebind_owns_both_functions(self):
        sysfs = self.root / 'sdio'
        driver = sysfs / 'drivers' / fixture.AP_SDIO_DRIVER
        driver.mkdir(parents=True)
        (driver / 'unbind').write_text('')
        (driver / 'bind').write_text('')
        for name in fixture.AP_SDIO_DEVICES:
            device = sysfs / 'devices' / name
            device.mkdir(parents=True)
            (device / 'driver').symlink_to(driver, target_is_directory=True)
        net = self.root / 'net' / 'wlan0'
        net.mkdir(parents=True)
        (net / 'address').write_text(fixture.RADIOS['wlan0'])
        with patch.object(fixture, 'SDIO_SYSFS', sysfs), \
                patch.object(fixture, 'NET_SYSFS', self.root / 'net'), \
                patch.object(fixture.time, 'sleep'), \
                patch.object(self.subject, 'note') as note:
            self.subject.rebind_sdio_radio()
        self.assertEqual((driver / 'unbind').read_text(), fixture.AP_SDIO_DEVICES[0])
        self.assertEqual((driver / 'bind').read_text(), fixture.AP_SDIO_DEVICES[-1])
        note.assert_called_once()

    def test_package7_retained_wifi_is_read_only(self):
        raw = json.dumps(dict(ssid='WsprryPico-Phase115', password='a' * 32,
                              ntp_ipv4='time.local')).encode()
        (self.root / 'retained-wifi.json').write_bytes(raw)
        packet = dict(schema='phase11.5-package7-fixture-v1', family='R4',
                      configuration_writes=0,
                      standing_authority='PHASE11.5-COMPLETION-20260915',
                      retained_wifi_sha256=__import__('hashlib').sha256(raw).hexdigest())
        self.assertEqual(fixture.fixture_wifi(self.root, packet, True, False),
                         json.loads(raw))
        packet['configuration_writes'] = 1
        with self.assertRaises(ValueError):
            fixture.fixture_wifi(self.root, packet, True, False)

    def test_package8_retained_wifi_allows_only_frozen_minimal_writes(self):
        raw = json.dumps(dict(ssid='WsprryPico-Phase115', password='a' * 32,
                              ntp_ipv4='time.local')).encode()
        (self.root / 'retained-wifi.json').write_bytes(raw)
        packet = dict(schema='phase11.5-package8-fixture-v1', family='R5',
                      configuration_writes=3,
                      standing_authority='PHASE11.5-COMPLETION-20260915',
                      retained_wifi_sha256=__import__('hashlib').sha256(raw).hexdigest())
        self.assertEqual(fixture.fixture_wifi(self.root, packet, True, False),
                         json.loads(raw))
        for writes in (0, 1, 4):
            packet['configuration_writes'] = writes
            with self.subTest(writes=writes), self.assertRaises(ValueError):
                fixture.fixture_wifi(self.root, packet, True, False)

    def test_package9_retained_wifi_is_read_only(self):
        raw = json.dumps(dict(ssid='WsprryPico-Phase115', password='a' * 32,
                              ntp_ipv4='time.local')).encode()
        (self.root / 'retained-wifi.json').write_bytes(raw)
        packet = dict(schema='phase11.5-package9-fixture-v1', family='R6',
                      configuration_writes=0,
                      standing_authority='PHASE11.5-COMPLETION-20260915',
                      retained_wifi_sha256=__import__('hashlib').sha256(raw).hexdigest())
        self.assertEqual(fixture.fixture_wifi(self.root, packet, True, False),
                         json.loads(raw))
        packet['configuration_writes'] = 1
        with self.assertRaises(ValueError):
            fixture.fixture_wifi(self.root, packet, True, False)

    def test_package10_retained_wifi_is_read_only(self):
        raw = json.dumps(dict(ssid='WsprryPico-Phase115', password='a' * 32,
                              ntp_ipv4='time.local')).encode()
        (self.root / 'retained-wifi.json').write_bytes(raw)
        packet = dict(schema='phase11.5-package10-fixture-v2', family='R6',
                      configuration_writes=0, authorization='PACKAGE10-480-RF-SECONDS',
                      retained_wifi_sha256=__import__('hashlib').sha256(raw).hexdigest())
        self.assertEqual(fixture.fixture_wifi(self.root, packet, True, False),
                         json.loads(raw))
        packet['configuration_writes'] = 1
        with self.assertRaises(ValueError):
            fixture.fixture_wifi(self.root, packet, True, False)

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
                     patch.object(subject,'rebind_sdio_radio'), \
                     patch.object(subject,'rebind_usb_radio'), \
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
