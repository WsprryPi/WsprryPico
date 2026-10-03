#!/usr/bin/env python3
"""Private B-only production negative paths on a named inhibited fixture, with exact raw HTTP/WTP."""
import hashlib
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
from check_standalone_image import validate_uf2
from phase12_consumer_composition import Evidence,canonical
from phase12_consumer_negative import run as negative,CASES
from phase12_engineering_setup import private_bytes
from phase12_engineering_fixture import command,management
from phase12_recovery_device import DEVICE,strict,require,console
from phase12_serial_observer import Observer
from phase12_composition_audit import counter


class HTTP:
    def __init__(self):self.attempts=0
    def wire(self,method,path,body):
        require((method,path) in {('GET','/api/owner/v1/public-status'),('GET','/api/owner/v1/claim/status'),
            ('POST','/api/owner/v1/claim/start'),('POST','/api/owner/v1/claim/submit')},'consumer route scope')
        require((method=='GET' and body is None) or (method=='POST' and isinstance(body,dict)),'consumer method/body')
        payload=b'' if body is None else canonical(body)
        require(len(payload)<=1024,'bounded consumer request')
        headers=dict(Host='192.168.4.1',Connection='close')
        if body is not None:
            headers.update(Origin='http://192.168.4.1',**{'Content-Type':'application/json',
                'X-WsprryPico-Owner':'1','Content-Length':str(len(payload))})
        return (method+' '+path+' HTTP/1.1\r\n'+''.join(k+': '+v+'\r\n' for k,v in headers.items())+'\r\n').encode()+payload
    def connect(self,deadline):
        require(time.monotonic()<deadline,'HTTP deadline before connect')
        stream=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            stream.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan2\0')
            stream.bind(('192.168.4.2',0))
            stream.settimeout(max(.01,min(5,deadline-time.monotonic())))
            stream.connect(('192.168.4.1',80));return stream
        except BaseException:stream.close();raise
    def __call__(self,method,path,body,deadline):
        self.attempts+=1;require(self.attempts<=100,'finite HTTP request count')
        wire=self.wire(method,path,body);raw=bytearray()
        with self.connect(deadline) as stream:
            require(time.monotonic()<deadline,'HTTP deadline before send')
            stream.settimeout(min(5,deadline-time.monotonic()))
            stream.sendall(wire)
            while True:
                require(time.monotonic()<deadline,'HTTP total deadline')
                stream.settimeout(min(5,deadline-time.monotonic()));chunk=stream.recv(4096)
                if not chunk:break
                raw.extend(chunk);require(len(raw)<=32768,'HTTP response bound')
        head,bodybytes=bytes(raw).split(b'\r\n\r\n',1);lines=head.split(b'\r\n')
        require(re.fullmatch(rb'HTTP/1\.1 [0-9]{3} .*',lines[0]) is not None,'HTTP status line')
        headers={}
        for line in lines[1:]:
            key,value=line.split(b':',1);key=key.lower();require(key not in headers,'duplicate HTTP header')
            headers[key]=value.strip()
        require(b'transfer-encoding' not in headers and re.fullmatch(rb'0|[1-9][0-9]*',headers.get(b'content-length',b'')) is not None and int(headers[b'content-length'])==len(bodybytes),
                'exact HTTP Content-Length')
        require(time.monotonic()<=deadline,'late HTTP response')
        return int(lines[0].split()[1]),strict(bodybytes),wire,bytes(raw)
    def interrupted(self,path,body,deadline):
        self.attempts+=1;require(self.attempts<=100,'finite HTTP request count')
        wire=self.wire('POST',path,body)
        with self.connect(deadline) as stream:
            require(time.monotonic()<deadline,'HTTP deadline before send')
            stream.settimeout(min(5,deadline-time.monotonic()))
            stream.sendall(wire);stream.shutdown(socket.SHUT_WR)
            # Deliberately retain no response. The subsequent public observation
            # must establish whether the complete START reached its granted slot.
        return wire



def private_nmcli(evidence, deadline, *args):
    require(time.monotonic()<deadline,'private nmcli deadline')
    argv=['sudo','-n','nmcli','--wait','5',*args]
    try:
        result=subprocess.run(argv,capture_output=True,timeout=min(7,deadline-time.monotonic()))
    except subprocess.TimeoutExpired as error:
        evidence.record('nmcli_timeout',argv=argv,stdout_hex=(error.stdout or b'').hex(),stderr_hex=(error.stderr or b'').hex())
        raise
    evidence.record('nmcli_actual',argv=argv,returncode=result.returncode,
                    stdout_hex=result.stdout.hex(),stderr_hex=result.stderr.hex())
    require(result.returncode==0,'bounded owned nmcli operation failed; inspect private transcript')
    return result.stdout.decode()


