#!/usr/bin/env python3
"""Opt-in, finite idle LOAD regression on the identified Pico A; no ARM operation."""
import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import select
import signal
import socket
import ssl
import subprocess
import threading
import time

from phase11_5_inventory import exclusive_port, exchange, require, loads_console
from phase11_5_pilot import Decoder, SERIAL, DEVICE
from phase11_5_pilot_supervisor import finished, PICOTOOL, PICOTOOL_SHA, configuration
from phase11_5_r3_allocation_diagnostic import request_bootsel, inactive
from phase11_5_network_fixture import Fixture
from phase11_5_r3_v2_admission import maximum_job, candidate
from validate_wtp_contract import frame, SchemaValidator, loads_strict

SOURCE='e256633304e03ab85998fde947360ccbaab6c68e'
C7_SESSION='d2f0af9141101f9a5c0d61e7cdee7983'
C7_RID='7082c6ffbb9d466eac3cfc636ba6538a'
C7_JOB='8d8734400ddd2d472799f3d08a92e6b5'
PRIOR_JOB='c339ee30075d458ccc3047bb3d8f8b18'
WIRE_SHA='e5b48b92dd2abd74e670f2b2aed3d660c9b357bd4857be6b64b8affedbcee670'
NAME='wsprrypico-0a60df.local'
PEER_SHA='06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016'
CONTINUATION='R3-G2-LOAD-CONTINUATION-v1'
RECOVERY='R3-G2-LOAD-WIFI-RECOVERY-v1'
PRIOR_PACKET_SHA='cbe4d13d0c3b19a2ef891366a9b0bcaf12b9077927b7d66da45a4703b8dc1a84'
RETAINED_BOOT='11dac3985326cb81c49022efcdceb5d4'
OPS={'HELLO','STATUS','CLAIM','LOAD','ABORT','RELEASE'}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
def request(op,body,rid,session=C7_SESSION):
    require(op in OPS,'Operation outside idle scope')
    return dict(type='request',protocol='WTP/1',session_id=session,request_id=rid,op=op,body=body)
def raw_request(q):return frame(json.dumps(q,separators=(',',':')).encode())
def primary():return request('LOAD',maximum_job(C7_JOB,duration=128000000000),C7_RID)
def validate_packet(p):
    require(p['scope'] in ['R3-G2-LOAD-TARGET-v1',CONTINUATION,RECOVERY] and p['source_revision']==SOURCE and
        p['serial']==SERIAL and p['device_id']==DEVICE and p['primary']==primary(), 'Exact target scope')
    require(len(raw_request(p['primary']))==52105 and hashlib.sha256(raw_request(p['primary'])).hexdigest()==WIRE_SHA,'Exact primary bytes')
    continuation=p['scope'] in [CONTINUATION,RECOVERY]
    recovery=p['scope']==RECOVERY
    if recovery:require(type(p['prepare_retained']) is bool,'Explicit retained preparation selection')
    if continuation:require(p['prior_packet_sha256']==PRIOR_PACKET_SHA and p['expected_boot']==RETAINED_BOOT,'Frozen retained continuation')
    require(p['limits']==dict(flashes=0 if continuation else 1,bootsel=0 if continuation else 1,primary_loads=1,replays=2,rf_jobs=0,configuration_writes=0,wifi_cycles=1 if recovery else 0,https_requests=4,network_seconds=90),'Finite limits')
    require(p['cleanup_deadline_utc_ns']-p['work_deadline_utc_ns']==900000000000 and
        p['cleanup_deadline_utc_ns']-p['start_utc_ns']==3600000000000,'Original hour/cleanup reserve')
    for key in ['b_session','inventory_session','owner_id','fresh_request_id','tls_session']:
        value=p[key];require(len(value)==32 and all(c in '0123456789abcdef' for c in value),'Protocol identity width')
    require(len({p[k] for k in ['b_session','inventory_session','owner_id','fresh_request_id','tls_session']})==5,'Distinct protocol identities')
    return p

