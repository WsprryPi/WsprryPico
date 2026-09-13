"""Preserve verified HTTP components and exact BF0/BF1 failure classifications."""
import json
from pathlib import Path
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_r3_preflight import audit_inventory
from audit_phase11_5_r3_capacity_probe import rows
from audit_phase11_5_r3_v2_admission import decode_requests
from audit_phase11_5_r3_v2_parallel_b import inventory
from phase11_5_r3_v2_parallel_b_plan import stimuli, B_DEVICE, B_SERIAL, SOURCE, PEER_SHA

PACKETS={
 'd9b6db99ad6d491c780a00c6f34a50a47c2be02de5665bab28c78ee0a5af59dd':4,
 '87032853b769c077555d6869aac10c642d1442c8205809d8b7ac299bddab9bb3':6,
 'e72a6130cf014515af75601b762c8df3cd93faa2d64440d22eef0f55137e17d5':6,
}

def audit(root, expected_packet):
    require(expected_packet in PACKETS and digest(root/'packet.json')==expected_packet,'Frozen stopped B packet')
    packet=json.loads((root/'packet.json').read_text());plan=stimuli(packet['seed'])
    before=inventory(root,packet,'before-b')
    require(before['wtp']['STATUS']['boot_id']==packet['boot_id'],'B original boot')
    trace=rows(root/'functional.jsonl');responses=[r for r in trace if r['kind']=='http_response']
    require(all(r['kind'] in {'start','finish','http_tx','http_write_complete','http_response',
        'usb_tx','usb_write','usb_rx','usb_message','failure'} for r in trace),'Undeclared B activity')
    tx=[r for r in trace if r['kind']=='http_tx'];written=[r for r in trace if r['kind']=='http_write_complete']
    require(len(responses)==len(tx)==len(written)==PACKETS[expected_packet],'Complete HTTP prefix')
    bodies=[]
    for i,(sent,done,row) in enumerate(zip(tx,written,responses)):
        case=plan['http_cases'][i];original=packet['stimuli']['http_cases'][i]
        require(sent['value']==original and original['wire_hex']==case['wire_hex'] and
            done['value']==dict(label=case['label'],bytes=len(bytes.fromhex(case['wire_hex']))) and
            sent['monotonic_ns']<=done['monotonic_ns']<=row['monotonic_ns'] and
            row['monotonic_ns']-sent['monotonic_ns']<=15_000_000_000,'Offered HTTP bytes/deadline')
        v=row['value'];raw=bytes.fromhex(v['body_hex']);body=json.loads(raw)
        lengths=[x for k,x in v['headers'] if k.lower()=='content-length']
        require(v['label']==case['label'] and v['status']==case['expected_status'] and
            v['peer_sha256']==PEER_SHA and lengths==[str(len(raw))] and
            not any(k.lower()=='transfer-encoding' for k,x in v['headers']),'HTTP status/peer/body completeness')
        if case['expected_status']==200:
            request=json.loads(bytes.fromhex(case['wire_hex']).split(b'\r\n\r\n',1)[1])
            require(body['ok'] is True and body['request_id']==request['request_id'] and
                body['result']['device_id']==B_DEVICE and body['result']['boot_id']==packet['boot_id'],
                'HTTP response identity')
        elif case['error_code']:
            require(body['error']['code']==case['error_code'] and
                (case['error_code']=='invalid_http' or body.get('ok') is False),'HTTP error semantics')
        bodies.append(body)
    require(bodies[0]==bodies[1],'Exact HTTP replay')
    result=json.loads((root/'functional-result.json').read_text())
    require(trace[0]['value']==dict(packet_sha256=expected_packet) and trace[-1]['value']==result and
        sum(r['kind']=='failure' for r in trace)==1 and result['rf_jobs']==result['arm_commands']==0,
        'Original failure retained')
    summary=dict(status='STOPPED_B_COMPONENTS_VERIFIED',packet_sha256=expected_packet,
        source_revision=packet['source_revision'],boot_id=packet['boot_id'],http_assertions=[c['label'] for c in plan['http_cases'][:len(responses)]],
        original_result_status=result['status'],rf_jobs=0,full_functional_pass=False)
    if len(responses)==4:
        require(result['error']=='ValueError: B HTTP outcome' and result['status']=='STOPPED_REQUIRES_DIAGNOSIS' and
            original['expected_status']==413 and not any(r['kind'].startswith('usb_') for r in trace),
            'BF0 wrong 413 expectation before USB')
        final=inventory(root,packet,'final-b');require(final['wtp']['STATUS']==before['wtp']['STATUS'],'BF0 inactive unchanged boot')
        summary['classification']='HARNESS_EXPECTATION_ERROR'
    else:
        require(result['status']=='STOPPED_FINAL_STATE_UNVERIFIED' and
            result['error']=='TimeoutError: B five-second USB exchange; no retry','BF1 original timeout')
        middle=inventory(root,packet,'after-http-b');require(middle['wtp']['STATUS']['boot_id']==packet['boot_id'],'BF1 pre-LOAD boot')
        sent=[r for r in trace if r['kind']=='usb_tx'];require(len(sent)==9,'BF1 maximum LOAD is final operation')
        for row,case in zip(sent,plan['usb_cases']):require(row['value']==case,'BF1 exact predeclared USB operations')
        last=sent[-1];wire=bytes.fromhex(last['value']['wire_hex']);decoded=decode_requests(wire)
        require(len(decoded)==1 and decoded[0][1]==plan['usb_cases'][8]['request'],'BF1 full CRC LOAD frame')
        count=0
        for row in trace:
            if row['monotonic_ns']>last['monotonic_ns'] and row['kind']=='usb_write':
                v=row['value'];require(0<v['bytes']<=4096 and v['total_written']==count+v['bytes'],'BF1 full write accounting');count+=v['bytes']
        require(count==len(wire) and not any(r['kind']=='usb_message' and
            r['monotonic_ns']>last['monotonic_ns'] for r in trace),'BF1 full write with no response')
        safe_failure=expected_packet=='e72a6130cf014515af75601b762c8df3cd93faa2d64440d22eef0f55137e17d5'
        final=audit_inventory(root/'diagnostic-b.stdout',dict(serial=B_SERIAL,device_id=B_DEVICE),
            '6fbf946122e21cee9ab6dfcd0c38aff7' if safe_failure else '63a026c0202c0574b144fc3d4a8c544d',
            packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        info=final['info'];status=final['wtp']['STATUS']
        if safe_failure:
            loaded=audit_inventory(root/'final-b.stdout',dict(serial=B_SERIAL,device_id=B_DEVICE),
                packet['inventory_session'],packet['stage_sha256']['scripts/phase11_5_inventory.py'])
            observed=loaded['wtp']['STATUS']
            require(observed['boot_id']==packet['boot_id'] and observed['state']=='loaded' and
                observed['output_active'] is False and observed['job_id']==plan['job_id'] and
                observed['owner_id']==plan['owner_id'],'BF2 known inactive Loaded state')
            for i in (info,loaded['info']):
                require(i['revision']==packet['source_revision'][:12]=='48ef82c7dedf' and
                    i['recovery_boot'] is False and i['fault_stage']==i['fault_hash']==0 and
                    i['fault_allocation_recorded'] is False and int(i['allocator_failures'])==1,
                    'BF2 nullable failure without panic')
            require(not (root/'diagnostic-b.stderr').read_bytes() and not (root/'final-b.stderr').read_bytes() and
                status['boot_id']==packet['boot_id'] and status['state']=='empty' and
                status['output_active'] is False and status['owner_id'] is status['job_id'] is None and
                len(status['terminal_records'])==1 and status['terminal_records'][0]['job_id']==plan['job_id'] and
                status['terminal_records'][0]['state']=='aborted' and
                status['terminal_records'][0]['output_active'] is False,'BF2 same-boot final inactive state')
            summary.update(classification='FIRMWARE_OUTPUT_ALLOCATION_REJECTED_WITHOUT_RESET',
                maximum_load_frame_bytes=count,loaded_state=observed,final_state=status,
                allocator_failures=1,panic_protection_verified=True,maximum_load_reply_pass=False)
            return summary
        require(not (root/'diagnostic-b.stderr').read_bytes() and info['revision']==SOURCE[:12] and
            info['recovery_boot'] is True and info['fault_stage']==5 and info['fault_hash']==3833354787 and
            info['fault_allocation_recorded'] is True and info['fault_allocation_request_bytes']==54917 and
            info['fault_allocation_returned_null'] is True,'BF1 allocation panic breadcrumbs')
        require(status['boot_id']!=packet['boot_id'] and status['state']=='empty' and status['output_active'] is False and
            status['owner_id'] is status['job_id'] is None,'BF1 authoritative reconciled recovery state')
        summary.update(classification='FIRMWARE_ALLOCATION_PANIC',failed_allocation_bytes=54917,
            maximum_load_frame_bytes=count,diagnostic_boot_id=status['boot_id'],final_state=status)
    return summary
