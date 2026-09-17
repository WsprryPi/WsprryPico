#!/usr/bin/env python3
"""Prove that Package 10's raw auditor rejects closure-critical mutations."""

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from audit_phase11_5_package10 import audit


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def linked_directory(source, destination):
    destination.mkdir()
    for child in source.iterdir():
        os.symlink(child, destination / child.name,
                   target_is_directory=child.is_dir())


def materialize(path):
    source = path.resolve(strict=True)
    path.unlink()
    shutil.copy2(source, path)
    return path


def change_json(path, change):
    path = materialize(path)
    value = json.loads(path.read_text())
    change(value)
    path.write_text(json.dumps(value, indent=2) + "\n")


def change_jsonl(path, change):
    path = materialize(path)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    change(rows)
    for index, row in enumerate(rows):
        row["sequence"] = index
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n"
                            for row in rows))


def row(rows, kind, occurrence=0):
    found = [value for value in rows if value["kind"] == kind]
    if len(found) <= occurrence:
        raise ValueError(f"Mutation prerequisite missing: {kind}[{occurrence}]")
    return found[occurrence]


def inventory_finish(rows):
    return row(rows, "finish")["value"]


def mutations():
    def packet(field, value):
        return lambda context: change_json(context["root"] / "packet.json",
            lambda packet_value: packet_value.__setitem__(field, value))

    return [
        ("candidate-source-identity", packet("source_revision", "0" * 40)),
        ("finite-rf-budget", packet("rf_jobs", 17)),
        ("cumulative-rf-budget", packet("cumulative_rf_duration_ns", 360799999999)),
        ("stopped-attempt-binding", lambda c: change_json(c["root"] / "packet.json",
            lambda value: value["prior_attempt"].__setitem__("result_sha256", "0" * 64))),
        ("quiet-schedule", lambda c: change_json(c["root"] / "packet.json",
            lambda value: value["quiet"].__setitem__("final_seconds", 359))),
        ("runtime-source-impact", lambda c: change_json(c["root"] / "packet.json",
            lambda value: value["source_impact"].__setitem__("runtime_source_changes", 1))),
        ("frozen-helper-hash", lambda c: change_json(c["root"] / "packet.json",
            lambda value: value["stage_sha256"].__setitem__(
                "scripts/phase11_5_package10.py", "0" * 64))),
        ("captured-duration-budget", lambda c: change_json(c["root"] / "campaign-result.json",
            lambda value: value.__setitem__("normal_seconds", 1799))),
        ("readiness-service-pause", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "installed_service_paused")["value"]
                .__setitem__("before_memory_readiness", False))),
        ("memory-readiness-admission", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "memory_headroom", -1)["value"].update(
                available_bytes=164999, usable=False))),
        ("warmup-count", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: rows.remove(row(rows, "normalizer_complete", 7)))),
        ("refresh-count", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: rows.remove(row(rows, "normalizer_complete", 12)))),
        ("normalizer-load", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: next(value for value in rows if value["kind"] == "normalizer_tx" and
                value["value"]["request"]["op"] == "LOAD")["value"]["request"]["body"]
                    .__setitem__("total_duration_ns", "999999999"))),
        ("normalizer-adjustment-hash", lambda c: change_jsonl(
            c["root"] / "campaign.jsonl", lambda rows: row(rows, "normalizer_complete", 0)
                ["value"].__setitem__("adjustment_sha256", "0" * 64))),
        ("terminal-class-cardinality", lambda c: change_jsonl(
            c["root"] / "campaign.jsonl", lambda rows: row(rows, "terminal_equivalence")
                ["value"].__setitem__("production_class_records", 2))),
        ("browser-action-count", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: rows.remove(row(rows, "browser_action_start", 47)))),
        ("browser-cadence", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "browser_action_start", 1)["value"]
                .__setitem__("offset_seconds", 31))),
        ("browser-resource", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "browser_get", 0)["value"].__setitem__("path", "/wrong"))),
        ("browser-response", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "browser_get", 0)["value"].__setitem__("status", 503))),
        ("browser-empty-body", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "browser_get", 0)["value"].__setitem__(
                "body_bytes", 0))),
        ("console-observer-gap", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "console_info", 100)["value"].__setitem__(
                "began_monotonic_ns", row(rows, "console_info", 99)["value"]
                    ["began_monotonic_ns"] + 3_000_000_000))),
        ("host-observer-state", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "host_health", 0)["value"].__setitem__(
                "installed_service", "active"))),
        ("production-host-safety", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "production_host_status", 0)["value"]["value"]["host"]
                .__setitem__("safety_fault", True))),
        ("production-host-armed", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: [value["value"]["value"]["host"]["remote"].__setitem__(
                "state", "running") for value in rows
                if value["kind"] == "production_host_status" and
                   value["value"]["cycle"] == 1 and
                   (value["value"]["value"]["host"].get("remote") or {}).get("state") ==
                       "armed"])),
        ("production-lifecycle", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "normal_finish", 0)["value"].__setitem__(
                "states", ["complete"]))),
        ("production-completion-report", lambda c: change_jsonl(
            c["root"] / "campaign.jsonl", lambda rows: row(rows, "normal_finish", 0)
                ["value"]["last_report"].__setitem__("arm_handed_off", False))),
        ("production-completion-identity", lambda c: change_jsonl(
            c["root"] / "campaign.jsonl", lambda rows: row(rows, "normal_finish", 0)
                ["value"]["last_report"].__setitem__("job_id", "0" * 32))),
        ("production-usb-completion", lambda c: change_jsonl(
            c["root"] / "campaign.jsonl", lambda rows: next(value for value in rows
                if value["kind"] == "usb_status" and value["value"]["cycle"] == 1 and
                value["value"]["value"]["state"] == "complete")["value"]["value"]
                .__setitem__("state", "running"))),
        ("production-usb-loaded", lambda c: change_jsonl(
            c["root"] / "campaign.jsonl", lambda rows: next(value for value in rows
                if value["kind"] == "usb_status" and value["value"]["cycle"] == 1 and
                value["value"]["value"]["state"] == "loaded")["value"]["value"]
                .__setitem__("state", "armed"))),
        ("production-launch-schedule", lambda c: change_jsonl(
            c["root"] / "campaign.jsonl", lambda rows: row(rows, "production_start", 0)
                .__setitem__("monotonic_ns", row(rows, "normal_begin", 0)["monotonic_ns"] +
                             59_000_000_000))),
        ("sampled-allocator-failure", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "console_info", 0)["value"]["value"]
                .__setitem__("allocator_failures", "1"))),
        ("sampled-rf-timing", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "console_info", -1)["value"]["value"]
                .__setitem__("rf_max_service_gap_ns", "2849392"))),
        ("quiet-owner", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: next(value for value in rows if value["kind"] == "console_info" and
                value["monotonic_ns"] > row(rows, "quiet_begin", 0)["monotonic_ns"])
                ["value"]["value"]["status"].__setitem__("owner_id", "0" * 32))),
        ("matched-resource-return", lambda c: change_jsonl(c["root"] / "campaign.jsonl",
            lambda rows: row(rows, "resource_window", 1)["value"].__setitem__(
                "heap_allocated_bytes", row(rows, "resource_window", 0)["value"]
                    ["heap_allocated_bytes"] + 1025))),
        ("production-ini-binding", lambda c: materialize(
            c["root"] / "production-1.ini").write_text(
                (c["root"] / "production-1.ini").read_text() + "# mutation\n")),
        ("production-wire", lambda c: mutate_binary(c["root"] / "production-1-tls.bin")),
        ("final-terminal-authority", lambda c: change_jsonl(c["root"] / "final-a.jsonl",
            lambda rows: inventory_finish(rows)["wtp"]["STATUS"]
                .__setitem__("output_active", True))),
        ("final-terminal-set", lambda c: change_jsonl(c["root"] / "final-a.jsonl",
            lambda rows: inventory_finish(rows)["wtp"]["STATUS"]["terminal_records"][0]
                .__setitem__("job_id", "0" * 32))),
        ("final-timing-gate", lambda c: change_jsonl(c["root"] / "final-a.jsonl",
            lambda rows: inventory_finish(rows)["info"].__setitem__(
                "max_refill_irq_to_ready_ns", "2849392"))),
        ("candidate-configuration", lambda c: change_jsonl(c["root"] / "final-a.jsonl",
            lambda rows: inventory_finish(rows)["info"].__setitem__("system_clock_hz", 137999999))),
        ("comparator-identity", lambda c: change_jsonl(c["root"] / "final-b.jsonl",
            lambda rows: inventory_finish(rows)["info"]["status"].__setitem__(
                "boot_id", "0" * 32))),
        ("comparator-source", lambda c: change_jsonl(c["root"] / "final-b.jsonl",
            lambda rows: inventory_finish(rows)["info"].__setitem__(
                "revision", "0" * 12))),
        ("reservation-release", lambda c: change_json(c["reservation"],
            lambda value: value.__setitem__("state", "HELD"))),
        ("fixture-restoration", lambda c: change_json(c["fixture"] / "fixture-state.json",
            lambda value: value.__setitem__("restored", False))),
        ("installed-service-restoration", lambda c: change_jsonl(
            c["fixture"] / "fixture.jsonl", lambda rows: row(rows, "host_restored")
                ["value"].__setitem__("installed_pid", "0"))),
        ("capture-drop", lambda c: mutate_capture_log(c["fixture"] / "capture-ap.log")),
    ]


