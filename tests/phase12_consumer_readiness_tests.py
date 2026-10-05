#!/usr/bin/env python3
"""Cold-checkpoint warm readiness failure paths and actual isolated helper closure."""
import ast,contextlib,copy,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_consumer_readiness_ap as ap
import phase12_consumer_readiness as body
import phase12_consumer_readiness_dispatch as dispatch
import phase12_consumer_readiness_fixture as fixture
import phase12_consumer_readiness_orchestrator as parent
import phase12_engineering_network_dispatch as network
import phase12_engineering_fixture as station_fixture
from phase12_fixture_roles import role_map
from phase12_recovery_device import DEVICE

class Evidence:
    def __init__(self):self.rows=[]
    def record(self,kind,**value):self.rows.append((kind,value))

class BodyTests(unittest.TestCase):
    def setUp(self):
        self.now=0;self.enabled=0;self.evidence=Evidence();self.public_count=0
        self.request=dict(case='station',source_commit='a'*40,generation=7,boot_id='b'*32,
            station={'callsign':'SYNTHETIC','locator':'AA00','power_dbm':0},time_server='192.168.84.1')
        self.health=patch.object(body,'resource_health');self.health.start();self.addCleanup(self.health.stop)
    def info(self,ready=False,pending=False,boot=None,generation=None):
        return dict(device_id=DEVICE,revision='a'*12,firmware='0.0.0-devel',provisioning_source='consumer_preclock',
            access_state='healthy',provisioning_generation=str(self.request['generation'] if generation is None else generation),
            saved_consumer_profile={'station':self.request['station'].copy(),'tls_pending':pending},lan_wtp_ready=ready,
            network=dict(ntp_server=self.request['time_server'],accepted='1' if ready else '0',link_status=3 if ready else -1,ipv4='192.168.84.2' if ready else '0.0.0.0'),
            status=dict(boot_id=boot or self.request['boot_id'],clock_state='synchronized' if ready else 'unsynchronized',
                storage_healthy=True,engine='inhibited-standalone-simulator',enabled=False,output_active=False,state='empty',owner_id=None,job_id=None))
    def public(self,info,ready=False):
        return dict(version=1,device_id=DEVICE,boot_id=info['status']['boot_id'],profile_source=5,generation=info['provisioning_generation'],
            clock_ready=ready,tls_ready=ready,readiness='ready' if ready else 'pending_trustworthy_time_or_tls')
    def sleep(self,seconds):self.now+=seconds
    def run_case(self,rows,public_error=False,late_fifth=False,deadline=30):
        first=self.info(pending=self.request['case']=='pending-tls');index=0;last=first
        def observe():
            nonlocal index,last
            last=first if index==0 else rows[min(index-1,len(rows)-1)];index+=1
            if late_fifth and index==6:self.now=deadline
            return copy.deepcopy(last)
        def public():
            self.public_count+=1
            if public_error and self.public_count>1:raise OSError('ordinary AP withdrawn')
            return self.public(last,ready=self.public_count>1)
        def enable():self.enabled+=1
        return body.exercise(self.request,observe,public,enable,self.evidence,deadline=deadline,
            clock=lambda:self.now,sleeper=self.sleep)
    def test_preserved_complete_tls_keeps_generation_boot_and_reports_five_actual_samples(self):
        result=self.run_case([self.info(ready=True)])
        self.assertEqual(result['generation'],7);self.assertEqual(result['boot_id'],'b'*32)
        self.assertEqual(len(result['samples']),5);self.assertTrue(result['public_ready_observed'])
        self.assertEqual(result['submit_attempts'],0);self.assertEqual(self.enabled,1)
    def test_pending_materialization_requires_one_generation_and_fresh_boot(self):
        self.request['case']='pending-tls'
        result=self.run_case([self.info(pending=True),self.info(ready=True,boot='c'*32,generation=8)])
        self.assertTrue(result['materialization']);self.assertEqual(result['generation'],8)
        self.assertEqual(result['boot_id'],'c'*32);self.assertEqual(self.enabled,1)
    def test_second_materialization_boot_before_readiness_refused(self):
        self.request['case']='pending-tls'
        with self.assertRaisesRegex(ValueError,'multiple materialization'):
            self.run_case([self.info(boot='c'*32,generation=8),self.info(ready=True,boot='d'*32,generation=8)])
    def test_unchanged_boot_or_pending_tls_cannot_count_as_materialized(self):
        self.request['case']='pending-tls'
        for value in (self.info(ready=True,generation=8),self.info(ready=True,pending=True,boot='c'*32,generation=8)):
            self.now=0;self.public_count=0
            with self.assertRaisesRegex(ValueError,'readiness deadline'):self.run_case([value],deadline=3)
    def test_time_unavailable_never_claims_readiness_or_retries_enable(self):
        with self.assertRaisesRegex(ValueError,'readiness deadline'):self.run_case([self.info()],deadline=3)
        self.assertEqual(self.enabled,1)
    def test_wrong_source_generation_settings_output_or_unexpected_reboot_failclosed(self):
        for kind in ('source','generation','station','time','output','boot'):
            value=self.info(ready=True);self.now=0
            if kind=='source':value['revision']='f'*12
            if kind=='generation':value['provisioning_generation']='9'
            if kind=='station':value['saved_consumer_profile']['station']['locator']='AA01'
            if kind=='time':value['network']['ntp_server']='192.168.84.254'
            if kind=='output':value['status']['output_active']=True
            if kind=='boot':value['status']['boot_id']='c'*32
            with self.subTest(kind=kind),self.assertRaises(ValueError):self.run_case([value])
    def test_late_fifth_observation_cannot_complete(self):
        with self.assertRaisesRegex(ValueError,'late readiness'):self.run_case([self.info(ready=True)],late_fifth=True)
    def test_withdrawn_http_carrier_is_explicit_info_native_scope_without_ready_public_claim(self):
        result=self.run_case([self.info(ready=True)],public_error=True)
        self.assertIsNone(result['public_ready']);self.assertFalse(result['public_ready_observed'])
        self.assertEqual(self.public_count,4);self.assertEqual(len(result['samples']),5)
    def test_readiness_loss_after_first_sample_refused(self):
        with self.assertRaisesRegex(ValueError,'readiness lost'):self.run_case([self.info(ready=True),self.info()])
    def test_typed_original_public_flags_version_and_generation_are_required(self):
        info=self.info();public=self.public(info)
        for field,value in (('version',2),('version',True),('clock_ready','false'),('tls_ready','false'),('generation','8')):
            changed=public.copy();changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):body.bound_public(changed,info)

