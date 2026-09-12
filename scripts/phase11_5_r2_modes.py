#!/usr/bin/env python3
"""One finite remaining-mode R2 campaign, with existing independent restoration."""
import argparse
import configparser
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from phase11_5_inventory import require
from phase11_5_device_fixture import DeviceFixture
from phase11_5_device_management import digest,save
from phase11_5_network_fixture import Fixture,PREFIX
from phase11_5_time_local import fixture_admission
from phase11_5_f1_plan import admit_caps
from phase11_5_r2_modes_plan import SCHEMA,SOURCE,PHYSICAL,COUNTS,jobs,validate
from audit_phase11_5_r2_modes import audit


CASE_HELPERS={str(p.relative_to(Path(__file__).resolve().parents[1])) for p in Path(__file__).resolve().parent.glob('*.py')
              if p.name.startswith(('phase11_5_', 'audit_phase11_5_', 'validate_phase11_5_'))} | {
              'scripts/phase11_4_hotspot.py','scripts/wtp_monitor.py','scripts/validate_wtp_contract.py',
              'src/campaign/plan.py','docs/protocol/wtp-1.schema.json'}


def run_packet(root,packet,d,f,path):
    source = packet['source_revision']
    physical = packet['images']['physical']['sha256']
    current=d.check_current(path+'-admission')
    target=root/path;target.mkdir(mode=0o700)
    nonce=packet['mode_nonces'][path]
    rf=dict(schema=SCHEMA,source_revision=source,revision=source[:12],uf2_sha256=physical,
        serial=packet['serial'],device_id=packet['device_id'],system_clock_hz=138000000,pio_divider=1,
        listener_enabled=True,rf_render_in_ram=True,boot_id=d.state['boot'],host_boot_id=packet['host_boot_id'],
        nonce=nonce,jobs=jobs(nonce,path),owner_id=packet['mode_owner_id'],browser_profile='N',nominal_seconds=300,
        submission_path=path,maximum_renewals=12,baseline=str(root/(path+'-admission.stdout')),
        prior_terminal_records=current['wtp']['STATUS']['terminal_records'])
    namespaces={key:f.in_client(['readlink',p]).stdout.strip() for key,p in
                [('netns','/proc/self/ns/net'),('mountns','/proc/self/ns/mnt')]}
    ini=root/'production.ini';start_utc=None
    if path=='production':
        c=configparser.ConfigParser(interpolation=None);c.optionxform=str;c.read(ini)
        # Freeze a single native scheduled launch far enough ahead to bind its
        # generated identity and start all observations. Next schedule is one hour later.
        start_utc=(time.time_ns()//10**9+90)*10**9
        utc=time.gmtime(start_utc//10**9)
        c['Operation']['Transmit']='true';c['Operation']['Enable on Boot']='Follow';c['Operation']['Mode']='QRSS'
        c['CW'].update({'Message':'ETE','Base Frequency':'135500','Dot Seconds':'3',
            'Inter Character Gap':'3','Fade Shape':'none','Start Minute':str(utc.tm_min),
            'Start Second':str(utc.tm_sec),'Repeat Minutes':'60'})
        ini=target/'production-job.ini'
        with ini.open('x') as out:c.write(out)
    plan=dict(boot_id=d.state['boot'],device_id=packet['device_id'],seconds=300,browser=True,
        address='10.77.15.10',**namespaces,binary=packet['production_binary'],
        binary_sha256=packet['production_binary_sha256'],ini=str(ini),ini_sha256=digest(ini),
        observer=packet['production_observer'],observer_sha256=packet['production_observer_sha256'],
        ca=str(root/'credentials/browser/client-ca.crt'),browser_cert=str(root/'credentials/browser/client.crt'),
        browser_key=str(root/'credentials/browser/client.key'),browser_profile='N',rf_family='R2')
    if path=='production':plan.update(production_job='QRSS-ETE-33s',production_start_utc_ns=start_utc)
    save(target/'load.json',plan)
    pid=f.value('systemctl','show',PREFIX+'-client','-p','MainPID','--value')
    commands=dict(observer=['python3',str(root/'scripts/phase11_5_rf_observer.py'),
        '--packet',str(target/'jobs.json'),'--baseline',rf['baseline'],'--output',str(target/'usb-health.jsonl'),
        '--session-id',secrets.token_hex(16),'--seconds','360','--run'],
        load=['nsenter','-t',pid,'-m','-n','python3',packet['production_driver'],'--root',str(target),
            '--seconds','300','--browser','--boot',d.state['boot'],'--run'])
    save(target/'execution.json',commands)
    processes={};streams=[];result=dict(result='FAILED',observer_exit=None,load_exit=None)
    def start(label):
        stream=(target/(label+'.log')).open('x');streams.append(stream)
        processes[label]=subprocess.Popen(commands[label],stdout=stream,stderr=subprocess.STDOUT)
    try:
        if path=='production':
            start('load');limit=time.monotonic()+40
            while not (target/'production-bound.json').exists():
                require(processes['load'].poll() is None and time.monotonic()<limit,'Production binding failed')
                time.sleep(.05)
            binding=json.loads((target/'production-bound.json').read_text())
            require(time.time_ns()+20_000_000_000<int(binding['dispatch_utc_ns']), 'Binding dispatch reserve')
            rf['production_binding']=binding;rf['owner_id']=binding['owner_id'];rf['jobs'][0]['job_id']=binding['job_id']
        validate(rf);admit_caps(rf,current['wtp']['CAPS']);save(target/'jobs.json',rf)
        start('observer');limit=time.monotonic()+5
        while not (target/'observer-info.json').exists() or not (target/'observer-status.json').exists():
            require(processes['observer'].poll() is None and time.monotonic()<limit,'Observer startup')
            time.sleep(.05)
        if path=='production':save(target/'observation-ready.json',dict(boot=d.state['boot']))
        else:start('load')
        limit=time.monotonic()+375
        while any(p.poll() is None for p in processes.values()):
            require(time.monotonic()<limit,'Bounded mode observation timeout')
            if processes['load'].poll() not in (None,0):
                save(target/'load-failed.json',dict(exit=processes['load'].returncode))
            if processes['observer'].poll() not in (None,0) and processes['load'].poll() is None:
                processes['load'].terminate()
            time.sleep(.1)
        require(all(p.returncode==0 for p in processes.values()),'Mode workers failed; no dependent RF')
        result['result']='CAPTURED_REQUIRES_AUDIT'
    finally:
        for label,p in processes.items():
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=20)
                except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
            result[label+'_exit']=p.returncode
        for stream in streams:stream.close()
        save(target/'result.json',result)
    value=audit(target,root/'pi/phase115_tls_observer_test.py');save(target/'audit.json',value)
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no host/device access.');return
    require(os.geteuid()==0,'wspr5 root required');os.umask(0o077);root=a.root.resolve(strict=True)
    require(digest(root/'packet.json')==a.packet_sha256,'Frozen remaining-mode packet changed')
    packet=json.loads((root/'packet.json').read_text())
    from phase11_5_r2_upload_plan import SOURCE as upload_source, COUNTS as upload_counts
    upload = packet.get('upload_check') is True
    source = upload_source if upload else SOURCE
    counts = upload_counts if upload else COUNTS
    require(packet['family']=='R2' and packet['remaining_modes'] is True and packet['source_revision']==source and
            packet['initial_management_counts']==counts and packet['fixture_authorized'] is True and
            packet['current_wiring_confirmed'] is True and packet['runtime_seconds']==2700 and
            packet['network_runtime_seconds']==4200,'Remaining-mode scope/counts/authority')
    require(not (root/'modes-result.json').exists(),'No remaining-mode packet replay')
    DeviceFixture(root).verify_helpers()
    require(set(packet['case_helper_sha256'])==CASE_HELPERS,'Incomplete remaining-mode helper manifest')
    require(set(packet['production_helper_sha256'])=={'pi/phase115_production_load.py','pi/phase115_tls_observer.c','pi/phase115_tls_observer_test.py'}, 'Production helper manifest')
    for group in ('case_helper_sha256','production_helper_sha256'):
        for relative,sha in packet[group].items():
            require(digest(root/relative)==sha,'Remaining-mode helper changed')
    for key in ('production_binary','production_observer'):
        require(digest(Path(packet[key]))==packet[key+'_sha256'],'Production artifact changed')
    require(digest(root/'production.ini')==packet['production_ini_sha256'],'Production INI changed')
    prior=Path(packet['reuse_evidence']['root'])
    for relative,sha in packet['reuse_evidence']['sha256'].items():require(digest(prior/relative)==sha,'Reused evidence changed')
    require(json.loads((prior/'r2-result.json').read_text())['completed_jobs']==3 and
            json.loads((prior/'r1-result.json').read_text())['source']==SOURCE,'Prior R1/Tone prerequisite')
    if upload:
        completed = Path(packet['reused_qrss']['root'])
        require(digest(completed/'production/audit.json')==packet['reused_qrss']['audit_sha256'] and
                json.loads((completed/'oom-recovery-result.json').read_text())['result']=='RESTORED_INHIBITED',
                'QRSS evidence/recovery prerequisite changed')
    result=dict(status='RUNNING',source_revision=source,completed_jobs=4 if upload else 3,required_jobs=7,family_closed=False,
                packet_sha256=a.packet_sha256,reused_R1=True,reused_Tone=True)
    def run(label,argv,seconds):
        result['stage']=label;save(root/'modes-result.json',result)
        with (root/(label+'.log')).open('x') as out:
            rc=subprocess.run(argv,stdout=out,stderr=subprocess.STDOUT,timeout=seconds).returncode
        require(rc==0,label+' failed')
    def device(action):run('device-'+action,['python3',str(root/'scripts/phase11_5_device_fixture.py'),action,'--root',str(root),'--run'],180)
    try:
        run('host-setup',['python3',str(root/'scripts/phase11_5_network_fixture.py'),'setup','--root',str(root),'--run'],330)
        f=Fixture(root);f.verify();fixture_admission(f,root,'modes-fixture-time')
        device('start');device('switch');d=DeviceFixture(root)
        for n in range(19):
            current=d.check_current('modes-ready-'+str(n))
            if current['wtp']['GET_CLOCK']['state']=='synchronized' and current['info']['network']['ipv4']=='10.77.15.10' and current['info']['network']['ntp_address']=='10.77.15.1':break
            require(n<18,'Mode clock/network readiness');time.sleep(5)
        for path in (('usb',) if upload else ('production','usb')):
            require(time.monotonic_ns()+450_000_000_000<d.state['deadline_monotonic_ns'],'Unchanged device restoration reserve')
            result['stage']=path;save(root/'modes-result.json',result)
            value=run_packet(root,packet,d,f,path);result[path]=value
            result['completed_jobs']+=value['completed_jobs'];save(root/'modes-result.json',result)
        result.update(status='PASS_REQUIRES_FINAL_REVIEW',family_closed=True)
    except BaseException as e:result.update(status='FAILED',error=type(e).__name__+': '+str(e))
    finally:
        if (root/'device-state.json').exists():
            try:device('restore');result['device_restored']=True
            except BaseException as e:result['restore_error']=str(e)
        if (root/'fixture-state.json').exists():
            try:
                run('host-cleanup',['python3',str(root/'scripts/phase11_5_network_fixture.py'),'cleanup','--root',str(root),'--run'],600)
                result['host_restored']=True
            except BaseException as e:result['host_restore_error']=str(e)
        save(root/'modes-result.json',result)
    require(result['completed_jobs']==7 and result.get('device_restored') and result.get('host_restored'),
            'R2 incomplete; preserve failed evidence')

if __name__=='__main__':main()
