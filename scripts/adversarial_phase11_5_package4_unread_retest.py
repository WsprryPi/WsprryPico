#!/usr/bin/env python3
"""Mutate accepted 2.3e retest evidence and require audit rejection."""

import argparse
import json
from pathlib import Path
import shutil
import tempfile

from audit_phase11_5_package4_unread_retest import audit
from phase11_5_inventory import require


def mutate_json(path, change):
    value = json.loads(path.read_text())
    change(value)
    path.write_text(json.dumps(value, indent=2) + "\n")


def mutate_row(path, kind, change):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    selected = [row for row in rows if row["kind"] == kind]
    require(len(selected) == 1, "Unique adversarial journal row: " + kind)
    change(selected[0])
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n"
                            for row in rows))


def replace(path, old, new):
    value = path.read_text()
    require(old in value, "Adversarial mutation source")
    path.write_text(value.replace(old, new, 1))


def run(root, fixture_root):
    journal = "unread-retest.jsonl"
    mutations = {
        "packet_job_identity": lambda r, f: mutate_json(r / "packet.json",
            lambda v: v["job"].update(job_id="0" * 32)),
        "result_rf_charge": lambda r, f: mutate_json(r / "unread-retest-result.json",
            lambda v: v.update(rf_jobs_charged=0)),
        "unread_start_application_read": lambda r, f: mutate_row(r / journal,
            "usb_unread_start", lambda v: v["value"].update(application_reads=1)),
        "unread_offered_request_floor": lambda r, f: mutate_row(r / journal,
            "usb_unread_offered", lambda v: v["value"].update(complete_requests=15)),
        "unread_hold_duration": lambda r, f: mutate_row(r / journal,
            "usb_unread_hold_complete", lambda v: v["value"].update(hold_seconds=11)),
        "response_deficit": lambda r, f: mutate_row(r / journal,
            "usb_unread_drained", lambda v: v["value"].update(
                response_count=v["value"]["complete_requests"])),
        "host_output_flush_dtr": lambda r, f: mutate_row(r / journal,
            "usb_unread_host_output_flushed",
            lambda v: v["value"].update(dtr_remained_asserted=False)),
        "same_session_silence": lambda r, f: mutate_row(r / journal,
            "usb_unread_silent", lambda v: v["value"].update(received_bytes=1)),
        "completion_output": lambda r, f: mutate_row(r / journal,
            "job_complete", lambda v: v["value"]["status"].update(output_active=True)),
        "final_a_state": lambda r, f: mutate_row(r / "final-a.stdout", "finish",
            lambda v: v["value"]["wtp"]["STATUS"].update(state="running")),
        "reservation_release": lambda r, f: mutate_json(
            r / "rf-reservation-released.json", lambda v: v.update(state="HELD")),
        "fixture_restored": lambda r, f: mutate_json(
            f / "fixture-state.json", lambda v: v.update(restored=False)),
        "fixture_cleanup": lambda r, f: mutate_row(f / "fixture.jsonl", "cleanup",
            lambda v: v["value"].update(failures=["injected"])),
    }
    rejected = []
    for name, mutate in mutations.items():
        with tempfile.TemporaryDirectory(prefix="phase115-p4-retest-adversarial-") as directory:
            temporary = Path(directory)
            candidate_root = temporary / "evidence"
            candidate_fixture = temporary / "fixture"
            shutil.copytree(root, candidate_root)
            shutil.copytree(fixture_root, candidate_fixture)
            mutate(candidate_root, candidate_fixture)
            try:
                audit(candidate_root, candidate_fixture, require_original_paths=False)
            except Exception:
                rejected.append(name)
            else:
                raise ValueError("Mutation accepted: " + name)
    intact = audit(root, fixture_root)
    require(intact["status"] == "PACKAGE4_2_3E_VERIFIED", "Intact accepted evidence")
    require(rejected == list(mutations), "Complete adversarial mutation coverage")
    return {"schema": "phase11.5-package4-unread-retest-adversarial-v1",
            "status": "PASS", "rejected": rejected,
            "mutation_count": len(mutations), "intact_status": intact["status"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.root.resolve(strict=True), args.fixture_root.resolve(strict=True))
    raw = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(raw)
    print(raw, end="")


if __name__ == "__main__":
    main()
