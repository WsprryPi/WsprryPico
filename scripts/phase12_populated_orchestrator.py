#!/usr/bin/env python3
"""B-only four-case populated source5 campaign, with unconditional exact restoration."""
from phase12_final_collection import collect_final
import argparse,hashlib,json,os,signal,time,uuid
from pathlib import Path
from phase12_candidate_manifest import read_json,verify
from phase12_engineering_orchestrator import RemoteAdapters,tranche_deadline
from phase12_independent_orchestrator import recover_only
from phase12_recovery_orchestrator import Backend,Ledger,private_write,sha,require,safe_info,assess,DEVICE,E10
from phase12_populated_fixture import build
from phase12_recovery_device import strict,SERIAL,CONSOLE
from phase12_composition_audit import counter
from phase12_fixture_roles import role_map,load_roles


CASES = ('station', 'network', 'provisioning', 'full')

def selected_cases(value=None):
    cases = CASES if value is None else tuple(value.split(',')) if isinstance(value, str) else tuple(value)
    require(bool(cases) and len(set(cases)) == len(cases) and all(case in CASES for case in cases),
            'ordered unique populated cases required')
    require(tuple(case for case in CASES if case in cases) == cases, 'populated case order required')
    return cases


def observe_seed_association(backend,remote,root,manifest,deployed,bounded,deadline,*,clock=time.monotonic,sleeper=time.sleep,target_proof=False,generation=None):
    """Retain actual decoded observations and observer/target bindings on every poll."""
    bindings=dict(ssh_host='wspr5',remote_root=backend.remote,helper=backend.remote+'/phase12_recovery_device.py',
        device_id=DEVICE,serial=SERIAL,console=CONSOLE,source_commit=manifest['source_commit'],
        expected_boot_id=deployed['info']['status']['boot_id'],
        helper_request=dict(action='info',allow_fault=True),
        selected_image_sha256=next((c['uf2']['sha256'] for c in manifest.get('candidates',[]) if c['role']=='restore'),None))
    index=0
    try:
        remote.fixture('inspect_ap',dict(phase='start'))
        while True:
            bounded();require(clock()<deadline,'owned station association deadline');index+=1
            require(index<=321,'finite seed association observations')
            try:info=backend.info()
            except Exception as observation_error:
                private_write(root/('seed-association-info-error-%03d.json'%index),dict(bindings=bindings,
                    error_type=type(observation_error).__name__,error_message=str(observation_error),observation=index))
                raise
            private_write(root/('seed-association-info-%03d.json'%index),dict(bindings=bindings,actual_decoded_info=info,
                host_elapsed_clock_s=clock(),observation=index))
            require(clock()<deadline,'owned station association deadline')
            safe_info(info,manifest['source_commit'][:12],0,False)
            require(info['status']['boot_id']==bindings['expected_boot_id'] and
                    info['status']['clock_state']=='unsynchronized','same offline seed boot')
            if info['network']['link_status']==3:
                require(info['network']['ipv4'].startswith('192.168.84.'),'owned station carrier')
                if target_proof:
                    proof=remote.fixture('prove_target',dict(phase='seed',source_commit=manifest['source_commit'],boot_id=bindings['expected_boot_id'],generation=generation,remaining_s=min(160,deadline-clock())))
                    private_write(root/'seed-target-association-receipt.json',proof);require(proof['status']=='TARGET_ASSOCIATION_VERIFIED' and proof['station_ipv4']==info['network']['ipv4'],'same target AP station proof')
                remote.fixture('inspect_ap',dict(phase='success'))
                require(clock()<deadline,'owned station association deadline')
                return info
            require(clock()<deadline,'owned station association deadline')
            sleeper(.5)
    except Exception:
        try:remote.fixture('inspect_ap',dict(phase='failure'))
        except Exception as diagnostic_error:
            private_write(root/'seed-association-inspection-error.json',dict(error_type=type(diagnostic_error).__name__))
        raise


