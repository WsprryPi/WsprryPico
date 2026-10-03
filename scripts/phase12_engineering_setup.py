#!/usr/bin/env python3
"""One-shot B-only inhibited engineering provisioning; explicit hardware opt-in.

Root owns backup, destructive transition to source2, exact deployment and final
source1 readback/restoration. This helper never flashes, resets or retries apply.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import time
from phase12_composition_audit import counter
from phase12_recovery_device import DEVICE, SERIAL, CONSOLE, console, healthy, strict
from wsprrypico_ble import Client, ClientError, BluezBackend, canonical_profile, normalize_address, UUIDS


def require(ok, message):
    if not ok:
        raise ValueError(message)


def private_bytes(path, limit):
    path = Path(path)
    require(path.is_absolute(), 'absolute private path required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        s = os.fstat(fd)
        require(stat.S_ISREG(s.st_mode) and s.st_uid == os.geteuid() and
                not s.st_mode & 0o077 and 0 < s.st_size <= limit, 'private file permissions/size')
        value = os.read(fd, limit + 1)
        require(len(value) == s.st_size, 'private file changed/oversized')
        return value
    finally:
        os.close(fd)


def setup(source, boot, generation, address, profile, password, command, client,
          *, clock=time.monotonic, event=lambda value: None, prepare_pair=None):
    start = clock()
    def bound():
        require(clock()-start < 120, 'whole setup deadline')
    def guard(info):
        bound()
        healthy(info)
        require(info.get('ok') is True and info['revision'] == source[:12] and
                info['firmware'] == '0.0.0-devel' and info['status']['boot_id'] == boot,
                'source/boot mismatch')
        require(info['provisioning_source'] == 'unprovisioned' and
                counter(info['provisioning_generation'], 'provisioning_generation') == generation and
                info['access_state'] == 'healthy' and info['access_default_password'] is True,
                'healthy source2/default access prerequisite')
        require('phase12_fault_stage' not in info and
                counter(info['softap_session_inactivity_ms'], 'session inactivity') == 900000 and
                counter(info['softap_session_absolute_ms'], 'session absolute') == 43200000,
                'ordinary engineering candidate required')
        require(password == 'wspr-'+info['local_suffix'], 'private default password mismatch')
        return info
    try:
        require(re.fullmatch('[0-9a-f]{40}', source) and re.fullmatch('[0-9a-f]{32}', boot),
                'exact source/boot binding')
        require(type(generation) is int and 0 <= generation < 2**64-1, 'generation')
        require(strict(bytes(profile))['device_id'] == DEVICE, 'profile wrong device')
        guard(command('INFO'))
        if prepare_pair is not None:
            prepare_pair(address)
            guard(command('INFO'))
        response = command('ACCESS ENROLL '+DEVICE)
        require(response.get('ok') is True, 'enrollment rejected')
        event({'action':'enrollment_opened'})
        bound()
        identity = client.connect(address, DEVICE, allow_pairing=True)
        require(identity['device_id'] == DEVICE and identity['generation'] == generation,
                'BLE generation/device mismatch')
        bound()
        client.authorize(password)
        bound()
        client.synchronize_time()
        event({'action':'controller_time_submitted'})
        guard(command('INFO'))
        confirmations = 0
        def confirm(device):
            nonlocal confirmations
            require(device == DEVICE and confirmations == 0, 'confirmation device/repeat')
            guard(command('INFO'))
            reply = command('ACCESS CONFIRM PROFILE '+DEVICE)
            require(reply.get('ok') is True, 'profile confirmation rejected')
            confirmations += 1
            event({'action':'usb_profile_confirmed'})
        event({'action':'one_profile_apply_attempt', 'expected_generation':generation+1})
        result = client.provision(profile, password, confirm)
        bound()
        require(result == generation+1 and confirmations == 1, 'apply generation/confirmation mismatch')
        return {'status':'APPLY_ACKNOWLEDGED_READBACK_REQUIRED', 'device_id':DEVICE,
                'source_commit':source, 'before_boot_id':boot, 'expected_source':1,
                'expected_generation':result, 'rf_jobs':0,
                'pending':['root verifies new boot, exact source1 payload and generation',
                           'root verifies TLS principals/bonds and restoration']}
    finally:
        profile[:] = b'\0'*len(profile)
        client.close()


class RecordedBackend(BluezBackend):
    def __init__(self, adapter, emit):
        super().__init__(adapter)
        self.emit = emit
    def _async(self,interface,method,timeout,code,*arguments):
        backend=self
        class OriginalErrorTap:
            def __getattr__(self,name):
                def invoke(*args,**kwargs):
                    original=kwargs['error_handler']
                    def observed(error):
                        try:
                            backend.emit(dict(kind='private_host_ble_async_error',method=method,code=code,
                                dbus_name=error.get_dbus_name() if hasattr(error,'get_dbus_name') else type(error).__name__,
                                message=str(error)))
                        except Exception:pass
                        finally:original(error)
                    kwargs['error_handler']=observed
                    return getattr(interface,name)(*args,**kwargs)
                return invoke
        self.emit(dict(kind='host_ble_async_attempt',method=method,code=code))
        result=super()._async(OriginalErrorTap(),method,timeout,code,*arguments)
        self.emit(dict(kind='host_ble_async_complete',method=method,code=code))
        return result
    def prepare_new_pair(self,address):
        require(self.adapter_path=='/org/bluez/hci0' and
                normalize_address(address)=='88:A2:9E:0A:9D:8A','exact B host pairing cache')
        path=self.adapter_path+'/dev_'+address.upper().replace(':','_')
        objects=self._objects();properties=objects.get(path,{}).get(self.DEVICE)
        if properties is None:
            self.emit({'kind':'fresh_host_peer_absent','address':address,'removal_attempts':0})
            return
        require(str(properties.get('Address','')).upper()==address and
                str(properties.get('AddressType',''))=='public' and
                str(properties.get('Name',''))=='WsprryPico-0a9d89' and
                UUIDS['service'] in [str(v).lower() for v in properties.get('UUIDs',[])],
                'exact previously identified B host peer')
        require(not bool(properties.get('Connected',True)),'connected host peer cannot be removed')
        before={key:bool(properties[key]) for key in ('Paired','Bonded','Connected','ServicesResolved') if key in properties}
        self.emit({'kind':'fresh_host_peer_before','address':address,'path':path,'properties':before})
        self.emit({'kind':'one_host_peer_removal_attempt','path':path})
        adapter=self.dbus.Interface(self.bus.get_object(self.BLUEZ,self.adapter_path),self.ADAPTER)
        self._async(adapter,'RemoveDevice',10,'host_peer_removal_failed',self.dbus.ObjectPath(path))
        require(path not in self._objects(),'host peer removal not observed')
        self.emit({'kind':'fresh_host_peer_removed','address':address,'path':path,'removal_attempts':1})
    def read(self, uuid):
        value = super().read(uuid)
        self.emit({'kind':'private_gatt_read', 'uuid':uuid, 'hex':value.hex()})
        return value
    def _characteristic(self, uuid):
        path, interface = super()._characteristic(uuid)
        backend = self
        class SynchronousErrorTap:
            def __getattr__(self, method):
                original = getattr(interface, method)
                if method != 'WriteValue':return original
                def observed(*args, **kwargs):
                    try:return original(*args, **kwargs)
                    except Exception as error:
                        try:
                            backend.emit(dict(kind='private_host_ble_sync_error',method=method,
                                uuid=uuid,dbus_name=error.get_dbus_name() if hasattr(error,'get_dbus_name') else type(error).__name__,
                                message=str(error)))
                        except Exception:pass # Preserve uncertain delivery and the original write error.
                        raise
                return observed
        return path, SynchronousErrorTap()
    def write(self, uuid, value, response=True):
        self.emit({'kind':'private_gatt_write', 'uuid':uuid, 'hex':bytes(value).hex(),
                   'with_response':response})
        return super().write(uuid, value, response)
    def start_notify(self, uuid, callback):
        def recorded(value):
            self.emit({'kind':'private_gatt_notify', 'uuid':uuid, 'hex':bytes(value).hex()})
            callback(value)
        return super().start_notify(uuid, recorded)


class RecordedClient(Client):
    def __init__(self, backend, emit):
        super().__init__(backend, timeout=10, confirmation_timeout=25)
        self.emit = emit
    def exchange(self, request, *args, **kwargs):
        self.emit({'kind':'private_field_request', 'request':request})
        result = super().exchange(request, *args, **kwargs)
        self.emit({'kind':'private_field_reply', 'reply':result})
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-commit', required=True)
    p.add_argument('--boot-id', required=True)
    p.add_argument('--generation', type=int, required=True)
    p.add_argument('--address', required=True)
    p.add_argument('--adapter', default='hci0')
    p.add_argument('--console', required=True)
    p.add_argument('--profile', type=Path, required=True)
    p.add_argument('--profile-sha256', required=True)
    p.add_argument('--password-file', type=Path, required=True)
    p.add_argument('--private-wire-log', type=Path, required=True)
    p.add_argument('--target-bond-clearance-file', type=Path, required=True)
    p.add_argument('--target-bond-clearance-sha256', required=True)
    p.add_argument('--run', action='store_true')
    a = p.parse_args()
    if not a.run: p.error('explicit --run and separately authorized setup required')
    require(a.console == CONSOLE, 'exact B console required')
    address = normalize_address(a.address)
    raw = private_bytes(a.profile, 7168)
    require(re.fullmatch('[0-9a-f]{64}', a.profile_sha256) and
            hashlib.sha256(raw).hexdigest() == a.profile_sha256, 'exact profile hash required')
    profile = canonical_profile(strict(raw))
    password = private_bytes(a.password_file, 64).decode('ascii').removesuffix('\n')
    require(8 <= len(password) <= 63 and all(32 <= ord(c) <= 126 for c in password),
            'private password format')
    require(a.private_wire_log.is_absolute(), 'absolute private wire log')
    clearance_raw=private_bytes(a.target_bond_clearance_file,2048)
    require(re.fullmatch('[0-9a-f]{64}',a.target_bond_clearance_sha256) and
            hashlib.sha256(clearance_raw).hexdigest()==a.target_bond_clearance_sha256,'target bond clearance hash')
    clearance=strict(clearance_raw)
    require(clearance['schema']=='phase12-fresh-pair-clearance/1' and clearance['device_id']==DEVICE and
            clearance['serial']==SERIAL and clearance['source_commit']==a.source_commit and
            clearance['boot_id']==a.boot_id and type(clearance['generation']) is int and
            clearance['generation']==a.generation and type(clearance['bond_count']) is int and
            clearance['bond_count']==0 and type(clearance['profile_source']) is int and
            clearance['profile_source']==2 and clearance['readback_name']=='reset-after.bin' and
            re.fullmatch('[0-9a-f]{64}',clearance['readback_sha256']), 'fresh zero-bond source2 proof')
    reset_bytes=private_bytes(a.target_bond_clearance_file.parent/clearance['readback_name'],4194304)
    require(len(reset_bytes)==4194304 and hashlib.sha256(reset_bytes).hexdigest()==clearance['readback_sha256'],
            'original cold zero-bond readback hash')
    reset_bytes=b''
    old_mask = os.umask(0o077)
    lock = None
    old_handler = signal.getsignal(signal.SIGALRM)
    try:
        lock = os.open('/home/pi/.wsprrypico-recovery-action-'+SERIAL+'.lock',
                       os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with a.private_wire_log.open('x') as log:
            def emit(value):
                log.write(json.dumps(value, separators=(',', ':'))+'\n')
                log.flush(); os.fsync(log.fileno())
            def timeout(*_): raise TimeoutError('whole setup deadline')
            signal.signal(signal.SIGALRM, timeout)
            signal.alarm(120)
            client = RecordedClient(RecordedBackend(a.adapter, emit), emit)
            try:
                result = setup(a.source_commit, a.boot_id, a.generation, address,
                               profile, password, console, client, event=emit,
                               prepare_pair=client.backend.prepare_new_pair)
                emit(result)
            except Exception as error:
                emit({'status':'STOPPED_RESULT_UNKNOWN_NO_RETRY', 'error_type':type(error).__name__,
                      'code':error.code if isinstance(error, ClientError) else 'setup_failed',
                      'pending':'root independent USB/reserved readback and restore; never repeat apply'})
                raise
            finally:
                signal.alarm(0)
        print(json.dumps(result, sort_keys=True))
    finally:
        profile[:] = b'\0'*len(profile)
        password = ''
        signal.signal(signal.SIGALRM, old_handler)
        if lock is not None: os.close(lock)
        os.umask(old_mask)


if __name__ == '__main__':
    try: main()
    except Exception as error:
        # Never expose private profile, password, wire frame or exception text.
        print(json.dumps({'status':'STOPPED_NO_RETRY', 'error_type':type(error).__name__}))
        raise SystemExit(1)
