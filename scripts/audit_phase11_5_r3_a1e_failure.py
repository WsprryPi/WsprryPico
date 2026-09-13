"""Classify the consumed A1e failure from raw bytes; grants no acceptance credit."""
import json
from collections import Counter
from pathlib import Path
from audit_phase11_5_idle import frames
from audit_phase11_5_r2_modes import timing
from phase11_5_inventory import require, loads_console
from phase11_5_device_management import digest
from phase11_5_pilot_supervisor import finished
from phase11_5_r3_preflight import audit_inventory, decode_frame
from phase11_5_rf_observer import validate_info, validate_event, validate_status
from phase11_5_time_local import validate_preserved
from validate_wtp_contract import SchemaValidator

PACKET = '27cd914815b8af8933fb134b44a923add1f09c8748afd0082115e4b1f202a518'
BOOT = '9c5aec394269e0b57ca16d73ad3d12b6'
JOB = 'd27689688f2f3e519a3836b775b3092b'


def rows(path):
    raw = path.read_text()
    require(raw.endswith('\n'), 'Truncated evidence')
    return [json.loads(line) for line in raw.splitlines()]


def wifi_exchange(path, enabled):
    trace = rows(path); pending = None; data = b''; replies = []
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] for a,b in zip(trace,trace[1:])), 'Wi-Fi chronology')
    for row in trace:
        if row['kind'] == 'tx':
            require(pending is None and not data, 'Overlapping Wi-Fi command')
            pending = bytes.fromhex(row['value']['hex'])
            began = row['monotonic_ns']
            expected = b'INFO\n' if not replies else (b'WIFI ON\n' if enabled else b'WIFI OFF\n')
            require(len(replies) < 2 and pending == expected, 'Unexpected Wi-Fi/Console mutation')
        elif row['kind'] == 'rx':
            require(pending is not None, 'Unsolicited Wi-Fi bytes')
            data += bytes.fromhex(row['value']['hex'])
            if b'\n' in data:
                require(data.endswith(b'\n') and data.count(b'\n') == 1, 'Wi-Fi response framing')
                require(row['monotonic_ns'] - began <= 5_000_000_000, 'Wi-Fi reply deadline')
                replies.append(loads_console(data.decode().strip())); data = b''; pending = None
        else: raise ValueError('Unexpected Wi-Fi exchange record')
    require(pending is None and not data and len(replies) == 2 and replies[1] == {'ok': True}, 'Missing Wi-Fi ACK')
    info = replies[0]
    require(info['device_id'] == 'fd6127d11d6aca42a9905fa3fb1bf1d5' and info['status']['boot_id'] == BOOT
            and info['status']['state'] == 'empty' and info['status']['output_active'] is False
            and info['network']['enabled'] is not enabled, 'Wi-Fi command lacked idle same-boot admission')


