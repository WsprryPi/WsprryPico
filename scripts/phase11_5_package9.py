#!/usr/bin/env python3
"""Execute the frozen Phase 11.5 Package 9 sustained mixed-operation packet."""

import argparse
import configparser
import contextlib
import hashlib
import http.client
import json
import os
from pathlib import Path
import signal
import socket
import ssl
import subprocess
import threading
import time

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_pilot import Decoder
from phase11_5_rf_reservation import Reservation
from validate_wtp_contract import frame


SOURCE = "91933c00970939e366d1bfcf3c1956b59be8f6c5"
IMAGE = "5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446"
BOOT = "ff719d304f1ba4ac23fddd93561b26f0"
SERIAL = "0BF4B4AEC9FFB344"
DEVICE = "fd6127d11d6aca42a9905fa3fb1bf1d5"
B_SERIAL = "CDDBF8767C506C07"
B_DEVICE = "29f20b7342051ef947aa56cb9d4fab42"
B_BOOT = "6684b4b197d80cfa0ce83b3aaf205cb0"
HOST_BOOT = "220e53ca-ca95-4206-9581-dbe28aa1eeb8"
WSPRRYPI_SOURCE = "21ae75ab9e38bd6237b1ae73f3e7ab8527324067"
HOSTNAME = "wsprrypico-0a60df.local"
ADDRESS = "10.77.15.10"
PEER_SHA = "06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016"
BASE = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}")
NORMALIZER_DURATION_NS = 1_000_000_000
NORMALIZER_ARM_LEAD_NS = 10_000_000_000
PRODUCTION_DURATION_NS = 114_600_000_000
RF_DURATION_NS = 8 * NORMALIZER_DURATION_NS + 3 * PRODUCTION_DURATION_NS
NORMAL_SECONDS = 600
BASELINE_QUIET_SECONDS = 360
INTERLEAVED_QUIET_SECONDS = 306
FINAL_QUIET_SECONDS = 360
CRITICAL_PATH_NS = 2_849_391
READINESS_SECONDS = 300
FRESH_CLOCK_WAIT_SECONDS = 90
FRESH_CLOCK_AGE_NS = 10_000_000_000
MAX_HOLDOVER_AGE_NS = 90_000_000_000
NORMALIZER_REQUEST_TIMEOUT_SECONDS = 20
MEMORY_PREFLIGHT_SECONDS = 360
MEMORY_PREFLIGHT_SAMPLE_SECONDS = 15
MINIMUM_PREFLIGHT_HEAP_AVAILABLE_BYTES = 165_000
MINIMUM_INVENTORY_HEAP_AVAILABLE_BYTES = 150_000
MINIMUM_CONNECTED_HEAP_AVAILABLE_BYTES = 125_000
HOST_SYSTEMCTL = ["/usr/bin/nsenter", "-t", "1", "-m", "-n",
                  "/usr/bin/systemctl"]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def identity(value, label):
    require(isinstance(value, str) and len(value) == 32 and value != "0" * 32 and
            all(c in "0123456789abcdef" for c in value), label)
    return value


def normalizer_jobs(seed):
    event_ns = 1_953_125
    events = [{"offset_ns": str(index * event_ns), "duration_ns": str(event_ns),
               "rf_on": True, "frequency_nhz":
               str(135_500_000_000_000 if index % 2 == 0 else 135_495_000_000_000)}
              for index in range(512)]
    return [{"job_id": hashlib.sha256(f"{seed}:warmup:{index}".encode()).hexdigest()[:32],
             "profile": "rf-events/1", "mode": "fskcw",
             "total_duration_ns": str(NORMALIZER_DURATION_NS),
             "allow_frequency_adjustment": True,
             "events": [dict(event) for event in events]} for index in range(8)]


def browser_actions():
    paths = ("/", "/api/v1/capabilities", "/api/v1/status", "/api/v1/config")
    one = [(0, "initialize", paths), (30, "refresh", ("/api/v1/status",)),
           (70, "refresh", ("/api/v1/status",)),
           (110, "refresh", ("/api/v1/status",)), (150, "reload", paths),
           (190, "refresh", ("/api/v1/status",)),
           (230, "refresh", ("/api/v1/status",)),
           (270, "refresh", ("/api/v1/status",))]
    # Lists survive the JSON packet round trip without a type change.
    return [[base + offset, action, list(resources)]
            for base in (0, 300) for offset, action, resources in one]


def validate(packet):
    require(packet["schema"] == "phase11.5-package9-fixture-v1" and
            packet["family"] == "R6" and
            packet["standing_authority"] == "PHASE11.5-COMPLETION-20260915" and
            packet["source_revision"] == SOURCE and packet["image_sha256"] == IMAGE and
            packet["boot_id"] == BOOT and packet["serial"] == SERIAL and
            packet["device_id"] == DEVICE and packet["b_serial"] == B_SERIAL and
            packet["b_device_id"] == B_DEVICE and packet["b_boot_id"] == B_BOOT and
            packet["host_boot_id"] == HOST_BOOT and
            packet["wsprrypi_source_revision"] == WSPRRYPI_SOURCE and
            packet["address"] == ADDRESS and packet["hostname"] == HOSTNAME and
            packet["peer_sha256"] == PEER_SHA, "Exact Package 9 identity")
    require(packet["network_runtime_seconds"] == 5400 and
            packet["network_restoration_seconds"] == 900 and
            packet["configuration_writes"] == packet["controlled_reboots"] ==
            packet["flashes"] == packet["bootsel"] == packet["wifi_cycles"] ==
            packet["allocation_probes"] == 0 and packet["rf_jobs"] == 11 and
            packet["rf_duration_ns"] == RF_DURATION_NS, "Finite Package 9 budget")
    require(packet["memory_preflight"] == {
        "timeout_seconds": MEMORY_PREFLIGHT_SECONDS,
        "sample_seconds": MEMORY_PREFLIGHT_SAMPLE_SECONDS,
        "minimum_heap_available_bytes": MINIMUM_PREFLIGHT_HEAP_AVAILABLE_BYTES,
        "minimum_inventory_heap_available_bytes":
            MINIMUM_INVENTORY_HEAP_AVAILABLE_BYTES,
        "minimum_connected_heap_available_bytes":
            MINIMUM_CONNECTED_HEAP_AVAILABLE_BYTES,
        "reason": "expire retained WTP response/session memory before the maximum warm-up LOAD",
    }, "Frozen Package 9 memory preflight")
    require(packet["normal_load"] == {
        "cycles": 3, "seconds_per_cycle": NORMAL_SECONDS,
        "browser_intervals_per_cycle": 2, "browser_actions": browser_actions(),
        "production": {"mode": "FSKCW", "message": "?" * 32,
            "base_frequency_hz": 135500, "shift_hz": 5,
            "dot_seconds": 0.2, "event_count": 383,
            "duration_ns": PRODUCTION_DURATION_NS,
            "start_offset_seconds": 90}}, "Frozen Package 9 normal workload")
    require(packet["quiet"] == {"baseline_seconds": BASELINE_QUIET_SECONDS,
            "interleaved_seconds": [INTERLEAVED_QUIET_SECONDS] * 3,
            "final_seconds": FINAL_QUIET_SECONDS,
            "minimum_measured_seconds": 3438}, "Frozen Package 9 quiet schedule")
    require(packet["normalizer_jobs"] == normalizer_jobs(packet["normalizer_seed"]),
            "Frozen Package 9 normalizer")
    require(packet["normalizer_request_timeout_seconds"] ==
            NORMALIZER_REQUEST_TIMEOUT_SECONDS,
            "Frozen normalizer request deadline")
    require(packet["credentials"] == {
        "controller": {"ca": "credentials/controller/client-ca.crt",
                       "cert": "credentials/controller/client.crt",
                       "key": "credentials/controller/client.key"},
        "browser": {"ca": "credentials/browser/client-ca.crt",
                    "cert": "credentials/browser/client.crt",
                    "key": "credentials/browser/client.key"}}, "Frozen credentials")
    names = ["normalizer_seed", "normalizer_session", "normalizer_owner",
             "before_a_session", "before_b_session", "final_a_session",
             "final_b_session"] + [f"usb_observer_session_{index}"
                                   for index in range(1, 4)]
    values = [identity(packet[name], name) for name in names]
    require(isinstance(packet["readiness_sessions"], list) and
            len(packet["readiness_sessions"]) == 4, "Package 9 readiness sessions")
    values.extend(identity(value, "readiness_session")
                  for value in packet["readiness_sessions"])
    require(len(values) == len(set(values)), "Distinct Package 9 identities")
    for name, expected in (("binary", packet["wsprrypi_binary_sha256"]),
                           ("observer", packet["tls_observer_sha256"])):
        path = Path(packet[name])
        require(path.is_file() and digest(path) == expected, "Frozen " + name)
    for name, expected in packet["stage_sha256"].items():
        path = (Path(packet["root"]) / name).resolve()
        require(path.is_relative_to(Path(packet["root"]).resolve()) and
                digest(path) == expected, "Changed staged input")
    return packet


