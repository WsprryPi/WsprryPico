#!/usr/bin/env python3
"""Private root-owned wlan0/wlan2 adapters for finite engineering network proof."""
import errno
import fcntl
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from contextlib import ExitStack
from phase12_engineering_network import run
from phase12_engineering_fixture import action as fixture, management as management_identity
from phase12_engineering_composition import QuietUSB
from phase12_engineering_setup import private_bytes
from phase12_serial_observer import Observer
from phase12_recovery_device import DEVICE,CONSOLE,strict,require
from check_usb_target import port
from check_standalone_image import validate_uf2

AUTHORITY='USER_AUTHORIZED_UNATTENDED_PHASE12'
HOST_AP='wlan2'
OBSERVER_INTERFACE='wlan0'
from phase12_fixture_roles import load_roles

def bind_radio_roles(root,request):
    global HOST_AP,OBSERVER_INTERFACE
    roles=load_roles(root)
    require(roles['selection'] in ('engineering','swapped'),'two independent radios required')
    require(request.get('roles_sha256',roles['sha256'] if roles['selection']=='engineering' else None)==roles['sha256'],'exact fixture roles hash')
    HOST_AP=roles['host_ap'];OBSERVER_INTERFACE=roles['observer']
    return roles

def command(args,timeout=20):
    value=subprocess.run(args,capture_output=True,timeout=timeout)
    require(value.returncode==0,'bounded host command failed: '+args[0]);return value.stdout

def activate_owned_observer(name,evidence):
    require(re.fullmatch('p12-observer-[0-9a-f]{32}',name) is not None,'owned observer name')
    argv=['sudo','-n','nmcli','connection','up',name]
    try:
        result=subprocess.run(argv,capture_output=True,timeout=20)
    except subprocess.TimeoutExpired as error:
        stdout=error.stdout or b'';stderr=error.stderr or b''
        try:
            evidence.record('observer_activation',argv=argv,timeout_s=20,outcome='timeout',
                            stdout_hex=stdout[:32768].hex(),stderr_hex=stderr[:32768].hex(),
                            stdout_truncated=len(stdout)>32768,stderr_truncated=len(stderr)>32768)
        except Exception:pass # Diagnostic failure cannot replace the activation timeout.
        raise
    evidence.record('observer_activation',argv=argv,timeout_s=20,outcome='returned',returncode=result.returncode,
                    stdout_hex=result.stdout[:32768].hex(),stderr_hex=result.stderr[:32768].hex(),
                    stdout_truncated=len(result.stdout)>32768,stderr_truncated=len(result.stderr)>32768)
    require(result.returncode==0,'bounded observer activation failed')
    return result.stdout


def fallback_beacon(evidence,end,runner=subprocess.run,clock=time.monotonic):
    left=end-clock()-20
    require(left>0,'no fallback scan/activation budget')
    argv=['sudo','-n','/usr/sbin/iw','dev',OBSERVER_INTERFACE,'scan','freq','2422']
    result=runner(argv,capture_output=True,timeout=min(5,left))
    require(len(result.stdout)<=262144 and len(result.stderr)<=16384,'fallback scan output bound')
    evidence.record('fallback_beacon',argv=argv,returncode=result.returncode,raw_hex=result.stdout.hex(),stderr_hex=result.stderr.hex())
    require(result.returncode==0 and clock()+20<end,'fresh fallback scan deadline')
    blocks=re.split(rb'(?m)^BSS ',result.stdout)[1:]
    exact=[b for b in blocks if b.splitlines()[0].split(b'(')[0].strip()==b'88:a2:9e:0a:9d:89']
    require(len(exact)==1,'one exact B fallback beacon')
    block=exact[0]
    lines=block.splitlines();headers=[i for i,line in enumerate(lines) if re.match(rb'^[ \t]*RSN:',line)]
    security=b''
    if len(headers)==1:
        begin=headers[0];indent=len(lines[begin].expandtabs())-len(lines[begin].lstrip().expandtabs())
        end=begin+1
        while end<len(lines):
            line=lines[end];width=len(line.expandtabs())-len(line.lstrip().expandtabs())
            if line.strip() and width<=indent:break
            end+=1
        security=b'\n'.join(lines[begin:end])
    require(re.findall(rb'(?m)^\s*SSID: (.*)$',block)==[b'WsprryPico-0a9d89'] and
            len(re.findall(rb'(?m)^\s*freq:',block))==1 and
            re.search(rb'(?m)^\s*freq: 2422(?:\.0+)?\s*$',block) and
            re.search(rb'(?m)^\s*capability: .*\bPrivacy\b',block) and
            len(re.findall(rb'(?m)^\s*RSN:',block))==1 and
            re.findall(rb'(?m)^\s*\* Group cipher: (.*)$',security)==[b'CCMP'] and
            re.findall(rb'(?m)^\s*\* Pairwise ciphers: (.*)$',security)==[b'CCMP'] and
            len(re.findall(rb'(?m)^\s*\* Authentication suites: (.*)$',security))==1 and
            b'PSK' in re.findall(rb'(?m)^\s*\* Authentication suites: (.*)$',security)[0].split(),
            'exact protected B fallback security')


