"""Audit the preserved P1g cadence failure and independently observed components."""
import json
from audit_phase11_5_completion_p1_failure import inputs
from audit_phase11_5_idle import frames
from audit_phase11_5_r3_v2_hour import journal, native_wire
from audit_phase11_5_r3_v2_rf import capacity_request, timing
from phase11_5_inventory import require, loads_console
from phase11_5_r3_v2_rf import validate_info, validate
from phase11_5_rf_reservation import BOARDS, inactive
from validate_wtp_contract import SchemaValidator

PACKET='4bc1919c3be6acba32a5c952a2fa00ffae65ce12a1cd8164e1dfa86d84558c57'


def audit(root):
    p,values=inputs(root,PACKET);validate(p);rows=journal(root/'rf.jsonl');job,=p['jobs']
    require(rows[0]['value']['packet_sha256']==PACKET,'Trace identity')
    schema=json.loads((root/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    pending=None;wire=b'';decoded=[];summaries=[];exchanges=[];caps=[];cap=None;seen=set();event_id=None
    console=b'';console_at=None;info_value=None;infos=[];status_value=None
    for r in rows:
        k,v,t=r['kind'],r['value'],r['monotonic_ns']
        if k=='console_tx':
            require(console_at is None and not console and info_value is None and bytes.fromhex(v['hex'])==b'INFO\n','INFO request')
            console_at=t
        elif k=='console_rx':
            require(console_at is not None,'Solicited INFO');console+=bytes.fromhex(v['hex'])
            if b'\n' in console:
                require(console.endswith(b'\n') and console.count(b'\n')==1 and t-console_at<=5000000000,'INFO framing/deadline')
                info_value=loads_console(console.decode().strip());console=b'';console_at=None
        elif k=='info':
            require(info_value==v['value'],'Raw INFO/summary');validate_info(info_value,values['before-a'],p)
            infos.append(r);info_value=None
        elif k in ('wtp_tx','capacity_tx'):
            require(pending is None,'Serialized request')
            if k=='capacity_tx':
                size=capacity_request(p,v,len(caps));cap=dict(size=size,written=0,invalid=0,index=len(caps))
                q=v['request']
            else:
                qs,left=frames(bytes.fromhex(v['hex']));require(not left and qs==[v['request']],'Request CRC/summary');q=qs[0]
            require(not validator.errors(q,schema) and q['session_id']==p['peer_session'] and q['request_id'] not in seen,'Request schema/identity/no retry')
            seen.add(q['request_id']);pending=(q,t)
        elif k=='capacity_write':
            require(cap is not None and 0<v['bytes']<=4096 and v['total_written']==cap['written']+v['bytes']<=cap['size'],'Full capacity write accounting')
            cap['written']=v['total_written']
        elif k in ('wtp_rx','capacity_rx'):
            messages,wire=frames(wire+bytes.fromhex(v['hex']));decoded.extend(messages)
        elif k in ('wtp_message','capacity_message'):
            require(len(decoded)>len(summaries) and decoded[len(summaries)]==v and not validator.errors(v,schema) and v['session_id']==p['peer_session'],'Raw response CRC/schema/summary')
            summaries.append(v)
            if v['type']=='event':
                require(v['boot_id']==p['boot_id'] and v['event'] in ('JOB_STATE','OWNER_RELEASED','INVALID_FRAME') and (event_id is None or int(v['event_id'])==event_id+1),'Event sequence/identity')
                event_id=int(v['event_id'])
                if v['event']=='INVALID_FRAME':
                    require(cap is not None and cap['index']==1 and cap['invalid']==0,'One oversized refusal');cap['invalid']+=1
                continue
            require(pending is not None and v['ok'] is True and all(v[x]==pending[0][x] for x in ('op','session_id','request_id')) and 0<=t-pending[1]<=5000000000,'Matched successful response/deadline')
            q,began=pending;pending=None;e=dict(request=q,response=v,started_ns=began,finished_ns=t);exchanges.append(e)
            if k=='capacity_message':
                require(cap is not None and cap['written']==cap['size'] and cap['invalid']==cap['index'],'Complete maximum/oversized write')
                if cap['index']==0:
                    require(v['body']['boot_id']==p['boot_id'] and v['body']['state']=='running' and v['body']['output_active'] is True and v['body']['owner_id']==p['owner_id'] and v['body']['job_id']==job['job_id'],'Maximum STATUS while RF active')
                else:require(v['body']==dict(token='after-capacity'),'Same-session recovery')
                caps.append(dict(cap,began_ns=began,ended_ns=t));cap=None
            elif q['op']=='STATUS':status_value=v['body']
        elif k=='status':
            require(status_value==v['value'],'STATUS raw/summary');status_value=None
    require(pending is None and not wire and decoded==summaries and not console and console_at is None and info_value is None and status_value is None and cap is None and len(caps)==2,'Complete raw exchanges')
    load,=[e for e in exchanges if e['request']['op']=='LOAD'];arm,=[e for e in exchanges if e['request']['op']=='ARM']
    require([e['request']['op'] for e in exchanges if e['request']['op'] not in ('HELLO','STATUS','GET_CLOCK','PING')]==['CLAIM','LOAD','ARM'],'One finite launch, no retry or renewals')
    require(load['request']['body']==job and load['response']['body']['adjustments']==[dict(event_index=i,requested_frequency_nhz=str(135500000000000 if i%2==0 else 135495000000000),realized_frequency_nhz=str(135500002652407 if i%2==0 else 135494990274310)) for i in range(512)],'Exact maximum job/adjustments')
    require(arm['request']['body']['job_id']==arm['response']['body']['job_id']==job['job_id'],'ARM job identity')
    require([r['value'] for r in rows if r['kind']=='arm_pending']==[dict(job=job,start_utc_ns=arm['request']['body']['start_utc_ns'])] and [r['value'] for r in rows if r['kind']=='arm_acknowledged']==[arm['response']['body']],'ARM summaries match raw wire')
    gaps=[b['value']['began_monotonic_ns']-a['value']['began_monotonic_ns'] for a,b in zip(infos,infos[1:])]
    require(len(infos)>=290 and all(0<g<=2000000000 for g in gaps),'Independent INFO through full observation')
    metrics=timing(p,[dict(job=job,start_utc_ns=arm['request']['body']['start_utc_ns'],monotonic_ns=arm['started_ns'],request=arm['request']['body'],acknowledgment=arm['response']['body'])],rows)
    native,native_metrics=native_wire(root,p,root/'pi/phase115_tls_observer_test.py')
    require(native_metrics['connections']==1,'Single native connection')
    for c in caps:
        before=[s for s in native if s['ended']<=c['began_ns']];after=[s for s in native if s['began']>=c['ended_ns']]
        require(before and after,'Native brackets each capacity exchange')
        for s in (before[-1],after[0]):
            require(s['value']['state']=='running' and s['value']['output_active'] is True and s['value']['owner_id']==p['owner_id'] and s['value']['job_id']==job['job_id'],'Independent native RF/owner')
    failure,=[r for r in rows if r['kind']=='failure']
    require(failure['value']==dict(worker='wtp',error='status cadence',type='ValueError') and failure['monotonic_ns']>caps[-1]['ended_ns'],'Exact subsequent cadence failure')
    contention=journal(root/'contention.jsonl');require(not any(r['kind'] in ('http_tx','https_status') for r in contention),'No HTTP offers')
    result=json.loads((root/'rf-result.json').read_text());require(result==rows[-1]['value'] and result['status']=='STOPPED_REQUIRES_DIAGNOSIS' and result['armed_jobs']==[job['job_id']] and result['completed_jobs']==[] and result['renewals']==0 and result['rf_duration_ns_charged']==128000000000,'Failed runner accounting')
    final=values['final-a']['wtp']['STATUS'];require(final['state']=='complete' and final['job_id']==job['job_id'] and final['owner_id'] is None and final['output_active'] is False and any(x['job_id']==job['job_id'] and x['state']=='complete' for x in final['terminal_records']),'Authoritative final completion')
    for phase,name,state in [('before','acquired','HELD'),('final','released','RELEASED')]:
        reservation=json.loads((root/('rf-reservation-'+name+'.json')).read_text());require(reservation['packet_sha256']==PACKET and reservation['state']==state and reservation['boards']==inactive({b:values[phase+'-'+b] for b in BOARDS}),'Shared reservation reconciled')
    peak=max([r['value']['value']['allocator_peak_bytes'] for r in infos]+[values['final-a']['info']['allocator_peak_bytes']]);validate_info(values['final-a']['info'],values['before-a'],p)
    return dict(status='WTP_CAPACITY_COMPONENTS_WITH_CADENCE_FAILURE_VERIFIED',packet_sha256=PACKET,source_revision=p['source_revision'],boot_id=p['boot_id'],accepted_components=['2.1a','2.1d','2.1e'],package_complete=False,family_closed=False,http_offers=0,wtp_capacity=caps,jobs=metrics,native=native_metrics,info_samples=len(infos),allocator_peak_bytes=peak,headroom_bytes=values['final-a']['info']['heap_capacity_bytes']-peak,rf_jobs=1,planned_rf_seconds=128,reservation_released=True,configurations_preserved=True,schedules_disabled=True,final_a=final)
