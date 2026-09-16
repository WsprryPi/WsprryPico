#!/usr/bin/env python3
"""Opt-in Package 7 direct authority and lost-response RF packet."""

import argparse
import contextlib
import ctypes
import hashlib
import http.client as http_client
import json
import os
from pathlib import Path
import signal
import socket
import ssl
import struct
import subprocess
import threading
import time
import uuid

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_package7_plan import (ADDRESS, BOOT, DEVICE, HOSTNAME, PEER_SHA,
                                     SERIAL, SOURCE, validate)
from phase11_5_pilot import Decoder
from rf_wtp import WtpPeer
from validate_wtp_contract import frame


class Journal:
    def __init__(self, path):
        self.stream = path.open("x")
        self.sequence = 0
        self.lock = threading.Lock()

    def emit(self, kind, value):
        with self.lock:
            row = dict(sequence=self.sequence, kind=kind, value=value,
                       utc_ns=time.time_ns(), monotonic_ns=time.monotonic_ns())
            self.stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.sequence += 1
        return row

    def close(self):
        self.stream.close()


class Filter(ctypes.Structure):
    _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]


class Program(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.POINTER(Filter))]


class NetworkPeer:
    def __init__(self, root, packet, journal):
        cred = packet["credentials"]["controller"]
        self.context = ssl.create_default_context(cafile=str(root / cred["ca"]))
        self.context.minimum_version = self.context.maximum_version = ssl.TLSVersion.TLSv1_3
        self.context.load_cert_chain(root / cred["cert"], root / cred["key"])
        self.context.set_alpn_protocols(["wtp/1"])
        self.packet, self.journal = packet, journal
        self.session = packet["network_session"]
        self.number, self.stream, self.decoder = 0, None, Decoder()

    def connect(self):
        require(self.stream is None, "Network peer already connected")
        raw = socket.create_connection((ADDRESS, 18443), timeout=5)
        raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            self.stream = self.context.wrap_socket(raw, server_hostname=HOSTNAME)
        except BaseException:
            raw.close()
            raise
        require(self.stream.version() == "TLSv1.3" and
                self.stream.selected_alpn_protocol() == "wtp/1" and
                hashlib.sha256(self.stream.getpeercert(binary_form=True)).hexdigest() == PEER_SHA,
                "Authenticated Package 7 controller")
        self.decoder = Decoder()
        self.journal.emit("network_connect", {"local": list(self.stream.getsockname()),
                          "peer": list(self.stream.getpeername()), "session": self.session})
        hello = self.ask("HELLO", {"versions": ["WTP/1"],
                         "client_name": "phase11-5-package7", "client_version": "1"})
        require(hello["device_id"] == DEVICE and hello["boot_id"] == BOOT,
                "Network HELLO identity")
        require(self.ask("CAPS")["engine"] == "pio-dma-gp2", "Network engine")

    def close(self, reset=False):
        if self.stream is not None:
            if reset:
                self.stream.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                       struct.pack("ii", 1, 0))
            self.stream.close()
            self.stream = None

    def request(self, op, body=None):
        self.number += 1
        return {"type": "request", "protocol": "WTP/1", "session_id": self.session,
                "request_id": f"{self.number:032x}", "op": op, "body": body or {}}

    def encoded(self, request):
        return frame(json.dumps(request, separators=(",", ":")).encode())

    def transact(self, request, encoded=None, timeout=6):
        encoded = encoded or self.encoded(request)
        self.journal.emit("network_tx", {"request": request, "hex": encoded.hex(),
                          "write_complete": False})
        self.stream.sendall(encoded)
        self.journal.emit("network_write_complete", {"op": request["op"],
                          "request_id": request["request_id"], "bytes": len(encoded)})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.stream.settimeout(max(.001, deadline - time.monotonic()))
            data = self.stream.recv(4096)
            require(data, "Network EOF")
            self.journal.emit("network_rx", {"op": request["op"], "hex": data.hex()})
            for value in self.decoder.feed(data):
                self.journal.emit("network_message", value)
                require(value["session_id"] == self.session, "Foreign network session")
                if value["type"] == "event":
                    require(value["boot_id"] == BOOT, "Event boot changed")
                    continue
                require(value["request_id"] == request["request_id"] and
                        value["op"] == request["op"] and value["ok"] is True,
                        f"{request['op']} failed: {value.get('error')}")
                return value["body"]
        raise TimeoutError(request["op"] + " response timeout")

    def ask(self, op, body=None):
        return self.transact(self.request(op, body))


