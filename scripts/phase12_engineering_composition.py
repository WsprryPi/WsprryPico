#!/usr/bin/env python3
"""Finite B engineering carrier wave. Explicit --run; never flashes or changes trust.

Root supplies approved image/profile readback and credentials, owns restoration
and the two-hour observer. This wave proves only its named directed cases.
"""
import argparse
from contextlib import ExitStack
import hashlib
import base64
import copy
import http.client
import io
import json
import ipaddress
import re
import os
from pathlib import Path
import signal
import socket
import ssl
import struct
import time
from types import SimpleNamespace
import uuid
import fcntl
from inhibited_network_acceptance import Peer, browser, connect, context, job_value, check_caps, check_clock, check_status, foreign_checks, https_authority
from phase12_recovery_device import DEVICE, SERIAL, CONSOLE, console, resource_health, strict
from phase12_engineering_setup import private_bytes, RecordedBackend
from phase12_composition_audit import counter
from check_usb_target import port
from rf_wtp import WtpPeer
from wtp_monitor import FrameDecoder
from validate_wtp_contract import loads_strict, frame, crc32c
from wsprrypico_ble import Client, ClientError, FRAGMENT_BYTES


def require(ok, reason):
    if not ok: raise ValueError(reason)


def guard(info, plan, *, empty=False):
    resource_health(info)
    s=info['status']
    require(info['device_id']==DEVICE and info['revision']==plan['source_commit'][:12] and
            info['firmware']=='0.0.0-devel' and s['boot_id']==plan['boot_id'], 'source/boot identity')
    require(info['provisioning_source']=='provisioned' and
            counter(info['provisioning_generation'],'profile generation')==plan['profile_generation'] and
            info['lan_wtp_mode']=='engineering-tls', 'engineering profile identity')
    require(s['engine']=='inhibited-standalone-simulator' and s['enabled'] is False and
            s['output_active'] is False and s['storage_healthy'] is True and
            info['access_state']=='healthy' and not info.get('bootstrap_reset_pending',False),
            'inactive healthy inhibited authority')
    require('phase12_fault_stage' not in info and
            counter(info['softap_session_inactivity_ms'],'inactivity')==900000 and
            counter(info['softap_session_absolute_ms'],'absolute')==43200000,
            'ordinary candidate required')
    if empty: require(s['state']=='empty', 'INFO scheduler must be empty')
    return info


def reject_foreign(call, job):
    try: call('ABORT',{'job_id':job})
    except ClientError as error:
        require(error.code=='NOT_OWNER','BLE rejection code')
    except RuntimeError as error:
        require(error.args and isinstance(error.args[0],dict) and error.args[0].get('code')=='NOT_OWNER',
                'USB rejection code')
    else: raise ValueError('foreign mutation accepted')


SIM_DURATION_NS=30_000_000_000
ARMED_LEAD_NS=45_000_000_000
RUNNING_LEAD_NS=10_000_000_000

def wave_caps(caps):
    check_caps(caps)
    require(counter(caps['max_job_duration_ns'],'maximum job duration')>=SIM_DURATION_NS,'30s job outside CAPS')
    require(counter(caps['minimum_arm_lead_ns'],'minimum ARM lead')<RUNNING_LEAD_NS and
            counter(caps['maximum_arm_ahead_ns'],'maximum ARM ahead')>=ARMED_LEAD_NS,
            'predeclared 45s ARM lead outside CAPS')

def wave_job(job):
    value=job_value(job)
    value['total_duration_ns']=str(SIM_DURATION_NS)
    value['events'][0]['duration_ns']=str(SIM_DURATION_NS)
    return value


