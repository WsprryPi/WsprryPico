#!/usr/bin/env python3
"""Hardware-free tests for the Package 11 two-host closure tooling."""

import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import phase11_5_package10 as package10
import phase11_5_package11 as package11
import phase11_5_package11_admission as admission
import phase11_5_package11_clock_poll_retest as clock_retest
import phase11_5_package11_fixture as fixture
import phase11_5_package11_remote_ap as remote
import phase11_5_package11_stage as stage
import phase11_5_time_local as time_local
from audit_phase11_5_package11 import FAMILY_STATUS, validate_result
from audit_phase11_5_package11_admission import validate_result as validate_admission_result
from audit_phase11_5_package11_retry3_failure import validate_result as validate_retry3
from audit_phase11_5_package11_usb_reducer_retest import (
    validate_result as validate_reducer_retest)
from adversarial_phase11_5_package11 import assess as assess_closure
from adversarial_phase11_5_package11_admission import assess as assess_admission
from adversarial_phase11_5_package11_retry1_failure import assess as assess_retry1
from adversarial_phase11_5_package11_retry2_failure import assess as assess_retry2
from adversarial_phase11_5_package11_retry3_failure import assess as assess_retry3
from adversarial_phase11_5_package11_usb_reducer_retest import (
    assess as assess_reducer_retest)


HASH = "a" * 64


def make_credentials(root):
    for role in ("controller", "browser"):
        directory = root / "credentials" / role
        directory.mkdir(parents=True, exist_ok=True)
        for kind, name in (("ca", "client-ca.crt"), ("cert", "client.crt"),
                           ("key", "client.key")):
            (directory / name).write_bytes((role + "-" + kind).encode())


def admission_result():
    return {"schema": "phase11.5-package11-admission-result-v1",
        "status": "PASS_ZERO_RF", "packet_sha256": HASH,
        "candidate": {"source_revision": package10.SOURCE,
            "image_sha256": package10.IMAGE, "boot_id": package10.BOOT,
            "device_id": package10.DEVICE},
        "fixture": {"ap_host": "wspr4", "ap_mac": package11.REMOTE_AP_MAC,
            "client_host": "wspr5", "client_mac": package11.CLIENT_MAC,
            "association_bssid": package11.REMOTE_AP_MAC, "channel": 11,
            "client_network_namespace": True, "client_mount_namespace": True},
        "readiness": {"observation_seconds": admission.OBSERVATION_SECONDS,
            "wtp_status_samples": admission.SAMPLES,
            "https_status_samples": admission.SAMPLES, "mdns_ntp_probes": 2,
            "same_boot": True, "terminal_set_unchanged": True},
        "zero_rf": {"reservation_acquired": False, "mutating_wtp_requests": 0,
            "launch_epoch_delta": 0, "tail_irq_delta": 0, "rf_jobs": 0,
            "rf_duration_ns": 0},
        "restoration": {"pico_a_inactive_unowned": True,
            "pico_b_inactive_unowned": True, "reservation_released_unchanged": True,
            "wspr5_restored": True, "wspr4_restored": True,
            "installed_service_active": True, "capture_drops": 0},
        "auditor_sha256": HASH, "evidence_sha256": {"packet.json": HASH}}


