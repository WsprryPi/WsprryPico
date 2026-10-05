#!/usr/bin/env python3
"""Private wspr5-only isolated engineering AP and finite UTC responder.

The campaign parent owns B exclusion and exact restoration. This adapter never
controls a Pico, changes a host clock, or changes the management connections.
"""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import signal
import socket
import struct
import subprocess
import sys
import time
import traceback


def strict(raw):
    def pairs(values):
        result={}
        for key,value in values:
            require(key not in result,'duplicate JSON member');result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda value:(_ for _ in ()).throw(ValueError(value)))

ADDRESS='192.168.84.1'
INTERFACE='wlan2'
OBSERVER='wlan0'
from phase12_fixture_roles import load_roles,preflight
AP_CHANNEL=3
AP_FREQUENCY_MHZ=2422
SERVER_DURATION_S=18000


def require(ok,message):
    if not ok:raise ValueError(message)


def private_write(path,value):
    temporary=path.with_suffix('.temporary')
    with temporary.open('w') as file:
        os.chmod(temporary,0o600);json.dump(value,file);file.write('\n');file.flush();os.fsync(file.fileno())
    temporary.replace(path)
    if os.geteuid()==0:
        user=pwd.getpwnam('pi');os.chown(path,user.pw_uid,user.pw_gid)


def command(*args):
    return subprocess.run(list(args),capture_output=True,text=True,check=True,timeout=40).stdout


def management(read=None):
    read=command if read is None else read
    # Only management identities/default routes are compared; the owned AP gets its
    # own local subnet and shared NAT without becoming a default route.
    addresses=[]
    for device in ('eth0','wlan1'):
        for link in strict(read('ip','-j','address','show','dev',device)):
            addresses.append(dict(ifname=link['ifname'],address=link.get('address'),
                operstate=link.get('operstate'),addresses=[
                    {k:a[k] for k in ('family','local','prefixlen','scope') if k in a}
                    for a in link.get('addr_info',[])]))
    defaults=[]
    for family in ('-4','-6'):
        defaults.extend([dict(family=family,route={k:v for k,v in route.items() if k!='expires'})
            for route in strict(read('ip',family,'-j','route','show','default'))])
    return dict(addresses=addresses,defaults=defaults)


def ntp_reply(query,utc_ns):
    require(len(query)==48 and query[0]&7==3 and (query[0]>>3)&7 in (3,4) and
            query[40:48]!=bytes(8),'supported NTP request')
    require(type(utc_ns) is int and 0<=utc_ns<(4_294_967_296-2_208_988_800)*1_000_000_000,'NTP era-zero UTC')
    seconds,nanoseconds=divmod(utc_ns,1_000_000_000)
    stamp=struct.pack('>II',seconds+2_208_988_800,(nanoseconds<<32)//1_000_000_000)
    reply=bytearray(48);reply[0]=0x24;reply[1]=1;reply[2]=6;reply[3]=236
    reply[8:12]=struct.pack('>I',66);reply[12:16]=b'LOCL'
    reply[16:24]=stamp;reply[24:32]=query[40:48];reply[32:40]=stamp;reply[40:48]=stamp
    return bytes(reply)


def fresh_ntp_files(root):
    for name in ('ntp-enabled.json','ntp-ready.json','ntp-pid.json','ntp-stopped.json',
                 'ntp-metrics.json','ntp-peer.json','ntp-server.log'):
        require(not (root/name).exists() and not (root/name).is_symlink(),'existing NTP fixture evidence; no restart')


def peer_allowed(root,peer):
    address=ipaddress.IPv4Address(peer[0])
    if address not in ipaddress.IPv4Network(ADDRESS+'/24',strict=False):return False
    path=root/'ntp-peer.json'
    return path.exists() and strict(path.read_bytes())['address']==str(address)


def serve(root,startup_token):
    global INTERFACE,OBSERVER
    roles=load_roles(root);INTERFACE=roles['host_ap'];OBSERVER=roles.get('beacon_observer',roles['observer'])
    require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and
            root.is_dir() and not root.is_symlink(),'server private root')
    stop=False
    def stopped(*_):
        nonlocal stop;stop=True
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGINT,stopped)
    start=time.monotonic();count=0;replies=0
    require(re.fullmatch('[0-9a-f]{32}',startup_token),'server startup token')
    private_write(root/'ntp-pid.json',dict(pid=os.getpid(),root=str(root),duration_s=SERVER_DURATION_S,startup_token=startup_token,roles_sha256=roles['sha256']))
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as server:
        # The retained chrony service listens on the wildcard address. Linux
        # selects this more specific owned address/interface for fixture queries;
        # reuse its port without stopping or reconfiguring that service.
        server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        server.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,INTERFACE.encode()+b'\0')
        server.bind((ADDRESS,123));server.settimeout(1)
        private_write(root/'ntp-ready.json',dict(address=ADDRESS,port=123,enabled=False,pid=os.getpid(),startup_token=startup_token,roles_sha256=roles['sha256']))
        while not stop and time.monotonic()-start<SERVER_DURATION_S and count<2000:
            try:query,peer=server.recvfrom(512)
            except socket.timeout:continue
            if not peer_allowed(root,peer):continue
            count+=1
            if not (root/'ntp-enabled.json').exists():continue
            utc_ns=time.time_ns()
            try:reply=ntp_reply(query,utc_ns)
            except ValueError:continue
            if (root/'journal-stale-arm.json').exists():
                from phase12_engineering_journal_stimuli import respond
                selected=respond(root,query,peer,reply,server.sendto,utc_ns=utc_ns)
                if selected!='normal':continue
            server.sendto(reply,peer);replies+=1
            private_write(root/'ntp-metrics.json',dict(requests=count,replies=replies,
                last_request_sha256=hashlib.sha256(query).hexdigest(),last_response_hex=reply.hex()))
    private_write(root/'ntp-stopped.json',dict(requests=count,replies=replies))