class Journal:
    def __init__(self,path):self.file=path.open('x');self.sequence=0;self.lock=threading.Lock()
    def __call__(self,kind,value):
        with self.lock:
            self.file.write(json.dumps(dict(sequence=self.sequence,monotonic_ns=time.monotonic_ns(),utc_ns=time.time_ns(),kind=kind,value=value))+'\n');self.file.flush();os.fsync(self.file.fileno());self.sequence+=1

class USB:
    def __init__(self,fd,boot,emit,check):
        self.fd=fd;self.boot=boot;self.emit=emit;self.check=check;self.decoder=Decoder()
        self.schema=loads_strict((Path(__file__).resolve().parents[1]/'docs/protocol/wtp-1.schema.json').read_text());self.validator=SchemaValidator(self.schema)
    def ask(self,q,label):
        require(q['op'] in OPS and not self.validator.errors(q,self.schema),'Valid idle request')
        self.check();raw=raw_request(q);pending=raw;end=time.monotonic()+5
        self.emit('usb_tx',dict(label=label,request=q,hex=raw.hex()))
        while time.monotonic()<end:
            self.check();reads,writes,_=select.select([self.fd],[self.fd] if pending else [],[],min(.025,max(0,end-time.monotonic())))
            if writes:
                try:n=os.write(self.fd,pending[:4096])
                except BlockingIOError:n=0
                if n:
                    pending=pending[n:];self.emit('usb_write',dict(label=label,bytes=n,total_written=len(raw)-len(pending)))
            if not reads:continue
            try:data=os.read(self.fd,4096)
            except BlockingIOError:continue
            require(data,'USB EOF; output authority unresolved');self.emit('usb_rx',dict(label=label,hex=data.hex()))
            response=None
            for value in self.decoder.feed(data):
                require(not self.validator.errors(value,self.schema) and value['session_id']==q['session_id'],'USB response schema/session')
                self.emit('usb_message',dict(label=label,message=value))
                if value['type']=='event':
                    require(value['boot_id']==self.boot and value['event'] in ['JOB_STATE','OWNER_RELEASED'],'USB event');continue
                require(not pending and response is None and all(value[k]==q[k] for k in ['request_id','op']) and value['ok'] is True,'USB operation outcome')
                response=value
            if response:
                require(time.monotonic()<=end,'Five-second exchange deadline');return response
        raise TimeoutError('Five-second exchange deadline; no retry: '+label)

def healthy(info,boot):
    require(info['device_id']==DEVICE and info['revision']==SOURCE[:12] and info['status']['boot_id']==boot and
        info['status']['output_active'] is False and info['status']['enabled'] is False and not info['recovery_boot'],'INFO identity/inactive')
    # Console encodes these uint64 counters as decimal strings, even at zero.
    require(info['allocator_failures']=='0' and info['launch_epoch']=='0' and
        info['tls_allocation_failures']==0 and all(info[k]==0 for k in
        ['fault_stage','fault_hash','fault_pc','fault_status','dma_irqs','alarm_irqs','tail_irqs']),'Idle counters/faults')
    for core in (0,1):
        require(info[f'core{core}_stack_guard_valid']==1 and info[f'core{core}_stack_fault_status']==0 and info[f'core{core}_stack_used_bytes']<=12288,'Stack guard/reserve')
    require(info['heap_capacity_bytes']-info['allocator_peak_bytes']>=32768,'Observed allocator reserve')

def response_ok(reply):
    b=reply['body'];require(b['job_id']==C7_JOB and b['state']=='loaded' and len(b['adjustments'])==512,'Complete LOAD body')
    for i,a in enumerate(b['adjustments']):
        require(a==dict(event_index=i,requested_frequency_nhz=str(135500000000000 if i%2==0 else 135495000000000),
            realized_frequency_nhz=str(135500002652407 if i%2==0 else 135494990274310)),'Adjustment value')
    require(len(json.dumps(reply,separators=(',',':')).encode())==54916,'LOAD response size')

def inventory(root,p,label,b=False):
    serial='CDDBF8767C506C07' if b else SERIAL;device='29f20b7342051ef947aa56cb9d4fab42' if b else DEVICE
    with (root/(label+'.stdout')).open('xb') as out,(root/(label+'.stderr')).open('xb') as err:
        proc=subprocess.run(['python3',str(root/'scripts/phase11_5_inventory.py'),'--serial',serial,'--device-id',device,'--session-id',p['b_session'] if b else p['inventory_session'],'--run'],stdout=out,stderr=err,timeout=65)
    require(proc.returncode==0,'Inventory failed: '+label);return finished(root/(label+'.stdout'),'READ_ONLY_INVENTORY')

