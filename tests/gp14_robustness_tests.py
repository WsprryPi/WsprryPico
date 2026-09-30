#!/usr/bin/env python3
"""Hardware-free negative cases for diagnostic evidence and image boundaries."""
from pathlib import Path
import json
import struct
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import gp14_robustness_campaign as campaign
from check_standalone_image import validate_uf2
from check_gp14_robustness_image import validate as validate_image
from check_gp14_flash_probe_image import validate as validate_flash_probe
from gp14_flash_overlap import bound_overlap


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(image='gp14-robustness', serial='CDDBF8767C506C07',
            revision='0123456789ab', started=1, synthetic=1, rf_output=0, clock_hz=150_000_000, settings_now=123,
            settings_before=123, samples=1000, reads0=100, reads1=200, boot_id=1,
            action='IDLE', active=0, sequence=0, prior_action=0, prior_sequence=0, prior_watchdog=0,
            prior_fault=0, fault_code=0, capture_fault=0, held=0, releases=0,
            stops=0, aps=0, would_reset=0, duration_us=0, blocks=0)

    def test_identity_fails_closed(self):
        campaign.identity(self.row, self.row['serial'], self.row['revision'])
        for key, value in (('image', 'WsprryPico'), ('revision', 'old'),
                           ('serial', '0BF4B4AEC9FFB344'), ('started', 0), ('clock_hz', 1)):
            bad = self.row | {key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                campaign.identity(bad, self.row['serial'], self.row['revision'])

    def test_incomplete_telemetry_fails_closed(self):
        row = dict.fromkeys(campaign.INTEGER_FIELDS, 0) | self.row | {'result': 'status'}
        decode = lambda v: campaign.decode_record(json.dumps(v), row['serial'], row['revision'])
        self.assertEqual(decode(row), row)
        # Observed target failure: a dropped middle chunk left valid JSON with
        # merged sample digits and missing core/policy fields. Never retry or
        # silently accept a later status as proof of the missing interval.
        for key in row:
            bad = row.copy()
            del bad[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                decode(bad)
        for value in (-1, True, '123', None, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                decode(row | {'samples': value})
        with self.assertRaises(ValueError):
            decode([])

    def test_bad_results_cannot_pass(self):
        after = self.row | dict(action='SHORT', sequence=1, releases=1, would_reset=1, duration_us=200_000)
        campaign.outcome('SHORT', self.row, after)
        for key, value in (('active', 1), ('boot_id', 2), ('duration_us', 600_000),
                           ('releases', 0), ('held', 1), ('stops', 1), ('fault_code', 9)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                campaign.outcome('SHORT', self.row, after | {key: value})

    def test_fault_and_reset_evidence(self):
        for action, code in campaign.FAULT_CODES.items():
            campaign.outcome(action, self.row, self.row | dict(action=action, sequence=1, capture_fault=1, fault_code=code))
            with self.assertRaises(ValueError):
                campaign.outcome(action, self.row, self.row)
        reset = self.row | dict(boot_id=2, prior_action=10, prior_sequence=1,
                                prior_watchdog=1)
        campaign.outcome('WATCHDOG', self.row, reset)
        for key, value in (('boot_id', 1), ('prior_action', 9), ('prior_sequence', 2),
                           ('prior_watchdog', 0), ('prior_fault', 1)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                campaign.outcome('WATCHDOG', self.row, reset | {key: value})

    def test_continuity(self):
        after = self.row | dict(samples=2000, reads0=200, reads1=300)
        campaign.continuity(self.row, after)
        for key in ('samples', 'reads0', 'reads1'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                campaign.continuity(self.row, after | {key: self.row[key]})
        with self.assertRaises(ValueError):
            campaign.continuity(self.row, after | {'settings_now': 999})
        with self.assertRaises(ValueError):
            campaign.continuity(self.row, after | {'boot_id': 2, 'settings_before': 999})

    def test_inert_cli(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/gp14_robustness_campaign.py')],
                                capture_output=True, text=True, check=True)
        self.assertIn('"device_io": false', result.stdout)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/gp14_robustness_campaign.py'),
                                 '--run'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)

    def test_link_checker_rejects_unsafe_topology(self):
        entries = [
            (0x10000100, 32, 'main'), (0x10000200, 32, 'robustness_core1'),
            (0x10000300, 32, 'robustness_flash_probe'),
            (0x10001000, 32768, 'robustness_flash_words'),
            (0x20000100, 64, 'robustness_flash_write'),
            (0x20000200, 32, 'robustness_hardfault'),
            (0x20000300, 32, 'flash_range_erase'),
            (0x20000400, 32, 'flash_range_program'),
            (0x20000500, 32, 'multicore_lockout_handler')]
        symbols = '\n'.join(f'{a:08x} {size:08x} T {name}' for a, size, name in entries)
        code = ''
        for address, _, name in entries:
            body = '  bx lr\n'
            if name in ('main', 'robustness_core1'):
                body = '  bl 10000300 <robustness_flash_probe>\n'
            if name == 'robustness_flash_write':
                body = '  bl 20000300 <flash_range_erase>\n  .word\t0x003f2000\n'
            code += f'{address:08x} <{name}>:\n{body}'
        memory = 'FLASH 0x10000000 0x003f2000 xr'
        uf2 = bytearray(512)
        struct.pack_into('<5I', uf2, 0, 0x0A324655, 0x9E5D5157, 0, 0x10000000, 256)
        struct.pack_into('<I', uf2, 508, 0x0AB16F30)
        validate_image(symbols, code, memory, bytes(uf2))
        for bad in (code.replace('bl 20000300', 'bl 10000300'),
                    code.replace('0x003f2000', '0x003f3000'),
                    code.replace('bl 20000300', 'blx r3 ; 20000300')):
            with self.assertRaises(ValueError):
                validate_image(symbols, bad, memory, bytes(uf2))
        with self.assertRaises(ValueError):
            validate_image(symbols + '\n10009000 00000020 T WorkerEngine', code, memory, bytes(uf2))

    def test_scratch_is_excluded_from_uf2(self):
        def block(address):
            buf = bytearray(512)
            struct.pack_into('<5I', buf, 0, 0x0A324655, 0x9E5D5157, 0, address, 256)
            struct.pack_into('<I', buf, 508, 0x0AB16F30)
            return bytes(buf)
        validate_uf2(block(0x103F1F00), 0x103F2000)
        for address in (0x103F2000, 0x103F3000, 0x103F5000, 0x103FF000):
            with self.subTest(address=address), self.assertRaises(ValueError):
                validate_uf2(block(address), 0x103F2000)

    def test_runtime_flash_probe_rejects_unsafe_image(self):
        symbols = ('20000100 00000080 T gp14_probe_flash_write\n'
                   '20000200 00000040 T flash_range_erase\n'
                   '20000300 00000040 T flash_range_program\n')
        code = ('20000100 <gp14_probe_flash_write>:\n'
                '  bl 20000200 <flash_range_erase>\n'
                '  bl 20000300 <flash_range_program>\n'
                '  .word\t0x003f2000\n')
        memory = 'FLASH 0x10000000 0x003f2000 xr'
        uf2 = bytearray(512)
        struct.pack_into('<5I',uf2,0,0x0A324655,0x9E5D5157,0,0x10000000,256)
        struct.pack_into('<I',uf2,508,0x0AB16F30)
        validate_flash_probe(symbols,code,memory,bytes(uf2))
        # The normal runtime also has XIP-to-RAM veneers. Only the actual SDK
        # routine may satisfy the RAM callback dependency check.
        validate_flash_probe(symbols+'10001000 00000008 T __flash_range_erase_veneer\n',
                             code,memory,bytes(uf2))
        for bad in (code.replace('bl 20000200','bl 10000200'),
                    code.replace('0x003f2000','0x003f3000'),
                    code+'  blx r3\n',code+'  .word\t0x10009000\n'):
            with self.assertRaises(ValueError):
                validate_flash_probe(symbols,bad,memory,bytes(uf2))
        with self.assertRaises(ValueError):
            validate_flash_probe(symbols,code,memory.replace('3f2000','3f3000'),bytes(uf2))
        with self.assertRaises(ValueError):
            validate_flash_probe(symbols+'20005000 00000010 T sample_override\n',code,memory,bytes(uf2))

    def test_real_gesture_with_equal_callback_endpoint_levels(self):
        result = bound_overlap(142208, 142226881, 142378245, 144378245,
                               144586718, 1340000)
        self.assertTrue(result['at_least_one_edge_inside_callback'])
        self.assertEqual(result['minimum_gesture_overlap_us'], 950282)

    def test_outside_and_surrounding_gestures_do_not_prove_an_edge(self):
        # Earliest raw start is zero; before/after gaps are 100 ms each.
        for duration in (1, 100000, 2000000, 2100000, 2200000):
            with self.subTest(duration=duration):
                result = bound_overlap(1, 0, 100000, 2100000, 2200000, duration)
                self.assertFalse(result['at_least_one_edge_inside_callback'])

    def test_overlap_claim_is_sound_for_every_possible_placement(self):
        # Exhaust possible placements independently of the bound calculation.
        for duration in range(10000, 2200001, 10000):
            result = bound_overlap(1, 0, 100000, 2100000, 2200000, duration)
            if not result['at_least_one_edge_inside_callback']:
                continue
            for start in range(0, 2200000-duration+1, 10000):
                self.assertTrue(100000 < start < 2100000 or
                                100000 < start+duration < 2100000)

    def test_overlap_rejects_bad_or_incomplete_timing(self):
        good = (142208, 142226881, 142378245, 144378245, 144586718, 1340000)
        for index in range(len(good)):
            for value in (-1, True, None, '1'):
                bad = list(good)
                bad[index] = value
                with self.subTest(index=index, value=value), self.assertRaises(ValueError):
                    bound_overlap(*bad)
        for bad in ((0, *good[1:]), good[:-1]+(0,), good[:-1]+(3000000,),
                    (11, 0, 100000, 2100000, 2200000, 1340000),
                    (142208, 1, *good[2:]),
                    (*good[:3], good[2], *good[4:])):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                bound_overlap(*bad)


if __name__ == '__main__':
    unittest.main()
