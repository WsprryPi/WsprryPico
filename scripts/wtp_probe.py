#!/usr/bin/env python3
"""Opt-in read-only WTP USB smoke probe. Does not load, arm or transmit jobs."""
import argparse
import fcntl
import json
import os
import select
import struct
import termios
import time
import uuid
from pathlib import Path

from validate_wtp_contract import SchemaValidator, frame, load_json, loads_strict
from wtp_monitor import FrameDecoder, configure_raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", type=Path)
    parser.add_argument("--run", action="store_true", help="explicitly perform USB device I/O")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run is required; use only with authorization for this USB smoke test")
    schema = load_json(Path(__file__).resolve().parents[1] / "docs/protocol/wtp-1.schema.json")
    validator = SchemaValidator(schema)
    session = uuid.uuid4().hex
    decoder = FrameDecoder()
    fd = os.open(args.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        configure_raw(fd)
        fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack("I", termios.TIOCM_DTR))
        for op in ["HELLO", "CAPS", "GET_CLOCK", "STATUS", "PING"]:
            rid = uuid.uuid4().hex
            body = {"versions": ["WTP/1"], "client_name": "wtp_probe", "client_version": "1"} if op == "HELLO" else {}
            request = dict(type="request", protocol="WTP/1", session_id=session, request_id=rid, op=op, body=body)
            pending = frame(json.dumps(request, separators=(",", ":")).encode())
            deadline = time.monotonic() + 5
            done = False
            while not done:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"{op}: no complete response within five seconds")
                readable, writable, _ = select.select([fd], [fd] if pending else [], [], remaining)
                if writable:
                    try:
                        pending = pending[os.write(fd, pending):]
                    except BlockingIOError:
                        pass
                if readable:
                    try:
                        data = os.read(fd, 4096)
                    except BlockingIOError:
                        continue
                    if not data:
                        raise ConnectionError("WTP device closed")
                    for payload in decoder.feed(data):
                        response = loads_strict(payload.decode("utf-8"))
                        errors = validator.errors(response, schema)
                        if errors:
                            raise ValueError(errors)
                        print(json.dumps(response, ensure_ascii=False))
                        if response["type"] == "response":
                            if (response["session_id"], response["request_id"], response["op"]) != (session, rid, op):
                                raise ValueError("unexpected response identity")
                            if not response["ok"]:
                                raise ValueError(response["error"])
                            done = True
    finally:
        try:
            fcntl.ioctl(fd, termios.TIOCMBIC, struct.pack("I", termios.TIOCM_DTR))
        finally:
            os.close(fd)


if __name__ == "__main__":
    main()