class HelperTests(unittest.TestCase):
    def staged_network(self,directory):
        root=Path(directory)/'controller';root.mkdir(mode=0o700)
        parent.private_write(root/'observer-inputs.json',{'original_helper':'f'*64})
        remote_root=Path(directory)/('phase12-recovery-'+'a'*32);remote_root.mkdir(mode=0o700)
        selected=dict(ssid='p12-'+'1'*12,password='2'*32,time_server='192.168.84.1')
        calls=[]
        class Remote:
            def stage(self,path,name):
                calls.append(name);destination=remote_root/name
                destination.write_bytes(Path(path).read_bytes());destination.chmod(0o600)
                return hashlib.sha256(destination.read_bytes()).hexdigest()
        inputs=parent.stage_network(root,Remote(),selected)
        return root,remote_root,selected,inputs,calls
    def test_parent_staged_inputs_drive_actual_owned_ap_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root,staged,selected,inputs,calls=self.staged_network(directory)
            request=dict(network_sha256=inputs['readiness-network.json'],
                populated_network_sha256=inputs['populated-network.json'],time_server=selected['time_server'])
            self.assertEqual(dispatch.load_network(staged,request),selected)
            self.assertEqual(calls,['readiness-network.json','populated-network.json'])
            self.assertEqual(inputs['readiness-network.json'],inputs['populated-network.json'])
            self.assertEqual(json.loads((root/'observer-inputs.json').read_bytes()),{'original_helper':'f'*64})
            self.assertEqual(json.loads((root/'readiness-network-inputs.json').read_bytes()),inputs)
            self.assertEqual((root/'readiness-network-inputs.json').stat().st_mode&0o777,0o600)
            observed=[]
            def read(*argv):
                observed.append(argv)
                if argv[:3]==('nmcli','-g','GENERAL.CONNECTION'):
                    return 'p12-engineering-'+staged.name.rsplit('-',1)[1]+'\n'
                if argv[0]=='nmcli':
                    return '\n'.join([selected['ssid'],'ap','3','wpa-psk','rsn','ccmp','ccmp'])+'\n'
                if argv==('sudo','-n','/usr/sbin/iw','dev','wlan2','info'):
                    return 'Interface wlan2\n\taddr e8:4e:06:ae:d7:09\n\tssid '+selected['ssid']+'\n\ttype AP\n\tchannel 3 (2422 MHz), width: 20 MHz\n'
                raise AssertionError('unexpected fixture reader')
            actual=station_fixture.owned_ap_configuration(staged,role_map(),read)
            self.assertEqual(actual['ssid'],selected['ssid']);self.assertEqual(actual['interface'],'wlan2')
            self.assertEqual(actual['frequency_mhz'],2422);self.assertEqual(actual['bssid'],'e8:4e:06:ae:d7:09')
            self.assertEqual(len(observed),3)
            for name in calls:
                self.assertEqual((staged/name).stat().st_mode&0o777,0o600)
                self.assertEqual((staged/name).read_bytes(),(root/'readiness-network.json').read_bytes())
            # Regression: removing exactly the formerly omitted staged artifact
            # must fail in the real production reader, before any host query.
            (staged/'populated-network.json').unlink();observed.clear()
            with self.assertRaises(FileNotFoundError):station_fixture.owned_ap_configuration(staged,role_map(),read)
            self.assertEqual(observed,[])
    def test_dispatch_rejects_missing_drifted_and_cross_bound_network_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            _,staged,selected,inputs,_=self.staged_network(directory)
            request=dict(network_sha256=inputs['readiness-network.json'],
                populated_network_sha256=inputs['populated-network.json'],time_server=selected['time_server'])
            original=(staged/'populated-network.json').read_bytes()
            for kind in ('changed','cross-hash','missing','symlink'):
                path=staged/'populated-network.json'
                if path.exists() or path.is_symlink():path.unlink()
                path.write_bytes(original);path.chmod(0o600);value=request.copy()
                if kind=='changed':path.write_bytes(original+b' ')
                if kind=='cross-hash':value['populated_network_sha256']='f'*64
                if kind=='missing':path.unlink()
                if kind=='symlink':path.unlink();path.symlink_to(staged/'readiness-network.json')
                with self.subTest(kind=kind),self.assertRaises((ValueError,FileNotFoundError,OSError)):
                    dispatch.load_network(staged,value)
    def test_parent_rejects_swapped_before_inspection_backend_or_staging(self):
        with patch.object(parent,'accepted_checkpoint') as checkpoint:
            with self.assertRaisesRegex(ValueError,'engineering radio roles'):
                parent.execute({},'artifacts','campaign','inspector','native','checkpoint','station',fixture_roles='swapped')
            checkpoint.assert_not_called()
    def test_dispatch_rejects_swapped_before_manifest_observer_or_host_queries(self):
        remote='/home/pi/phase12-recovery-'+'a'*32
        class Root:
            def __str__(self):return remote
            def is_dir(self):return True
            def is_symlink(self):return False
        swapped=role_map('swapped')
        with patch.object(dispatch,'Path',return_value=Root()),patch.object(dispatch,'load_roles',return_value=swapped),\
                patch.object(dispatch,'private_bytes') as read,patch.object(dispatch,'Observer') as observer,\
                patch.object(dispatch,'management') as management:
            with self.assertRaisesRegex(ValueError,'engineering radio roles'):
                dispatch.run(dict(authority='USER_AUTHORIZED_UNATTENDED_PHASE12',root=remote,roles_sha256=swapped['sha256']))
            read.assert_not_called();observer.assert_not_called();management.assert_not_called()
    def test_actual_management_tuple_import_and_isolated_staging_closure(self):
        self.assertIs(dispatch.management,network.management)
        with tempfile.TemporaryDirectory() as directory:
            for name in parent.STAGED_HELPERS:shutil.copyfile(Path(parent.__file__).parent/name,Path(directory)/name)
            result=subprocess.run([sys.executable,'-I','-c','import sys;sys.path.insert(0,sys.argv[1]);import phase12_consumer_readiness_dispatch,phase12_consumer_readiness_fixture',directory],
                cwd=directory,capture_output=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr.decode())
    def test_alias_direct_api_holds_same_nonblocking_lock_and_busy_never_calls_action(self):
        root='/home/pi/phase12-recovery-'+'a'*32;events=[]
        class Root:
            def __str__(self):return root
            def is_dir(self):return True
            def is_symlink(self):return False
            def __truediv__(self,name):return root+'/'+name
        with patch.object(fixture,'Path',return_value=Root()),patch.object(fixture.os,'open',return_value=123) as opened,\
                patch.object(fixture.os,'close'),patch.object(fixture.fcntl,'flock',side_effect=lambda *a:events.append('lock')),\
                patch.object(fixture,'_action',side_effect=lambda r:events.append('action')):
            fixture.action({'root':root})
        self.assertEqual(events,['lock','action']);self.assertEqual(opened.call_args.args[1],os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW)
        with patch.object(fixture,'Path',return_value=Root()),patch.object(fixture.os,'open',return_value=123),\
                patch.object(fixture.os,'close'),patch.object(fixture.fcntl,'flock',side_effect=BlockingIOError('previous alias action running')),\
                patch.object(fixture,'_action') as action:
            with self.assertRaises(BlockingIOError):fixture.action({'root':root})
            action.assert_not_called()
    def test_alias_owner_requires_exact_interface_index_prefix_and_label(self):
        receipt=dict(ifindex=7,label='wlan2:p12abcd')
        row=dict(ifindex=7,addr_info=[dict(family='inet',local=fixture.ADDRESS,prefixlen=24,label='wlan2:p12abcd')])
        self.assertTrue(fixture.owns_alias(row,receipt))
        for kind in ('ifindex','label','prefix','duplicate'):
            changed=copy.deepcopy(row)
            if kind=='ifindex':changed['ifindex']=8
            if kind=='label':changed['addr_info'][0]['label']='foreign'
            if kind=='prefix':changed['addr_info'][0]['prefixlen']=16
            if kind=='duplicate':changed['addr_info']*=2
            self.assertFalse(fixture.owns_alias(changed,receipt))
    def test_owned_responder_pid_root_token_and_script_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path('/home/pi/phase12-recovery-'+'a'*32);process=Path(directory)/'123';process.mkdir()
            receipt=dict(pid=123,startup_token='b'*32)
            args=[b'python3',str(Path(fixture.__file__).resolve()).encode(),b'--serve-alias',str(root).encode(),b'b'*32]
            (process/'cmdline').write_bytes(b'\0'.join(args)+b'\0')
            self.assertTrue(fixture.process_bound(root,receipt,process_root=Path(directory)))
            for index in (1,2,3,4):
                changed=args.copy();changed[index]=b'foreign';(process/'cmdline').write_bytes(b'\0'.join(changed))
                with self.assertRaisesRegex(ValueError,'process identity'):fixture.process_bound(root,receipt,process_root=Path(directory))
    def test_actual_owned_ap_namespace_matches_start_adapter(self):
        import ast
        tree=ast.parse((Path(fixture.__file__).parent/'phase12_engineering_fixture.py').read_text())
        assignments=[n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='name' for t in n.targets)]
        self.assertTrue(any(isinstance(n,ast.BinOp) and isinstance(n.left,ast.Constant) and n.left.value=='p12-engineering-' for n in assignments))
        self.assertIn("name='p12-engineering-'",Path(fixture.__file__).read_text())
    def test_actual_alias_start_requires_owned_ap_and_retains_pi_readable_original_wire(self):
        remote='/home/pi/phase12-recovery-'+'a'*32;roles={'host_ap':'wlan2','sha256':'c'*64}
        before=dict(ifname='wlan2',ifindex=7,addr_info=[dict(family='inet',local='192.168.84.1',prefixlen=24)])
        calls=[];added=False;real_path=Path
        with tempfile.TemporaryDirectory() as directory:
            local=Path(directory)
            class Root:
                name=remote.rsplit('/',1)[1]
                def __str__(self):return remote
                def is_dir(self):return True
                def is_symlink(self):return False
                def __truediv__(self,name):return local/name
            def path(value):return Root() if value==remote else real_path(value)
            def addresses(interface):
                row=copy.deepcopy(before)
                if added:row['addr_info'].append(dict(family='inet',local=fixture.ADDRESS,prefixlen=24,label='wlan2:p120000'))
                return row
            def command(*args):
                nonlocal added
                calls.append(args)
                if args[0]=='nmcli':return 'p12-engineering-'+'a'*32+'\n'
                if 'add' in args:added=True
                return ''
            def popen(argv,**kw):
                # The daemon's private append target already belongs to the
                # ordinary action user before any sudo process is launched.
                wire=local/'readiness-time-wire.jsonl'
                self.assertTrue(wire.is_file());self.assertEqual(wire.stat().st_mode&0o777,0o600)
                self.assertEqual(wire.stat().st_uid,os.getuid())
                (local/'readiness-alias-ready.json').write_text(json.dumps(dict(pid=123,startup_token='0'*32,address=fixture.ADDRESS,
                    roles_sha256=roles['sha256'],duration_s=fixture.DURATION)))
                return SimpleNamespace(pid=123,poll=lambda:None)
            with patch.object(fixture,'Path',side_effect=path),patch.object(fixture,'load_roles',return_value=roles),\
                    patch.object(fixture,'addresses',side_effect=addresses),patch.object(fixture,'command',side_effect=command),\
                    patch.object(fixture,'management',return_value={'unchanged':'management'}),patch.object(fixture.os,'urandom',return_value=bytes(16)),\
                    patch.object(fixture.subprocess,'Popen',side_effect=popen),patch.object(fixture,'process_bound',return_value=True):
                result=fixture._action(dict(root=remote,authority='USER_AUTHORIZED_UNATTENDED_PHASE12',roles_sha256=roles['sha256'],action='start'))
            self.assertEqual(result['status'],'OWNED_ALIAS_STARTED_DISABLED')
            self.assertIn(('sudo','-n','ip','address','add','192.168.84.254/24','dev','wlan2','label','wlan2:p120000'),calls)
            self.assertFalse((local/'readiness-alias-enabled.json').exists())
            self.assertEqual(json.loads((local/'readiness-alias-owned.json').read_text())['pid'],123)

