#!/usr/bin/env python3
"""Parent-owned B engineering time cases and ordinary two-hour resource capture."""
import hashlib
import copy
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time
import uuid
from types import SimpleNamespace
import inhibited_network_acceptance as network
from phase12_composition_capture import capture
from phase12_composition_audit import validate_plan,counter
from phase12_consumer_composition import Evidence
from phase12_consumer_dispatch import directed_waves
from phase12_engineering_composition import run_device,run_idle_device,guard,validate_device_plan,resource_http,application_readback,RecordedPeer
from phase12_engineering_setup import RecordedBackend,private_bytes
from phase12_engineering_time import EvidenceClient,run as run_time
from phase12_engineering_fixture import action as fixture
from phase12_serial_observer import Observer
from phase12_authority_capture import capture as authority_capture
from phase12_recovery_device import DEVICE,CONSOLE,SERIAL,console,strict,require
from check_standalone_image import validate_uf2

AUTHORITY='USER_AUTHORIZED_UNATTENDED_PHASE12'


def save(path,value):
    with path.open('x') as file:
        os.chmod(path,0o600);json.dump(value,file);file.write('\n');file.flush();os.fsync(file.fileno())


def warm_accepted_time(plan,observer,control,root,*,clock=time.monotonic,sleeper=time.sleep):
    """Fresh owned SNTP prerequisite only; never reaccept T1-T4."""
    end=clock()+180;bound=False;samples=0;initial_accepted=None
    while clock()<end:
        require(end-clock()>=6,'warm observer cannot fit deadline')
        info,raw=observer();guard(info,plan,empty=True)
        require(strict(raw)==info,'original warm INFO bytes')
        samples+=1;require(samples<=361 and clock()<end,'finite fresh SNTP prerequisite')
        save(root/('continuation-warm-info-%03d.json'%samples),dict(raw_hex=raw.hex(),info=info))
        require(info['network']['ntp_server']=='192.168.84.1','owned warm time source')
        accepted=counter(info['network']['accepted'],'accepted SNTP')
        if initial_accepted is None:initial_accepted=accepted
        if info['network']['link_status']==3:
            require(info['network']['ipv4'].startswith('192.168.84.'),'owned warm station')
            if not bound:
                control('bind_peer',address=info['network']['ipv4']);control('sntp_on');bound=True
            if info['status']['clock_state']=='synchronized' and accepted>initial_accepted:
                require(clock()<end,'warm prerequisite completion deadline')
                return dict(status='PREREQUISITE_ONLY_ACCEPTED_TIME_CASES_SKIPPED',cases=[],
                    retained_accepted_cases=['T1','T2','T3','T4'],samples=samples,max_seconds=180,
                    station_address=info['network']['ipv4'])
        sleeper(min(.5,max(0,end-clock())))
    raise TimeoutError('fresh owned SNTP prerequisite deadline')


