#!/usr/bin/env python3
"""Build the three-cycle Package 5 reclamation aggregate audit packet."""
import argparse
import hashlib
import json
from pathlib import Path

from phase11_5_package5_plan import BOOT, DEVICE, IMAGE, SOURCE


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--normalizer-root", type=Path, required=True)
    parser.add_argument("--normalizer-packet-sha256", required=True)
    parser.add_argument("--normalizer-rf-packet-sha256", required=True)
    parser.add_argument("--cycle-root", type=Path, action="append", required=True)
    parser.add_argument("--cycle-packet-sha256", action="append", required=True)
    parser.add_argument("--package2-result", type=Path, required=True)
    args = parser.parse_args()
    if len(args.cycle_root) != 3 or len(args.cycle_packet_sha256) != 3:
        raise ValueError("Exactly three reclamation cycles")
    hashes = [args.normalizer_packet_sha256, args.normalizer_rf_packet_sha256,
              *args.cycle_packet_sha256]
    if any(len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
           for value in hashes):
        raise ValueError("Packet SHA-256")
    root = args.root.resolve(strict=True)
    package2 = args.package2_result.resolve(strict=True)
    packet = dict(schema="phase11.5-package5-reclaim-v1",
                  scope="phase11.5-package5-reclaim-v1", root=str(root),
                  source_revision=SOURCE, image_sha256=IMAGE, boot_id=BOOT,
                  device_id=DEVICE,
                  normalizer=dict(root=str(args.normalizer_root.resolve(strict=True)),
                      packet_sha256=args.normalizer_packet_sha256,
                      rf_packet_sha256=args.normalizer_rf_packet_sha256),
                  cycles=[dict(number=n, root=str(path.resolve(strict=True)),
                               packet_sha256=sha)
                          for n, (path, sha) in enumerate(
                              zip(args.cycle_root, args.cycle_packet_sha256), 1)],
                  resource_return_tolerance_bytes=1024,
                  package2_result_path=str(package2),
                  highest_resource_basis=dict(package2_result_sha256=digest(package2),
                      supported_allocator_peak_bytes=148088,
                      overload_allocator_peak_bytes=164296,
                      selected="bounded-overload"))
    packet["stage_sha256"] = {}
    for top in ("scripts", "src", "docs"):
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
