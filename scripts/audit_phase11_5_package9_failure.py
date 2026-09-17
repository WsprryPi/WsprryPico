#!/usr/bin/env python3
"""Audit and sanitize the completed-but-failed Phase 11.5 Package 9 run."""

import argparse
import json
from pathlib import Path

from audit_phase11_5_package9 import digest, finished, rows, values
from phase11_5_inventory import require
from phase11_5_package9 import (B_BOOT, B_DEVICE, BOOT, DEVICE, IMAGE,
    RF_DURATION_NS, SOURCE, validate)


LIMIT_NS = 1_200_000_000_000


def audit(root, packet_sha, fixture_root, reservation_path, attempt_path):
    require(digest(root / "packet.json") == packet_sha, "Failure packet hash")
    validate(json.loads((root / "packet.json").read_text()))
    records = rows(root / "campaign.jsonl")
    failures = values(records, "failure")
    require(len(failures) == 1 and failures[0] is records[-1] and
            failures[0]["value"] == {"type": "ValueError",
                                     "error": "Final terminal/authority"} and
            not values(records, "worker_failure") and
            not values(records, "observer_failure"), "Exact final failure")

    normalizers = values(records, "normalizer_complete")
    begins, finishes = values(records, "normal_begin"), values(records, "normal_finish")
    actions = values(records, "browser_action_finish")
    gets = values(records, "browser_get")
    windows = values(records, "resource_window")
    require(len(normalizers) == 8 and
            [row["value"]["index"] for row in normalizers] == list(range(8)) and
            len(begins) == len(finishes) == 3 and
            [row["value"]["cycle"] for row in finishes] == [1, 2, 3] and
            len(actions) == 48 and len(gets) == 84 and
            all(row["value"]["status"] == 200 and row["value"]["body_bytes"] > 0
                for row in gets), "Completed workload counts")
    for cycle, finish in enumerate(finishes, 1):
        report = finish["value"]["last_report"]
        status = [row["value"]["value"] for row in values(records, "usb_status")
                  if row["value"]["cycle"] == cycle]
        states = {item["state"] for item in status}
        jobs = {item["job_id"] for item in status if item.get("job_id")}
        require({"armed", "running"}.issubset(finish["value"]["states"]) and
                report["outcome"] == "complete" and report["arm_handed_off"] is True and
                report["job_id"] == finish["value"]["job_id"] and
                report["job"]["state"] == "complete" and
                report["job"]["output_active"] is False and
                report["job"]["device_output_active"] is False and
                {"loaded", "armed", "running", "complete"}.issubset(states) and
                jobs == {finish["value"]["job_id"]}, "Completed production lifecycle")

    labels = ["post-warmup-baseline", "post-n1", "post-n2", "post-n3", "final-q"]
    require([row["value"]["label"] for row in windows] == labels and
            [row["value"]["seconds"] for row in windows] == [360, 306, 306, 306, 360] and
            all(row["value"]["output_active"] is False for row in windows),
            "Completed quiet windows")
    heaps = [row["value"]["heap_allocated_bytes"] for row in windows]
    baseline, posts, final_q = heaps[0], heaps[1:4], heaps[4]
    deltas = [value - baseline for value in posts]
    final_delta = final_q - baseline
    require(any(abs(value) > 1024 for value in deltas) and abs(final_delta) > 1024,
            "Expected resource-return failure absent")

    final_a, final_b = finished(root / "final-a.jsonl"), finished(root / "final-b.jsonl")
    a_status, b_status = final_a["wtp"]["STATUS"], final_b["wtp"]["STATUS"]
    require(final_a["info"]["device_id"] == DEVICE and
            final_a["info"]["revision"] == SOURCE[:12] and
            final_a["info"]["status"]["boot_id"] == BOOT and
            a_status["state"] == "empty" and a_status["owner_id"] is None and
            a_status["output_active"] is False and len(a_status["terminal_records"]) == 4 and
            all(record["state"] == "complete" and record["output_active"] is False
                for record in a_status["terminal_records"]), "Final Pico A state")
    require(final_b["info"]["device_id"] == B_DEVICE and
            final_b["info"]["status"]["boot_id"] == B_BOOT and
            b_status["state"] == "empty" and b_status["owner_id"] is None and
            b_status["output_active"] is False, "Final Pico B state")

    reservation = json.loads(Path(reservation_path).read_text())
    fixture = json.loads((fixture_root / "fixture-state.json").read_text())
    fixture_rows = [json.loads(line) for line in
                    (fixture_root / "fixture.jsonl").read_text().splitlines()]
    cleanup = [row for row in fixture_rows if row["kind"] == "cleanup"]
    restored = [row for row in fixture_rows if row["kind"] == "host_restored"]
    require(reservation["state"] == "RELEASED" and
            reservation["packet_sha256"] == packet_sha and fixture.get("restored") is True and
            len(cleanup) == len(restored) == 1 and cleanup[0]["value"]["failures"] == [] and
            str(restored[0]["value"].get("installed_pid", "")).isdigit() and
            int(restored[0]["value"]["installed_pid"]) > 0,
            "Failure-run restoration")

    attempts = json.loads(Path(attempt_path).read_text())
    remaining = LIMIT_NS - attempts["charged_rf_duration_ns"]
    require(attempts["status"] == "PASS" and attempts["attempt_count"] >= 45 and
            attempts["charged_rf_duration_ns"] <= LIMIT_NS and remaining >= 0 and
            remaining < RF_DURATION_NS and attempts["flashes"] == attempts["bootsel"] == 6 and
            attempts["configuration_writes"] == attempts["controlled_reboots"] ==
                attempts["wifi_cycles"] == 0, "Exhausted cumulative Package 9 budget")

    evidence = {name: digest(root / name) for name in
        ("packet.json", "campaign.jsonl", "final-a.jsonl", "final-b.jsonl")}
    evidence["fixture-state.json"] = digest(fixture_root / "fixture-state.json")
    evidence["fixture.jsonl"] = digest(fixture_root / "fixture.jsonl")
    evidence["reservation.json"] = digest(reservation_path)
    evidence["attempt-history.json"] = digest(attempt_path)
    return {"schema": "phase11.5-package9-failure-v1",
        "status": "PACKAGE9_OPEN_R6_RESOURCE_RETURN_FAILED",
        "phase11_5_status": "OPEN_5_OF_6_FAMILIES",
        "packet_sha256": packet_sha,
        "candidate": {"source_revision": SOURCE, "image_sha256": IMAGE,
            "boot_id": BOOT, "device_id": DEVICE, "system_clock_hz": 138000000,
            "engine": "pio-dma-gp2", "renderer": "RAM"},
        "completed_workload": {"normal_load_seconds": 1800, "rf_jobs": 11,
            "planned_rf_duration_ns": RF_DURATION_NS, "normalizer_jobs": 8,
            "production_jobs": 3, "browser_actions": 48, "browser_gets": 84,
            "resource_windows": 5, "production_lifecycles_complete": True},
        "failed_gate": {"name": "matched_resource_return",
            "limit_bytes": 1024, "baseline_bytes": baseline, "post_n_bytes": posts,
            "post_n_deltas_bytes": deltas, "post_n_span_bytes": max(posts) - min(posts),
            "final_q_bytes": final_q, "final_q_delta_bytes": final_delta,
            "final_terminal_records": 4},
        "closure_auditor": {"status": "REJECTED", "reason": "Campaign failure record"},
        "cumulative_budget": {key: attempts[key] for key in
            ("attempt_count", "charged_rf_jobs", "charged_rf_duration_ns", "flashes",
             "bootsel", "configuration_writes", "controlled_reboots", "wifi_cycles")} |
            {"remaining_rf_duration_ns": remaining,
             "complete_retry_duration_ns": RF_DURATION_NS},
        "restoration": {"pico_a_empty_unowned_inactive": True,
            "pico_b_empty_unowned_inactive": True, "reservation_released": True,
            "host_fixture_restored": True, "installed_service_active": True},
        "evidence_sha256": evidence, "auditor_sha256": digest(Path(__file__))}


