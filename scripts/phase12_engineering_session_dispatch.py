#!/usr/bin/env python3
"""Private accelerated B SoftAP observer; parent owns image and restoration."""
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import sys
import threading
import time

from check_standalone_image import validate_uf2
from check_usb_target import port
from phase12_composition_audit import counter
from phase12_consumer_composition import Evidence
from phase12_engineering_composition import QuietUSB
from phase12_engineering_fixture import action as fixture, command, management
from phase12_engineering_sessions import run_device
from phase12_engineering_setup import private_bytes, RecordedBackend
from phase12_engineering_time import EvidenceClient
from phase12_recovery_device import DEVICE, CONSOLE, strict, require, console
from phase12_serial_observer import Observer

AUTHORITY='USER_AUTHORIZED_UNATTENDED_PHASE12'


def ap_observation(root,source,boot,observe_info,record):
    """Actual association and interface-bound connection, independent of INFO IP."""
    name='p12-recovery-'+root.name.rsplit('-',1)[1]
    require(command('nmcli','-g','GENERAL.CONNECTION','device','show','wlan2').strip()==name,
            'owned B AP association required')
    require(command('nmcli','-g','802-11-wireless.ssid','connection','show',name).strip()=='WsprryPico-0a9d89',
            'exact B AP SSID')
    addresses=strict(command('ip','-j','-4','address','show','dev','wlan2'))
    require(any(a.get('local')=='192.168.4.2' and a.get('prefixlen')==24
                for link in addresses for a in link.get('addr_info',[])), 'actual AP source address')
    info=observe_info()
    require(info['device_id']==DEVICE and info['revision']==source[:12] and
            info['status']['boot_id']==boot,'same exact B boot during AP association')
    # A successful TCP connection is evidence of the AP path, not TLS authority.
    # Every subsequent HTTPS exchange independently verifies the B certificate.
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as stream:
        stream.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan2\0')
        stream.settimeout(3);stream.connect(('192.168.4.1',443))
        require(stream.getsockname()[0]=='192.168.4.2','actual interface-bound socket origin')
    value=dict(device_id=DEVICE,boot_id=boot,source_commit=source,interface='wlan2',
        destination='192.168.4.1',associated=True,local_ipv4='192.168.4.2')
    record('actual_ap_observation',proof=value)
    return value


def authenticate_then_stop(client, request, password, boot, stop, verify_management, deadline_guard=lambda: None):
    """One retained-peer authentication before the owned WiFi transition."""
    identity=client.connect(request['ble_address'],DEVICE,allow_pairing=False)
    require(identity['generation']==request['profile_generation'],'retained BLE generation')
    client.authorize(password)
    hello=client.enable_local_control()
    require(hello['boot_id']==boot,'retained BLE current boot')
    deadline_guard()
    stop()
    verify_management()