def resource_http(args, evidence, method, path, body=None, revision=None, *, deadline=None):
    """One strictly framed TLS/HTTPS exchange inside the original three seconds."""
    require(method in ('GET','PUT') and path in ('/api/v1/application','/api/v1/config',
            '/api/v1/station','/api/v1/hardware'),'bounded application route')
    require(revision is None or re.fullmatch('"[0-9a-f]{64}"',revision),'canonical revision')
    started=time.monotonic()
    deadline=min(deadline if deadline is not None else started+3,started+3)
    raw=bytearray();stream=None;primary=None;result=None;phase='connect'
    marks={'started_s':started,'deadline_s':deadline}
    try:
        evidence.record('private_application_https_attempt',dict(method=method,path=path,**marks))
        marks['context_started_s']=time.monotonic();ctx=context(args,True)
        marks['context_finished_s']=time.monotonic();require(marks['context_finished_s']<deadline,'application context deadline')
        marks['connect_started_s']=time.monotonic()
        stream=connect(args,ctx,'http/1.1',evidence,observer_deadline=deadline)
        marks['tls_finished_s']=time.monotonic();require(marks['tls_finished_s']<deadline,'application TLS deadline')
        authority=https_authority(args)
        payload=b'' if body is None else json.dumps(body,separators=(',',':')).encode()
        require(len(payload)<=1024,'application request bound')
        headers=(f'{method} {path} HTTP/1.1\r\nHost: {authority}\r\n'
                 f'Origin: https://{authority}\r\nContent-Type: application/json\r\n'
                 'X-WsprryPico-Request: 1\r\nConnection: close\r\n'+
                 (f'If-Match: {revision}\r\n' if revision is not None else '')+
                 f'Content-Length: {len(payload)}\r\n\r\n').encode()
        wire=headers+payload;phase='send'
        evidence.record('private_application_https_tx',dict(method=method,path=path,hex=wire.hex()))
        marks['send_started_s']=time.monotonic();remaining=deadline-marks['send_started_s'];require(remaining>0,'application send deadline')
        stream.settimeout(remaining);stream.sendall(wire)
        marks['send_finished_s']=time.monotonic();require(marks['send_finished_s']<deadline,'application send completion deadline')
        phase='receive';response=None;expected=None
        while True:
            remaining=deadline-time.monotonic();require(remaining>0,'application reply deadline')
            stream.settimeout(remaining);chunk=stream.recv(4096)
            raw.extend(chunk)
            require(len(raw)<=6144,'application response bound')
            marks['last_receive_s']=time.monotonic();require(marks['last_receive_s']<deadline,'application reply completion deadline')
            if response is None and b'\r\n\r\n' in raw:
                header,_,_=bytes(raw).partition(b'\r\n\r\n')
                class Buffered:
                    def makefile(self,mode):return io.BytesIO(header+b'\r\n\r\n')
                response=http.client.HTTPResponse(Buffered());response.begin()
                lengths=[value for name,value in response.getheaders() if name.lower()=='content-length']
                transfers=[value for name,value in response.getheaders() if name.lower()=='transfer-encoding']
                require(len(lengths)==1 and re.fullmatch('0|[1-9][0-9]*',lengths[0]) and not transfers,
                        'single canonical application content length')
                require(not response.chunked and response.length==int(lengths[0]) and response.length<=4096,
                        'bounded exact application content length')
                expected=len(header)+4+response.length
            if expected is not None:
                require(len(raw)<=expected,'application response trailer/extra bytes')
                if len(raw)==expected:break
            require(chunk,'incomplete application response')
        phase='parse'
        evidence.record('private_application_https_rx',dict(method=method,path=path,hex=raw.hex()))
        payload=bytes(raw).split(b'\r\n\r\n',1)[1]
        result=(response.status,loads_strict(payload.decode()),response.getheader('ETag'))
        require(time.monotonic()<deadline,'application parse deadline')
        phase='complete'
    except BaseException as error:primary=error
    finally:
        # Keep the bounded original, including partial bytes, before reporting
        # failure. Evidence/close failure cannot replace the first error.
        try:
            evidence.record('private_application_https_finish',dict(method=method,path=path,phase=phase,
                hex=bytes(raw[:6144]).hex(),bytes=len(raw),truncated=len(raw)>6144,error_type=type(primary).__name__ if primary else None,
                finished_s=time.monotonic(),**marks))
        except BaseException as error:
            if primary is None:primary=error
        try:
            if stream is not None:stream.close()
        except BaseException as error:
            if primary is None:primary=error
    if primary is not None:raise primary
    require(time.monotonic()<deadline,'application final completion deadline')
    return result


def application_readback(http,plan,*,deadline=None):
    code,app,revision=http('GET','/api/v1/application',deadline=deadline)
    require(code==200 and re.fullmatch('"[0-9a-f]{64}"',revision or ''),'application GET/revision')
    target=dict(scope='member',device_id=DEVICE,boot_id=plan['boot_id'])
    require(app['schema']=='transmitter-application/1' and app['target']==target,'application target')
    for name,schema in (('station','transmitter-station/1'),('hardware','transmitter-hardware/1')):
        require(app[name]['schema']==schema and app[name]['target']==target and
                app[name]['storage_healthy'] is True,'embedded resource target/health')
    require(counter(app['station']['saved_generation'],'station generation')==
            counter(app['hardware']['saved_generation'],'hardware generation'),'common saved generation')
    require(app['hardware']['saved'] is not None and app['hardware']['active'] is not None and
            app['hardware']['application_error'] is None and
            app['hardware']['execution_engine']=='inhibited-standalone-simulator',
            'saved/active healthy inhibited hardware')
    code,config,config_revision=http('GET','/api/v1/config',deadline=deadline)
    require(code==200 and config_revision==revision and config['config'] is not None and
            config['config']['enabled'] is False and
            config['config']['station']==app['station']['station'],'config/resource common authority')
    return dict(application=app,config=config,revision=revision)


def application_candidates(baseline):
    app=baseline['application'];target=copy.deepcopy(app['target'])
    station=copy.deepcopy(app['station']['station'])
    station['power_dbm']=0 if station['power_dbm'] else 10
    pins=copy.deepcopy(app['hardware']['saved'])
    require(pins['engine']=='direct' and pins['i2c_pair'] is None and
            pins['amplifier_gp'] is None and pins['lpf_gps']==[],'supported direct fixture')
    owned={pins['rf_gp'],pins['button_gp'],pins['indicator_gp']}
    pins['rf_gp']=next(gp for gp in (28,27,26,*range(22,-1,-1)) if gp not in owned)
    return (dict(schema='transmitter-station/1',target=target,station=station),
            dict(schema='transmitter-hardware/1',target=copy.deepcopy(target),pins=pins))


def busy_application_resources(http,baseline,plan,verify,emit,*,clock=time.monotonic,deadline=None):
    """Two nonmutating busy attempts within the existing job/case deadlines."""
    deadline=min(deadline if deadline is not None else clock()+12,clock()+12)
    station,pins=application_candidates(baseline)
    for path,body in (('/api/v1/station',station),('/api/v1/hardware',pins)):
        verify()
        code,value,_=http('PUT',path,body,baseline['revision'],deadline=deadline)
        require(clock()<=deadline and code==409 and value==dict(error=dict(code='busy')),
                'exact application busy refusal')
        verify()
        emit('application_busy_refusal',dict(path=path,target=body['target'],revision=baseline['revision']))
    require(application_readback(http,plan,deadline=deadline)==baseline,
            'busy application attempt changed durable generation/pins/unrelated config')
    require(clock()<=deadline,'application busy total deadline')
    verify()
    emit('application_busy_unchanged',dict(generation=baseline['application']['hardware']['saved_generation'],
         saved_pins=baseline['application']['hardware']['saved'],active_pins=baseline['application']['hardware']['active']))


