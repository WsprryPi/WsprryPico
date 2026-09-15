"""Audit native-idlej's complete third LOAD without a response and inactive cleanup."""
import json

from audit_phase11_5_idle import frames
from audit_phase11_5_r3_v2_hour import journal, native_wire
from phase11_5_device_management import digest
from phase11_5_inventory import require, loads_console
from phase11_5_load_reply_target import healthy
from phase11_5_pilot_supervisor import configuration
from phase11_5_r3_preflight import audit_inventory
from phase11_5_rf_reservation import BOARDS, inactive
from validate_wtp_contract import SchemaValidator

PACKET = 'e5dc4a0e1563f5c75acc87e95cecedac38dd0140dd71a86b435a78164dbc9329'


def audit(root):
    require(digest(root/'packet.json') == PACKET, 'Exact failed native packet')
    p = json.loads((root/'packet.json').read_text())
    private = json.loads((root/'private-input-hashes.json').read_text())
    for name, sha in p['stage_sha256'].items():
        require((private[name] if name in private else digest(root/name)) == sha, 'Executed input '+name)
    values = {}
    for phase in ('before', 'final'):
        values[phase] = {}
        for b, (serial, device) in BOARDS.items():
            path = root/(phase+'-'+b+'.stdout')
            require(not path.with_suffix('.stderr').read_bytes(), 'Inventory stderr')
            values[phase][b] = audit_inventory(path, dict(serial=serial, device_id=device),
                p['b_session' if b == 'b' else 'inventory_session'],
                p['stage_sha256']['scripts/phase11_5_inventory.py'])
        inactive(values[phase])
        healthy(values[phase]['a']['info'], p['boot_id'], p['source_revision'])
    require([r['job_id'] for r in values['before']['a']['wtp']['STATUS']['terminal_records']] ==
            p['initial_terminal_jobs'], 'Declared retained baseline')
    require(all(configuration(values['before'][b]) == configuration(values['final'][b]) for b in BOARDS)
            and values['before']['b']['wtp']['STATUS'] == values['final']['b']['wtp']['STATUS'],
            'Preserved configuration and B')
    rows = journal(root/'idle.jsonl')
    require(rows[0]['value'] == dict(packet_sha256=PACKET), 'Trace packet')
    schema = json.loads((root/'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    requests = {}; responses = {}; wire = b''; console = b''; decoded = None; began = None
    infos = []; cleanup_commands = []; messages_seen = []
    for row in rows:
        kind, v, stamp = row['kind'], row['value'], row['monotonic_ns']
        if kind == 'usb_tx':
            messages, left = frames(bytes.fromhex(v['hex']))
            require(not left and messages == [v['request']] and not validator.errors(messages[0], schema),
                    'Exact request CRC/schema/summary')
            q = messages[0]
            require(q['request_id'] not in requests and q['op'] != 'ARM', 'Unique requests; no ARM')
            requests[q['request_id']] = dict(q=q, label=v['label'], began=stamp,
                size=len(bytes.fromhex(v['hex'])), written=0)
        elif kind == 'usb_write':
            q, = [x for x in requests.values() if x['label'] == v['label']]
            q['written'] += v['bytes']
            require(v['bytes'] > 0 and v['total_written'] == q['written'] <= q['size'], 'Write accounting')
            q['last_write'] = stamp
        elif kind == 'usb_rx':
            messages, wire = frames(wire + bytes.fromhex(v['hex']))
            messages_seen.extend(messages)
            for m in messages:
                require(not validator.errors(m, schema), 'Response/event schema')
                if m['type'] == 'event':
                    require(m['boot_id'] == p['boot_id'] and m['event'] in ('JOB_STATE','OWNER_RELEASED'), 'Idle event')
                    continue
                q = requests[m['request_id']]
                require(m['request_id'] not in responses and m['ok'] is True and
                        q['written'] == q['size'] and 0 <= stamp-q['began'] <= 5_000_000_000 and
                        all(m[k] == q['q'][k] for k in ('op','request_id','session_id')), 'Full matched exchange')
                responses[m['request_id']] = dict(message=m, ended=stamp)
        elif kind == 'console_tx':
            require(began is None and not console and decoded is None and
                    bytes.fromhex(v['hex']) == b'INFO\n', 'Read-only INFO')
            began = stamp
        elif kind == 'console_rx':
            require(began is not None, 'Solicited INFO bytes')
            console += bytes.fromhex(v['hex'])
            if console.endswith(b'\n'):
                require(console.count(b'\n') == 1 and stamp-began <= 5_000_000_000, 'INFO framing/deadline')
                decoded = loads_console(console.decode().strip()); console = b''; began = None
        elif kind == 'info':
            require(decoded == v['value'], 'Raw INFO agrees')
            healthy(decoded, p['boot_id'], p['source_revision']); infos.append(row); decoded = None
        elif kind == 'cleanup_tx':
            cleanup_commands.append(bytes.fromhex(v['hex']))
    require(not wire and not console and began is None and decoded is None and
            messages_seen == [r['value']['message'] for r in rows if r['kind'] == 'usb_message'],
            'Complete observations')
    expected = ['HELLO','CLAIM','LOAD','ABORT','RELEASE','STATUS','CLAIM','LOAD','ABORT','RELEASE',
                'STATUS','CLAIM','LOAD','HELLO','CLAIM','RELEASE']
    require([r['q']['op'] for r in requests.values()] == expected and cleanup_commands == [b'INFO\n',b'ABORT\n'],
            'Exact main and cleanup operation counts')
    loads = [r for r in requests.values() if r['q']['op'] == 'LOAD']
    for q, job in zip(loads, p['jobs']):
        require(q['q']['body'] == job and q['written'] == q['size'] == 52105, 'Complete exact maximum LOAD')
    unanswered = set(requests)-set(responses)
    require(unanswered == {loads[2]['q']['request_id']}, 'Only third LOAD lacks a response')
    for q in loads[:2]:
        body = responses[q['q']['request_id']]['message']['body']
        require(body['job_id'] == q['q']['body']['job_id'] and body['state'] == 'loaded' and
                body['adjustments'] == [dict(event_index=i,
                    requested_frequency_nhz=str(135500000000000 if i % 2 == 0 else 135495000000000),
                    realized_frequency_nhz=str(135500002652407 if i % 2 == 0 else 135494990274310))
                    for i in range(512)], 'Exact successful preceding replies')
    failures = [r for r in rows if r['kind'] == 'failure']
    require(len(failures) == 1 and failures[0]['value'] == dict(worker='main',
            error='Five-second exchange deadline; no retry: load-2') and
            5_000_000_000 <= failures[0]['monotonic_ns']-loads[2]['began'] < 5_500_000_000,
            'Preserved original five-second failure')
    require(loads[2]['last_write'] < failures[0]['monotonic_ns'], 'Full LOAD written before timeout')
    final = values['final']['a']['wtp']['STATUS']
    require(final['state'] == 'empty' and [r['job_id'] for r in final['terminal_records']] ==
            [p['jobs'][1]['job_id'],p['jobs'][0]['job_id']]+p['initial_terminal_jobs'] and
            all(r['state'] == 'aborted' and r['output_active'] is False for r in final['terminal_records']),
            'No third resident job; exact retained terminal order')
    native, metrics = native_wire(root,p,root/'pi/phase115_tls_observer_test.py')
    require(native and all(s['value']['output_active'] is False for s in native), 'Native inactive observations')
    for phase, name, state in [('before','acquired','HELD'),('final','released','RELEASED')]:
        r = json.loads((root/('reservation-'+name+'.json')).read_text())
        require(r['state'] == state and r['packet_sha256'] == PACKET and
                r['boards'] == inactive(values[phase]), 'Shared reservation reconciliation')
    result = json.loads((root/'run-result.json').read_text())
    require(result == rows[-1]['value'] and result['status'] == 'FAILED' and result['rf_jobs'] == 0 and
            result['loads'] == 3 and result['replays'] == 0, 'Failed result and zero RF charge')
    return dict(status='RETAINED_LOAD_FAILURE_AND_INACTIVE_CLEANUP_VERIFIED',packet_sha256=PACKET,
        source_revision=p['source_revision'],boot_id=p['boot_id'],rf_jobs=0,loads_written=3,
        successful_load_responses=2,missing_response_load_index=2,replays=0,main_claims=3,
        main_aborts=2,main_releases=2,cleanup_console_aborts=1,cleanup_claims=1,cleanup_releases=1,
        peak_allocator_bytes=values['final']['a']['info']['allocator_peak_bytes'],
        heap_capacity_bytes=values['final']['a']['info']['heap_capacity_bytes'],allocation_failures=0,
        native=metrics,boards=inactive(values['final']),configurations_preserved=True,
        schedules_disabled=True,reservation_released=True,accepted_components=[],family_closed=False,
        limitation='Admission pressure is reproduced in the host model; the exact target branch is not instrumented.')
