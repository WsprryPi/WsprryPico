"""Raw observation reconstruction for a stopped R3 actor; diagnostic only."""
import json
from collections import Counter
from pathlib import Path
from phase11_5_inventory import require, loads_console
from phase11_5_device_management import digest
from phase11_5_pilot_supervisor import finished
from phase11_5_rf_observer import validate_info, validate_status, validate_event
from validate_wtp_contract import SchemaValidator
from audit_phase11_5_idle import frames
from audit_phase11_5_r3_a1e_failure import rows


def audit(root, packet, rf, failure_ns):
    case = root / 'tls-a1'
    observed = rows(case / 'usb-health.jsonl')
    require([r['sequence'] for r in observed] == list(range(len(observed))) and
            all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(observed, observed[1:])), 'Observer sequence')
    require(observed[0]['value']['packet_sha256'] == digest(case / 'jobs.json') and
            observed[0]['value']['baseline_sha256'] == digest(root / 'r3-a1-admission.stdout'), 'Observer identity')
    failures = [r['value'] for r in observed if r['kind'] == 'failure']
    require(failures == [dict(worker='wtp', type='ValueError', error='Remaining USB jobs did not finish')] and
            observed[-1]['value'] == dict(result='FAILED', faults=['wtp: Remaining USB jobs did not finish']), 'Observer failure differs')
    schema = json.loads((Path(__file__).resolve().parents[1] / 'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    pending, received, exchanges, events = {}, [], [], []
    wire, console, console_value, last_status = b'', b'', None, None
    console_pending = False
    requests = []
    session = observed[0]['value']['session_id']
    baseline = finished(root / 'r3-a1-admission.stdout', 'READ_ONLY_INVENTORY')
    samples = Counter()
    first_event_id = None
    for row in observed:
        kind, value = row['kind'], row['value']
        require(kind in ('start', 'finish', 'console_tx', 'console_rx', 'wtp_tx', 'wtp_rx',
                         'wtp_message', 'info', 'status', 'health', 'info_finish',
                         'status_finish', 'health_finish', 'armed_job', 'failure'),
                'Unexpected observer operation')
        if kind == 'wtp_tx':
            decoded, left = frames(bytes.fromhex(value['hex']))
            require(not left and decoded == [value['request']], 'Request differs from raw wire')
            q = decoded[0]
            require(not validator.errors(q, schema) and q['session_id'] == session and
                    q['request_id'] not in {r['request_id'] for r in requests}, 'Request schema/replay')
            requests.append(q); pending[q['request_id']] = (q, row['monotonic_ns'])
        elif kind == 'wtp_rx':
            decoded, wire = frames(wire + bytes.fromhex(value['hex'])); received.extend(decoded)
        elif kind == 'wtp_message':
            require(received and received.pop(0) == value and not validator.errors(value, schema), 'Response differs from raw wire')
            require(value['session_id'] == session, 'Response session changed')
            if value['type'] == 'event':
                validate_event(value, rf['boot_id'], rf)
                if first_event_id is None: first_event_id = int(value['event_id'])
                require(int(value['event_id']) == len(events) + first_event_id, 'Event sequence')
                events.append(value)
            else:
                q, began = pending.pop(value['request_id'])
                require(value['ok'] is True and value['op'] == q['op'] and
                        0 <= row['monotonic_ns'] - began <= 5_000_000_000, 'Request failed/deadline')
                exchanges.append(dict(request=q, response=value, started_ns=began))
                if q['op'] == 'STATUS': last_status = value['body']
        elif kind == 'console_tx':
            require(not console_pending and not console and console_value is None and bytes.fromhex(value['hex']) == b'INFO\n', 'Console mutation')
            console_pending = True; console_began = row['monotonic_ns']
        elif kind == 'console_rx':
            require(console_pending, 'Unsolicited Console bytes')
            console += bytes.fromhex(value['hex'])
            if b'\n' in console:
                require(console.count(b'\n') == 1 and console.endswith(b'\n'), 'Console framing')
                console_value = loads_console(console.decode().strip()); console = b''
                require(row['monotonic_ns'] - console_began <= 5_000_000_000, 'Console reply deadline')
                console_pending = False
        elif kind == 'info':
            require(value['value'] == console_value, 'INFO differs from raw bytes')
            validate_info(console_value, baseline); console_value = None; samples[kind] += 1
        elif kind == 'status':
            require(value['value'] == last_status, 'STATUS differs from raw bytes')
            validate_status(last_status, rf['boot_id'], rf, failure_observation=row['monotonic_ns'] > failure_ns)
            samples[kind] += 1
        elif kind == 'health':
            require(value['value']['boot'] == packet['host_boot_id'] and value['value']['throttled'] == 'throttled=0x0', 'Host health changed')
            samples[kind] += 1
    require(not wire and not received and not pending and not console and not console_pending and console_value is None, 'Unfinished raw exchange')
    for kind,period in (('info',1),('status',5),('health',5)):
        selected = [r for r in observed if r['kind']==kind]
        starts = [r['value']['began_monotonic_ns'] for r in selected]
        require(len(starts)==360//period and max(b-a for a,b in zip(starts,starts[1:])) <= (period+1)*10**9
                and starts[-1]-starts[0] >= (360-period-1)*10**9, 'Incomplete observer cadence')
        require([r['value'] for r in observed if r['kind']==kind+'_finish'] ==
                [dict(samples=len(starts),completed=True)], 'Observer completion marker changed')
    info_rows = [r for r in observed if r['kind'] == 'info']
    info_starts = [r['value']['began_monotonic_ns'] for r in info_rows]
    require(len(info_rows) == 360 and max(b-a for a,b in zip(info_starts,info_starts[1:])) <= 2_000_000_000,
            'INFO start cadence failed independently')
    require(observed[-1]['monotonic_ns'] - observed[0]['monotonic_ns'] >= 360000000000,
            'Stopped observer interval truncated')
    require(all(q['op'] in ('HELLO','STATUS','CLAIM','LOAD','ARM','GET_CLOCK','RENEW','RELEASE')
                for q in requests), 'Unexpected stopped-actor mutation')
    return dict(status='DIAGNOSTIC_ONLY', samples=dict(samples), requests=requests, exchanges=exchanges,
                events=events, last_status=last_status, rows=observed,
                seconds=(observed[-1]['monotonic_ns']-observed[0]['monotonic_ns'])/1e9)