def idle_application_resources(http,peer,plan,verify,emit,*,clock=time.monotonic,deadline=None):
    """Separate 60-second B12C stage: four saves, no job and no automatic restart.

    Run after composition/resource work, or in its own root-prepared engineering
    setup. The first hardware save inhibits all shared job admissions until boot;
    the root must perform the planned reboot/readback/restoration afterward.
    """
    deadline=min(deadline if deadline is not None else clock()+60,clock()+60)
    def safe():
        # INFO plus the existing WTP STATUS each have finite transport bounds.
        require(deadline-clock()>=14,'idle application guard cannot fit deadline');verify()
        check_status(peer.request('STATUS',{}),plan['boot_id'],unowned=True)
        require(clock()<deadline,'idle application guard deadline')
    safe();baseline=application_readback(http,plan,deadline=deadline)
    app=baseline['application']
    require(app['hardware']['pending_restart'] is False and app['reboot_required'] is False,
            'idle application baseline pending restart')
    station,hardware=application_candidates(baseline)
    generation=counter(app['hardware']['saved_generation'],'initial application generation')
    revision=baseline['revision'];current=baseline;saves=0
    bad_device=copy.deepcopy(station);bad_device['target']['device_id']='0'*32 if DEVICE!='0'*32 else '1'*32
    bad_boot=copy.deepcopy(station);bad_boot['target']['boot_id']='0'*32 if plan['boot_id']!='0'*32 else '1'*32
    stale='"'+('0' if revision[1]!='0' else '1')+revision[2:]
    for body,token,code,error in ((bad_device,revision,409,'target_mismatch'),
            (bad_boot,revision,409,'target_mismatch'),(station,None,428,'revision_required'),
            (station,stale,412,'revision_conflict')):
        safe();status,value,_=http('PUT','/api/v1/station',body,token,deadline=deadline)
        require(status==code and value==dict(error=dict(code=error)),'idle target/revision exact refusal')
        emit('application_idle_negative',dict(code=error,target=body['target']))
    require(application_readback(http,plan,deadline=deadline)==baseline,'target/revision negative mutation')
    expected_config=copy.deepcopy(baseline['config'])
    expected_app=copy.deepcopy(app)
    def save(path,body,*,pending):
        nonlocal current,revision,saves
        safe();require(saves<4,'four application saves ceiling')
        saves+=1 # Consume before any ambiguous request; no retry after failure.
        status,_,new_revision=http('PUT',path,body,revision,deadline=deadline)
        require(status==200 and new_revision!=revision,'idle application save response')
        current=application_readback(http,plan,deadline=deadline)
        expected_app['station']['saved_generation']=str(generation+saves)
        expected_app['hardware']['saved_generation']=str(generation+saves)
        expected_app['hardware']['pending_restart']=pending
        expected_app['reboot_required']=pending
        require(current['application']==expected_app and current['config']==expected_config and
                current['revision']==new_revision,'exact application save and unrelated preservation')
        revision=new_revision;safe()
        emit('application_idle_save',dict(path=path,generation=str(generation+saves),
             revision=revision,saved_pins=current['application']['hardware']['saved'],
             active_pins=current['application']['hardware']['active'],pending_restart=pending))
    expected_config['config']['station']=station['station'];expected_app['station']['station']=station['station']
    save('/api/v1/station',station,pending=False)
    restore_station=copy.deepcopy(station);restore_station['station']=app['station']['station']
    expected_config=copy.deepcopy(baseline['config']);expected_app['station']['station']=app['station']['station']
    save('/api/v1/station',restore_station,pending=False)
    expected_config['config']['pins']=hardware['pins'];expected_app['hardware']['saved']=hardware['pins']
    save('/api/v1/hardware',hardware,pending=True)
    def inhibited():
        result=peer.request('CLAIM',{'owner_id':uuid.uuid4().hex,'lease_ms':60000},expected_error='BUSY')
        require(result.get('code')=='BUSY','pending hardware must inhibit shared CLAIM')
        safe()
    inhibited()
    restore_hardware=copy.deepcopy(hardware);restore_hardware['pins']=app['hardware']['saved']
    expected_config=copy.deepcopy(baseline['config']);expected_app['hardware']['saved']=app['hardware']['saved']
    save('/api/v1/hardware',restore_hardware,pending=True)
    inhibited()
    require(saves==4 and clock()<=deadline,'idle application finite completion')
    result=dict(status='PASS_IDLE_APPLICATION_REBOOT_PENDING',saves=saves,simulated_jobs=0,rf_jobs=0,
         boot_id=plan['boot_id'],initial_generation=str(generation),saved_generation=str(generation+saves),
         initial_revision=baseline['revision'],final_revision=revision,
         baseline=baseline,final=current,
         pending=['root normal reboot, exact cold saved/active readback and planned restoration'])
    emit('application_idle_complete',result)
    return result

