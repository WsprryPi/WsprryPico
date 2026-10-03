#!/usr/bin/env python3
"""Private T5 latency reproduction, sampled expiry guards and one-job budgets."""
import importlib.util,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).parents[1];sys.path.insert(0,str(root/'scripts'))
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
base=load(root/'tests/phase12_engineering_time_jobs_tests.py','jobs_test_seam')
private=load(root/'scripts/phase12_engineering_time_jobs.py','private_jobs')
original=load(root/'tests/fixtures/phase12_time_jobs_full_sampling.py','original_jobs')

class Slow(base.Fake):
    def step(self):self.clock[0]+=1.2
    def field_status(self):self.step();return super().field_status()
    def wtp_status(self,boot):self.step();return super().wtp_status(boot)
    def _field(self,op,**body):self.step();return super()._field(op,**body)
    def wtp_exchange(self,op,body):self.step();return super().wtp_exchange(op,body)

class Tests(unittest.TestCase):
    def exercise(self,module,*,regress=False,wrong_boot=False,late=False,monotonic_regress=False):
        clock=[0.0];evidence=base.Evidence();client=Slow(evidence,clock);raw_count=[0];original_backend=client.backend
        info=dict(device_id=module.DEVICE,revision='b'*12,status=dict(boot_id='a'*32,engine='inhibited-standalone-simulator',enabled=False,output_active=False,storage_healthy=True),provisioning_source='provisioned',access_state='healthy',provisioning_generation='7')
        def observe():
            clock[0]+=1.2;raw_count[0]+=1
            if wrong_boot and client.sample is not None and clock[0]-client.sample>91:info['status']['boot_id']='c'*32
            return info,json.dumps(info).encode()
        def on():client.network=True
        def off():client.network=False
        exchange=client.wtp_exchange
        def wire(op,body):
            value=exchange(op,body)
            if op=='GET_CLOCK' and client.sample is not None:
                age=clock[0]-client.sample
                if regress and age>30:value['sync_age_ns']='0'
                if monotonic_regress and age>30:value['monotonic_now_ns']='0'
                if late and age>80:clock[0]=241
            return value
        client.wtp_exchange=wire
        with patch.object(module,'resource_health'),patch.object(module,'check_caps'),patch.object(module,'check_clock',return_value=100):
            try:result=module.run(client,observe,'b'*40,'a'*32,evidence,on,off,clock=lambda:clock[0],sleeper=lambda s:clock.__setitem__(0,clock[0]+s),utc=lambda:1000000000000);error=None
            except (ValueError,TimeoutError) as failure:result=None;error=failure
        self.assertIs(client.backend,original_backend);self.assertFalse(client.network)
        return result,error,client,evidence,clock[0]

    def test_original_full_snapshot_false_stop_with_transaction_latency(self):
        result,error,client,evidence,elapsed=self.exercise(original)
        self.assertIsNone(result);self.assertIsNotNone(error);self.assertIn('expired field boundary',str(error));self.assertEqual(client.calls.count('LOAD'),0)

    def test_lean_clock_with_full_guard_bookends_exact_three_jobs(self):
        result,error,client,evidence,elapsed=self.exercise(private)
        self.assertIsNone(error);self.assertEqual(result['simulator_jobs'],3);self.assertLessEqual(elapsed,240)
        self.assertEqual(client.calls.count('LOAD'),3);self.assertEqual(client.calls.count('ARM'),3);self.assertIsNone(client.owner)
        boundaries=[row for kind,row in evidence.rows if kind=='expiry_age_boundary'];self.assertEqual(len(boundaries),1)
        self.assertTrue(91e9<=int(boundaries[0]['clock']['sync_age_ns'])<=94e9);self.assertEqual(boundaries[0]['field']['time_source'],'none')
        self.assertEqual(sum(kind=='field_submission' for kind,_ in evidence.rows),3)

    def test_regression_wrong_boot_and_late_clock_stop_before_jobs(self):
        for kwargs in (dict(regress=True),dict(wrong_boot=True),dict(late=True),dict(monotonic_regress=True)):
            with self.subTest(kwargs=kwargs):
                result,error,client,evidence,elapsed=self.exercise(private,**kwargs)
                self.assertIsNone(result);self.assertIsNotNone(error);self.assertEqual(client.calls.count('LOAD'),0)

if __name__=='__main__':unittest.main()
