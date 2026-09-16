#!/usr/bin/env python3
"""Reject targeted mutations of a retained Package 4 evidence packet."""

import argparse
import copy
import json
from pathlib import Path
import shutil
import tempfile

from audit_phase11_5_package4_usb import audit
from phase11_5_inventory import require


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def rows(root):
    return [json.loads(line) for line in (root / "package4.jsonl").read_text().splitlines()]


def write_rows(root, value):
    for sequence, row in enumerate(value):
        row["sequence"] = sequence
    (root / "package4.jsonl").write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in value))


def packet_identity(root, reconcile):
    packet = read_json(root / "packet.json")
    packet["source_revision"] = "f" * 40
    write_json(root / "packet.json", packet)


def staged_source(root, reconcile):
    with (root / "src/wtp/frame_parser.cpp").open("a") as stream:
        stream.write("\n")


def tls_peer(root, reconcile):
    value = rows(root)
    next(row for row in value if row["kind"] == "network_tls")["value"]["peer_sha256"] = "0" * 64
    write_rows(root, value)


def raw_network(root, reconcile):
    value = rows(root)
    row = next(row for row in value if row["kind"] == "network_rx")
    raw = bytearray.fromhex(row["value"]["hex"])
    raw[-1] ^= 1
    row["value"]["hex"] = raw.hex()
    write_rows(root, value)


def raw_console(root, reconcile):
    value = rows(root)
    row = next(row for row in value if row["kind"] == "console_rx")
    raw = bytearray.fromhex(row["value"]["value"]["hex"])
    raw[-1] ^= 1
    row["value"]["value"]["hex"] = raw.hex()
    write_rows(root, value)


def parser_wire(root, reconcile):
    value = rows(root)
    next(row for row in value if row["kind"] == "usb_parser_start")["value"]["wire_bytes"] -= 1
    write_rows(root, value)


def raw_parser_response(root, reconcile):
    value = rows(root)
    row = next(row for row in value if row["kind"] == "usb_parser_rx")
    raw = bytearray.fromhex(row["value"]["hex"])
    raw[-1] ^= 1
    row["value"]["hex"] = raw.hex()
    write_rows(root, value)


def parser_recovery_removed(root, reconcile):
    write_rows(root, [row for row in rows(root) if row["kind"] != "usb_parser_recovery"])


def fabricated_unread_proof(root, reconcile):
    value = rows(root)
    finish = next(index for index, row in enumerate(value) if row["kind"] == "finishing")
    prior = value[finish - 1]
    value.insert(finish, {"sequence": 0, "kind": "usb_unread_silent",
        "value": {"probe_hex": "", "silence_seconds": 2, "received_bytes": 0},
        "monotonic_ns": prior["monotonic_ns"], "utc_ns": prior["utc_ns"]})
    write_rows(root, value)


def failure_reason(root, reconcile):
    value = rows(root)
    next(row for row in value if row["kind"] == "failure")["value"]["error"] = "changed"
    write_rows(root, value)


def result_overclaim(root, reconcile):
    result = read_json(root / "package4-result.json")
    result["status"] = "CAPTURED_REQUIRES_AUDIT"
    result["faults"] = []
    write_json(root / "package4-result.json", result)
    value = rows(root)
    value[-1]["value"] = copy.deepcopy(result)
    write_rows(root, value)


def reconciliation_state(root, reconcile):
    result = read_json(reconcile / "result.json")
    result["reservation_released"] = False
    write_json(reconcile / "result.json", result)


def reservation_packet(root, reconcile):
    result = read_json(reconcile / "rf-reservation-released.json")
    result["packet_sha256"] = "0" * 64
    write_json(reconcile / "rf-reservation-released.json", result)


MUTATIONS = {
    "packet-identity": packet_identity,
    "staged-source": staged_source,
    "tls-peer": tls_peer,
    "raw-network": raw_network,
    "raw-console": raw_console,
    "parser-wire": parser_wire,
    "raw-parser-response": raw_parser_response,
    "parser-recovery-removed": parser_recovery_removed,
    "fabricated-unread-proof": fabricated_unread_proof,
    "failure-reason": failure_reason,
    "result-overclaim": result_overclaim,
    "reconciliation-state": reconciliation_state,
    "reservation-packet": reservation_packet,
}


def run(root, reconciliation_root):
    intact = audit(root, reconciliation_root)
    require(intact["status"] == "PACKAGE4_PARTIAL_VERIFIED", "Intact Package 4 audit")
    rejected = []
    with tempfile.TemporaryDirectory(prefix="phase11-5-package4-adversarial-") as directory:
        base = Path(directory)
        for name, mutate in MUTATIONS.items():
            candidate = base / (name + "-main")
            reconcile = base / (name + "-reconcile")
            shutil.copytree(root, candidate, symlinks=True)
            shutil.copytree(reconciliation_root, reconcile, symlinks=True)
            mutate(candidate, reconcile)
            try:
                audit(candidate, reconcile)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                rejected.append(name)
            else:
                raise ValueError("Adversarial mutation accepted: " + name)
            shutil.rmtree(candidate)
            shutil.rmtree(reconcile)
    require(rejected == list(MUTATIONS), "Package 4 mutation coverage")
    return {"schema": "phase11.5-package4-adversarial-v1", "status": "PASS",
            "intact_status": intact["status"], "rejected_count": len(rejected),
            "rejected_mutations": rejected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--reconciliation-root", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root.resolve(strict=True), args.reconciliation_root.resolve(strict=True))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