def prepare_busy_profile(client, profile, password, generation, verify, emit, *, clock=time.monotonic,deadline=None):
    """Upload retained bytes while loaded; return one apply/cancel continuation."""
    require(client.generation==generation,'profile client generation')
    verify();stage_deadline=min(deadline if deadline is not None else clock()+20,clock()+20)
    def field(operation,end,**values):
        remaining=end-clock();require(remaining>0,'profile pressure deadline')
        result=client._field(operation,timeout=min(5,remaining),**values)
        require(clock()<=end,'late profile pressure response');return result
    session=uuid.uuid4().hex;apply_request=uuid.uuid4().hex
    opened=False;cancel_attempted=False;finish_attempted=False
    def cancel(verify=lambda:None):
        nonlocal cancel_attempted
        if opened and not cancel_attempted:
            cancel_attempted=True
            client._field('cancel',session_id=session,timeout=5)
            verify()
            emit('profile_stage_cancelled',{'profile_session_id':session,'generation':generation})
    def finish(verify,*,deadline=None):
        nonlocal finish_attempted
        require(not finish_attempted,'profile apply continuation must not repeat')
        finish_attempted=True
        end=min(deadline if deadline is not None else clock()+20,clock()+20)
        try:
            verify()
            step=field('profile_step_up',end,profile_session_id=session,
                apply_request_id=apply_request,expected_generation=generation,password=password)
            require(step.get('confirmation_required') is True and step.get('ready') is False,
                    'unconfirmed default-password profile safeguard')
            verify()
            remaining=end-clock();require(remaining>0,'profile apply deadline')
            try:
                client.exchange(dict(version=1,operation='apply',request_id=apply_request,
                    session_id=session,device_id=DEVICE,expected_generation=generation),timeout=min(5,remaining))
            except ClientError as error:
                require(error.code=='busy','exact profile busy required')
            else:raise ValueError('busy profile apply unexpectedly accepted')
            require(clock()<=end,'late profile busy response')
            verify()
            emit('profile_apply_busy',{'generation':generation,'profile_sha256':hashlib.sha256(profile).hexdigest(),
                'physical_confirmation_sent':False,'apply_request_id':apply_request})
        finally:cancel(verify)
        require(clock()<=end,'profile cancellation exceeded pressure deadline')
    try:
        opened=True
        field('open',stage_deadline,session_id=session)
        for offset in range(0,len(profile),FRAGMENT_BYTES):
            end=min(offset+FRAGMENT_BYTES,len(profile))
            field('write',stage_deadline,session_id=session,offset=offset,final=end==len(profile),
                          payload=base64.b64encode(profile[offset:end]).decode('ascii'))
        verify()
        require(clock()<=stage_deadline,'profile staging total deadline')
        return SimpleNamespace(finish=finish,cancel=cancel)
    except BaseException:
        cancel(verify);raise


def busy_profile_apply(client, profile, password, generation, verify, emit, *, clock=time.monotonic,deadline=None):
    """Stage/apply once; default-password confirmation is never given."""
    end=min(deadline if deadline is not None else clock()+20,clock()+20)
    prepared=prepare_busy_profile(client,profile,password,generation,verify,emit,clock=clock,deadline=end)
    prepared.finish(verify,deadline=end)


