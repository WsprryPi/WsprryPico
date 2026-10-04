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
        self.calls=[];self.requests=[];self.run_count=0;self.uncertain=False;self.generation=7;self.fail_op=None
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
        self.calls.append(op);self.requests.append((op,body))
        if op=='CAPS':return {}
        if op=='GET_CLOCK':
            age=0 if self.sample is None else self.clock[0]-self.sample
            state='synchronized' if self.network or (self.sample is not None and age<90) else ('unsynchronized' if self.sample is None else 'holdover')
            return dict(state=state,leap='normal',sync_age_ns=str(int(age*1e9)),monotonic_now_ns=str(int(self.clock[0]*1e9)),uncertainty_ns='1000000',utc_now_ns=str(int((1000+self.clock[0])*1e9)))
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
    def exercise_sntp(self,delays=None,ready_after=0,expect_success=False,selection='all',uncertain=False,completion_elapsed=None):
        clock=[0.0];evidence=Evidence();trace=[];sleeps=[];delays=delays or {}
        class Delayed(Fake):
            def __init__(self):
                super().__init__(evidence,clock);self.timeout=5;self.waiting=False;self.started=None;self.follow_on=[]
                self.armed_at=None;self.completion_observations=[]
            def observation(self,name):
                if self.waiting:
                    trace.append((name,clock[0]-self.started,self.timeout))
                    clock[0]+=delays.get(name,0)
            def field_status(self):
                self.observation('field_status');value=super().field_status()
                if self.waiting and clock[0]-self.started<ready_after:value['time_source']='none'
                return value
            def wtp_exchange(self,operation,body):
                if operation=='GET_CLOCK':self.observation(operation)
                value=super().wtp_exchange(operation,body)
                if operation=='ARM' and self.network:self.armed_at=clock[0]
                return value
            def wtp_status(self,boot):
                if self.network and self.state=='running' and completion_elapsed is not None:
                    self.completion_observations.append((clock[0]-self.armed_at,self.timeout))
                    clock[0]=self.armed_at+completion_elapsed
                value=super().wtp_status(boot)
                if self.network and value['state']=='running' and completion_elapsed is not None:
                    clock[0]=self.armed_at+24.75
                return value
            def _field(self,operation,**body):
                if self.network:self.follow_on.append(operation);self.waiting=False
                return super()._field(operation,**body)
        client=Delayed();client.uncertain=uncertain;original=client.backend;result=None
        info=dict(device_id=runner.DEVICE,revision='b'*12,status=dict(boot_id='a'*32,
            engine='inhibited-standalone-simulator',enabled=False,output_active=False,storage_healthy=True),
            provisioning_source='provisioned',access_state='healthy',provisioning_generation='7')
        raw=json.dumps(info).encode()
        def observe():client.observation('INFO');return info,raw
        def on():client.network=True;client.waiting=True;client.started=clock[0]
        def off():client.network=False;client.waiting=False
        def sleep(seconds):
            if client.waiting:sleeps.append(seconds)
            clock[0]+=seconds
        with patch.object(runner,'resource_health'),patch.object(runner,'check_caps'):
            def action():return runner.run(client,observe,'b'*40,'a'*32,evidence,on,off,
                clock=lambda:clock[0],sleeper=sleep,utc=lambda:1000000000000,selection=selection)
            if uncertain:
                with self.assertRaisesRegex(TimeoutError,'uncertain ARM'):action()
            elif completion_elapsed is not None and not expect_success:
                with self.assertRaisesRegex(ValueError,'bounded local completion after observation'):action()
            elif expect_success:
                result=action();self.assertEqual(result['simulator_jobs'],3 if selection=='all' else 1)
            else:
                with self.assertRaisesRegex(ValueError,'SNTP prerequisite unavailable'):action()
                # The first two permitted jobs have finished and released before
                # this prerequisite. Late data must admit no dependent mutation.
                accepted=2 if selection=='all' else 0
                self.assertEqual(client.calls.count('CLAIM'),accepted)
                self.assertEqual(client.calls.count('LOAD'),accepted);self.assertEqual(client.calls.count('ARM'),accepted)
                self.assertEqual(client.follow_on,[])
                self.assertEqual([value['case'] for kind,value in evidence.rows if kind=='T5_case_complete'],
                    ['expired_field_arm_refusal','fresh_field_local_completion'] if selection=='all' else [])
                if selection=='all':self.assertTrue(any(kind=='cleanup_confirmed' for kind,value in evidence.rows))
        self.assertIs(client.backend,original);self.assertEqual(client.timeout,5);self.assertFalse(client.network)
        self.assertIsNone(client.owner)
        client.result=result;client.evidence_rows=evidence.rows
        return client,trace,sleeps

    def test_sntp_early_success_keeps_three_jobs_and_remaining_request_timeout(self):
        for elapsed in (0,59.5):
            with self.subTest(elapsed=elapsed):
                client,trace,_=self.exercise_sntp({'INFO':elapsed},expect_success=True)
                self.assertEqual(client.result,dict(status='T5_REVIEW_REQUIRED',simulator_jobs=3,rf_jobs=0,physical_acceptance=False))
                self.assertEqual(client.calls.count('LOAD'),3);self.assertEqual(client.calls.count('ARM'),3)
                self.assertEqual(client.follow_on,['time_challenge','time_submit'])
                self.assertEqual([name for name,_,_ in trace],['INFO','GET_CLOCK','field_status'])
                for name,started,timeout in trace:
                    if name!='INFO':self.assertEqual(timeout,min(5,60-started))

    def test_sntp_exact_and_late_success_are_not_accepted(self):
        for elapsed in (60,62.738174938):
            with self.subTest(elapsed=elapsed):
                _,trace,_=self.exercise_sntp({'field_status':elapsed})
                self.assertEqual([name for name,_,_ in trace],['INFO','GET_CLOCK','field_status'])

    def test_sntp_slow_info_stops_before_clock_or_field_query(self):
        for elapsed in (60,62.58):
            with self.subTest(elapsed=elapsed):
                _,trace,_=self.exercise_sntp({'INFO':elapsed})
                self.assertEqual([name for name,_,_ in trace],['INFO'])

    def test_sntp_slow_clock_stops_before_field_query_and_restores_timeout(self):
        for elapsed in (.5,3.15):
            with self.subTest(elapsed=elapsed):
                _,trace,_=self.exercise_sntp({'INFO':59.5,'GET_CLOCK':elapsed})
                self.assertEqual([name for name,_,_ in trace],['INFO','GET_CLOCK'])
                self.assertEqual(trace[-1][2],.5)

    def test_sntp_cumulative_observation_time_has_one_absolute_end(self):
        _,trace,_=self.exercise_sntp({'INFO':20,'GET_CLOCK':20,'field_status':20})
        self.assertEqual([started for _,started,_ in trace],[0,20,40])

    def test_sntp_sleep_uses_remaining_time_and_does_not_start_boundary_observation(self):
        _,trace,sleeps=self.exercise_sntp({'INFO':59.5},ready_after=60)
        self.assertEqual(sleeps,[.5])
        self.assertEqual([name for name,_,_ in trace],['INFO','GET_CLOCK','field_status'])

    def test_selector_refuses_unknown_or_untyped_values_before_client_access(self):
        for selection in (None,True,1,'','standard','SNTP','sntp-only',[],{'selection':'sntp'}):
            with self.subTest(selection=selection),self.assertRaisesRegex(ValueError,'explicit T5 case selection'):
                runner.run(object(),None,None,None,None,None,None,selection=selection)

    def test_explicit_sntp_only_has_one_actual_six_second_job_and_ten_second_lead(self):
        for elapsed in (0,59.5):
            with self.subTest(elapsed=elapsed):
                client,_,_=self.exercise_sntp({'INFO':elapsed},expect_success=True,selection='sntp')
                self.assertEqual(client.result,dict(status='T5_SNTP_REVIEW_REQUIRED',selection='sntp',max_seconds=120,
                    simulator_jobs=1,rf_jobs=0,physical_acceptance=False))
                self.assertEqual(client.calls.count('CLAIM'),1);self.assertEqual(client.calls.count('LOAD'),1)
                self.assertEqual(client.calls.count('ARM'),1);self.assertEqual(client.calls.count('RELEASE'),1)
                self.assertEqual(client.follow_on,['time_challenge','time_submit'])
                job=next(body for op,body in client.requests if op=='LOAD')
                self.assertEqual(job['mode'],'tone');self.assertEqual(job['total_duration_ns'],'6000000000')
                self.assertEqual(job['events'][0]['duration_ns'],'6000000000')
                arm=next(body for op,body in client.requests if op=='ARM')
                clocks=[value['value'] for kind,value in client.evidence_rows if kind=='clock']
                self.assertEqual(int(arm['start_utc_ns'])-int(clocks[-1]['utc_now_ns']),10000000000)
                fields=[value for kind,value in client.evidence_rows if kind=='field_submission']
                self.assertEqual([(value['offset_ns'],value['expected']) for value in fields],[(5000000000,'busy')])
                self.assertEqual([value['case'] for kind,value in client.evidence_rows if kind=='T5_case_complete'],
                    ['sntp_conflict_preserved_local_completion'])

    def test_explicit_sntp_exact_or_late_prerequisite_has_zero_jobs_and_field_mutations(self):
        for operation in ('INFO','GET_CLOCK','field_status'):
            for elapsed in (60,62.738174938):
                with self.subTest(operation=operation,elapsed=elapsed):
                    self.exercise_sntp({operation:elapsed},selection='sntp')

    def test_explicit_sntp_total_body_overrun_stops_before_job_admission(self):
        clock=[0.0];evidence=Evidence();client=Fake(evidence,clock);client.timeout=5;original=client.backend
        info=dict(device_id=runner.DEVICE,revision='b'*12,status=dict(boot_id='a'*32,
            engine='inhibited-standalone-simulator',enabled=False,output_active=False,storage_healthy=True),
            provisioning_source='provisioned',access_state='healthy',provisioning_generation='7')
        field=client._field
        def slow_challenge(operation,**body):
            if client.network and operation=='time_challenge':clock[0]=120.1
            return field(operation,**body)
        client._field=slow_challenge
        with patch.object(runner,'resource_health'),patch.object(runner,'check_caps'):
            with self.assertRaisesRegex(ValueError,'T5 deadline after request'):
                runner.run(client,lambda:(info,json.dumps(info).encode()),'b'*40,'a'*32,evidence,
                    lambda:setattr(client,'network',True),lambda:setattr(client,'network',False),
                    clock=lambda:clock[0],sleeper=lambda seconds:clock.__setitem__(0,clock[0]+seconds),selection='sntp')
        for operation in ('CLAIM','LOAD','ARM'):self.assertEqual(client.calls.count(operation),0)
        self.assertFalse(any(kind=='field_submission' for kind,value in evidence.rows))
        self.assertIs(client.backend,original);self.assertEqual(client.timeout,5);self.assertFalse(client.network)

    def test_explicit_sntp_uncertain_arm_is_not_replayed_and_owned_cleanup_is_once(self):
        client,_,_=self.exercise_sntp(selection='sntp',uncertain=True)
        self.assertEqual(client.calls.count('CLAIM'),1);self.assertEqual(client.calls.count('LOAD'),1)
        self.assertEqual(client.calls.count('ARM'),1);self.assertEqual(client.calls.count('ABORT'),1)
        self.assertEqual(client.calls.count('RELEASE'),1)
        self.assertFalse(any(kind=='T5_case_complete' for kind,value in client.evidence_rows))

    def test_completion_early_response_is_accepted_with_remaining_timeout(self):
        client,_,_=self.exercise_sntp(selection='sntp',completion_elapsed=24.999,expect_success=True)
        self.assertEqual(client.calls.count('ARM'),1)
        self.assertEqual(len(client.completion_observations),1)
        self.assertAlmostEqual(client.completion_observations[0][0],24.85)
        self.assertAlmostEqual(client.completion_observations[0][1],.15)
        self.assertEqual([value['case'] for kind,value in client.evidence_rows if kind=='T5_case_complete'],
            ['sntp_conflict_preserved_local_completion'])

    def test_completion_exact_and_late_response_cannot_count_or_replay_arm(self):
        for selection in ('all','sntp'):
            for elapsed in (25,25.5):
                with self.subTest(selection=selection,elapsed=elapsed):
                    client,_,_=self.exercise_sntp(selection=selection,completion_elapsed=elapsed)
                    self.assertEqual(client.calls.count('ARM'),3 if selection=='all' else 1)
                    self.assertEqual(client.calls.count('RELEASE'),3 if selection=='all' else 1)
                    self.assertEqual([value['case'] for kind,value in client.evidence_rows if kind=='T5_case_complete'],
                        ['expired_field_arm_refusal','fresh_field_local_completion'] if selection=='all' else [])
                    self.assertTrue(any(kind=='cleanup_confirmed' for kind,value in client.evidence_rows))

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
