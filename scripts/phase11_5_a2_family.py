#!/usr/bin/env python3
"""Opt-in bounded A2 idle family: quiet, actual controller, browser, quiet. No RF jobs."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import secrets
import subprocess
import sys
import time
from phase11_5_device_fixture import DeviceFixture
from phase11_5_network_fixture import Fixture
from phase11_5_inventory import require
from audit_phase11_5_idle import audit as audit_idle
from audit_phase11_5_load import audit as audit_load


def resume_stages(previous):
    stage=previous.get('current_interval')
    expected={'controller':{'quiet-before'},'nominal':{'quiet-before','controller'},
              'quiet-after':{'quiet-before','controller','nominal','quiet-after'}}
    require(previous.get('status')=='FAILED' and stage in expected and
            set(previous.get('intervals',{}))==expected[stage],'Invalid preserved-stage boundary')
    if stage=='quiet-after':
        require(previous.get('error')=='ValueError: Unexplained matched quiet retained heap' and
                abs(previous.get('quiet_heap_delta_bytes',0))>1024,'Only retained-heap comparison may repeat')
    return ('controller','nominal','quiet-after') if stage=='controller' else ('nominal','quiet-after')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--kind',choices=('inhibited','physical'),required=True)
    p.add_argument('--attempt',default='')
    p.add_argument('--workload-manifest',type=Path)
    p.add_argument('--resume-from','--resume-nominal-from',dest='resume_from',type=Path)
    p.add_argument('--run',action='store_true');args=p.parse_args()
    if not args.run:print('Plan only; no host or device access');return
    require(sys.platform=='linux' and os.geteuid()==0,'wspr5 root required')
    os.umask(0o077);root=args.root.resolve(strict=True)
    fixture=Fixture(root);fixture.verify()
    d=DeviceFixture(root);d.verify_helpers()
    require(d.state['kind']==args.kind and not d.state.get('pending') and
            time.monotonic_ns()+1500_000_000_000<d.state['deadline_monotonic_ns'],
            'A2 lifecycle/time admission')
    require(not args.attempt or re.fullmatch('[a-z0-9-]{1,32}',args.attempt),'Invalid attempt label')
    name='a2-'+args.kind+('-'+args.attempt if args.attempt else '')
    result=dict(case=name,status='RUNNING',intervals={})
    deadline=time.monotonic()+1450
    extra=['--attempt',args.attempt] if args.attempt else []
    decoder=root/'pi/phase115_tls_observer_test.py'
    if args.workload_manifest:
        extra+=['--workload-manifest',str(args.workload_manifest)]
        amendment=json.loads(args.workload_manifest.read_text())
        decoder=Path(amendment['production_decoder'])
        result['workload_manifest_sha256']=hashlib.sha256(args.workload_manifest.read_bytes()).hexdigest()
    def run(label,argv,timeout):
        require(time.monotonic()+timeout<deadline,'Family deadline')
        with (root/(label+'.driver.stdout')).open('x') as out, \
             (root/(label+'.driver.stderr')).open('x') as err:
            q=subprocess.run(argv,stdout=out,stderr=err,timeout=timeout)
        require(q.returncode==0,label+' failed; no dependent case or retry')
    def write_result():
        (root/(name+'-family-result.json')).write_text(json.dumps(result,indent=2)+'\n')
    try:
        baseline_name=name+'-admission'
        current=d.check_current(baseline_name)
        require(current['info']['network']['ipv4']=='10.77.15.10' and
                current['info']['network']['ntp_address']=='10.77.15.1','Fixture network not ready')
        packet=dict(case=name,boot=d.state['boot'],source='4058d3a4a95110326006a7db6e37eb4b562a500c',
            clock_hz=current['info']['system_clock_hz'],observer_session_id=secrets.token_hex(16),
            observer_sha256=hashlib.sha256((root/'scripts/phase11_5_idle_observer.py').read_bytes()).hexdigest(),
            intervals=[['quiet-before',360],['controller',180],['nominal',180],['quiet-after',360]],
            rf_jobs=[],family_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        stages=('quiet-before','controller','nominal','quiet-after')
        if args.resume_from:
            old_path=args.resume_from.resolve(strict=True)
            require(old_path.parent==root,'Resume evidence must be in the same lifecycle root')
            old=json.loads(old_path.read_text());old_name=old['case']
            require(re.fullmatch('a2-'+args.kind+'-[a-z0-9-]{1,32}',old_name),'Invalid previous case')
            stages=resume_stages(old)
            old_packet=json.loads((root/(old_name+'-packet.json')).read_text())
            require(all(old_packet[k]==packet[k] for k in ('boot','source','clock_hz','observer_sha256')),
                    'Previous observer or firmware identity changed')
            packet['observer_session_id']=old_packet['observer_session_id']
            warm=old['current_interval']=='quiet-after'
            quiet='quiet-after' if warm else 'quiet-before'
            q=audit_idle(root/(old_name+'-'+quiet+'.jsonl'),
                         root/(old_name+('-quiet-after-admission' if warm else '-admission')+'.stdout'))
            previous=root/(old_name+'-controller')
            require(q==old['intervals'][quiet] and q['boot']==d.state['boot'],
                    'Previous quiet evidence changed')
            if old['current_interval'] in ('nominal','quiet-after'):
                control=dict(usb=audit_idle(previous/'usb-health.jsonl',root/(old_name+'-controller-admission.stdout')),
                             load=audit_load(previous,decoder))
                require(control==old['intervals']['controller'] and control['usb']['boot']==d.state['boot'],
                        'Previous controller evidence changed')
            old_load=json.loads((previous/'load.json').read_text())
            require(args.workload_manifest and old_load['binary']==amendment['production']['production_binary'] and
                    old_load['binary_sha256']==amendment['production']['production_binary_sha256'],
                    'Controller artifact changed; full family required')
            result['intervals']=dict(old['intervals'])
            if warm:
                prior=root/(old_name+'-nominal')
                nominal=dict(usb=audit_idle(prior/'usb-health.jsonl',root/(old_name+'-nominal-admission.stdout')),
                             load=audit_load(prior,decoder))
                require(nominal==old['intervals']['nominal'],'Previous nominal evidence changed')
                result['intervals']={'quiet-before':q,'controller':control}
                result['initial_retained_difference_bytes']=old['quiet_heap_delta_bytes']
                result['quiet_baseline_is_post_load']=True
            result['preserved_failed_attempt']=str(old_path)
            result['preserved_failed_attempt_sha256']=hashlib.sha256(old_path.read_bytes()).hexdigest()
        with (root/(name+'-packet.json')).open('x') as stream:json.dump(packet,stream,indent=2)
        for stage in stages:
            result['current_interval']=stage;write_result()
            if stage.startswith('quiet'):
                label=name+'-'+stage
                if stage=='quiet-after':
                    baseline_name=label+'-admission';d.check_current(baseline_name)
                baseline=root/(baseline_name+'.stdout')
                run(label,['python3',str(root/'scripts/phase11_5_idle_observer.py'),
                    '--baseline',str(baseline),'--output',str(root/(label+'.jsonl')),
                    '--session-id',packet['observer_session_id'],'--seconds','360','--run'],375)
                evidence=audit_idle(root/(label+'.jsonl'),baseline)
            else:
                run(name+'-'+stage,['python3',str(Path(__file__).with_name('phase11_5_a2_load.py')),
                    '--root',str(root),'--kind',args.kind,*extra,*(['--browser'] if stage=='nominal' else []),
                    '--run'],280)
                target=root/(name+'-'+stage)
                evidence=dict(usb=audit_idle(target/'usb-health.jsonl',
                    root/(name+'-'+stage+'-admission.stdout')),
                    load=audit_load(target,decoder))
            result['intervals'][stage]=evidence;write_result()
        result['quiet_heap_delta_bytes']=(result['intervals']['quiet-after']['last_heap_allocated_bytes']-
                                         result['intervals']['quiet-before']['last_heap_allocated_bytes'])
        require(abs(result['quiet_heap_delta_bytes'])<=1024,'Unexplained matched quiet retained heap')
        result['status']='CAPTURED_REQUIRES_FINAL_REVIEW'
    except BaseException as error:
        result['status']='FAILED'
        result['error']=type(error).__name__+': '+str(error)
        raise
    finally:write_result()


if __name__=='__main__':main()
