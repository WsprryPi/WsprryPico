#!/usr/bin/env python3
"""Build a quiet-only packet bound to an accepted Package 5 predecessor."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--predecessor-root", type=Path, required=True)
    parser.add_argument("--predecessor-packet-sha256", required=True)
    parser.add_argument("--predecessor-audit", type=Path, required=True)
    parser.add_argument("--phase", required=True,
                        choices=("normalizer", "cycle-1", "cycle-2", "cycle-3"))
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    predecessor = args.predecessor_root.resolve(strict=True)
    template = json.loads(args.template.resolve(strict=True).read_text())
    packet = dict(schema="phase11.5-package5-quiet-v1",
                  scope="phase11.5-package5-quiet-v1", root=str(root),
                  source_revision=template["source_revision"],
                  image_sha256=template["image_sha256"], boot_id=template["boot_id"],
                  device_id=template["device_id"], host_boot_id=template["host_boot_id"],
                  fixture_root=template["fixture_root"],
                  fixture_packet_sha256=template["fixture_packet_sha256"],
                  fixture_deadline_monotonic_ns=template["fixture_deadline_monotonic_ns"],
                  runtime_seconds=390, restoration_seconds=template["restoration_seconds"],
                  rf_jobs=0, wifi_cycles=0, flashes=0, configuration_writes=0,
                  controlled_reboots=0,
                  post_quiet=dict(seconds=360, sample_interval_seconds=30,
                                  phase=args.phase),
                  quiet_predecessor=dict(root=str(predecessor),
                      packet_sha256=args.predecessor_packet_sha256,
                      audit_sha256=digest(args.predecessor_audit.resolve(strict=True))))
    if len(args.predecessor_packet_sha256) != 64 or any(
            c not in "0123456789abcdef" for c in args.predecessor_packet_sha256):
        raise ValueError("Predecessor packet SHA-256")
    packet["stage_sha256"] = {}
    for path in sorted((root / "scripts").glob("*.py")):
        packet["stage_sha256"][str(path.relative_to(root))] = digest(path)
    (root / "packet.json").write_text(json.dumps(packet, indent=2) + "\n")
    print(digest(root / "packet.json"))


if __name__ == "__main__":
    main()