class Journal:
    def __init__(self, path):
        self.stream = path.open("x")
        self.lock = threading.Lock()
        self.sequence = 0

    def emit(self, kind, value):
        with self.lock:
            row = {"sequence": self.sequence, "kind": kind,
                   "monotonic_ns": time.monotonic_ns(), "utc_ns": time.time_ns(),
                   "value": value}
            self.stream.write(json.dumps(row, separators=(",", ":")) + "\n")
            self.stream.flush()
            os.fsync(self.stream.fileno())
            self.sequence += 1
            return row

    def close(self):
        self.stream.close()


def tls_context(root, packet, role, alpn):
    cred = packet["credentials"][role]
    context = ssl.create_default_context(cafile=str(root / cred["ca"]))
    context.minimum_version = context.maximum_version = ssl.TLSVersion.TLSv1_3
    group = packet.get("tls_key_exchange_group")
    if group is not None:
        require(group == "X25519", "Unreviewed TLS key-exchange group")
        context.set_ecdh_curve(group)
    context.load_cert_chain(root / cred["cert"], root / cred["key"])
    context.set_alpn_protocols([alpn])
    return context


class NetworkPeer:
    def __init__(self, root, packet, journal, session):
        self.root, self.packet, self.journal, self.session = root, packet, journal, session
        self.stream = None
        self.decoder = Decoder()
        self.events = []
        self.number = 0

    def connect(self):
        raw = socket.create_connection((ADDRESS, 18443), timeout=
                                       self.packet.get("normalizer_connect_timeout_seconds", 5))
        try:
            self.stream = tls_context(self.root, self.packet, "controller", "wtp/1").wrap_socket(
                raw, server_hostname=HOSTNAME)
        except BaseException:
            raw.close()
            raise
        require(self.stream.selected_alpn_protocol() == "wtp/1" and
                hashlib.sha256(self.stream.getpeercert(binary_form=True)).hexdigest() == PEER_SHA,
                "Authenticated normalizer peer")
        hello = self.ask("HELLO", {"versions": ["WTP/1"],
                         "client_name": "phase11-5-package9-normalizer",
                         "client_version": "1"})
        require(hello["device_id"] == DEVICE and hello["boot_id"] == BOOT,
                "Normalizer HELLO identity")
        caps = self.ask("CAPS")
        require(caps["engine"] == "pio-dma-gp2" and caps["max_events"] == 512,
                "Normalizer capabilities")
        return self

    def close(self):
        if self.stream:
            self.stream.close()
            self.stream = None

    def ask(self, op, body=None):
        self.number += 1
        request = {"type": "request", "protocol": "WTP/1", "session_id": self.session,
                   "request_id": f"{self.number:032x}", "op": op, "body": body or {}}
        wire = frame(json.dumps(request, separators=(",", ":")).encode())
        began = time.monotonic_ns()
        self.journal.emit("normalizer_tx", {"request": request, "wire_sha256":
                          hashlib.sha256(wire).hexdigest(), "bytes": len(wire),
                          "began_monotonic_ns": began})
        self.stream.sendall(wire)
        deadline_seconds = self.packet["normalizer_request_timeout_seconds"]
        deadline = time.monotonic() + deadline_seconds
        while time.monotonic() < deadline:
            self.stream.settimeout(max(.001, deadline - time.monotonic()))
            data = self.stream.recv(4096)
            require(data, "Normalizer WTP EOF")
            self.journal.emit("normalizer_rx", {"op": op, "hex": data.hex()})
            for value in self.decoder.feed(data):
                if value["type"] == "event":
                    require(value["boot_id"] == BOOT, "Normalizer event boot")
                    self.events.append(value)
                    self.journal.emit("normalizer_event", value)
                    continue
                require(value["session_id"] == self.session and
                        value["request_id"] == request["request_id"] and
                        value["op"] == op and value["ok"] is True,
                        "Normalizer response")
                ended = time.monotonic_ns()
                self.journal.emit("normalizer_response", {"session_id": self.session,
                    "request_id": request["request_id"], "op": op,
                    "began_monotonic_ns": began, "ended_monotonic_ns": ended,
                    "deadline_seconds": deadline_seconds})
                return value["body"]
        raise TimeoutError("Normalizer " + op)


def arm_clock_usable(clock):
    state_ok = (clock["state"] == "synchronized" or
                (clock["state"] == "holdover" and
                 int(clock["sync_age_ns"]) <= MAX_HOLDOVER_AGE_NS))
    return (state_ok and clock["leap"] == "normal" and
            int(clock["uncertainty_ns"]) <= 500_000_000)


def wait_for_fresh_clock(peer, journal, label):
    """Leave enough fresh-clock runway for one bounded LOAD before ARM."""
    deadline = time.monotonic() + FRESH_CLOCK_WAIT_SECONDS
    while True:
        clock = peer.ask("GET_CLOCK")
        fresh = (clock["state"] == "synchronized" and clock["leap"] == "normal" and
                 int(clock["uncertainty_ns"]) <= 500_000_000 and
                 int(clock["sync_age_ns"]) <= FRESH_CLOCK_AGE_NS)
        journal.emit("normalizer_clock_readiness", {"label": label, "usable": fresh,
            "state": clock["state"], "leap": clock["leap"],
            "uncertainty_ns": clock["uncertainty_ns"],
            "sync_age_ns": clock["sync_age_ns"]})
        if fresh:
            return clock
        require(time.monotonic() < deadline, "Fresh clock readiness deadline")
        time.sleep(2)


