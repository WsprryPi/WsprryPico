#!/usr/bin/env python3
"""Hardware-free tests for Package 10 matched replay-state evidence."""

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase11_5_package10 as package10
import phase11_5_package10_stage as stage
import phase11_4_hotspot as hotspot
import phase11_5_network_fixture as network_fixture
from audit_phase11_5_package10 import (FAMILY_STATUS, validate_published_result,
    validate_stopped_attempt)
from adversarial_phase11_5_package10 import mutations
from audit_phase11_5_package10_failure import validate_result as validate_failure_result
from adversarial_phase11_5_package10_failure import (assess as assess_failure,
    mutations as failure_mutations)


class Package10Tests(unittest.TestCase):
    def result(self):
        return {"schema": "phase11.5-package10-result-v1",
            "status": "PACKAGE10_COMPLETE_R6_CLOSED",
            "phase11_5_status": "CLOSED_6_OF_6_FAMILIES",
            "family_status": FAMILY_STATUS,
            "accepted_configuration": {
                "board": "Pico A 0BF4B4AEC9FFB344", "device_id": package10.DEVICE,
                "source_revision": package10.SOURCE, "image_sha256": package10.IMAGE,
                "boot_id": package10.BOOT, "system_clock_hz": 138000000,
                "pio_divider": 1, "engine": "pio-dma-gp2", "renderer": "RAM",
                "rf_pin": "GP2", "schedule_base_frequency_nhz": "135500000000000",
                "network_listener": "configured"},
            "campaign": {"packet_sha256": "1" * 64, "normal_load_seconds": 1800,
                "rf_jobs": 16, "planned_rf_duration_ns": package10.RF_DURATION_NS,
                "warmup_jobs": 8, "refresh_jobs": 5, "production_jobs": 3,
                "browser_actions": 48, "browser_gets": 84, "resource_windows": 5,
                "final_terminal_records": 8, "matched_baseline_bytes": 56000,
                "post_n_bytes": [56008, 56004, 56004], "final_q_bytes": 56000,
                "maximum_post_span_bytes": 4, "monotonic_retained_growth": False,
                "terminal_class_cardinality": {"production": 3, "maximum": 5},
                "production_adjustment_sha256": "2" * 64,
                "maximum_adjustment_sha256": "3" * 64},
            "diagnosis": {"package9_failure_preserved": True,
                "cause": "inequivalent retained WTP replay-history classes",
                "firmware_memory_leak_found": False, "resource_limit_bytes": 1024,
                "protocol_retention_preserved": True},
            "source_impact": {"deployed_candidate": package10.SOURCE,
                "repository_baseline_revision":
                    "e22c86c83ceb161080c218748baf5d3eaa892652",
                "runtime_source_changes": 0,
                "decision": "measurement-only replay-history normalization",
                "wsprrypi_source_revision": package10.WSPRRYPI_SOURCE},
            "budget": {"attempts": 2, "authorized_rf_duration_ns": 480_000_000_000,
                "charged_rf_jobs": 20, "charged_rf_duration_ns": 360_800_000_000,
                "unused_authorized_rf_duration_ns": 119_200_000_000,
                "authorized_max_flashes": 2, "authorized_max_bootsel": 2,
                "flashes": 0, "bootsel": 0, "configuration_writes": 0,
                "controlled_reboots": 0, "wifi_cycles": 0, "allocation_probes": 0},
            "restoration": {"pico_a_inactive": True, "pico_a_empty_unowned": True,
                "pico_b_unchanged_inactive": True, "reservation_released": True,
                "host_fixture_restored": True, "installed_service_active": True,
                "capture_drops": 0},
            "evidence_sha256": {"packet": "1" * 64, "raw_audit": "4" * 64,
                "adversarial": "5" * 64, "stopped_attempt": "6" * 64}}

    def test_production_class_is_exact_383_event_one_second_plan(self):
        job = package10.production_class_job("a" * 32, 0)
        self.assertEqual(len(job["events"]), 383)
        self.assertEqual(int(job["total_duration_ns"]), 1_000_000_000)
        offset = 0
        for event in job["events"]:
            self.assertEqual(int(event["offset_ns"]), offset)
            self.assertTrue(event["rf_on"])
            offset += int(event["duration_ns"])
        self.assertEqual(offset, 1_000_000_000)
        self.assertEqual([int(event["duration_ns"]) for event in job["events"][:22]],
                         [2_610_967] * 22)
        self.assertTrue(all(int(event["duration_ns"]) == 2_610_966
                            for event in job["events"][22:]))

    def test_frequency_sequence_matches_question_mark_fskcw_shape(self):
        frequencies = package10.production_frequencies()
        mark, space = 135_505_000_000_000, 135_500_000_000_000
        self.assertEqual(len(frequencies), 383)
        self.assertEqual(frequencies[:11],
                         [mark, space, mark, space, mark, space,
                          mark, space, mark, space, mark])
        self.assertEqual(frequencies[11], space)
        self.assertEqual(frequencies.count(mark), 32 * 6)
        self.assertEqual(frequencies.count(space), 32 * 5 + 31)

    def test_warmup_and_refresh_preserve_exact_class_cardinality(self):
        warmup = package10.warmup_jobs("b" * 32)
        refresh = package10.refresh_jobs("b" * 32)
        self.assertEqual([len(job["events"]) for job in warmup], [383] * 3 + [512] * 5)
        self.assertEqual([len(job["events"]) for job in refresh], [512] * 5)
        ids = [job["job_id"] for job in warmup + refresh]
        self.assertEqual(len(ids), len(set(ids)))
        production = ["p1", "p2", "p3"]
        current = [job["job_id"] for job in warmup]
        for index, job_id in enumerate(production):
            current = current[1:] + [job_id]
            self.assertEqual(len(current), 8)
            self.assertEqual(sum(value in production for value in current), index + 1)
            self.assertEqual(sum(value in {job["job_id"] for job in warmup[:3]}
                                 for value in current), 2 - index)
        for job in refresh:
            current = current[1:] + [job["job_id"]]
        self.assertEqual(set(current), set(production) | {job["job_id"] for job in refresh})

    def test_adjustment_hash_is_numeric_and_order_sensitive(self):
        values = [{"event_index": "0", "requested_frequency_nhz": "10",
                   "realized_frequency_nhz": "11"},
                  {"event_index": 1, "requested_frequency_nhz": 20,
                   "realized_frequency_nhz": 21}]
        self.assertEqual(package10.adjustment_hash(values),
                         package10.adjustment_hash(json.loads(json.dumps(values))))
        reversed_values = list(reversed(values))
        self.assertNotEqual(package10.adjustment_hash(values),
                            package10.adjustment_hash(reversed_values))

    def test_refresh_rejects_wrong_adjustment_class(self):
        warmup = {"maximum_hash": "a" * 64}
        batch = {"status": {"terminal_records": []}, "jobs": ["j"],
                 "adjustment_hashes": ["b" * 64]}
        with patch.object(package10, "run_job_batch", return_value=batch):
            with self.assertRaisesRegex(ValueError, "Refresh adjustment class"):
                package10.run_refresh(Path("."), {"refresh_jobs": ["j"],
                    "refresh_session": "s", "refresh_owner": "o"}, object(),
                    [{"job_id": "p1"}, {"job_id": "p2"}, {"job_id": "p3"}], warmup)

    def test_published_result_validator_and_mutation_inventory(self):
        value = self.result()
        self.assertIs(validate_published_result(value), value)
        altered = copy.deepcopy(value)
        altered["campaign"]["final_q_bytes"] += 1025
        with self.assertRaises(ValueError):
            validate_published_result(altered)
        names = [name for name, _ in mutations()]
        self.assertEqual(len(names), len(set(names)))
        self.assertGreaterEqual(len(names), 44)
        self.assertIn("terminal-class-cardinality", names)
        self.assertIn("final-terminal-set", names)

    def test_stopped_attempt_is_preserved_and_bound_to_corrected_packet(self):
        path = Path(__file__).resolve().parents[1] / "docs/development/phase11-5-package10-attempt1-result.json"
        value = json.loads(path.read_text())
        self.assertIs(validate_stopped_attempt(value), value)
        self.assertEqual(package10.digest(path), package10.PRIOR_ATTEMPT_RESULT_SHA256)
        altered = copy.deepcopy(value)
        altered["charged_rf_duration_ns"] = 0
        with self.assertRaises(ValueError):
            validate_stopped_attempt(altered)

    def test_blocked_result_and_adversarial_assessment_are_reproducible(self):
        root = Path(__file__).resolve().parents[1] / "docs/development"
        result_path = root / "phase11-5-package10-failure-result.json"
        adversarial_path = root / "phase11-5-package10-failure-adversarial-result.json"
        value = validate_failure_result(json.loads(result_path.read_text()))
        self.assertEqual(value["execution"]["corrected_rf_jobs"], 0)
        self.assertEqual(value["budget"]["charged_rf_duration_ns"], 4_000_000_000)
        self.assertEqual(value["budget"]["unused_authorized_rf_duration_ns"],
                         476_000_000_000)
        expected = assess_failure(value)
        expected["failure_result_sha256"] = hashlib.sha256(
            result_path.read_bytes()).hexdigest()
        self.assertEqual(json.loads(adversarial_path.read_text()), expected)
        names = [name for name, _ in failure_mutations()]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(names), 24)

    def test_package10_fixture_has_bounded_association_runway(self):
        self.assertEqual(network_fixture.CLIENT_ASSOCIATION_SECONDS, 90)
        self.assertEqual(network_fixture.CLIENT_READY_SECONDS, 105)
        with self.assertRaises(AssertionError):
            hotspot.client(association_seconds=0)
        with self.assertRaises(AssertionError):
            hotspot.client(association_seconds=121)

    def test_normalizer_uses_package10_connect_timeout(self):
        peer = package10.package9.NetworkPeer(Path('.'),
            {"normalizer_connect_timeout_seconds":
             package10.NORMALIZER_CONNECT_TIMEOUT_SECONDS}, None, "a" * 32)
        with patch.object(package10.package9.socket, "create_connection",
                          side_effect=OSError("bounded test")) as connect:
            with self.assertRaises(OSError):
                peer.connect()
        connect.assert_called_once_with((package10.ADDRESS, 18443),
                                        timeout=package10.NORMALIZER_CONNECT_TIMEOUT_SECONDS)

    def test_package10_uses_quiet_clock_settle_and_sparse_retries(self):
        self.assertEqual(package10.NETWORK_ROUTE_SECONDS, 600)
        self.assertEqual(package10.NETWORK_SETTLE_SECONDS, 180)
        self.assertEqual(package10.NETWORK_READINESS_SECONDS, 300)
        self.assertEqual(package10.NORMALIZER_RETRY_SECONDS, 30)
        self.assertEqual((package10.FIXTURE_AP_IF, package10.FIXTURE_CLIENT_IF),
                         (network_fixture.AP_IF, network_fixture.CLIENT_IF))

    def test_network_settle_waits_on_name_without_opening_tcp(self):
        class Journal:
            def __init__(self):
                self.kinds = []
            def emit(self, kind, value):
                self.kinds.append((kind, value))
        journal = Journal()
        answer = [(package10.socket.AF_INET, package10.socket.SOCK_STREAM, 6, '',
                   (package10.ADDRESS, 18443))]
        with patch.object(package10.socket, 'getaddrinfo', return_value=answer) as lookup, \
                patch.object(package10.socket, 'create_connection') as connect:
            package10.wait_for_network_settle(
                {"network_route_seconds": 1, "network_settle_seconds": 0}, journal)
        connect.assert_not_called()
        lookup.assert_called_once()
        self.assertEqual([kind for kind, _ in journal.kinds],
                         ["network_route_readiness", "network_clock_settle_complete"])

    def test_package10_tls_clients_use_x25519_only(self):
        context = MagicMock()
        packet = {"tls_key_exchange_group": "X25519", "credentials": {
            "controller": {"ca": "ca", "cert": "cert", "key": "key"}}}
        with patch.object(package10.package9.ssl, "create_default_context",
                          return_value=context):
            actual = package10.package9.tls_context(
                Path('/private/root'), packet, "controller", "wtp/1")
        self.assertIs(actual, context)
        context.set_ecdh_curve.assert_called_once_with("X25519")
        self.assertIn("Groups = X25519", stage.production_openssl_config())


if __name__ == "__main__":
    unittest.main()
