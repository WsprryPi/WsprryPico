#!/usr/bin/env python3
"""B-only ordinary consumer negative tranche with unconditional exact restore."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import time
import uuid
from phase12_candidate_manifest import read_json,verify
from phase12_engineering_orchestrator import RemoteAdapters
from phase12_independent_orchestrator import recover_only
from phase12_recovery_orchestrator import Backend,Ledger,private_write,sha,require,safe_info
from phase12_composition_audit import counter
from phase12_consumer_negative import CASES

STAGED_HELPERS=('phase12_consumer_negative_dispatch.py','phase12_consumer_negative.py','phase12_consumer_composition.py',
    'phase12_candidate_manifest.py','phase12_engineering_setup.py','phase12_engineering_fixture.py','phase12_fixture_roles.py','phase12_composition_audit.py','phase12_composition_capture.py',
    'phase12_serial_observer.py','phase12_recovery_device.py','check_standalone_image.py',
    'inhibited_network_acceptance.py','rf_wtp.py','wtp_monitor.py','validate_wtp_contract.py',
    'check_usb_target.py','standalone_console.py','wsprrypico_ble.py')

def selected_cases(value=None):
    if value is None:return tuple(CASES)
    cases=tuple(value.split(',')) if isinstance(value,str) else tuple(value)
    require(cases and len(set(cases))==len(cases) and all(c in CASES for c in cases), 'known unique negative cases required')
    require(cases==tuple(c for c in CASES if c in cases),'negative cases must preserve contract order')
    return cases


def execute(manifest,artifacts,root,inspector,*,backend_factory=Backend,remote_factory=RemoteAdapters,cases=None):
    cases=selected_cases(cases)
    root=Path(root);require(not root.exists(),'new campaign required');root.mkdir(mode=0o700,parents=True)
    identity=uuid.uuid4().hex;backend=backend_factory(dict(campaign_id=identity,interface='wlan2'),manifest,artifacts,root,inspector)
    remote=remote_factory(root);remote.backend=backend;ledger=Ledger(root/'ledger.jsonl')
    baseline=None;primary=None;restoration=None
    binding=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    private_write(root/'campaign-config.json',dict(campaign_id=identity,source_commit=manifest['source_commit'],manifest_sha256=binding,cases=cases))
    saved=root/'observer-phase12_consumer_negative_orchestrator.py';saved.write_bytes(Path(__file__).read_bytes());os.chmod(saved,0o600)
    ledger.record('campaign_start',authority='USER_AUTHORIZED_UNATTENDED_PHASE12',runner_sha256=sha(saved),rf_jobs=0)
    started=time.monotonic()
    try:
        info=backend.setup();safe_info(info,manifest['source_commit'][:12])
        baseline=backend.snapshot('baseline.bin')
        private_write(root/'baseline-receipt.json',dict(path='baseline.bin',sha256=baseline['sha256'],manifest_sha256=binding))
        backend.restore(baseline,'restoration-preflight.bin');backend.stable_restore(baseline,'preflight-info.json')
        info=backend.info()
        require(info['provisioning_source']=='consumer_preclock','consumer source5')
        private_write(root/'manifest.json',manifest)
        names=STAGED_HELPERS
        inputs={name:remote.stage(Path(__file__).parent/name,name) for name in names}
        inputs['manifest.json']=remote.stage(root/'manifest.json','manifest.json');private_write(root/'observer-inputs.json',inputs)
        for case in cases:
            require(time.monotonic()-started<1800,'whole negative fixture campaign deadline')
            deployed=backend.deploy('fault_8',baseline,'negative-'+case.lower()+'-deployment.bin')
            info=safe_info(deployed['info'],manifest['source_commit'][:12],8,False)
            remaining=1800-(time.monotonic()-started)
            require(remaining>0,'negative fixture deployment exceeded campaign deadline')
            result=remote.invoke('phase12_consumer_negative_dispatch.py',dict(root=backend.remote,
                authority='USER_AUTHORIZED_UNATTENDED_PHASE12',manifest_sha256=sha(root/'manifest.json'),
                source_commit=manifest['source_commit'],boot_id=info['status']['boot_id'],case=case,
                profile_generation=counter(info['provisioning_generation'],'generation'),
                station=baseline['inspection']['effective_station']),timeout=min(170,remaining),keepalive=True)
            require(result['status']=='NEGATIVES_REVIEW_REQUIRED' and result['cases']==1 and
                    result['wtp_owner_verified'] is False and result['wtp_job_identity_verified'] is False,
                    'one completed AP-only negative case')
            require(time.monotonic()-started<1800,'negative case exceeded campaign deadline')
            after=backend.snapshot('negative-'+case.lower()+'-after.bin')
            require(time.monotonic()-started<1800,'negative readback exceeded campaign deadline')
            require((root/baseline['path']).read_bytes()[0x3f3000:]==(root/after['path']).read_bytes()[0x3f3000:],
                    'negative request changed reserved settings/E10')
            ledger.record('negative_fixture_case_complete',case,role='fault_8',reserved_unchanged=True,
                          scope='production AP claim paths',wtp_owner_verified=False,wtp_job_identity_verified=False)
        ledger.record('negative_cases_complete',cases=len(cases),selected_cases=cases,reserved_unchanged=True,physical_acceptance=False)
    except BaseException as error:
        primary=dict(type=type(error).__name__,message=str(error));ledger.record('campaign_failed',error=primary)
    finally:
        try:remote.collect(tuple('negative-'+case.lower()+'-'+tail for case in cases for tail in ('wire.jsonl','result.json')))
        except BaseException as error:primary=primary or dict(type=type(error).__name__,message='private retrieval failed')
        if baseline:
            try:
                restoration=backend.restore(baseline,'final-restoration.bin')
                restoration['stability']=backend.stable_restore(baseline)
                ledger.record('final_restoration_pass',readback=restoration['readback'])
            except BaseException as error:restoration=dict(error=type(error).__name__,message=str(error))
        try:backend.cleanup()
        except BaseException as error:primary=primary or dict(type=type(error).__name__,message='host cleanup failed')
    result=dict(status='NEGATIVES_COMPLETE_REVIEW_REQUIRED' if primary is None and restoration and 'error' not in restoration else 'STOPPED',
                error=primary,restoration=restoration,rf_jobs=0,physical_acceptance=False,remote_root=backend.remote,
                wtp_owner_verified=False,wtp_job_identity_verified=False,full_composition_qualified=False)
    private_write(root/'result.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','artifact-root','campaign','inspector'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--cases',help='Comma-separated ordered subset; default all seven');p.add_argument('--run',action='store_true');p.add_argument('--recover-only',action='store_true');a=p.parse_args()
    manifest=read_json(a.manifest);verify(manifest,a.artifact_root);cases=selected_cases(a.cases)
    if not a.run:print(json.dumps(dict(status='VALIDATED_NO_HARDWARE',cases=len(cases),selected_cases=cases,rf_jobs=0,simulator_jobs=0)));return
    os.umask(0o077)
    def stopped(*_):raise KeyboardInterrupt('parent interrupted')
    signal.signal(signal.SIGTERM,stopped)
    if a.recover_only:print(json.dumps(recover_only(manifest,a.artifact_root,a.campaign,a.inspector)));return
    result=execute(manifest,a.artifact_root,a.campaign,a.inspector,cases=cases)
    print(json.dumps(dict(status=result['status'],restored=bool(result['restoration'] and 'error' not in result['restoration']))))
    if result['status']=='STOPPED':raise SystemExit(1)


if __name__=='__main__':main()