def wait_for_normalizer_readiness(root, packet, journal, session, label="initial",
                                  seconds=READINESS_SECONDS):
    """Prove the fresh AP route and clock without taking RF ownership."""
    deadline = time.monotonic() + seconds
    attempt = 0
    peer = None
    request_number = 0
    while time.monotonic() < deadline:
        attempt += 1
        delay = 2
        try:
            if peer is None:
                peer = NetworkPeer(root, packet, journal, session)
                peer.number = request_number
                peer.connect()
            status = peer.ask("STATUS")
            clock = peer.ask("GET_CLOCK")
            usable = (status["boot_id"] == BOOT and
                      status["output_active"] is False and status["owner_id"] is None and
                      clock["state"] == "synchronized" and clock["leap"] == "normal" and
                      int(clock["uncertainty_ns"]) <= 500_000_000 and
                      int(clock["sync_age_ns"]) <= FRESH_CLOCK_AGE_NS)
            journal.emit("normalizer_network_readiness", {"label": label,
                "attempt": attempt,
                "usable": usable, "state": status["state"],
                "clock_state": clock["state"], "clock_leap": clock["leap"],
                "clock_uncertainty_ns": clock["uncertainty_ns"],
                "clock_sync_age_ns": clock["sync_age_ns"]})
            if usable:
                peer.close()
                return
        except (OSError, TimeoutError) as error:
            journal.emit("normalizer_network_wait", {"attempt": attempt,
                         "error_type": type(error).__name__})
            request_number = peer.number
            peer.close()
            peer = None
            delay = packet.get("normalizer_retry_seconds", 2)
        # A healthy connection with a synchronized but older clock sample must
        # be polled faster than the Pico SNTP cadence.  Reusing the 30-second
        # transport backoff here can alias a roughly 60-second update cadence
        # and miss every <=10-second freshness window.
        time.sleep(min(delay, max(0, deadline - time.monotonic())))
    if peer is not None:
        peer.close()
    raise TimeoutError("Normalizer network/clock readiness deadline")


def resource_gate(info, expected_boot=BOOT, expected_source=SOURCE):
    require(info["device_id"] == DEVICE and info["revision"] == expected_source[:12] and
            info["status"]["boot_id"] == expected_boot and
            info["system_clock_hz"] == 138_000_000 and
            info["status"]["engine"] == "pio-dma-gp2" and info["rf_render_in_ram"] is True,
            "Console identity/configuration")
    require(info["core0_stack_guard_valid"] == info["core1_stack_guard_valid"] == 1 and
            info["core0_stack_fault_status"] == info["core1_stack_fault_status"] == 0 and
            info["core0_stack_used_bytes"] <= 12_288 and
            info["core1_stack_used_bytes"] <= 12_288, "Stack reserve")
    require(int(info["allocator_failures"]) == 0 and info["tls_allocation_failures"] == 0 and
            info["heap_capacity_bytes"] - info["allocator_peak_bytes"] >= 32_768,
            "Heap reserve/failure")
    require(info["fault_stage"] == info["fault_hash"] == info["fault_pc"] ==
            info["fault_status"] == 0 and info["dma_errors"] == 0 and
            info["refill_irq_unpaired"] == 0 and info["refill_invalid_reserves"] == 0 and
            not info["engine_diagnostic"], "Fault/DMA/engine gate")


def console_info_once(journal, label):
    with exclusive_port(Path(str(BASE) + "-if00")) as fd:
        began = time.monotonic_ns()
        info = exchange(fd, b"INFO\n", time.monotonic() + 5,
                        lambda kind, value: journal.emit(
                            "preflight_console_" + kind, value), False)
        ended = time.monotonic_ns()
    resource_gate(info)
    journal.emit("preflight_console_info", {"label": label,
        "began_monotonic_ns": began, "ended_monotonic_ns": ended,
        "heap_available_bytes": info["heap_available_bytes"],
        "heap_allocated_bytes": info["heap_allocated_bytes"],
        "allocator_live_bytes": info["allocator_live_bytes"],
        "tls_allocated_bytes": info["tls_allocated_bytes"],
        "wtp_input_reserved_bytes": info["wtp_input_reserved_bytes"]})
    return info


def wait_for_memory_headroom(packet, journal):
    """Let retained WTP caches expire before any reservation or RF ownership."""
    deadline = time.monotonic() + packet["memory_preflight"]["timeout_seconds"]
    minimum = packet["memory_preflight"]["minimum_heap_available_bytes"]
    sample = packet["memory_preflight"]["sample_seconds"]
    attempt = 0
    while True:
        attempt += 1
        info = console_info_once(journal, f"memory-headroom-{attempt}")
        available = info["heap_available_bytes"]
        journal.emit("memory_headroom", {"attempt": attempt, "available_bytes": available,
            "required_bytes": minimum, "usable": available >= minimum,
            "allocator_failures": info["allocator_failures"],
            "network_wtp_close_reason": info["network_wtp_close_reason"]})
        if available >= minimum:
            return info
        require(time.monotonic() < deadline, "Memory headroom readiness deadline")
        time.sleep(min(sample, max(0, deadline - time.monotonic())))


def wait_for_readiness_session_release(packet, journal):
    """Observe the short readiness TLS session return to its idle allocation."""
    deadline = time.monotonic() + 45
    attempt = 0
    while True:
        attempt += 1
        info = console_info_once(journal, f"readiness-session-release-{attempt}")
        usable = (info["tls_allocated_bytes"] <= 8192 and
                  info["heap_available_bytes"] >=
                  packet["memory_preflight"]["minimum_inventory_heap_available_bytes"])
        journal.emit("readiness_session_release", {"attempt": attempt,
            "tls_allocated_bytes": info["tls_allocated_bytes"],
            "heap_available_bytes": info["heap_available_bytes"], "usable": usable})
        if usable:
            return info
        require(time.monotonic() < deadline, "Readiness TLS session release deadline")
        time.sleep(min(1, max(0, deadline - time.monotonic())))


