#!/usr/bin/env python3
"""Private B engineering preparation parent; restoration is unconditional after backup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import shlex
import subprocess
import time
import uuid
import threading
from contextlib import contextmanager
from phase12_candidate_manifest import read_json, verify
from phase12_recovery_orchestrator import Backend, Ledger, private_write, sha, require, safe_info, assess, local_security_keys
from phase12_independent_orchestrator import transfer, shutdown_child, recover_only
from phase12_recovery_device import DEVICE, CONSOLE
from phase12_composition_audit import counter
from wsprrypico_ble import canonical_profile

from phase12_fixture_roles import role_map
from phase12_flash_preservation import preserve as preserve_flash_reserved

AUTHORITY='USER_AUTHORIZED_UNATTENDED_PHASE12'

# These declarations serve both the offline admission check and the actual
# stage loops. All scopes stage the common inputs before their selected case.
FIXTURE_HELPERS=('phase12_engineering_fixture.py','phase12_fixture_roles.py','wsprrypico_ble.py')
PROVISION_HELPERS=('phase12_engineering_setup.py','wsprrypico_ble.py',
    'phase12_composition_audit.py','phase12_recovery_device.py','standalone_console.py',
    'validate_wtp_contract.py','check_usb_target.py','wtp_monitor.py','rf_wtp.py')
COMMON_HELPERS=('capacity_pending.py','phase12_engineering_dispatch.py','phase12_engineering_time.py',
    'phase12_engineering_composition.py','phase12_engineering_setup.py','phase12_serial_observer.py',
    'phase12_authority_capture.py','phase12_composition_capture.py','phase12_composition_audit.py',
    'phase12_consumer_composition.py','phase12_consumer_dispatch.py','phase12_recovery_orchestrator.py',
    'phase12_candidate_manifest.py','phase12_recovery_device.py','inhibited_network_acceptance.py',
    'check_standalone_image.py','validate_wtp_contract.py','wtp_monitor.py','rf_wtp.py',
    'check_usb_target.py','standalone_console.py','wsprrypico_ble.py')
# (repository input, remote destination, existing dispatch receipt key)
COMMON_REPOSITORY_ASSETS=(
    ('docs/development/phase12-composition-engineering-plan-template.json',
     'engineering-composition-template.json','engineering-composition-template.json'),
    ('docs/protocol/wtp-1.schema.json','docs/protocol/wtp-1.schema.json','schema'))
CREDENTIAL_ASSETS=(('client-ca.crt','ca/server/client-ca.crt'),('owner-client.crt','owner/client.crt'),
    ('owner-client.key','owner/client.key'),('contender-client.crt','contender/client.crt'),
    ('contender-client.key','contender/client.key'))
CONFIGURATION_ASSETS=('ca/server/deployment.json','ca/server/server.crt','ca/server/server.key')
ACCELERATED_HELPERS=('phase12_engineering_time_jobs.py','phase12_engineering_time_dispatch.py',
    'phase12_engineering_session_dispatch.py','phase12_engineering_sessions.py',
    'phase12_engineering_cookie_grace.py','phase12_engineering_network.py',
    'phase12_engineering_network_dispatch.py')
FLASH_STATUS_HELPERS=('phase12_engineering_flash_status.py','phase12_engineering_flash_status_dispatch.py')
JOURNAL_HELPERS=('phase12_engineering_journal.py','phase12_engineering_journal_dispatch.py')
JOURNAL_STIMULI_HELPERS=('phase12_engineering_journal_stimuli.py',)
BOND_REFUSAL_HELPERS=('phase12_engineering_bond_refusal_dispatch.py',
    'phase12_engineering_flash_status_dispatch.py','phase12_engineering_flash_status.py')
SCOPES=('all','composition','application','flash-status','journal','journal-stimuli','time-jobs',
        'time-jobs-invalidation','time-jobs-sntp','network','sessions','bond-revocation')


def journal_outputs(request):
    """Retrieve only originals this invocation could create, within its budget."""
    action=request.get('action');stage=str(request.get('journal_stage',request['stage']))
    if action is None:return ('journal-apply-'+stage+'-wire.jsonl','journal-apply-'+stage+'-result.json')
    if action=='tls':return ('journal-tls-'+stage+'-wire.jsonl','journal-tls-'+stage+'-result.json')
    if action in ('stale_a_ready','stale_prepare'):return ('journal-'+action+'-wire.jsonl',)
    if action=='observe_fault':return ('journal-observe_fault-wire.jsonl','journal-corrupt-result.json')
    if action=='observe_checkpoint':
        return ('journal-stale-new-wire.jsonl',) if request.get('journal_selection')=='stimuli' and request['stage']==0 else ()
    require(action in ('stale_suspend','stale_arm'),'named journal output scope')
    return ()


def accelerated_helpers(scope):
    require(scope in SCOPES,'named engineering scope')
    return ACCELERATED_HELPERS + (('phase12_engineering_time_invalidation.py',)
        if scope=='time-jobs-invalidation' else ())


def staging_inputs(scope, preparation_manifest, credential_root):
    """Return the complete static inputs consumed by the selected CLI campaign.

    Candidate image checks remain in manifest verification. Generated profiles,
    reset requests and per-case fixtures do not exist before the campaign.
    """
    require(scope in SCOPES,'named engineering scope')
    repository=Path(__file__).parents[1];scripts=repository/'scripts'
    helpers=FIXTURE_HELPERS+PROVISION_HELPERS+COMMON_HELPERS
    if scope in ('all','time-jobs','time-jobs-invalidation','time-jobs-sntp','network','sessions'):
        helpers+=accelerated_helpers(scope)
    if scope in ('all','flash-status'):helpers+=FLASH_STATUS_HELPERS
    if scope in ('all','journal','journal-stimuli'):helpers+=JOURNAL_HELPERS+('network_certificates.py',)
    if scope=='journal-stimuli':helpers+=JOURNAL_STIMULI_HELPERS
    if scope in ('all','bond-revocation'):helpers+=BOND_REFUSAL_HELPERS
    paths=[scripts/name for name in helpers]
    paths.extend(repository/source for source,_,_ in COMMON_REPOSITORY_ASSETS)
    paths.append(Path(preparation_manifest))
    paths.extend(Path(credential_root)/source for _,source in CREDENTIAL_ASSETS)
    paths.extend(Path(credential_root)/source for source in CONFIGURATION_ASSETS)
    return tuple(dict.fromkeys(paths))


def preflight_staging(scope, preparation_manifest, credential_root):
    """Fail offline before backend creation, board acquisition or provisioning."""
    for path in staging_inputs(scope,preparation_manifest,credential_root):
        require(path.is_file() and not path.is_symlink(),'regular scope staging input: '+str(path))
        with path.open('rb') as source:
            require(bool(source.read(1)),'nonempty scope staging input: '+str(path))


@contextmanager
def tranche_deadline(seconds=900):
    """Interrupt blocking calls too; restore the process alarm before cleanup.

    The authorized CLI runs on the main thread. Refuse unsupported callers
    before mutation rather than pretending polling bounds blocking transports.
    """
    require(threading.current_thread() is threading.main_thread(), 'tranche timer requires main thread')
    require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), 'existing process timer cannot be replaced')
    previous = signal.getsignal(signal.SIGALRM)
    def expired(*_):
        raise TimeoutError('whole ordinary serialization tranche deadline')
    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def bounded_flash_status(callback):
    def bounded(context):
        with tranche_deadline():
            return callback(context)
    return bounded


def session_selection(scope, stages=None, cookie_only=False):
    require(stages is None or stages=='running','explicit remaining running stage')
    require(not (stages is not None or cookie_only) or scope=='sessions','cookie selection requires sessions scope')
    require(not cookie_only or stages=='running','cookie-only requires explicit running stage')
    return None if stages is None else dict(cookie_grace_stages=['running'],cookie_grace_only=cookie_only)


def session_payload(payload, selection):
    result=dict(payload)
    if selection is not None:result.update(selection)
    return result


def execute(recovery, preparation, artifacts, root, inspector, config, *, backend_factory=Backend,
            fixture=None, provision=None, cases=None, accelerated=None, journal=None, flash_status=None, bond_revocation=None, preparation_artifacts=None, clock=time.monotonic, sleeper=time.sleep, scope='all', session_choice=None, fixture_roles='engineering'):
    require(scope in SCOPES,'named engineering scope')
    if session_choice is not None:
        require(session_choice==session_selection(scope,'running',session_choice.get('cookie_grace_only',False)),'exact session selection')
    require(fixture_roles in ('engineering','swapped') and (fixture_roles=='engineering' or scope=='network'),'swapped roles require network scope')
    roles=role_map(fixture_roles)
    root=Path(root);require(not root.exists(),'new campaign required')
    root.mkdir(mode=0o700,parents=True)
    plan=dict(campaign_id=uuid.uuid4().hex,interface='wlan2')
    backend=backend_factory(plan,recovery,artifacts,root,inspector)
    ledger=Ledger(root/'ledger.jsonl');baseline=None;primary=None;restoration=None;fixture_attempted=False;cases_attempted=False
    original=root/'observer-phase12_engineering_orchestrator.py';original.write_bytes(Path(__file__).read_bytes());os.chmod(original,0o600)
    private_write(root/'observer-inputs.json',dict(runner_sha256=sha(original),recovery=recovery,preparation=preparation))
    binding=hashlib.sha256(json.dumps(recovery,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    private_write(root/'campaign-config.json',dict(campaign_id=plan['campaign_id'],manifest_sha256=binding,
                   source_commit=recovery['source_commit'],preparation_source=preparation['source_commit'],scope=scope,fixture_roles=roles,session_selection=session_choice))
    ledger.record('campaign_start',authority=AUTHORITY,runner_sha256=sha(__file__),rf_jobs=0,scope=scope,fixture_roles=roles,session_selection=session_choice)
    cleanup_failures=[]
    def record_cleanup_failure(event,error):
        failure=dict(event=event,error_type=type(error).__name__)
        cleanup_failures.append(failure)
        try:ledger.record(event,error_type=type(error).__name__)
        except BaseException as recording_error:
            failure['ledger_error_type']=type(recording_error).__name__

    try:
        require(fixture is not None and provision is not None and cases is not None,'all bounded adapters required')
        info=backend.setup();safe_info(info,recovery['source_commit'][:12],0,False)
        baseline=backend.snapshot('baseline.bin')
        private_write(root/'baseline-receipt.json',dict(path='baseline.bin',sha256=baseline['sha256'],manifest_sha256=binding))
        backend.restore(baseline,'restoration-preflight.bin');backend.stable_restore(baseline,'preflight-info.json')
        case=dict(id='engineering-provisioning-reset',kind='reset',level='provisioning',stage=1)
        before=backend.snapshot('reset-before.bin')
        deployed=backend.deploy('fault_1',before,'reset-deployment.bin')
        safe_info(deployed['info'],recovery['source_commit'][:12],1,False)
        initial=deployed['info']['status']['boot_id']
        prepared=backend.prepare(case,dict(before['inspection']['effective_station']))
        private_write(root/'reset-prepared.json',prepared)
        ledger.record('mutation_attempt',case['id'],prepared_sha256=prepared['sha256'])
        started=clock();backend.submit(prepared)
        while True:
            require(clock()-started<120,'reset observation deadline')
            try:info=backend.info()
            except (OSError,TimeoutError):sleeper(.5);continue
            require(info['device_id']==DEVICE and info['revision']==recovery['source_commit'][:12],'reset identity')
            if info.get('phase12_fault_consumed') is True:
                safe_info(info,recovery['source_commit'][:12],1,True)
                require(info['status']['boot_id']!=initial,'reset reboot missing');break
            sleeper(.5)
        reset=backend.snapshot('reset-after.bin');r=reset['inspection'];b=before['inspection']
        require(r['profile_source']==2 and not r['profile_payload'] and r['profile_sequence']==1 and
                r['epoch']==b['epoch']+1 and r['bond_count']==0 and r['default_password'] and
                r['effective_station']==b['effective_station'],'provisioning reset readback')
        assess(case,b,r,(root/before['path']).read_bytes(),(root/reset['path']).read_bytes(),prepared)
        engineering=next(c for c in preparation['candidates'] if c['role']=='engineering')
        backend.roles['engineering']=engineering
        transfer(backend,Path(preparation_artifacts or artifacts)/engineering['uf2']['path'],'engineering.uf2')
        deployed=backend.deploy('engineering',reset,'engineering-deployment.bin');info=deployed['info']
        require(info['revision']==preparation['source_commit'][:12] and info['device_id']==DEVICE and
                info['provisioning_source']=='unprovisioned','engineering source2 identity')
        ssid='p12-'+uuid.uuid4().hex[:12];password=uuid.uuid4().hex
        fixture_attempted=True
        if fixture_roles=='swapped':
            private_write(root/'fixture-roles.json',roles)
            transfer(backend,root/'fixture-roles.json','fixture-roles.json')
        fixture('start_ap',dict(ssid=ssid,password=password,interface=roles['host_ap'],time_server='192.168.84.1'))
        profile=dict(version=1,device_id=DEVICE,wifi=dict(ssid=ssid,password=password,time_server='192.168.84.1'),tls=config['tls'])
        raw=bytes(canonical_profile(profile));path=root/'engineering-profile.json'
        path.write_bytes(raw);os.chmod(path,0o600)
        password_path=root/'default-password.txt';password_path.write_text('wspr-'+info['local_suffix']);os.chmod(password_path,0o600)
        discovery=fixture('discover_ble',dict(expected_name='WsprryPico-0a9d89'))
        address=discovery['address'];require(discovery['matching_names']==1,'unique named B discovery')
        generation=counter(info['provisioning_generation'],'source2 generation');boot=info['status']['boot_id']
        clearance_path=root/'fresh-pair-clearance.json'
        private_write(clearance_path,dict(schema='phase12-fresh-pair-clearance/1',device_id=DEVICE,
            serial='CDDBF8767C506C07',source_commit=preparation['source_commit'],boot_id=boot,
            generation=generation,bond_count=r['bond_count'],profile_source=r['profile_source'],
            readback_sha256=reset['sha256'],readback_name=reset['path']))
        ledger.record('one_provision_attempt',expected_generation=generation+1)
        provision(dict(source_commit=preparation['source_commit'],boot_id=boot,generation=generation,
                       address=address,console=config['console'],profile=str(path),profile_sha256=sha(path),
                       password_file=str(password_path),private_wire_log=str(root/'setup-wire.jsonl'),
                       target_bond_clearance_file=str(clearance_path),target_bond_clearance_sha256=sha(clearance_path)))
        started=clock()
        while True:
            require(clock()-started<120,'provision reboot deadline')
            try:info=backend.info()
            except (OSError,TimeoutError):sleeper(.5);continue
            require(info['device_id']==DEVICE and info['revision']==preparation['source_commit'][:12],'provision identity')
            if info['provisioning_source']=='provisioned':break
            sleeper(.5)
        require(info['status']['boot_id']!=boot and counter(info['provisioning_generation'],'source1 generation')==generation+1,
                'fresh provision generation/boot')
        saved=backend.snapshot('engineering-profile-readback.bin');s=saved['inspection']
        require(s['profile_source']==1 and s['profile_sequence']==generation+1 and
                bytes(canonical_profile(json.loads(s['profile_payload'])))==raw and s['bond_count']==1 and
                s['access_state']==2 and s['profile_healthy'],'exact runtime profile and bond readback')
        deployed=backend.deploy('engineering',saved,'engineering-readback-redeployment.bin')
        private_write(root/'engineering-readback-info.json',deployed['info'])
        cases_attempted=True
        cases(dict(info=deployed['info'],profile_path=str(path),password_file=str(password_path),
                   ble_address=address,engineering=engineering,backup=saved,backend=backend,root=root,
                   preparation=preparation))
        ledger.record('cases_complete' if scope in ('all','composition') else 'common_inputs_complete',scope=scope,physical_acceptance=False)
        if flash_status is not None:
            flash_status(dict(info=backend.info(),backend=backend,root=root,preparation=preparation,
                              preparation_artifacts=preparation_artifacts or artifacts,ble_address=address,
                              profile_path=str(path),password_file=str(password_path)))
            ledger.record('ordinary_flash_status_complete',physical_acceptance=False)
        # Journal selection needs the owned station AP and UTC responder. The
        # final accelerated session group deliberately removes that fixture
        # before joining B's AP, so it must follow all station-dependent cases.
        if journal is not None:
            journal(dict(info=backend.info(),backend=backend,root=root,preparation=preparation,
                         preparation_artifacts=preparation_artifacts or artifacts,ble_address=address,
                         profile_path=str(path),password_file=str(password_path)))
            ledger.record('engineering_journal_complete',physical_acceptance=False)
        if accelerated is not None:
            accelerated(dict(info=backend.info(),backend=backend,root=root,preparation=preparation,
                             preparation_artifacts=preparation_artifacts or artifacts,ble_address=address,
                             profile_path=str(path),password_file=str(password_path)))
            ledger.record('accelerated_cases_complete',physical_acceptance=False)
        if bond_revocation is not None:
            revoked=bond_revocation(dict(info=backend.info(),backend=backend,root=root,preparation=preparation,
                preparation_artifacts=preparation_artifacts or artifacts,ble_address=address))
            ledger.record('single_bond_revocation_complete',assessment=revoked,physical_acceptance=False)

    except BaseException as error:
        primary=dict(type=type(error).__name__,message='engineering parent stopped; inspect private ledger')
        ledger.record('campaign_failed',error_type=type(error).__name__,private_message=str(error))
    finally:
        if fixture_attempted:
            try:fixture('stop',{})
            except BaseException as error:
                primary=primary or dict(type=type(error).__name__,message='fixture cleanup failed')
                record_cleanup_failure('fixture_cleanup_failed',error)
        if baseline:
            try:
                if primary is not None and cases_attempted:
                    # Allow the longest directed lease to expire after uncertain child loss.
                    for _ in range(13):sleeper(5)
                restoration=backend.restore(baseline,'final-restoration.bin')
                restoration['stability']=backend.stable_restore(baseline)
                ledger.record('final_restoration_pass',readback=restoration['readback'])
            except BaseException as error:
                restoration=dict(error=type(error).__name__);record_cleanup_failure('final_restoration_failed',error)
        try:backend.cleanup()
        except BaseException as error:
            primary=primary or dict(type=type(error).__name__,message='host cleanup failed')
            record_cleanup_failure('host_cleanup_failed',error)
    result=dict(status='PREPARED_CASES_REVIEW_REQUIRED' if primary is None and restoration and 'error' not in restoration else 'STOPPED',
                error=primary,cleanup_failures=cleanup_failures,restoration=restoration,rf_jobs=0,physical_acceptance=False,remote_root=backend.remote,scope=scope,fixture_roles=roles,session_selection=session_choice)
    private_write(root/'result.json',result);return result

def bonded_security_keys(data):
    """Pinned BTstack TLV, RP2350 struct60/no signed-write, four BTD slots.

    Read local roots from the selected bank while admitting actual peer records
    and zero-tag deleted history. No secret value is serialized or printed.
    """
    require(len(data)==8192,'two exact BLE TLV banks')
    banks=[data[:4096],data[4096:]];valid=[]
    for index,bank in enumerate(banks):
        if bank==b'\xff'*4096:continue
        require(bank[:7]==b'BTstack' and bank[7] in range(4),'BLE bank framing')
        valid.append(index)
    require(valid,'populated BLE bank required')
    if len(valid)==2:
        e0,e1=banks[0][7],banks[1][7]
        require((e0-e1)%4 in (1,3),'BLE bank epoch selection')
        selected=0 if (e0-e1)%4==1 else 1
    else:selected=valid[0]
    roots={};peers=set();metadata=set();ccc_devices=[];at=8;bank=banks[selected]
    while at+8<=4096:
        tag,size=struct.unpack_from('>II',bank,at)
        if tag==0xffffffff:
            require(bank[at:]==b'\xff'*(4096-at),'BLE erased tail')
            break
        require(size in (8,16,60) and at+8+size<=4096,'BLE record size/framing')
        value=bank[at+8:at+8+size]
        if tag in (0x534d4552,0x534d4952):
            require(size==16 and tag not in roots,'unique local BLE root')
            roots[tag]=value
        elif 0x42544400<=tag<=0x42544403:
            require(size==60 and tag not in peers,'production peer TLV')
            peers.add(tag)
        elif tag==0x42544442: # Pinned ATT server database hash (BTDB), 16 bytes.
            require(size==16 and tag not in metadata,'unique ATT database hash')
            metadata.add(tag)
        elif 0x42544300<=tag<=0x42544313: # Pinned 20 persistent CCC slots.
            require(size==8 and tag not in metadata,'unique persistent CCC slot')
            sequence,handle,value,device=struct.unpack('<IHBB',value)
            require(sequence>0 and handle>0 and value in (1,2,3) and device<4,'persistent CCC encoding')
            metadata.add(tag);ccc_devices.append(device)
        else:require(tag==0,'unknown BLE TLV tag')
        at+=8+size
    else:raise ValueError('BLE missing erased tail')
    require(set(roots)=={0x534d4552,0x534d4952} and len(peers)==1,'two local roots and exactly one active peer')
    require(all(0x42544400+device in peers for device in ccc_devices),'CCC references active peer')
    return roots


def revoke_single_bond(context, *, peer_attempt=None, clock=time.monotonic, sleeper=time.sleep):
    """One actual populated bond reset and optional one retained-peer refusal probe."""
    with tranche_deadline(300):
        backend=context['backend'];root=Path(context['root']);preparation=context['preparation']
        source=preparation['source_commit'];end=clock()+300
        case=dict(id='engineering-single-bond-revocation',kind='reset',level='provisioning',stage=1)
        require(context['info']['revision']==source[:12],'single-bond selected source before checkpoint')
        info=safe_info(backend.info(),source[:12],0,False)
        private_write(root/'single-bond-before-info.json',info)
        require(info['status']['state']=='empty' and info['status']['enabled'] is False and
                info['status']['output_active'] is False,'inactive single-bond checkpoint')
        before=backend.snapshot('single-bond-before.bin');b=before['inspection']
        require(b['bond_count']==1 and b['profile_source']==1 and b['profile_healthy'] and
                b['operational_healthy'] and b['access_state']==2 and
                (b['config'] is None or b['config']['enabled'] is False),'actual one-bond disabled checkpoint')
        before_bytes=(root/before['path']).read_bytes()
        old_roots=bonded_security_keys(before_bytes[0x3f5000:0x3f7000])
        candidate=next(c for c in preparation['candidates'] if c['role']=='fault_1')
        require(candidate['fault_stage']==1 and candidate['revision']==source[:12], 'selected single-bond reset source')
        old_manifest=backend.manifest;old_role=backend.roles['fault_1']
        try:
            backend.manifest=preparation;backend.roles['fault_1']=candidate
            transfer(backend,Path(context['preparation_artifacts'])/candidate['uf2']['path'],'fault_1.uf2')
            deployed=backend.deploy('fault_1',before,'single-bond-reset-deployment.bin')
            initial=safe_info(deployed['info'],source[:12],1,False)['status']['boot_id']
            prepared=backend.prepare(case,b['effective_station'])
            private_write(root/'single-bond-reset-prepared.json',prepared)
            private_write(root/'single-bond-reset-budget.json',dict(max_resets=1,max_old_peer_attempts=int(peer_attempt is not None),max_old_peer_seconds=20,
                max_seconds=300,source_commit=source,scope=('native bond/root readback plus one retained-peer security-refusal attempt without enrollment'
                       if peer_attempt is not None else 'native physical bond/root revocation readback')))
            try:
                backend.submit(prepared) # One attempt; never resubmit an unknown outcome.
            except (OSError,TimeoutError) as error:
                private_write(root/'single-bond-submit-unknown.json',dict(error_type=type(error).__name__,submit_attempts=1))
            while True:
                require(clock()<end,'single-bond reset watchdog deadline')
                try:observed=backend.info()
                except (OSError,TimeoutError):sleeper(.5);continue
                require(observed['device_id']==DEVICE and observed['revision']==source[:12],'single-bond reset identity')
                if observed.get('phase12_fault_consumed') is True:
                    safe_info(observed,source[:12],1,True)
                    require(observed['status']['boot_id']!=initial,'single-bond actual watchdog reboot')
                    private_write(root/'single-bond-watchdog-info.json',observed)
                    break
                sleeper(.5)
            after=backend.snapshot('single-bond-after.bin');after_bytes=(root/after['path']).read_bytes()
            assess(case,b,after['inspection'],before_bytes,after_bytes,prepared)
            new_roots=local_security_keys(after_bytes[0x3f5000:0x3f7000])
            require(new_roots is not None and set(new_roots)==set(old_roots) and
                    all(new_roots[tag]!=old_roots[tag] for tag in old_roots),'both local BLE roots must rotate')
            require(after['inspection']['profile_source']==2 and after['inspection']['bond_count']==0 and
                    after['inspection']['profile_sequence']==1,'single-bond cleared selection')
            ordinary=backend.deploy('engineering',after,'single-bond-source2-redeployment.bin')
            safe_info(ordinary['info'],source[:12],0,False)
            require(ordinary['info']['provisioning_source']=='unprovisioned','ordinary source2 after revocation')
            peer_result=None
            if peer_attempt is not None:
                require(end-clock()>65,'single peer attempt and readback fit tranche budget')
                try:
                    peer_result=peer_attempt(dict(context,info=ordinary['info'],remaining_s=20))
                except (OSError,TimeoutError) as error:
                    peer_result=dict(status='INCONCLUSIVE',old_peer_attempts=1,
                        cryptographic_peer_refusal_observed=False,error_type=type(error).__name__)
                require(peer_result['old_peer_attempts']==1,'one old peer attempt only')
                post=backend.snapshot('single-bond-after-peer.bin');post_bytes=(root/post['path']).read_bytes()
                require(post['inspection']['bond_count']==0 and post_bytes[0x3f5000:0x3f7000]==
                        after_bytes[0x3f5000:0x3f7000],'old peer attempt must not enroll or mutate BLE roots')
                assess(case,b,post['inspection'],before_bytes,post_bytes,prepared)
                source2=backend.deploy('engineering',post,'single-bond-after-peer-source2.bin')
                safe_info(source2['info'],source[:12],0,False)
                require(source2['info']['provisioning_source']=='unprovisioned','source2 preserved after peer attempt')
            result=dict(status='SINGLE_BOND_REVOKED_READBACK_REVIEW_REQUIRED',before_bonds=1,after_bonds=0,
                        reset_attempts=1,local_roots_rotated=2,post_peer_bond_zero_verified=peer_attempt is not None,
                        old_peer_attempts=int(peer_attempt is not None),
                        cryptographic_peer_refusal_observed=bool(peer_result and peer_result['cryptographic_peer_refusal_observed']),
                        old_peer_result=peer_result,
                        source_commit=source,rf_jobs=0,physical_rf_acceptance=False)
            private_write(root/'single-bond-result.json',result)
            return result
        finally:
            backend.manifest=old_manifest;backend.roles['fault_1']=old_role


def deploy_accelerated(context):
    """One declared accelerated image transition, retaining the provisioned flash."""
    backend=context['backend']
    saved=backend.snapshot('before-session-fixture.bin')
    require(saved['inspection']['profile_source']==1 and saved['inspection']['profile_healthy'],
            'accelerator requires retained runtime profile')
    role=next(c for c in context['preparation']['candidates'] if c['role']=='session_deadline')
    backend.roles['session_deadline']=role
    transfer(backend,Path(context['preparation_artifacts'])/role['uf2']['path'],'session_deadline.uf2')
    result=backend.deploy('session_deadline',saved,'session-fixture-deployment.bin')
    return dict(info=result['info'],backup=saved,candidate=role)


def return_journal_checkpoint(context):
    """Restore A before observers that are independently bound to its credentials."""
    checkpoint=Path(context['root'])/'journal-a-before.bin'
    require(checkpoint.is_file() and not checkpoint.is_symlink(),'regular pre-journal checkpoint')
    saved=dict(path=checkpoint.name,sha256=sha(checkpoint),inspection=context['backend'].inspect(checkpoint))
    require(saved['inspection']['profile_source']==1 and saved['inspection']['profile_healthy'] is True and
            saved['inspection']['profile_payload'].encode('ascii')==Path(context['profile_path']).read_bytes() and
            saved['inspection']['bond_count']==1,'exact pre-journal A checkpoint')
    return context['backend'].deploy('engineering',saved,'journal-a-return.bin',restore=True)

class RemoteAdapters:
    def __init__(self,root):self.root=root;self.backend=None;self.child=None
    def invoke(self,script,payload=None,args=(),timeout=180,keepalive=False):
        command=shlex.join(['python3',self.backend.remote+'/'+script,*map(str,args)])
        log=self.root/('remote-'+uuid.uuid4().hex+'.log')
        with log.open('x') as output:
            os.chmod(log,0o600)
            self.child=subprocess.Popen(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','wspr5',command],
                stdin=subprocess.PIPE,stdout=output,stderr=subprocess.STDOUT)
            try:
                if payload is not None:self.child.stdin.write(json.dumps(payload).encode()+b'\n');self.child.stdin.flush()
                if not keepalive:self.child.stdin.close();self.child.stdin=None
                code=self.child.wait(timeout=timeout)
                require(code==0,'bounded remote adapter failed; inspect private transcript')
            finally:
                errors=shutdown_child(self.child);self.child=None
                require(not errors,'remote adapter shutdown failed')
        # Helpers have one JSON stdout record; keep raw private and never print.
        lines=log.read_text().splitlines();require(lines,'remote adapter result missing')
        return json.loads(lines[-1])
    def stage(self,source,name):
        source=Path(source)
        require(source.is_file() and not source.is_symlink(),'regular input')
        transfer(self.backend,source,name)
        subprocess.run(['ssh','wspr5','chmod','600',self.backend.remote+'/'+name],check=True,timeout=10)
        saved=self.root/('observer-'+name.replace('/','-'))
        if not saved.exists():saved.write_bytes(source.read_bytes());os.chmod(saved,0o600)
        return sha(source)
    def collect(self,names):
        for name in names:
            target=self.root/name
            if target.exists():continue
            result=subprocess.run(['scp','-q','wspr5:'+self.backend.remote+'/'+name,str(target)],capture_output=True,timeout=45)
            if result.returncode==0:os.chmod(target,0o600)
            elif target.exists():target.unlink() # failed partial retrieval is not evidence
    def fixture(self,action,args):
        if self.backend is None:raise ValueError('remote backend not bound')
        try:return self.invoke('phase12_engineering_fixture.py',dict(root=self.backend.remote,authority=AUTHORITY,action=action,**args),timeout=7380 if action=='cases' else 180,keepalive=action=='cases')
        except BaseException:
            try:self.collect(('fixture-action-failure.json',))
            except BaseException:pass
            raise
        finally:
            if action=='discover_ble':
                try:self.collect(('ble-discovery-original.jsonl',))
                except BaseException:pass # Diagnostic retrieval preserves original discovery outcome.
    def provision(self,p):
        for key,name in [('profile','engineering-profile.json'),('password_file','default-password.txt'),
                         ('target_bond_clearance_file','fresh-pair-clearance.json')]:
            transfer(self.backend,Path(p[key]),name);p[key]=self.backend.remote+'/'+name
        names=PROVISION_HELPERS
        for name in names:
            source=Path(__file__).parent/name;transfer(self.backend,source,name)
            saved=self.root/('observer-'+name);saved.write_bytes(source.read_bytes());os.chmod(saved,0o600)
        private_write(self.root/'setup-inputs.json',{name:sha(self.root/('observer-'+name)) for name in names})
        args=['--run']
        for key,value in p.items():
            if key=='private_wire_log':value=self.backend.remote+'/setup-wire.jsonl'
            args.extend(['--'+key.replace('_','-'),str(value)])
        primary=None
        try:
            result=self.invoke('phase12_engineering_setup.py',args=args,timeout=150)
        except BaseException as error:
            primary=error
            raise
        finally:
            try:self.collect(('setup-wire.jsonl',))
            except BaseException as error:
                try:private_write(self.root/'setup-capture-error.json',dict(error_type=type(error).__name__))
                except BaseException:
                    if primary is None:raise error
                if primary is None:raise
        target=self.root/'setup-wire.jsonl'
        require(target.is_file() and not target.is_symlink() and target.stat().st_size>0,
                'original setup capture required')
        return result


def credential_config(root):
    from phase12_engineering_setup import private_bytes
    root=Path(root).resolve();deployment=read_json(root/'ca/server/deployment.json')
    require(deployment['device_id']==DEVICE,'certificate deployment B identity')
    def text(name):return private_bytes(root/name,16384).decode('ascii')
    return dict(console=CONSOLE,
        tls=dict(hostname=deployment['hostname'],port=443,
                 server_certificate=text('ca/server/server.crt'),server_private_key=text('ca/server/server.key'),
                 client_ca=text('ca/server/client-ca.crt')))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','artifact-root','preparation-manifest','preparation-artifact-root','campaign','inspector','credential-root'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--scope',choices=SCOPES,default='all')
    p.add_argument('--skip-accepted-time-cases',action='store_true')
    p.add_argument('--cookie-grace-stages',choices=('running',))
    p.add_argument('--cookie-grace-only',action='store_true')
    p.add_argument('--fixture-roles',choices=('engineering','swapped'),default='engineering')
    p.add_argument('--native',type=Path)
    p.add_argument('--run',action='store_true');p.add_argument('--recover-only',action='store_true');a=p.parse_args()
    choice=session_selection(a.scope,a.cookie_grace_stages,a.cookie_grace_only)
    require(not a.skip_accepted_time_cases or a.scope in ('all','composition','application'),
            'accepted time continuation requires composition/application scope')
    require(a.fixture_roles=='engineering' or a.scope=='network','swapped roles require network scope')
    recovery=read_json(a.manifest)
    verify(recovery,a.artifact_root)
    if a.run and a.recover_only:
        os.umask(0o077)
        retained=read_json(a.campaign/'campaign-config.json')
        remote=RemoteAdapters(a.campaign)
        from types import SimpleNamespace
        remote.backend=SimpleNamespace(remote='/home/pi/phase12-recovery-'+retained['campaign_id'])
        try:
            result=recover_only(recovery,a.artifact_root,a.campaign,a.inspector)
        finally:
            remote.fixture('stop',{})
        print(json.dumps(result));return
    preparation=read_json(a.preparation_manifest)
    verify(preparation,a.preparation_artifact_root)
    preflight_staging(a.scope,a.preparation_manifest,a.credential_root)
    config=credential_config(a.credential_root)
    certificate=subprocess.check_output(['openssl','x509','-in',str(a.credential_root/'ca/server/server.crt'),'-outform','DER'],timeout=10)
    server_sha256=hashlib.sha256(certificate).hexdigest()
    require(server_sha256==read_json(a.credential_root/'ca/server/deployment.json')['certificate_sha256'],'server DER fingerprint binding')
    canonical_profile(dict(version=1,device_id=DEVICE,wifi=dict(ssid='p12-validation',password='0'*32,time_server='192.168.84.1'),tls=config['tls']))
    if not a.run:
        print(json.dumps(dict(status='VALIDATED_NO_HARDWARE',rf_jobs=0,provision_attempts=1)));return
    require(a.native is not None and a.native.is_file(), 'native journal preconditioner required')
    os.umask(0o077)
    def interrupted(*_):raise KeyboardInterrupt('parent interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    remote=RemoteAdapters(a.campaign)
    def factory(*args):
        b=Backend(*args);remote.backend=b
        original=b.setup
        def setup():
            info=original()
            for name in FIXTURE_HELPERS:
                remote.stage(Path(__file__).parent/name,name)
            if a.scope=='journal-stimuli':
                for name in JOURNAL_STIMULI_HELPERS:
                    remote.stage(Path(__file__).parent/name,name)
            return info
        b.setup=setup;return b
    def cases(context):
        inputs={name:remote.stage(Path(__file__).parent/name,name) for name in COMMON_HELPERS}
        repository=Path(__file__).parents[1]
        inputs['preparation-manifest.json']=remote.stage(a.preparation_manifest,'preparation-manifest.json')
        subprocess.run(['ssh','wspr5','mkdir','-p',remote.backend.remote+'/docs/protocol'],check=True,timeout=10)
        for source,name,key in COMMON_REPOSITORY_ASSETS:
            inputs[key]=remote.stage(repository/source,name)
        for name,source in CREDENTIAL_ASSETS:inputs[name]=remote.stage(a.credential_root/source,name)
        private_write(context['root']/'dispatch-inputs.json',inputs)
        if a.scope not in ('all','composition','application'):
            # Independent station-dependent scopes inherit the same owned
            # peer-bound UTC prerequisite normally established by T1-T4.
            if a.scope in ('time-jobs','time-jobs-invalidation','time-jobs-sntp','flash-status','journal','journal-stimuli','network','sessions'):
                warm_end=time.monotonic()+180
                peer_bound=False;warm_observation=0
                while True:
                    info=context['backend'].info()
                    warm_observation+=1
                    require(warm_observation<=361,'finite isolated warm observations')
                    private_write(context['root']/('isolated-warm-info-%03d.json'%warm_observation),info)
                    safe_info(info,preparation['source_commit'][:12],0,False)
                    require(info['status']['boot_id']==context['info']['status']['boot_id'],'isolated warm same boot')
                    require(time.monotonic()<warm_end,'isolated station/time prerequisite deadline')
                    require(info['provisioning_source']=='provisioned' and counter(info['provisioning_generation'],'isolated generation')==counter(context['info']['provisioning_generation'],'original generation'),'isolated warm source/generation')
                    if info['network']['link_status']==3:
                        require(info['network']['ipv4'].startswith('192.168.84.'),'isolated owned station')
                        if not peer_bound:
                            remote.fixture('bind_peer',dict(address=info['network']['ipv4']));peer_bound=True
                            if a.scope not in ('time-jobs','time-jobs-invalidation','time-jobs-sntp'):remote.fixture('sntp_on',{})
                        if a.scope in ('time-jobs','time-jobs-invalidation','time-jobs-sntp') or (info['status']['clock_state']=='synchronized' and int(info['network']['accepted'])>0):break
                    time.sleep(.5)
            return dict(status='COMMON_INPUTS_STAGED',scope=a.scope)
        info=context['info']
        payload=dict(root=remote.backend.remote,authority=AUTHORITY,manifest_sha256=sha(a.preparation_manifest),
            boot_id=info['status']['boot_id'],source_commit=preparation['source_commit'],
            profile_generation=counter(info['provisioning_generation'],'generation'),
            profile_sha256=sha(context['profile_path']),image_sha256=context['engineering']['uf2']['sha256'],
            ble_address=context['ble_address'],server_sha256=server_sha256,
            scope='application' if a.scope=='application' else 'composition',
            skip_accepted_time_cases=a.skip_accepted_time_cases or a.scope=='application')
        try:
            return remote.invoke('phase12_engineering_dispatch.py',payload,timeout=450 if a.scope=='application' else 7900,keepalive=True)
        finally:
            remote.collect(('time-wire.jsonl','time-result.json','composition-capture.jsonl','composition-plan.json',
                'directed-plan.json','directed-wave-1-wire.jsonl','directed-wave-2-wire.jsonl',
                'directed-wave-timeline.jsonl','directed-failure.json','final-authority.json','remote-result.json',
                'application-idle-wire.jsonl','application-idle-result.json','application-reboot-attempt.json',
                'application-reboot-result.json','application-cold-wire.jsonl','application-cold-result.json'))
    def accelerated(context):
        # Predetermined fresh-boot time tranche. Disabling only the campaign's
        # responder before reboot prevents retained SNTP from biasing T5.
        backend=context['backend']
        if a.scope=='network':
            # Keep the exact boot whose station/clock prerequisite was already verified.
            retained_end=time.monotonic()+5
            info=backend.info()
            private_write(context['root']/'network-retained-warm-info.json',info)
            safe_info(info,preparation['source_commit'][:12],0,False)
            require(time.monotonic()<retained_end and info['status']['boot_id']==context['info']['status']['boot_id'] and
                    info['provisioning_source']=='provisioned' and
                    counter(info['provisioning_generation'],'network generation')==counter(context['info']['provisioning_generation'],'warm generation') and
                    info['network']['link_status']==3 and info['network']['ipv4'].startswith('192.168.84.') and
                    info['status']['clock_state']=='synchronized' and counter(info['network']['accepted'],'accepted')>0,
                    'exact retained warm network prerequisite')
        else:
            remote.fixture('sntp_off',{})
            prefix={'time-jobs-invalidation':'time-invalidation','time-jobs-sntp':'time-sntp'}.get(a.scope,'time-jobs')
            saved=backend.snapshot('before-'+prefix+'.bin')
            require(saved['inspection']['profile_source']==1 and saved['inspection']['profile_healthy'],
                    'T5 requires exact healthy runtime profile')
            info=backend.deploy('engineering',saved,prefix+'-deployment.bin')['info']
        names=accelerated_helpers(a.scope)
        inputs={name:remote.stage(Path(__file__).parent/name,name) for name in names}
        private_write(context['root']/'accelerated-inputs.json',inputs)
        def payload(info,candidate):
            return dict(root=backend.remote,authority=AUTHORITY,manifest_sha256=sha(a.preparation_manifest),
                source_commit=preparation['source_commit'],boot_id=info['status']['boot_id'],
                profile_generation=counter(info['provisioning_generation'],'generation'),
                profile_sha256=sha(context['profile_path']),image_sha256=candidate['uf2']['sha256'],
                ble_address=context['ble_address'],server_sha256=server_sha256)
        engineering=next(c for c in preparation['candidates'] if c['role']=='engineering')
        if a.scope in ('all','time-jobs','time-jobs-invalidation','time-jobs-sntp'):
          selected=payload(info,engineering)
          prefix={'time-jobs-invalidation':'time-invalidation','time-jobs-sntp':'time-sntp'}.get(a.scope,'time-jobs')
          if a.scope=='time-jobs-invalidation':selected['time_selection']='invalidation'
          if a.scope=='time-jobs-sntp':selected['time_selection']='sntp'
          try:
            remote.invoke('phase12_engineering_time_dispatch.py',selected,
                          timeout={'time-jobs-invalidation':220,'time-jobs-sntp':160}.get(a.scope,280),keepalive=True)
          finally:remote.collect((prefix+'-wire.jsonl',prefix+'-result.json'))
        if a.scope in ('all','network'):
          remote.fixture('sntp_on',{})
          try:
            remote.invoke('phase12_engineering_network_dispatch.py',dict(payload(backend.info(),engineering),roles_sha256=role_map(a.fixture_roles)['sha256']),
                          timeout=950,keepalive=True)
          finally:remote.collect(('network-wire.jsonl','network-result.json'))
        if a.scope in ('all','sessions'):
          remote.fixture('sntp_off',{})
          selected=deploy_accelerated(context)
          try:
              remote.invoke('phase12_engineering_session_dispatch.py',session_payload(payload(selected['info'],selected['candidate']),choice),
                            timeout=500,keepalive=True)
          finally:
              remote.collect(('session-fixture-wire.jsonl','session-wire.jsonl','session-result.json',
                              'ntp-metrics.json','ntp-stopped.json','fixture-management-before.json'))
    @bounded_flash_status
    def flash_status(context):
        backend=context['backend']; root=context['root']; ordinary=next(c for c in preparation['candidates'] if c['role']=='engineering')
        outer_end=time.monotonic()+900
        def remaining():
            left=outer_end-time.monotonic();require(left>0,'whole ordinary serialization tranche deadline');return left
        remaining()
        before=backend.snapshot('before-config-rollover.bin'); b=before['inspection']
        require(b['profile_source']==1 and b['profile_healthy'] and b['operational_healthy'] and
                b['config'] and b['config']['enabled'] is False,'healthy disabled operational checkpoint')
        prepared_path=root/'config-rollover.bin'
        output=subprocess.run([str(a.native.resolve()),'--backup',str(root/before['path']),
            '--prepare-config-rollover','yes','--output',str(prepared_path)],capture_output=True,timeout=min(30,remaining()),check=True)
        receipt=json.loads(output.stdout);require(receipt['status']=='OFFLINE_ROLLOVER_READY' and receipt['appends'] in (0,1),'finite unchanged-config preparation')
        private_write(root/'config-rollover-receipt.json',dict(receipt,native_sha256=sha(a.native),fixture_sha256=sha(prepared_path)))
        prepared=backend.inspect(prepared_path); original=(root/before['path']).read_bytes(); seed=prepared_path.read_bytes()
        require(seed[:0x3fb000]==original[:0x3fb000] and seed[0x3fd000:]==original[0x3fd000:] and
            prepared['config']==b['config'] and prepared['watermark']==b['watermark'] and
            prepared['cursor_sequence']==b['cursor_sequence'] and prepared['config_sequence']==b['config_sequence']+receipt['appends'],
            'preconditioning exact configuration/cursor/unrelated preservation')
        remote.stage(prepared_path,'config-rollover.bin')
        remaining()
        deployed=backend.deploy('engineering',dict(path='config-rollover.bin',sha256=sha(prepared_path),inspection=prepared),
                                'config-rollover-deployment.bin',restore=True)
        end=min(outer_end,time.monotonic()+180)
        while True:
            info=backend.info();safe_info(info,preparation['source_commit'][:12],0,False)
            require(info['status']['boot_id']==deployed['info']['status']['boot_id'] and
                counter(info['provisioning_generation'],'generation')==prepared['profile_sequence'],'preconditioned exact boot/generation')
            if info['network']['link_status']==3 and info['status']['clock_state']=='synchronized' and info['network']['ipv4'].startswith('192.168.84.') and int(info['network']['accepted'])>0:break
            require(time.monotonic()<end,'ordinary trace station/time readiness');time.sleep(.5)
        config_path=root/'flash-status-config.json';private_write(config_path,prepared['config'])
        config_hash=remote.stage(config_path,'flash-status-config.json')
        for name in FLASH_STATUS_HELPERS:
            remote.stage(Path(__file__).parent/name,name)
        plan=dict(device_id=DEVICE,console=CONSOLE,wtp_console=CONSOLE.replace('-if00','-if02'),
            source_commit=preparation['source_commit'],boot_id=info['status']['boot_id'],profile_generation=prepared['profile_sequence'],
            image_path=backend.remote+'/engineering.uf2',image_sha256=ordinary['uf2']['sha256'],
            profile_path=backend.remote+'/engineering-profile.json',profile_sha256=sha(context['profile_path']),
            address=info['network']['ipv4'],port=443,hostname=config['tls']['hostname'],server_sha256=server_sha256,
            ca=backend.remote+'/client-ca.crt',cert=backend.remote+'/owner-client.crt',key=backend.remote+'/owner-client.key',
            contender_cert=backend.remote+'/contender-client.crt',contender_key=backend.remote+'/contender-client.key',
            password_file=backend.remote+'/default-password.txt',ble_address=context['ble_address'],
            config_path=backend.remote+'/flash-status-config.json',config_sha256=config_hash,
            credential_hashes={k:sha(a.credential_root/v) for k,v in dict(ca='ca/server/client-ca.crt',cert='owner/client.crt',key='owner/client.key').items()})
        private_write(root/'flash-status-plan.json',plan)
        try:
            remote.invoke('phase12_engineering_flash_status_dispatch.py',dict(root=backend.remote,authority=AUTHORITY,
                manifest_sha256=sha(a.preparation_manifest),source_commit=preparation['source_commit'],plan=plan),timeout=min(340,remaining()),keepalive=True)
        finally:remote.collect(('flash-status-wire.jsonl','flash-status-result.json'))
        result=read_json(root/'flash-status-result.json');require(result['review_required'] is True and result['status_samples']==60,'complete measured ordinary serialization')
        remaining()
        after=backend.snapshot('after-flash-status.bin'); actual=(root/after['path']).read_bytes(); selected=after['inspection']
        preserve_flash_reserved(seed,actual)
        require(
            selected['config']==result['config'] and selected['config_sequence']==prepared['config_sequence']+1 and
            selected['watermark']==prepared['watermark'] and selected['cursor_sequence']==prepared['cursor_sequence'],
            'exact one-save durable configuration and unrelated preservation')
        backend.deploy('engineering',after,'after-flash-status-redeployment.bin')
        remaining()
    def journal(context):
        from phase12_engineering_journal import prepare, tranche
        import sys
        # The supported certificate CLI confines repository keys to config/local.
        credentials_root=Path(__file__).parents[1]/'config/local'/('phase12-journal-'+Path(context['root']).name)
        # A fresh frozen source tree deliberately contains no private outputs.
        # Create the supported CLI's private parent as part of this campaign.
        credentials_root.mkdir(mode=0o700,parents=True)
        def create(args):
            result=subprocess.run([sys.executable,str(Path(__file__).parent/'network_certificates.py'),*args],
                capture_output=True,timeout=30)
            require(result.returncode==0,'local independent credential creation failed')
        principals=prepare(credentials_root,Path(context['profile_path']).read_bytes(),create)
        principals['A']=dict(ca=str(a.credential_root/'ca/server/client-ca.crt'),
            cert=str(a.credential_root/'owner/client.crt'),key=str(a.credential_root/'owner/client.key'),
            server_sha256=server_sha256,profile_path=context['profile_path'],profile_sha256=sha(context['profile_path']))
        for role in ('B','C'):
            remote.stage(principals[role]['profile_path'],'engineering-profile-'+role+'.json')
        principal_hashes={}
        for role,principal in principals.items():
            principal_hashes[role]={}
            for key in ('ca','cert','key'):
                principal_hashes[role][key]=remote.stage(principal[key],'journal-'+role+'-'+key+('.key' if key=='key' else '.crt'))
        for name in JOURNAL_HELPERS:
            remote.stage(Path(__file__).parent/name,name)
        if a.scope=='journal-stimuli':
            for name in JOURNAL_STIMULI_HELPERS:
                remote.stage(Path(__file__).parent/name,name)
        def stage_image(role,candidate):
            context['backend'].roles[role]=candidate
            remote.stage(Path(context['preparation_artifacts'])/candidate['uf2']['path'],role+'.uf2')
        def invoke(request):
            try:return remote.invoke('phase12_engineering_journal_dispatch.py',request,timeout=min(request['remaining_s'],125 if request.get('action') else 180),keepalive=True)
            finally:
                remote.collect(journal_outputs(request))
        result=tranche(dict(context,principals=principals,authority=AUTHORITY,
            manifest_sha256=sha(a.preparation_manifest),hostname=config['tls']['hostname'],principal_hashes=principal_hashes),
            stage_image,invoke,invoke,private_write,
            selection='stimuli' if a.scope=='journal-stimuli' else 'standard',stage_seed=remote.stage)
        private_write(context['root']/'journal-result.json',result)
        # The following time/network/session observers are bound to profile A.
        # Return to its exact pre-journal checkpoint, including the measured
        # operational save, rather than passing C credentials to A observers.
        return_journal_checkpoint(context)
    def old_peer(context):
        for name in BOND_REFUSAL_HELPERS:
            remote.stage(Path(__file__).parent/name,name)
        info=context['info']
        request=dict(root=context['backend'].remote,authority=AUTHORITY,
            manifest_sha256=sha(a.preparation_manifest),source_commit=preparation['source_commit'],
            boot_id=info['status']['boot_id'],ble_address=context['ble_address'])
        try:return remote.invoke('phase12_engineering_bond_refusal_dispatch.py',request,timeout=20,keepalive=True)
        finally:remote.collect(('single-bond-old-peer-wire.jsonl','single-bond-old-peer-result.json'))
    def revoke(context):return revoke_single_bond(context,peer_attempt=old_peer)
    try:
        result=execute(recovery,preparation,a.artifact_root,a.campaign,a.inspector,config,
            backend_factory=factory,fixture=remote.fixture,provision=remote.provision,cases=cases,accelerated=accelerated if a.scope in ('all','time-jobs','time-jobs-invalidation','time-jobs-sntp','network','sessions') else None,
            journal=journal if a.scope in ('all','journal','journal-stimuli') else None,
            flash_status=flash_status if a.scope in ('all','flash-status') else None,
            bond_revocation=revoke if a.scope in ('all','bond-revocation') else None,
            preparation_artifacts=a.preparation_artifact_root,scope=a.scope,session_choice=choice,fixture_roles=a.fixture_roles)
    finally:
        remote.collect(('fixture-roles.json','fixture-roles-bound.json','fixture-radio-preflight.json','owned-ap-beacon-readiness.json','fixture-management-before.json',
                        'ntp-ready.json','ntp-stopped.json','ntp-startup-failure.json',
                        'populated-seed-start-ap-inspection.json',
                        'populated-seed-failure-ap-inspection.json',
                        'populated-seed-success-ap-inspection.json'))
        if a.scope=='journal-stimuli':
            from phase12_engineering_journal_stimuli import FILES
            remote.collect(('journal-stale-suspend.json',*FILES))
    print(json.dumps(dict(status=result['status'],restored=bool(result['restoration'] and 'error' not in result['restoration']))))
    if result['status']=='STOPPED':raise SystemExit(1)
if __name__=='__main__':main()
