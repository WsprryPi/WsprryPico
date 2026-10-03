#!/usr/bin/env python3
"""Original target/host proof binding; injected only, no device operations."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import phase12_engineering_fixture as f
import phase12_populated_orchestrator as parent
from phase12_fixture_roles import role_map
from phase12_recovery_device import DEVICE

class Tests(unittest.TestCase):
    def exercise(self,*,change=None,late=False):
        directory=tempfile.TemporaryDirectory(prefix="target-proof-");self.addCleanup(directory.cleanup);root=Path(directory.name);roles=role_map();now=[0.0];commands=[]
        ssid='p12-'+'b'*12;name='p12-engineering-'+root.name.rsplit('-',1)[1];ap=dict(connection=name,ssid=ssid,bssid='e8:4e:06:ae:d7:09',interface='wlan2',frequency_mhz=2422,roles_sha256=roles['sha256'])
        for file,value in [('populated-network.json',dict(ssid=ssid)),('fixture-ap-proof.json',dict(mode='target',roles_sha256=roles['sha256'],ap=ap)),('fixture-management-before.json',{}),('manifest.json',dict(source_commit='b'*40))]:f.private_write(root/file,value)
        info=dict(device_id=DEVICE,revision='b'*12,provisioning_generation='7',provisioning_source='consumer_preclock',access_state='healthy',saved_consumer_profile=dict(network=dict(ssid=ssid)),network=dict(link_status=3,ipv4='192.168.84.89',station_mac='88:a2:9e:0a:9d:89'),status=dict(boot_id='a'*32,engine='inhibited-standalone-simulator',enabled=False,output_active=False,state='empty',clock_state='unsynchronized',owner_id=None,job_id=None,storage_healthy=True))
        if change:change(info)
        request=dict(phase='seed',remaining_s=160,source_commit='b'*40,boot_id='a'*32,generation=7)
        def observe():
            return info,json.dumps(info).encode()+b'\n'
        def run(argv,**kw):
            commands.append((argv,kw['timeout']))
            if 'GENERAL.CONNECTION' in argv:raw=name+'\n'
            elif 'connection' in argv:raw='\n'.join([ssid,'ap','3','wpa-psk','rsn','ccmp','ccmp'])+'\n'
            elif argv[-1]=='info':raw='Interface wlan2\n addr e8:4e:06:ae:d7:09\n ssid '+ssid+'\n type AP\n channel 3 (2422 MHz)\n'
            elif 'station' in argv:raw='Station 88:a2:9e:0a:9d:89 (on wlan2)\n authenticated: yes\n authorized: yes\n'
            elif 'address' in argv:raw=json.dumps([dict(ifname='wlan2',addr_info=[dict(family='inet',local='192.168.84.1',prefixlen=24)])])
            elif 'route' in argv:raw=json.dumps([dict(dst='192.168.84.0/24',dev='wlan2',prefsrc='192.168.84.1')])
            elif argv[-1].endswith('.leases'):raw='9999999999 88:a2:9e:0a:9d:89 192.168.84.89 target *\n'
            else:raise AssertionError(argv)
            if self.host_change:raw=self.host_change(argv,raw)
            if late:now[0]=31
            return f.subprocess.CompletedProcess(argv,0,raw,'')
        with patch.object(f,'management',return_value={}),patch('phase12_recovery_device.resource_health'):
            try:result=f.target_association_proof(root,roles,request,observe=observe,runner=run,clock=lambda:now[0]);error=None
            except ValueError as failure:result=None;error=failure
        receipt=json.loads((root/'target-ap-proof-seed.json').read_text())
        self.assertFalse(any(word in ('up','add','set','delete','join') for argv,_ in commands for word in argv))
        self.assertTrue(all(timeout<=5 for _,timeout in commands))
        return result,error,receipt,commands

    def setUp(self):self.host_change=None
    def test_original_same_boot_usb_and_exact_authorized_host_peer(self):
        result,error,receipt,commands=self.exercise()
        self.assertIsNone(error);self.assertEqual(result['status'],'TARGET_ASSOCIATION_VERIFIED');self.assertEqual(result['boot_id'],'a'*32);self.assertEqual(result['generation'],7)
        self.assertEqual(len(receipt['usb_info']),2)
        import hashlib
        for row in receipt['usb_info']:self.assertEqual(hashlib.sha256(bytes.fromhex(row['raw_hex'])).hexdigest(),row['sha256'])

    def test_wrong_usb_identity_boot_generation_mac_and_link_refuse(self):
        changes=(lambda v:v.update(device_id='c'*32),lambda v:v['status'].update(boot_id='c'*32),lambda v:v.update(provisioning_generation='8'),lambda v:v['network'].update(station_mac='88:a2:9e:0a:9d:88'),lambda v:v['network'].update(link_status=0),lambda v:v['network'].update(ipv4='192.168.1.89'))
        for change in changes:
            with self.subTest(change=change):
                result,error,receipt,commands=self.exercise(change=change);self.assertIsNone(result);self.assertIsNotNone(error);self.assertEqual(receipt['status'],'TARGET_ASSOCIATION_FAILED')

    def test_unauthorized_peer_wrong_lease_route_config_and_late_results_refuse(self):
        changes=(lambda argv,raw:raw.replace('authorized: yes','authorized: no'),lambda argv,raw:raw.replace('192.168.84.89','192.168.84.88') if argv[-1].endswith('.leases') else raw,lambda argv,raw:raw.replace('192.168.84.0/24','192.168.1.0/24'),lambda argv,raw:raw.replace('ccmp','tkip'),lambda argv,raw:raw.replace('9999999999','1') if argv[-1].endswith('.leases') else raw)
        for change in changes:
            with self.subTest(change=change):
                self.host_change=change;result,error,receipt,commands=self.exercise();self.assertIsNone(result);self.assertIsNotNone(error)
        self.host_change=None;result,error,receipt,commands=self.exercise(late=True);self.assertIsNone(result);self.assertIsNotNone(error)

    def test_unfiltered_route_requires_actual_explicit_interface(self):
        for missing in (False,True):
            with self.subTest(missing=missing):
                def changed(argv,raw):
                    if argv==['ip','-4','-j','route','show']:
                        rows=json.loads(raw)
                        if missing:rows[0].pop('dev')
                        else:rows[0]['dev']='wlan1'
                        return json.dumps(rows)
                    return raw
                self.host_change=changed
                result,error,receipt,commands=self.exercise()
                self.assertIsNone(result);self.assertIsNotNone(error)
                self.assertTrue(any(argv==['ip','-4','-j','route','show'] for argv,_ in commands))

    def test_seed_proof_failure_stops_before_success_and_AP_stop(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory(prefix='target-proof-') as directory:
            root=Path(directory);backend=MagicMock();backend.remote='/remote';remote=MagicMock();calls=[]
            info=dict(status=dict(boot_id='a'*32,clock_state='unsynchronized'),network=dict(link_status=3,ipv4='192.168.84.89'))
            backend.info.return_value=info
            def fixture(action,args):
                calls.append((action,args))
                if action=='prove_target':raise ValueError('unproven peer')
            remote.fixture.side_effect=fixture
            with patch.object(parent,'safe_info',side_effect=lambda value,*args:value):
                with self.assertRaisesRegex(ValueError,'unproven peer'):
                    parent.observe_seed_association(backend,remote,root,dict(source_commit='b'*40),dict(info=info),lambda:None,160,clock=lambda:0,target_proof=True,generation=7)
            self.assertEqual([row[0] for row in calls],['inspect_ap','prove_target','inspect_ap'])
            self.assertEqual(calls[1][1]['boot_id'],'a'*32);self.assertEqual(calls[1][1]['generation'],7)
            self.assertFalse(any(row[0] in ('stop','sntp_on','bind_peer') for row in calls))

    def test_unproven_target_cannot_bind_peer_or_enable_sntp(self):
        root='/home/pi/phase12-recovery-'+'a'*32;roles=role_map();pending=dict(status='TARGET_PROOF_PENDING',address='192.168.84.89')
        for action in ('bind_peer','sntp_on'):
            with self.subTest(action=action),patch.object(f,'load_roles',return_value=roles),patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False),patch.object(Path,'exists',lambda path:path.name in ('fixture-ap-proof.json','ntp-ready.json','ntp-peer.json')),patch.object(Path,'read_bytes',return_value=json.dumps(pending).encode()),patch.object(f,'private_write') as write:
                with self.assertRaisesRegex(ValueError,'target proof required'):
                    f.action(dict(root=root,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action=action,address='192.168.84.89'))
                write.assert_not_called()

    def test_target_pending_path_starts_disabled_responder_without_beacon_claim(self):
        from unittest.mock import MagicMock
        root='/home/pi/phase12-recovery-'+'a'*32;roles=role_map();ap=dict(bssid='e8:4e:06:ae:d7:09')
        ready=dict(pid=42,enabled=False,startup_token='a'*32,roles_sha256=roles['sha256'])
        process=MagicMock();process.poll.return_value=None
        def exists(path):return path.name in ('ntp-ready.json','ntp-pid.json')
        with patch.object(f,'load_roles',return_value=roles),patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False),patch.object(Path,'exists',exists),patch.object(Path,'read_bytes',return_value=json.dumps(ready).encode()),patch.object(Path,'open',return_value=MagicMock()),patch.object(f,'fresh_ntp_files'),patch.object(f,'private_write'),patch.object(f,'management',return_value={}),patch.object(f,'command',side_effect=['30 (disconnected)','','','']),patch.object(f,'owned_ap_configuration',return_value=ap),patch.object(f,'wait_owned_beacon') as beacon,patch.object(f.os,'urandom',return_value=bytes.fromhex('a'*32)),patch.object(f.subprocess,'Popen',return_value=process):
            result=f.action(dict(root=root,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action='start_ap',proof_mode='target',ssid='p12-'+'a'*12,password='b'*32))
        beacon.assert_not_called();self.assertEqual(result['status'],'TARGET_PROOF_PENDING');self.assertFalse(result['independent_beacon_verified'])

if __name__=='__main__':unittest.main()
