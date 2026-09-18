#!/usr/bin/env python3
"""Bounded Phase 11.6 adapter for the accepted wspr5 Package 11 fixture.

The closed Package 11 implementation remains unchanged.  This adapter gives a
new campaign its own packet schema, unit/namespace names and six-hour ceiling
while deliberately reusing the reviewed setup, verification and restoration
code.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys

import phase11_5_package11_fixture as package11


SCHEMA = "phase11.6-fixture-v1"
AUTHORIZATION = "PHASE11.6-CONDUCTED-RF-20260918"
MAX_RUNTIME_SECONDS = 21_600
MAX_RESTORATION_SECONDS = 900
PREFIX = "phase116-campaign"
PLAN_SHA256 = {
    "ea512b70a786c46fbe15f769b327139d69ad3b0cae984b3622d79f145a076c53",
    "9324f6057ae8f4e552375919836bbe4e0c30176405eedaf3915f0ab67d929556",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def configure_module():
    package11.PREFIX = PREFIX
    package11.NETNS = PREFIX + "-client"
    package11.__file__ = __file__


class Fixture(package11.Fixture):
    def validate_packet(self):
        packet = self.packet
        require(
            packet.get("schema") == SCHEMA
            and packet.get("authorization") == AUTHORIZATION
            and packet.get("root") == str(self.root)
            and packet.get("host_boot_id") == package11.HOST_BOOT
            and packet.get("client_if") == package11.CLIENT_IF
            and packet.get("client_mac") == package11.CLIENT_MAC
            and packet.get("remote_ap_mac") == package11.REMOTE_AP_MAC
            and packet.get("client_address") == package11.CLIENT_ADDRESS
            and packet.get("time_authority_address") == package11.TIME_ADDRESS
            and type(packet.get("network_runtime_seconds")) is int
            and 0 < packet["network_runtime_seconds"] <= MAX_RUNTIME_SECONDS
            and type(packet.get("network_restoration_seconds")) is int
            and 0 < packet["network_restoration_seconds"] <= MAX_RESTORATION_SECONDS,
            "Phase 11.6 local fixture packet",
        )
        wifi = packet.get("wifi")
        require(
            isinstance(wifi, dict)
            and wifi.get("ssid") == "WsprryPico-Phase115"
            and wifi.get("ntp_ipv4") == "time.local"
            and isinstance(wifi.get("password"), str)
            and len(wifi["password"]) == 32,
            "Phase 11.6 retained Wi-Fi identity",
        )
        require(packet.get("plan_sha256") in PLAN_SHA256,
                "Phase 11.6 immutable plan lineage")
        paths = package11.credential_paths(packet)
        require(
            set(packet.get("credential_sha256", {})) == set(paths),
            "Phase 11.6 credential binding",
        )
        for relative in paths:
            path = self.root / relative
            require(
                path.is_file()
                and not path.is_symlink()
                and hashlib.sha256(path.read_bytes()).hexdigest()
                == packet["credential_sha256"][relative],
                "Phase 11.6 credential identity",
            )
        attestation = json.loads((self.root / "remote-ready.json").read_text())
        require(
            attestation == packet.get("remote_ready")
            and attestation.get("schema")
            == "phase11.5-package11-remote-ap-ready-v1"
            and attestation.get("host") == "wspr4"
            and attestation.get("ap_mac") == package11.REMOTE_AP_MAC
            and attestation.get("channel") == 11
            and attestation.get("address") == package11.REMOTE_AP_ADDRESS,
            "Phase 11.6 remote AP attestation",
        )
        return packet


def main():
    configure_module()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("setup", "verify", "cleanup", "client", "broker", "ntp-client"),
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no wspr5 fixture mutation.")
        return
    require(sys.platform == "linux" and os.geteuid() == 0, "Linux root required")
    root = args.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077 == 0, "Private Phase 11.6 root required")
    os.umask(0o077)

    def interrupted(_signum, _frame):
        raise InterruptedError("Phase 11.6 fixture interrupted")

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    if args.action == "client":
        package11.hotspot.ROOT = root
        package11.hotspot.CLIENT_IF = package11.CLIENT_IF
        package11.hotspot.client(package11.CLIENT_ADDRESS, association_seconds=90)
    elif args.action == "broker":
        package11.ntp_broker(root)
    elif args.action == "ntp-client":
        package11.ntp_client(root)
    else:
        getattr(Fixture(root), args.action)()


if __name__ == "__main__":
    main()
