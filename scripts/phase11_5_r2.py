#!/usr/bin/env python3
"""Opt-in R2 first RF gate, with separate host/device restoration and no RF retries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
from phase11_5_inventory import require
from phase11_5_device_fixture import DeviceFixture
from phase11_5_device_management import digest
from phase11_5_network_fixture import Fixture, PREFIX
from phase11_5_time_local import fixture_admission
from phase11_5_r2_plan import SOURCE, IMAGE, SCHEMA, SECONDS, jobs, validate
from phase11_5_f1_plan import admit_caps
from audit_phase11_5_r2 import audit


R2_HELPERS = {'scripts/'+name+'.py' for name in ('phase11_5_r2', 'phase11_5_r2_plan',
    'audit_phase11_5_r2', 'phase11_5_f1_plan', 'phase11_5_browser_jobs', 'phase11_5_rf_observer',
    'audit_phase11_5_a3', 'audit_phase11_5_idle', 'audit_phase11_5_load', 'audit_phase11_5_r1',
    'phase11_5_r1')} | {'src/campaign/plan.py'}


def tone_packet(root, packet, d, f):
    current=d.check_current('r2-tone-admission')
    require(current['wtp']['STATUS']['terminal_records']==[], 'R2 first gate requires empty history')
    target=root/'r2-tone';target.mkdir(mode=0o700)
    source=packet['source_revision']
    from phase11_5_r2_plan import AMENDED_SCHEMA, AMENDED_SOURCE, AMENDED_IMAGE
    rf=dict(schema=AMENDED_SCHEMA if source==AMENDED_SOURCE else SCHEMA,
        source_revision=source,revision=source[:12],uf2_sha256=AMENDED_IMAGE if source==AMENDED_SOURCE else IMAGE,
        serial=packet['serial'],device_id=packet['device_id'],system_clock_hz=138000000,
        pio_divider=1,listener_enabled=True,rf_render_in_ram=True,boot_id=d.state['boot'],
        host_boot_id=packet['host_boot_id'],nonce=packet['rf_nonce'],jobs=packet['rf_jobs'],
        owner_id=packet['rf_owner_id'],browser_session_id=packet['rf_session_id'],
        browser_profile='N',nominal_seconds=SECONDS,submission_path='browser',prior_terminal_records=[],
        baseline=str(root/'r2-tone-admission.stdout'))
    validate(rf);admit_caps(rf,current['wtp']['CAPS'])
    (target/'jobs.json').write_text(json.dumps(rf,indent=2)+'\n')
    namespaces={key:f.in_client(['readlink',path]).stdout.strip() for key,path in
                [('netns','/proc/self/ns/net'),('mountns','/proc/self/ns/mnt')]}
    plan=dict(boot_id=d.state['boot'],device_id=packet['device_id'],seconds=SECONDS,browser=True,
        address='10.77.15.10',**namespaces,binary=packet['production_binary'],
        binary_sha256=packet['production_binary_sha256'],ini=str(root/'production.ini'),
        ini_sha256=packet['production_ini_sha256'],observer=packet['production_observer'],
        observer_sha256=packet['production_observer_sha256'],ca=str(root/'credentials/browser/client-ca.crt'),
        browser_cert=str(root/'credentials/browser/client.crt'),browser_key=str(root/'credentials/browser/client.key'),
        browser_lock=str(target/'browser.lock'),browser_control_lane=True,browser_profile='N',rf_family='R2')
    (target/'load.json').write_text(json.dumps(plan,indent=2)+'\n')
    pid=f.value('systemctl','show',PREFIX+'-client','-p','MainPID','--value')
    commands=dict(observer=['python3',str(root/'scripts/phase11_5_rf_observer.py'),
        '--packet',str(target/'jobs.json'),'--baseline',rf['baseline'],'--output',str(target/'usb-health.jsonl'),
        '--session-id',secrets.token_hex(16),'--seconds',str(SECONDS+60),'--run'],
        load=['nsenter','-t',pid,'-m','-n','python3',packet['production_driver'],'--root',str(target),
            '--seconds',str(SECONDS),'--browser','--boot',d.state['boot'],'--run'],
        actor=['nsenter','-t',pid,'-m','-n','python3',str(root/'scripts/phase11_5_browser_jobs.py'),
            '--root',str(target),'--run'])
    (target/'execution.json').write_text(json.dumps(commands,indent=2)+'\n')
    processes={};streams=[];result=dict(result='FAILED',observer_exit=None,load_exit=None)
    def start(label):
        stream=(target/(label+'.log')).open('x');streams.append(stream)
        processes[label]=subprocess.Popen(commands[label],stdout=stream,stderr=subprocess.STDOUT)
    try:
        start('observer');time.sleep(1)
        require(processes['observer'].poll() is None,'Observer startup failed')
        start('load');end=time.monotonic()+40
        while not (target/'ready.json').exists() and time.monotonic()<end:
            require(all(p.poll() is None for p in processes.values()),'Worker failed before readiness')
            time.sleep(.1)
        ready=json.loads((target/'ready.json').read_text())
        require(ready['boot_id']==d.state['boot'] and
                0<=time.monotonic_ns()-ready['start_monotonic_ns']<5*10**9,'Stale load readiness')
        start('actor');end=time.monotonic()+SECONDS+65
        while time.monotonic()<end:
            # Do not kill read-only USB observation merely because the network
            # actor/load fails. Record the failure and let its bounded interval
            # retain final authoritative state. No dependent actor is restarted.
            if all(p.poll() is not None for p in processes.values()):break
            if any(processes[name].poll() is not None and processes[name].returncode
                   for name in ('observer','load')):
                if processes['actor'].poll() is None:processes['actor'].terminate()
            time.sleep(.1)
        require(all(p.poll()==0 for p in processes.values()),'R2 RF workers did not all finish')
        result['result']='CAPTURED_REQUIRES_AUDIT'
    finally:
        for label,p in processes.items():
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=20)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
            if label in ('observer','load'):result[label+'_exit']=p.returncode
        for stream in streams:stream.close()
        (target/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        (target/'actor-result.json').write_text(json.dumps(dict(exit=processes['actor'].returncode if 'actor' in processes else None))+'\n')
    value=audit(target,root/'pi/phase115_tls_observer_test.py')
    (target/'audit.json').write_text(json.dumps(value,indent=2)+'\n')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--packet-sha256',required=True)
    p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no host, network or device access.');return
    require(sys.platform=='linux' and os.geteuid()==0,'wspr5 root required')
    os.umask(0o077);root=a.root.resolve(strict=True)
    require(root.is_dir() and root.stat().st_mode & 0o077 == 0, 'Private R2 directory required')
    require(digest(root/'packet.json')==a.packet_sha256,'Frozen R2 packet changed')
    packet=json.loads((root/'packet.json').read_text())
    require(packet['status']=='FROZEN_R2' and packet.get('fixture_authorized') is True and
            packet.get('current_wiring_confirmed') is True, 'R2 fixture/wiring authorization not recorded')
    require(packet['family']=='R2' and packet['source_revision']==SOURCE and packet['runtime_seconds']==2700 and
            packet['network_runtime_seconds']==4200 and packet['rf_jobs']==jobs(packet['rf_nonce']) and
            packet['time_server_mdns'] is True and packet['network_root']==str(root), 'R2 finite scope')
    require(not (root/'r2-result.json').exists(),'No R2 rerun')
    DeviceFixture(root).verify_helpers()
    require(set(packet['case_helper_sha256'])==R2_HELPERS, 'Incomplete R2 helper identity set')
    for group in ('case_helper_sha256','production_helper_sha256'):
        for relative,expected in packet[group].items():
            path=(root/relative).resolve(strict=True)
            require(path.is_relative_to(root) and digest(path)==expected,'R2 helper changed')
    for file,sha in (('production_binary','production_binary_sha256'),('production_observer','production_observer_sha256')):
        require(digest(Path(packet[file]))==packet[sha], 'Production artifact changed')
    require(digest(root/'production.ini')==packet['production_ini_sha256'],'Production INI changed')
    result=dict(family='R2',status='RUNNING',completed_jobs=0,required_jobs=7,family_closed=False,
        packet_sha256=a.packet_sha256,accepted_configurations=[])
    def save():(root/'r2-result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(label,command,timeout):
        result['stage']=label;save()
        with (root/(label+'.log')).open('x') as out:
            rc=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,timeout=timeout).returncode
        require(rc==0,label+' failed; stop dependent actions')
    def device(action):run('device-'+action,['python3',str(root/'scripts/phase11_5_device_fixture.py'),action,'--root',str(root),'--run'],180)
    try:
        run('host-setup',['python3',str(root/'scripts/phase11_5_network_fixture.py'),'setup','--root',str(root),'--run'],330)
        f=Fixture(root);f.verify();fixture_admission(f,root,'r2-fixture-time')
        device('start');device('switch');d=DeviceFixture(root)
        for index in range(13):
            current=d.check_current('r2-ready-'+str(index))
            if current['wtp']['GET_CLOCK']['state']=='synchronized' and current['info']['network']['ipv4']=='10.77.15.10' and current['info']['network']['ntp_address']=='10.77.15.1':break
            require(index<12,'R2 target network/time deadline');time.sleep(5)
        require(time.monotonic_ns()+(SECONDS+300)*10**9<d.state['deadline_monotonic_ns'],'R2 restoration reserve')
        result['stage']='tone-gate';save();result['tone']=tone_packet(root,packet,d,f)
        result['completed_jobs']=3;result['status']='TONE_GATE_PASSED_R2_REMAINS_OPEN'
    except BaseException as error:
        result['status']='FAILED';result['error']=type(error).__name__+': '+str(error);result['failed_stage']=result.get('stage')
    finally:
        if (root/'device-state.json').exists():
            try:device('restore');result['device_restored']=True
            except BaseException as error:result['restore_error']=type(error).__name__+': '+str(error)
        if (root/'fixture-state.json').exists():
            try:
                run('host-cleanup',['python3',str(root/'scripts/phase11_5_network_fixture.py'),'cleanup','--root',str(root),'--run'],600)
                result['host_restored']=True
            except BaseException as error:result['host_restore_error']=type(error).__name__+': '+str(error)
        save()
    require(result['status']=='TONE_GATE_PASSED_R2_REMAINS_OPEN' and result.get('device_restored') and result.get('host_restored'),'R2 first packet incomplete; preserve evidence')

if __name__=='__main__':main()
