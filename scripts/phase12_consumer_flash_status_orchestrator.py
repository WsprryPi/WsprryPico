#!/usr/bin/env python3
"""B-only one consumer station-save trace; unconditional original standard restore."""
from phase12_final_collection import collect_final
import argparse,hashlib,json,os,signal,time,uuid,subprocess
from pathlib import Path
from phase12_recovery_orchestrator import Backend,Ledger,private_write,sha,safe_info,require,DEVICE
from phase12_engineering_orchestrator import RemoteAdapters,tranche_deadline
from phase12_candidate_manifest import read_json,verify
from phase12_populated_fixture import build
from phase12_composition_audit import counter
from phase12_fixture_roles import role_map


STAGED_HELPERS = (
    'check_standalone_image.py',
    'check_usb_target.py',
    'inhibited_network_acceptance.py',
    'phase12_authority_capture.py',
    'phase12_candidate_manifest.py',
    'phase12_composition_audit.py',
    'phase12_composition_capture.py',
    'phase12_consumer_composition.py',
    'phase12_consumer_dispatch.py',
    'phase12_consumer_flash_status.py',
    'phase12_consumer_busy_claim.py',
    'phase12_consumer_flash_status_dispatch.py',
    'phase12_consumer_negative.py',
    'phase12_consumer_negative_dispatch.py',
    'phase12_engineering_composition.py',
    'phase12_engineering_dispatch.py',
    'phase12_engineering_fixture.py',
    'phase12_fixture_roles.py','phase12_virtual_observer.py',
    'phase12_engineering_flash_status.py',
    'phase12_engineering_flash_status_dispatch.py',
    'phase12_engineering_network.py',
    'phase12_engineering_network_dispatch.py',
    'phase12_engineering_setup.py',
    'phase12_engineering_time.py',
    'phase12_populated_dispatch.py',
    'phase12_recovery_device.py',
    'phase12_recovery_orchestrator.py',
    'phase12_serial_observer.py',
    'rf_wtp.py',
    'standalone_console.py',
    'validate_wtp_contract.py',
    'wsprrypico_ble.py',
    'wtp_monitor.py',
)


def reserved_equal(actual,seed,*,profile_mutation=False):
    require(len(actual)==len(seed)==0x400000,'exact full flash readback')
    if profile_mutation:
        return actual[0x3f3000:0x3f7000]==seed[0x3f3000:0x3f7000] and actual[0x3fb000:]==seed[0x3fb000:]
    return actual[0x3f3000:]==seed[0x3f3000:]


