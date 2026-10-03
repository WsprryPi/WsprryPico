#!/usr/bin/env python3
"""Parent-owned B engineering time cases and ordinary two-hour resource capture."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time
from types import SimpleNamespace
import inhibited_network_acceptance as network
from phase12_composition_capture import capture
from phase12_composition_audit import validate_plan,counter
from phase12_consumer_composition import Evidence
from phase12_consumer_dispatch import directed_waves
from phase12_engineering_composition import run_device,guard
from phase12_engineering_setup import RecordedBackend,private_bytes
from phase12_engineering_time import EvidenceClient,run as run_time
from phase12_engineering_fixture import action as fixture
from phase12_serial_observer import Observer
from phase12_authority_capture import capture as authority_capture
from phase12_recovery_device import DEVICE,CONSOLE,strict,require
from check_standalone_image import validate_uf2

AUTHORITY='USER_AUTHORIZED_UNATTENDED_PHASE12'


def save(path,value):
    with path.open('x') as file:
        os.chmod(path,0o600);json.dump(value,file);file.write('\n');file.flush();os.fsync(file.fileno())


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
    control('sntp_on')
    # End time-carrier allocations before selecting a resource baseline.
    deadline=time.monotonic()+30
    while True:
        info=guard(observer()[0],plan,empty=True)
        if (info['ble_active_connections']==0 and info['network_active_connections']==0 and
                info['network_pending_connections']==0 and not info['ble_indication_pending']):break
        require(time.monotonic()<deadline,'time carrier reclamation');time.sleep(.5)
    network.ROOT=root  # Root contains the separately hash-verified protocol schema.
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
    save(root/'remote-result.json',dict(status='CASES_COMPLETE_REVIEW_REQUIRED',time_cases=time_result['cases'],
        directed_waves=2,simulated_jobs=6,rf_jobs=0,samples=241,full_composition_qualified=False,
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