def audit(root):
    require(digest(root / 'packet.json') == PACKET, 'Different consumed A1e packet')
    packet = json.loads((root / 'packet.json').read_text())
    for group in ('case_helper_sha256', 'production_helper_sha256'):
        for name, sha in packet[group].items():
            require(digest(root / name) == sha, 'Executed source changed')
    result = json.loads((root / 'retained-result.json').read_text())
    require(result == dict(status='FAILED', packet_sha256=PACKET, family_closed=False,
            error='ValueError: R3 worker failed; no retry', device_inactive_unowned=True,
            b_unchanged=True, host_restored=True, configuration_writes=0, flashes=0),
            'Executed failure/cleanup record differs')
    case = root / 'tls-a1'
    rf = json.loads((case / 'jobs.json').read_text())
    require(rf['boot_id'] == BOOT and rf['jobs'][0]['job_id'] == JOB and
            rf['jobs'] == packet['finite_job_templates'], 'Physical job identity')
    pressure = rows(case / 'pressure.jsonl')
    require([r['sequence'] for r in pressure] == list(range(14)) and
            [r['kind'] for r in pressure] == ['start','case_begin','tcp_open','tls','http','case_finish',
                'case_begin','tcp_open','tls','case_finish','case_begin','tcp_open','tls','failure'] and
            pressure[-1]['value'] == dict(type='ValueError', error='Stale observer without bounded read in flight'),
            'Pressure failure differs')
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] for a,b in zip(pressure,pressure[1:])), 'Pressure time order')
    require(pressure[0]['value'] == dict(packet_sha256=digest(case/'jobs.json'), load_sha256=digest(case/'load.json')),
            'Pressure binding')
    from phase11_5_r3_tls_pressure import response, PEER
    response(bytes.fromhex(pressure[4]['value']['response_hex']), rf, rf['jobs'][0])
    require(pressure[5]['value']['label'] == 'positive' and pressure[9]['value']['label'] == 'missing-certificate'
            and pressure[9]['value']['alert'] == 116 and
            pressure[9]['value']['reason'] == 'TLSV13_ALERT_CERTIFICATE_REQUIRED', 'Completed preliminary cases changed')
    require(all(r['value']['peer_sha256'] == PEER and r['value']['version'] == 'TLSv1.3'
                for r in pressure if r['kind'] == 'tls'), 'TLS identity changed')
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
                validate_event(value, BOOT, rf)
                require(int(value['event_id']) == len(events) + 7, 'Event sequence')
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
            validate_status(last_status, BOOT, rf, failure_observation=row['monotonic_ns'] > pressure[-1]['monotonic_ns'])
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
    failure_ns = pressure[-1]['monotonic_ns']
    previous_info = [r for r in info_rows if r['monotonic_ns'] < failure_ns][-1]
    next_info = next(r for r in info_rows if r['monotonic_ns'] > failure_ns)
    inflight = [r for r in observed if r['kind'] == 'console_tx' and r['monotonic_ns'] < failure_ns][-1]
    require(previous_info['monotonic_ns'] + 2_000_000_000 < failure_ns < next_info['monotonic_ns']
            and previous_info['monotonic_ns'] < inflight['monotonic_ns'] < failure_ns
            and next_info['monotonic_ns'] - inflight['monotonic_ns'] <= 5_000_000_000
            and all(r['value']['value']['status']['state'] == 'running'
                    and r['value']['value']['status']['output_active'] is True for r in (previous_info,next_info)),
            'Raw timing does not establish a valid in-flight INFO at pressure stop')
    load_events = rows(case/'load-events.jsonl')
    load_failure = next(r for r in load_events if r['kind'] == 'load_failure')
    require(failure_ns < load_failure['monotonic_ns'] and
            'interrupted 15' in load_events[-1]['value']['failures'] and
            load_events[-1]['value']['exit'] == 0 and
            observed[-1]['monotonic_ns'] - observed[0]['monotonic_ns'] >= 360_000_000_000,
            'Worker consequence chronology differs')
    counts = Counter(q['op'] for q in requests)
    require(counts == dict(HELLO=1, STATUS=72, CLAIM=1, LOAD=1, GET_CLOCK=1, ARM=1), 'Unexpected mutation/retry')
    load = next(q for q in requests if q['op'] == 'LOAD')
    arm = next(e for e in exchanges if e['request']['op'] == 'ARM')
    require(load['body'] == rf['jobs'][0] and arm['request']['body']['job_id'] == JOB and
            arm['response']['body']['start_utc_ns'] == arm['request']['body']['start_utc_ns'], 'Finite job/ARM changed')
    require([e['body']['state'] for e in events if e['event'] == 'JOB_STATE'] == ['loaded', 'armed', 'running', 'complete'] and
            events[-1]['event'] == 'OWNER_RELEASED' and events[-1]['body']['reason'] == 'terminal', 'Finite terminal lifecycle')
    require(last_status['boot_id'] == BOOT and last_status['state'] == 'complete' and
            last_status['owner_id'] is None and last_status['output_active'] is False and last_status['job_id'] == JOB,
            'Final raw STATUS is not complete/inactive/unowned')
    path = root / 'final-terminal-before.stdout'
    invrows = rows(path)
    tx = [v for v in invrows if v['kind'] == 'tx']; session = decode_frame(bytes.fromhex(tx[1]['value']['hex']))['session_id']
    inventory = audit_inventory(path, dict(serial=packet['serial'], device_id=packet['device_id']), session,
                                packet['case_helper_sha256']['scripts/phase11_5_inventory.py'])
    require(inventory['wtp']['STATUS'] == last_status and inventory['info']['status']['output_active'] is False,
            'Restoration admission contradicts terminal state')
    host = json.loads((root / 'fixture-state.json').read_text()); log = rows(root / 'fixture.jsonl')
    require(host['restored'] is True and next(r['value'] for r in log if r['kind'] == 'host_restored') == host['before'], 'Host not restored')
    require(next(r['value'] for r in log if r['kind'] == 'cleanup')['failures'] == [], 'Host cleanup failures')
    validate_preserved(host['time_local_before'], next(r['value'] for r in log if r['kind'] == 'time_local_after'))
    from audit_phase11_5_r3_retained_failure import cleanup
    from phase11_5_pilot_supervisor import idle, configuration, B_SERIAL, B_DEVICE
    final = audit_inventory(root/'final-terminal-after.stdout', dict(serial=packet['serial'],device_id=packet['device_id']),
                            packet['inventory_session_id'],packet['case_helper_sha256']['scripts/phase11_5_inventory.py'])
    cleanup(root/'final-terminal-release.jsonl',packet,inventory,final); idle(final)
    comparators = []
    for name in ('before-b','after-b'):
        b = audit_inventory(root/(name+'.stdout'),dict(serial=B_SERIAL,device_id=B_DEVICE),
                            packet['b_inventory_session_id'],packet['case_helper_sha256']['scripts/phase11_5_inventory.py'])
        idle(b); require(b['wtp']['STATUS']['boot_id']==packet['initial_b_boot_id'],'B changed')
        comparators.append(b)
    require(configuration(comparators[0]) == configuration(comparators[1]), 'B configuration changed')
    require(json.loads((root/'wifi-recovery.json').read_text()) ==
            dict(status='CYCLE_COMPLETED_REJOIN_NOT_YET_PROVEN',off=1,on=1), 'Wi-Fi cycle accounting changed')
    require(json.loads((root/'retained-ap-identity.json').read_text()) == dict(psk_matches_retained=True),
            'AP credential comparison missing')
    wifi_exchange(root/'wifi-off-exchange.jsonl',False)
    wifi_exchange(root/'wifi-on-exchange.jsonl',True)
    # Timing is a separately labeled diagnostic. It does not make this interrupted
    # pressure/observation run pass its full acceptance gates.
    try:
        measured = timing(rf, [dict(job=rf['jobs'][0], start_utc_ns=arm['request']['body']['start_utc_ns'],
                                  monotonic_ns=arm['started_ns'])], observed)
        timing_result = dict(status='DIAGNOSTIC_ONLY', values=measured)
    except ValueError as error:
        timing_result = dict(status='DIAGNOSTIC_GATE_FAILED', error=str(error))
    return dict(classification='HARNESS_STALE_CHECK_DURING_VALID_INFLIGHT_INFO', accepted_assertions=0,
                packet_sha256=PACKET, boot=BOOT, submitted_jobs=1, completed_jobs=1,
                unused_job_id=rf['jobs'][1]['job_id'], pressure_connections=3,
                preliminary_case_finishes=2, recovery_completed=False, http_response_bytes_retained=True,
                observer_samples=dict(samples), observer_seconds=(observed[-1]['monotonic_ns']-observed[0]['monotonic_ns'])/1e9,
                causal_timing=dict(pressure_failure_ns=failure_ns, load_failure_ns=load_failure['monotonic_ns'],
                    previous_info_age_ns=failure_ns-previous_info['monotonic_ns'],
                    inflight_elapsed_at_failure_ns=failure_ns-inflight['monotonic_ns'],
                    replacement_info_roundtrip_ns=next_info['monotonic_ns']-inflight['monotonic_ns'],
                    max_info_start_gap_ns=max(b-a for a,b in zip(info_starts,info_starts[1:]))),
                final_status=final['wtp']['STATUS'], host_restored=True, configuration_writes=0, flashes=0,
                wifi_off=1,wifi_on=1, requests=dict(counts),timing=timing_result)
