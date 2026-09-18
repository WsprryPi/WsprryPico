"""No-hardware checks for the frozen Package 8 packet and schedule selection."""

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase11_5_package8 as package8
from audit_phase11_5_package8 import validate_result
from audit_phase11_5_package9 import validate_published_result as validate_package9
from adversarial_phase11_5_package8 import assess


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "docs/development/phase11-5-package8-result.json"
RAW_AUDIT_PATH = ROOT / "docs/development/phase11-5-package8-raw-audit-result.json"
ADVERSARIAL_PATH = ROOT / "docs/development/phase11-5-package8-adversarial-result.json"
MATRIX_PATH = ROOT / "docs/development/phase11-5-completion-matrix.json"


class Package8Tests(unittest.TestCase):
    def packet(self):
        identities = [f"{n:032x}" for n in range(1, 10)]
        return dict(schema="phase11.5-package8-fixture-v1", family="R5",
                    standing_authority="PHASE11.5-COMPLETION-20260915",
                    source_revision=package8.SOURCE, image_sha256=package8.IMAGE,
                    boot_id=package8.DEPLOYED_BOOT, b_boot_id=package8.B_BOOT,
                    host_boot_id=package8.HOST_BOOT, configuration_writes=2,
                    rf_jobs=2, rf_duration_ns=350_592_000_000,
                    controlled_reboots=1, flashes=0, bootsel=0, wifi_cycles=0,
                    network_runtime_seconds=7200, network_restoration_seconds=900,
                    address_change=[package8.OLD_ADDRESS, package8.NEW_ADDRESS],
                    external_link_loss_seconds=15,
                    schedule_base_frequency_nhz=package8.BASE_NHZ,
                    credentials={"controller": {"ca": "credentials/controller/client-ca.crt",
                        "cert": "credentials/controller/client.crt", "key": "credentials/controller/client.key"},
                        "browser": {"ca": "credentials/browser/client-ca.crt",
                        "cert": "credentials/browser/client.crt", "key": "credentials/browser/client.key"}},
                    storage_plan={"before_sequence": "68", "before_offset": 6144,
                        "record_size": 2048, "enabled_sequence": "69", "enabled_offset": 0,
                        "restored_sequence": "70", "restored_offset": 2048},
                    execution_history={"prior_attempts": [
                        {"packet_sha256": "44918000c592b5348179fbafb5d96432efd2a577f6c1f5b3b9d7fcf8e853724d",
                         "disposition": "pre-claim-harness-failure", "rf_jobs": 0,
                         "rf_duration_ns": 0},
                        {"packet_sha256": "7248629e1c08d45571598f101da4f3687ea062680a4ed86e9e2ea2e6c9a6a5e3",
                         "disposition": "address-recovery-failure", "rf_jobs": 1,
                         "rf_duration_ns": 240_000_000_000}],
                        "repair_deployment": {
                            "packet_sha256": "45cdcb5c276498b5720a8745b0c8b76af255ad967ebb63445919f1b4d2c28324",
                            "source_revision": package8.SOURCE, "image_sha256": package8.IMAGE,
                            "boot_id": package8.DEPLOYED_BOOT, "flashes": 1, "bootsel": 1},
                        "aggregate_after_planned_success": {"rf_jobs": 3,
                            "rf_duration_ns": 590_592_000_000, "configuration_writes": 2,
                            "controlled_reboots": 1, "flashes": 2, "bootsel": 2}},
                    **dict(zip(("network_session", "network_owner", "network_job", "usb_session",
                        "post_network_session", "schedule_usb_session", "schedule_network_session",
                        "inventory_session", "b_session"), identities)))

    def test_exact_packet_and_budget(self):
        package8.validate(self.packet())
        amended = self.packet()
        amended["corrective_amendment"] = {
            "reason": "pre-CLAIM CAPS field-shape harness defect",
            "prior_packet_sha256": "44918000c592b5348179fbafb5d96432efd2a577f6c1f5b3b9d7fcf8e853724d",
            "prior_attempt_rf_submissions": 0, "additional_rf_jobs": 0,
            "additional_rf_duration_ns": 0}
        package8.validate(amended)
        for key, value in (("configuration_writes", 3), ("rf_jobs", 3),
                           ("schedule_base_frequency_nhz", "3570100000000000")):
            changed = self.packet(); changed[key] = value
            with self.assertRaises(ValueError):
                package8.validate(changed)

    def test_occurrence_is_even_minute_plus_one_and_at_least_240_seconds_ahead(self):
        for now in (0.0, 100.25, 86390.0, 1_789_604_200.5):
            occurrence, phase = package8.schedule_occurrence(now)
            self.assertGreaterEqual(occurrence - now, 240)
            self.assertEqual((occurrence - 1) % 120, 0)
            self.assertEqual(phase, (occurrence - 1) % 86400)

    def test_https_helper_does_not_shadow_http_module(self):
        self.assertTrue(callable(package8.https_request))
        self.assertTrue(hasattr(package8.http, "client"))

    def test_storage_retry_packet_is_bound_to_failed_evidence_and_helpers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "packet.json").write_text("{}\n")
            (root / "storage-run.jsonl").write_text('{"kind":"preserved_failure"}\n')
            reservation = Path(package8.__file__).with_name("phase11_5_rf_reservation.py")
            (root / "scripts" / reservation.name).write_bytes(reservation.read_bytes())
            packet = {
                "schema": "phase11.5-package8-storage-retry-v1",
                "standing_authority": "PHASE11.5-COMPLETION-20260915",
                "parent_packet_sha256": package8.digest(root / "packet.json"),
                "source_revision": package8.SOURCE,
                "image_sha256": package8.IMAGE,
                "prior_boot_id": package8.DEPLOYED_BOOT,
                "current_boot_id": "8af7e0f0f4cef61bcbf8d5f7173d4c78",
                "prior_attempt": {
                    "result": "observer-idle-timeout-before-autonomous-rf",
                    "rf_jobs": 0,
                    "rf_duration_ns": 0,
                    "configuration_writes": 2,
                    "controlled_reboots": 1,
                    "storage_run_sha256": package8.digest(root / "storage-run.jsonl"),
                },
                "limits": {"rf_jobs": 1, "rf_duration_ns": 110_592_000_000,
                    "loads": 0, "arm": 0, "time_commands": 0,
                    "configuration_writes": 2, "controlled_reboots": 1,
                    "flashes": 0, "bootsel": 0, "wifi_cycles": 0},
                "storage_plan": {"before_sequence": "70", "before_offset": 2048,
                    "record_size": 2048, "enabled_sequence": "71", "enabled_offset": 4096,
                    "restored_sequence": "72", "restored_offset": 6144,
                    "watermark_utc_ns": "1789606801000000000"},
                "aggregate_after_planned_success": {"rf_jobs": 3,
                    "rf_duration_ns": 590_592_000_000, "configuration_writes": 4,
                    "controlled_reboots": 2, "flashes": 2, "bootsel": 2},
                "helper_sha256": package8.digest(Path(package8.__file__)),
                "reservation_helper_sha256": package8.digest(
                    root / "scripts" / reservation.name),
                "usb_session": "1" * 32,
                "armed_network_session": "2" * 32,
                "running_network_session": "3" * 32,
            }
            retry_path = root / "storage-retry-packet.json"
            retry_path.write_text(json.dumps(packet) + "\n")
            actual, packet_sha = package8.storage_retry_packet(root)
            self.assertEqual(actual, packet)
            self.assertEqual(packet_sha, package8.digest(retry_path))
            (root / "storage-run.jsonl").write_text('{"kind":"changed"}\n')
            with self.assertRaisesRegex(ValueError, "Exact bounded"):
                package8.storage_retry_packet(root)

    def test_publication_closes_exactly_r5(self):
        result = validate_result(json.loads(RESULT_PATH.read_text()))
        matrix = json.loads(MATRIX_PATH.read_text())
        rows = [row for row in matrix["assertions"] if row["group"] == "R5"]
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(row["classification"] == "accepted/applicable" for row in rows))
        self.assertTrue(matrix["family_status"]["R5"].startswith("CLOSED"))
        if (ROOT / "docs/development/phase11-5-package11-retry4-result.json").exists():
            self.assertTrue(matrix["family_status"]["R6"].startswith("CLOSED"))
            self.assertIsNotNone(matrix["accepted_configuration"])
        else:
            self.assertTrue(matrix["family_status"]["R6"].startswith("OPEN"))
            self.assertIsNone(matrix["accepted_configuration"])
        self.assertEqual(result["phase11_5_status"], "OPEN_5_OF_6_FAMILIES")

    def test_raw_audit_publication_binds_offline_evidence(self):
        value = json.loads(RAW_AUDIT_PATH.read_text())
        self.assertEqual(value["schema"], "phase11.5-package8-raw-audit-v1")
        self.assertEqual(value["status"], "PASS")
        self.assertEqual(value["evidence_files_bound"], 21)
        self.assertEqual(value["device_or_network_operations"], 0)
        self.assertTrue(value["reservation_chain_verified"])
        self.assertTrue(value["host_restoration_verified"])
        self.assertEqual(value["sanitized_result_sha256"],
            hashlib.sha256(RESULT_PATH.read_bytes()).hexdigest())
        self.assertEqual(value["auditor_sha256"], hashlib.sha256(
            (ROOT / "scripts/audit_phase11_5_package8.py").read_bytes()).hexdigest())

    def test_published_adversarial_assessment_is_reproducible(self):
        expected = json.loads(ADVERSARIAL_PATH.read_text())
        actual = assess(json.loads(RESULT_PATH.read_text()))
        self.assertEqual(actual, expected)
        self.assertEqual(actual["mutations"], 46)

    def test_only_reviewed_package9_runtime_paths_changed_after_candidate(self):
        completed = subprocess.run(
            ["git", "diff", "--name-only", package8.SOURCE + "..HEAD", "--",
             "src", "include", "firmware", "cmake"], cwd=ROOT, check=True,
            text=True, stdout=subprocess.PIPE)
        self.assertEqual(set(completed.stdout.splitlines()),
            {"src/network/api.cpp", "src/network/http.hpp",
             "src/network/pico/server.cpp", "src/network/pico/server.hpp",
             "src/standalone/pico/main.cpp", "src/usb/reply_priority.hpp"})
        package9_path = ROOT / "docs/development/phase11-5-package9-result.json"
        if package9_path.exists():
            package9 = validate_package9(json.loads(package9_path.read_text()))
            self.assertEqual(package9["source_impact"]["prior_candidate"],
                             package8.SOURCE)


if __name__ == "__main__":
    unittest.main()
