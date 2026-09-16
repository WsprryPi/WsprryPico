#!/usr/bin/env python3
"""Opt-in Package 3 network-WTP timeout and recovery evidence on Pico A."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import ssl
import subprocess
import time

from phase11_5_device_management import digest, save
from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_pilot import Decoder, DEVICE, SERIAL
from phase11_5_pilot_supervisor import B_DEVICE, B_SERIAL, configuration, finished
from phase11_5_r3_v2_admission import maximum_job
from validate_wtp_contract import frame


SCHEMA = "phase11.5-package3-progress-v1"
SOURCE = "ca3c5dce40360b7eea2f9c45618232caa68cdbb6"
IMAGE = "6c7aa0b7df6756e8f248570d682c6af4bbcfc44a5ad67e94d6761709ced0bd59"
BOOT = "5e0d6bc3e383b8c1cb4b0db9ed636bf5"
NAME = "wsprrypico-0a60df.local"
PEER_SHA = "06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016"
CASES = ["drained-inactivity", "incomplete-input", "no-output-progress"]
OPS = {"HELLO", "STATUS", "CLAIM", "LOAD", "ABORT", "RELEASE"}


def identity(value):
    require(isinstance(value, str) and len(value) == 32 and
            all(c in "0123456789abcdef" for c in value), "32-character identity")
    return value


def validate(packet):
    require(packet["schema"] == packet["scope"] == SCHEMA and
            packet["standing_authority"] == "R3-COMPLETE-20260913-v2" and
            packet["source_revision"] == SOURCE and packet["image_sha256"] == IMAGE and
            packet["boot_id"] == BOOT and packet["serial"] == SERIAL and
            packet["device_id"] == DEVICE and packet["cases"] == CASES,
            "Exact Package 3 progress scope")
    require(packet["runtime_seconds"] == 240 and packet["restoration_seconds"] == 150 and
            packet["rf_jobs"] == packet["rf_duration_ns"] == packet["flashes"] ==
            packet["wifi_cycles"] == packet["configuration_writes"] == 0,
            "Finite zero-RF/no-management budget")
    require(packet["client_netns"] == f"/proc/{packet['client_pid']}/ns/net" and
            packet["client_mountns"] == f"/proc/{packet['client_pid']}/ns/mnt" and
            packet["address"] == "10.77.15.10" and packet["port"] == 18443,
            "Frozen isolated client endpoint")
    for key in ("inventory_session", "b_session", "idle_session", "partial_session",
                "output_session", "owner_id", "job_id"):
        identity(packet[key])
    require(len({packet[k] for k in ("inventory_session", "b_session", "idle_session",
                "partial_session", "output_session", "owner_id", "job_id")}) == 7,
            "Distinct Package 3 identities")
    require(packet["credentials"] == {
        "controller": {"ca": "credentials/controller/client-ca.crt",
            "cert": "credentials/controller/client.crt",
            "key": "credentials/controller/client.key"},
        "browser": {"ca": "credentials/browser/client-ca.crt",
            "cert": "credentials/browser/client.crt",
            "key": "credentials/browser/client.key"},
    }, "Frozen controller/browser credentials")
    return packet


class Journal:
    def __init__(self, path):
        self.file = path.open("x")
        self.sequence = 0

    def emit(self, kind, value):
        self.file.write(json.dumps({"sequence": self.sequence, "kind": kind, "value": value,
            "monotonic_ns": time.monotonic_ns(), "utc_ns": time.time_ns()}) + "\n")
        self.file.flush()
        os.fsync(self.file.fileno())
        self.sequence += 1

    def close(self):
        self.file.close()


class NetworkWtp:
    def __init__(self, root, packet, journal):
        self.root = root
        self.packet = packet
        self.journal = journal
        self.request_number = 0
        self.decoders = {}
        credentials = packet["credentials"]["controller"]
        self.context = ssl.create_default_context(cafile=str(root / credentials["ca"]))
        self.context.minimum_version = self.context.maximum_version = ssl.TLSVersion.TLSv1_3
        self.context.load_cert_chain(root / credentials["cert"], root / credentials["key"])
        self.context.set_alpn_protocols(["wtp/1"])
        credentials = packet["credentials"]["browser"]
        self.browser_context = ssl.create_default_context(cafile=str(root / credentials["ca"]))
        self.browser_context.minimum_version = self.browser_context.maximum_version = ssl.TLSVersion.TLSv1_3
        self.browser_context.load_cert_chain(root / credentials["cert"], root / credentials["key"])
        self.browser_context.set_alpn_protocols(["http/1.1"])

    def connect(self, label):
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            raw.settimeout(5)
            raw.connect((self.packet["address"], self.packet["port"]))
            stream = self.context.wrap_socket(raw, server_hostname=NAME)
        except BaseException:
            raw.close()
            raise
        require(stream.version() == "TLSv1.3" and stream.selected_alpn_protocol() == "wtp/1" and
                hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest() == PEER_SHA,
                "Authenticated TLS 1.3 WTP peer")
        stream.settimeout(.25)
        self.journal.emit("tls", {"label": label, "version": stream.version(), "alpn": "wtp/1",
            "peer_sha256": PEER_SHA, "local": list(stream.getsockname()),
            "peer": list(stream.getpeername()),
            "receive_buffer": stream.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)})
        self.decoders[stream.fileno()] = Decoder()
        return stream

    def constrain_receive(self, stream, label):
        stream.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
        stream.setsockopt(socket.IPPROTO_TCP, socket.TCP_WINDOW_CLAMP, 1024)
        actual = stream.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
        require(actual <= 4096, "Bounded WTP receive window")
        self.journal.emit("receive_window", {"label": label, "requested": 1024, "actual": actual})
        return actual

    def request(self, op, body, session):
        require(op in OPS, "Package 3 WTP operation")
        self.request_number += 1
        return {"type": "request", "protocol": "WTP/1", "session_id": session,
            "request_id": f"{self.request_number:032x}", "op": op, "body": body}

    def ask(self, stream, label, op, body, session, deadline_seconds=5):
        request = self.request(op, body, session)
        raw = frame(json.dumps(request, separators=(",", ":")).encode())
        self.journal.emit("wtp_tx", {"label": label, "request": request, "hex": raw.hex()})
        stream.sendall(raw)
        decoder = self.decoders[stream.fileno()]
        end = time.monotonic() + deadline_seconds
        while time.monotonic() < end:
            try:
                part = stream.recv(4096)
            except (socket.timeout, ssl.SSLWantReadError):
                continue
            require(part, "WTP EOF before response")
            self.journal.emit("wtp_rx", {"label": label, "hex": part.hex()})
            answer = None
            for value in decoder.feed(part):
                self.journal.emit("wtp_message", {"label": label, "message": value})
                require(value["session_id"] == session, "WTP response session")
                if value["type"] == "event":
                    require(value["boot_id"] == BOOT, "WTP event boot")
                    continue
                require(answer is None and value["request_id"] == request["request_id"] and
                        value["op"] == op and value["ok"] is True, "WTP operation response")
                answer = value
            if answer is not None:
                return answer["body"]
        raise TimeoutError(f"Five-second WTP response deadline: {label}")

    def transport(self, label):
        request = (f"GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\n"
                   "Connection: close\r\n\r\n").encode()
        deadline = time.monotonic() + 8
        with socket.create_connection((self.packet["address"], self.packet["port"]), timeout=5) as raw:
            with self.browser_context.wrap_socket(raw, server_hostname=NAME) as stream:
                require(stream.version() == "TLSv1.3" and
                        stream.selected_alpn_protocol() == "http/1.1" and
                        hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest() == PEER_SHA,
                        "Authenticated TLS 1.3 HTTPS peer")
                stream.settimeout(.25)
                stream.sendall(request)
                response = b""
                complete = None
                while time.monotonic() < deadline:
                    try:
                        part = stream.recv(4096)
                    except (socket.timeout, ssl.SSLWantReadError):
                        continue
                    except ssl.SSLEOFError:
                        part = b""
                    if part:
                        response += part
                        require(len(response) <= 131072, "Bounded HTTPS status response")
                    if b"\r\n\r\n" in response:
                        head, body = response.split(b"\r\n\r\n", 1)
                        lengths = [line.split(b":", 1)[1].strip() for line in head.split(b"\r\n")
                                   if line.lower().startswith(b"content-length:")]
                        require(len(lengths) == 1, "One HTTPS Content-Length")
                        length = int(lengths[0])
                        if len(body) >= length:
                            require(len(body) == length, "Exact HTTPS status body")
                            complete = (head, body)
                            break
                    if not part:
                        break
        require(complete is not None, "Complete HTTPS status response")
        head, body = complete
        self.journal.emit("https_raw", {"label": label, "request_hex": request.hex(),
            "response_hex": response.hex(), "peer_sha256": PEER_SHA})
        status_line = head.split(b"\r\n", 1)[0].split(b" ", 2)
        require(len(status_line) == 3 and status_line[:2] == [b"HTTP/1.1", b"200"],
                "HTTPS status code")
        value = json.loads(body)
        require(value["job"]["boot_id"] == BOOT and
                isinstance(value["transport"]["active"], int) and
                isinstance(value["transport"]["pending"], int) and
                isinstance(value["transport"]["timeouts"], int),
                "Current HTTPS transport status")
        self.journal.emit("https_status", {"label": label, "request_hex": request.hex(),
            "response_hex": response.hex(), "value": value, "peer_sha256": PEER_SHA})
        return value["transport"]


def inventory(root, packet, label, b=False):
    with (root / f"{label}.stdout").open("xb") as out, (root / f"{label}.stderr").open("xb") as err:
        result = subprocess.run(["python3", str(root / "scripts/phase11_5_inventory.py"),
            "--serial", B_SERIAL if b else SERIAL, "--device-id", B_DEVICE if b else DEVICE,
            "--session-id", packet["b_session"] if b else packet["inventory_session"], "--run"],
            stdout=out, stderr=err, timeout=65)
    require(result.returncode == 0, "Package 3 inventory: " + label)
    return finished(root / f"{label}.stdout", "READ_ONLY_INVENTORY")


def inactive(value, boot):
    status = value["wtp"]["STATUS"]
    require(status["boot_id"] == boot and status["state"] == "empty" and
            status["output_active"] is False and status["owner_id"] is None and
            status["job_id"] is None and value["info"]["status"]["enabled"] is False,
            "Empty/inactive/unowned authority")


def cleanup_loaded(root, packet, journal, label="failure-cleanup"):
    client = NetworkWtp(root, packet, journal)
    session = hashlib.sha256(("cleanup:" + packet["output_session"]).encode()).hexdigest()[:32]
    with client.connect(label) as stream:
        hello = client.ask(stream, label + "-hello", "HELLO",
            {"versions": ["WTP/1"], "client_name": "Package 3 cleanup", "client_version": "1"},
            session, deadline_seconds=10)
        require(hello["boot_id"] == BOOT, "Cleanup HELLO")
        status = client.ask(stream, label + "-status", "STATUS", {}, session,
            deadline_seconds=10)
        require(status["boot_id"] == BOOT and status["output_active"] is False,
                "Cleanup inactive authority")
        if status["state"] == "loaded":
            require(status["job_id"] == packet["job_id"] and
                    status["owner_id"] in (None, packet["owner_id"]),
                    "Cleanup exact retained Package 3 job")
        if status["state"] == "loaded" or status["owner_id"] == packet["owner_id"]:
            claimed = client.ask(stream, label + "-claim", "CLAIM",
                {"owner_id": packet["owner_id"], "lease_ms": 60000}, session,
                deadline_seconds=10)
            require(claimed["owner_id"] == packet["owner_id"], "Cleanup CLAIM")
            if status["state"] == "loaded":
                client.ask(stream, label + "-abort", "ABORT", {"job_id": packet["job_id"]},
                    session, deadline_seconds=10)
            client.ask(stream, label + "-release", "RELEASE", {}, session, deadline_seconds=10)
            status = client.ask(stream, label + "-final", "STATUS", {}, session,
                deadline_seconds=10)
        require(status["state"] == "empty" and status["job_id"] is None and
                status["owner_id"] is None and status["output_active"] is False,
                "Cleanup final empty authority")
    journal.emit("cleanup", {"label": label, "status": status})
    return status


def run(root, packet):
    journal = Journal(root / "progress.jsonl")
    result = {"status": "RUNNING", "cases": [], "rf_jobs": 0, "rf_duration_ns": 0}
    save(root / "progress-result.json", result)
    started = time.monotonic()
    client = NetworkWtp(root, packet, journal)

    def checkpoint():
        require(time.monotonic() - started < packet["runtime_seconds"], "Package 3 runtime")

    def console_info(label):
        checkpoint()
        with exclusive_port(Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")) as fd:
            value = exchange(fd, b"INFO\n", time.monotonic() + 5,
                lambda kind, body: journal.emit("console_" + kind, {"label": label, "value": body}), False)
        require(value["device_id"] == DEVICE and value["revision"] == SOURCE[:12] and
                value["status"]["boot_id"] == BOOT and value["status"]["output_active"] is False,
                "Current inactive Package 3 INFO")
        journal.emit("info", {"label": label, "value": value})
        return value

    def wait_close(stream, label, minimum, maximum, began_ns=None):
        began = began_ns or time.monotonic_ns()
        received = 0
        outcome = None
        while (time.monotonic_ns() - began) / 1e9 <= maximum:
            checkpoint()
            try:
                part = stream.recv(4096)
                if not part:
                    outcome = "eof"
                    break
                received += len(part)
                journal.emit("unexpected_rx", {"label": label, "hex": part.hex()})
            except socket.timeout:
                continue
            except (ConnectionResetError, ssl.SSLEOFError):
                outcome = "reset"
                break
        elapsed = (time.monotonic_ns() - began) / 1e9
        journal.emit("target_close", {"label": label, "outcome": outcome,
            "elapsed_seconds": elapsed, "received_bytes": received})
        require(outcome in ("eof", "reset") and minimum <= elapsed <= maximum,
                f"{label} close interval")
        return elapsed, outcome, received

    def recover(label, session, began_ns, expected_status="empty"):
        with client.connect(label) as stream:
            hello = client.ask(stream, label + "-hello", "HELLO",
                {"versions": ["WTP/1"], "client_name": "Package 3 recovery", "client_version": "1"}, session)
            require(hello["device_id"] == DEVICE and hello["boot_id"] == BOOT, "Recovery HELLO")
            status = client.ask(stream, label + "-status", "STATUS", {}, session)
            require(status["boot_id"] == BOOT and status["state"] == expected_status and
                    status["output_active"] is False, "Authenticated recovery state")
        elapsed = (time.monotonic_ns() - began_ns) / 1e9
        require(elapsed <= 15, "Authenticated recovery within fifteen seconds")
        settle_end = time.monotonic() + 3
        while True:
            settled = client.transport(label + "-settled")
            if settled["active"] == 1 and settled["pending"] == 0:
                break
            require(time.monotonic() < settle_end, "Recovery connection reclamation")
            time.sleep(.1)
        journal.emit("recovery", {"label": label, "elapsed_seconds": elapsed, "status": status})
        return elapsed, status

    before_a = before_b = None
    try:
        before_b = inventory(root, packet, "before-b", True)
        inactive(before_b, packet["b_boot_id"])
        before_a = inventory(root, packet, "before-a")
        inactive(before_a, BOOT)
        console_info("initial")
        initial_transport = client.transport("initial")
        require(initial_transport["active"] == 1 and initial_transport["pending"] == 0,
                "No initial client besides the authenticated status request")

        # 2.3a: fully drain HELLO, then send no bytes for the independent 30 s timer.
        with client.connect("drained-inactivity") as stream:
            hello = client.ask(stream, "drained-inactivity", "HELLO",
                {"versions": ["WTP/1"], "client_name": "Package 3 inactivity", "client_version": "1"},
                packet["idle_session"])
            require(hello["boot_id"] == BOOT, "Inactivity HELLO")
            idle_began = time.monotonic_ns()
            prior = client.transport("drained-before")
            require(prior["active"] == 2 and prior["pending"] == 0,
                    "Drained WTP plus authenticated status concurrency")
            elapsed, outcome, received = wait_close(stream, "drained-inactivity", 29.0, 33.5,
                idle_began)
        closed_at = time.monotonic_ns()
        after_info = console_info("drained-after")
        after = client.transport("drained-after")
        require(after_info["network_wtp_close_reason"] == 3 and
                after["timeouts"] == prior["timeouts"] + 1 and
                after["active"] == 1 and after["pending"] == 0 and received == 0,
                "Distinct drained WTP inactivity close")
        recovery_seconds, _ = recover("drained-recovery", packet["idle_session"], closed_at)
        result["cases"].append({"id": "2.3a", "status": "PASS", "elapsed_seconds": elapsed,
            "close": outcome, "close_reason": 3, "timeout_delta": 1,
            "recovery_seconds": recovery_seconds})
        save(root / "progress-result.json", result)

        # 2.3b: a valid frame prefix starts the parser's separate five-second deadline.
        with client.connect("incomplete-input") as stream:
            hello = client.ask(stream, "incomplete-hello", "HELLO",
                {"versions": ["WTP/1"], "client_name": "Package 3 partial", "client_version": "1"},
                packet["partial_session"])
            require(hello["boot_id"] == BOOT, "Incomplete-input HELLO")
            request = client.request("STATUS", {}, packet["partial_session"])
            raw = frame(json.dumps(request, separators=(",", ":")).encode())
            prior = client.transport("incomplete-before")
            require(prior["active"] == 2 and prior["pending"] == 0,
                    "Partial WTP plus authenticated status concurrency")
            journal.emit("wtp_partial_tx", {"label": "incomplete-input", "request": request,
                "full_sha256": hashlib.sha256(raw).hexdigest(), "full_bytes": len(raw),
                "sent_hex": raw[:8].hex(), "sent_bytes": 8})
            stream.sendall(raw[:8])
            elapsed, outcome, received = wait_close(stream, "incomplete-input", 4.8, 7.5)
        closed_at = time.monotonic_ns()
        after_info = console_info("incomplete-after")
        after = client.transport("incomplete-after")
        require(after_info["network_wtp_close_reason"] == 4 and
                after["timeouts"] == prior["timeouts"] and
                after["active"] == 1 and after["pending"] == 0 and received == 0,
                "Distinct incomplete WTP input close")
        recovery_seconds, _ = recover("incomplete-recovery", packet["partial_session"], closed_at)
        result["cases"].append({"id": "2.3b", "status": "PASS", "elapsed_seconds": elapsed,
            "close": outcome, "close_reason": 4, "timeout_delta": 0,
            "partial_bytes": 8, "recovery_seconds": recovery_seconds})
        save(root / "progress-result.json", result)

        # 2.3c: one complete maximum LOAD creates a single large response; do not read it.
        stream = client.connect("no-output-progress")
        try:
            hello = client.ask(stream, "output-hello", "HELLO",
                {"versions": ["WTP/1"], "client_name": "Package 3 output stall", "client_version": "1"},
                packet["output_session"])
            require(hello["boot_id"] == BOOT, "Output-stall HELLO")
            claim = client.ask(stream, "output-claim", "CLAIM",
                {"owner_id": packet["owner_id"], "lease_ms": 60000}, packet["output_session"])
            require(claim["owner_id"] == packet["owner_id"], "Output-stall CLAIM")
            client.constrain_receive(stream, "no-output-load")
            job = maximum_job(packet["job_id"], duration=128_000_000_000)
            request = client.request("LOAD", job, packet["output_session"])
            raw = frame(json.dumps(request, separators=(",", ":")).encode())
            prior = client.transport("output-before")
            require(prior["active"] == 2 and prior["pending"] == 0,
                    "Output-stall WTP plus authenticated status concurrency")
            journal.emit("wtp_tx", {"label": "no-output-load", "request": request, "hex": raw.hex(),
                "application_reads_after_load": 0})
            stream.sendall(raw)
            began = time.monotonic_ns()
            samples = []
            while (time.monotonic_ns() - began) / 1e9 <= 25:
                info = console_info("output-wait")
                samples.append({"monotonic_ns": time.monotonic_ns(),
                    "state": info["status"]["state"], "reason": info["network_wtp_close_reason"]})
                if info["status"]["state"] == "loaded" and info["network_wtp_close_reason"] == 4:
                    break
                time.sleep(.25)
            elapsed = (time.monotonic_ns() - began) / 1e9
            require(4.8 <= elapsed <= 25 and samples[-1]["state"] == "loaded" and
                    samples[-1]["reason"] == 4,
                    "Distinct WTP no-output-progress close")
            journal.emit("output_stall", {"elapsed_seconds": elapsed, "load_bytes": len(raw),
                "load_sha256": hashlib.sha256(raw).hexdigest(), "application_reads_after_load": 0,
                "samples": samples})
        finally:
            stream.close()
        closed_at = time.monotonic_ns()
        after_info = console_info("output-after")
        after = client.transport("output-after")
        require(after["timeouts"] == prior["timeouts"] and after["active"] == 1 and
                after["pending"] == 0 and after_info["network_wtp_close_reason"] == 4,
                "Output timeout is endpoint-local")
        with client.connect("output-recovery") as recovery:
            hello = client.ask(recovery, "output-recovery-hello", "HELLO",
                {"versions": ["WTP/1"], "client_name": "Package 3 output recovery", "client_version": "1"},
                packet["output_session"])
            require(hello["boot_id"] == BOOT, "Output recovery HELLO")
            status = client.ask(recovery, "output-recovery-status", "STATUS", {}, packet["output_session"])
            require(status["state"] == "loaded" and status["job_id"] == packet["job_id"] and
                    status["owner_id"] == packet["owner_id"] and status["output_active"] is False,
                    "LOAD applied exactly once despite unread response")
            client.ask(recovery, "output-abort", "ABORT", {"job_id": packet["job_id"]}, packet["output_session"])
            client.ask(recovery, "output-release", "RELEASE", {}, packet["output_session"])
            final_status = client.ask(recovery, "output-final-status", "STATUS", {}, packet["output_session"])
            require(final_status["state"] == "empty" and final_status["job_id"] is None and
                    final_status["owner_id"] is None and final_status["output_active"] is False,
                    "Output-stall cleanup authority")
        recovery_seconds = (time.monotonic_ns() - closed_at) / 1e9
        require(recovery_seconds <= 15, "Output-stall authenticated recovery")
        settle_end = time.monotonic() + 3
        while True:
            settled = client.transport("output-recovery-settled")
            if settled["active"] == 1 and settled["pending"] == 0:
                break
            require(time.monotonic() < settle_end, "Output recovery connection reclamation")
            time.sleep(.1)
        result["cases"].append({"id": "2.3c", "status": "PASS", "elapsed_seconds": elapsed,
            "close_reason": 4, "timeout_delta": 0, "load_bytes": len(raw),
            "application_reads_after_load": 0, "recovery_seconds": recovery_seconds,
            "recovered_state": "loaded", "final_state": "empty"})
        result["status"] = "CAPTURED_REQUIRES_AUDIT"
    except BaseException as error:
        result.update(status="STOPPED_REQUIRES_DIAGNOSIS",
            error=type(error).__name__ + ": " + str(error))
        journal.emit("failure", {"type": type(error).__name__, "error": str(error)})
    finally:
        if result["status"] != "CAPTURED_REQUIRES_AUDIT":
            try:
                result["cleanup"] = cleanup_loaded(root, packet, journal)
            except BaseException as error:
                result["cleanup_error"] = str(error)
                result["status"] = "STOPPED_FINAL_STATE_UNVERIFIED"
        try:
            final_a = inventory(root, packet, "final-a")
            inactive(final_a, BOOT)
            require(before_a is not None and configuration(final_a) == configuration(before_a) and
                    final_a["info"]["revision"] == SOURCE[:12], "A final source/configuration")
            result["final_a"] = final_a["wtp"]["STATUS"]
        except BaseException as error:
            result["final_a_error"] = str(error)
            result["status"] = "STOPPED_FINAL_STATE_UNVERIFIED"
        try:
            final_b = inventory(root, packet, "final-b", True)
            inactive(final_b, packet["b_boot_id"])
            require(before_b is not None and configuration(final_b) == configuration(before_b) and
                    final_b["info"]["revision"] == before_b["info"]["revision"],
                    "B final source/configuration")
            result["final_b"] = final_b["wtp"]["STATUS"]
        except BaseException as error:
            result["final_b_error"] = str(error)
            result["status"] = "STOPPED_FINAL_STATE_UNVERIFIED"
        result["elapsed_seconds"] = time.monotonic() - started
        save(root / "progress-result.json", result)
        journal.emit("finish", result)
        journal.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no sockets, devices or fixture changes.")
        return
    root = args.root.resolve(strict=True)
    require(os.geteuid() == 0 and digest(root / "packet.json") == args.packet_sha256,
            "Root and frozen packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            Path("/proc/sys/kernel/random/boot_id").read_text().strip() == packet["host_boot_id"] and
            os.readlink("/proc/self/ns/net") == os.readlink(packet["client_netns"]) and
            os.readlink("/proc/self/ns/mnt") == os.readlink(packet["client_mountns"]),
            "Host and isolated namespaces")
    require(time.monotonic_ns() + (packet["runtime_seconds"] + packet["restoration_seconds"]) * 10**9 <
            packet["fixture_deadline_monotonic_ns"], "Fixture restoration reserve")
    for name, sha in packet["stage_sha256"].items():
        require((root / name).resolve().is_relative_to(root) and digest(root / name) == sha,
                "Staged Package 3 input changed")
    for name, spec in packet["remote_copy_inputs"].items():
        require(digest(root / name) == spec["sha256"], "Private Package 3 input changed")
    result = run(root, packet)
    require(result["status"] == "CAPTURED_REQUIRES_AUDIT", result["status"])


if __name__ == "__main__":
    main()
