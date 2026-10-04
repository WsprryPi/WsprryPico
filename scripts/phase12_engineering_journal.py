#!/usr/bin/env python3
"""Injected exact B engineering profile-journal proof. Import has no hardware action.

Parent alone deploys/restores images and flash snapshots. This helper performs at
most one authenticated apply and one USB confirmation; uncertain applies are not
cancelled or retried. TLS proof is readonly HELLO/STATUS, never jobs/ownership.
"""
import base64
import hashlib
import json
import os
import secrets
import re
import ssl
import time
from pathlib import Path
from types import SimpleNamespace
import inhibited_network_acceptance as network
from phase12_composition_audit import counter
from phase12_recovery_device import DEVICE, strict, require
from phase12_recovery_orchestrator import safe_info
from wsprrypico_ble import ClientError, FRAGMENT_BYTES, canonical_profile

REFUSALS = {'TLSV1_ALERT_UNKNOWN_CA',
            'SSLV3_ALERT_BAD_CERTIFICATE', 'TLSV13_ALERT_CERTIFICATE_REQUIRED',
            'TLSV1_ALERT_ACCESS_DENIED', 'SSLV3_ALERT_HANDSHAKE_FAILURE'}


def prepare(root, baseline, create):
    """Offline credential creation through injected supported certificate CLI.

    create receives argument arrays for network_certificates.main, not shell text.
    Refuses existing output; caller owns ignored private root and baseline file.
    """
    root = Path(root)
    require(root.is_absolute() and root.is_dir() and not root.is_symlink(), 'private root')
    value = strict(baseline)
    canonical_profile(value)
    require(value['device_id'] == DEVICE and value['wifi']['time_server'] == '192.168.84.1',
            'exact B isolated fixture')
    result = {}
    for role in ('B', 'C'):
        directory = root / ('engineering-trust-' + role)
        require(not directory.exists() and not directory.is_symlink(), 'existing trust fixture')
        create(['init', '--directory', str(directory), '--device-id', DEVICE,
                '--hostname', value['tls']['hostname']])
        create(['issue-client', '--ca-directory', str(directory), '--name', 'journal-' + role,
                '--output', str(directory / 'client')])
        replacement = dict(value, tls=dict(value['tls']))
        replacement['tls'].update(server_certificate=(directory/'server/server.crt').read_text(),
                                 server_private_key=(directory/'server/server.key').read_text(),
                                 client_ca=(directory/'client-ca.crt').read_text())
        payload = canonical_profile(replacement)
        path = root / ('engineering-profile-' + role + '.json')
        with path.open('xb') as file:
            path.chmod(0o600); file.write(payload)
        result[role] = dict(profile_path=str(path), profile_sha256=hashlib.sha256(payload).hexdigest(),
                            ca=str(directory/'client-ca.crt'), cert=str(directory/'client/client.crt'),
                            key=str(directory/'client/client.key'), server=str(directory/'server/server.crt'),
                            server_sha256=hashlib.sha256(ssl.PEM_cert_to_DER_cert(
                                replacement['tls']['server_certificate'])).hexdigest(),
                            ca_sha256=hashlib.sha256(replacement['tls']['client_ca'].encode()).hexdigest())
        payload[:] = bytes(len(payload))
    original_ca=hashlib.sha256(value['tls']['client_ca'].encode()).hexdigest()
    require(all(result[role]['ca_sha256'] != original_ca for role in ('B','C')), 'independent from retained A')
    require(result['B']['ca_sha256'] != result['C']['ca_sha256'] and
            result['B']['server_sha256'] != result['C']['server_sha256'], 'independent fixtures')
    return result