def mutate_binary(path):
    path = materialize(path)
    value = bytearray(path.read_bytes())
    if not value:
        raise ValueError("Mutation prerequisite missing: production wire")
    value[-1] ^= 1
    path.write_bytes(value)


def mutate_capture_log(path):
    path = materialize(path)
    value = path.read_text()
    if "0 packets dropped by kernel" not in value:
        raise ValueError("Mutation prerequisite missing: capture drop claim")
    path.write_text(value.replace("0 packets dropped by kernel",
                                  "1 packet dropped by kernel", 1))


def run(root, packet_sha, decoder, fixture_root, reservation):
    intact = audit(root, packet_sha, decoder, fixture_root, reservation)
    rejected = []
    for name, change in mutations():
        with tempfile.TemporaryDirectory(prefix="phase11-5-package10-adversarial-") as temp:
            base = Path(temp)
            test_root, test_fixture = base / "root", base / "fixture"
            linked_directory(root, test_root)
            linked_directory(fixture_root, test_fixture)
            test_reservation = base / "reservation.json"
            shutil.copy2(reservation, test_reservation)
            context = {"root": test_root, "fixture": test_fixture,
                       "reservation": test_reservation}
            change(context)
            expected_sha = digest(test_root / "packet.json")
            try:
                audit(test_root, expected_sha, decoder, test_fixture, test_reservation)
            except Exception as error:
                rejected.append({"mutation": name, "rejected": True,
                    "error_type": type(error).__name__, "reason": str(error)})
            else:
                raise ValueError("Adversarial mutation was accepted: " + name)
    return {"schema": "phase11.5-package10-adversarial-v1", "status": "PASS",
        "packet_sha256": packet_sha, "intact_raw_audit_status": intact["status"],
        "mutation_count": len(rejected), "all_mutations_rejected": True,
        "mutations": rejected,
        "adversarial_script_sha256": digest(Path(__file__)),
        "raw_auditor_sha256": digest(Path(audit.__code__.co_filename)),
        "inputs": {"campaign_journal_sha256": digest(root / "campaign.jsonl"),
            "campaign_result_sha256": digest(root / "campaign-result.json"),
            "fixture_state_sha256": digest(fixture_root / "fixture-state.json"),
            "reservation_sha256": digest(reservation)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--decoder", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--reservation", type=Path,
                        default=Path("/home/pi/phase11-5-shared-rf-reservation.json"))
    args = parser.parse_args()
    print(json.dumps(run(args.root.resolve(strict=True), args.packet_sha256,
        args.decoder.resolve(strict=True), args.fixture_root.resolve(strict=True),
        args.reservation.resolve(strict=True)), indent=2))


if __name__ == "__main__":
    main()
