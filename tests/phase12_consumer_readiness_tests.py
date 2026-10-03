#!/usr/bin/env python3
"""Cold-checkpoint warm readiness failure paths and actual isolated helper closure."""
import contextlib,copy,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_consumer_readiness as body
import phase12_consumer_readiness_dispatch as dispatch
import phase12_consumer_readiness_fixture as fixture
import phase12_consumer_readiness_orchestrator as parent
import phase12_engineering_network_dispatch as network
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

if __name__=='__main__':unittest.main()
