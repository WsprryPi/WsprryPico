"""Exact capacity stimulus bytes; pure preparation, no hardware authority."""
import hashlib
import json
import re
import struct

from phase11_5_inventory import require
from validate_wtp_contract import crc32c

MAX_DURATION_NS = 110592000000
FREQUENCY_NHZ = 135500000000000


def identity(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{32}', value)
            and value != '0' * 32, 'Capacity nonzero identity')
    return value


def maximum_job(nonce):
    identity(nonce)
    # Every boundary is an integral 138 MHz sample count: 500 ns = 69 samples.
    boundaries = [(index * MAX_DURATION_NS // (162 * 500)) * 500 for index in range(163)]
    return dict(job_id=hashlib.sha256(('R3-MAX:' + nonce).encode()).hexdigest()[:32],
                profile='rf-events/1', mode='tone', total_duration_ns=str(MAX_DURATION_NS),
                allow_frequency_adjustment=True,
                events=[dict(offset_ns=str(start), duration_ns=str(end - start), rf_on=True,
                             frequency_nhz=str(FREQUENCY_NHZ)) for start, end in zip(boundaries, boundaries[1:])])


def padded_json(value, size):
    raw = json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode()
    require(type(size) is int and len(raw) <= size <= 65537, 'Capacity JSON size')
    return raw + b' ' * (size - len(raw))


def wtp_capacity_frame(session, request, oversized=False):
    size = 65537 if oversized else 65536
    body = dict(type='request', protocol='WTP/1', session_id=identity(session),
                request_id=identity(request), op='STATUS', body={})
    payload = padded_json(body, size)
    return struct.pack('!4sBBHII', b'WTPF', 1, 1, 0, size, crc32c(payload)) + payload


def http_capacity_body(session, request, oversized=False):
    # Browser jobs supports HELLO, not STATUS/PING. HELLO is a valid harmless
    # API operation; padding is outside JSON and does not inflate its WTP body.
    value = dict(session_id=identity(session), request_id=identity(request), operation='HELLO',
                 body=dict(versions=['WTP/1'], client_name='R3-capacity', client_version='1'))
    return padded_json(value, 32769 if oversized else 32768)


def browser_capacity_file(job, oversized=False):
    return padded_json(job, 30001 if oversized else 30000)
