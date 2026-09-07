#!/usr/bin/env python3
"""Retained matrix tampering must never create an RF qualification claim."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from campaign.plan import compose, digest, initial_matrix
from campaign.evidence import verify, verify_pico_identity, verify_receiver_identity


class EvidenceTests(unittest.TestCase):
    def bundle(self, path, bands):
        plan = compose(bands)
        result = dict(
            plan_sha256=digest(plan),
            matrix=initial_matrix(plan),
            complete=False,
            cleanup_verified=True,
            scope=plan["scope"],
        )
        (path / "plan.json").write_text(json.dumps(plan))
        (path / "result.json").write_text(json.dumps(result))
        self.seal(path)
        return result

    def seal(self, path):
        files = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.iterdir()
            if p.is_file() and p.name != "artifacts.json"
        }
        (path / "artifacts.json").write_text(json.dumps(files))

    def test_pico_identity_substitution_rejected(self):
        result = dict(device_id="1" * 32, revision="recorded-build")
        plan = dict(sample_rate_hz=138000000)
        info = dict(
            device_id=result["device_id"],
            revision=result["revision"],
            sample_rate_hz=138000000,
        )
        transaction = dict(
            hello=dict(device_id=result["device_id"]),
            initial_idle=info,
            final_idle=info,
        )
        verify_pico_identity(transaction, result, plan)
        for field, replacement in [
            ("device_id", "2" * 32),
            ("revision", "other-build"),
        ]:
            changed = dict(result, **{field: replacement})
            with self.assertRaises(ValueError):
                verify_pico_identity(transaction, changed, plan)
        with self.assertRaises(ValueError):
            verify_pico_identity(transaction, result, dict(sample_rate_hz=150000000))

    def test_receiver_substitution_and_retuning_rejected(self):
        result = dict(receiver_serial="fixture-receiver")
        metadata = dict(
            resolved_device=dict(driver="sdrplay", serial="fixture-receiver"),
            actual_settings=dict(
                format="CF32",
                sample_rate_hz=250000,
                bandwidth_hz=200000,
                center_frequency_hz=3545100,
                gain_db=20,
                channel=0,
                agc=False,
                bias_tee=False,
            ),
        )
        verify_receiver_identity(metadata, result, 3570100)
        with self.assertRaises(ValueError):
            verify_receiver_identity(metadata, dict(receiver_serial="other"), 3570100)
        with self.assertRaises(ValueError):
            verify_receiver_identity(metadata, result, 7040100)
        changed = copy.deepcopy(metadata)
        changed["actual_settings"]["sample_rate_hz"] = 2000000
        with self.assertRaises(ValueError):
            verify_receiver_identity(changed, result, 3570100)

    def test_partial_matrix_is_valid_but_not_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            self.bundle(path, ["80m", "2m"])
            result = verify(path)
            self.assertEqual(result["operational_qualified"], 0)
            self.assertFalse(result["complete"])

    def test_unsupported_and_missing_evidence_cannot_qualify(self):
        for band in ["80m", "2m"]:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)
                result = self.bundle(path, [band])
                result["matrix"][0]["status"] = "qualified"
                (path / "result.json").write_text(json.dumps(result))
                self.seal(path)
                with self.assertRaises(ValueError):
                    verify(path)

    def test_resealed_complete_claim_requires_attempts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            result = self.bundle(path, ["80m"])
            result["complete"] = True
            (path / "result.json").write_text(json.dumps(result))
            self.seal(path)
            with self.assertRaises(ValueError):
                verify(path)

    def test_resealed_scope_and_lifecycle_claims_rejected(self):
        for field, value in [
            ("scope", "unrestricted qualification"),
            ("complete", "false"),
            ("cleanup_verified", "false"),
        ]:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)
                result = self.bundle(path, ["2m"])
                result[field] = value
                (path / "result.json").write_text(json.dumps(result))
                self.seal(path)
                with self.assertRaises(ValueError):
                    verify(path)

    def test_complete_campaign_rejects_extra_repetitions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            result = self.bundle(path, ["80m"])
            result["complete"] = True
            result["matrix"][0]["observations"] = ["first", "second"]
            (path / "result.json").write_text(json.dumps(result))
            self.seal(path)
            with self.assertRaisesRegex(ValueError, "observation count"):
                verify(path)

    def test_nested_inventory_file_is_not_exempt_from_index(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            self.bundle(path, ["2m"])
            (path / "extra").mkdir()
            (path / "extra" / "artifacts.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "inventory mismatch"):
                verify(path)

    def test_changed_artifact_and_added_file_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            self.bundle(path, ["2m"])
            (path / "unindexed.txt").write_text("extra")
            with self.assertRaises(ValueError):
                verify(path)


if __name__ == "__main__":
    unittest.main()