class ConsoleObserver(threading.Thread):
    def __init__(self, journal, stop, expected_boot=BOOT, expected_source=SOURCE,
                 pause=None):
        super().__init__(name="package9-console")
        self.journal, self.stop, self.failure, self.latest = journal, stop, None, None
        self.expected_boot = expected_boot
        self.expected_source = expected_source
        self.pause = pause
        self.starts = []

    def run(self):
        try:
            with exclusive_port(Path(str(BASE) + "-if00")) as fd:
                due = time.monotonic()
                while not self.stop.is_set():
                    if self.pause is not None and self.pause.is_set():
                        self.stop.wait(.025)
                        # Resume from a fresh cadence instead of trying to
                        # repay deliberately suppressed diagnostic samples.
                        due = time.monotonic()
                        continue
                    now = time.monotonic()
                    if now < due:
                        self.stop.wait(min(.05, due - now))
                        continue
                    began = time.monotonic_ns()
                    info = exchange(fd, b"INFO\n", time.monotonic() + 5,
                                    lambda kind, value: self.journal.emit(
                                        "console_" + kind, value), False)
                    ended = time.monotonic_ns()
                    resource_gate(info, self.expected_boot, self.expected_source)
                    self.starts.append(began)
                    self.latest = info
                    self.journal.emit("console_info", {"began_monotonic_ns": began,
                        "ended_monotonic_ns": ended, "value": info})
                    due += 1
                    require(time.monotonic() - due <= 1, "Console cadence lost")
        except BaseException as error:
            self.failure = f"{type(error).__name__}: {error}"
            self.journal.emit("observer_failure", {"observer": "console", "error": self.failure})
            self.stop.set()


class HostObserver(threading.Thread):
    def __init__(self, journal, stop):
        super().__init__(name="package9-host")
        self.journal, self.stop, self.failure = journal, stop, None
        self.starts = []

    def run(self):
        try:
            due = time.monotonic()
            while not self.stop.is_set():
                now = time.monotonic()
                if now < due:
                    self.stop.wait(min(.1, due - now))
                    continue
                began = time.monotonic_ns()
                require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT,
                        "Host boot changed")
                mem = {line.split(":", 1)[0]: line.split(":", 1)[1].strip()
                       for line in Path("/proc/meminfo").read_text().splitlines()}
                service = subprocess.run([*HOST_SYSTEMCTL, "is-active", "wsprrypi.service"],
                    capture_output=True, text=True, timeout=3)
                self.starts.append(began)
                self.journal.emit("host_health", {"began_monotonic_ns": began,
                    "loadavg": Path("/proc/loadavg").read_text().strip(),
                    "mem_available": mem["MemAvailable"],
                    "installed_service": service.stdout.strip(),
                    "service_returncode": service.returncode})
                due += 5
                require(time.monotonic() - due <= 1, "Host cadence lost")
        except BaseException as error:
            self.failure = f"{type(error).__name__}: {error}"
            self.journal.emit("observer_failure", {"observer": "host", "error": self.failure})
            self.stop.set()


class UsbStatusObserver(threading.Thread):
    def __init__(self, journal, stop, session, cycle, expected_boot=BOOT,
                 observe_clock=False):
        super().__init__(name=f"package9-usb-{cycle}")
        self.journal, self.stop, self.session, self.cycle = journal, stop, session, cycle
        self.failure, self.starts, self.states, self.latest = None, [], set(), None
        self.expected_boot = expected_boot
        self.observe_clock = observe_clock
        self.clock = None
        self.ready = threading.Event()
        self.jobs, self.event_states, self.event_jobs = set(), set(), set()
        self.last_event_id = None

    def consume_events(self, peer):
        """Preserve lifecycle events left pending while a STATUS reply is selected."""
        while peer.pending:
            value = peer.pending.popleft()
            require(value.get("type") == "event"
                    and value.get("boot_id") == self.expected_boot,
                    "USB observer event identity")
            raw_id = value.get("event_id")
            require(isinstance(raw_id, str) and raw_id.isdigit() and
                    str(int(raw_id)) == raw_id and
                    (self.last_event_id is None or int(raw_id) == self.last_event_id + 1),
                    "USB observer event order")
            self.last_event_id = int(raw_id)
            require(value.get("event") in {"JOB_STATE", "OWNER_RELEASED"},
                    "USB observer adverse event")
            self.journal.emit("usb_event", {"cycle": self.cycle, "value": value})
            if value.get("event") == "JOB_STATE":
                state = value["body"]["state"]
                job = value["body"].get("job_id")
                # Preserve adverse terminal events as evidence.  Success
                # validators below still require the complete lifecycle, but
                # an abort/miss/failure must not kill the independent observer
                # before its final authoritative STATUS is recorded.
                require(state in {"loaded", "armed", "running", "complete",
                                  "aborted", "missed", "failed", "empty"} and
                        type(value["body"].get("output_active")) is bool and
                        value["body"]["output_active"] is (state == "running") and
                        ((state == "empty" and job is None) or
                         (state != "empty" and identity(job, "USB event job") == job)),
                        "USB observer lifecycle event")
                self.event_states.add(state)
                if job:
                    self.event_jobs.add(job)

    def run(self):
        try:
            from rf_wtp import WtpPeer
            with exclusive_port(Path(str(BASE) + "-if02")) as fd:
                peer = WtpPeer(fd, session=self.session)
                deadline = time.monotonic() + 90
                attempt = 0
                while True:
                    attempt += 1
                    try:
                        hello = peer.request("HELLO", {"versions": ["WTP/1"],
                            "client_name": f"phase11-5-package9-observer-{self.cycle}",
                            "client_version": "1"}, timeout=5)
                        break
                    except RuntimeError as error:
                        detail = error.args[0] if error.args else None
                        retryable = (isinstance(detail, dict)
                            and detail.get("code") == "BUSY"
                            and detail.get("retryable") is True)
                        if not retryable or time.monotonic() >= deadline:
                            raise
                        self.journal.emit("usb_admission_busy", {
                            "cycle": self.cycle, "attempt": attempt,
                            "remaining_seconds": deadline - time.monotonic(),
                        })
                        self.stop.wait(min(5, max(0, deadline - time.monotonic())))
                        require(not self.stop.is_set(),
                                "USB observer stopped during admission")
                require(hello["device_id"] == DEVICE
                        and hello["boot_id"] == self.expected_boot,
                        "USB observer identity")
                due = time.monotonic()
                while not self.stop.is_set():
                    now = time.monotonic()
                    if now < due:
                        self.stop.wait(min(.1, due - now))
                        continue
                    began = time.monotonic_ns()
                    if self.observe_clock:
                        self.clock = peer.request("GET_CLOCK", {}, timeout=5)
                        self.journal.emit("usb_clock", {
                            "cycle": self.cycle, "value": self.clock,
                        })
                    status = peer.request("STATUS", {}, timeout=5)
                    self.consume_events(peer)
                    ended = time.monotonic_ns()
                    require(status["boot_id"] == self.expected_boot,
                            "USB observer boot")
                    self.starts.append(began)
                    self.states.add(status["state"])
                    if status.get("job_id"):
                        self.jobs.add(status["job_id"])
                    self.latest = status
                    self.ready.set()
                    self.journal.emit("usb_status", {"cycle": self.cycle,
                        "began_monotonic_ns": began, "ended_monotonic_ns": ended,
                        "value": status})
                    due += 5
                    require(time.monotonic() - due <= 1, "USB STATUS cadence lost")
        except BaseException as error:
            self.failure = f"{type(error).__name__}: {error}"
            self.ready.set()
            self.journal.emit("observer_failure", {"observer": "usb-status",
                              "cycle": self.cycle, "error": self.failure})
            self.stop.set()