def apply_once(context, payload, password, client, observe, command, evidence,
               *, clock=time.monotonic, sleeper=time.sleep):
    start = clock(); confirmations = 0; applies = 0
    ceiling=min(300,context.get('remaining_s',300));require(type(ceiling) in (int,float) and 0<ceiling<=300,'remaining budget')
    stage = context['stage']; require(stage in (0, 8, 9, 10), 'named journal stage')
    require(re.fullmatch('[0-9a-f]{40}', context['source_commit']) and
            re.fullmatch('[0-9a-f]{32}', context['boot_id']), 'full source and boot identity')
    require(type(context['generation']) is int and 0 <= context['generation'] < 2**64-1,
            'generation range')
    parsed = strict(bytes(payload))
    require(parsed['device_id'] == DEVICE and
            hashlib.sha256(payload).hexdigest() == context['profile_sha256'], 'profile binding')
    require(bytes(canonical_profile(parsed)) == bytes(payload), 'canonical exact profile')
    stage_end = start + ceiling
    def remaining(end=stage_end, message='whole journal stage deadline'):
        left = end - clock()
        require(left > 0, message)
        return left
    def call(operation, *args, end=stage_end, message='whole journal stage deadline', **values):
        left = remaining(end, message)
        timeout = client.timeout
        client.timeout = min(timeout, left)
        try:
            result = operation(*args, **values)
        finally:
            client.timeout = timeout
        remaining(end, message)
        return result
    def guard():
        remaining()
        info, raw = observe()
        require(isinstance(raw, bytes), 'actual INFO wire')
        evidence.record('journal_info', raw_hex=raw.hex())
        remaining()
        require(strict(raw) == info, 'actual INFO wire')
        safe_info(info, context['source_commit'][:12], stage, False)
        require(info['status']['boot_id'] == context['boot_id'] and
                counter(info['provisioning_generation'], 'generation') == context['generation'] and
                info['provisioning_source'] == 'provisioned' and
                info['lan_wtp_mode'] == 'engineering-tls', 'exact retained profile authority')
        require(info['access_default_password'] is True and
                password == 'wspr-'+info['local_suffix'], 'exact retained default access credential')
        remaining()
        return info
    try:
        guard()
        identity = call(client.connect, context['ble_address'], DEVICE, allow_pairing=False)
        require(identity['generation'] == context['generation'], 'retained BLE generation')
        call(client.authorize, password); call(client.synchronize_time); guard()
        session = secrets.token_hex(16); request = secrets.token_hex(16)
        call(client._field, 'open', session_id=session)
        for offset in range(0, len(payload), FRAGMENT_BYTES):
            end = min(offset+FRAGMENT_BYTES, len(payload))
            call(client._field, 'write', session_id=session, offset=offset, final=end == len(payload),
                          payload=base64.b64encode(payload[offset:end]).decode('ascii'))
        step = call(client._field, 'profile_step_up', profile_session_id=session,
                             apply_request_id=request, expected_generation=context['generation'],
                             password=password)
        confirmation, ready = client._step_up_ready(step)
        remaining()
        require(confirmation and not ready, 'fresh USB confirmation required')
        guard(); remaining(); reply = command('ACCESS CONFIRM PROFILE '+DEVICE)
        remaining()
        require(reply.get('ok') is True, 'USB confirmation rejected'); confirmations += 1
        deadline = min(stage_end, clock()+25)
        while not ready:
            sleeper(min(.1, remaining(deadline, 'confirmation deadline')))
            remaining(deadline, 'confirmation deadline')
            step = call(client._field, 'profile_step_up_status', apply_request_id=request,
                        end=deadline, message='confirmation deadline')
            _, ready = client._step_up_ready(step)
            remaining(deadline, 'confirmation deadline')
        guard(); applies += 1
        evidence.record('journal_apply_attempt', stage=stage, expected_generation=context['generation']+1)
        try:
            reply = call(client.exchange, dict(version=1, operation='apply', request_id=request,
                session_id=session, device_id=DEVICE, expected_generation=context['generation']))
        except ClientError as error:
            # Never issue cancel or resend after entering the apply boundary.
            evidence.record('journal_apply_uncertain', code=error.code)
            remaining()
            return dict(status='APPLY_UNCERTAIN_READBACK_REQUIRED', stage=stage,
                        applies=applies, confirmations=confirmations, rf_jobs=0)
        require(stage == 0 and reply.get('generation') == context['generation']+1,
                'fault stage unexpectedly acknowledged or wrong generation')
        remaining()
        return dict(status='APPLY_ACKNOWLEDGED_READBACK_REQUIRED', stage=stage,
                    applies=applies, confirmations=confirmations, rf_jobs=0)
    finally:
        payload[:] = bytes(len(payload)); password = ''; client.close()


