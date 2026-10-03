#!/usr/bin/env python3
"""One existing B peer attempt after reset; no pairing, login or enrollment."""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time
from phase12_engineering_flash_status_dispatch import DeadlineBackend, DeadlineInterface
from phase12_engineering_setup import private_bytes
from phase12_serial_observer import Observer
from phase12_recovery_orchestrator import safe_info
from phase12_recovery_device import DEVICE, strict, require
from phase12_consumer_composition import Evidence
from phase12_engineering_dispatch import AUTHORITY, save
from wsprrypico_ble import Client


def qualifies(error):
    return error.get('method') in ('Connect','ReadValue','StartNotify') and (error['name'] in ('org.bluez.Error.AuthenticationFailed','org.bluez.Error.AuthenticationRejected') or (
        error['name'].startswith('org.bluez.Error.') and
        error['message'].strip().casefold() in ('pin or key missing','key missing','authentication failed: pin or key missing')))


class CaptureInterface:
    def __init__(self,interface,capture):self.interface=interface;self.capture=capture
    def __getattr__(self,name):
        method=getattr(self.interface,name)
        def call(*args,**kwargs):
            try:return method(*args,**kwargs)
            except Exception as error:self.capture(name,error);raise
        return call


class RefusalBackend(DeadlineBackend):
    def __init__(self,*args,**kwargs):self.errors=[];super().__init__(*args,**kwargs)
    def capture(self,method,error):
        name=error.get_dbus_name() if callable(getattr(error,'get_dbus_name',None)) else ''
        message=error.get_dbus_message() if callable(getattr(error,'get_dbus_message',None)) else ''
        value=dict(method=method,name=str(name),message=str(message))
        self.errors.append(value);self.emit(dict(kind='actual_dbus_refusal',**value))
    def interface(self,path,kind):return CaptureInterface(super().interface(path,kind),self.capture)
    def _register_agent(self):raise ValueError('pairing agent prohibited')
    def _async(self,interface,method,timeout,code,*arguments):
        require(method!='Pair','no pairing attempt')
        state={}
        def failed(error):self.capture(method,error);state.update(done=True,error=error)
        DeadlineInterface(interface,self.remaining).__getattr__(method)(*arguments,
            reply_handler=lambda *unused:state.update(done=True),error_handler=failed)
        self._wait(lambda:bool(state.get('done')),min(timeout,self.remaining()),code)
        if 'error' in state:raise state['error']


def attempt(client,backend,address,deadline):
    """One Client.connect with retained host bond; classify only real DBus errors."""
    backend.deadline=deadline;client.timeout=min(5,backend.remaining())
    outcome='INCONCLUSIVE';connected=False;exception=''
    try:
        client.connect(address,DEVICE,allow_pairing=False);connected=True
    except Exception as error:exception=type(error).__name__
    refusal=next((error for error in backend.errors if qualifies(error)),None)
    # A successful encrypted identity read is not a cryptographic rejection.
    observed=refusal is not None and not connected
    if observed:outcome='EXISTING_PEER_SECURITY_REFUSAL_REVIEW_REQUIRED'
    return dict(status=outcome,old_peer_attempts=1,cryptographic_peer_refusal_observed=observed,
                connected=connected,exception_type=exception,actual_dbus_errors=list(backend.errors),
                pairing_attempts=0,enrollment_attempts=0,rf_jobs=0)


def run(request):
    require(request['authority']==AUTHORITY,'authority')
    root=Path(request['root']);require(re.fullmatch('/home/pi/phase12-recovery-[0-9a-f]{32}',str(root)) and
                                      root.is_dir() and not root.is_symlink(),'private root')
    manifest_raw=private_bytes(root/'preparation-manifest.json',262144)
    require(hashlib.sha256(manifest_raw).hexdigest()==request['manifest_sha256'],'manifest hash')
    manifest=strict(manifest_raw);candidate=next(c for c in manifest['candidates'] if c['role']=='engineering')
    require(manifest['source_commit']==request['source_commit'] and candidate['fault_stage']==0 and
            candidate['target']=='WsprryPico' and candidate['lan_mode']=='tls','ordinary engineering candidate')
    require(hashlib.sha256(private_bytes(root/'engineering.uf2',4*1024*1024)).hexdigest()==candidate['uf2']['sha256'],
            'exact ordinary image')
    evidence=Evidence(root/'single-bond-old-peer-wire.jsonl');client=None;deadline=time.monotonic()+19
    observer=Observer()
    def checked_info():
        info,raw=observer();require(strict(raw)==info,'actual INFO wire');safe_info(info,request['source_commit'][:12],0,False)
        require(info['status']['boot_id']==request['boot_id'] and info['provisioning_source']=='unprovisioned' and
                info['ble_enrollment_open'] is False,'same source2 boot with enrollment closed')
        evidence.record('actual_info',raw_hex=raw.hex());return info
    try:
        checked_info()
        backend=RefusalBackend('hci0',lambda value:evidence.record('ble',value=value),deadline)
        client=Client(backend,timeout=5)
        result=attempt(client,backend,request['ble_address'],deadline)
        checked_info();require(time.monotonic()<deadline,'single peer20s deadline')
        save(root/'single-bond-old-peer-result.json',result);return result
    finally:
        if client is not None:client.close()
        evidence.close()


def main():
    os.umask(0o077);request=strict(sys.stdin.buffer.readline(65537))
    def stopped(*_):raise KeyboardInterrupt('single peer parent/deadline')
    signal.signal(signal.SIGTERM,stopped);signal.signal(signal.SIGALRM,stopped);signal.alarm(20)
    def watch():
        if os.read(sys.stdin.fileno(),1)==b'':os.kill(os.getpid(),signal.SIGTERM)
    threading.Thread(target=watch,daemon=True).start()
    print(json.dumps(run(request)),flush=True)


if __name__=='__main__':main()
