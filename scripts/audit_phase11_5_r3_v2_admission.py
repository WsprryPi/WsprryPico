"""Independent E0a raw-wire audit; idle credit, no RF or whole-family closure."""
import json
from pathlib import Path
import struct
from phase11_5_inventory import require
from phase11_5_device_management import digest
from phase11_5_pilot import Decoder, SERIAL, DEVICE
from phase11_5_pilot_supervisor import B_SERIAL, B_DEVICE, configuration
from phase11_5_r3_preflight import audit_inventory
from audit_phase11_5_r3_capacity_probe import rows
from validate_wtp_contract import crc32c, loads_strict, SchemaValidator

PACKET='ddfb38d310f2eb30f5888380013bc87c91e9bbb84d77ef6883a7cea8abb2ec53'
ASSERTIONS=['clean_extended_image_idle','wtp_65536_full_write',
 'wtp_65537_rejected_same_connection_recovered','events_513_atomic_rejection',
 'duration_3600_plus_ns_atomic_rejection','events_512_duration_3600_idle_load','loaded_abort_release']


def decode_requests(raw):
    result=[]
    while raw:
        require(len(raw)>=16,'Truncated request header')
        magic,version,encoding,flags,size,crc=struct.unpack('>4sBBHII',raw[:16])
        require((magic,version,encoding,flags)==(b'WTPF',1,1,0) and 0<size<=65537 and
                len(raw)>=16+size,'Request framing/length')
        payload=raw[16:16+size]
        require(crc32c(payload)==crc,'Request CRC')
        result.append((size,loads_strict(payload.decode())))
        raw=raw[16+size:]
    return result


