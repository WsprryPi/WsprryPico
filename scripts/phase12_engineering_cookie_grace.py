#!/usr/bin/env python3
"""Three bounded cookie lifetime jobs on the explicitly inhibited B fixture."""
import time
import uuid
import re
from phase12_composition_audit import counter
from phase12_recovery_device import DEVICE, require, resource_health
from inhibited_network_acceptance import check_status
from phase12_consumer_composition import job_value


def reclaimed_status(value, boot, job=None):
    """Authority may be free while the exact aborted job history remains."""
    check_status(value,boot)
    require(value['owner_id'] is None,'cleanup owner still present')
    if value['state']=='empty':
        require(value['job_id'] is None,'empty cleanup has a job')
        return
    require(job is not None and value['state']=='aborted' and value['job_id']==job,
            'cleanup retained unexpected job/state')
    records=value.get('terminal_records',[])
    matching=[v for v in records if v.get('job_id')==job]
    require(len(matching)==1 and matching[0].get('state')=='aborted' and
            matching[0].get('output_active') is False and
            counter(matching[0].get('ended_monotonic_ns'),'terminal end')>0,
            'exact inactive aborted terminal record required')


def run(exchange, observe_info, observe_status, observe_ap, refresh_time, evidence,
        password, source, boot, *, profile_generation, clock=time.monotonic, sleeper=time.sleep, stages=('loaded','armed','running')):
    require(type(profile_generation) is int and profile_generation>0,'exact profile generation')
    allowed=('loaded','armed','running')
    require(isinstance(stages,(list,tuple)) and len(stages)>0 and
            tuple(stages)==tuple(v for v in allowed if v in stages),'ordered unique cookie stage subset')
    start=clock();attempts=[];jobs=0;last_refresh=[clock()];prior_job=None
    def safe():
        require(clock()-start<260,'cookie grace total deadline')
        info=observe_info();ap=observe_ap();resource_health(info);s=info['status']
        require(info['device_id']==DEVICE and info['revision']==source[:12] and
                s['boot_id']==boot and s['engine']=='inhibited-standalone-simulator' and
                s['output_active'] is False and s['enabled'] is False and
                s['storage_healthy'] is True and info['access_state']=='healthy' and
                info['provisioning_source']=='provisioned' and info['lan_wtp_mode']=='engineering-tls' and
                counter(info['provisioning_generation'],'generation')==profile_generation and
                not info.get('bootstrap_reset_pending',False), 'exact healthy inhibited B')
        require(counter(info['softap_session_inactivity_ms'],'idle')==15000 and
                counter(info['softap_session_absolute_ms'],'absolute')==60000, 'accelerated cookie limits')
        require(ap['device_id']==DEVICE and ap['boot_id']==boot and ap['source_commit']==source and
                ap['interface']=='wlan2' and ap['destination']=='192.168.4.1' and
                ap['associated'] is True and ap['local_ipv4']=='192.168.4.2', 'exact AP association')
        return info
    def status(owner=None,job=None,state=None,unowned=False):
        safe();value=observe_status()
        check_status(value,boot,owner=owner,job=job,
                     states=None if state is None else (state,),unowned=unowned)
        evidence.record('usb_authority',value=value)
        return value
    def call(method,path,body=None,cookie=None,session=None):
        safe();attempts.append((method,path))
        result=exchange(method,path,body,cookie,session,min(start+260,clock()+10))
        safe();return result
    def wait_until(target):
        while clock()<target:
            safe()
            if clock()-last_refresh[0]>=30:
                refresh_time();last_refresh[0]=clock();safe()
            require(clock()-start<260,'cookie grace total deadline')
            remaining=target-clock()
            if remaining<=0:return
            sleeper(min(1,remaining))
    def reclaim(owner,job):
        deadline=min(start+260,clock()+65)
        while True:
            value=status()
            require(clock()<deadline,'lease cleanup deadline')
            if value['owner_id'] is None:
                reclaimed_status(value,boot,job)
                return
            require(value['owner_id']==owner and value['job_id'] in (job,None),'cleanup authority changed')
            require(clock()<deadline,'lease cleanup deadline');sleeper(1)
    for stage in stages:
        reclaimed_status(status(),boot,prior_job);safe();refresh_time();last_refresh[0]=clock();safe()
        cookie=None;session=uuid.uuid4().hex;owner=uuid.uuid4().hex;job=uuid.uuid4().hex
        claimed=False
        try:
            created=clock()
            code,value,headers=call('POST','/local/v1/login',dict(version=1,device_id=DEVICE,password=password))
            require(code==200 and value['ok'] is True,'grace login; no retry')
            cookie=headers['set-cookie'].split(';',1)[0]
            require(re.fullmatch(r'__Host-wsprrypico=[0-9a-f]{32}',cookie) is not None,'cookie token shape')
            def operation(op,body):
                request_id=uuid.uuid4().hex
                code,response,_=call('POST','/api/v1/jobs',dict(session_id=session,request_id=request_id,
                    operation=op,body=body),cookie,session)
                require(code==200 and response['ok'] is True and
                        response['request_id']==request_id,
                        'cookie WTP correlation/success: '+op)
                return response['result']
            hello=operation('HELLO',dict(versions=['WTP/1'],client_name='phase12-cookie-grace',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==boot,'cookie HELLO identity')
            code,capability,_=call('GET','/api/v1/capabilities',cookie=cookie,session=session)
            require(code==200,'cookie CAPS admission')
            caps=capability['wtp']
            require(caps['engine']=='inhibited-standalone-simulator' and 'tone' in caps['modes'] and
                    'rf-events/1' in caps['profiles'] and counter(caps['max_job_duration_ns'],'maxduration')>=45_000_000_000 and
                    counter(caps['minimum_arm_lead_ns'],'minlead')<5_000_000_000 and
                    counter(caps['maximum_arm_ahead_ns'],'maxlead')>=45_000_000_000 and
                    counter(caps['maximum_arm_uncertainty_ns'],'maxuncertainty')>=500_000_000 and
                    counter(caps['minimum_lease_ms'],'minlease')<=20000<=60000<=counter(caps['maximum_lease_ms'],'maxlease') and
                    any(counter(r['minimum_nhz'],'minfrequency')<=3_570_100_000_000_000<=counter(r['maximum_nhz'],'maxfrequency')
                        for r in caps['frequency_ranges']), 'predetermined cookie jobs outside CAPS')
            def keepalive(expired=False):
                code,value,_=call('GET','/api/v1/status',cookie=cookie,session=session)
                if expired:
                    require(code==401 and value['error']['code']=='authentication_required','actual cookie expiry refusal')
                else:
                    require(code==200,'grace STATUS rejected');check_status(value['job'],boot)
                    evidence.record('cookie_status',stage=stage,value=value['job'])
                    return value['job']
            if stage!='loaded':
                for age in (10,20,30):wait_until(created+age);keepalive()
            claimed=True
            result=operation('CLAIM',dict(owner_id=owner,lease_ms=60000))
            require(result['owner_id']==owner,'cookie owner identity')
            value=job_value(job);duration=30 if stage=='armed' else 45
            value['total_duration_ns']=str(duration*1_000_000_000)
            value['events'][0]['duration_ns']=value['total_duration_ns'];jobs+=1
            require(jobs<=3,'fixed three-job budget')
            operation('LOAD',value);status(owner,job,'loaded')
            if stage!='loaded':
                info=observe_info();snapshot=info['status']
                require(snapshot['clock_state']=='synchronized' and
                        counter(snapshot['uncertainty_ns'],'uncertainty')<=500_000_000,'ARM usable clock')
                lead=45 if stage=='armed' else 5
                operation('ARM',dict(job_id=job,start_utc_ns=str(counter(snapshot['utc_now_ns'],'UTC')+lead*1_000_000_000),
                    max_start_uncertainty_ns='500000000'))
            for age in ((10,20,30,40,50) if stage=='loaded' else (40,50)):
                wait_until(created+age);keepalive()
            require(clock()-created<55,'renew must precede cookie absolute expiry')
            operation('RENEW',dict(owner_id=owner,lease_ms=20000))
            wait_until(created+62)
            status(owner,job,stage)
            if stage=='loaded':
                keepalive(expired=True);status(owner,job,'loaded')
                evidence.record('loaded_expiry_no_grace',job_id=job)
            else:
                value=keepalive();check_status(value,boot,owner=owner,job=job,states=(stage,))
                operation('ABORT',dict(job_id=job));status(owner,job,'aborted')
                keepalive(expired=True)
                evidence.record('owner_grace_status_abort_pass',stage=stage,job_id=job)
        except BaseException as error:
            evidence.record('case_failed',stage=stage,error_type=type(error).__name__,retry=False)
            raise
        finally:
            # Never retry a mutation with an uncertain response. Natural expiry
            # provides bounded cleanup, observed through independent authority.
            if claimed:reclaim(owner,job)
        prior_job=job
        evidence.record('case_complete',stage=stage,physical_acceptance=False)
    return dict(status='COOKIE_GRACE_COMPLETE_REVIEW_REQUIRED',stages=list(stages),simulated_jobs=jobs,
                rf_jobs=0,physical_acceptance=False,forbidden_active_mutation_tested=False)