class TimeEvidenceTests(unittest.TestCase):
    def test_original_alias_raw_packets_peer_and_cleanup_are_all_required(self):
        from phase12_engineering_fixture import ntp_reply
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);peer='192.168.84.2';query=bytearray(48);query[0]=0x23;query[40:48]=bytes(range(1,9))
            utc=1791054577000000000;row=dict(peer_address=peer,query_hex=bytes(query).hex(),reply_hex=ntp_reply(bytes(query),utc).hex(),
                utc_ns=utc,monotonic_before_ns=1,monotonic_after_ns=2)
            (root/'ntp-peer.json').write_text(json.dumps({'address':peer}));(root/'readiness-alias-cleanup.json').write_text(json.dumps({'status':'OWNED_ALIAS_REMOVED'}))
            path=root/'readiness-time-wire.jsonl';result={'samples':[{'network':{'ipv4':peer}}]*5}
            def write(value):path.write_text(json.dumps(value)+'\n');path.chmod(0o600)
            write(row);self.assertEqual(parent.time_evidence('network',root,result)['status'],'ORIGINAL_TIME_RESPONDER_EVIDENCE_BOUND')
            for kind in ('peer','reply','late','empty','cleanup'):
                changed=row.copy();write(row)
                if kind=='peer':changed['peer_address']='192.168.84.3'
                if kind=='reply':changed['reply_hex']='00'*48
                if kind=='late':changed['monotonic_before_ns']=3
                if kind=='empty':path.write_bytes(b'')
                elif kind=='cleanup':(root/'readiness-alias-cleanup.json').write_text(json.dumps({'status':'UNKNOWN'}))
                else:write(changed)
                with self.subTest(kind=kind),self.assertRaises(ValueError):parent.time_evidence('network',root,result)
                (root/'readiness-alias-cleanup.json').write_text(json.dumps({'status':'OWNED_ALIAS_REMOVED'}))

