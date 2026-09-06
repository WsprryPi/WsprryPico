#!/usr/bin/env python3
"""Operate the separately built Pico RF bench over its Commands CDC interface."""
from __future__ import annotations

import argparse
import fcntl
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import select
import struct
import termios
import time

from wtp_monitor import configure_raw
from validate_wtp_contract import unique_object, reject_constant


def finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("Non-finite bench number")
    return value


def decode_response(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                      parse_float=finite_float, parse_constant=reject_constant)


class Serial:
    def __init__(self, port: str, evidence: Path):
        self.fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self.evidence = evidence
        self.buffer = bytearray()
        try:
            fcntl.ioctl(self.fd, termios.TIOCEXCL)
            configure_raw(self.fd)
            fcntl.ioctl(self.fd, termios.TIOCMBIS, struct.pack('I', termios.TIOCM_DTR))
        except BaseException:
            os.close(self.fd)
            raise

    def close(self):
        try:
            fcntl.ioctl(self.fd, termios.TIOCMBIC, struct.pack('I', termios.TIOCM_DTR))
        except OSError as error:
            if error.errno not in (errno.ENXIO, errno.ENODEV, errno.EIO):
                raise
        finally:
            os.close(self.fd)

    def exchange(self, command: str, timeout: float = 5.0) -> dict:
        payload = (command + '\n').encode('ascii')
        if len(payload) > 129 or b'\n' in payload[:-1]:
            raise ValueError('Invalid command')
        deadline = time.monotonic() + timeout
        offset = 0
        with (self.evidence / 'traffic.jsonl').open('a') as log:
            log.write(json.dumps({'utc_ns': time.time_ns(), 'tx': command}) + '\n')
            while offset < len(payload):
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([], [self.fd], [], remaining)[1]:
                    raise TimeoutError('Serial write timed out')
                try:
                    offset += os.write(self.fd, payload[offset:])
                except BlockingIOError:
                    continue
            while b'\n' not in self.buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([self.fd], [], [], remaining)[0]:
                    raise TimeoutError('Serial response timed out')
                try:
                    chunk = os.read(self.fd, 4096)
                except BlockingIOError:
                    continue
                if not chunk:
                    raise ConnectionError('Serial disconnected')
                with (self.evidence / 'rx.bin').open('ab') as raw:
                    raw.write(chunk)
                self.buffer.extend(chunk)
                if len(self.buffer) > 4096:
                    raise ValueError('Oversized response')
            raw, _, rest = self.buffer.partition(b'\n')
            self.buffer = bytearray(rest)
            response = decode_response(raw)
            if not isinstance(response, dict) or type(response.get('ok')) is not bool:
                raise ValueError('Invalid bench response')
            log.write(json.dumps({'utc_ns': time.time_ns(), 'rx': response}) + '\n')
            return response


