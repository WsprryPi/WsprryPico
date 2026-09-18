#!/usr/bin/env python3

import copy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "scripts"))

from phase11_6.plan import compose  # noqa: E402
from phase11_6.wspr_group import (  # noqa: E402
    SLOT_NS,
    _next_slot,
    _slice_capture,
    compose_group,
    group_digest,
    validate_group,
)


class Phase116WsprGroupTests(unittest.TestCase):
    def _group(self, temporary: str):
        plan = compose()
        jobs = [job for packet in plan["packets"] for job in packet["jobs"]
                if job["band"] == "2200m" and job["mode"] == "WSPR"
                and job["purpose"] == "nominal"]
        attempts = []
        paths = []
        for index, job in enumerate(jobs):
            attempt = {
                "job_id": job["id"],
                "planned_rf_seconds": job["planned_duration_ns"] / 1e9,
                "sequence": index + 1,
            }
            path = Path(temporary) / f"attempt-{index}.json"
            path.write_text(json.dumps(attempt))
            attempts.append(attempt)
            paths.append(path)
        return plan, compose_group(plan, "2200m", attempts, paths, ROOT)

    def test_group_is_three_jobs_in_consecutive_execution_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan, group = self._group(temporary)
            jobs = validate_group(group, plan, ROOT)
        paths = {job["submission_path"]: job["id"] for job in jobs}
        self.assertEqual(
            group["execution_order"],
            [paths["production"], paths["controller_disconnect"], paths["browser_raw"]],
        )
        self.assertEqual(group["slot_spacing_ns"], str(SLOT_NS))
        self.assertEqual(group["planned_jobs"], 3)
        self.assertEqual(len(group_digest(group)), 64)

    def test_group_packet_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan, group = self._group(temporary)
            changed = copy.deepcopy(group)
            changed["slot_spacing_ns"] = "1"
            with self.assertRaises(ValueError):
                validate_group(changed, plan, ROOT)

    def test_next_slot_is_aligned_with_required_lead(self):
        now = 20 * SLOT_NS + 100
        with mock.patch("phase11_6.wspr_group.time.time_ns", return_value=now):
            target = _next_slot()
        self.assertEqual(target % SLOT_NS, 0)
        self.assertGreaterEqual(target - now, 45_000_000_000)
        self.assertLess(target - now, 165_000_000_000)

    def test_capture_slice_keeps_provenance_outside_strict_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            parent.mkdir()
            iq = np.arange(200, dtype=np.float32).view(np.complex64)
            iq.tofile(parent / "capture.cf32")
            metadata = {
                "helper_version": "test",
                "capture_id": "parent",
                "timestamps": {
                    "retained_capture_start_utc": "1970-01-01T00:00:00.000Z",
                    "retained_capture_complete_utc": "1970-01-01T00:00:05.000Z",
                },
                "elapsed_duration_s": 5.0,
                "actual_settings": {"sample_rate_hz": 10},
                "resolved_device": {"driver": "test", "serial": "test"},
                "requested_sample_count": 50,
                "retained_sample_count": 50,
                "output": {},
            }
            (parent / "capture.json").write_text(json.dumps(metadata))
            checked = []
            capture_metadata = types.ModuleType(
                "wsprrypi_qualification.capture_metadata"
            )

            def validate_metadata(path):
                value = json.loads(path.read_text())
                self.assertNotIn("derived_slice", value)
                checked.append(value)

            capture_metadata.load_capture_metadata = validate_metadata
            package = types.ModuleType("wsprrypi_qualification")
            job = {
                "id": "band:WSPR:0:production:nominal",
                "submission_path": "production",
                "planned_duration_ns": 1_000_000_000,
            }
            with mock.patch.dict(sys.modules, {
                "wsprrypi_qualification": package,
                "wsprrypi_qualification.capture_metadata": capture_metadata,
            }):
                result = _slice_capture(parent, [job], [3_000_000_000], root / "out")
            capture = root / "out/production/capture"
            self.assertEqual(len(checked), 1)
            self.assertTrue((capture / "capture-provenance.json").is_file())
            self.assertEqual(result[0]["sample_count"], 50)
            self.assertEqual(result[0]["derived_slice"]["sample_range"], [10, 60])
            self.assertEqual(checked[0]["timestamps"]["retained_capture_start_utc"],
                             "1970-01-01T00:00:01.000Z")


if __name__ == "__main__":
    unittest.main()
