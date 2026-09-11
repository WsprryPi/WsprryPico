#!/usr/bin/env python3
"""Restoration decisions and preimage verification without device operations."""
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from phase11_5_pilot_supervisor import finished, restoration_admitted, verify_application_backup
from phase11_5_recover import admission, BOOT, JOB


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
    def test_fault_recovery_requires_exact_preserved_inactive_fault(self):
        original = inventory("a" * 32, "original", "inhibited-standalone-simulator")
        comparator = inventory("b" * 32, "comparator", "inhibited-standalone-simulator")
        current = inventory(BOOT, "ce1c339a976e", "pio-dma-gp2")
        current["info"]["device_id"] = "fd6127d11d6aca42a9905fa3fb1bf1d5"
        current["info"]["status"].update(boot_id=BOOT, state="failed")
        current["wtp"]["STATUS"].update(state="failed", job_id=JOB, terminal_records=[
            dict(job_id=JOB, state="failed", output_active=False, error=dict(code="DEVICE_FAULT"))])
        admission(current, original, comparator, comparator)
        for path, value in ((('wtp', 'STATUS', 'output_active'), True),
                            (('wtp', 'STATUS', 'state'), 'running'),
                            (('wtp', 'STATUS', 'owner_id'), 'd' * 32),
                            (('wtp', 'STATUS', 'boot_id'), 'e' * 32),
                            (('wtp', 'STATUS', 'job_id'), 'f' * 32),
                            (('info', 'system_clock_hz'), 150000000),
                            (('info', 'status', 'enabled'), True)):
            altered = copy.deepcopy(current)
            target = altered
            for key in path[:-1]: target = target[key]
            target[path[-1]] = value
            with self.assertRaises(ValueError):
                admission(altered, original, comparator, comparator)

    def test_host_evidence_uses_64_bit_timestamps_and_complete_records(self):
        rows = [dict(sequence=i, kind=kind, utc_ns=1789130169102617537 + i,
                     monotonic_ns=74669953165628 + i, value=dict(result="DONE"))
                for i, kind in enumerate(("start", "finish"))]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "records.jsonl"
            source = "".join(json.dumps(row) + "\n" for row in rows)
            path.write_text(source)
            self.assertEqual(finished(path, "DONE"), {"result": "DONE"})
            for bad in (source[:-1], source.replace('"sequence": 1', '"sequence": 3'),
                        source.replace('"utc_ns": 1789130169102617537', '"utc_ns": -1'),
                        source.replace('"sequence": 0', '"sequence": 0, "sequence": 0'),
                        source.replace('"sequence": 0', '"sequence": NaN'),
                        source.replace('"kind": "start"', '"kind": "other"')):
                path.write_text(bad)
                with self.assertRaises(ValueError):
                    finished(path, "DONE")

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
