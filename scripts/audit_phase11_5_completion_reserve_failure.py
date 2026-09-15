"""Confirm the immutable three-LOAD reserve failure; grant no workload acceptance."""
import json
from audit_phase11_5_completion_p1_failure import inputs
from audit_phase11_5_idle import frames
from audit_phase11_5_r3_v2_hour import journal, native_wire
from phase11_5_device_management import digest
from phase11_5_inventory import require, loads_console
from phase11_5_pilot_supervisor import configuration
from phase11_5_r3_preflight import audit_inventory
from phase11_5_rf_reservation import BOARDS, inactive
from validate_wtp_contract import SchemaValidator

PACKETS = {
    '575ede223180c866915d600724bd2ad778d63be522be38f08c8437d816afd630': (31200,187808,False,52105),
    '1f578a4b0f403434e3110d9c9b08e48daaa6f22c4f2c94da62dc38c2b277a951': (31680,187304,True,49152),
}


def audit(root):
    packet = digest(root/'packet.json'); require(packet in PACKETS, 'Exact failed packet')
    expected_head, expected_peak, cleanup_sent, replay_written = PACKETS[packet]
    p, values = inputs(root, packet)
    rows = journal(root/'idle.jsonl')
    require(rows[0]['value'] == dict(packet_sha256=packet), 'Packet trace binding')
    schema = json.loads((root/'docs/protocol/wtp-1.schema.json').read_text())
    validator = SchemaValidator(schema)
    requests = {}; written = {}; replies = {}; wire = b''
    console = b''; pending = False; decoded = None; info = []
    for row in rows:
        k, v = row['kind'], row['value']
        if k == 'usb_tx':
            messages, left = frames(bytes.fromhex(v['hex'])); label = v['label']
            require(not left and messages == [v['request']] and label not in requests and
                    not validator.errors(messages[0], schema), 'Exact request framing/schema/CRC')
            require(messages[0]['op'] in ('HELLO','CLAIM','LOAD','ABORT','RELEASE','STATUS'), 'Zero-RF operations')
            requests[label] = messages[0]; written[label] = 0; replies[label] = []
        elif k == 'usb_write':
            label = v['label']; written[label] += v['bytes']
            require(v['bytes'] > 0 and written[label] == v['total_written'], 'Complete write accounting')
        elif k == 'usb_rx':
            label = v['label']; messages, wire = frames(wire+bytes.fromhex(v['hex']))
            for m in messages:
                require(not validator.errors(m, schema) and m['session_id'] == requests[label]['session_id'], 'Reply/event schema/session')
                if m['type'] == 'response':
                    require(m['ok'] is True and all(m[x] == requests[label][x] for x in ('op','request_id')), 'Reply identity/outcome')
                    replies[label].append(m)
                else:
                    require(m['boot_id'] == p['boot_id'] and m['event'] in ('JOB_STATE','OWNER_RELEASED'), 'Idle event identity')
        elif k == 'console_tx':
            require(not pending and not console and decoded is None and bytes.fromhex(v['hex']) == b'INFO\n', 'Single-flight INFO')
            pending = True
        elif k == 'console_rx':
            require(pending, 'Solicited INFO bytes'); console += bytes.fromhex(v['hex'])
            if b'\n' in console:
                require(console.endswith(b'\n') and console.count(b'\n') == 1, 'INFO framing')
                decoded = loads_console(console.decode().strip()); console = b''; pending = False
        elif k == 'info':
            require(decoded == v['value'], 'Raw INFO agreement'); info.append(decoded); decoded = None
    expected = ['hello']
    for i in range(3):
        expected += [f'claim-{i}', f'load-{i}']
        if i < 2: expected += [f'abort-{i}', f'release-{i}', f'retained-{i}']
    expected += ['fresh-id-replay']
    if cleanup_sent: expected += ['cleanup-HELLO','cleanup-CLAIM','cleanup-RELEASE']
    require(list(requests) == expected, 'Exact finite sequence')
    for i in range(3):
        label = f'load-{i}'; q = requests[label]
        require(q['body'] == p['jobs'][i] and written[label] == 52105 and len(replies[label]) == 1, 'Three complete maximum LOADs')
        body = replies[label][0]['body']
        require(body['job_id'] == p['jobs'][i]['job_id'] and body['state'] == 'loaded' and
                body['adjustments'] == [dict(event_index=n,
                    requested_frequency_nhz=str(135500000000000 if n%2 == 0 else 135495000000000),
                    realized_frequency_nhz=str(135500002652407 if n%2 == 0 else 135494990274310)) for n in range(512)], 'All exact adjustments')
    require(requests['fresh-id-replay']['body'] == p['jobs'][-1] and written['fresh-id-replay'] == replay_written and
            not replies['fresh-id-replay'] and not wire, 'Exact replay write prefix without complete reply')
    require(not pending and not console and decoded is None and info, 'Complete INFO observer prefix')
    for v in info + [values['final-a']['info']]:
        require(v['device_id'] == BOARDS['a'][1] and v['revision'] == p['source_revision'][:12] and
                v['status']['boot_id'] == p['boot_id'] and v['status']['output_active'] is False and
                v['status']['enabled'] is False and v['launch_epoch'] == '0' and v['allocator_failures'] == '0' and
                v['tls_allocation_failures'] == 0 and all(v[k] == 0 for k in
                ('fault_stage','fault_hash','fault_pc','fault_status','dma_irqs','alarm_irqs','tail_irqs')), 'Identity, no RF and no allocation failure/fault')
    final = {}
    for b, (serial, device) in BOARDS.items():
        path = root/('reconciled-final-'+b+'.stdout')
        final[b] = audit_inventory(path, dict(serial=serial,device_id=device),
            p['b_session' if b == 'b' else 'inventory_session'], p['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not path.with_suffix('.stderr').read_bytes() and configuration(final[b]) == configuration(values['before-'+b]), 'Fresh reconciliation/configuration')
    identities = inactive(final)
    f = final['a']['info']; headroom = f['heap_capacity_bytes'] - f['allocator_peak_bytes']
    require(headroom == expected_head and headroom < 32768 and f['allocator_peak_bytes'] == expected_peak, 'Preserved failed reserve')
    require({t['job_id'] for t in final['a']['wtp']['STATUS']['terminal_records']} == {j['job_id'] for j in p['jobs']} and
            all(t['state'] == 'aborted' and t['output_active'] is False for t in final['a']['wtp']['STATUS']['terminal_records']), 'Three inactive terminal records')
    reservation = json.loads((root/'reservation-reconciled.json').read_text())
    require(reservation['state'] == 'RELEASED' and reservation['packet_sha256'] == packet and
            reservation['boards'] == identities and reservation['host_boot'] == p['host_boot_id'], 'Same packet reconciled release')
    native, metrics = native_wire(root,p,root/'pi/phase115_tls_observer_test.py')
    require(native and all(s['value']['output_active'] is False for s in native), 'Independent native inactive prefix')
    result = json.loads((root/'run-result.json').read_text())
    require(result == rows[-1]['value'] and result['status'] == 'FAILED' and result['rf_jobs'] == 0 and
            ((not result.get('cleanup_error') and result['reconciliation_error']=='Extended candidate identity/capacity/resource') if cleanup_sent else result['cleanup_error']=='Observed allocator reserve'), 'Failure and cleanup defect preserved')
    require([bytes.fromhex(r['value']['hex']) for r in rows if r['kind']=='cleanup_tx']==([b'INFO\n',b'ABORT\n'] if cleanup_sent else [b'INFO\n']), 'Exact cleanup command count')
    return dict(status='REPLAY_RESERVE_FAILURE_CONFIRMED', packet_sha256=packet,
        source_revision=p['source_revision'],boot_id=p['boot_id'],maximum_load_replies=3,
        replay_request_bytes=replay_written,replay_accepted=False,cleanup_abort_sent=cleanup_sent,allocator_peak_bytes=f['allocator_peak_bytes'],
        allocator_headroom_bytes=headroom,required_headroom_bytes=32768,rf_jobs=0,
        native_prefix=metrics,capacity_acceptance=False,reservation_released=True,
        configurations_preserved=True,schedules_disabled=True)