def assess_save(before,after,before_bytes,after_bytes,rows,station,network,save_cases=('station','network')):
    require(before_bytes[:0x3f7000]==after_bytes[:0x3f7000] and before_bytes[0x3fb000:]==after_bytes[0x3fb000:],
            'save changed unrelated application/access/BLE/operational/E10')
    old=strict(before['profile_payload']);new=strict(after['profile_payload'])
    require(len(old['clients'])==2 and new['tls']==old['tls'] and new['clients']==old['clients'],'populated trust changed')
    require(new['owners']==old['owners'] and new['owner_epoch']==old['owner_epoch'],'owner authority changed')
    require(new['station']==station and new['network']==network,'exact saved station/network')
    require(new['request_sha256']==rows[-1]['request_digest'] and after['profile_sequence']==before['profile_sequence']+len(save_cases),
            'exact durable request/generation')
    require(len(rows)==len(save_cases) and all(row['submit_attempts']==1 and
            row['generation']==before['profile_sequence']+index+1 for index,row in enumerate(rows)) and
            all(row['application_response_discarded'] is True for kind,row in zip(save_cases,rows) if kind=='network') and
            (len(rows)<2 or rows[0]['boot_id']!=rows[1]['boot_id']), 'selected one-use freshboot saves')
    require(after['config']==before['config'] and after['watermark']==before['watermark'],'operational state changed')
    return dict(result='PASS',cases=len(save_cases),scope='populated trust, offline station/network commit, application-discarded response, cold durable selection')


def run_saves(backend,remote,root,manifest,seed,seed_path,station,bounded,ledger,save_cases=('station','network')):
    roles=load_roles(root)
    save_rows=[]
    for kind in save_cases:
        bounded();info=backend.info()
        result=remote.invoke('phase12_populated_dispatch.py',dict(root=backend.remote,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',
            roles_sha256=roles['sha256'],source_commit=manifest['source_commit'],manifest_sha256=sha(root/'manifest.json'),network_sha256=sha(root/'populated-network.json'),
            boot_id=info['status']['boot_id'],generation=seed['inspection']['profile_sequence']+len(save_rows),suffix=info['local_suffix'],station=station,case=kind),timeout=340,keepalive=True)
        require(result['status']=='POPULATED_SAVES_REVIEW_REQUIRED' and len(result['cases'])==1,'one completed save')
        remote.collect(('populated-'+kind+'-wire.jsonl','populated-'+kind+'-result.json'))
        require((root/('populated-'+kind+'-result.json')).is_file(),'save evidence retrieval')
        observed=backend.snapshot('after-'+kind+'-save.bin');inspection=observed['inspection'];profile=strict(inspection['profile_payload']);old=strict(seed['inspection']['profile_payload'])
        require(profile['tls']==old['tls'] and profile['clients']==old['clients'] and profile['station']==station and
            profile['request_sha256']==result['cases'][0]['request_digest'] and inspection['profile_sequence']==seed['inspection']['profile_sequence']+len(save_rows)+1,
            'each exact trust/station/durable tuple')
        require(seed_path.read_bytes()[:0x3f7000]==(root/observed['path']).read_bytes()[:0x3f7000] and
            seed_path.read_bytes()[0x3fb000:]==(root/observed['path']).read_bytes()[0x3fb000:],'each unrelated region unchanged')
        save_rows.extend(result['cases'])
        if kind=='station' and 'network' in save_cases:
            # Full-flash snapshot deliberately leaves B in ROM. Redeploy the
            # ordinary candidate against the freshly retained selected settings;
            # this diagnostic reboot is separate from the one save activation.
            deployed=backend.deploy('restore',observed,'after-station-readback-redeployment.bin')
            selected=safe_info(deployed['info'],manifest['source_commit'][:12],0,False)
            require(counter(selected['provisioning_generation'],'redeployed generation')==inspection['profile_sequence'] and
                selected['provisioning_source']=='consumer_preclock','station readback redeployment selection')
            fresh=safe_info(backend.info(),manifest['source_commit'][:12],0,False)
            require(fresh['status']['boot_id']==selected['status']['boot_id'] and
                counter(fresh['provisioning_generation'],'fresh generation')==inspection['profile_sequence'],
                'independent ordinary post-readback observation')
            ledger.record('diagnostic_readback_redeployment',generation=inspection['profile_sequence'],
                activation_boot_id=result['cases'][0]['boot_id'],diagnostic_boot_id=fresh['status']['boot_id'])
    return observed,save_rows


