#!/usr/bin/env python3
"""Hardware-free request-bound tests for the Package 9 normalizer."""

import hashlib
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase11_5_package9 as package9
import phase11_5_package9_stage as stage
from audit_phase11_5_package9_attempts import attempt_roots, one as audit_attempt
from audit_phase11_5_package9 import (FAMILY_STATUS, PRIOR_SOURCE, RUNTIME_CHANGES,
    SOURCE_DIFF_SHA256, single, validate_published_result)
from adversarial_phase11_5_package9 import mutations
from audit_phase11_5_package9_failure import validate_result as validate_failure_result
from adversarial_phase11_5_package9_failure import assess as assess_failure


ROOT = Path(__file__).resolve().parents[1]


class Journal:
    def __init__(self):
        self.rows = []

    def emit(self, kind, value):
        self.rows.append((kind, value))


class Stream:
    def __init__(self, replies=()):
        self.replies = list(replies)
        self.sent = []
        self.timeouts = []

    def sendall(self, value):
        self.sent.append(value)

    def settimeout(self, value):
        self.timeouts.append(value)

    def recv(self, _):
        if not self.replies:
            raise TimeoutError("injected timeout")
        return self.replies.pop(0)


class Package9RequestTests(unittest.TestCase):
    def published_result(self):
        return {
            "schema": "phase11.5-package9-result-v1",
            "status": "PACKAGE9_COMPLETE_R6_CLOSED",
            "phase11_5_status": "CLOSED_6_OF_6_FAMILIES",
            "family_status": FAMILY_STATUS,
            "accepted_configuration": {
                "board": "Pico A 0BF4B4AEC9FFB344", "device_id": package9.DEVICE,
                "source_revision": package9.SOURCE, "image_sha256": package9.IMAGE,
                "boot_id": package9.BOOT, "system_clock_hz": 138000000,
                "pio_divider": 1, "engine": "pio-dma-gp2", "renderer": "RAM",
                "rf_pin": "GP2", "schedule_base_frequency_nhz": "135500000000000",
                "network_listener": "configured"},
            "campaign": {"packet_sha256": "1" * 64,
                "normal_load_seconds": 1800, "rf_jobs": 11,
                "planned_rf_duration_ns": package9.RF_DURATION_NS,
                "normalizer_jobs": 8, "production_jobs": 3, "browser_actions": 48,
                "browser_gets": 84, "resource_windows": 5,
                "final_terminal_records": 8, "matched_baseline_bytes": 1000,
                "post_n_bytes": [1008, 1004, 1004], "final_q_bytes": 1000,
                "maximum_post_span_bytes": 4, "monotonic_retained_growth": False},
            "source_impact": {"prior_candidate": PRIOR_SOURCE,
                "deployed_candidate": package9.SOURCE,
                "changed_runtime_files": RUNTIME_CHANGES,
                "diff_sha256": SOURCE_DIFF_SHA256,
                "decision": "Static page streaming and bounded Console/HTTP scheduling change "
                            "network resource service only. Package 9 directly covers the changed "
                            "mixed WTP, HTTPS, Console and RF interaction; RF renderer, launch, "
                            "refill, mode compilation and duration arithmetic are unchanged.",
                "later_runtime_source_changes": 0,
                "wsprrypi_source_revision": package9.WSPRRYPI_SOURCE},
            "cumulative_budget": {"attempt_count": 1, "charged_rf_jobs": 11,
                "charged_rf_duration_ns": package9.RF_DURATION_NS,
                "flashes": 6, "bootsel": 6, "configuration_writes": 0,
                "controlled_reboots": 0, "wifi_cycles": 0},
            "repairs": {"zero_rf_flashes": 6, "incorrect_build_rejected": True,
                "static_page_streaming": True,
                "bounded_console_http_grace_ms_per_second": 500,
                "accepted_configuration_restored": True},
            "restoration": {"pico_a_inactive": True,
                "pico_a_schedule_disabled": True, "pico_b_unchanged_inactive": True,
                "reservation_released": True, "host_fixture_restored": True,
                "installed_service_active": True, "capture_drops": 0},
            "evidence_sha256": {name: "1" * 64 for name in
                ("packet", "raw_audit", "adversarial", "attempt_history")},
        }

    def test_published_result_contract_rejects_resource_drift(self):
        value = self.published_result()
        self.assertIs(validate_published_result(value), value)
        value["campaign"]["maximum_post_span_bytes"] = 1025
        with self.assertRaises(ValueError):
            validate_published_result(value)

    def test_published_failure_and_attempt_budget_are_reproducible(self):
        result_path = ROOT / "docs/development/phase11-5-package9-failure-result.json"
        adversarial_path = (ROOT /
            "docs/development/phase11-5-package9-failure-adversarial-result.json")
        attempts_path = ROOT / "docs/development/phase11-5-package9-attempt-history.json"
        value = validate_failure_result(json.loads(result_path.read_text()))
        self.assertEqual(value["failed_gate"]["post_n_deltas_bytes"],
                         [12432, 12432, 11944])
        attempts = json.loads(attempts_path.read_text())
        self.assertEqual(value["cumulative_budget"]["charged_rf_duration_ns"],
                         attempts["charged_rf_duration_ns"])
        self.assertEqual(attempts["charged_rf_duration_ns"], 1_164_400_000_000)
        self.assertEqual(attempts["attempts"][-1]["attempt"],
                         "phase11-5-package9-v9-20260916")
        by_name = {item["attempt"]: item for item in attempts["attempts"]}
        self.assertEqual(by_name["phase11-5-package9-v44-20260917"]
                         ["charged_rf_duration_ns"], package9.RF_DURATION_NS)
        expected = assess_failure(value)
        expected["failure_result_sha256"] = hashlib.sha256(
            result_path.read_bytes()).hexdigest()
        self.assertEqual(json.loads(adversarial_path.read_text()), expected)

    def test_fixture_transitive_helpers_are_frozen(self):
        self.assertTrue({"scripts/phase11_5_join_diagnostics.py",
                         "scripts/phase11_5_time_local.py",
                         "scripts/phase11_4_hotspot.py"}.issubset(stage.STAGED_INPUTS))

    def test_raw_auditor_selects_exactly_one_named_record(self):
        row = {"kind": "installed_service_paused", "value": {"was_active": True}}
        self.assertIs(single([row], "installed_service_paused"), row)
        with self.assertRaises(ValueError):
            single([row, dict(row)], "installed_service_paused")

    def test_adversarial_review_covers_repaired_authority_chain(self):
        names = {name for name, _ in mutations()}
        self.assertEqual(len(names), 40)
        self.assertTrue({"readiness-service-pause", "memory-readiness-admission",
            "production-completion-report", "production-completion-identity",
            "production-usb-completion", "production-usb-loaded",
            "production-host-safety", "production-host-armed",
            "installed-service-restoration"}.issubset(names))

    def peer(self, stream):
        journal = Journal()
        peer = package9.NetworkPeer(Path("."),
            {"normalizer_request_timeout_seconds": 20}, journal, "1" * 32)
        peer.stream = stream
        return peer, journal

    def test_timeout_is_bounded_and_does_not_resend(self):
        stream = Stream()
        peer, journal = self.peer(stream)
        with patch.object(package9.time, "monotonic", return_value=10):
            with self.assertRaises(TimeoutError):
                peer.ask("GET_CLOCK")
        self.assertEqual(len(stream.sent), 1)
        self.assertEqual(stream.timeouts, [20])
        self.assertEqual([kind for kind, _ in journal.rows], ["normalizer_tx"])

    def test_response_records_the_frozen_deadline(self):
        response = {"type": "response", "protocol": "WTP/1",
            "session_id": "1" * 32, "request_id": "0" * 31 + "1",
            "op": "STATUS", "ok": True, "body": {"state": "empty"}}
        stream = Stream([package9.frame(json.dumps(response).encode())])
        peer, journal = self.peer(stream)
        with patch.object(package9.time, "monotonic", return_value=10):
            self.assertEqual(peer.ask("STATUS"), {"state": "empty"})
        self.assertEqual(len(stream.sent), 1)
        evidence = [value for kind, value in journal.rows
                    if kind == "normalizer_response"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["deadline_seconds"], 20)
        self.assertEqual(evidence[0]["request_id"], response["request_id"])

    def test_failed_long_observer_prevents_new_cycle_readiness(self):
        observer_stop = threading.Event()
        observer_stop.set()
        with patch.object(package9, "wait_for_normalizer_readiness") as readiness:
            with self.assertRaisesRegex(ValueError, "Long observer failed"):
                package9.run_normal_cycle(Path("."), {}, Journal(), 1, observer_stop)
        readiness.assert_not_called()

    def test_production_completion_uses_matching_post_release_report(self):
        job = "1" * 32
        report = {"outcome": "complete", "job_id": job,
            "arm_handed_off": True, "job": {"state": "complete",
                "output_active": False, "device_output_active": False}}
        last = {"last_report": report, "remote": {"state": "empty"}}
        self.assertIs(package9.production_lifecycle(last,
            {"armed", "running", "empty"}, {"2" * 32}, {job}, {"3" * 32}),
            report)
        altered = json.loads(json.dumps(last))
        altered["last_report"]["arm_handed_off"] = False
        with self.assertRaisesRegex(ValueError, "Production lifecycle"):
            package9.production_lifecycle(altered,
                {"armed", "running", "empty"}, {"2" * 32}, {job}, {"3" * 32})

    def test_production_completion_requires_host_handoff_states(self):
        job = "1" * 32
        last = {"last_report": {"outcome": "complete", "job_id": job,
            "arm_handed_off": True, "job": {"state": "complete",
                "output_active": False, "device_output_active": False}}}
        with self.assertRaisesRegex(ValueError, "Production lifecycle"):
            package9.production_lifecycle(last, {"running", "empty"},
                {"2" * 32}, {job}, {"3" * 32})

    def test_installed_service_is_paused_before_readiness_and_always_restored(self):
        calls = []

        def command(args, **kwargs):
            calls.append((list(args), kwargs))
            return package9.subprocess.CompletedProcess(args, 0)

        with patch.object(package9.subprocess, "run", side_effect=command), \
             patch.object(package9, "_run_with_service_paused",
                          side_effect=ValueError("injected readiness failure")):
            with self.assertRaisesRegex(ValueError, "injected readiness failure"):
                package9.run(Path("."), {}, Journal())
        self.assertEqual([call[0][-2:] for call in calls],
            [["--quiet", "wsprrypi.service"], ["stop", "wsprrypi.service"],
             ["start", "wsprrypi.service"]])

    def test_attempt_history_includes_undated_repair_deployments(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            names = ["phase11-5-package9-v33-20260917",
                     "phase11-5-package9-deploy-v32"]
            for name in names:
                (base / name).mkdir()
            (base / "unrelated").mkdir()
            self.assertEqual([path.name for path in attempt_roots(base)],
                             sorted(names))

    def test_rejected_post_flash_attempt_is_still_charged(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "packet.json").write_text(json.dumps({
                "flashes": 1, "bootsel": 1, "rf_jobs": 0}) + "\n")
            (root / "candidate-load.stdout").write_text("")
            value = audit_attempt(root, None)
            self.assertEqual((value["flashes"], value["bootsel"]), (1, 1))
            (root / "candidate-load.stdout").unlink()
            value = audit_attempt(root, None)
            self.assertEqual((value["flashes"], value["bootsel"]), (0, 0))


if __name__ == "__main__":
    unittest.main()