def deploy(root,p,emit,check):
    require(p['scope']=='R3-G2-LOAD-TARGET-v1','Continuation has no flash authority')
    check();require(not (root/'deployment.json').exists(),'Single deployment only')
    before=inventory(root,p,'before-a');before_b=inventory(root,p,'before-b',True);inactive(before);inactive(before_b)
    require(before['info']['revision']==p['prior_revision'] and before['wtp']['STATUS']['boot_id']==p['prior_boot'],'Prior image/boot')
    require(digest(PICOTOOL)==PICOTOOL_SHA and digest(root/'candidate.uf2')==p['image_sha256'],'Reviewed tool/image')
    state=dict(bootsel_commands=1,flashes_started=0);save(root/'deployment.json',state)
    emit('bootsel_intent',state);request_bootsel(emit)
    end=time.monotonic()+15
    while time.monotonic()<end:
        found=False
        for serial in Path('/sys/bus/usb/devices').glob('*/serial'):
            try:found|=serial.read_text().strip().upper()==SERIAL and (serial.parent/'idVendor').read_text().strip()=='2e8a' and (serial.parent/'idProduct').read_text().strip()=='000f'
            except OSError:pass
        if found:break
        time.sleep(.2)
    require(found,'Serial-specific bootloader absent');check();state['flashes_started']=1;save(root/'deployment.json',state)
    with (root/'flash.stdout').open('xb') as out,(root/'flash.stderr').open('xb') as err:
        r=subprocess.run([str(PICOTOOL),'load','-v','-x',str(root/'candidate.uf2'),'--ser',SERIAL],stdout=out,stderr=err,timeout=60)
    require(r.returncode==0,'Flash failed; no retry')
    end=time.monotonic()+15
    while not Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00').exists() and time.monotonic()<end:time.sleep(.2)
    after=inventory(root,p,'after-flash-a');boot=candidate(after,p)
    require(boot!=p['prior_boot'] and configuration(after)==configuration(before),'Boot/configuration preservation')
    healthy(after['info'],boot)
    state.update(boot_id=boot,status='CANDIDATE_VERIFIED');save(root/'deployment.json',state);emit('deployment',state)

def wifi_cycle(root,boot,check,cleanup_deadline):
    log=Journal(root/'wifi.jsonl');log('start',dict(boot_id=boot));state=dict(off_started=0,on_started=0,status='STARTED');save(root/'wifi-state.json',state)
    with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
        def ask(command):
            reply=exchange(fd,command,time.monotonic()+10,log,False)
            log('message',dict(command=command.decode().strip(),reply=reply));require(reply.get('ok') is True,'Wi-Fi recovery acknowledgement');return reply
        info=ask(b'INFO\n');healthy(info,boot);require(info['status']['state']=='empty','Idle Wi-Fi recovery')
        check()
        try:
            state['off_started']=1;save(root/'wifi-state.json',state);ask(b'WIFI OFF\n')
            until=time.monotonic()+10
            while True:
                info=ask(b'INFO\n');healthy(info,boot)
                if info['network']['enabled'] is False and not info['network']['withdrawal_pending']:break
                require(time.monotonic()<until,'Wi-Fi OFF completion deadline');time.sleep(.2)
        finally:
            # Restore network enablement even if the OFF acknowledgement is lost.
            require(time.time_ns()<cleanup_deadline,'Wi-Fi ON cleanup deadline')
            state['on_started']=1;save(root/'wifi-state.json',state);ask(b'WIFI ON\n')
        info=ask(b'INFO\n');healthy(info,boot);require(info['network']['enabled'] is True,'Wi-Fi ON state')
    state['status']='WIFI_RECOVERED';save(root/'wifi-state.json',state);log('finish',state)