def execute(manifest,artifacts,root,inspector,native,*,backend_factory=Backend,remote_factory=RemoteAdapters,builder=build,clock=time.monotonic,sleeper=time.sleep,cases=None,fixture_roles='engineering',ap_proof='beacon'):
    identity=uuid.uuid4().hex;roles=role_map(fixture_roles,identity);require(ap_proof in ('beacon','target'),'finite AP proof mode')
    cases=selected_cases(cases);save_cases=tuple(case for case in cases if case in ('station','network'))
    root=Path(root);require(not root.exists(),'new campaign required');root.mkdir(mode=0o700,parents=True)
    start=clock();backend=backend_factory(dict(campaign_id=identity,interface='wlan2'),manifest,artifacts,root,inspector)
    remote=remote_factory(root);remote.backend=backend;ledger=Ledger(root/'ledger.jsonl');baseline=None;primary=None;restoration=None;fixture=False;helper_staged=False
    binding=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    private_write(root/'campaign-config.json',dict(campaign_id=identity,manifest_sha256=binding,source_commit=manifest['source_commit'],rf_jobs=0,max_cases=len(cases),selected_cases=cases,max_seconds=1200,fixture_roles=roles,ap_proof=ap_proof))
    saved=root/'observer-phase12_populated_orchestrator.py';saved.write_bytes(Path(__file__).read_bytes());os.chmod(saved,0o600)
    ledger.record('campaign_start',authority='USER_AUTHORIZED_UNATTENDED_PHASE12',runner_sha256=sha(saved),selected_cases=cases,rf_jobs=0)
    def bounded():require(clock()-start<1200,'whole populated campaign deadline')
    cleanup_failures=[]
    def record_cleanup_failure(event,error):
        failure=dict(event=event,error_type=type(error).__name__)
        cleanup_failures.append(failure)
        try:ledger.record(event,error_type=type(error).__name__)
        except BaseException as recording_error:
            failure['ledger_error_type']=type(recording_error).__name__

    try:
        with tranche_deadline(1200):
            bounded();info=backend.setup();safe_info(info,manifest['source_commit'][:12],0,False)
            baseline=backend.snapshot('baseline.bin');private_write(root/'baseline-receipt.json',dict(path='baseline.bin',sha256=baseline['sha256'],manifest_sha256=binding))
            backend.restore(baseline,'restoration-preflight.bin');backend.stable_restore(baseline,'preflight-info.json')
            private_write(root/'manifest.json',manifest)
            network_file=None
            if save_cases:
                names=('phase12_candidate_manifest.py','phase12_populated_dispatch.py','phase12_consumer_negative_dispatch.py','phase12_consumer_negative.py',
                    'phase12_consumer_composition.py','phase12_engineering_network_dispatch.py','phase12_engineering_network.py',
                    'phase12_engineering_setup.py','phase12_fixture_roles.py','phase12_virtual_observer.py','phase12_engineering_fixture.py','phase12_engineering_composition.py',
                    'phase12_composition_audit.py','phase12_composition_capture.py','phase12_serial_observer.py','phase12_recovery_device.py','check_standalone_image.py',
                    'inhibited_network_acceptance.py','rf_wtp.py','wtp_monitor.py','validate_wtp_contract.py','check_usb_target.py',
                    'standalone_console.py','wsprrypico_ble.py')
                inputs={name:remote.stage(Path(__file__).parent/name,name) for name in names};inputs['manifest.json']=remote.stage(root/'manifest.json','manifest.json')
                private_write(root/'fixture-roles.json',roles);inputs['fixture-roles.json']=remote.stage(root/'fixture-roles.json','fixture-roles.json')
                network=dict(ssid='p12-'+uuid.uuid4().hex[:12],password=uuid.uuid4().hex,time_server='192.168.84.1')
                private_write(root/'populated-network.json',network);inputs['populated-network.json']=remote.stage(root/'populated-network.json','populated-network.json')
                private_write(root/'observer-inputs.json',inputs);helper_staged=True
                network_file=root/'populated-network.json'
            receipt=builder(root/'baseline.bin',root/'fixture',Path(inspector),Path(native),network_file=network_file)
            private_write(root/'fixture-receipt.json',receipt)
            path=root/'fixture/populated.bin';require(sha(path)==receipt['fixture_sha256'],'native fixture binding')
            remote.stage(path,'populated.bin');seed=dict(path='populated.bin',sha256=sha(path),inspection=backend.inspect(path))
            s=seed['inspection'];require(s['profile_source']==5 and s['access_sequence']==baseline['inspection']['access_sequence'] and
                s['bond_count']==0 and len(strict(s['profile_payload'])['clients'])==2 and s['config']['enabled'] is False and len(s['config']['schedules'])==2 and s['watermark']>0,'populated seed inactive requirements')
            if save_cases:
                fixture=True;private_write(root/'fixture-start-ap.json',remote.fixture('start_ap',dict(interface=roles['host_ap'],proof_mode=ap_proof,**network)));remote.fixture('sntp_off',{})
                deployed=backend.restore(seed,'seed-deployment.bin');info=deployed['info'];safe_info(info,manifest['source_commit'][:12],0,False)
                # Establish actual consumer station association before removing only
                # this campaign's private AP. Consumer source5 cannot mutate via USB.
                link_end=min(start+1200,clock()+160)
                info=observe_seed_association(backend,remote,root,manifest,deployed,bounded,link_end,clock=clock,sleeper=sleeper,target_proof=ap_proof=='target',generation=s['profile_sequence'])
                remote.fixture('stop',dict(preserve_disabled_ntp=True));fixture=False
                ledger.record('owned_station_ap_removed',rf_jobs=0)
                # Each dispatch independently waits for actual loss/fallback association,
                # including the diagnostic redeployment between station/network saves.
                station=dict(s['effective_station']);station['power_dbm']=(27 if station['power_dbm']!=27 else 30) if 'station' in save_cases else station['power_dbm']
                observed,save_rows=run_saves(backend,remote,root,manifest,seed,path,station,bounded,ledger,save_cases)
                after=observed;expected=dict(network,time_server='192.168.84.254') if 'network' in save_cases else strict(s['profile_payload'])['network']
                evaluation=assess_save(s,after['inspection'],path.read_bytes(),(root/after['path']).read_bytes(),save_rows,station,expected,save_cases)
                ledger.record('populated_saves_pass',assessment=evaluation)
            for level in (case for case in cases if case in ('provisioning','full')):
                bounded();case=dict(id='populated-'+level+'-1',kind='reset',level=level,stage=1)
                backend.restore(seed,case['id']+'.seed-restored.bin');before=backend.snapshot(case['id']+'.before.bin')
                require((root/before['path']).read_bytes()[0x3f3000:]==path.read_bytes()[0x3f3000:],'freshseed reserved restore')
                candidate=next(c for c in manifest['candidates'] if c['role']=='fault_1')
                bindings=dict(device_id=DEVICE,serial=SERIAL,console=CONSOLE,source_commit=manifest['source_commit'],
                    revision=manifest['source_commit'][:12],fault_stage=1,image_sha256=candidate['uf2']['sha256'],
                    input_readback_sha256=before['sha256'],remote_root=backend.remote)
                deployed=backend.deploy('fault_1',before,case['id']+'.deployment.bin')
                deployment_path=root/(case['id']+'.deployment-receipt.json')
                private_write(deployment_path,dict(bindings=bindings,actual_deployment=deployed))
                safe_info(deployed['info'],manifest['source_commit'][:12],1,False)
                boot=deployed['info']['status']['boot_id'];bindings['old_boot_id']=boot
                prepared=backend.prepare(case,s['effective_station']);private_write(root/(case['id']+'.prepared.json'),prepared)
                ledger.record('mutation_attempt',case['id'],prepared_sha256=prepared['sha256']);backend.submit(prepared);end=clock()+150;observation=0
                while True:
                    bounded();require(clock()<end,'reset watchdog deadline')
                    observation+=1
                    observation_path=root/(case['id']+'.reset-info-%03d.json'%observation)
                    try:observed=backend.info()
                    except Exception as error:
                        private_write(observation_path,dict(bindings=bindings,observation=observation,
                            host_elapsed_clock_s=clock(),error_type=type(error).__name__,error_message=str(error)))
                        if not isinstance(error,(OSError,TimeoutError)):raise
                        sleeper(.5);continue
                    private_write(observation_path,dict(bindings=bindings,observation=observation,
                        host_elapsed_clock_s=clock(),actual_decoded_info=observed))
                    require(observed['device_id']==DEVICE and observed['revision']==manifest['source_commit'][:12],'reset identity')
                    if observed.get('phase12_fault_consumed') is True:
                        safe_info(observed,manifest['source_commit'][:12],1,True);require(observed['status']['boot_id']!=boot,'actual watchdog freshboot');break
                    sleeper(.5)
                after=backend.snapshot(case['id']+'.after.bin');evaluation=assess(case,before['inspection'],after['inspection'],(root/before['path']).read_bytes(),(root/after['path']).read_bytes(),prepared)
                ledger.record('populated_reset_pass',case['id'],assessment=evaluation,
                    source_commit=manifest['source_commit'],image_sha256=bindings['image_sha256'],
                    before_readback_sha256=before['sha256'],deployment_readback_sha256=deployed['readback']['sha256'],
                    after_readback_sha256=after['sha256'],deployment_receipt_sha256=sha(deployment_path),
                    consumed_info_path=observation_path.name,consumed_info_sha256=sha(observation_path),
                    old_boot_id=boot,fresh_boot_id=observed['status']['boot_id'])
    except BaseException as error:primary=dict(type=type(error).__name__,message=str(error));ledger.record('campaign_failed',error=primary)
    finally:
        if helper_staged:
            try:remote.collect(tuple('populated-'+kind+'-'+tail for kind in save_cases for tail in ('wire.jsonl','result.json'))+
                ('ntp-startup-failure.json','ntp-server.log','fixture-management-before.json','ntp-ready.json','ntp-pid.json','ntp-stopped.json',
                 'ntp-preserved.json','fixture-ap-proof.json','target-ap-proof-seed.json','target-ap-proof-station.json','target-ap-proof-network.json','virtual-observer-owned.json','fixture-roles-bound.json','ntp-pid.json','ntp-ready.json','fixture-radio-preflight.json','owned-ap-beacon-readiness.json','populated-seed-start-ap-inspection.json',
                 'populated-seed-failure-ap-inspection.json','populated-seed-success-ap-inspection.json'))
            except BaseException as error:
                primary=primary or dict(type=type(error).__name__,message='private collection failed')
                record_cleanup_failure('evidence_collection_failed',error)
            try:remote.invoke('phase12_populated_dispatch.py',dict(root=backend.remote,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action='cleanup'),timeout=40)
            except BaseException as error:
                primary=primary or dict(type=type(error).__name__,message='observer cleanup failed')
                record_cleanup_failure('observer_cleanup_failed',error)
        if fixture or helper_staged:
            finish_succeeded=False
            try:
                remote.fixture('finish',{});finish_succeeded=True
            except BaseException as error:
                primary=primary or dict(type=type(error).__name__,message='fixture cleanup failed')
                record_cleanup_failure('fixture_cleanup_failed',error)
            try:collect_final(remote,('virtual-observer-owned.json','ntp-stopped.json','ntp-metrics.json','ntp-server.log','fixture-management-before.json','fixture-management-after.json'),required=('fixture-management-after.json',) if finish_succeeded else ())
            except BaseException as error:
                primary=primary or dict(type=type(error).__name__,message='final fixture evidence collection failed')
                record_cleanup_failure('final_collection_failed',error)
        if baseline:
            try:
                restoration=backend.restore(baseline,'final-restoration.bin');restoration['stability']=backend.stable_restore(baseline)
                ledger.record('final_restoration_pass',readback=restoration['readback'])
            except BaseException as error:
                restoration=dict(error=type(error).__name__,message=str(error))
                record_cleanup_failure('final_restoration_failed',error)
        try:backend.cleanup()
        except BaseException as error:
            primary=primary or dict(type=type(error).__name__,message='host cleanup failed')
            record_cleanup_failure('host_cleanup_failed',error)
    if clock()-start>=1200 and primary is None:
        primary=dict(type='TimeoutError',message='whole campaign exceeded twenty minutes; restoration retained')
    result=dict(fixture_roles=roles,status='POPULATED_COMPLETE_REVIEW_REQUIRED' if primary is None and restoration and 'error' not in restoration else 'STOPPED',
        error=primary,cleanup_failures=cleanup_failures,restoration=restoration,rf_jobs=0,physical_acceptance=False,selected_cases=cases,remote_root=backend.remote,seconds=clock()-start)
    private_write(root/'result.json',result);return result