def directed_wave(plan, owner, contender, usb, ble, http_status, info, pressure,
                  *, clock=time.monotonic, sleeper=time.sleep, emit=lambda k,v:None):
    start=clock();jobs=0;current_owner=None;current_job=None
    attempted_abort=set();attempted_release=set();case_started=None;prepared_profile=None
    def safe(empty=False):
        require(clock()-start<240,'wave deadline')
        require(case_started is None or clock()-case_started<60,'case deadline')
        return guard(info(),plan,empty=empty)
    def observe(state):
        safe()
        for name,call in [('owner',owner.request),('usb',usb.request),('ble',ble.wtp_exchange)]:
            snapshot=call('STATUS',{})
            safe()
            check_status(snapshot,plan['boot_id'],owner=current_owner,job=current_job,states=(state,))
            emit('shared_status',{'carrier':name,'state':state,'job_id':current_job})
        contender.request('ABORT',{'job_id':current_job},expected_error='NOT_OWNER')
        safe()
        reject_foreign(usb.request,current_job)
        safe()
        reject_foreign(ble.wtp_exchange,current_job)
        safe()
        result=http_status()
        safe()
        check_status(result,plan['boot_id'],owner=current_owner,job=current_job,states=(state,))
        emit('shared_status',{'carrier':'https-contender','state':state,'job_id':current_job})
        safe()
        check_status(owner.request('STATUS',{}),plan['boot_id'],owner=current_owner,
                     job=current_job,states=(state,))
    safe(empty=True)
    check_status(owner.request('STATUS',{}),plan['boot_id'],unowned=True)
    wave_caps(owner.request('CAPS',{}))
    pressure()
    safe(empty=True)
    try:
        for target in ('loaded','armed','running'):
            require(jobs<6,'six job ceiling')
            case_started=clock()
            current_owner=uuid.uuid4().hex;current_job=uuid.uuid4().hex
            # Record before ambiguous CLAIM/LOAD; no dependent retry after loss.
            jobs+=1
            emit('job_attempt',{'state':target,'owner_id':current_owner,'job_id':current_job})
            claim=owner.request('CLAIM',{'owner_id':current_owner,'lease_ms':60000})
            safe()
            require(claim['owner_id']==current_owner,'claim identity')
            owner.request('LOAD',wave_job(current_job))
            safe()
            if target=='running':
                prepare=getattr(ble,'phase12_profile_prepare',None)
                require(callable(prepare),'running profile staging callback required')
                prepared_profile=prepare(current_owner,current_job)
                require(callable(prepared_profile.finish) and callable(prepared_profile.cancel),'profile continuation required')
                safe()
            execution_end=None
            if target!='loaded':
                arm_marker=clock();clock_value=owner.request('GET_CLOCK',{})
                at=check_clock(clock_value)
                if target=='armed':at+=ARMED_LEAD_NS-RUNNING_LEAD_NS
                execution_end=arm_marker+(at-int(clock_value['utc_now_ns'])+SIM_DURATION_NS)/1e9
                owner.request('ARM',{'job_id':current_job,'start_utc_ns':str(at),
                                     'max_start_uncertainty_ns':'500000000'})
            if target=='running':
                deadline=clock()+14
                while True:
                    safe()
                    state=owner.request('STATUS',{})
                    if state['state']=='running':break
                    require(state['state']=='armed' and clock()<deadline,'running not observed')
                    sleeper(.1)
            observe(target)
            application_pressure=getattr(ble,'phase12_application_pressure',None)
            require(callable(application_pressure),'application busy callback required')
            pressure_deadline=None
            if target=='running':
                # Three seconds remain reserved before conservative job completion.
                require(execution_end-clock()>=21,'running pressure cannot fit remaining job')
                pressure_deadline=min(clock()+18,execution_end-3)
            application_pressure(target,current_owner,current_job,deadline=pressure_deadline)
            profile_pressure=getattr(ble,'phase12_profile_pressure',None)
            require(callable(profile_pressure),'bounded busy profile callback required')
            profile_pressure(target,current_owner,current_job,deadline=pressure_deadline,prepared=prepared_profile)
            if pressure_deadline is not None:require(clock()<=pressure_deadline,'combined running pressure deadline')
            prepared_profile=None
            observe(target)
            attempted_abort.add(current_job)
            owner.request('ABORT',{'job_id':current_job})
            check_status(owner.request('STATUS',{}),plan['boot_id'],owner=current_owner,
                         job=current_job,states=('aborted',))
            attempted_release.add(current_owner)
            owner.request('RELEASE',{})
            check_status(owner.request('STATUS',{}),plan['boot_id'],unowned=True)
            safe(empty=True)
            emit('case_pass',{'state':target})
            current_owner=current_job=None;case_started=None
        contender.close();ble.close();usb.close()
        # Owner remains connected only for final authenticated readback. Its
        # slot is released by the caller before checking adapter reclamation.
        check_status(owner.request('STATUS',{}),plan['boot_id'],unowned=True)
        safe(empty=True)
        return {'status':'PASS_NAMED_DIRECTED_SCOPE','simulated_jobs':jobs,'max_simulated_job_duration_s':30,'rf_jobs':0,
                'covered':['TLS owner+USB+BLE+HTTPS contender shared status',
                           'loaded/armed/running foreign ABORT refusal',
                           'loaded/armed/running exact busy profile apply and staged cancellation',
                           'loaded/armed/running exact targeted/revisioned station/hardware busy refusal with unchanged durable config',
                           'maximum 65536-byte valid STATUS framing','third network connection refusal','three oversized WTP headers cause bounded disconnect'],
                'pending':['SoftAP retained session pressure',
                           'BLE excess peer pressure','two-hour resource return soak',
                           'root profile/image readback and final restoration']}
    except BaseException:
        case_started=None
        if prepared_profile is not None:
            try:prepared_profile.cancel()
            except BaseException:emit('profile_stage_cleanup_unconfirmed',{})
        # Reconcile once through the existing owner connection only. Never
        # reopen/repeat CLAIM, LOAD, ARM or the failed request.
        try:
            safe()
            state=owner.request('STATUS',{})
            if state['owner_id']==current_owner and state['job_id'] in (None,current_job):
                if state['state'] in ('loaded','armed','running'):
                    require(current_job not in attempted_abort, 'uncertain ABORT must not repeat')
                    attempted_abort.add(current_job)
                    owner.request('ABORT',{'job_id':current_job})
                    state=owner.request('STATUS',{})
                    check_status(state,plan['boot_id'],owner=current_owner,job=current_job,states=('aborted',))
                require(current_owner not in attempted_release, 'uncertain RELEASE must not repeat')
                attempted_release.add(current_owner)
                owner.request('RELEASE',{})
            check_status(owner.request('STATUS',{}),plan['boot_id'],unowned=True)
            check_status(owner.request('STATUS',{}),plan['boot_id'],unowned=True)
            safe(empty=True)
            emit('cleanup_confirmed',{})
        except BaseException:
            emit('cleanup_unconfirmed',{'pending':'root USB readback/abort/restoration'})
        raise


class QuietUSB(WtpPeer):
    def __init__(self,fd,emit):super().__init__(fd);self.emit=emit
    def _receive(self):
        chunk=os.read(self.fd,4096)
        require(chunk,'USB closed')
        self.emit('private_usb_rx',{'hex':chunk.hex()})
        for payload in self.decoder.feed(chunk):
            m=loads_strict(payload.decode())
            require(m.get('protocol')=='WTP/1' and m.get('session_id')==self.session and
                    m.get('type') in ('response','event'),'USB frame identity')
            self.pending.append(m)
    def request(self,op,body,timeout=8):
        self.emit('private_usb_request',{'op':op,'body':body,'session':self.session})
        return super().request(op,body,timeout)
    def close(self):pass # ExitStack owns the USB descriptor.


