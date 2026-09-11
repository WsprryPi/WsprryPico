#!/usr/bin/env python3
"""Restoration decisions and preimage verification without device operations."""
import copy
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase11_5_pilot_supervisor import restoration_admitted, verify_application_backup


def inventory(boot, revision, engine):
    return dict(wtp=dict(STATUS=dict(state="empty", output_active=False, owner_id=None,
                                     job_id=None, boot_id=boot)),
                info=dict(revision=revision, system_clock_hz=138000000, recovery_boot=False,
                          status=dict(state="empty", output_active=False, enabled=False,
                                      last_error=None, storage_healthy=True, configured=True,
                                      engine=engine, station={}, schedules=[], watermark_utc_ns="0"),
                          network=dict(station_mac="00:00:00:00:00:00",
                                       configured_hostname="synthetic.local", control_configured=True)))


class SupervisorTests(unittest.TestCase):
    def fixtures(self):
        before_a = inventory("a" * 32, "original", "inhibited-standalone-simulator")
        before_b = inventory("b" * 32, "comparator", "inhibited-standalone-simulator")
        candidate = inventory("c" * 32, "candidate", "pio-dma-gp2")
        complete = dict(result="DIAGNOSTIC_COMPLETED_NOT_ACCEPTANCE", boot_id="c" * 32,
                        output_active=False)
        return [before_a, before_b, candidate, complete, copy.deepcopy(candidate),
                copy.deepcopy(before_b), "candidate"]

    def test_matched_idle_restoration(self):
        restoration_admitted(*self.fixtures())

    def test_changed_boot_owner_output_clock_and_config_refuse_flash(self):
        for index, path, value in (
            (4, ("wtp", "STATUS", "boot_id"), "d" * 32),
            (4, ("wtp", "STATUS", "output_active"), True),
            (4, ("wtp", "STATUS", "owner_id"), "e" * 32),
            (4, ("info", "system_clock_hz"), 150000000),
            (4, ("info", "status", "watermark_utc_ns"), "1"),
            (4, ("info", "status", "last_error"), "fault"),
            (4, ("info", "recovery_boot"), True),
            (5, ("wtp", "STATUS", "boot_id"), "f" * 32),
            (3, ("result",), "FAILED"),
            (3, ("output_active",), True),
        ):
            with self.subTest(path=path):
                args = self.fixtures()
                target = args[index]
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(ValueError):
                    restoration_admitted(*args)

    def test_backup_payload_must_match_before_candidate_write(self):
        uf2 = bytearray(512)
        struct.pack_into("<5I", uf2, 0, 0x0A324655, 0x9E5D5157, 0x2000, 0x10000000, 256)
        uf2[32:288] = bytes(range(256))
        struct.pack_into("<I", uf2, 508, 0x0AB16F30)
        self.assertEqual(verify_application_backup(uf2, bytes(range(256))), 1)
        for backup in (bytes(256), bytes(range(255))):
            with self.assertRaises(ValueError):
                verify_application_backup(uf2, backup)
        with self.assertRaises(ValueError):
            verify_application_backup(uf2[:-1], bytes(range(256)))


if __name__ == "__main__":
    unittest.main()