def observe_then_activate(name,evidence,end,beacon=fallback_beacon,activate=activate_owned_observer,diagnose=None,clock=time.monotonic):
    beacon(evidence,end)
    require(clock()+20<end,'activation absolute deadline')
    try:activate(name,evidence)
    except BaseException:
        try:(diagnose or failure_window)(evidence,end)
        except BaseException:pass # Preserve original activation uncertainty.
        raise


def failure_window(evidence,end,runner=subprocess.run,clock=time.monotonic):
    # Passive, one bounded command per surface, never another activation.
    for argv in (['/usr/sbin/iw','dev',OBSERVER_INTERFACE,'link'],
                 ['nmcli','-t','-f','GENERAL','device','show',OBSERVER_INTERFACE],
                 ['sudo','-n','journalctl','--no-pager','-n','80','--since','-40 seconds','-u','NetworkManager','-u','wpa_supplicant']):
        left=end-clock()
        if left<=0:return
        try:
            result=runner(argv,capture_output=True,timeout=min(2,left))
            stdout,stderr=result.stdout,result.stderr
            value=dict(returncode=result.returncode,outcome='returned')
        except subprocess.TimeoutExpired as error:
            stdout,stderr=error.stdout or b'',error.stderr or b''
            value=dict(outcome='timeout')
        evidence.record('activation_failure_window',argv=argv,stdout_hex=stdout[:32768].hex(),stderr_hex=stderr[:16384].hex(),
                        stdout_truncated=len(stdout)>32768,stderr_truncated=len(stderr)>16384,**value)


def create_owned_observer(name,args,evidence):
    require(re.fullmatch('p12-observer-[0-9a-f]{32}',name) is not None,'owned observer name')
    require(args['interface']==OBSERVER_INTERFACE,'selected observer interface required')
    command(['sudo','-n','nmcli','connection','add','type','wifi','ifname',OBSERVER_INTERFACE,'con-name',name,'ssid',args['ssid'],
        'connection.autoconnect','no','wifi-sec.key-mgmt','wpa-psk','wifi-sec.psk',args['password'],
        'wifi-sec.proto','rsn','wifi-sec.pairwise','ccmp','wifi-sec.group','ccmp',
        'ipv4.method','manual','ipv4.addresses','192.168.4.3/24','ipv4.never-default','yes','ipv6.method','disabled'])
    observe_then_activate(name,evidence,args['deadline'])


def disconnect_owned_observer(name,command_fn=command):
    require(re.fullmatch('p12-observer-[0-9a-f]{32}',name) is not None,'owned observer name')
    active=command_fn(['nmcli','-g','GENERAL.CONNECTION','device','show',OBSERVER_INTERFACE]).decode().strip()
    if active in ('','--'):return
    require(active==name,'refuse disconnecting foreign observer connection')
    command_fn(['sudo','-n','nmcli','connection','down',name])


def management():
    return command(['nmcli','-t','-f','DEVICE,STATE,CONNECTION','device','status']),command(['ip','-4','route','show','default'])

def cleanup_action(root):
    root=Path(root);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)),'private root')
    name='p12-observer-'+root.name.rsplit('-',1)[1]
    names=command(['nmcli','-t','-f','NAME','connection','show']).decode().splitlines()
    if name in names:command(['sudo','-n','nmcli','connection','delete',name])
    return dict(status='OWNED_OBSERVER_REMOVED')

class Evidence:
    def __init__(self,path):self.file=path.open('x');os.chmod(path,0o600);self.size=0
    def record(self,kind,**value):
        raw=json.dumps(dict(kind=kind,monotonic_ns=str(time.monotonic_ns()),value=value))+'\n'
        self.size+=len(raw);require(self.size<=4*1024*1024,'network evidence bound')
        self.file.write(raw);self.file.flush();os.fsync(self.file.fileno())
    def close(self):self.file.close()

