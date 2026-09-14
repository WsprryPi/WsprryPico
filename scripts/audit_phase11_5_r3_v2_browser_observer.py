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
from phase11_5_r3_v2_rf import validate_info,comparator_required
from audit_phase11_5_r3_v2_hour import journal
from phase11_5_r3_v2_observer_policy import SINGLE_FLIGHT,validate_intervals


def audit(root,packet,*,prefix='browser',b7_diagnostic=False):
    if b7_diagnostic:
        require(prefix=='browser' and digest(root/'packet.json')==
            '22f191f41c43eab0dea11de654dd13ef20235aa72f1ba08c57c01e9b7acbdce3',
            'Diagnostic exception is limited to frozen B7')
    require(prefix in ['browser','native'] and (prefix=='browser' or
        packet['schema']=='phase11.5-r3-v2-native-v1'), 'Observer evidence family')
    stopped_native=prefix=='native' and digest(root/'packet.json') in ['2a3d8c11635c48dda176c006b668bc1286114bdb7398791c12be96cbc83ab029',
        'a0260a2b0da99c33a9091e77e359a81f22d4b9e855a13f8f5f0461d51638a2b6',
        '5e18bbe50867720be83a42ee3a0b431640f2d3520da16f4dd98612e75bb06be4',
        '6b332a2f69a8f9b53dee5d8eeb83ac171beea475ee580df317b2f8deb7ce2894']
    stopped_b6 = digest(root/'packet.json') == '2f1d5f744042fa65923d21e8d26e0f25d1ce614c52cfdb39b0a7cb3adc8adc91'
    stopped_b4 = digest(root/'packet.json') in ['8d37a3a5fb5085716a4add0e6d8b5a1c74c59e36846d31af2b79ba5ba1d51170',
        '05e1e318b504e3c20e7fb0b233ba42663f52bfd55983e35b1a56f05ced449c80',
        '1b0d44f5215c2e6580f8c2bd6ec25b72eb6d9ef76e8c9e85067b2b0dce1e1966'] or stopped_b6
    inventories={}
    for label in (['before-a','before-b','final-a','final-b'] if comparator_required(packet) else ['before-a','final-a']):
        b=label.endswith('-b')
        v=audit_inventory(root/(label+'.stdout'),dict(serial=B_SERIAL if b else SERIAL,device_id=B_DEVICE if b else DEVICE),
            packet['b_session'] if b else packet['inventory_session'],packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not (root/(label+'.stderr')).read_bytes(),'Inventory stderr')
        s=v['wtp']['STATUS'];require(s['boot_id']==(packet['b_boot_id'] if b else packet['boot_id']) and
            s['owner_id'] is None and s['output_active'] is False and
            s['state'] in (['empty','complete','aborted'] if label=='final-a' or (prefix=='native' and label=='before-a') else ['empty']),'Inventory authority')
        inventories[label]=v
    before=inventories['before-a'];final=inventories['final-a']
    require(configuration(before)==configuration(final),'Preserved A')
    if comparator_required(packet):
        require(configuration(inventories['before-b'])==configuration(inventories['final-b']) and
        inventories['before-b']['info']['revision']==inventories['final-b']['info']['revision'] and
        inventories['before-b']['wtp']['STATUS']==inventories['final-b']['wtp']['STATUS'],'Preserved A/B')
    validate_info(before['info'],before,packet);validate_info(final['info'],before,packet)
    rows=journal(root/(prefix+'-observer.jsonl'))
    require(rows[0]['value']==dict(packet_sha256=digest(root/'packet.json'),baseline_sha256=digest(root/'before-a.stdout'),
        boot_id=packet['boot_id']),'Observer provenance')
    require(all(r['kind'] in ['start','finish','console_tx','console_rx','wtp_tx','wtp_rx','wtp_message',
        'info','status','health','info_finish','status_finish','health_finish',prefix+'_starting',
        *(['failure'] if stopped_b4 or stopped_native or b7_diagnostic else []),
        *(['zero_rf_failure_observation_complete'] if stopped_b6 else [])] for r in rows),
        'Observer failure/undeclared operation')
    failures = [r['value'] for r in rows if r['kind']=='failure']
    if b7_diagnostic:
        require(failures==[
            dict(worker='info',error='info cadence',type='ValueError'),
            dict(worker='supervisor',error='Browser stopped after independent observer failure',type='ValueError')],
            'Original B7 failures changed')
    if stopped_b4 or stopped_native:
        require(failures == [dict(worker='supervisor',error=('Native' if stopped_native else 'Browser')+' process/observation failure',type='ValueError')],
            'Only the preserved B4 producer failure is admitted')
    if stopped_b6:
        require([r['value'] for r in rows if r['kind']=='zero_rf_failure_observation_complete']==[
            dict(reason='GET-only producer failure; fresh Empty/inactive/unowned authority')], 'B6 bounded zero-RF stop proof')
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
        if packet.get('observer_policy')==SINGLE_FLIGHT and kind=='info':
            require(not b7_diagnostic and len(endings)==1 and endings[0]['value']==dict(samples=len(values)),
                'Prospective INFO finish/count')
            cadence[kind]=validate_intervals(starts,[r['monotonic_ns'] for r in values],
                rows[0]['monotonic_ns'],endings[0]['monotonic_ns'])
            continue
        if b7_diagnostic and kind=='info':
            failure=next(r for r in rows if r['kind']=='failure')
            require(not endings and 2_000_000_000<values[-1]['monotonic_ns']-starts[-1]<=5_000_000_000 and
                0<=failure['monotonic_ns']-values[-1]['monotonic_ns']<=1_000_000_000 and
                starts[0]-rows[0]['monotonic_ns']<=2_000_000_000 and max(gaps,default=0)<=2_000_000_000,
                'B7 cadence failure must remain a failed incomplete observation')
            cadence[kind]=dict(samples=len(values),max_start_gap_ns=max(gaps,default=0),
                status='FAILED',last_roundtrip_ns=values[-1]['monotonic_ns']-starts[-1])
            continue
        require(len(endings)==1 and endings[0]['value']==dict(samples=len(values)) and
                starts[0]-rows[0]['monotonic_ns']<=(period+1)*10**9 and
                endings[0]['monotonic_ns']-starts[-1]<=(period+1)*10**9 and
                max(gaps,default=0)<=(period+1)*10**9,'Cadence count/start/end/gap')
        cadence[kind]=dict(samples=len(values),max_start_gap_ns=max(gaps,default=0))

    result=json.loads((root/(prefix+'-observer-result.json')).read_text())
    require(result==rows[-1]['value'],'Observer result/raw mismatch')
    if b7_diagnostic:
        require(result['status']=='STOPPED_REQUIRES_DIAGNOSIS' and result['faults']==[
            'info: info cadence','supervisor: Browser stopped after independent observer failure'] and
            json.loads((root/'observer-failed.json').read_text())==dict(faults=result['faults']),
            'Original B7 result changed')
    elif stopped_b4 or stopped_native:
        require(result['status']=='STOPPED_REQUIRES_DIAGNOSIS' and
            result['faults']==['supervisor: '+('Native' if stopped_native else 'Browser')+' process/observation failure'] and
            json.loads((root/'observer-failed.json').read_text())==dict(faults=result['faults']),
            'Preserve original B4 failure')
    else:
        require(result['status']=='CAPTURED_REQUIRES_AUDIT' and result['faults']==[] and
            not (root/'observer-failed.json').exists(),'Observer completion')
    return dict(inventories=inventories,rows=rows,samples=samples,cadence=cadence)
