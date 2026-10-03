# Historical production T5 sampler retained only to reproduce transaction-latency failure.
#!/usr/bin/env python3
"""Injected T5 ARM boundary/local execution: exactly three inhibited jobs."""
import hashlib
import secrets
import re
import time
from phase12_composition_audit import counter
from phase12_consumer_composition import require
from phase12_recovery_device import DEVICE, resource_health, strict
from inhibited_network_acceptance import check_caps, check_status, check_clock, job_value
from wsprrypico_ble import ClientError


def run(client,observe_info,source,boot,evidence,sntp_on,sntp_off,
        *,clock=time.monotonic,sleeper=time.sleep,utc=time.time_ns):
    require(client.authorized and client.expected_device_id==DEVICE and
            client.field_session and client.wtp_session and
            getattr(client,'evidence',None) is evidence and hasattr(client,'last_response'),
            'authorized exact B EvidenceClient required')
    require(re.fullmatch("[0-9a-f]{40}",source) and re.fullmatch("[0-9a-f]{32}",boot),"exact source/boot identity")
    require(type(client.generation) is int and client.generation>=0,"client profile generation")
    deadline=clock()+240
    backend=client.backend
    class RecordedBackend:
        def __getattr__(self,name):return getattr(backend,name)
        def write(self,characteristic,value,*args,**kwargs):
            raw=bytes(value)
            evidence.record('gatt_write_attempt',characteristic=characteristic,raw_hex=raw.hex(),
                            sha256=hashlib.sha256(raw).hexdigest())
            return backend.write(characteristic,value,*args,**kwargs)
    client.backend=RecordedBackend()
    prior_timeout=getattr(client,'timeout',10)
    def budget_call(method,*args,**kwargs):
        remaining=deadline-clock()
        require(remaining>0,'T5 deadline before request')
        client.timeout=min(prior_timeout,remaining)
        try:
            result=method(*args,**kwargs)
            require(clock()<=deadline,'T5 deadline after request')
            return result
        finally:client.timeout=prior_timeout
    def wtp(operation,body):return budget_call(client.wtp_exchange,operation,body)
    owner=job=None;sent=set();completed=0
    def status(owner_id=None,job_id=None,state=None,unowned=False):
        require(clock()<deadline,'T5 total deadline')
        value=budget_call(client.wtp_status,boot)
        require(clock()<=deadline,'late STATUS')
        check_status(value,boot,owner=owner_id,job=job_id,
                     states=None if state is None else (state,),unowned=unowned)
        evidence.record('authority',value=value);return value
    def info():
        value,raw=observe_info();require(isinstance(raw,bytes) and raw and strict(raw)==value,'actual INFO wire')
        resource_health(value)
        require(value['device_id']==DEVICE and value['revision']==source[:12] and
                value['status']['boot_id']==boot and
                value['status']['engine']=='inhibited-standalone-simulator' and value['status']['enabled'] is False and
                value['status']['output_active'] is False and value['status']['storage_healthy'] is True and
                value['provisioning_source']=='provisioned' and value['access_state']=='healthy' and
                counter(value['provisioning_generation'],'profile generation')==client.generation,
                'B source boot profile storage disabled output')
        evidence.record('usb_info',raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest())
        require(clock()<=deadline,'late INFO')
    def snapshot():
        info();value=wtp('GET_CLOCK',{});require(clock()<=deadline,'late GET_CLOCK')
        evidence.record('clock',value=value);return budget_call(client.field_status),value
    def submit(offset,expected):
        nonce=secrets.token_hex(16)
        response=budget_call(client._field,'time_challenge',nonce=nonce)
        require(response['nonce']==nonce,'field challenge nonce')
        client.last_response=None
        try:response=budget_call(client._field,'time_submit',without_response=True,nonce=nonce,utc_ns=str(utc()+offset))
        except ClientError:
            response=client.last_response
            require(response and response.get('ok') is False and response.get('error')==expected,'field exact rejection')
        else:require(expected=='accepted' and response.get('accepted') is True,'field expected acceptance')
        require(clock()<=deadline,'late field submission')
        evidence.record('field_submission',offset_ns=offset,expected=expected,response=response)
    def load():
        nonlocal owner,job,sent
        status(unowned=True);owner=secrets.token_hex(16);job=secrets.token_hex(16);sent=set()
        sent.add('CLAIM');claimed=wtp('CLAIM',dict(owner_id=owner,lease_ms=60000))
        require(claimed['owner_id']==owner,'owner claim')
        sent.add('LOAD');wtp('LOAD',job_value(job));status(owner,job,'loaded')
    def release():
        sent.add('RELEASE');wtp('RELEASE',{});status(unowned=True)
    def execute(case):
        nonlocal completed
        load();field,snap=snapshot();start=check_clock(snap)
        require(field['time_source'] in ('controller','sntp'),'accepted current clock source')
        sent.add('ARM');wtp('ARM',dict(job_id=job,start_utc_ns=str(start),max_start_uncertainty_ns='500000000'))
        status(owner,job,'armed');end=min(deadline,clock()+25);running=False
        for _ in range(251):
            value=status(owner,job)
            require(value['state'] in ('armed','running','complete'),'local execution failure')
            if value['state']=='running':running=True
            if value['state']=='complete':
                require(running,'running state not observed');break
            require(clock()<end,'bounded local completion');sleeper(.1)
        else:raise TimeoutError('finite execution poll count')
        release();completed+=1;evidence.record('T5_case_complete',case=case,simulator_jobs=1,rf_jobs=0)
    try:
        info();caps=wtp('CAPS',{});check_caps(caps);status(unowned=True)
        sntp_off();field,snap=snapshot()
        require(field['time_source']=='none' and not field['time_disagreement'] and
                snap['state']=='unsynchronized','fresh no-source T5 prerequisite')
        submit(0,'accepted');field,snap=snapshot();age=counter(snap['sync_age_ns'],'sync age')
        for _ in range(96):
            if age>=91_000_000_000:break
            sleeper(1);field,snap=snapshot();next_age=counter(snap['sync_age_ns'],'sync age')
            require(next_age>=age,'clock age regression');age=next_age
        require(91_000_000_000<=age<=94_000_000_000 and field['time_source']=='none','expired field boundary')
        load();before=status(owner,job,'loaded');sent.add('ARM');client.last_response=None
        try:wtp('ARM',dict(job_id=job,start_utc_ns=str(counter(snap['utc_now_ns'],'utc')+10_000_000_000),max_start_uncertainty_ns='500000000'))
        except ClientError:
            response=client.last_response
            require(response and response.get('ok') is False and response.get('error',{}).get('code')=='CLOCK_UNSYNCHRONIZED','exact expired ARM refusal')
        else:raise ValueError('expired ARM accepted')
        after=status(owner,job,'loaded');require(before==after,'expired ARM changed authority')
        sent.add('ABORT');wtp('ABORT',dict(job_id=job));status(owner,job,'aborted');release();completed+=1
        evidence.record('T5_case_complete',case='expired_field_arm_refusal',simulator_jobs=1,rf_jobs=0)
        submit(0,'accepted');execute('fresh_field_local_completion')
        sntp_on();end=min(deadline,clock()+60)
        for _ in range(61):
            field,snap=snapshot()
            if field['time_source']=='sntp' and snap['state']=='synchronized':break
            require(clock()<end,'SNTP prerequisite unavailable');sleeper(1)
        else:raise TimeoutError('finite SNTP observations')
        submit(5_000_000_000,'busy');field,_=snapshot()
        require(field['time_source']=='sntp' and not field['time_disagreement'],'conflicting field changed SNTP')
        execute('sntp_conflict_preserved_local_completion')
        require(completed==3,'three-job budget');info();status(unowned=True)
        return dict(status='T5_REVIEW_REQUIRED',simulator_jobs=3,rf_jobs=0,physical_acceptance=False)
    except BaseException:
        if owner:
            try:
                value=status()
                if value['owner_id']==owner and value['job_id'] in (None,job):
                    if value['state'] in ('loaded','armed','running') and 'ABORT' not in sent:
                        sent.add('ABORT');wtp('ABORT',dict(job_id=job));value=status()
                    if value['state'] in ('empty','aborted','complete','missed') and 'RELEASE' not in sent:
                        sent.add('RELEASE');wtp('RELEASE',{})
                status(unowned=True)
                evidence.record('cleanup_confirmed',unowned=True)
            except BaseException as error:evidence.record('cleanup_failed',error=type(error).__name__,pending='root authority readback/restoration')
        raise
    finally:
        client.backend=backend;client.timeout=prior_timeout;sntp_off()