class ParentFailureTests(unittest.TestCase):
    def test_actual_parent_handoff_reaches_real_ap_reader_preserving_original_input_receipt(self):
        raw=bytes(4194304);digest=hashlib.sha256(raw).hexdigest();seen=[]
        selected=dict(ssid='p12-'+'1'*12,password='2'*32,time_server='192.168.84.1')
        profile={'network':selected,'station':{'callsign':'SYNTHETIC','locator':'AA00','power_dbm':0}}
        class Backend:
            def __init__(self,plan,manifest,artifacts,root,inspector):self.remote='/home/pi/phase12-recovery-'+plan['campaign_id'];self.root=root
            def setup(self):return {}
            def snapshot(self,name):
                (self.root/name).write_bytes(raw);(self.root/name).chmod(0o600)
                return dict(path=name,sha256=digest,inspection={})
            def restore(self,saved,name):
                return dict(readback={'sha256':digest},info={'status':{'boot_id':'b'*32},'local_suffix':'000000'})
            def stable_restore(self,*args):return {'samples':5}
            def cleanup(self):pass
        class Remote:
            def __init__(self,root):self.root=root
            def staged(self):return self.root.parent/Path(self.backend.remote).name
            def stage(self,path,name):
                staged=self.staged();staged.mkdir(mode=0o700,exist_ok=True)
                destination=staged/name;destination.write_bytes(Path(path).read_bytes());destination.chmod(0o600)
                return hashlib.sha256(destination.read_bytes()).hexdigest()
            def invoke(self,script,request,**kwargs):
                if script!='phase12_consumer_readiness_dispatch.py':return {}
                staged=self.staged();seen.append(dispatch.load_network(staged,request))
                def read(*argv):
                    if argv[:3]==('nmcli','-g','GENERAL.CONNECTION'):
                        return 'p12-engineering-'+staged.name.rsplit('-',1)[1]+'\n'
                    if argv[0]=='nmcli':return '\n'.join([selected['ssid'],'ap','3','wpa-psk','rsn','ccmp','ccmp'])+'\n'
                    if argv==('sudo','-n','/usr/sbin/iw','dev','wlan2','info'):
                        return 'Interface wlan2\n\taddr e8:4e:06:ae:d7:09\n\tssid '+selected['ssid']+'\n\ttype AP\n\tchannel 3 (2422 MHz), width: 20 MHz\n'
                    raise AssertionError('unexpected fixture reader')
                seen.append(station_fixture.owned_ap_configuration(staged,role_map(),read))
                raise ValueError('intentional stop after real owned AP reader')
            def collect(self,names):
                if names==('final-restoration.bin',):
                    path=self.root/'final-restoration.bin';path.write_bytes(raw);path.chmod(0o600)
        with tempfile.TemporaryDirectory() as directory:
            artifacts=Path(directory)/'artifacts';artifacts.mkdir();(artifacts/'restore.uf2').write_bytes(b'opaque-test-UF2')
            checkpoint_path=Path(directory)/'checkpoint.bin';checkpoint_path.write_bytes(raw);checkpoint_path.chmod(0o600)
            manifest=dict(source_commit='a'*40,candidates=[{'role':'restore','uf2':{'path':'restore.uf2'}}])
            checkpoint=dict(path=checkpoint_path,sha256=digest,inspection={'profile_payload':json.dumps(profile),'profile_sequence':7},original_result_sha256='c'*64)
            root=Path(directory)/'campaign'
            with patch.object(parent,'accepted_checkpoint',return_value=checkpoint),patch.object(parent,'safe_info'),patch.object(parent,'verify_image'):
                result=parent.execute(manifest,artifacts,root,'inspector','native',checkpoint_path,'station',backend_factory=Backend,remote_factory=Remote)
            self.assertEqual(result['error']['message'],'intentional stop after real owned AP reader')
            self.assertEqual(len(seen),2);self.assertEqual(seen[0],selected);self.assertEqual(seen[1]['interface'],'wlan2')
            initial=json.loads((root/'observer-inputs.json').read_bytes());network_inputs=json.loads((root/'readiness-network-inputs.json').read_bytes())
            self.assertIn('fixture-roles.json',initial);self.assertNotIn('readiness-network.json',initial)
            self.assertEqual(set(network_inputs),{'readiness-network.json','populated-network.json'})
            self.assertEqual(len(set(network_inputs.values())),1);self.assertEqual(result['cleanup_errors'],[])
            self.assertEqual(result['restoration']['stability']['samples'],5)
    def test_body_failure_restores_exact_original_and_releases_guard_without_save(self):
        raw=bytes(4194304);digest=hashlib.sha256(raw).hexdigest();calls=[];source='a'*40
        class Backend:
            def __init__(self,plan,manifest,artifacts,root,inspector):self.remote='/home/pi/phase12-recovery-'+plan['campaign_id'];self.root=root
            def setup(self):calls.append('setup');return {}
            def snapshot(self,name):
                (self.root/name).write_bytes(raw);(self.root/name).chmod(0o600)
                return dict(path=name,sha256=digest,inspection={})
            def restore(self,baseline,name):calls.append(name);return dict(readback={'sha256':digest})
            def stable_restore(self,*args):calls.append('stable');return {'samples':5}
            def cleanup(self):calls.append('cleanup')
        class Remote:
            def __init__(self,root):self.root=root
            def stage(self,*args):raise ValueError('original staging failure')
            def collect(self,names):
                self.assert_names=names;(self.root/'final-restoration.bin').write_bytes(raw);(self.root/'final-restoration.bin').chmod(0o600)
        with tempfile.TemporaryDirectory() as directory:
            artifacts=Path(directory)/'artifacts';artifacts.mkdir();(artifacts/'restore.uf2').write_bytes(b'opaque-test-UF2')
            manifest=dict(source_commit=source,candidates=[{'role':'restore','uf2':{'path':'restore.uf2'}}])
            checkpoint=dict(sha256=digest,inspection={},original_result_sha256='b'*64)
            with patch.object(parent,'accepted_checkpoint',return_value=checkpoint),patch.object(parent,'safe_info'),patch.object(parent,'verify_image'):
                result=parent.execute(manifest,artifacts,Path(directory)/'campaign','inspector','native','checkpoint','station',backend_factory=Backend,remote_factory=Remote)
        self.assertEqual(result['status'],'STOPPED');self.assertEqual(result['error']['message'],'original staging failure')
        self.assertEqual(calls,['setup','final-restoration.bin','stable','cleanup'])
        self.assertEqual(result['submit_attempts'],0);self.assertEqual(result['restoration']['stability']['samples'],5)