def closure_result():
    baseline = 50000
    return {"schema": "phase11.5-package11-result-v1",
        "status": "PACKAGE11_COMPLETE_R6_CLOSED",
        "phase11_5_status": "CLOSED_6_OF_6_FAMILIES", "family_status": FAMILY_STATUS,
        "accepted_configuration": {"board": "Pico A 0BF4B4AEC9FFB344",
            "device_id": package10.DEVICE, "source_revision": package10.SOURCE,
            "image_sha256": package10.IMAGE, "boot_id": package10.BOOT,
            "system_clock_hz": 138000000, "pio_divider": 1, "engine": "pio-dma-gp2",
            "renderer": "RAM", "rf_pin": "GP2",
            "schedule_base_frequency_nhz": "135500000000000",
            "network_listener": "configured"},
        "campaign": {"packet_sha256": HASH, "normal_load_seconds": 1800,
            "rf_jobs": package10.RF_JOBS,
            "planned_rf_duration_ns": package10.RF_DURATION_NS,
            "warmup_jobs": 8, "refresh_jobs": 5, "production_jobs": 3,
            "browser_actions": 48, "browser_gets": 84, "resource_windows": 5,
            "matched_baseline_bytes": baseline,
            "post_n_bytes": [baseline, baseline + 128, baseline],
            "final_q_bytes": baseline + 64, "maximum_post_span_bytes": 128,
            "monotonic_retained_growth": False, "final_terminal_records": 8,
            "terminal_class_cardinality": {"production": 3, "maximum": 5},
            "production_adjustment_sha256": "b" * 64,
            "maximum_adjustment_sha256": "c" * 64},
        "diagnosis": {"package9_failure_preserved": True,
            "package10_fixture_blocker_preserved": True,
            "package11_attempt1_failure_preserved": True,
            "package11_retry1_failure_preserved": True,
            "package11_retry2_failure_preserved": True,
            "credential_owner_repair_zero_rf_verified": True,
            "clock_poll_repair_zero_rf_verified": True,
            "terminal_retention_preflight_verified": True,
            "cause": "inequivalent retained WTP replay-history classes",
            "firmware_memory_leak_found": False, "resource_limit_bytes": 1024,
            "protocol_retention_preserved": True},
        "fixture": {"zero_rf_admission": "PASS", "ap_host": "wspr4",
            "ap_mac": package11.REMOTE_AP_MAC, "client_host": "wspr5",
            "client_mac": package11.CLIENT_MAC, "channel": 11,
            "wspr4_restored": True, "wspr5_restored": True},
        "source_impact": {"deployed_candidate": package10.SOURCE,
            "repository_baseline_revision": "e22c86c83ceb161080c218748baf5d3eaa892652",
            "runtime_source_changes": 0,
            "decision": "measurement-only replay-history normalization",
            "wsprrypi_source_revision": package10.WSPRRYPI_SOURCE},
        "budget": {"authorized_rf_duration_ns": package11.AUTHORIZED_RF_DURATION_NS,
            "charged_rf_jobs": package10.RF_JOBS,
            "charged_rf_duration_ns": package10.RF_DURATION_NS,
            "unused_authorized_rf_duration_ns":
                package11.AUTHORIZED_RF_DURATION_NS - package10.RF_DURATION_NS,
            "prior_attempt_charged_rf_jobs": package11.ATTEMPT1_RF_JOBS,
            "prior_attempt_charged_rf_duration_ns": package11.ATTEMPT1_RF_DURATION_NS,
            "retry1_charged_rf_jobs": package11.RETRY1_RF_JOBS,
            "retry1_charged_rf_duration_ns": package11.RETRY1_RF_DURATION_NS,
            "retry2_charged_rf_jobs": package11.RETRY2_RF_JOBS,
            "retry2_charged_rf_duration_ns": package11.RETRY2_RF_DURATION_NS,
            "cumulative_package11_rf_jobs": package11.CUMULATIVE_RF_JOBS,
            "cumulative_package11_rf_duration_ns": package11.CUMULATIVE_RF_DURATION_NS,
            "flashes": 0, "bootsel": 0, "configuration_writes": 0,
            "controlled_reboots": 0, "wifi_cycles": 0, "allocation_probes": 0},
        "restoration": {"pico_a_inactive": True, "pico_a_empty_unowned": True,
            "pico_b_unchanged_inactive": True, "reservation_released": True,
            "wspr5_fixture_restored": True, "wspr4_fixture_restored": True,
            "installed_service_active": True, "capture_drops": 0},
        "admission_result_sha256": package11.ADMISSION_RESULT_SHA256,
        "admission_adversarial_sha256": package11.ADMISSION_ADVERSARIAL_SHA256,
        "prior_attempt_result_sha256": package11.ATTEMPT1_RESULT_SHA256,
        "clock_poll_retest_result_sha256": package11.CLOCK_POLL_RETEST_RESULT_SHA256,
        "retry1_attempt_result_sha256": package11.RETRY1_RESULT_SHA256,
        "retry1_adversarial_sha256": package11.RETRY1_ADVERSARIAL_SHA256,
        "credential_retest_result_sha256": package11.CREDENTIAL_RETEST_RESULT_SHA256,
        "retry2_attempt_result_sha256": package11.RETRY2_RESULT_SHA256,
        "retry2_adversarial_sha256": package11.RETRY2_ADVERSARIAL_SHA256,
        "raw_audit_sha256": HASH, "evidence_sha256": {"packet.json": HASH}}