def validate_usb_lifecycle(observer, job_id):
    """Combine advisory USB events with authoritative periodic STATUS state."""
    latest = observer.latest or {}
    records = latest.get("terminal_records", [])
    terminal = [record for record in latest.get("terminal_records", [])
                if record.get("job_id") == job_id]
    require({"armed", "running"}.issubset(observer.states) and
            observer.states <= {"empty", "loaded", "armed", "running", "complete"} and
            observer.jobs == {job_id} and
            observer.event_states == {"loaded", "armed", "running", "complete", "empty"} and
            observer.event_jobs == {job_id} and
            latest.get("state") == "empty" and latest.get("owner_id") is None and
            latest.get("output_active") is False and len(records) == 8 and
            all(record.get("state") == "complete" and
                record.get("output_active") is False for record in records) and
            len(terminal) == 1 and
            terminal[0].get("state") == "complete" and
            terminal[0].get("output_active") is False,
            "USB lifecycle/terminal authority")
    return {"status_states": sorted(observer.states),
            "event_states": sorted(observer.event_states),
            "terminal_records": len(latest["terminal_records"])}


def inventory(root, packet, label, serial, device, session):
    path = root / f"{label}.jsonl"
    error = root / f"{label}.stderr"
    command = ["python3", str(root / "scripts/phase11_5_inventory.py"),
               "--serial", serial, "--device-id", device, "--session-id", session, "--run"]
    with path.open("xb") as out, error.open("xb") as err:
        result = subprocess.run(command, stdout=out, stderr=err, timeout=65)
    require(result.returncode == 0, label + " inventory")
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    found = [row["value"] for row in rows if row["kind"] == "finish"]
    require(len(found) == 1 and found[0]["result"] == "READ_ONLY_INVENTORY",
            label + " inventory finish")
    return found[0]


