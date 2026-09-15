"""Raw-evidence acceptance for the one frozen zero-RF native/retained LOAD packet."""
import json

from audit_phase11_5_idle import frames
from audit_phase11_5_r3_preflight import audit_inventory
from audit_phase11_5_r3_v2_hour import journal, native_wire
from phase11_5_device_management import digest
from phase11_5_inventory import require, loads_console
from phase11_5_load_reply_target import healthy
from phase11_5_pilot_supervisor import configuration
from phase11_5_rf_reservation import BOARDS, inactive
from validate_wtp_contract import SchemaValidator

PACKET='575ede223180c866915d600724bd2ad778d63be522be38f08c8437d816afd630'


def audit(root):
    require(digest(root/'packet.json')==PACKET,'Exact reviewed idle packet')
    p=json.loads((root/'packet.json').read_text())
    private=json.loads((root/'private-input-hashes.json').read_text())
    for n,h in p['stage_sha256'].items():require((private[n] if n in private else digest(root/n))==h,'Executed input '+n)
    values={}
    for phase in ('before','final'):
        values[phase]={}
        for b,(serial,device) in BOARDS.items():
            path=root/(phase+'-'+b+'.stdout')
            require(not path.with_suffix('.stderr').read_bytes(),'Inventory errors')
            values[phase][b]=audit_inventory(path,dict(serial=serial,device_id=device),
                p['b_session' if b=='b' else 'inventory_session'],p['stage_sha256']['scripts/phase11_5_inventory.py'])
        inactive(values[phase])
        healthy(values[phase]['a']['info'],p['boot_id'],p['source_revision'])
    require(values['before']['a']['wtp']['STATUS']['state']=='empty' and
            [r['job_id'] for r in values['before']['a']['wtp']['STATUS']['terminal_records']]==p['initial_terminal_jobs'],'Exact retained baseline')
    for b in BOARDS:require(configuration(values['before'][b])==configuration(values['final'][b]),'Configuration preserved')
    require(values['before']['b']['wtp']['STATUS']==values['final']['b']['wtp']['STATUS'],'B unchanged')
    rows=journal(root/'idle.jsonl');require(rows[0]['value']==dict(packet_sha256=PACKET),'Trace packet')
    schema=json.loads((root/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    pending=None;wire=b'';received=[];exchanges=[];console=b'';console_at=None;decoded=None;infos=[]
    for r in rows:
        k,v,t=r['kind'],r['value'],r['monotonic_ns']
        require(k not in ('failure',) and not k.startswith('cleanup_'),'Failed or cleanup path earns no acceptance')
        if k=='usb_tx':
            q,left=frames(bytes.fromhex(v['hex']))
            require(pending is None and not left and q==[v['request']] and not validator.errors(q[0],schema),'USB request wire/schema')
            pending=dict(request=q[0],start=t,written=0,size=len(bytes.fromhex(v['hex'])),label=v['label'])
        elif k=='usb_write':
            require(pending is not None and v['label']==pending['label'] and v['bytes']>0,'Solicited USB write')
            pending['written']+=v['bytes'];require(v['total_written']==pending['written']<=pending['size'],'Full-write accounting')
        elif k=='usb_rx':
            messages,wire=frames(wire+bytes.fromhex(v['hex']))
            for m in messages:
                require(not validator.errors(m,schema) and m['session_id']==p['peer_session'],'USB frame/schema/session')
                received.append(m)
                if m['type']=='event':
                    require(m['boot_id']==p['boot_id'] and m['event'] in ('JOB_STATE','OWNER_RELEASED'),'Idle event')
                else:
                    require(pending is not None and pending['written']==pending['size'] and m['ok'] is True and
                        all(m[x]==pending['request'][x] for x in ('op','session_id','request_id')) and
                        0<=t-pending['start']<=5_000_000_000,'Matched full exchange/deadline')
                    exchanges.append(dict(pending,response=m,end=t));pending=None
        elif k=='console_tx':
            require(console_at is None and not console and decoded is None and bytes.fromhex(v['hex'])==b'INFO\n','Read-only Console request')
            console_at=t
        elif k=='console_rx':
            require(console_at is not None,'Solicited Console bytes');console+=bytes.fromhex(v['hex'])
            if b'\n' in console:
                require(console.endswith(b'\n') and console.count(b'\n')==1 and t-console_at<=5_000_000_000,'Console framing/deadline')
                decoded=loads_console(console.decode().strip());console=b'';console_at=None
        elif k=='info':
            require(v['value']==decoded,'Raw INFO matches summary');healthy(decoded,p['boot_id'],p['source_revision']);infos.append(r);decoded=None
    require(pending is None and not wire and not console and console_at is None and decoded is None and
            received==[r['value']['message'] for r in rows if r['kind']=='usb_message'],'Complete raw observations')
    expected_ops=['HELLO']
    for i in range(len(p['jobs'])):expected_ops+=['CLAIM','LOAD']+(['LOAD'] if i==len(p['jobs'])-1 else [])+['ABORT','RELEASE','STATUS']
    require([e['request']['op'] for e in exchanges]==expected_ops,'Exact idle sequence; no ARM')
    loads=[e for e in exchanges if e['request']['op']=='LOAD']
    for e,job in zip(loads,p['jobs']+[p['jobs'][-1]]):
        require(e['request']['body']==job and e['size']==52105,'Exact complete maximum LOAD')
        body=e['response']['body'];require(body['job_id']==job['job_id'] and body['state']=='loaded' and len(body['adjustments'])==512,'Maximum response')
        for n,a in enumerate(body['adjustments']):
            require(a==dict(event_index=n,requested_frequency_nhz=str(135500000000000 if n%2==0 else 135495000000000),
                realized_frequency_nhz=str(135500002652407 if n%2==0 else 135494990274310)),'Exact adjustment')
    require(loads[-2]['request']['request_id']!=loads[-1]['request']['request_id'] and
            loads[-2]['response']['body']==loads[-1]['response']['body'],'Same-job fresh-ID replay')
    retained=[e for e in exchanges if e['request']['op']=='STATUS']
    for e,job in zip(retained,p['jobs']):
        b=e['response']['body'];require(b['boot_id']==p['boot_id'] and b['state']=='empty' and b['owner_id'] is None and
            b['output_active'] is False and any(r['job_id']==job['job_id'] and r['state']=='aborted' and not r['output_active'] for r in b['terminal_records']), 'Retained aborted baseline')
    native,metrics=native_wire(root,p,root/'pi/phase115_tls_observer_test.py')
    require(metrics['connections']==1 and native[0]['ended']<loads[0]['start'] and native[-1]['began']>loads[-1]['end'] and
            native[-1]['ended']-native[0]['began']>=80_000_000_000 and
            all(0<b['began']-a['began']<=6_000_000_000 for a,b in zip(native,native[1:])),'Unbroken real native coverage')
    for j in p['jobs']:
        require(any(s['value']['state']=='loaded' and s['value']['job_id']==j['job_id'] for s in native),'Native observed each Loaded job')
    require(all(s['value']['output_active'] is False for s in native),'Native confirms no RF')
    require(infos and infos[0]['monotonic_ns']<loads[0]['start'] and infos[-1]['monotonic_ns']>loads[-1]['end'] and
            all(0<b['value']['began_ns']-a['value']['began_ns']<=2_000_000_000 for a,b in zip(infos,infos[1:])),'Independent INFO overlap/cadence')
    contention=journal(root/'contention.jsonl');cr=json.loads((root/'contention-result.json').read_text())
    require(cr==contention[-1]['value'] and cr['status']=='CAPTURED_REQUIRES_AUDIT' and cr['https_requests']==0 and cr['native_exit']==0 and
            not any(r['kind']=='https_status' for r in contention),'Native-only successful completion')
    result=json.loads((root/'run-result.json').read_text())
    require(result==rows[-1]['value'] and result['status']=='CAPTURED_REQUIRES_AUDIT','Runner complete')
    for name,state,phase in [('acquired','HELD','before'),('released','RELEASED','final')]:
        r=json.loads((root/('reservation-'+name+'.json')).read_text())
        require(r['packet_sha256']==PACKET and r['state']==state and r['boards']==inactive(values[phase]),'Reservation reconciliation')
    final=values['final']['a']['wtp']['STATUS']
    require(final['state']=='empty' and {r['job_id'] for r in final['terminal_records']}=={j['job_id'] for j in p['jobs']}|set(p['initial_terminal_jobs']),'Final retained records')
    return dict(status='IDLE_NATIVE_RETAINED_LOAD_PASS',packet_sha256=PACKET,rf_jobs=0,source_revision=p['source_revision'],boot_id=p['boot_id'],
        load_exchange_seconds=[(e['end']-e['start'])/1e9 for e in loads],native=metrics,info_samples=len(infos),
        allocator_peak_bytes=max(r['value']['value']['allocator_peak_bytes'] for r in infos),heap_capacity_bytes=values['final']['a']['info']['heap_capacity_bytes'],
        configurations_preserved=True,schedules_disabled=True,reservation_released=True,family_closed=False,
        scope='Aborted retained LOAD/native continuity only; no Complete-state or RF capacity acceptance.')
