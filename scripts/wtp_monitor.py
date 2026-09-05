#!/usr/bin/env python3
"""Monitor a WTP USB CDC byte stream without third-party Python packages."""

from __future__ import annotations

import argparse
import glob
import json
import os
import select
import struct
import sys
import termios
import time
from pathlib import Path

from validate_wtp_contract import crc32c, loads_strict


MAGIC = b"WTPF"
HEADER_SIZE = 16
MAX_PAYLOAD = 65_536
MAX_BUFFER = HEADER_SIZE + MAX_PAYLOAD + 3


def serial_ports() -> list[str]:
    patterns = ("/dev/cu.usbmodem*", "/dev/ttyACM*", "/dev/ttyUSB*")
    return sorted({path for pattern in patterns for path in glob.glob(pattern)})


def configure_raw(fd: int) -> None:
    attributes = termios.tcgetattr(fd)
    attributes[0] = 0
    attributes[1] = 0
    attributes[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attributes[3] = 0
    attributes[4] = termios.B115200
    attributes[5] = termios.B115200
    attributes[6][termios.VMIN] = 0
    attributes[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attributes)


class FrameDecoder:
    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        self.buffer.extend(data)
        payloads: list[bytes] = []
        while True:
            magic = self.buffer.find(MAGIC)
            if magic < 0:
                del self.buffer[:-3]
                break
            if magic:
                del self.buffer[:magic]
            if len(self.buffer) < HEADER_SIZE:
                break
            version, encoding, flags, length, checksum = struct.unpack(">BBHII", self.buffer[4:16])
            if version != 1 or encoding != 1 or flags != 0 or not 1 <= length <= MAX_PAYLOAD:
                print("invalid WTP header; resynchronizing", file=sys.stderr)
                del self.buffer[0]
                continue
            frame_size = HEADER_SIZE + length
            if len(self.buffer) < frame_size:
                break
            payload = bytes(self.buffer[HEADER_SIZE:frame_size])
            del self.buffer[:frame_size]
            if crc32c(payload) != checksum:
                print("invalid WTP CRC-32C; frame discarded", file=sys.stderr)
                continue
            payloads.append(payload)
        if len(self.buffer) > MAX_BUFFER:
            raise RuntimeError("monitor buffer exceeded the WTP frame bound")
        return payloads


def show_payload(payload: bytes) -> None:
    try:
        text = payload.decode("utf-8")
        message = loads_strict(text)
    except (UnicodeDecodeError, ValueError) as error:
        print(f"valid frame with invalid WTP JSON: {error}")
        print(payload.hex())
        return
    print(json.dumps(message, indent=2, ensure_ascii=False))


def monitor(path: Path) -> None:
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        configure_raw(fd)
        decoder = FrameDecoder()
        print(f"Monitoring {path}; press Ctrl-C to stop.")
        while True:
            readable, _, _ = select.select([fd], [], [], 1.0)
            if not readable:
                continue
            data = os.read(fd, 4096)
            if not data:
                time.sleep(0.05)
                continue
            for payload in decoder.feed(data):
                show_payload(payload)
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", nargs="?", type=Path, help="WTP serial device")
    parser.add_argument("--list", action="store_true", help="list candidate serial devices")
    args = parser.parse_args()
    if args.list:
        ports = serial_ports()
        print("\n".join(ports) if ports else "No candidate serial devices found.")
        return 0
    if args.port is None:
        parser.error("provide a serial device or use --list")
    try:
        monitor(args.port)
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
