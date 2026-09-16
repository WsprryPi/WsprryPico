#!/usr/bin/env python3
"""Mutate the rejected 2.3e retest evidence and require audit rejection."""

import argparse
import json
from pathlib import Path
import shutil
import tempfile

from audit_phase11_5_package4_unread_retest_failure import audit
from phase11_5_inventory import require


def replace(path, old, new):
    value = path.read_text()
    require(old in value, "Adversarial mutation source")
    path.write_text(value.replace(old, new, 1))


def run(root, fixture_root):
    mutations = {
        "packet_job": lambda r, f: replace(r / "packet.json",
            "eda66092283064e6539f8ffd59e3cb9d", "0da66092283064e6539f8ffd59e3cb9d"),
        "runner_network_state": lambda r, f: replace(r / "unread-retest.jsonl",
            '\"state\":\"running\"', '\"state\":\"armed\"'),
        "runner_result_overclaim": lambda r, f: replace(r / "unread-retest-result.json",
            "STOPPED_FINAL_STATE_UNVERIFIED", "CAPTURED_REQUIRES_AUDIT"),
        "completion_output": lambda r, f: replace(r / "post-completion-a.jsonl",
            '\"output_active\": false', '\"output_active\": true'),
        "recovery_operation": lambda r, f: replace(r / "post-failure-release.jsonl",
            '\"op\":\"RELEASE\"', '\"op\":\"ABORT\"'),
        "final_a_state": lambda r, f: replace(r / "reconciled-a.stdout",
            '\"state\": \"empty\"', '\"state\": \"running\"'),
        "reservation_state": lambda r, f: replace(r / "rf-reservation-reconciled.json",
            '\"state\": \"RELEASED\"', '\"state\": \"HELD\"'),
        "fixture_restored": lambda r, f: replace(f / "fixture-state.json",
            '\"restored\": true', '\"restored\": false'),
        "fixture_cleanup": lambda r, f: replace(f / "fixture.jsonl",
            '\"failures\": []', '\"failures\": [\"injected\"]'),
        "client_capture": lambda r, f: (f / "capture-client.pcap").write_bytes(
            (f / "capture-client.pcap").read_bytes() + b"injected"),
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
    require(intact["status"] == "RETEST_FAILURE_VERIFIED", "Intact failure evidence")
    return {"schema": "phase11.5-package4-unread-retest-failure-adversarial-v1",
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
