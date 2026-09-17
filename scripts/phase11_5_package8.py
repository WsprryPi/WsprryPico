#!/usr/bin/env python3
"""Execute the two bounded Phase 11.5 Package 8 R5 runs on wspr5."""

import argparse
import contextlib
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import time

from phase11_5_device_management import digest, save
from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_load_reply_target import finished, inventory
from phase11_5_network_fixture import Fixture
from phase11_5_pilot import Decoder
from phase11_5_rf_reservation import Reservation
from rf_wtp import WtpPeer
from validate_wtp_contract import frame


SOURCE = "7c5296471250cc06416c79a73c9627aed0eb3624"
IMAGE = "c73e0714572cb0edd7f3ba4c6c0c9e3b3a8ac500aca7a7edea23fc4b32cb9e87"
SERIAL = "0BF4B4AEC9FFB344"
DEVICE = "fd6127d11d6aca42a9905fa3fb1bf1d5"
B_BOOT = "6684b4b197d80cfa0ce83b3aaf205cb0"
DEPLOYED_BOOT = "61130461c14d4fb9297684539d4ebd45"
HOST_BOOT = "220e53ca-ca95-4206-9581-dbe28aa1eeb8"
HOSTNAME = "wsprrypico-0a60df.local"
PEER_SHA = "06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016"
OLD_ADDRESS, NEW_ADDRESS = "10.77.15.10", "10.77.15.20"
LOCAL_OWNER = "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
BASE_NHZ = "135500000000000"
BASE = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}")