def disconnect_owned(evidence,name,deadline):
    active=private_nmcli(evidence,deadline,'-g','GENERAL.CONNECTION','device','show','wlan2').strip()
    require(active==name,'only campaign-owned BAP may be disconnected')
    private_nmcli(evidence,deadline,'connection','down',name)


def wait_visible_ap(evidence,ssid,deadline,observe,*,clock=time.monotonic,sleeper=time.sleep):
    """Complete active scans, not cached nmcli discovery or a blind delay."""
    require(re.fullmatch('WsprryPico-[0-9a-f]{6}',ssid),'exact B AP SSID')
    for _ in range(20):
        require(clock()<deadline,'actual AP visibility deadline')
        observe() # Exact current boot/source/stage guard before every scan.
        argv=['sudo','-n','/usr/sbin/iw','dev','wlan2','scan']
        try:
            result=subprocess.run(argv,capture_output=True,timeout=min(10,deadline-clock()))
        except subprocess.TimeoutExpired as error:
            evidence.record('actual_ap_scan_timeout',argv=argv,stdout_hex=(error.stdout or b'').hex(),stderr_hex=(error.stderr or b'').hex())
            continue
        require(len(result.stdout)<=262144 and len(result.stderr)<=16384,'bounded actual scan bytes')
        evidence.record('actual_ap_scan',argv=argv,returncode=result.returncode,
                        stdout_hex=result.stdout.hex(),stderr_hex=result.stderr.hex())
        require(clock()<deadline,'actual scan exceeded visibility deadline')
        if result.returncode==0:
            matches=[]
            for block in re.split(rb'(?m)^BSS ',result.stdout)[1:]:
                address=re.match(rb'([0-9a-f:]{17})',block)
                names=re.findall(rb'(?m)^\s*SSID: (.*)$',block)
                if address and names==[ssid.encode()]:matches.append(address[1].decode())
            require(len(matches)<=1,'B AP visibility is ambiguous')
            if matches:
                observe()
                evidence.record('actual_exact_ap_visible',interface='wlan2',ssid=ssid,bssid=matches[0])
                return matches[0]
        sleeper(min(.5,max(0,deadline-clock())))
    raise TimeoutError('bounded complete AP scans exhausted')


def rejoin_owned(evidence,name,ssid,deadline,observe):
    wait_visible_ap(evidence,ssid,deadline,observe)
    private_nmcli(evidence,deadline,'connection','up',name) # Exactly one join attempt.


