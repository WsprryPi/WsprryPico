"""Independent raw-wire B deployment/functional audit; never A RF acceptance."""
import json
from pathlib import Path
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_pilot import Decoder
from phase11_5_pilot_supervisor import configuration
from phase11_5_r3_preflight import audit_inventory
from audit_phase11_5_r3_capacity_probe import rows
from audit_phase11_5_r3_v2_admission import decode_requests
from phase11_5_r3_v2_parallel_b_plan import B_SERIAL, B_DEVICE, SOURCE, PEER_SHA, stimuli
from validate_wtp_contract import SchemaValidator


def inventory(root, packet, name, deployed=True):
    value=audit_inventory(root/(name+'.stdout'),dict(serial=B_SERIAL,device_id=B_DEVICE),
        packet['inventory_session'],packet['stage_sha256']['scripts/phase11_5_inventory.py'])
    require(not (root/(name+'.stderr')).read_bytes(),'B inventory stderr')
    info=value['info'];status=value['wtp']['STATUS'];caps=value['wtp']['CAPS']
    require(status['state']==info['status']['state']=='empty' and
            status['output_active'] is info['status']['output_active'] is False and
            status['owner_id'] is status['job_id'] is None and info['status']['enabled'] is False and
            info['status']['storage_healthy'] is True and info['status']['last_error'] is None,
            'B inactive/scheduling authority')
    if deployed:
        require(info['revision']==SOURCE[:12] and info['status']['engine']=='pio-dma-gp2' and
                info['system_clock_hz']==138000000 and info['rf_render_in_ram'] is True and
                info['recovery_boot'] is False and
                all(info[k]==0 for k in ('fault_stage','fault_hash','fault_pc','fault_status')) and
                int(info['allocator_failures'])==0 and
                info['heap_capacity_bytes']-info['allocator_peak_bytes']>=32768,
                'B image/resource identity')
        require(caps['max_events']==512 and int(caps['max_job_duration_ns'])==3600_000_000_000 and
                caps['max_payload_bytes']==65536,'B extended capabilities')
        require(all(int(info[k])==0 for k in ('launch_epoch','dma_irqs','alarm_irqs','tail_irqs')),
                'B unexpected RF activity')
        for core in (0,1):
            require(type(info[f'core{core}_stack_guard_valid']) is int and
                    info[f'core{core}_stack_guard_valid']==1 and info[f'core{core}_stack_fault_status']==0 and
                    info[f'core{core}_stack_guard_limit']-info[f'core{core}_stack_guard_bottom']==4096,
                    'B stack guard')
    return value


def saved(value):
    station,network=configuration(value)
    return station,{k:network[k] for k in ('configured_hostname','control_configured')}


