#!/usr/bin/env python3
"""Private one-apply engineering journal dispatcher; parent owns flashing/readback/TLS stage orchestration."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time
from phase12_engineering_dispatch import save, AUTHORITY
from phase12_engineering_fixture import action as fixture
from phase12_engineering_journal import apply_once, tls_probe
from phase12_engineering_setup import private_bytes, RecordedBackend, RecordedClient
from phase12_consumer_composition import Evidence
from phase12_serial_observer import Observer
from phase12_recovery_device import DEVICE, console, strict, require
from phase12_recovery_orchestrator import safe_info
from phase12_composition_audit import counter
from check_standalone_image import validate_uf2


def run(request):
    require(request['authority'] == AUTHORITY, 'authority')
    root = Path(request['root'])
    require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}', str(root)) and
            root.is_dir() and not root.is_symlink(), 'private root')
    stage = request['stage']; require(stage in (0, 8, 9, 10), 'named stage')
    raw = private_bytes(root/'preparation-manifest.json', 262144)
    require(hashlib.sha256(raw).hexdigest() == request['manifest_sha256'], 'manifest binding')
    manifest = strict(raw)
    role = 'engineering' if stage == 0 else 'fault_'+str(stage)
    require(request.get('candidate_role',role)==role, 'exact declared stage role')
    candidates = [c for c in manifest['candidates'] if c['role'] == role]
    require(len(candidates) == 1, 'exact one candidate')
    candidate = candidates[0]
    require(manifest['source_commit'] == request['source_commit'] and
            candidate['target'] == 'WsprryPico' and candidate['fault_stage'] == stage and
            candidate['lan_mode'] == ('tls' if stage == 0 else 'plain'), 'inhibited engineering candidate')
    image_name = request['image_name']; require(image_name==role+'.uf2', 'exact stage image basename')
    image = private_bytes(root/image_name, 4*1024*1024); validate_uf2(image)
    require(hashlib.sha256(image).hexdigest() == candidate['uf2']['sha256'] == request['image_sha256'], 'image bytes')
    if request.get('action') == 'observe_checkpoint':
        observer=Observer();deadline=time.monotonic()+min(90,request['remaining_s'])
        def remaining():
            left=deadline-time.monotonic()
            require(left>0,'checkpoint observation deadline')
            return left
        while True:
            remaining()
            try:info,wire=observer()
            except (OSError,TimeoutError):
                time.sleep(min(.5,remaining()));continue
            remaining()
            if info['status']['boot_id']==request['boot_id'] or (stage and info.get('phase12_fault_consumed') is not True):
                time.sleep(min(.5,remaining()));continue
            safe_info(info,request['source_commit'][:12],stage,bool(stage))
            require(info['provisioning_source']=='provisioned' and info['lan_wtp_mode']=='engineering-tls','exact source1 carrier')
            remaining()
            return dict(info=info,wire_hex=wire.hex(),rf_jobs=0)
    if request.get('action') == 'tls':
        require(stage == 0, 'readonly TLS uses ordinary engineering image')
        evidence = Evidence(root/('journal-tls-'+str(request['journal_stage'])+'-wire.jsonl'))
        observer = Observer(); deadline = time.monotonic()+min(90,request['remaining_s'])
        def remaining():
            left=deadline-time.monotonic()
            require(left>0,'fresh SNTP TLS readiness')
            return left
        def guard():
            remaining()
            info,wire=observer();evidence.record('tls_usb_info',raw_hex=wire.hex())
            remaining()
            require(strict(wire)==info,'actual TLS INFO wire')
            safe_info(info,request['source_commit'][:12],0,False)
            require(info['status']['boot_id']==request['boot_id'] and
                    counter(info['provisioning_generation'],'gen')==request['profile_generation'], 'TLS boot/gen')
            remaining();return info
        try:
            time_started=False
            while True:
                info=guard()
                if info['network']['link_status']==3 and info['network']['ipv4'].startswith('192.168.84.') and not time_started:
                    fixture(dict(root=str(root),authority=request['authority'],action='bind_peer',address=info['network']['ipv4']))
                    remaining()
                    fixture(dict(root=str(root),authority=request['authority'],action='sntp_on'))
                    remaining()
                    time_started=True
                if (info['network']['link_status']==3 and info['status']['clock_state']=='synchronized' and
                        info['network']['ipv4'].startswith('192.168.84.') and
                        info['network']['ntp_server']=='192.168.84.1' and
                        info['network']['ntp_address']=='192.168.84.1' and
                        counter(info['network']['accepted'],'SNTP accepted')>0):break
                time.sleep(min(.5,remaining()))
            selected_payload=private_bytes(root/('engineering-profile-'+request['selected']+'.json'),7168)
            require(hashlib.sha256(selected_payload).hexdigest()==request['selected_profile_sha256'], 'selected profile archive hash')
            selected_profile=strict(selected_payload)
            require(selected_profile['device_id']==DEVICE and selected_profile['tls']['hostname']==request['hostname'] and
                    selected_profile['tls']['port']==443 and selected_profile['wifi']['time_server']=='192.168.84.1',
                    'selected exact device/hostname/port/time source')
            server_ca=root/('journal-'+request['selected']+'-ca.crt')
            require(private_bytes(server_ca,16384).decode('ascii')==selected_profile['tls']['client_ca'], 'selected server CA matches exact profile')
            plan=dict(address=info['network']['ipv4'],port=443,hostname=request['hostname'],ca=str(server_ca),
                server_sha256=request['server_sha256'],device_id=DEVICE,boot_id=request['boot_id'])
            probes={}
            for role in (request['selected'],*sorted({'A','B','C'}-{request['selected']})):
                guard()
                principal={key:str(root/('journal-'+role+'-'+key+('.crt' if key!='key' else '.key')))
                           for key in ('ca','cert','key')}
                for key,path in principal.items():
                    require(hashlib.sha256(private_bytes(Path(path),16384)).hexdigest()==
                            request['principal_hashes'][role][key], 'exact independently staged client identity')
                remaining()
                probes[role]=tls_probe(plan,principal,evidence)
                remaining()
                guard()
            remaining()
            result=dict(probes=probes,boot_id=request['boot_id'],rf_jobs=0)
            save(root/('journal-tls-'+str(request['journal_stage'])+'-result.json'),result)
            remaining()
            return result
        finally:evidence.close()
    selected = 'B' if stage == 0 else 'C'
    payload = bytearray(private_bytes(root/('engineering-profile-'+selected+'.json'), 7168))
    require(hashlib.sha256(payload).hexdigest() == request['profile_sha256'] and
            strict(bytes(payload))['device_id'] == DEVICE, 'exact replacement')
    password = private_bytes(root/'default-password.txt', 64).decode('ascii').removesuffix('\n')
    evidence = Evidence(root/('journal-apply-'+str(stage)+'-wire.jsonl'))
    observer = Observer()
    client = RecordedClient(RecordedBackend('hci0', lambda value:evidence.record('gatt', value=value)),
                            lambda value:evidence.record('field', value=value))
    try:
        context = dict(request, generation=request['profile_generation'])
        result = apply_once(context, payload, password, client, observer,
                            lambda text:console(text), evidence)
        save(root/('journal-apply-'+str(stage)+'-result.json'), result)
        return result
    finally:
        payload[:] = bytes(len(payload)); password = ''; client.close(); evidence.close()


def main():
    os.umask(0o077); request = strict(sys.stdin.buffer.readline(65537))
    def stopped(*_):raise KeyboardInterrupt('journal parent lost/interrupted')
    signal.signal(signal.SIGTERM, stopped)
    def watch():
        if os.read(sys.stdin.fileno(), 1) == b'':os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=watch, daemon=True).start()
    print(json.dumps(run(request)), flush=True)


if __name__ == '__main__':main()
