#!/usr/bin/env python3
"""Wire timestamp and scoped cleanup checks, with no network/device operations."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import phase12_engineering_fixture as f


class Tests(unittest.TestCase):
    def test_action_failure_is_private_and_preserves_original_exception(self):
        root='/home/pi/phase12-recovery-'+'a'*32
        for capture_fails in (False,True):
            with self.subTest(capture_fails=capture_fails):
                original=ValueError('actual fixture failure')
                with patch.object(f.sys,'argv',['fixture.py']),patch.object(f.sys,'stdin') as input_file,patch.object(f,'action',side_effect=original),patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False),patch.object(Path,'exists',return_value=False),patch.object(f,'private_write',side_effect=OSError('capture failed') if capture_fails else None) as saved:
                    input_file.buffer.read.return_value=json.dumps(dict(root=root,action='start_ap')).encode()
                    with self.assertRaises(ValueError) as caught:f.main()
                self.assertIs(caught.exception,original)
                saved.assert_called_once()
                path,data=saved.call_args.args
                self.assertEqual(path,Path(root)/'fixture-action-failure.json')
                self.assertEqual(data['action'],'start_ap')
                self.assertIn('actual fixture failure',data['traceback'])
    def test_malformed_diagnostic_root_does_not_mask_action_failure(self):
        original=ValueError('actual fixture failure')
        with patch.object(f.sys,'argv',['fixture.py']),patch.object(f.sys,'stdin') as input_file,patch.object(f,'action',side_effect=original),patch.object(f,'private_write') as saved:
            input_file.buffer.read.return_value=json.dumps(dict(root=123,action='start_ap')).encode()
            with self.assertRaises(ValueError) as caught:f.main()
        self.assertIs(caught.exception,original);saved.assert_not_called()
    def test_start_ap_cannot_launch_responder_before_independent_beacon(self):
        root='/home/pi/phase12-recovery-'+'a'*32
        with patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False),              patch.object(f,'fresh_ntp_files'),patch.object(f,'private_write'),patch.object(f,'management',return_value={}),              patch.object(f,'command',side_effect=['30 (disconnected)','', '', '']),              patch.object(f,'wait_owned_beacon',side_effect=TimeoutError('beacon not observed')) as beacon,              patch.object(f.subprocess,'Popen') as launch:
            with self.assertRaisesRegex(TimeoutError,'beacon not observed'):
                f.action(dict(root=root,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action='start_ap',
                              ssid='p12-'+'a'*12,password='b'*32))
            beacon.assert_called_once();launch.assert_not_called()
            argv=f.command.call_args_list[2].args
            for key,value in (('802-11-wireless.channel','3'),('wifi-sec.proto','rsn'),('wifi-sec.pairwise','ccmp'),('wifi-sec.group','ccmp')):
                self.assertEqual(argv[argv.index(key)+1],value)

    def test_independent_frequency_beacon_gate_and_unused_observer(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ssid='p12-'+'a'*12;before={'routes':[]}
            info=('Interface wlan2\n\taddr e8:4e:06:ae:d7:09\n\tssid '+ssid+'\n\ttype AP\n\tchannel 3 (2422 MHz), width: 20 MHz\n').encode()
            scans=[b'BSS 11:22:33:44:55:66(on wlan0)\n\tfreq: 2422\n\tSSID: Other\n',
                   ('BSS e8:4e:06:ae:d7:09(on wlan0)\n\tfreq: 2422\n\tSSID: '+ssid+'\n\tRSN: * Version: 1\n\t * Group cipher: CCMP\n\t * Pairwise ciphers: CCMP\n\t * Authentication suites: PSK\n').encode()]
            def execute(argv,**kwargs):
                if 'GENERAL.STATE' in argv:return f.subprocess.CompletedProcess(argv,0,b'30 (disconnected)\n',b'')
                if argv[-1]=='link':return f.subprocess.CompletedProcess(argv,0,b'Not connected.\n',b'')
                if argv[-1]=='info':return f.subprocess.CompletedProcess(argv,0,info,b'')
                return f.subprocess.CompletedProcess(argv,0,scans.pop(0),b'actual scan')
            now=[0]
            with patch.object(f,'management',return_value=before),patch.object(f.subprocess,'run',side_effect=execute) as command:
                result=f.wait_owned_beacon(root,ssid,before,clock=lambda:now[0],sleeper=lambda delay:now.__setitem__(0,now[0]+delay))
            self.assertEqual(result['status'],'INDEPENDENT_BEACON_READY');self.assertEqual(result['scan_attempts'],2)
            actual_scans=[call for call in command.call_args_list if 'scan' in call.args[0]]
            self.assertEqual(len(actual_scans),2)
            self.assertTrue(all(call.args[0][-3:]==['scan','freq','2422'] and call.kwargs['timeout']<=15 for call in actual_scans))
            self.assertFalse(any(word in ('up','down','add','delete') for row in result['commands'] for word in row['argv']))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(f.subprocess,'run',return_value=f.subprocess.CompletedProcess([],0,b'100 (connected)',b'private')) as command:
                with self.assertRaisesRegex(ValueError,'observer must be unused'):f.wait_owned_beacon(root,ssid,before)
            self.assertEqual(command.call_count,1)
            failed=json.loads((root/'owned-ap-beacon-readiness.json').read_text())
            self.assertEqual(failed['status'],'INDEPENDENT_BEACON_FAILED')

    def test_psk_support_allows_extra_akms_but_not_psk_absence_or_wpa_ie(self):
        for suites,wpa,accepted in [('PSK PSK/SHA-256 SAE',False,True),('PSK/SHA-256 SAE',False,False),('PSK',True,False)]:
            with self.subTest(suites=suites,wpa=wpa),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);ssid='p12-'+'a'*12
                info=('addr e8:4e:06:ae:d7:09\nssid '+ssid+'\ntype AP\nchannel 3 (2422 MHz)\n').encode()
                scan=('BSS e8:4e:06:ae:d7:09(on wlan0)\nfreq: 2422\nSSID: '+ssid+
                      '\nRSN: * Version: 1\n * Group cipher: CCMP\n * Pairwise ciphers: CCMP\n * Authentication suites: '+suites+'\n'+('WPA: * Version: 1\n' if wpa else '')).encode()
                def execute(argv,**kwargs):
                    data=b'30 (disconnected)' if 'GENERAL.STATE' in argv else b'Not connected.' if argv[-1]=='link' else info if argv[-1]=='info' else scan
                    return f.subprocess.CompletedProcess(argv,0,data,b'')
                with patch.object(f,'management',return_value={}),patch.object(f.subprocess,'run',side_effect=execute):
                    if accepted:
                        result=f.wait_owned_beacon(root,ssid,{})
                        self.assertEqual(result['authentication_suites'],suites.split())
                        self.assertEqual(result['status'],'INDEPENDENT_BEACON_READY')
                    else:
                        with self.assertRaisesRegex(ValueError,'CCMP only'):f.wait_owned_beacon(root,ssid,{})

    def test_live_iw_decimal_frequency_and_wrong_missing_duplicate_frequencies(self):
        # The retained live iw scan reports "freq: 2422.0" while iw info reports
        # "channel 3 (2422 MHz)". Only an exact integral match admits readiness.
        for lines,accepted in [(b'freq: 2422',True),(b'freq: 2422.0',True),
                (b'freq: 2422.00',True),(b'freq: 2422.5',False),
                (b'freq: 24220',False),(b'freq: 2437.0',False),(b'freq: 2412.0',False),(b'',False),
                (b'freq: 2422.0\nfreq: 2422',False),
                (b'freq: 2422.0\nfreq: 2422.5',False),
                (b'freq: 2422.0\nfreq: garbage',False)]:
            with self.subTest(lines=lines),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);ssid='p12-'+'a'*12;now=[0]
                info=('addr e8:4e:06:ae:d7:09\nssid '+ssid+'\ntype AP\nchannel 3 (2422 MHz)\n').encode()
                scan=(b'BSS e8:4e:06:ae:d7:09(on wlan0)\n'+lines+b'\nSSID: '+ssid.encode()+
                    b'\nRSN: * Version: 1\n * Group cipher: CCMP\n * Pairwise ciphers: CCMP\n * Authentication suites: PSK\n')
                def execute(argv,**kwargs):
                    data=b'30 (disconnected)' if 'GENERAL.STATE' in argv else b'Not connected.' if argv[-1]=='link' else info if argv[-1]=='info' else scan
                    return f.subprocess.CompletedProcess(argv,0,data,b'')
                with patch.object(f,'management',return_value={}),patch.object(f.subprocess,'run',side_effect=execute):
                    invoke=lambda:f.wait_owned_beacon(root,ssid,{},clock=lambda:now[0],sleeper=lambda delay:now.__setitem__(0,now[0]+delay))
                    if accepted:self.assertEqual(invoke()['status'],'INDEPENDENT_BEACON_READY')
                    else:
                        with self.assertRaisesRegex(TimeoutError,'beacon not observed'):invoke()

    def test_visible_mixed_tkip_beacon_cannot_be_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ssid='p12-'+'a'*12
            info=('addr e8:4e:06:ae:d7:09\nssid '+ssid+'\ntype AP\nchannel 3 (2422 MHz)\n').encode()
            scan=('BSS e8:4e:06:ae:d7:09(on wlan0)\nfreq: 2422\nSSID: '+ssid+
                  '\nRSN: * Version: 1\n * Group cipher: TKIP\n * Pairwise ciphers: CCMP TKIP\n * Authentication suites: PSK\n').encode()
            def execute(argv,**kwargs):
                data=b'30 (disconnected)' if 'GENERAL.STATE' in argv else b'Not connected.' if argv[-1]=='link' else info if argv[-1]=='info' else scan
                return f.subprocess.CompletedProcess(argv,0,data,b'')
            with patch.object(f,'management',return_value={}),patch.object(f.subprocess,'run',side_effect=execute):
                with self.assertRaisesRegex(ValueError,'CCMP only'):f.wait_owned_beacon(root,ssid,{})
            self.assertEqual(json.loads((root/'owned-ap-beacon-readiness.json').read_text())['status'],'INDEPENDENT_BEACON_FAILED')

    def test_previous_owned_channel_one_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as directory:
            ssid='p12-'+'a'*12
            info=('addr e8:4e:06:ae:d7:09\nssid '+ssid+'\ntype AP\nchannel 1 (2412 MHz)\n').encode()
            def execute(argv,**kwargs):
                data=b'30 (disconnected)' if 'GENERAL.STATE' in argv else b'Not connected.' if argv[-1]=='link' else info
                return f.subprocess.CompletedProcess(argv,0,data,b'')
            with patch.object(f,'management',return_value={}),patch.object(f.subprocess,'run',side_effect=execute) as called:
                with self.assertRaisesRegex(ValueError,'channel identity'):f.wait_owned_beacon(Path(directory),ssid,{})
                self.assertFalse(any('scan' in row.args[0] for row in called.call_args_list))

    def test_initial_empty_scans_can_observe_delayed_beacon_within_original_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ssid='p12-'+'a'*12;now=[0];scanned=[]
            info=('addr e8:4e:06:ae:d7:09\nssid '+ssid+'\ntype AP\nchannel 3 (2422 MHz)\n').encode()
            beacon=('BSS e8:4e:06:ae:d7:09(on wlan0)\nfreq: 2422.0\nSSID: '+ssid+
                '\nRSN: * Version: 1\n * Group cipher: CCMP\n * Pairwise ciphers: CCMP\n * Authentication suites: PSK\n').encode()
            def execute(argv,**kwargs):
                if 'GENERAL.STATE' in argv:data=b'30 (disconnected)'
                elif argv[-1]=='link':data=b'Not connected.'
                elif argv[-1]=='info':data=info
                else:
                    scanned.append(now[0]);data=beacon if now[0]>=20 else b''
                return f.subprocess.CompletedProcess(argv,0,data,b'')
            with patch.object(f,'management',return_value={}),patch.object(f.subprocess,'run',side_effect=execute):
                result=f.wait_owned_beacon(root,ssid,{},clock=lambda:now[0],sleeper=lambda delay:now.__setitem__(0,now[0]+delay))
            self.assertEqual(scanned,[0,10,20]);self.assertEqual(result['scan_attempts'],3)
            self.assertEqual(result['max_seconds'],45);self.assertEqual(result['max_scans'],4)

    def test_final_management_observation_cannot_publish_ready_after_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ssid='p12-'+'a'*12;now=[0];checked=[0]
            info=('addr e8:4e:06:ae:d7:09\nssid '+ssid+'\ntype AP\nchannel 3 (2422 MHz)\n').encode()
            beacon=('BSS e8:4e:06:ae:d7:09(on wlan0)\nfreq: 2422.0\nSSID: '+ssid+
                '\nRSN: * Version: 1\n * Group cipher: CCMP\n * Pairwise ciphers: CCMP\n * Authentication suites: PSK\n').encode()
            def execute(argv,**kwargs):
                data=b'30 (disconnected)' if 'GENERAL.STATE' in argv else b'Not connected.' if argv[-1]=='link' else info if argv[-1]=='info' else beacon
                return f.subprocess.CompletedProcess(argv,0,data,b'')
            def management(**kwargs):
                checked[0]+=1
                if checked[0]==3:now[0]=45
                return {}
            with patch.object(f,'management',side_effect=management),patch.object(f.subprocess,'run',side_effect=execute):
                with self.assertRaisesRegex(ValueError,'final observation exceeded readiness deadline'):
                    f.wait_owned_beacon(root,ssid,{},clock=lambda:now[0],sleeper=lambda delay:None)
            self.assertEqual(json.loads((root/'owned-ap-beacon-readiness.json').read_text())['status'],'INDEPENDENT_BEACON_FAILED')

    def test_beacon_timeouts_remain_inside_whole45second_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);ssid='p12-'+'a'*12;before={};now=[0]
            info=('addr e8:4e:06:ae:d7:09\nssid '+ssid+'\ntype AP\nchannel 3 (2422 MHz)\n').encode()
            def execute(argv,**kwargs):
                if 'GENERAL.STATE' in argv:return f.subprocess.CompletedProcess(argv,0,b'30 (disconnected)',b'')
                if argv[-1]=='link':return f.subprocess.CompletedProcess(argv,0,b'Not connected.',b'')
                if argv[-1]=='info':return f.subprocess.CompletedProcess(argv,0,info,b'')
                now[0]+=kwargs['timeout']
                raise f.subprocess.TimeoutExpired(argv,kwargs['timeout'],output=b'partial scan',stderr=b'actual failure')
            with patch.object(f,'management',return_value=before),patch.object(f.subprocess,'run',side_effect=execute):
                with self.assertRaisesRegex(ValueError,'readiness deadline'):
                    f.wait_owned_beacon(root,ssid,before,clock=lambda:now[0],sleeper=lambda delay:now.__setitem__(0,now[0]+delay))
            receipt=json.loads((root/'owned-ap-beacon-readiness.json').read_text())
            timed=[row for row in receipt['commands'] if row.get('status')=='TIMEOUT']
            self.assertEqual(len(timed),3);self.assertEqual(now[0],45)
            self.assertEqual(timed[0]['stderr_hex'],b'actual failure'.hex())

    def test_readonly_owned_ap_inspection_retains_raw_commands_and_refuses_foreign_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/('phase12-recovery-'+'a'*32);root.mkdir()
            before={'routes':[]};(root/'fixture-management-before.json').write_text(json.dumps(before))
            name='p12-engineering-'+'a'*32
            responses=[f.subprocess.CompletedProcess([],0,(name+'\n').encode(),b''),
                f.subprocess.CompletedProcess([],0,b'wlan2\nap\n3\n',b''),
                f.subprocess.CompletedProcess([],0,b'channel 3 (2422 MHz)',b''),
                f.subprocess.CompletedProcess([],0,b'Station aa:bb:cc:dd:ee:ff',b''),
                f.subprocess.CompletedProcess([],0,b'[{"ifname":"wlan2"}]',b'')]
            with patch.object(f,'management',return_value=before),patch.object(f.subprocess,'run',side_effect=responses) as execute:
                result=f.inspect_owned_ap(root,'start')
            self.assertEqual(result['status'],'READ_ONLY_INSPECTION_COMPLETE')
            self.assertEqual(execute.call_count,5)
            self.assertTrue(all(call.kwargs['timeout']==10 for call in execute.call_args_list))
            self.assertEqual(bytes.fromhex(result['commands'][3]['stdout_hex']),b'Station aa:bb:cc:dd:ee:ff')
            self.assertFalse(any(word in ('up','down','add','delete') for row in result['commands'] for word in row['argv']))
            with patch.object(f,'management',return_value=before),patch.object(f.subprocess,'run',return_value=f.subprocess.CompletedProcess([],0,b'foreign\n',b'private')) as execute:
                with self.assertRaisesRegex(ValueError,'unrelated or inactive'):f.inspect_owned_ap(root,'failure')
            self.assertEqual(execute.call_count,1)
            failed=json.loads((root/'populated-seed-failure-ap-inspection.json').read_text())
            self.assertEqual(failed['status'],'READ_ONLY_INSPECTION_FAILED')
            self.assertEqual(failed['commands'][0]['stderr_hex'],b'private'.hex())

    def test_ntp_reply_origin_mode_and_fresh_timestamps(self):
        query=bytearray(48);query[0]=0x23;query[40:48]=b'12345678'
        utc=1_790_976_000_123_456_789
        reply=f.ntp_reply(query,utc)
        self.assertEqual(len(reply),48);self.assertEqual(reply[0],0x24)
        self.assertEqual(reply[24:32],query[40:48]);self.assertEqual(reply[32:40],reply[40:48])
        seconds,fraction=struct.unpack('>II',reply[40:48])
        recovered=(seconds-2_208_988_800)*1_000_000_000+((fraction*1_000_000_000)>>32)
        self.assertLessEqual(abs(recovered-utc),1)
    def test_invalid_requests_cannot_be_server_responses(self):
        for query in (bytes(48),bytes(49),bytes(47),b'\x24'+bytes(47)):
            with self.assertRaises(ValueError):f.ntp_reply(query,1_000_000_000)
        query=bytearray(48);query[0]=0x23;query[40:48]=b'12345678'
        for utc in (True,-1,2_208_988_800_000_000_000):
            with self.assertRaises(ValueError):f.ntp_reply(query,utc)
    def test_management_snapshot_ignores_lease_countdown(self):
        def outputs(lifetime):
            return [json.dumps([{'ifname':d,'address':'ab:cd','operstate':'UP','addr_info':[
                dict(family='inet',local='192.168.1.1',prefixlen=24,scope='global',valid_life_time=lifetime)]}])
                for d in ('eth0','wlan1')]+[json.dumps([dict(dst='default',dev='eth0',gateway='192.168.1.254')]),'[]']
        with patch.object(f,'command',side_effect=outputs(500)):before=f.management()
        with patch.object(f,'command',side_effect=outputs(450)):after=f.management()
        self.assertEqual(before,after)
    def test_server_restart_refuses_stale_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);f.fresh_ntp_files(root)
            (root/'ntp-enabled.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'existing'):f.fresh_ntp_files(root)
    def test_only_actual_bound_b_fixture_address_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            self.assertFalse(f.peer_allowed(root,('192.168.84.10',999)))
            (root/'ntp-peer.json').write_text('{"address":"192.168.84.10"}')
            self.assertTrue(f.peer_allowed(root,('192.168.84.10',999)))
            self.assertFalse(f.peer_allowed(root,('192.168.84.11',999)))
            self.assertFalse(f.peer_allowed(root,('192.168.1.10',999)))
    def test_failed_server_stop_still_deletes_owned_ap(self):
        root='/home/pi/phase12-recovery-'+'a'*32
        with (patch.object(Path,'is_dir',return_value=True),patch.object(Path,'is_symlink',return_value=False),
             patch.object(Path,'exists',return_value=False),patch.object(f,'stop_ntp',side_effect=OSError('server stop')),
             patch.object(f,'command',side_effect=['p12-engineering-'+'a'*32+'\n','deleted']) as command):
            with self.assertRaises(OSError):f.action(dict(root=root,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action='stop'))
            self.assertEqual(command.call_args_list[-1].args,
                ('sudo','-n','nmcli','connection','delete','p12-engineering-'+'a'*32))


class DiscoveryDiagnosticTests(unittest.TestCase):
    def scenario(self,matched,stop_error=None,start_error=None,diagnostic_advance=0,delays=None):
        import wsprrypico_ble
        from types import SimpleNamespace
        now=[0];calls=[]
        class Adapter:
            def SetDiscoveryFilter(self,*args):calls.append('filter')
            def StartDiscovery(self):
                calls.append('start')
                if start_error:raise start_error
            def StopDiscovery(self):
                calls.append('stop')
                if stop_error:raise stop_error
        adapter=Adapter()
        class Backend:
            adapter_path='/adapter';ADAPTER='adapter';DEVICE='device';BLUEZ='bluez'
            dbus=SimpleNamespace(Interface=lambda *a:adapter,String=str,Array=lambda v,**kw:v)
            bus=SimpleNamespace(get_object=lambda *a:None)
            def __init__(self,*args):pass
            def pump(self,seconds):now[0]+=seconds
            def _objects(self):return {'/adapter':{},'/adapter/dev_bound':{'device':dict(Address='88:A2:9E:0A:9D:8A',Name='Expected' if matched else '',UUIDs=[wsprrypico_ble.UUIDS['service']],Paired=False,Connected=False)}}
        def sync(_):
            now[0]+=diagnostic_advance
            rows=Path(d,'ble-discovery-original.jsonl').read_text().splitlines()
            if rows:now[0]+=(delays or {}).get(json.loads(rows[-1])['kind'],0)
        with tempfile.TemporaryDirectory() as d,patch.object(wsprrypico_ble,'BluezBackend',Backend),patch.object(f.time,'monotonic',side_effect=lambda:now[0]),patch.object(f.os,'fsync',side_effect=sync):
            result=None;error=None
            try:result=f.discover('Expected',Path(d))
            except Exception as caught:error=caught
            rows=[json.loads(v) for v in Path(d,'ble-discovery-original.jsonl').read_text().splitlines()]
        return calls,result,error,rows,now[0]
    def test_uncertain_start_attempt_always_stops_once(self):
        original=RuntimeError('start applied then reply failed')
        calls,result,error,rows,elapsed=self.scenario(False,OSError('stop failed'),original)
        self.assertIs(error,original);self.assertEqual(calls.count('start'),1);self.assertEqual(calls.count('stop'),1)
    def test_diagnostic_io_does_not_move_original_fifteen_second_anchor(self):
        calls,result,error,rows,elapsed=self.scenario(True,diagnostic_advance=16)
        self.assertIsInstance(error,ValueError);self.assertIsNone(result)
        self.assertFalse(any(v['kind']=='original_objects' for v in rows))
        self.assertEqual(calls.count('start'),1);self.assertEqual(calls.count('stop'),1)
        calls,result,error,rows,elapsed=self.scenario(True,diagnostic_advance=8)
        self.assertIsInstance(error,ValueError);self.assertIsNone(result)
        self.assertEqual(sum(v['kind']=='original_objects' for v in rows),1)
    def test_delayed_candidate_or_cleanup_cannot_return_late_success(self):
        for kind in ('discovery_candidate','discovery_stopped'):
            calls,result,error,rows,elapsed=self.scenario(True,delays={kind:16})
            self.assertIsInstance(error,ValueError);self.assertIsNone(result)
            self.assertEqual(str(error),'fresh named BLE discovery deadline')
            self.assertEqual(calls.count('start'),1);self.assertEqual(calls.count('stop'),1)
    def test_original_zero_name_objects_retained_and_primary_survives_stop_failure(self):
        calls,result,error,rows,elapsed=self.scenario(False,OSError('stop failure'))
        self.assertIsInstance(error,ValueError);self.assertEqual(str(error),'fresh named BLE candidate not unique')
        self.assertEqual(calls.count('start'),1);self.assertEqual(calls.count('stop'),1)
        objects=[v for v in rows if v['kind']=='original_objects']
        self.assertTrue(objects);self.assertTrue(all(v['matching_count']==0 and v['candidate_count']==1 for v in objects))
        self.assertEqual(rows[-1]['kind'],'discovery_stop_failed');self.assertLess(elapsed,15.3)
    def test_unique_original_candidate_has_one_discovery_and_private_counts(self):
        calls,result,error,rows,elapsed=self.scenario(True)
        self.assertIsNone(error);self.assertEqual(result['matching_names'],1)
        self.assertEqual(calls,['filter','start','stop']);self.assertLess(elapsed,1)
        self.assertEqual(next(v for v in rows if v['kind']=='original_objects')['matching_count'],1)
    def test_parent_retrieves_original_discovery_failure_without_masking_it(self):
        from phase12_engineering_orchestrator import RemoteAdapters
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            adapter=RemoteAdapters(Path(d));adapter.backend=SimpleNamespace(remote='/private')
            original=ValueError('no unique candidate');calls=[]
            def invoke(*args,**kwargs):raise original
            def collect(names):calls.append(names);raise OSError('capture failure')
            adapter.invoke=invoke;adapter.collect=collect
            with self.assertRaises(ValueError) as caught:adapter.fixture('discover_ble',{})
            self.assertIs(caught.exception,original)
            self.assertIn(('ble-discovery-original.jsonl',),calls)
    def test_parent_successful_actual_discover_ble_collects_original(self):
        from phase12_engineering_orchestrator import RemoteAdapters
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            adapter=RemoteAdapters(Path(d));adapter.backend=SimpleNamespace(remote='/private')
            result=dict(address='88:A2:9E:0A:9D:8A',matching_names=1);calls=[]
            adapter.invoke=lambda *args,**kwargs:result
            adapter.collect=lambda names:calls.append(names)
            self.assertIs(adapter.fixture('discover_ble',{}),result)
            self.assertEqual(calls,[('ble-discovery-original.jsonl',)])
    def test_successful_match_stop_error_remains_failure(self):
        original=OSError('stop failure');calls,result,error,rows,elapsed=self.scenario(True,original)
        self.assertIs(error,original);self.assertEqual(calls.count('start'),1)

if __name__=='__main__':unittest.main()
