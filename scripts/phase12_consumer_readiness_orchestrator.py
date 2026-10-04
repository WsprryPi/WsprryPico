#!/usr/bin/env python3
"""One <=900 s inhibited B warm continuation from an accepted cold save."""
import argparse,copy,hashlib,json,os,signal,subprocess,time,uuid
from pathlib import Path
from phase12_candidate_manifest import read_json,verify
from phase12_consumer_flash_status_orchestrator import STAGED_HELPERS as SHARED_HELPERS
from phase12_consumer_readiness import CASES
from phase12_engineering_orchestrator import RemoteAdapters,tranche_deadline
from phase12_fixture_roles import role_map
from phase12_populated_fixture import canonical,private_read,write,command,public_der,p256,expiry
from phase12_recovery_device import strict,verify_image
from phase12_recovery_orchestrator import Backend,Ledger,private_write,safe_info,sha,require,DEVICE,SIZE,RESERVED
from phase12_engineering_fixture import ntp_reply

STAGED_HELPERS=SHARED_HELPERS+('phase12_consumer_readiness.py','phase12_consumer_readiness_dispatch.py','phase12_consumer_readiness_fixture.py')
BODY_SECONDS=340
TOTAL_SECONDS=900

def stage_network(root,remote,network):
    """Bind one saved network to both real dispatcher/owned-AP input names."""
    path=Path(root)/'readiness-network.json'
    require(not path.exists() and not path.is_symlink(),'fresh readiness network staging')
    private_write(path,network);expected=sha(path)
    inputs={name:remote.stage(path,name) for name in ('readiness-network.json','populated-network.json')}
    require(all(value==expected for value in inputs.values()),'identical staged readiness/owned-AP network')
    private_write(Path(root)/'readiness-network-inputs.json',inputs)
    return inputs

def accepted_checkpoint(path,case,inspector):
    require(case in CASES,'named readiness case')
    raw=private_read(path,SIZE);require(len(raw)==SIZE,'exact accepted cold flash')
    loaded=strict(command([inspector,path]));profile=strict(loaded['profile_payload'])
    original_case='station' if case=='pending-tls' else case
    receipt=read_json(path.parent/('populated-'+original_case+'-result.json'))
    row=receipt['cases'][0]
    require(receipt['status']=='POPULATED_SAVES_REVIEW_REQUIRED' and len(receipt['cases'])==1 and
            row['case']==original_case and row['submit_attempts']==1 and
            loaded['profile_sequence']==row['generation'] and profile['request_sha256']==row['request_digest'],
            'original accepted save checkpoint binding')
    require(loaded['profile_healthy'] and loaded['operational_healthy'] and loaded['access_state']==2 and
            loaded['profile_source']==5 and loaded['config'] and loaded['config']['enabled'] is False and
            profile['device_id']==DEVICE and not profile.get('tls_pending',False) and len(profile['clients'])==2 and
            profile['network']['time_server']==('192.168.84.254' if original_case=='network' else '192.168.84.1'),
            'accepted complete-TLS inactive checkpoint')
    return dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),inspection=loaded,original_case=original_case,
                original_result_sha256=sha(path.parent/('populated-'+original_case+'-result.json')))

def prepare_pending(checkpoint,output,inspector,native):
    output.mkdir(mode=0o700)
    loaded=checkpoint['inspection'];old=strict(loaded['profile_payload']);profile=dict(version=2,tls_pending=True)
    profile.update({key:copy.deepcopy(value) for key,value in old.items() if key!='version'})
    profile['request_sha256']=hashlib.sha256(b'phase12-explicit-pending-fixture/1\0'+bytes.fromhex(checkpoint['sha256'])).hexdigest()
    require(profile['request_sha256']!=old['request_sha256'],'distinct pending fixture request binding')
    profile['clients']=[]
    for key in ('ca_certificate','ca_private_key','server_certificate','server_private_key'):profile['tls'][key]=''
    profile['tls']['ca_not_after_utc']='0';profile['tls']['server_not_after_utc']='0'
    profile_path=output/'pending-profile.json';config_path=output/'retained-config.json';path=output/'pending.bin'
    write(profile_path,canonical(profile));write(config_path,canonical(loaded['config']))
    command([native,'--backup',checkpoint['path'],'--consumer-profile',profile_path,'--config',config_path,
             '--watermark',str(loaded['watermark']),'--output',path,'--allow-tls-pending','yes'])
    after=strict(command([inspector,path]));selected=strict(after['profile_payload'])
    before=private_read(checkpoint['path'],SIZE);raw=private_read(path,SIZE)
    require(after['profile_healthy'] and after['operational_healthy'] and selected==profile and
            after['profile_sequence']==loaded['profile_sequence']+1 and after['config']==loaded['config'] and
            after['watermark']==loaded['watermark'] and raw[:0x3f7000]==before[:0x3f7000] and
            raw[0x3fb000:]==before[0x3fb000:],'offline production pending-TLS seed and exact unrelated regions')
    return dict(path=path,sha256=sha(path),inspection=after)

