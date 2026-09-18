#!/usr/bin/env python3
"""Own the bounded wspr4 AP/time/capture side of Package 11.

The script never opens a Pico or the RF reservation.  It preserves wlan0 as the
management interface, temporarily replaces wlan1's ordinary connection with an
isolated AP, and arms cleanup before the first mutation.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import select
import signal
import socket
import struct
import subprocess
import sys
import time


HOST_BOOT = "5fbac52a-9d54-497f-8623-1476a380fcad"
MANAGEMENT_IF = "wlan0"
MANAGEMENT_MAC = "dc:a6:32:23:77:b6"
MANAGEMENT_PROFILE = "aba741f9-4817-36bb-bede-67861e5d74a6"
AP_IF = "wlan1"
AP_MAC = "e8:4e:06:ac:f3:87"
RESTORE_PROFILE = "1fff2c03-dfb1-46be-9ae8-fae4f652931a"
PROFILE = "phase115-package11-ap"
PREFIX = "phase115-package11-ap"
SUBNET = "10.77.15.0/24"
AP_ADDRESS = "10.77.15.1"
CLIENT_ADDRESS = "10.77.15.2"
DUT_ADDRESS = "10.77.15.10"
DUT_MAC = "88:a2:9e:0a:60:df"
NTP_UPSTREAM = "192.168.1.54"
TIME_NAME = "time.local"
SCHEMAS = ("phase11.5-package11-admission-v1",
           "phase11.5-package11-fixture-v1")
UNITS = (PREFIX + "-dhcp.service", PREFIX + "-capture.service")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_command(args, check=True, timeout=35):
    try:
        result = subprocess.run([str(value) for value in args], capture_output=True,
                                text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise TimeoutError("Remote AP command deadline: " + Path(args[0]).name) from None
    if check and result.returncode:
        raise RuntimeError("Remote AP command failed: " + Path(args[0]).name)
    return result


class RemoteAp:
    def __init__(self, root):
        self.root = root
        self.packet = json.loads((root / "packet.json").read_text())
        self.state_path = root / "remote-state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}

    def value(self, *args):
        return run_command(args).stdout.strip()

    def note(self, kind, value):
        with (self.root / "remote.jsonl").open("a") as stream:
            stream.write(json.dumps({"monotonic_ns": time.monotonic_ns(),
                "utc_ns": time.time_ns(), "kind": kind, "value": value}) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def save(self):
        temporary = self.root / "remote-state.tmp"
        with temporary.open("w") as stream:
            json.dump(self.state, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.state_path)

    def intent(self, name):
        self.state[name] = True
        self.save()

    def validate_packet(self):
        packet = self.packet
        authorization = ("PACKAGE11-TWO-HOST-R6" if
                         packet.get("schema") == "phase11.5-package11-admission-v1" else
                         "PACKAGE11-TWO-HOST-R6-RETRY3")
        require(packet.get("schema") in SCHEMAS and
                packet.get("authorization") == authorization and
                packet.get("root") == str(self.root) and
                packet.get("remote_host") == "wspr4" and
                packet.get("remote_host_boot_id") == HOST_BOOT and
                packet.get("remote_ap_if") == AP_IF and
                packet.get("remote_ap_mac") == AP_MAC and
                packet.get("client_address") == CLIENT_ADDRESS and
                packet.get("dut_address") == DUT_ADDRESS and
                packet.get("time_authority_address") == CLIENT_ADDRESS and
                packet.get("wifi_sha256") == hashlib.sha256(
                    (json.dumps(packet.get("wifi"), sort_keys=True,
                                separators=(",", ":")) + "\n").encode()).hexdigest() and
                type(packet.get("runtime_seconds")) is int and
                0 < packet["runtime_seconds"] <= 7200 and
                type(packet.get("restoration_seconds")) is int and
                0 < packet["restoration_seconds"] <= 900,
                "Remote AP packet scope")
        wifi = packet.get("wifi")
        require(isinstance(wifi, dict) and wifi.get("ssid") == "WsprryPico-Phase115" and
                wifi.get("ntp_ipv4") == TIME_NAME and
                isinstance(wifi.get("password"), str) and len(wifi["password"]) == 32 and
                all(value in "0123456789abcdef" for value in wifi["password"]),
                "Remote AP retained Wi-Fi")
        return packet

    def host(self, paused=False):
        require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT,
                "Remote host boot changed")
        for interface, mac in ((MANAGEMENT_IF, MANAGEMENT_MAC), (AP_IF, AP_MAC)):
            require(Path("/sys/class/net", interface, "address").read_text().strip() == mac,
                    "Remote radio identity changed")
        require(self.value("nmcli", "-g", "GENERAL.CON-UUID", "device", "show",
                           MANAGEMENT_IF) == MANAGEMENT_PROFILE,
                "Remote management profile changed")
        require("192.168.1.68/24" in self.value("ip", "-brief", "address", "show",
                                                  "dev", MANAGEMENT_IF),
                "Remote management address absent")
        require(Path("/proc/sys/net/ipv4/ip_forward").read_text().strip() == "0",
                "Remote forwarding changed")
        timer_active = run_command(
            ["systemctl", "is-active", "pi-wifi-recover.timer"], check=False
        ).stdout.strip()
        require(self.value("systemctl", "is-enabled", "pi-wifi-recover.timer") == "enabled" and
                timer_active == ("inactive" if paused else "active"),
                "Remote Wi-Fi recovery timer changed")
        return {"interfaces": self.value("ip", "-brief", "address"),
                "routes": self.value("ip", "-4", "route"),
                "connections": self.value("nmcli", "-t", "-f", "NAME,UUID,DEVICE",
                                            "connection", "show", "--active"),
                "network_manager_pid": self.value("systemctl", "show", "-p", "MainPID",
                                                  "--value", "NetworkManager"),
                "chrony_pid": self.value("systemctl", "show", "-p", "MainPID", "--value",
                                           "chrony"),
                "avahi_pid": self.value("systemctl", "show", "-p", "MainPID", "--value",
                                          "avahi-daemon")}

    def unit(self, suffix, args):
        name = PREFIX + "-" + suffix + ".service"
        require(name in UNITS, "Unknown remote unit")
        self.state.setdefault("units", []).append(name)
        self.save()
        run_command(["systemd-run", "--quiet", "--collect", "--unit=" + name,
            "--description=" + self.state["token"], "--property=UMask=0077",
            "--property=RuntimeMaxSec=" + str(self.packet["runtime_seconds"]),
            "--property=TimeoutStopSec=15", "--property=KillSignal=SIGINT",
            "--property=WorkingDirectory=" + str(self.root),
            "--property=StandardOutput=append:" + str(self.root / (suffix + ".log")),
            "--property=StandardError=append:" + str(self.root / (suffix + ".log")), *args])

    def setup(self):
        packet = self.validate_packet()
        require(not self.state, "Fresh remote AP root required")
        before = self.host()
        require(PROFILE not in self.value("nmcli", "-g", "NAME", "connection", "show") and
                "10.77.15." not in before["interfaces"] + before["routes"] and
                self.value("nmcli", "-g", "GENERAL.CON-UUID", "device", "show", AP_IF) ==
                    RESTORE_PROFILE,
                "Remote AP preflight state")
        for name in (*UNITS, PREFIX + "-cleanup.timer", PREFIX + "-cleanup.service"):
            require(self.value("systemctl", "show", "-p", "LoadState", "--value", name) ==
                    "not-found", "Remote unit collision")
        self.state = {"version": 1, "token": "Package11 remote AP " + secrets.token_hex(16),
                      "host_boot": HOST_BOOT, "before": before, "units": []}
        self.save()
        run_command(["systemd-run", "--quiet", "--unit=" + PREFIX + "-cleanup",
            "--description=" + self.state["token"],
            "--on-active=" + str(packet["runtime_seconds"]) + "s",
            "--property=UMask=0077",
            "--property=RuntimeMaxSec=" + str(packet["restoration_seconds"]),
            "--property=TimeoutStartSec=" + str(packet["restoration_seconds"]),
            "--property=WorkingDirectory=" + str(self.root),
            "--property=StandardOutput=append:" + str(self.root / "cleanup.log"),
            "--property=StandardError=append:" + str(self.root / "cleanup.log"),
            "/usr/bin/python3", str(Path(__file__).resolve()), "cleanup", "--root",
            str(self.root), "--run"])
        self.intent("cleanup_armed")
        self.intent("recovery_timer_paused")
        run_command(["systemctl", "stop", "pi-wifi-recover.timer",
                     "pi-wifi-recover.service"])
        # wlan1 normally carries a redundant management connection whose
        # autoconnect policy can reclaim the radio after the temporary AP is
        # reported active. Hold only the device's runtime autoconnect flag;
        # the saved connection profile is not edited.
        self.intent("device_autoconnect_disabled")
        run_command(["nmcli", "device", "set", AP_IF, "autoconnect", "no"])
        self.intent("restore_connection_down")
        run_command(["nmcli", "--wait", "25", "connection", "down", "uuid", RESTORE_PROFILE])
        self.intent("ap_profile")
        wifi = packet["wifi"]
        run_command(["nmcli", "connection", "add", "save", "no", "type", "wifi",
            "ifname", AP_IF, "con-name", PROFILE, "ssid", wifi["ssid"],
            "802-11-wireless.mode", "ap", "802-11-wireless.band", "bg",
            "802-11-wireless.channel", "11", "802-11-wireless.powersave", "2",
            "connection.autoconnect", "no", "ipv4.method", "manual",
            "ipv4.addresses", AP_ADDRESS + "/24", "ipv4.never-default", "yes",
            "ipv6.method", "disabled", "wifi-sec.key-mgmt", "wpa-psk",
            "wifi-sec.proto", "rsn", "wifi-sec.pairwise", "ccmp", "wifi-sec.psk",
            wifi["password"]])
        run_command(["nmcli", "--wait", "25", "connection", "up", PROFILE])
        run_command(["iw", "dev", AP_IF, "set", "power_save", "off"])
        (self.root / "dhcp-hosts").write_text(DUT_MAC + "," + DUT_ADDRESS + ",60s\n")
        (self.root / "dnsmasq.conf").write_text("\n".join([
            "port=0", "interface=" + AP_IF, "bind-interfaces", "dhcp-authoritative",
            "dhcp-range=10.77.15.0,static,255.255.255.0,60s",
            "dhcp-hostsfile=" + str(self.root / "dhcp-hosts"),
            "dhcp-leasefile=" + str(self.root / "leases"), "dhcp-option=3",
            "dhcp-option=6", "log-dhcp", "log-facility=-", "user=root", "group=root"]) + "\n")
        run_command(["/usr/sbin/dnsmasq", "--test",
                     "--conf-file=" + str(self.root / "dnsmasq.conf")])
        self.unit("dhcp", ["/usr/sbin/dnsmasq", "--keep-in-foreground",
                           "--conf-file=" + str(self.root / "dnsmasq.conf")])
        self.unit("capture", ["/usr/bin/python3", str(Path(__file__).resolve()), "capture",
                              "--root", str(self.root), "--run"])
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not (self.root / "capture.pcap").exists():
            time.sleep(.1)
        require((self.root / "capture.pcap").exists(), "Remote AP capture did not start")
        self.verify()
        self.intent("ready")
        attestation = {"schema": "phase11.5-package11-remote-ap-ready-v1",
            "host": "wspr4", "host_boot_id": HOST_BOOT, "ap_if": AP_IF,
            "ap_mac": AP_MAC, "management_if": MANAGEMENT_IF,
            "management_mac": MANAGEMENT_MAC, "channel": 11,
            "address": AP_ADDRESS, "packet_sha256": digest(self.root / "packet.json"),
            "wifi_sha256": packet["wifi_sha256"],
            "state_sha256": digest(self.state_path)}
        (self.root / "remote-ready.json").write_text(json.dumps(attestation, indent=2) + "\n")
        self.note("ready", attestation)

    def verify(self):
        current = self.host(paused=True)
        require(self.value("nmcli", "-g", "GENERAL.CONNECTION", "device", "show", AP_IF) ==
                PROFILE and AP_ADDRESS + "/24" in current["interfaces"] and
                "default via" not in "\n".join(line for line in current["routes"].splitlines()
                                                 if "dev " + AP_IF in line),
                "Remote AP address/route")
        link = self.value("iw", "dev", AP_IF, "info")
        require("type AP" in link and "channel 11" in link and
                all(self.value("systemctl", "is-active", name) == "active" for name in UNITS),
                "Remote AP services")
        self.note("verified", {"host": current, "ap": link})

    def stop_owned(self, name):
        load = self.value("systemctl", "show", "-p", "LoadState", "--value", name)
        if load == "not-found":
            return
        require(self.value("systemctl", "show", "-p", "Description", "--value", name) ==
                self.state["token"], "Remote unit ownership changed")
        run_command(["systemctl", "stop", name])

    def cleanup(self):
        if not self.state or self.state.get("restored"):
            return
        require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() ==
                self.state["host_boot"], "Remote host boot changed during cleanup")
        failures = []

        def attempt(label, action):
            try:
                action()
            except Exception as error:
                failures.append({"step": label, "type": type(error).__name__,
                                 "message": str(error)})

        for name in reversed(self.state.get("units", [])):
            attempt(name, lambda name=name: self.stop_owned(name))
        if self.state.get("ap_profile"):
            attempt("AP profile", lambda: run_command(
                ["nmcli", "connection", "delete", PROFILE]) if PROFILE in
                self.value("nmcli", "-g", "NAME", "connection", "show") else None)
        if self.state.get("restore_connection_down"):
            attempt("restore wlan1", lambda: run_command(
                ["nmcli", "--wait", "35", "connection", "up", "uuid", RESTORE_PROFILE,
                 "ifname", AP_IF]))
        if self.state.get("device_autoconnect_disabled"):
            attempt("restore wlan1 autoconnect", lambda: run_command(
                ["nmcli", "device", "set", AP_IF, "autoconnect", "yes"]))
        if self.state.get("recovery_timer_paused"):
            attempt("Wi-Fi recovery timer", lambda: run_command(
                ["systemctl", "start", "pi-wifi-recover.timer"]))

        def verify_restored():
            deadline = time.monotonic() + 45
            last = None
            while time.monotonic() < deadline:
                last = self.host()
                active = self.value("nmcli", "-g", "GENERAL.CON-UUID", "device", "show",
                                    AP_IF)
                if active == RESTORE_PROFILE and "192.168.1.120/24" in last["interfaces"]:
                    break
                time.sleep(.5)
            require(last is not None and active == RESTORE_PROFILE and
                    "192.168.1.120/24" in last["interfaces"] and
                    PROFILE not in self.value("nmcli", "-g", "NAME", "connection", "show") and
                    "10.77.15." not in last["interfaces"] + last["routes"],
                    "Remote host restoration")
            self.note("host_restored", last)

        attempt("remote host", verify_restored)
        self.note("cleanup", {"failures": failures})
        require(not failures, "Remote AP cleanup incomplete")
        if self.state.get("cleanup_armed"):
            self.stop_owned(PREFIX + "-cleanup.timer")
        self.state["restored"] = True
        self.save()


def serve_time(root):
    """Publish time.local and proxy NTP to wspr5's PPS-backed chrony."""
    mdns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    mdns.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # RFC 6762 requires every mDNS packet to use an IP TTL of 255. Avahi
    # rejects an otherwise valid unicast response when the default TTL is used.
    mdns.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, 255)
    mdns.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    mdns.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                    socket.inet_aton(AP_ADDRESS))
    mdns.bind(("", 5353))
    mdns.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                    socket.inet_aton("224.0.0.251") + socket.inet_aton(AP_ADDRESS))
    ntp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ntp.bind((AP_ADDRESS, 123))
    upstream = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    upstream.bind(("192.168.1.68", 0))
    upstream.settimeout(.55)
    stop = False
    upstream_timeouts = 0
    upstream_invalid = 0

    def interrupted(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    events = 0
    try:
        while not stop:
            readable, _, _ = select.select([mdns, ntp], [], [], .5)
            for source in readable:
                request, peer = source.recvfrom(4096)
                if source is mdns:
                    legacy = peer[1] != 5353
                    answer = mdns_response(request, legacy=legacy)
                    if answer is not None:
                        mdns.sendto(answer, peer if legacy else ("224.0.0.251", 5353))
                        events += 1
                else:
                    require(len(request) == 48, "Unexpected NTP request")
                    response, timeouts, invalid = upstream_ntp(upstream, request)
                    upstream_timeouts += timeouts
                    upstream_invalid += invalid
                    if response is not None:
                        ntp.sendto(response, peer)
                        events += 1
    finally:
        print(json.dumps({"events": events, "upstream_timeouts": upstream_timeouts,
                          "upstream_invalid": upstream_invalid, "status": "stopped"}),
              flush=True)
        mdns.close(); ntp.close(); upstream.close()


def mdns_response(request, legacy=True):
    """Return the bounded time.local A response for a query, never a response."""
    question = b"\x04time\x05local\x00\x00\x01\x00\x01"
    if len(request) < 12 or struct.unpack_from("!H", request, 2)[0] & 0x8000 or \
            question not in request:
        return None
    if legacy:
        query_flags = struct.unpack_from("!H", request, 2)[0]
        flags = 0x8400 | (query_flags & 0x0100)
        record = struct.pack("!HHIH", 1, 1, 10, 4) + socket.inet_aton(AP_ADDRESS)
        return (request[:2] + struct.pack("!5H", flags, 1, 1, 0, 0) + question +
                b"\xc0\x0c" + record)
    record = struct.pack("!HHIH", 1, 0x8001, 120, 4) + socket.inet_aton(AP_ADDRESS)
    return struct.pack("!6H", 0, 0x8400, 0, 1, 0, 0) + question[:-4] + record


def upstream_ntp(upstream, request, attempts=4):
    """Retry one NTP query inside the caller's three-second deadline."""
    timeouts = 0
    invalid = 0
    for _ in range(attempts):
        upstream.sendto(request, (NTP_UPSTREAM, 123))
        try:
            response, address = upstream.recvfrom(512)
        except TimeoutError:
            timeouts += 1
            continue
        if address != (NTP_UPSTREAM, 123) or len(response) != 48 or \
                response[24:32] != request[40:48]:
            invalid += 1
            continue
        return response, timeouts, invalid
    return None, timeouts, invalid


def capture(root):
    """Write an Ethernet pcap and report kernel packet drops."""
    path = root / "capture.pcap"
    raw = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
    raw.bind((AP_IF, 0))
    raw.settimeout(.5)
    stop = False

    def interrupted(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    count = 0
    with path.open("xb") as stream:
        stream.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
        stream.flush(); os.fsync(stream.fileno())
        while not stop:
            try:
                frame = raw.recv(65535)
            except socket.timeout:
                continue
            now = time.time_ns()
            stream.write(struct.pack("<IIII", now // 1_000_000_000,
                                     (now % 1_000_000_000) // 1000,
                                     len(frame), len(frame)))
            stream.write(frame)
            count += 1
        stream.flush(); os.fsync(stream.fileno())
    packets, drops = struct.unpack("II", raw.getsockopt(263, 6, 8))
    raw.close()
    print(json.dumps({"captured": count, "kernel_packets": packets,
                      "kernel_drops": drops}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("setup", "verify", "cleanup", "serve-time", "capture"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no remote host mutation.")
        return
    require(sys.platform == "linux" and os.geteuid() == 0, "Linux root required")
    root = args.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077 == 0, "Private remote root required")
    os.umask(0o077)
    if args.action == "serve-time":
        serve_time(root)
    elif args.action == "capture":
        capture(root)
    else:
        remote = RemoteAp(root)
        getattr(remote, args.action)()


if __name__ == "__main__":
    main()
