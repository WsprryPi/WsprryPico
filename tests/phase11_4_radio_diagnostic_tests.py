#!/usr/bin/env python3
"""Hardware-free monitor evidence and execution refusal tests."""
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import phase11_4_radio_diagnostic as radio


class RadioTests(unittest.TestCase):
    def capture(self, payload, original=None, link=127):
        header = struct.pack('<IHHIIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, link)
        return header + struct.pack('<IIII', 1, 2, len(payload), len(payload) if original is None else original) + payload

    def decode(self, data, live=False):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'monitor.pcap'; p.write_bytes(data)
            return radio.radio_frames(p, live=live)

    def frame(self, fc=0x80):
        return b'\x00\x00\x08\x00\x00\x00\x00\x00' + struct.pack('<HH', fc, 0) + bytes.fromhex('ffffffffffffe84e06aed709e84e06aed7090000') + bytes(12)

    def test_beacon_identity(self):
        f = self.decode(self.capture(self.frame()))[0]
        self.assertEqual((f['type'], f['subtype']), (0, 8))
        self.assertIn('e8:4e:06:ae:d7:09', f['addresses'])
        self.assertEqual(f['epoch_ns'], 1000002000)

    def test_data_retry_and_protection(self):
        f = self.decode(self.capture(self.frame(0x4808)))[0]
        self.assertTrue(f['retry'] and f['protected'])
        self.assertEqual(f['type'], 2)

    def test_ethernet_not_radio_evidence(self):
        with self.assertRaises(ValueError): self.decode(self.capture(self.frame(), link=1))

    def test_snaplen_truncation_refused(self):
        with self.assertRaises(ValueError): self.decode(self.capture(self.frame(), original=999))

    def test_final_incomplete_record_refused(self):
        with self.assertRaises(ValueError): self.decode(self.capture(self.frame())[:-1])

    def test_live_incomplete_record_not_promoted(self):
        self.assertEqual(self.decode(self.capture(self.frame())[:-1], live=True), [])

    def test_partial_final_header_refused(self):
        with self.assertRaises(ValueError): self.decode(self.capture(self.frame()) + b'\x00')

    def test_bad_fcs_cannot_admit_monitor(self):
        header = struct.pack('<BBHI', 0, 0, 9, 2) + b'\x40'
        self.assertEqual(self.decode(self.capture(header + self.frame()[8:])), [])

    def test_flags_alignment_with_extended_presence_bitmap(self):
        header = struct.pack('<BBHII', 0, 0, 25, 0x80000003, 0) + bytes(12) + b'\x40'
        self.assertEqual(self.decode(self.capture(header + self.frame()[8:])), [])

    def test_malformed_presence_bitmap_refused(self):
        header = struct.pack('<BBHI', 0, 0, 8, 0x80000000)
        with self.assertRaises(ValueError): self.decode(self.capture(header + self.frame()[8:]))

    def test_authentication_transaction_decoded(self):
        frame = self.frame(0xb0)[:32] + struct.pack('<HHH', 0, 1, 0)
        f = self.decode(self.capture(frame))[0]
        self.assertEqual(f['authentication'], {'algorithm': 0, 'transaction': 1, 'status': 0})

    def test_invalid_timestamp_refused(self):
        data = bytearray(self.capture(self.frame()))
        struct.pack_into('<I', data, 28, 1_000_000)
        with self.assertRaises(ValueError): self.decode(data)

    def test_optimized_execution_refused(self):
        p = subprocess.run([sys.executable, '-O', radio.__file__, 'setup', '--root', '/nonexistent', '--run'], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('enabled assertions', p.stderr)

    def test_no_setup_marker_no_host_mutation(self):
        with tempfile.TemporaryDirectory() as d, patch.object(radio.h, 'ROOT', Path(d)), patch.object(radio.h, 'cmd') as cmd:
            radio.cleanup()
            cmd.assert_not_called()

    def test_stale_admission_cannot_reconfigure_pico_after_cleanup(self):
        for marker in ('cleanup-started', 'radio-cleanup-result.json', 'target-restored'):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                for name in ('setup-started', 'monitor-admission.json', marker):
                    (root / name).touch()
                with patch.object(radio.h, 'ROOT', root), patch.object(radio.h, 'cmd') as cmd, patch.object(radio.h, 'console') as console:
                    for action in (radio.run, radio.change):
                        with self.assertRaisesRegex(AssertionError, 'fresh fixture'):
                            action()
                    cmd.assert_not_called()
                    console.assert_not_called()

    def cleanup_case(self, wrong_phy=False):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'setup-started').touch()
            (root / 'management-power.json').write_text('{"value":"on"}')
            net = root / 'sys/class/net'
            (net / 'wlan1').mkdir(parents=True)
            (net / 'wlan1/address').write_text(radio.MANAGEMENT_MAC)
            (net / 'wlan1/phy80211').symlink_to(root / 'phy0')
            if wrong_phy:
                (root / 'monitor-child-created').touch()
                (net / 'radiomon0').mkdir()
                (net / 'radiomon0/phy80211').symlink_to(root / 'phy9')
            def path(value):
                return root / value.lstrip('/') if str(value).startswith('/sys/') else Path(value)
            def command(args, **kwargs):
                return SimpleNamespace(stdout='30 (disconnected)' if 'GENERAL.STATE' in args else '', returncode=0)
            with patch.object(radio.h, 'ROOT', root), patch.object(radio, 'Path', side_effect=path), \
                 patch.object(radio.h, 'cleanup', side_effect=RuntimeError('injected base restore failure')), \
                 patch.object(radio.h, 'cmd', side_effect=command) as cmd, \
                 patch.object(radio, 'BASE_HOST_CHECK', return_value={'management':'Connected to ' + radio.BSSID}):
                with self.assertRaises(AssertionError):
                    radio.cleanup()
                calls = [c.args[0] for c in cmd.call_args_list]
                self.assertIn(['systemctl', 'start', 'pi-wifi-recover.timer'], calls)
                self.assertIn(['systemctl', 'start', 'pi-wifi-recover.service'], calls)
                self.assertIn(['nmcli', '--wait', '25', 'connection', 'up', 'uuid', radio.h.PROFILE, 'ifname', 'wlan1'], calls)
                if wrong_phy:
                    self.assertNotIn(['iw', 'dev', 'radiomon0', 'del'], calls)

    def test_base_cleanup_failure_still_restores_management(self):
        self.cleanup_case()

    def test_foreign_monitor_not_deleted_and_recovery_still_attempted(self):
        self.cleanup_case(wrong_phy=True)


if __name__ == '__main__': unittest.main()
