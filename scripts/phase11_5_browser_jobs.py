#!/usr/bin/env python3
"""Opt-in three finite A3 Tone jobs through the real authenticated browser API.

No flash, configuration, retries, automatic abort, recovery, or fault clearing.
An independent RF observer and normal production/browser load must already run.
"""
import argparse
import fcntl
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import ssl
import threading
import time
import uuid
from phase11_5_inventory import require,inventory_session
from phase11_5_pilot import validate_packet,DEVICE
from phase11_5_rf_observer import validate_info,validate_status
from phase11_5_pilot_supervisor import finished
from validate_wtp_contract import SchemaValidator,loads_strict
from phase11_5_device_management import save

NAME='wsprrypico-0a60df.local'
PEER='06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016'


def checked_reply(request, code, data):
    require(code==200 and len(data)<=32768,'HTTP job response status/size')
    reply=loads_strict(data.decode())
    require(reply.get('ok') is True and reply.get('request_id')==request['request_id'] and
            set(reply)=={'ok','request_id','result'},'Job operation rejected or mismatched')
    schema=json.loads((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text())
    envelope=dict(type='response',protocol='WTP/1',session_id=request['session_id'],
                  request_id=request['request_id'],op=request['operation'],ok=True,body=reply['result'])
    require(not SchemaValidator(schema).errors(envelope,schema),'Browser result schema')
    result=reply['result'];operation=request['operation']
    if operation in ('LOAD','ARM'):
        require(result['job_id']==request['body']['job_id'],'Response job changed')
    if operation=='ARM':
        require(result['start_utc_ns']==request['body']['start_utc_ns'] and
                result['clock']['state']=='synchronized' and result['clock']['leap']=='normal',
                'Response ARM timing changed')
    if operation=='CLAIM':require(result['owner_id']==request['body']['owner_id'],'Response owner changed')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--run',action='store_true');args=parser.parse_args()
    if not args.run:print('Plan only; no host, network or device accessed');return
    root=args.root.resolve(strict=True);require(root.stat().st_mode & 0o077==0,'Private case root')
    os.umask(0o077)
    packet_path=root/'jobs.json';packet=json.loads(packet_path.read_text());validate_packet(packet)
    require(packet['revision']=='8fb3894253ef' and packet['uf2_sha256']==
            '75b26e3fa2fc74e517fbfe9cdbe8ee7b9c0e6eabfc13708827d48d978ea0ba9f','Exact physical candidate')
    owner=inventory_session(packet['owner_id']);session=inventory_session(packet['browser_session_id'])
    plan=json.loads((root/'load.json').read_text())
    require(plan['boot_id']==packet['boot_id'] and plan['device_id']==DEVICE and
            plan['browser'] is True and plan['address']=='10.77.15.10' and
            os.readlink('/proc/self/ns/net')==plan['netns'] and
            os.readlink('/proc/self/ns/mnt')==plan['mountns'],'Isolated normal-load identity')
    baseline=finished(Path(packet['baseline']),'READ_ONLY_INVENTORY')
    require(baseline['info']['status']['boot_id']==packet['boot_id'],'Baseline boot')
    ctx=ssl.create_default_context(cafile=plan['ca']);ctx.minimum_version=ctx.maximum_version=ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain(plan['browser_cert'],plan['browser_key']);ctx.set_alpn_protocols(['http/1.1'])
    require(Path(plan['browser_lock'])==root/'browser.lock' and plan['browser_control_lane'] is True,
            'Shared browser lane path/policy')
    packet_sha=hashlib.sha256(packet_path.read_bytes()).hexdigest()
    deadline=time.monotonic()+200;sequence=0
    with (root/'browser-jobs.jsonl').open('x') as log:
        def note(kind,value):
            nonlocal sequence
            log.write(json.dumps(dict(sequence=sequence,kind=kind,value=value,
                monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns()))+'\n')
            log.flush();os.fsync(log.fileno());sequence+=1
        def checkpoint():
            require(time.monotonic()<deadline,'Finite A3 actor deadline')
            require(not (root/'observer-failure.json').exists() and
                    not (root/'observer-finish.json').exists(),'Independent observer ended or failed')
            snapshot=json.loads((root/'observer-info.json').read_text())
            require(snapshot['packet_sha256']==packet_sha==hashlib.sha256(packet_path.read_bytes()).hexdigest() and
                    0<=time.monotonic_ns()-snapshot['monotonic_ns']<=2_000_000_000,'Stale INFO observer')
            os.kill(snapshot['pid'],0)
            stat=Path('/proc')/str(snapshot['pid'])/'stat'
            require(stat.read_text().rsplit(')',1)[1].split()[19]==snapshot['pid_start_ticks'],
                    'Observer process identity changed')
            info=snapshot['value']['value'];validate_info(info,baseline)
            return info
        def status():
            checkpoint();snapshot=json.loads((root/'observer-status.json').read_text())
            require(snapshot['packet_sha256']==packet_sha and
                    0<=time.monotonic_ns()-snapshot['monotonic_ns']<=6_000_000_000,
                    'Stale authoritative USB STATUS')
            value=snapshot['value']['value'];validate_status(value,packet['boot_id'],packet)
            return value
        def pause(seconds):
            end=time.monotonic()+seconds
            while time.monotonic()<end:checkpoint();time.sleep(min(.1,end-time.monotonic()))
        def request(operation,body):
            checkpoint()
            value=dict(session_id=session,request_id=uuid.uuid4().hex,operation=operation,body=body)
            pending=root/'browser-control-pending.json'
            require(not pending.exists(),'Unresolved browser control intent')
            save(pending,dict(request_id=value['request_id'],boot_id=packet['boot_id']))
            permit_path=root/'browser-control-permit.json';waiting=time.monotonic()+30
            while True:
                checkpoint()
                permit=json.loads(permit_path.read_text()) if permit_path.exists() else {}
                if permit.get('request_id')==value['request_id']:break
                require(time.monotonic()<waiting,'Browser control permit deadline');pause(.05)
            require(permit['boot_id']==packet['boot_id'] and
                    time.monotonic_ns()+1_000_000_000<permit['end_monotonic_ns'], 'Stale browser control permit')
            pending.unlink()
            # Share one logical browser I/O lane with page/status polling.
            with Path(plan['browser_lock']).open('a') as lock:
                until=time.monotonic()+5
                while True:
                    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                    except BlockingIOError:
                        require(time.monotonic()<until,'Browser control lane deadline');pause(.02)
                info=checkpoint();started=time.monotonic_ns()
                if operation=='ARM':
                    # The browser slot may take seconds to become available.
                    # Choose the finite start from fresh device time only now.
                    clock=info['status']
                    require(clock['clock_state']=='synchronized' and
                            int(clock['uncertainty_ns'])<=500000000,'Clock admission before ARM')
                    start=((int(clock['utc_now_ns'])+12_000_000_000+999)//1000)*1000
                    value['body']={**body,'start_utc_ns':str(start)}
                payload=json.dumps(value,separators=(',',':')).encode()
                wire=(f'POST /api/v1/jobs HTTP/1.1\r\nHost: {NAME}:18443\r\n'
                      f'Origin: https://{NAME}:18443\r\nX-WsprryPico-Request: 1\r\n'
                      'Sec-Fetch-Site: same-origin\r\nContent-Type: application/json\r\n'
                      f'Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n').encode()+payload
                end=min(time.monotonic()+5,permit['end_monotonic_ns']/1e9)
                note('request_intent',dict(request=value,wire_hex=wire.hex()))
                with socket.create_connection((plan['address'],18443),timeout=max(.001,end-time.monotonic())) as raw:
                    raw.settimeout(max(.001,end-time.monotonic()))
                    with ctx.wrap_socket(raw,server_hostname=NAME) as stream:
                        require(stream.selected_alpn_protocol()=='http/1.1' and
                                hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()==PEER,
                                'Authenticated browser peer')
                        def expire():
                            try:stream.shutdown(socket.SHUT_RDWR)
                            except OSError:pass
                        timer=threading.Timer(max(.001,end-time.monotonic()),expire);timer.start()
                        try:
                            stream.settimeout(max(.001,end-time.monotonic()));stream.sendall(wire)
                            response=http.client.HTTPResponse(stream);response.begin();data=response.read(32769)
                            code=response.status;response.close()
                        finally:timer.cancel();timer.join(1)
                note('response',dict(request_id=value['request_id'],http_status=code,body_hex=data.hex(),
                    began_monotonic_ns=started,peer_sha256=PEER))
                require(code==200 and len(data)<=32768 and time.monotonic()<=end,'HTTP job response/deadline')
                return checked_reply(value,code,data)
        note('start',dict(packet=packet,helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
        try:
            info=checkpoint();require(info['status']['state']=='empty','Initial idle required')
            hello=request('HELLO',dict(versions=['WTP/1'],client_name='phase11-5-A3',client_version='1'))
            require(hello['device_id']==DEVICE and hello['boot_id']==packet['boot_id'],'HELLO identity')
            for job in packet['jobs']:
                request('CLAIM',dict(owner_id=owner,lease_ms=60000));request('LOAD',job)
                # Wait for an independent Loaded observation before ARM.
                end=time.monotonic()+6
                while time.monotonic()<end:
                    observed=status()
                    if observed['state']=='loaded' and observed['job_id']==job['job_id']:break
                    pause(.1)
                else:raise TimeoutError('No authoritative Loaded observation')
                pause(2)
                armed=request('ARM',dict(job_id=job['job_id'],max_start_uncertainty_ns='500000000'))
                note('armed_job',dict(job=job,start_utc_ns=armed['start_utc_ns']))
                end=time.monotonic()+30;seen=set();active=False
                while time.monotonic()<end:
                    observed=status()
                    if observed['job_id']==job['job_id']:
                        seen.add(observed['state']);active|=observed['state']=='running' and observed['output_active']
                        if observed['state']=='complete':break
                    pause(.1)
                require(observed['state']=='complete' and {'armed','running','complete'}<=seen and active,
                        'Missing finite completion or state/output coverage')
                request('RELEASE',{})
                end=time.monotonic()+6
                while time.monotonic()<end:
                    observed=status()
                    if observed['state']=='empty' and observed['owner_id'] is None:break
                    pause(.1)
                require(observed['state']=='empty' and observed['owner_id'] is None,'Release not authoritative')
            note('finish',dict(result='CAPTURED_REQUIRES_AUDIT',output_active=False))
        except BaseException as error:
            note('failure',dict(type=type(error).__name__,error=str(error),action='STOP; preserve state; no retry'))
            raise


if __name__=='__main__':main()
