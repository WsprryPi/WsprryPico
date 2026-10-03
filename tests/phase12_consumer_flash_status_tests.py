#!/usr/bin/env python3
"""Actual frame seams and finite one-submit trace/failure behavior; no device I/O."""
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_consumer_flash_status as r
from validate_wtp_contract import frame

class Tests(unittest.TestCase):
    def exercise(self,bad_crc=False,nested=False,unhealthy=False,fixture=False,claimable=True):
        records=[];stamp=[10];submitted=[0];calls=[];boot='a'*32;source='b'*40
        def pair(kind):
            sid=len(records)+1
            for phase,outcome in [('begin','pending'),('end','complete')]:
                stamp[0]+=1;records.append(dict(seq=str(len(records)+1),span=str(sid),monotonic_ns=str(stamp[0]),kind=kind,phase=phase,outcome=outcome))
        def observe(deadline):
            stamp[0]+=1;v=dict(device_id=r.DEVICE,revision=source[:12],provisioning_source='consumer_preclock',provisioning_generation=str(5+submitted[0]),access_state='healthy',lan_wtp_ready=True,network={'link_status':3},status=dict(boot_id=boot,monotonic_now_ns=str(stamp[0]),state='empty',enabled=False,output_active=False,engine='inhibited-standalone-simulator'))
            v.update(firmware='0.0.0-devel',softap_session_inactivity_ms='900000',softap_session_absolute_ms='43200000',core0_stack_guard_valid=1,fault_allocation_recorded=False)
            v['status']['storage_healthy']=True
            for name in ('allocator_failures','tls_allocation_failures','core0_stack_fault_status','fault_stage','fault_hash','fault_pc','fault_status','flash_read_failures','flash_erase_failures','flash_program_failures'):v[name]='0'
            if unhealthy:v['allocator_failures']='1'
            if fixture:v['phase12_fault_stage']='8'
            v['btstack_pools']={name:dict(failures=0,faults=0,used=0,capacity=1) for name in ('hci_connections','l2cap_channels','l2cap_services','sm_lookup','whitelist')}
            v['network']['memory']={name:dict(errors=0,used=0,capacity=1) for name in ('heap','tcp_pcbs','tcp_listeners','udp_pcbs','timeouts','igmp_groups','tcp_segments','packet_pool')};v['network']['memory']['statistics_enabled']=True
            return v,json.dumps(v).encode()
        def con(text,deadline):
            if not claimable:raise AssertionError('unclaimable fixture must stop before trace')
            v=dict(ok=True,device_id=r.DEVICE,revision=source[:12],boot_id=boot,capture_epoch='1')
            if 'BEGIN' in text:v['enabled']=True
            else:v.update(records=records,next_cursor=str(len(records)),record_count=str(len(records)),more=False,overflow=False,clock_regressed=False,open_spans='0',dropped_spans='0')
            return v,json.dumps(v).encode()
        def status(deadline):
            pair('status');rid=f'{len(records):032x}';a=dict(protocol='WTP/1',type='request',session_id='c'*32,request_id=rid,op='STATUS',body={});b=dict(a,type='response',ok=True,body=dict(boot_id=boot,state='empty',owner_id=None,job_id=None,output_active=False));wire=frame(json.dumps(b).encode())
            if bad_crc:wire=wire[:-1]+bytes([wire[-1]^1])
            return frame(json.dumps(a).encode()),wire
        def http(method,path,body,deadline):
            calls.append(path)
            if path.endswith('public-status'):return 200,dict(device_id=r.DEVICE,boot_id=boot,profile_source=5,generation='5',claim_available=claimable),b'req',b'resp'
            if not claimable:raise AssertionError('unclaimable fixture must never mutate')
            if path.endswith('start'):return 200,dict(device_id=r.DEVICE,boot_id=boot,generation='5',browser_nonce='nonce',browser_public_key='key'),b'req',b'resp'
            submitted[0]+=1;pair('profile_erase');pair('profile_program');pair('profile_program')
            if nested:records[-2]['kind']='status';records[-1]['kind']='status'
            return 200,dict(state='checking'),b'req',b'resp'
        with patch.object(r,'keys',return_value=({'browser_nonce':'nonce','browser_public_key':'key'},None)),patch.object(r,'seal',return_value={'request_id':'d'*32}):
            result=r.measure(dict(boot_id=boot,generation=5,source_commit=source,expected_programs=2),{},observe,con,http,status,clock=lambda:0)
        return result,calls
    def test_consumer_association_delegates_once_and_retains_caller_deadline(self):
        import phase12_consumer_flash_status_dispatch as dispatcher
        from unittest.mock import Mock
        evidence=Mock();deadline=dispatcher.time.monotonic()+30
        with patch.object(dispatcher,'associate_observer') as joined,patch.object(dispatcher,'bounded_command',return_value=b'route'),patch.object(dispatcher,'identity',return_value={'management':'same'}):
            dispatcher.associate_guarded('owned','WsprryPico-abcdef',deadline,evidence,{'management':'same'},b'route')
            joined.assert_called_once_with('owned','WsprryPico-abcdef',deadline,evidence,interface='wlan0')
        with patch.object(dispatcher,'associate_observer',side_effect=TimeoutError('uncertain single activation')) as joined,patch.object(dispatcher,'bounded_command') as observe:
            with self.assertRaises(TimeoutError):dispatcher.associate_guarded('owned','WsprryPico-abcdef',deadline,evidence,{},b'route')
            self.assertEqual(joined.call_count,1);observe.assert_not_called()
        with patch.object(dispatcher,'associate_observer'),patch.object(dispatcher,'bounded_command',return_value=b'foreign'),patch.object(dispatcher,'identity',return_value={}):
            with self.assertRaisesRegex(ValueError,'management unchanged'):dispatcher.associate_guarded('owned','WsprryPico-abcdef',deadline,evidence,{},b'route')

    def test_flash_comparison_ignores_application_overlay_but_preserves_reserved(self):
        from phase12_consumer_flash_status_orchestrator import reserved_equal
        seed=bytes(0x400000);actual=bytearray(seed);actual[0]=1
        self.assertTrue(reserved_equal(actual,seed));self.assertTrue(reserved_equal(actual,seed,profile_mutation=True))
        actual[0x3f7000]=1
        self.assertFalse(reserved_equal(actual,seed));self.assertTrue(reserved_equal(actual,seed,profile_mutation=True))
        for offset in (0x3f3000,0x3f5000,0x3fb000,0x3fffff):
            changed=bytearray(seed);changed[offset]=1
            self.assertFalse(reserved_equal(changed,seed));self.assertFalse(reserved_equal(changed,seed,profile_mutation=True))

    def test_exact_staged_helper_closure_imports_without_repo_path(self):
        import tempfile,subprocess,shutil
        import phase12_consumer_flash_status_orchestrator as parent
        with tempfile.TemporaryDirectory() as directory:
            for name in parent.STAGED_HELPERS:shutil.copyfile(Path(__file__).resolve().parents[1]/'scripts'/name,Path(directory)/name)
            code="import sys;sys.path.insert(0,sys.argv[1]);import phase12_consumer_flash_status_dispatch"
            result=subprocess.run([sys.executable,'-I','-c',code,directory],cwd=directory,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr.decode())

    def test_parent_preparation_failure_restores_original_and_cleans(self):
        import tempfile
        import phase12_consumer_flash_status_orchestrator as parent
        calls=[]
        class Backend:
            def __init__(self,plan,manifest,artifacts,root,inspector):self.remote='/home/pi/phase12-recovery-'+plan['campaign_id'];self.root=root;self.roles={}
            def setup(self):return {}
            def snapshot(self,name):p=self.root/name;p.write_bytes(b'backup');return dict(path=name,sha256=parent.sha(p),inspection={})
            def restore(self,baseline,name):calls.append(name);return {'readback':name}
            def stable_restore(self,*args):return {'samples':5}
            def cleanup(self):calls.append('cleanup')
        class Remote:
            def __init__(self,root):pass
            def stage(self,*args):return 'a'*64
            def invoke(self,*args,**kw):calls.append('observercleanup');return {}
            def collect(self,*args):pass
        def fail(*args,**kw):raise ValueError('preparation failed')
        candidate=dict(role='restore',target='WsprryPico',fault_stage=0,gp14=False,lan_mode='plain',session_deadline_fixture=False,uf2={'path':'restore.uf2'})
        with tempfile.TemporaryDirectory() as directory,patch.object(parent,'safe_info',lambda *a:None):
            result=parent.execute({'source_commit':'a'*40},directory,{'source_commit':'b'*40,'candidates':[candidate]},directory,Path(directory)/'new',Path(directory)/'inspector',Path(directory)/'native',backend_factory=Backend,remote_factory=Remote,builder=fail)
        self.assertEqual(result['status'],'STOPPED');self.assertIn('final-restoration.bin',calls);self.assertEqual(calls[-1],'cleanup')

    def test_whole_case_timer_interrupts_blocking_body_before_cleanup(self):
        import tempfile
        import phase12_consumer_flash_status_orchestrator as parent
        import time,signal
        actual_deadline=parent.tranche_deadline
        calls=[]
        class Backend:
            def __init__(self,plan,manifest,artifacts,root,inspector):self.remote='/home/pi/phase12-recovery-'+plan['campaign_id'];self.root=root;self.roles={}
            def setup(self):return {}
            def snapshot(self,name):p=self.root/name;p.write_bytes(b'backup');return dict(path=name,sha256=parent.sha(p),inspection={})
            def restore(self,baseline,name):calls.append(name);return {'readback':name}
            def stable_restore(self,*args):return {'samples':5}
            def cleanup(self):calls.append('cleanup')
        class Remote:
            def __init__(self,root):pass
            def stage(self,*args):return 'a'*64
            def invoke(self,*args,**kw):calls.append('observercleanup');return {}
            def collect(self,*args):pass
        def fail(*args,**kw):time.sleep(.2);raise AssertionError('timer did not interrupt blocking builder')
        candidate=dict(role='restore',target='WsprryPico',fault_stage=0,gp14=False,lan_mode='plain',session_deadline_fixture=False,uf2={'path':'restore.uf2'})
        with tempfile.TemporaryDirectory() as directory,patch.object(parent,'safe_info',lambda *a:None),patch.object(parent,'tranche_deadline',lambda seconds:actual_deadline(.02)):
            result=parent.execute({'source_commit':'a'*40},directory,{'source_commit':'b'*40,'candidates':[candidate]},directory,Path(directory)/'new',Path(directory)/'inspector',Path(directory)/'native',backend_factory=Backend,remote_factory=Remote,builder=fail)
        self.assertEqual(result['error']['type'],'TimeoutError');self.assertEqual(signal.getitimer(signal.ITIMER_REAL),(0.0,0.0));self.assertEqual(result['status'],'STOPPED');self.assertIn('final-restoration.bin',calls);self.assertEqual(calls[-1],'cleanup')

    def test_original_crc_correlations_twenty_status_one_submit(self):
        result,calls=self.exercise();self.assertEqual(result['status_samples'],20);self.assertEqual(len(result['status_wire']),20);self.assertEqual(calls,['/api/owner/v1/public-status','/api/owner/v1/claim/start','/api/owner/v1/claim/submit']);self.assertFalse(result['terminal_response_observed'])
    def test_unclaimable_empty_fixture_stops_before_trace_or_mutation(self):
        with self.assertRaisesRegex(ValueError,'empty production claim authority required'):self.exercise(claimable=False)
    def test_faulted_or_fixture_info_refuses_before_submit(self):
        for kwargs in ({'unhealthy':True},{'fixture':True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.exercise(**kwargs)

    def test_corrupt_actual_status_refuses_before_save(self):
        with self.assertRaises(ValueError):self.exercise(bad_crc=True)
    def test_unexpected_trace_kind_or_nested_span_refuses(self):
        with self.assertRaises(ValueError):self.exercise(nested=True)
    def test_overlap_is_rejected_even_if_timestamps_equal(self):
        # Begin status inside the profile pair; equal target ticks do not excuse nesting.
        records=[]
        for seq,span,kind,phase in [(1,1,'status','begin'),(2,1,'status','end'),(3,3,'profile_erase','begin'),(4,4,'status','begin'),(5,4,'status','end'),(6,3,'profile_erase','end')]:records.append(dict(seq=str(seq),span=str(span),kind=kind,phase=phase,monotonic_ns='1',outcome='pending' if phase=='begin' else 'complete'))
        with self.assertRaises(ValueError):r.assess(records,1,1,0)
if __name__=='__main__':unittest.main()
