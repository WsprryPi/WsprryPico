"""No hardware: reject unreviewed native scheduling, identity and frequency changes."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase11_5_r3_v2_native_plan import render_ini,validate_ini,validate_binding,validate_template
ROOT=Path(__file__).resolve().parents[1]
class NativePlanTests(unittest.TestCase):
    def test_process_exit_preserves_intentional_failure_history(self):
        from phase11_5_r3_v2_native_producer import validate_exit
        validate_exit(0,False,False);validate_exit(1,True,True)
        for args in [(1,False,False),(0,True,True),(1,True,False),(-15,True,True),
            (2,True,True),(0,False,True)]:
            with self.subTest(args=args),self.assertRaises(ValueError):validate_exit(*args)
    def test_native_templates_and_frequency_semantics(self):
        folder=ROOT/'build/phase11-5-r3-v2-native-preparation/final-templates'
        if not folder.exists():self.skipTest('Identified native compiler exports required')
        for mode in ['qrss','fskcw','dfcw']:
            job=json.loads((folder/(mode+'-load-template.json')).read_text())['body'];validate_template(job,mode)
            for field,value in [('total_duration_ns','1'),('mode','tone'),('allow_frequency_adjustment',False)]:
                changed=copy.deepcopy(job);changed[field]=value
                with self.subTest(mode=mode,field=field),self.assertRaises(ValueError):validate_template(changed,mode)
            changed=copy.deepcopy(job);changed['events'][0]['frequency_nhz']='14097000000000000'
            with self.assertRaises(ValueError):validate_template(changed,mode)
    def test_exact_ini_and_hour_rollover(self):
        f=ROOT/'build/phase11-5-r3-v2-pressure-t4/stage/production.ini'
        if not f.exists():self.skipTest('Reviewed inactive INI required')
        base=f.read_text();root=Path('/task/private');start=1800000000000000000
        for mode in ['qrss','fskcw','dfcw']:
            actual=render_ini(base,mode,start,root);validate_ini(actual,base,mode,start,root)
            for old,new in [('Use Amp = false','Use Amp = true'),('Repeat Minutes = 60','Repeat Minutes = 1'),('Base Frequency = 135','Base Frequency = 145'),('Start Second =','Start Second = 0')]:
                self.assertIn(old,actual)
                with self.assertRaises(ValueError):validate_ini(actual.replace(old,new),base,mode,start,root)
    def test_binding_requires_dispatch_reserve_and_exact_peer(self):
        b=dict(phase='waiting',identity=dict(device_id='device',boot_id='boot'),network=dict(resolved_address='10.77.15.10',authenticated_identity='wsprrypico-0a60df.local'),start_utc_ns='1800000000000000000',dispatch_utc_ns='1799999990000000000',session_id='a'*32,owner_id='b'*32,job_id='c'*16+'0000000000000001')
        p=dict(device_id='device',boot_id='boot');validate_binding(b,p,1800000000000000000,1799999950000000000)
        for field,value in [('phase','armed'),('start_utc_ns','1'),('dispatch_utc_ns','1799999980000000000'),('job_id','c'*32)]:
            changed=copy.deepcopy(b);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_binding(changed,p,1800000000000000000,1799999950000000000)
class NativeInitialAuthorityTests(unittest.TestCase):
    def test_exact_production_config_export(self):
        import json
        from phase11_5_r3_v2_native_plan import configuration_template,validate_template
        root=Path(__file__).resolve().parents[1]/'build/phase11-5-r3-v2-native-preparation/final-templates'
        if not root.exists():self.skipTest('Identified native compiler exports required')
        for mode in ['qrss','fskcw','dfcw']:
            original=json.loads((root/(mode+'-load-template.json')).read_text())['body']
            actual=configuration_template(original)
            self.assertEqual(int(actual['total_duration_ns']),155749999969 if mode=='dfcw' else 143250000000)
            if mode=='dfcw':
                with self.assertRaises(ValueError):validate_template(original,mode,'production-config-builder-v1')
            changed=copy.deepcopy(actual);changed['events'][0]['frequency_nhz']='135499000000000'
            with self.assertRaises(ValueError):validate_template(changed,mode,'production-config-builder-v1')
    def test_exact_inactive_terminal_and_preserved_history(self):
        from phase11_5_r3_v2_native_plan import validate_initial
        packet=dict(boot_id='a'*32,native=dict(initial_authority=dict(state='aborted',job_id='b'*32)))
        status=dict(boot_id='a'*32,state='aborted',job_id='b'*32,owner_id=None,output_active=False,
            terminal_records=[dict(job_id='b'*32,state='aborted',output_active=False)])
        validate_initial(status,packet)
        for key,value in [('boot_id','c'*32),('job_id','c'*32),('owner_id','c'*32),('output_active',True),
            ('state','running'),('terminal_records',[])]:
            changed=copy.deepcopy(status);changed[key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):validate_initial(changed,packet)

class NativeQueuedSuccessorTests(unittest.TestCase):
    def test_future_plan_is_not_a_second_submission(self):
        from phase11_5_r3_v2_native_plan import validate_host_scope
        b=dict(job_id='a'*16+'0000000000000001',session_id='b'*32,start_utc_ns='1800000000000000000')
        p=dict(device_id='c'*32,boot_id='d'*32,runtime_seconds=600)
        h=dict(identity=dict(device_id=p['device_id'],boot_id=p['boot_id']),session_id=b['session_id'],
            job_id=b['job_id'],phase='idle',job=dict(job_id=b['job_id'],state='complete',authoritative=True,
                output_active=False,device_output_active=False,boot_id=p['boot_id']))
        self.assertTrue(validate_host_scope(h,b,p,False))
        next=dict(h,phase='waiting',job=None,job_id='a'*16+'0000000000000002',
            start_utc_ns='1800003600000000000',dispatch_utc_ns='1800003590000000000')
        self.assertTrue(validate_host_scope(next,b,p,True))
        with self.assertRaises(ValueError):validate_host_scope(next,b,p,False)
        durable=dict(next,last_report=dict(job_id=b['job_id'],outcome='complete',job=h['job'],
            execution=dict(ok=True,faulted=False,stopped=False)))
        self.assertTrue(validate_host_scope(durable,b,p,False))
        bad=copy.deepcopy(durable);bad['last_report']['job']['authoritative']=False
        with self.assertRaises(ValueError):validate_host_scope(bad,b,p,False)
        for key,value in [('phase','executing'),('job_id','a'*16+'0000000000000003'),
            ('session_id','e'*32),('dispatch_utc_ns','1800000100000000000'),('start_utc_ns','1800000100000000000')]:
            changed=copy.deepcopy(next);changed[key]=value
            with self.subTest(field=key),self.assertRaises(ValueError):validate_host_scope(changed,b,p,True)

if __name__=='__main__':unittest.main()
