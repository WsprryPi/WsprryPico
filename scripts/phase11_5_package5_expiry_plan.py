#!/usr/bin/env python3
"""Freeze the real Package 5 terminal-expiry packet from the third cycle."""
import argparse
import hashlib
import json
from pathlib import Path
import uuid

from phase11_5_package5_plan import (BOOT, DEVICE, IMAGE, SOURCE, expiry_cases)
from phase11_5_pilot_supervisor import finished


PRIVATE = (
    "credentials/browser/client-ca.crt",
    "credentials/browser/client.crt",
    "credentials/browser/client.key",
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prior-root", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--fixture-packet-sha256", required=True)
    parser.add_argument("--fixture-extension-packet-sha256", required=True)
    parser.add_argument("--fixture-deadline-monotonic-ns", type=int, required=True)
    parser.add_argument("--client-pid", type=int, required=True)
    parser.add_argument("--client-netns", required=True)
    parser.add_argument("--client-mountns", required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    prior = args.prior_root.resolve(strict=True)
    records = finished(prior / "final-a.stdout", "READ_ONLY_INVENTORY")["wtp"]["STATUS"][
        "terminal_records"]
    if len(records) != 8 or any(record["state"] != "complete" or
                                record["output_active"] is not False for record in records):
        raise ValueError("Expiry requires eight complete inactive terminal records")
    seed = uuid.uuid4().hex
    packet = dict(schema="phase11.5-package5-terminal-expiry-v2",
                  scope="phase11.5-package5-terminal-expiry-v2",
                  policy="phase115-package5-terminal-expiry-v1", root=str(root),
                  source_revision=SOURCE, image_sha256=IMAGE, boot_id=BOOT,
                  device_id=DEVICE, host_boot_id="220e53ca-ca95-4206-9581-dbe28aa1eeb8",
                  address="10.77.15.10", port=18443,
                  client_pid=args.client_pid, client_netns=args.client_netns,
                  client_mountns=args.client_mountns,
                  fixture_root=str(args.fixture_root.resolve(strict=True)),
                  fixture_packet_sha256=args.fixture_packet_sha256,
                  fixture_extension_packet_sha256=args.fixture_extension_packet_sha256,
                  fixture_deadline_monotonic_ns=args.fixture_deadline_monotonic_ns,
                  runtime_seconds=3900, restoration_seconds=150,
                  configuration_writes=0, controlled_reboots=0, wifi_cycles=0,
                  flashes=0, rf_jobs=0,
                  terminal_expiry=dict(seed=seed, cases=expiry_cases(seed), terminal_entries=8,
                      source_ttl_seconds=3600, quiet_seconds=3660,
                      authenticated_recovery_seconds=15,
                      initial_terminal_records=records))
    hashes = [args.fixture_packet_sha256, args.fixture_extension_packet_sha256]
    if any(len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
           for value in hashes):
        raise ValueError("Fixture packet SHA-256")
    packet["stage_sha256"] = {}
    for top in ("scripts", "src", "docs"):
        base = root / top
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                packet["stage_sha256"][str(path.relative_to(root))] = digest(path)
    packet["private_input_sha256"] = {name: digest(root / name) for name in PRIVATE}
    (root / "packet.json").write_text(json.dumps(packet, indent=2) + "\n")
    print(digest(root / "packet.json"))


if __name__ == "__main__":
    main()
