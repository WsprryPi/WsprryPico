#!/usr/bin/env python3
"""Finite source-bound AP withdrawal proof; no profile submit or import I/O."""
import time,uuid
from phase12_consumer_flash_status import decode
from phase12_consumer_negative import keys
from phase12_recovery_device import DEVICE,require
from phase12_composition_audit import counter
from inhibited_network_acceptance import job_value,check_clock


BUSY_DURATION_NS=30_000_000_000
WITHDRAW_SECONDS=5
START_SECONDS=3

def exercise(plan,observe,http,exchange,withdraw,associate,*,clock=time.monotonic,sleeper=time.sleep,deadline=None):
    end=min(clock()+60,deadline) if deadline is not None else clock()+60;boot=plan['boot_id'];gen=plan['generation'];target=plan['busy_state'];owner=uuid.uuid4().hex;job=uuid.uuid4().hex;attempted=set();wire=[];requests=set()
    require(target in ('loaded','armed','running'),'finite named busy state')
    def call(op,body):
        require(clock()<end,'60s busy deadline')
        if op in ('CLAIM','LOAD','ARM','ABORT','RELEASE'):
            require(op not in attempted,'no mutation retry');attempted.add(op)
        req,resp=exchange(op,body,end);a,b=decode(req),decode(resp)
        require(a['protocol']==b['protocol']=='WTP/1' and a['type']=='request' and a['request_id'] not in requests and a['op']==b['op']==op and a['request_id']==b['request_id'] and a['session_id']==b['session_id'] and b['type']=='response' and b['ok'] is True,'original busy response correlation')
        requests.add(a['request_id']);wire.append(dict(request_hex=req.hex(),response_hex=resp.hex()));return b['body']
    def status(state=None,unowned=False):
        s=call('STATUS',{});require(s['boot_id']==boot and s['output_active'] is False,'same inhibited busy boot')
        if unowned:require(s['owner_id'] is None and s['job_id'] is None and s['state']=='empty','empty authority')
        else:require(s['owner_id']==owner and s['job_id']==job and (state is None or s['state']==state),'owned job authority')
        v=observe(end)[0];require(v['status']['boot_id']==boot and counter(v['provisioning_generation'],'generation')==gen and v['status']['output_active'] is False and v['status']['state']==s['state'],'same durable generation and independent state')
        return s
    def control():
        code,p,_,_=http('GET','/api/owner/v1/public-status',None,end)
        require(code==200 and p['device_id']==DEVICE and p['boot_id']==boot and p['profile_source']==5 and counter(p['generation'],'generation')==gen and p['claim_available'] is True,'actual empty AP claim control')
        code,slot,_,_=http('GET','/api/owner/v1/claim/status',None,end)
        require(code==200 and slot['boot_id']==boot and counter(slot['generation'],'generation')==gen and slot['slot_state']=='none','no prepared slot')
    status(unowned=True);control()
    try:
        require(call('CLAIM',dict(owner_id=owner,lease_ms=60000))['owner_id']==owner,'claim owner')
        caps=call('CAPS',{});require(counter(caps['max_job_duration_ns'],'max duration')>=BUSY_DURATION_NS,'bounded busy duration supported')
        value=job_value(job);value['total_duration_ns']=str(BUSY_DURATION_NS);value['events'][0]['duration_ns']=str(BUSY_DURATION_NS)
        call('LOAD',value);status('loaded')
        if target!='loaded':
            start=check_clock(call('GET_CLOCK',{}));call('ARM',dict(job_id=job,start_utc_ns=str(start),max_start_uncertainty_ns='500000000'));status('armed')
        if target=='running':
            until=min(end,clock()+14)
            while True:
                s=status()
                if s['state']=='running':break
                require(s['state']=='armed' and clock()<until,'running deadline');sleeper(.1)
        before=status(target);carrier=withdraw(end)
        body,_=keys(gen);outcome=None
        try:
            code,reply,rawreq,rawresp=http('POST','/api/owner/v1/claim/start',body,min(end,clock()+START_SECONDS))
            outcome=dict(kind='http',code=code,reply=reply,request_hex=rawreq.hex(),response_hex=rawresp.hex())
            require(code==403 and reply.get('error')=='unavailable','START unexpectedly admitted')
        except (OSError,TimeoutError) as error:outcome=dict(kind='socket_failure',error_type=type(error).__name__)
        after=status(target);require(before==after or all(before[k]==after[k] for k in ('boot_id','owner_id','job_id','state','output_active')),'busy authority unchanged')
        # Mark before delivery. A lost response is reconciled, never resent.
        try:call('ABORT',dict(job_id=job))
        except (OSError,TimeoutError):require(status()['state']=='aborted','uncertain ABORT unresolved')
        status('aborted')
        try:call('RELEASE',{})
        except (OSError,TimeoutError):status(unowned=True)
        status(unowned=True);associate(end);control();require(clock()<end,'finite busy completion')
        return dict(state=target,boot_id=boot,generation=gen,owner_id=owner,job_id=job,wire=wire,carrier=carrier,start_outcome=outcome,submit_attempts=0,simulator_jobs=1,rf_jobs=0)
    except BaseException:
        # Cleanup at most once, only after read-only reconciliation of our owner.
        try:
            s=call('STATUS',{})
            if s['owner_id']==owner and s['job_id'] in (None,job):
                if s['state'] in ('loaded','armed','running') and 'ABORT' not in attempted:call('ABORT',dict(job_id=job));s=call('STATUS',{})
                if s['state'] in ('empty','aborted','complete','missed') and 'RELEASE' not in attempted:call('RELEASE',{})
        except BaseException:pass
        raise
