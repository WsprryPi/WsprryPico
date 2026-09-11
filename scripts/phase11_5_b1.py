#!/usr/bin/env python3
"""Opt-in B1: Q360, three N300 intervals, Q360 on the admitted physical image.

Reuses the independently observed production/browser workload. No RF jobs,
configuration, flash, retry, recovery, or extension of the lifecycle deadline.
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
from phase11_5_network_fixture import Fixture
from phase11_5_inventory import require
from audit_phase11_5_idle import audit as audit_idle
from audit_phase11_5_load import audit as audit_load


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:
        print('Plan only; no files, host or devices accessed.');return
    require(sys.platform=='linux' and os.geteuid()==0,'wspr5 root required')
    os.umask(0o077);root=a.root.resolve(strict=True)
    manifest=json.loads(a.manifest.read_text())
    require(sha(root/'packet.json')==manifest['lifecycle_packet_sha256'],'Lifecycle packet changed')
    for path,expected in manifest['helper_sha256'].items():
        require(sha(Path(path))==expected,'Frozen helper changed')
    for relative,expected in manifest['prerequisite_sha256'].items():
        path=(root/relative).resolve(strict=True)
        require(path.is_relative_to(root) and sha(path)==expected,'Reviewed prerequisite changed')
    require(set(manifest['prerequisite_sha256'])=={
        'a2-physical-browser-priority-family-result.json','a3-physical/audit.json'},
        'Both reviewed physical prerequisites required')
    require(json.loads((root/'a2-physical-browser-priority-family-result.json').read_text())['status']==
            'CAPTURED_REQUIRES_FINAL_REVIEW' and
            json.loads((root/'a3-physical/audit.json').read_text())['status']==
            'CAPTURED_REQUIRES_FINAL_REVIEW','Unfinished physical prerequisite')
    fixture=Fixture(root);fixture.verify()
    d=DeviceFixture(root);d.verify_helpers()
    require(d.state['kind']=='physical' and not d.state.get('pending') and
            time.monotonic_ns()+2100_000_000_000<d.state['deadline_monotonic_ns'],
            'B1 physical lifecycle/time admission')
    a2=json.loads((root/'a2-physical-browser-priority-family-result.json').read_text())
    a3=json.loads((root/'a3-physical/audit.json').read_text())
    require(a2['intervals']['quiet-after']['boot']==a3['usb']['boot']==d.state['boot'],
            'Reviewed prerequisite boot changed')
    result_path=root/'b1-family-result.json'
    require(not result_path.exists(),'Preserved B1 attempt already exists')
    session=secrets.token_hex(16);decoder=Path(manifest['production_decoder'])
    result=dict(case='B1',status='RUNNING',intervals={},rf_jobs=[],
                manifest_sha256=sha(a.manifest),observer_session_id=session)
    deadline=time.monotonic()+2050
    def publish():
        result_path.write_text(json.dumps(result,indent=2)+'\n')
    def run(label,argv,timeout):
        require(time.monotonic()+timeout<deadline,'B1 family deadline')
        with (root/(label+'.driver.stdout')).open('x') as out, \
             (root/(label+'.driver.stderr')).open('x') as err:
            q=subprocess.run(argv,stdout=out,stderr=err,timeout=timeout)
        require(q.returncode==0,label+' failed; no dependent interval')
    try:
        current=d.check_current('b1-admission')
        require(current['info']['system_clock_hz']==138000000 and
                current['info']['revision']=='8fb3894253ef' and
                current['info']['network']['ipv4']=='10.77.15.10','B1 identity')
        result.update(boot=d.state['boot'],source='8fb3894253ef45adc3aad28f25a684168487490f',
                      clock_hz=138000000)
        terminal=current['wtp']['STATUS']['terminal_records']
        for stage in ('quiet-before','repeat-1','repeat-2','repeat-3','quiet-after'):
            result['current_interval']=stage;publish()
            if stage.startswith('quiet'):
                label='b1-'+stage
                c=d.check_current(label+'-admission')
                require(c['wtp']['STATUS']['terminal_records']==terminal,'Unmatched terminal history')
                baseline=root/(label+'-admission.stdout')
                run(label,['python3',str(root/'scripts/phase11_5_idle_observer.py'),
                    '--baseline',str(baseline),'--output',str(root/(label+'.jsonl')),
                    '--session-id',session,'--seconds','360','--run'],375)
                evidence=audit_idle(root/(label+'.jsonl'),baseline)
            else:
                attempt='b1-'+stage;name='a2-physical-'+attempt
                packet=dict(case=name,boot=d.state['boot'],source=result['source'],clock_hz=138000000,
                    observer_session_id=session,observer_sha256=sha(root/'scripts/phase11_5_idle_observer.py'),
                    intervals=[['nominal',300]],rf_jobs=[],family_sha256=sha(Path(__file__)))
                with (root/(name+'-packet.json')).open('x') as out:json.dump(packet,out,indent=2)
                run(name,['python3',str(Path(__file__).with_name('phase11_5_a2_load.py')),
                    '--root',str(root),'--kind','physical','--attempt',attempt,
                    '--browser','--seconds','300','--workload-manifest',str(a.manifest),'--run'],400)
                target=root/(name+'-nominal')
                evidence=dict(usb=audit_idle(target/'usb-health.jsonl',
                    root/(name+'-nominal-admission.stdout')),load=audit_load(target,decoder))
            result['intervals'][stage]=evidence;publish()
        final=d.check_current('b1-final')
        require(final['wtp']['STATUS']['terminal_records']==terminal,'Terminal history changed')
        result['quiet_heap_delta_bytes']=(result['intervals']['quiet-after']['last_heap_allocated_bytes']-
                                         result['intervals']['quiet-before']['last_heap_allocated_bytes'])
        require(abs(result['quiet_heap_delta_bytes'])<=1024,'Unexplained matched quiet retained heap')
        result['status']='CAPTURED_REQUIRES_FINAL_REVIEW'
    except BaseException as error:
        result['status']='FAILED';result['error']=type(error).__name__+': '+str(error)
        raise
    finally:publish()


if __name__=='__main__':main()
