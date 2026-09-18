#!/usr/bin/env python3
"""Bounded Phase 11.6 adapter for the accepted wspr4 Package 11 AP."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import phase11_5_package11_remote_ap as package11


SCHEMA = "phase11.6-fixture-v1"
AUTHORIZATION = "PHASE11.6-CONDUCTED-RF-20260918"
MAX_RUNTIME_SECONDS = 21_600
MAX_RESTORATION_SECONDS = 900
PREFIX = "phase116-campaign-ap"
PROFILE = "phase116-campaign-ap"
PLAN_SHA256 = {
    "ea512b70a786c46fbe15f769b327139d69ad3b0cae984b3622d79f145a076c53",
    "9324f6057ae8f4e552375919836bbe4e0c30176405eedaf3915f0ab67d929556",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def configure_module():
    package11.PREFIX = PREFIX
    package11.PROFILE = PROFILE
    package11.UNITS = (PREFIX + "-dhcp.service", PREFIX + "-capture.service")
    package11.__file__ = __file__


class RemoteAp(package11.RemoteAp):
    def validate_packet(self):
        packet = self.packet
        wifi = packet.get("wifi")
        require(
            packet.get("schema") == SCHEMA
            and packet.get("authorization") == AUTHORIZATION
            and packet.get("root") == str(self.root)
            and packet.get("remote_host") == "wspr4"
            and packet.get("remote_host_boot_id") == package11.HOST_BOOT
            and packet.get("remote_ap_if") == package11.AP_IF
            and packet.get("remote_ap_mac") == package11.AP_MAC
            and packet.get("client_address") == package11.CLIENT_ADDRESS
            and packet.get("dut_address") == package11.DUT_ADDRESS
            and packet.get("time_authority_address") == package11.CLIENT_ADDRESS
            and packet.get("plan_sha256") in PLAN_SHA256
            and type(packet.get("runtime_seconds")) is int
            and 0 < packet["runtime_seconds"] <= MAX_RUNTIME_SECONDS
            and type(packet.get("restoration_seconds")) is int
            and 0 < packet["restoration_seconds"] <= MAX_RESTORATION_SECONDS,
            "Phase 11.6 remote fixture packet",
        )
        require(
            isinstance(wifi, dict)
            and wifi.get("ssid") == "WsprryPico-Phase115"
            and wifi.get("ntp_ipv4") == package11.TIME_NAME
            and isinstance(wifi.get("password"), str)
            and len(wifi["password"]) == 32
            and all(value in "0123456789abcdef" for value in wifi["password"]),
            "Phase 11.6 retained Wi-Fi",
        )
        require(
            packet.get("wifi_sha256")
            == hashlib.sha256(
                (json.dumps(wifi, sort_keys=True, separators=(",", ":")) + "\n").encode()
            ).hexdigest(),
            "Phase 11.6 Wi-Fi hash",
        )
        return packet


def main():
    configure_module()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("setup", "verify", "cleanup", "serve-time", "capture"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no wspr4 fixture mutation.")
        return
    require(sys.platform == "linux" and os.geteuid() == 0, "Linux root required")
    root = args.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077 == 0, "Private Phase 11.6 root required")
    os.umask(0o077)
    if args.action == "serve-time":
        package11.serve_time(root)
    elif args.action == "capture":
        package11.capture(root)
    else:
        getattr(RemoteAp(root), args.action)()


if __name__ == "__main__":
    main()
