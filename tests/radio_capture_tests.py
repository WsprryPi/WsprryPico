#!/usr/bin/env python3
"""Synthetic radiotap packet decoding and corruption tests."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import radio_capture as radio


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


if __name__ == '__main__':
    unittest.main()
