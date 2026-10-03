#!/usr/bin/env python3
"""One ordinary consumer checkpoint: GET-only HTTP, original INFO, owned time return."""
import hashlib,json,os,re,signal,sys,threading,time
from pathlib import Path
from phase12_consumer_readiness import exercise,bound_info
from phase12_consumer_composition import Evidence
from phase12_engineering_fixture import action as fixture_action,command,management as management_identity
from phase12_engineering_network_dispatch import cleanup_action,parse_interfaces,management
from phase12_populated_dispatch import HTTP,associate_observer
from phase12_consumer_readiness_fixture import action as alias_action
from phase12_engineering_setup import private_bytes
from phase12_fixture_roles import load_roles
from phase12_recovery_device import strict,require
from phase12_serial_observer import Observer
from check_standalone_image import validate_uf2

def run(request):
    require(request['authority']=='USER_AUTHORIZED_UNATTENDED_PHASE12','readiness authority')
    root=Path(request['root']);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and root.is_dir() and not root.is_symlink(),'private readiness root')
    roles=load_roles(root);require(roles['selection'] in ('engineering','swapped') and request['roles_sha256']==roles['sha256'],'independent readiness radios')
    manifest_raw=private_bytes(root/'manifest.json',262144);require(hashlib.sha256(manifest_raw).hexdigest()==request['manifest_sha256'],'readiness manifest')
    manifest=strict(manifest_raw);candidate=next(c for c in manifest['candidates'] if c['role']=='restore')
    image=private_bytes(root/'restore.uf2',4194304);validate_uf2(image)
    require(manifest['source_commit']==request['source_commit'] and candidate['revision']==request['source_commit'][:12] and
            candidate['target']=='WsprryPico' and candidate['fault_stage']==0 and candidate['gp14'] is False and
            candidate['session_deadline_fixture'] is False and candidate['lan_mode']=='plain' and
            hashlib.sha256(image).hexdigest()==candidate['uf2']['sha256'],'ordinary inhibited image binding')
    network_raw=private_bytes(root/'readiness-network.json',2048)
    require(hashlib.sha256(network_raw).hexdigest()==request['network_sha256'],'cold selected network binding')
    network=strict(network_raw);require(network['time_server']==request['time_server'] and request['time_server'] in ('192.168.84.1','192.168.84.254'),'isolated saved time target')
    evidence=Evidence(root/'consumer-readiness-wire.jsonl');observer=Observer();http=HTTP();http.interface=roles['observer']
    before_management=management();before_identity=management_identity();name='p12-observer-'+root.name.rsplit('-',1)[1];ssid='WsprryPico-'+request['suffix']
    deadline=time.monotonic()+300;created=False;fixture_attempted=False;alias_attempted=False
    def info():
        started=time.monotonic_ns();value,raw=observer();ended=time.monotonic_ns()
        require(strict(raw)==value,'original readiness INFO bytes');bound_info(value,request)
        evidence.record('actual_info',monotonic_before_ns=started,raw_hex=raw.hex(),monotonic_after_ns=ended)
        return value
    def public_status():
        started=time.monotonic_ns()
        code,value,wire,raw=http('GET','/api/owner/v1/public-status',None,min(deadline,time.monotonic()+6))
        evidence.record('http_request',raw_hex=wire.hex(),monotonic_before_ns=started)
        evidence.record('http_response',raw_hex=raw.hex(),monotonic_after_ns=time.monotonic_ns())
        require(code==200,'read-only ordinary public response');return value
    def alias(operation):
        return alias_action(dict(root=str(root),authority=request['authority'],roles_sha256=roles['sha256'],action=operation))
    def enable_time():
        nonlocal fixture_attempted,alias_attempted
        fixture_attempted=True
        receipt=fixture_action(dict(root=str(root),authority=request['authority'],action='start_ap',
            interface=roles['host_ap'],proof_mode='target',ssid=network['ssid'],password=network['password'],time_server='192.168.84.1'))
        evidence.record('owned_station_carrier_start',receipt=receipt)
        until=min(deadline,time.monotonic()+130)
        while True:
            require(time.monotonic()<until,'readiness original station association deadline');value=info()
            if value['network']['link_status']==3:
                proof=fixture_action(dict(root=str(root),authority=request['authority'],action='prove_target',phase='warm',
                    source_commit=request['source_commit'],boot_id=value['status']['boot_id'],generation=request['generation'],remaining_s=min(130,until-time.monotonic())))
                require(time.monotonic()<until and proof['status']=='TARGET_ASSOCIATION_VERIFIED' and proof['station_ipv4']==value['network']['ipv4'],'original same checkpoint station association')
                evidence.record('target_station_association',proof=proof);break
            time.sleep(.5)
        fixture_action(dict(root=str(root),authority=request['authority'],action='bind_peer',address=value['network']['ipv4']))
        if request['time_server']=='192.168.84.254':
            alias_attempted=True;evidence.record('owned_saved_time_responder',receipt=alias('start'))
            evidence.record('owned_time_enabled',receipt=alias('enable'))
        else:evidence.record('owned_time_enabled',receipt=fixture_action(dict(root=str(root),authority=request['authority'],action='sntp_on')))
    cleanup_errors=[]
    try:
        require(parse_interfaces(before_management[0]).get(roles['observer'],{}).get('state')=='disconnected' and
                name not in command('nmcli','-t','-f','NAME','connection','show').splitlines(),'unused independent observer')
        owned=root/'populated-observer-owned.json';require(not owned.exists(),'new observer ownership')
        owned.write_text(json.dumps(dict(name=name)));owned.chmod(0o600);created=True
        command('sudo','-n','nmcli','connection','add','type','wifi','ifname',roles['observer'],'con-name',name,'ssid',ssid,
            'connection.autoconnect','no','ipv4.method','manual','ipv4.addresses','192.168.4.3/24','ipv4.never-default','yes','ipv6.method','disabled')
        associate_observer(name,ssid,min(deadline,time.monotonic()+110),evidence,interface=roles['observer'])
        require(management()[1]==before_management[1] and management_identity()==before_identity,'management default routes/identities unchanged')
        result=exercise(request,info,public_status,enable_time,evidence,deadline=deadline)
        private=root/'consumer-readiness-result.json';private.write_text(json.dumps(result)+'\n');private.chmod(0o600)
        return dict(status=result['status'],case=request['case'],generation=result['generation'],boot_id=result['boot_id'],
                    public_ready_observed=result['public_ready_observed'],submit_attempts=0,rf_jobs=0)
    finally:
        primary=sys.exc_info()[1]
        for label,callback in (('alias',lambda:alias('stop') if alias_attempted else None),
                ('observer',lambda:cleanup_action(root) if created else None),
                ('station_fixture',lambda:fixture_action(dict(root=str(root),authority=request['authority'],action='finish')) if fixture_attempted else None)):
            try:callback()
            except BaseException as error:
                cleanup_errors.append(dict(scope=label,error_type=type(error).__name__))
        try:
            require(management()[1]==before_management[1] and management_identity()==before_identity,'management changed after readiness cleanup')
            evidence.record('readiness_host_cleanup',errors=cleanup_errors,management_routes_unchanged=True)
        except BaseException as error:cleanup_errors.append(dict(scope='management_or_recording',error_type=type(error).__name__))
        finally:
            try:evidence.close()
            except BaseException as error:cleanup_errors.append(dict(scope='evidence_close',error_type=type(error).__name__))
        if cleanup_errors:
            if primary is not None:primary.add_note('Readiness cleanup failed: '+json.dumps(cleanup_errors))
            else:raise ValueError('readiness owned host cleanup failed: '+json.dumps(cleanup_errors))

def main():
    os.umask(0o077);request=strict(sys.stdin.buffer.readline(65537))
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt('parent lost')))
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('readiness case deadline')));signal.alarm(330)
    def watch():
        if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=watch,daemon=True).start()
    print(json.dumps(run(request)),flush=True)
if __name__=='__main__':main()
