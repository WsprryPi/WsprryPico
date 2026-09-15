"""Reconcile two immutable failed packets; grants no RF/capacity acceptance."""
import json

from audit_phase11_5_completion_p1_failure import inputs
from audit_phase11_5_idle import frames
from audit_phase11_5_r3_v2_hour import journal, native_wire
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_rf_reservation import BOARDS, inactive
from validate_wtp_contract import SchemaValidator

PACKETS = {
    '69c5b306bdde2231764b078e47da05cd47e661eef35b0bb294eb83ae1734de18': 'initial_status_guard',
    'aa603d6510059bbc34a6f79627402e477615ef04ff789a8d66992352db619662': 'replacement_load_admission',
}


def audit(root):
    sha = digest(root/'packet.json')
    require(sha in PACKETS, 'Reviewed pre-ARM failure')
    packet, values = inputs(root, sha)
    rows = journal(root/'rf.jsonl')
    require(rows[0]['value']['packet_sha256'] == sha, 'Trace identity')
    schema = json.loads((root/'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    requests = []; replies = []; pending = None; wire = b''
    for row in rows:
        if row['kind'] == 'wtp_tx':
            messages, left = frames(bytes.fromhex(row['value']['hex']))
            require(not left and messages == [row['value']['request']] and pending is None,
                    'USB request framing and serial exchange')
            pending = messages[0]; requests.append(pending)
            require(not validator.errors(pending, schema), 'USB request schema')
        elif row['kind'] == 'wtp_rx':
            messages, wire = frames(wire + bytes.fromhex(row['value']['hex']))
            for message in messages:
                require(not validator.errors(message, schema), 'USB response schema')
                if message['type'] == 'event':
                    require(message['boot_id'] == packet['boot_id'], 'Event boot')
                else:
                    require(pending is not None and all(message[k] == pending[k]
                        for k in ('session_id','request_id','op')), 'USB response identity')
                    pending = None
                replies.append(message)
    require(pending is None and not wire and replies ==
            [r['value'] for r in rows if r['kind'] == 'wtp_message'], 'Complete USB capture')
    operations = [r['op'] for r in requests]
    if PACKETS[sha] == 'initial_status_guard':
        require(operations == ['HELLO','STATUS'] and all(r['ok'] for r in replies), 'Read-only guard failure')
    else:
        require(all(op in ('HELLO','STATUS','CLAIM','LOAD') for op in operations) and
                operations.count('CLAIM') == operations.count('LOAD') == 1, 'Exact pre-ARM writes')
        load, = [r for r in requests if r['op'] == 'LOAD']
        require(load['body'] == packet['jobs'][0], 'Exact maximum replacement job')
        errors = [r for r in replies if r.get('ok') is False]
        require(len(errors) == 1 and errors[0]['op'] == 'LOAD' and errors[0]['error'] ==
                dict(code='INTERNAL_ERROR', message='INTERNAL_ERROR', retryable=False), 'Preserved admission failure')
    require(not any(r['kind'].startswith('capacity_') or r['kind'].startswith('arm_') for r in rows),
            'No RF or capacity action')
    native, metrics = native_wire(root, packet, root/'pi/phase115_tls_observer_test.py')
    require(all(v['value']['output_active'] is False and v['value']['state'] == 'complete'
                for v in native), 'Native inactive terminal observations')
    for phase, name, state in [('before','acquired','HELD'),('final','released','RELEASED')]:
        reservation = json.loads((root/('rf-reservation-'+name+'.json')).read_text())
        require(reservation['packet_sha256'] == sha and reservation['state'] == state and
                reservation['host_boot'] == packet['host_boot_id'] and
                reservation['boards'] == inactive({b: values[phase+'-'+b] for b in BOARDS}),
                'Reservation with authoritative A/B state')
    for board in BOARDS:
        before, after = (values[phase+'-'+board] for phase in ('before','final'))
        require(before['wtp']['STATUS'] == after['wtp']['STATUS'], 'Preserved terminal authority')
        require(all(before['info'][k] == after['info'][k] for k in
                    ('launch_epoch','dma_irqs','alarm_irqs','tail_irqs')), 'No launch or RF counter change')
    result = json.loads((root/'rf-result.json').read_text())
    require(rows[-1]['value'] == result and result['status'] == 'STOPPED_REQUIRES_DIAGNOSIS' and
            result['armed_jobs'] == result['completed_jobs'] == [] and
            result['rf_duration_ns_charged'] == result['renewals'] == 0, 'Zero-RF failed accounting')
    return dict(status='PREARM_FAILURE_CONFIRMED', classification=PACKETS[sha], packet_sha256=sha,
        acceptance=False, rf_jobs_charged=0, rf_seconds_charged=0, native=metrics,
        configurations_preserved=True, schedules_disabled=True, reservation_released=True,
        final_a=values['final-a']['wtp']['STATUS'], final_b=values['final-b']['wtp']['STATUS'],
        failures=result['faults'])
