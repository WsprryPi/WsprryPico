#!/usr/bin/env python3
"""Freeze the private wspr4 side of a Package 11 fixture packet."""

import argparse
import hashlib
import json
from pathlib import Path

from phase11_5_package11_remote_ap import (AP_IF, AP_MAC, CLIENT_ADDRESS,
    DUT_ADDRESS, HOST_BOOT)


def canonical_wifi(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--kind", choices=("admission", "campaign"), required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    packet_path = root / "packet.json"
    if packet_path.exists():
        raise ValueError("Fresh remote Package 11 packet required")
    wifi = json.loads((root / "retained-wifi.json").read_text())
    runtime = 1200 if args.kind == "admission" else 5400
    schema = ("phase11.5-package11-admission-v1" if args.kind == "admission" else
              "phase11.5-package11-fixture-v1")
    authorization = ("PACKAGE11-TWO-HOST-R6" if args.kind == "admission" else
                     "PACKAGE11-TWO-HOST-R6-RETRY4")
    packet = {"schema": schema, "authorization": authorization,
        "root": str(root), "remote_host": "wspr4", "remote_host_boot_id": HOST_BOOT,
        "remote_ap_if": AP_IF, "remote_ap_mac": AP_MAC,
        "client_address": CLIENT_ADDRESS, "dut_address": DUT_ADDRESS,
        "time_authority_address": CLIENT_ADDRESS, "runtime_seconds": runtime,
        "restoration_seconds": 900, "wifi": wifi,
        "wifi_sha256": hashlib.sha256(canonical_wifi(wifi)).hexdigest()}
    raw = (json.dumps(packet, indent=2) + "\n").encode()
    packet_path.write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    main()