def verify_disabled_ntp(root,roles,*,process_root=Path('/proc')):
    require(not (root/'ntp-enabled.json').exists() and not (root/'ntp-stopped.json').exists(),'original responder must remain disabled and live')
    pid=strict((root/'ntp-pid.json').read_bytes());ready=strict((root/'ntp-ready.json').read_bytes())
    require(pid['root']==str(root) and pid['duration_s']==SERVER_DURATION_S and type(pid['pid']) is int and pid['pid']>1 and
            ready['pid']==pid['pid'] and ready['startup_token']==pid['startup_token'] and ready['enabled'] is False and
            ready['address']==ADDRESS and ready['port']==123 and pid['roles_sha256']==roles['sha256'] and ready['roles_sha256']==roles['sha256'],'original disabled responder receipts')
    args=(process_root/str(pid['pid'])/'cmdline').read_bytes().split(b'\0')
    require(b'--serve-ntp' in args and str(root).encode() in args and str(Path(__file__).resolve()).encode() in args and pid['startup_token'].encode() in args,'original responder live process identity')
    bound=root/'ntp-preserved.json'
    identity=dict(pid=pid,ready=ready,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if bound.exists():require(strict(bound.read_bytes())==identity,'preserved original responder changed')
    else:private_write(bound,identity)
    return identity


def verify_warmed_ntp(root,roles,*,process_root=Path('/proc')):
    pid=strict((root/'ntp-pid.json').read_bytes());ready=strict((root/'ntp-ready.json').read_bytes())
    enabled=root/'ntp-enabled.json'
    require(enabled.is_file() and not enabled.is_symlink(),'warmed responder enabled')
    require(type(pid['pid']) is int and pid['pid']>1 and pid['root']==str(root) and ready['pid']==pid['pid'] and
            ready['startup_token']==pid['startup_token'] and pid['roles_sha256']==roles['sha256'] and
            ready['roles_sha256']==roles['sha256'] and ready['address']==ADDRESS and ready['port']==123,'warmed responder receipt identity')
    args=(process_root/str(pid['pid'])/'cmdline').read_bytes().split(b'\0')
    require(b'--serve-ntp' in args and str(root).encode() in args and str(Path(__file__).resolve()).encode() in args and pid['startup_token'].encode() in args,'warmed responder live identity')
    return dict(pid=pid,ready=ready,enabled_sha256=hashlib.sha256(enabled.read_bytes()).hexdigest(),cmdline_sha256=hashlib.sha256(b'\0'.join(args)).hexdigest())

def stop_ntp(root):
    (root/'ntp-enabled.json').unlink(missing_ok=True)
    receipt=root/'ntp-pid.json'
    if not receipt.exists():return
    value=strict(receipt.read_bytes());require(value['root']==str(root),'server root binding')
    pid=value['pid'];require(type(pid) is int and pid>1,'server PID')
    process=Path('/proc')/str(pid)
    if not process.exists():return
    args=(process/'cmdline').read_bytes().split(b'\0')
    require(b'--serve-ntp' in args and str(root).encode() in args and
            str(Path(__file__).resolve()).encode() in args,'server process identity changed')
    command('sudo','-n','kill','-TERM',str(pid))
    deadline=time.monotonic()+5
    while process.exists() and time.monotonic()<deadline:time.sleep(.1)
    require(not process.exists() or (root/'ntp-stopped.json').exists(),'server stop unconfirmed')


def discovery_selection(devices,name,expected_address=None):
    from wsprrypico_ble import UUIDS,normalize_address
    service=lambda v:UUIDS['service'] in [str(u).lower() for u in v.get('UUIDs',[])]
    named=[v for v in devices if str(v.get('Name',''))==name and service(v)]
    if expected_address is None:return named
    require(normalize_address(expected_address)=='88:A2:9E:0A:9D:8A' and name=='WsprryPico-0a9d89','explicit verified B discovery address/name')
    require(all(normalize_address(str(v.get('Address','')))==expected_address for v in named),'distinct named address ambiguity')
    selected=[v for v in devices if str(v.get('Address','')).upper()==expected_address and service(v)]
    require(len(selected)<=1,'duplicate bound address ambiguity')
    require(all(str(v.get('AddressType',''))=='public' for v in selected),'bound public address required')
    return selected


def discover(name, root=None, expected_address=None):
    from wsprrypico_ble import BluezBackend,UUIDS,normalize_address
    if expected_address is not None:
        expected_address=normalize_address(expected_address)
        require(expected_address=='88:A2:9E:0A:9D:8A' and name=='WsprryPico-0a9d89','explicit verified B discovery address/name')
    backend=BluezBackend('hci0');objects=backend._objects()
    require(backend.adapter_path in objects,'adapter missing')
    adapter=backend.dbus.Interface(backend.bus.get_object(backend.BLUEZ,backend.adapter_path),backend.ADAPTER)
    diagnostic=None;record_count=0;primary=None;discovery_attempted=False
    if root is not None:
        target=Path(root)/'ble-discovery-original.jsonl'
        diagnostic=target.open('x');os.chmod(target,0o600)
    def retain(kind,**value):
        nonlocal record_count
        if diagnostic is None:return
        try:
            record_count+=1
            require(record_count<=128,'bounded discovery diagnostics')
            raw=json.dumps(dict(kind=kind,monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns(),**value),sort_keys=True)+'\n'
            require(len(raw)<=32768,'bounded discovery diagnostic row')
            diagnostic.write(raw);diagnostic.flush();os.fsync(diagnostic.fileno())
        except BaseException:pass # Diagnostics never replace an original discovery failure.
    try:
        adapter.SetDiscoveryFilter({'Transport':backend.dbus.String('le'),
            'UUIDs':backend.dbus.Array([backend.dbus.String(UUIDS['service'])],signature='s')})
        discovery_attempted=True
        adapter.StartDiscovery();deadline=time.monotonic()+15
        retain('discovery_started',expected_name=name,expected_address=expected_address,selection_mode='bound_public_address' if expected_address is not None else 'legacy_name',fresh_advertisement_proven=False)
        matches=[]
        while time.monotonic()<deadline:
            backend.pump(.2)
            devices=[dict(v[backend.DEVICE]) for p,v in backend._objects().items()
                     if p.startswith(backend.adapter_path+'/') and backend.DEVICE in v]
            matches=discovery_selection(devices,name,expected_address)
            candidates=[dict(address=str(v.get('Address','')),name_matches=str(v.get('Name',''))==name,
                name_present=bool(v.get('Name')),actual_name=str(v.get('Name','')),address_type=str(v.get('AddressType','')),object_provenance='cached_BlueZ_Device1_not_fresh_advertisement',service_matches=UUIDS['service'] in [str(u).lower() for u in v.get('UUIDs',[])],
                paired=bool(v.get('Paired',False)),connected=bool(v.get('Connected',False)))
                for v in devices if str(v.get('Name',''))==name or UUIDS['service'] in [str(u).lower() for u in v.get('UUIDs',[])]]
            retain('original_objects',device_count=len(devices),matching_count=len(matches),candidate_count=len(candidates),
                   candidates=candidates[:32],candidates_truncated=len(candidates)>32)
            if len(matches)==1:
                require(time.monotonic()<deadline,'fresh named BLE discovery deadline')
                break
        require(len(matches)==1,'fresh named BLE candidate not unique')
        result=dict(address=normalize_address(str(matches[0]['Address'])),matching_names=int(str(matches[0].get('Name',''))==name),matching_bound_addresses=1 if expected_address is not None else None,actual_name=str(matches[0].get('Name','')),selection_mode='bound_public_address' if expected_address is not None else 'legacy_name',fresh_advertisement_proven=False)
        retain('discovery_candidate',**result)
    except BaseException as error:
        primary=error;retain('discovery_failed',error_type=type(error).__name__);raise
    finally:
        try:
            try:
                if discovery_attempted:adapter.StopDiscovery();retain('discovery_stopped')
            except BaseException as error:
                retain('discovery_stop_failed',error_type=type(error).__name__)
                if primary is None:primary=error;raise
        finally:
            if diagnostic is not None:
                try:diagnostic.close()
                except BaseException:
                    if primary is None:raise
    require(time.monotonic()<deadline,'fresh named BLE discovery deadline')
    return result


def wait_owned_beacon(root,ssid,before,*,alternate_scans=False,clock=time.monotonic,sleeper=time.sleep):
    """Independent active frequency scans on the unused observer; never join B."""
    target=root/'owned-ap-beacon-readiness.json'
    require(not target.exists(),'owned beacon receipt already exists')
    receipt=dict(schema='phase12-owned-ap-beacon/1',observer_interface=OBSERVER,ap_interface=INTERFACE,
                 max_seconds=45,max_scans=4,max_scan_seconds=15,scan_schedule_seconds=[0,10,20,30],
                 commands=[],status='STARTED',scan_mode='narrow-wide-narrow-wide' if alternate_scans else 'narrow-only')
    private_write(target,receipt);started=clock();deadline=started+45
    def actual(argv,maximum=10):
        require(clock()<deadline,'owned beacon readiness deadline')
        try:result=subprocess.run(argv,capture_output=True,timeout=min(maximum,deadline-clock()))
        except subprocess.TimeoutExpired as error:
            receipt['commands'].append(dict(argv=argv,status='TIMEOUT',stdout_hex=(error.stdout or b'').hex(),
                                            stderr_hex=(error.stderr or b'').hex()))
            private_write(target,receipt);raise
        require(len(result.stdout)<=262144 and len(result.stderr)<=16384,'bounded beacon raw output')
        receipt['commands'].append(dict(argv=argv,returncode=result.returncode,
                                       stdout_hex=result.stdout.hex(),stderr_hex=result.stderr.hex()))
        private_write(target,receipt);return result
    def unused():
        state=actual(['nmcli','-g','GENERAL.STATE','device','show',OBSERVER])
        require(state.returncode==0 and state.stdout.strip().startswith(b'30 '),'independent beacon observer must be unused')
        link=actual(['sudo','-n','/usr/sbin/iw','dev',OBSERVER,'link'])
        require(link.returncode==0 and link.stdout.strip()==b'Not connected.','beacon observer must remain disconnected')
        def bounded_management(*args):
            result=actual(list(args))
            require(result.returncode==0,'bounded management observation failed')
            return result.stdout.decode()
        require(management(read=bounded_management)==before,'management changed during independent beacon readiness')
    def legal_broad_frequencies():
        require(OBSERVER=='wlan0','alternating beacon observer must remain wlan0')
        info=actual(['sudo','-n','/usr/sbin/iw','dev',OBSERVER,'info'],5)
        require(info.returncode==0 and re.findall(rb'(?m)^\s*wiphy (\d+)\s*$',info.stdout)==[b'1'] and
                re.findall(rb'(?m)^\s*Interface (\S+)\s*$',info.stdout)==[OBSERVER.encode()],
                'actual unused beacon observer must be PHY1')
        capabilities=actual(['sudo','-n','/usr/sbin/iw','phy','phy1','info'],5)
        require(capabilities.returncode==0,'actual live PHY1 legality required')
        frequencies=[]
        for channel in range(1,12):
            marker=b'['+str(channel).encode()+b']'
            lines=[line for line in capabilities.stdout.splitlines() if marker in line]
            frequency=str(2407+channel*5).encode()
            field=re.fullmatch(rb'\s*\*\s+'+frequency+rb'(?:\.0+)?\s+MHz\s+\['+str(channel).encode()+rb'\](.*)',lines[0]) if len(lines)==1 and capabilities.stdout.count(marker)==1 else None
            require(field is not None and not any(flag in field[1].lower() for flag in (b'disabled',b'no ir',b'no-ir',b'radar')),
                    'declared broad frequency lacks unique active legality')
            frequencies.append(frequency.decode())
        return frequencies

    try:
        unused()
        info=actual(['sudo','-n','/usr/sbin/iw','dev',INTERFACE,'info'])
        require(info.returncode==0,'owned AP info unavailable')
        bssid=re.search(rb'(?m)^\s*addr ([0-9a-f:]{17})\s*$',info.stdout)
        frequency=re.search(rb'channel '+str(AP_CHANNEL).encode()+rb' \(('+str(AP_FREQUENCY_MHZ).encode()+rb') MHz\)',info.stdout)
        names=re.findall(rb'(?m)^\s*ssid (.*)$',info.stdout)
        require(bssid and frequency and names==[ssid.encode()] and re.search(rb'(?m)^\s*type AP\s*$',info.stdout),
                'actual owned AP SSID/BSSID/channel identity')
        receipt.update(ssid=ssid,bssid=bssid[1].decode(),frequency_mhz=int(frequency[1]))
        for index in range(4):
            unused()
            require(clock()<deadline,'owned beacon readiness deadline')
            frequencies=legal_broad_frequencies() if alternate_scans and index in (1,3) else [frequency[1].decode()]
            try:scan=actual(['sudo','-n','/usr/sbin/iw','dev',OBSERVER,'scan','freq',*frequencies],15)
            except subprocess.TimeoutExpired:continue
            require(clock()<deadline,'owned beacon scan exceeded whole deadline')
            if scan.returncode==0:
                matches=[]
                for block in re.split(rb'(?m)^BSS ',scan.stdout)[1:]:
                    address=re.match(rb'([0-9a-f:]{17})',block)
                    frequencies=re.findall(rb'(?m)^\s*freq:(.*)$',block)
                    if (address and address[1]==bssid[1] and
                        re.findall(rb'(?m)^\s*SSID: (.*)$',block)==[ssid.encode()] and
                        len(frequencies)==1 and
                        re.fullmatch(rb'\s*'+frequency[1]+rb'(?:\.0+)?\s*',frequencies[0])):
                        authentication=re.findall(rb'(?m)^\s*\* Authentication suites: (.*)$',block)
                        require(re.search(rb'(?m)^\s*RSN:',block) and
                            re.findall(rb'(?m)^\s*\* Group cipher: (.*)$',block)==[b'CCMP'] and
                            re.findall(rb'(?m)^\s*\* Pairwise ciphers: (.*)$',block)==[b'CCMP'] and
                            not re.search(rb'(?m)^\s*WPA:',block) and
                            len(authentication)==1 and b'PSK' in authentication[0].split(),
                            'owned beacon must advertise WPA2 PSK CCMP only')
                        receipt['authentication_suites']=authentication[0].decode().split()
                        matches.append(address[1])
                require(len(matches)<=1,'owned beacon identity ambiguous')
                if matches:
                    unused();require(clock()<deadline,'owned beacon final observation exceeded readiness deadline')
                    receipt.update(status='INDEPENDENT_BEACON_READY',scan_attempts=index+1)
                    private_write(target,receipt);return receipt
            if index<3:
                sleeper(min(max(0,started+(index+1)*10-clock()),max(0,deadline-clock())))
        raise TimeoutError('bounded independent owned AP beacon not observed')
    except Exception as error:
        receipt.update(status='INDEPENDENT_BEACON_FAILED',error_type=type(error).__name__,error_message=str(error))
        private_write(target,receipt);raise


def inspect_owned_ap(root,phase):
    """Read-only observations of the exact campaign AP; retain failed guards too."""
    require(phase in ('start','failure','success'),'finite AP inspection phase')
    name='p12-engineering-'+root.name.rsplit('-',1)[1]
    target=root/('populated-seed-'+phase+'-ap-inspection.json')
    require(not target.exists(),'AP inspection receipt already exists')
    receipt=dict(schema='phase12-owned-ap-inspection/1',read_only=True,interface=INTERFACE,
                 expected_connection=name,phase=phase,commands=[],status='STARTED')
    private_write(target,receipt)
    def actual(argv):
        try:
            result=subprocess.run(argv,capture_output=True,timeout=10)
        except subprocess.TimeoutExpired as error:
            receipt['commands'].append(dict(argv=argv,status='TIMEOUT',stdout_hex=(error.stdout or b'').hex(),
                                            stderr_hex=(error.stderr or b'').hex()))
            private_write(target,receipt);raise
        require(len(result.stdout)<=262144 and len(result.stderr)<=16384,'bounded AP inspection output')
        receipt['commands'].append(dict(argv=argv,returncode=result.returncode,
                                       stdout_hex=result.stdout.hex(),stderr_hex=result.stderr.hex()))
        private_write(target,receipt)
        require(result.returncode==0,'owned AP read-only command failed; inspect private receipt')
        return result.stdout.decode()
    try:
        saved=root/'fixture-management-before.json'
        require(saved.is_file() and not saved.is_symlink(),'owned fixture management receipt required')
        before=management();receipt['management_before']=before
        require(before==strict(saved.read_bytes()),'management changed before AP inspection')
        active=actual(['nmcli','-g','GENERAL.CONNECTION','device','show',INTERFACE]).strip()
        require(active==name,'AP inspection refuses unrelated or inactive connection')
        config=actual(['nmcli','-g','connection.interface-name,802-11-wireless.mode,802-11-wireless.channel',
                      'connection','show',name]).splitlines()
        require(config==[INTERFACE,'ap',str(AP_CHANNEL)],'owned AP mode/interface mismatch')
        actual(['sudo','-n','/usr/sbin/iw','dev',INTERFACE,'info'])
        actual(['sudo','-n','/usr/sbin/iw','dev',INTERFACE,'station','dump'])
        actual(['ip','-j','address','show','dev',INTERFACE])
        receipt['management_after']=management()
        require(receipt['management_after']==before,'management changed during AP inspection')
        receipt['status']='READ_ONLY_INSPECTION_COMPLETE'
        private_write(target,receipt);return receipt
    except Exception as error:
        receipt['status']='READ_ONLY_INSPECTION_FAILED';receipt['error_type']=type(error).__name__
        receipt['error_message']=str(error);private_write(target,receipt);raise


def owned_ap_configuration(root,roles,read):
    name='p12-engineering-'+root.name.rsplit('-',1)[1]
    require(roles['host_ap']=='wlan2','target receiver proof is scoped to owned wlan2 AP')
    network=strict((root/'populated-network.json').read_bytes())
    require(read('nmcli','-g','GENERAL.CONNECTION','device','show','wlan2').strip()==name,'actual owned AP connection')
    values=read('nmcli','-g','802-11-wireless.ssid,802-11-wireless.mode,802-11-wireless.channel,802-11-wireless-security.key-mgmt,802-11-wireless-security.proto,802-11-wireless-security.pairwise,802-11-wireless-security.group','connection','show',name).splitlines()
    require(values==[network['ssid'],'ap','3','wpa-psk','rsn','ccmp','ccmp'],'actual owned SSID/AP/channel/RSN/CCMP configuration')
    raw=read('sudo','-n','/usr/sbin/iw','dev','wlan2','info')
    addresses=re.findall(r'(?m)^\s*addr ([0-9a-f:]{17})\s*$',raw)
    require(len(addresses)==1 and re.findall(r'(?m)^\s*ssid (.*)$',raw)==[network['ssid']] and
            re.findall(r'(?m)^\s*type (\S+)\s*$',raw)==['AP'] and
            len(re.findall(r'\bchannel\s',raw))==1 and re.search(r'channel 3 \(2422(?:\.0+)? MHz\)',raw),'actual AP radio identity')
    return dict(connection=name,ssid=network['ssid'],bssid=addresses[0],interface='wlan2',frequency_mhz=2422,roles_sha256=roles['sha256'])


def target_association_proof(root,roles,request,*,observe=None,runner=None,clock=time.monotonic):
    from phase12_serial_observer import Observer
    from phase12_recovery_device import DEVICE,resource_health
    from phase12_composition_audit import counter
    observe=Observer() if observe is None else observe;runner=subprocess.run if runner is None else runner
    require(request['phase'] in ('seed','warm','station','network'),'finite target proof phase')
    mode=strict((root/'fixture-ap-proof.json').read_bytes())
    require(mode['mode']=='target' and mode['roles_sha256']==roles['sha256'],'target AP proof mode binding')
    manifest=strict((root/'manifest.json').read_bytes());require(manifest['source_commit']==request['source_commit'] and re.fullmatch('[0-9a-f]{40}',request['source_commit']) and re.fullmatch('[0-9a-f]{32}',request['boot_id']) and type(request['generation']) is int and request['generation']>=0,'target source/boot/generation request')
    remaining=request['remaining_s'];require(type(remaining) in (int,float) and 0<remaining<=160,'original target association budget')
    end=clock()+min(30,remaining);receipt=dict(schema='phase12-target-ap-proof/1',phase=request['phase'],status='STARTED',roles_sha256=roles['sha256'],commands=[],usb_info=[])
    target=root/('target-ap-proof-'+request['phase']+'.json');require(not target.exists(),'target proof never repeated')
    private_write(target,receipt)
    def read(*argv):
        require(clock()<end,'target AP proof deadline')
        row=runner(list(argv),capture_output=True,text=True,timeout=min(5,end-clock()))
        receipt['commands'].append(dict(argv=list(argv),returncode=row.returncode,stdout=row.stdout[:262144],stderr=row.stderr[:16384]));private_write(target,receipt)
        require(len(row.stdout)<=262144 and len(row.stderr)<=16384 and row.returncode==0 and clock()<end,'actual bounded target proof command')
        return row.stdout
    def info():
        require(clock()<end,'target proof INFO deadline');value,raw=observe()
        receipt['usb_info'].append(dict(raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()));private_write(target,receipt)
        require(strict(raw)==value and clock()<end,'original bounded target INFO');resource_health(value)
        status=value['status'];ip=ipaddress.IPv4Address(value['network']['ipv4'])
        require(value['device_id']==DEVICE and value['revision']==request['source_commit'][:12] and status['boot_id']==request['boot_id'] and
                counter(value['provisioning_generation'],'target profile generation')==request['generation'] and value['provisioning_source']=='consumer_preclock' and
                status['engine']=='inhibited-standalone-simulator' and status['enabled'] is False and status['output_active'] is False and status['state']=='empty' and
                not status.get('owner_id') and not status.get('job_id') and status['storage_healthy'] is True and value['access_state']=='healthy' and
                value['network']['link_status']==3 and value['network']['station_mac']=='88:a2:9e:0a:9d:89' and
                ip in ipaddress.IPv4Network('192.168.84.0/24') and str(ip) not in ('192.168.84.0',ADDRESS,'192.168.84.255'),'exact original target USB association')
        require(value['saved_consumer_profile']['network']['ssid']==mode['ap']['ssid'] and not value.get('bootstrap_reset_pending',False),'target saved SSID binding')
        if request['phase'] in ('seed','warm'):require(status['clock_state']=='unsynchronized','target proof precedes accepted time')
        return value,str(ip)
    try:
        before=strict((root/'fixture-management-before.json').read_bytes());require(management(read=read)==before,'target proof management before')
        first,ip=info();ap=owned_ap_configuration(root,roles,read);require(ap==mode['ap'],'target AP identity changed')
        station=read('sudo','-n','/usr/sbin/iw','dev','wlan2','station','get','88:a2:9e:0a:9d:89')
        require(re.findall(r'(?m)^Station ([0-9a-f:]{17}) \(on wlan2\)',station)==['88:a2:9e:0a:9d:89'] and
                re.findall(r'(?m)^\s*authenticated:\s*(\S+)\s*$',station)==['yes'] and
                re.findall(r'(?m)^\s*authorized:\s*(\S+)\s*$',station)==['yes'],'exact actual authenticated authorized target station')
        links=strict(read('ip','-j','address','show','dev','wlan2'))
        require(len(links)==1 and links[0]['ifname']=='wlan2' and any(a.get('family')=='inet' and a.get('local')==ADDRESS and a.get('prefixlen')==24 for a in links[0].get('addr_info',[])),'actual AP interface address')
        # A device-filtered ip route query suppresses its dev field. Read all
        # original routes so the selected connected route binds its interface.
        routes=strict(read('ip','-4','-j','route','show'))
        require(sum(r.get('dst')=='192.168.84.0/24' and r.get('dev')=='wlan2' and r.get('prefsrc')==ADDRESS for r in routes)==1,'actual target DHCP subnet route')
        leases=read('sudo','-n','cat','/var/lib/NetworkManager/dnsmasq-wlan2.leases')
        matches=[line.split() for line in leases.splitlines() if len(line.split())==5 and line.split()[1]=='88:a2:9e:0a:9d:89']
        require(len(matches)==1 and matches[0][2]==ip and matches[0][0].isdigit() and (int(matches[0][0])==0 or int(matches[0][0])>time.time()),'original DHCP current exact target MAC/IP lease')
        last,last_ip=info();require(last_ip==ip and last['status']['boot_id']==first['status']['boot_id'],'same target proof bookend')
        require(management(read=read)==before and clock()<end,'target proof management after/deadline')
        receipt.update(status='TARGET_ASSOCIATION_VERIFIED',device_id=DEVICE,boot_id=request['boot_id'],generation=request['generation'],source_commit=request['source_commit'],station_mac='88:a2:9e:0a:9d:89',station_ipv4=ip,ap=ap)
        private_write(target,receipt);return {k:receipt[k] for k in ('status','device_id','boot_id','generation','source_commit','station_mac','station_ipv4','ap')}
    except BaseException as error:
        receipt.update(status='TARGET_ASSOCIATION_FAILED',error_type=type(error).__name__);private_write(target,receipt);raise


def action(request):
    global INTERFACE,OBSERVER
    roles=load_roles(request['root'])
    old=(INTERFACE,OBSERVER);INTERFACE=roles['host_ap'];OBSERVER=roles.get('beacon_observer',roles['observer'])
    try:return _action(request,roles)
    finally:INTERFACE,OBSERVER=old


def _action(request,roles):
    require(request['authority']=='USER_AUTHORIZED_UNATTENDED_PHASE12','authority')
    root=Path(request['root']);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root))
        and root.is_dir() and not root.is_symlink(),'private root')
    name='p12-engineering-'+root.name.rsplit('-',1)[1]
    operation=request['action']
    if roles['selection']=='concurrent':require(root.name.rsplit('-',1)[1]==roles['campaign_id'],'concurrent root role binding')
    if operation.startswith('journal_stale_'):
        from phase12_engineering_journal_stimuli import arm,control,publish,original
        require(roles['selection']=='engineering','journal stimulus exact owned engineering fixture')
        if operation=='journal_stale_suspend':
            require(re.fullmatch('[0-9a-f]{40}',request['source_commit']) and
                    type(request['generation']) is int and 0<request['generation']<2**64-1,
                    'exact suspension source/generation')
            identity=verify_warmed_ntp(root,roles)
            require(not (root/'journal-stale-arm.json').exists(),'suspend only before one fresh interval')
            publish(root/'journal-stale-suspend.json',dict(schema='phase12-journal-suspension/1',root=str(root),
                source_commit=request['source_commit'],generation=request['generation'],
                warmed_identity=identity,monotonic_s=time.monotonic(),rf_jobs=0))
            # Consume the immutable attempt before the only owned suspension.
            (root/'ntp-enabled.json').unlink()
            disabled=verify_disabled_ntp(root,roles)
            require(disabled['pid']==identity['pid'] and disabled['ready']==identity['ready'],'same original responder after suspension')
            return dict(status='OWNED_SNTP_SUSPENDED_ONCE',rf_jobs=0)
        if operation in ('journal_stale_arm','journal_stale_old_bind'):
            verify_disabled_ntp(root,roles)
            suspended=strict(original(root/'journal-stale-suspend.json'))
            require(suspended['schema']=='phase12-journal-suspension/1' and suspended['root']==str(root) and
                    suspended['rf_jobs']==0,'original one-use suspension')
            if operation=='journal_stale_arm':
                require(suspended['source_commit']==request['source_commit'] and suspended['generation']==request['generation'],
                        'same suspended A source/generation')
        else:verify_warmed_ntp(root,roles)
        if operation=='journal_stale_arm':
            return arm(root,request['source_commit'],request['generation'],request['remaining_s'])
        controls={'journal_stale_old_bind':'old_bind','journal_stale_hold':'hold',
                  'journal_stale_new_bind':'new_bind','journal_stale_release':'release'}
        require(operation in controls,'named journal stimulus action')
        return control(root,controls[operation],bytes.fromhex(request['info_raw_hex']))
    if operation=='prove_target':return target_association_proof(root,roles,request)
    if operation in ('station_ap_down','station_ap_up'):
        saved=root/'fixture-management-before.json'
        require(saved.is_file() and not saved.is_symlink(),'original owned management required')
        warmed=verify_warmed_ntp(root,roles)
        before=strict(saved.read_bytes());require(management()==before,'management identity before station toggle')
        config=command('nmcli','-g','connection.interface-name,802-11-wireless.mode','connection','show',name).splitlines()
        require(config==[INTERFACE,'ap'],'exact owned station AP profile')
        limit=request.get('remaining_s',10)
        require(type(limit) in (int,float) and 0<limit<=10,'bounded owned station toggle')
        result=subprocess.run(['sudo','-n','nmcli','--wait',str(max(1,int(limit)-1)),'connection','down' if operation=='station_ap_down' else 'up',name],capture_output=True,timeout=limit)
        require(result.returncode==0,'owned station toggle failed')
        require(management()==before,'management changed by owned station toggle')
        require(verify_warmed_ntp(root,roles)==warmed,'warmed responder changed during station toggle')
        return dict(status='OWNED_STATION_AP_DOWN' if operation=='station_ap_down' else 'OWNED_STATION_AP_UP',interface=INTERFACE,connection=name,ntp_process_preserved=True)
    if operation=='inspect_ap':return inspect_owned_ap(root,request['phase'])
    if operation=='restart_ap_offline':
        # Single campaign restart after the initial owned AP/responder cleanup.
        # Keep the original management receipt; never launch another responder.
        saved=root/'fixture-management-before.json'
        require(saved.exists() and not saved.is_symlink(),'original fixture receipt required')
        before=strict(saved.read_bytes());require(management()==before,'management changed before owned restart')
        if request.get('preserve_disabled_ntp') is True:
            verify_disabled_ntp(root,roles)
        else:
            require((root/'ntp-stopped.json').exists() and not (root/'ntp-enabled.json').exists(),
                    'original responder must be stopped and disabled')
            stop_ntp(root)
        network_path=root/'populated-network.json'
        require(network_path.is_file() and not network_path.is_symlink(),'private populated network required')
        network=strict(network_path.read_bytes());ssid,password=network['ssid'],network['password']
        require(re.fullmatch('p12-[0-9a-f]{12}',ssid) and re.fullmatch('[0-9a-f]{32}',password), 'owned private credentials')
        require('30 (disconnected)' in command('nmcli','-t','-f','GENERAL.STATE','device','show',INTERFACE),
                'owned AP adapter must be unused')
        require(name not in command('nmcli','-t','-f','NAME','connection','show').splitlines(),
                'owned restart connection already exists')
        command('sudo','-n','nmcli','connection','add','type','wifi','ifname',INTERFACE,'con-name',name,'ssid',ssid,
            '802-11-wireless.mode','ap','802-11-wireless.band','bg','802-11-wireless.channel',str(AP_CHANNEL),
            'wifi-sec.key-mgmt','wpa-psk','wifi-sec.proto','rsn',
            'wifi-sec.pairwise','ccmp','wifi-sec.group','ccmp','wifi-sec.psk',password,
            'connection.autoconnect','no','ipv4.method','shared','ipv4.addresses',ADDRESS+'/24',
            'ipv4.never-default','yes','ipv6.method','disabled')
        command('sudo','-n','nmcli','connection','up',name)
        require(management()==before,'management changed by owned restart')
        if request.get('preserve_disabled_ntp') is True:verify_disabled_ntp(root,roles)
        return dict(status='OWNED_AP_RESTARTED_NO_SNTP',interface=INTERFACE,connection=name,ntp_started=False,roles_sha256=roles['sha256'])
    if operation=='start_ap':
        require(request.get('proof_mode','beacon') in ('beacon','target'),'finite AP proof mode')
        if request.get('proof_mode')=='target':require(roles['host_ap']=='wlan2','target receiver AP role must be wlan2')
        if (root/'fixture-roles.json').exists():
            require(not (root/'fixture-roles-bound.json').exists(),'fixture radio roles already bound; no repeat')
            private_write(root/'fixture-roles-bound.json',roles)
        require(request.get('interface',INTERFACE)==INTERFACE,'AP request radio roles mismatch')
        if roles['selection'] in ('swapped','concurrent'):
            before_roles=management()
            end=time.monotonic()+90;observations=[]
            def capability_read(*argv):
                remaining=end-time.monotonic();require(remaining>0,'radio preflight deadline')
                try:row=subprocess.run(list(argv),capture_output=True,text=True,timeout=min(5,remaining))
                except subprocess.TimeoutExpired as error:
                    observations.append(dict(argv=list(argv),timeout=True));raise
                observations.append(dict(argv=list(argv),returncode=row.returncode,stdout=row.stdout[:262144],stderr=row.stderr[:16384]))
                require(len(row.stdout)<=262144 and len(row.stderr)<=16384,'radio preflight output bound')
                require(row.returncode==0,'radio preflight command failed')
                return row.stdout
            try:receipt=preflight(roles,capability_read)
            except BaseException as error:
                private_write(root/'fixture-radio-preflight.json',dict(status='RADIO_PREFLIGHT_FAILED',roles_sha256=roles['sha256'],error_type=type(error).__name__,message=str(error),commands=observations))
                raise
            require(management()==before_roles,'management changed during radio preflight')
            private_write(root/'fixture-radio-preflight.json',receipt)
            if roles['selection']=='concurrent':
                from phase12_virtual_observer import create
                create(root,roles,receipt['virtual'],capability_read,capability_read,private_write,deadline=end)
        fresh_ntp_files(root)
        before=management();private_write(root/'fixture-management-before.json',before)
        ssid,password=request['ssid'],request['password']
        require(re.fullmatch('p12-[0-9a-f]{12}',ssid) and re.fullmatch('[0-9a-f]{32}',password),'private AP credentials')
        state=command('nmcli','-t','-f','GENERAL.STATE','device','show',INTERFACE)
        if '30 (disconnected)' not in state:
            companion='p12-recovery-'+root.name.rsplit('-',1)[1]
            active=command('nmcli','-g','GENERAL.CONNECTION','device','show',INTERFACE).strip()
            require(active==companion,'spare adapter owned by another connection')
            command('sudo','-n','nmcli','connection','down',companion)
            state=command('nmcli','-t','-f','GENERAL.STATE','device','show',INTERFACE)
        require('30 (disconnected)' in state,'spare adapter not idle')
        existing=command('nmcli','-t','-f','NAME','connection','show').splitlines()
        require(name not in existing,'fixture exists; never repeat start')
        command('sudo','-n','nmcli','connection','add','type','wifi','ifname',INTERFACE,'con-name',name,'ssid',ssid,
            '802-11-wireless.mode','ap','802-11-wireless.band','bg','802-11-wireless.channel',str(AP_CHANNEL),
            'wifi-sec.key-mgmt','wpa-psk','wifi-sec.proto','rsn',
            'wifi-sec.pairwise','ccmp','wifi-sec.group','ccmp','wifi-sec.psk',password,
            'connection.autoconnect','no','ipv4.method','shared','ipv4.addresses',ADDRESS+'/24',
            'ipv4.never-default','yes','ipv6.method','disabled')
        command('sudo','-n','nmcli','connection','up',name)
        require(management()==before,'management connectivity changed')
        if request.get('proof_mode','beacon')=='target':
            ap=owned_ap_configuration(root,roles,command)
            proof_path=root/'fixture-ap-proof.json';require(not proof_path.exists(),'AP proof mode already bound')
            private_write(proof_path,dict(mode='target',roles_sha256=roles['sha256'],ap=ap))
            beacon=None
        else:
            require(request.get('proof_mode','beacon')=='beacon','finite AP proof mode')
            beacon=wait_owned_beacon(root,ssid,before,**({'alternate_scans':True} if roles['selection']=='concurrent' else {}))
        with (root/'ntp-server.log').open('x') as log:
            token=os.urandom(16).hex()
            process=subprocess.Popen(['sudo','-n','python3',str(Path(__file__).resolve()),'--serve-ntp',str(root),token],
                stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        deadline=time.monotonic()+5
        while not (root/'ntp-ready.json').exists() and time.monotonic()<deadline:time.sleep(.1)
        require((root/'ntp-ready.json').exists(),'UTC responder unavailable')
        ready=strict((root/'ntp-ready.json').read_bytes());pid=strict((root/'ntp-pid.json').read_bytes())
        require(process.poll() is None and ready['startup_token']==token and pid['startup_token']==token and
                ready['pid']==pid['pid'] and ready.get('roles_sha256')==roles['sha256'] and pid.get('roles_sha256')==roles['sha256'] and ready['enabled'] is False and
                not (root/'ntp-enabled.json').exists(),'fresh initially disabled server proof')
        return dict(status='TARGET_PROOF_PENDING' if beacon is None else 'AP_READY',interface=INTERFACE,time_server=ADDRESS,connection=name,roles_sha256=roles['sha256'],
                    independent_beacon_verified=beacon is not None,bssid=ap['bssid'] if beacon is None else beacon['bssid'],frequency_mhz=2422 if beacon is None else beacon['frequency_mhz'])
    if operation=='discover_ble':
        require(request['expected_name']=='WsprryPico-0a9d89','exact B advertising name')
        return discover(request['expected_name'],root,request.get('expected_address'))
    if operation=='bind_peer':
        if (root/'fixture-ap-proof.json').exists():
            proof=strict((root/'target-ap-proof-warm.json').read_bytes());require(proof['status']=='TARGET_ASSOCIATION_VERIFIED' and proof['roles_sha256']==roles['sha256'] and proof['station_ipv4']==request['address'],'target proof required before responder binding')
        address=ipaddress.IPv4Address(request['address'])
        require(address in ipaddress.IPv4Network(ADDRESS+'/24',strict=False) and
                str(address) not in (ADDRESS,'192.168.84.0','192.168.84.255'),'exact isolated B peer required')
        private_write(root/'ntp-peer.json',dict(address=str(address)))
        return dict(address=str(address))
    if operation in ('sntp_on','sntp_off'):
        require((root/'ntp-ready.json').exists(),'server not started')
        if operation=='sntp_on':
            if (root/'fixture-ap-proof.json').exists():
                proof=strict((root/'target-ap-proof-warm.json').read_bytes());peer=strict((root/'ntp-peer.json').read_bytes());require(proof['status']=='TARGET_ASSOCIATION_VERIFIED' and proof['roles_sha256']==roles['sha256'] and peer['address']==proof['station_ipv4'],'target proof required before SNTP')
            require((root/'ntp-peer.json').exists(),'actual B peer not bound')
            private_write(root/'ntp-enabled.json',dict(enabled=True))
        else:(root/'ntp-enabled.json').unlink(missing_ok=True)
        return dict(enabled=operation=='sntp_on')
    require(operation in ('stop','finish'),'unsupported fixture operation')
    error=None
    try:
        if operation=='stop' and request.get('preserve_disabled_ntp') is True:verify_disabled_ntp(root,roles)
        else:stop_ntp(root)
    except BaseException as failure:error=failure
    existing=command('nmcli','-t','-f','NAME','connection','show').splitlines()
    if name in existing:command('sudo','-n','nmcli','connection','delete',name)
    observer='p12-observer-'+root.name.rsplit('-',1)[1]
    if observer in existing:command('sudo','-n','nmcli','connection','delete',observer)
    saved=root/'fixture-management-before.json'
    if saved.exists():require(management()==strict(saved.read_bytes()),'management restoration changed')
    if operation=='finish' and roles['selection']=='concurrent':
        from phase12_virtual_observer import remove
        end=time.monotonic()+25
        def virtual_command(*argv):
            remaining=end-time.monotonic();require(remaining>0,'virtual cleanup deadline')
            row=subprocess.run(list(argv),capture_output=True,text=True,timeout=min(5,remaining))
            require(len(row.stdout)<=262144 and len(row.stderr)<=16384 and row.returncode==0,'virtual cleanup command')
            return row.stdout
        remove(root,roles,virtual_command,virtual_command,private_write)
    if operation=='finish':
        try:
            final_management=management()
            private_write(root/'fixture-management-after.json',final_management)
            if saved.exists():require(final_management==strict(saved.read_bytes()),'management changed after virtual removal')
        except BaseException as failure:
            if error is None:error=failure
    if error is not None:raise error
    return dict(status='FIXTURE_REMOVED',ntp_stopped=True)


def main():
    os.umask(0o077)
    if len(sys.argv)==4 and sys.argv[1]=='--serve-ntp':serve(Path(sys.argv[2]),sys.argv[3]);return
    request=strict(sys.stdin.buffer.read(16385))
    try:print(json.dumps(action(request)))
    except BaseException as error:
        value=request.get('root') if isinstance(request,dict) else None
        diagnostic_root=Path(value) if isinstance(value,str) else Path('.')
        if re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(diagnostic_root)) and diagnostic_root.is_dir() and not diagnostic_root.is_symlink():
            try:
                path=diagnostic_root/'fixture-action-failure.json'
                if not path.exists() and not path.is_symlink():
                    private_write(path,dict(action=request.get('action'),error_type=type(error).__name__,traceback=traceback.format_exc()))
            except Exception:pass
        raise


if __name__=='__main__':
    try:main()
    except Exception as error:
        # Retain the actual exception privately for autonomous fixture repairs.
        # Console output stays redacted; exceptions can contain host details.
        if len(sys.argv)==4 and sys.argv[1]=='--serve-ntp':
            diagnostic_root=Path(sys.argv[2])
            if re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(diagnostic_root)) and diagnostic_root.is_dir() and not diagnostic_root.is_symlink():
                private_write(diagnostic_root/'ntp-startup-failure.json',dict(error_type=type(error).__name__,traceback=traceback.format_exc()))
        print(json.dumps(dict(status='STOPPED_NO_RETRY',error_type=type(error).__name__)));raise SystemExit(1)