def browser_context(root, packet):
    cred = packet["credentials"]["browser"]
    result = ssl.create_default_context(cafile=str(root / cred["ca"]))
    result.minimum_version = result.maximum_version = ssl.TLSVersion.TLSv1_3
    result.load_cert_chain(root / cred["cert"], root / cred["key"])
    result.set_alpn_protocols(["http/1.1"])
    return result


def http(root, packet, journal, method, path, body=None, headers=None):
    context = browser_context(root, packet)
    encoded = b"" if body is None else json.dumps(body, separators=(",", ":")).encode()
    request_headers = {"Host": f"{HOSTNAME}:18443", "Connection": "close"}
    if method != "GET":
        request_headers.update({"Origin": f"https://{HOSTNAME}:18443",
                                "Content-Type": "application/json",
                                "X-WsprryPico-Request": "1"})
    request_headers.update(headers or {})
    with socket.create_connection((ADDRESS, 18443), timeout=5) as raw:
        with context.wrap_socket(raw, server_hostname=HOSTNAME) as stream:
            require(stream.selected_alpn_protocol() == "http/1.1" and
                    hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest() == PEER_SHA,
                    "Authenticated Package 7 browser")
            connection = http_client.HTTPConnection(HOSTNAME)
            connection.sock = stream
            connection.request(method, path, body=encoded, headers=request_headers)
            response = connection.getresponse()
            data = response.read(131073)
            result_headers = dict(response.getheaders())
    require(len(data) <= 131072, "Oversized management response")
    value = json.loads(data)
    journal.emit("http", {"method": method, "path": path, "status": response.status,
                 "headers": result_headers, "body": value,
                 "request_body_sha256": hashlib.sha256(encoded).hexdigest()})
    return response.status, result_headers, value


def console_info(path, journal):
    def emit(kind, value):
        journal.emit("console_" + kind, value)
    with exclusive_port(path) as fd:
        info = exchange(fd, b"INFO\n", time.monotonic() + 5, emit, False)
    require(info["ok"] is True and info["device_id"] == DEVICE and
            info["revision"] == SOURCE[:12] and info["status"]["boot_id"] == BOOT and
            info["status"]["engine"] == "pio-dma-gp2" and
            info["rf_render_in_ram"] is True, "Console candidate identity")
    return info


def status(peer, state, job, owner, active=None):
    value = peer.ask("STATUS")
    require(value["boot_id"] == BOOT and value["state"] == state and
            value["job_id"] == job and value["owner_id"] == owner,
            "Package 7 state/authority")
    if active is not None:
        require(value["output_active"] is active, "Package 7 output authority")
    return value


def foreign_checks(usb, peer, journal, state, job, owner):
    expected = {"CLAIM": "BUSY", "RELEASE": "NOT_OWNER", "ABORT": "NOT_OWNER"}
    before = status(peer, state, job, owner)
    for op, body in (("CLAIM", {"owner_id": uuid.uuid4().hex, "lease_ms": 60000}),
                     ("RELEASE", {}), ("ABORT", {"job_id": job or uuid.uuid4().hex})):
        try:
            usb.request(op, body)
        except RuntimeError as error:
            value = error.args[0]
            require(value["code"] == expected[op], f"Unexpected foreign {op} result")
            journal.emit("foreign_rejected", {"state": state, "op": op, "error": value})
        else:
            raise ValueError("Foreign operation succeeded: " + op)
        after = status(peer, state, job, owner)
        require({k: after[k] for k in ("state", "job_id", "owner_id", "output_active")} ==
                {k: before[k] for k in ("state", "job_id", "owner_id", "output_active")},
                "Foreign rejection changed authority")


def storage_check(root, packet, peer, journal, state, job, owner, expected_config):
    before_status = status(peer, state, job, owner)
    code, headers, before = http(root, packet, journal, "GET", "/api/v1/config")
    require(code == 200 and "ETag" in headers and before["config"] == expected_config,
            "Configuration precondition")
    revision = headers["ETag"]
    code, _, rejected = http(root, packet, journal, "PUT", "/api/v1/config",
                              before["config"], {"If-Match": revision})
    require(code == 409 and rejected["error"]["code"] == "busy",
            "Busy configuration write was not rejected")
    code, after_headers, after = http(root, packet, journal, "GET", "/api/v1/config")
    after_status = status(peer, state, job, owner)
    require(code == 200 and after_headers["ETag"] == revision and after == before and
            {k: after_status[k] for k in ("state", "job_id", "owner_id", "output_active")} ==
            {k: before_status[k] for k in ("state", "job_id", "owner_id", "output_active")},
            "Rejected storage write changed durable or job state")
    journal.emit("storage_rejected", {"state": state, "etag": revision,
                 "job_id": job, "owner_id": owner})


