#!/usr/bin/env python3
"""Opt-in three-job USB RF diagnostic, not Phase 11.5 acceptance.

No flashing, clock setting, network configuration, retry, automatic abort or
fault clearing. Run only inside the separately authorized local supervisor.
On failure preserve the finite job and output-unknown state for reconciliation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import select
import struct
import subprocess
import sys
import threading
import time
import uuid

from phase11_5_inventory import exclusive_port, exchange, require
from validate_wtp_contract import SchemaValidator, crc32c, frame, loads_strict


SERIAL = "0BF4B4AEC9FFB344"
DEVICE = "fd6127d11d6aca42a9905fa3fb1bf1d5"
CLOCK = 138000000
DURATION = 10_000_000_000
FREQUENCY = 135500_000_000_000


def validate_packet(packet):
    require(packet["schema"] in ("phase11.5-pilot-v1", "phase11.5-pilot-v2"), "packet schema")
    if packet["schema"] == "phase11.5-pilot-v2":
        require(type(packet.get("rf_render_in_ram")) is bool, "explicit renderer placement")
        require(re.fullmatch(r"[0-9a-f]{40}", packet.get("source_revision", "")) is not None and
                packet["source_revision"][:12] == packet["revision"], "full source identity")
    require(packet["serial"] == SERIAL and packet["device_id"] == DEVICE, "pilot DUT")
    require(type(packet["system_clock_hz"]) is int and packet["system_clock_hz"] == CLOCK,
            "pilot clock")
    require(re.fullmatch(r"[0-9a-f]{12}", packet["revision"]) is not None, "clean revision")
    require(re.fullmatch(r"[0-9a-f]{64}", packet["uf2_sha256"]) is not None, "image hash")
    require(re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
                         packet.get("host_boot_id", "")) is not None, "host boot identity")
    jobs = packet["jobs"]
    require(len(jobs) == 3, "exactly three jobs")
    require(len({job["job_id"] for job in jobs}) == 3, "unique finite jobs")
    for job in jobs:
        require(re.fullmatch(r"[0-9a-f]{32}", job["job_id"]) is not None, "job identity")
        require(job["job_id"] != "0" * 32, "nonzero job identity")
        require(job == dict(job_id=job["job_id"], profile="rf-events/1", mode="tone",
                            total_duration_ns=str(DURATION), allow_frequency_adjustment=True,
                            events=[dict(offset_ns="0", duration_ns=str(DURATION),
                                         rf_on=True, frequency_nhz=str(FREQUENCY))]),
                "pilot job differs from reviewed 135500 Hz / 10-second Tone")
        require(job["allow_frequency_adjustment"] is True and job["events"][0]["rf_on"] is True,
                "pilot boolean fields")


def check_renderer(packet, info):
    # Old frozen v1 packets predate placement telemetry. New campaigns use v2.
    if packet["schema"] == "phase11.5-pilot-v2":
        require(type(info.get("rf_render_in_ram")) is bool and
                info["rf_render_in_ram"] is packet["rf_render_in_ram"], "renderer placement changed")


class Decoder:
    """No resynchronization or silent dropping of corrupt/advisory records."""
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        require(len(self.buffer) <= 131104, "receive buffer bound")
        messages = []
        while len(self.buffer) >= 16:
            magic, version, encoding, flags, size, crc = struct.unpack(
                ">4sBBHII", self.buffer[:16])
            require((magic, version, encoding, flags) == (b"WTPF", 1, 1, 0) and
                    1 <= size <= 65536, "WTP frame header")
            if len(self.buffer) < size + 16:
                break
            payload = bytes(self.buffer[16:size + 16])
            require(crc32c(payload) == crc, "WTP frame CRC")
            messages.append(loads_strict(payload.decode()))
            del self.buffer[:size + 16]
        return messages


class Peer:
    def __init__(self, fd, emit, checkpoint, boot):
        self.fd, self.emit, self.checkpoint = fd, emit, checkpoint
        self.boot = boot
        self.session = uuid.uuid4().hex
        self.decoder = Decoder()
        self.schema = loads_strict((Path(__file__).resolve().parents[1] /
                                    "docs/protocol/wtp-1.schema.json").read_text())
        self.validator = SchemaValidator(self.schema)

    def request(self, operation, body=None):
        self.checkpoint()
        request = dict(type="request", protocol="WTP/1", session_id=self.session,
                       request_id=uuid.uuid4().hex, op=operation, body=body or {})
        require(not self.validator.errors(request, self.schema), "request schema")
        pending = frame(json.dumps(request, separators=(",", ":")).encode())
        self.emit("wtp_tx", dict(request=request, hex=pending.hex()))
        end = time.monotonic() + 5
        while time.monotonic() < end:
            self.checkpoint()
            reads, writes, _ = select.select([self.fd], [self.fd] if pending else [], [], .1)
            if writes:
                try:
                    pending = pending[os.write(self.fd, pending):]
                except BlockingIOError:
                    pass
            if not reads:
                continue
            try:
                data = os.read(self.fd, 4096)
            except BlockingIOError:
                continue
            require(bool(data), "USB EOF; output unknown")
            self.emit("wtp_rx", dict(hex=data.hex()))
            response = None
            for value in self.decoder.feed(data):
                require(not self.validator.errors(value, self.schema), "response/event schema")
                require(value["session_id"] == self.session, "foreign session")
                self.emit("wtp_message", value)
                if value["type"] == "event":
                    require(value["boot_id"] == self.boot, "event boot changed")
                    require(value["event"] not in ("DEVICE_FAULT", "INVALID_FRAME",
                                                  "SESSION_REPLACED", "MISSED_START"),
                            "device/protocol fault event")
                    continue
                require(not pending and response is None and
                        value["request_id"] == request["request_id"] and
                        value["op"] == operation, "unexpected/duplicate response")
                require(value["ok"] is True, f"{operation} rejected: {value.get('error')}")
                response = value["body"]
            if response is not None:
                return response
        raise TimeoutError(f"{operation} response timeout; no automatic retry; output unknown")


def check_status(status, boot, states, job=None, owner=None):
    require(status["boot_id"] == boot and status["state"] in states, "boot/state changed")
    require(type(status["output_active"]) is bool, "missing output authority")
    # Finite tail shutdown can precede foreground retirement of Running.
    require(status["state"] == "running" or not status["output_active"], "output/state mismatch")
    require(status["job_id"] == job and status["owner_id"] == owner, "job/owner changed")


def check_rf_observation(info):
    # Predeclared pilot stop thresholds, not a complete resource acceptance gate.
    for key in ("dma_errors", "refill_invalid_reserves", "exhausted_successor_links",
                "refill_irq_unpaired"):
        require(type(info[key]) is int and info[key] == 0, f"RF observation failure: {key}")
    observations = 0
    for key in ("refill_full_predecessor", "refill_short_predecessor"):
        reserve = info[key]
        if reserve is None:
            continue
        total, remaining = reserve["total_words"], reserve["remaining_words"]
        require(type(total) is int and type(remaining) is int and
                0 < total <= 16384 and 0 <= remaining <= total, "invalid reserve")
        require(remaining * 4 >= total, "less than 25 percent predecessor reserve")
        observations += reserve["observations"]
    require(observations == info["running_successor_links"] == info["refill_irq_pairs"],
            "incomplete running refill coverage")
    # Start-to-start gap includes prior poll: never add max_poll a second time.
    require(0 <= int(info["rf_max_service_gap_ns"]) <= 2849391, "worker service-gap budget")


def run_jobs(peer, jobs, boot, pause, emit):
    for job in jobs:
        owner = uuid.uuid4().hex
        peer.request("CLAIM", dict(owner_id=owner, lease_ms=60000))
        peer.request("LOAD", job)
        check_status(peer.request("STATUS"), boot, {"loaded"}, job["job_id"], owner)
        pause(2)  # Expose Loaded separately to the independent INFO observer.
        clock = peer.request("GET_CLOCK")
        require(clock["state"] == "synchronized" and clock["leap"] == "normal" and
                int(clock["uncertainty_ns"]) <= 500_000_000, "clock admission")
        start = ((int(clock["utc_now_ns"]) + 5_000_000_000 + 999) // 1000) * 1000
        arm = peer.request("ARM", dict(job_id=job["job_id"], start_utc_ns=str(start),
                                       max_start_uncertainty_ns="500000000"))
        emit("armed_job", dict(job=job, requested_start_utc_ns=str(start), response=arm))
        end, seen, saw_active = time.monotonic() + 22, set(), False
        while time.monotonic() < end:
            status = peer.request("STATUS")
            check_status(status, boot, {"armed", "running", "complete"}, job["job_id"], owner)
            seen.add(status["state"])
            saw_active |= status["state"] == "running" and status["output_active"]
            if status["state"] == "complete":
                require(seen == {"armed", "running", "complete"} and saw_active,
                        "missing state/output coverage")
                peer.request("RELEASE")
                check_status(peer.request("STATUS"), boot, {"empty"})
                break
            pause(1)
        else:
            raise TimeoutError("finite job did not confirm completion; output unknown")
        pause(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("--uf2", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    packet = loads_strict(args.packet.read_text())
    validate_packet(packet)
    if not args.run:
        print("Packet valid: three 10-second 135500 Hz Tone jobs; no hardware accessed")
        return
    require(sys.platform.startswith("linux") and os.geteuid() == 0, "run only on wspr5")
    require(args.uf2 and args.evidence, "image and new private evidence directory required")
    require(hashlib.sha256(args.uf2.read_bytes()).hexdigest() == packet["uf2_sha256"], "image hash")
    args.evidence.mkdir(mode=0o700, parents=False, exist_ok=False)
    lock, stop, ready = threading.Lock(), threading.Event(), threading.Event()
    health_ready = threading.Event()
    observed, faults = [], []
    started = time.monotonic()
    with (args.evidence / "events.jsonl").open("x") as log:
        os.chmod(log.name, 0o600)
        sequence = 0

        def emit(kind, value):
            nonlocal sequence
            with lock:
                log.write(json.dumps(dict(sequence=sequence, kind=kind, utc_ns=time.time_ns(),
                                          monotonic_ns=time.monotonic_ns(), value=value)) + "\n")
                log.flush()
                os.fsync(log.fileno())
                sequence += 1

        def checkpoint():
            require(not faults and time.monotonic() - started < 180, "observer/deadline failure")

        def pause(seconds):
            end = time.monotonic() + seconds
            while time.monotonic() < end:
                checkpoint()
                stop.wait(min(.1, end - time.monotonic()))

        def observer():
            try:
                with exclusive_port(Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")) as fd:
                    last = None
                    while not stop.is_set():
                        before = time.monotonic()
                        info = exchange(fd, b"INFO\n", before + 5, emit, False)
                        check_renderer(packet, info)
                        require(info["device_id"] == DEVICE and info["revision"] == packet["revision"]
                                and info["system_clock_hz"] == CLOCK and
                                info["status"]["engine"] == "pio-dma-gp2" and
                                info["status"]["enabled"] is False and
                                info["status"]["last_error"] is None and
                                not info["recovery_boot"], "INFO identity/state")
                        require(not observed or info["status"]["boot_id"] ==
                                observed[0]["status"]["boot_id"], "observer boot changed")
                        require(last is None or before - last <= 2, "INFO coverage gap")
                        emit("info", info)
                        check_rf_observation(info)
                        observed.append(info)
                        last = before
                        ready.set()
                        stop.wait(max(0, before + 1 - time.monotonic()))
                emit("info_finish", dict(samples=len(observed)))
            except Exception as error:
                faults.append(str(error))
                emit("observer_failure", str(error))
                ready.set()

        def health():
            try:
                last = None
                while not stop.is_set():
                    before = time.monotonic()
                    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
                    require(boot == packet["host_boot_id"], "host boot changed")
                    throttle = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True,
                                              text=True, timeout=2, check=True).stdout.strip()
                    require(throttle == "throttled=0x0", "host throttling")
                    require(last is None or before - last <= 6, "host-health coverage gap")
                    emit("host_health", dict(boot_id=boot, throttled=throttle,
                                             loadavg=Path("/proc/loadavg").read_text().strip(),
                                             meminfo=Path("/proc/meminfo").read_text(),
                                             temperature_millidegrees=int(Path(
                                                 "/sys/class/thermal/thermal_zone0/temp").read_text())))
                    last = before
                    health_ready.set()
                    stop.wait(max(0, before + 5 - time.monotonic()))
                emit("host_health_finish", dict(result="STOPPED_BY_SUPERVISOR"))
            except Exception as error:
                faults.append(str(error))
                emit("host_health_failure", str(error))
                health_ready.set()

        emit("start", dict(packet=packet, helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
        thread = threading.Thread(target=observer)
        health_thread = threading.Thread(target=health)
        thread.start()
        health_thread.start()
        try:
            require(ready.wait(6) and health_ready.wait(3), "observer startup deadline")
            checkpoint()
            baseline = observed[0]
            require(baseline["dma_irqs"] == 0 and baseline["alarm_irqs"] == 0 and
                    baseline["status"]["state"] == "empty" and
                    baseline["status"]["output_active"] is False, "fresh idle physical image required")
            boot = baseline["status"]["boot_id"]
            with exclusive_port(Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02")) as fd:
                peer = Peer(fd, emit, checkpoint, boot)
                hello = peer.request("HELLO", dict(versions=["WTP/1"], client_name="phase11-5-pilot", client_version="1"))
                require(hello["device_id"] == DEVICE and hello["boot_id"] == boot, "HELLO identity")
                caps = peer.request("CAPS")
                require(caps["engine"] == "pio-dma-gp2" and "tone" in caps["modes"] and
                        int(caps["max_job_duration_ns"]) >= DURATION and caps["max_events"] >= 1 and
                        any(int(r["minimum_nhz"]) <= FREQUENCY <= int(r["maximum_nhz"])
                            for r in caps["frequency_ranges"]), "CAPS admission")
                check_status(peer.request("STATUS"), boot, {"empty"})
                pause(10)
                run_jobs(peer, packet["jobs"], boot, pause, emit)
                pause(10)
                check_status(peer.request("STATUS"), boot, {"empty"})
            stop.set()
            thread.join(6)
            health_thread.join(3)
            require(not thread.is_alive() and not health_thread.is_alive(), "observer did not finish")
            checkpoint()
            blocks = (CLOCK * 10 + 524287) // 524288
            final = observed[-1]
            require(final["dma_irqs"] == 3 * (blocks + 1) and final["tail_irqs"] == 3 and
                    final["alarm_irqs"] == 3 and final["running_successor_links"] == 3 * (blocks - 1),
                    "missing full-job DMA/launch/tail coverage")
            emit("finish", dict(result="DIAGNOSTIC_COMPLETED_NOT_ACCEPTANCE", boot_id=boot,
                                info_samples=len(observed), output_active=False))
        except Exception as error:
            emit("failure", dict(error=str(error), output="UNKNOWN_UNTIL_AUTHORITATIVE_RECONCILIATION"))
            raise
        finally:
            stop.set()
            thread.join(6)
            health_thread.join(3)


if __name__ == "__main__":
    main()