def parse_interfaces(raw):
    rows={}
    for line in raw.decode().splitlines():
        fields=line.split(':',2)
        if len(fields)==3:rows[fields[0]]=dict(state=fields[1],connection=None if fields[2] in ('','--') else fields[2])
    return rows

def scan_link():
    scan=command(['sudo','-n','/usr/sbin/iw','dev',OBSERVER_INTERFACE,'scan'],timeout=20)
    link=command(['/usr/sbin/iw','dev',OBSERVER_INTERFACE,'link'])
    bssids=re.findall(rb'^BSS ([0-9a-f:]{17})',scan,re.M)
    ssids=re.findall(rb'^\s*SSID: (.*)$',scan,re.M)
    associated=re.search(rb'Connected to ([0-9a-f:]{17})',link)
    ssid=re.search(rb'^\s*SSID: (.*)$',link,re.M)
    return scan,link,[v.decode() for v in ssids],[v.decode() for v in bssids],None if associated is None else associated[1].decode(),None if ssid is None else ssid[1].decode()

def http_identity(boot):
    stream=socket.socket(socket.AF_INET,socket.SOCK_STREAM);stream.settimeout(5)
    try:
        stream.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,(OBSERVER_INTERFACE+'\0').encode('ascii'));stream.bind(('192.168.4.3',0))
        stream.connect(('192.168.4.1',80))
        stream.sendall(b'GET /api/recovery/v1/status HTTP/1.1\r\nHost: 192.168.4.1\r\nConnection: close\r\n\r\n')
        raw=bytearray();deadline=time.monotonic()+5
        while True:
            require(time.monotonic()<deadline,'HTTP identity total deadline')
            stream.settimeout(max(.001,deadline-time.monotonic()));chunk=stream.recv(4096)
            if not chunk:break
            raw.extend(chunk);require(len(raw)<=16384,'HTTP identity size')
        class Buffered:
            def makefile(self,*a):return io.BytesIO(raw)
        response=http.client.HTTPResponse(Buffered());response.begin();require(response.status==200,'B recovery readonly identity HTTP')
        value=strict(response.read());require(value['device_id']==DEVICE and value['boot_id']==boot and value['pending'] is False,'B AP full identity')
        return bytes(raw),value['device_id'],'reply'
    except socket.timeout:return b'',None,'timeout'
    except OSError as error:
        outcomes={errno.ECONNREFUSED:'refused',errno.ENETUNREACH:'network_unreachable',errno.EHOSTUNREACH:'network_unreachable',errno.EADDRNOTAVAIL:'association_lost'}
        require(error.errno in outcomes,'unclassified socket failure');return b'',None,outcomes[error.errno]
    finally:stream.close()

