#!/usr/bin/env python3
"""B-only consumer composition parent with durable backup and automatic restore."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time
import uuid
from phase12_candidate_manifest import read_json, verify
from phase12_recovery_orchestrator import Backend, Ledger, private_write, sha, require, safe_info
from phase12_composition_audit import validate_plan, counter


def transfer(backend,source,name):
    subprocess.run(['scp','-q',str(source),'wspr5:'+backend.remote+'/'+name],check=True,timeout=30)
    digest=subprocess.check_output(['ssh','wspr5','sha256sum',backend.remote+'/'+name],text=True,timeout=10).split()[0]
    require(digest==sha(source),'transferred input hash: '+name)


def shutdown_child(child):
    """Bound every local SSH shutdown step without bypassing target restoration."""
    errors=[]
    if child is None:return errors
    def attempt(operation):
        try:operation();return True
        except BaseException as error:
            errors.append(dict(type=type(error).__name__,message=str(error)));return False
    if child.stdin is not None:attempt(child.stdin.close)
    if attempt(lambda:child.wait(timeout=10)):return errors
    attempt(child.terminate)
    if attempt(lambda:child.wait(timeout=10)):return errors
    attempt(child.kill)
    attempt(lambda:child.wait(timeout=10))
    return errors


def exercise_selection(manifest,artifact_root,exercise_manifest=None,exercise_artifact_root=None):
    require((exercise_manifest is None)==(exercise_artifact_root is None),'paired exercise manifest/artifact root required')
    if exercise_manifest is not None:
        verify(exercise_manifest,exercise_artifact_root)
        selected=exercise_manifest;artifacts=Path(exercise_artifact_root);image_name='exercise.uf2'
    else:selected=manifest;artifacts=Path(artifact_root);image_name='restore.uf2'
    candidate=next(c for c in selected['candidates'] if c['role']=='restore')
    require(candidate['fault_stage']==0 and candidate['session_deadline_fixture'] is False and
        candidate['target']=='WsprryPico' and candidate['lan_mode']=='plain' and candidate['gp14'] is False,
        'ordinary inhibited exercise candidate required')
    require(candidate['revision']==selected['source_commit'][:12],'exercise candidate source binding')
    return selected,artifacts,candidate,image_name


def wait_exercise_ready(backend,baseline,source,*,clock=time.monotonic,sleeper=time.sleep):
    end=clock()+180;stable=0;boot=None
    while clock()<end:
        try:info=safe_info(backend.info(),source[:12],0,False)
        except (OSError,TimeoutError):sleeper(.5);continue
        require(info['provisioning_source']=='consumer_preclock' and
            counter(info['provisioning_generation'],'profile generation')==baseline['inspection']['profile_sequence'] and
            counter(info['access_generation'],'access generation')==baseline['inspection']['access_sequence'],
            'exercise selected exact original reserved generation')
        require(info['saved_consumer_profile']['station']==baseline['inspection']['effective_station'],
            'exercise preserved effective station')
        if boot is None:boot=info['status']['boot_id']
        require(info['status']['boot_id']==boot,'unexpected exercise readiness reboot')
        ready=(info['network']['link_status']==3 and bool(info['network']['ipv4']) and
            info['status']['clock_state']=='synchronized' and info['lan_wtp_mode']=='plain')
        stable=stable+1 if ready else 0
        if stable>=5:return info
        sleeper(2)
    raise TimeoutError('bounded actual exercise consumer network/time readiness')


def execute(manifest,artifact_root,root,inspector,*,exercise_manifest=None,exercise_artifact_root=None):
    require((exercise_manifest is None)==(exercise_artifact_root is None),
        'paired exercise manifest/artifact root required')
    preselected=exercise_selection(manifest,artifact_root,exercise_manifest,exercise_artifact_root) if exercise_manifest is not None else None
    root=Path(root);require(not root.exists(),'new private campaign required')
    root.mkdir(mode=0o700,parents=True)
    plan={'campaign_id':uuid.uuid4().hex,'interface':'wlan2'}
    backend=Backend(plan,manifest,artifact_root,root,inspector)
    ledger=Ledger(root/'ledger.jsonl');baseline=None;child=None;primary=None;restoration=None
    private_write(root/'campaign-config.json',dict(campaign_id=plan['campaign_id'],
        manifest_sha256=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        source_commit=manifest['source_commit']))
    target=root/'observer-phase12_independent_orchestrator.py';target.write_bytes(Path(__file__).read_bytes());os.chmod(target,0o600)
    ledger.record('campaign_start',authority='USER_AUTHORIZED_UNATTENDED_PHASE12',
                  source_commit=manifest['source_commit'],runner_sha256=sha(__file__),rf_jobs=0)
    try:
        # Existing setup's exact B checks and fresh helper/image transfer precede ROM work.
        info=backend.setup()
        require(info['revision']==manifest['source_commit'][:12],'initial exact standard revision')
        baseline=backend.snapshot('baseline.bin')
        private_write(root/'baseline-receipt.json',dict(path='baseline.bin',sha256=baseline['sha256'],
            manifest_sha256=read_json(root/'campaign-config.json')['manifest_sha256']))
        ledger.record('backup_retained',sha256=baseline['sha256'])
        backend.restore(baseline,'restoration-preflight.bin')
        stability=backend.stable_restore(baseline,'preflight-stable-info.json')
        info=backend.info()
        selected,selected_artifacts,candidate,image_name=preselected or exercise_selection(manifest,artifact_root)
        if exercise_manifest is not None:
            transfer(backend,selected_artifacts/candidate['uf2']['path'],'exercise.uf2')
            backend.roles['exercise']=candidate
            deployed=backend.deploy('exercise',baseline,'exercise-deployment-readback.bin')
            safe_info(deployed['info'],selected['source_commit'][:12],0,False)
            info=wait_exercise_ready(backend,baseline,selected['source_commit'])
            ledger.record('exercise_candidate_ready',source_commit=selected['source_commit'],
                image_name=image_name,image_sha256=candidate['uf2']['sha256'],boot_id=info['status']['boot_id'])
        p=read_json(Path(__file__).parents[1]/'docs/development/phase12-composition-consumer-plan-template.json')
        linked=(selected_artifacts/candidate['map']['path']).read_text()
        require('__StackTop = (ORIGIN (SCRATCH_Y) + LENGTH (SCRATCH_Y))' in linked and
                '0x20080000' in linked and '0x20078000' in linked,'retained linked stack bounds')
        p.update(source_commit=selected['source_commit'],image_sha256=candidate['uf2']['sha256'],
                 device_id=info['device_id'],boot_id=info['status']['boot_id'],
                 firmware=info['firmware'],core0_stack_capacity_bytes=32768)
        validate_plan(p);private_write(root/'composition-plan.json',p)
        private_write(root/'manifest.json',selected)
        names=('phase12_consumer_dispatch.py','phase12_consumer_composition.py',
               'phase12_composition_capture.py','phase12_composition_audit.py',
               'phase12_serial_observer.py','phase12_authority_capture.py',
               'phase12_recovery_device.py','phase12_candidate_manifest.py','check_standalone_image.py',
               'inhibited_network_acceptance.py','validate_wtp_contract.py','wtp_monitor.py',
               'check_usb_target.py','rf_wtp.py')
        inputs={}
        for name in names:
            source=Path(__file__).parent/name;transfer(backend,source,name);inputs[name]=sha(source)
            target=root/('observer-'+name);target.write_bytes(source.read_bytes());os.chmod(target,0o600)
        for name in ('composition-plan.json','manifest.json'):transfer(backend,root/name,name)
        private_write(root/'observer-inputs.json',inputs)
        payload=dict(authority='USER_AUTHORIZED_UNATTENDED_PHASE12',root=backend.remote,
                     manifest_sha256=sha(root/'manifest.json'),address=info['network']['ipv4'],image_name=image_name)
        command=shlex.join(['python3',backend.remote+'/phase12_consumer_dispatch.py'])
        with (root/'remote-dispatch.log').open('x') as log:
            os.chmod(log.name,0o600)
            child=subprocess.Popen(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','wspr5',command],
                                   stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
            child.stdin.write(json.dumps(payload).encode()+b'\n');child.stdin.flush()
            ledger.record('consumer_capture_started',boot_id=p['boot_id'],duration_s=7200,
                          max_simulated_jobs=6,heap_return_tolerance_bytes=p['heap_return_tolerance_bytes'])
            code=child.wait(timeout=7380)
            require(code==0,'remote consumer driver/capture stopped')
        for name in ('composition-capture.jsonl','directed-wave-1-wire.jsonl',
                     'directed-wave-2-wire.jsonl','directed-wave-timeline.jsonl','final-authority.json','remote-result.json'):
            target=root/name
            subprocess.run(['scp','-q','wspr5:'+backend.remote+'/'+name,str(target)],check=True,timeout=45)
            os.chmod(target,0o600)
        ledger.record('consumer_capture_complete',capture_sha256=sha(root/'composition-capture.jsonl'),
                      wire_sha256=[sha(root/f'directed-wave-{n}-wire.jsonl') for n in (1,2)],physical_acceptance=False)
    except BaseException as error:
        primary={'type':type(error).__name__,'message':str(error)}
        ledger.record('campaign_failed',error=primary)
    finally:
        shutdown_errors=shutdown_child(child)
        if shutdown_errors:
            primary=primary or dict(type='ChildShutdownFailed',message='bounded child shutdown reported errors')
            ledger.record('child_shutdown_failed',errors=shutdown_errors)
        if baseline:
            try:
                if primary is not None:
                    # Failed child descriptors are closed; expire its longest 60-second lease.
                    for _ in range(13):time.sleep(5)
                restoration=backend.restore(baseline,'final-restoration.bin')
                restoration['stability']=backend.stable_restore(baseline)
                ledger.record('final_restoration_pass',readback=restoration['readback'])
            except BaseException as error:
                restoration={'error':type(error).__name__,'message':str(error)}
                ledger.record('final_restoration_failed',**restoration)
        try:backend.cleanup()
        except Exception as error:
            primary=primary or {'type':'HostCleanupFailed','message':str(error)}
            ledger.record('host_cleanup_failed',error=type(error).__name__)
    result=dict(status='CAPTURE_COMPLETE_REVIEW_REQUIRED' if primary is None and restoration and 'error' not in restoration else 'STOPPED',
                error=primary,restoration=restoration,rf_jobs=0,physical_acceptance=False,
                remote_root=backend.remote)
    private_write(root/'result.json',result)
    return result


def recover_only(manifest,artifact_root,root,inspector):
    root=Path(root);require(root.is_dir() and not root.is_symlink(),'existing private campaign')
    config=read_json(root/'campaign-config.json');receipt=read_json(root/'baseline-receipt.json')
    binding=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(config['source_commit']==manifest['source_commit'] and config['manifest_sha256']==binding and
            receipt['manifest_sha256']==binding,'recovery manifest binding')
    baseline=root/'baseline.bin'
    require(not baseline.is_symlink() and baseline.stat().st_size==4194304 and
            sha(baseline)==receipt['sha256'],'verified recovery backup missing/changed')
    backend=Backend(dict(campaign_id=config['campaign_id'],interface='wlan2'),manifest,artifact_root,root,inspector)
    ledger=Ledger(root/('recovery-'+uuid.uuid4().hex+'.jsonl'))
    name='recovery-'+uuid.uuid4().hex+'.bin'
    backend.acquire()
    try:
        transfer(backend,Path(__file__).parent/'phase12_recovery_device.py','phase12_recovery_device.py')
        transfer(backend,Path(__file__).parent/'check_standalone_image.py','check_standalone_image.py')
        transfer(backend,baseline,name)
        role=next(c for c in manifest['candidates'] if c['role']=='restore')
        transfer(backend,Path(artifact_root)/role['uf2']['path'],'restore.uf2')
        saved=dict(path=name,sha256=receipt['sha256'],inspection=backend.inspect(baseline))
        restored=backend.restore(saved,name+'.readback.bin')
        restored['stability']=backend.stable_restore(saved,name+'.stable-info.json')
        ledger.record('recovery_only_restored',readback=restored['readback'],resumed_cases=0)
        return dict(status='RESTORED_RECOVERY_ONLY',resumed_cases=0)
    finally:
        backend.connection_created=True
        backend.cleanup()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--artifact-root',type=Path,required=True)
    p.add_argument('--exercise-manifest',type=Path);p.add_argument('--exercise-artifact-root',type=Path)
    p.add_argument('--campaign',type=Path,required=True);p.add_argument('--inspector',type=Path,required=True)
    p.add_argument('--run',action='store_true');p.add_argument('--recover-only',action='store_true');a=p.parse_args()
    manifest=read_json(a.manifest);verify(manifest,a.artifact_root)
    require((a.exercise_manifest is None)==(a.exercise_artifact_root is None),'paired exercise options required')
    exercise=read_json(a.exercise_manifest) if a.exercise_manifest and not a.recover_only else None
    if exercise is not None:exercise_selection(manifest,a.artifact_root,exercise,a.exercise_artifact_root)
    if not a.run:print(json.dumps(dict(status='VALIDATED_NO_HARDWARE',duration_s=7200,max_simulated_jobs=6,rf_jobs=0)));return
    os.umask(0o077)
    def interrupted(*_):raise KeyboardInterrupt('parent interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    if a.recover_only:
        print(json.dumps(recover_only(manifest,a.artifact_root,a.campaign,a.inspector)));return
    result=execute(manifest,a.artifact_root,a.campaign,a.inspector,exercise_manifest=exercise,exercise_artifact_root=a.exercise_artifact_root)
    print(json.dumps(dict(status=result['status'],restored=bool(result['restoration'] and 'error' not in result['restoration']))))
    if result['status']=='STOPPED':raise SystemExit(1)


if __name__=='__main__':main()
