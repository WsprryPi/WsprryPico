#!/usr/bin/env python3
"""Negative acceptance tests with synthetic identities, never target evidence."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_phase11_5 import CASES, GATES, validate


class RegisterTests(unittest.TestCase):
    def setUp(self):
        self.register = json.loads((ROOT / "docs/development/phase11-5-register.json").read_text())

    def accepted_fixture(self):
        value = copy.deepcopy(self.register)
        config = dict(id="synthetic", sample_clock_hz=138000000,
                      system_clock_hz=138000000, pio_divider=[1, 1],
                      uf2_sha256="a" * 64, source_revision="b" * 40, device_id="c" * 32,
                      cases={case: "PASS" for case in CASES})
        config["gates"] = {gate: dict(status="PASS", uf2_sha256="a" * 64,
                                     sample_clock_hz=138000000, device_id="c" * 32,
                                     boot_id="d" * 32, reviewed_evidence="synthetic-test-only")
                           for gate in GATES}
        value["accepted_configurations"] = [config]
        value["clocks"][0]["physical_status"] = "ACCEPTED"
        value["cases"] = config["cases"].copy()
        value["phase_status"] = "CLOSED"
        return value

    def test_checked_in_register(self):
        validate(self.register)

    def test_open_is_not_acceptance(self):
        self.register["phase_status"] = "CLOSED"
        with self.assertRaises(ValueError):
            validate(self.register)

    def test_cross_clock_and_image_evidence_rejected(self):
        validate(self.accepted_fixture())
        for field, wrong in (("sample_clock_hz", 150000000), ("uf2_sha256", "e" * 64),
                             ("device_id", "f" * 32), ("boot_id", ""),
                             ("status", "NOT_RUN"), ("reviewed_evidence", "")):
            with self.subTest(field=field):
                value = self.accepted_fixture()
                value["accepted_configurations"][0]["gates"]["refill"][field] = wrong
                with self.assertRaises(ValueError):
                    validate(value)

    def test_new_clock_requires_deadlines_and_checks(self):
        value = self.accepted_fixture()
        value["clocks"][1]["selected_for_11_6"] = True
        with self.assertRaises(ValueError):
            validate(value)
        value = self.accepted_fixture()
        value["clocks"][0]["full_buffer_period_ns"] = [10485760, 3]  # 150 MHz
        with self.assertRaises(ValueError):
            validate(value)

    def test_missing_gate_or_case_rejected(self):
        for key in ("gates", "cases"):
            value = self.accepted_fixture()
            value["accepted_configurations"][0][key].popitem()
            with self.assertRaises(ValueError):
                validate(value)


if __name__ == "__main__":
    unittest.main()