def audit(root, *, packet_digest=PACKET):
    require(packet_digest in [PACKET,'e41c50ae3cef279a28082cdb0ae9de639e57e6f940cf1a0fbe6731b8da8da39d','4f2f3680f88021adfc14b32930eaea575cbbe291045bce3c5f3daa02807d2783','8bd146adfccd861974e86fe669584ef5de221c56826c9a2589b4315a3b6433c1','5b61ffdf74ab0e1f5daa77bef59ea2c3e7d797c128cf8499d3d90c6178965ab0','37a6cd1d990e0c79cc8510a7e5b7fc81e3ac13316de76cabc65b4d2dfa7f7207'],
            'Unreviewed idle admission packet')
    require(digest(root/'packet.json')==packet_digest,'Frozen idle admission packet')
    packet=json.loads((root/'packet.json').read_text());values={}
    for name in ['before-a','before-b','after-flash-a','final-a','final-b']:
        b=name.endswith('-b')
        value=audit_inventory(root/(name+'.stdout'),dict(serial=B_SERIAL if b else SERIAL,
            device_id=B_DEVICE if b else DEVICE),packet['b_session'] if b else packet['a_session'],
            packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not (root/(name+'.stderr')).read_bytes(),'Inventory stderr')
        info,status=value['info'],value['wtp']['STATUS']
        require(status['state']==info['status']['state']=='empty' and
                status['output_active'] is info['status']['output_active'] is False and
                status['owner_id'] is status['job_id'] is None and info['status']['enabled'] is False and
                info['status']['storage_healthy'] is True and info['status']['last_error'] is None,
                'Inactive authority/configuration')
        values[name]=value
    old,after,final=(values[k] for k in ['before-a','after-flash-a','final-a'])
    boot=after['wtp']['STATUS']['boot_id']
    require(old['wtp']['STATUS']['boot_id']==packet['prior_boot'] and
            old['info']['revision']==packet['prior_revision'][:12] and boot!=packet['prior_boot'],
            'Prior/deployed identity')
    def saved(value):
        station,network=configuration(value)
        return station,{k:network[k] for k in ['configured_hostname','control_configured']}
    for value in [after,final]:
        i=value['info'];c=value['wtp']['CAPS']
        require(value['wtp']['STATUS']['boot_id']==boot and i['revision']==packet['source_revision'][:12] and
                i['recovery_boot'] is False and all(i[k]==0 for k in ['fault_stage','fault_hash','fault_pc','fault_status']) and
                i['fault_allocation_recorded'] is False and i['fault_allocation_returned_null'] is None and
                i['system_clock_hz']==138000000 and i['rf_render_in_ram'] is True and
                i['status']['engine']=='pio-dma-gp2' and saved(value)==saved(old),'Deployed image/configuration/fault')
        require(c['max_events']==512 and c['max_job_duration_ns']=='3600000000000' and
                c['max_payload_bytes']==65536 and i['allocator_failures']=='0' and
                i['heap_capacity_bytes']-i['allocator_peak_bytes']>=32768,'Capacity and allocator reserve')
        for core in [0,1]:
            require(type(i[f'core{core}_stack_guard_valid']) is int and i[f'core{core}_stack_guard_valid']==1 and
                    i[f'core{core}_stack_fault_status']==0 and
                    i[f'core{core}_stack_guard_limit']-i[f'core{core}_stack_guard_bottom']==4096,'Stack guards')
        require(all(int(i[k])==0 for k in ['launch_epoch','dma_irqs','alarm_irqs','tail_irqs']), 'Unexpected RF work')
    b0,b1=values['before-b'],values['final-b']
    require(configuration(b0)==configuration(b1) and b0['wtp']['STATUS']==b1['wtp']['STATUS'] and
            b0['wtp']['CAPS']==b1['wtp']['CAPS'] and
            b0['wtp']['STATUS']['boot_id']==packet['b_boot'] and
            b0['info']['revision']==b1['info']['revision']==('8921a7008183' if packet_digest in ['e41c50ae3cef279a28082cdb0ae9de639e57e6f940cf1a0fbe6731b8da8da39d','4f2f3680f88021adfc14b32930eaea575cbbe291045bce3c5f3daa02807d2783','37a6cd1d990e0c79cc8510a7e5b7fc81e3ac13316de76cabc65b4d2dfa7f7207','8bd146adfccd861974e86fe669584ef5de221c56826c9a2589b4315a3b6433c1'] else 'dbf1d86f0885-dirty'),'B changed')
    trace=rows(root/'admission.jsonl');kinds=[r['kind'] for r in trace]
    require(trace[0]['kind']=='start' and trace[0]['value']==dict(packet_sha256=packet_digest) and
            trace[-1]['kind']=='finish' and trace[-1]['monotonic_ns']-trace[0]['monotonic_ns']<=600_000_000_000,
            'Trace boundary/deadline')
    require(kinds.count('bootsel_pending')==kinds.count('bootsel_acknowledged')==kinds.count('flash_pending')==
            kinds.count('flash_exit')==1 and 'failure' not in kinds,'Flash/BOOTSEL count/failure')
    tx=next(r for r in trace if r['kind']=='tx');rx=next(r for r in trace if r['kind']=='rx')
    require(bytes.fromhex(tx['value']['hex'])==b'BOOTSEL\n' and
            json.loads(bytes.fromhex(rx['value']['hex']))==dict(ok=True,rebooting=True),'BOOTSEL wire ACK')
    flash=next(r['value'] for r in trace if r['kind']=='flash_pending')
    require(flash==dict(argv=['/home/pi/phase11-4-e1/picotool-build/picotool','load','-v','-x',
            packet['root']+'/candidate.uf2','--ser',SERIAL],sha256=packet['image_sha256']) and
            next(r['value'] for r in trace if r['kind']=='flash_exit')==dict(exit=0),'Flash identity')
    text=(root/'flash.stdout').read_text()
    require('Verifying Flash:' in text and '100%\n  OK' in text and
            'The device was rebooted to start the application.' in text and not (root/'flash.stderr').read_bytes(),
            'Flash verification')
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    validator=SchemaValidator(schema);decoder=Decoder();decoded=[];transactions=[];current=None
    for row in trace:
        kind,v=row['kind'],row['value']
        if kind in ['idle_tx','capacity_tx']:
            require(current is None or current['response'] is not None,'Missing prior response')
            raw=bytes.fromhex(v['hex']);requests=decode_requests(raw)
            require(requests[-1][1]==v['request'] and v['request']['session_id']==packet['peer_session'],
                    'Raw/summary request mismatch')
            current=dict(tx=row,raw=raw,requests=requests,written=0,response=None,events=[])
            transactions.append(current)
        elif kind in ['idle_write','capacity_write']:
            require(current is not None and current['response'] is None and type(v['bytes']) is int and
                    0<v['bytes']<=4096 and v['total_written']==current['written']+v['bytes'], 'Full write accounting')
            current['written']+=v['bytes'];require(current['written']<=len(current['raw']),'Excess write')
        elif kind in ['idle_rx','capacity_rx']:
            decoded.extend(decoder.feed(bytes.fromhex(v['hex'])))
        elif kind in ['idle_message','capacity_message']:
            require(decoded and decoded.pop(0)==v and not validator.errors(v,schema) and
                    v['session_id']==packet['peer_session'],'Raw/summary response mismatch')
            if v['type']=='event':
                require(v['boot_id']==boot and v['event'] in ['INVALID_FRAME','JOB_STATE','OWNER_RELEASED'],
                        'Unexpected event/boot')
                current['events'].append(v)
            else:
                request=current['requests'][-1][1]
                require(current['response'] is None and current['written']==len(current['raw']) and
                        all(v[k]==request[k] for k in ['session_id','request_id','op']) and
                        row['monotonic_ns']-current['tx']['monotonic_ns']<=5_000_000_000,'Response identity/write/deadline')
                current['response']=v
    require(not decoded and not decoder.buffer and all(t['response'] is not None for t in transactions),
            'Unconsumed/missing response bytes')
    require([t['requests'][-1][1]['op'] for t in transactions]==
            ['HELLO','STATUS','STATUS','CLAIM','LOAD','STATUS','LOAD','STATUS','LOAD','STATUS','ABORT','RELEASE','STATUS'],
            'Unexpected/missing operations')
    responses=[t['response'] for t in transactions]
    require(all(r['ok'] is (i not in [4,6]) for i,r in enumerate(responses)), 'Operation outcome')
    require(responses[0]['body']['device_id']==DEVICE and responses[0]['body']['boot_id']==boot,'HELLO identity')
    require(transactions[1]['requests'][0][0]==65536 and len(transactions[1]['requests'])==1 and
            [s for s,_ in transactions[2]['requests']][0]==65537 and len(transactions[2]['requests'])==2 and
            [e['event'] for e in transactions[2]['events']]==['INVALID_FRAME'],'Maximum/oversized framing')
    require(sum(e['event']=='INVALID_FRAME' for t in transactions for e in t['events'])==1,'Extra invalid frame')
    for index,state,owner,job in [(1,'empty',None,None),(2,'empty',None,None),
            (5,'empty',packet['owner_id'],None),(7,'empty',packet['owner_id'],None),
            (9,'loaded',packet['owner_id'],packet['maximum_job_id']),(12,'empty',None,None)]:
        s=responses[index]['body']
        require(s['boot_id']==boot and s['state']==state and s['owner_id']==owner and s['job_id']==job and
                s['output_active'] is False,'Atomic state/authority')
    require(responses[3]['body']['owner_id']==packet['owner_id'] and
            responses[3]['body']['granted_lease_ms']==60000,'Claim scope')
    require(responses[4]['error']['code']=='INVALID_MESSAGE' and
            len(transactions[4]['requests'][0][1]['body']['events'])==513 and
            responses[6]['error']['code']=='JOB_LIMIT_EXCEEDED' and
            transactions[6]['requests'][0][1]['body']['total_duration_ns']=='3600000000001','Boundary rejection')
    require(transactions[8]['requests'][0][1]['body']==packet['maximum_job'] and
            len(packet['maximum_job']['events'])==512 and packet['maximum_job']['total_duration_ns']=='3600000000000',
            'Maximum admitted job')
    adjustments=responses[8]['body']['adjustments']
    require(responses[8]['body']['job_id']==packet['maximum_job_id'] and
            responses[8]['body']['state']=='loaded' and len(adjustments)==512,'Maximum LOAD response')
    require(responses[12]['body']==final['wtp']['STATUS'] and
            len(final['wtp']['STATUS']['terminal_records'])==1 and
            final['wtp']['STATUS']['terminal_records'][0]['job_id']==packet['maximum_job_id'] and
            final['wtp']['STATUS']['terminal_records'][0]['state']=='aborted','Final retained result')
    result=json.loads((root/'admission-result.json').read_text())
    require(result==trace[-1]['value'] and result['status']=='OBSERVED_REQUIRES_INDEPENDENT_AUDIT' and
            result['passed_assertions']==[r['value'] for r in trace if r['kind']=='assertion_observed']==ASSERTIONS and
            result['flashes_started']==result['bootsel_commands']==1 and
            all(result[k]==0 for k in ['rf_jobs','wifi_cycles','configuration_writes','heap_probes']), 'Result counters/claims')
    label = {'e41c50ae3cef279a28082cdb0ae9de639e57e6f940cf1a0fbe6731b8da8da39d':'E5','4f2f3680f88021adfc14b32930eaea575cbbe291045bce3c5f3daa02807d2783':'E4',PACKET:'E0A', '5b61ffdf74ab0e1f5daa77bef59ea2c3e7d797c128cf8499d3d90c6178965ab0':'E1',
        '37a6cd1d990e0c79cc8510a7e5b7fc81e3ac13316de76cabc65b4d2dfa7f7207':'E2',
        '8bd146adfccd861974e86fe669584ef5de221c56826c9a2589b4315a3b6433c1':'E3'}[packet_digest]
    return dict(status=label+'_IDLE_BOUNDARIES_VERIFIED',family_closed=False,packet_sha256=packet_digest,
                source_revision=packet['source_revision'],image_sha256=packet['image_sha256'],boot_id=boot,
                assertions=ASSERTIONS,rf_jobs=0,flashes=1,bootsel_commands=1,b_unchanged=True,
                allocator_peak_bytes=final['info']['allocator_peak_bytes'],
                heap_capacity_bytes=final['info']['heap_capacity_bytes'],
                physical_hour_or_contention_verified=False)