write=ap.write
binding=SimpleNamespace(SOURCE='a'*40,AUTHORITY='USER_AUTHORIZED_UNATTENDED_PHASE12',require=parent.require)

class OfflineCycle(unittest.TestCase):
 def test_real_same_uuid_down_up_preserves_disabled_time_and_originals(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/('phase12-recovery-'+'a'*32);root.mkdir();uuid='11111111-2222-3333-4444-555555555555';name='p12-engineering-'+root.name.rsplit('-',1)[1]
   roles=dict(host_ap='wlan2');managed=dict(addresses=[],defaults=[]);responder=dict(pid=123)
   request=dict(root=str(root),case='network',generation=8,inputs={},boot_id='new')
   receipt=dict(root=str(root),case='network',generation=8,inputs={},activation_attempts=1,deadline_monotonic_s=300,management_before=managed,ntp_identity=responder,ap=dict(connection=name))
   write(root/'readiness-ap-ready-before-boot.json',receipt);request['ap_ready_sha256']=hashlib.sha256((root/'readiness-ap-ready-before-boot.json').read_bytes()).hexdigest()
   calls=[];events=[];active=[True]
   class Evidence:
    def record(self,label,**values):events.append((label,values))
   def runner(argv,**kwargs):
    calls.append(argv)
    if 'connection.uuid' in argv:raw=(uuid+'\n').encode()
    elif 'GENERAL.STATE' in argv:raw=b'30 (disconnected)\n'
    elif 'down' in argv:active[0]=False;raw=b'Connection successfully deactivated\n'
    elif 'up' in argv:active[0]=True;raw=b'Connection successfully activated\n'
    else:raise AssertionError(argv)
    return subprocess.CompletedProcess(argv,0,raw,b'')
   def reuse(*args,**kwargs):self.assertTrue(active[0]);return receipt
   with patch.object(ap,'inputs',return_value=(roles,{})),patch.object(ap,'reuse',side_effect=reuse):
    for operation in ('down','up'):
     result=ap.station_cycle(request,operation,Evidence(),110,clock=lambda:2,runner=runner,managed=lambda _:managed,disabled=lambda *_:responder)
     self.assertFalse(result['ntp_enabled']);self.assertEqual(result['connection_uuid'],uuid)
    self.assertEqual(result['total_activation_attempts'],2)
    self.assertEqual([a for a in calls if a[0]=='sudo'],[['sudo','-n','nmcli','--wait','9','connection','down','uuid',uuid],['sudo','-n','nmcli','--wait','9','connection','up','uuid',uuid]])
    with self.assertRaisesRegex(ValueError,'never replayed'):ap.station_cycle(request,'up',Evidence(),110,clock=lambda:2,runner=runner,managed=lambda _:managed,disabled=lambda *_:responder)
   originals=[v for k,v in events if k=='station_cycle_command']
   self.assertEqual(len(originals),len(calls));self.assertTrue(all('stdout_hex' in row and 'stderr_hex' in row for row in originals))
 def test_observed_join_loss_then_sixty_seconds_uses_same_association_end(self):
  now=[0.];links=iter((3,1,1));observations=[];events=[]
  class Evidence:
   def record(self,label,**values):events.append((label,values))
  def observe(*args,**kwargs):observations.append((now[0],args[2]));return dict(network=dict(link_status=next(links)))
  with patch.object(ap,'offline_info',side_effect=observe):
   result=ap.controlled_loss(dict(boot_id='new',generation=8),None,Evidence(),110,clock=lambda:now[0],sleeper=lambda duration:now.__setitem__(0,now[0]+duration))
  self.assertEqual(now[0],60.5);self.assertEqual(result['network']['link_status'],1)
  self.assertEqual(observations,[(0.,60.),(.5,60.),(60.5,110)])
  self.assertEqual(events[-1][1]['held_seconds'],60.)
 def test_fallback_hold_is_refused_if_original_association_has_no_room(self):
  with patch.object(ap,'offline_info',return_value=dict(network=dict(link_status=1))):
   with self.assertRaisesRegex(ValueError,'within original110'):ap.controlled_loss(dict(boot_id='new',generation=8),None,None,60,clock=lambda:0,sleeper=lambda _:self.fail('no hold outside original deadline'))

class OwnedLossOrderingTests(unittest.TestCase):
 def sequence(self,broken=False):
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve();calls=[];request=dict(root='/home/pi/phase12-recovery-'+'a'*32,case='station',roles_sha256='r',source_commit=binding.SOURCE,generation=7,checkpoint_sha256='c',prior_boot_id='old',inputs={'x':'y'})
    receipt=dict(status='AP_READY_SNTP_DISABLED_BEFORE_BOOT',root=request['root'],case='station',roles_sha256='r',source_commit=binding.SOURCE,generation=7,checkpoint_sha256='c',prior_boot_id='old',inputs={'x':'y'},activation_attempts=1,beacon=dict(status='INDEPENDENT_BEACON_READY',ap_interface='wlan2',observer_interface='wlan0'),started_monotonic_s=1,ready_monotonic_s=2,deadline_monotonic_s=301)
    if broken:receipt['beacon']['status']='FAILED'
    raw=json.dumps(receipt).encode();(root/'readiness-ap-ready-before-boot.json').write_bytes(raw);(root/'readiness-ap-ready-before-boot.json').chmod(0o600)
    class Backend:
     campaign=root
     def restore(self,saved,name):
      calls.append('deploy');self.assert_ready=(root/'ap-ready-before-deployment.json').exists()
      if not self.assert_ready:raise RuntimeError('unretained AP readiness')
      return dict(info=dict(status=dict(boot_id='new'),local_suffix='suffix'))
    class Remote:
     def invoke(self,script,payload,args=(),**kw):calls.append(('prepare',script,args));return dict(status=receipt['status'],receipt=receipt,receipt_sha256=hashlib.sha256(raw).hexdigest())
     def collect(self,names):calls.append(('retain',names))
    if broken:
     with self.assertRaisesRegex(ValueError,'fresh beacon'):parent.deploy_after_ready(Backend(),Remote(),request,{},clock=lambda:3,deadline=340)
     self.assertNotIn('deploy',calls)
    else:
     parent.deploy_after_ready(Backend(),Remote(),request,{},clock=lambda:3,deadline=340)
     self.assertEqual(calls,[('prepare','phase12_consumer_readiness_ap.py',('--prepare-ap',)),('retain',('readiness-ap-ready-before-boot.json',)),'deploy'])
     self.assertEqual(request['boot_id'],'new')
 def test_actual_parent_retains_ap_ready_before_one_deploy(self):self.sequence()
 def test_no_deploy_without_fresh_beacon(self):self.sequence(True)
 def test_real_dispatcher_resumes_owned_uuid_before_station_proof_and_time(self):
   tree=ast.parse(Path(dispatch.__file__).read_bytes())
   run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run');enable=next(n for n in run.body if isinstance(n,ast.FunctionDef) and n.name=='enable_time')
   calls=[]
   with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp).resolve();roles=dict(host_ap='wlan2');request=dict(root=str(root),authority=binding.AUTHORITY,source_commit=binding.SOURCE,generation=7,time_server='192.168.84.1',ap_ready_sha256='r')
    class Evidence:
     def record(self,*a,**k):pass
    value=dict(network=dict(link_status=3,ipv4='192.168.84.3'),status=dict(boot_id='new'))
    def fixture(req):
     calls.append(req['action'])
     if req['action']=='start_ap':raise AssertionError('second AP activation')
     return dict(status='TARGET_ASSOCIATION_VERIFIED',station_ipv4='192.168.84.3')
    def offline(*args,**kwargs):calls.append('offline_info');return value
    def cycle(*args,**kwargs):calls.append('up');return dict(connection_uuid='actual-uuid')
    namespace=dict(owned_loss=True,root=root,roles=roles,request=request,deadline=300,info=lambda:value,fixture_action=fixture,evidence=Evidence(),offline_info=offline,station_cycle=cycle,require=binding.require,json=json,os=os,time=type('Time',(),dict(monotonic=staticmethod(lambda:1),sleep=staticmethod(lambda _:None))),min=min)
    # Remove only enclosing-function nonlocal declarations for exact AST callback.
    node=copy.deepcopy(enable);node.body=[x for x in node.body if not isinstance(x,ast.Nonlocal)]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'actual-readiness-enable','exec'),namespace)
    namespace['enable_time']();self.assertEqual(calls,['offline_info','up','offline_info','prove_target','bind_peer','sntp_on'])
    with self.assertRaisesRegex(ValueError,'never replayed'):namespace['enable_time']()
    self.assertEqual(calls,['offline_info','up','offline_info','prove_target','bind_peer','sntp_on'])

 def test_owned_loss_station_refused_before_any_inspection_or_setup(self):
  with patch.object(parent,'accepted_checkpoint') as inspect:
   with self.assertRaisesRegex(ValueError,'network/pending only'):
    parent.execute({},'artifacts','campaign','inspector','native','checkpoint','station',owned_loss=True)
   inspect.assert_not_called()

