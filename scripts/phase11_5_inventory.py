#!/usr/bin/env python3
"""Opt-in serial-bound Phase 11.5 inventory; never submit a mutation."""
import argparse
import contextlib
import fcntl
import hashlib
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

from validate_wtp_contract import SchemaValidator, crc32c, frame, loads_strict
from wtp_monitor import configure_raw


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inventory_session(value):
    if value is None:
        return uuid.uuid4().hex
    require(len(value) == 32 and value != '0' * 32 and
            all(c in '0123456789abcdef' for c in value), 'Invalid logical inventory session')
    return value


def validate_inventory(info, responses, device):
    require(info.get('ok') is True and info.get('device_id') == device, 'Console identity')
    require(set(responses) == {'HELLO', 'CAPS', 'GET_CLOCK', 'STATUS', 'PING'},
            'Incomplete inventory')
    hello, status = responses['HELLO'], responses['STATUS']
    require(hello['device_id'] == device, 'WTP device mismatch')
    require(info['status']['boot_id'] == hello['boot_id'] == status['boot_id'], 'Boot mismatch')
    require(info['status']['engine'] == responses['CAPS']['engine'], 'Engine mismatch')
    require(type(status['output_active']) is bool and
            type(info['status']['output_active']) is bool, 'Missing output authority')
    # This read-only inventory admits active/owned/failed states and records them.
    # Campaign mutation admission is a separate, stricter decision.


@contextlib.contextmanager
def exclusive_port(path):
    observed = subprocess.run(['fuser', str(path)], capture_output=True, timeout=5)
    require(observed.returncode == 1 and not observed.stdout and not observed.stderr,
            'Endpoint occupied or ownership check unavailable')
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.ioctl(fd, termios.TIOCEXCL)
        configure_raw(fd)
        fcntl.ioctl(fd, termios.TIOCMBIS, struct.pack('I', termios.TIOCM_DTR))
        yield fd
    finally:
        try:
            fcntl.ioctl(fd, termios.TIOCMBIC, struct.pack('I', termios.TIOCM_DTR))
        finally:
            try:
                fcntl.ioctl(fd, termios.TIOCNXCL)
            finally:
                os.close(fd)


def exchange(fd, data, deadline, emit, framed):
    emit('tx', {'hex': data.hex()})
    pending, received = data, bytearray()
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError('Inventory exchange deadline')
        read, write, _ = select.select([fd], [fd] if pending else [], [], left)
        if write:
            try:
                pending = pending[os.write(fd, pending):]
            except BlockingIOError:
                pass
        if read:
            try:
                part = os.read(fd, 4096)
            except BlockingIOError:
                continue
            require(bool(part), 'USB EOF')
            emit('rx', {'hex': part.hex()})
            received.extend(part)
            require(len(received) <= 65552, 'Oversized inventory response')
        if not framed and b'\n' in received:
            require(received.endswith(b'\n') and received.count(b'\n') == 1, 'Console framing')
            require(not pending, 'Response before request completed')
            return loads_strict(received.decode().strip())
        if framed and len(received) >= 16:
            magic, version, encoding, flags, size, crc = struct.unpack('>4sBBHII', received[:16])
            require((magic, version, encoding, flags) == (b'WTPF', 1, 1, 0) and
                    1 <= size <= 65536, 'WTP header')
            if len(received) >= 16 + size:
                require(not pending and len(received) == 16 + size, 'WTP framing suffix')
                payload = received[16:]
                require(crc32c(payload) == crc, 'WTP CRC')
                return loads_strict(payload.decode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--device-id', required=True)
    parser.add_argument('--session-id', help='Reuse one explicitly recorded logical administration session')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run:
        parser.error('--run requires explicit USB inventory authorization')
    require(sys.platform.startswith('linux') and os.geteuid() == 0,
            'Run on wspr5 with permission to inspect all endpoint users')
    require(len(args.serial) == 16 and all(c in '0123456789ABCDEF' for c in args.serial),
            'Invalid USB serial')
    require(len(args.device_id) == 32 and all(c in '0123456789abcdef' for c in args.device_id),
            'Invalid device identity')
    session = inventory_session(args.session_id)
    schema = loads_strict((Path(__file__).resolve().parents[1] /
                          'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    sequence = 0

    def emit(kind, value):
        nonlocal sequence
        print(json.dumps(dict(sequence=sequence, kind=kind, utc_ns=time.time_ns(),
                              monotonic_ns=time.monotonic_ns(), serial=args.serial,
                              value=value)), flush=True)
        sequence += 1

    emit('start', {'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    end = time.monotonic() + 60
    try:
        base = '/dev/serial/by-id/usb-WsprryPi_WsprryPico_' + args.serial
        with exclusive_port(Path(base + '-if00')) as fd:
            info = exchange(fd, b'INFO\n', min(end, time.monotonic() + 5), emit, False)
            require(info.get('device_id') == args.device_id, 'Console device mismatch')
            emit('info', info)
        responses = {}
        with exclusive_port(Path(base + '-if02')) as fd:
            for op in ('HELLO', 'CAPS', 'GET_CLOCK', 'STATUS', 'PING'):
                request = dict(type='request', protocol='WTP/1', session_id=session,
                               request_id=uuid.uuid4().hex, op=op,
                               body={'versions': ['WTP/1'], 'client_name': 'phase11-5-inventory',
                                     'client_version': '1'} if op == 'HELLO' else {})
                response = exchange(fd, frame(json.dumps(request, separators=(',', ':')).encode()),
                                    min(end, time.monotonic() + 5), emit, True)
                require(not validator.errors(response, schema), 'WTP schema')
                require(response['type'] == 'response' and response.get('ok') is True and
                        all(response[key] == request[key] for key in ('session_id', 'request_id', 'op')),
                        'WTP response identity/result')
                responses[op] = response['body']
                emit('response', response)
        validate_inventory(info, responses, args.device_id)
        emit('finish', {'result': 'READ_ONLY_INVENTORY', 'info': info, 'wtp': responses})
    except BaseException as error:
        emit('failure', {'type': type(error).__name__, 'message': str(error)})
        raise


if __name__ == '__main__':
    main()