def capacity_probe(connector, emit):
    stream=None
    try:
        stream=connector()
    except (ConnectionResetError,ConnectionRefusedError,BrokenPipeError,ssl.SSLEOFError) as error:
        emit('excess_connection_refused',{'observed':type(error).__name__})
    except ssl.SSLError as error:
        require(getattr(error,'reason',None) in ('TLSV1_ALERT_ACCESS_DENIED','SSLV3_ALERT_HANDSHAKE_FAILURE'),
                'unexpected TLS error is not capacity evidence')
        emit('excess_connection_refused',{'observed':'TLS alert','reason':error.reason})
    else:
        raise ValueError('third TLS admitted')
    finally:
        if stream is not None:stream.close()


def invalid_disconnect(stream, session, boot, *, observe_close=None, headers=None, emit=None):
    decoder=FrameDecoder();count=0;total=0;deadline=time.monotonic()+5;closed=None
    if observe_close is not None:
        require(headers==struct.pack('>4sBBHII',b'WTPF',1,1,0,65537,0)*3,'three exact oversized headers required')
        before=observe_close();require(time.monotonic()<deadline,'late framing baseline')
        require(counter(before['network_wtp_close_reason'],'before close')!=4,'stale framing close reason')
        stream.settimeout(deadline-time.monotonic());stream.sendall(headers)
        if emit:emit('three_oversized_headers_sent',{'hex':headers.hex()})
    while True:
        remaining=deadline-time.monotonic();require(remaining>0,'framing disconnect deadline')
        stream.settimeout(remaining)
        try:value=stream.recv(4096)
        except ConnectionResetError:closed='reset';break
        except ssl.SSLEOFError:closed='tls_eof';break
        if not value:closed='eof';break
        total+=len(value);require(total<=8192,'framing error response bound')
        for payload in decoder.feed(value):
            m=loads_strict(payload.decode())
            require(m.get('type')=='event' and m.get('protocol')=='WTP/1' and
                    m.get('session_id')==session and m.get('boot_id')==boot and
                    m.get('event')=='INVALID_FRAME' and
                    m['body']['error']['code']=='INVALID_FRAME','wrong framing rejection')
            count+=1;require(count<=3,'excess framing events')
    if observe_close is None:require(count==3,'three framing rejections required')
    else:
        after=observe_close();require(time.monotonic()<deadline,'late framing close observation')
        require(counter(after['network_wtp_close_reason'],'after close')==4 and
                type(after['network_wtp_tls_result']) is int and after['network_wtp_tls_result']==0 and
                counter(after['network_active_connections'],'after active')==0 and
                counter(after['network_pending_connections'],'after pending')==0,'actual endpoint framing close/reclamation required')
        result=dict(peer_outcome=closed,advisory_events_received=count,received_bytes=total,
                    three_exact_headers_sent=True,endpoint_close_reason=4,tls_result=0)
        if emit:emit('framing_endpoint_close_observed',result)
        return result


class Stream:
    def __init__(self,stream,evidence):self.stream=stream;self.evidence=evidence
    def __getattr__(self,name):return getattr(self.stream,name)
    def sendall(self,value):
        self.evidence.record('private_tls_tx',{'hex':bytes(value).hex()})
        return self.stream.sendall(value)
    def recv(self,size):
        value=self.stream.recv(size)
        self.evidence.record('private_tls_rx',{'hex':value.hex()})
        return value


class HTTPSContender:
    """Distinct-certificate HTTPS principal; Pico admits only one WTP socket."""
    def __init__(self,args,evidence):self.args=args;self.evidence=evidence
    def request(self,op,body,expected_error=None):
        require(op=='ABORT' and expected_error=='NOT_OWNER','HTTPS contender operation')
        foreign_checks(self.args,self.evidence,body['job_id'])
        return {'code':'NOT_OWNER'}
    def close(self):pass # browser owns and closes every ephemeral HTTPS stream.


class RecordedPeer(Peer):
    def exact(self,size,deadline):
        value=super().exact(size,deadline)
        self.evidence.record('private_tls_rx_exact',{'hex':value.hex()})
        return value
    def padded_status(self):
        request=dict(type='request',protocol='WTP/1',session_id=self.session,
                     request_id=uuid.uuid4().hex,op='STATUS',body={})
        require(not self.validator.errors(request,self.schema),'invalid maximum request schema')
        payload=json.dumps(request,separators=(',',':')).encode()
        require(len(payload)<65536,'maximum request padding capacity')
        payload+=b' '*(65536-len(payload))
        wire=frame(payload);deadline=time.monotonic()+8
        self.evidence.record('maximum_valid_status_request',{'request_id':request['request_id'],
            'payload_bytes':65536,'wire_sha256':hashlib.sha256(wire).hexdigest()})
        self.stream.settimeout(8);self.stream.sendall(wire)
        for _ in range(33):
            header=self.exact(16,deadline)
            magic,version,encoding,flags,length,checksum=struct.unpack('>4sBBHII',header)
            require((magic,version,encoding,flags)==(b'WTPF',1,1,0) and 0<length<=65536,
                    'maximum STATUS response framing')
            raw=self.exact(length,deadline);require(crc32c(raw)==checksum,'maximum STATUS response CRC')
            message=loads_strict(raw.decode())
            require(not self.validator.errors(message,self.schema) and message['session_id']==self.session,
                    'maximum STATUS response schema/session')
            self.evidence.record('maximum_valid_status_response',message)
            if message['type']=='event':
                require(message['boot_id']==self.args.boot_id,'maximum STATUS event boot');continue
            require((message['request_id'],message['op'])==(request['request_id'],'STATUS') and
                    message['ok'] is True,'maximum STATUS response correlation/acceptance')
            check_status(message['body'],self.args.boot_id,unowned=True)
            return message['body']
        raise ValueError('maximum STATUS event ceiling')
    def open(self):
        super().open()
        self.stream=Stream(self.stream,self.evidence)


