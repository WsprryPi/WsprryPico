#!/usr/bin/env python3
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from phase11_5_device_fixture import DeviceFixture, journal_config


def record(sequence, value):
    data = json.dumps(value).encode()
    result = bytearray(b'\xff'*2048)
    struct.pack_into('<QQI', result, 0, 0x32524f5453505757, sequence, len(data))
    result[32:32+len(data)] = data
    struct.pack_into('<I', result, 2044, zlib.crc32(result[:-4]))
    return result


def backup(records):
    result = bytearray(b'\xff'*0x400000)
    for i, value in enumerate(records): result[0x3fb000+i*2048:0x3fb000+(i+1)*2048] = value
    return result


class FixtureTests(unittest.TestCase):
    def test_journal_selection(self):
        self.assertEqual(journal_config(backup([record(30,{'enabled':True}),
            record(31,{'enabled':False})])), (31,{'enabled':False}))

    def test_corrupt_newer_cannot_resurrect_old(self):
        newer = record(31,{'enabled':False});newer[90] ^= 1
        with self.assertRaises(ValueError):
            journal_config(backup([record(30,{'enabled':True}),newer]))

    def test_magic_and_sequence(self):
        for offset, value in ((0,0),(8,0)):
            bad = record(1,{'enabled':False});struct.pack_into('<Q',bad,offset,value)
            struct.pack_into('<I',bad,2044,zlib.crc32(bad[:-4]))
            with self.assertRaises(ValueError): journal_config(backup([bad]))
        with self.assertRaises(ValueError):
            journal_config(backup([record(31,{}),record(31,{})]))
        with self.assertRaises(ValueError): journal_config(backup([]))

    def test_restore_never_mutates_after_failed_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = DeviceFixture(Path(directory));fixture.state={'kind':'physical'}
            with patch.object(fixture,'verify_helpers'), \
                 patch.object(fixture,'check_current',side_effect=ValueError('unexpected boot')), \
                 patch.object(fixture,'manage') as manage, patch.object(fixture,'flash') as flash:
                with self.assertRaises(ValueError): fixture.restore()
                manage.assert_not_called();flash.assert_not_called()

    def test_pending_transition_blocks_before_usb(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = DeviceFixture(Path(directory));fixture.state={'pending':'BOOTSEL'}
            with patch.object(fixture,'inventory') as inventory:
                with self.assertRaises(ValueError): fixture.check_current('unexpected')
                inventory.assert_not_called()

    def test_guard_failure_blocks_switch_before_flash(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = DeviceFixture(Path(directory));fixture.state={'kind':'inhibited',
                'deadline_monotonic_ns':2**63}
            with patch.object(fixture,'verify_helpers'), \
                 patch.object(fixture,'check_current',side_effect=ValueError('guard invalid')), \
                 patch.object(fixture,'flash') as flash:
                with self.assertRaises(ValueError): fixture.switch()
                flash.assert_not_called()

    def test_no_run_performs_no_io(self):
        from phase11_5_device_fixture import main
        with patch.object(sys,'argv',['fixture','start','--root','/does-not-exist']), \
             patch.object(DeviceFixture,'start') as start:
            main();start.assert_not_called()


if __name__ == '__main__': unittest.main()
