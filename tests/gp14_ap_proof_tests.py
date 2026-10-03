#!/usr/bin/env python3
"""Hardware-free AP evidence attribution and conservative timing checks."""
import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_gp14_ap_proof as p
import phase12_gp14_rf as rf
import gp14_rf_orchestration_tests as orchestration


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.attempt = dict(case='long_ap', boot_id='boot', final_boot_id='boot',
                            firmware='0.0.0-devel', packet_sha256='packet',
                            target_gesture_checks_passed=True,
                            release_host_bracket=dict(earliest_monotonic_ns='1000000000',
                                                      latest_monotonic_ns='2000000000',
                                                      host_boot_id='host-boot', hostname='host'))
        self.packet = dict(schema='phase12-gp14-rf-v2', device_id=rf.DEVICE,
                           revision='ec0f68facb50')
        info = orchestration.LongApTests().final()
        info.update(device_id=rf.DEVICE, revision=self.packet['revision'], system_clock_hz=138000000,
                    gp14_rf_acceptance=True, gp14_samples='100', recovery_boot=False,
                    gp14_capture_fault=False, core0_stack_guard_valid=1, core1_stack_guard_valid=1,
                    allocator_failures='0', firmware='0.0.0-devel')
        info['status'].update(boot_id='boot', engine='pio-dma-gp2', enabled=False,
                              storage_healthy=True, reboot_required=False)
        for key in ('fault_stage', 'fault_hash', 'fault_pc', 'fault_status', 'provisioning_fault',
                    'core0_stack_fault_status', 'core1_stack_fault_status', 'dma_errors'):
            info[key] = 0
        assoc = dict(interface='wlan1', ssid='approved', bssid='00:11:22:33:44:55')
        self.proof = dict(schema='phase12-gp14-ap-interface-v1', attempt_sha256='attempt',
                          packet_sha256='packet', boot_id='boot', host_boot_id='host-boot',
                          hostname='host', started_monotonic_ns='3000000000',
                          completed_monotonic_ns='90000000000', approved_ap_interface='wlan1',
                          management_interface='eth0', approved_ssid='approved',
                          approved_bssid='00:11:22:33:44:55', association_before=assoc,
                          association_after=copy.deepcopy(assoc),
                          identity=dict(device_id=rf.DEVICE, firmware='0.0.0-devel'),
                          usb_before=dict(begin_monotonic_ns='3000000000',
                                          end_monotonic_ns='4000000000', info=info),
                          usb_after=dict(begin_monotonic_ns='80000000000',
                                         end_monotonic_ns='85000000000', info=copy.deepcopy(info)),
                          http=[dict(path=path, status=200, destination=p.ADDRESS,
                                     bound_interface='wlan1', source='192.168.4.2', size_bytes=1,
                                     begin_monotonic_ns='5000000000', end_monotonic_ns='7000000000')
                                for path in ['/local/v1/identity', '/']],
                          phone_observation='PENDING')

    def validate(self):
        p.validate(self.proof, self.attempt, self.packet, 'attempt', 'packet')

    def test_exact_bound_proof_and_pending_phone(self):
        self.validate()
        self.proof['completed_monotonic_ns'] = '91000000000'
        self.validate()

    def test_expiry_uses_earliest_release_bound_and_same_host_boot(self):
        for key, value in [('completed_monotonic_ns', '91000000001'),
                           ('started_monotonic_ns', '1999999999'),
                           ('host_boot_id', 'rebooted'), ('hostname', 'other-host'),
                           ('completed_monotonic_ns', '1000000000')]:
            with self.subTest(key=key, value=value):
                original = self.proof[key]; self.proof[key] = value
                with self.assertRaises(RuntimeError): self.validate()
                self.proof[key] = original

    def test_firmware_device_run_and_interface_binding_refuse(self):
        for key, value in [('boot_id', 'other'), ('attempt_sha256', 'other'),
                           ('packet_sha256', 'other'), ('management_interface', 'wlan1'),
                           ('phone_observation', 'PASS')]:
            original = self.proof[key]; self.proof[key] = value
            with self.assertRaises(RuntimeError): self.validate()
            self.proof[key] = original
        for key in ('device_id', 'firmware'):
            original = self.proof['identity'][key]; self.proof['identity'][key] = 'other'
            with self.assertRaises(RuntimeError): self.validate()
            self.proof['identity'][key] = original

    def test_station_page_redirect_or_changed_association_is_not_ap_proof(self):
        for key, value in [('destination', '192.168.1.53'), ('source', '192.168.1.2'),
                           ('source', p.ADDRESS), ('bound_interface', 'eth0'),
                           ('status', 302), ('size_bytes', 0)]:
            original = self.proof['http'][0][key]; self.proof['http'][0][key] = value
            with self.assertRaises(RuntimeError): self.validate()
            self.proof['http'][0][key] = original
        self.proof['association_after']['bssid'] = 'ff:ff:ff:ff:ff:ff'
        with self.assertRaises(RuntimeError): self.validate()

    def test_usb_same_boot_health_and_latch_must_bracket_collection(self):
        for key in ('usb_before', 'usb_after'):
            original = copy.deepcopy(self.proof[key])
            for field, value in [('boot_id', 'other'), ('output_active', True),
                                 ('storage_healthy', False), ('reboot_required', True)]:
                self.proof[key]['info']['status'][field] = value
                with self.assertRaises(RuntimeError): self.validate()
                self.proof[key] = copy.deepcopy(original)
            self.proof[key]['info']['gp14_ap_events'] = 2
            with self.assertRaises(RuntimeError): self.validate()
            self.proof[key] = copy.deepcopy(original)
            self.proof[key]['end_monotonic_ns'] = '999000000000'
            with self.assertRaises(RuntimeError): self.validate()
            self.proof[key] = original

    def test_iw_requires_expected_ssid_bssid_and_connection(self):
        output = 'Connected to 00:11:22:33:44:55 (on wlan1)\n\tSSID: approved\n'
        self.assertEqual(p.association(output, 'approved', '00:11:22:33:44:55')['interface'], 'wlan1')
        for changed in ('Not connected.\n', output.replace('approved', 'other'),
                        output.replace('00:11:22:33:44:55', 'ff:ff:ff:ff:ff:ff')):
            with self.assertRaises(RuntimeError):
                p.association(changed, 'approved', '00:11:22:33:44:55')

    def test_expired_collection_refuses_before_network_or_iw(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'attempt.json').write_text(json.dumps(self.attempt))
            (root/'packet.json').write_text(json.dumps(self.packet))
            with patch.object(p, 'validate_packet'), \
                    patch.object(p.Path, 'read_text', side_effect=[json.dumps(self.attempt),
                                                                 json.dumps(self.packet), 'host-boot']), \
                    patch.object(p.socket, 'gethostname', return_value='host'), \
                    patch.object(p.time, 'monotonic_ns', return_value=91_000_000_001), \
                    patch.object(p.socket, 'socket') as sock, \
                    patch.object(p, 'console') as usb, \
                    patch.object(p.subprocess, 'run') as iw:
                with self.assertRaises(RuntimeError):
                    p.collect(root, 'wlan1', 'eth0', 'approved', '00:11:22:33:44:55')
            sock.assert_not_called(); iw.assert_not_called(); usb.assert_not_called()
            self.assertFalse((root/'ap-interface-proof.json').exists())

    def test_cli_requires_run_before_collection(self):
        with patch.object(sys, 'argv', ['collector', '/unavailable']), \
                patch.object(p, 'collect') as collector:
            with self.assertRaises(SystemExit): p.main()
        collector.assert_not_called()

    def test_concurrent_collector_and_existing_proof_refuse_before_hardware(self):
        with TemporaryDirectory() as tmp:
            campaign = Path(tmp); root = campaign/'run-example'; root.mkdir()
            with patch.object(p, '_collect_locked') as locked:
                with rf.campaign_lock(campaign):
                    with self.assertRaises(BlockingIOError):
                        p.collect(root, 'wlan1', 'eth0', 'approved', '00:11:22:33:44:55')
                locked.assert_not_called()
                (root/'ap-interface-proof.json').write_text('{}')
                with self.assertRaises(RuntimeError):
                    p.collect(root, 'wlan1', 'eth0', 'approved', '00:11:22:33:44:55')
                locked.assert_not_called()

    def test_collector_creates_private_artifact_and_restores_umask_on_failure(self):
        with TemporaryDirectory() as tmp:
            campaign = Path(tmp); root = campaign/'run-example'; root.mkdir()
            with patch.object(p.os, 'umask', side_effect=[0o022, 0o077]) as mask, \
                    patch.object(p, '_collect_locked', side_effect=RuntimeError('failed')):
                with self.assertRaises(RuntimeError):
                    p.collect(root, 'wlan1', 'eth0', 'approved', '00:11:22:33:44:55')
                self.assertEqual([call.args[0] for call in mask.call_args_list], [0o077, 0o022])

    def test_http_binding_failure_never_falls_back_to_default_route(self):
        sock = Mock(); sock.setsockopt.side_effect = PermissionError('bind denied')
        with patch.object(p.time, 'monotonic_ns', return_value=1), \
                patch.object(p.socket, 'socket', return_value=sock), \
                patch.object(p.socket, 'SO_BINDTODEVICE', 25, create=True):
            with self.assertRaises(PermissionError): p.http_get('wlan1', '/', 1000000000)
        sock.connect.assert_not_called(); sock.sendall.assert_not_called(); sock.close.assert_called_once()

    def test_http_sends_get_through_bound_socket_and_rejects_redirect(self):
        sock = Mock(); sock.getsockname.return_value = ('192.168.4.2', 12345)
        response = Mock(); response.status = 302; response.getheader.return_value = p.ADDRESS
        with patch.object(p.time, 'monotonic_ns', return_value=1), \
                patch.object(p.socket, 'socket', return_value=sock), \
                patch.object(p.socket, 'SO_BINDTODEVICE', 25, create=True), \
                patch.object(p.http.client, 'HTTPResponse', return_value=response):
            with self.assertRaises(RuntimeError): p.http_get('wlan1', '/local/v1/identity', 1000000000)
        sock.setsockopt.assert_called_once_with(p.socket.SOL_SOCKET, 25, b'wlan1\0')
        sock.connect.assert_called_once_with((p.ADDRESS, 80))
        self.assertTrue(sock.sendall.call_args.args[0].startswith(b'GET /local/v1/identity '))
        response.read.assert_not_called(); sock.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
