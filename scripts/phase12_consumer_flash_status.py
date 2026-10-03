#!/usr/bin/env python3
"""Injected ordinary source5 station-save/Plain LAN serialization proof; no import I/O."""
import hashlib,time
from phase12_engineering_flash_status import decode
from phase12_consumer_negative import keys,seal
from phase12_recovery_device import DEVICE,require,strict,resource_health
from phase12_composition_audit import counter


def assess(records,before,after,programs):
    opened={};spans=[];last=before
    for index,r in enumerate(records,1):
        stamp=counter(r['monotonic_ns'],'trace time');sid=counter(r['span'],'span')
        require(counter(r['seq'],'sequence')==index and last<=stamp<=after,'trace sequence/time')
        last=stamp
        if r['phase']=='begin':
            require(sid==index and sid not in opened and r['outcome']=='pending','begin binding');opened[sid]=r
        else:
            require(r['phase']=='end' and sid in opened and r['outcome']=='complete','complete pair')
            b=opened.pop(sid);require(b['kind']==r['kind'],'pair kind')
            spans.append((r['kind'],counter(b['monotonic_ns'],'begin'),stamp,counter(b['seq'],'begin seq'),index))
    require(not opened,'open trace span')
    statuses=[s for s in spans if s[0]=='status'];flash=[s for s in spans if s[0] in ('profile_erase','profile_program')]
    require(len(statuses)==20 and len(spans)==len(statuses)+len(flash),'exact trace scope')
    require(sum(s[0]=='profile_erase' for s in flash)==1 and sum(s[0]=='profile_program' for s in flash)==programs,'one profile append')
    require(all((b<=c or d<=a) and (ae<cb or ce<ab) for _,a,b,ab,ae in statuses for _,c,d,cb,ce in flash),'STATUS nested in profile flash')
    require(any(s[2]<=min(f[1] for f in flash) for s in statuses) and any(s[1]>=max(f[2] for f in flash) for s in statuses),'STATUS before and after append')
    return spans


def measure(plan,station,observe,console,http,status,*,clock=time.monotonic,sleeper=time.sleep):
    """status(deadline) returns original frames; adapter reconnects only read-only peers.
    Never fetch terminal HTTP result, suppress restart, or retry the single submit.
    """
    deadline=clock()+120;boot=plan['boot_id'];generation=plan['generation'];requests=set();wire=[]
    def info():
        require(clock()<deadline,'120s trace deadline');v,raw=observe(deadline)
        resource_health(v)
        require(v.get('firmware')=='0.0.0-devel' and 'phase12_fault_stage' not in v and
                counter(v['softap_session_inactivity_ms'],'inactivity')==900000 and
                counter(v['softap_session_absolute_ms'],'absolute')==43200000, 'ordinary consumer candidate')
        require(strict(raw)==v and v['device_id']==DEVICE and v['revision']==plan['source_commit'][:12] and v['status']['boot_id']==boot,'actual source/device/boot INFO')
        require(v['provisioning_source']=='consumer_preclock' and counter(v['provisioning_generation'],'generation') in (generation,generation+1) and v['access_state']=='healthy','healthy selected consumer')
        s=v['status'];require(s['state']=='empty' and s['enabled'] is False and s['output_active'] is False and s['engine']=='inhibited-standalone-simulator' and s['storage_healthy'] is True and not v.get('bootstrap_reset_pending',False),'inhibited healthy idle consumer')
        return v
    def command(text):
        require(clock()<deadline,'trace command deadline');v,raw=console(text,deadline)
        require(strict(raw)==v and v.get('ok') is True and v['device_id']==DEVICE and v['revision']==plan['source_commit'][:12] and v['boot_id']==boot,'actual trace identity')
        return v
    def sample():
        req,resp=status(deadline);a,b=decode(req),decode(resp)
        require(a['type']=='request' and b['type']=='response' and a['op']==b['op']=='STATUS' and a['protocol']==b['protocol']=='WTP/1' and b['ok'] is True,'actual STATUS frame')
        require(a['request_id']==b['request_id'] and a['session_id']==b['session_id'] and a['request_id'] not in requests,'STATUS correlation');requests.add(a['request_id'])
        s=b['body'];require(s['boot_id']==boot and s['state']=='empty' and s['owner_id'] is None and s['job_id'] is None and s['output_active'] is False,'actual unowned sameboot STATUS')
        wire.append(dict(request_hex=req.hex(),response_hex=resp.hex()))
    # An unavailable empty fixture cannot prove an activity-specific refusal.
    # In particular, production deliberately disables open setup in field mode.
    info()
    code,public,_,_=http('GET','/api/owner/v1/public-status',None,deadline)
    require(code==200 and public.get('device_id')==DEVICE and public.get('boot_id')==boot and
            public.get('profile_source')==5 and counter(public['generation'],'public generation')==generation and
            public.get('claim_available') is True,'empty production claim authority required')
    before=counter(info()['status']['monotonic_now_ns'],'before');start=command('ACTIVITYTRACE BEGIN '+DEVICE);require(start['enabled'] is True,'enabled capture');epoch=start['capture_epoch']
    for _ in range(10):sample()
    body,private=keys(generation);code,grant,_,_=http('POST','/api/owner/v1/claim/start',body,deadline)
    require(code==200 and grant['device_id']==DEVICE and grant['boot_id']==boot and counter(grant['generation'],'grantgen')==generation and grant['browser_nonce']==body['browser_nonce'] and grant['browser_public_key']==body['browser_public_key'],'claim grant binding')
    submit=seal(grant,body,private,station);code,reply,_,_=http('POST','/api/owner/v1/claim/submit',submit,deadline)
    require(code==200 and reply['state']=='checking','single checking reply; no terminal delivery')
    committed_at=None
    while True:
        v=info()
        if counter(v['provisioning_generation'],'generation')==generation+1:
            if committed_at is None:committed_at=clock()
            require(clock()-committed_at<45,'RAM trace capture before restart')
            if v['lan_wtp_ready'] and v['network']['link_status']==3:break
        sleeper(.2)
    for _ in range(10):sample()
    after=counter(info()['status']['monotonic_now_ns'],'after');records=[];cursor=0
    # READ is observational and available while pending bootstrap prevents END.
    for _ in range(8):
        page=command('ACTIVITYTRACE READ '+str(cursor))
        require(page['capture_epoch']==epoch and page['overflow'] is False and page['clock_regressed'] is False and counter(page['open_spans'],'open')==0 and counter(page['dropped_spans'],'dropped')==0,'complete trace')
        records.extend(page['records']);next_cursor=counter(page['next_cursor'],'cursor');require(next_cursor>=cursor and (not page['more'] or next_cursor>cursor),'cursor progress');cursor=next_cursor
        if not page['more']:
            require(cursor==counter(page['record_count'],'count')==len(records),'complete pagination');break
    else:raise ValueError('trace pagination exhausted')
    require(clock()<deadline and clock()-committed_at<45,'trace collected before automatic restart')
    spans=assess(records,before,after,plan['expected_programs'])
    return dict(status='CONSUMER_FLASH_STATUS_REVIEW_REQUIRED',status_samples=20,submit_attempts=1,request_digest=hashlib.sha256(bytes.fromhex(submit['request_id'])).hexdigest(),generation=generation+1,boot_id=boot,trace=records,spans=spans,status_wire=wire,station=station,elapsed_s=clock()-(deadline-120),terminal_response_observed=False,scope='ordinary source5 profile adapter intervals including verification; Plain LAN STATUS before/after station reconnection',rf_jobs=0,physical_acceptance=False)