def run_normalizers(root, packet, journal):
    peer = NetworkPeer(root, packet, journal, packet["normalizer_session"]).connect()
    try:
        initial = peer.ask("STATUS")
        require(initial["boot_id"] == BOOT and initial["output_active"] is False and
                initial["owner_id"] is None, "Normalizer initial authority")
        connected_info = console_info_once(journal, "normalizer-connected")
        require(connected_info["heap_available_bytes"] >=
                packet["memory_preflight"]["minimum_connected_heap_available_bytes"],
                "Connected normalizer LOAD headroom")
        completed = []
        for index, job in enumerate(packet["normalizer_jobs"]):
            event_start = len(peer.events)
            wait_for_fresh_clock(peer, journal, f"warmup-{index}")
            peer.ask("CLAIM", {"owner_id": packet["normalizer_owner"], "lease_ms": 60000})
            loaded = peer.ask("LOAD", job)
            require(loaded["job_id"] == job["job_id"] and len(loaded["adjustments"]) == 512,
                    "Normalizer LOAD")
            clock = peer.ask("GET_CLOCK")
            require(arm_clock_usable(clock), "Normalizer clock")
            target = ((int(clock["utc_now_ns"]) + NORMALIZER_ARM_LEAD_NS +
                       999_999_999) // 1_000_000_000) * 1_000_000_000
            peer.ask("ARM", {"job_id": job["job_id"], "start_utc_ns": str(target),
                     "max_start_uncertainty_ns": "500000000"})
            states = set()
            deadline = time.monotonic() + 25
            final = None
            while time.monotonic() < deadline:
                status = peer.ask("STATUS")
                states.add(status["state"])
                if status["state"] == "complete":
                    final = status
                    break
                # Warm-up STATUS has no cadence requirement. One request per
                # second leaves the local scheduler ample time to launch while
                # the same connection queues authoritative lifecycle events.
                time.sleep(1)
            states.update(event["body"]["state"] for event in peer.events[event_start:]
                          if event["event"] == "JOB_STATE" and
                          event["body"].get("job_id") == job["job_id"])
            require(final is not None and "loaded" in states and "armed" in states and
                    "running" in states and
                    final["output_active"] is False and final["job_id"] == job["job_id"],
                    "Normalizer lifecycle")
            peer.ask("RELEASE")
            released = peer.ask("STATUS")
            require(released["owner_id"] is None and released["output_active"] is False,
                    "Normalizer release")
            completed.append(job["job_id"])
            journal.emit("normalizer_complete", {"index": index, "job_id": job["job_id"],
                         "states": sorted(states), "terminal_records": released["terminal_records"]})
        require(len(released["terminal_records"]) == 8 and
                {record["job_id"] for record in released["terminal_records"]} == set(completed) and
                all(record["state"] == "complete" and not record["output_active"]
                    for record in released["terminal_records"]), "Normalized terminals")
        return released
    finally:
        peer.close()


def write_production_ini(root, packet, cycle, target_utc_ns):
    config = configparser.ConfigParser(interpolation=None, strict=True)
    config.optionxform = str
    base = root / "production-base.ini"
    require(config.read(base) == [str(base)], "Production base INI")
    config.set("Operation", "Mode", "FSKCW")
    config.set("Operation", "Transmit", "true")
    config.set("Operation", "Transmit Backend", "wtp")
    config.set("Operation", "Enable on Boot", "Follow")
    config.set("Operation", "Use LED", "false")
    config.set("Operation", "Use Amp", "false")
    config.set("Operation", "Use Shutdown", "false")
    config.set("Operation", "Web Port", str(31420 + cycle))
    config.set("Operation", "Socket Port", str(31520 + cycle))
    config.set("Experimental", "Allow Unqualified Frequency", "true")
    config.set("Experimental", "Allow Non-Amateur Frequency", "true")
    config.set("CW", "Message", "?" * 32)
    config.set("CW", "Base Frequency", "135500")
    config.set("CW", "Shift Hz", "5")
    config.set("CW", "Dot Seconds", "0.2")
    config.set("CW", "Intra Element Gap", "1")
    config.set("CW", "Inter Character Gap", "3")
    config.set("CW", "Inter Word Gap", "7")
    config.set("CW", "Fade Shape", "none")
    config.set("CW", "Repeat Minutes", "60")
    when = time.gmtime(target_utc_ns // 1_000_000_000)
    config.set("CW", "Start Minute", str(when.tm_min))
    config.set("CW", "Start Second", str(when.tm_sec))
    controller = root / "credentials/controller"
    for key, value in (("Transport", "network"), ("Hostname", HOSTNAME),
                       ("TCP Port", "18443"), ("TLS Server Identity", HOSTNAME),
                       ("TLS CA File", str(controller / "client-ca.crt")),
                       ("TLS Client Certificate", str(controller / "client.crt")),
                       ("TLS Client Key", str(controller / "client.key")),
                       ("Device ID", DEVICE), ("Start Uncertainty ns", "500000000"),
                       ("Allow Frequency Adjustment", "true"), ("Endpoint", "")):
        config.set("WTP", key, value)
    path = root / f"production-{cycle}.ini"
    with path.open("x") as stream:
        config.write(stream)
        stream.flush()
        os.fsync(stream.fileno())
    return path


def host_status(port, journal, cycle):
    import urllib.request
    began = time.monotonic_ns()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(f"http://127.0.0.1:{port}/api/v1/status", timeout=3) as response:
        raw = response.read(131073)
    require(len(raw) <= 131072, "Production host status size")
    value = json.loads(raw)
    journal.emit("production_host_status", {"cycle": cycle,
                 "began_monotonic_ns": began, "value": value})
    return value


def browser_get(root, packet, journal, cycle, path):
    began = time.monotonic_ns()
    deadline = time.monotonic() + 15
    with socket.create_connection((ADDRESS, 18443), timeout=15) as raw:
        with tls_context(root, packet, "browser", "http/1.1").wrap_socket(
                raw, server_hostname=HOSTNAME) as stream:
            require(stream.selected_alpn_protocol() == "http/1.1" and
                    hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest() == PEER_SHA,
                    "Browser peer")
            connection = http.client.HTTPConnection(HOSTNAME)
            connection.sock = stream
            connection.request("GET", path, headers={"Host": f"{HOSTNAME}:18443",
                               "Connection": "close"})
            response = connection.getresponse()
            body = response.read(131073)
            headers = dict(response.getheaders())
            status = response.status
    require(status == 200 and len(body) <= 131072 and time.monotonic() <= deadline,
            "Browser request")
    parsed = None
    if path.startswith("/api/"):
        parsed = json.loads(body)
        if path == "/api/v1/status":
            require(parsed["job"]["boot_id"] == BOOT, "Browser status boot")
    journal.emit("browser_get", {"cycle": cycle, "path": path,
        "began_monotonic_ns": began, "ended_monotonic_ns": time.monotonic_ns(),
        "status": status, "content_type": headers.get("Content-Type"),
        "body_bytes": len(body), "body_sha256": hashlib.sha256(body).hexdigest(),
        "status_state": None if parsed is None or path != "/api/v1/status" else
        parsed["job"]["state"]})


def browser_worker(root, packet, journal, cycle, start, stop, failures):
    try:
        for index, (offset, action, paths) in enumerate(browser_actions()):
            due = start + offset
            while time.monotonic() < due and not stop.is_set():
                stop.wait(min(.1, due - time.monotonic()))
            require(not stop.is_set() and 0 <= time.monotonic() - due <= 15,
                    "Browser action late/stopped")
            began = time.monotonic_ns()
            journal.emit("browser_action_start", {"cycle": cycle, "index": index,
                "offset_seconds": offset, "action": action, "paths": paths,
                "scheduled_monotonic_ns": int(due * 1e9)})
            for path in paths:
                browser_get(root, packet, journal, cycle, path)
            require(time.monotonic_ns() - began <= 60_000_000_000, "Browser action deadline")
            journal.emit("browser_action_finish", {"cycle": cycle, "index": index,
                         "action": action})
    except BaseException as error:
        failures.append(f"browser-{cycle}: {type(error).__name__}: {error}")
        journal.emit("worker_failure", {"worker": "browser", "cycle": cycle,
                     "error": failures[-1]})
        stop.set()


def production_lifecycle(last, states, owners, jobs, sessions):
    """Validate WsprryPi handoff and its completed report after release.

    The live remote state can move directly from Running to Empty when
    WsprryPi observes completion and releases ownership between five-second
    host samples. Completion is authoritative in last_report and is also
    checked independently by the USB observer.
    """
    report = (last or {}).get("last_report") or {}
    # LOAD and ARM are adjacent controller operations. A five-second host API
    # sample can therefore observe ARM without ever sampling the transient
    # Loaded state. Require the durable handoff states here; the independent
    # USB event stream proves transient lifecycle and USB STATUS proves the
    # retained terminal record.
    require(last is not None and {"armed", "running"}.issubset(states) and
            len(owners) == len(jobs) == len(sessions) == 1 and
            report.get("outcome") == "complete" and report.get("job_id") in jobs and
            report.get("arm_handed_off") is True and
            report.get("job", {}).get("state") == "complete" and
            report["job"].get("output_active") is False and
            report["job"].get("device_output_active") is False,
            "Production lifecycle")
    return report


def run_normal_cycle(root, packet, journal, cycle, observer_stop):
    require(not observer_stop.is_set(), "Long observer failed before normal cycle")
    wait_for_normalizer_readiness(root, packet, journal,
                                  packet["readiness_sessions"][cycle], f"cycle-{cycle}",
                                  FRESH_CLOCK_WAIT_SECONDS)
    require(not observer_stop.is_set(), "Long observer failed during cycle readiness")
    target_utc_ns = ((time.time_ns() + 120_000_000_000 + 999_999_999) //
                     1_000_000_000) * 1_000_000_000
    ini = write_production_ini(root, packet, cycle, target_utc_ns)
    n_start_utc_ns = target_utc_ns - 90_000_000_000
    production_start_utc_ns = target_utc_ns - 25_000_000_000
    port = 31420 + cycle
    process = None
    stop = threading.Event()
    failures = []
    usb = UsbStatusObserver(journal, stop, packet[f"usb_observer_session_{cycle}"], cycle)
    log = root / f"production-{cycle}.log"
    tls = root / f"production-{cycle}-tls.bin"
    try:
        with log.open("xb") as output:
            start = time.monotonic() + (n_start_utc_ns - time.time_ns()) / 1e9
            require(15 <= start - time.monotonic() <= 35, "Production setup timing")
            while time.monotonic() < start and not observer_stop.is_set():
                observer_stop.wait(min(.1, start - time.monotonic()))
            require(not observer_stop.is_set(), "Long observer failed before normal start")
            journal.emit("normal_begin", {"cycle": cycle, "start_monotonic_ns":
                         int(start * 1e9), "target_utc_ns": target_utc_ns})
            usb.start()
            browser = threading.Thread(target=browser_worker,
                args=(root, packet, journal, cycle, start, stop, failures),
                name=f"package9-browser-{cycle}")
            browser.start()
            end = start + NORMAL_SECONDS
            health_due = start
            launch = time.monotonic() + (production_start_utc_ns - time.time_ns()) / 1e9
            require(60 <= launch - start <= 70, "Production launch offset")
            while (time.monotonic() < launch and not stop.is_set() and
                   not observer_stop.is_set()):
                if time.monotonic() >= health_due:
                    journal.emit("production_process_health", {"cycle": cycle,
                        "began_monotonic_ns": time.monotonic_ns(),
                        "state": "not_started", "pid": None, "returncode": None})
                    health_due += 5
                stop.wait(.05)
            require(not stop.is_set() and not observer_stop.is_set() and
                    not failures and usb.failure is None,
                    "Normal workers before production")
            environment = dict(os.environ, LD_PRELOAD=packet["observer"],
                               PHASE115_TLS_LOG=str(tls))
            if packet.get("production_openssl") is not None:
                openssl = (root / packet["production_openssl"]).resolve(strict=True)
                require(openssl.is_relative_to(root.resolve()), "Production OpenSSL config path")
                environment["OPENSSL_CONF"] = str(openssl)
            process = subprocess.Popen([packet["binary"], "--backend", "wtp", "-i", str(ini),
                "--socket-loopback-only", "--socket-loopback-family", "ipv4",
                "--allow-unqualified-frequency", "--allow-non-amateur-frequency"],
                cwd=root, stdout=output, stderr=subprocess.STDOUT,
                env=environment)
            journal.emit("production_start", {"cycle": cycle, "pid": process.pid,
                "target_utc_ns": target_utc_ns, "ini_sha256": digest(ini)})
            deadline = min(time.monotonic() + 12,
                           time.monotonic() + (target_utc_ns - 10_000_000_000 -
                                               time.time_ns()) / 1e9)
            status = None
            while (time.monotonic() < deadline and not stop.is_set() and
                   not observer_stop.is_set()):
                require(process.poll() is None, "Production exited before readiness")
                if time.monotonic() >= health_due:
                    journal.emit("production_process_health", {"cycle": cycle,
                        "began_monotonic_ns": time.monotonic_ns(), "state": "running",
                        "pid": process.pid, "returncode": process.poll()})
                    health_due += 5
                try:
                    status = host_status(port, journal, cycle)
                except OSError:
                    stop.wait(.05)
                    continue
                identity_value = status.get("host", {}).get("identity")
                if identity_value:
                    require(identity_value["device_id"] == DEVICE and
                            identity_value["boot_id"] == BOOT, "Production identity")
                    break
                stop.wait(.05)
            require(not observer_stop.is_set() and not stop.is_set() and status and
                    status.get("host", {}).get("identity"), "Production readiness")
            states = set()
            owners, jobs, sessions = set(), set(), set()
            last = None
            due = time.monotonic()
            while (time.monotonic() < end and not stop.is_set() and
                   not observer_stop.is_set()):
                require(process.poll() is None, "Production process died")
                if time.monotonic() >= health_due:
                    journal.emit("production_process_health", {"cycle": cycle,
                        "began_monotonic_ns": time.monotonic_ns(), "state": "running",
                        "pid": process.pid, "returncode": process.poll()})
                    health_due += 5
                if time.monotonic() >= due:
                    last = host_status(port, journal, cycle)["host"]
                    require(last["identity"]["boot_id"] == BOOT and
                            last["identity"]["device_id"] == DEVICE and
                            not last["recovery_required"] and not last["safety_fault"],
                            "Production health")
                    execution = last.get("execution") or {}
                    report = last.get("last_report") or {}
                    require(not execution.get("faulted", False) and
                            report.get("outcome") != "failed",
                            "Production execution failed")
                    remote = last.get("remote")
                    if remote:
                        states.add(remote["state"])
                        if remote.get("owner_id"):
                            owners.add(remote["owner_id"])
                        if remote.get("job_id"):
                            jobs.add(remote["job_id"])
                    if last.get("session_id"):
                        sessions.add(last["session_id"])
                    due += 5
                stop.wait(.05)
            if observer_stop.is_set():
                stop.set()
            browser.join(20)
            require(not browser.is_alive() and not failures and not stop.is_set() and
                    not observer_stop.is_set(),
                    "Normal workers")
            report = production_lifecycle(last, states, owners, jobs, sessions)
            journal.emit("normal_finish", {"cycle": cycle, "states": sorted(states),
                "owner_id": next(iter(owners)), "job_id": next(iter(jobs)),
                "session_id": next(iter(sessions)), "last_report": report})
            stop.set()
            usb.join(10)
            require(not usb.is_alive() and usb.failure is None,
                    "USB observer completion/cadence")
            usb_evidence = validate_usb_lifecycle(usb, next(iter(jobs)))
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=12)
            require(process.returncode == 0, "Production clean exit")
            process = None
            return {"cycle": cycle, "job_id": next(iter(jobs)),
                    "owner_id": next(iter(owners)), "session_id": next(iter(sessions)),
                    "states": sorted(states),
                    "usb_states": usb_evidence["status_states"],
                    "usb_event_states": usb_evidence["event_states"],
                    "usb_terminal_records": usb_evidence["terminal_records"],
                    "ini_sha256": digest(ini), "tls_sha256": digest(tls),
                    "target_utc_ns": target_utc_ns}
    finally:
        stop.set()
        if usb.is_alive():
            usb.join(10)
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def quiet(journal, console, label, seconds):
    ready_deadline = time.monotonic() + 6
    while console.latest is None and console.failure is None and time.monotonic() < ready_deadline:
        time.sleep(.02)
    require(console.latest is not None and console.failure is None,
            "Console unavailable before quiet")
    began = time.monotonic_ns()
    journal.emit("quiet_begin", {"label": label, "seconds": seconds})
    deadline = began / 1e9 + seconds
    while time.monotonic() < deadline:
        require(console.failure is None, "Console failed during quiet")
        time.sleep(min(.2, deadline - time.monotonic()))
    require(time.monotonic_ns() - began >= seconds * 1_000_000_000,
            "Quiet interval shortened")
    info = console.latest
    resource_gate(info)
    window = {"label": label, "seconds": seconds,
        "began_monotonic_ns": began, "ended_monotonic_ns": time.monotonic_ns(),
        "heap_allocated_bytes": info["heap_allocated_bytes"],
        "allocator_live_bytes": int(info["allocator_live_bytes"]),
        "allocator_peak_bytes": int(info["allocator_peak_bytes"]),
        "heap_capacity_bytes": info["heap_capacity_bytes"],
        "core0_stack_used_bytes": info["core0_stack_used_bytes"],
        "core1_stack_used_bytes": info["core1_stack_used_bytes"],
        "max_refill_irq_to_ready_ns": int(info["max_refill_irq_to_ready_ns"]),
        "rf_max_service_gap_ns": int(info["rf_max_service_gap_ns"]),
        "min_data_successor_ready_words": info["min_data_successor_ready_words"],
        "min_tail_successor_ready_words": info["min_tail_successor_ready_words"],
        "launch_epoch": int(info["launch_epoch"]), "dma_errors": info["dma_errors"],
        "output_active": info["status"]["output_active"],
        "owner_state": info["status"]["state"]}
    require(window["output_active"] is False, "Quiet output active")
    journal.emit("resource_window", window)
    return window


def _run_with_service_paused(root, packet, journal):
    wait_for_memory_headroom(packet, journal)
    wait_for_normalizer_readiness(root, packet, journal,
                                  packet["readiness_sessions"][0])
    wait_for_readiness_session_release(packet, journal)
    before_a = inventory(root, packet, "before-a", SERIAL, DEVICE, packet["before_a_session"])
    before_b = inventory(root, packet, "before-b", B_SERIAL, B_DEVICE, packet["before_b_session"])
    require(before_a["info"]["revision"] == SOURCE[:12] and
            before_a["wtp"]["STATUS"]["boot_id"] == BOOT and
            before_b["wtp"]["STATUS"]["boot_id"] == B_BOOT and
            before_a["info"]["heap_available_bytes"] >=
                packet["memory_preflight"]["minimum_inventory_heap_available_bytes"],
            "Preflight identity/headroom")
    reservation = Reservation(digest(root / "packet.json"))
    reservation.acquire({"a": before_a, "b": before_b})
    journal.emit("reservation_acquired", json.loads(reservation.path.read_text()))
    console_stop = threading.Event()
    console = ConsoleObserver(journal, console_stop)
    host = HostObserver(journal, console_stop)
    cycles, windows = [], []
    final_values = None
    capture = None
    capture_output = None
    try:
        capture_output = (root / "campaign-capture.log").open("xb")
        capture = subprocess.Popen(["tcpdump", "--immediate-mode", "-i", "wlan2", "-U",
            "-s", "0", "-w", str(root / "campaign.pcap"),
            "tcp port 18443 or arp or udp port 123 or udp port 5353"],
            stdout=capture_output, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 5
        while not (root / "campaign.pcap").exists() and time.monotonic() < deadline:
            time.sleep(.05)
        require((root / "campaign.pcap").exists() and capture.poll() is None,
                "Campaign capture did not start")
        journal.emit("capture_started", {"pid": capture.pid})
        # Serialize maximum LOADs with Console INFO construction. Both have
        # independent bounds, but overlap would consume the headroom under test.
        normalizer = run_normalizers(root, packet, journal)
        console.start()
        host.start()
        windows.append(quiet(journal, console, "post-warmup-baseline", BASELINE_QUIET_SECONDS))
        for cycle in range(1, 4):
            cycles.append(run_normal_cycle(root, packet, journal, cycle, console_stop))
            windows.append(quiet(journal, console, f"post-n{cycle}",
                                 INTERLEAVED_QUIET_SECONDS))
        windows.append(quiet(journal, console, "final-q", FINAL_QUIET_SECONDS))
        console_stop.set()
        console.join(10)
        host.join(10)
        require(not console.is_alive() and not host.is_alive() and
                console.failure is None and host.failure is None, "Long observers")
        final_a = inventory(root, packet, "final-a", SERIAL, DEVICE, packet["final_a_session"])
        final_b = inventory(root, packet, "final-b", B_SERIAL, B_DEVICE, packet["final_b_session"])
        final_values = {"a": final_a, "b": final_b}
        final_status = final_a["wtp"]["STATUS"]
        require(final_status["boot_id"] == BOOT and final_status["owner_id"] is None and
                final_status["output_active"] is False and
                len(final_status["terminal_records"]) == 8 and
                all(record["state"] == "complete" and not record["output_active"]
                    for record in final_status["terminal_records"]), "Final terminal/authority")
        baseline = windows[0]["heap_allocated_bytes"]
        posts = [window["heap_allocated_bytes"] for window in windows[1:4]]
        require(all(abs(value - baseline) <= 1024 for value in posts) and
                max(posts) - min(posts) <= 1024 and not (posts[0] < posts[1] < posts[2]),
                "R6 matched resource return")
        final_live = windows[4]["heap_allocated_bytes"]
        require(abs(final_live - baseline) <= 1024, "Final Q resource return")
        final_info = final_a["info"]
        require(int(final_info["rf_max_service_gap_ns"]) <= CRITICAL_PATH_NS and
                int(final_info["max_refill_irq_to_ready_ns"]) <= CRITICAL_PATH_NS and
                final_info["refill_full_predecessor"]["measured"] and
                final_info["refill_short_predecessor"]["measured"] and
                final_info["refill_full_predecessor"]["remaining_words"] * 4 >=
                    final_info["refill_full_predecessor"]["total_words"] and
                final_info["refill_short_predecessor"]["remaining_words"] * 4 >=
                    final_info["refill_short_predecessor"]["total_words"] and
                final_info["tail_irqs"] >= 11 and int(final_info["launch_epoch"]) >=
                    int(before_a["info"]["launch_epoch"]) + 11,
                "Final RF timing/path gate")
        result = {"status": "CAPTURED_REQUIRES_AUDIT", "packet_sha256": digest(root / "packet.json"),
            "normalizer_terminal_records": len(normalizer["terminal_records"]),
            "cycles": cycles, "windows": windows, "normal_seconds": 1800,
            "rf_jobs": 11, "rf_duration_ns": RF_DURATION_NS,
            "final_terminal_records": final_status["terminal_records"],
            "console_samples": len(console.starts), "host_samples": len(host.starts),
            "final_metrics": {key: final_info[key] for key in (
                "allocator_peak_bytes", "heap_capacity_bytes", "core0_stack_used_bytes",
                "core1_stack_used_bytes", "rf_max_service_gap_ns",
                "max_refill_irq_to_ready_ns", "min_data_successor_ready_words",
                "min_tail_successor_ready_words", "dma_errors", "tail_irqs", "launch_epoch")}}
        (root / "campaign-result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        console_stop.set()
        if console.is_alive():
            console.join(10)
        if host.is_alive():
            host.join(10)
        if capture is not None and capture.poll() is None:
            capture.send_signal(signal.SIGINT)
            try:
                capture.wait(timeout=15)
            except subprocess.TimeoutExpired:
                capture.terminate()
                capture.wait(timeout=5)
        if capture_output is not None:
            capture_output.close()
        if capture is not None:
            journal.emit("capture_stopped", {"exit": capture.returncode,
                "pcap_bytes": (root / "campaign.pcap").stat().st_size
                    if (root / "campaign.pcap").exists() else 0})
        if reservation.held and final_values is not None:
            reservation.release(final_values)
            journal.emit("reservation_released", json.loads(reservation.path.read_text()))
        reservation.close()


def run(root, packet, journal):
    """Pause the installed client before the Console-only readiness window."""
    service_was_active = subprocess.run([*HOST_SYSTEMCTL, "is-active", "--quiet",
        "wsprrypi.service"]).returncode == 0
    require(service_was_active, "Installed WsprryPi service baseline")
    subprocess.run([*HOST_SYSTEMCTL, "stop", "wsprrypi.service"], check=True, timeout=15)
    journal.emit("installed_service_paused", {"was_active": True,
        "before_memory_readiness": True})
    try:
        return _run_with_service_paused(root, packet, journal)
    finally:
        subprocess.run([*HOST_SYSTEMCTL, "start", "wsprrypi.service"],
                       check=False, timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no host, network, USB or RF access.")
        return
    require(os.geteuid() == 0 and os.name == "posix", "Linux root required")
    root = args.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077 == 0 and digest(root / "packet.json") ==
            args.packet_sha256, "Private root/packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT,
            "Package 9 root/host")
    require(os.readlink("/proc/self/ns/net") != os.readlink("/proc/1/ns/net") and
            os.readlink("/proc/self/ns/mnt") != os.readlink("/proc/1/ns/mnt"),
            "Package 9 requires the independent client namespaces")
    os.umask(0o077)
    journal = Journal(root / "campaign.jsonl")
    try:
        journal.emit("start", {"packet_sha256": args.packet_sha256})
        result = run(root, packet, journal)
        journal.emit("finish", result)
    except BaseException as error:
        journal.emit("failure", {"type": type(error).__name__, "error": str(error)})
        raise
    finally:
        journal.close()


if __name__ == "__main__":
    main()