def execute(serial, command: str, timeout: float, serial_id: str, revision: str, abort_after_s=None) -> dict:
    info = serial.exchange('INFO')
    if (info.get('product') != 'WsprryPico-RFBench' or
            info.get('serial', '').lower() != serial_id.lower() or
            info.get('utc_synchronized') is not False or info.get('revision') != revision):
        raise ValueError('Unexpected firmware or board identity')
    caps = serial.exchange('CAPS')
    if caps.get('interface') != 'pico-rf-bench/1' or caps.get('engine') != 'pio-dma-gp2':
        raise ValueError('Unexpected bench interface')
    if command.startswith('FRAME ') and caps.get('frame') != 'cycle4-162':
        raise ValueError('Firmware does not support the synthetic frame')
    result = {'info_before': info, 'caps': caps, 'command': command, 'completed': False}
    starts_work = command.startswith(('RUN ', 'BENCH ', 'FRAME '))
    try:
        response = serial.exchange(command)
        if not response['ok']:
            raise RuntimeError(str(response))
        deadline = time.monotonic() + timeout
        running_since = None
        aborted = False
        while starts_work and response.get('state') in ('armed', 'running', 'benchmarking'):
            if response.get('state') == 'running':
                if running_since is None:
                    running_since = time.monotonic()
                if abort_after_s is not None and time.monotonic() - running_since >= abort_after_s:
                    response = serial.exchange('STOP')
                    aborted = True
                    break
            if time.monotonic() >= deadline:
                raise TimeoutError('Bench operation timed out')
            time.sleep(0.05)
            response = serial.exchange('STATUS', min(5.0, max(0.01, deadline - time.monotonic())))
            if not response['ok']:
                raise RuntimeError(str(response))
        result['terminal'] = response
        result['intentional_abort'] = aborted
        if abort_after_s is not None and not aborted:
            raise RuntimeError('Run ended before requested abort was exercised')
        if command != 'BOOTSEL':
            result['info_after'] = serial.exchange('INFO')
        result['completed'] = (response.get('state') in ('complete', 'benchmark_complete')
                               if starts_work else response['ok'])
        if aborted:
            result['completed'] = response.get('ok') is True and response.get('state') == 'stopped'
        if starts_work and response.get('output_active') is not False:
            result['completed'] = False
    finally:
        if starts_work:
            # STOP is ordinary job cleanup, including after a partially written RUN.
            result['cleanup'] = serial.exchange('STOP')
            if (result['cleanup'].get('ok') is not True or
                    result['cleanup'].get('output_active') is not False or
                    result['cleanup'].get('state') != 'stopped'):
                raise RuntimeError('Output stop not confirmed')
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port', required=True, help='RFBench Commands CDC path')
    p.add_argument('--serial', required=True, help='Expected Pico USB serial')
    p.add_argument('--revision', required=True, help='Expected firmware build revision')
    p.add_argument('--firmware', required=True, type=Path, help='Exact flashed UF2 for manifest')
    p.add_argument('--output', required=True, type=Path, help='New evidence directory')
    p.add_argument('--abort-after-ms', type=int, choices=range(1, 10001), metavar='1..10000')
    p.add_argument('--timeout', type=float, default=30)
    sub = p.add_subparsers(dest='action', required=True)
    sub.add_parser('status')
    sub.add_parser('stop')
    sub.add_parser('bootloader')
    benchmark = sub.add_parser('benchmark')
    benchmark.add_argument('--blocks', type=int, default=128, choices=range(1, 4097), metavar='1..4096')
    frame = sub.add_parser('frame')
    frame.add_argument('--delay-ms', type=int, choices=range(100, 10001), default=1000, metavar='100..10000')
    run = sub.add_parser('run')
    run.add_argument('--tone', type=int, choices=range(4), default=0)
    run.add_argument('--duration-ms', type=int, choices=range(1, 10001), default=1000, metavar='1..10000')
    run.add_argument('--delay-ms', type=int, choices=range(100, 10001), default=1000, metavar='100..10000')
    return p


def main():
    args = parser().parse_args()
    if args.abort_after_ms is not None and args.action not in ('run', 'frame'):
        raise ValueError('Abort timing applies only to run/frame')
    if not 1 <= args.timeout <= 300:
        raise ValueError('Timeout must be 1..300 seconds')
    digest = hashlib.sha256(args.firmware.read_bytes()).hexdigest()
    command = {'status': 'STATUS', 'stop': 'STOP', 'benchmark': 'BENCH', 'run': 'RUN', 'bootloader': 'BOOTSEL', 'frame': 'FRAME'}[args.action]
    if args.action == 'benchmark':
        command += f' {args.blocks}'
    elif args.action == 'frame':
        command += f' {args.delay_ms}'
        args.timeout = max(args.timeout, 120 + args.delay_ms / 1000)
    elif args.action == 'run':
        command += f' {args.tone} {args.duration_ms} {args.delay_ms}'
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {'firmware_sha256': digest, 'firmware': str(args.firmware.resolve()),
                'expected_serial': args.serial, 'port': args.port, 'command': command,
                'started_utc_ns': time.time_ns(), 'completed': False}
    serial = None
    try:
        serial = Serial(args.port, args.output)
        manifest.update(execute(serial, command, args.timeout, args.serial, args.revision,
                                None if args.abort_after_ms is None else args.abort_after_ms / 1000))
    except BaseException as error:
        manifest['error'] = str(error)
        raise
    finally:
        try:
            if serial:
                serial.close()
        except BaseException as error:
            manifest['completed'] = False
            manifest['close_error'] = str(error)
            raise
        finally:
            manifest['ended_utc_ns'] = time.time_ns()
            (args.output / 'result.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))
    return 0 if manifest['completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