def validate_tls(profile,root,openssl='openssl'):
    tls=profile['tls'];directory=root/'materialized-tls';directory.mkdir(mode=0o700)
    for cert_field,key_field,label in (('ca_certificate','ca_private_key','ca'),('server_certificate','server_private_key','server')):
        cert=directory/(label+'.crt');key=directory/(label+'.key')
        write(cert,tls[cert_field].encode());write(key,tls[key_field].encode())
        public=public_der(openssl,certificate=cert);p256(public)
        require(public==public_der(openssl,key=key),'materialized key/certificate binding')
        subject=command([openssl,'x509','-in',cert,'-noout','-subject','-issuer','-nameopt','RFC2253']).decode()
        require(subject.count('OU='+DEVICE)==2,'materialized exact device OU')
        require(expiry(openssl,cert)==int(tls['ca_not_after_utc' if label=='ca' else 'server_not_after_utc']),
                'materialized certificate expiry binding')
    command([openssl,'verify','-CAfile',directory/'ca.crt','-purpose','sslserver','-verify_hostname',tls['hostname'],directory/'server.crt'])
    return dict(status='NATIVE_MATERIALIZED_TLS_VALIDATED',hostname=tls['hostname'],clients=len(profile['clients']))

def assess(case,seed,after,seed_bytes,after_bytes,result,root):
    require(len(seed_bytes)==len(after_bytes)==SIZE and seed_bytes[RESERVED:0x3f7000]==after_bytes[RESERVED:0x3f7000] and
            seed_bytes[0x3fb000:]==after_bytes[0x3fb000:],'readiness changed access/BLE/operational/E10')
    old=strict(seed['inspection']['profile_payload']);new=strict(after['inspection']['profile_payload'])
    pending=case=='pending-tls';generation=seed['inspection']['profile_sequence']+int(pending)
    require(after['inspection']['profile_healthy'] and after['inspection']['operational_healthy'] and
            after['inspection']['profile_sequence']==generation and result['generation']==generation and
            result['submit_attempts']==0 and result['rf_jobs']==0,'one materialization or unchanged selected generation')
    if pending:
        require(old.get('tls_pending') is True and not new.get('tls_pending',False) and new['version']==1,
                'pending TLS not materialized')
        for key in ('device_id','network','station','owners','owner_epoch','clients','request_sha256'):
            require(new[key]==old[key],'materialization changed unrelated consumer authority: '+key)
        tls=validate_tls(new,root)
    else:
        require(new==old and seed_bytes[RESERVED:]==after_bytes[RESERVED:],'complete-TLS readiness changed cold profile/trust')
        tls=validate_tls(new,root)
    return dict(status='COLD_READINESS_PRESERVATION_PASS',generation=generation,materialization=pending,
                existing_client_trust_preserved=not pending,public_ready_observed=result['public_ready_observed'],tls=tls,
                scope='cold profile/time/INFO readiness; no consumer engineering TLS admission',submit_attempts=0,rf_jobs=0)

def time_evidence(case,root,result):
    peer=read_json(root/'ntp-peer.json')['address']
    require(all(sample['network']['ipv4']==peer for sample in result['samples']),'same original SNTP peer and target INFO')
    if case=='network':
        path=root/'readiness-time-wire.jsonl';rows=[strict(line) for line in private_read(path,2097152).splitlines()]
        require(bool(rows),'original .254 time query/reply evidence missing')
        for row in rows:
            require(row['peer_address']==peer and row['monotonic_before_ns']<=row['monotonic_after_ns'] and
                    ntp_reply(bytes.fromhex(row['query_hex']),row['utc_ns'])==bytes.fromhex(row['reply_hex']),
                    'original bounded peer .254 time query/reply bytes')
        require(read_json(root/'readiness-alias-cleanup.json')['status']=='OWNED_ALIAS_REMOVED','owned .254 alias cleanup proof')
    else:
        path=root/'ntp-metrics.json';metrics=read_json(path)
        reply=bytes.fromhex(metrics['last_response_hex'])
        require(metrics['requests']>=metrics['replies']>0 and len(metrics['last_request_sha256'])==64 and
                len(reply)==48 and reply[0]==0x24 and reply[1]==1 and reply[24:32]!=bytes(8) and
                reply[32:40]==reply[40:48] and reply[40:48]!=bytes(8),'original .1 enabled responder packet evidence')
        require(read_json(root/'ntp-stopped.json')['replies']>0,'original .1 responder cleanup proof')
    return dict(status='ORIGINAL_TIME_RESPONDER_EVIDENCE_BOUND',peer=peer,evidence_sha256=sha(path),
        query_scope='raw query/reply' if case=='network' else 'original query hash and raw reply')

