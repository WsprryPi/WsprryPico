#!/usr/bin/env python3
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import unittest
from unittest.mock import patch
import phase12_engineering_time_jobs as runner
class Evidence:
    def __init__(self):self.rows=[]
    def record(self,kind,**value):self.rows.append((kind,value))
class Fake:
    authorized=True;expected_device_id=runner.DEVICE;field_session='field';wtp_session='wtp'
    def __init__(self,evidence,clock):
        self.evidence=evidence;self.last_response=None;self.backend=object();self.clock=clock
        self.sample=None;self.network=False;self.source='none';self.state='empty';self.owner=self.job=None
        self.calls=[];self.run_count=0;self.uncertain=False;self.generation=7;self.fail_op=None
    def field_status(self):
        source='sntp' if self.network else ('controller' if self.sample is not None and self.clock[0]-self.sample<90 else 'none')
        return dict(time_source=source,time_disagreement=False)
    def wtp_status(self,boot):
        if self.state=='armed':
            self.run_count+=1
            if self.run_count>=2:self.state='running'
        elif self.state=='running':self.state='complete'
        return dict(boot_id=boot,output_active=False,state=self.state,owner_id=self.owner,job_id=self.job)
    def _field(self,op,**body):
        if op=='time_challenge':return {'nonce':body['nonce']}
        if self.network:
            self.last_response={'ok':False,'error':'busy'};raise runner.ClientError('busy')
        self.sample=self.clock[0];return {'accepted':True}
    def wtp_exchange(self,op,body):
        self.calls.append(op)
        if op=='CAPS':return {}
        if op=='GET_CLOCK':
            age=0 if self.sample is None else self.clock[0]-self.sample
            state='synchronized' if self.network or (self.sample is not None and age<90) else ('unsynchronized' if self.sample is None else 'holdover')
            return dict(state=state,sync_age_ns=str(int(age*1e9)),monotonic_now_ns=str(int(self.clock[0]*1e9)),uncertainty_ns='1000000',utc_now_ns=str(int((1000+self.clock[0])*1e9)))
        if op=='CLAIM':self.owner=body['owner_id'];return {'owner_id':self.owner}
        if op=='LOAD':self.job=body['job_id'];self.state='loaded';return {}
        if op=='ARM':
            if not self.network and self.clock[0]-self.sample>=90:
                self.last_response={'ok':False,'error':{'code':'CLOCK_UNSYNCHRONIZED'}}
                raise runner.ClientError('clock')
            if self.uncertain:raise TimeoutError('uncertain ARM')
            self.state='armed';self.run_count=0;return {}
        if op=='ABORT':
            if self.fail_op==op:raise TimeoutError('uncertain abort')
            self.state='aborted';return {}
        if op=='RELEASE':
            if self.fail_op==op:raise TimeoutError('uncertain release')
            self.state='empty';self.owner=self.job=None;return {}
class Tests(unittest.TestCase):
    def exercise(self,uncertain=False,invalid_raw=False,fail_op=None,wrong_generation=False):
        clock=[0];evidence=Evidence();client=Fake(evidence,clock);client.uncertain=uncertain;client.fail_op=fail_op;original=client.backend
        info=dict(device_id=runner.DEVICE,revision='b'*12,status=dict(boot_id='a'*32,
                  engine='inhibited-standalone-simulator',enabled=False,output_active=False,storage_healthy=True),
                  provisioning_source='provisioned',access_state='healthy',provisioning_generation='8' if wrong_generation else '7')
        raw=json.dumps(info).encode()
        def observe():return info,b'{}' if invalid_raw else raw
        def off():client.network=False
        def on():client.network=True
        with patch.object(runner,'resource_health'),patch.object(runner,'check_caps'),patch.object(runner,'check_clock',return_value=100):
            def action():return runner.run(client,observe,'b'*40,'a'*32,evidence,on,off,
                    clock=lambda:clock[0],sleeper=lambda s:clock.__setitem__(0,clock[0]+s),utc=lambda:1000000000000)
            if uncertain or invalid_raw or fail_op or wrong_generation:
                with self.assertRaises((TimeoutError,ValueError)):action()
            else:self.assertEqual(action()['simulator_jobs'],3)
        self.assertIs(client.backend,original);self.assertFalse(client.network)
        return client,evidence
    def test_three_jobs_expired_refusal_and_local_completion(self):
        client,evidence=self.exercise()
        self.assertEqual(client.calls.count('LOAD'),3);self.assertEqual(client.calls.count('ARM'),3)
        self.assertEqual([v['case'] for k,v in evidence.rows if k=='T5_case_complete'],
          ['expired_field_arm_refusal','fresh_field_local_completion','sntp_conflict_preserved_local_completion'])
        self.assertIsNone(client.owner)
    def test_uncertain_arm_never_replayed_cleanup_once(self):
        client,evidence=self.exercise(uncertain=True)
        self.assertEqual(client.calls.count('LOAD'),2);self.assertEqual(client.calls.count('ARM'),2)
        self.assertEqual(client.calls.count('ABORT'),2);self.assertIsNone(client.owner)
    def test_uncertain_abort_release_never_replayed_and_unconfirmed(self):
        for operation in ('ABORT','RELEASE'):
            with self.subTest(operation=operation):
                client,evidence=self.exercise(fail_op=operation)
                self.assertEqual(client.calls.count(operation),1)
                self.assertTrue(any(k=='cleanup_failed' for k,v in evidence.rows))
    def test_profile_generation_drift_stops_before_load(self):
        client,_=self.exercise(wrong_generation=True)
        self.assertEqual(client.calls.count('LOAD'),0)
    def test_actual_info_bytes_required_before_mutation(self):
        client,_=self.exercise(invalid_raw=True)
        self.assertEqual(client.calls.count('LOAD'),0)
if __name__=='__main__':unittest.main()
