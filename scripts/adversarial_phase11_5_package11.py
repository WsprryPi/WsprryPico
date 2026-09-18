#!/usr/bin/env python3
"""Mutation assessment for the Package 11 Phase 11.5 closure result."""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from phase11_5_inventory import require
from audit_phase11_5_package11 import validate_result


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def mutations(value):
    result = []

    def add(name, edit):
        candidate = copy.deepcopy(value)
        edit(candidate)
        result.append((name, candidate))

    add("closure", lambda v: v.__setitem__("status", "OPEN"))
    add("phase", lambda v: v.__setitem__("phase11_5_status", "OPEN_5_OF_6"))
    add("r6", lambda v: v["family_status"].__setitem__("R6", "OPEN"))
    add("source", lambda v: v["accepted_configuration"].__setitem__("source_revision", "0" * 40))
    add("boot", lambda v: v["accepted_configuration"].__setitem__("boot_id", "0" * 32))
    add("clock", lambda v: v["accepted_configuration"].__setitem__("system_clock_hz", 132000000))
    add("normal-seconds", lambda v: v["campaign"].__setitem__("normal_load_seconds", 1799))
    add("packet-hash", lambda v: v["campaign"].__setitem__("packet_sha256", "0" * 63))
    add("rf-jobs", lambda v: v["campaign"].__setitem__("rf_jobs", 15))
    add("rf-duration", lambda v: v["campaign"].__setitem__("planned_rf_duration_ns", 1))
    add("warmup", lambda v: v["campaign"].__setitem__("warmup_jobs", 7))
    add("refresh", lambda v: v["campaign"].__setitem__("refresh_jobs", 4))
    add("browser-actions", lambda v: v["campaign"].__setitem__("browser_actions", 47))
    add("browser-gets", lambda v: v["campaign"].__setitem__("browser_gets", 83))
    add("windows", lambda v: v["campaign"].__setitem__("resource_windows", 4))
    add("terminal-count", lambda v: v["campaign"].__setitem__("final_terminal_records", 7))
    add("class-cardinality", lambda v: v["campaign"]["terminal_class_cardinality"].__setitem__("production", 2))
    add("resource-delta", lambda v: v["campaign"].__setitem__("final_q_bytes",
        v["campaign"]["matched_baseline_bytes"] + 1025))
    add("resource-span", lambda v: v["campaign"].__setitem__("maximum_post_span_bytes", 1025))
    add("growth", lambda v: v["campaign"].__setitem__("monotonic_retained_growth", True))
    add("adjustments", lambda v: v["campaign"].__setitem__("maximum_adjustment_sha256",
        v["campaign"]["production_adjustment_sha256"]))
    add("package9", lambda v: v["diagnosis"].__setitem__("package9_failure_preserved", False))
    add("package10", lambda v: v["diagnosis"].__setitem__("package10_fixture_blocker_preserved", False))
    add("package11-attempt1", lambda v: v["diagnosis"].__setitem__(
        "package11_attempt1_failure_preserved", False))
    add("package11-retry1", lambda v: v["diagnosis"].__setitem__(
        "package11_retry1_failure_preserved", False))
    add("package11-retry2", lambda v: v["diagnosis"].__setitem__(
        "package11_retry2_failure_preserved", False))
    add("credential-retest", lambda v: v["diagnosis"].__setitem__(
        "credential_owner_repair_zero_rf_verified", False))
    add("clock-poll-retest", lambda v: v["diagnosis"].__setitem__(
        "clock_poll_repair_zero_rf_verified", False))
    add("retention-preflight", lambda v: v["diagnosis"].__setitem__(
        "terminal_retention_preflight_verified", False))
    add("threshold", lambda v: v["diagnosis"].__setitem__("resource_limit_bytes", 16384))
    add("source-impact", lambda v: v["source_impact"].__setitem__("runtime_source_changes", 1))
    add("admission", lambda v: v["fixture"].__setitem__("zero_rf_admission", "SKIPPED"))
    add("ap-host", lambda v: v["fixture"].__setitem__("ap_host", "wspr5"))
    add("ap-mac", lambda v: v["fixture"].__setitem__("ap_mac", "00:00:00:00:00:00"))
    add("client-mac", lambda v: v["fixture"].__setitem__("client_mac", "00:00:00:00:00:00"))
    add("remote-restoration", lambda v: v["fixture"].__setitem__("wspr4_restored", False))
    add("budget", lambda v: v["budget"].__setitem__("authorized_rf_duration_ns", 999999999999))
    add("charge", lambda v: v["budget"].__setitem__("charged_rf_jobs", 15))
    add("prior-charge", lambda v: v["budget"].__setitem__(
        "prior_attempt_charged_rf_jobs", 7))
    add("retry1-charge", lambda v: v["budget"].__setitem__(
        "retry1_charged_rf_jobs", 7))
    add("retry2-charge", lambda v: v["budget"].__setitem__(
        "retry2_charged_rf_jobs", 1))
    add("cumulative-charge", lambda v: v["budget"].__setitem__(
        "cumulative_package11_rf_jobs", 23))
    add("flash", lambda v: v["budget"].__setitem__("flashes", 1))
    add("reservation", lambda v: v["restoration"].__setitem__("reservation_released", False))
    add("pico-active", lambda v: v["restoration"].__setitem__("pico_a_inactive", False))
    add("wspr5-restoration", lambda v: v["restoration"].__setitem__("wspr5_fixture_restored", False))
    add("capture-drop", lambda v: v["restoration"].__setitem__("capture_drops", 1))
    add("raw-hash", lambda v: v.__setitem__("raw_audit_sha256", "0" * 63))
    add("admission-result-hash", lambda v: v.__setitem__(
        "admission_result_sha256", "0" * 64))
    add("admission-adversarial-hash", lambda v: v.__setitem__(
        "admission_adversarial_sha256", "0" * 64))
    add("prior-attempt-hash", lambda v: v.__setitem__(
        "prior_attempt_result_sha256", "0" * 63))
    add("clock-retest-hash", lambda v: v.__setitem__(
        "clock_poll_retest_result_sha256", "0" * 63))
    add("retry1-result-hash", lambda v: v.__setitem__(
        "retry1_attempt_result_sha256", "0" * 64))
    add("retry1-adversarial-hash", lambda v: v.__setitem__(
        "retry1_adversarial_sha256", "0" * 64))
    add("credential-retest-hash", lambda v: v.__setitem__(
        "credential_retest_result_sha256", "0" * 64))
    add("retry2-result-hash", lambda v: v.__setitem__(
        "retry2_attempt_result_sha256", "0" * 64))
    add("retry2-adversarial-hash", lambda v: v.__setitem__(
        "retry2_adversarial_sha256", "0" * 64))
    add("evidence-hash", lambda v: v["evidence_sha256"].__setitem__(
        next(iter(v["evidence_sha256"])), "0" * 63))
    return result


def assess(value):
    validate_result(value)
    outcomes = []
    for name, candidate in mutations(value):
        try:
            validate_result(candidate)
        except Exception as error:
            outcomes.append({"name": name, "rejected": True,
                             "error_type": type(error).__name__})
        else:
            outcomes.append({"name": name, "rejected": False})
    require(all(item["rejected"] for item in outcomes), "Package 11 mutation accepted")
    validate_result(value)
    return {"schema": "phase11.5-package11-adversarial-v1", "status": "PASS",
        "mutation_count": len(outcomes), "all_mutations_rejected": True,
        "mutations": outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = json.loads(args.result.read_text())
    result = assess(value)
    result["result_sha256"] = digest(args.result)
    result["adversarial_script_sha256"] = digest(Path(__file__))
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