def attach_drop(stream):
    filters = (Filter * 1)(Filter(6, 0, 0, 0))
    program = Program(1, filters)
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.setsockopt(stream.fileno(), socket.SOL_SOCKET, 26,
                             ctypes.byref(program), ctypes.sizeof(program))
    require(result == 0, "Unable to attach socket-local receive drop")


def lost(root, peer, usb, journal, op, body, target, job, owner):
    request = peer.request(op, body)
    encoded = peer.encoded(request)
    (root / f"{op.lower()}-request.bin").write_bytes(encoded)
    local = peer.stream.getsockname()
    capture_log = (root / f"{op.lower()}-capture.log").open("xb")
    capture = subprocess.Popen(["/usr/bin/tcpdump", "-U", "-n", "-i", "wlan2", "-w",
        str(root / f"{op.lower()}.pcap"), "host", ADDRESS, "and", "tcp", "and", "port",
        "18443", "and", "port", str(local[1])], stdout=capture_log, stderr=capture_log)
    try:
        time.sleep(.5)
        require(capture.poll() is None, "Packet capture failed to start")
        attach_drop(peer.stream)
        journal.emit("fault_attached", {"op": op, "local": list(local),
                     "filter": "socket-local RET 0"})
        peer.stream.sendall(encoded)
        journal.emit("lost_write_complete", {"op": op, "request": request,
                     "hex": encoded.hex(), "bytes": len(encoded), "delivered_reply_bytes": 0})
        peer.stream.settimeout(.8)
        try:
            delivered = peer.stream.recv(65536)
        except socket.timeout:
            delivered = b""
        require(not delivered, "Lost-response filter delivered bytes")
        independent = usb.request("STATUS", {})
        require(independent["boot_id"] == BOOT and independent["state"] == target and
                independent["job_id"] == job and independent["owner_id"] == owner,
                "Independent lost-operation effect")
        journal.emit("lost_independent_effect", {"op": op, "status": independent})
        peer.close(reset=True)
        time.sleep(.2)
    finally:
        if capture.poll() is None:
            capture.send_signal(signal.SIGINT)
            capture.wait(timeout=5)
        capture_log.close()
    decoded = subprocess.check_output(["/usr/bin/tcpdump", "-tttt", "-nnvvv", "-r",
                                      str(root / f"{op.lower()}.pcap")],
                                      stderr=subprocess.DEVNULL, text=True)
    (root / f"{op.lower()}-packets.txt").write_text(decoded)
    require("0 packets dropped by kernel" in (root / f"{op.lower()}-capture.log").read_text(),
            "Capture dropped packets")
    inbound = [line for line in decoded.splitlines()
               if f"{ADDRESS}.18443 > {local[0]}.{local[1]}" in line and "length 0" not in line]
    require(inbound, "No captured inbound response ciphertext")
    peer.connect()
    status(peer, target, job, owner)
    replay = peer.transact(request, encoded)
    status(peer, target, job, owner)
    journal.emit("lost_replay_pass", {"op": op, "request_id": request["request_id"],
                 "job_id": job, "replay": replay, "inbound_ciphertext_packets": len(inbound)})


