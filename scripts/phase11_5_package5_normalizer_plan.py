#!/usr/bin/env python3
"""Freeze the authorized eight-job Package 5 cache normalizer packet."""
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
    parser.add_argument("--prior-inventory", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--fixture-packet-sha256", required=True)
    parser.add_argument("--fixture-deadline-monotonic-ns", type=int, required=True)
    args = parser.parse_args()
    if len(args.fixture_packet_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in args.fixture_packet_sha256):
        raise ValueError("Fixture packet SHA-256")
    root = args.root.resolve(strict=True)
    sys.path.insert(0, str(root / "scripts"))
    from phase11_5_package5_plan import (BOOT, IMAGE, NORMALIZER_POLICY, SOURCE,
                                        normalizer_jobs)
    from phase11_5_pilot_supervisor import finished

    packet = json.loads(args.template.read_text())
    baseline = finished(args.prior_inventory.resolve(strict=True),
                        "READ_ONLY_INVENTORY")["wtp"]["STATUS"]
    seed = uuid.uuid4().hex
    packet.update(root=str(root), source_revision=SOURCE, image_sha256=IMAGE,
                  boot_id=BOOT, closure_policy=NORMALIZER_POLICY,
                  owner_id=uuid.uuid4().hex, peer_session=uuid.uuid4().hex,
                  inventory_session=uuid.uuid4().hex, b_session=uuid.uuid4().hex,
                  initial_a_state=baseline["state"],
                  initial_a_job_id=baseline["job_id"],
                  initial_terminal_records=baseline["terminal_records"],
                  maximum_initial_terminal_records=len(baseline["terminal_records"]),
                  normalizer_seed=seed, jobs=normalizer_jobs(seed),
                  normalization=dict(entries=8, events_per_job=512,
                      duration_ns="1000000000", event_duration_ns="1953125",
                      frequencies_nhz=["135500000000000", "135495000000000"]),
                  post_quiet=dict(seconds=360, sample_interval_seconds=30,
                                  phase="normalizer"),
                  runtime_seconds=720, restoration_seconds=150,
                  maximum_renewals=2, rf_jobs=8, wifi_cycles=0, flashes=0,
                  configuration_writes=0, controlled_reboots=0,
                  fixture_root=str(args.fixture_root.resolve(strict=True)),
                  fixture_packet_sha256=args.fixture_packet_sha256,
                  fixture_deadline_monotonic_ns=args.fixture_deadline_monotonic_ns,
                  not_before_host_monotonic_ns=time.monotonic_ns() - 1_000_000_000)
    for key in ("terminal_capacity", "terminal_seed"):
        packet.pop(key, None)
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
