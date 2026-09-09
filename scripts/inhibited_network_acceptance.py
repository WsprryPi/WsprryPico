#!/usr/bin/env python3
"""Opt-in six-job direct Pico acceptance; never production-host or RF evidence."""

import argparse
import datetime
import hashlib
import http.client
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
import struct
import time
import uuid

from validate_wtp_contract import SchemaValidator, crc32c, frame, loads_strict

ROOT = Path(__file__).resolve().parents[1]
ENGINE = "inhibited-standalone-simulator"
DURATION = 6_000_000_000
FREQUENCY = 3_570_100_000_000_000
BUDGET = 500_000_000
LEAD = 10_000_000_000
CASES = ("complete", "abort_loaded", "abort_armed", "abort_running",
         "disconnect_after_arm", "clock_uncertain")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def job_value(job_id):
    return dict(job_id=job_id, profile="rf-events/1", mode="tone",
                total_duration_ns=str(DURATION), allow_frequency_adjustment=False,
                events=[dict(offset_ns="0", duration_ns=str(DURATION), rf_on=True,
                             frequency_nhz=str(FREQUENCY))])


def check_caps(caps):
    require(caps["engine"] == ENGINE, "inhibited engine required")
    require("tone" in caps["modes"] and "rf-events/1" in caps["profiles"], "profile/mode")
    require(caps["max_events"] >= 1 and int(caps["max_job_duration_ns"]) >= DURATION,
            "job exceeds CAPS")
    require(int(caps["minimum_arm_lead_ns"]) < LEAD <= int(caps["maximum_arm_ahead_ns"]),
            "lead outside CAPS")
    require(int(caps["maximum_arm_uncertainty_ns"]) >= BUDGET, "uncertainty CAPS")
    require(caps["minimum_lease_ms"] <= 60000 <= caps["maximum_lease_ms"], "lease CAPS")
    require(any(int(r["minimum_nhz"]) <= FREQUENCY <= int(r["maximum_nhz"])
                for r in caps["frequency_ranges"]), "frequency outside CAPS")


def check_status(status, boot, *, owner=None, job=None, states=None, unowned=False):
    require(status["boot_id"] == boot, "boot changed; no dependent mutation")
    require(status["output_active"] is False, "output not authoritatively inactive")
    if unowned:
        require(status["owner_id"] is None and status["job_id"] is None
                and status["state"] == "empty", "initial/final state is not empty and unowned")
    if owner is not None:
        require(status["owner_id"] == owner, "owner mismatch")
    if job is not None:
        require(status["job_id"] == job, "job mismatch")
    if states is not None:
        require(status["state"] in states, "unexpected job state: " + status["state"])


def check_clock(clock):
    require(clock["state"] == "synchronized" and clock["leap"] == "normal", "clock not usable")
    require(1 < int(clock["uncertainty_ns"]) <= BUDGET, "clock budget not usable")
    return int(clock["utc_now_ns"]) + LEAD


class Evidence:
    def __init__(self, directory):
        directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.file = (directory / "events.jsonl").open("x", encoding="utf-8")

    def record(self, kind, value):
        self.file.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                        monotonic_ns=str(time.monotonic_ns()), kind=kind,
                                        value=value), separators=(",", ":")) + "\n")
        self.file.flush()


def context(args, browser=False):
    ctx = ssl.create_default_context(cafile=str(args.ca))
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(str(args.browser_cert if browser else args.cert),
                        str(args.browser_key if browser else args.key))
    ctx.set_alpn_protocols(["http/1.1" if browser else "wtp/1"])
    return ctx


def connect(args, ctx, alpn, evidence):
    # Numeric destination bounds connect without an unbounded system resolver.
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    deadline = time.monotonic() + 10
    raw.settimeout(10)
    try:
        raw.connect((args.address, args.port))
        raw.settimeout(max(0.001, deadline - time.monotonic()))
        stream = ctx.wrap_socket(raw, server_hostname=args.hostname)
    except BaseException:
        raw.close()
        raise
    try:
        require(stream.selected_alpn_protocol() == alpn, "ALPN mismatch")
        fingerprint = hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()
        require(fingerprint == args.server_sha256, "server fingerprint mismatch")
        evidence.record("tls", dict(destination=args.address, identity=args.hostname,
                                     fingerprint=fingerprint, alpn=alpn, version=stream.version()))
        return stream
    except BaseException:
        stream.close()
        raise