def wait_network(root,boot,check):
    log=Journal(root/'readiness.jsonl');log('start',dict(boot_id=boot));until=time.monotonic()+90
    try:
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as fd:
            consecutive=0
            while time.monotonic()<until:
                check();info=exchange(fd,b'INFO\n',min(until,time.monotonic()+5),log,False);log('info',info);healthy(info,boot)
                network=info['network']
                ready=(network['initialized'] and network['enabled'] and network['link_status']==3 and network['ipv4']=='10.77.15.10' and network['control_listening'])
                consecutive=consecutive+1 if ready else 0
                if consecutive>=2:log('finish',dict(status='PICO_NETWORK_READY'));return
                time.sleep(min(2,max(0,until-time.monotonic())))
        raise TimeoutError('Pico network readiness deadline')
    except BaseException as error:
        log('failure',dict(error=str(error)));raise


def network(root,p,emit,check):
    boot=json.loads((root/'deployment.json').read_text())['boot_id'];end=time.monotonic()+90;stop=threading.Event();errors=[]
    def context(role,alpn):
        d=root/'credentials'/role;c=ssl.create_default_context(cafile=d/'client-ca.crt');c.minimum_version=c.maximum_version=ssl.TLSVersion.TLSv1_3;c.load_cert_chain(d/'client.crt',d/'client.key');c.set_alpn_protocols([alpn]);return c
    def connect(ctx,alpn):
        check();raw=socket.create_connection(('10.77.15.10',18443),timeout=5)
        try:s=ctx.wrap_socket(raw,server_hostname=NAME)
        except BaseException:raw.close();raise
        require(s.selected_alpn_protocol()==alpn and hashlib.sha256(s.getpeercert(binary_form=True)).hexdigest()==PEER_SHA,'TLS peer');s.settimeout(5)
        emit('tls',dict(version=s.version(),alpn=alpn,peer_sha256=PEER_SHA));return s
    def https():
        try:
            ctx=context('browser','http/1.1');previous=start
            for i in range(1,5):
                if stop.wait(max(0,max(start+i*20,previous+20)-time.monotonic())):return
                check();q=f'GET /api/v1/status HTTP/1.1\r\nHost: {NAME}:18443\r\nConnection: close\r\n\r\n'.encode();began=time.monotonic_ns();previous=began/1e9
                with connect(ctx,'http/1.1') as s:
                    until=began/1e9+15
                    def expire():
                        try:s.shutdown(socket.SHUT_RDWR)
                        except OSError:pass
                    timer=threading.Timer(max(0,until-time.monotonic()),expire);timer.start()
                    try:
                        s.sendall(q);r=http.client.HTTPResponse(s);r.begin();body=r.read(131073)
                        require(time.monotonic()<=until,'HTTPS overall deadline')
                    finally:timer.cancel();timer.join(1)
                    require(r.status==200 and len(body)<=131072,'HTTPS status response');v=json.loads(body);require(v['job']['boot_id']==boot and v['job']['output_active'] is False,'HTTPS job authority')
                    emit('https',dict(began_ns=began,request_hex=q.hex(),status=r.status,headers=r.getheaders(),body_hex=body.hex()))
        except BaseException as e:errors.append(str(e));stop.set();emit('failure',dict(worker='https',error=str(e)))
    start=time.monotonic();thread=None
    try:
        with connect(context('controller','wtp/1'),'wtp/1') as s:
            decoder=Decoder();session=p['tls_session'];seq=0
            def ask(op,body):
                nonlocal seq
                seq+=1;q=request(op,body,f'{seq:032x}',session);raw=raw_request(q);until=time.monotonic()+5;emit('tls_tx',dict(request=q,hex=raw.hex()));s.sendall(raw)
                while time.monotonic()<until:
                    s.settimeout(max(.001,until-time.monotonic()));part=s.recv(4096);require(part,'TLS EOF');emit('tls_rx',dict(hex=part.hex()))
                    answer=None
                    for v in decoder.feed(part):
                        emit('tls_message',v);require(v['session_id']==session,'TLS session')
                        if v['type']=='event':require(v['boot_id']==boot,'TLS event boot');continue
                        require(answer is None and v['request_id']==q['request_id'] and v['op']==op and v['ok'],'TLS response');answer=v
                    if answer:return answer
                raise TimeoutError('TLS five-second reply deadline')
            h=ask('HELLO',dict(versions=['WTP/1'],client_name='LOAD-reply-observer',client_version='1'))
            require(h['body']['device_id']==DEVICE and h['body']['boot_id']==boot,'TLS device/boot')
            save(root/'network-ready.json',dict(boot_id=boot,monotonic_ns=time.monotonic_ns()));thread=threading.Thread(target=https);thread.start()
            next_at=time.monotonic()
            while time.monotonic()<end and not stop.is_set():
                check();v=ask('STATUS',{});require(v['body']['boot_id']==boot and v['body']['output_active'] is False,'TLS inactive status');next_at+=5;stop.wait(max(0,min(next_at,end)-time.monotonic()))
            require(not errors,'HTTPS worker failed')
        emit('finish',dict(status='NETWORK_COMPLETE'))
    finally:
        stop.set()
        if thread:thread.join(12)