def run(request):
    require(request['authority']==AUTHORITY,'authority')
    selected=request.get('cookie_grace_stages',('loaded','armed','running'))
    require(isinstance(selected,(list,tuple)) and tuple(selected)==tuple(v for v in ('loaded','armed','running') if v in selected) and len(selected)>0,'ordered cookie stage selection')
    cookie_only=request.get('cookie_grace_only',False)
    require(type(cookie_only) is bool and (not cookie_only or tuple(selected)==('running',)),'explicit running-only selection')
    root=Path(request['root'])
    require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and
            root.is_dir() and not root.is_symlink(),'private root')
    raw=private_bytes(root/'preparation-manifest.json',262144)
    require(hashlib.sha256(raw).hexdigest()==request['manifest_sha256'],'manifest binding')
    manifest=strict(raw);candidate=next(c for c in manifest['candidates'] if c['role']=='session_deadline')
    require(manifest['source_commit']==request['source_commit'] and candidate['fault_stage']==0 and
            candidate['target']=='WsprryPico','accelerated candidate binding')
    image=private_bytes(root/'session_deadline.uf2',4*1024*1024);validate_uf2(image)
    require(hashlib.sha256(image).hexdigest()==candidate['uf2']['sha256']==request['image_sha256'],
            'exact accelerated image hash')
    profile=private_bytes(root/'engineering-profile.json',7168)
    require(hashlib.sha256(profile).hexdigest()==request['profile_sha256'],'profile hash')
    profile=strict(profile);require(profile['device_id']==DEVICE,'profile B')
    password=private_bytes(root/'default-password.txt',64).decode('ascii').removesuffix('\n')
    observer=Observer();source=request['source_commit'];boot=request['boot_id']
    evidence=Evidence(root/'session-fixture-wire.jsonl');client=None
    deadline=time.monotonic()+480
    def info():
        require(time.monotonic()<deadline,'accelerated dispatcher deadline')
        value,wire=observer();evidence.record('actual_info',raw_hex=wire.hex())
        require(value['device_id']==DEVICE and value['revision']==source[:12] and
            value['status']['boot_id']==boot and
            counter(value['provisioning_generation'],'generation')==request['profile_generation'] and
            value['provisioning_source']=='provisioned' and value['status']['storage_healthy'] is True and
            value['status']['enabled'] is False and value['status']['output_active'] is False and
            value['status']['engine']=='inhibited-standalone-simulator' and value['access_state']=='healthy',
            'exact healthy inhibited B profile/boot')
        return value
    before=management()
    try:
        info()
        client=EvidenceClient(RecordedBackend('hci0',lambda value:evidence.record('gatt',value=value)),
                              evidence=evidence,timeout=5)
        authenticate_then_stop(client, request, password, boot,
            lambda: fixture(dict(root=str(root),authority=AUTHORITY,action='stop')),
            lambda: require(management()==before,'management changed by isolated fixture stop'),
            lambda: require(time.monotonic()<deadline,'accelerated dispatcher deadline'))
        def refresh():
            info();client.synchronize_time()
            field=client.field_status()
            require(field['time_source']=='controller' and not field['time_disagreement'],
                    'authenticated controller time prerequisite')
            evidence.record('accepted_controller_time',field=field)
        refresh()
        name='p12-recovery-'+root.name.rsplit('-',1)[1]
        require(name in command('nmcli','-t','-f','NAME','connection','show').splitlines(),
                'parent-owned AP profile missing')
        command('sudo','-n','nmcli','connection','modify',name,
            '802-11-wireless-security.key-mgmt','wpa-psk','802-11-wireless-security.psk',password)
        # Exactly one join-grace request. An uncertain result is never repeated.
        info();evidence.record('one_ap_join_attempt',device_id=DEVICE)
        result=console('ACCESS SOFTAP '+DEVICE)
        require(result==dict(ok=True,join_grace_ms=120000),'AP join grace refused')
        evidence.record('ap_join_result',value=result)
        command('sudo','-n','nmcli','connection','up',name)
        require(management()==before,'management changed during B AP association')
        with ExitStack() as stack:
            fd=stack.enter_context(port(CONSOLE.replace('-if00','-if02')))
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            usb=QuietUSB(fd,lambda kind,value:evidence.record(kind,value=value))
            hello=usb.request('HELLO',dict(versions=['WTP/1'],client_name='phase12-session-observer',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==boot,'USB actual B AP peer')
            status=lambda:usb.request('STATUS',{})
            ap=lambda:ap_observation(root,source,boot,info,evidence.record)
            if not cookie_only:
                run_device(candidate,manifest,'192.168.4.1',boot,profile['tls']['hostname'],
                           root/'client-ca.crt',password,root/'session-wire.jsonl',info,status,ap)
            refresh()
            from phase12_engineering_cookie_grace import run as grace
            from phase12_engineering_sessions import HTTPS
            grace_result=grace(HTTPS('192.168.4.1',profile['tls']['hostname'],root/'client-ca.crt',evidence),
                info,status,ap,refresh,evidence,password,source,boot,
                profile_generation=request['profile_generation'],
                stages=request.get('cookie_grace_stages',('loaded','armed','running')))
            evidence.record('cookie_grace_result',value=grace_result)
        result=dict(status='SESSIONS_REVIEW_REQUIRED',cookie_pressure=not cookie_only,idle_expiry=not cookie_only,absolute_expiry=not cookie_only,
                    cookie_grace_stages=list(selected),cookie_grace_only=cookie_only,
                    cookie_grace=grace_result,rf_jobs=0,physical_acceptance=False)
        path=root/'session-result.json'
        with path.open('x') as file:os.chmod(path,0o600);json.dump(result,file);file.write('\n')
        return dict(status=result['status'],rf_jobs=0)
    finally:
        try:
            if client is not None:client.close()
        finally:
            evidence.close();password=''


def main():
    os.umask(0o077);request=strict(sys.stdin.buffer.readline(65537))
    def stopped(*_):raise KeyboardInterrupt('session parent lost/interrupted')
    signal.signal(signal.SIGTERM,stopped)
    def watch():
        if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=watch,daemon=True).start()
    print(json.dumps(run(request)),flush=True)


if __name__=='__main__':main()