class Package11Tests(unittest.TestCase):
    def test_remote_ntp_retries_timeout_and_rejects_stale_reply(self):
        request = bytearray(48)
        request[40:48] = b"12345678"
        stale = bytearray(48)
        valid = bytearray(48)
        valid[24:32] = request[40:48]

        class Upstream:
            def __init__(self):
                self.replies = [TimeoutError(), (bytes(stale), (remote.NTP_UPSTREAM, 123)),
                                (bytes(valid), (remote.NTP_UPSTREAM, 123))]
                self.sent = []

            def sendto(self, value, address):
                self.sent.append((value, address))

            def recvfrom(self, _):
                value = self.replies.pop(0)
                if isinstance(value, BaseException):
                    raise value
                return value

        upstream = Upstream()
        response, timeouts, invalid = remote.upstream_ntp(upstream, bytes(request))
        self.assertEqual(bytes(valid), response)
        self.assertEqual((1, 1, 3), (timeouts, invalid, len(upstream.sent)))

    def test_admission_console_gate_uses_current_info_diagnostics(self):
        info = {"network": {"ipv4": package10.ADDRESS, "mdns_state": "active"},
                "status": {"clock_state": "synchronized", "output_active": False,
                    "reboot_required": False, "last_error": None},
                "engine_diagnostic": ""}
        self.assertTrue(admission.console_ready(info))
        for path, value in (("reboot_required", True), ("last_error", "fault")):
            changed = copy.deepcopy(info)
            changed["status"][path] = value
            self.assertFalse(admission.console_ready(changed))
        changed = copy.deepcopy(info)
        changed["engine_diagnostic"] = "dma"
        self.assertFalse(admission.console_ready(changed))

    def test_admission_waits_for_pico_time_without_mutation(self):
        values = [
            {"network": {"ntp_address": "", "ntp_resolution": "unresolved"},
             "status": {"clock_state": "unsynchronized", "output_active": False}},
            {"network": {"ntp_address": package11.TIME_ADDRESS,
                         "ntp_resolution": "resolved"},
             "status": {"clock_state": "synchronized", "output_active": False}},
        ]

        class Journal:
            def __init__(self):
                self.events = []

            def emit(self, kind, value):
                self.events.append((kind, value))

        journal = Journal()
        with patch.object(admission.package9, "console_info_once",
                          side_effect=values) as console, \
                patch.object(admission.time, "monotonic", side_effect=(0, 0, 1)), \
                patch.object(admission.time, "sleep"):
            result = admission.wait_for_pico_time(
                journal, admission.PICO_TIME_READINESS_SECONDS)
        self.assertEqual("synchronized", result["status"]["clock_state"])
        self.assertEqual(2, console.call_count)
        self.assertEqual([False, True],
                         [value["ready"] for kind, value in journal.events
                          if kind == "admission_pico_time_readiness"])

    def test_admission_status_retries_only_transport_failure(self):
        class Peer:
            calls = 0

            def __init__(self, *_):
                self.number = 0

            def connect(self):
                Peer.calls += 1
                self.number += 2
                if Peer.calls == 1:
                    raise ConnectionResetError()
                return self

            def ask(self, operation):
                self.assert_operation = operation
                return {"state": "empty"}

            def close(self):
                pass

        class Journal:
            def __init__(self):
                self.events = []

            def emit(self, kind, value):
                self.events.append((kind, value))

        journal = Journal()
        packet = {"status_readiness_seconds": admission.STATUS_READINESS_SECONDS,
                  "normalizer_retry_seconds": 0}
        with patch.object(admission.package9, "NetworkPeer", Peer), \
                patch.object(admission.time, "monotonic", side_effect=(0, 0, 1)), \
                patch.object(admission.time, "sleep"):
            status = admission.status_with_retry(Path("/tmp"), packet, journal,
                                                 "a" * 32, "sample-0")
        self.assertEqual({"state": "empty"}, status)
        self.assertEqual(["admission_status_wait", "admission_status_ready"],
                         [kind for kind, _ in journal.events])

    def test_campaign_clock_poll_does_not_reuse_transport_backoff(self):
        class Peer:
            def __init__(self, *_):
                self.number = 0
                self.clocks = [
                    {"state": "synchronized", "leap": "normal",
                     "uncertainty_ns": "5000000", "sync_age_ns": "56000000000"},
                    {"state": "synchronized", "leap": "normal",
                     "uncertainty_ns": "5000000", "sync_age_ns": "1000000000"},
                ]

            def connect(self):
                return self

            def ask(self, operation):
                if operation == "STATUS":
                    return {"boot_id": package10.BOOT, "output_active": False,
                            "owner_id": None, "state": "empty"}
                assert operation == "GET_CLOCK"
                return self.clocks.pop(0)

            def close(self):
                pass

        class Journal:
            def __init__(self):
                self.events = []

            def emit(self, kind, value):
                self.events.append((kind, value))

        peer = Peer()
        journal = Journal()
        with patch.object(package11.package9, "NetworkPeer", return_value=peer), \
                patch.object(package11.package9.time, "monotonic",
                             side_effect=(0, 0, 0, 0)), \
                patch.object(package11.package9.time, "sleep") as sleep:
            package11.package9.wait_for_normalizer_readiness(
                Path("/tmp"), {"normalizer_retry_seconds": 30}, journal,
                "a" * 32, "cycle-1", 90)
        sleep.assert_called_once_with(2)
        self.assertEqual([False, True],
                         [value["usable"] for kind, value in journal.events
                          if kind == "normalizer_network_readiness"])

    def test_clock_poll_retest_accepts_protocol_handshake_but_no_mutation(self):
        initial = {"sync_age_ns": str(clock_retest.MINIMUM_INITIAL_AGE_NS)}
        readiness = [{"usable": False, "clock_sync_age_ns": "55000000000"},
                     {"usable": True, "clock_sync_age_ns": "1000000000"}]
        operations = ["HELLO", "CAPS", "STATUS", "GET_CLOCK"]
        self.assertTrue(clock_retest.accepted_clock_poll(
            initial, readiness, operations, True))
        self.assertFalse(clock_retest.accepted_clock_poll(
            initial, readiness, operations + ["LOAD"], True))
        self.assertFalse(clock_retest.accepted_clock_poll(
            initial, readiness, operations, False))

    def test_remote_mdns_response_is_valid_and_does_not_answer_responses(self):
        query = struct.pack("!6H", 12345, 0, 1, 0, 0, 0) + \
            b"\x04time\x05local\x00\x00\x01\x00\x01"
        response = remote.mdns_response(query)
        self.assertEqual({remote.AP_ADDRESS}, set(time_local.mdns_addresses(response)))
        record = response.index(b"\xc0\x0c") + 2
        self.assertEqual((1, 1, 10), struct.unpack_from("!HHI", response, record))
        recursive_query = query[:2] + b"\x01\x00" + query[4:]
        self.assertEqual(0x8500,
                         struct.unpack_from("!H", remote.mdns_response(recursive_query), 2)[0])
        multicast = remote.mdns_response(query, legacy=False)
        self.assertEqual(b"\x00\x00", multicast[:2])
        self.assertEqual({remote.AP_ADDRESS}, set(time_local.mdns_addresses(multicast)))
        self.assertIsNone(remote.mdns_response(response))

    def test_client_is_bound_to_remote_bssid_and_channel(self):
        value = fixture.wpa_config("WsprryPico-Phase115", "a" * 32)
        self.assertIn("bssid=" + package11.REMOTE_AP_MAC + "\n", value)
        self.assertIn("scan_freq=2462\n", value)

    def test_runtime_credentials_are_bound_and_protected_for_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_credentials(root)
            packet = {"credentials": fixture.CREDENTIALS}
            paths = fixture.credential_paths(packet)
            packet["credential_sha256"] = {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in paths}
            for name in paths:
                (root / name).chmod(0o644)
            result = fixture.prepare_runtime_credentials(root, packet)
            self.assertEqual(set(paths), {value["path"] for value in result})
            for name in paths:
                info = (root / name).stat()
                self.assertEqual(0o600, info.st_mode & 0o777)
                self.assertEqual(os.geteuid(), info.st_uid)
            changed = copy.deepcopy(packet)
            changed["credential_sha256"][paths[0]] = "0" * 64
            with self.assertRaises(ValueError):
                fixture.prepare_runtime_credentials(root, changed)
            (root / paths[0]).unlink()
            (root / paths[0]).symlink_to(root / paths[1])
            with self.assertRaises(ValueError):
                fixture.prepare_runtime_credentials(root, packet)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_credentials(root)
            packet = {"credentials": fixture.CREDENTIALS}
            paths = fixture.credential_paths(packet)
            packet["credential_sha256"] = {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in paths}
            browser = root / "credentials/browser"
            for child in browser.iterdir():
                child.unlink()
            browser.rmdir()
            browser.symlink_to(root / "credentials/controller", target_is_directory=True)
            with self.assertRaises(ValueError):
                fixture.prepare_runtime_credentials(root, packet)

    def test_credential_protection_precedes_radio_mutation(self):
        source = Path(fixture.__file__).read_text()
        armed = 'self.intent("cleanup_armed")'
        protected = "protected = prepare_runtime_credentials(self.root, packet)"
        timer = 'self.intent("timer_paused")'
        self.assertLess(source.index(armed), source.index(protected))
        self.assertLess(source.index(protected), source.index(timer))

    def test_staging_credential_hash_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_credentials(root)
            name = fixture.CREDENTIALS["controller"]["key"]
            expected = hashlib.sha256((root / name).read_bytes()).hexdigest()
            self.assertEqual(expected, stage.credential_digest(root, name))
            path = root / name
            path.unlink()
            path.symlink_to(root / fixture.CREDENTIALS["controller"]["cert"])
            with self.assertRaises((OSError, ValueError)):
                stage.credential_digest(root, name)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_credentials(root)
            browser = root / "credentials/browser"
            for child in browser.iterdir():
                child.unlink()
            browser.rmdir()
            browser.symlink_to(root / "credentials/controller", target_is_directory=True)
            with self.assertRaises(ValueError):
                stage.credential_digest(root, fixture.CREDENTIALS["browser"]["key"])

    def test_campaign_budget_is_fresh_and_bounded(self):
        self.assertEqual(package10.RF_JOBS, 16)
        self.assertEqual(package10.RF_DURATION_NS, 356_800_000_000)
        self.assertLess(package10.RF_DURATION_NS, package11.AUTHORIZED_RF_DURATION_NS)
        self.assertEqual(package11.PRIOR_RF_JOBS, 16)
        self.assertEqual(package11.PRIOR_RF_DURATION_NS, 16_000_000_000)
        self.assertEqual(package11.CUMULATIVE_RF_JOBS, 32)
        self.assertEqual(package11.CUMULATIVE_RF_DURATION_NS, 372_800_000_000)
        self.assertNotEqual(package11.RETRY2_AUTHORIZATION, package11.RETRY3_AUTHORIZATION)

    def test_retained_terminal_preflight_waits_without_relaxing_heap_gate(self):
        record = {"job_id": "a" * 32, "state": "complete", "output_active": False,
                  "ended_monotonic_ns": "1000"}

        def value(records):
            return {"info": {"status": {"enabled": False}}, "wtp": {
                "GET_CLOCK": {"monotonic_now_ns": "3599999999900"},
                "STATUS": {"boot_id": package10.BOOT, "owner_id": None,
                    "output_active": False, "terminal_records": records}}}

        class Journal:
            def __init__(self):
                self.events = []

            def emit(self, kind, payload):
                self.events.append((kind, payload))

        packet = {"terminal_retention_preflight": {"timeout_seconds": 600,
            "sample_seconds": 15, "terminal_record_ttl_seconds": 3600,
            "maximum_terminal_records": 8, "sessions": ["1" * 32, "2" * 32]}}
        journal = Journal()
        with patch.object(package11.package9, "inventory",
                          side_effect=(value([record]), value([]))) as inventory, \
                patch.object(package11.time, "monotonic", side_effect=(0, 1)), \
                patch.object(package11.time, "sleep") as sleep:
            package11.wait_for_terminal_retention(Path("/tmp"), packet, journal)
        self.assertEqual(2, inventory.call_count)
        sleep.assert_called_once_with(15)
        self.assertEqual([1, 0], [entry[1]["terminal_records"]
                                  for entry in journal.events])

    def test_retained_terminal_preflight_rejects_unsafe_record(self):
        value = {"info": {"status": {"enabled": False}}, "wtp": {
            "GET_CLOCK": {"monotonic_now_ns": "2000"},
            "STATUS": {"boot_id": package10.BOOT, "owner_id": None,
                "output_active": False, "terminal_records": [{
                    "job_id": "a" * 32, "state": "failed", "output_active": False,
                    "ended_monotonic_ns": "1000"}]}}}
        packet = {"terminal_retention_preflight": {"timeout_seconds": 600,
            "sample_seconds": 15, "terminal_record_ttl_seconds": 3600,
            "maximum_terminal_records": 8, "sessions": ["1" * 32]}}
        class Journal:
            def emit(self, *_):
                pass

        with patch.object(package11.package9, "inventory", return_value=value), \
                patch.object(package11.time, "monotonic", return_value=0), \
                self.assertRaises(ValueError):
            package11.wait_for_terminal_retention(Path("/tmp"), packet, Journal())

    def test_legacy_mapping_does_not_charge_package10_to_package11(self):
        packet = {"authorized_rf_duration_ns": package11.AUTHORIZED_RF_DURATION_NS,
                  "authorized_max_flashes": 0, "authorized_max_bootsel": 0}
        value = package11.legacy_packet(packet)
        self.assertEqual(value["authorized_rf_duration_ns"],
                         package10.AUTHORIZED_RF_DURATION_NS)
        self.assertEqual(value["cumulative_rf_jobs"], package10.CUMULATIVE_RF_JOBS)
        self.assertEqual(packet["authorized_rf_duration_ns"],
                         package11.AUTHORIZED_RF_DURATION_NS)
        self.assertNotIn("cumulative_rf_jobs", packet)

    def test_retry_stage_binds_prior_attempt_and_zero_rf_retest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            make_credentials(root)
            (root / "scripts").mkdir()
            (root / "scripts/phase11_5_package11_fixture.py").write_bytes(
                Path(fixture.__file__).read_bytes())
            wifi = {"ssid": "WsprryPico-Phase115", "password": "a" * 32,
                    "ntp_ipv4": "time.local"}
            (root / "retained-wifi.json").write_text(json.dumps(wifi))
            wifi_hash = hashlib.sha256((json.dumps(wifi, sort_keys=True,
                separators=(",", ":")) + "\n").encode()).hexdigest()
            (root / "remote-ready.json").write_text(json.dumps({
                "host": "wspr4", "ap_mac": package11.REMOTE_AP_MAC,
                "channel": 11, "wifi_sha256": wifi_hash}))
            binary, observer = root / "wsprrypi", root / "observer.so"
            binary.write_bytes(b"binary")
            observer.write_bytes(b"observer")
            admission_path, adversarial_path = root / "admission.json", root / "adv.json"
            admission_value = admission_result()
            admission_path.write_text(json.dumps(admission_value))
            adversarial_value = assess_admission(admission_value)
            adversarial_value["admission_result_sha256"] = hashlib.sha256(
                admission_path.read_bytes()).hexdigest()
            adversarial_path.write_text(json.dumps(adversarial_value))
            prior_path = root / "prior.json"
            prior_path.write_text(json.dumps({
                "schema": "phase11.5-package11-attempt-failure-v1",
                "status": "STOPPED_PRE_CYCLE_CLOCK_POLL_ALIAS",
                "packet_sha256": package11.ATTEMPT1_PACKET_SHA256,
                "actual_budget": {"charged_rf_jobs": package11.ATTEMPT1_RF_JOBS,
                    "charged_rf_duration_ns": package11.ATTEMPT1_RF_DURATION_NS,
                    "automatic_retry_authorized": False},
                "completed_scope": {"r6_credit": False},
                "failure": {"product_failure": False,
                    "resource_result_accepted": False},
                "restoration": {
                    "reservation_released_after_fresh_reconciliation": True,
                    "wspr5_fixture_restored": True,
                    "wspr4_fixture_restored": True}}))
            clock_path = root / "clock.json"
            clock_path.write_text(json.dumps({
                "schema": "phase11.5-package11-clock-poll-retest-result-v1",
                "status": "PASS_ZERO_RF",
                "budget": {"rf_jobs": 0, "rf_duration_ns": 0},
                "finding": {
                    "transport_backoff_separated_from_healthy_stale_clock_polling": True,
                    "fresh_pico_clock_window_observed": True},
                "restoration": {"reservation_released_unchanged": True,
                    "wspr5_fixture_restored": True,
                    "wspr4_fixture_restored": True}}))
            retry1_path = root / "retry1.json"
            retry1_value = json.loads((Path(__file__).resolve().parents[1] /
                "docs/development/phase11-5-package11-retry1-result.json").read_text())
            retry1_path.write_text(json.dumps(retry1_value))
            retry1_adversarial_path = root / "retry1-adversarial.json"
            retry1_adversarial_value = assess_retry1(retry1_value)
            retry1_adversarial_value["result_sha256"] = hashlib.sha256(
                retry1_path.read_bytes()).hexdigest()
            retry1_adversarial_path.write_text(json.dumps(retry1_adversarial_value))
            credential_retest_path = root / "credential-retest.json"
            credential_retest_value = json.loads((Path(__file__).resolve().parents[1] /
                "docs/development/phase11-5-package11-credential-retest-result.json").read_text())
            credential_retest_value["fixture_source_sha256"] = hashlib.sha256(
                Path(fixture.__file__).read_bytes()).hexdigest()
            credential_retest_path.write_text(json.dumps(credential_retest_value))
            retry2_path = root / "retry2.json"
            retry2_value = json.loads((Path(__file__).resolve().parents[1] /
                "docs/development/phase11-5-package11-retry2-result.json").read_text())
            retry2_path.write_text(json.dumps(retry2_value))
            retry2_adversarial_path = root / "retry2-adversarial.json"
            retry2_adversarial_value = assess_retry2(retry2_value)
            retry2_adversarial_value["result_sha256"] = hashlib.sha256(
                retry2_path.read_bytes()).hexdigest()
            retry2_adversarial_path.write_text(json.dumps(retry2_adversarial_value))
            argv = ["stage", "--root", str(root), "--kind", "campaign",
                    "--binary", str(binary), "--observer", str(observer),
                    "--admission-result", str(admission_path),
                    "--admission-adversarial", str(adversarial_path),
                    "--prior-attempt-result", str(prior_path),
                    "--clock-poll-retest-result", str(clock_path),
                    "--retry1-result", str(retry1_path),
                    "--retry1-adversarial", str(retry1_adversarial_path),
                    "--credential-retest-result", str(credential_retest_path),
                    "--retry2-result", str(retry2_path),
                    "--retry2-adversarial", str(retry2_adversarial_path)]
            dependency_hashes = {
                "ADMISSION_RESULT_SHA256": hashlib.sha256(
                    admission_path.read_bytes()).hexdigest(),
                "ADMISSION_ADVERSARIAL_SHA256": hashlib.sha256(
                    adversarial_path.read_bytes()).hexdigest(),
                "ATTEMPT1_RESULT_SHA256": hashlib.sha256(
                    prior_path.read_bytes()).hexdigest(),
                "CLOCK_POLL_RETEST_RESULT_SHA256": hashlib.sha256(
                    clock_path.read_bytes()).hexdigest(),
                "RETRY1_RESULT_SHA256": hashlib.sha256(
                    retry1_path.read_bytes()).hexdigest(),
                "RETRY1_ADVERSARIAL_SHA256": hashlib.sha256(
                    retry1_adversarial_path.read_bytes()).hexdigest(),
                "CREDENTIAL_RETEST_RESULT_SHA256": hashlib.sha256(
                    credential_retest_path.read_bytes()).hexdigest(),
                "RETRY2_RESULT_SHA256": hashlib.sha256(
                    retry2_path.read_bytes()).hexdigest(),
                "RETRY2_ADVERSARIAL_SHA256": hashlib.sha256(
                    retry2_adversarial_path.read_bytes()).hexdigest()}
            with patch.object(sys, "argv", argv), patch.object(stage, "COMMON_INPUTS",
                    ("scripts/phase11_5_package11_fixture.py",)), \
                    patch.object(package11, "ADMISSION_RESULT_SHA256",
                                 dependency_hashes["ADMISSION_RESULT_SHA256"]), \
                    patch.object(package11, "ADMISSION_ADVERSARIAL_SHA256",
                                 dependency_hashes["ADMISSION_ADVERSARIAL_SHA256"]), \
                    patch.object(package11, "ATTEMPT1_RESULT_SHA256",
                                 dependency_hashes["ATTEMPT1_RESULT_SHA256"]), \
                    patch.object(package11, "CLOCK_POLL_RETEST_RESULT_SHA256",
                                 dependency_hashes["CLOCK_POLL_RETEST_RESULT_SHA256"]), \
                    patch.object(package11, "RETRY1_RESULT_SHA256",
                                 dependency_hashes["RETRY1_RESULT_SHA256"]), \
                    patch.object(package11, "RETRY1_ADVERSARIAL_SHA256",
                                 dependency_hashes["RETRY1_ADVERSARIAL_SHA256"]), \
                    patch.object(package11, "CREDENTIAL_RETEST_RESULT_SHA256",
                                 dependency_hashes["CREDENTIAL_RETEST_RESULT_SHA256"]), \
                    patch.object(package11, "RETRY2_RESULT_SHA256",
                                 dependency_hashes["RETRY2_RESULT_SHA256"]), \
                    patch.object(package11, "RETRY2_ADVERSARIAL_SHA256",
                                 dependency_hashes["RETRY2_ADVERSARIAL_SHA256"]), \
                    redirect_stdout(io.StringIO()):
                stage.main()
                packet = json.loads((root / "packet.json").read_text())
                self.assertEqual(package11.RETRY3_AUTHORIZATION, packet["authorization"])
                self.assertEqual(package11.CUMULATIVE_RF_JOBS,
                                 packet["cumulative_package11_rf_jobs"])
                self.assertEqual(hashlib.sha256(prior_path.read_bytes()).hexdigest(),
                                 packet["prior_attempt_result_sha256"])
                self.assertEqual(hashlib.sha256(clock_path.read_bytes()).hexdigest(),
                                 packet["clock_poll_retest_result_sha256"])
                self.assertEqual(hashlib.sha256(retry1_path.read_bytes()).hexdigest(),
                                 packet["retry1_attempt_result_sha256"])
                self.assertEqual(hashlib.sha256(
                    retry1_adversarial_path.read_bytes()).hexdigest(),
                    packet["retry1_adversarial_sha256"])
                self.assertEqual(hashlib.sha256(
                    credential_retest_path.read_bytes()).hexdigest(),
                    packet["credential_retest_result_sha256"])
                self.assertEqual(hashlib.sha256(retry2_path.read_bytes()).hexdigest(),
                                 packet["retry2_attempt_result_sha256"])
                self.assertEqual(hashlib.sha256(
                    retry2_adversarial_path.read_bytes()).hexdigest(),
                    packet["retry2_adversarial_sha256"])
                self.assertEqual(set(fixture.credential_paths(packet)),
                                 set(packet["credential_sha256"]))
                package11.validate(packet)
                credential = next(iter(packet["credential_sha256"]))
                changed = copy.deepcopy(packet)
                changed["credential_sha256"][credential] = "0" * 64
                with self.assertRaises(ValueError):
                    package11.validate(changed)
                for key in ("admission_result_sha256",
                            "admission_adversarial_sha256",
                            "prior_attempt_result_sha256",
                            "clock_poll_retest_result_sha256",
                            "retry1_attempt_result_sha256",
                            "retry1_adversarial_sha256",
                            "credential_retest_result_sha256",
                            "retry2_attempt_result_sha256",
                            "retry2_adversarial_sha256"):
                    changed = copy.deepcopy(packet)
                    changed[key] = "0" * 64
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        package11.validate(changed)
                changed = copy.deepcopy(packet)
                changed["cumulative_package11_rf_jobs"] -= 1
                with self.assertRaises(ValueError):
                    package11.validate(changed)
                changed = copy.deepcopy(packet)
                changed["prior_package11_attempt"]["resource_result_accepted"] = True
                with self.assertRaises(ValueError):
                    package11.validate(changed)
                changed = copy.deepcopy(packet)
                changed["clock_poll_retest"]["status"] = "SKIPPED"
                with self.assertRaises(ValueError):
                    package11.validate(changed)
                changed = copy.deepcopy(packet)
                changed["retry1_package11_attempt"]["production_jobs_armed"] = 1
                with self.assertRaises(ValueError):
                    package11.validate(changed)
                changed = copy.deepcopy(packet)
                changed["credential_retest"]["fixture_source_sha256"] = "0" * 64
                with self.assertRaises(ValueError):
                    package11.validate(changed)
                changed = copy.deepcopy(packet)
                changed["retry2_package11_attempt"]["reservation_acquired"] = True
                with self.assertRaises(ValueError):
                    package11.validate(changed)
                changed = copy.deepcopy(packet)
                changed["terminal_retention_preflight"]["timeout_seconds"] = 599
                with self.assertRaises(ValueError):
                    package11.validate(changed)

    def test_admission_and_closure_mutations_are_all_rejected(self):
        admission_value = admission_result()
        validate_admission_result(admission_value)
        admission_assessment = assess_admission(admission_value)
        self.assertTrue(admission_assessment["all_mutations_rejected"])
        closure_value = closure_result()
        validate_result(closure_value)
        closure_assessment = assess_closure(closure_value)
        self.assertTrue(closure_assessment["all_mutations_rejected"])

    def test_retry3_failure_and_reducer_retest_are_reproducible(self):
        root = Path(__file__).resolve().parents[1] / "docs/development"
        failure_path = root / "phase11-5-package11-retry3-result.json"
        failure_adversarial_path = root / "phase11-5-package11-retry3-adversarial.json"
        failure = validate_retry3(json.loads(failure_path.read_text()))
        failure_assessment = assess_retry3(failure)
        failure_assessment["result_sha256"] = hashlib.sha256(
            failure_path.read_bytes()).hexdigest()
        failure_assessment["adversarial_script_sha256"] = hashlib.sha256(
            Path(sys.modules[assess_retry3.__module__].__file__).read_bytes()).hexdigest()
        self.assertEqual(json.loads(failure_adversarial_path.read_text()),
                         failure_assessment)
        self.assertEqual(failure_assessment["mutation_count"], 35)

        retest_path = root / "phase11-5-package11-retry3-usb-reducer-retest-result.json"
        retest_adversarial_path = (
            root / "phase11-5-package11-retry3-usb-reducer-retest-adversarial.json")
        retest = validate_reducer_retest(json.loads(retest_path.read_text()))
        retest_assessment = assess_reducer_retest(retest)
        retest_assessment["result_sha256"] = hashlib.sha256(
            retest_path.read_bytes()).hexdigest()
        retest_assessment["adversarial_script_sha256"] = hashlib.sha256(
            Path(sys.modules[assess_reducer_retest.__module__].__file__).read_bytes()
        ).hexdigest()
        self.assertEqual(json.loads(retest_adversarial_path.read_text()),
                         retest_assessment)
        self.assertEqual(retest_assessment["mutation_count"], 22)

    def test_remote_packet_rejects_wrong_host_or_unbounded_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            wifi = {"ssid": "WsprryPico-Phase115", "password": "a" * 32,
                    "ntp_ipv4": "time.local"}
            wifi_hash = hashlib.sha256((json.dumps(wifi, sort_keys=True,
                separators=(",", ":")) + "\n").encode()).hexdigest()
            packet = {"schema": "phase11.5-package11-admission-v1",
                "authorization": package11.AUTHORIZATION, "root": str(root),
                "remote_host": "wspr4", "remote_host_boot_id": remote.HOST_BOOT,
                "remote_ap_if": remote.AP_IF, "remote_ap_mac": remote.AP_MAC,
                "client_address": remote.CLIENT_ADDRESS,
                "dut_address": remote.DUT_ADDRESS,
                "time_authority_address": remote.CLIENT_ADDRESS,
                "runtime_seconds": 1200, "restoration_seconds": 900,
                "wifi": wifi, "wifi_sha256": wifi_hash}
            (root / "packet.json").write_text(json.dumps(packet))
            subject = remote.RemoteAp(root)
            self.assertEqual(subject.validate_packet(), packet)
            for key, value in (("remote_host", "elsewhere"),
                               ("runtime_seconds", 7201),
                               ("remote_ap_mac", "00:00:00:00:00:00")):
                changed = copy.deepcopy(packet)
                changed[key] = value
                (root / "packet.json").write_text(json.dumps(changed))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    remote.RemoteAp(root).validate_packet()
            campaign = copy.deepcopy(packet)
            campaign["schema"] = "phase11.5-package11-fixture-v1"
            campaign["authorization"] = package11.RETRY3_AUTHORIZATION
            campaign["runtime_seconds"] = 5400
            (root / "packet.json").write_text(json.dumps(campaign))
            self.assertEqual(remote.RemoteAp(root).validate_packet(), campaign)

    def test_remote_ap_holds_runtime_autoconnect_before_disconnect(self):
        source = Path(remote.__file__).read_text()
        timer = 'run_command(["systemctl", "stop", "pi-wifi-recover.timer"'
        hold = 'run_command(["nmcli", "device", "set", AP_IF, "autoconnect", "no"])'
        down = 'run_command(["nmcli", "--wait", "25", "connection", "down"'
        restore = '["nmcli", "device", "set", AP_IF, "autoconnect", "yes"]'
        self.assertLess(source.index(timer), source.index(hold))
        self.assertLess(source.index(hold), source.index(down))
        self.assertIn(restore, source)
        self.assertIn('["systemctl", "start", "pi-wifi-recover.timer"]', source)

    def test_default_fixture_invocations_are_plan_only(self):
        for module, argv in ((clock_retest,
                              ["clock-retest", "--root", "/absent",
                               "--packet-sha256", "0" * 64]),
                             (fixture, ["fixture", "setup", "--root", "/absent"]),
                             (remote, ["remote", "setup", "--root", "/absent"])):
            with self.subTest(module=module.__name__), \
                    patch.object(sys, "argv", argv), \
                    patch.object(module.os, "geteuid",
                                 side_effect=AssertionError("host accessed")):
                module.main()


if __name__ == "__main__":
    unittest.main()