def tls_probe(plan, principal, evidence):
    """Probe actual pinned server and readonly wire; errors remain inconclusive unless TLS-auth specific."""
    require('ca' in plan, 'selected server CA required independently of tested client')
    args = SimpleNamespace(**dict(plan, cert=principal['cert'], key=principal['key']))
    require(re.fullmatch(r'192\.168\.84\.(?:[1-9][0-9]?|1[0-9]{2}|2[0-4][0-9]|25[0-4])', args.address) and
            args.device_id == DEVICE and args.port == 443 and
            re.fullmatch('[0-9a-f]{64}', args.server_sha256), 'exact isolated TLS destination')
    evidence.record('journal_tls_attempt', address=args.address, hostname=args.hostname,
                    server_sha256=args.server_sha256, boot_id=args.boot_id, device_id=args.device_id)
    pinned=[]
    class NetworkEvidence:
        def record(self,kind,value):
            evidence.record(kind,value=value)
            if kind=='tls':
                require(value['fingerprint']==args.server_sha256 and value['destination']==args.address and
                        value['identity']==args.hostname, 'actual TLS server pin evidence')
                pinned.append(value)
    peer = network.Peer(args, NetworkEvidence())
    try:
        peer.open()
        status = peer.request('STATUS', {})
        network.check_status(status, args.boot_id, unowned=True)
        return dict(outcome='accepted', server_sha256=args.server_sha256, boot_id=args.boot_id,
                    device_id=args.device_id, status=status, address=args.address, hostname=args.hostname)
    except ssl.SSLError as error:
        reason = getattr(error, 'reason', '')
        require(reason in REFUSALS and len(pinned)==1,
                'inconclusive TLS failure: selected server pin and server authentication alert required')
        evidence.record('journal_tls_refusal', reason=reason, address=args.address,
                        hostname=args.hostname, server_sha256=args.server_sha256)
        return dict(outcome='tls_auth_refused', reason=reason, address=args.address,
                    hostname=args.hostname, server_sha256=args.server_sha256)
    finally:
        peer.close()


def verify_selection(context, info, raw, exact_payload, observed_payload, before_regions,
                     after_regions, probes, evidence):
    """Parent supplies fresh consumed fixture boot, full profile bytes, independent TLS results and region hashes."""
    stage = context['stage']; require(stage in (0, 8, 9, 10), 'stage')
    require(strict(raw) == info, 'actual post INFO wire')
    safe_info(info, context['source_commit'][:12], stage, stage != 0)
    require(info['status']['boot_id'] != context['boot_id'], 'fresh boot required')
    expected = context['generation'] + (stage in (0, 10))
    require(counter(info['provisioning_generation'], 'generation') == expected and
            info['provisioning_source'] == 'provisioned' and info['lan_wtp_mode'] == 'engineering-tls', 'exact selected generation/source')
    require(isinstance(exact_payload,bytes) and isinstance(observed_payload,bytes) and
            observed_payload == exact_payload and
            bytes(canonical_profile(strict(exact_payload))) == exact_payload, 'full exact canonical profile readback')
    require(set(before_regions) == {'standalone', 'e10'} and before_regions == after_regions and
            all(isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) for v in before_regions.values()), 'operational/E10 preservation')
    selected = 'C' if stage == 10 else 'B'
    require(set(probes) == {'A', 'B', 'C'}, 'three independent principals')
    require(probes[selected]['outcome'] == 'accepted' and
            probes[selected]['device_id'] == DEVICE and
            probes[selected]['boot_id'] == context.get('tls_boot_id', info['status']['boot_id']), 'actual selected TLS HELLO/STATUS')
    for role in {'A', 'B', 'C'} - {selected}:
        refusal = probes[role]
        require(refusal['outcome'] == 'tls_auth_refused' and refusal['reason'] in REFUSALS and
                refusal['server_sha256'] == probes[selected]['server_sha256'] and
                refusal['address'] == probes[selected]['address'] and
                refusal['hostname'] == probes[selected]['hostname'], 'retired TLS refusal binding')
    evidence.record('journal_selection', stage=stage, generation=expected, selected=selected,
                    profile_sha256=hashlib.sha256(exact_payload).hexdigest(), probes=probes)
    return dict(status='ENGINEERING_JOURNAL_STAGE_ACCEPTED', stage=stage, selected=selected,
                generation=expected, rf_jobs=0)


