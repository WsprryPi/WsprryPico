#!/usr/bin/env python3
"""Opt-in Package 4 USB pressure during network-owned finite RF."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import ssl
import subprocess
import termios
import threading
import time

from phase11_5_device_management import digest, save
from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_pilot import Decoder, DEVICE, Peer, SERIAL
from phase11_5_pilot_supervisor import B_DEVICE, B_SERIAL, configuration, finished, idle
from phase11_5_r3_capacity_plan import wtp_capacity_frame
from phase11_5_r3_v2_rf import validate_info
from validate_wtp_contract import frame


SCHEMA = "phase11.5-package4-usb-v1"
SOURCE = "ca3c5dce40360b7eea2f9c45618232caa68cdbb6"
IMAGE = "6c7aa0b7df6756e8f248570d682c6af4bbcfc44a5ad67e94d6761709ced0bd59"
BOOT = "5e0d6bc3e383b8c1cb4b0db9ed636bf5"
B_BOOT = "6684b4b197d80cfa0ce83b3aaf205cb0"
NAME = "wsprrypico-0a60df.local"
PEER_SHA = "06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016"
CASES = ["usb-parser-pressure", "usb-unread-output"]
OPS = {"HELLO", "STATUS", "GET_CLOCK", "PING", "CLAIM", "RENEW", "LOAD", "ARM",
       "ABORT", "RELEASE"}


def identity(value):
    require(isinstance(value, str) and len(value) == 32 and value != "0" * 32 and
            all(c in "0123456789abcdef" for c in value), "Package 4 identity")
    return value


def validate(packet):
    require(packet["schema"] == packet["scope"] == SCHEMA and
            packet["standing_authority"] == "R3-COMPLETE-20260913-v2" and
            packet["source_revision"] == SOURCE and packet["image_sha256"] == IMAGE and
            packet["boot_id"] == BOOT and packet["b_boot_id"] == B_BOOT and
            packet["serial"] == SERIAL and packet["device_id"] == DEVICE and
            packet["b_serial"] == B_SERIAL and packet["b_device_id"] == B_DEVICE and
            packet["cases"] == CASES, "Exact Package 4 target/scope")
    require(packet["runtime_seconds"] == 360 and packet["restoration_seconds"] == 150 and
            packet["rf_jobs"] == 2 and packet["rf_duration_ns"] == 200_000_000_000 and
            packet["absolute_rf_jobs"] == 4 and
            packet["absolute_rf_duration_ns"] == 400_000_000_000 and
            packet["flashes"] == packet["wifi_cycles"] == packet["configuration_writes"] ==
            packet["controlled_reboots"] == 0 and packet["maximum_renewals"] == 8,
            "Finite Package 4 budget")
    require(packet["client_netns"] == f"/proc/{packet['client_pid']}/ns/net" and
            packet["client_mountns"] == f"/proc/{packet['client_pid']}/ns/mnt" and
            packet["address"] == "10.77.15.10" and packet["port"] == 18443 and
            packet["shared_rf_reservation"] == "durable-both-picos-v1",
            "Frozen isolated client/fixture")
    ids = ["inventory_session", "b_session", "network_session", "owner_id",
           "parser_session", "parser_request", "parser_recovery", "unread_session",
           "unread_probe", "unread_recovery_session"]
    require(len({identity(packet[k]) for k in ids}) == len(ids), "Distinct Package 4 identities")
    require(packet["usb"] == {"maximum_payload_bytes": 65536, "maximum_wire_bytes": 65552,
            "parser_write_bytes": 512, "parser_write_pause_ms": 15,
            "unread_max_requests": 1024, "unread_write_seconds": 3,
            "unread_hold_seconds": 12, "unread_capture_bytes": 1048576,
            "silence_seconds": 2}, "Exact Package 4 USB pressure")
    require(len(packet["jobs"]) == 2 and
            [j["case"] for j in packet["jobs"]] == CASES and
            len({identity(j["job_id"]) for j in packet["jobs"]}) == 2,
            "Two distinct Package 4 jobs")
    for job in packet["jobs"]:
        require(job["profile"] == "rf-events/1" and job["mode"] == "tone" and
                job["total_duration_ns"] == "100000000000" and
                job["allow_frequency_adjustment"] is True and job["events"] == [{
                    "offset_ns": "0", "duration_ns": "100000000000", "rf_on": True,
                    "frequency_nhz": "135500000000000"}], "Exact 100-second Tone")
    require(packet["credentials"] == {"controller": {
        "ca": "credentials/controller/client-ca.crt",
        "cert": "credentials/controller/client.crt",
        "key": "credentials/controller/client.key"}}, "Frozen controller credentials")
    if "fixture_recovery" in packet:
        require(packet["fixture_recovery"] == {
            "prior_packet_sha256": "d09c9a35ce35b00a57004a69290cc6ad39a439e2dcd6c31014da3e88c63f21d8",
            "prior_rf_jobs": 0, "host_ap_station_evictions": 1,
            "target_configuration_writes": 0, "target_controlled_reboots": 0},
            "Exact pre-RF fixture association recovery")
    if "execution_history" in packet:
        require(packet["execution_history"] == {
            "preflight_packet_sha256": "d09c9a35ce35b00a57004a69290cc6ad39a439e2dcd6c31014da3e88c63f21d8",
            "preflight_rf_jobs": 0,
            "observer_defect_packet_sha256": "8896f2cbf44dff298864600bbcd8656314fc61638f2df71eceaa4221f208b983",
            "observer_defect_rf_jobs": 1,
            "observer_defect_rf_duration_ns": 100000000000,
            "observer_reconciliation_packet_sha256": "9f110f5e99f1391102a39afd6741a863377ff949ffa0f59ff4fd75bf9b4d38a9",
            "gate_defect_packet_sha256": "5c999fd00d27f041a79d0991ca1d58e8555b4dc3df5b72911b264958fcd207e4",
            "gate_defect_rf_jobs": 1,
            "gate_defect_rf_duration_ns": 100000000000,
            "gate_reconciliation_packet_sha256": "fbd68f1f4215bbc1d5c136ae1e02809e7bd6013ea2966fef898a4806ee657829",
            "cumulative_prior_rf_jobs": 2,
            "cumulative_prior_rf_duration_ns": 200000000000},
            "Exact retained Package 4 attempt history")
        require(packet["execution_history"]["cumulative_prior_rf_jobs"] + packet["rf_jobs"] ==
                packet["absolute_rf_jobs"] and
                packet["execution_history"]["cumulative_prior_rf_duration_ns"] +
                packet["rf_duration_ns"] == packet["absolute_rf_duration_ns"],
                "Package 4 absolute hardware budget")
    return packet


class Journal:
    def __init__(self, path):
        self.stream = path.open("x")
        self.lock = threading.Lock()
        self.sequence = 0

    def emit(self, kind, value):
        with self.lock:
            row = {"sequence": self.sequence, "kind": kind, "value": value,
                   "monotonic_ns": time.monotonic_ns(), "utc_ns": time.time_ns()}
            self.stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.sequence += 1
            return row["monotonic_ns"]

    def close(self):
        self.stream.close()


class NetworkPeer:
    def __init__(self, root, packet, journal):
        credentials = packet["credentials"]["controller"]
        self.context = ssl.create_default_context(cafile=str(root / credentials["ca"]))
        self.context.minimum_version = self.context.maximum_version = ssl.TLSVersion.TLSv1_3
        self.context.load_cert_chain(root / credentials["cert"], root / credentials["key"])
        self.context.set_alpn_protocols(["wtp/1"])
        self.packet, self.journal = packet, journal
        self.session = packet["network_session"]
        self.decoder = Decoder()
        self.number = 0

    def __enter__(self):
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            raw.settimeout(5)
            raw.connect((self.packet["address"], self.packet["port"]))
            self.stream = self.context.wrap_socket(raw, server_hostname=NAME)
        except BaseException:
            raw.close()
            raise
        require(self.stream.version() == "TLSv1.3" and
                self.stream.selected_alpn_protocol() == "wtp/1" and
                hashlib.sha256(self.stream.getpeercert(binary_form=True)).hexdigest() == PEER_SHA,
                "Authenticated Package 4 network authority")
        self.stream.settimeout(.25)
        self.journal.emit("network_tls", {"version": "TLSv1.3", "alpn": "wtp/1",
            "peer_sha256": PEER_SHA, "local": list(self.stream.getsockname()),
            "peer": list(self.stream.getpeername())})
        return self

    def __exit__(self, kind, value, traceback):
        self.stream.close()

    def ask(self, label, op, body=None, seconds=5):
        require(op in OPS, "Package 4 WTP operation")
        self.number += 1
        request = {"type": "request", "protocol": "WTP/1", "session_id": self.session,
                   "request_id": f"{self.number:032x}", "op": op, "body": body or {}}
        raw = frame(json.dumps(request, separators=(",", ":")).encode())
        self.journal.emit("network_tx", {"label": label, "request": request, "hex": raw.hex()})
        self.stream.sendall(raw)
        end, answer = time.monotonic() + seconds, None
        while time.monotonic() < end:
            try:
                part = self.stream.recv(4096)
            except (socket.timeout, ssl.SSLWantReadError):
                continue
            require(part, "Network WTP EOF")
            self.journal.emit("network_rx", {"label": label, "hex": part.hex()})
            for message in self.decoder.feed(part):
                self.journal.emit("network_message", {"label": label, "message": message})
                require(message["session_id"] == self.session, "Foreign network WTP session")
                if message["type"] == "event":
                    require(message["boot_id"] == BOOT and message["event"] not in
                            ("DEVICE_FAULT", "MISSED_START", "SESSION_REPLACED"),
                            "Network authority fault event")
                else:
                    require(answer is None and message["request_id"] == request["request_id"] and
                            message["op"] == op and message["ok"] is True,
                            "Network authority operation rejected")
                    answer = message["body"]
            if answer is not None:
                return answer
        raise TimeoutError("Network WTP deadline: " + label)


def inventory(root, packet, label, b=False):
    with (root / (label + ".stdout")).open("xb") as out, \
         (root / (label + ".stderr")).open("xb") as err:
        result = subprocess.run(["python3", str(root / "scripts/phase11_5_inventory.py"),
            "--serial", B_SERIAL if b else SERIAL, "--device-id", B_DEVICE if b else DEVICE,
            "--session-id", packet["b_session"] if b else packet["inventory_session"], "--run"],
            stdout=out, stderr=err, timeout=65)
    require(result.returncode == 0, "Package 4 inventory: " + label)
    value = finished(root / (label + ".stdout"), "READ_ONLY_INVENTORY")
    idle(value)
    require(value["wtp"]["STATUS"]["boot_id"] == (B_BOOT if b else BOOT),
            "Package 4 inventory boot")
    return value


def usb_peer(fd, packet, journal, session, label):
    def emit(kind, value):
        journal.emit("usb_" + kind, {"case": label, "value": value})
    peer = Peer(fd, emit, lambda: None, BOOT)
    peer.session = session
    hello = peer.request("HELLO", {"versions": ["WTP/1"], "client_name": "Package 4 USB",
                                   "client_version": "1"})
    require(hello["device_id"] == DEVICE and hello["boot_id"] == BOOT,
            "Package 4 USB HELLO identity")
    return peer


def parser_pressure(packet, journal):
    path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02")
    cfg = packet["usb"]
    with exclusive_port(path) as fd:
        peer = usb_peer(fd, packet, journal, packet["parser_session"], CASES[0])
        raw = wtp_capacity_frame(peer.session, packet["parser_request"])
        require(len(raw) == cfg["maximum_wire_bytes"], "Maximum USB parser wire size")
        began = journal.emit("usb_parser_start", {"wire_bytes": len(raw),
            "payload_bytes": len(raw) - 16, "sha256": hashlib.sha256(raw).hexdigest()})
        offset = 0
        while offset < len(raw):
            ready = select.select([], [fd], [], 1)[1]
            require(ready, "Maximum USB parser write readiness")
            try:
                count = os.write(fd, raw[offset:offset + cfg["parser_write_bytes"]])
            except BlockingIOError:
                continue
            require(count > 0, "Maximum USB parser write progress")
            offset += count
            if offset == len(raw) or offset % 4096 < count:
                journal.emit("usb_parser_write", {"bytes": count, "total_written": offset})
            if offset < len(raw):
                time.sleep(cfg["parser_write_pause_ms"] / 1000)
        response = None
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and response is None:
            if not select.select([fd], [], [], .1)[0]:
                continue
            try:
                data = os.read(fd, 4096)
            except BlockingIOError:
                continue
            require(data, "Maximum USB parser response EOF")
            journal.emit("usb_parser_rx", {"hex": data.hex()})
            for message in peer.decoder.feed(data):
                journal.emit("usb_parser_message", message)
                require(not peer.validator.errors(message, peer.schema) and
                        message["session_id"] == peer.session, "Maximum parser response schema")
                if message["type"] == "event":
                    require(message["boot_id"] == BOOT, "Maximum parser event boot")
                else:
                    require(response is None and message["request_id"] == packet["parser_request"] and
                            message["op"] == "STATUS" and message["ok"] is True,
                            "Maximum parser STATUS response")
                    response = message["body"]
        require(response is not None and response["boot_id"] == BOOT and
                response["state"] == "running" and response["output_active"] is True and
                response["owner_id"] == packet["owner_id"], "Maximum parser RF authority")
        pong = peer.request("PING", {"token": packet["parser_recovery"]})
        require(pong == {"token": packet["parser_recovery"]}, "Parser same-connection recovery")
        ended = journal.emit("usb_parser_end", {"written_bytes": offset, "status": response,
            "same_connection_recovery": True})
    time.sleep(.25)
    with exclusive_port(path) as fd:
        peer = usb_peer(fd, packet, journal, packet["parser_recovery"], "parser-dtr-recovery")
        status = peer.request("STATUS")
        require(status["boot_id"] == BOOT and status["state"] == "running" and
                status["output_active"] is True and status["owner_id"] == packet["owner_id"],
                "Parser DTR recovery authority")
        recovered = journal.emit("usb_parser_recovery", {"status": status})
    return {"id": "2.3d", "status": "CAPTURED_REQUIRES_AUDIT", "wire_bytes": offset,
            "began_monotonic_ns": began, "ended_monotonic_ns": ended,
            "recovered_monotonic_ns": recovered}


def flush_unsent_usb_output(fd, journal):
    """Discard host-to-device backlog without closing the DTR-held endpoint."""
    termios.tcflush(fd, termios.TCOFLUSH)
    journal.emit("usb_unread_host_output_flushed", {"dtr_remained_asserted": True})


def unread_pressure(packet, journal):
    path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02")
    cfg = packet["usb"]
    with exclusive_port(path) as fd:
        peer = usb_peer(fd, packet, journal, packet["unread_session"], CASES[1])
        requests, raw = [], bytearray()
        for index in range(cfg["unread_max_requests"]):
            request = {"type": "request", "protocol": "WTP/1",
                "session_id": peer.session,
                "request_id": hashlib.sha256(f"{peer.session}:{index}".encode()).hexdigest()[:32],
                "op": "STATUS", "body": {}}
            wire = frame(json.dumps(request, separators=(",", ":")).encode())
            requests.append((len(raw) + len(wire), request))
            raw.extend(wire)
        began = journal.emit("usb_unread_start", {"maximum_requests": len(requests),
            "maximum_wire_bytes": len(raw), "application_reads": 0,
            "sha256": hashlib.sha256(raw).hexdigest()})
        deadline, written = time.monotonic() + cfg["unread_write_seconds"], 0
        while written < len(raw) and time.monotonic() < deadline:
            if not select.select([], [fd], [], .05)[1]:
                continue
            try:
                count = os.write(fd, raw[written:written + 16384])
            except BlockingIOError:
                continue
            require(count > 0, "Unread USB offered write progress")
            written += count
        complete = sum(end <= written for end, _ in requests)
        require(complete >= 16, "Unread USB accepted too few complete requests")
        journal.emit("usb_unread_offered", {"written_bytes": written,
            "complete_requests": complete, "application_reads": 0})
        time.sleep(cfg["unread_hold_seconds"])
        held = journal.emit("usb_unread_hold_complete", {"hold_seconds": cfg["unread_hold_seconds"],
            "application_reads": 0})
        captured = bytearray()
        quiet = time.monotonic() + .5
        capture_end = time.monotonic() + 3
        while time.monotonic() < capture_end and time.monotonic() < quiet:
            if not select.select([fd], [], [], min(.1, quiet - time.monotonic()))[0]:
                continue
            try:
                part = os.read(fd, 65536)
            except BlockingIOError:
                continue
            require(part, "Unread USB EOF")
            captured.extend(part)
            require(len(captured) <= cfg["unread_capture_bytes"], "Unread USB capture bound")
            quiet = time.monotonic() + .5
        messages = peer.decoder.feed(captured)
        trailing_bytes = len(peer.decoder.buffer)
        require(trailing_bytes < 65552, "Unread USB trailing response bound")
        responses = []
        expected = {request["request_id"] for _, request in requests[:complete]}
        for message in messages:
            require(not peer.validator.errors(message, peer.schema) and
                    message["session_id"] == peer.session, "Unread USB response schema")
            if message["type"] == "event":
                require(message["boot_id"] == BOOT, "Unread USB event boot")
            else:
                require(message["request_id"] in expected and message["op"] == "STATUS" and
                        message["ok"] is True, "Unread USB response identity")
                responses.append(message["request_id"])
        require(len(responses) == len(set(responses)) < complete,
                "Unread USB did not establish a response deficit")
        journal.emit("usb_unread_drained", {"captured_hex": captured.hex(),
            "captured_bytes": len(captured), "response_ids": responses,
            "response_count": len(responses), "complete_requests": complete,
            "trailing_response_bytes": trailing_bytes})
        # The no-read interval can also fill the host's outbound tty queue with
        # requests that the now-closed endpoint will never consume. Discard
        # only that host-side unsent backlog while DTR remains asserted, then
        # offer the proof PING to the unchanged target transport session.
        flush_unsent_usb_output(fd, journal)
        probe = {"type": "request", "protocol": "WTP/1", "session_id": peer.session,
                 "request_id": packet["unread_probe"], "op": "PING", "body": {"token": "after-unread"}}
        probe_raw = frame(json.dumps(probe, separators=(",", ":")).encode())
        sent = 0
        end = time.monotonic() + 1
        while sent < len(probe_raw) and time.monotonic() < end:
            if select.select([], [fd], [], .05)[1]:
                try:
                    sent += os.write(fd, probe_raw[sent:])
                except BlockingIOError:
                    pass
        require(sent == len(probe_raw), "Unread USB silence probe write")
        silence = bytearray()
        end = time.monotonic() + cfg["silence_seconds"]
        while time.monotonic() < end:
            if not select.select([fd], [], [], min(.1, end - time.monotonic()))[0]:
                continue
            try:
                silence.extend(os.read(fd, 4096))
            except BlockingIOError:
                pass
        require(not silence, "Unread USB endpoint responded before DTR recovery")
        silent = journal.emit("usb_unread_silent", {"probe_hex": probe_raw.hex(),
            "silence_seconds": cfg["silence_seconds"], "received_bytes": 0})
    time.sleep(.25)
    with exclusive_port(path) as fd:
        require(not select.select([fd], [], [], .3)[0], "Stale USB output after DTR recovery")
        peer = usb_peer(fd, packet, journal, packet["unread_recovery_session"],
                        "unread-dtr-recovery")
        status = peer.request("STATUS")
        require(status["boot_id"] == BOOT and status["state"] == "running" and
                status["output_active"] is True and status["owner_id"] == packet["owner_id"],
                "Unread DTR recovery authority")
        recovered = journal.emit("usb_unread_recovery", {"status": status})
    return {"id": "2.3e", "status": "CAPTURED_REQUIRES_AUDIT",
            "written_bytes": written, "complete_requests": complete,
            "response_count": len(responses), "captured_bytes": len(captured),
            "trailing_response_bytes": trailing_bytes,
            "began_monotonic_ns": began, "held_monotonic_ns": held,
            "silent_monotonic_ns": silent, "recovered_monotonic_ns": recovered}


def run(root, packet):
    os.umask(0o077)
    started = time.monotonic()
    journal = Journal(root / "package4.jsonl")
    stop = threading.Event()
    console_ready = threading.Event()
    case_ready = [threading.Event(), threading.Event()]
    case_done = [threading.Event(), threading.Event()]
    latest_lock = threading.Lock()
    latest = {"info": None}
    faults = []
    result = {"status": "RUNNING", "cases": [], "armed_jobs": [], "completed_jobs": [],
              "rf_jobs_charged": 0, "rf_duration_ns_charged": 0, "renewals": 0}
    save(root / "package4-result.json", result)
    before = before_b = None
    reservation = None
    final_values = {}

    def fail(worker, error):
        faults.append(worker + ": " + type(error).__name__ + ": " + str(error))
        journal.emit("failure", {"worker": worker, "type": type(error).__name__,
                                  "error": str(error)})
        stop.set()
        for event in case_ready + case_done:
            event.set()

    def console_worker():
        try:
            path = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")
            with exclusive_port(path) as fd:
                while not stop.is_set():
                    began = time.monotonic_ns()
                    value = exchange(fd, b"INFO\n", time.monotonic() + 5,
                        lambda kind, body: journal.emit("console_" + kind, {"value": body}), False)
                    validate_info(value, before, packet)
                    with latest_lock:
                        latest["info"] = (time.monotonic_ns(), value)
                    journal.emit("info", {"began_monotonic_ns": began, "value": value})
                    console_ready.set()
                    stop.wait(.25)
        except BaseException as error:
            fail("console", error)

    def running_info():
        with latest_lock:
            sample = latest["info"]
        require(sample is not None and 0 <= time.monotonic_ns() - sample[0] <= 2_000_000_000,
                "Fresh Console INFO required")
        info = sample[1]
        status = info["status"]
        require(status["boot_id"] == BOOT and status["state"] == "running" and
                status["output_active"] is True, "Console Running authority")
        return info

    def network_worker():
        try:
            require(console_ready.wait(10), "Initial Console observer")
            with NetworkPeer(root, packet, journal) as peer:
                hello = peer.ask("hello", "HELLO", {"versions": ["WTP/1"],
                    "client_name": "Package 4 network authority", "client_version": "1"})
                require(hello["device_id"] == DEVICE and hello["boot_id"] == BOOT,
                        "Network HELLO identity")
                for index, job in enumerate(packet["jobs"]):
                    status = peer.ask(f"{index}-initial", "STATUS")
                    require(status["state"] == "empty" and status["owner_id"] is None and
                            status["job_id"] is None and status["output_active"] is False,
                            "Network initial Empty authority")
                    lease = peer.ask(f"{index}-claim", "CLAIM",
                        {"owner_id": packet["owner_id"], "lease_ms": 60000})
                    require(lease["owner_id"] == packet["owner_id"], "Network CLAIM")
                    payload = {key: value for key, value in job.items() if key != "case"}
                    loaded = peer.ask(f"{index}-load", "LOAD", payload)
                    require(loaded["job_id"] == job["job_id"], "Network LOAD")
                    clock = peer.ask(f"{index}-clock", "GET_CLOCK")
                    require(clock["state"] == "synchronized" and clock["leap"] == "normal" and
                            int(clock["uncertainty_ns"]) <= 500_000_000,
                            "Network synchronized ARM clock")
                    target = ((int(clock["utc_now_ns"]) + 10_000_000_000 + 999) // 1000) * 1000
                    result["armed_jobs"].append(job["job_id"])
                    result["rf_jobs_charged"] += 1
                    result["rf_duration_ns_charged"] += int(job["total_duration_ns"])
                    save(root / "package4-result.json", result)
                    arm = peer.ask(f"{index}-arm", "ARM", {"job_id": job["job_id"],
                        "start_utc_ns": str(target), "max_start_uncertainty_ns": "500000000"})
                    require(arm["start_utc_ns"] == str(target), "Network ARM changed start")
                    journal.emit("job_armed", {"index": index, "job": job,
                                               "start_utc_ns": str(target), "arm": arm})
                    last_renew = time.monotonic()
                    while not stop.is_set():
                        status = peer.ask(f"{index}-status", "STATUS")
                        journal.emit("network_status", {"index": index, "case": job["case"],
                                                        "value": status})
                        require(status["boot_id"] == BOOT and status["job_id"] == job["job_id"] and
                                status["owner_id"] == packet["owner_id"] and status["state"] in
                                ("armed", "running", "complete"), "Network finite RF authority")
                        if status["state"] == "running":
                            require(status["output_active"] is True, "Network Running output")
                            running_info()
                            case_ready[index].set()
                        else:
                            require(status["output_active"] is False, "Network inactive state")
                        if status["state"] == "complete":
                            require(case_done[index].is_set() and not faults,
                                    "RF completed before accepted pressure/recovery")
                            result["completed_jobs"].append(job["job_id"])
                            peer.ask(f"{index}-release", "RELEASE")
                            released = peer.ask(f"{index}-released-status", "STATUS")
                            require(released["owner_id"] is None and released["job_id"] is None and
                                    released["state"] == "empty" and
                                    released["output_active"] is False, "Network RELEASE")
                            journal.emit("job_complete", {"index": index, "job_id": job["job_id"],
                                                          "status": status})
                            save(root / "package4-result.json", result)
                            break
                        if time.monotonic() - last_renew >= 30:
                            require(result["renewals"] < packet["maximum_renewals"],
                                    "Package 4 renewal bound")
                            lease = peer.ask(f"{index}-renew", "RENEW",
                                {"owner_id": packet["owner_id"], "lease_ms": 60000})
                            require(lease["owner_id"] == packet["owner_id"], "Network RENEW")
                            result["renewals"] += 1
                            last_renew = time.monotonic()
                        time.sleep(.35)
                    if stop.is_set():
                        return
        except BaseException as error:
            fail("network", error)

    try:
        before_b = inventory(root, packet, "before-b", True)
        before = inventory(root, packet, "before-a")
        validate_info(before["info"], before, packet)
        require(before["wtp"]["CAPS"]["max_payload_bytes"] == 65536,
                "Package 4 maximum payload")
        from phase11_5_rf_reservation import Reservation
        reservation = Reservation(digest(root / "packet.json"))
        reservation.acquire({"a": before, "b": before_b})
        save(root / "rf-reservation-acquired.json", json.loads(reservation.path.read_text()))
        journal.emit("start", {"packet_sha256": digest(root / "packet.json"),
            "before_a_sha256": digest(root / "before-a.stdout"),
            "before_b_sha256": digest(root / "before-b.stdout")})
        console_thread = threading.Thread(target=console_worker, name="package4-console")
        network_thread = threading.Thread(target=network_worker, name="package4-network")
        console_thread.start()
        network_thread.start()
        for index, action in enumerate((parser_pressure, unread_pressure)):
            gate_seconds = 45 if index == 0 else 45 + int(packet["jobs"][index - 1]["total_duration_ns"]) / 1e9
            require(case_ready[index].wait(gate_seconds) and not faults,
                    "Package 4 Running case gate")
            outcome = action(packet, journal)
            result["cases"].append(outcome)
            save(root / "package4-result.json", result)
            case_done[index].set()
        network_thread.join(260)
        require(not network_thread.is_alive() and not faults and
                result["completed_jobs"] == [j["job_id"] for j in packet["jobs"]],
                "Package 4 network/RF completion")
        result["status"] = "CAPTURED_REQUIRES_AUDIT"
    except BaseException as error:
        fail("supervisor", error)
        result["status"] = "STOPPED_REQUIRES_DIAGNOSIS"
    finally:
        stop.set()
        for name in ("network_thread", "console_thread"):
            thread = locals().get(name)
            if thread is not None:
                thread.join(10)
        for label, b in (("final-a", False), ("final-b", True)):
            try:
                value = inventory(root, packet, label, b)
                final_values["b" if b else "a"] = value
                if b:
                    require(before_b is not None and configuration(value) == configuration(before_b) and
                            value["info"]["revision"] == before_b["info"]["revision"],
                            "Package 4 B unchanged")
                else:
                    require(before is not None and configuration(value) == configuration(before),
                            "Package 4 A configuration unchanged")
                    validate_info(value["info"], before, packet)
                result[label] = value["wtp"]["STATUS"]
            except BaseException as error:
                result[label + "-error"] = type(error).__name__ + ": " + str(error)
                result["status"] = "STOPPED_FINAL_STATE_UNVERIFIED"
        if reservation is not None:
            try:
                if reservation.held and set(final_values) == {"a", "b"}:
                    reservation.release(final_values)
                    save(root / "rf-reservation-released.json",
                         json.loads(reservation.path.read_text()))
            except BaseException as error:
                faults.append("reservation: " + str(error))
                result["status"] = "STOPPED_FINAL_STATE_UNVERIFIED"
            finally:
                reservation.close()
        result["faults"] = faults
        result["elapsed_seconds"] = time.monotonic() - started
        journal.emit("finishing", {"elapsed_seconds": result["elapsed_seconds"]})
        save(root / "package4-result.json", result)
        journal.emit("finish", result)
        journal.close()
    require(result["status"] == "CAPTURED_REQUIRES_AUDIT", result["status"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no sockets, USB endpoints, jobs or fixture changes.")
        return
    require(os.geteuid() == 0, "Package 4 runs as root on wspr5")
    root = args.root.resolve(strict=True)
    require(digest(root / "packet.json") == args.packet_sha256, "Frozen Package 4 packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            Path("/proc/sys/kernel/random/boot_id").read_text().strip() == packet["host_boot_id"] and
            os.readlink("/proc/self/ns/net") == os.readlink(packet["client_netns"]) and
            os.readlink("/proc/self/ns/mnt") == os.readlink(packet["client_mountns"]),
            "Package 4 host/namespaces")
    require(time.monotonic_ns() + (packet["runtime_seconds"] + packet["restoration_seconds"]) *
            1_000_000_000 < packet["fixture_deadline_monotonic_ns"],
            "Package 4 fixture restoration reserve")
    for name, sha in packet["stage_sha256"].items():
        require((root / name).resolve().is_relative_to(root) and digest(root / name) == sha,
                "Package 4 staged input changed")
    for name, spec in packet["remote_copy_inputs"].items():
        require(digest(root / name) == spec["sha256"], "Package 4 private input changed")
    run(root, packet)


if __name__ == "__main__":
    main()