def run(root,p,emit,check):
    require(not (root/'run-result.json').exists(),'Single physical attempt only')
    boot=json.loads((root/'deployment.json').read_text())['boot_id'];result=dict(status='RUNNING',passed=[],primary_loads=0,replays=0,rf_jobs=0);save(root/'run-result.json',result)
    fixture=Fixture(root);stop=threading.Event();info_ready=threading.Event();errors=[];observer=None;net=None;fd=None
    def info_worker():
        try:
            with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as console:
                next_at=time.monotonic()
                while not stop.is_set():
                    check();began=time.monotonic_ns();info=exchange(console,b'INFO\n',time.monotonic()+5,lambda k,v:emit('console_'+k,v),False);emit('info',dict(began_ns=began,value=info));healthy(info,boot);info_ready.set();next_at+=1;stop.wait(max(0,next_at-time.monotonic()))
        except BaseException as e:errors.append(str(e));stop.set();emit('failure',dict(worker='info',error=str(e)))
    def active_check():
        check();require(not stop.is_set() and not errors,'Observer failure')
        if net and net.poll() is not None:
            done=root/'network-result.json'
            require(done.exists() and json.loads(done.read_text())['status']=='COMPLETE','Network observer exited unexpectedly')
    try:
        with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as fd:
            peer=USB(fd,boot,emit,active_check)
            def ask(op,body,label,rid):return peer.ask(request(op,body,rid),label)
            hello=dict(versions=['WTP/1'],client_name='LOAD-reply-check',client_version='1')
            if p['scope']==RECOVERY:
                fixture.setup();fixture.verify();wifi_cycle(root,boot,active_check,p['cleanup_deadline_utc_ns'])
            if p['scope']==CONTINUATION or (p['scope']==RECOVERY and not p['prepare_retained']):
                prior=json.loads((root/'prior/run.jsonl').read_text().splitlines()[-1])
                require(time.monotonic_ns()-prior['monotonic_ns']>=310000000000,'Retained cache aging')
                result['passed'].append('retained_preparation_reused')
                if p['scope']!=RECOVERY:fixture.setup();fixture.verify()
            else:
                ask('HELLO',hello,'prime-hello','a'*32);ask('CLAIM',dict(owner_id=p['owner_id'],lease_ms=60000),'prime-claim','b'*32)
                prime=ask('LOAD',maximum_job(PRIOR_JOB),'prime-load','c'*32)
                response_ok(dict(prime,body=dict(prime['body'],job_id=C7_JOB)))
                ask('ABORT',dict(job_id=PRIOR_JOB),'prime-abort','d'*32);ask('RELEASE',{},'prime-release','e'*32)
                retained_at=time.monotonic();result['passed'].append('retained_job_prepared');save(root/'run-result.json',result)
                if p['scope']!=RECOVERY:fixture.setup();fixture.verify()
                while time.monotonic()-retained_at<310:active_check();time.sleep(min(1,310-(time.monotonic()-retained_at)))
            ask('HELLO',hello,'test-hello','f'*32)
            s=ask('STATUS',{},'retained-status','0'*32)['body'];require(s['state']=='empty' and s['owner_id'] is None and s['output_active'] is False and len(s['terminal_records'])==1 and s['terminal_records'][0]['job_id']==PRIOR_JOB and s['terminal_records'][0]['state']=='aborted','Retained baseline')
            result['passed'].append('retained_baseline_verified')
            wait_network(root,boot,active_check)
            pid=int(fixture.value('systemctl','show','-p','MainPID','--value','phase115-closure-client'))
            net=subprocess.Popen(['nsenter','-t',str(pid),'-m','-n','python3',str(Path(__file__).resolve()),'network','--root',str(root),'--packet-sha256',digest(root/'test-packet.json'),'--run'],stdout=(root/'network.stdout').open('xb'),stderr=(root/'network.stderr').open('xb'))
            until=time.monotonic()+10
            while not (root/'network-ready.json').exists() and time.monotonic()<until:active_check();require(net.poll() is None,'Network observer exited');time.sleep(.1)
            require((root/'network-ready.json').exists(),'Network readiness deadline')
            observer=threading.Thread(target=info_worker);observer.start()
            require(info_ready.wait(6),'First healthy INFO readiness');active_check()
            for i in range(7):
                if i:stop.wait(5)
                active_check();ask('STATUS',{},'pre-status-'+str(i),f'{i+1:032x}')
            ask('CLAIM',dict(owner_id=p['owner_id'],lease_ms=60000),'test-claim','8'*32)
            require(net.poll() is None,'Persistent TLS observer ended before LOAD')
            result['primary_loads']=1;save(root/'run-result.json',result)
            reply=peer.ask(p['primary'],'primary');response_ok(reply);result['passed'].append('primary_reply')
            result['replays']=1;save(root/'run-result.json',result);again=peer.ask(p['primary'],'identical-replay');require(again==reply,'Replay response equality')
            fresh=dict(p['primary'],request_id=p['fresh_request_id']);result['replays']=2;save(root/'run-result.json',result);again=peer.ask(fresh,'fresh-id-replay');response_ok(again);require(dict(again,request_id=reply['request_id'])==reply,'Fresh-ID response equality')
            s=ask('STATUS',{},'loaded-status','9'*32)['body'];require(s['state']=='loaded' and s['job_id']==C7_JOB and s['owner_id']==p['owner_id'] and s['output_active'] is False,'Loaded authority')
            result['passed'].append('both_replays_and_loaded_state')
            ask('ABORT',dict(job_id=C7_JOB),'test-abort','a1'*16);ask('RELEASE',{},'test-release','a2'*16)
            ended=time.monotonic()
            while time.monotonic()-ended<30 or net.poll() is None:
                active_check();require(time.monotonic()-ended<110,'Observation end bound');stop.wait(.5)
            require(net.returncode==0,'Network observer failure');result['passed'].append('observation_complete');result['status']='CAPTURED_REQUIRES_AUDIT'
    except BaseException as e:
        result['status']='FAILED';result['error']=str(e);emit('failure',dict(worker='main',error=str(e)))
    finally:
        stop.set()
        if observer:observer.join(7)
        if net and net.poll() is None:
            try:net.terminate();net.wait(timeout=10)
            except BaseException as e:result['network_cleanup_error']=str(e);result['status']='FAILED'
        if result['status']=='FAILED':
            try:
                with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00')) as console:
                    info=exchange(console,b'INFO\n',time.monotonic()+5,lambda k,v:emit('cleanup_'+k,v),False)
                    require(info['device_id']==DEVICE and info['status']['boot_id']==boot,'Cleanup identity')
                    ack=exchange(console,b'ABORT\n',time.monotonic()+5,lambda k,v:emit('cleanup_'+k,v),False);require(ack.get('ok'),'Console abort')
                with exclusive_port(Path(f'/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if02')) as cleanup_fd:
                    cleanup_peer=USB(cleanup_fd,boot,emit,lambda: require(time.time_ns()<p['cleanup_deadline_utc_ns'],'Cleanup deadline'))
                    for op,body,rid in [('HELLO',dict(versions=['WTP/1'],client_name='LOAD-reply-cleanup',client_version='1'),'f1'*16),('CLAIM',dict(owner_id=p['owner_id'],lease_ms=5000),'f2'*16),('RELEASE',{},'f3'*16)]:
                        cleanup_peer.ask(request(op,body,rid),'cleanup-'+op.lower())
            except BaseException as e:result['cleanup_error']=str(e)
        if errors:
            result['status']='FAILED';result['observer_errors']=errors
        try:
            final=inventory(root,p,'final-a');inactive(final);healthy(final['info'],boot)
            result['final_a_authority_verified']=True
        except BaseException as e:result['final_a_authority_error']=str(e);result['status']='FAILED'
        try:
            final_b=inventory(root,p,'final-b',True);inactive(final_b)
            before_b=finished(root/'before-b.stdout','READ_ONLY_INVENTORY')
            require(final_b['wtp']['STATUS']['boot_id']==before_b['wtp']['STATUS']['boot_id'] and configuration(final_b)==configuration(before_b),'B unchanged')
            result['final_b_authority_verified']=True
        except BaseException as e:result['final_b_authority_error']=str(e);result['status']='FAILED'
        try:fixture.cleanup()
        except BaseException as e:result['fixture_cleanup_error']=str(e);result['status']='FAILED'
        save(root/'run-result.json',result);emit('finish',result)

