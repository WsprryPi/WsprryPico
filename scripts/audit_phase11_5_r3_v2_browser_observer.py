"""Independent read-only USB observer evidence for browser-owned jobs."""
import json
from pathlib import Path
from phase11_5_inventory import require,loads_console
from phase11_5_device_management import digest
from phase11_5_pilot_supervisor import configuration,B_SERIAL,B_DEVICE
from phase11_5_pilot import SERIAL,DEVICE
from phase11_5_r3_preflight import audit_inventory
from validate_wtp_contract import SchemaValidator
from audit_phase11_5_idle import frames
from phase11_5_r3_v2_rf import validate_info
from audit_phase11_5_r3_v2_hour import journal


def audit(root,packet):
    inventories={}
    for label in ['before-a','before-b','final-a','final-b']:
        b=label.endswith('-b')
        v=audit_inventory(root/(label+'.stdout'),dict(serial=B_SERIAL if b else SERIAL,device_id=B_DEVICE if b else DEVICE),
            packet['b_session'] if b else packet['inventory_session'],packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not (root/(label+'.stderr')).read_bytes(),'Inventory stderr')
        s=v['wtp']['STATUS'];require(s['boot_id']==(packet['b_boot_id'] if b else packet['boot_id']) and
            s['owner_id'] is None and s['output_active'] is False and
            s['state'] in (['empty','complete','aborted'] if label=='final-a' else ['empty']),'Inventory authority')
        inventories[label]=v
    before=inventories['before-a'];final=inventories['final-a']
    require(configuration(before)==configuration(final) and
        configuration(inventories['before-b'])==configuration(inventories['final-b']) and
        inventories['before-b']['info']['revision']==inventories['final-b']['info']['revision'] and
        inventories['before-b']['wtp']['STATUS']==inventories['final-b']['wtp']['STATUS'],'Preserved A/B')
    validate_info(before['info'],before,packet);validate_info(final['info'],before,packet)
    rows=journal(root/'browser-observer.jsonl')
    require(rows[0]['value']==dict(packet_sha256=digest(root/'packet.json'),baseline_sha256=digest(root/'before-a.stdout'),
        boot_id=packet['boot_id']),'Observer provenance')
    require(all(r['kind'] in ['start','finish','console_tx','console_rx','wtp_tx','wtp_rx','wtp_message',
        'info','status','health','info_finish','status_finish','health_finish','browser_starting'] for r in rows),
        'Observer failure/undeclared operation')
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    pending={};seen=set();wire=b'';messages=[];console=b'';console_pending=None;console_value=None
    latest_status=None;exchanges=[];events=[];event_id=None;samples={}
    for row in rows:
        kind,v=row['kind'],row['value'];stamp=row['monotonic_ns']
        if kind=='console_tx':
            require(console_pending is None and not console and console_value is None and
                    bytes.fromhex(v['hex'])==b'INFO\n','Unexpected Console operation')
            console_pending=stamp
        elif kind=='console_rx':
            require(console_pending is not None,'Unsolicited Console bytes');console+=bytes.fromhex(v['hex'])
            if b'\n' in console:
                require(console.endswith(b'\n') and console.count(b'\n')==1 and stamp-console_pending<=5_000_000_000,
                        'Console response/deadline')
                console_value=loads_console(console.decode().strip());console=b'';console_pending=None
        elif kind=='wtp_tx':
            values,left=frames(bytes.fromhex(v['hex']));require(not left and values==[v['request']],'Request raw/summary')
            request=values[0]
            require(not validator.errors(request,schema) and request['session_id']==packet['peer_session'] and
                    request['request_id'] not in seen and not pending and request['op'] in ['HELLO','STATUS'],'Request schema/session/no retry')
            seen.add(request['request_id']);pending[request['request_id']]=(stamp,request)
        elif kind=='wtp_rx':
            values,wire=frames(wire+bytes.fromhex(v['hex']));messages.extend(values)
        elif kind=='wtp_message':
            require(messages and messages.pop(0)==v and not validator.errors(v,schema) and
                    v['session_id']==packet['peer_session'],'Response raw/summary/schema')
            if v['type']=='event':
                require(v['boot_id']==packet['boot_id'] and v['event'] in ['JOB_STATE','OWNER_RELEASED'] and
                        (event_id is None or int(v['event_id'])==event_id+1),'Event gap/fault/boot')
                event_id=int(v['event_id']);events.append(v);continue
            require(v['ok'] is True and v['request_id'] in pending,'Unmatched/rejected response')
            began,q=pending.pop(v['request_id']);require(q['op']==v['op'] and stamp-began<=5_000_000_000,'Operation/deadline')
            exchanges.append(dict(request=q,response=v,started_ns=began,finished_ns=stamp))
            if q['op']=='STATUS':latest_status=v['body']
            if q['op']=='HELLO':require(v['body']['boot_id']==packet['boot_id'] and v['body']['device_id']==DEVICE,'HELLO identity')
        elif kind in ['info','status','health']:
            samples.setdefault(kind,[]).append(row)
            require(0<=stamp-v['began_monotonic_ns']<=5_000_000_000,'Sample roundtrip')
            if kind=='info':
                require(console_value==v['value'],'INFO not raw');console_value=None;validate_info(v['value'],before,packet)
            elif kind=='status':
                require(latest_status==v['value'] and latest_status['boot_id']==packet['boot_id'],'STATUS not raw/boot');latest_status=None
            else:require(v['value']['boot']==packet['host_boot_id'] and v['value']['throttled']=='throttled=0x0','Host health')
    require(not pending and not wire and not messages and not console and console_pending is None and
            console_value is None and latest_status is None,'Unconsumed/missing wire')
    cadence={}
    for kind,period in [('info',1),('status',5),('health',5)]:
        values=samples.get(kind,[]);require(values,'Missing observation family')
        starts=[r['value']['began_monotonic_ns'] for r in values];gaps=[b-a for a,b in zip(starts,starts[1:])]
        endings=[r for r in rows if r['kind']==kind+'_finish']
        require(len(endings)==1 and endings[0]['value']==dict(samples=len(values)) and
                starts[0]-rows[0]['monotonic_ns']<=(period+1)*10**9 and
                endings[0]['monotonic_ns']-starts[-1]<=(period+1)*10**9 and
                max(gaps,default=0)<=(period+1)*10**9,'Cadence count/start/end/gap')
        cadence[kind]=dict(samples=len(values),max_start_gap_ns=max(gaps,default=0))

    result=json.loads((root/'browser-observer-result.json').read_text())
    require(result==rows[-1]['value'] and result['status']=='CAPTURED_REQUIRES_AUDIT' and result['faults']==[] and
        not (root/'observer-failed.json').exists(),'Observer completion')
    return dict(inventories=inventories,rows=rows,samples=samples,cadence=cadence)
