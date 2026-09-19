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
import time

import phase11_5_package11_fixture as package11


SCHEMA = "phase11.6-fixture-v1"
AUTHORIZATION = "PHASE11.6-CONDUCTED-RF-20260918"
MAX_RUNTIME_SECONDS = 21_600
MAX_RESTORATION_SECONDS = 900
PREFIX = "phase116-campaign"
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
    "da5ccbc3438e598fe466ef4c097330bc83a85cc638db447e87d34a17c1cb4db4",
    "b03ad9058b31699aaf5bcbbc71e7892c02127751952790c0303fb3193a2053b6",
    "e28ad6a58c6234d35dba302ed481c0d803f16fe605433c02fa589ab81275758a",
    "2814e4fa0bd076d9c1ed716f78cbd4351ea3fadfdc5bbacc24794b94f3a9f399",
    "893d8d92eb382e3e7230f068b30c481e9275bc52b7ec699b719ae6002e33a7e2",
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
    "ef6624ccfa3be1b05ec914721071271fe1ef2bdb2afca5bffb200b1812ae279c",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def configure_module():
    package11.PREFIX = PREFIX
    package11.NETNS = PREFIX + "-client"
    package11.__file__ = __file__


class Fixture(package11.Fixture):
    def installed_service_marker(self):
        """Bind the pre-paused transmitter state into the immutable run root."""
        installed_pid = self.value(
            "systemctl", "show", "-p", "MainPID", "--value",
            "wsprrypi.service",
        )
        installed_state = self.value(
            "systemctl", "show", "-p", "ActiveState", "--value",
            "wsprrypi.service",
        )
        require(installed_pid == "0" and installed_state == "inactive",
                "Installed WsprryPi service is not pre-paused")
        return f"MainPID={installed_pid}\nActiveState={installed_state}\n"

    def setup(self):
        marker = self.root / "installed-paused.txt"
        require(not marker.exists(), "Fresh installed-service marker required")
        with marker.open("x") as stream:
            stream.write(self.installed_service_marker())
            stream.flush()
            os.fsync(stream.fileno())
        super().setup()

    def verify(self):
        super().verify()
        require(
            (self.root / "installed-paused.txt").read_text()
            == self.installed_service_marker(),
            "Installed WsprryPi pause marker changed",
        )

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
            and 0 < packet["network_restoration_seconds"] <= MAX_RESTORATION_SECONDS
            and packet.get("installed_service_prepaused") is True,
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

    def host(self, paused=False):
        """Verify the host while preserving its pre-existing transmitter pause."""
        require(
            Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            == package11.HOST_BOOT,
            "wspr5 boot changed",
        )
        interfaces = [("eth0", package11.ETHERNET_MAC),
                      ("wlan1", package11.MANAGEMENT_MAC)]
        if not paused:
            interfaces.append((package11.CLIENT_IF, package11.CLIENT_MAC))
        for interface, mac in interfaces:
            require(
                Path("/sys/class/net", interface, "address").read_text().strip()
                == mac,
                "wspr5 interface identity changed",
            )
        timer_active = package11.command(
            ["systemctl", "is-active", "pi-wifi-recover.timer"], check=False
        ).stdout.strip()
        installed_pid = self.value(
            "systemctl", "show", "-p", "MainPID", "--value",
            "wsprrypi.service",
        )
        installed_state = self.value(
            "systemctl", "show", "-p", "ActiveState", "--value",
            "wsprrypi.service",
        )
        require(
            Path("/sys/class/net/eth0/carrier").read_text().strip() == "1"
            and self.value("nmcli", "-g", "GENERAL.CON-UUID", "device", "show",
                           "wlan1") == package11.MANAGEMENT_PROFILE
            and hashlib.sha256(
                Path("/usr/local/bin/wsprrypi").read_bytes()
            ).hexdigest() == package11.INSTALLED_SHA
            and installed_state == "inactive"
            and installed_pid == "0"
            and self.value("systemctl", "is-enabled", "pi-wifi-recover.timer")
            == "enabled"
            and timer_active == ("inactive" if paused else "active"),
            "wspr5 management/pre-paused-service state",
        )
        return {
            "interfaces": self.value("ip", "-brief", "address"),
            "routes": self.value("ip", "-4", "route"),
            "installed_pid": installed_pid,
            "installed_active_state": installed_state,
        }

    def cleanup(self):
        """Restore the fixture without starting the pre-paused transmitter."""
        if not self.state or self.state.get("restored"):
            return
        require(
            Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            == self.state["host_boot"],
            "wspr5 boot changed during cleanup",
        )
        failures = []

        def attempt(label, action):
            try:
                action()
            except Exception as error:
                failures.append({"step": label, "type": type(error).__name__,
                                 "message": str(error)})

        for name in reversed(self.state.get("units", [])):
            attempt(name, lambda name=name: self.stop_owned(name))
        if self.state.get("namespace"):
            attempt(
                "namespace",
                lambda: package11.command(
                    ["ip", "netns", "delete", package11.NETNS]
                ) if package11.NETNS in self.value("ip", "netns", "list") else None,
            )

        def restore_radio():
            deadline = time.monotonic() + 60
            path = Path("/sys/class/net", package11.CLIENT_IF, "address")
            while time.monotonic() < deadline and not path.exists():
                time.sleep(.2)
            require(path.read_text().strip() == package11.CLIENT_MAC,
                    "Client radio did not return")
            if self.state.get("client_unmanaged"):
                package11.command(
                    ["nmcli", "device", "set", package11.CLIENT_IF,
                     "managed", "yes"]
                )
            package11.command(
                ["iw", "dev", package11.CLIENT_IF, "set", "power_save",
                 self.state["radio_power_save"]]
            )
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                value = self.value(
                    "nmcli", "-g", "GENERAL.STATE", "device", "show",
                    package11.CLIENT_IF,
                )
                if value.startswith("30 "):
                    return
                time.sleep(.2)
            raise ValueError("Client radio did not restore disconnected")

        if self.state.get("namespace") or self.state.get("client_unmanaged"):
            attempt("client radio", restore_radio)
        if self.state.get("timer_paused"):
            attempt(
                "recovery timer",
                lambda: package11.command(
                    ["systemctl", "start", "pi-wifi-recover.timer"]
                ),
            )

        def restore_management():
            active = package11.command(
                ["nmcli", "-g", "GENERAL.CON-UUID", "device", "show", "wlan1"],
                check=False,
            ).stdout.strip()
            if active != package11.MANAGEMENT_PROFILE:
                package11.command(
                    ["nmcli", "connection", "up", "uuid",
                     package11.MANAGEMENT_PROFILE, "ifname", "wlan1"],
                    timeout=60,
                )

        attempt("management profile", restore_management)

        def verify_restored():
            current = self.host()
            require(
                package11.NETNS not in self.value("ip", "netns", "list")
                and "10.77.15." not in current["interfaces"] + current["routes"]
                and current["installed_pid"] == "0"
                and current["installed_active_state"] == "inactive",
                "wspr5 fixture restoration",
            )
            self.note("host_restored", current)

        attempt("wspr5 host", verify_restored)
        self.note("cleanup", {"failures": failures, "pico_state": "not inferred"})
        require(not failures, "Phase 11.6 fixture cleanup incomplete")
        if self.state.get("cleanup_armed"):
            self.stop_owned(package11.PREFIX + "-cleanup.timer")
        self.state["restored"] = True
        self.save()


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
