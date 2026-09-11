#!/usr/bin/env python3
"""Run one frozen A2 idle load interval with independent USB and health observers."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time

from phase11_5_inventory import require
from phase11_5_network_fixture import Fixture, PREFIX
from phase11_5_device_fixture import DeviceFixture


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--kind',choices=('inhibited','physical'),required=True)
    parser.add_argument('--browser',action='store_true')
    parser.add_argument('--attempt',default='')
    parser.add_argument('--workload-manifest',type=Path)
    parser.add_argument('--run',action='store_true')
    args = parser.parse_args()
    if not args.run:
        print('Plan only; no fixture, process or device accessed.'); return
    require(os.geteuid()==0 and sys.platform=='linux','Linux root required')
    os.umask(0o077)
    root=args.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077 == 0,'Private root required')
    fixture=Fixture(root);fixture.verify()
    device=DeviceFixture(root);device.verify_helpers()
    require(device.state['kind']==args.kind and not device.state.get('pending') and
            time.monotonic_ns()+270_000_000_000 < device.state['deadline_monotonic_ns'],
            'Device lifecycle admission')
    require(not args.attempt or re.fullmatch('[a-z0-9-]{1,32}',args.attempt),'Invalid attempt label')
    prefix=f'a2-{args.kind}'+('-'+args.attempt if args.attempt else '')
    case=json.loads((root/(prefix+'-packet.json')).read_text())
    require(case['boot']==device.state['boot'] and
            digest(root/'scripts/phase11_5_idle_observer.py')==case['observer_sha256'],
            'A2 identity changed')
    name=prefix+'-'+('nominal' if args.browser else 'controller')
    baseline_name=name+'-admission'
    device.check_current(baseline_name)
    target=root/name;target.mkdir(mode=0o700)
    packet=json.loads((root/'packet.json').read_text())
    if args.workload_manifest:
        amendment=json.loads(args.workload_manifest.read_text())
        require(amendment['lifecycle_packet_sha256']==digest(root/'packet.json') and
                amendment['firmware_revision']==packet['source_revision'], 'Workload amendment identity')
        for path,expected in amendment['helper_sha256'].items():
            require(digest(Path(path))==expected,'Amended workload helper changed')
        packet={**packet,**amendment['production']}
    for relative,expected in packet['production_helper_sha256'].items():
        require(digest(root/relative)==expected,'Production helper changed')
    observer=Path(packet.get('production_observer','/home/pi/phase11-5-closure-fb0a2eb/phase115_tls_observer.so'))
    require(digest(observer)==packet['production_observer_sha256'],'TLS observer changed')
    pid=fixture.value('systemctl','show',PREFIX+'-client','-p','MainPID','--value')
    namespaces={key:fixture.in_client(['readlink',path]).stdout.strip()
                for key,path in [('netns','/proc/self/ns/net'),('mountns','/proc/self/ns/mnt')]}
    plan=dict(boot_id=case['boot'],device_id=packet['device_id'],seconds=180,
        browser=args.browser,address='10.77.15.10',**namespaces,
        binary=packet['production_binary'],binary_sha256=packet['production_binary_sha256'],ini=str(root/'production.ini'),
        ini_sha256=packet['production_ini_sha256'],observer=str(observer),
        observer_sha256=packet['production_observer_sha256'],
        ca=str(root/'credentials/browser/client-ca.crt'),
        browser_cert=str(root/'credentials/browser/client.crt'),
        browser_key=str(root/'credentials/browser/client.key'))
    (target/'load.json').write_text(json.dumps(plan,indent=2)+'\n')
    observer_cmd=['python3',str(root/'scripts/phase11_5_idle_observer.py'),
        '--baseline',str(root/(baseline_name+'.stdout')),'--output',str(target/'usb-health.jsonl'),
        '--session-id',case['observer_session_id'],'--seconds','240','--run']
    load_cmd=['nsenter','-t',pid,'-m','-n','python3',packet.get('production_driver',str(root/'pi/phase115_production_load.py')),
        '--root',str(target),'--seconds','180','--boot',case['boot'],
        *(['--browser'] if args.browser else []),'--run']
    frozen=dict(case=case,load=plan,observer_seconds=240,
        coordinator_sha256=digest(Path(__file__)),observer_cmd=observer_cmd,load_cmd=load_cmd)
    (target/'execution.json').write_text(json.dumps(frozen,indent=2)+'\n')
    observed=loaded=None
    result=dict(result='FAILED',observer_exit=None,load_exit=None)
    try:
        with (target/'observer.log').open('x') as o, (target/'driver.log').open('x') as l:
            observed=subprocess.Popen(observer_cmd,stdout=o,stderr=subprocess.STDOUT)
            time.sleep(1)
            require(observed.poll() is None,'Observer startup failed')
            loaded=subprocess.Popen(load_cmd,stdout=l,stderr=subprocess.STDOUT)
            end=time.monotonic()+255
            while time.monotonic()<end:
                if observed.poll() is not None:
                    require(observed.returncode==0,'Independent observation failed')
                if loaded.poll() is not None:
                    require(loaded.returncode==0,'Production/browser load failed')
                if loaded.poll() is not None and observed.poll() is not None:break
                time.sleep(.2)
            else: raise TimeoutError('A2 interval supervisor deadline')
            result['result']='CAPTURED_REQUIRES_AUDIT'
    finally:
        for label,process in [('observer',observed),('load',loaded)]:
            if process:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=35)
                    except subprocess.TimeoutExpired:
                        process.kill();process.wait(timeout=5)
                        result['result']='FAILED'
                result[label+'_exit']=process.returncode
        (target/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    require(result['result']=='CAPTURED_REQUIRES_AUDIT','A2 interval failed')


if __name__=='__main__':main()
