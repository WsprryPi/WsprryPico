#!/usr/bin/env python3
"""Private fresh-boot T5 dispatcher; no image or host clock mutation."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time
from phase12_engineering_dispatch import save
from phase12_engineering_fixture import action as fixture
from phase12_engineering_setup import private_bytes,RecordedBackend
from phase12_engineering_time import EvidenceClient
from phase12_engineering_time_jobs import run as run_time
from phase12_consumer_composition import Evidence
from phase12_serial_observer import Observer
from phase12_composition_audit import counter
from phase12_recovery_device import DEVICE,strict,require
from check_standalone_image import validate_uf2
from wsprrypico_ble import ClientError


def retain_failure_info(request, observer, evidence, end):
    """One read-only original INFO attempt; never substitutes for the failure."""
    left=min(5.0,end-time.monotonic())
    if left<=0:
        evidence.record('failure_info_unavailable',reason='dispatcher deadline')
        return
    previous_handler=signal.getsignal(signal.SIGALRM)
    previous_timer=signal.getitimer(signal.ITIMER_REAL)
    started=time.monotonic()
    def expired(*unused):raise TimeoutError('failure INFO diagnostic deadline')
    signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,min(left,previous_timer[0]) if previous_timer[0]>0 else left)
    try:
        info,raw=observer()
        evidence.record('failure_usb_info',raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest())
        require(time.monotonic()<=end and time.monotonic()-started<=left,'late failure INFO')
        require(strict(raw)==info and info['device_id']==DEVICE and info['revision']==request['source_commit'][:12] and
                info['status']['boot_id']==request['boot_id'] and counter(info['provisioning_generation'],'generation')==request['profile_generation'],
                'failure INFO binding')
    except Exception as error:
        evidence.record('failure_info_unavailable',error_type=type(error).__name__)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous_handler)
        if previous_timer[0]>0:signal.setitimer(signal.ITIMER_REAL,max(.000001,previous_timer[0]-(time.monotonic()-started)),previous_timer[1])


def run(request):
    dispatcher_end=time.monotonic()+280
    require(request['authority']=='USER_AUTHORIZED_UNATTENDED_PHASE12','authority')
    root=Path(request['root']);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and
            root.is_dir() and not root.is_symlink(),'private root')
    image=private_bytes(root/'engineering.uf2',4*1024*1024);validate_uf2(image)
    raw=private_bytes(root/'preparation-manifest.json',262144)
    require(hashlib.sha256(raw).hexdigest()==request['manifest_sha256'],'manifest transfer')
    manifest=strict(raw);candidate=next(c for c in manifest['candidates'] if c['role']=='engineering')
    require(candidate['fault_stage']==0 and candidate['target']=='WsprryPico' and candidate['lan_mode']=='tls' and
            manifest['source_commit']==request['source_commit'] and
            hashlib.sha256(image).hexdigest()==candidate['uf2']['sha256']==request['image_sha256'],'ordinary image binding')
    observer=Observer();first=observer()[0]
    require(first['device_id']==DEVICE and first['revision']==request['source_commit'][:12] and
            first['status']['boot_id']==request['boot_id'] and
            counter(first['provisioning_generation'],'generation')==request['profile_generation'],'fresh T5 device binding')
    password=private_bytes(root/'default-password.txt',64).decode('ascii').removesuffix('\n')
    evidence=Evidence(root/'time-jobs-wire.jsonl')
    client=EvidenceClient(RecordedBackend('hci0',lambda value:evidence.record('gatt',value=value)),evidence=evidence,timeout=5)
    def control(action):return fixture(dict(root=str(root),authority=request['authority'],action=action))
    try:
        identity=client.connect(request['ble_address'],DEVICE,allow_pairing=False)
        require(identity['generation']==request['profile_generation'],'retained field generation')
        client.authorize(password);hello=client.enable_local_control()
        require(hello['boot_id']==request['boot_id'],'fresh field WTP boot')
        result=run_time(client,observer,request['source_commit'],request['boot_id'],evidence,
                        lambda:control('sntp_on'),lambda:control('sntp_off'))
        save(root/'time-jobs-result.json',result);return result
    except Exception as error:
        if isinstance(error,ClientError) and error.code=='gatt_write':
            try:retain_failure_info(request,observer,evidence,dispatcher_end)
            except Exception:pass # Preserve the original failure even if retention fails.
        raise
    finally:
        try:client.close()
        finally:evidence.close();password=''


def main():
    os.umask(0o077);request=strict(sys.stdin.buffer.readline(65537))
    def stopped(*_):raise KeyboardInterrupt('T5 parent lost/interrupted')
    signal.signal(signal.SIGTERM,stopped)
    def watch():
        if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=watch,daemon=True).start()
    print(json.dumps(run(request)),flush=True)


if __name__=='__main__':main()
