#!/usr/bin/env python3
"""R3 admission only: prepare, audit, or explicitly run four read-only inventories.

No imports from a flashing, management, network-fixture or RF executor. Preparation
and auditing are hardware-free. A packet hash is an integrity check, not authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from phase11_5_inventory import loads_console, require, validate_inventory
from validate_wtp_contract import crc32c, loads_strict, unique_object, SchemaValidator
import struct

SOURCE = '2e43110f05304efdc2ae25c298baa0ef6426955b'
HOST_BOOT = '220e53ca-ca95-4206-9581-dbe28aa1eeb8'
ROOT = '/home/pi/phase11-5-r3-preflight-20260912'
COUNTS = {'config': 34, 'heap-probe': 6, 'wifi-off': 0, 'wifi-on': 0}
BOARDS = {
    'A': {'serial': '0BF4B4AEC9FFB344', 'device_id': 'fd6127d11d6aca42a9905fa3fb1bf1d5',
          'revision': '802c91a7b86e-dirty', 'prior_boot': '587c672d4267e467649bb43765542284'},
    'B': {'serial': 'CDDBF8767C506C07', 'device_id': '29f20b7342051ef947aa56cb9d4fab42',
          'revision': 'dbf1d86f0885-dirty', 'prior_boot': 'feffcd075ab6cb0b74e7e0c2fde6c87f'},
}
HELPERS = ('scripts/phase11_5_r3_preflight.py', 'scripts/phase11_5_inventory.py',
           'scripts/validate_wtp_contract.py', 'scripts/wtp_monitor.py',
           'docs/protocol/wtp-1.schema.json')
OPERATIONS = ('HELLO', 'CAPS', 'GET_CLOCK', 'STATUS', 'PING')
ORDER = ('before-A', 'before-B', 'after-A', 'after-B')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(), object_pairs_hook=unique_object)


def plan(repo, sessions):
    return {'schema': 'phase11.5-r3-preflight-v1', 'source_revision': SOURCE,
            'root': ROOT, 'host_boot_id': HOST_BOOT, 'boards': BOARDS,
            'sessions': sessions, 'order': list(ORDER), 'runtime_seconds': 300,
            'inventory_seconds': 60, 'management_counts': COUNTS,
            'additional_config_writes': 0, 'additional_heap_probes': 0,
            'rf_jobs': [], 'fixture_activation': False,
            'helper_sha256': {name: digest(repo / name) for name in HELPERS}}


def validate(packet, repo):
    sessions = packet['sessions']
    require(set(sessions) == {'A', 'B'} and len(set(sessions.values())) == 2 and
            all(isinstance(s, str) and re.fullmatch('[0-9a-f]{32}', s) and
                s != '0' * 32 for s in sessions.values()), 'Two distinct nonzero sessions required')
    # Exact equality rejects extensions, truthy substitutions, changed budgets and
    # legacy packet relabeling; canonical JSON also distinguishes bool from int.
    require(json.dumps(packet, sort_keys=True) == json.dumps(plan(repo, sessions), sort_keys=True),
            'Frozen preflight scope or helper identity changed')
    return packet


def decode_frame(data):
    require(len(data) >= 16, 'Truncated WTP header')
    magic, version, encoding, flags, size, crc = struct.unpack('>4sBBHII', data[:16])
    require((magic, version, encoding, flags) == (b'WTPF', 1, 1, 0) and
            0 < size <= 65536 and len(data) == size + 16 and crc32c(data[16:]) == crc,
            'Incomplete, corrupt or extra WTP frame')
    return loads_strict(data[16:].decode())


def audit_inventory(path, board, session, helper_sha):
    schema = loads_strict((Path(__file__).resolve().parents[1] /
                           'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    text = path.read_text()
    require(text.endswith('\n'), 'Truncated inventory envelope')
    rows = [loads_console(line) for line in text.splitlines()]
    require(rows and rows[0]['kind'] == 'start' and rows[-1]['kind'] == 'finish' and
            rows[0]['value'] == {'source_sha256': helper_sha}, 'Inventory boundaries/source')
    require([r['sequence'] for r in rows] == list(range(len(rows))) and
            all(type(r['sequence']) is int and r['serial'] == board['serial'] and
                all(type(r[k]) is int and r[k] >= 0 for k in ('utc_ns', 'monotonic_ns'))
                for r in rows), 'Inventory sequence/serial/timestamps')
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(rows, rows[1:])) and
            rows[-1]['monotonic_ns'] - rows[0]['monotonic_ns'] <= 60_000_000_000,
            'Inventory clock/deadline')
    position = 1
    values = {}
    request_ids = set()
    for op in ('INFO',) + OPERATIONS:
        require(position < len(rows) - 1 and rows[position]['kind'] == 'tx', 'Missing request')
        wire = bytes.fromhex(rows[position]['value']['hex'])
        request = None
        if op == 'INFO':
            require(wire == b'INFO\n', 'Forbidden Console operation')
        else:
            request = decode_frame(wire)
            require(not validator.errors(request, schema), 'Request schema')
            body = {'versions': ['WTP/1'], 'client_name': 'phase11-5-inventory',
                    'client_version': '1'} if op == 'HELLO' else {}
            require(set(request) == {'type', 'protocol', 'session_id', 'request_id', 'op', 'body'} and
                    request['type'] == 'request' and request['protocol'] == 'WTP/1' and
                    request['session_id'] == session and request['op'] == op and request['body'] == body and
                    isinstance(request['request_id'], str) and
                    re.fullmatch('[0-9a-f]{32}', request['request_id']) and
                    request['request_id'] not in request_ids, 'Request mutation, replay or identity')
            request_ids.add(request['request_id'])
        start_ns = rows[position]['monotonic_ns']
        position += 1
        received = bytearray()
        while position < len(rows) - 1 and rows[position]['kind'] == 'rx':
            received.extend(bytes.fromhex(rows[position]['value']['hex']))
            require(len(received) <= 65552, 'Oversized inventory response')
            position += 1
        require(received and position < len(rows) - 1 and
                rows[position]['monotonic_ns'] - start_ns <= 5_000_000_000,
                'Missing response or exchange deadline')
        if op == 'INFO':
            require(received.endswith(b'\n') and received.count(b'\n') == 1, 'Console suffix')
            response = loads_console(received.decode().strip())
            require(rows[position]['kind'] == 'info', 'Missing INFO record')
            values['info'] = response
        else:
            response = decode_frame(received)
            require(not validator.errors(response, schema), 'Response schema')
            require(rows[position]['kind'] == 'response' and response['type'] == 'response' and
                    response['protocol'] == 'WTP/1' and response['ok'] is True and
                    all(response[k] == request[k] for k in ('session_id', 'request_id', 'op')),
                    'Response binding/result')
            values[op] = response['body']
        require(rows[position]['value'] == response, 'Summary differs from raw wire')
        position += 1
    expected = {'result': 'READ_ONLY_INVENTORY', 'info': values.pop('info'), 'wtp': values}
    require(position == len(rows) - 1 and rows[-1]['value'] == expected,
            'Hidden traffic or final summary differs from wire')
    validate_inventory(expected['info'], values, board['device_id'])
    # Reporting an active/faulted board is still useful read-only evidence. Its
    # admission disposition is deliberately separate from capture completeness.
    return expected


def assess(values, packet):
    blockers = []
    boards = {}
    for label, expected in BOARDS.items():
        first, last = values['before-' + label], values['after-' + label]
        for value in (first, last):
            i, s = value['info'], value['wtp']['STATUS']
            if not (i['revision'] == expected['revision'] and
                    i['status']['engine'] == 'inhibited-standalone-simulator' and
                    i['status']['state'] == s['state'] == 'empty' and
                    i['status']['output_active'] is s['output_active'] is False and
                    s['owner_id'] is None and s['job_id'] is None and
                    i['status']['enabled'] is False and i['status']['last_error'] is None and
                    i['status']['storage_healthy'] is True and not i['recovery_boot'] and
                    all(i[k] == 0 for k in ('fault_stage', 'fault_hash', 'fault_pc', 'fault_status'))):
                blockers.append(label + ': unexpected original firmware, state or fault')
        boot = first['wtp']['STATUS']['boot_id']
        if boot != last['wtp']['STATUS']['boot_id']:
            blockers.append(label + ': boot changed during preflight')
        if boot != expected['prior_boot']:
            blockers.append(label + ': between-campaign boot needs operator reconciliation')
        for key in ('configured', 'enabled', 'station', 'schedules', 'watermark_utc_ns'):
            if first['info']['status'][key] != last['info']['status'][key]:
                blockers.append(label + ': visible configuration changed: ' + key)
        if first['wtp']['CAPS'] != last['wtp']['CAPS']:
            blockers.append(label + ': CAPS changed during preflight')
        boards[label] = {'boot_id': boot, 'revision': first['info']['revision'],
                         'caps': first['wtp']['CAPS'], 'final_status': last['wtp']['STATUS']}
    return {'schema': 'phase11.5-r3-preflight-result-v1',
            'status': 'BLOCKED' if blockers else 'READ_ONLY_ADMISSION_CAPTURED',
            'blockers': sorted(set(blockers)), 'boards': boards,
            'management_counts': packet['management_counts'],
            'R3_acceptance_assertions_completed': 0, 'rf_jobs_completed': 0,
            'accepted_configurations': [],
            'limitations': ['Restored inhibited CAPS are not physical candidate CAPS.',
                            'INFO cannot establish private configuration byte parity or journal position.',
                            'Preflight does not authorize flashing, fixture activation or RF.']}


def audit(root, packet):
    intent = read_json(root / 'run-intent.json')
    require(intent['packet_sha256'] == digest(root / 'packet.json') and
            intent['host_boot_id'] == HOST_BOOT and type(intent['started_ns']) is int,
            'Missing run/packet/host binding')
    previous_end = intent['started_ns']
    seen_requests = set()
    for name in ORDER:
        rows = [loads_console(s) for s in (root / (name + '.jsonl')).read_text().splitlines()]
        require(rows and previous_end <= rows[0]['monotonic_ns'] <= rows[-1]['monotonic_ns'] <=
                intent['started_ns'] + packet['runtime_seconds'] * 1_000_000_000,
                'Inventories overlap, are reordered, stale or exceed packet deadline')
        previous_end = rows[-1]['monotonic_ns']
        for row in rows:
            if row['kind'] == 'tx' and bytes.fromhex(row['value']['hex']) != b'INFO\n':
                request = decode_frame(bytes.fromhex(row['value']['hex']))
                identity = request['session_id'], request['request_id']
                require(identity not in seen_requests, 'Cross-inventory request replay')
                seen_requests.add(identity)
    values = {name: audit_inventory(root / (name + '.jsonl'), BOARDS[name[-1]],
                                   packet['sessions'][name[-1]],
                                   packet['helper_sha256']['scripts/phase11_5_inventory.py']) for name in ORDER}
    result = assess(values, packet)
    result['packet_sha256'] = digest(root / 'packet.json')
    result['raw_sha256'] = {name + '.jsonl': digest(root / (name + '.jsonl')) for name in ORDER}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'audit', 'run'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--packet-sha256')
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    if args.action == 'prepare':
        args.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        value = plan(repo, {b: uuid.uuid4().hex for b in BOARDS})
        with (args.root / 'packet.json').open('x') as stream:
            stream.write(json.dumps(value, indent=2) + '\n')
        print(digest(args.root / 'packet.json'))
        return
    packet_path = args.root / 'packet.json'
    require(digest(packet_path) == args.packet_sha256, 'Packet digest mismatch')
    packet = validate(read_json(packet_path), repo)
    if args.action == 'run':
        require(args.run, 'Explicit authorization and --run required for USB inventory')
        require(sys.platform == 'linux' and os.geteuid() == 0 and
                args.root.resolve() == Path(ROOT) and args.root.stat().st_mode & 0o077 == 0,
                'Expected private wspr5 root required')
        require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == HOST_BOOT,
                'Host boot changed')
        # Exclusive creation consumes this packet even if admission or capture fails.
        with (args.root / 'run-intent.json').open('x') as stream:
            json.dump({'packet_sha256': args.packet_sha256, 'host_boot_id': HOST_BOOT,
                       'started_ns': time.monotonic_ns()}, stream)
        os.umask(0o077)
        end = time.monotonic() + packet['runtime_seconds']
        for name in ORDER:
            require(time.monotonic() + 65 < end, 'Preflight time reserve')
            board = BOARDS[name[-1]]
            with (args.root / (name + '.jsonl')).open('x') as out, \
                    (args.root / (name + '.stderr')).open('x') as err:
                subprocess.run([sys.executable, str(repo / 'scripts/phase11_5_inventory.py'),
                                '--serial', board['serial'], '--device-id', board['device_id'],
                                '--session-id', packet['sessions'][name[-1]], '--run'],
                               stdout=out, stderr=err, timeout=65, check=True)
            audit_inventory(args.root / (name + '.jsonl'), board, packet['sessions'][name[-1]],
                            packet['helper_sha256']['scripts/phase11_5_inventory.py'])
            require(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == HOST_BOOT,
                    'Host boot changed during preflight')
    result = audit(args.root, packet)
    with (args.root / 'preflight-result.json').open('x') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'blockers': result['blockers'],
                      'R3_acceptance_assertions_completed': 0}))


if __name__ == '__main__':
    main()
