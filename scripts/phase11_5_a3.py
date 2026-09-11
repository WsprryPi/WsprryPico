#!/usr/bin/env python3
"""Opt-in A3: three 10-second 135.5 kHz Tone jobs under the frozen nominal load.

Requires both A2 baselines, exact lifecycle admission and a frozen helper manifest.
No flash, configuration, retry, automatic abort, release or recovery on failure.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from phase11_5_device_fixture import DeviceFixture
from phase11_5_network_fixture import Fixture,PREFIX
from phase11_5_pilot import validate_packet
from phase11_5_inventory import require
from audit_phase11_5_a3 import audit


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no hardware or file access');return
    require(sys.platform=='linux' and os.geteuid()==0,'wspr5 root required')
    os.umask(0o077);root=a.root.resolve(strict=True);manifest=json.loads(a.manifest.read_text())
    require(sha(root/'packet.json')==manifest['lifecycle_packet_sha256'],'Lifecycle packet changed')
    for path,expected in manifest['helper_sha256'].items():require(sha(Path(path))==expected,'Helper changed')
    d=DeviceFixture(root);d.verify_helpers();f=Fixture(root);f.verify()
    require(d.state['kind']=='physical' and not d.state.get('pending') and
            time.monotonic_ns()+600_000_000_000<d.state['deadline_monotonic_ns'],'Physical lifecycle/time admission')
    for kind in ('inhibited','physical'):
        result=json.loads((root/f'a2-{kind}-browser-priority-family-result.json').read_text())
        require(result['status']=='CAPTURED_REQUIRES_FINAL_REVIEW' and
                set(result['intervals'])=={'quiet-before','controller','nominal','quiet-after'},'A2 prerequisite')
        if kind=='physical':require(result['intervals']['quiet-after']['boot']==d.state['boot'],'A2 physical boot changed')
    current=d.check_current('a3-physical-admission')
    require(current['wtp']['STATUS']['terminal_records']==[],'A3 starts with empty terminal history')
    baseline=root/'a3-physical-admission.stdout'
    target=root/'a3-physical';target.mkdir(mode=0o700)
    packet=dict(schema='phase11.5-pilot-v2',serial='0BF4B4AEC9FFB344',
        device_id='fd6127d11d6aca42a9905fa3fb1bf1d5',system_clock_hz=138000000,
        revision='4ca44943e844',source_revision='4ca44943e844465e6109719ad91b900159f9d84f',
        uf2_sha256='7235bcd8ea1e54c09c894a23558232d83c538d8cc2c1ffc78dd6b4a809c81ef5',
        host_boot_id=d.state['host_boot'],rf_render_in_ram=True,boot_id=d.state['boot'],
        baseline=str(baseline),owner_id=secrets.token_hex(16),browser_session_id=secrets.token_hex(16),
        jobs=[dict(job_id=secrets.token_hex(16),profile='rf-events/1',mode='tone',
            total_duration_ns='10000000000',allow_frequency_adjustment=True,
            events=[dict(offset_ns='0',duration_ns='10000000000',rf_on=True,
                         frequency_nhz='135500000000000')]) for _ in range(3)])
    validate_packet(packet)
    with (target/'jobs.json').open('x') as out:json.dump(packet,out,indent=2);out.write('\n')
    base=json.loads((root/'packet.json').read_text());prod=manifest['production']
    require(sha(Path(prod['production_binary']))==prod['production_binary_sha256'] and
            sha(Path(prod['production_observer']))==prod['production_observer_sha256'],'Host artifact changed')
    namespaces={key:f.in_client(['readlink',path]).stdout.strip() for key,path in
                [('netns','/proc/self/ns/net'),('mountns','/proc/self/ns/mnt')]}
    plan=dict(boot_id=d.state['boot'],device_id=packet['device_id'],seconds=180,browser=True,
        address='10.77.15.10',**namespaces,binary=prod['production_binary'],
        binary_sha256=prod['production_binary_sha256'],ini=str(root/'production.ini'),
        ini_sha256=base['production_ini_sha256'],observer=prod['production_observer'],
        observer_sha256=prod['production_observer_sha256'],ca=str(root/'credentials/browser/client-ca.crt'),
        browser_cert=str(root/'credentials/browser/client.crt'),browser_key=str(root/'credentials/browser/client.key'),
        browser_lock=str(target/'browser.lock'),browser_control_lane=True)
    with (target/'load.json').open('x') as out:json.dump(plan,out,indent=2);out.write('\n')
    scripts=Path(__file__).parent
    pid=f.value('systemctl','show',PREFIX+'-client','-p','MainPID','--value')
    commands=dict(observer=['python3',str(scripts/'phase11_5_rf_observer.py'),
        '--packet',str(target/'jobs.json'),'--baseline',str(baseline),'--output',str(target/'usb-health.jsonl'),
        '--session-id',secrets.token_hex(16),'--seconds','240','--run'],
        load=['nsenter','-t',pid,'-m','-n','python3',prod['production_driver'],'--root',str(target),
              '--seconds','180','--browser','--boot',d.state['boot'],'--run'],
        actor=['nsenter','-t',pid,'-m','-n','python3',str(scripts/'phase11_5_browser_jobs.py'),
               '--root',str(target),'--run'])
    with (target/'execution.json').open('x') as out:
        json.dump(dict(manifest_sha256=sha(a.manifest),commands=commands,packet_sha256=sha(target/'jobs.json')),
                  out,indent=2);out.write('\n')
    processes={};streams=[];result=dict(result='FAILED',observer_exit=None,load_exit=None)
    try:
        def start(label):
            stream=(target/(label+'.log')).open('x');streams.append(stream)
            processes[label]=subprocess.Popen(commands[label],stdout=stream,stderr=subprocess.STDOUT)
        start('observer');time.sleep(1)
        require(processes['observer'].poll() is None,'Observer startup failed')
        start('load');end=time.monotonic()+40
        while not (target/'ready.json').exists() and time.monotonic()<end:
            require(all(proc.poll() is None for proc in processes.values()),'Worker exited before readiness')
            time.sleep(.1)
        ready=json.loads((target/'ready.json').read_text())
        require(ready['boot_id']==d.state['boot'] and
                0<=time.monotonic_ns()-ready['start_monotonic_ns']<5_000_000_000,'Load readiness elapsed')
        start('actor');end=time.monotonic()+245
        while time.monotonic()<end:
            for label,proc in processes.items():
                if proc.poll() is not None:require(proc.returncode==0,label+' failed; stop dependent actions')
            if all(proc.poll() is not None for proc in processes.values()):break
            time.sleep(.1)
        else:raise TimeoutError('A3 supervisor deadline')
        result['result']='CAPTURED_REQUIRES_AUDIT'
    finally:
        for label,proc in processes.items():
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=35)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5);result['result']='FAILED'
            if label in ('observer','load'):result[label+'_exit']=proc.returncode
        for stream in streams:stream.close()
        (target/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        (target/'actor-result.json').write_text(json.dumps(dict(
            exit=processes['actor'].returncode if 'actor' in processes else None))+'\n')
    require(result['result']=='CAPTURED_REQUIRES_AUDIT','A3 did not complete')
    assessed=audit(target,Path(manifest['production_decoder']))
    (target/'audit.json').write_text(json.dumps(assessed,indent=2)+'\n')


if __name__=='__main__':main()
