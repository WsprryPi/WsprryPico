#!/usr/bin/env python3
"""Explicit, B-only actual-wire ordinary CONFIG/STATUS dispatcher; no import action."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import struct
import ssl
import sys
import termios
import threading
import time
import uuid
from contextlib import ExitStack

from phase12_engineering_flash_status import decode, dispatch
from phase12_engineering_composition import guard, validate_device_plan
from phase12_engineering_dispatch import AUTHORITY, save
from phase12_engineering_setup import private_bytes, RecordedBackend
from phase12_recovery_device import CONSOLE, SERIAL, DEVICE, require, strict
from phase12_consumer_composition import Evidence
from check_usb_target import port
from check_standalone_image import validate_uf2
from inhibited_network_acceptance import connect, context, check_caps
from rf_wtp import write_all
from validate_wtp_contract import frame
from wsprrypico_ble import Client, UUIDS


class CapturedFrames:
    """Retain original headers and payloads without resync or reconstruction."""
    def __init__(self):self.buffer=bytearray();self.frames=[];self.total=0
    def feed(self, value):
        self.total+=len(value);require(self.total<=262144,'wire capture 256KB bound')
        self.buffer.extend(value)
        while len(self.buffer)>=16:
            magic,size,_=struct.unpack('>8sII',self.buffer[:16])
            require(magic==b'WTPF\x01\x01\x00\x00' and 0<size<=65536,'actual frame header')
            if len(self.buffer)<16+size:return
            raw=bytes(self.buffer[:16+size]);del self.buffer[:16+size]
            decode(raw);self.frames.append(raw)
            require(len(self.frames)<=65,'64 events plus response bound')
    def matching(self, request):
        found=[]
        for raw in self.frames:
            msg=decode(raw)
            require(msg['protocol']=='WTP/1' and msg['session_id']==request['session_id'],'wire session/protocol')
            if msg['type']=='event':continue
            require(msg['type']=='response' and msg['op']==request['op'] and
                    msg['request_id']==request['request_id'],'actual response correlation')
            found.append(raw)
        require(len(found)==1 and not self.buffer,'one complete actual response')
        return found[0]


class WireChannel:
    def __init__(self, send, receive, evidence, carrier):
        self.send=send;self.receive=receive;self.evidence=evidence;self.carrier=carrier
        self.session=uuid.uuid4().hex
    def wire_exchange(self, op, body, deadline):
        deadline=min(deadline,time.monotonic()+5)
        require(time.monotonic()<deadline,'WTP deadline before send')
        request=dict(protocol='WTP/1',type='request',session_id=self.session,
                     request_id=uuid.uuid4().hex,op=op,body=body)
        raw=frame(json.dumps(request,separators=(',',':')).encode());capture=CapturedFrames()
        self.send(raw,deadline);self.evidence.record('wtp_tx',carrier=self.carrier,hex=raw.hex())
        while True:
            require(time.monotonic()<deadline,'actual WTP response deadline')
            chunk=self.receive(deadline);require(chunk,'WTP EOF')
            self.evidence.record('wtp_rx',carrier=self.carrier,hex=chunk.hex());capture.feed(chunk)
            if any(decode(w)['type']=='response' for w in capture.frames):break
        response=capture.matching(request)
        require(decode(response)['ok'] is True,'WTP refused')
        return raw,response
    def ready(self, boot, deadline):
        _,raw=self.wire_exchange('HELLO',dict(versions=['WTP/1'],client_name='phase12-flash-status',client_version='1'),deadline)
        hello=decode(raw)['body'];require(hello['device_id']==DEVICE and hello['boot_id']==boot and
                                       hello['selected_version']=='WTP/1','same B HELLO boot')
        _,raw=self.wire_exchange('CAPS',{},deadline);check_caps(decode(raw)['body'])


class DeadlineInterface:
    def __init__(self, interface, remaining):self.interface=interface;self.remaining=remaining
    def __getattr__(self,name):
        method=getattr(self.interface,name)
        def invoke(*args,**kwargs):
            kwargs['timeout']=self.remaining()
            # Introspection is disabled; declare GATT option dictionaries explicitly.
            if name=='ReadValue':kwargs['signature']='a{sv}'
            elif name=='WriteValue':kwargs['signature']='aya{sv}'
            return method(*args,**kwargs)
        return invoke


class NoIntrospectionBus:
    def __init__(self,bus):self.bus=bus
    def __getattr__(self,name):return getattr(self.bus,name)
    def get_object(self,*args,**kwargs):
        kwargs['introspect']=False
        return self.bus.get_object(*args,**kwargs)


class DeadlineBackend(RecordedBackend):
    """Retained-bond BlueZ adapter with explicit absolute DBus deadlines."""
    def __init__(self,adapter,emit,deadline):
        self.deadline=deadline
        super().__init__(adapter,emit)
        self.bus=NoIntrospectionBus(self.bus)
    def remaining(self):
        remaining=self.deadline-time.monotonic()
        require(remaining>0,'BLE absolute deadline')
        return min(5,remaining)
    def interface(self,path,kind):
        self.remaining()
        obj=self.bus.get_object(self.BLUEZ,path,introspect=False)
        return DeadlineInterface(self.dbus.Interface(obj,kind),self.remaining)
    def _objects(self):return self.interface('/',self.OBJECT_MANAGER).GetManagedObjects()
    def _property(self,path,interface,name):return self.interface(path,self.PROPERTIES).Get(interface,name)
    def _characteristic(self,uuid):
        path=self.characteristics.get(uuid);require(path,'BLE characteristic missing')
        return path,self.interface(path,self.CHARACTERISTIC)
    def _find_device(self,address,service_uuid,timeout):
        # This case must use the retained, already known B bond; no discovery/pairing.
        path=f"{self.adapter_path}/dev_{address.replace(':','_')}"
        require(path in self._objects(),'retained B must already be known to BlueZ')
        return path
    def _async(self,interface,method,timeout,code,*arguments):
        bounded=DeadlineInterface(interface,self.remaining)
        return super()._async(bounded,method,min(timeout,self.remaining()),code,*arguments)
    def _wait(self,predicate,timeout,code):
        return super()._wait(predicate,min(timeout,self.remaining()),code)
    def pump(self,seconds):
        end=time.monotonic()+min(seconds,self.remaining())
        while time.monotonic()<end:
            self.remaining()
            if self.context.pending():self.context.iteration(False)
            else:time.sleep(min(.01,max(0,end-time.monotonic())))
    def close(self):
        # Local signal teardown plus one finite disconnect; pairing agents are absent.
        for match in self.matches:
            try:match.remove()
            except Exception:pass
        self.matches.clear()
        if self.device_path:
            try:
                obj=self.bus.get_object(self.BLUEZ,self.device_path,introspect=False)
                self.dbus.Interface(obj,self.DEVICE).Disconnect(timeout=1)
            except Exception:pass
        self.device_path='';self.characteristics.clear()


class DeadlineClient(Client):
    def _wait(self,responses,request_id,code,timeout=None):
        # The wait budget begins AFTER all fragments, using only remaining time.
        remaining=self.backend.remaining()
        selected=self.timeout if timeout is None else timeout
        return super()._wait(responses,request_id,code,min(selected,remaining))


class BleWire:
    def __init__(self, client, evidence):
        self.client=client;self.evidence=evidence;self.tx=bytearray();self.rx=CapturedFrames();self.active=False
    def emitted(self, value):
        if not self.active:return
        raw=bytes.fromhex(value['hex'])
        if value['kind']=='private_gatt_write' and value['uuid']==UUIDS['wtpCommand']:
            self.tx.extend(raw);require(len(self.tx)<=65552,'BLE request bound')
        elif value['kind']=='private_gatt_notify' and value['uuid']==UUIDS['wtpStatus']:
            self.rx.feed(raw)
    def wire_exchange(self, op, body, deadline):
        require(time.monotonic()<deadline,'BLE deadline')
        self.client.backend.deadline=min(deadline,time.monotonic()+5)
        self.client.timeout=max(.001,min(5,deadline-time.monotonic()))
        self.tx=bytearray();self.rx=CapturedFrames();self.active=True
        try:self.client.wtp_exchange(op,body)
        finally:self.active=False
        request=bytes(self.tx);message=decode(request);response=self.rx.matching(message)
        require(message['op']==op and message['body']==body and decode(response)['ok'] is True,'actual BLE exchange')
        self.evidence.record('wtp_exchange',carrier='ble',request_hex=request.hex(),response_hex=response.hex())
        return request,response


class RawConsole:
    def __init__(self,evidence):self.lock=threading.RLock();self.evidence=evidence
    def __call__(self,command,deadline):
        require(command=='INFO' or command.startswith(('ACTIVITYTRACE ','CONFIG ')),'console operation whitelist')
        deadline=min(deadline,time.monotonic()+5)
        require(time.monotonic()<deadline,'console deadline before action')
        with self.lock:
            action=os.open('/home/pi/.wsprrypico-recovery-action-'+SERIAL+'.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
            try:
                while True:
                    try:fcntl.flock(action,fcntl.LOCK_EX|fcntl.LOCK_NB);break
                    except BlockingIOError:
                        require(time.monotonic()<deadline,'action lock deadline');time.sleep(.02)
                with port(CONSOLE) as fd:
                    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);termios.tcflush(fd,termios.TCIFLUSH)
                    require(time.monotonic()<deadline,'console deadline before write')
                    written=command.encode()+b'\n';write_all(fd,written,deadline)
                    self.evidence.record('console_tx',hex=written.hex());raw=bytearray()
                    while time.monotonic()<deadline:
                        if select.select([fd],[],[],max(0,deadline-time.monotonic()))[0]:
                            value=os.read(fd,1);require(value,'console EOF');raw.extend(value)
                            require(len(raw)<=16384,'console line bound')
                            if value==b'\n':
                                if raw.strip():
                                    self.evidence.record('console_rx',hex=raw.hex());return strict(bytes(raw)),bytes(raw)
                                raw.clear()
                    raise TimeoutError('console response deadline')
            finally:os.close(action)


def bound_plan(request):
    require(request['authority']==AUTHORITY,'authority')
    root=Path(request['root']);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and
                                      root.is_dir() and not root.is_symlink(),'private root')
    plan=request['plan'];require(plan['source_commit']==request['source_commit'],'source binding')
    for key in ('image_path','profile_path','config_path','password_file','ca','cert','key','contender_cert','contender_key'):
        path=Path(plan[key]);require(path.parent==root and not path.is_symlink(),'exact private staged file')
    manifest_raw=private_bytes(root/'preparation-manifest.json',262144)
    require(hashlib.sha256(manifest_raw).hexdigest()==request['manifest_sha256'],'manifest hash')
    manifest=strict(manifest_raw);candidates=[c for c in manifest['candidates'] if c['role']=='engineering']
    require(len(candidates)==1 and manifest['source_commit']==plan['source_commit'],'ordinary engineering source')
    candidate=candidates[0]
    require(candidate['target']=='WsprryPico' and candidate['fault_stage']==0 and candidate['lan_mode']=='tls' and
            candidate['uf2']['sha256']==plan['image_sha256'],'ordinary inhibited image')
    image=private_bytes(Path(plan['image_path']),4*1024*1024);validate_uf2(image)
    raw=private_bytes(Path(plan['config_path']),16384)
    require(hashlib.sha256(raw).hexdigest()==plan['config_sha256'],'exact saved disabled CONFIG hash')
    config=strict(raw);require(config['enabled'] is False,'disabled CONFIG')
    args,_,password=validate_device_plan(plan)
    profile=strict(private_bytes(Path(plan['profile_path']),16384))
    require(profile['tls']['hostname']==plan['hostname'] and profile['tls']['port']==plan['port'] and
            profile['tls']['client_ca']==private_bytes(Path(plan['ca']),16384).decode('ascii'), 'exact selected TLS identity')
    require(hashlib.sha256(ssl.PEM_cert_to_DER_cert(profile['tls']['server_certificate'])).hexdigest()==
            plan['server_sha256'],'selected profile server fingerprint')
    for key in ('ca','cert','key'):
        require(hashlib.sha256(private_bytes(Path(plan[key]),16384)).hexdigest()==plan['credential_hashes'][key],
                'client credential hash')
    return root,plan,config,args,password


def run(request):
    root,plan,config,args,password=bound_plan(request);setup_deadline=time.monotonic()+180
    base_evidence=Evidence(root/'flash-status-wire.jsonl')
    class LockedEvidence:
        def __init__(self):self.lock=threading.RLock()
        def record(self,kind,**value):
            with self.lock:base_evidence.record(kind,**value)
        def close(self):
            with self.lock:base_evidence.close()
    evidence=LockedEvidence()
    class TLSLog:
        def record(self,kind,value):evidence.record(kind,value=value)
    try:
        with ExitStack() as stack:
            con=RawConsole(evidence)
            def observe():return con('INFO',min(setup_deadline,time.monotonic()+5))
            info,_=observe();guard(info,plan,empty=True)
            require(info['network']['ipv4']==plan['address'] and plan['address'].startswith('192.168.84.') and
                    info['network']['link_status']==3 and info['status']['clock_state']=='synchronized' and
                    info['network']['ntp_server']=='192.168.84.1' and info['network']['ntp_address']=='192.168.84.1' and
                    int(info['network']['accepted'])>0,'isolated current SNTP station/TLS readiness')
            require(int(info['network_active_connections'])==0 and int(info['network_pending_connections'])==0,'exclusive TLS baseline')
            require(time.monotonic()+10<=setup_deadline,'TLS connect fits setup deadline')
            stream=connect(args,context(args),'wtp/1',TLSLog());stack.callback(stream.close)
            def tls_send(raw,end):stream.settimeout(max(.001,end-time.monotonic()));stream.sendall(raw)
            def tls_receive(end):stream.settimeout(max(.001,end-time.monotonic()));return stream.recv(65552)
            tls=WireChannel(tls_send,tls_receive,evidence,'tls');tls.ready(plan['boot_id'],setup_deadline)
            fd=stack.enter_context(port(plan['wtp_console']));fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            def usb_receive(end):
                require(select.select([fd],[],[],max(0,end-time.monotonic()))[0],'USB response deadline')
                return os.read(fd,65552)
            usb=WireChannel(lambda raw,end:write_all(fd,raw,end),usb_receive,evidence,'usb');usb.ready(plan['boot_id'],setup_deadline)
            holder={}
            def emitted(value):
                # Field authentication credentials are never retained; only WTP bytes.
                if value.get('kind') in ('private_host_ble_async_error','private_host_ble_sync_error'):
                    evidence.record('ble_host_error',value=value)
                if value.get('uuid') in (UUIDS['wtpCommand'],UUIDS['wtpStatus']):
                    evidence.record('ble_wtp',value=value)
                    if 'peer' in holder:holder['peer'].emitted(value)
            client=DeadlineClient(DeadlineBackend(plan.get('adapter','hci0'),emitted,setup_deadline),timeout=5);stack.callback(client.close)
            ble=BleWire(client,evidence);holder['peer']=ble
            ident=client.connect(plan['ble_address'],DEVICE,allow_pairing=False)
            require(ident['generation']==plan['profile_generation'],'BLE retained generation')
            client.authorize(password);hello=client.enable_local_control()
            require(hello['boot_id']==plan['boot_id'],'BLE same boot')
            _,raw=ble.wire_exchange('CAPS',{},setup_deadline);check_caps(decode(raw)['body'])
            require(time.monotonic()<setup_deadline,'180 second setup deadline')
            # INFO callback during measurement has its own 5s bound, not expired setup timer.
            result=dispatch(plan,config,dict(usb=usb,ble=ble,tls=tls),lambda:con('INFO',time.monotonic()+5),con)
            save(root/'flash-status-result.json',result);return result
    finally:password='';evidence.close()


def main():
    os.umask(0o077);request=strict(sys.stdin.buffer.readline(65537))
    def stopped(*_):raise KeyboardInterrupt('flash STATUS parent lost/deadline')
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGALRM,stopped);signal.alarm(300)
    def watch():
        if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=watch,daemon=True).start()
    print(json.dumps(run(request)),flush=True)


if __name__=='__main__':main()
