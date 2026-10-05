#!/usr/bin/env python3
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_setup as runner
from wsprrypico_ble import ClientError

class Client:
    def __init__(self):
        self.actions=[];self.generation=6;self.fail=False;self.confirm=runner.DEVICE
    def connect(self,*a,**kw):
        self.actions.append('connect')
        return {'device_id':runner.DEVICE,'generation':self.generation}
    def authorize(self,password): self.actions.append('authorize')
    def synchronize_time(self): self.actions.append('time')
    def provision(self,profile,password,confirm):
        self.actions.append('apply')
        confirm(self.confirm)
        if self.fail: raise ClientError('timeout')
        return 7
    def close(self):self.actions.append('close')

class Tests(unittest.TestCase):
    def test_original_bluez_error_is_retained_without_retry_or_error_remapping(self):
        rows=[];calls=[];backend=object.__new__(runner.RecordedBackend);backend.emit=rows.append
        backend._wait=lambda predicate,timeout,code:self.assertTrue(predicate())
        class OriginalError(Exception):
            def get_dbus_name(self):return 'org.bluez.Error.AuthenticationFailed'
        class Interface:
            def Pair(self,**kwargs):
                calls.append('Pair');kwargs['error_handler'](OriginalError('actual host refusal'))
        with self.assertRaises(ClientError) as caught:backend._async(Interface(),'Pair',10,'pairing_failed')
        self.assertEqual(caught.exception.code,'pairing_failed');self.assertEqual(calls,['Pair'])
        self.assertEqual(rows[-1]['dbus_name'],'org.bluez.Error.AuthenticationFailed')
        self.assertEqual(rows[-1]['message'],'actual host refusal')
    def test_failed_error_capture_still_delivers_original_completion(self):
        backend=object.__new__(runner.RecordedBackend)
        def emit(value):
            if value['kind']=='private_host_ble_async_error':raise OSError('capture unavailable')
        backend.emit=emit;backend._wait=lambda predicate,timeout,code:self.assertTrue(predicate())
        class Interface:
            def Pair(self,**kwargs):kwargs['error_handler'](RuntimeError('original host refusal'))
        with self.assertRaises(ClientError) as caught:backend._async(Interface(),'Pair',10,'pairing_failed')
        self.assertEqual(caught.exception.code,'pairing_failed')
    def setUp(self):
        self.info={'ok':True,'device_id':runner.DEVICE,'revision':'1'*12,'firmware':'0.0.0-devel',
            'status':{'boot_id':'2'*32,'engine':'inhibited-standalone-simulator',
                      'enabled':False,'output_active':False,'state':'empty','owner_id':None,
                      'job_id':None,'storage_healthy':True},
            'access_state':'healthy','access_default_password':True,'local_suffix':'0a60df',
            'provisioning_source':'unprovisioned','provisioning_generation':'6',
            'softap_session_inactivity_ms':'900000','softap_session_absolute_ms':'43200000'}
        self.commands=[];self.client=Client()
        self.profile=bytearray(('{"device_id":"'+runner.DEVICE+'"}').encode())
        self.clock=lambda:0
    def command(self,value):
        self.commands.append(value)
        return copy.deepcopy(self.info) if value=='INFO' else {'ok':True}
    def run_case(self):
        with patch('phase12_recovery_device.resource_health'):
            return runner.setup('1'*40,'2'*32,6,'AA:BB:CC:DD:EE:FF',self.profile,
                'wspr-0a60df',self.command,self.client,clock=self.clock)
    def test_one_apply_requires_root_readback_and_scrubs(self):
        result=self.run_case()
        self.assertEqual(result['expected_generation'],7)
        self.assertEqual(result['status'],'APPLY_ACKNOWLEDGED_READBACK_REQUIRED')
        self.assertEqual(self.client.actions,['connect','authorize','time','apply','close'])
        self.assertEqual(self.commands.count('ACCESS ENROLL '+runner.DEVICE),1)
        self.assertEqual(self.commands.count('ACCESS CONFIRM PROFILE '+runner.DEVICE),1)
        self.assertTrue(all(b==0 for b in self.profile))
    def test_wrong_boot_or_source_prevents_enrollment(self):
        for key,value in [('provisioning_source','consumer_preclock'),('revision','3'*12)]:
            self.setUp();self.info[key]=value
            with self.assertRaises(ValueError):self.run_case()
            self.assertEqual(self.commands,['INFO'])
            self.assertEqual(self.client.actions,['close'])
    def test_active_output_or_owner_prevents_enrollment(self):
        for key,value in [('output_active',True),('owner_id','3'*32),('enabled',True)]:
            self.setUp();self.info['status'][key]=value
            with self.assertRaises(ValueError):self.run_case()
            self.assertEqual(self.commands,['INFO'])
    def test_generation_change_prevents_authorize(self):
        self.client.generation=7
        with self.assertRaises(ValueError):self.run_case()
        self.assertNotIn('authorize',self.client.actions)
    def test_wrong_device_confirmation_refused(self):
        self.client.confirm='3'*32
        with self.assertRaises(ValueError):self.run_case()
        self.assertFalse(any(c.startswith('ACCESS CONFIRM') for c in self.commands))
    def test_unknown_result_never_retries_apply(self):
        self.client.fail=True
        with self.assertRaises(ClientError):self.run_case()
        self.assertEqual(self.client.actions.count('apply'),1)
        self.assertEqual(self.client.actions[-1],'close')

    def test_fresh_peer_preparation_requires_source2_guard_before_enrollment(self):
        actions=[]
        def prepare(address):
            self.assertEqual(self.commands,['INFO']);actions.append(address)
        with patch('phase12_recovery_device.resource_health'):
            result=runner.setup('1'*40,'2'*32,6,'AA:BB:CC:DD:EE:FF',self.profile,
                'wspr-0a60df',self.command,self.client,clock=self.clock,prepare_pair=prepare)
        self.assertEqual(actions,['AA:BB:CC:DD:EE:FF']);self.assertEqual(self.commands[:2],['INFO','INFO'])
        self.assertEqual(result['expected_generation'],7)
        self.setUp();self.info['provisioning_source']='consumer_preclock';actions.clear()
        with patch('phase12_recovery_device.resource_health'),self.assertRaises(ValueError):
            runner.setup('1'*40,'2'*32,6,'AA:BB:CC:DD:EE:FF',self.profile,
                'wspr-0a60df',self.command,self.client,clock=self.clock,prepare_pair=prepare)
        self.assertEqual(actions,[]);self.assertEqual(self.commands,['INFO'])

    def test_uncertain_host_peer_removal_prevents_enrollment_and_apply(self):
        def prepare(address):raise ClientError('host_peer_removal_failed')
        with patch('phase12_recovery_device.resource_health'),self.assertRaises(ClientError):
            runner.setup('1'*40,'2'*32,6,'AA:BB:CC:DD:EE:FF',self.profile,
                'wspr-0a60df',self.command,self.client,clock=self.clock,prepare_pair=prepare)
        self.assertEqual(self.commands,['INFO']);self.assertEqual(self.client.actions,['close'])

    def host_backend(self,properties):
        from unittest.mock import MagicMock
        backend=object.__new__(runner.RecordedBackend);backend.adapter_path='/org/bluez/hci0'
        backend.bus=MagicMock();backend.dbus=MagicMock();backend.dbus.ObjectPath.side_effect=lambda path:path
        backend.emit=MagicMock();backend._async=MagicMock()
        path=backend.adapter_path+'/dev_88_A2_9E_0A_9D_8A'
        objects={} if properties is None else {path:{backend.DEVICE:properties},'/unrelated':{backend.DEVICE:{'Address':'other','Paired':True}}}
        backend._objects=MagicMock(side_effect=[objects,{'/unrelated':objects.get('/unrelated',{})}])
        return backend,path

    def test_exact_disconnected_stale_peer_is_removed_once(self):
        properties=dict(Address='88:A2:9E:0A:9D:8A',AddressType='public',Name='WsprryPico-0a9d89',
            UUIDs=[runner.UUIDS['service']],Paired=True,Bonded=True,Connected=False,ServicesResolved=False)
        backend,path=self.host_backend(properties);backend.prepare_new_pair(properties['Address'])
        backend._async.assert_called_once()
        self.assertEqual(backend._async.call_args.args[1:],('RemoveDevice',10,'host_peer_removal_failed',path))
        self.assertEqual(backend.emit.call_args.args[0]['kind'],'fresh_host_peer_removed')

    def test_absent_peer_and_unsafe_cached_peer_never_remove_any_record(self):
        backend,path=self.host_backend(None);backend.prepare_new_pair('88:A2:9E:0A:9D:8A');backend._async.assert_not_called()
        base=dict(Address='88:A2:9E:0A:9D:8A',AddressType='public',Name='WsprryPico-0a9d89',
            UUIDs=[runner.UUIDS['service']],Connected=False)
        for changes in ({'Connected':True},{'Address':'other'},{'Name':'other'},{'AddressType':'random'},{'UUIDs':[]}):
            backend,path=self.host_backend(dict(base,**changes))
            with self.subTest(changes=changes),self.assertRaises(ValueError):backend.prepare_new_pair('88:A2:9E:0A:9D:8A')
            backend._async.assert_not_called()

    def test_removal_error_or_missing_after_proof_never_retries(self):
        base=dict(Address='88:A2:9E:0A:9D:8A',AddressType='public',Name='WsprryPico-0a9d89',
            UUIDs=[runner.UUIDS['service']],Connected=False)
        for uncertain in (True,False):
            backend,path=self.host_backend(base)
            if uncertain:backend._async.side_effect=ClientError('host_peer_removal_failed')
            else:backend._objects.side_effect=None;backend._objects.return_value={path:{backend.DEVICE:base}}
            with self.subTest(uncertain=uncertain),self.assertRaises((ClientError,ValueError)):
                backend.prepare_new_pair('88:A2:9E:0A:9D:8A')
            self.assertEqual(backend._async.call_count,1)
    def test_deadline_prevents_further_hardware(self):
        samples=iter([0,0,121])
        self.clock=lambda:next(samples)
        with self.assertRaises(ValueError):self.run_case()
        self.assertNotIn('connect',self.client.actions)
    def test_unsafe_policy_wire_values_refused_before_enrollment(self):
        for key in ('softap_session_inactivity_ms','softap_session_absolute_ms'):
            for value in (True, 900000.0, -1, '0900000', '0', '15000',
                          '18446744073709551616', '900000\n'):
                self.setUp();self.info[key]=value
                with self.assertRaises(ValueError):self.run_case()
                self.assertEqual(self.commands,['INFO'])
                self.assertEqual(self.client.actions,['close'])
    def test_unsafe_generation_wire_refused_before_enrollment(self):
        for value in (True, 6.0, '06', '-1', '18446744073709551616'):
            self.setUp();self.info['provisioning_generation']=value
            with self.assertRaises(ValueError):self.run_case()
            self.assertEqual(self.commands,['INFO'])
    def test_unsafe_private_file_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'password';p.write_text('private-pass');p.chmod(0o644)
            with self.assertRaises(ValueError):runner.private_bytes(p,64)
            p.chmod(0o600);self.assertEqual(runner.private_bytes(p,64),b'private-pass')
            link=Path(tmp)/'link';link.symlink_to(p)
            with self.assertRaises(OSError):runner.private_bytes(link,64)

