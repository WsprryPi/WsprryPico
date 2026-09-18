#!/usr/bin/env python3
"""Own the bounded wspr5 client side of the Package 11 two-host fixture."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import stat
import subprocess
import sys
import time

from phase11_5_inventory import require
import phase11_4_hotspot as hotspot


HOST_BOOT = "220e53ca-ca95-4206-9581-dbe28aa1eeb8"
PREFIX = "phase115-package11"
NETNS = PREFIX + "-client"
CLIENT_IF = "wlan2"
CLIENT_MAC = "e8:4e:06:ae:d7:09"
CLIENT_USB_DEVICE = "4-1.1:1.0"
CLIENT_USB_DRIVER = "mt7921u"
CLIENT_ADDRESS = "10.77.15.2"
REMOTE_AP_MAC = "e8:4e:06:ac:f3:87"
REMOTE_AP_ADDRESS = "10.77.15.1"
TIME_ADDRESS = CLIENT_ADDRESS
NTP_UPSTREAM = "192.168.1.54"
MANAGEMENT_MAC = "90:de:80:47:b9:da"
ETHERNET_MAC = "2c:cf:67:62:76:64"
MANAGEMENT_PROFILE = "921301fe-cdfd-4965-8ac7-c96e9d908ea6"
INSTALLED_SHA = "ab1989097cc87b54f76f5fcf776d7d16a166e1edca29ed2c71a2f396fdd22a90"
SCHEMAS = ("phase11.5-package11-admission-v1",
           "phase11.5-package11-fixture-v1")
UNIT_SUFFIXES = ("client.service", "ntp-broker.service", "ntp-client.service",
                 "capture-client.service", "campaign.service")
CREDENTIALS = {
    "controller": {"ca": "credentials/controller/client-ca.crt",
                   "cert": "credentials/controller/client.crt",
                   "key": "credentials/controller/client.key"},
    "browser": {"ca": "credentials/browser/client-ca.crt",
                "cert": "credentials/browser/client.crt",
                "key": "credentials/browser/client.key"},
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command(args, check=True, timeout=35):
    try:
        result = subprocess.run([str(value) for value in args], capture_output=True,
                                text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise TimeoutError("Package 11 fixture command deadline: " +
                           Path(args[0]).name) from None
    if check and result.returncode:
        raise RuntimeError("Package 11 fixture command failed: " +
                           Path(args[0]).name)
    return result


def wpa_config(ssid, psk):
    return ("ctrl_interface=/run/wpa_supplicant\nnetwork={\n"
            "ssid=\"" + ssid + "\"\npsk=\"" + psk + "\"\n"
            "key_mgmt=WPA-PSK\nproto=RSN\npairwise=CCMP\n"
            "bssid=" + REMOTE_AP_MAC + "\nscan_freq=2462\n}\n")


def credential_paths(packet):
    credentials = packet.get("credentials", {})
    require(credentials == CREDENTIALS, "Package 11 credential paths")
    paths = tuple(credentials[role][kind]
                  for role in ("controller", "browser")
                  for kind in ("ca", "cert", "key"))
    require(len(paths) == len(set(paths)) == 6, "Distinct Package 11 credentials")
    return paths


def prepare_runtime_credentials(root, packet):
    """Bind and protect credentials for the effective WsprryPi launcher user."""
    expected = packet.get("credential_sha256", {})
    paths = credential_paths(packet)
    require(set(expected) == set(paths), "Frozen Package 11 credential hashes")
    root = root.resolve(strict=True)
    owner, group = os.geteuid(), os.getegid()
    result = []
    for relative in paths:
        relative_path = Path(relative)
        require(not relative_path.is_absolute() and ".." not in relative_path.parts,
                "Credential path must remain below the fixture root")
        parent = root
        for part in relative_path.parts[:-1]:
            parent /= part
            parent_info = parent.lstat()
            require(stat.S_ISDIR(parent_info.st_mode),
                    "Credential parent must be a real directory")
        path = root / relative_path
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
                before.st_size > 0, "Credential must be one nonempty regular file")
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        try:
            opened = os.fstat(fd)
            require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino),
                    "Credential changed during secure open")
            hasher = hashlib.sha256()
            while True:
                block = os.read(fd, 65536)
                if not block:
                    break
                hasher.update(block)
            require(hasher.hexdigest() == expected[relative],
                    "Changed Package 11 credential")
            os.fchown(fd, owner, group)
            os.fchmod(fd, 0o600)
            after = os.fstat(fd)
            require(stat.S_ISREG(after.st_mode) and after.st_nlink == 1 and
                    after.st_uid == owner and after.st_gid == group and
                    stat.S_IMODE(after.st_mode) == 0o600,
                    "Credential runtime protection")
            result.append({"path": relative, "sha256": expected[relative],
                           "uid": after.st_uid, "gid": after.st_gid,
                           "mode": "0600"})
        finally:
            os.close(fd)
    return result


class Fixture:
    def __init__(self, root):
        self.root = root
        self.packet = json.loads((root / "packet.json").read_text())
        self.state_path = root / "fixture-state.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {}

    def value(self, *args):
        return command(args).stdout.strip()

    def note(self, kind, value):
        with (self.root / "fixture.jsonl").open("a") as stream:
            stream.write(json.dumps({"monotonic_ns": time.monotonic_ns(),
                "utc_ns": time.time_ns(), "kind": kind, "value": value}) + "\n")
            stream.flush(); os.fsync(stream.fileno())

    def save(self):
        temporary = self.root / "fixture-state.tmp"
        with temporary.open("w") as stream:
            json.dump(self.state, stream, indent=2)
            stream.write("\n")
            stream.flush(); os.fsync(stream.fileno())
        temporary.replace(self.state_path)

    def intent(self, name):
        self.state[name] = True
        self.save()

    def validate_packet(self):
        packet = self.packet
        authorization = ("PACKAGE11-TWO-HOST-R6" if
                         packet.get("schema") == "phase11.5-package11-admission-v1" else
                         "PACKAGE11-TWO-HOST-R6-RETRY4")
        require(packet.get("schema") in SCHEMAS and
                packet.get("authorization") == authorization and
                packet.get("root") == str(self.root) and
                packet.get("host_boot_id") == HOST_BOOT and
                packet.get("client_if") == CLIENT_IF and
                packet.get("client_mac") == CLIENT_MAC and
                packet.get("remote_ap_mac") == REMOTE_AP_MAC and
                packet.get("client_address") == CLIENT_ADDRESS and
                packet.get("time_authority_address") == TIME_ADDRESS and
                type(packet.get("network_runtime_seconds")) is int and
                0 < packet["network_runtime_seconds"] <= 7200 and
                type(packet.get("network_restoration_seconds")) is int and
                0 < packet["network_restoration_seconds"] <= 900,
                "Package 11 local fixture packet")
        wifi = packet.get("wifi")
        require(isinstance(wifi, dict) and wifi.get("ssid") == "WsprryPico-Phase115" and
                wifi.get("ntp_ipv4") == "time.local" and
                isinstance(wifi.get("password"), str) and len(wifi["password"]) == 32,
                "Package 11 local retained Wi-Fi")
        attestation = json.loads((self.root / "remote-ready.json").read_text())
        require(attestation == packet.get("remote_ready") and
                attestation.get("schema") == "phase11.5-package11-remote-ap-ready-v1" and
                attestation.get("host") == "wspr4" and
                attestation.get("ap_mac") == REMOTE_AP_MAC and
                attestation.get("channel") == 11 and
                attestation.get("address") == REMOTE_AP_ADDRESS,
                "Remote AP attestation")
        return packet

    def host(self, paused=False):
        require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT,
                "wspr5 boot changed")
        interfaces = [("eth0", ETHERNET_MAC), ("wlan1", MANAGEMENT_MAC)]
        if not paused:
            interfaces.append((CLIENT_IF, CLIENT_MAC))
        for interface, mac in interfaces:
            require(Path("/sys/class/net", interface, "address").read_text().strip() == mac,
                    "wspr5 interface identity changed")
        timer_active = command(
            ["systemctl", "is-active", "pi-wifi-recover.timer"], check=False
        ).stdout.strip()
        require(Path("/sys/class/net/eth0/carrier").read_text().strip() == "1" and
                self.value("nmcli", "-g", "GENERAL.CON-UUID", "device", "show", "wlan1") ==
                    MANAGEMENT_PROFILE and
                hashlib.sha256(Path("/usr/local/bin/wsprrypi").read_bytes()).hexdigest() ==
                    INSTALLED_SHA and
                self.value("systemctl", "is-active", "wsprrypi.service") == "active" and
                self.value("systemctl", "is-enabled", "pi-wifi-recover.timer") == "enabled" and
                timer_active == ("inactive" if paused else "active"),
                "wspr5 management/service state")
        return {"interfaces": self.value("ip", "-brief", "address"),
                "routes": self.value("ip", "-4", "route"),
                "installed_pid": self.value("systemctl", "show", "-p", "MainPID", "--value",
                                            "wsprrypi.service")}

    def unit(self, suffix, args):
        require(suffix + ".service" in UNIT_SUFFIXES, "Unknown Package 11 unit")
        name = PREFIX + "-" + suffix + ".service"
        self.state.setdefault("units", []).append(name)
        self.save()
        command(["systemd-run", "--quiet", "--collect", "--unit=" + name,
            "--description=" + self.state["token"], "--property=UMask=0077",
            "--property=RuntimeMaxSec=" + str(self.packet["network_runtime_seconds"]),
            "--property=TimeoutStopSec=15", "--property=KillSignal=SIGINT",
            "--property=WorkingDirectory=" + str(self.root),
            "--property=StandardOutput=append:" + str(self.root / (suffix + ".log")),
            "--property=StandardError=append:" + str(self.root / (suffix + ".log")), *args])

    def rebind_client(self):
        device = Path("/sys/bus/usb/devices") / CLIENT_USB_DEVICE
        require((device / "driver").resolve(strict=True).name == CLIENT_USB_DRIVER,
                "wspr5 client USB driver changed")
        driver = Path("/sys/bus/usb/drivers") / CLIENT_USB_DRIVER
        for action in ("unbind", "bind"):
            with (driver / action).open("w") as stream:
                stream.write(CLIENT_USB_DEVICE)
            if action == "unbind":
                time.sleep(3)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if (Path("/sys/class/net") / CLIENT_IF / "address").exists() and \
                    (Path("/sys/class/net") / CLIENT_IF / "address").read_text().strip() == CLIENT_MAC:
                self.note("usb_radio_rebind", {"device": CLIENT_USB_DEVICE,
                                                "driver": CLIENT_USB_DRIVER})
                return
            time.sleep(.2)
        raise ValueError("wspr5 client radio did not return")

    def setup(self):
        packet = self.validate_packet()
        require(not self.state, "Fresh Package 11 fixture root required")
        before = self.host()
        require(NETNS not in self.value("ip", "netns", "list") and
                "10.77.15." not in before["interfaces"] + before["routes"] and
                self.value("nmcli", "-g", "GENERAL.STATE", "device", "show", CLIENT_IF)
                    .startswith("30 "), "Package 11 local preflight")
        for name in (*[PREFIX + "-" + suffix for suffix in UNIT_SUFFIXES],
                     PREFIX + "-cleanup.timer", PREFIX + "-cleanup.service"):
            require(self.value("systemctl", "show", "-p", "LoadState", "--value", name) ==
                    "not-found", "Package 11 unit collision")
        power = self.value("iw", "dev", CLIENT_IF, "get", "power_save").split()[-1]
        require(power in ("on", "off"), "Unknown client power-save state")
        self.state = {"version": 1, "token": "Package11 wspr5 " + secrets.token_hex(16),
                      "host_boot": HOST_BOOT, "before": before, "units": [],
                      "radio_power_save": power}
        self.save()
        command(["systemd-run", "--quiet", "--unit=" + PREFIX + "-cleanup",
            "--description=" + self.state["token"],
            "--on-active=" + str(packet["network_runtime_seconds"]) + "s",
            "--property=UMask=0077",
            "--property=RuntimeMaxSec=" + str(packet["network_restoration_seconds"]),
            "--property=TimeoutStartSec=" + str(packet["network_restoration_seconds"]),
            "--property=WorkingDirectory=" + str(self.root),
            "--property=StandardOutput=append:" + str(self.root / "cleanup.log"),
            "--property=StandardError=append:" + str(self.root / "cleanup.log"),
            "/usr/bin/python3", str(Path(__file__).resolve()), "cleanup", "--root",
            str(self.root), "--run"])
        self.intent("cleanup_armed")
        protected = prepare_runtime_credentials(self.root, packet)
        self.note("credentials_protected", {"files": protected,
                  "effective_uid": os.geteuid(), "effective_gid": os.getegid()})
        self.intent("timer_paused")
        command(["systemctl", "stop", "pi-wifi-recover.timer", "pi-wifi-recover.service"])
        self.rebind_client()
        self.intent("client_unmanaged")
        command(["nmcli", "device", "set", CLIENT_IF, "managed", "no"])
        self.intent("namespace")
        command(["ip", "netns", "add", NETNS])
        phy = Path("/sys/class/net", CLIENT_IF, "phy80211").resolve(strict=True).name
        command(["iw", "phy", phy, "set", "netns", "name", NETNS])
        command(["ip", "-n", NETNS, "link", "set", "lo", "up"])
        wifi = packet["wifi"]
        (self.root / "wpa.conf").write_text(wpa_config(wifi["ssid"], wifi["password"]))
        (self.root / "avahi.conf").write_text(
            "[server]\nhost-name=time\nuse-ipv4=yes\nuse-ipv6=no\n"
            "allow-interfaces=" + CLIENT_IF + "\nenable-dbus=no\n"
            "[publish]\ndisable-publishing=no\npublish-addresses=yes\n"
            "publish-hinfo=no\npublish-workstation=no\n")
        self.unit("client", ["ip", "netns", "exec", NETNS, "unshare", "--mount",
            "--propagation", "private", "/usr/bin/python3", str(Path(__file__).resolve()),
            "client", "--root", str(self.root), "--run"])
        deadline = time.monotonic() + 105
        while time.monotonic() < deadline and not (self.root / "client-ready").exists():
            time.sleep(.2)
        require((self.root / "client-ready").exists(), "Package 11 client did not start")
        pid = self.value("systemctl", "show", "-p", "MainPID", "--value",
                         PREFIX + "-client.service")
        self.unit("ntp-broker", ["/usr/bin/python3", str(Path(__file__).resolve()),
            "broker", "--root", str(self.root), "--run"])
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (self.root / "ntp-broker.sock").exists():
            time.sleep(.1)
        require((self.root / "ntp-broker.sock").exists(), "Host NTP broker did not start")
        self.unit("ntp-client", ["nsenter", "-t", pid, "-m", "-n",
            "/usr/bin/python3", str(Path(__file__).resolve()), "ntp-client", "--root",
            str(self.root), "--run"])
        self.unit("capture-client", ["nsenter", "-t", pid, "-m", "-n",
            "/usr/bin/tcpdump", "--immediate-mode", "-i", CLIENT_IF, "-U", "-s", "0",
            "-w", str(self.root / "capture-client.pcap")])
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (self.root / "capture-client.pcap").exists():
            time.sleep(.1)
        require((self.root / "capture-client.pcap").exists(), "Client capture did not start")
        self.verify()
        self.intent("ready")
        self.note("ready", {"host_only": True,
            "expires_after_seconds": packet["network_runtime_seconds"],
            "remote_ap_mac": REMOTE_AP_MAC})

    def in_client(self, args, timeout=35, check=True):
        pid = self.value("systemctl", "show", "-p", "MainPID", "--value",
                         PREFIX + "-client.service")
        require(pid.isdigit() and int(pid) > 1, "Package 11 client absent")
        return command(["nsenter", "-t", pid, "-m", "-n", *args],
                       timeout=timeout, check=check)

    def verify(self):
        current = self.host(paused=True)
        peer = {label: self.in_client(args).stdout for label, args in {
            "link": ["iw", "dev", CLIENT_IF, "link"],
            "identity": ["cat", "/sys/class/net/" + CLIENT_IF + "/address"],
            "routes": ["ip", "-4", "route"],
            "addresses": ["ip", "-brief", "address"],
            "netns": ["readlink", "/proc/self/ns/net"],
            "mountns": ["readlink", "/proc/self/ns/mnt"]}.items()}
        deadline = time.monotonic() + 15
        time_value = None
        while time.monotonic() < deadline:
            time_result = self.in_client(["env", "PHASE115_TIME_ADDRESS=" + TIME_ADDRESS,
                "/usr/bin/python3", str(self.root / "scripts/phase11_5_time_local.py"),
                "probe", "--run"], timeout=20, check=False)
            if time_result.returncode == 0:
                time_value = json.loads(time_result.stdout)
                if time_value.get("status") == "PASS" and \
                        time_value.get("native_resolution", "").split() == \
                            ["time.local", TIME_ADDRESS]:
                    break
            time.sleep(1)
        require(time_value is not None and time_value.get("status") == "PASS" and
                time_value.get("native_resolution", "").split() ==
                    ["time.local", TIME_ADDRESS], "Package 11 client time authority")
        peer["time"] = time_value
        require("Connected to " + REMOTE_AP_MAC in peer["link"] and
                peer["identity"].strip() == CLIENT_MAC and
                CLIENT_ADDRESS + "/24" in peer["addresses"] and
                "default" not in peer["routes"] and
                peer["netns"].strip() != os.readlink("/proc/self/ns/net") and
                peer["mountns"].strip() != os.readlink("/proc/self/ns/mnt") and
                self.in_client(["ping", "-c", "2", "-W", "2", REMOTE_AP_ADDRESS],
                               check=False).returncode == 0,
                "Package 11 independent client")
        self.note("verified", {"host": current, "peer": peer})

    def stop_owned(self, name):
        load = self.value("systemctl", "show", "-p", "LoadState", "--value", name)
        if load == "not-found":
            return
        require(self.value("systemctl", "show", "-p", "Description", "--value", name) ==
                self.state["token"], "Package 11 unit ownership changed")
        command(["systemctl", "stop", name])

    def cleanup(self):
        if not self.state or self.state.get("restored"):
            return
        require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() ==
                self.state["host_boot"], "wspr5 boot changed during cleanup")
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
            attempt("namespace", lambda: command(["ip", "netns", "delete", NETNS])
                    if NETNS in self.value("ip", "netns", "list") else None)

        def restore_radio():
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and not Path(
                    "/sys/class/net", CLIENT_IF, "address").exists():
                time.sleep(.2)
            require(Path("/sys/class/net", CLIENT_IF, "address").read_text().strip() ==
                    CLIENT_MAC, "Client radio did not return")
            if self.state.get("client_unmanaged"):
                command(["nmcli", "device", "set", CLIENT_IF, "managed", "yes"])
            command(["iw", "dev", CLIENT_IF, "set", "power_save",
                     self.state["radio_power_save"]])
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                state = self.value("nmcli", "-g", "GENERAL.STATE", "device", "show",
                                   CLIENT_IF)
                if state.startswith("30 "):
                    return
                time.sleep(.2)
            raise ValueError("Client radio did not restore disconnected")

        if self.state.get("namespace") or self.state.get("client_unmanaged"):
            attempt("client radio", restore_radio)
        if self.state.get("timer_paused"):
            attempt("recovery timer", lambda: command(
                ["systemctl", "start", "pi-wifi-recover.timer"]))

        def restore_management():
            active = command(["nmcli", "-g", "GENERAL.CON-UUID", "device", "show",
                              "wlan1"], check=False).stdout.strip()
            if active != MANAGEMENT_PROFILE:
                command(["nmcli", "connection", "up", "uuid", MANAGEMENT_PROFILE,
                         "ifname", "wlan1"], timeout=60)

        attempt("management profile", restore_management)

        def verify_restored():
            current = self.host()
            require(NETNS not in self.value("ip", "netns", "list") and
                    "10.77.15." not in current["interfaces"] + current["routes"] and
                    current["installed_pid"].isdigit() and int(current["installed_pid"]) > 0,
                    "wspr5 fixture restoration")
            self.note("host_restored", current)

        attempt("wspr5 host", verify_restored)
        self.note("cleanup", {"failures": failures, "pico_state": "not inferred"})
        require(not failures, "Package 11 fixture cleanup incomplete")
        if self.state.get("cleanup_armed"):
            self.stop_owned(PREFIX + "-cleanup.timer")
        self.state["restored"] = True
        self.save()


def receive_exact(stream, size):
    value = bytearray()
    while len(value) < size:
        block = stream.recv(size - len(value))
        if not block:
            break
        value.extend(block)
    return bytes(value)


def ntp_broker(root):
    """Bridge client-namespace NTP requests to wspr5's local PPS chrony."""
    path = root / "ntp-broker.sock"
    require(not path.exists(), "NTP broker socket already exists")
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(str(path))
    listener.listen(4)
    listener.settimeout(.5)
    stop = False
    counters = {"requests": 0, "replies": 0, "timeouts": 0, "invalid": 0}

    def interrupted(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        while not stop:
            try:
                connection, _ = listener.accept()
            except TimeoutError:
                continue
            with connection:
                connection.settimeout(3)
                request = receive_exact(connection, 48)
                if len(request) != 48:
                    counters["invalid"] += 1
                    continue
                counters["requests"] += 1
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
                    upstream.bind((NTP_UPSTREAM, 0))
                    upstream.settimeout(.4)
                    for _ in range(5):
                        upstream.sendto(request, (NTP_UPSTREAM, 123))
                        try:
                            response, address = upstream.recvfrom(512)
                        except TimeoutError:
                            counters["timeouts"] += 1
                            continue
                        if address != (NTP_UPSTREAM, 123) or len(response) != 48 or \
                                response[24:32] != request[40:48]:
                            counters["invalid"] += 1
                            continue
                        connection.sendall(response)
                        counters["replies"] += 1
                        break
    finally:
        listener.close()
        path.unlink(missing_ok=True)
        print(json.dumps(dict(counters, status="stopped")), flush=True)


def ntp_client(root):
    """Serve PPS-backed NTP on the isolated client address via the Unix broker."""
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((TIME_ADDRESS, 123))
    server.settimeout(.5)
    stop = False
    counters = {"requests": 0, "replies": 0, "broker_failures": 0}

    def interrupted(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        while not stop:
            try:
                request, peer = server.recvfrom(512)
            except TimeoutError:
                continue
            if len(request) != 48:
                continue
            counters["requests"] += 1
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as broker:
                    broker.settimeout(2.5)
                    broker.connect(str(root / "ntp-broker.sock"))
                    broker.sendall(request)
                    broker.shutdown(socket.SHUT_WR)
                    response = receive_exact(broker, 48)
                require(len(response) == 48 and response[24:32] == request[40:48],
                        "Invalid broker NTP reply")
                server.sendto(response, peer)
                counters["replies"] += 1
            except (OSError, TimeoutError, ValueError):
                counters["broker_failures"] += 1
    finally:
        server.close()
        print(json.dumps(dict(counters, status="stopped")), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("setup", "verify", "cleanup", "client",
                                           "broker", "ntp-client"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no wspr5 fixture mutation.")
        return
    require(sys.platform == "linux" and os.geteuid() == 0, "Linux root required")
    root = args.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077 == 0, "Private Package 11 root required")
    os.umask(0o077)

    def interrupted(signum, frame):
        raise InterruptedError("Package 11 fixture interrupted")

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    if args.action == "client":
        hotspot.ROOT, hotspot.CLIENT_IF = root, CLIENT_IF
        hotspot.client(CLIENT_ADDRESS, association_seconds=90)
    elif args.action == "broker":
        ntp_broker(root)
    elif args.action == "ntp-client":
        ntp_client(root)
    else:
        fixture = Fixture(root)
        getattr(fixture, args.action)()


if __name__ == "__main__":
    main()
