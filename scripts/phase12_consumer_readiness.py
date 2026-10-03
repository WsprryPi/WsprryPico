#!/usr/bin/env python3
"""Read-only cold-checkpoint trustworthy-time/readiness continuation."""
import time
from phase12_composition_audit import counter
from phase12_recovery_device import DEVICE,require,resource_health

CASES=('station','network','pending-tls')

def bound_info(value,request):
    resource_health(value)
    status=value['status']
    require(value['device_id']==DEVICE and value['revision']==request['source_commit'][:12] and
            value['firmware']=='0.0.0-devel' and 'phase12_fault_stage' not in value and
            value['provisioning_source']=='consumer_preclock' and value['access_state']=='healthy' and
            status['storage_healthy'] is True and status['engine']=='inhibited-standalone-simulator' and
            status['enabled'] is False and status['output_active'] is False and status['state']=='empty' and
            not status.get('owner_id') and not status.get('job_id') and
            not value.get('bootstrap_reset_pending',False),'ordinary inactive consumer checkpoint')
    require(value['saved_consumer_profile']['station']==request['station'] and
            value['network']['ntp_server']==request['time_server'],'saved checkpoint settings changed')
    return value

def bound_public(value,info):
    require(type(value.get('version')) is int and value['version']==1 and type(value.get('clock_ready')) is bool and type(value.get('tls_ready')) is bool and
            value['device_id']==DEVICE and value['boot_id']==info['status']['boot_id'] and
            value['profile_source']==5 and counter(value['generation'],'public generation')==
            counter(info['provisioning_generation'],'INFO generation'),'original public/INFO binding')
    return value

def exercise(request,observe,public_status,enable_time,evidence,*,deadline,
             clock=time.monotonic,sleeper=time.sleep):
    require(request['case'] in CASES and clock()<deadline,'named finite readiness case')
    pending=request['case']=='pending-tls';generation=request['generation'];boot=request['boot_id']
    first=bound_info(observe(),request)
    require(clock()<deadline and first['status']['boot_id']==boot and
            counter(first['provisioning_generation'],'initial generation')==generation and
            first['status']['clock_state']=='unsynchronized' and
            counter(first['network']['accepted'],'offline SNTP count')==0 and
            first['saved_consumer_profile']['tls_pending'] is pending and first['lan_wtp_ready'] is False,
            'original offline readiness boundary')
    public=bound_public(public_status(),first)
    require(clock()<deadline and public['clock_ready'] is False and public['tls_ready'] is False and
            public['readiness']=='pending_trustworthy_time_or_tls','original offline public readiness')
    evidence.record('offline_readiness_observed',case=request['case'],generation=generation,
                    boot_id=boot,public=public,submit_attempts=0)
    enable_time()
    require(clock()<deadline,'time enable deadline')
    samples=[];ready_boot=None;materialized_boot=None;http_ready=None;http_attempts=0
    for index in range(401):
        require(clock()<deadline,'trustworthy-time/readiness deadline')
        try:info=bound_info(observe(),request)
        except (OSError,TimeoutError):sleeper(min(.5,max(0,deadline-clock())));continue
        require(clock()<deadline,'late readiness INFO')
        selected=counter(info['provisioning_generation'],'warm generation')
        require(selected in ((generation,generation+1) if pending else (generation,)),
                'unexpected readiness generation')
        current=info['status']['boot_id']
        if not pending:require(current==boot,'preserved TLS readiness unexpectedly rebooted')
        elif current!=boot:
            require(selected==generation+1,'unbound materialization reboot')
            if materialized_boot is None:materialized_boot=current
            require(current==materialized_boot,'multiple materialization reboots')
        elif materialized_boot is not None:raise ValueError('materialization boot returned to original')
        ready=(info['status']['clock_state']=='synchronized' and info['network']['link_status']==3 and
               info['network'].get('ipv4','').startswith('192.168.84.') and
               counter(info['network']['accepted'],'fresh SNTP count')>0 and info['lan_wtp_ready'] is True and
               info['saved_consumer_profile']['tls_pending'] is False and
               (not pending or (selected==generation+1 and current!=boot)))
        if ready:
            if ready_boot is None:ready_boot=current
            require(current==ready_boot,'multiple materialization/readiness reboots')
            samples.append(info)
            if http_attempts<3 and http_ready is None:
                http_attempts+=1
                try:
                    public=bound_public(public_status(),info)
                    require(clock()<deadline,'late ready public response')
                    if public['clock_ready'] is True and public['tls_ready'] is True and public['readiness']=='ready':http_ready=public
                except (OSError,TimeoutError):
                    evidence.record('ready_public_carrier_unavailable',attempt=http_attempts,
                        scope='INFO/native readiness only; public ready not observed')
            if len(samples)==5:
                return dict(status='CONSUMER_READINESS_REVIEW_REQUIRED',case=request['case'],
                    generation=selected,boot_id=ready_boot,samples=samples,public_ready=http_ready,
                    materialization= pending,submit_attempts=0,rf_jobs=0,
                    public_ready_observed=http_ready is not None)
        else:
            require(not samples,'readiness lost after accepted sample')
        sleeper(min(2 if ready else .5,max(0,deadline-clock())))
    raise TimeoutError('finite readiness observation budget')
