#!/usr/bin/env python3
"""Explicit USB UTC + WTP client for one finite encoded WSPR job."""
import argparse
import fcntl
import hashlib
import json
import os
import select
import struct
import termios
import time
import uuid
from collections import deque
from pathlib import Path

from validate_wtp_contract import frame
from wtp_monitor import FrameDecoder, configure_raw

GOLDEN37 = ("13220200302213120030232311300200223201230220201213223121020110322221321030323001023231"
            "2023321232223022203021221110310011010221130002210302110202202112323320031202")
SYMBOL_NS_NUMERATOR = 8192 * 1_000_000_000
SYMBOL_NS_DENOMINATOR = 12000


def rounded_ratio(value, numerator, denominator):
    return (value * numerator + denominator // 2) // denominator


def make_job(symbols, frequency_hz):
    if len(symbols) != 162 or any(tone not in "0123" for tone in symbols):
        raise ValueError("symbols must be exactly 162 digits in range 0..3")
    if frequency_hz != 3_570_100:
        raise ValueError("this RF engine image is built for a 3570100 Hz base")
    events = []
    for index, tone in enumerate(symbols):
        begin = rounded_ratio(index, SYMBOL_NS_NUMERATOR, SYMBOL_NS_DENOMINATOR)
        end = rounded_ratio(index + 1, SYMBOL_NS_NUMERATOR, SYMBOL_NS_DENOMINATOR)
        tone_nhz = frequency_hz * 1_000_000_000 + int(tone) * 1_464_843_750
        events.append(dict(offset_ns=str(begin), duration_ns=str(end - begin), rf_on=True,
                           frequency_nhz=str(tone_nhz)))
    body = dict(job_id=hashlib.sha256((symbols + str(frequency_hz)).encode()).hexdigest()[:32],
                profile="rf-events/1", mode="wspr",
                total_duration_ns=str(rounded_ratio(162, SYMBOL_NS_NUMERATOR,
                                                    SYMBOL_NS_DENOMINATOR)), events=events,
                allow_frequency_adjustment=True)
    return body


def open_port(path):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    configure_raw(fd)
    fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack("I", termios.TIOCM_DTR))
    return fd


def write_all(fd, data, deadline):
    while data:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("serial write timeout")
        _, writable, _ = select.select([], [fd], [], remaining)
        if writable:
            data = data[os.write(fd, data):]


def read_line(fd, deadline):
    data = bytearray()
    while time.monotonic() < deadline:
        readable, _, _ = select.select([fd], [], [], deadline - time.monotonic())
        if readable:
            chunk = os.read(fd, 512)
            if not chunk:
                raise ConnectionError("serial device closed")
            data.extend(chunk)
            while b"\n" in data:
                line, _, remainder = data.partition(b"\n")
                data = bytearray(remainder)
                if line.startswith(b"{"):
                    return json.loads(line)
    raise TimeoutError("serial response timeout")


def synchronize(time_fd, host_uncertainty_ns):
    before_mono = time.monotonic_ns()
    before_utc = time.time_ns()
    write_all(time_fd, b"SAMPLE\n", time.monotonic() + 2)
    sample = read_line(time_fd, time.monotonic() + 2)
    after_mono = time.monotonic_ns()
    after_utc = before_utc + (after_mono - before_mono)
    if not sample.get("ok"):
        raise RuntimeError(sample)
    raw_midpoint = (before_utc + after_utc) // 2
    utc_midpoint = (raw_midpoint + 500) // 1000 * 1000
    uncertainty = (after_mono - before_mono + 1) // 2 + host_uncertainty_ns + 500
    device_sample = sample["sample_monotonic_ns"]
    command = f"SET {device_sample} {utc_midpoint} {uncertainty} NORMAL\n".encode()
    write_all(time_fd, command, time.monotonic() + 2)
    result = read_line(time_fd, time.monotonic() + 2)
    if not result.get("ok"):
        raise RuntimeError(result)
    return dict(sample_monotonic_ns=device_sample, utc_ns=utc_midpoint,
                round_trip_ns=after_mono-before_mono, uncertainty_ns=uncertainty,
                device_uncertainty_ns=result["uncertainty_ns"])