def admit(root,p,emit,check):
    require(p['scope'] in [CONTINUATION,RECOVERY] and not (root/'deployment.json').exists(),'Single retained admission')
    check()
    require(digest(root/'prior/test-packet.json')==p['prior_packet_sha256'],'Prior packet')
    prior=json.loads((root/'prior/test-packet.json').read_text())
    require(prior['host_boot_id']==p['host_boot_id'] and prior['image_sha256']==p['image_sha256'],'Same host/image')
    before=inventory(root,p,'before-a');before_b=inventory(root,p,'before-b',True)
    inactive(before);inactive(before_b);healthy(before['info'],p['expected_boot'])
    expected_records=[] if p['scope']==RECOVERY and p['prepare_retained'] else finished(root/'prior/post-restoration-a.stdout','READ_ONLY_INVENTORY')['wtp']['STATUS']['terminal_records']
    require(before['wtp']['STATUS']['terminal_records']==expected_records,'Retained preparation admission')
    # The earlier preparation may expire; only the explicitly selected replacement is permitted.
    for value,name in [(before,'a'),(before_b,'b')]:
        old=finished(root/('prior/post-restoration-'+name+'.stdout'),'READ_ONLY_INVENTORY')
        require(configuration(value)==configuration(old) and value['wtp']['STATUS']['boot_id']==old['wtp']['STATUS']['boot_id'] and value['info']['revision']==old['info']['revision'],'Retained board/configuration identity')
    state=dict(bootsel_commands=0,flashes_started=0,boot_id=p['expected_boot'],status='RETAINED_CANDIDATE_VERIFIED')
    save(root/'deployment.json',state);emit('admission',state)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=['deploy','admit','run','network']);parser.add_argument('--root',type=Path,required=True);parser.add_argument('--packet-sha256',required=True);parser.add_argument('--run',action='store_true');a=parser.parse_args()
    if not a.run:print('Plan only; no device or network access.');return
    root=a.root.resolve(strict=True);require(digest(root/'test-packet.json')==a.packet_sha256,'Frozen packet hash');p=validate_packet(json.loads((root/'test-packet.json').read_text()));require(str(root)==p['root'],'Private root identity')
    for path,sha in p['stage_sha256'].items():require((root/path).resolve().is_relative_to(root) and digest(root/path)==sha,'Frozen helper/input hash')
    require(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==p['host_boot_id'],'Host boot identity')
    os.umask(0o077);emit=Journal(root/(a.mode+'.jsonl'))
    def check():require(time.time_ns()<p['work_deadline_utc_ns'] and time.monotonic_ns()<p['host_work_deadline_monotonic_ns'],'Original work deadline')
    def terminate(*_):raise TimeoutError('Bounded supervisor requested cleanup')
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
    check();emit('start',dict(packet_sha256=a.packet_sha256,source=SOURCE))
    try:
        globals()[a.mode](root,p,emit,check)
        if a.mode=='network':save(root/'network-result.json',dict(status='COMPLETE'))
    except BaseException as e:
        if a.mode=='network':save(root/'network-result.json',dict(status='FAILED',error=str(e)))
        emit('failure',dict(worker=a.mode,error=str(e)));raise
if __name__=='__main__':main()
