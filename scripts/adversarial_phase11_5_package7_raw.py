#!/usr/bin/env python3
"""Alter private Package 7 evidence copies and require audit rejection."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from audit_phase11_5_package7 import audit


def rewrite_jsonl(path, select, change):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    matches = [row for row in rows if select(row)]
    if len(matches) != 1:
        raise AssertionError(f"Expected one mutation target in {path}: {len(matches)}")
    change(matches[0])
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows))


def edit_value(path, kind, change, occurrence=0):
    seen = 0

    def select(row):
        nonlocal seen
        if row["kind"] != kind:
            return False
        if seen == occurrence:
            seen += 1
            return True
        seen += 1
        return False

    rewrite_jsonl(path, select, lambda row: change(row["value"]))


def verify(root, decoder, fixture_root, expected):
    result = audit(root, decoder, fixture_root)
    if result != expected:
        raise ValueError("Raw audit differs from immutable sanitized result")


def assess(root, decoder, fixture_root, expected):
    verify(root, decoder, fixture_root, expected)

    def packet(field, value):
        def mutation(evidence, _fixture):
            path = evidence / "packet.json"
            data = json.loads(path.read_text())
            data[field] = value
            path.write_text(json.dumps(data, indent=2) + "\n")
        return mutation

    mutations = {
        "wrong-source": packet("source_revision", "0" * 40),
        "wrong-image": packet("image_sha256", "0" * 64),
        "wrong-boot": packet("boot_id", "0" * 32),
        "wrong-session": packet("network_session", "0" * 32),
        "wrong-job": packet("direct_job_id", "0" * 32),
        "budget-inflation": packet("rf_jobs", 17),
        "incomplete-write": lambda evidence, _fixture: edit_value(
            evidence / "direct.jsonl", "lost_write_complete",
            lambda value: value.update(bytes=value["bytes"] - 1)),
        "request-framing": lambda evidence, _fixture:
            (evidence / "load-request.bin").write_bytes(
                (evidence / "load-request.bin").read_bytes() + b"x"),
        "delivered-lost-reply": lambda evidence, _fixture: edit_value(
            evidence / "direct.jsonl", "lost_write_complete",
            lambda value: value.update(delivered_reply_bytes=1)),
        "capture-loss": lambda evidence, _fixture:
            (evidence / "load-capture.log").write_text(
                (evidence / "load-capture.log").read_text().replace(
                    "0 packets dropped by kernel", "1 packets dropped by kernel")),
        "client-response-ack": lambda evidence, _fixture:
            (evidence / "load-packets.txt").write_text(
                (evidence / "load-packets.txt").read_text() +
                "2099-01-01 00:00:00.000000 IP (proto TCP (6), length 40)\n"
                "    10.77.15.2.51422 > 10.77.15.10.18443: Flags [.], "
                "seq 446, ack 54, win 57486, length 0\n"),
        "foreign-success": lambda evidence, _fixture: edit_value(
            evidence / "direct.jsonl", "foreign_rejected",
            lambda value: value["error"].update(code="OK")),
        "changed-owner": lambda evidence, _fixture: edit_value(
            evidence / "direct.jsonl", "lost_independent_effect",
            lambda value: value["status"].update(owner_id="0" * 32)),
        "accepted-storage-write": lambda evidence, _fixture: edit_value(
            evidence / "direct.jsonl", "http",
            lambda value: value.update(status=200), occurrence=2),
        "production-missing-abort": lambda evidence, _fixture: edit_value(
            evidence / "running/production.jsonl", "browser_abort_response",
            lambda value: value.update(status=409)),
        "production-not-active": lambda evidence, _fixture: edit_value(
            evidence / "running/production.jsonl", "production_selected_state",
            lambda value: value["status"].update(output_active=False)),
        "wrong-production-owner": lambda evidence, _fixture: edit_value(
            evidence / "armed/production.jsonl", "production_selected_state",
            lambda value: value["host"].update(owns=False)),
        "false-terminal": lambda evidence, _fixture: edit_value(
            evidence / "running/production.jsonl", "production_pass",
            lambda value: value["terminal"].update(state="completed")),
        "production-wire-truncation": lambda evidence, _fixture:
            (evidence / "running/production-tls.bin").write_bytes(
                (evidence / "running/production-tls.bin").read_bytes()[:-1]),
        "incomplete-restoration": lambda _evidence, fixture:
            (fixture / "fixture-state.json").write_text(json.dumps(
                {**json.loads((fixture / "fixture-state.json").read_text()),
                 "restored": False}, indent=2) + "\n"),
        "final-active-output": lambda evidence, _fixture: edit_value(
            evidence / "final-a.jsonl", "finish",
            lambda value: value["wtp"]["STATUS"].update(
                state="running", output_active=True)),
    }

    rejected = []
    for name, mutate in mutations.items():
        with tempfile.TemporaryDirectory(prefix="phase11-5-package7-adversarial-") as temporary:
            temporary = Path(temporary)
            evidence = temporary / "evidence"
            fixture = temporary / "fixture"
            shutil.copytree(root, evidence)
            shutil.copytree(fixture_root, fixture)
            mutate(evidence, fixture)
            try:
                verify(evidence, decoder, fixture, expected)
            except (AssertionError, KeyError, TypeError, ValueError, RuntimeError):
                rejected.append(name)
            else:
                raise AssertionError("Raw mutation survived: " + name)
    if rejected != list(mutations):
        raise AssertionError("Raw mutation rejection order/count drift")
    verify(root, decoder, fixture_root, expected)
    return {
        "schema": "phase11.5-package7-raw-adversarial-v1",
        "status": "PASS",
        "intact_raw_before": "PASS",
        "mutations": len(mutations),
        "rejected": rejected,
        "intact_raw_after": "PASS",
        "device_or_network_operations": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--decoder", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    args = parser.parse_args()
    expected = json.loads(args.expected.read_text())
    print(json.dumps(assess(args.root, args.decoder, args.fixture_root, expected), indent=2))


if __name__ == "__main__":
    main()