class Peer:
    def __init__(self, args, evidence):
        self.args, self.evidence = args, evidence
        self.session = uuid.uuid4().hex
        self.stream = None
        self.schema = json.loads((ROOT / "docs/protocol/wtp-1.schema.json").read_text())
        self.validator = SchemaValidator(self.schema)

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None

    def open(self):
        self.close()
        self.stream = connect(self.args, context(self.args), "wtp/1", self.evidence)
        hello = self.request("HELLO", dict(versions=["WTP/1"],
                             client_name="inhibited-network-acceptance", client_version="1"))
        require(hello["device_id"] == self.args.device_id, "device mismatch")
        require(hello["boot_id"] == self.args.boot_id, "boot mismatch")
        check_caps(self.request("CAPS", {}))

    def exact(self, size, deadline):
        data = bytearray()
        while len(data) < size:
            remaining = deadline - time.monotonic()
            require(remaining > 0, "WTP transaction timed out; outcome unconfirmed")
            self.stream.settimeout(remaining)
            part = self.stream.recv(size - len(data))
            require(bool(part), "WTP connection closed; outcome unconfirmed")
            data.extend(part)
        return bytes(data)

    def request(self, op, body, expected_error=None):
        request = dict(type="request", protocol="WTP/1", session_id=self.session,
                       request_id=uuid.uuid4().hex, op=op, body=body)
        require(not self.validator.errors(request, self.schema), "invalid outgoing request")
        self.evidence.record("request", request)
        deadline = time.monotonic() + 8
        self.stream.settimeout(8)
        self.stream.sendall(frame(json.dumps(request, separators=(",", ":")).encode()))
        while True:
            header = self.exact(16, deadline)
            magic, version, encoding, flags, length, checksum = struct.unpack(">4sBBHII", header)
            require((magic, version, encoding, flags) == (b"WTPF", 1, 1, 0)
                    and 0 < length <= 65536, "invalid frame; no resynchronizing acceptance")
            payload = self.exact(length, deadline)
            require(crc32c(payload) == checksum, "CRC mismatch")
            message = loads_strict(payload.decode())
            require(not self.validator.errors(message, self.schema), "invalid response schema")
            require(message["session_id"] == self.session, "response session mismatch")
            self.evidence.record("received", message)
            if message["type"] == "event":
                require(message["boot_id"] == self.args.boot_id, "event boot mismatch")
                continue
            require((message["request_id"], message["op"]) == (request["request_id"], op),
                    "unexpected response identity; no blind mutation retry")
            if expected_error:
                require(message["ok"] is False and message["error"]["code"] == expected_error,
                        "wrong rejection layer/code")
                return message["error"]
            require(message["ok"] is True, "operation rejected: " +
                    str(message.get("error", {}).get("code")))
            return message["body"]


def browser(args, evidence, method="GET", body=None):
    deadline = time.monotonic() + 20
    stream = connect(args, context(args, True), "http/1.1", evidence)
    try:
        authority = args.hostname + ":" + str(args.port)
        path = "/api/v1/jobs" if body else "/api/v1/status"
        payload = json.dumps(body, separators=(",", ":")).encode() if body else b""
        headers = (f"{method} {path} HTTP/1.1\r\nHost: {authority}\r\n"
                   f"Origin: https://{authority}\r\nContent-Type: application/json\r\n"
                   "X-WsprryPico-Request: 1\r\nConnection: close\r\n"
                   f"Content-Length: {len(payload)}\r\n\r\n").encode()
        evidence.record("https_request", dict(method=method, path=path, body=body))
        stream.settimeout(max(0.001, deadline - time.monotonic()))
        stream.sendall(headers + payload)
        raw = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            require(remaining > 0, "HTTP total deadline exceeded")
            stream.settimeout(remaining)
            chunk = stream.recv(4096)
            if not chunk:
                break
            raw.extend(chunk)
            require(len(raw) <= 67584, "HTTP response exceeds acceptance bound")
        class BufferedResponse:
            def makefile(self, mode):
                return io.BytesIO(raw)
        response = http.client.HTTPResponse(BufferedResponse())
        response.begin()
        data = response.read(65537)
        require(len(data) <= 65536, "HTTP body exceeds acceptance bound")
        value = json.loads(data)
        evidence.record("https_response", dict(status=response.status, body=value))
        return response.status, value
    finally:
        stream.close()