def execute(standard,standard_artifacts,exercise,exercise_artifacts,root,inspector,native,*,backend_factory=Backend,remote_factory=RemoteAdapters,builder=build,clock=time.monotonic,sleeper=time.sleep,fixture_roles='engineering',ap_proof='beacon',station_up_after_beacon=False):
    identity=uuid.uuid4().hex;roles=role_map(fixture_roles,identity);require(ap_proof in ('beacon','target'),'finite AP proof mode')
    root=Path(root);require(not root.exists(),'new campaign');root.mkdir(mode=0o700,parents=True);started=clock();end=started+1200
    backend=backend_factory(dict(campaign_id=identity,interface='wlan2'),standard,standard_artifacts,root,inspector);remote=remote_factory(root);remote.backend=backend;ledger=Ledger(root/'ledger.jsonl');baseline=None;primary=None;restoration=None;fixture=False;staged=False
    require(type(station_up_after_beacon) is bool,'explicit station-return ordering')
    binding=hashlib.sha256(json.dumps(standard,sort_keys=True,separators=(',',':')).encode()).hexdigest();private_write(root/'campaign-config.json',dict(campaign_id=identity,manifest_sha256=binding,source_commit=standard['source_commit'],exercise_source=exercise['source_commit'],max_seconds=1200,simulator_jobs=3,diagnostic_redeployments=4,valid_saves=1,rf_jobs=0,fixture_roles=roles,ap_proof=ap_proof,station_up_after_beacon=station_up_after_beacon,offline_HTTP_qualified=False))
    observer=root/'observer-phase12_consumer_flash_status_orchestrator.py';observer.write_bytes(Path(__file__).read_bytes());observer.chmod(0o600);ledger.record('campaign_start',runner_sha256=sha(observer),rf_jobs=0)
    def bounded():require(clock()<end,'whole1200s case deadline')
    cleanup_failures=[]
    def record_cleanup_failure(event,error):
        failure=dict(event=event,error_type=type(error).__name__)
        cleanup_failures.append(failure)
        try:ledger.record(event,error_type=type(error).__name__)
        except BaseException as recording_error:
            failure['ledger_error_type']=type(recording_error).__name__

    try:
        with tranche_deadline(1200):
            bounded();safe_info(backend.setup(),standard['source_commit'][:12],0,False);baseline=backend.snapshot('baseline.bin');private_write(root/'baseline-receipt.json',dict(path='baseline.bin',sha256=baseline['sha256'],manifest_sha256=binding));backend.restore(baseline,'preflight.bin');backend.stable_restore(baseline,'preflight-info.json')
            private_write(root/'manifest.json',exercise)
            inputs={name:remote.stage(Path(__file__).parent/name,name) for name in STAGED_HELPERS};inputs['manifest.json']=remote.stage(root/'manifest.json','manifest.json');private_write(root/'fixture-roles.json',roles);inputs['fixture-roles.json']=remote.stage(root/'fixture-roles.json','fixture-roles.json');private_write(root/'observer-inputs.json',inputs);staged=True
            candidate=next(c for c in exercise['candidates'] if c['role']=='restore');require(candidate['target']=='WsprryPico' and candidate['fault_stage']==0 and candidate['gp14'] is False and candidate['lan_mode']=='plain' and candidate['session_deadline_fixture'] is False,'ordinary inhibited exercise')
            remote.stage(Path(exercise_artifacts)/candidate['uf2']['path'],'consumer_trace.uf2');backend.roles['consumer_trace']=candidate
            network=dict(ssid='p12-'+uuid.uuid4().hex[:12],password=uuid.uuid4().hex,time_server='192.168.84.1');private_write(root/'populated-network.json',network);remote.stage(root/'populated-network.json','populated-network.json')
            bounded();receipt=builder(root/'baseline.bin',root/'fixture',inspector,native,network_file=root/'populated-network.json');populated=root/'fixture/populated.bin'
            seedbytes=populated.read_bytes();remote.stage(populated,'populated.bin');seed=dict(path='populated.bin',sha256=sha(populated),inspection=backend.inspect(populated));s=seed['inspection'];profile=json.loads(s['profile_payload']);require(len(profile['clients'])==2 and not s['config']['enabled'] and s['watermark']>0,'populated inactive seed')
            fixture=True;private_write(root/'fixture-start-ap.json',remote.fixture('start_ap',dict(interface=roles['host_ap'],proof_mode=ap_proof,**network)));remote.fixture('sntp_off',{})
            deployed=backend.deploy('consumer_trace',seed,'trace-seed-deployment.bin',restore=True);boot=deployed['info']['status']['boot_id'];linkend=min(end,clock()+180);joinend=min(linkend,clock()+160);target_proved=False
            while True:
                bounded();info=safe_info(backend.info(),exercise['source_commit'][:12],0,False);require(info['status']['boot_id']==boot,'same exercise boot')
                if info['network']['link_status']==3:
                    require(info['network']['ipv4'].startswith('192.168.84.'),'owned station')
                    if ap_proof=='target' and not target_proved:
                        require(clock()<joinend,'original target join deadline')
                        proof=remote.fixture('prove_target',dict(phase='warm',source_commit=exercise['source_commit'],boot_id=boot,generation=s['profile_sequence'],remaining_s=min(160,joinend-clock())))
                        private_write(root/'warm-target-association-receipt.json',proof);require(clock()<joinend and proof['status']=='TARGET_ASSOCIATION_VERIFIED' and proof['station_ipv4']==info['network']['ipv4'],'same target warm proof');target_proved=True
                    remote.fixture('bind_peer',dict(address=info['network']['ipv4']));remote.fixture('sntp_on',{})
                    if info['lan_wtp_ready'] and info['status']['clock_state']=='synchronized' and counter(info['network']['accepted'],'accepted')>0:
                        private_write(root/'warm-ready-info.json',info)
                        require(clock()<linkend,'late warm readiness INFO');break
                require(clock()<linkend and (ap_proof!='target' or target_proved or clock()<joinend),'station/SNTP readiness');sleeper(.5)
            station_ipv4=info['network']['ipv4']
            # Warm responder stays enabled and bound to the actual B peer. Each
            # diagnostic activation restores exactly the seed, then requesting real station-loss fallback.
            def fallback_ready(deployed,label):
                remote.fixture('station_ap_down',{})
                fallback_end=min(end,clock()+120)
                index=0;down_since=None;previous_ns=None
                while True:
                    bounded();require(clock()<fallback_end,'ordinary fallback readiness deadline')
                    observed=safe_info(backend.info(),exercise['source_commit'][:12],0,False);index+=1
                    private_write(root/(label+'-fallback-info-%03d.json'%index),observed)
                    require(clock()<fallback_end,'late ordinary fallback INFO')
                    require(observed['status']['boot_id']==deployed['info']['status']['boot_id'],'same fallback boot')
                    require(observed['provisioning_source']=='consumer_preclock' and counter(observed['provisioning_generation'],'fallback generation')==counter(deployed['info']['provisioning_generation'],'deployed generation'),'same ordinary fallback profile')
                    now_ns=counter(observed['status']['monotonic_now_ns'],'fallback monotonic')
                    require(previous_ns is None or now_ns>=previous_ns,'fallback monotonic regression');previous_ns=now_ns
                    if observed['network']['link_status']!=3:
                        if down_since is None:down_since=now_ns
                        if now_ns-down_since>=60_000_000_000:
                            private_write(root/(label+'-station-loss-observation.json'),dict(status='STATION_LOSS_60S_OBSERVED_AP_PROOF_PENDING',boot_id=observed['status']['boot_id'],generation=observed['provisioning_generation'],first_down_ns=str(down_since),last_down_ns=str(now_ns)))
                            remaining=fallback_end-clock()
                            require(remaining>0,'remaining fallback proof budget')
                            return dict(initial_join_seconds=min(30,remaining),fallback_monotonic_ns=str(now_ns),initial_target_deadline_ns=str(now_ns+int(remaining*1_000_000_000)))
                    else:down_since=None
                    sleeper(.5)
            busy=[]
            for state in ('loaded','armed','running'):
                bounded();deployed=backend.deploy('consumer_trace',seed,'busy-'+state+'-deployment.bin',restore=True);info=deployed['info'];boot=info['status']['boot_id']
                private_write(root/('busy-'+state+'-deployment-receipt.json'),deployed)
                fallback_binding=fallback_ready(deployed,'busy-'+state)
                request=dict(root=backend.remote,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',roles_sha256=roles['sha256'],manifest_sha256=sha(root/'manifest.json'),source_commit=exercise['source_commit'],boot_id=boot,generation=s['profile_sequence'],suffix=info['local_suffix'],station_ipv4=station_ipv4,busy_state=state,station_up_after_beacon=station_up_after_beacon,**fallback_binding)
                reply=remote.invoke('phase12_consumer_flash_status_dispatch.py',request,timeout=min(100,end-clock()),keepalive=True)
                require(reply['status']=='CONSUMER_BUSY_CLAIM_REVIEW_REQUIRED' and reply['simulator_jobs']==1 and reply['submit_attempts']==0,'one finite busy job, no submit');bounded()
                names=('consumer-busy-'+state+'-wire.jsonl','consumer-busy-'+state+'-result.json');remote.collect(names);busy.append(read_json(root/names[1]))
                after_busy=backend.snapshot('after-busy-'+state+'.bin');bounded();require(reserved_equal((root/after_busy['path']).read_bytes(),seedbytes),'busy case exact reserved seed preservation')
                ledger.record('busy_claim_case_complete',state=state,boot_id=boot,simulator_jobs=1,submit_attempts=0,reserved_preserved=True)
            bounded();deployed=backend.deploy('consumer_trace',seed,'fresh-trace-deployment.bin',restore=True);info=deployed['info'];boot=info['status']['boot_id']
            private_write(root/'fresh-trace-deployment-receipt.json',deployed)
            fallback_binding=fallback_ready(deployed,'trace')
            station=dict(profile['station']);station['power_dbm']=27 if station['power_dbm']!=27 else 30
            expected=dict(profile,station=station,request_sha256='0'*64)
            from phase12_populated_fixture import canonical
            programs=(len(canonical(expected))+255)//256+2
            bounded();result=remote.invoke('phase12_consumer_flash_status_dispatch.py',dict(root=backend.remote,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',roles_sha256=roles['sha256'],manifest_sha256=sha(root/'manifest.json'),source_commit=exercise['source_commit'],boot_id=boot,generation=s['profile_sequence'],suffix=info['local_suffix'],station_ipv4=station_ipv4,station=station,expected_programs=programs,station_up_after_beacon=station_up_after_beacon,**fallback_binding),timeout=min(280,end-clock()),keepalive=True)
            require(result['status']=='CONSUMER_FLASH_STATUS_REVIEW_REQUIRED' and result['status_samples']==20 and result['submit_attempts']==1,'measured20STATUS/onesave');bounded();remote.collect(('consumer-flash-status-wire.jsonl','consumer-flash-status-result.json'));result=read_json(root/'consumer-flash-status-result.json')
            # Wait for production's autonomous reboot; never suppress/retry it.
            rebootend=min(end,clock()+90)
            while True:
                bounded();info=backend.info()
                if info['status']['boot_id']!=boot:
                    safe_info(info,exercise['source_commit'][:12],0,False);require(counter(info['provisioning_generation'],'generation')==s['profile_sequence']+1,'one committed generation');break
                require(clock()<rebootend,'automatic reboot deadline');sleeper(.5)
            after=backend.snapshot('after-consumer-save.bin');bounded();raw=(root/after['path']).read_bytes();selected=json.loads(after['inspection']['profile_payload'])
            require(reserved_equal(raw,seedbytes,profile_mutation=True),'access/bonds/config/cursor/E10 preservation');require(selected['tls']==profile['tls'] and selected['clients']==profile['clients'] and selected['network']==profile['network'] and selected['owners']==profile['owners'] and selected['owner_epoch']==profile['owner_epoch'] and selected['station']==station and selected['request_sha256']==result['request_digest'],'exact one station save trust preservation');require(after['inspection']['profile_sequence']==s['profile_sequence']+1,'cold durable generation');ledger.record('consumer_flash_status_complete',status_samples=20,profile_appends=1,simulator_jobs=3,diagnostic_redeployments=4,reserved_preserved=True,physical_acceptance=False)
    except BaseException as error:primary=dict(type=type(error).__name__,message=str(error));ledger.record('campaign_failed',error=primary)
    finally:
        if staged:
            try:remote.collect(('consumer-flash-status-wire.jsonl','consumer-flash-status-result.json',
                               'fixture-ap-proof.json','target-ap-proof-warm.json','virtual-observer-owned.json','fixture-roles-bound.json','ntp-pid.json','ntp-ready.json','fixture-radio-preflight.json','owned-ap-beacon-readiness.json',*( 'consumer-busy-'+state+suffix for state in ('loaded','armed','running') for suffix in ('-wire.jsonl','-result.json'))))
            except BaseException as error:
                primary=primary or dict(type=type(error).__name__,message='collection failed')
                record_cleanup_failure('evidence_collection_failed',error)
            try:remote.invoke('phase12_populated_dispatch.py',dict(root=backend.remote,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action='cleanup'),timeout=40)
            except BaseException as error:
                primary=primary or dict(type=type(error).__name__,message='observer cleanup failed')
                record_cleanup_failure('observer_cleanup_failed',error)
        if fixture or staged:
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
            try:restoration=backend.restore(baseline,'final-restoration.bin');restoration['stability']=backend.stable_restore(baseline)
            except BaseException as error:
                restoration=dict(error=type(error).__name__)
                record_cleanup_failure('final_restoration_failed',error)
        try:backend.cleanup()
        except BaseException as error:
            primary=primary or dict(type=type(error).__name__,message='host cleanup failed')
            record_cleanup_failure('host_cleanup_failed',error)
    result=dict(fixture_roles=roles,status='CONSUMER_FLASH_STATUS_COMPLETE_REVIEW_REQUIRED' if primary is None and restoration and 'error' not in restoration else 'STOPPED',error=primary,cleanup_failures=cleanup_failures,restoration=restoration,rf_jobs=0,physical_acceptance=False);private_write(root/'result.json',result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','artifact-root','exercise-manifest','exercise-artifact-root','campaign','inspector','native'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--station-up-after-beacon',action='store_true')
    p.add_argument('--ap-proof',choices=('beacon','target'),default='beacon');p.add_argument('--fixture-roles',choices=('engineering','swapped','concurrent'),default='engineering');p.add_argument('--run',action='store_true');a=p.parse_args();standard=read_json(a.manifest);exercise=read_json(a.exercise_manifest);verify(standard,a.artifact_root);verify(exercise,a.exercise_artifact_root)
    if not a.run:print(json.dumps(dict(status='VALIDATED_NO_HARDWARE',status_samples=20,valid_saves=1,rf_jobs=0,fixture_roles=role_map(a.fixture_roles,uuid.uuid4().hex))));raise SystemExit
    os.umask(0o077);signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt('parent stopped')))
    result=execute(standard,a.artifact_root,exercise,a.exercise_artifact_root,a.campaign,a.inspector,a.native,fixture_roles=a.fixture_roles,ap_proof=a.ap_proof,station_up_after_beacon=a.station_up_after_beacon);print(json.dumps(dict(status=result['status'],restored=result['restoration'] is not None and 'error' not in result['restoration'])));raise SystemExit(result['status']=='STOPPED')