class Evidence:
    def __init__(self,file):self.file=file;self.bytes=0
    def record(self,kind,value):
        text=json.dumps({'monotonic_ns':str(time.monotonic_ns()),'kind':kind,'value':value})+'\n'
        self.bytes+=len(text.encode());require(self.bytes<=4*1024*1024,'transcript bound')
        self.file.write(text);self.file.flush();os.fsync(self.file.fileno())


def validate_device_plan(plan):
    require(plan['device_id']==DEVICE and plan['console']==CONSOLE and
            plan['wtp_console']==CONSOLE.replace('-if00','-if02'),'B USB binding')
    require(re.fullmatch('[0-9a-f]{40}',plan['source_commit']) and
            re.fullmatch('[0-9a-f]{32}',plan['boot_id']) and
            type(plan['profile_generation']) is int,'plan identity')
    require(str(ipaddress.IPv4Address(plan['address']))==plan['address'], 'numeric IPv4 required')
    require(type(plan['port']) is int and 1<=plan['port']<=65535, 'port')
    image=private_bytes(Path(plan['image_path']),4*1024*1024)
    require(re.fullmatch('[0-9a-f]{64}',plan['image_sha256']) and
            hashlib.sha256(image).hexdigest()==plan['image_sha256'], 'exact offline image hash')
    for key in ('profile_path','ca','cert','key','contender_cert','contender_key'):
        content=private_bytes(Path(plan[key]),16384)
        if key=='profile_path':
            require(hashlib.sha256(content).hexdigest()==plan['profile_sha256'] and
                    strict(content)['device_id']==DEVICE,'root verified profile binding')
    require(hashlib.sha256(private_bytes(Path(plan['cert']),16384)).digest()!=
            hashlib.sha256(private_bytes(Path(plan['contender_cert']),16384)).digest(),
            'distinct TLS credentials required')
    password=private_bytes(Path(plan['password_file']),64).decode('ascii').removesuffix('\n')
    require(8<=len(password)<=63,'password format')
    args=SimpleNamespace(**{k:plan[k] for k in ('address','port','hostname','server_sha256','ca','cert','key')},
                         device_id=DEVICE,boot_id=plan['boot_id'],
                         browser_cert=plan['contender_cert'],browser_key=plan['contender_key'])
    other=SimpleNamespace(**vars(args));other.cert=plan['contender_cert'];other.key=plan['contender_key']
    return args,other,password