class WtpPeer:
    def __init__(self, fd):
        self.fd, self.decoder = fd, FrameDecoder()
        self.session, self.sequence = uuid.uuid4().hex, 0
        self.pending = deque()

    def _receive(self):
        chunk = os.read(self.fd, 4096)
        if not chunk:
            raise ConnectionError("serial device closed")
        for payload in self.decoder.feed(chunk):
            message = json.loads(payload)
            print(json.dumps(message, separators=(",", ":")), flush=True)
            self.pending.append(message)

    def _take_response(self, request_id):
        for index, message in enumerate(self.pending):
            if message.get("type") == "response" and message.get("request_id") == request_id:
                del self.pending[index]
                return message
        return None

    def request(self, operation, body, timeout=8):
        self.sequence += 1
        request_id = f"{self.sequence:032x}"
        value = dict(type="request", protocol="WTP/1", session_id=self.session,
                     request_id=request_id, op=operation, body=body)
        write_all(self.fd, frame(json.dumps(value, separators=(",", ":")).encode()),
                  time.monotonic() + timeout)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self._take_response(request_id)
            if message is not None:
                if not message.get("ok"):
                    raise RuntimeError(message["error"])
                return message["body"]
            readable, _, _ = select.select([self.fd], [], [], deadline-time.monotonic())
            if not readable:
                continue
            self._receive()
        raise TimeoutError(f"{operation} response timeout")

    def next_message(self, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.pending:
                return self.pending.popleft()
            readable, _, _ = select.select([self.fd], [], [], deadline-time.monotonic())
            if not readable:
                continue
            self._receive()
        raise TimeoutError("terminal event timeout")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--time-port", type=Path, required=True)
    parser.add_argument("--wtp-port", type=Path)
    parser.add_argument("--frequency-hz", type=int)
    parser.add_argument("--symbols", default=GOLDEN37)
    parser.add_argument("--start-delay-s", type=float, default=5.0)
    parser.add_argument("--host-uncertainty-ns", type=int, default=1_000_000)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--bootsel", action="store_true",
                        help="request bootloader only after the device confirms RF is inactive")
    parser.add_argument("--info", action="store_true", help="read current device diagnostics")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run is required for clock setting and RF job submission")
    if args.bootsel or args.info:
        time_fd = open_port(args.time_port)
        try:
            write_all(time_fd, b"BOOTSEL\n" if args.bootsel else b"INFO\n",
                      time.monotonic() + 2)
            result = read_line(time_fd, time.monotonic() + 2)
            print(json.dumps(result), flush=True)
            if not result.get("ok"):
                raise RuntimeError(result)
        finally:
            os.close(time_fd)
        return
    if args.wtp_port is None or args.frequency_hz is None:
        parser.error("--wtp-port and --frequency-hz are required for a job")
    if args.start_delay_s < 1 or args.start_delay_s > 9:
        parser.error("--start-delay-s must be between 1 and 9 seconds")
    job = make_job(args.symbols, args.frequency_hz)
    time_fd = open_port(args.time_port)
    wtp_fd = open_port(args.wtp_port)
    try:
        peer = WtpPeer(wtp_fd)
        peer.request("HELLO", dict(versions=["WTP/1"], client_name="rf_wtp",
                                   client_version="1"))
        owner = uuid.uuid4().hex
        peer.request("CLAIM", dict(owner_id=owner, lease_ms=60000))
        job["job_id"] = uuid.uuid4().hex
        peer.request("LOAD", job, timeout=30)
        sync = synchronize(time_fd, args.host_uncertainty_ns)
        print(json.dumps(dict(type="utc_observation", **sync)), flush=True)
        raw_start = time.time_ns() + round(args.start_delay_s * 1_000_000_000)
        start_utc_ns = (raw_start + 500) // 1000 * 1000
        arm = peer.request("ARM", dict(job_id=job["job_id"], start_utc_ns=str(start_utc_ns),
                                       max_start_uncertainty_ns="20000000"))
        print(json.dumps(dict(type="scheduled_job", requested_start_utc_ns=start_utc_ns,
                              job_id=job["job_id"], arm=arm)), flush=True)
        deadline = time.monotonic() + args.start_delay_s + 120
        while time.monotonic() < deadline:
            message = peer.next_message(deadline-time.monotonic())
            if message.get("type") == "event" and message.get("event") == "JOB_STATE":
                state = message["body"]["state"]
                if state in ("loaded", "armed", "running"):
                    continue
                if state != "complete":
                    write_all(time_fd, b"INFO\n", time.monotonic() + 2)
                    print(json.dumps(dict(type="device_diagnostic",
                                          body=read_line(time_fd, time.monotonic() + 2))),
                          flush=True)
                    raise RuntimeError(f"job ended in {state}")
                status = peer.request("STATUS", {})
                if status["state"] != "complete" or status["output_active"]:
                    raise RuntimeError(f"invalid terminal status: {status}")
                print(json.dumps(dict(type="terminal_job", status=status)), flush=True)
                break
        else:
            raise TimeoutError("job did not reach terminal state")
    finally:
        for fd in (wtp_fd, time_fd):
            try:
                fcntl.ioctl(fd, termios.TIOCMBIC, struct.pack("I", termios.TIOCM_DTR))
            finally:
                os.close(fd)


if __name__ == "__main__":
    main()
