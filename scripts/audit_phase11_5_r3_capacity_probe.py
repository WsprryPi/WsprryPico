"""Raw C0 idle capacity audit; no RF acceptance credit."""
import json
from pathlib import Path

from phase11_5_inventory import require, loads_console
from phase11_5_device_management import digest, admit
from phase11_5_r3_capacity_probe import validate, BOOT, SOURCE, SERIAL, DEVICE, B_SERIAL, B_DEVICE
from phase11_5_r3_capacity_plan import wtp_capacity_frame
from phase11_5_r3_preflight import audit_inventory, decode_frame
from phase11_5_pilot import Decoder
from phase11_5_pilot_supervisor import idle, configuration
from phase11_5_rf_observer import validate_info
from validate_wtp_contract import frame, loads_strict, SchemaValidator


def rows(path):
    text = path.read_text()
    require(text.endswith('\n'), 'Truncated C0 trace')
    result = [loads_console(line) for line in text.splitlines()]
    require(result and [r['sequence'] for r in result] == list(range(len(result))) and
            all(type(r['monotonic_ns']) is int for r in result) and
            all(a['monotonic_ns'] <= b['monotonic_ns'] for a,b in zip(result,result[1:])), 'C0 chronology')
    return result


def audit(root, packet_sha):
    require(digest(root/'packet.json') == packet_sha, 'Different C0 packet')
    packet = validate(loads_strict((root/'packet.json').read_text()))
    schema=loads_strict((root/'docs/protocol/wtp-1.schema.json').read_text())
    validator=SchemaValidator(schema)
    for name, sha in packet['stage_sha256'].items():
        require((root/name).resolve().is_relative_to(root.resolve()) and digest(root/name) == sha, 'C0 tooling changed')
    inventories, traces = {}, {}
    for name in ('before-b', 'before-a', 'after-a', 'after-b'):
        b = name.endswith('-b')
        value = audit_inventory(root/(name+'.stdout'),
            dict(serial=B_SERIAL if b else SERIAL,device_id=B_DEVICE if b else DEVICE),
            packet['b_inventory_session_id'] if b else packet['inventory_session_id'],
            packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not (root/(name+'.stderr')).read_bytes(), 'C0 inventory stderr')
        idle(value)
        require(value['wtp']['STATUS']['boot_id'] == (packet['b_boot_id'] if b else BOOT), 'C0 boot')
        inventories[name] = value; traces[name] = rows(root/(name+'.stdout'))
    for board in ('a', 'b'):
        before, after = inventories['before-'+board], inventories['after-'+board]
        require(configuration(before) == configuration(after) and before['wtp']['CAPS'] == after['wtp']['CAPS'],
                'C0 identity/configuration/CAPS changed')
        require(before['info']['revision']==after['info']['revision'] and
                before['info']['status']['engine']==after['info']['status']['engine'] and
                before['info']['system_clock_hz']==after['info']['system_clock_hz'], 'C0 board source/engine/clock')
        for key in ('launch_epoch','dma_irqs','alarm_irqs','tail_irqs'):
            require(before['info'][key] == after['info'][key], 'C0 unexpected RF work')
    before, after = inventories['before-a'], inventories['after-a']
    admit(after,before,SOURCE);validate_info(before['info'],before);validate_info(after['info'],before)
    require(before['wtp']['CAPS']['max_payload_bytes'] == 65536 and
            before['info']['allocator_largest_successful_request_bytes'] < 65552 and
            after['info']['allocator_largest_successful_request_bytes'] == 65552, 'C0 new maximum allocation not proved')
    trace = rows(root/'capacity.jsonl')
    require(trace[0]['kind']=='start' and trace[0]['value']=={'packet_sha256':packet_sha} and
            trace[-1]['kind']=='finish', 'C0 boundaries')
    require(traces['before-b'][-1]['monotonic_ns'] <= traces['before-a'][0]['monotonic_ns'] and
            traces['before-a'][-1]['monotonic_ns'] <= trace[0]['monotonic_ns'] <= trace[-1]['monotonic_ns'] <=
            traces['after-a'][0]['monotonic_ns'] and
            traces['after-a'][-1]['monotonic_ns'] <= traces['after-b'][0]['monotonic_ns'] and
            traces['after-b'][-1]['monotonic_ns']-traces['before-b'][0]['monotonic_ns'] <= 300000000000,
            'C0 overall order/deadline')
    position = 1
    messages = []
    for index, operation in enumerate(('HELLO','STATUS','PING','STATUS')):
        prefix = 'wtp' if index in (0,3) else 'capacity'
        start = trace[position];position += 1
        require(start['kind'] == prefix+'_tx', 'C0 missing operation')
        value = start['value'];raw = bytes.fromhex(value['hex']);request = value['request']
        require(not validator.errors(request,schema),'C0 request schema')
        require(request['op'] == operation and request['session_id'] == packet['peer_session_id'], 'C0 operation/session')
        if index == 1:
            require(raw == wtp_capacity_frame(packet['peer_session_id'],packet['maximum_request_id']) and
                    value['expected_invalid_frames'] == 0 and decode_frame(raw) == request, 'C0 maximum raw bytes')
        elif index == 2:
            require(request['request_id'] == packet['recovery_request_id'] and request['body']=={'token':'C0-after-oversize'} and
                    value['expected_invalid_frames']==1 and raw ==
                    wtp_capacity_frame(packet['peer_session_id'],packet['oversized_request_id'],True) +
                    frame(json.dumps(request,separators=(',',':')).encode()), 'C0 oversized/recovery raw bytes')
        else:
            require(decode_frame(raw) == request, 'C0 ordinary raw request')
        decoder = Decoder();decoded=[];logged=[];written=0
        while position < len(trace) and trace[position]['kind'] in (prefix+'_rx',prefix+'_message','capacity_write'):
            row=trace[position];position+=1
            if row['kind']=='capacity_write':
                require(prefix=='capacity' and type(row['value']['bytes']) is int and 0<row['value']['bytes']<=4096,
                        'C0 write progress shape')
                written+=row['value']['bytes']
                require(row['value']['total_written']==written<=len(raw),'C0 write progress count')
            elif row['kind'].endswith('_rx'):decoded.extend(decoder.feed(bytes.fromhex(row['value']['hex'])))
            else:logged.append(row['value'])
        require(prefix!='capacity' or written==len(raw),'C0 incomplete host writes')
        require(not decoder.buffer and decoded == logged and decoded and
                all(not validator.errors(m,schema) for m in decoded) and
                trace[position-1]['monotonic_ns']-start['monotonic_ns']<=5000000000, 'C0 raw response/deadline')
        events=[m for m in decoded if m['type']=='event'];replies=[m for m in decoded if m['type']=='response']
        require(len(events)==(1 if index==2 else 0) and len(replies)==1 and
                all(m['session_id']==request['session_id'] for m in decoded), 'C0 event/response cardinality')
        if events:require(events[0]['event']=='INVALID_FRAME' and events[0]['boot_id']==BOOT, 'C0 rejection event')
        reply=replies[0]
        require(reply['ok'] is True and reply['op']==operation and reply['request_id']==request['request_id'], 'C0 response identity')
        body=reply['body'];messages.append(body)
        if index==0:require(body['boot_id']==BOOT and body['device_id']==DEVICE, 'C0 HELLO')
        elif index==2:require(body==request['body'], 'C0 recovery token')
        else:
            require(body['boot_id']==BOOT and body['state']=='empty' and body['output_active'] is False and
                    body['owner_id'] is None and body['job_id'] is None, 'C0 output authority')
        if index==1:
            require(trace[position]['kind']=='maximum_admitted' and trace[position]['value']==body,'C0 admission summary')
            position+=1
    require(position==len(trace)-1 and trace[-1]['value']==dict(status='CAPTURED_REQUIRES_AUDIT',final_status=messages[-1]),
            'C0 extra traffic/finish summary')
    expected=dict(status='CAPTURED_REQUIRES_AUDIT',rf_jobs=0,configuration_writes=0,wifi_cycles=0,flashes=0,
                  device_inactive_unowned=True,b_unchanged=True,final_status=after['wtp']['STATUS'],
                  largest_successful_request_bytes=65552)
    require(loads_strict((root/'capacity-result.json').read_text())==expected,'C0 final supervisor')
    return dict(status='PASS_C0_IDLE_CAPACITY',packet_sha256=packet_sha, family_closed=False,
                maximum_payload_bytes=65536, rejected_payload_bytes=65537, same_connection_recovery=True,
                largest_successful_request_bytes=65552,
                allocator_peak_bytes=after['info']['allocator_peak_bytes'],
                heap_capacity_bytes=after['info']['heap_capacity_bytes'],
                final_heap_allocated_bytes=after['info']['heap_allocated_bytes'],
                rf_jobs=0,configuration_writes=0,wifi_cycles=0,flashes=0,
                final_status=after['wtp']['STATUS'],b_unchanged=True,
                limitation='Idle USB advertised capacity only; contention remains unqualified')
