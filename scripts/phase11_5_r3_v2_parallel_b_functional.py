#!/usr/bin/env python3
"""Opt-in exact B-only zero-RF USB and HTTPS admission campaign."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import select
import socket
import ssl
import subprocess
import threading
import time
from phase11_5_inventory import require, exclusive_port
from phase11_5_pilot import Peer
from phase11_5_pilot_supervisor import finished
from phase11_5_device_management import digest, save
from phase11_5_r3_allocation_diagnostic import saved_configuration
from phase11_5_r3_v2_parallel_b_deploy import candidate
from phase11_5_r3_v2_parallel_b_plan import validate, B_SERIAL, B_DEVICE, NAME, PEER_SHA


def usb_exchange(peer, case):
    """No generic operation API: transmit only the exact prevalidated frozen case."""
    raw=bytes.fromhex(case['wire_hex']);request=case['request'];pending=raw
    require(request['op'] in ('HELLO','STATUS','CLAIM','LOAD','ABORT','RELEASE'), 'B idle operations only')
    peer.emit('usb_tx',case);end=time.monotonic()+5;response=None;invalid=0
    while time.monotonic()<end:
        peer.checkpoint()
        reads,writes,_=select.select([peer.fd],[peer.fd] if pending else [],[],.025)
        if writes:
            try:
                n=os.write(peer.fd,pending[:4096]);require(n>0,'B USB write stalled');pending=pending[n:]
                peer.emit('usb_write',dict(bytes=n,total_written=len(raw)-len(pending)))
            except BlockingIOError:pass
        if reads:
            try:data=os.read(peer.fd,4096)
            except BlockingIOError:continue
            require(data,'B USB EOF; state unresolved');peer.emit('usb_rx',dict(hex=data.hex()))
            for value in peer.decoder.feed(data):
                require(not peer.validator.errors(value,peer.schema) and value['session_id']==peer.session,
                        'B invalid/foreign response')
                peer.emit('usb_message',value)
                if value['type']=='event':
                    require(value['boot_id']==peer.boot and value['event'] in ('INVALID_FRAME','JOB_STATE','OWNER_RELEASED'),
                            'B unexpected event')
                    if value['event']=='INVALID_FRAME':invalid+=1
                    if value['event']=='JOB_STATE':
                        require(value['body']['state'] not in ('armed','running') and
                                value['body']['output_active'] is False,'B event indicates RF authority')
                else:
                    require(response is None and not pending and all(value[k]==request[k] for k in
                            ('session_id','request_id','op')), 'B unmatched/premature response')
                    require((case['error'] is None and value['ok'] is True) or
                            (case['error'] is not None and value['ok'] is False and
                             value['error']['code']==case['error']), 'B unexpected outcome')
                    response=value
            if response is not None:
                require(invalid==case['invalid_frames'],'B parser advisory count');return response
    raise TimeoutError('B five-second USB exchange; no retry')


def connect_http(packet):
    path=packet.get('network_path')
    if path is None:return socket.create_connection((packet['address'],18443),timeout=5)
    require(path==dict(interface='wlan1',source_address='192.168.1.117'),'Fixed B management socket path')
    stream=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        stream.settimeout(5)
        stream.setsockopt(socket.SOL_SOCKET,socket.SO_BINDTODEVICE,b'wlan1\0')
        stream.bind(('192.168.1.117',0));stream.connect((packet['address'],18443))
        return stream
    except BaseException:
        stream.close();raise


def http_exchange(root, packet, case, emit, *, target=None):
    name,peer_sha,device = target or (NAME,PEER_SHA,B_DEVICE)
    require((name,peer_sha,device) in [(NAME,PEER_SHA,B_DEVICE),
        ('wsprrypico-0a60df.local','06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016',
         'fd6127d11d6aca42a9905fa3fb1bf1d5')],'Reviewed HTTP identity')
    ctx=ssl.create_default_context(cafile=str(root/'credentials/browser/client-ca.crt'))
    ctx.minimum_version=ssl.TLSVersion.TLSv1_3;ctx.maximum_version=ssl.TLSVersion.TLSv1_3
    ctx.set_alpn_protocols(['http/1.1'])
    ctx.load_cert_chain(str(root/'credentials/browser/client.crt'),str(root/'credentials/browser/client.key'))
    began=time.monotonic_ns();deadline=time.monotonic()+15
    emit('http_tx',case)
    with connect_http(packet) as raw:
        if packet.get('network_path') is not None:
            emit('http_connected',dict(label=case['label'],local=list(raw.getsockname()),peer=list(raw.getpeername()),network_path=packet['network_path']))
        with ctx.wrap_socket(raw,server_hostname=name) as stream:
            peer=hashlib.sha256(stream.getpeercert(binary_form=True)).hexdigest()
            require(peer==peer_sha and stream.selected_alpn_protocol()=='http/1.1','B authenticated TLS peer')
            stream.settimeout(max(.001,deadline-time.monotonic()))
            def expire():
                try:stream.shutdown(socket.SHUT_RDWR)
                except OSError:pass
            timer=threading.Timer(max(.001,deadline-time.monotonic()),expire);timer.daemon=True;timer.start()
            try:
                stream.sendall(bytes.fromhex(case['wire_hex']))
                emit('http_write_complete',dict(label=case['label'],bytes=len(bytes.fromhex(case['wire_hex']))))
                response=http.client.HTTPResponse(stream);response.begin();body=response.read(131073)
            finally:timer.cancel();timer.join(1)
            emit('http_response',dict(label=case['label'],status=response.status,headers=response.getheaders(),
                body_hex=body.hex(),peer_sha256=peer,began_monotonic_ns=began))
            require(time.monotonic()<=deadline and len(body)<=131072,'B HTTP bound')
            require(response.status==case['expected_status'],'B HTTP outcome')
            value=json.loads(body)
            if case['error_code'] is not None:
                require(value['error']['code']==case['error_code'] and
                        (case['error_code']=='invalid_http' or value.get('ok') is False),'B HTTP error')
            elif response.status==200:
                require(value['ok'] is True and value['result']['device_id']==device and
                        value['result']['boot_id']==packet['boot_id'],'B HELLO identity')
            return value


def run(root, packet):
    deadline=time.monotonic()+packet['runtime_seconds'];cleanup_deadline=deadline+150
    result=dict(status='RUNNING',passed_cases=[],accepted_loads=0,rf_jobs=0,arm_commands=0)
    sequence=0;log=(root/'functional.jsonl').open('x')
    def emit(kind,value):
        nonlocal sequence
        log.write(json.dumps(dict(sequence=sequence,kind=kind,value=value,
            monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns()))+'\n')
        log.flush();os.fsync(log.fileno());sequence+=1
    def checkpoint():require(time.monotonic()<deadline,'B finite functional deadline')
    def inventory(label,cleanup=False,enforce_candidate=True):
        require(time.monotonic()+65<(cleanup_deadline if cleanup else deadline),'B inventory deadline')
        with (root/(label+'.stdout')).open('xb') as out,(root/(label+'.stderr')).open('xb') as err:
            code=subprocess.run(['python3',str(root/'scripts/phase11_5_inventory.py'),'--serial',B_SERIAL,
                '--device-id',B_DEVICE,'--session-id',packet['inventory_session'],'--run'],
                stdout=out,stderr=err,timeout=65).returncode
        require(code==0,'B inventory failed: '+label)
        value=finished(root/(label+'.stdout'),'READ_ONLY_INVENTORY')
        if enforce_candidate:candidate(value,packet,boot=packet['boot_id'])
        return value
    before=None
    try:
        emit('start',dict(packet_sha256=digest(root/'packet.json')))
        before=inventory('before-b')
        replies=[]
        for case in packet['stimuli']['http_cases']:
            checkpoint();replies.append(http_exchange(root,packet,case,emit));result['passed_cases'].append(case['label'])
            save(root/'functional-result.json',result)
        require(replies[0]==replies[1],'Exact HELLO replay differs')
        middle=inventory('after-http-b')
        require(saved_configuration(middle)==saved_configuration(before),'B config changed')
        stimuli=packet['stimuli'];state='empty'
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{B_SERIAL}-if02')) as fd:
            peer=Peer(fd,emit,checkpoint,packet['boot_id']);peer.session=stimuli['usb_session']
            for case in stimuli['usb_cases']:
                op=case['request']['op']
                if op=='ABORT':require(state=='loaded','B ABORT only while Loaded/inactive')
                response=usb_exchange(peer,case);body=response.get('body',{})
                if op=='HELLO':
                    require(body['device_id']==B_DEVICE and body['boot_id']==packet['boot_id'],'B USB identity')
                if op=='STATUS':
                    expected='loaded' if case['label']=='loaded-status' else 'empty'
                    require(body['state']==expected and body['output_active'] is False and
                            body['boot_id']==packet['boot_id'],'B inactive status')
                    owned=case['label'] in ('after-513','after-overduration','loaded-status')
                    require(body['owner_id']==(stimuli['owner_id'] if owned else None) and
                            body['job_id']==(stimuli['job_id'] if expected=='loaded' else None),'B authority')
                    state=expected
                if op=='LOAD' and response['ok']:
                    require(body['state']=='loaded' and body['job_id']==stimuli['job_id'] and
                            len(body['adjustments'])==512,'B maximum LOAD response')
                    result['accepted_loads']+=1;state='loaded'
                result['passed_cases'].append(case['label']);save(root/'functional-result.json',result)
        result['status']='OBSERVED_REQUIRES_INDEPENDENT_AUDIT'
    except BaseException as error:
        result.update(status='STOPPED_REQUIRES_DIAGNOSIS',error=type(error).__name__+': '+str(error))
        emit('failure',result['error'])
    finally:
        try:
            final=inventory('final-b',cleanup=True,enforce_candidate=False)
            require(before is not None and saved_configuration(final)==saved_configuration(before),'B final config')
            info=final['info'];status=final['wtp']['STATUS']
            require(info['device_id']==B_DEVICE and info['revision']==packet['source_revision'][:12] and
                info['status']['boot_id']==status['boot_id'] and
                info['status']['state']==status['state'] and
                info['status']['output_active'] is status['output_active'] is False,
                'B final inactive authority not established')
            result['final_b']=final['wtp']['STATUS']
            try:candidate(final,packet,boot=packet['boot_id'])
            except ValueError as error:
                result.update(status='STOPPED_REQUIRES_DIAGNOSIS',final_b_admission_error=str(error))
        except BaseException as error:
            result.update(status='STOPPED_FINAL_STATE_UNVERIFIED',final_b_error=str(error))
        emit('finish',result);save(root/'functional-result.json',result);log.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True)
    p.add_argument('--packet-sha256',required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    if not a.run:print('Plan only; no device or filesystem changes.');return
    require(os.geteuid()==0,'wspr5 root required');os.umask(0o077);root=a.root.resolve(strict=True)
    require(digest(root/'packet.json')==a.packet_sha256,'Packet changed')
    packet=validate(json.loads((root/'packet.json').read_text()));require(packet['root']==str(root),'Root changed')
    prior=Path(packet['deployment_audit_file'])
    require(digest(prior)==packet['deployment_audit_sha256'],'B deployment audit missing/changed')
    audit=json.loads(prior.read_text())
    require(audit['status']=='B_DEPLOYMENT_VERIFIED' and audit['boot_id']==packet['boot_id'] and
            audit['image_sha256']==packet['image_sha256'] and audit['source_revision']==packet['source_revision'],
            'B verified deployment binding')
    required={'scripts/phase11_5_r3_v2_parallel_b_functional.py','scripts/phase11_5_inventory.py',
              'docs/protocol/wtp-1.schema.json'}
    require(required<=packet['stage_sha256'].keys(),'B dependency manifest incomplete')
    for name,sha in packet['stage_sha256'].items():
        require((root/name).resolve().is_relative_to(root) and digest(root/name)==sha,'B dependency changed')
    for name,sha in packet['credential_sha256'].items():
        require(name in ('client-ca.crt','client.crt','client.key') and
                digest(root/'credentials/browser'/name)==sha,'B TLS input changed')
    require(set(packet['credential_sha256'])=={'client-ca.crt','client.crt','client.key'},'B credential closure')
    with (root/'functional-result.json').open('x') as stream:json.dump(dict(status='STARTING'),stream)
    run(root,packet)


if __name__=='__main__':main()