def normal_reboot(plan,*,request=console):
    """One local REBOOT under the same action flock; never retries an unknown reply."""
    lock=os.open('/home/pi/.wsprrypico-recovery-action-'+SERIAL+'.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        before=guard(request('INFO'),plan,empty=True)
        reply=request('REBOOT')
        require(reply==dict(ok=True,rebooting=True),'normal REBOOT acknowledgement')
        return dict(attempts=1,command='REBOOT',before_boot=before['status']['boot_id'],reply=reply)
    finally:os.close(lock)


def cold_admission(peer,boot,evidence,end,*,clock=time.monotonic):
    """One CLAIM/RELEASE proves the reboot cleared admission, with no job."""
    owner=uuid.uuid4().hex;claim_attempted=False;release_attempted=False
    def status():
        require(end-clock()>=8,'cold admission STATUS cannot fit deadline')
        return peer.request('STATUS',{})
    try:
        network.check_status(status(),boot,unowned=True)
        require(end-clock()>=8,'cold CLAIM cannot fit deadline')
        claim_attempted=True
        reply=peer.request('CLAIM',dict(owner_id=owner,lease_ms=60000))
        require(reply['owner_id']==owner,'cold CLAIM identity')
        owned=status();network.check_status(owned,boot,owner=owner,states=('empty',))
        require(owned['job_id'] is None,'cold CLAIM must not load a job')
        require(end-clock()>=8,'cold RELEASE cannot fit deadline')
        release_attempted=True;peer.request('RELEASE',{})
        network.check_status(status(),boot,unowned=True)
        require(clock()<end,'cold admission completion deadline')
        evidence.record('cold_shared_admission_recovered',claims=1,releases=1,simulated_jobs=0,owner_id=owner)
    except BaseException:
        # One readback may reconcile an uncertain CLAIM. Never repeat a CLAIM
        # or a RELEASE whose response was lost; root owns any remaining lease.
        try:
            if claim_attempted and not release_attempted:
                snapshot=status()
                network.check_status(snapshot,boot,states=('empty',))
                if snapshot['owner_id']==owner:
                    require(snapshot['job_id'] is None and end-clock()>=8,'cold owned cleanup guard')
                    release_attempted=True;peer.request('RELEASE',{})
            network.check_status(status(),boot,unowned=True)
            evidence.record('cold_shared_admission_cleanup_confirmed',claim_attempted=claim_attempted,
                release_attempted=release_attempted)
        except BaseException as error:
            try:evidence.record('cold_shared_admission_cleanup_unconfirmed',error_type=type(error).__name__)
            except BaseException:pass # Preserve the original admission/transport failure.
        raise


def cold_application(plan,stage,observer,root,control,*,clock=time.monotonic,sleeper=time.sleep,deadline=None):
    """Bound new boot, settings/time and exact restored pins before restoration."""
    end=min(deadline if deadline is not None else clock()+180,clock()+180)
    current_plan=dict(plan);samples=0;new_boot=None;bound=False
    args,_,password=validate_device_plan(plan)
    evidence=Evidence(root/'application-cold-wire.jsonl')
    wire=SimpleNamespace(record=lambda kind,value:evidence.record(kind,value=value))
    try:
        while clock()<end:
            require(end-clock()>=6,'cold observer cannot fit deadline')
            try:info,raw=observer()
            except (OSError,TimeoutError):sleeper(min(.5,max(0,end-clock())));continue
            require(clock()<end and strict(raw)==info,'original cold INFO/deadline')
            boot=info['status']['boot_id']
            if boot==plan['boot_id']:
                sleeper(min(.5,max(0,end-clock())));continue
            if new_boot is None:new_boot=boot
            require(boot==new_boot,'unexpected second cold reboot')
            current_plan['boot_id']=new_boot;guard(info,current_plan,empty=True)
            samples+=1;require(samples<=361,'finite cold observations')
            save(root/('application-cold-info-%03d.json'%samples),dict(raw_hex=raw.hex(),info=info))
            require(info['network']['ntp_server']=='192.168.84.1','cold time source retained')
            for key in ('access_generation','provisioning_generation','provisioning_source',
                        'access_state','access_default_password','saved_consumer_profile'):
                require(info[key]==stage['before_info'][key],'cold retained settings/generations')
            if info['network']['link_status']==3 and not bound:
                require(info['network']['ipv4'].startswith('192.168.84.'),'cold owned station')
                control('bind_peer',address=info['network']['ipv4']);bound=True
            if info['network']['link_status']!=3 or info['status']['clock_state']!='synchronized' or counter(info['network']['accepted'],'cold accepted SNTP')==0:
                sleeper(min(.5,max(0,end-clock())));continue
            require(info['network']['ipv4'].startswith('192.168.84.'),'cold owned station')
            args.address=info['network']['ipv4'];args.boot_id=new_boot
            require(end-clock()>=100,'cold HTTPS/admission proof cannot fit deadline')
            def http(method,path,body=None,revision=None,*,deadline=None):
                return resource_http(args,wire,method,path,body,revision,deadline=min(end,deadline if deadline is not None else end))
            readback=application_readback(http,current_plan,deadline=end)
            expected=copy.deepcopy(stage['baseline']['application'])
            target=dict(scope='member',device_id=DEVICE,boot_id=new_boot)
            for resource in (expected,expected['station'],expected['hardware']):resource['target']=copy.deepcopy(target)
            for name in ('station','hardware'):expected[name]['saved_generation']=stage['saved_generation']
            expected['hardware']['pending_restart']=False;expected['reboot_required']=False
            pins=expected['hardware']['saved'];expected['hardware']['active']=copy.deepcopy(pins)
            active=':'.join((DEVICE,new_boot,'hardware',json.dumps(pins,separators=(',',':'))))
            expected['hardware']['active_revision']=hashlib.sha256(active.encode()).hexdigest()
            expected['recurrence']['suspended']=False
            require(readback['application']==expected and readback['config']==stage['baseline']['config'],
                    'cold application settings/saved-active preservation')
            require(readback['revision'] not in (stage['initial_revision'],stage['final_revision']),
                    'cold revision must bind new boot')
            peer=RecordedPeer(args,wire)
            try:
                # Open <=26s, five transactions <=40s, uncertain-outcome
                # cleanup <=24s. Reserve all of it inside the original bound.
                require(end-clock()>=94,'cold shared authority cannot fit deadline')
                peer.open();cold_admission(peer,new_boot,evidence,end,clock=clock)
            finally:peer.close()
            require(clock()<end,'cold proof completion deadline')
            result=dict(status='PASS_IDLE_APPLICATION_COLD_PROOF',normal_reboots=1,saves=4,
                old_boot=plan['boot_id'],boot_id=new_boot,saved_generation=stage['saved_generation'],
                application=readback,claims=1,releases=1,simulated_jobs=0,rf_jobs=0,full_composition_qualified=False)
            save(root/'application-cold-result.json',result);return result
        raise TimeoutError('cold application proof deadline')
    finally:evidence.close();password=''


def application_stage(plan,observer,root,control):
    before=guard(observer()[0],plan,empty=True)
    stage=run_idle_device(plan,(root/'application-idle-wire.jsonl').resolve(),lambda:observer()[0])
    stage['before_info']=before
    save(root/'application-idle-result.json',stage)
    require(stage['saves']==4 and stage['simulated_jobs']==stage['rf_jobs']==0,'finite idle stage result')
    save(root/'application-reboot-attempt.json',dict(attempts=1,before_boot=before['status']['boot_id']))
    cold_end=time.monotonic()+180
    reboot=normal_reboot(plan);save(root/'application-reboot-result.json',reboot)
    return cold_application(plan,stage,observer,root,control,deadline=cold_end)


def run(request):
    require(request['authority']==AUTHORITY,'authority')
    root=Path(request['root']);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and
        root.is_dir() and not root.is_symlink(),'private root')
    raw=(root/'preparation-manifest.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==request['manifest_sha256'],'preparation transfer')
    manifest=strict(raw);candidate=next(c for c in manifest['candidates'] if c['role']=='engineering')
    require(candidate['target']=='WsprryPico' and candidate['fault_stage']==0 and candidate['lan_mode']=='tls' and
            manifest['source_commit']==request['source_commit'],'ordinary engineering candidate')
    image=private_bytes(root/'engineering.uf2',4*1024*1024);validate_uf2(image)
    require(hashlib.sha256(image).hexdigest()==candidate['uf2']['sha256']==request['image_sha256'],'actual image binding')
    profile=private_bytes(root/'engineering-profile.json',7168)
    require(hashlib.sha256(profile).hexdigest()==request['profile_sha256'] and strict(profile)['device_id']==DEVICE,'actual profile binding')
    profile_value=strict(profile);require(profile_value['wifi']['time_server']=='192.168.84.1','isolated time source')
    password=private_bytes(root/'default-password.txt',64).decode('ascii').removesuffix('\n')
    observer=Observer()
    def control(action,**args):return fixture(dict(root=str(root),authority=AUTHORITY,action=action,**args))
    first=observer()[0];boot=request['boot_id']
    plan=dict(source_commit=request['source_commit'],boot_id=boot,device_id=DEVICE,
        profile_generation=request['profile_generation'],console=CONSOLE,wtp_console=CONSOLE.replace('-if00','-if02'),
        image_path=str(root/'engineering.uf2'),image_sha256=request['image_sha256'],
        profile_path=str(root/'engineering-profile.json'),profile_sha256=request['profile_sha256'],
        address=first['network']['ipv4'],port=443,hostname=profile_value['tls']['hostname'],
        server_sha256=request['server_sha256'],ca=str(root/'client-ca.crt'),
        cert=str(root/'owner-client.crt'),key=str(root/'owner-client.key'),
        contender_cert=str(root/'contender-client.crt'),contender_key=str(root/'contender-client.key'),
        password_file=str(root/'default-password.txt'),ble_address=request['ble_address'])
    guard(first,plan,empty=True)
    scope=request.get('scope','composition');require(scope in ('composition','application'),'dispatch scope')
    skip=request.get('skip_accepted_time_cases',False);require(type(skip) is bool,'explicit time continuation flag')
    if scope=='application' or skip:
        time_result=warm_accepted_time(plan,observer,control,root)
        plan['address']=time_result['station_address']
        save(root/'time-result.json',time_result);password=''
    else:
        deadline=time.monotonic()+90
        while True:
            info=guard(observer()[0],plan,empty=True)
            if info['network']['link_status']==3 and info['network']['ipv4'].startswith('192.168.84.'):
                plan['address']=info['network']['ipv4'];break
            require(time.monotonic()<deadline,'isolated station readiness deadline');time.sleep(.5)
        control('bind_peer',address=plan['address']);control('sntp_off')
        time_evidence=Evidence(root/'time-wire.jsonl')
        client=EvidenceClient(RecordedBackend('hci0',lambda value:time_evidence.record('gatt',value=value)),
                              evidence=time_evidence,timeout=5)
        try:
            identity=client.connect(plan['ble_address'],DEVICE,allow_pairing=False)
            require(identity['generation']==plan['profile_generation'],'retained BLE generation')
            client.authorize(password);hello=client.enable_local_control()
            require(hello['boot_id']==boot,'time client boot')
            time_result=run_time(client,observer,plan['source_commit'],boot,time_evidence,
                lambda:control('sntp_on'),lambda:control('sntp_off'))
            save(root/'time-result.json',time_result)
        finally:
            client.close();time_evidence.close();password=''
    if not (scope=='application' or skip):control('sntp_on')
    network.ROOT=root # Shared WTP schema is separately staged and hash-verified.
    if scope=='application':
        result=application_stage(plan,observer,root,control)
        save(root/'remote-result.json',dict(status='APPLICATION_CASES_COMPLETE_REVIEW_REQUIRED',
            application=result,time_cases=[],directed_waves=0,simulated_jobs=0,rf_jobs=0,
            full_composition_qualified=False,pending=['independent evidence review and planned restoration']))
        return dict(status='APPLICATION_CASES_COMPLETE_REVIEW_REQUIRED',saves=4,normal_reboots=1,simulated_jobs=0,rf_jobs=0)
    # End time-carrier allocations before selecting a resource baseline.
    deadline=time.monotonic()+30
    while True:
        info=guard(observer()[0],plan,empty=True)
        if (info['ble_active_connections']==0 and info['network_active_connections']==0 and
                info['network_pending_connections']==0 and not info['ble_indication_pending']):break
        require(time.monotonic()<deadline,'time carrier reclamation');time.sleep(.5)
    composition=strict((root/'engineering-composition-template.json').read_bytes())
    composition.update(source_commit=plan['source_commit'],image_sha256=plan['image_sha256'],device_id=DEVICE,
        boot_id=boot,firmware=info['firmware'],core0_stack_capacity_bytes=32768,
        controller_acl_credits_required=True,controller_acl_min_free_slots=0)
    validate_plan(composition);save(root/'composition-plan.json',composition);save(root/'directed-plan.json',plan)
    first_sample=threading.Event();finished=threading.Event();failures=[];baseline=[]
    def capture_clock():
        current=time.monotonic()
        if not baseline:baseline.append(current)
        return current
    def observed():
        require(not failures,'engineering directed wave failed')
        value=observer();first_sample.set();return value
    def drive():
        try:
            require(first_sample.wait(10),'resource baseline missing')
            directed_waves(root,lambda path:run_device(plan,path,lambda:observer()[0],observe_original_info=observer),baseline[0])
        except BaseException as error:
            failures.append(dict(type=type(error).__name__,message=str(error)))
            save(root/'directed-failure.json',failures[-1])
        finally:finished.set()
    worker=threading.Thread(target=drive,daemon=True);worker.start()
    capture(composition,CONSOLE,root/'composition-capture.jsonl',observer=observed,clock=capture_clock)
    require(finished.is_set() and not failures,'engineering directed wave incomplete/failed')
    args=SimpleNamespace(**{k:plan[k] for k in ('address','port','hostname','server_sha256','ca','cert','key')})
    class Wire:
        def record(self,kind,value):pass
    stream=network.connect(args,network.context(args),'wtp/1',Wire())
    try:
        proof=authority_capture(stream,boot,lambda:time.monotonic()-baseline[0],'tls_wtp')
        save(root/'final-authority.json',proof)
    finally:stream.close()
    application=application_stage(plan,observer,root,control)
    save(root/'remote-result.json',dict(status='CASES_COMPLETE_REVIEW_REQUIRED',time_cases=time_result['cases'],
        directed_waves=2,simulated_jobs=6,rf_jobs=0,samples=241,full_composition_qualified=False,
        application=application,saves=4,normal_reboots=1,
        pending=['retained HTTPS sessions in ordinary composition',
                 'BLE excess peer pressure','ordinary-save serialization overlap','independent evidence review']))
    return dict(status='CASES_COMPLETE_REVIEW_REQUIRED',simulated_jobs=6,rf_jobs=0)


def main():
    os.umask(0o077)
    request=strict(sys.stdin.buffer.readline(65537))
    def stopped(*_):raise KeyboardInterrupt('engineering parent lost or interrupted')
    signal.signal(signal.SIGTERM,stopped)
    def watch():
        if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=watch,daemon=True).start()
    print(json.dumps(run(request)),flush=True)


if __name__=='__main__':main()