def run_device(plan, evidence_path, observe_info, *, observe_original_info=None):
    """Run one bounded wave; caller owns campaign lease and short INFO locking.

    Safe for a worker thread: no signal handlers, process umask changes or
    whole-wave console/action lock. All network and USB operations are bounded.
    """
    wave_end=time.monotonic()+240
    args,other,password=validate_device_plan(plan)
    evidence_path=Path(evidence_path)
    require(evidence_path.is_absolute(),'absolute transcript')
    try:
        with ExitStack() as stack:
            fdlog=os.open(evidence_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            log=stack.enter_context(os.fdopen(fdlog,'w'));e=Evidence(log)
            owner=RecordedPeer(args,e);contender=HTTPSContender(args,e)
            stack.callback(owner.close);stack.callback(contender.close)
            initial=guard(observe_info(),plan,empty=True)
            require(counter(initial['network_active_connections'],'baseline connections')==0 and
                    counter(initial['network_pending_connections'],'baseline pending')==0,
                    'exclusive network baseline required')
            owner.open()
            fd=stack.enter_context(port(plan['wtp_console']))
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            usb=QuietUSB(fd,e.record)
            h=usb.request('HELLO',{'versions':['WTP/1'],'client_name':'phase12-engineering','client_version':'1'})
            require(h['device_id']==DEVICE and h['boot_id']==plan['boot_id'],'USB HELLO')
            check_caps(usb.request('CAPS',{}))
            ble=Client(RecordedBackend(plan.get('adapter','hci0'),lambda v:e.record('private_ble',v)),timeout=5)
            stack.callback(ble.close)
            ident=ble.connect(plan['ble_address'],DEVICE,allow_pairing=False)
            require(ident['generation']==plan['profile_generation'],'BLE generation')
            ble.authorize(password);bh=ble.enable_local_control()
            require(bh['boot_id']==plan['boot_id'],'BLE boot')
            retained_profile=private_bytes(Path(plan['profile_path']),7168)
            def http_resource(method,path,body=None,revision=None,*,deadline=None):
                return resource_http(args,e,method,path,body,revision,deadline=deadline)
            application_baseline=application_readback(http_resource,plan)
            require(application_baseline['application']['hardware']['pending_restart'] is False and
                    application_baseline['application']['reboot_required'] is False,
                    'application baseline already pending restart')
            def application_pressure(target,owner_id,job_id,*,deadline=None):
                def verify():
                    guard(observe_info(),plan)
                    check_status(owner.request('STATUS',{}),plan['boot_id'],owner=owner_id,job=job_id,states=(target,))
                busy_application_resources(http_resource,application_baseline,plan,verify,e.record,deadline=deadline)
            ble.phase12_application_pressure=application_pressure
            def profile_verify(target,owner_id,job_id):
                def verify():
                    value=guard(observe_info(),plan)
                    require(value['access_default_password'] is True and
                            ble.generation==plan['profile_generation'],'unconfirmed profile safety')
                    check_status(owner.request('STATUS',{}),plan['boot_id'],owner=owner_id,job=job_id,states=(target,))
                return verify
            def profile_prepare(owner_id,job_id):
                return prepare_busy_profile(ble,retained_profile,password,plan['profile_generation'],
                    profile_verify('loaded',owner_id,job_id),e.record)
            ble.phase12_profile_prepare=profile_prepare
            def profile_pressure(target,owner_id,job_id,*,deadline=None,prepared=None):
                verify=profile_verify(target,owner_id,job_id)
                if prepared is not None:prepared.finish(verify,deadline=deadline)
                else:busy_profile_apply(ble,retained_profile,password,plan['profile_generation'],verify,e.record,deadline=deadline)
            ble.phase12_profile_pressure=profile_pressure
            def http_status():
                code,value=browser(args,e)
                require(code==200,'HTTPS status rejected')
                return value['job']
            def pressure():
                from capacity_pending import run as pending_capacity
                owner.padded_status()
                # Third connection must fail at bounded TLS admission; any
                # successful handshake is a capacity-contract failure.
                held=connect(args,context(args,True),'http/1.1',e)
                try:
                    held.sendall(('GET /api/v1/status HTTP/1.1\r\nHost: '+https_authority(args)+'\r\n').encode())
                    check_status(owner.request('STATUS',{}),plan['boot_id'],unowned=True)
                    held_end=time.monotonic()+12
                    def capacity_info():
                        info=guard(observe_info(),plan)
                        e.record('capacity_original_info',info)
                        return dict(boot=info['status']['boot_id'],source=info['revision'],
                            active=counter(info['network_active_connections'],'active'),
                            pending=counter(info['network_pending_connections'],'pending'),
                            pool=(counter(info['tls_allocated_bytes'],'TLS pool'),counter(info['network_pending_tcp_bytes'],'pending bytes')),
                            timeouts=0,rejected=0)
                    capacity_result=pending_capacity(lambda deadline:connect(other,context(other),'wtp/1',e,observer_deadline=deadline),
                        capacity_info,
                        lambda deadline:check_status(owner.request('STATUS',{}),plan['boot_id'],unowned=True),
                        lambda deadline:require(time.monotonic()<held_end,'held HTTPS lifetime observation bracket'),
                        e.record,wave_end)
                    e.record('capacity_refusal_and_reclamation',capacity_result)

                    check_status(owner.request('STATUS',{}),plan['boot_id'],unowned=True)
                finally:held.close()
                # Apply framing pressure to the single WTP owner before CLAIM.
                # Three complete invalid headers reach the parser ceiling;
                # reconnect this declared session once with no job mutation.
                limit=int(owner.request('CAPS',{})['max_payload_bytes'])
                require(limit==65536,'reviewed framing limit required')
                header=struct.pack('>4sBBHII',b'WTPF',1,1,0,limit+1,0)
                if observe_original_info is None:
                    owner.stream.sendall(header*3)
                    invalid_disconnect(owner.stream,owner.session,plan['boot_id'])
                else:
                    def framing_info():
                        info,raw=observe_original_info()
                        require(isinstance(raw,bytes) and strict(raw)==info,'original framing INFO bytes')
                        e.record('framing_original_info',{'raw_hex':raw.hex()})
                        return guard(info,plan,empty=True)
                    invalid_disconnect(owner.stream,owner.session,plan['boot_id'],observe_close=framing_info,headers=header*3,emit=e.record)
                e.record('three_oversized_headers_refused',{'hex':(header*3).hex()})
                owner.close();owner.open()
            result=directed_wave(plan,owner,contender,usb,ble,http_status,lambda:observe_info(),pressure,
                                 emit=e.record)
            owner.close();guard(observe_info(),plan,empty=True)
            e.record('result',result)
            return result
    finally:
        password=''


def run_idle_device(plan,evidence_path,observe_info):
    """One post-capture B12C application stage; parent owns reboot/cold proof."""
    deadline=time.monotonic()+60
    args,_,password=validate_device_plan(plan)
    evidence_path=Path(evidence_path)
    require(evidence_path.is_absolute(),'absolute idle transcript')
    try:
        with ExitStack() as stack:
            fdlog=os.open(evidence_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            log=stack.enter_context(os.fdopen(fdlog,'w'));e=Evidence(log)
            def verify():guard(observe_info(),plan,empty=True)
            verify()
            owner=RecordedPeer(args,e);stack.callback(owner.close);owner.open()
            require(time.monotonic()<deadline,'idle application setup deadline')
            def http(method,path,body=None,revision=None,*,deadline=None):
                return resource_http(args,e,method,path,body,revision,deadline=deadline)
            result=idle_application_resources(http,owner,plan,verify,e.record,deadline=deadline)
            e.record('result',result)
            return result
    finally:password=''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--private-transcript',type=Path,required=True)
    p.add_argument('--run',action='store_true')
    a=p.parse_args()
    if not a.run:p.error('explicit --run and root approval required')
    plan=strict(private_bytes(a.plan,16384))
    handler=signal.getsignal(signal.SIGALRM)
    def timeout(*_):raise TimeoutError('wave deadline')
    try:
        signal.signal(signal.SIGALRM,timeout);signal.alarm(240)
        result=run_device(plan,a.private_transcript,lambda:console('INFO'))
        print(json.dumps(result,sort_keys=True))
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,handler)


if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'status':'STOPPED_NO_RETRY_ROOT_RESTORATION_REQUIRED','error_type':type(error).__name__}))
        raise SystemExit(1)