def validate_result(value):
    require(value.get("schema") == "phase11.5-package9-failure-v1" and
            value.get("status") == "PACKAGE9_OPEN_R6_RESOURCE_RETURN_FAILED" and
            value.get("phase11_5_status") == "OPEN_5_OF_6_FAMILIES",
            "Failure publication status")
    candidate = value.get("candidate", {})
    require(candidate == {"source_revision": SOURCE, "image_sha256": IMAGE,
            "boot_id": BOOT, "device_id": DEVICE, "system_clock_hz": 138000000,
            "engine": "pio-dma-gp2", "renderer": "RAM"}, "Failure candidate")
    workload = value.get("completed_workload", {})
    require(workload == {"normal_load_seconds": 1800, "rf_jobs": 11,
            "planned_rf_duration_ns": RF_DURATION_NS, "normalizer_jobs": 8,
            "production_jobs": 3, "browser_actions": 48, "browser_gets": 84,
            "resource_windows": 5, "production_lifecycles_complete": True},
            "Failure workload")
    gate = value.get("failed_gate", {})
    require(gate.get("name") == "matched_resource_return" and
            gate.get("limit_bytes") == 1024 and len(gate.get("post_n_bytes", [])) == 3 and
            gate.get("post_n_deltas_bytes") ==
                [item - gate["baseline_bytes"] for item in gate["post_n_bytes"]] and
            gate.get("post_n_span_bytes") == max(gate["post_n_bytes"]) -
                min(gate["post_n_bytes"]) and
            gate.get("final_q_delta_bytes") == gate.get("final_q_bytes") -
                gate.get("baseline_bytes") and
            any(abs(item) > 1024 for item in gate["post_n_deltas_bytes"]) and
            abs(gate["final_q_delta_bytes"]) > 1024 and
            gate.get("final_terminal_records") == 4, "Published failed gate")
    budget = value.get("cumulative_budget", {})
    require(budget.get("charged_rf_duration_ns", LIMIT_NS + 1) <= LIMIT_NS and
            budget.get("remaining_rf_duration_ns") == LIMIT_NS -
                budget["charged_rf_duration_ns"] and
            0 <= budget["remaining_rf_duration_ns"] < RF_DURATION_NS and
            budget.get("complete_retry_duration_ns") == RF_DURATION_NS and
            budget.get("flashes") == budget.get("bootsel") == 6 and
            budget.get("configuration_writes") == budget.get("controlled_reboots") ==
                budget.get("wifi_cycles") == 0, "Published exhausted budget")
    require(value.get("closure_auditor") ==
            {"status": "REJECTED", "reason": "Campaign failure record"} and
            value.get("restoration") == {"pico_a_empty_unowned_inactive": True,
                "pico_b_empty_unowned_inactive": True, "reservation_released": True,
                "host_fixture_restored": True, "installed_service_active": True},
            "Published rejection/restoration")
    evidence = value.get("evidence_sha256", {})
    require(set(evidence) == {"packet.json", "campaign.jsonl", "final-a.jsonl",
            "final-b.jsonl", "fixture-state.json", "fixture.jsonl",
            "reservation.json", "attempt-history.json"} and
            all(isinstance(item, str) and len(item) == 64 and item != "0" * 64
                for item in evidence.values()), "Failure evidence hashes")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--reservation", type=Path, required=True)
    parser.add_argument("--attempt-history", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root.resolve(strict=True), args.packet_sha256,
        args.fixture_root.resolve(strict=True), args.reservation.resolve(strict=True),
        args.attempt_history.resolve(strict=True))
    validate_result(result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