def tranche(context, stage_image, apply_remote, tls_remote, save, *, clock=time.monotonic, sleeper=time.sleep,
            selection='standard', stage_seed=None):
    """Root-owned parent state machine; callbacks injectable without hardware.

    stage_image(role,candidate) stages exact bytes and sets backend.roles.
    apply_remote/tls_remote take strict dispatch requests; parent restoration stays
    in execute() finally. Snapshot enters ROM, so ordinary redeployment creates a
    separately bound TLS boot; checkpoint fresh-boot evidence is retained first.
    """
    require(selection in ('standard','stimuli'),'explicit journal selection')
    require(selection!='stimuli' or stage_seed is not None,'owned seed staging required')
    backend=context['backend']; root=Path(context['root']); prep=context['preparation']
    candidates={c['role']:c for c in prep['candidates']}
    ordinary=candidates['engineering']; source=prep['source_commit']
    fixture_roles={n:candidates['fault_'+str(n)] for n in (8,9,10)}
    for candidate in (ordinary,*fixture_roles.values()):
        require(candidate['target']=='WsprryPico', 'inhibited image')
    baseline=backend.snapshot('journal-a-before.bin')
    require(baseline['inspection']['profile_source']==1 and baseline['inspection']['bond_count']==1,
            'retained engineering A bond')
    current=baseline; results=[]
    class ParentEvidence:
        def record(self,kind,**value):save(root/('journal-parent-'+kind+'-'+str(len(results))+'.json'),value)
    for stage in (0,8,9,10):
        start=clock()
        def remaining():
            left=300-(clock()-start);require(left>0,'stage budget');return left
        remaining()
        if stage:
            # Predetermined B checkpoint restore before each independent fault.
            current=b_saved
            backend.deploy('engineering',current,'journal-b-restore-'+str(stage)+'.bin',restore=True)
            role='fault_'+str(stage);stage_image(role,fixture_roles[stage])
        else:role='engineering';stage_image(role,ordinary)
        stale_end=None
        if selection=='stimuli' and stage==0:
            # The original300s stage includes cold deployment. One owned
            # suspension holds replies without restarting the UDP process.
            suspension=dict(root=backend.remote,authority=context['authority'],manifest_sha256=context['manifest_sha256'],
                source_commit=source,stage=0,candidate_role='engineering',image_name='engineering.uf2',
                image_sha256=ordinary['uf2']['sha256'],profile_generation=current['inspection']['profile_sequence'],
                action='stale_suspend',journal_selection='stimuli',remaining_s=remaining())
            suspended=apply_remote(suspension);remaining()
            require(suspended['status']=='OWNED_SNTP_SUSPENDED_ONCE','one owned SNTP suspension')
        deployed=backend.deploy(role,current,'journal-deploy-'+str(stage)+'.bin');info=deployed['info']
        remaining()
        safe_info(info,source[:12],stage,False)
        require(info['provisioning_source']=='provisioned' and info['lan_wtp_mode']=='engineering-tls',
                'source1 engineering TLS carrier')
        generation=counter(info['provisioning_generation'],'generation'); boot=info['status']['boot_id']
        payload_role='B' if stage==0 else 'C'; replacement=context['principals'][payload_role]
        request=dict(root=backend.remote,authority=context['authority'],manifest_sha256=context['manifest_sha256'],
            source_commit=source,stage=stage,candidate_role=role,image_name=role+'.uf2',
            image_sha256=candidates[role]['uf2']['sha256'],profile_generation=generation,
            profile_sha256=replacement['profile_sha256'],boot_id=boot,ble_address=context['ble_address'])
        if selection=='stimuli' and stage==0:
            ready=apply_remote(dict(request,action='stale_a_ready',journal_selection='stimuli',remaining_s=remaining()))
            remaining()
            require(ready['status']=='FRESH_A_NO_SNTP_READY','fresh connected unsynchronized A prerequisite')
            from phase12_engineering_journal_stimuli import info_binding
            ready_wire=bytes.fromhex(ready['wire_hex'])
            require(strict(ready_wire)==ready['info'],'actual fresh A original')
            info_binding(ready_wire,source,generation,boot)
            require(ready['info']['status']['clock_state']=='unsynchronized' and
                    ready['info']['network']['accepted']==0,'A has no time before first stale interval')
            # First and only90s interval begins after the cold prefix. It
            # includes capture/hold, the existing apply and B rejection proof.
            stale_end=clock()+min(90,remaining())
            apply_remote(dict(request,action='stale_arm',journal_selection='stimuli',remaining_s=stale_end-clock()))
            require(clock()<stale_end,'original stale interval')
        # No retry after callback exception or uncertain result.
        def apply_remaining():
            left=remaining() if stale_end is None else min(remaining(),stale_end-clock())
            require(left>0,'original stale interval');return left
        if stale_end is not None:
            prepared=apply_remote(dict(request,action='stale_prepare',journal_selection='stimuli',remaining_s=apply_remaining()))
            require(prepared['status']=='STIMULUS_HOLD','captured actual A reply before apply')
            apply_remaining()
            request['journal_selection']='stimuli'
        request['remaining_s']=apply_remaining()
        applied=apply_remote(request)
        apply_remaining()
        require(applied['applies']==applied['confirmations']==1 and applied['rf_jobs']==0,'one bounded apply')
        checkpoint=apply_remote(dict(request,action='observe_checkpoint',remaining_s=apply_remaining()))
        apply_remaining()
        if stale_end is not None:
            require(checkpoint['stale_datagrams']==1 and checkpoint['stale_time_not_adopted'] is True,
                    'one old reply rejected before fresh time release')
        after=checkpoint['info'];checkpoint_wire=bytes.fromhex(checkpoint['wire_hex'])
        require(strict(checkpoint_wire)==after,'actual checkpoint USB wire')
        safe_info(after,source[:12],stage,bool(stage))
        save(root/('journal-checkpoint-'+str(stage)+'.json'),after)
        require(remaining()>60,'snapshot time admission')
        saved=backend.snapshot('journal-after-'+str(stage)+'.bin'); inspection=saved['inspection']
        selected='C' if stage==10 else 'B'; expected=Path(context['principals'][selected]['profile_path']).read_bytes()
        actual=inspection['profile_payload'].encode('ascii')
        raw_after=(root/saved['path']).read_bytes();raw_before=(root/current['path']).read_bytes()
        require(raw_before[0x3f3000:0x3f7000]==raw_after[0x3f3000:0x3f7000],
                'access/bond journals/local BLE keys changed')
        require(inspection['bond_count']==1 and inspection['default_password'] and inspection['profile_healthy'],
                'preserved retained engineering access')
        require(remaining()>60,'TLS redeploy time admission')
        restored=backend.deploy('engineering',saved,'journal-tls-deploy-'+str(stage)+'.bin')['info']
        tls_request=dict(request,action='tls',stage=0,candidate_role='engineering',image_name='engineering.uf2',
            image_sha256=ordinary['uf2']['sha256'],journal_stage=stage,selected=selected,
            boot_id=restored['status']['boot_id'],profile_generation=counter(restored['provisioning_generation'],'gen'),
            hostname=context['hostname'],server_sha256=context['principals'][selected]['server_sha256'],
            selected_profile_sha256=context['principals'][selected]['profile_sha256'],
            principal_hashes=context['principal_hashes'])
        tls_request['remaining_s']=remaining()
        probes=tls_remote(tls_request)['probes']
        require(clock()-start<300,'entire stage ceiling')
        def regions(raw):return dict(standalone=hashlib.sha256(raw[0x3fb000:0x3ff000]).hexdigest(),
                                     e10=hashlib.sha256(raw[0x3ff000:]).hexdigest())
        verify_context=dict(request,generation=generation,tls_boot_id=tls_request['boot_id'])
        result=verify_selection(verify_context,after,checkpoint_wire,expected,actual,
                                regions(raw_before),regions(raw_after),probes,ParentEvidence())
        results.append(result)
        if stage==0:b_saved=saved
    fault=None
    if selection=='stimuli':
        from phase12_engineering_journal_stimuli import corrupt_newest, fault_info, publish
        start=clock()
        def remaining_fault():
            left=300-(clock()-start);require(left>0,'corrupted journal case deadline');return left
        seed,seed_receipt=corrupt_newest(raw_after,expected,inspection['profile_sequence'])
        path=root/'journal-corrupt-newest.bin'
        require(not path.exists() and not path.is_symlink(),'fresh one-byte fault seed')
        with path.open('xb') as stream:
            path.chmod(0o600);stream.write(seed);stream.flush()
            os.fsync(stream.fileno())
        publish(root/'journal-corrupt-seed.json',seed_receipt)
        remaining_fault()
        fault_inspection=backend.inspect(path)
        remaining_fault()
        require(fault_inspection['profile_healthy'] is False and fault_inspection['profile_source']==0 and
                fault_inspection['profile_sequence']==0 and fault_inspection['profile_payload']=='',
                'production native loader faults instead of selecting intact older B')
        unrelated={'access_loaded','access_state','access_sequence','epoch','reset_level','reset_phase',
                   'bond_count','default_password','operational_healthy','config_sequence','cursor_sequence',
                   'watermark','config','effective_station'}
        require(all(fault_inspection[key]==inspection[key] for key in unrelated),
                'native unrelated access/operational selection preserved')
        save(root/'journal-corrupt-native.json',fault_inspection)
        corrupted=dict(path=path.name,sha256=hashlib.sha256(seed).hexdigest(),inspection=fault_inspection)
        remaining_fault();stage_seed(path,path.name);remaining_fault()
        previous_boot=tls_request['boot_id']
        # The existing restoration primitive writes only the declared reserved
        # seed; ordinary deploy intentionally preserves current reserved bytes.
        deployed=backend.deploy('engineering',corrupted,'journal-corrupt-deploy.bin',restore=True)
        remaining_fault()
        fault_info(json.dumps(deployed['info']).encode(),source,previous_boot)
        fault_request=dict(tls_request,action='observe_fault',journal_selection='stimuli',
            boot_id=previous_boot,remaining_s=remaining_fault())
        fault=apply_remote(fault_request);remaining_fault()
        require(fault['fault_samples']==5 and fault['rf_jobs']==0,'five actual guarded fault observations')
        fault_info(bytes.fromhex(fault['wire_hex']),source,previous_boot)
        fault=dict(fault,seed_sha256=corrupted['sha256'],seed_receipt_sha256=hashlib.sha256((root/'journal-corrupt-seed.json').read_bytes()).hexdigest(),
            older_committed_B_intact=True,all_other_seed_bytes_equal=True,
            usb_fault_admission_scope='INFO storage fault plus inactive empty unowned inhibited and absent station/LAN authority; no crypto refusal claim')
        save(root/'journal-corrupt-review-required.json',fault);remaining_fault()
    return dict(status='ENGINEERING_JOURNAL_TRANCHE_ACCEPTED' if selection=='standard' else 'ENGINEERING_JOURNAL_STIMULI_REVIEW_REQUIRED',
                stages=results,corrupted_newest=fault,stale_datagrams=0 if selection=='standard' else 1,rf_jobs=0)