def execute(request):
    require(request['authority']==AUTHORITY,'authority');root=Path(request['root'])
    require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and root.is_dir() and not root.is_symlink(),'private root')
    roles=bind_radio_roles(root,request)
    raw=private_bytes(root/'preparation-manifest.json',1024*1024);require(hashlib.sha256(raw).hexdigest()==request['manifest_sha256'],'manifest hash')
    manifest=strict(raw);require(manifest['source_commit']==request['source_commit'],'source binding')
    candidate=next(c for c in manifest['candidates'] if c['role']=='engineering')
    require(candidate['fault_stage']==0 and candidate['target']=='WsprryPico' and candidate['lan_mode']=='tls',
            'ordinary engineering candidate required')
    image=private_bytes(root/'engineering.uf2',4*1024*1024);validate_uf2(image)
    require(hashlib.sha256(image).hexdigest()==candidate['uf2']['sha256']==request['image_sha256'],'ordinary image hash')
    profile=private_bytes(root/'engineering-profile.json',7168);require(hashlib.sha256(profile).hexdigest()==request['profile_sha256'],'profile hash')
    password=private_bytes(root/'default-password.txt',64).decode().removesuffix('\n')
    baseline,route=management();interfaces=parse_interfaces(baseline);identity=management_identity()
    owned='p12-engineering-'+root.name.rsplit('-',1)[1]
    evidence=Evidence(root/'network-wire.jsonl')
    evidence.record('host_preflight',raw_hex=baseline.hex(),route_hex=route.hex(),roles=roles)
    try:
        require(interfaces[OBSERVER_INTERFACE]['state']=='disconnected' and interfaces[OBSERVER_INTERFACE]['connection'] is None and
                interfaces[HOST_AP]['connection']==owned and interfaces['eth0']['state']=='connected' and
                interfaces['wlan1']['state']=='connected','management/spare preflight')
    except BaseException:
        evidence.close();raise
    observer=Observer();name='p12-observer-'+root.name.rsplit('-',1)[1];created=False
    def control(action):
        if action=='station_down':
            fixture(dict(root=str(root),authority=AUTHORITY,action='sntp_off'))
            command(['sudo','-n','nmcli','connection','down',owned])
        else:
            current=parse_interfaces(management()[0])
            if current[HOST_AP]['connection']!=owned:command(['sudo','-n','nmcli','connection','up',owned])
            deadline=time.monotonic()+90
            while True:
                info=observer()[0]
                if info['network']['link_status']==3 and info['network']['ipv4']:break
                require(time.monotonic()<deadline,'B station recovery');time.sleep(1)
            metrics=root/'ntp-metrics.json'
            prior=strict(metrics.read_bytes())['replies'] if metrics.exists() else 0
            fixture(dict(root=str(root),authority=AUTHORITY,action='bind_peer',address=info['network']['ipv4']))
            fixture(dict(root=str(root),authority=AUTHORITY,action='sntp_on'))
            deadline=time.monotonic()+180
            while True:
                if metrics.exists():
                    raw=metrics.read_bytes();value=strict(raw)
                    if value['replies']>prior:
                        evidence.record('fresh_sntp_reply',raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest());break
                require(time.monotonic()<deadline,'fresh B SNTP reply unavailable');time.sleep(1)
    def associate(args):
        nonlocal created
        if args.get('action')=='disconnect_owned':
            if created:disconnect_owned_observer(name)
            return
        created=True
        create_owned_observer(name,args,evidence)
    def observe_ap():
        scan,link,ssids,bssids,bssid,ssid=scan_link();wire,device,outcome=http_identity(request['boot_id'])
        return dict(interface=OBSERVER_INTERFACE,scan_fresh=True,link_observed=True,scan_ssids=ssids,scan_bssids=bssids,
            associated_ssid=ssid,associated_bssid=bssid,http_raw=wire,http_device_id=device,socket_outcome=outcome,
            scan_raw_hex=scan.hex(),scan_sha256=hashlib.sha256(scan).hexdigest(),link_raw_hex=link.hex())
    try:
        with port(CONSOLE.replace('-if00','-if02')) as fd:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            raw_wtp=[]
            def wire(kind,value):
                evidence.record(kind,**value)
                if kind=='private_usb_rx':raw_wtp.append(bytes.fromhex(value['hex']))
            usb=QuietUSB(fd,wire);hello=usb.request('HELLO',dict(versions=['WTP/1'],client_name='phase12-network',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==request['boot_id'],'USB HELLO identity')
            def observe_wtp():
                raw_wtp.clear();value=usb.request('STATUS',{});return value,b''.join(raw_wtp)
            context=dict(source_commit=request['source_commit'],boot_id=request['boot_id'],profile_generation=request['profile_generation'],
                interfaces=interfaces,fixture_connection=owned,radio_roles=roles,ssid='WsprryPico-0a9d89',password=password,no_join_cookie_token_reply=True)
            result=run(context,control,observer,observe_wtp,associate,observe_ap,evidence)
            (root/'network-result.json').write_text(json.dumps(result)+'\n');os.chmod(root/'network-result.json',0o600)
            return result
    finally:
        try:cleanup_action(root)
        finally:
            after,afterroute=management();afterrows=parse_interfaces(after)
            evidence.record('host_final',raw_hex=after.hex(),route_hex=afterroute.hex())
            evidence.close()
            require(afterrows['eth0']==interfaces['eth0'] and afterrows['wlan1']==interfaces['wlan1'] and
                    afterroute==route and management_identity()==identity,'management state changed')
            require(afterrows[OBSERVER_INTERFACE]['state']=='disconnected' and afterrows[OBSERVER_INTERFACE]['connection'] is None,
                    'owned observer adapter not restored')


def main():
    os.umask(0o077);request=strict(sys.stdin.buffer.readline(65537))
    def stopped(*_):raise KeyboardInterrupt('parent lost')
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGALRM,stopped);signal.alarm(900)
    def watch():
        if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=watch,daemon=True).start()
    print(json.dumps(execute(request)),flush=True)
if __name__=='__main__':main()
