#!/usr/bin/env python3
"""Offline populated campaign sealing/scope and failed preparation restoration tests."""
import copy,hashlib,json,sys,tempfile,time,unittest,importlib.util
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_populated_dispatch as dispatch
import phase12_populated_orchestrator as parent
import phase12_engineering_fixture as fixture
from phase12_recovery_device import DEVICE
from phase12_consumer_negative import b64,keys,unb64

class Tests(unittest.TestCase):
    def test_save_helper_closure_imports_in_isolated_directory(self):
        import ast,subprocess,shutil
        tree=ast.parse(Path(parent.__file__).read_text())
        names=next(ast.literal_eval(node.value) for node in ast.walk(tree)
            if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='names' for target in node.targets))
        with tempfile.TemporaryDirectory() as directory:
            for name in names:shutil.copyfile(Path(parent.__file__).parent/name,Path(directory)/name)
            code='import sys;sys.path.insert(0,sys.argv[1]);import phase12_populated_dispatch,phase12_engineering_fixture,phase12_virtual_observer'
            result= subprocess.run([sys.executable,'-I','-c',code,directory],cwd=directory,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode())

    def test_case_selection_rejects_bad_subset_before_campaign_creation(self):
        self.assertEqual(parent.selected_cases(), ('station','network','provisioning','full'))
        self.assertEqual(parent.selected_cases('provisioning,full'), ('provisioning','full'))
        for value in ('', 'full,provisioning', 'full,full', 'unknown'):
            with self.subTest(value=value),self.assertRaises(ValueError):parent.selected_cases(value)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'new'
            with self.assertRaises(ValueError):parent.execute({},None,root,None,None,cases='full,full')
            self.assertFalse(root.exists())

    def reset_only_flow(self,timeout=False,invalid_boot=False):
        import signal
        calls=[];source='a'*40;actual_timer=parent.tranche_deadline
        inspection=dict(profile_source=5,access_sequence=7,bond_count=0,
            config=dict(enabled=False,schedules=[{},{}]),watermark=11,
            profile_payload=json.dumps(dict(clients=[{},{}])),effective_station={'power_dbm':30})
        seed_bytes=b'x'*4194304
        class Backend:
            def __init__(self,plan,manifest,artifacts,root,inspector):self.remote='/home/pi/phase12-recovery-'+plan['campaign_id'];self.root=root;self.observations=0
            def setup(self):return {}
            def snapshot(self,name):
                path=self.root/name;path.write_bytes(seed_bytes)
                return dict(path=name,sha256=parent.sha(path),inspection=inspection)
            def restore(self,seed,name):calls.append(('restore',name));return {'readback':name}
            def stable_restore(self,*args):return {'samples':5}
            def inspect(self,path):return inspection
            def deploy(self,role,before,name):
                calls.append(('deploy',role));self.observations=0
                return {'info':dict(device_id=DEVICE,revision=source[:12],phase12_fault_stage='1',phase12_fault_consumed=False,status={'boot_id':'before'}),'readback':{'path':name,'sha256':'c'*64}}
            def prepare(self,case,station):calls.append(('prepare',case['level']));return {'sha256':'b'*64,'case':case}
            def submit(self,prepared):calls.append(('submit',prepared['case']['level']))
            def info(self):
                self.observations+=1
                if self.observations==2:raise OSError('bounded transient observation error')
                consumed=self.observations>=3
                return dict(device_id=DEVICE,revision=source[:12],phase12_fault_stage='1',phase12_fault_consumed=consumed,status={'boot_id':'before' if invalid_boot or not consumed else 'after'})
            def cleanup(self):calls.append(('cleanup',))
        class Remote:
            def __init__(self,root):pass
            def stage(self,path,name):calls.append(('stage',name));return 'b'*64
            def fixture(self,*args):raise AssertionError('Reset-only must not touch station fixtures')
            def invoke(self,*args,**kwargs):raise AssertionError('Reset-only must not call station dispatcher')
            def collect(self,*args):raise AssertionError('Reset-only must not collect station evidence')
        def builder(backup,output,*args,**kwargs):
            self.assertIsNone(kwargs['network_file'])
            if timeout:time.sleep(.2);raise AssertionError('timer did not interrupt')
            output.mkdir();path=output/'populated.bin';path.write_bytes(seed_bytes)
            return {'fixture_sha256':parent.sha(path)}
        with tempfile.TemporaryDirectory() as directory,patch.object(parent,'safe_info',lambda value,*args:value), \
             patch.object(parent,'assess',return_value={'result':'PASS'}) as assess, \
             patch.object(parent,'run_saves',side_effect=AssertionError('saves forbidden')), \
             patch.object(parent,'observe_seed_association',side_effect=AssertionError('association forbidden')), \
             patch.object(parent,'tranche_deadline',lambda seconds:actual_timer(.02 if timeout else seconds)):
            root=Path(directory)/'new'
            result=parent.execute({'source_commit':source,'candidates':[dict(role='fault_1',uf2={'sha256':'d'*64})]},directory,root,Path(directory)/'inspector',Path(directory)/'native',
                backend_factory=Backend,remote_factory=Remote,builder=builder,cases='provisioning,full')
            config=json.loads((root/'campaign-config.json').read_text())
            self.assertEqual(config['selected_cases'],['provisioning','full']);self.assertEqual(config['max_cases'],2)
            self.assertEqual(result['selected_cases'],('provisioning','full'))
            self.assertEqual(assess.call_count,0 if timeout or invalid_boot else 2)
            if not timeout:
                case='populated-provisioning-1'
                deployed=json.loads((root/(case+'.deployment-receipt.json')).read_text())
                self.assertEqual(deployed['actual_deployment']['info']['status']['boot_id'],'before')
                observations=[json.loads(p.read_text()) for p in sorted(root.glob(case+'.reset-info-*.json'))]
                self.assertEqual(observations[0]['actual_decoded_info']['status']['boot_id'],'before')
                self.assertEqual(observations[1]['error_type'],'OSError')
                self.assertEqual(observations[2]['actual_decoded_info']['phase12_fault_consumed'],True)
                rows=[json.loads(line) for line in (root/'ledger.jsonl').read_text().splitlines()]
                passes=[row['payload'] for row in rows if row.get('kind')=='populated_reset_pass']
                if invalid_boot:self.assertEqual(passes,[])
                else:
                    self.assertEqual(len(passes),2)
                    for row in passes:
                        self.assertEqual(row['old_boot_id'],'before');self.assertEqual(row['fresh_boot_id'],'after');self.assertEqual(row['image_sha256'],'d'*64)
                        self.assertEqual(row['deployment_readback_sha256'],'c'*64)
                        retained=root/row['consumed_info_path'];self.assertEqual(row['consumed_info_sha256'],parent.sha(retained))
                        self.assertEqual(json.loads(retained.read_text())['actual_decoded_info']['status']['boot_id'],'after')
                        self.assertEqual(retained.stat().st_mode & 0o777,0o600)
            self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0))
        self.assertIn(('restore','final-restoration.bin'),calls);self.assertEqual(calls[-1],('cleanup',))
        return result,calls

    def test_reset_only_completes_without_any_station_adapter(self):
        result,calls=self.reset_only_flow()
        self.assertEqual(result['status'],'POPULATED_COMPLETE_REVIEW_REQUIRED')
        self.assertEqual([c for c in calls if c[0]=='submit'],[('submit','provisioning'),('submit','full')])
        self.assertEqual([c for c in calls if c[0]=='deploy'],[('deploy','fault_1'),('deploy','fault_1')])
        self.assertEqual([c for c in calls if c[0]=='stage'],[('stage','populated.bin')])

    def test_same_boot_consumed_observation_retained_without_success_claim(self):
        result,calls=self.reset_only_flow(invalid_boot=True)
        self.assertEqual(result['status'],'STOPPED');self.assertIn('freshboot',result['error']['message'])

    def test_reset_only_blocking_preparation_deadline_restores(self):
        result,calls=self.reset_only_flow(timeout=True)
        self.assertEqual(result['status'],'STOPPED');self.assertEqual(result['error']['type'],'TimeoutError')
        self.assertFalse(any(c[0]=='submit' for c in calls))

    def test_failed_association_retains_each_actual_info_and_host_inspection(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);backend=MagicMock();backend.remote='/remote';remote=MagicMock();now=[0]
            actual={'status':{'boot_id':'b'*32,'clock_state':'unsynchronized'},'network':{'link_status':-1}}
            backend.info.return_value=actual
            with patch.object(parent,'safe_info',side_effect=lambda value,*args:value):
                with self.assertRaisesRegex(ValueError,'association deadline'):
                    parent.observe_seed_association(backend,remote,root,{'source_commit':'a'*40},
                        {'info':actual},lambda:None,1,clock=lambda:now[0],sleeper=lambda delay:now.__setitem__(0,now[0]+delay))
            records=sorted(root.glob('seed-association-info-*.json'))
            self.assertEqual(len(records),2)
            value=json.loads(records[0].read_text());self.assertEqual(value['actual_decoded_info'],actual)
            self.assertEqual(value['bindings']['ssh_host'],'wspr5');self.assertEqual(value['bindings']['expected_boot_id'],'b'*32)
            self.assertEqual([c.args[1]['phase'] for c in remote.fixture.call_args_list],['start','failure'])

    def test_late_join_info_or_success_inspection_cannot_qualify(self):
        from unittest.mock import MagicMock
        for late_info in (True,False):
            with self.subTest(late_info=late_info),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);backend=MagicMock();backend.remote='/remote';remote=MagicMock();now=[0]
                actual={'status':{'boot_id':'b'*32,'clock_state':'unsynchronized'},'network':{'link_status':3,'ipv4':'192.168.84.10'}}
                def read():
                    if late_info:now[0]=1
                    return actual
                def inspect(operation,value):
                    if value['phase']=='success':now[0]=1
                backend.info.side_effect=read;remote.fixture.side_effect=inspect
                with patch.object(parent,'safe_info',side_effect=lambda value,*args:value):
                    with self.assertRaisesRegex(ValueError,'association deadline'):
                        parent.observe_seed_association(backend,remote,root,{'source_commit':'a'*40},
                            {'info':actual},lambda:None,1,clock=lambda:now[0],sleeper=lambda delay:None)
                self.assertEqual(len(list(root.glob('seed-association-info-*.json'))),1)
                self.assertEqual(remote.fixture.call_args_list[-1].args[1]['phase'],'failure')

    def test_observer_wrong_link_and_exhausted_scan_never_qualify(self):
        from types import SimpleNamespace
        class Evidence:
            def __init__(self):self.rows=[]
            def record(self,kind,**value):self.rows.append((kind,value))
        now=[0];calls=[];evidence=Evidence()
        def runner(argv,**kw):
            calls.append(argv)
            if argv[-1]=='scan':
                return SimpleNamespace(returncode=0,stdout=b'BSS 11:22:33:44:55:66\n SSID: WsprryPico-abcdef\n',stderr=b'')
            if 'nmcli' in argv:return SimpleNamespace(returncode=0,stdout=b'joined',stderr=b'')
            return SimpleNamespace(returncode=0,stdout=b'Connected to 99:88:77:66:55:44\n SSID: WsprryPico-abcdef\n',stderr=b'')
        with self.assertRaisesRegex(ValueError,'exact scanned'):
            dispatch.associate_observer('owned','WsprryPico-abcdef',3,evidence,
                clock=lambda:now[0],runner=runner,sleeper=lambda _:None)
        calls.clear();evidence.rows.clear()
        def missing(argv,**kw):
            calls.append(argv);now[0]+=kw['timeout']
            raise dispatch.subprocess.TimeoutExpired(argv,kw['timeout'],output=b'partial',stderr=b'timeout')
        with self.assertRaises(dispatch.subprocess.TimeoutExpired):
            dispatch.associate_observer('owned','WsprryPico-abcdef',3,evidence,
                clock=lambda:now[0],runner=missing,sleeper=lambda _:None)
        self.assertEqual(len(calls),1);self.assertNotIn('nmcli',calls[0])
        self.assertEqual(evidence.rows[-1][0],'observer_command_timeout')
        self.assertEqual(evidence.rows[-1][1]['stdout_hex'],b'partial'.hex())

    def test_observer_oversized_success_or_timeout_output_cannot_qualify(self):
        from types import SimpleNamespace
        class Evidence:
            def __init__(self):self.rows=[]
            def record(self,kind,**value):self.rows.append((kind,value))
        for timed in (False,True):
            evidence=Evidence();calls=[]
            def runner(argv,**kw):
                calls.append(argv)
                if timed:raise dispatch.subprocess.TimeoutExpired(argv,1,output=b'x'*262145,stderr=b'failure')
                return SimpleNamespace(returncode=0,stdout=b'x'*262145,stderr=b'')
            with self.assertRaisesRegex(ValueError,'output bound'):
                dispatch.associate_observer('owned','WsprryPico-abcdef',30,evidence,clock=lambda:0,runner=runner)
            self.assertEqual(len(calls),1);self.assertNotIn('nmcli',calls[0])
            if timed:self.assertTrue(evidence.rows[-1][1]['output_overflow']);self.assertEqual(len(bytes.fromhex(evidence.rows[-1][1]['stdout_hex'])),262144)

    def test_scan_timeout_then_beacon_uses_remaining_single_join_budget(self):
        from types import SimpleNamespace
        class Evidence:
            def record(self,*args,**kwargs):pass
        now=[58];calls=[]
        def runner(argv,**kw):
            calls.append((argv,kw['timeout']))
            if argv[-1]=='scan':
                if len(calls)==1:
                    now[0]+=kw['timeout'];raise dispatch.subprocess.TimeoutExpired(argv,kw['timeout'],output=b'partial',stderr=b'scan timeout')
                now[0]=82;return SimpleNamespace(returncode=0,stdout=b'BSS 11:22:33:44:55:66\n SSID: WsprryPico-abcdef\n',stderr=b'')
            if 'nmcli' in argv:
                self.assertEqual(argv[argv.index('--wait')+1],'27');self.assertEqual(kw['timeout'],28)
                return SimpleNamespace(returncode=0,stdout=b'joined',stderr=b'')
            return SimpleNamespace(returncode=0,stdout=b'Connected to 11:22:33:44:55:66\n SSID: WsprryPico-abcdef\n',stderr=b'')
        dispatch.associate_observer('owned','WsprryPico-abcdef',110,Evidence(),clock=lambda:now[0],runner=runner,sleeper=lambda d:now.__setitem__(0,now[0]+d))
        self.assertEqual(sum('nmcli' in argv for argv,limit in calls),1)

    def test_scan_busy_retries_but_join_timeout_never_reactivates(self):
        from types import SimpleNamespace
        class Evidence:
            def __init__(self):self.rows=[]
            def record(self,kind,**value):self.rows.append((kind,value))
        now=[0];calls=[];evidence=Evidence()
        def runner(argv,**kw):
            calls.append((argv,kw['timeout']))
            if argv[-1]=='scan':
                if len(calls)<=2:return SimpleNamespace(returncode=240,stdout=b'',stderr=b'command failed: busy (-16)' if len(calls)==1 else b'command failed: again (-11)')
                return SimpleNamespace(returncode=0,stdout=b'BSS 11:22:33:44:55:66\n SSID: WsprryPico-abcdef\n',stderr=b'')
            self.assertIn('nmcli',argv);self.assertEqual(argv[argv.index('--wait')+1],'30');self.assertLessEqual(kw['timeout'],40-now[0])
            raise dispatch.subprocess.TimeoutExpired(argv,kw['timeout'],output=b'activation pending',stderr=b'uncertain')
        with self.assertRaises(dispatch.subprocess.TimeoutExpired):
            dispatch.associate_observer('owned','WsprryPico-abcdef',40,evidence,clock=lambda:now[0],runner=runner,sleeper=lambda d:now.__setitem__(0,now[0]+d))
        self.assertEqual(sum('nmcli' in argv for argv,limit in calls),1);self.assertEqual(len(calls),4)
        self.assertEqual(evidence.rows[-1][0],'observer_command_timeout')
        calls.clear();now[0]=0
        def busy(argv,**kw):calls.append(argv);return SimpleNamespace(returncode=240,stdout=b'',stderr=b'command failed: busy (-16)')
        with self.assertRaisesRegex(ValueError,'association deadline'):
            dispatch.associate_observer('owned','WsprryPico-abcdef',1,evidence,clock=lambda:now[0],runner=busy,sleeper=lambda d:now.__setitem__(0,now[0]+d))
        self.assertFalse(any('nmcli' in argv for argv in calls));self.assertEqual(now[0],1)

    def test_observer_scans_exact_ssid_before_join_and_records_failure(self):
        from types import SimpleNamespace
        class Evidence:
            def __init__(self):self.rows=[]
            def record(self,kind,**value):self.rows.append((kind,value))
        for failed in (False,True):
            with self.subTest(failed=failed):
                calls=[];evidence=Evidence();scans=[b'BSS aa:bb:cc:dd:ee:ff\n SSID: other\n',b'BSS 11:22:33:44:55:66\n SSID: WsprryPico-abcdef\n']
                def runner(argv,**kw):
                    calls.append(argv)
                    if argv[-1]=='scan':return SimpleNamespace(returncode=0,stdout=scans.pop(0),stderr=b'')
                    if 'nmcli' in argv:return SimpleNamespace(returncode=4 if failed else 0,stdout=b'join',stderr=b'failure' if failed else b'')
                    return SimpleNamespace(returncode=0,stdout=b'Connected to 11:22:33:44:55:66\n SSID: WsprryPico-abcdef\n',stderr=b'')
                if failed:
                    with self.assertRaises(dispatch.subprocess.CalledProcessError):dispatch.associate_observer('owned','WsprryPico-abcdef',10,evidence,clock=lambda:0,runner=runner,sleeper=lambda _:None)
                else:dispatch.associate_observer('owned','WsprryPico-abcdef',10,evidence,clock=lambda:0,runner=runner,sleeper=lambda _:None)
                self.assertEqual([a[-1] for a in calls[:2]],['scan','scan'])
                self.assertIn('nmcli',calls[2]);self.assertEqual(sum('nmcli' in a for a in calls),1)
                if failed:self.assertEqual(evidence.rows[-1][1]['stderr_hex'],b'failure'.hex())

    def test_scan_enobufs_recovers_once_and_preserves_original_failure(self):
        from types import SimpleNamespace
        class Evidence:
            def __init__(self):self.rows=[]
            def record(self,kind,**value):self.rows.append((kind,value))
        calls=[];now=[0];evidence=Evidence()
        def runner(argv,**kw):
            calls.append(argv)
            if len(calls)==1:return SimpleNamespace(returncode=151,stdout=b'',stderr=b'command failed: No buffer space available (-105)\n')
            if argv[-1]=='scan':return SimpleNamespace(returncode=0,stdout=b'BSS 11:22:33:44:55:66\n SSID: WsprryPico-abcdef\n',stderr=b'')
            if 'nmcli' in argv:return SimpleNamespace(returncode=0,stdout=b'joined',stderr=b'')
            return SimpleNamespace(returncode=0,stdout=b'Connected to 11:22:33:44:55:66\n SSID: WsprryPico-abcdef\n',stderr=b'')
        dispatch.associate_observer('owned','WsprryPico-abcdef',40,evidence,clock=lambda:now[0],runner=runner,sleeper=lambda d:now.__setitem__(0,now[0]+d))
        self.assertEqual(sum('nmcli' in argv for argv in calls),1)
        self.assertEqual(evidence.rows[0][1]['returncode'],151)
        self.assertEqual(bytes.fromhex(evidence.rows[0][1]['stderr_hex']),b'command failed: No buffer space available (-105)\n')

    def test_persistent_scan_enobufs_stops_at_original_deadline_without_join(self):
        from types import SimpleNamespace
        class Evidence:
            def record(self,*args,**kwargs):pass
        calls=[];now=[0]
        def runner(argv,**kw):
            calls.append(argv)
            return SimpleNamespace(returncode=151,stdout=b'',stderr=b'command failed: No buffer space available (-105)\n')
        with self.assertRaisesRegex(ValueError,'association deadline'):
            dispatch.associate_observer('owned','WsprryPico-abcdef',1,Evidence(),clock=lambda:now[0],runner=runner,sleeper=lambda d:now.__setitem__(0,now[0]+d))
        self.assertEqual(now[0],1)
        self.assertFalse(any('nmcli' in argv for argv in calls))

    def test_hard_scan_errors_and_activation_enobufs_are_never_retried(self):
        from types import SimpleNamespace
        class Evidence:
            def record(self,*args,**kwargs):pass
        for stderr in (b'failure (-104)',b'failure (-106)',b'failure (-1)',b'failure without errno'):
            calls=[]
            def runner(argv,**kw):calls.append(argv);return SimpleNamespace(returncode=151,stdout=b'',stderr=stderr)
            with self.subTest(stderr=stderr),self.assertRaises(dispatch.subprocess.CalledProcessError):
                dispatch.associate_observer('owned','WsprryPico-abcdef',40,Evidence(),clock=lambda:0,runner=runner)
            self.assertEqual(len(calls),1)
            self.assertFalse(any('nmcli' in argv for argv in calls))
        calls=[]
        def activate(argv,**kw):
            calls.append(argv)
            if argv[-1]=='scan':return SimpleNamespace(returncode=0,stdout=b'BSS 11:22:33:44:55:66\n SSID: WsprryPico-abcdef\n',stderr=b'')
            return SimpleNamespace(returncode=151,stdout=b'uncertain',stderr=b'failure (-105)')
        with self.assertRaises(dispatch.subprocess.CalledProcessError):
            dispatch.associate_observer('owned','WsprryPico-abcdef',40,Evidence(),clock=lambda:0,runner=activate)
        self.assertEqual(len(calls),2)
        self.assertEqual(sum('nmcli' in argv for argv in calls),1)

    def test_owned_restart_preserves_receipt_and_launches_no_responder(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/('phase12-recovery-'+'a'*32);root.mkdir();before={'management':'unchanged'}
            (root/'fixture-management-before.json').write_text(json.dumps(before))
            (root/'ntp-stopped.json').write_text('{}')
            (root/'populated-network.json').write_text(json.dumps(dict(ssid='p12-'+'a'*12,password='b'*32)))
            commands=[];original=fixture.re.fullmatch
            def match(pattern,value):
                if pattern.startswith('/home/pi/phase12-recovery-'):return True
                return original(pattern,value)
            def command(*args):
                commands.append(args)
                if args[:5]==('nmcli','-t','-f','GENERAL.STATE','device'):return '30 (disconnected)'
                return ''
            with patch.object(fixture.re,'fullmatch',side_effect=match),patch.object(fixture,'management',return_value=before),                  patch.object(fixture,'stop_ntp') as stop,patch.object(fixture,'command',side_effect=command),                  patch.object(fixture.subprocess,'Popen') as launch:
                result=fixture.action(dict(root=str(root),authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action='restart_ap_offline'))
                self.assertFalse(result['ntp_started']);stop.assert_called_once_with(root);launch.assert_not_called()
                self.assertEqual(json.loads((root/'fixture-management-before.json').read_text()),before)
                self.assertTrue(any('add' in c and 'wlan2' in c for c in commands))
                argv=next(c for c in commands if 'add' in c)
                for key,value in (('802-11-wireless.channel','3'),('wifi-sec.proto','rsn'),('wifi-sec.pairwise','ccmp'),('wifi-sec.group','ccmp')):
                    self.assertEqual(argv[argv.index(key)+1],value)
                (root/'ntp-enabled.json').write_text('{}')
                with self.assertRaisesRegex(ValueError,'stopped and disabled'):
                    fixture.action(dict(root=str(root),authority='USER_AUTHORIZED_UNATTENDED_PHASE12',action='restart_ap_offline'))

    def test_real_loss_then_carrier_fallback_no_usb_mutation(self):
        now=[0];calls=[]
        observations=iter([{'network':{'link_status':3}}, {'network':{'link_status':-1}},
                           {'network':{'link_status':-1}}])
        def associate():
            calls.append('associate')
            if len(calls)==1:raise TimeoutError('AP grace')
        with self.assertRaisesRegex(TimeoutError,'AP grace'):
            dispatch.wait_fallback(lambda:next(observations),associate,5,
                clock=lambda:now[0],sleeper=lambda delay:now.__setitem__(0,now[0]+delay))
        self.assertEqual(calls,['associate'])
        with self.assertRaisesRegex(ValueError,'fallback deadline'):
            dispatch.wait_fallback(lambda:{'network':{'link_status':3}},associate,now[0]+1,
                clock=lambda:now[0],sleeper=lambda delay:now.__setitem__(0,now[0]+delay))

    def test_markers_and_exact_routes(self):
        http=dispatch.HTTP()
        for path,marker in [('/api/bootstrap/v1/start',b'Bootstrap'),('/api/owner/v1/claim/start',b'Owner')]:
            raw=http.wire('POST',path,{'version':1});self.assertIn(b'X-WsprryPico-'+marker+b': 1\r\n',raw)
        for method,path,body in [('POST','/api/recovery/v1/submit',{}),('POST','/api/bootstrap/v1/status',{}),('GET','/api/bootstrap/v1/status',{})]:
            with self.assertRaises(ValueError):http.wire(method,path,body)
    @unittest.skipUnless(importlib.util.find_spec("cryptography"), "optional retained cryptography runtime")
    def test_network_seal_interop(self):
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from cryptography.hazmat.primitives import serialization,hashes
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
        peer=X25519PrivateKey.generate();private=X25519PrivateKey.generate()
        raw=lambda key:key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        body=dict(browser_public_key=b64(raw(private)),request_nonce='11'*16)
        start=dict(device_id=DEVICE,boot_id='22'*16,slot_id='33'*16,pico_public_key=b64(raw(peer)))
        network=dict(ssid='p12-123456789abc',password='44'*16,time_server='192.168.84.254')
        box=dispatch.seal_network(start,body,private,network)
        aad=b'WsprryPico/WiFi-Bootstrap/1\0'+bytes.fromhex(DEVICE)+bytes.fromhex(start['boot_id'])+bytes.fromhex(start['slot_id'])+raw(private)+raw(peer)+bytes.fromhex(body['request_nonce'])+bytes.fromhex(box['request_id'])
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey
        key=HKDF(algorithm=hashes.SHA256(),length=32,salt=hashlib.sha256(aad).digest(),info=b'WsprryPico network-only AEAD v1').derive(peer.exchange(X25519PublicKey.from_public_bytes(raw(private))))
        expected=b''.join(bytes([len(network[k])])+network[k].encode() for k in ('ssid','password','time_server'))
        self.assertEqual(ChaCha20Poly1305(key).decrypt(unb64(box['aead_nonce']),unb64(box['ciphertext'])+unb64(box['tag']),aad),expected)
        altered=dict(start,device_id='00'*16)
        with self.assertRaises(ValueError):dispatch.seal_network(altered,body,private,network)
    def test_exact_readback_negative_cases(self):
        station=dict(callsign='K1ABC',locator='FN20',power_dbm=27);network=dict(ssid='x',password='abcdefgh',time_server='192.168.84.254')
        profile=dict(tls={'ca':'real'},clients=[{'public':'a'},{'public':'b'}],owners=[],owner_epoch=0,station=station,network=network,request_sha256='11'*32)
        before=dict(profile_payload=json.dumps(profile),profile_sequence=5,config={'enabled':False,'schedules':[1,2]},watermark=42)
        after=copy.deepcopy(before);after['profile_sequence']=7;after['profile_payload']=json.dumps(profile)
        rows=[dict(submit_attempts=1,generation=6,boot_id='a',request_digest='22'*32),dict(submit_attempts=1,generation=7,boot_id='b',request_digest='11'*32,application_response_discarded=True)]
        data=b'\xff'*(4*1024*1024)
        self.assertEqual(parent.assess_save(before,after,data,data,rows,station,network)['result'],'PASS')
        for kind in ('station','network'):
            single=dict(after,profile_sequence=6)
            row=dict(rows[-1],generation=6)
            self.assertEqual(parent.assess_save(before,single,data,data,[row],station,network,(kind,))['cases'],1)
            if kind=='network':
                with self.assertRaises(ValueError):parent.assess_save(before,single,data,data,[dict(row,application_response_discarded=False)],station,network,(kind,))
        for field,value in [('tls',{'ca':'foreign'}),('clients',[]),('owners',[1]),('request_sha256','33'*32),('station',{})]:
            corrupted=copy.deepcopy(profile);corrupted[field]=value;bad=dict(after,profile_payload=json.dumps(corrupted))
            with self.assertRaises(ValueError):parent.assess_save(before,bad,data,data,rows,station,network)
        changed=bytearray(data);changed[-1]=0
        with self.assertRaises(ValueError):parent.assess_save(before,after,data,bytes(changed),rows,station,network)
        badrows=copy.deepcopy(rows);badrows[-1]['submit_attempts']=2
        with self.assertRaises(ValueError):parent.assess_save(before,after,data,data,badrows,station,network)
    def test_builder_failure_still_restores(self):
        calls=[]
        class Backend:
            def __init__(self,plan,manifest,artifacts,root,inspector):self.remote='/home/pi/phase12-recovery-'+plan['campaign_id'];self.root=root
            def setup(self):calls.append('setup');return {}
            def snapshot(self,name):p=self.root/name;p.write_bytes(b'backup');return dict(path=name,sha256=parent.sha(p),inspection={})
            def restore(self,baseline,name):calls.append(name);return {'readback':name}
            def stable_restore(self,*args):return {'samples':5}
            def cleanup(self):calls.append('cleanup')
        class Remote:
            def __init__(self,root):pass
            def stage(self,*args):return 'a'*64
            def invoke(self,*args,**kw):calls.append('observercleanup');return {}
            def collect(self,*args):pass
        def fail(*args,**kw):raise ValueError('builder injected failure')
        with tempfile.TemporaryDirectory() as directory,patch.object(parent,'safe_info',lambda *a:None):
            result=parent.execute({'source_commit':'a'*40},directory,Path(directory)/'new',Path(directory)/'inspector',Path(directory)/'native',backend_factory=Backend,remote_factory=Remote,builder=fail)
        self.assertEqual(result['status'],'STOPPED');self.assertIn('final-restoration.bin',calls);self.assertEqual(calls[-1],'cleanup')
    def test_delivered_unobserved_drains_once_without_decoding(self):
        events=[]
        class Stream:
            def __init__(self,raw):self.parts=[raw[:12],raw[12:],b'']
            def __enter__(self):return self
            def __exit__(self,*args):events.append('close')
            def settimeout(self,value):pass
            def sendall(self,value):events.append('send')
            def recv(self,size):
                value=self.parts.pop(0);events.append('eof' if not value else 'recv');return value
        raw=b'HTTP/1.1 503 Error\r\nContent-Length: 9\r\n\r\nnot-json!'
        http=dispatch.HTTP()
        with patch.object(http,'connect',lambda deadline:Stream(raw)),patch.object(dispatch,'strict',side_effect=AssertionError('must not decode')):
            request,response=http.delivered_unobserved('/api/bootstrap/v1/submit',{'version':1},time.monotonic()+10)
        self.assertEqual(http.attempts,1);self.assertEqual(response,raw);self.assertEqual(events.count('send'),1)
        self.assertLess(events.index('eof'),events.index('close'))
        self.assertIn(b'X-WsprryPico-Bootstrap: 1',request)
        for bad in [raw.replace(b'Content-Length: 9',b'Content-Length: 8'),raw.replace(b'Content-Length: 9',b'Content-Length: 9\r\nContent-Length: 9'),raw[:-1]]:
            with patch.object(http,'connect',lambda deadline:Stream(bad)),self.assertRaises(ValueError):
                http.delivered_unobserved('/api/bootstrap/v1/submit',{},time.monotonic()+10)
    def test_transient_attempt_old_generation_then_commit_then_reboot(self):
        infos=iter([{'provisioning_generation':7,'status':{'boot_id':'old'}},
                    {'provisioning_generation':8,'status':{'boot_id':'old'}},
                    {'provisioning_generation':8,'status':{'boot_id':'new'}}])
        slots=iter([dict(device_id=DEVICE,boot_id='old',generation=7,request_id_digest='a'*64,slot_state='trial'),
                    dict(device_id=DEVICE,boot_id='old',generation=8,request_id_digest='a'*64,slot_state='terminal')])
        slot_count=[];now=[0]
        def read():slot_count.append(1);return next(slots)
        def sleep(value):now[0]+=value
        saved=dispatch.wait_saved_boot(lambda:next(infos),read,'station',7,'old','a'*64,10,clock=lambda:now[0],sleeper=sleep)
        self.assertEqual(saved['status']['boot_id'],'new');self.assertEqual(len(slot_count),2)
        with self.assertRaises(ValueError):
            dispatch.wait_saved_boot(lambda:dict(provisioning_generation=8,status={'boot_id':'old'}),
                lambda:dict(device_id=DEVICE,boot_id='old',generation=8,request_id_digest='foreign',slot_state='terminal'),
                'station',7,'old','a'*64,10,clock=lambda:0,sleeper=lambda _:None)
    def test_old_info_then_new_http_then_independent_new_info(self):
        fresh='f'*32;infos=iter([dict(provisioning_generation=7,status={'boot_id':'old'}),dict(provisioning_generation=8,status={'boot_id':fresh})])
        now=[0]
        def sleep(value):now[0]+=value
        def slot():return dict(device_id=DEVICE,boot_id=fresh,generation=8,request_id_digest='a'*64,slot_state='none')
        observed=dispatch.wait_saved_boot(lambda:next(infos),slot,'station',7,'old','a'*64,10,clock=lambda:now[0],sleeper=sleep)
        self.assertEqual(observed['status']['boot_id'],fresh)
        for bad in [dict(slot(),generation=7),dict(slot(),device_id='foreign'),dict(slot(),request_id_digest=None),dict(slot(),boot_id='unknown')]:
            with self.assertRaises(ValueError):
                dispatch.wait_saved_boot(lambda:dict(provisioning_generation=7,status={'boot_id':'old'}),lambda:bad,
                    'station',7,'old','a'*64,10,clock=lambda:0,sleeper=lambda _:None)
        infos=iter([dict(provisioning_generation=7,status={'boot_id':'old'}),dict(provisioning_generation=8,status={'boot_id':'e'*32})])
        with self.assertRaises(ValueError):
            dispatch.wait_saved_boot(lambda:next(infos),slot,'station',7,'old','a'*64,10,clock=lambda:0,sleeper=lambda _:None)
    def test_reset_only_recovery_never_calls_absent_station_helpers(self):
        class Remote:
            def __init__(self,root):pass
            def invoke(self,*args,**kwargs):raise AssertionError('No station helper was staged')
            def fixture(self,*args):raise AssertionError('No station fixture was created')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest={'source_commit':'a'*40}
            binding=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            parent.private_write(root/'campaign-config.json',dict(campaign_id='b'*32,manifest_sha256=binding,
                source_commit='a'*40,selected_cases=['provisioning','full']))
            calls=[]
            def restore(*args):calls.append('restore');return {'restored':True}
            self.assertTrue(parent.recover_populated(manifest,root,root,root/'inspector',
                restore=restore,remote_factory=Remote)['restored'])
            self.assertEqual(calls,['restore'])

    def test_recovery_only_cleans_orphans_even_if_restore_fails(self):
        for restore_failure in (False,True):
            for observer_failure in (False,True):
                calls=[]
                class Remote:
                    def __init__(self,root):pass
                    def invoke(self,*a,**kw):
                        calls.append('observer cleanup')
                        if observer_failure:raise RuntimeError('observer cleanup injected failure')
                    def fixture(self,action,args):calls.append(action)
                def restore(*args):
                    calls.append('restore')
                    if restore_failure:raise RuntimeError('restore injected failure')
                    return {'restored':True}
                with tempfile.TemporaryDirectory() as directory:
                    root=Path(directory);manifest={'source_commit':'a'*40}
                    binding=hashlib.sha256(json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                    parent.private_write(root/'campaign-config.json',dict(campaign_id='b'*32,manifest_sha256=binding,source_commit='a'*40))
                    if restore_failure or observer_failure:
                        with self.assertRaises(RuntimeError):parent.recover_populated(manifest,root,root,root/'inspector',restore=restore,remote_factory=Remote)
                    else:self.assertTrue(parent.recover_populated(manifest,root,root,root/'inspector',restore=restore,remote_factory=Remote)['restored'])
                self.assertEqual(calls,['restore','observer cleanup','finish'])
    def test_full_flash_readback_rom_redeploy_before_second_save(self):
        calls=[]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'manifest.json').write_text('{}');(root/'populated-network.json').write_text('{}')
            data=b'\xff'*(4*1024*1024);path=root/'seed.bin';path.write_bytes(data)
            station=dict(callsign='K1ABC',locator='FN20',power_dbm=27)
            profile=dict(tls={'real':'retained'},clients=[1,2],station=station,request_sha256='0'*64)
            seed=dict(inspection=dict(profile_payload=json.dumps(profile),profile_sequence=5))
            class Backend:
                remote='/private/mock'
                def __init__(self):self.rom=False;self.generation=5;self.boot='initial';self.profile=copy.deepcopy(profile)
                def info(self):
                    calls.append('info')
                    if self.rom:raise TimeoutError('ROM has no console')
                    return dict(provisioning_generation=self.generation,provisioning_source='consumer_preclock',local_suffix='abcdef',status={'boot_id':self.boot})
                def snapshot(self,name):
                    calls.append('snapshot '+name);self.rom=True;(root/name).write_bytes(data)
                    return dict(path=name,inspection=dict(profile_payload=json.dumps(self.profile),profile_sequence=self.generation))
                def deploy(self,role,observed,name):
                    calls.append('deploy '+name);self.rom=False;self.boot='diagnostic';return dict(info=self.info())
            backend=Backend()
            class Remote:
                def invoke(self,script,payload,**kw):
                    # Mirrors the adapter's required actual ordinary INFO.
                    backend.info();calls.append('invoke '+payload['case']);backend.generation+=1
                    backend.boot='activation-'+payload['case'];digest=str(backend.generation)*64
                    backend.profile['request_sha256']=digest
                    return dict(status='POPULATED_SAVES_REVIEW_REQUIRED',cases=[dict(request_digest=digest,boot_id=backend.boot)])
                def collect(self,names):
                    for name in names:(root/name).write_text('{}')
            class Ledger:
                def record(self,name,**kw):calls.append(name)
            with patch.object(parent,'safe_info',lambda info,*args:info):
                observed,rows=parent.run_saves(backend,Remote(),root,{'source_commit':'a'*40},seed,path,station,lambda:None,Ledger())
            self.assertEqual(len(rows),2);self.assertTrue(backend.rom)
            self.assertLess(calls.index('snapshot after-station-save.bin'),calls.index('deploy after-station-readback-redeployment.bin'))
            self.assertLess(calls.index('deploy after-station-readback-redeployment.bin'),calls.index('invoke network'))
            self.assertIn('diagnostic_readback_redeployment',calls)
            self.assertEqual(calls.count('invoke station'),1);self.assertEqual(calls.count('invoke network'),1)
    def test_no_hardware_on_bad_authority(self):
        with self.assertRaises(ValueError):dispatch.run({'authority':'foreign'})
if __name__=='__main__':unittest.main()
