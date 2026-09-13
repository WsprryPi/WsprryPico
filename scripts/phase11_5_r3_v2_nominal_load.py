#!/usr/bin/env python3
"""Finite native Pi WTP observer plus authenticated HTTPS status contention; no RF control."""
import argparse
import configparser
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import signal
import ssl
import subprocess
import sys
import time
import threading
import urllib.request

from phase11_5_inventory import require
from phase11_5_device_management import digest,save
from phase11_5_pilot import DEVICE

NAME='wsprrypico-0a60df.local'
PEER_SHA='06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016'


def periodic_https(first_start, deadline, stop, observe, finished, monotonic=time.monotonic):
    """Schedule starts independently of native HTTP reads and previous reply latency."""
    next_at=first_start+20
    while next_at<deadline and not finished():
        if stop.wait(max(0,next_at-monotonic())) or finished() or monotonic()>=deadline:return
        require(0<=monotonic()-next_at<=1,'HTTPS scheduled start missed by over one second')
        observe()
        next_at+=20


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no process or network activity.');return
    root=a.root.resolve(strict=True);require(digest(root/'packet.json')==a.packet_sha256,'Nominal packet hash')
    packet=json.loads((root/'packet.json').read_text());plan=packet['contention'];os.umask(0o077)
    require(plan['policy'] in ['native-wtp-and-https-status-20s-v1','native-wtp-and-bounded-pressure-v1'] and packet['standing_authority']=='R3-COMPLETE-20260913-v2' and
            1<=packet['runtime_seconds']<=4000 and plan['maximum_https_requests']<=201,'Nominal finite scope')
    require(os.readlink('/proc/self/ns/net')==plan['netns'] and os.readlink('/proc/self/ns/mnt')==plan['mountns'],
            'Client namespace identity')
    for key in ['binary','observer']:
        require(digest(Path(plan[key]))==plan[key+'_sha256'],'Native binary/observer identity')
    require(digest(root/'production.ini')==plan['ini_sha256'],'Native INI identity')
    sys.path.insert(0,str(root/'pi'));from phase115_production_load import validate_ini
    validate_ini(root/'production.ini',False)
    cfg=configparser.ConfigParser(interpolation=None);cfg.optionxform=str;cfg.read(root/'production.ini')
    require(all(cfg['WTP'][k]==str(root/'credentials/controller'/f) for k,f in
            [('TLS CA File','client-ca.crt'),('TLS Client Certificate','client.crt'),('TLS Client Key','client.key')]),
            'Controller credential paths')
    ctx=ssl.create_default_context(cafile=root/'credentials/browser/client-ca.crt')
    ctx.minimum_version=ctx.maximum_version=ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(root/'credentials/browser/client.crt',root/'credentials/browser/client.key')
    ctx.set_alpn_protocols(['http/1.1']);opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    log=(root/'contention.jsonl').open('x');seq=0;process=None;end=time.monotonic()+packet['runtime_seconds']
    result=dict(status='RUNNING',https_requests=0);pressure_process=None;capture=None
    pressure_mode=plan['policy']=='native-wtp-and-bounded-pressure-v1'
    if pressure_mode:
        from phase11_5_r3_v2_pressure_plan import validate as validate_pressure
        validate_pressure(packet)
        with (root/'jobs.json').open('xb') as f:f.write((root/'packet.json').read_bytes())
        pressure_plan=dict(boot_id=packet['boot_id'],device_id=DEVICE,seconds=packet['runtime_seconds'],browser=False,
            address='10.77.15.10',netns=plan['netns'],mountns=plan['mountns'],ca=str(root/'credentials/browser/client-ca.crt'))
        for role in ['browser','controller']:
            for key,filename in [('cert','client.crt'),('key','client.key')]:pressure_plan[role+'_'+key]=str(root/'credentials'/role/filename)
        with (root/'load.json').open('x') as f:json.dump(pressure_plan,f)
    stop=threading.Event();log_lock=threading.Lock();https_thread=None;https_errors=[]
    signal.signal(signal.SIGTERM,lambda *_:stop.set())
    signal.signal(signal.SIGINT,lambda *_:stop.set())
    def emit(kind,value):
        nonlocal seq
        with log_lock:
            log.write(json.dumps(dict(sequence=seq,kind=kind,value=value,monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns()))+'\n')
            log.flush();os.fsync(log.fileno());seq+=1
    def host_status():
        began=time.monotonic_ns()
        with opener.open('http://127.0.0.1:31425/api/v1/status',timeout=3) as response:
            raw=response.read(131073);require(len(raw)<=131072,'Host status bound');value=json.loads(raw)
        emit('native_status',dict(began_monotonic_ns=began,body_hex=raw.hex(),value=value));return value
    def https():
        began=time.monotonic_ns();deadline=time.monotonic()+15
        request=f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode()
        with socket.create_connection(('10.77.15.10',18443),timeout=5) as raw:
            with ctx.wrap_socket(raw,server_hostname=NAME) as stream:
                require(stream.selected_alpn_protocol()=='http/1.1' and
                    hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()==PEER_SHA,'Authenticated peer')
                stream.settimeout(max(.001,deadline-time.monotonic()));stream.sendall(request)
                def expire():
                    try:stream.shutdown(socket.SHUT_RDWR)
                    except OSError:pass
                timer=threading.Timer(max(.001,deadline-time.monotonic()),expire);timer.daemon=True;timer.start()
                try:
                    response=http.client.HTTPResponse(stream);response.begin();body=response.read(131073)
                finally:timer.cancel();timer.join(1)
                require(response.status==200 and len(body)<=131072 and time.monotonic()<=deadline,'HTTPS response/deadline')
                value=json.loads(body);require(value['job']['boot_id']==packet['boot_id'],'HTTPS boot')
                require(value['transport']['active']==2 and value['transport']['pending']==0,
                        'Native WTP plus HTTPS supported concurrency')
                emit('https_status',dict(began_monotonic_ns=began,request_hex=request.hex(),status=response.status,
                    headers=response.getheaders(),body_hex=body.hex(),peer_sha256=PEER_SHA))
                result['https_requests']+=1
        return began/1_000_000_000
    try:
        emit('start',dict(packet_sha256=a.packet_sha256,policy=plan['policy'],binary_sha256=plan['binary_sha256']))
        with (root/'production.log').open('xb') as out:
            process=subprocess.Popen([plan['binary'],'--backend','wtp','-i',str(root/'production.ini'),
                '--socket-loopback-only','--socket-loopback-family','ipv4','--allow-unqualified-frequency',
                '--allow-non-amateur-frequency'],cwd=root,stdout=out,stderr=subprocess.STDOUT,
                env=dict(os.environ,LD_PRELOAD=plan['observer'],PHASE115_TLS_LOG=str(root/'production-tls.bin')))
            until=time.monotonic()+40;ready=None
            while time.monotonic()<until and not stop.is_set():
                require(process.poll() is None,'Native exited before readiness')
                try:status=host_status()
                except OSError:time.sleep(.2);continue
                identity=status.get('host',{}).get('identity')
                if identity:
                    require(identity['device_id']==DEVICE and identity['boot_id']==packet['boot_id'] and
                        status['host']['network']['resolved_address']=='10.77.15.10' and
                        status['host']['network']['authenticated_identity']==NAME,'Native peer identity')
                    first_https_start=https();ready=dict(packet_sha256=a.packet_sha256,boot_id=packet['boot_id'],
                        observed_monotonic_ns=time.monotonic_ns(),pid=process.pid);break
                time.sleep(.2)
            require(ready is not None,'Native readiness deadline')
            if pressure_mode:
                save(root/'tcp-clock-start.json',dict(monotonic_ns=time.monotonic_ns(),realtime_ns=time.time_ns()))
                with (root/'pressure-capture.stderr').open('xb') as err:
                    capture=subprocess.Popen(['tcpdump','-i','wlan2','-U','-s','0','-w',str(root/'pressure.pcap'),
                        'tcp and host 10.77.15.10 and port 18443'],stdout=subprocess.DEVNULL,stderr=err)
                time.sleep(.3);require(capture.poll() is None,'Pressure capture startup')
                with (root/'pressure.stdout').open('xb') as out,(root/'pressure.stderr').open('xb') as err:
                    pressure_process=subprocess.Popen(['python3',str(root/'scripts/phase11_5_r3_v2_pressure.py'),
                        '--root',str(root),'--run'],stdout=out,stderr=err)
                until=time.monotonic()+5
                while not (root/'pressure-ready.json').exists():
                    require(pressure_process.poll() is None and time.monotonic()<until,'Pressure readiness deadline')
                    time.sleep(.05)
                require(json.loads((root/'pressure-ready.json').read_text())['packet_sha256']==a.packet_sha256,
                        'Pressure readiness packet')
            save(root/'contention-ready.json',ready)
            if not pressure_mode:
                def observe_https():
                    require(result['https_requests']<plan['maximum_https_requests'],'HTTPS count bound')
                    https()
                def https_worker():
                    try:
                        periodic_https(first_https_start,end,stop,observe_https,
                            lambda:(root/'rf-observation-done.json').exists())
                    except BaseException as error:
                        https_errors.append(error);stop.set()
                https_thread=threading.Thread(target=https_worker,name='finite-https-status')
                https_thread.start()
            while time.monotonic()<end and not stop.is_set() and not (root/'rf-observation-done.json').exists():
                require(process.poll() is None,'Native exited during finite observation')
                status=host_status();identity=status.get('host',{}).get('identity')
                require(identity and identity['device_id']==DEVICE and identity['boot_id']==packet['boot_id'],'Native identity lost')
                if pressure_mode:
                    require(pressure_process.poll() in [None,0] and capture.poll() is None,'Pressure/capture process failed')
                save(root/'contention-live.json',dict(packet_sha256=a.packet_sha256,observed_monotonic_ns=time.monotonic_ns()))
                time.sleep(min(1,max(0,end-time.monotonic())))
            if https_errors:raise https_errors[0]
            if pressure_mode:
                pressure_process.wait(timeout=5);require(pressure_process.returncode==0,'Pressure completion')
                result['pressure_exit']=pressure_process.returncode
            result['status']='CAPTURED_REQUIRES_AUDIT'
    except BaseException as error:
        result.update(status='FAILED',error=str(error));emit('failure',dict(type=type(error).__name__,error=str(error)))
        save(root/'contention-failed.json',result)
    finally:
        stop.set()
        if https_thread is not None:
            https_thread.join(17)
            if https_thread.is_alive() or https_errors:
                result.update(status='FAILED',error=str(https_errors[0]) if https_errors else 'HTTPS worker failed to stop')
        if pressure_process is not None and pressure_process.poll() is None:
            pressure_process.terminate()
            try:pressure_process.wait(timeout=5)
            except subprocess.TimeoutExpired:pressure_process.kill();pressure_process.wait(timeout=5)
        if capture is not None:
            if capture.poll() is None:
                capture.send_signal(signal.SIGINT)
                try:capture.wait(timeout=5)
                except subprocess.TimeoutExpired:capture.kill();capture.wait(timeout=5)
            save(root/'tcp-clock-end.json',dict(monotonic_ns=time.monotonic_ns(),realtime_ns=time.time_ns()))
            result['capture_exit']=capture.returncode
            if capture.returncode!=0:result['status']='FAILED'
        if process is not None:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=5);result.update(status='FAILED',error='Native required SIGKILL')
            result['native_exit']=process.returncode
            if process.returncode!=0:result['status']='FAILED'
        emit('finish',result);save(root/'contention-result.json',result);log.close()
        require(result['status']=='CAPTURED_REQUIRES_AUDIT','Nominal load failed')

if __name__=='__main__':main()