class BoundedBackend(Backend):
    def call(self,action,*,transport_timeout=270,**args):
        maximum=80 if action=='snapshot' else 220 if action in ('restore','deploy') else 60 if action=='reboot_original' else 6
        return super().call(action,transport_timeout=min(transport_timeout,maximum,self.deadline-time.monotonic()),**args)

def execute(manifest,artifacts,root,inspector,native,checkpoint_path,case,*,backend_factory=BoundedBackend,
            remote_factory=RemoteAdapters,clock=time.monotonic,fixture_roles='engineering'):
    require(fixture_roles=='engineering','readiness target AP proof requires engineering radio roles')
    checkpoint=accepted_checkpoint(Path(checkpoint_path),case,inspector)
    identity=uuid.uuid4().hex;roles=role_map(fixture_roles,identity)
    root=Path(root);require(not root.exists(),'fresh readiness campaign');root.mkdir(mode=0o700,parents=True)
    started=clock();backend=backend_factory(dict(campaign_id=identity,interface='wlan2'),manifest,artifacts,root,inspector)
    backend.deadline=time.monotonic()+TOTAL_SECONDS-75 # Reserve bounded Backend.cleanup and lease release.
    remote=remote_factory(root);remote.backend=backend;ledger=Ledger(root/'ledger.jsonl')
    baseline=None;restoration=None;primary=None;host_cleanup=[];staged=False;body=None
    binding=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    private_write(root/'campaign-config.json',dict(campaign_id=identity,manifest_sha256=binding,source_commit=manifest['source_commit'],
        max_seconds=TOTAL_SECONDS,max_body_seconds=BODY_SECONDS,case=case,checkpoint_sha256=checkpoint['sha256'],
        checkpoint_result_sha256=checkpoint['original_result_sha256'],valid_saves=0,rf_jobs=0,fixture_roles=roles))
    def event(kind,**args):
        try:ledger.record(kind,**args)
        except BaseException as error:host_cleanup.append(dict(scope='ledger:'+kind,error_type=type(error).__name__))
    try:
        with tranche_deadline(BODY_SECONDS):
            safe_info(backend.setup(),manifest['source_commit'][:12],0,False)
            baseline=backend.snapshot('baseline.bin')
            private_write(root/'baseline-receipt.json',dict(path='baseline.bin',sha256=baseline['sha256'],manifest_sha256=binding))
            private_write(root/'manifest.json',manifest);private_write(root/'fixture-roles.json',roles)
            inputs={name:remote.stage(Path(__file__).parent/name,name) for name in STAGED_HELPERS}
            for name in ('manifest.json','fixture-roles.json'):inputs[name]=remote.stage(root/name,name)
            private_write(root/'observer-inputs.json',inputs);staged=True
            seed=prepare_pending(checkpoint,root/'pending-fixture',inspector,native) if case=='pending-tls' else checkpoint
            profile=strict(seed['inspection']['profile_payload']);network=profile['network']
            inputs.update(stage_network(root,remote,network))
            remote.stage(seed['path'],'checkpoint.bin');saved=dict(path='checkpoint.bin',sha256=seed['sha256'],inspection=seed['inspection'])
            deployed=backend.restore(saved,'checkpoint-deployment.bin');private_write(root/'checkpoint-deployment.json',deployed)
            request=dict(root=backend.remote,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',roles_sha256=roles['sha256'],
                manifest_sha256=sha(root/'manifest.json'),network_sha256=inputs['readiness-network.json'],
                populated_network_sha256=inputs['populated-network.json'],source_commit=manifest['source_commit'],
                case=case,generation=seed['inspection']['profile_sequence'],boot_id=deployed['info']['status']['boot_id'],
                station=profile['station'],time_server=network['time_server'],suffix=deployed['info']['local_suffix'])
            body=remote.invoke('phase12_consumer_readiness_dispatch.py',request,timeout=min(330,BODY_SECONDS-(clock()-started)),keepalive=True)
            require(body['status']=='CONSUMER_READINESS_REVIEW_REQUIRED' and body['submit_attempts']==0 and body['rf_jobs']==0,'finite GET-only continuation')
            names=('consumer-readiness-wire.jsonl','consumer-readiness-result.json','readiness-time-wire.jsonl','ntp-metrics.json',
                   'ntp-ready.json','ntp-pid.json','ntp-peer.json','ntp-stopped.json','readiness-alias-ready.json','readiness-alias-cleanup.json')
            remote.collect(names)
            result=read_json(root/'consumer-readiness-result.json')
            time_proof=time_evidence(case,root,result)
            observed=backend.snapshot('after-readiness.bin')
            evaluation=assess(case,seed,observed,private_read(seed['path'],SIZE),private_read(root/observed['path'],SIZE),result,root)
            evaluation['time_evidence']=time_proof
            private_write(root/'readiness-assessment.json',evaluation);event('consumer_readiness_complete',assessment=evaluation)
    except BaseException as error:primary=dict(type=type(error).__name__,message=str(error));event('campaign_failed',error=primary)
    finally:
        try:
            with tranche_deadline(max(.001,backend.deadline-time.monotonic())):
                if staged and (primary is not None or body is None):
                    for script,action,timeout in (('phase12_consumer_readiness_fixture.py','stop',35),('phase12_engineering_fixture.py','finish',45)):
                        try:remote.invoke(script,dict(root=backend.remote,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',roles_sha256=roles['sha256'],action=action),timeout=timeout)
                        except BaseException as error:host_cleanup.append(dict(scope=script,error_type=type(error).__name__))
                if baseline:
                    restoration=backend.restore(baseline,'final-restoration.bin')
                    remote.collect(('final-restoration.bin',));raw=private_read(root/'final-restoration.bin',SIZE)
                    require(hashlib.sha256(raw).hexdigest()==restoration['readback']['sha256'] and
                            raw[RESERVED:]==private_read(root/'baseline.bin',SIZE)[RESERVED:],'independent final reserved/E10 copy')
                    role=next(c for c in manifest['candidates'] if c['role']=='restore');verify_image(raw,(Path(artifacts)/role['uf2']['path']).read_bytes())
                    restoration['stability']=backend.stable_restore(baseline,'final-stable-info.json')
                    event('final_restoration_pass',readback=restoration['readback'],stability=restoration['stability'])
        except BaseException as error:
            restoration=dict(error_type=type(error).__name__,message=str(error));event('final_restoration_failed',restoration=restoration)
        try:backend.cleanup()
        except BaseException as error:host_cleanup.append(dict(scope='backend',error_type=type(error).__name__))
    passed=primary is None and restoration and 'error_type' not in restoration and not host_cleanup and clock()-started<TOTAL_SECONDS
    result=dict(status='CONSUMER_READINESS_COMPLETE_REVIEW_REQUIRED' if passed else 'STOPPED',error=primary,restoration=restoration,
        cleanup_errors=host_cleanup,case=case,source_commit=manifest['source_commit'],submit_attempts=0,rf_jobs=0,elapsed_s=clock()-started)
    private_write(root/'result.json',result);return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','artifact-root','campaign','inspector','native','checkpoint'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',choices=CASES,required=True);parser.add_argument('--fixture-roles',choices=('engineering',),default='engineering')
    parser.add_argument('--run',action='store_true');args=parser.parse_args();manifest=read_json(args.manifest);verify(manifest,args.artifact_root)
    checkpoint=accepted_checkpoint(args.checkpoint,args.case,args.inspector)
    if not args.run:print(json.dumps(dict(status='VALIDATED_NO_DEVICE_ACTION',case=args.case,generation=checkpoint['inspection']['profile_sequence'],max_seconds=TOTAL_SECONDS,submit_attempts=0,rf_jobs=0)));return
    os.umask(0o077);signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt('parent interrupted')))
    result=execute(manifest,args.artifact_root,args.campaign,args.inspector,args.native,args.checkpoint,args.case,fixture_roles=args.fixture_roles)
    print(json.dumps(dict(status=result['status'],case=args.case,rf_jobs=0)));raise SystemExit(0 if result['status']=='CONSUMER_READINESS_COMPLETE_REVIEW_REQUIRED' else 1)
if __name__=='__main__':main()