def foreign_checks(args, evidence, job):
    session = uuid.uuid4().hex
    for operation, body in (("HELLO", dict(versions=["WTP/1"], client_name="foreign-browser", client_version="1")),
                            ("ABORT", {"job_id": job}), ("RELEASE", {})):
        status, result = browser(args, evidence, "POST", dict(session_id=session,
                                request_id=uuid.uuid4().hex, operation=operation, body=body))
        if operation == "HELLO":
            require(status == 200 and result["ok"] is True, "foreign HELLO failed")
            require(result["result"]["device_id"] == args.device_id
                    and result["result"]["boot_id"] == args.boot_id, "foreign identity mismatch")
        else:
            require(status == 409 and result["ok"] is False
                    and result["error"]["code"] == "NOT_OWNER", "foreign mutation was not rejected as NOT_OWNER")


def status_for(peer, owner=None, job=None, states=None, unowned=False):
    status = peer.request("STATUS", {})
    check_status(status, peer.args.boot_id, owner=owner, job=job, states=states, unowned=unowned)
    return status


def await_state(peer, owner, job, target, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = status_for(peer, owner, job)
        if status["state"] == target:
            return status
        require(status["state"] in ("armed", "running"), "job ended before required observation")
        time.sleep(0.15)
    raise TimeoutError("required state was not observed: " + target)


def run_case(peer, name):
    args, evidence = peer.args, peer.evidence
    status_for(peer, unowned=True)
    code, baseline = browser(args, evidence)
    require(code == 200, "browser baseline failed")
    check_status(baseline["job"], args.boot_id, unowned=True)
    require(baseline["standalone"]["enabled"] is False
            and baseline["standalone"]["engine"] == ENGINE
            and baseline["network"]["deployment_identity_matches"] is True, "unsafe standalone baseline")
    owner, job = uuid.uuid4().hex, uuid.uuid4().hex
    evidence.record("case_begin", dict(case=name, owner=owner, job=job))
    claimed = False
    try:
        # Set before sending: a lost CLAIM reply is an ambiguous claim.
        claimed = True
        claim = peer.request("CLAIM", dict(owner_id=owner, lease_ms=60000))
        require(claim["owner_id"] == owner, "CLAIM returned a different owner")
        peer.request("LOAD", job_value(job))
        status_for(peer, owner, job, ("loaded",))
        if name == "complete":
            code, observation = browser(args, evidence)
            require(code == 200, "concurrent status failed")
            check_status(observation["job"], args.boot_id, owner=owner, job=job, states=("loaded",))
            foreign_checks(args, evidence, job)
            status_for(peer, owner, job, ("loaded",))
        if name == "abort_loaded":
            peer.request("ABORT", dict(job_id=job))
        else:
            start = check_clock(peer.request("GET_CLOCK", {}))
            arm = dict(job_id=job, start_utc_ns=str(start),
                       max_start_uncertainty_ns=str(1 if name == "clock_uncertain" else BUDGET))
            peer.request("ARM", arm, "CLOCK_UNCERTAIN" if name == "clock_uncertain" else None)
            if name == "clock_uncertain":
                status_for(peer, owner, job, ("loaded",))
                peer.request("ABORT", dict(job_id=job))
            elif name == "abort_armed":
                status_for(peer, owner, job, ("armed",))
                peer.request("ABORT", dict(job_id=job))
            elif name == "disconnect_after_arm":
                status_for(peer, owner, job, ("armed",))
                peer.close()
                evidence.record("connection_closed", {"case": name, "output": "unknown"})
                time.sleep(18)
                peer.open()  # same principal/session, fresh HELLO/device/boot/CAPS
                status_for(peer, owner, job, ("complete",))
            else:
                status_for(peer, owner, job, ("armed",))
                await_state(peer, owner, job, "running", 14)
                if name == "abort_running":
                    peer.request("ABORT", dict(job_id=job))
                else:
                    await_state(peer, owner, job, "complete", 10)
        expected = "complete" if name in ("complete", "disconnect_after_arm") else "aborted"
        terminal = status_for(peer, owner, job, (expected,))
        require(any(r["job_id"] == job and r["state"] == expected
                    and r["output_active"] is False for r in terminal["terminal_records"]),
                "matching terminal record missing")
        peer.request("RELEASE", {})
        status_for(peer, unowned=True)
        claimed = False
        evidence.record("case_pass", {"case": name})
    except BaseException:
        evidence.record("case_failed", {"case": name, "output": "unknown until reconciliation"})
        if claimed:
            # Only same-session recovery of the exact owner/job is allowed.
            try:
                peer.open()
                state = status_for(peer)
                if state["owner_id"] == owner:
                    require(state["job_id"] in (None, job), "cleanup job mismatch")
                    if state["job_id"] == job and state["state"] in ("loaded", "armed", "running"):
                        peer.request("ABORT", dict(job_id=job))
                        status_for(peer, owner, job, ("aborted",))
                    state = status_for(peer, owner)
                    require(state["state"] in ("empty", "loaded", "complete", "aborted", "missed"),
                            "cleanup blocked by unresolved state")
                    peer.request("RELEASE", {})
                status_for(peer, unowned=True)
                evidence.record("cleanup_confirmed", {"case": name})
            except BaseException as error:
                evidence.record("cleanup_unconfirmed", {"case": name, "error_type": type(error).__name__})
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="requires separate exact-batch physical approval")
    parser.add_argument("--address", help="explicit observed IPv4; this is not an mDNS test")
    parser.add_argument("--hostname")
    parser.add_argument("--port", type=int, default=18443)
    parser.add_argument("--device-id")
    parser.add_argument("--boot-id")
    parser.add_argument("--server-sha256")
    for name in ("ca", "cert", "key", "browser-cert", "browser-key", "evidence"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if not args.run:
        print(json.dumps(dict(execution=False, cases=CASES, maximum_jobs=6,
                              duration_ns=str(DURATION), frequency_nhz=str(FREQUENCY),
                              lead_ns=str(LEAD), uncertainty_ns=str(BUDGET)), indent=2))
        return
    for name in ("address", "hostname", "device_id", "boot_id", "server_sha256",
                 "ca", "cert", "key", "browser_cert", "browser_key", "evidence"):
        if not getattr(args, name):
            parser.error("--run requires explicit " + name.replace("_", "-"))
    ipaddress.IPv4Address(args.address)
    require(1 <= args.port <= 65535, "port")
    require(re.fullmatch(r"[a-z0-9][a-z0-9.-]*\.local", args.hostname), "explicit local DNS identity required")
    require(all(re.fullmatch(r"[0-9a-f]{32}", v) for v in (args.device_id, args.boot_id)), "full IDs required")
    require(re.fullmatch(r"[0-9a-f]{64}", args.server_sha256), "server SHA-256 required")
    controller_leaf = ssl.PEM_cert_to_DER_cert(args.cert.read_text())
    browser_leaf = ssl.PEM_cert_to_DER_cert(args.browser_cert.read_text())
    require(controller_leaf != browser_leaf, "independent browser principal required")
    os.umask(0o077)
    evidence = Evidence(args.evidence)
    evidence.record("run", {"arguments": {k: str(v) for k, v in vars(args).items()},
                            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    peer = Peer(args, evidence)
    try:
        peer.open()
        for case in CASES:
            run_case(peer, case)
        evidence.record("batch_pass", {"cases": list(CASES), "evidence_class": "direct inhibited target"})
        print("All six direct inhibited cases passed; production-host and Chrome mutation cases remain separate.")
    except BaseException as error:
        evidence.record("batch_failed", {"error_type": type(error).__name__,
                                          "message": str(error)})
        raise
    finally:
        peer.close()
        evidence.file.close()


if __name__ == "__main__":
    main()