def make_job(job_id, duration_ns):
    return {"job_id": job_id, "profile": "rf-events/1", "mode": "tone",
            "total_duration_ns": str(duration_ns), "allow_frequency_adjustment": True,
            "events": [{"offset_ns": "0", "duration_ns": str(duration_ns),
                        "rf_on": True, "frequency_nhz": "135500000000000"}]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no device, RF, network or USB accessed.")
        return
    require(os.geteuid() == 0, "Package 7 direct packet requires root")
    root = args.root.resolve(strict=True)
    require(root.is_dir() and root.stat().st_mode & 0o077 == 0, "Private evidence root")
    packet = validate(json.loads((root / "packet.json").read_text()))
    os.umask(0o077)
    journal = Journal(root / "direct.jsonl")
    base = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}")
    before = console_info(Path(str(base) + "-if00"), journal)
    require(before["status"]["state"] == "empty" and
            before["status"]["output_active"] is False and
            before["status"]["enabled"] is False and
            before["status"]["storage_healthy"] is True and
            before["status"]["clock_state"] == "synchronized", "Direct admission")
    code, _, config = http(root, packet, journal, "GET", "/api/v1/config")
    require(code == 200 and config["config"] is not None, "Configuration baseline")
    owner, job = packet["owner_id"], packet["direct_job_id"]
    peer = NetworkPeer(root, packet, journal)
    try:
        with exclusive_port(Path(str(base) + "-if02")) as fd, \
                (root / "foreign-usb-frames.jsonl").open("x") as wire:
            def emit(kind, value):
                journal.emit("foreign_usb_" + kind, value)
            usb = WtpPeer(fd, session=packet["foreign_session"])
            with contextlib.redirect_stdout(wire):
                hello = usb.request("HELLO", {"versions": ["WTP/1"],
                                    "client_name": "phase11-5-package7-foreign",
                                    "client_version": "1"})
                require(hello["device_id"] == DEVICE and hello["boot_id"] == BOOT,
                        "Foreign USB identity")
                peer.connect()
                caps = peer.ask("CAPS")
                require(caps["minimum_lease_ms"] <= 60000 <= caps["maximum_lease_ms"] and
                        int(caps["max_job_duration_ns"]) >= 12_000_000_000,
                        "Direct capability bounds")
                peer.ask("CLAIM", {"owner_id": owner, "lease_ms": 60000})
                foreign_checks(usb, peer, journal, "empty", None, owner)
                storage_check(root, packet, peer, journal, "empty", None, owner, config["config"])
                lost(root, peer, usb, journal, "LOAD", make_job(job, 12_000_000_000),
                     "loaded", job, owner)
                foreign_checks(usb, peer, journal, "loaded", job, owner)
                storage_check(root, packet, peer, journal, "loaded", job, owner, config["config"])
                peer.ask("RENEW", {"owner_id": owner, "lease_ms": 60000})
                clock = peer.ask("GET_CLOCK")
                require(clock["state"] == "synchronized" and clock["leap"] == "normal",
                        "Synchronized arm clock")
                arm = {"job_id": job, "start_utc_ns": str(int(clock["utc_now_ns"]) + 10_000_000_000),
                       "max_start_uncertainty_ns": "500000000"}
                lost(root, peer, usb, journal, "ARM", arm, "armed", job, owner)
                foreign_checks(usb, peer, journal, "armed", job, owner)
                storage_check(root, packet, peer, journal, "armed", job, owner, config["config"])
                deadline = time.monotonic() + 12
                while True:
                    current = usb.request("STATUS", {})
                    if current["state"] == "running" and current["output_active"] is True:
                        break
                    require(current["state"] == "armed" and time.monotonic() < deadline,
                            "Running transition")
                    time.sleep(.05)
                running_info = console_info(Path(str(base) + "-if00"), journal)
                require(running_info["status"]["state"] == "running" and
                        running_info["status"]["output_active"] is True and
                        running_info["status"]["job_id"] == job, "Console running authority")
                foreign_checks(usb, peer, journal, "running", job, owner)
                storage_check(root, packet, peer, journal, "running", job, owner, config["config"])
                lost(root, peer, usb, journal, "ABORT", {"job_id": job}, "aborted", job, owner)
                terminal = status(peer, "aborted", job, owner, False)
                matches = [r for r in terminal["terminal_records"] if r["job_id"] == job]
                require(len(matches) == 1 and matches[0]["state"] == "aborted" and
                        matches[0]["output_active"] is False, "One aborted terminal")
                peer.ask("RELEASE")
                final = peer.ask("STATUS")
                require(final["state"] == "empty" and final["job_id"] is None and
                        final["owner_id"] is None and final["output_active"] is False,
                        "Direct final idle")
                journal.emit("direct_pass", {"job_id": job, "planned_duration_ns": 12_000_000_000,
                             "terminal": matches[0], "final": final})
    finally:
        try:
            if peer.stream is not None:
                current = peer.ask("STATUS")
                if current.get("owner_id") == owner:
                    if (current.get("job_id") is not None and current["state"] not in
                            ("complete", "aborted", "failed", "missed")):
                        peer.ask("ABORT", {"job_id": current["job_id"]})
                    peer.ask("RELEASE")
        finally:
            peer.close()
            after = console_info(Path(str(base) + "-if00"), journal)
            journal.emit("direct_cleanup", after)
            journal.close()


if __name__ == "__main__":
    main()
