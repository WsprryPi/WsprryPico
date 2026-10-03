#!/usr/bin/env python3
"""Actual-wire ordinary inhibited B consumer trace dispatcher, one save only."""
import hashlib,json,os,re,signal,socket,sys,time,subprocess
from pathlib import Path
from phase12_consumer_flash_status import measure
from phase12_consumer_busy_claim import exercise,WITHDRAW_SECONDS
from phase12_engineering_flash_status_dispatch import RawConsole,WireChannel
from phase12_populated_dispatch import HTTP,associate_observer
from phase12_fixture_roles import load_roles
from phase12_engineering_network_dispatch import management,cleanup_action,parse_interfaces
from phase12_engineering_fixture import action as fixture_action,command,management as identity
from phase12_consumer_composition import Evidence
from phase12_engineering_setup import private_bytes
from phase12_recovery_device import DEVICE,strict,require,resource_health
from phase12_composition_audit import counter
from check_standalone_image import validate_uf2


def bounded_command(argv,deadline,evidence,*,clock=time.monotonic,runner=subprocess.run,limit=3):
    require(clock()<deadline,'carrier command deadline')
    try:result=runner(argv,capture_output=True,timeout=min(limit,deadline-clock()))
    except subprocess.TimeoutExpired as error:
        evidence.record('carrier_command_timeout',argv=argv,stdout_hex=(error.stdout or b'')[:32768].hex(),stderr_hex=(error.stderr or b'')[:32768].hex());raise
    require(len(result.stdout)<=32768 and len(result.stderr)<=32768,'carrier output bound')
    evidence.record('carrier_command',argv=argv,returncode=result.returncode,stdout_hex=result.stdout.hex(),stderr_hex=result.stderr.hex())
    require(clock()<deadline and result.returncode==0,'complete bounded carrier command')
    return result.stdout


def associate_guarded(name,ssid,deadline,evidence,before,routes,interface='wlan0',single_channel=False,before_activation=None):
    associate_observer(name,ssid,deadline,evidence,interface=interface,**({'before_activation':before_activation} if before_activation is not None else {}),**({'single_channel':True} if single_channel else {}))
    def read(*argv):return bounded_command(list(argv),deadline,evidence).decode()
    actual_routes=bounded_command(['ip','-4','route','show','default'],deadline,evidence)
    require(identity(read=read)==before and actual_routes==routes,'management unchanged after actual AP association')
    require(time.monotonic()<deadline,'late guarded association')