def deployment(root, expected_packet):
    require(digest(root/'packet.json')==expected_packet,'Frozen B deployment packet')
    packet=json.loads((root/'packet.json').read_text())
    before=inventory(root,packet,'before-b',False)
    after=inventory(root,packet,'after-flash-b');final=inventory(root,packet,'final-b')
    boot=after['wtp']['STATUS']['boot_id']
    require(before['info']['revision']==packet['prior_revision']=='dbf1d86f0885-dirty' and
            before['wtp']['STATUS']['boot_id']==packet['prior_boot'] and boot!=packet['prior_boot'] and
            final['wtp']['STATUS']['boot_id']==boot and saved(before)==saved(after)==saved(final),
            'B deployment boot/configuration')
    trace=rows(root/'deployment.jsonl');kinds=[r['kind'] for r in trace]
    require(trace[0]['kind']=='start' and trace[0]['value']==dict(packet_sha256=expected_packet) and
            trace[-1]['kind']=='finish' and 'failure' not in kinds and
            trace[-1]['monotonic_ns']-trace[0]['monotonic_ns']<=450_000_000_000,'B trace boundary')
    require(all(k in {'start','finish','bootsel_pending','bootsel_acknowledged','flash_pending',
                      'flash_exit','tx','rx','bootsel_disconnect_cleanup'} for k in kinds),
            'B undeclared deployment activity')
    for kind in ('bootsel_pending','bootsel_acknowledged','flash_pending','flash_exit'):
        require(kinds.count(kind)==1,'B one flash/BOOTSEL')
    tx=[bytes.fromhex(r['value']['hex']) for r in trace if r['kind']=='tx']
    rx=b''.join(bytes.fromhex(r['value']['hex']) for r in trace if r['kind']=='rx')
    require(tx==[b'BOOTSEL\n'] and json.loads(rx)==dict(ok=True,rebooting=True),'B BOOTSEL bytes')
    flash=next(r['value'] for r in trace if r['kind']=='flash_pending')
    require(flash==dict(argv=['/home/pi/phase11-4-e1/picotool-build/picotool','load','-v','-x',
                packet['root']+'/candidate.uf2','--ser',B_SERIAL],sha256=packet['image_sha256']) and
            next(r['value'] for r in trace if r['kind']=='flash_exit')==dict(exit=0),'B flash binding')
    text=(root/'flash.stdout').read_text()
    require('Verifying Flash:' in text and '100%\n  OK' in text and
            'The device was rebooted to start the application.' in text and
            not (root/'flash.stderr').read_bytes(),'B verified flash output')
    result=json.loads((root/'deployment-result.json').read_text())
    require(result==trace[-1]['value'] and result['status']=='OBSERVED_REQUIRES_INDEPENDENT_AUDIT' and
            result['flashes_started']==result['bootsel_commands']==1 and result['boot_id']==boot and
            all(result[k]==0 for k in ('rf_jobs','arm_commands','loads','configuration_writes','wifi_cycles')),
            'B deployment result')
    return dict(status='B_DEPLOYMENT_VERIFIED',packet_sha256=expected_packet,source_revision=SOURCE,
                image_sha256=packet['image_sha256'],boot_id=boot,rf_jobs=0,rf_acceptance=False)