class PendingProofOrderingTests(unittest.TestCase):
 def proof(self,case):
  calls=[];root=Path('/private/synthetic-readiness')
  class Backend:
   def snapshot(self,name):calls.append(('native',name));return dict(path=name)
  class Remote:
   def collect(self,names):calls.append(('collect',tuple(names)))
  def time_proof(*args):calls.append('time_proof');return dict(status='time')
  def cold_proof(*args):calls.append('native_tls_proof');return dict(status='native')
  with patch.object(parent,'read_json',return_value={}),patch.object(parent,'private_read',return_value=b'original'),patch.object(parent,'time_evidence',side_effect=time_proof),patch.object(parent,'assess',side_effect=cold_proof):
   result=parent.completed_readiness_proofs(case,Backend(),Remote(),root,{},b'seed',('original-archive',))
  self.assertEqual(result['time_evidence']['status'],'time')
  return calls
 def test_pending_native_precedes_only_four_mandatory_files_and_both_proofs(self):
  self.assertEqual(self.proof('pending-tls'),[('native','after-readiness.bin'),('collect',parent.PENDING_REQUIRED_NAMES),'time_proof','native_tls_proof'])
  self.assertEqual(len(parent.PENDING_REQUIRED_NAMES),4)
 def test_accepted_network_order_is_unchanged(self):
  self.assertEqual(self.proof('network'),[('collect',('original-archive',)),'time_proof',('native','after-readiness.bin'),'native_tls_proof'])

 def test_pending_native_failure_still_archives_originals_then_restores(self):
  raw=bytes(4194304);digest=hashlib.sha256(raw).hexdigest();calls=[]
  profile=dict(network=dict(ssid='synthetic',password='synthetic-password',time_server='192.168.84.1'),station={})
  class Backend:
   def __init__(self,plan,manifest,artifacts,root,inspector):self.remote='/home/pi/phase12-recovery-'+plan['campaign_id'];self.root=root
   def setup(self):return {}
   def snapshot(self,name):
    calls.append(('snapshot',name))
    if name=='after-readiness.bin':raise ValueError('original pending native failure')
    (self.root/name).write_bytes(raw);(self.root/name).chmod(0o600)
    return dict(path=name,sha256=digest,inspection={})
   def restore(self,saved,name):
    calls.append(('restore',name));return dict(readback={'sha256':digest},info={'status':{'boot_id':'b'*32},'local_suffix':'000000'})
   def stable_restore(self,*args):return {'samples':5}
   def cleanup(self):calls.append('cleanup')
  class Remote:
   def __init__(self,root):self.root=root
   def stage(self,path,name):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
   def invoke(self,script,request,**kwargs):
    if script=='phase12_consumer_readiness_dispatch.py':return dict(status='CONSUMER_READINESS_REVIEW_REQUIRED',submit_attempts=0,rf_jobs=0)
    return {}
   def collect(self,names):
    calls.append(('collect',tuple(names)))
    if names==('final-restoration.bin',):(self.root/'final-restoration.bin').write_bytes(raw);(self.root/'final-restoration.bin').chmod(0o600)
  with tempfile.TemporaryDirectory() as directory:
   directory=Path(directory);image=directory/'restore.uf2';image.write_bytes(b'image');seed_path=directory/'seed.bin';seed_path.write_bytes(raw);seed_path.chmod(0o600)
   manifest=dict(source_commit='a'*40,candidates=[dict(role='restore',uf2={'path':'restore.uf2'})])
   seed=dict(path=seed_path,sha256=digest,inspection={'profile_payload':json.dumps(profile),'profile_sequence':8},original_result_sha256='c'*64)
   with patch.object(parent,'accepted_checkpoint',return_value=seed),patch.object(parent,'prepare_pending',return_value=seed),patch.object(parent,'safe_info'),patch.object(parent,'verify_image'):
    result=parent.execute(manifest,directory,directory/'campaign','inspector','native',seed_path,'pending-tls',backend_factory=Backend,remote_factory=Remote)
  self.assertEqual(result['error']['message'],'original pending native failure')
  self.assertEqual(result['status'],'STOPPED')
  self.assertEqual(calls.count(('snapshot','after-readiness.bin')),1)
  self.assertIn(('collect',parent.PENDING_ARCHIVAL_NAMES),calls)
  self.assertNotIn(('collect',parent.PENDING_REQUIRED_NAMES),calls)
  self.assertLess(calls.index(('collect',parent.PENDING_ARCHIVAL_NAMES)),calls.index(('restore','final-restoration.bin')))
  self.assertEqual(calls[-1],'cleanup')

if __name__=='__main__':unittest.main()
