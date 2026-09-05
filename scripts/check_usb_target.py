#!/usr/bin/env python3
"""Opt-in, read-only CDC isolation/reconnect checks; never load or arm a job."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import select
import struct
import subprocess
import sys
import termios
import time
import uuid

from validate_wtp_contract import SchemaValidator, crc32c, frame, load_json, loads_strict
from wtp_monitor import configure_raw


@contextlib.contextmanager
def port(path):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        configure_raw(fd)
        fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack('I', termios.TIOCM_DTR))
        yield fd
    finally:
        try:
            fcntl.ioctl(fd, termios.TIOCMBIC, struct.pack('I', termios.TIOCM_DTR))
        finally:
            os.close(fd)


def read_for(fd, seconds):
    data = bytearray()
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if select.select([fd], [], [], max(0, deadline - time.monotonic()))[0]:
            try:
                chunk = os.read(fd, 4096)
            except BlockingIOError:
                continue
            if not chunk:
                raise ConnectionError('serial stream closed')
            data.extend(chunk)
            if len(data) > 131072:
                raise ValueError('capture exceeded bound')
    return bytes(data)


def write_all(fd, data):
    deadline = time.monotonic() + 5
    while data:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('serial write')
        if select.select([], [fd], [], remaining)[1]:
            try:
                data = data[os.write(fd, data):]
            except BlockingIOError:
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--console', required=True)
    parser.add_argument('--wtp', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        parser.error('--run requires explicit authorization for target USB I/O')
    if os.path.realpath(args.console) == os.path.realpath(args.wtp):
        parser.error('Console and WTP must be different interfaces')
    args.output.mkdir(parents=True, exist_ok=False)
    schema = load_json(Path(__file__).resolve().parents[1] / 'docs/protocol/wtp-1.schema.json')
    validator = SchemaValidator(schema)
    session = uuid.uuid4().hex
    sequence = 0

    def request(op):
        body = {'versions': ['WTP/1'], 'client_name': 'usb-target-check', 'client_version': '1'} if op == 'HELLO' else {}
        return dict(type='request', protocol='WTP/1', session_id=session,
                    request_id=uuid.uuid4().hex, op=op, body=body)

    def exchange(fd, op, expected_error=None):
        nonlocal sequence
        message = request(op)
        tx = frame(json.dumps(message, separators=(',', ':')).encode())
        write_all(fd, tx)
        rx = read_for(fd, 1)
        sequence += 1
        (args.output / f'{sequence}-{op}-tx.bin').write_bytes(tx)
        (args.output / f'{sequence}-{op}-rx.bin').write_bytes(rx)
        # No resynchronization: reject every stray byte, bad header or suffix.
        if len(rx) < 16 or rx[:4] != b'WTPF':
            raise ValueError('missing frame or unframed WTP bytes')
        version, encoding, flags, length, checksum = struct.unpack('>BBHII', rx[4:16])
        if (version, encoding, flags) != (1, 1, 0) or not 1 <= length <= 65536:
            raise ValueError('invalid header')
        if len(rx) != 16 + length or crc32c(rx[16:]) != checksum:
            raise ValueError('incomplete/extra bytes or invalid CRC')
        response = loads_strict(rx[16:].decode('utf-8'))
        if validator.errors(response, schema):
            raise ValueError('invalid response schema')
        for key in ('protocol', 'session_id', 'request_id', 'op'):
            if response[key] != message[key]:
                raise ValueError('response identity mismatch')
        if response['type'] != 'response':
            raise ValueError('expected response')
        if expected_error:
            if response['ok'] or response['error']['code'] != expected_error:
                raise ValueError('expected ' + expected_error)
        elif not response['ok']:
            raise ValueError(response)
        if op == 'HELLO' and not expected_error:
            if response['body']['device_id'] != console_fields['device_id'] or response['body']['boot_id'] != console_fields['boot_id']:
                raise ValueError('Console/WTP identity mismatch')
        if op == 'STATUS' and not expected_error:
            if response['body']['boot_id'] != console_fields['boot_id'] or response['body']['output_active'] or response['body']['state'] != 'empty':
                raise ValueError('unexpected status or boot identity')
        print(json.dumps(response), flush=True)
        return response

    with port(args.console) as console:
        banner = read_for(console, 1)
        (args.output / 'console.txt').write_bytes(banner)
        text = banner.decode('utf-8')
        console_fields = dict(line.split(': ', 1) for line in text.splitlines() if ': ' in line)
        for expected in ('WsprryPico starting', 'clock: unsynchronized', 'rf_output: false'):
            if expected not in text:
                raise ValueError('incomplete console banner')
        # Exercise the repository probe unchanged, with Console still open.
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('wtp_probe.py')),
                                 args.wtp, '--run'], capture_output=True, text=True, timeout=30)
        (args.output / 'probe.jsonl').write_text(result.stdout)
        (args.output / 'probe.stderr').write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(result.stderr)
        time.sleep(0.2)
        with port(args.wtp) as wtp:
            if read_for(wtp, 0.3):
                raise ValueError('unsolicited/stale WTP bytes on reopen')
            exchange(wtp, 'PING', 'HELLO_REQUIRED')
        time.sleep(0.2)
        with port(args.wtp) as wtp:
            if read_for(wtp, 0.3):
                raise ValueError('stale WTP bytes')
            exchange(wtp, 'HELLO')
            caps = exchange(wtp, 'CAPS')
            clock = exchange(wtp, 'GET_CLOCK')
            status = exchange(wtp, 'STATUS')
            if caps['body']['engine'] != 'inhibited-no-rf' or clock['body']['state'] != 'unsynchronized' or status['body']['output_active']:
                raise ValueError('inhibition/clock mismatch')
            # Leave an incomplete read-only request in the old stream.
            partial = frame(json.dumps(request('PING')).encode())[:19]
            write_all(wtp, partial)
            (args.output / 'partial-tx.bin').write_bytes(partial)
        time.sleep(0.2)
        with port(args.wtp) as wtp:
            if read_for(wtp, 0.3):
                raise ValueError('stale partial-frame response')
            exchange(wtp, 'PING', 'HELLO_REQUIRED')
        time.sleep(0.2)
        with port(args.wtp) as wtp:
            session = uuid.uuid4().hex
            exchange(wtp, 'HELLO')
            exchange(wtp, 'PING')
            if read_for(console, 0.3):
                raise ValueError('WTP exchange leaked into Console')
    # Console close/reopen with WTP held open must only repeat Console banner.
    with port(args.wtp) as wtp:
        with port(args.console) as console:
            repeated = read_for(console, 1)
            (args.output / 'console-reopen.txt').write_bytes(repeated)
            if repeated != banner or read_for(wtp, 0.3):
                raise ValueError('Console reopen isolation failure')
            session = uuid.uuid4().hex
            exchange(wtp, 'HELLO')
            exchange(wtp, 'STATUS')
    print('PASS: read-only probe, strict frames, DTR reconnect, partial-frame reset, Console isolation')


if __name__ == '__main__':
    main()