def run(request):
    require(request['authority']=='USER_AUTHORIZED_UNATTENDED_PHASE12','authority')
    root=Path(request['root']);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and
            root.is_dir() and not root.is_symlink(),'private root')
    raw=private_bytes(root/'manifest.json',262144)
    require(hashlib.sha256(raw).hexdigest()==request['manifest_sha256'],'manifest binding')
    manifest=strict(raw);case=request['case'];require(case in CASES,'one named negative case')
    candidate=next(c for c in manifest['candidates'] if c['role']=='fault_8')
    require(candidate['fault_stage']==8,'negative fixture stage')
    image=private_bytes(root/'fault_8.uf2',4*1024*1024);validate_uf2(image)
    require(hashlib.sha256(image).hexdigest()==candidate['uf2']['sha256'] and
            manifest['source_commit']==request['source_commit'],'inhibited negative fixture binding')
    evidence=Evidence(root/('negative-'+case.lower()+'-wire.jsonl'));observer=Observer()
    http=HTTP();current=dict(boot=request['boot_id']);results=[];reboot_attempted=False
    deadline=time.monotonic()+150
    def info():
        require(time.monotonic()<deadline,'negative tranche deadline')
        value,wire=observer()
        require(time.monotonic()<deadline and isinstance(wire,bytes) and strict(wire)==value,'actual timely INFO wire')
        evidence.record('negative_guard_info',raw_hex=wire.hex())
        require(value['device_id']==DEVICE and value['revision']==manifest['source_commit'][:12] and
                value['status']['boot_id']==current['boot'] and
                counter(value['provisioning_generation'],'generation')==request['profile_generation'],
                'consumer exact boot/source/profile generation')
        require(counter(value.get('phase12_fault_stage'),'fixture stage')==8 and value.get('phase12_fault_consumed') is False and
                value.get('phase12_boot_ap_window_ms')==120000,
                'fresh unconsumed negative fixture')
        require(value['status']['state']=='empty' and value['status']['enabled'] is False and
                value['status']['output_active'] is False,'inactive INFO safety observation')
        return value,wire
    def wait_with_observation(seconds):
        end=time.monotonic()+seconds
        require(end<deadline,'negative wait exceeds whole tranche deadline')
        while time.monotonic()<end:
            time.sleep(min(2,end-time.monotonic()))
            value,wire=info()
            evidence.record('negative_wait_info',raw_hex=wire.hex(),boot_id=current['boot'])
    def reboot():
        nonlocal reboot_attempted
        require(not reboot_attempted,'never repeat reboot')
        old=current['boot'];before=info()[0];host_before=management()
        disconnect_owned(evidence,'p12-recovery-'+root.name.rsplit('-',1)[1],min(deadline,time.monotonic()+15))
        evidence.record('one_reboot_attempt',boot_id=old)
        reboot_attempted=True
        try:
            response=console('REBOOT');require(response.get('ok') is True,'single reboot refused')
        except (OSError,TimeoutError) as error:
            evidence.record('one_reboot_response_unknown',error_type=type(error).__name__)
        end=min(deadline,time.monotonic()+60)
        while True:
            require(time.monotonic()<end,'fresh reboot observation deadline')
            try:value,wire=observer()
            except (OSError,TimeoutError):time.sleep(.3);continue
            require(value['device_id']==DEVICE and value['revision']==manifest['source_commit'][:12] and
                counter(value['provisioning_generation'],'generation')==request['profile_generation'] and
                value['provisioning_source']=='consumer_preclock' and counter(value.get('phase12_fault_stage'),'fixture stage')==8 and
                value.get('phase12_fault_consumed') is False,'reboot exact durable fixture')
            if value['status']['boot_id']!=old:break
            time.sleep(.3)
        current['boot']=value['status']['boot_id'];evidence.record('reboot_actual_info',raw_hex=wire.hex())
        require(counter(value['status']['monotonic_now_ns'],'fresh fixture uptime')<120_000_000_000,
                'fresh cancellation fixture AP window too late')
        require(re.fullmatch('[0-9a-f]{32}',current['boot']) is not None,'fresh boot identity')
        join_end=min(deadline,time.monotonic()+60)
        rejoin_owned(evidence,'p12-recovery-'+root.name.rsplit('-',1)[1],
                     'WsprryPico-'+before['local_suffix'],join_end,lambda:info()[0])
        value=info()[0]
        require(counter(value['status']['monotonic_now_ns'],'postjoin fresh uptime')<120_000_000_000,
                'single fresh join exceeded declared fixture AP window')
        require(management()==host_before,'management changed across cancellation rejoin')
        return dict(boundary='REBOOT',before_boot_id=old,boot_id=current['boot'],reboot_attempts=1,
                    profile_generation=request['profile_generation'])
    try:
        first=info()[0];require(first['status']['state']=='empty' and first['status']['enabled'] is False and
             first['status']['output_active'] is False and first['provisioning_source']=='consumer_preclock',
             'inactive source5 required')
        name='p12-recovery-'+root.name.rsplit('-',1)[1]
        time.sleep(3);info()
        command('sudo','-n','nmcli','connection','up',name)
        require(counter(info()[0]['status']['monotonic_now_ns'],'fixture uptime')<40_000_000_000,
                'fresh negative AP window too late')
        result=negative(case,http,info,None,manifest['source_commit'],current['boot'],evidence,
            request['station'],cancel_boundary=reboot,interrupted_start=http.interrupted,
            sleeper=wait_with_observation)
        require(result['status']=='NEGATIVE_REVIEW_REQUIRED','incomplete negative case')
        results.append(result)
        result=dict(status='NEGATIVES_REVIEW_REQUIRED',cases=results,rf_jobs=0,simulator_jobs=0,
                    boot_id=current['boot'],image_role='fault_8',physical_acceptance=False,
                    wtp_owner_verified=False,wtp_job_identity_verified=False,full_composition_qualified=False)
        with (root/('negative-'+case.lower()+'-result.json')).open('x') as file:
            os.chmod(file.name,0o600);json.dump(result,file);file.write('\n');file.flush();os.fsync(file.fileno())
        return dict(status=result['status'],cases=len(results),rf_jobs=0,wtp_owner_verified=False,wtp_job_identity_verified=False)
    finally:
        evidence.close()


def main():
    os.umask(0o077);request=strict(sys.stdin.buffer.readline(65537))
    def stopped(*_):raise KeyboardInterrupt('negative parent lost/interrupted')
    signal.signal(signal.SIGTERM,stopped)
    def watch():
        if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=watch,daemon=True).start()
    print(json.dumps(run(request)),flush=True)


if __name__=='__main__':main()