class Journal:
    def __init__(self, path):
        self.stream = path.open("x")
        self.sequence = 0

    def emit(self, kind, value):
        row = dict(sequence=self.sequence, monotonic_ns=time.monotonic_ns(),
                   utc_ns=time.time_ns(), kind=kind, value=value)
        self.stream.write(json.dumps(row, separators=(",", ":")) + "\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.sequence += 1
        return row

    def close(self):
        self.stream.close()


def validate(packet):
    require(packet["schema"] == "phase11.5-package8-fixture-v1" and
            packet["family"] == "R5" and
            packet["standing_authority"] == "PHASE11.5-COMPLETION-20260915" and
            packet["source_revision"] == SOURCE and packet["image_sha256"] == IMAGE and
            packet["boot_id"] == DEPLOYED_BOOT and packet["b_boot_id"] == B_BOOT and
            packet["host_boot_id"] == HOST_BOOT and packet["configuration_writes"] == 2 and
            packet["rf_jobs"] == 2 and
            packet["rf_duration_ns"] == 350_592_000_000 and
            packet["controlled_reboots"] == 1 and packet["flashes"] == 0 and
            packet["bootsel"] == 0 and packet["wifi_cycles"] == 0 and
            packet["network_runtime_seconds"] == 7200 and
            packet["network_restoration_seconds"] == 900 and
            packet["address_change"] == [OLD_ADDRESS, NEW_ADDRESS] and
            packet["external_link_loss_seconds"] == 15 and
            packet["schedule_base_frequency_nhz"] == BASE_NHZ,
            "Exact Package 8 identity and finite budget")
    require(packet["credentials"] == {
        "controller": {"ca": "credentials/controller/client-ca.crt",
                       "cert": "credentials/controller/client.crt",
                       "key": "credentials/controller/client.key"},
        "browser": {"ca": "credentials/browser/client-ca.crt",
                    "cert": "credentials/browser/client.crt",
                    "key": "credentials/browser/client.key"}},
        "Frozen Package 8 credentials")
    names = ("network_session", "network_owner", "network_job", "usb_session",
             "post_network_session", "schedule_usb_session", "schedule_network_session",
             "inventory_session", "b_session")
    values = [packet[name] for name in names]
    require(len(set(values)) == len(values) and all(len(v) == 32 and v != "0" * 32 and
            all(c in "0123456789abcdef" for c in v) for v in values),
            "Distinct Package 8 identities")
    require(packet["storage_plan"] == {"before_sequence": "68", "before_offset": 6144,
            "record_size": 2048, "enabled_sequence": "69", "enabled_offset": 0,
            "restored_sequence": "70", "restored_offset": 2048},
            "Frozen two-write rotation plan")
    amendment = packet.get("corrective_amendment")
    require(amendment is None or amendment == {
        "reason": "pre-CLAIM CAPS field-shape harness defect",
        "prior_packet_sha256": "44918000c592b5348179fbafb5d96432efd2a577f6c1f5b3b9d7fcf8e853724d",
        "prior_attempt_rf_submissions": 0,
        "additional_rf_jobs": 0,
        "additional_rf_duration_ns": 0}, "Exact Package 8 corrective amendment")
    require(packet.get("execution_history") == {
        "prior_attempts": [
            {"packet_sha256":
             "44918000c592b5348179fbafb5d96432efd2a577f6c1f5b3b9d7fcf8e853724d",
             "disposition": "pre-claim-harness-failure", "rf_jobs": 0,
             "rf_duration_ns": 0},
            {"packet_sha256":
             "7248629e1c08d45571598f101da4f3687ea062680a4ed86e9e2ea2e6c9a6a5e3",
             "disposition": "address-recovery-failure", "rf_jobs": 1,
             "rf_duration_ns": 240_000_000_000}],
        "repair_deployment": {
            "packet_sha256":
            "45cdcb5c276498b5720a8745b0c8b76af255ad967ebb63445919f1b4d2c28324",
            "source_revision": SOURCE, "image_sha256": IMAGE,
            "boot_id": DEPLOYED_BOOT, "flashes": 1, "bootsel": 1},
        "aggregate_after_planned_success": {
            "rf_jobs": 3, "rf_duration_ns": 590_592_000_000,
            "configuration_writes": 2, "controlled_reboots": 1,
            "flashes": 2, "bootsel": 2}},
        "Exact Package 8 attempt and repair accounting")
    return packet


def tls_context(root, packet, role, alpn):
    cred = packet["credentials"][role]
    context = ssl.create_default_context(cafile=str(root / cred["ca"]))
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(root / cred["cert"], root / cred["key"])
    context.set_alpn_protocols([alpn])
    return context


class NetworkPeer:
    def __init__(self, root, packet, journal, address, boot, session):
        self.root, self.packet, self.journal = root, packet, journal
        self.address, self.boot, self.session = address, boot, session
        self.number, self.stream, self.decoder = 0, None, Decoder()

    def connect(self):
        raw = socket.create_connection((self.address, 18443), timeout=5)
        raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            self.stream = tls_context(self.root, self.packet, "controller", "wtp/1").wrap_socket(
                raw, server_hostname=HOSTNAME)
        except BaseException:
            raw.close()
            raise
        require(self.stream.version() == "TLSv1.3" and
                self.stream.selected_alpn_protocol() == "wtp/1" and
                hashlib.sha256(self.stream.getpeercert(binary_form=True)).hexdigest() == PEER_SHA,
                "Authenticated Package 8 WTP peer")
        self.journal.emit("network_connect", {"address": self.address,
                          "local": list(self.stream.getsockname()), "session": self.session})
        hello = self.ask("HELLO", {"versions": ["WTP/1"],
                         "client_name": "phase11-5-package8", "client_version": "1"})
        require(hello["device_id"] == DEVICE and hello["boot_id"] == self.boot,
                "Package 8 HELLO identity")
        require(self.ask("CAPS")["engine"] == "pio-dma-gp2", "Package 8 RF engine")
        return self

    def close(self):
        if self.stream is not None:
            self.stream.close()
            self.stream = None

    def ask(self, op, body=None):
        self.number += 1
        request = {"type": "request", "protocol": "WTP/1", "session_id": self.session,
                   "request_id": f"{self.number:032x}", "op": op, "body": body or {}}
        encoded = frame(json.dumps(request, separators=(",", ":")).encode())
        self.journal.emit("network_tx", {"request": request, "hex": encoded.hex()})
        self.stream.sendall(encoded)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            self.stream.settimeout(max(.001, deadline - time.monotonic()))
            data = self.stream.recv(4096)
            require(data, "Package 8 WTP EOF")
            self.journal.emit("network_rx", {"op": op, "hex": data.hex()})
            for value in self.decoder.feed(data):
                self.journal.emit("network_message", value)
                if value["type"] == "event":
                    require(value["boot_id"] == self.boot, "Package 8 event boot changed")
                    continue
                require(value["session_id"] == self.session and
                        value["request_id"] == request["request_id"] and
                        value["op"] == op and value["ok"] is True,
                        f"Package 8 {op} failed: {value.get('error')}")
                return value["body"]
        raise TimeoutError("Package 8 WTP response timeout: " + op)


def header(headers, name):
    return next((value for key, value in headers.items() if key.lower() == name.lower()), None)


def https_request(root, packet, journal, address, method, path, body=None, headers=None,
                  allow_disconnect=False):
    encoded = b"" if body is None else json.dumps(body, separators=(",", ":")).encode()
    request_headers = {"Host": f"{HOSTNAME}:18443", "Connection": "close"}
    if method != "GET":
        request_headers.update({"Origin": f"https://{HOSTNAME}:18443",
                                "Content-Type": "application/json",
                                "X-WsprryPico-Request": "1"})
    request_headers.update(headers or {})
    try:
        with socket.create_connection((address, 18443), timeout=5) as raw:
            with tls_context(root, packet, "browser", "http/1.1").wrap_socket(
                    raw, server_hostname=HOSTNAME) as stream:
                require(stream.selected_alpn_protocol() == "http/1.1" and
                        hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest() == PEER_SHA,
                        "Authenticated Package 8 HTTPS peer")
                connection = http.client.HTTPConnection(HOSTNAME)
                connection.sock = stream
                connection.request(method, path, body=encoded, headers=request_headers)
                response = connection.getresponse()
                data = response.read(131073)
                response_headers = dict(response.getheaders())
                status = response.status
    except (ConnectionError, OSError, TimeoutError):
        if allow_disconnect:
            journal.emit("http_disconnect_after_request", {"method": method, "path": path,
                         "request_body_sha256": hashlib.sha256(encoded).hexdigest()})
            return None, {}, None
        raise
    require(len(data) <= 131072, "Oversized Package 8 management response")
    value = json.loads(data)
    journal.emit("http", {"address": address, "method": method, "path": path,
                 "status": status, "headers": response_headers, "body": value,
                 "request_body_sha256": hashlib.sha256(encoded).hexdigest()})
    return status, response_headers, value


def console(journal, command, boot=None, timeout=8):
    def emit(kind, value):
        journal.emit("console_" + kind, value)
    with exclusive_port(Path(str(BASE) + "-if00")) as fd:
        info = exchange(fd, b"INFO\n", time.monotonic() + 5, emit, False)
        require(info["device_id"] == DEVICE and info["revision"] == SOURCE[:12],
                "Package 8 Console source/device")
        if boot is not None:
            require(info["status"]["boot_id"] == boot, "Package 8 Console boot")
        if command == "INFO":
            return info
        return exchange(fd, (command + "\n").encode(), time.monotonic() + timeout, emit, False)


def make_tone(job):
    duration = 240_000_000_000
    return {"job_id": job, "profile": "rf-events/1", "mode": "tone",
            "total_duration_ns": str(duration), "allow_frequency_adjustment": True,
            "events": [{"offset_ns": "0", "duration_ns": str(duration), "rf_on": True,
                        "frequency_nhz": BASE_NHZ}]}


def wait_info(journal, predicate, timeout, boot=None):
    deadline = time.monotonic() + timeout
    error = None
    while time.monotonic() < deadline:
        try:
            value = console(journal, "INFO", boot)
            journal.emit("info_observation", value)
            if predicate(value):
                return value
        except (OSError, ValueError, TimeoutError) as caught:
            error = caught
        time.sleep(.5)
    raise TimeoutError("Package 8 INFO convergence" + (": " + str(error) if error else ""))


def inv(root, packet, label, b=False):
    return inventory(root, packet, label, b)


def run_network(root, packet):
    suffix = "-attempt2" if (root / "network-run.jsonl").exists() else ""
    journal = Journal(root / ("network-run" + suffix + ".jsonl"))
    reservation = Reservation(digest(root / "packet.json"))
    peer = None
    try:
        ready = wait_info(journal, lambda i: i["network"]["ipv4"] == OLD_ADDRESS and
                          i["status"]["clock_state"] == "synchronized" and
                          i["status"]["enabled"] is False and
                          i["status"]["schedule_base_frequency_nhz"] == BASE_NHZ,
                          180, DEPLOYED_BOOT)
        before = {name: inv(root, packet, "network" + suffix + "-before-" + name, name == "b")
                  for name in ("a", "b")}
        require(before["a"]["wtp"]["STATUS"]["boot_id"] == DEPLOYED_BOOT and
                before["b"]["wtp"]["STATUS"]["boot_id"] == B_BOOT,
                "Package 8 network starting boots")
        reservation.acquire(before)
        save(root / ("network" + suffix + "-reservation-acquired.json"),
             json.loads(reservation.path.read_text()))
        peer = NetworkPeer(root, packet, journal, OLD_ADDRESS, DEPLOYED_BOOT,
                           packet["network_session"]).connect()
        caps = peer.ask("CAPS")
        require(int(caps["max_job_duration_ns"]) >= 240_000_000_000 and
                any(int(item["minimum_nhz"]) <= int(BASE_NHZ) <= int(item["maximum_nhz"])
                    for item in caps["frequency_ranges"]), "Package 8 tone capability")
        peer.ask("CLAIM", {"owner_id": packet["network_owner"], "lease_ms": 60000})
        peer.ask("LOAD", make_tone(packet["network_job"]))
        peer.ask("RENEW", {"owner_id": packet["network_owner"], "lease_ms": 60000})
        clock = peer.ask("GET_CLOCK")
        require(clock["state"] == "synchronized" and clock["leap"] == "normal",
                "Package 8 network clock")
        peer.ask("ARM", {"job_id": packet["network_job"],
                 "start_utc_ns": str(int(clock["utc_now_ns"]) + 5_000_000_000),
                 "max_start_uncertainty_ns": "500000000"})
        fault_script = root / "scripts/phase11_5_network_fault.py"
        with exclusive_port(Path(str(BASE) + "-if02")) as fd, \
                (root / ("network-usb-frames" + suffix + ".jsonl")).open("x") as wire, \
                contextlib.redirect_stdout(wire):
            usb = WtpPeer(fd, session=packet["usb_session"])
            hello = usb.request("HELLO", {"versions": ["WTP/1"],
                                "client_name": "phase11-5-package8-observer",
                                "client_version": "1"})
            require(hello["device_id"] == DEVICE and hello["boot_id"] == DEPLOYED_BOOT,
                    "Package 8 USB observer identity")
            deadline = time.monotonic() + 12
            while True:
                status = usb.request("STATUS", {})
                journal.emit("usb_status", status)
                if status["state"] == "running" and status["output_active"] is True:
                    break
                require(status["state"] == "armed" and time.monotonic() < deadline,
                        "Package 8 network Running transition")
                time.sleep(.05)
            require(status["job_id"] == packet["network_job"] and
                    status["owner_id"] == packet["network_owner"],
                    "Package 8 network Running authority")
            running_started = time.monotonic_ns()
            subprocess.run(["python3", str(fault_script), "lease", "--root", str(root), "--run"],
                           check=True, timeout=30)
            link = subprocess.Popen(["python3", str(fault_script), "link", "--root", str(root),
                                     "--run"], stdout=subprocess.DEVNULL,
                                    stderr=(root / ("network-link" + suffix + ".stderr")).open("xb"))
            running_samples = 0
            complete = None
            deadline = time.monotonic() + 260
            while time.monotonic() < deadline:
                status = usb.request("STATUS", {})
                journal.emit("usb_status", status)
                if status["state"] == "running":
                    require(status["job_id"] == packet["network_job"] and
                            status["owner_id"] == packet["network_owner"] and
                            status["output_active"] is True,
                            "Package 8 network authority changed")
                    running_samples += 1
                elif status["state"] == "complete":
                    complete = status
                    break
                else:
                    require(status["state"] == "armed", "Unexpected Package 8 network state")
                time.sleep(.2)
            require(complete is not None and running_samples >= 50,
                    "Package 8 USB continuity/completion")
            link.wait(timeout=10)
            require(link.returncode == 0, "Package 8 external link helper")
        peer.close(); peer = None
        terminal = [row for row in complete["terminal_records"]
                    if row["job_id"] == packet["network_job"]]
        require(len(terminal) == 1 and terminal[0]["state"] == "complete" and
                terminal[0]["output_active"] is False, "One Package 8 network completion")
        recovered = wait_info(journal, lambda i: i["network"]["ipv4"] == NEW_ADDRESS and
                              i["network"]["control_listening"] is True and
                              i["status"]["clock_state"] == "synchronized" and
                              i["status"]["state"] == "complete" and
                              i["status"]["output_active"] is False,
                              180, DEPLOYED_BOOT)
        fixture = Fixture(root)
        resolutions = []
        for _ in range(2):
            result = fixture.in_client(["getent", "-s", "mdns4", "ahostsv4", HOSTNAME],
                                       timeout=8)
            addresses = sorted({line.split()[0] for line in result.stdout.splitlines() if line})
            require(addresses == [NEW_ADDRESS], "Native Package 8 name recovery")
            resolutions.append(addresses)
            time.sleep(1)
        post = NetworkPeer(root, packet, journal, NEW_ADDRESS, DEPLOYED_BOOT,
                           packet["post_network_session"]).connect()
        post_status = post.ask("STATUS")
        post.close()
        require(post_status["state"] == "complete" and post_status["output_active"] is False,
                "Authenticated WTP recovery")
        code, _, web = https_request(root, packet, journal, NEW_ADDRESS, "GET", "/api/v1/status")
        require(code == 200 and web["job"]["boot_id"] == DEPLOYED_BOOT and
                web["job"]["output_active"] is False, "Authenticated HTTPS recovery")
        after = {name: inv(root, packet, "network" + suffix + "-final-" + name, name == "b")
                 for name in ("a", "b")}
        reservation.release(after)
        save(root / ("network" + suffix + "-reservation-released.json"),
             json.loads(reservation.path.read_text()))
        result = {"status": "accepted", "boot_id": DEPLOYED_BOOT,
                  "job_id": packet["network_job"], "owner_id": packet["network_owner"],
                  "planned_duration_ns": 240_000_000_000,
                  "running_started_monotonic_ns": running_started,
                  "running_usb_samples": running_samples, "terminal": terminal[0],
                  "recovered_ipv4": recovered["network"]["ipv4"],
                  "native_resolutions": resolutions,
                  "sntp_accepted": recovered["network"]["accepted"],
                  "sntp_rejected": recovered["network"]["rejected"]}
        save(root / "network-result.json", result)
        journal.emit("network_pass", result)
    finally:
        if peer is not None:
            peer.close()
        reservation.close()
        journal.close()


def run_network_finalize(root, packet):
    continuation_path = root / "network-finalize-packet.json"
    continuation = json.loads(continuation_path.read_text())
    require(continuation == {
        "schema": "phase11.5-package8-network-finalize-v1",
        "standing_authority": "PHASE11.5-COMPLETION-20260915",
        "parent_packet_sha256": digest(root / "packet.json"),
        "parent_failure": "post-recovery HTTPS helper name collision",
        "helper_sha256": digest(Path(__file__)),
        "limits": {"rf_jobs": 0, "rf_duration_ns": 0, "loads": 0, "arm": 0,
                   "configuration_writes": 0, "controlled_reboots": 0,
                   "flashes": 0, "bootsel": 0, "wifi_cycles": 0}},
        "Exact zero-mutation Package 8 network continuation")
    require(not (root / "network-result.json").exists(),
            "Package 8 network result already exists")
    rows = [json.loads(line) for line in (root / "network-run.jsonl").read_text().splitlines()]
    statuses = [row for row in rows if row["kind"] == "usb_status"]
    running = [row for row in statuses if row["value"]["state"] == "running"]
    completed = [row for row in statuses if row["value"]["state"] == "complete"]
    require(len(running) >= 50 and len(completed) == 1,
            "Preserved Package 8 RF continuity/completion")
    complete = completed[0]["value"]
    terminal = [row for row in complete["terminal_records"]
                if row["job_id"] == packet["network_job"]]
    require(len(terminal) == 1 and terminal[0]["state"] == "complete" and
            terminal[0]["output_active"] is False and complete["output_active"] is False,
            "Preserved Package 8 terminal record")
    recovered_rows = [row["value"] for row in rows if row["kind"] == "info_observation" and
                      row["value"]["network"]["ipv4"] == NEW_ADDRESS and
                      row["value"]["status"]["clock_state"] == "synchronized"]
    require(recovered_rows and recovered_rows[-1]["network"]["link_status"] == 3 and
            recovered_rows[-1]["network"]["control_listening"] is True and
            recovered_rows[-1]["status"]["state"] == "complete" and
            recovered_rows[-1]["status"]["output_active"] is False,
            "Preserved Package 8 address/SNTP recovery")
    post_status = [row["value"]["body"] for row in rows
                   if row["kind"] == "network_message" and
                   row["value"].get("session_id") == packet["post_network_session"] and
                   row["value"].get("op") == "STATUS" and row["value"].get("ok") is True]
    require(post_status and post_status[-1]["state"] == "complete" and
            post_status[-1]["output_active"] is False,
            "Preserved authenticated WTP recovery")
    fixture_rows = [json.loads(line) for line in (root / "fixture.jsonl").read_text().splitlines()]
    kinds = [row["kind"] for row in fixture_rows]
    require(kinds.count("dhcp_binding_changed") == 1 and
            kinds.count("external_link_down") == 1 and
            kinds.count("external_link_restored") == 1,
            "One preserved Package 8 network fault sequence")
    journal = Journal(root / "network-finalize.jsonl")
    reservation = None
    try:
        current = wait_info(journal, lambda i: i["network"]["ipv4"] == NEW_ADDRESS and
                            i["network"]["link_status"] == 3 and
                            i["status"]["clock_state"] == "synchronized" and
                            i["status"]["state"] == "complete" and
                            i["status"]["output_active"] is False,
                            30, DEPLOYED_BOOT)
        fixture = Fixture(root)
        resolutions = []
        for _ in range(2):
            answer = fixture.in_client(["getent", "-s", "mdns4", "ahostsv4", HOSTNAME],
                                       timeout=8)
            addresses = sorted({line.split()[0] for line in answer.stdout.splitlines() if line})
            require(addresses == [NEW_ADDRESS], "Native Package 8 name recovery")
            resolutions.append(addresses)
            time.sleep(1)
        code, _, web = https_request(root, packet, journal, NEW_ADDRESS, "GET", "/api/v1/status")
        require(code == 200 and web["job"]["boot_id"] == DEPLOYED_BOOT and
                web["job"]["state"] == "complete" and
                web["job"]["output_active"] is False,
                "Authenticated HTTPS recovery")
        before = {name: inv(root, packet, "network-finalize-before-" + name, name == "b")
                  for name in ("a", "b")}
        observed = time.monotonic_ns()
        reservation = Reservation(digest(root / "packet.json"),
                                  reconciliation=(before, observed))
        after = {name: inv(root, packet, "network-finalize-final-" + name, name == "b")
                 for name in ("a", "b")}
        reservation.release(after)
        save(root / "network-finalize-reservation-released.json",
             json.loads(reservation.path.read_text()))
        result = {"status": "accepted", "boot_id": DEPLOYED_BOOT,
                  "job_id": packet["network_job"], "owner_id": packet["network_owner"],
                  "planned_duration_ns": 240_000_000_000,
                  "running_started_monotonic_ns": running[0]["monotonic_ns"],
                  "running_usb_samples": len(running), "terminal": terminal[0],
                  "recovered_ipv4": current["network"]["ipv4"],
                  "native_resolutions": resolutions,
                  "sntp_accepted": current["network"]["accepted"],
                  "sntp_rejected": current["network"]["rejected"],
                  "https_status": code,
                  "continuation_packet_sha256": digest(continuation_path)}
        save(root / "network-result.json", result)
        journal.emit("network_pass", result)
    finally:
        if reservation is not None:
            reservation.close()
        journal.close()


def schedule_occurrence(now_s):
    occurrence = ((int(now_s) + 359) // 120) * 120 + 1
    if occurrence - now_s < 240:
        occurrence += 120
    return occurrence, (occurrence - 1) % 86400


def storage_position(value):
    require(value["ok"] is True and value["healthy"] is True, "Healthy Package 8 storage")
    return value["config"]


def storage_retry_packet(root):
    path = root / "storage-retry-packet.json"
    value = json.loads(path.read_text())
    require(value.get("schema") == "phase11.5-package8-storage-retry-v1" and
            value.get("standing_authority") == "PHASE11.5-COMPLETION-20260915" and
            value.get("parent_packet_sha256") == digest(root / "packet.json") and
            value.get("source_revision") == SOURCE and value.get("image_sha256") == IMAGE and
            value.get("prior_boot_id") == DEPLOYED_BOOT and
            value.get("current_boot_id") == "8af7e0f0f4cef61bcbf8d5f7173d4c78" and
            value.get("prior_attempt") == {
                "result": "observer-idle-timeout-before-autonomous-rf",
                "rf_jobs": 0, "rf_duration_ns": 0, "configuration_writes": 2,
                "controlled_reboots": 1,
                "storage_run_sha256": digest(root / "storage-run.jsonl")} and
            value.get("limits") == {"rf_jobs": 1, "rf_duration_ns": 110_592_000_000,
                "loads": 0, "arm": 0, "time_commands": 0, "configuration_writes": 2,
                "controlled_reboots": 1, "flashes": 0, "bootsel": 0,
                "wifi_cycles": 0} and
            value.get("storage_plan") == {"before_sequence": "70", "before_offset": 2048,
                "record_size": 2048, "enabled_sequence": "71", "enabled_offset": 4096,
                "restored_sequence": "72", "restored_offset": 6144,
                "watermark_utc_ns": "1789606801000000000"} and
            value.get("aggregate_after_planned_success") == {
                "rf_jobs": 3, "rf_duration_ns": 590_592_000_000,
                "configuration_writes": 4, "controlled_reboots": 2,
                "flashes": 2, "bootsel": 2} and
            value.get("helper_sha256") == digest(Path(__file__)) and
            value.get("reservation_helper_sha256") ==
                digest(root / "scripts/phase11_5_rf_reservation.py"),
            "Exact bounded Package 8 storage retry")
    sessions = [value.get(name) for name in
                ("usb_session", "armed_network_session", "running_network_session")]
    require(len(set(sessions)) == 3 and all(isinstance(item, str) and len(item) == 32 and
            all(c in "0123456789abcdef" for c in item) for item in sessions),
            "Distinct Package 8 retry identities")
    return value, digest(path)


def run_storage_retry(root, packet):
    retry, retry_sha = storage_retry_packet(root)
    journal = Journal(root / "storage-retry.jsonl")
    reservation = None
    current_boot = retry["current_boot_id"]
    original_private = None
    writes = 0
    restored = False
    try:
        before = {name: inv(root, packet, "storage-retry-before-" + name, name == "b")
                  for name in ("a", "b")}
        observed = time.monotonic_ns()
        old = Reservation(digest(root / "packet.json"), reconciliation=(before, observed),
                          authorized_boot_changes={"a": (DEPLOYED_BOOT, current_boot)})
        try:
            old.release(before)
            save(root / "storage-retry-parent-reservation-released.json",
                 json.loads(old.path.read_text()))
        finally:
            old.close()
        reservation = Reservation(retry_sha)
        reservation.acquire(before)
        save(root / "storage-retry-reservation-acquired.json",
             json.loads(reservation.path.read_text()))
        initial = storage_position(console(journal, "STORAGE", current_boot))
        require(initial == {"sequence": "70", "latest_offset": 2048, "record_size": 2048},
                "Package 8 retry starting journal position")
        initial_info = console(journal, "INFO", current_boot)
        require(initial_info["status"]["enabled"] is False and
                initial_info["status"]["suspended"] is True and
                initial_info["status"]["watermark_utc_ns"] ==
                    retry["storage_plan"]["watermark_utc_ns"] and
                initial_info["status"]["output_active"] is False,
                "Package 8 failed attempt cleanup state")
        code, headers, body = https_request(root, packet, journal, NEW_ADDRESS,
                                             "GET", "/api/v1/config")
        require(code == 200 and body["config"]["enabled"] is False and
                body["config"]["station"] == {"callsign": "AA0NT", "locator": "EM18",
                                                "power_dbm": 20} and
                body["config"]["schedules"] == [{"period_s": 120, "phase_s": 0}],
                "Package 8 retry retained baseline")
        original = body["config"]
        original_private = json.loads(json.dumps(original))
        original_private["wifi"]["password"] = json.loads(
            (root / "retained-wifi.json").read_text())["password"]
        occurrence, phase = schedule_occurrence(time.time())
        enabled = json.loads(json.dumps(original))
        enabled.update(enabled=True, expires_utc_s=occurrence + 300,
                       schedules=[{"period_s": 86400, "phase_s": phase}])
        writes = 1
        code, save_headers, saved = https_request(root, packet, journal, NEW_ADDRESS, "PUT",
            "/api/v1/config", enabled, {"If-Match": header(headers, "ETag")})
        require(code == 200 and saved["config"]["enabled"] is True and
                saved.get("reboot_required") is False, "Package 8 retry enabled save")
        rotated = storage_position(console(journal, "STORAGE", current_boot))
        require(rotated == {"sequence": "71", "latest_offset": 4096, "record_size": 2048},
                "Package 8 retry enabled journal position")
        code, _, _ = https_request(root, packet, journal, NEW_ADDRESS, "POST",
            "/api/v1/restart", {}, {"If-Match": header(save_headers, "ETag")}, True)
        require(code in (None, 202), "Package 8 retry restart request")
        first = wait_info(journal, lambda i: i["status"]["boot_id"] != current_boot, 30)
        current_boot = first["status"]["boot_id"]
        require(first["status"]["enabled"] is True and
                first["status"]["suspended"] is False and
                first["status"]["clock_state"] == "unsynchronized" and
                first["status"]["watermark_utc_ns"] ==
                    retry["storage_plan"]["watermark_utc_ns"] and
                first["status"]["state"] == "empty" and
                first["status"]["output_active"] is False,
                "Package 8 retry boot admission gate")
        synchronized = wait_info(journal, lambda i: i["network"]["ipv4"] == NEW_ADDRESS and
                                 i["status"]["clock_state"] == "synchronized" and
                                 i["status"]["enabled"] is True, 180, current_boot)
        expected_job = "eeeeeeeeeeeeeeee" + f"{occurrence * 1_000_000_000:016x}"
        with exclusive_port(Path(str(BASE) + "-if02")) as fd, \
                (root / "storage-retry-usb-frames.jsonl").open("x") as wire, \
                contextlib.redirect_stdout(wire):
            usb = WtpPeer(fd, session=retry["usb_session"])
            hello = usb.request("HELLO", {"versions": ["WTP/1"],
                                "client_name": "phase11-5-package8-retry-observer",
                                "client_version": "1"})
            require(hello["device_id"] == DEVICE and hello["boot_id"] == current_boot,
                    "Package 8 retry USB identity")
            deadline = time.monotonic() + max(30, occurrence - time.time() + 130)
            armed = running = complete = None
            while time.monotonic() < deadline:
                state = usb.request("STATUS", {})
                journal.emit("retry_usb_status", state)
                if state["state"] == "armed" and armed is None:
                    require(state["owner_id"] == LOCAL_OWNER and state["job_id"] == expected_job and
                            state["output_active"] is False, "Package 8 retry local Armed")
                    armed = state
                    durable = console(journal, "INFO", current_boot)
                    require(durable["status"]["watermark_utc_ns"] ==
                            str(occurrence * 1_000_000_000),
                            "Package 8 retry durable watermark")
                    observer = NetworkPeer(root, packet, journal, NEW_ADDRESS, current_boot,
                                           retry["armed_network_session"]).connect()
                    try:
                        require(observer.ask("STATUS")["job_id"] == expected_job,
                                "Package 8 retry network Armed observer")
                    finally:
                        observer.close()
                    https_request(root, packet, journal, NEW_ADDRESS, "GET", "/api/v1/status")
                elif state["state"] == "running" and running is None:
                    require(state["owner_id"] == LOCAL_OWNER and state["job_id"] == expected_job and
                            state["output_active"] is True, "Package 8 retry local Running")
                    running = state
                    position = storage_position(console(journal, "STORAGE", current_boot))
                    rejected = console(journal, "CONFIG " + json.dumps(
                        original_private, separators=(",", ":")), current_boot)
                    require(rejected == {"ok": False, "error": "busy"} and
                            storage_position(console(journal, "STORAGE", current_boot)) == position,
                            "Package 8 retry busy write rejection")
                    observer = NetworkPeer(root, packet, journal, NEW_ADDRESS, current_boot,
                                           retry["running_network_session"]).connect()
                    try:
                        require(observer.ask("STATUS")["output_active"] is True,
                                "Package 8 retry network Running observer")
                    finally:
                        observer.close()
                    code, _, web = https_request(root, packet, journal, NEW_ADDRESS,
                                                 "GET", "/api/v1/status")
                    require(code == 200 and web["job"]["job_id"] == expected_job and
                            web["job"]["output_active"] is True,
                            "Package 8 retry HTTPS Running observer")
                elif state["state"] == "complete":
                    complete = state
                    break
                else:
                    require(state["state"] in ("empty", "armed", "running"),
                            "Unexpected Package 8 retry state")
                time.sleep(.2)
        require(armed is not None and running is not None and complete is not None and
                complete["owner_id"] is None and complete["output_active"] is False,
                "Package 8 retry autonomous lifecycle")
        terminals = [row for row in complete["terminal_records"]
                     if row["job_id"] == expected_job]
        require(len(terminals) == 1 and terminals[0]["state"] == "complete" and
                terminals[0]["output_active"] is False,
                "Package 8 retry autonomous completion")
        code, restore_headers, current = https_request(root, packet, journal, NEW_ADDRESS,
                                                        "GET", "/api/v1/config")
        require(code == 200 and current["config"]["enabled"] is True,
                "Package 8 retry pre-restoration configuration")
        writes = 2
        code, _, restored_body = https_request(root, packet, journal, NEW_ADDRESS, "PUT",
            "/api/v1/config", original, {"If-Match": header(restore_headers, "ETag")})
        require(code == 200 and restored_body["config"] == original and
                restored_body.get("reboot_required") is False,
                "Package 8 retry API restoration")
        restored = True
        final_storage = storage_position(console(journal, "STORAGE", current_boot))
        require(final_storage == {"sequence": "72", "latest_offset": 6144,
                                  "record_size": 2048},
                "Package 8 retry final journal position")
        final_info = console(journal, "INFO", current_boot)
        require(final_info["status"]["enabled"] is False and
                final_info["status"]["watermark_utc_ns"] ==
                    str(occurrence * 1_000_000_000) and
                final_info["status"]["output_active"] is False and
                final_info["status"]["schedule_base_frequency_nhz"] == BASE_NHZ,
                "Package 8 retry final retained state")
        after = {name: inv(root, packet, "storage-retry-final-" + name, name == "b")
                 for name in ("a", "b")}
        require(after["b"]["wtp"]["STATUS"]["boot_id"] == B_BOOT,
                "Package 8 retry comparator unchanged")
        reservation.release(after)
        save(root / "storage-retry-reservation-released.json",
             json.loads(reservation.path.read_text()))
        result = {"status": "accepted", "prior_boot_id": retry["current_boot_id"],
                  "boot_id": current_boot,
                  "occurrence_utc_ns": str(occurrence * 1_000_000_000),
                  "job_id": expected_job, "owner_id": LOCAL_OWNER,
                  "planned_duration_ns": 110_592_000_000,
                  "unsynchronized_observation": first["status"],
                  "synchronized_observation": synchronized["status"],
                  "storage_before": initial, "storage_rotated": rotated,
                  "storage_restored": final_storage, "terminal": terminals[0],
                  "final_status": final_info["status"], "configuration_writes": writes,
                  "retry_packet_sha256": retry_sha}
        save(root / "storage-result.json", result)
        journal.emit("storage_retry_pass", result)
    except BaseException:
        if writes and not restored and original_private is not None:
            try:
                observed = console(journal, "INFO")
                current_boot = observed["status"]["boot_id"]
                (stopped := console(journal, "STOP", current_boot))
                journal.emit("retry_cleanup_stop", stopped)
                position = storage_position(console(journal, "STORAGE", current_boot))
                if position["sequence"] != retry["storage_plan"]["restored_sequence"] and writes < 2:
                    reply = console(journal, "CONFIG " + json.dumps(
                        original_private, separators=(",", ":")), current_boot)
                    journal.emit("retry_cleanup_restore", reply)
            except BaseException as cleanup_error:
                journal.emit("retry_cleanup_failure", {
                    "type": type(cleanup_error).__name__, "message": str(cleanup_error)})
        raise
    finally:
        if reservation is not None:
            reservation.close()
        journal.close()


def run_storage(root, packet):
    journal = Journal(root / "storage-run.jsonl")
    reservation = Reservation(digest(root / "packet.json"))
    enabled_written = restored = False
    current_boot = DEPLOYED_BOOT
    original_private = None
    try:
        before = {name: inv(root, packet, "storage-before-" + name, name == "b")
                  for name in ("a", "b")}
        reservation.acquire(before)
        save(root / "storage-reservation-acquired.json", json.loads(reservation.path.read_text()))
        initial = storage_position(console(journal, "STORAGE", DEPLOYED_BOOT))
        require(initial == {"sequence": "68", "latest_offset": 6144, "record_size": 2048},
                "Package 8 live rotation starting position")
        code, headers, body = https_request(root, packet, journal, NEW_ADDRESS, "GET", "/api/v1/config")
        require(code == 200 and body["config"]["enabled"] is False and
                body["config"]["station"] == {"callsign": "AA0NT", "locator": "EM18",
                                               "power_dbm": 20} and
                body["config"]["wifi"]["ssid"] == "WsprryPico-Phase115" and
                body["config"]["wifi"]["ntp_ipv4"] == "time.local" and
                body["config"]["schedules"] == [{"period_s": 120, "phase_s": 0}] and
                body["config"].get("expires_utc_s", 0) == 0,
                "Package 8 retained configuration baseline")
        original = body["config"]
        original_private = json.loads(json.dumps(original))
        retained = json.loads((root / "retained-wifi.json").read_text())
        original_private["wifi"]["password"] = retained["password"]
        occurrence, phase = schedule_occurrence(time.time())
        enabled = json.loads(json.dumps(original))
        enabled.update(enabled=True, expires_utc_s=occurrence + 300,
                       schedules=[{"period_s": 86400, "phase_s": phase}])
        code, save_headers, saved = https_request(root, packet, journal, NEW_ADDRESS, "PUT",
            "/api/v1/config", enabled, {"If-Match": header(headers, "ETag")})
        require(code == 200 and saved["config"]["enabled"] is True and
                saved["config"]["schedules"] == enabled["schedules"] and
                saved["config"]["expires_utc_s"] == enabled["expires_utc_s"] and
                saved.get("reboot_required") is False, "Package 8 enabled save")
        enabled_written = True
        rotated = storage_position(console(journal, "STORAGE", DEPLOYED_BOOT))
        require(rotated == {"sequence": "69", "latest_offset": 0, "record_size": 2048},
                "Package 8 journal bank crossing")
        old_watermark = console(journal, "INFO", DEPLOYED_BOOT)["status"]["watermark_utc_ns"]
        code, _, response = https_request(root, packet, journal, NEW_ADDRESS, "POST",
                                          "/api/v1/restart", {},
                                          {"If-Match": header(save_headers, "ETag")}, True)
        require(code in (None, 202), "Package 8 restart request")
        first = wait_info(journal, lambda i: i["status"]["boot_id"] != DEPLOYED_BOOT, 30)
        current_boot = first["status"]["boot_id"]
        require(first["status"]["enabled"] is True and
                first["status"]["clock_state"] == "unsynchronized" and
                first["status"]["watermark_utc_ns"] == old_watermark and
                first["status"]["state"] == "empty" and
                first["status"]["last_job"] == "" and
                first["status"]["output_active"] is False,
                "Package 8 unsynchronized admission gate")
        synchronized = wait_info(journal, lambda i: i["network"]["ipv4"] == NEW_ADDRESS and
                                 i["status"]["clock_state"] == "synchronized" and
                                 i["status"]["enabled"] is True,
                                 180, current_boot)
        expected_job = "eeeeeeeeeeeeeeee" + f"{occurrence * 1_000_000_000:016x}"
        network = NetworkPeer(root, packet, journal, NEW_ADDRESS, current_boot,
                              packet["schedule_network_session"]).connect()
        with exclusive_port(Path(str(BASE) + "-if02")) as fd, \
                (root / "schedule-usb-frames.jsonl").open("x") as wire, \
                contextlib.redirect_stdout(wire):
            usb = WtpPeer(fd, session=packet["schedule_usb_session"])
            hello = usb.request("HELLO", {"versions": ["WTP/1"],
                                "client_name": "phase11-5-package8-schedule-observer",
                                "client_version": "1"})
            require(hello["device_id"] == DEVICE and hello["boot_id"] == current_boot,
                    "Package 8 schedule USB identity")
            deadline = time.monotonic() + max(30, occurrence - time.time() + 130)
            armed = running = complete = None
            while time.monotonic() < deadline:
                state = usb.request("STATUS", {})
                journal.emit("schedule_usb_status", state)
                if state["state"] == "armed" and armed is None:
                    require(state["owner_id"] == LOCAL_OWNER and state["job_id"] == expected_job and
                            state["output_active"] is False, "Package 8 local Armed authority")
                    armed = state
                    durable = console(journal, "INFO", current_boot)
                    require(durable["status"]["watermark_utc_ns"] == str(occurrence * 1_000_000_000),
                            "Package 8 durable occurrence watermark")
                    require(network.ask("STATUS")["job_id"] == expected_job,
                            "Package 8 network WTP Armed observer")
                    https_request(root, packet, journal, NEW_ADDRESS, "GET", "/api/v1/status")
                elif state["state"] == "running" and running is None:
                    require(state["owner_id"] == LOCAL_OWNER and state["job_id"] == expected_job and
                            state["output_active"] is True, "Package 8 local Running authority")
                    running = state
                    storage_before = storage_position(console(journal, "STORAGE", current_boot))
                    rejected = console(journal, "CONFIG " + json.dumps(
                        original_private, separators=(",", ":")), current_boot)
                    require(rejected == {"ok": False, "error": "busy"},
                            "Package 8 Running CONFIG rejection")
                    storage_after = storage_position(console(journal, "STORAGE", current_boot))
                    require(storage_after == storage_before == rotated,
                            "Package 8 busy write left journal unchanged")
                    require(network.ask("STATUS")["output_active"] is True,
                            "Package 8 network WTP Running observer")
                    code, _, web = https_request(root, packet, journal, NEW_ADDRESS,
                                                 "GET", "/api/v1/status")
                    require(code == 200 and web["job"]["job_id"] == expected_job and
                            web["job"]["output_active"] is True,
                            "Package 8 HTTPS Running observer")
                elif state["state"] == "complete":
                    complete = state
                    break
                else:
                    require(state["state"] in ("empty", "armed", "running"),
                            "Unexpected Package 8 autonomous state")
                time.sleep(.2)
        network.close()
        require(armed is not None and running is not None and complete is not None and
                complete["owner_id"] is None and complete["output_active"] is False,
                "Package 8 autonomous lifecycle")
        terminals = [row for row in complete["terminal_records"] if row["job_id"] == expected_job]
        require(len(terminals) == 1 and terminals[0]["state"] == "complete" and
                terminals[0]["output_active"] is False, "One autonomous completion")
        code, restore_headers, current = https_request(root, packet, journal, NEW_ADDRESS,
                                                       "GET", "/api/v1/config")
        require(code == 200 and current["config"]["enabled"] is True,
                "Package 8 pre-restoration configuration")
        code, _, restored_body = https_request(root, packet, journal, NEW_ADDRESS, "PUT",
            "/api/v1/config", original, {"If-Match": header(restore_headers, "ETag")})
        require(code == 200 and restored_body["config"] == original and
                restored_body.get("reboot_required") is False, "Package 8 API restoration")
        restored = True
        final_storage = storage_position(console(journal, "STORAGE", current_boot))
        require(final_storage == {"sequence": "70", "latest_offset": 2048,
                                  "record_size": 2048}, "Package 8 final storage position")
        final_info = console(journal, "INFO", current_boot)
        require(final_info["status"]["enabled"] is False and
                final_info["status"]["watermark_utc_ns"] == str(occurrence * 1_000_000_000) and
                final_info["status"]["output_active"] is False and
                final_info["status"]["schedule_base_frequency_nhz"] == BASE_NHZ,
                "Package 8 final retained state")
        after = {name: inv(root, packet, "storage-final-" + name, name == "b")
                 for name in ("a", "b")}
        require(after["b"]["wtp"]["STATUS"]["boot_id"] == B_BOOT,
                "Package 8 comparator unchanged")
        reservation.release(after)
        save(root / "storage-reservation-released.json", json.loads(reservation.path.read_text()))
        result = {"status": "accepted", "prior_boot_id": DEPLOYED_BOOT,
                  "boot_id": current_boot, "occurrence_utc_ns": str(occurrence * 1_000_000_000),
                  "job_id": expected_job, "owner_id": LOCAL_OWNER,
                  "planned_duration_ns": 110_592_000_000,
                  "unsynchronized_observation": first["status"],
                  "synchronized_observation": synchronized["status"],
                  "storage_before": initial, "storage_rotated": rotated,
                  "storage_restored": final_storage, "terminal": terminals[0],
                  "final_status": final_info["status"]}
        save(root / "storage-result.json", result)
        journal.emit("storage_pass", result)
    except BaseException:
        if enabled_written and not restored and original_private is not None:
            try:
                wait_info(journal, lambda i: i["status"]["boot_id"] == current_boot, 30)
                (void := console(journal, "STOP", current_boot))
                journal.emit("cleanup_stop", void)
                deadline = time.monotonic() + 130
                while time.monotonic() < deadline:
                    info = console(journal, "INFO", current_boot)
                    if info["status"]["state"] not in ("armed", "running") and not info["status"]["output_active"]:
                        break
                    time.sleep(.5)
                reply = console(journal, "CONFIG " + json.dumps(
                    original_private, separators=(",", ":")), current_boot)
                journal.emit("cleanup_restore", reply)
            except BaseException as cleanup_error:
                journal.emit("cleanup_failure", {"type": type(cleanup_error).__name__,
                             "message": str(cleanup_error)})
        raise
    finally:
        reservation.close()
        journal.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("network", "network-finalize", "storage",
                                           "storage-retry"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no device, RF, network or configuration action performed.")
        return
    require(os.geteuid() == 0 and Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT,
            "Package 8 wspr5 root/boot")
    root = args.root.resolve(strict=True)
    require(root.is_dir() and root.stat().st_mode & 0o077 == 0 and
            Path(__file__).resolve() == root / "scripts/phase11_5_package8.py",
            "Fresh private staged Package 8 root")
    os.umask(0o077)
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(digest(root / "candidate.sha256") == packet["candidate_identity_sha256"],
            "Package 8 candidate identity record")
    if args.action == "network":
        run_network(root, packet)
    elif args.action == "network-finalize":
        run_network_finalize(root, packet)
    elif args.action == "storage-retry":
        require((root / "network-result.json").exists() and
                (root / "storage-run.jsonl").exists(),
                "Network closure and preserved failed storage evidence required")
        run_storage_retry(root, packet)
    else:
        require((root / "network-result.json").exists(), "Network run must close before storage run")
        run_storage(root, packet)


if __name__ == "__main__":
    main()
