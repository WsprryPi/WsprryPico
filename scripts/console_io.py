"""Bounded local USB Console I/O; no remote execution framing."""
import contextlib
import fcntl
import json
import os
import select
import struct
import termios
import time
from strict_json import unique_object, reject_float, reject_constant, json_depth, validate_unicode



def require(condition, message):
    if not condition:
        raise ValueError(message)


def loads_console(source):
    """Console diagnostics include native uint32 hashes and uint64 counters."""
    def integer(text):
        value = int(text)
        require(-(1 << 63) <= value <= (1 << 64) - 1, 'Console integer exceeds 64-bit range')
        return value
    value = json.loads(source, object_pairs_hook=unique_object, parse_int=integer,
                       parse_float=reject_float, parse_constant=reject_constant)
    require(json_depth(value) <= 16, 'Console JSON nesting exceeds 16')
    validate_unicode(value)
    return value




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



def exchange(fd, data, deadline, emit):
    emit('tx', {'hex': data.hex()})
    pending = data
    received = bytearray()
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError('Console exchange deadline')
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
            require(len(received) <= 131104, 'Oversized inventory response')
        if b'\n' in received:
            require(received.endswith(b'\n'), 'Console framing')
            require(not pending, 'Response before request completed')
            lines = [line for line in received.splitlines() if line]
            require(lines and len(lines) <= 4, 'Console response count')
            # An abruptly stopped observer can leave one complete INFO reply in
            # the CDC queue.  Preserve it and use the last complete line, which
            # is the reply to this request.
            for line in lines[:-1]:
                emit('stale_console_reply', {'hex': line.hex()})
            return loads_console(lines[-1].decode())
