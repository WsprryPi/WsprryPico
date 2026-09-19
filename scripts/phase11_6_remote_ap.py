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
    "9b5d8c6e7137626305c5d3492b6b0024a59e2e7975a82638076ad6c9df7fb503",
    "558d84ecc29546b0a67e7267405bf54c68198f048ad201e3cfd7ccc867f466e5",
    "9ba62ee71fde9c9667f5401ea0625524334fbda3c2be40b17a6fac2d29817d04",
    "a15d46c017be441dd192e9c100d8eb4316e5ba5748d4c73848e987933988e69b",
    "4ce799fadbb8837f2db6ef9ddccc9964858c166b318002d65300dc77848b0661",
    "01a828715f786bec40c8792056f2d973e36e0df95e9cd2fa5921422faa702538",
    "a03a6b62eebe75202062c447b95498c3300b9e425796df96989fbe498796986a",
    "cb0ca7be3a0468add27186f0fb0c18dbec62d7804d206ea897f0b36e1fb3f51c",
    "6f233e933b5d7bd5ceaa557e7353cfc3076c387b16065a728c9d35d143ef1f52",
    "c3392251cac3f718655a8ae641ac164d185ce0d51dc3db7e86b4dea6e66bf601",
    "2f4d0608afdcb6a494c84ebbd8c55c665ca87e9bc0cea9de692d7e6c792b0123",
    "1b9f96f5b965290be805e7a728a3719bfb958152bc184acaefeeab035ffa66a4",
    "f3ec51a05618313a766a1804a44eda31cc6cae5d90a59f50a14df14f2306e07c",
    "711678805fbaea9edbe102db07fde50d10906f971a6e7b3a4f83f3e0723db217",
    "70cbc05046f1b9344ed26a926b9d4d2e83de20d0f503941aca7896ddc8c1786e",
    "51ca64a56b5f862a913916f667a913c15fe94fcecb4313342d83a465f01110b2",
    "da092f2b72e4583045801de2bf14223e87c61c208370fc9b7c0f72255ff8d241",
    "f66facd3c57c4cae45519e402b89151589286eb5de9b6448e4ce22649a66c78a",
    "1d09bcd96ce0b71a1d6ff790a8d6e42f5840c95ac0ac6f63ea9c02119b8f8a8f",
    "cc35d9afe5167572a37584c601c94e5733d77272bb71e3aa125b1753508838fb",
    "7d81849fd9828362d47a7dbfce9ed8260108b816ffce570d34c10db461233504",
    "0697eeaa4e5e99883efa5d2492e8e26a58030cd25370af86290bf19be7cefaf5",
    "20a3681d39b84c3e37e7e85dae582eed7093dff4db4102bd98ed327ac45e71ae",
    "1b0afcc0148096e668e31fc63ffbb35af0b0c9089a37308977ca679247d43902",
    "ea512b70a786c46fbe15f769b327139d69ad3b0cae984b3622d79f145a076c53",
    "9324f6057ae8f4e552375919836bbe4e0c30176405eedaf3915f0ab67d929556",
    "8a52e4d9b3f252097bca0112c08b3b1e41792905775624940bcbf313b5cb072b",
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
