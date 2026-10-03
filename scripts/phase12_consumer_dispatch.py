#!/usr/bin/env python3
"""Private wspr5 child: real serial observer plus finite inhibited consumer driver."""
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
from phase12_recovery_device import DEVICE, SERIAL, CONSOLE, resource_health, strict
from phase12_composition_capture import capture
from phase12_consumer_composition import run_device, Evidence, require
from check_usb_target import port
from check_standalone_image import validate_uf2
from phase12_serial_observer import Observer
from phase12_authority_capture import capture as authority_capture


WAVE_OFFSETS = (0, 2400)


def directed_waves(root, driver, baseline, *, clock=time.monotonic,
                   sleeper=time.sleep, timeline_factory=Evidence):
    """Two fixed three-job waves, no retry; each must finish before the quiet windows."""
    timeline = timeline_factory(root/'directed-wave-timeline.jsonl')
    completed = 0
    try:
        for index, offset in enumerate(WAVE_OFFSETS, 1):
            target = baseline+offset
            while clock() < target:
                sleeper(min(1, target-clock()))
            require(clock()-target <= 45, 'wave start missed bounded schedule')
            path = root/('directed-wave-%d-wire.jsonl' % index)
            timeline.record('wave_started', wave=index, scheduled_offset_s=offset,
                            observed_offset_s=clock()-baseline, wire_file=path.name,
                            simulator_job_budget=3, rf_jobs=0)
            try:
                driver(path)
                require(clock()-target <= 600, 'wave exceeded ten-minute window')
            except BaseException as error:
                timeline.record('wave_failed', wave=index, error=type(error).__name__,
                                observed_offset_s=clock()-baseline, retry=False)
                raise
            completed += 1
            timeline.record('wave_complete', wave=index, observed_offset_s=clock()-baseline,
                            simulated_jobs=3, rf_jobs=0,
                            wire_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        return completed
    finally:
        timeline.close()


def bound_inputs(root,request):
    raw=(root/'manifest.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==request['manifest_sha256'],'manifest transfer')
    manifest=strict(raw);candidate=next(c for c in manifest['candidates'] if c['role']=='restore')
    image_name=request.get('image_name','restore.uf2')
    require(image_name in ('restore.uf2','exercise.uf2'),'finite exact image name')
    path=root/image_name;require(path.is_file() and not path.is_symlink(),'regular bound exercise image')
    image=path.read_bytes();validate_uf2(image)
    require(hashlib.sha256(image).hexdigest()==candidate['uf2']['sha256'],'exact selected exercise image')
    plan=strict((root/'composition-plan.json').read_bytes())
    require(plan['image_sha256']==candidate['uf2']['sha256'] and
            plan['source_commit']==manifest['source_commit'] and plan['device_id']==DEVICE,
            'source/plan/image binding')
    require(candidate['fault_stage']==0 and candidate['session_deadline_fixture'] is False and candidate['target']=='WsprryPico' and
        candidate['revision']==manifest['source_commit'][:12] and candidate['lan_mode']=='plain' and candidate['gp14'] is False,
        'ordinary inhibited image/source binding')
    return manifest,candidate,plan


def main():
    os.umask(0o077)
    request=strict(sys.stdin.buffer.readline(65537))
    require(request['authority']=='USER_AUTHORIZED_UNATTENDED_PHASE12','authority')
    root=Path(request['root'])
    require(re.fullmatch(r'/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and
            root.is_dir() and not root.is_symlink(),'private root')
    manifest,candidate,plan=bound_inputs(root,request)
    fresh=Observer();first=threading.Event();finished=threading.Event()
    failures=[];baseline=[]
    def signal_stop(*_):raise KeyboardInterrupt('parent connection lost or interrupted')
    signal.signal(signal.SIGTERM,signal_stop)
    def parent_watch():
        # Avoid holding a buffered-reader lock in a daemon during interpreter
        # shutdown; the stopped attempt retained that CPython shutdown failure.
        if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=parent_watch,daemon=True).start()
    def observe_raw():
        require(not failures,'directed driver failed')
        return fresh()
    def capture_clock():
        current=time.monotonic()
        if not baseline:baseline.append(current)
        return current
    def observer():
        value=observe_raw()
        first.set()
        return value
    def drive():
        first.wait(10)
        try:
            require(first.is_set(),'initial observation missing')
            directed_waves(root, lambda path:run_device(
                candidate,manifest,request['address'],plan['boot_id'],path,
                observe_info=lambda:observe_raw()[0]), baseline[0])
        except BaseException as error:failures.append(type(error).__name__)
        finally:finished.set()
    worker=threading.Thread(target=drive,daemon=True);worker.start()
    try:
        capture(plan,CONSOLE,root/'composition-capture.jsonl',observer=observer,clock=capture_clock)
        require(finished.is_set() and not failures,'directed driver incomplete/failed')
        # This proof must precede the parent's reboot/restoration. INFO does
        # not contain WTP ownership fields and cannot substitute for STATUS.
        with socket.create_connection((request['address'],31417),timeout=5) as stream:
            proof=authority_capture(stream,plan['boot_id'],lambda:time.monotonic()-baseline[0],'plain_lan')
        with (root/'final-authority.json').open('x') as file:
            os.chmod(file.name,0o600);json.dump(proof,file);file.write('\n');file.flush();os.fsync(file.fileno())
        (root/'remote-result.json').write_text(json.dumps(dict(status='CAPTURE_COMPLETE_REVIEW_REQUIRED',
            samples=241,simulated_jobs=6,directed_waves=2,rf_jobs=0,physical_acceptance=False,
            quiet_windows_s=[[1200,2160],[6000,7200]],
            coverage='PLAIN_LAN_CONTROL_USB_INFO_DIRECTED_WAVES_AND_RESOURCE_CAPTURE',
            full_composition_qualified=False))+'\n')
        print(json.dumps(dict(status='CAPTURE_COMPLETE_REVIEW_REQUIRED',samples=241,directed_waves=2,simulated_jobs=6,rf_jobs=0)),flush=True)
    finally:
        # A failed collector stops the whole child; parent restores after leases expire.
        if not finished.is_set():failures.append('collector_stopped')


if __name__=='__main__':main()