def functional(root, expected_packet):
    require(digest(root/'packet.json')==expected_packet,'Frozen B functional packet')
    packet=json.loads((root/'packet.json').read_text());plan=stimuli(packet['seed'])
    require(packet['stimuli']==plan,'B frozen stimuli')
    values=[inventory(root,packet,name) for name in ('before-b','after-http-b','final-b')]
    boot=packet['boot_id'];require(all(v['wtp']['STATUS']['boot_id']==boot for v in values),'B boot continuity')
    require(saved(values[0])==saved(values[1])==saved(values[2]),'B saved config continuity')
    trace=rows(root/'functional.jsonl')
    require(trace[0]['kind']=='start' and trace[0]['value']==dict(packet_sha256=expected_packet) and
            trace[-1]['kind']=='finish' and not any(r['kind']=='failure' for r in trace) and
            trace[-1]['monotonic_ns']-trace[0]['monotonic_ns']<=750_000_000_000,'B functional trace boundary')
    require(all(r['kind'] in {'start','finish','http_tx','http_write_complete','http_response',
                             'usb_tx','usb_write','usb_rx','usb_message'} for r in trace),
            'B undeclared functional activity')
    http=[];current=None
    for row in trace:
        kind,v=row['kind'],row['value']
        if kind=='http_tx':
            require(current is None and v==plan['http_cases'][len(http)],'B HTTP stimulus order')
            current=dict(case=v,tx=row,written=False)
        elif kind=='http_write_complete':
            require(current is not None and not current['written'] and
                    v==dict(label=current['case']['label'],bytes=len(bytes.fromhex(current['case']['wire_hex']))),
                    'B offered HTTP byte count');current['written']=True
        elif kind=='http_response':
            require(current is not None and current['written'] and
                    v['label']==current['case']['label'] and v['peer_sha256']==PEER_SHA and
                    v['status']==current['case']['expected_status'] and
                    row['monotonic_ns']-current['tx']['monotonic_ns']<=15_000_000_000,'B HTTPS response')
            payload=bytes.fromhex(v['body_hex']);headers=v['headers']
            lengths=[x for k,x in headers if k.lower()=='content-length']
            require(len(lengths)==1 and int(lengths[0])==len(payload) and
                    not any(k.lower()=='transfer-encoding' for k,x in headers), 'B HTTP body length')
            body=json.loads(payload);case=current['case']
            if v['status']==200:
                request=json.loads(bytes.fromhex(case['wire_hex']).split(b'\r\n\r\n',1)[1])
                require(body['ok'] is True and body['request_id']==request['request_id'] and
                        body['result']['device_id']==B_DEVICE and body['result']['boot_id']==boot,'B HTTP identity')
            if case['error_code']:
                require(body['error']['code']==case['error_code'] and
                        (case['error_code']=='invalid_http' or body.get('ok') is False),'B HTTP error')
            http.append(body);current=None
    require(current is None and len(http)==6 and http[0]==http[1],'B HTTP completeness/replay')
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator=SchemaValidator(schema);decoder=Decoder();decoded=[];transactions=[];current=None
    for row in trace:
        kind,v=row['kind'],row['value']
        if kind=='usb_tx':
            require(current is None or current['response'] is not None,'B missing USB response')
            require(v==plan['usb_cases'][len(transactions)],'B USB frozen sequence')
            raw=bytes.fromhex(v['wire_hex']);requests=decode_requests(raw)
            require(requests[-1][1]==v['request'] and all(q['op']!='ARM' for _,q in requests),'B USB request bytes')
            current=dict(case=v,tx=row,raw=raw,written=0,response=None,invalid=0);transactions.append(current)
        elif kind=='usb_write':
            require(current is not None and current['response'] is None and type(v['bytes']) is int and
                    0<v['bytes']<=4096 and v['total_written']==current['written']+v['bytes'], 'B USB write accounting')
            current['written']+=v['bytes'];require(current['written']<=len(current['raw']),'B USB excess bytes')
        elif kind=='usb_rx':decoded.extend(decoder.feed(bytes.fromhex(v['hex'])))
        elif kind=='usb_message':
            require(current is not None and decoded and decoded.pop(0)==v and not validator.errors(v,schema) and
                    v['session_id']==plan['usb_session'],'B raw/decoded response')
            if v['type']=='event':
                require(v['boot_id']==boot and v['event'] in ('INVALID_FRAME','JOB_STATE','OWNER_RELEASED'), 'B event')
                current['invalid']+=v['event']=='INVALID_FRAME'
                if v['event']=='JOB_STATE':require(v['body']['state'] not in ('armed','running') and
                                                  v['body']['output_active'] is False,'B RF state event')
            else:
                request=current['case']['request'];error=current['case']['error']
                require(current['response'] is None and current['written']==len(current['raw']) and
                        all(v[k]==request[k] for k in ('session_id','request_id','op')) and
                        row['monotonic_ns']-current['tx']['monotonic_ns']<=5_000_000_000,'B USB response binding')
                require((error is None and v['ok'] is True) or
                        (error is not None and v['ok'] is False and v['error']['code']==error),'B USB outcome')
                current['response']=v
    require(len(transactions)==13 and not decoded and not decoder.buffer and
            all(t['response'] is not None and t['invalid']==t['case']['invalid_frames'] for t in transactions),
            'B USB completeness')
    responses=[t['response'] for t in transactions]
    for index,state,owner,job in [(1,'empty',None,None),(2,'empty',None,None),
            (5,'empty',plan['owner_id'],None),(7,'empty',plan['owner_id'],None),
            (9,'loaded',plan['owner_id'],plan['job_id']),(12,'empty',None,None)]:
        value=responses[index]['body']
        require(value['boot_id']==boot and value['state']==state and value['owner_id']==owner and
                value['job_id']==job and value['output_active'] is False,'B exact inactive authority')
    require(responses[0]['body']['device_id']==B_DEVICE and responses[0]['body']['boot_id']==boot and
            responses[8]['body']['job_id']==plan['job_id'] and responses[8]['body']['state']=='loaded' and
            len(responses[8]['body']['adjustments'])==512 and
            responses[12]['body']==values[-1]['wtp']['STATUS'],'B maximum/final response')
    result=json.loads((root/'functional-result.json').read_text())
    require(result==trace[-1]['value'] and result['status']=='OBSERVED_REQUIRES_INDEPENDENT_AUDIT' and
            result['passed_cases']==[c['label'] for c in plan['http_cases']+plan['usb_cases']] and
            result['accepted_loads']==1 and result['rf_jobs']==result['arm_commands']==0,'B result claims')
    return dict(status='B_IDLE_FUNCTIONAL_VERIFIED',packet_sha256=expected_packet,source_revision=SOURCE,
        image_sha256=packet['image_sha256'],boot_id=boot,passed_cases=result['passed_cases'],
        accepted_loads=1,rf_jobs=0,a_under_rf_acceptance=False)