def recover_populated(manifest,artifacts,root,inspector,*,restore=recover_only,remote_factory=RemoteAdapters):
    """Always remove the retained owned fixture, even if restoration fails."""
    from types import SimpleNamespace
    root=Path(root);retained=read_json(root/'campaign-config.json')
    import re
    require(re.fullmatch('[0-9a-f]{32}',retained['campaign_id']) is not None,'retained campaign identity')
    binding=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(retained['manifest_sha256']==binding and retained['source_commit']==manifest['source_commit'],'retained recovery manifest')
    remote=remote_factory(root);remote.backend=SimpleNamespace(remote='/home/pi/phase12-recovery-'+retained['campaign_id'])
    cases=selected_cases(retained.get('selected_cases'))
    try:return restore(manifest,artifacts,root,inspector)
    finally:
        if any(case in ('station','network') for case in cases):
            try:remote.invoke('phase12_populated_dispatch.py',dict(root=remote.backend.remote,
                authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action='cleanup'),timeout=40)
            finally:remote.fixture('finish',{})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('manifest','artifact-root','campaign','inspector','native'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--ap-proof',choices=('beacon','target'),default='beacon');p.add_argument('--fixture-roles',choices=('engineering','swapped','concurrent'),default='engineering');p.add_argument('--cases',help='Ordered unique subset: station,network,provisioning,full');p.add_argument('--run',action='store_true');p.add_argument('--recover-only',action='store_true');a=p.parse_args()
    cases=selected_cases(a.cases);manifest=read_json(a.manifest);verify(manifest,a.artifact_root)
    if not a.run:print(json.dumps(dict(status='VALIDATED_NO_HARDWARE',cases=len(cases),selected_cases=cases,rf_jobs=0,max_seconds=1200,fixture_roles=role_map(a.fixture_roles,uuid.uuid4().hex))));return
    os.umask(0o077);signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt('parent interrupted')))
    if a.recover_only:print(json.dumps(recover_populated(manifest,a.artifact_root,a.campaign,a.inspector)));return
    result=execute(manifest,a.artifact_root,a.campaign,a.inspector,a.native,cases=cases,fixture_roles=a.fixture_roles,ap_proof=a.ap_proof);print(json.dumps(dict(status=result['status'],restored=bool(result['restoration'] and 'error' not in result['restoration']))))
    if result['status']=='STOPPED':raise SystemExit(1)
if __name__=='__main__':main()