class BoundSetupTests(unittest.TestCase):
    setUp=Tests.setUp
    host_backend=Tests.host_backend
    command=Tests.command
    run_case=Tests.run_case
    def test_bound_cached_name_mode_keeps_exact_B_public_service_and_single_removal(self):
        base=dict(Address='88:A2:9E:0A:9D:8A',AddressType='public',Name='retained-cache-name',UUIDs=[runner.UUIDS['service']],Connected=False)
        backend,path=self.host_backend(base);backend.prepare_new_pair(base['Address'],expected_address=base['Address']);self.assertEqual(backend._async.call_count,1)
        before=[x.args[0] for x in backend.emit.call_args_list if x.args[0]['kind']=='fresh_host_peer_before'][0];self.assertEqual(before['actual_name'],base['Name']);self.assertFalse(before['fresh_advertisement_proven'])
        backend,path=self.host_backend(base)
        with self.assertRaises(ValueError):backend.prepare_new_pair(base['Address'])
        backend._async.assert_not_called()
        for changed in ({'Connected':True},{'AddressType':'random'},{'UUIDs':[]},{'Address':'88:A2:9E:0A:60:E0'}):
            backend,path=self.host_backend(dict(base,**changed))
            with self.subTest(changed=changed),self.assertRaises(ValueError):backend.prepare_new_pair(base['Address'],expected_address=base['Address'])
            backend._async.assert_not_called()
    def test_exact_actual_gatt_identity_and_USB_bookend_precede_field_write(self):
        for identity in ({'device_id':'3'*32,'generation':6},{'device_id':runner.DEVICE,'generation':7},{'device_id':runner.DEVICE,'generation':True}):
            self.setUp();self.client.connect=lambda *a,**kw:identity
            with self.subTest(identity=identity),self.assertRaises(ValueError):self.run_case()
            self.assertNotIn('authorize',self.client.actions);self.assertNotIn('apply',self.client.actions)
        self.setUp();events=[]
        def command(value):
            if value=='INFO' and 'connect' in self.client.actions:
                self.assertNotIn('authorize',self.client.actions) if not events else None
            return self.command(value)
        with patch('phase12_recovery_device.resource_health'):
            runner.setup('1'*40,'2'*32,6,'88:A2:9E:0A:9D:8A',self.profile,'wspr-0a60df',command,self.client,clock=self.clock,event=events.append)
        row=next(v for v in events if v.get('action')=='gatt_identity_verified_before_field_write');self.assertEqual(row['device_id'],runner.DEVICE);self.assertEqual(row['generation'],6);self.assertEqual(row['usb_boot_id'],'2'*32)

if __name__=='__main__':unittest.main()
