"""Classify the consumed A1b failure from raw bytes; grants no acceptance credit."""
import json
from collections import Counter
from pathlib import Path
from audit_phase11_5_idle import frames
from audit_phase11_5_r2_modes import timing
from phase11_5_inventory import require, loads_console
from phase11_5_device_management import digest
from phase11_5_pilot_supervisor import finished
from phase11_5_r3_preflight import audit_inventory, decode_frame
from phase11_5_rf_observer import validate_info, validate_event
from phase11_5_time_local import validate_preserved
from validate_wtp_contract import SchemaValidator

PACKET = '590da5a47dc37c1d4c8addea4713ca0cfcb25872a3daaff46a4c9abb9702b218'
BOOT = '9c5aec394269e0b57ca16d73ad3d12b6'
JOB = '91bd2c3d57e3e74f7de183203796f463'


def rows(path):
    raw = path.read_text()
    require(raw.endswith('\n'), 'Truncated evidence')
    return [json.loads(line) for line in raw.splitlines()]


def audit(root):
    require(digest(root / 'packet.json') == PACKET, 'Different consumed A1b packet')
    packet = json.loads((root / 'packet.json').read_text())
    for name, sha in packet['case_helper_sha256'].items():
        require(digest(root / name) == sha, 'Executed source changed')
    result = json.loads((root / 'r3-result.json').read_text())
    require(result['status'] == 'FAILED' and result['completed_jobs'] == 0 and
            result['packet_sha256'] == PACKET and result['host_restored'] is True and
            result['restore_error'] == 'R3 stage failed: device-restore' and
            not result.get('device_restored'), 'Executed failure/restoration record differs')
    case = root / 'tls-a1'
    rf = json.loads((case / 'jobs.json').read_text())
    require(rf['boot_id'] == BOOT and rf['jobs'][0]['job_id'] == JOB and
            rf['jobs'] == packet['finite_job_templates'], 'Physical job identity')
    pressure = rows(case / 'pressure.jsonl')
    require([r['sequence'] for r in pressure] == list(range(5)) and
            [r['kind'] for r in pressure] == ['start', 'case_begin', 'tcp_open', 'tls', 'failure'] and
            pressure[-1]['value'] == dict(type='ValueError', error='R3 HTTP status'), 'Pressure failure differs')
    require(all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(pressure, pressure[1:])),
            'Pressure time order')
    require(pressure[0]['value'] == dict(packet_sha256=digest(case / 'jobs.json'),
            load_sha256=digest(case / 'load.json')) and
            pressure[1]['value'] == dict(label='positive', job_id=JOB, launch_epoch=1), 'Pressure binding')
    observed = rows(case / 'usb-health.jsonl')
    require([r['sequence'] for r in observed] == list(range(len(observed))) and
            all(a['monotonic_ns'] <= b['monotonic_ns'] for a, b in zip(observed, observed[1:])), 'Observer sequence')
    require(observed[0]['value']['packet_sha256'] == digest(case / 'jobs.json') and
            observed[0]['value']['baseline_sha256'] == digest(root / 'r3-a1-admission.stdout'), 'Observer identity')
    failures = [r['value'] for r in observed if r['kind'] == 'failure']
    require(failures == [dict(worker='wtp', type='ValueError', error='Unexpected job/owner')] and
            observed[-1]['value'] == dict(result='FAILED', faults=['wtp: Unexpected job/owner']), 'Observer failure differs')
    schema = json.loads((Path(__file__).resolve().parents[1] / 'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    pending, received, exchanges, events = {}, [], [], []
    wire, console, console_value, last_status = b'', b'', None, None
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
                require(int(value['event_id']) == len(events), 'Event sequence')
                events.append(value)
            else:
                q, began = pending.pop(value['request_id'])
                require(value['ok'] is True and value['op'] == q['op'] and
                        0 <= row['monotonic_ns'] - began <= 5_000_000_000, 'Request failed/deadline')
                exchanges.append(dict(request=q, response=value, started_ns=began))
                if q['op'] == 'STATUS': last_status = value['body']
        elif kind == 'console_tx':
            require(not console and console_value is None and bytes.fromhex(value['hex']) == b'INFO\n', 'Console mutation')
        elif kind == 'console_rx':
            console += bytes.fromhex(value['hex'])
            if b'\n' in console:
                require(console.count(b'\n') == 1 and console.endswith(b'\n'), 'Console framing')
                console_value = loads_console(console.decode().strip()); console = b''
        elif kind == 'info':
            require(value['value'] == console_value, 'INFO differs from raw bytes')
            validate_info(console_value, baseline); console_value = None; samples[kind] += 1
        elif kind == 'status':
            require(value['value'] == last_status, 'STATUS differs from raw bytes'); samples[kind] += 1
        elif kind == 'health': samples[kind] += 1
    require(not wire and not received and not pending and not console and console_value is None, 'Unfinished raw exchange')
    counts = Counter(q['op'] for q in requests)
    require(counts == dict(HELLO=1, STATUS=26, CLAIM=1, LOAD=1, GET_CLOCK=1, ARM=1), 'Unexpected mutation/retry')
    load = next(q for q in requests if q['op'] == 'LOAD')
    arm = next(e for e in exchanges if e['request']['op'] == 'ARM')
    require(load['body'] == rf['jobs'][0] and arm['request']['body']['job_id'] == JOB and
            arm['response']['body']['start_utc_ns'] == arm['request']['body']['start_utc_ns'], 'Finite job/ARM changed')
    require([e['body']['state'] for e in events if e['event'] == 'JOB_STATE'] == ['loaded', 'armed', 'running', 'complete'] and
            events[-1]['event'] == 'OWNER_RELEASED' and events[-1]['body']['reason'] == 'terminal', 'Finite terminal lifecycle')
    require(last_status['boot_id'] == BOOT and last_status['state'] == 'complete' and
            last_status['owner_id'] is None and last_status['output_active'] is False and last_status['job_id'] == JOB,
            'Final raw STATUS is not complete/inactive/unowned')
    path = root / 'restore-admission-a.stdout'
    invrows = rows(path)
    tx = [v for v in invrows if v['kind'] == 'tx']; session = decode_frame(bytes.fromhex(tx[1]['value']['hex']))['session_id']
    inventory = audit_inventory(path, dict(serial=packet['serial'], device_id=packet['device_id']), session,
                                packet['helper_sha256']['scripts/phase11_5_inventory.py'])
    require(inventory['wtp']['STATUS'] == last_status and inventory['info']['status']['output_active'] is False,
            'Restoration admission contradicts terminal state')
    host = json.loads((root / 'fixture-state.json').read_text()); log = rows(root / 'fixture.jsonl')
    require(host['restored'] is True and next(r['value'] for r in log if r['kind'] == 'host_restored') == host['before'], 'Host not restored')
    require(next(r['value'] for r in log if r['kind'] == 'cleanup')['failures'] == [], 'Host cleanup failures')
    validate_preserved(host['time_local_before'], next(r['value'] for r in log if r['kind'] == 'time_local_after'))
    management = json.loads((root / 'management-state.json').read_text())
    require(management['counts'] == dict(config=37, **{'wifi-off': 0, 'wifi-on': 0, 'heap-probe': 6}) and
            not management['pending'] and not management['blocked'], 'Management outcome changed')
    # Timing is a separately labeled diagnostic. It does not make this interrupted
    # pressure/observation run pass its full acceptance gates.
    try:
        measured = timing(rf, [dict(job=rf['jobs'][0], start_utc_ns=arm['request']['body']['start_utc_ns'],
                                  monotonic_ns=arm['started_ns'])], observed)
        timing_result = dict(status='DIAGNOSTIC_ONLY', values=measured)
    except ValueError as error:
        timing_result = dict(status='DIAGNOSTIC_GATE_FAILED', error=str(error))
    return dict(classification='FAILED_HTTP_CHECK_ONE_JOB_COMPLETE_HOST_RESTORED', accepted_assertions=0,
                packet_sha256=PACKET, boot=BOOT, submitted_jobs=1, completed_jobs=1, released_jobs=0,
                pressure_connections=1, pressure_cases_passed=0, http_response_bytes_retained=False,
                observer_samples=dict(samples), observer_seconds=(observed[-1]['monotonic_ns']-observed[0]['monotonic_ns'])/1e9,
                final_status=last_status, host_restored=True, original_configuration_restored=False,
                management_counts=management['counts'], requests=dict(counts), timing=timing_result)
