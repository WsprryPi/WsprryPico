#!/usr/bin/env python3
"""Freeze one current-image Package 5 reclamation cycle from retained evidence."""
import argparse
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prior-root", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--fixture-deadline-monotonic-ns", type=int, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--fixture-packet-sha256", required=True)
    parser.add_argument("--client-pid", type=int, required=True)
    parser.add_argument("--client-netns", required=True)
    parser.add_argument("--client-mountns", required=True)
    parser.add_argument("--cycle-number", type=int, choices=(1, 2, 3), required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    prior = args.prior_root.resolve(strict=True)
    sys.path.insert(0, str(root / "scripts"))
    from phase11_5_completion_combined import PACKAGE5_IDENTITY, cases
    from phase11_5_pilot_supervisor import finished

    packet = json.loads(args.template.read_text())
    source, image, boot = PACKAGE5_IDENTITY
    baseline = finished(prior / "final-a.stdout", "READ_ONLY_INVENTORY")["wtp"]["STATUS"]
    seed = uuid.uuid4().hex
    packet.update(root=str(root), source_revision=source, image_sha256=image, boot_id=boot,
                  owner_id=uuid.uuid4().hex, peer_session=uuid.uuid4().hex,
                  inventory_session=uuid.uuid4().hex, b_session=uuid.uuid4().hex,
                  maximum_initial_terminal_records=len(baseline["terminal_records"]),
                  initial_a_state=baseline["state"], initial_a_job_id=baseline["job_id"],
                  initial_terminal_records=baseline["terminal_records"],
                  fixture_root=str(args.fixture_root.resolve(strict=True)),
                  fixture_packet_sha256=args.fixture_packet_sha256,
                  fixture_deadline_monotonic_ns=args.fixture_deadline_monotonic_ns,
                  not_before_host_monotonic_ns=time.monotonic_ns() - 1_000_000_000,
                  continuation_cycle_number=args.cycle_number,
                  post_quiet=dict(seconds=360, sample_interval_seconds=30,
                                  phase=f"cycle-{args.cycle_number}"))
    if len(args.fixture_packet_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in args.fixture_packet_sha256):
        raise ValueError("Fixture packet SHA-256")
    packet["jobs"][0]["job_id"] = uuid.uuid4().hex
    packet["combined"] = {
        "mode": "overload", "seed": seed, "wtp_request_id": uuid.uuid4().hex,
        "cases": cases(seed, "overload"), "minimum_resident_delta_bytes": 32768,
        "wtp_payload_bytes": 32768,
    }
    packet["contention"].update(client_pid=args.client_pid,
                                netns=args.client_netns,
                                mountns=args.client_mountns)
    packet["stage_sha256"] = {}
    for top in ("scripts", "src", "docs", "pi"):
        base = root / top
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                packet["stage_sha256"][str(path.relative_to(root))] = digest(path)
    (root / "packet.json").write_text(json.dumps(packet, indent=2) + "\n")
    print(digest(root / "packet.json"))


if __name__ == "__main__":
    main()
