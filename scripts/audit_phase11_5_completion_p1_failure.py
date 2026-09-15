"""Audit the immutable first completion packet; never grants capacity acceptance."""
import json
from pathlib import Path

from phase11_5_device_management import digest
from phase11_5_inventory import require, loads_console
from phase11_5_pilot_supervisor import configuration
from phase11_5_r3_preflight import audit_inventory
from phase11_5_rf_reservation import BOARDS, inactive
from audit_phase11_5_r3_v2_hour import journal, native_wire
from audit_phase11_5_idle import frames
from phase11_5_r3_capacity_plan import wtp_capacity_frame
from phase11_5_r3_v2_rf import validate_info

PACKET = 'cbc6f4b871841c0cf4f6976e5cde73976699798aa0ccdc3ff65b72dc50c73e8d'


def audit(root):
    require(digest(root/'packet.json') == PACKET, 'Exact failed packet')
    packet = json.loads((root/'packet.json').read_text())
    private = json.loads((root/'private-input-hashes.json').read_text())
    require(set(private) == {'production.ini'} | {
        'credentials/'+role+'/'+name for role in ('browser','controller')
        for name in ('client-ca.crt','client.crt','client.key')}, 'Private input hash inventory')
    for name, sha in packet['stage_sha256'].items():
        require((private[name] if name in private else digest(root/name)) == sha,
                'Executed helper identity: ' + name)
    values = {}
    for phase in ('before', 'final'):
        for board, (serial, device) in BOARDS.items():
            label = phase + '-' + board
            values[label] = audit_inventory(root/(label+'.stdout'),
                dict(serial=serial, device_id=device),
                packet['b_session' if board == 'b' else 'inventory_session'],
                packet['stage_sha256']['scripts/phase11_5_inventory.py'])
            require(not (root/(label+'.stderr')).read_bytes(), 'Inventory stderr')
    for board in BOARDS:
        require(configuration(values['before-'+board]) == configuration(values['final-'+board]),
                'Preserved configuration')
    require(values['before-b']['wtp']['STATUS'] == values['final-b']['wtp']['STATUS'], 'B unchanged')
    rows = journal(root/'rf.jsonl')
    require(rows[0]['value']['packet_sha256'] == PACKET, 'Trace packet')
    info = []; pending = None; buffer = b''; decoded = None
    for row in rows:
        kind, value, stamp = row['kind'], row['value'], row['monotonic_ns']
        if kind == 'console_tx':
            require(pending is None and not buffer and decoded is None and
                    bytes.fromhex(value['hex']) == b'INFO\n', 'Single INFO request')
            pending = stamp
        elif kind == 'console_rx':
            require(pending is not None, 'Solicited Console bytes')
            buffer += bytes.fromhex(value['hex'])
            if b'\n' in buffer:
                require(buffer.endswith(b'\n') and buffer.count(b'\n') == 1 and
                        stamp-pending <= 5_000_000_000, 'Console framing/deadline')
                decoded = loads_console(buffer.decode().strip()); buffer = b''; pending = None
        elif kind == 'info':
            require(decoded == value['value'], 'Console raw/summary agreement')
            validate_info(decoded, values['before-a'], packet)
            info.append(row); decoded = None
    require(info and pending is None and not buffer and decoded is None, 'Complete Console capture')
    gaps = [b['value']['began_monotonic_ns']-a['value']['began_monotonic_ns'] for a,b in zip(info,info[1:])]
    require(all(0 < gap <= 2_000_000_000 for gap in gaps), 'Console cadence')
    capacity, = [r for r in rows if r['kind'] == 'capacity_tx']
    expected = wtp_capacity_frame(packet['peer_session'], packet['wtp_capacity']['maximum_request_id'])
    require(bytes.fromhex(capacity['value']['hex']) == expected, 'Exact maximum offered frame')
    writes = [r for r in rows if r['kind'] == 'capacity_write']
    require([r['value'] for r in writes] == [dict(bytes=4096,total_written=4096)] and
            not any(r['kind'] in ('capacity_rx','capacity_message') for r in rows), 'Exact partial write failure')
    requests = []; replies = []; wire = b''
    for row in rows:
        if row['kind'] == 'wtp_tx':
            messages, left = frames(bytes.fromhex(row['value']['hex']))
            require(not left and messages == [row['value']['request']], 'USB request framing/CRC')
            requests.extend(messages)
        elif row['kind'] == 'wtp_rx':
            messages, wire = frames(wire+bytes.fromhex(row['value']['hex'])); replies.extend(messages)
    require(not wire and replies == [r['value'] for r in rows if r['kind']=='wtp_message'], 'USB response framing/CRC')
    load, = [q for q in requests if q['op']=='LOAD']
    require(load['body'] == packet['jobs'][0], 'Exact 512-event job')
    arm, = [q for q in requests if q['op']=='ARM']
    arm_reply, = [q for q in replies if q.get('request_id')==arm['request_id']]
    require(arm_reply['ok'] is True and arm_reply['session_id']==packet['peer_session'] and
            arm_reply['body']['job_id']==packet['jobs'][0]['job_id'], 'Raw ARM acknowledgement')
    load_reply, = [q for q in replies if q.get('request_id')==load['request_id']]
    require(load_reply['ok'] is True and load_reply['session_id']==packet['peer_session'], 'Raw LOAD acknowledgement')
    final = values['final-a']['wtp']['STATUS']; job = packet['jobs'][0]
    require(final['boot_id']==packet['boot_id'] and final['job_id']==job['job_id'] and
            final['state']=='complete' and final['owner_id'] is None and final['output_active'] is False,
            'Authoritative finite completion after failed observer')
    before = values['before-a']['info']; after = values['final-a']['info']
    require(int(after['launch_epoch'])-int(before['launch_epoch'])==1 and
            after['tail_irqs']-before['tail_irqs']==1, 'Single launch and tail')
    native, native_metrics = native_wire(root, packet, root/'pi/phase115_tls_observer_test.py')
    contention = journal(root/'contention.jsonl')
    overlapping = [r for r in contention if r['kind']=='https_status' and
        r['value']['began_monotonic_ns'] <= capacity['monotonic_ns'] <= r['monotonic_ns']]
    require(len(overlapping)==1 and not any(r['kind']=='http_tx' for r in contention), 'Actual ordinary HTTPS overlap')
    for phase, name, state in [('before','acquired','HELD'),('final','released','RELEASED')]:
        reservation=json.loads((root/('rf-reservation-'+name+'.json')).read_text())
        require(reservation['packet_sha256']==PACKET and reservation['state']==state and
                reservation['host_boot']==packet['host_boot_id'] and
                reservation['boards']==inactive({b:values[phase+'-'+b] for b in BOARDS}), 'Reservation authority')
        require(reservation['monotonic_ns'] <= rows[0]['monotonic_ns'] if phase=='before' else
                info[-1]['monotonic_ns'] <= reservation['monotonic_ns'] <= rows[-1]['monotonic_ns'],
                'Reservation held through final observations')
    result=json.loads((root/'rf-result.json').read_text())
    require(rows[-1]['value']==result and result['status']=='STOPPED_REQUIRES_DIAGNOSIS' and
            result['armed_jobs']==[job['job_id']] and result['rf_duration_ns_charged']==128_000_000_000,
            'Failed packet accounting')
    require([r['value'] for r in rows if r['kind']=='failure'] == [
        dict(worker='wtp action',error='C0 five-second capacity operation deadline; no retry or RF action',type='TimeoutError'),
        dict(worker='wtp',error='STATUS response timeout; no automatic retry; output unknown',type='TimeoutError')],
        'Preserved exact USB failures')
    require([r['value'] for r in contention if r['kind']=='failure'] == [
        dict(type='ValueError',error='Stale observer without bounded read in flight')], 'Preserved HTTPS guard failure')
    prior=next(r for r in reversed(info) if r['monotonic_ns']<capacity['monotonic_ns'])
    return dict(status='FAILED_CAPACITY_PARTIAL_WRITE_CONFIRMED',packet_sha256=PACKET,
        capacity_acceptance=False,group2_closed=False,rf_jobs_charged=1,rf_seconds_charged=128,
        maximum_payload_bytes=65536,frame_bytes=len(expected),host_bytes_written=4096,
        http_capacity_cases_executed=0,console_samples=len(info),maximum_console_start_gap_ns=max(gaps),
        native=native_metrics,ordinary_https_overlap=True,
        preceding_heap_available_bytes=prior['value']['value']['heap_available_bytes'],
        preceding_heap_sample_age_ns=capacity['monotonic_ns']-prior['monotonic_ns'],
        admission_requirement_bytes=65552+32768,
        diagnosis='Source and sampled heap support parser admission refusal during HTTPS overlap; the exact target branch is not directly observed.',
        final_a=final,final_b=values['final-b']['wtp']['STATUS'],configurations_preserved=True,
        schedules_disabled=True,reservation_released=True,
        limitations=['No maximum-frame acceptance, oversize recovery or HTTP boundary credit.',
                    'Finite completion is confirmed; the complete multi-observer capacity gate failed.'],
        failures=[r['value'] for r in rows+contention if r['kind']=='failure'])