def run(request):
    require(request['authority']=='USER_AUTHORIZED_UNATTENDED_PHASE12','authority');root=Path(request['root']);roles=load_roles(root);require(request.get('roles_sha256',roles['sha256'] if roles['selection']=='engineering' else None)==roles['sha256'],'radio roles binding')
    require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and root.is_dir() and not root.is_symlink(),'private root')
    manifest_raw=private_bytes(root/'manifest.json',262144);require(hashlib.sha256(manifest_raw).hexdigest()==request['manifest_sha256'],'manifest binding');manifest=strict(manifest_raw)
    c=next(c for c in manifest['candidates'] if c['role']=='restore');image=private_bytes(root/'consumer_trace.uf2',4194304);validate_uf2(image)
    require(manifest['source_commit']==request['source_commit'] and c['revision']==request['source_commit'][:12] and c['target']=='WsprryPico' and c['gp14'] is False and c['fault_stage']==0 and c['session_deadline_fixture'] is False and c['lan_mode']=='plain' and hashlib.sha256(image).hexdigest()==c['uf2']['sha256'],'ordinary exact image/source')
    case=request.get('busy_state');require(case in (None,'loaded','armed','running'),'named case');label='consumer-busy-'+case if case else 'consumer-flash-status';evidence=Evidence(root/(label+'-wire.jsonl'));con=RawConsole(evidence);end=time.monotonic()+(100 if case else 240);before=identity();routes=management()[1];stream=None;peer=None;created=False
    evidence.record('fixture_radio_roles',roles=roles)
    name='p12-observer-'+root.name.rsplit('-',1)[1];ssid='WsprryPico-'+request['suffix'];require(re.fullmatch('WsprryPico-[0-9a-f]{6}',ssid),'exact AP suffix')
    def observe(deadline):
        v,raw=con('INFO',deadline);resource_health(v);require(strict(raw)==v,'actual original INFO bytes');require(v['firmware']=='0.0.0-devel' and 'phase12_fault_stage' not in v and v['access_state']=='healthy' and v['status']['storage_healthy'] is True and v['status']['engine']=='inhibited-standalone-simulator' and v['status']['enabled'] is False and counter(v['softap_session_inactivity_ms'],'ordinary inactivity')==900000 and counter(v['softap_session_absolute_ms'],'ordinary absolute')==43200000 and not v.get('bootstrap_reset_pending',False),'ordinary healthy inhibited consumer');require(v['device_id']==DEVICE and v['revision']==request['source_commit'][:12] and v['status']['boot_id']==request['boot_id'],'same ordinary B')
        return v,raw
    def exchange(op,body,deadline):
        nonlocal stream,peer
        ready_end=min(deadline,time.monotonic()+15)
        while True:
            info=observe(deadline)[0]
            if info['lan_wtp_ready']:break
            require(time.monotonic()<ready_end,'fresh station WTP readiness');time.sleep(.1)
        require(info['lan_wtp_ready'] and info['network']['ipv4']==request['station_ipv4'] and info['network']['ipv4'].startswith('192.168.84.') and info['network']['ntp_server']=='192.168.84.1' and info['network']['ntp_address']=='192.168.84.1' and counter(info['network']['accepted'],'SNTP')>0,'isolated synchronized Plain LAN')
        # An owner trial tears down station TCP. Establish a new read-only peer
        # only when the target has selected the committed generation.
        generation=counter(info['provisioning_generation'],'generation')
        if peer is None or peer.selected_generation!=generation:
            if stream is not None:stream.close()
            stream=socket.socket(socket.AF_INET,socket.SOCK_STREAM);stream.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,roles['host_ap'].encode()+b'\0');stream.bind(('192.168.84.1',0));stream.settimeout(min(5,deadline-time.monotonic()));stream.connect((info['network']['ipv4'],31417))
            def send(raw,d):stream.settimeout(max(.001,d-time.monotonic()));stream.sendall(raw)
            def recv(d):stream.settimeout(max(.001,d-time.monotonic()));return stream.recv(65552)
            peer=WireChannel(send,recv,evidence,'plain_lan');peer.ready(request['boot_id'],deadline);peer.selected_generation=generation
        return peer.wire_exchange(op,body,deadline)
    def status(deadline):return exchange('STATUS',{},deadline)
    def http(method,path,body,deadline):
        client=HTTP();client.interface=roles['observer'];intended=client.wire(method,path,body)
        evidence.record('http_attempt',method=method,path=path,intended_request_hex=intended.hex(),source_interface=roles['observer'],source_address='192.168.4.3',transmission_verified=False)
        try:code,value,wire,raw=client(method,path,body,min(deadline,time.monotonic()+10))
        except (OSError,TimeoutError) as error:
            evidence.record('http_socket_failure',method=method,path=path,error_type=type(error).__name__,transmission_verified=False);raise
        evidence.record('http_request',raw_hex=wire.hex());evidence.record('http_response',raw_hex=raw.hex());return code,value,wire,raw
    def scan(deadline):
        return bounded_command(['sudo','-n','/usr/sbin/iw','dev',roles['observer'],'scan','freq',*(['2422'] if roles['selection']=='concurrent' else ['2412','2422'])],deadline,evidence,limit=5)
    def associate(deadline,before_activation=None):associate_guarded(name,ssid,deadline,evidence,before,routes,interface=roles['observer'],single_channel=True,before_activation=before_activation)
    def withdraw(deadline):
        # Completed active scan plus actual disassociation; timeout alone is insufficient.
        until=min(deadline,time.monotonic()+WITHDRAW_SECONDS)
        while True:
            raw=scan(until);link=bounded_command(['/usr/sbin/iw','dev',roles['observer'],'link'],until,evidence).decode()
            evidence.record('busy_ap_link',link=link)
            if ssid.encode() not in re.findall(rb'(?m)^\s*SSID: (.*)$',raw) and 'Not connected.' in link:return dict(scan_hex=raw.hex(),link=link,target_ssid=ssid)
            require(time.monotonic()<until,'AP carrier was not withdrawn');time.sleep(.1)
    try:
        require(parse_interfaces(management()[0]).get(roles['observer'],{}).get('state')=='disconnected','unused observer interface')
        require(name not in command('nmcli','-t','-f','NAME','connection','show').splitlines(),'unused observer')
        receipt=root/'populated-observer-owned.json';receipt.write_text(json.dumps(dict(name=name)));receipt.chmod(0o600);created=True
        command('sudo','-n','nmcli','connection','add','type','wifi','ifname',roles['observer'],'con-name',name,'ssid',ssid,'connection.autoconnect','no','ipv4.method','manual','ipv4.addresses','192.168.4.3/24','ipv4.never-default','yes','ipv6.method','disabled','802-11-wireless.band','bg','802-11-wireless.channel','3')
        initial_budget=request['initial_join_seconds'];require(type(initial_budget) in (int,float) and 0<initial_budget<=30,'bounded remaining initial association')
        initial_end=min(end,time.monotonic()+initial_budget)
        info_started=time.monotonic()
        ready,raw=observe(initial_end);evidence.record('preassociation_info',raw_hex=raw.hex(),decoded=ready)
        require(ready['network']['link_status']!=3,'actual station loss before AP proof')
        require(time.monotonic()<initial_end and counter(ready['provisioning_generation'],'initial generation')==request['generation'] and ready['provisioning_source']=='consumer_preclock','initial generation/source/deadline')
        observed_ns=counter(ready['status']['monotonic_now_ns'],'initial monotonic')
        require(observed_ns>=counter(request['fallback_monotonic_ns'],'original fallback monotonic'),'sameboot initial monotonic progression')
        remaining_ns=counter(request['initial_target_deadline_ns'],'target AP proof deadline')-observed_ns
        require(remaining_ns>0,'initial target proof deadline exhausted')
        initial_end=min(initial_end,info_started+remaining_ns/1_000_000_000)
        early_return=request.get('station_up_after_beacon',False)
        require(type(early_return) is bool,'explicit station-return ordering')
        returned=None;station_return_attempted=False
        def return_station(deadline):
            nonlocal returned,station_return_attempted
            require(not station_return_attempted,'one station return only')
            reserve=60 if case else 120
            available=min(deadline,end-reserve)-time.monotonic()
            require(available>0,'remaining station return budget')
            station_return_attempted=True
            fixture_action(dict(root=str(root),authority=request['authority'],action='station_ap_up',remaining_s=min(10,available)))
            require(time.monotonic()<deadline and end-time.monotonic()>=reserve,'late station return')
            returned=time.monotonic()
            evidence.record('station_return_order',before_host_activation=early_return,offline_HTTP_qualified=False)
        associate(initial_end,before_activation=return_station if early_return else None)
        code,public,_,_=http('GET','/api/owner/v1/public-status',None,initial_end)
        require(time.monotonic()<initial_end and code==200 and public['device_id']==DEVICE and public['boot_id']==request['boot_id'] and public['profile_source']==5 and counter(public['generation'],'AP proof generation')==request['generation'] and public['claim_available'] is True,'actual ordinary sameboot AP claim readiness')
        if not early_return:return_station(end)
        def retained_associate(deadline):
            require(time.monotonic()<returned+30,'postrelease fallback retention deadline')
            associate(min(deadline,returned+30))
        require(identity()==before and management()[1]==routes,'management unchanged')
        result=exercise(request,observe,http,exchange,withdraw,retained_associate,deadline=end) if case else measure(request,request['station'],observe,con,http,status)
        if case:result['status']='CONSUMER_BUSY_CLAIM_REVIEW_REQUIRED'
        result['image_sha256']=c['uf2']['sha256'];result['source_commit']=manifest['source_commit'];result['device_id']=DEVICE
        path=root/(label+'-result.json');path.write_text(json.dumps(result)+'\n');path.chmod(0o600);return dict(status=result['status'],status_samples=0 if case else 20,submit_attempts=0 if case else 1,simulator_jobs=1 if case else 0,rf_jobs=0)
    finally:
        if stream is not None:stream.close()
        try:
            if created:cleanup_action(root)
        finally:
            require(identity()==before and management()[1]==routes,'management unchanged after observer cleanup');evidence.close()

if __name__=='__main__':
    os.umask(0o077);signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(KeyboardInterrupt('parent lost')));signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('case deadline')));signal.alarm(280)
    print(json.dumps(run(strict(sys.stdin.buffer.readline(65537)))),flush=True)
