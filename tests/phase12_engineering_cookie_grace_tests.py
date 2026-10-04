#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_cookie_grace as r


class Fixture:
    def __init__(self, uncertain=False):
        self.now=0;self.created=0;self.last=0;self.owner=None;self.job=None
        self.state='empty';self.lease=0;self.begin=0;self.duration=0;self.calls=[]
        self.uncertain=uncertain;self.evidence=[];self.refreshes=[]
    def record(self,kind,**data):self.evidence.append((kind,data))
    def prune(self):
        if self.owner and self.now>=self.lease:self.owner=None;self.job=None;self.state='empty'
        if self.state=='armed' and self.now>=self.begin:self.state='running'
        if self.state=='running' and self.now>=self.begin+self.duration:self.state='complete'
    def status(self):
        self.prune();return dict(boot_id='b'*32,owner_id=self.owner,job_id=self.job,state=self.state,
                                 output_active=False,terminal_records=[])
    def info(self):
        return dict(device_id=r.DEVICE,revision='a'*12,provisioning_source='provisioned',
            lan_wtp_mode='engineering-tls',provisioning_generation=1,access_state='healthy',softap_session_inactivity_ms='15000',
            softap_session_absolute_ms='60000',status=dict(boot_id='b'*32,engine='inhibited-standalone-simulator',
                output_active=False,enabled=False,storage_healthy=True,clock_state='synchronized',
                utc_now_ns=str(int((1000+self.now)*1e9)),uncertainty_ns='1000000'))
    def ap(self):return dict(device_id=r.DEVICE,boot_id='b'*32,source_commit='a'*40,
        interface='wlan2',destination='192.168.4.1',associated=True,local_ipv4='192.168.4.2')
    def exchange(self,method,path,body,cookie,session,deadline):
        self.prune();self.calls.append((path,body,self.now))
        if path.endswith('login'):
            self.created=self.last=self.now
            return 200,dict(ok=True),{'set-cookie':'__Host-wsprrypico='+'c'*32+'; Secure'}
        op=body['operation'] if body else 'STATUS'
        grace=self.owner is not None and self.state in ('armed','running')
        if (self.now-self.created>=60 and not(grace and op in ('STATUS','ABORT'))) or (
                self.now-self.last>=15 and not grace):
            return 401,{'error':{'code':'authentication_required'}},{}
        self.last=self.now
        if path.endswith('capabilities'):
            return 200,{'wtp':dict(engine='inhibited-standalone-simulator',modes=['tone'],profiles=['rf-events/1'],
                max_job_duration_ns='45000000000',minimum_arm_lead_ns='1000000000',maximum_arm_ahead_ns='45000000000',
                maximum_arm_uncertainty_ns='500000000',minimum_lease_ms=5000,maximum_lease_ms=60000,
                frequency_ranges=[dict(minimum_nhz='1',maximum_nhz='999999999999999999')])},{}
        if method=='GET':return 200,{'job':self.status()},{}
        result={};value=body['body']
        if op=='HELLO':result=dict(device_id=r.DEVICE,boot_id='b'*32)
        if op=='CLAIM':self.owner=value['owner_id'];self.lease=self.now+value['lease_ms']/1000;result=dict(owner_id=self.owner)
        if op=='LOAD':
            self.job=value['job_id'];self.state='loaded';self.duration=int(value['total_duration_ns'])/1e9
            if self.uncertain:raise TimeoutError('LOAD result unknown')
        if op=='ARM':self.begin=int(value['start_utc_ns'])/1e9-1000;self.state='armed'
        if op=='RENEW':self.lease=self.now+value['lease_ms']/1000
        if op=='ABORT':self.state='aborted'
        return 200,dict(ok=True,request_id=body['request_id'],result=result),{}
    def run(self):
        with patch.object(r,'resource_health'):
            return r.run(self.exchange,self.info,self.status,self.ap,
                         lambda:self.refreshes.append(self.now),self,'private','a'*40,'b'*32,
                         profile_generation=1,clock=lambda:self.now,sleeper=lambda seconds:setattr(self,'now',self.now+seconds))


class Tests(unittest.TestCase):
    def test_three_jobs_absolute_expiry_and_grace_without_replay(self):
        f=Fixture();result=f.run()
        self.assertEqual(result['simulated_jobs'],3);self.assertLess(f.now,260)
        ops=[x[1]['operation'] for x in f.calls if x[1] and 'operation' in x[1]]
        self.assertEqual(ops.count('CLAIM'),3);self.assertEqual(ops.count('LOAD'),3)
        self.assertEqual(ops.count('ARM'),2);self.assertEqual(ops.count('ABORT'),2)
        self.assertEqual(ops.count('RENEW'),3);self.assertNotIn('RELEASE',ops)
        self.assertIsNone(f.owner);self.assertEqual(f.state,'empty')
        self.assertGreaterEqual(len(f.refreshes),6)
    def test_uncertain_load_never_replayed_and_lease_cleanup_observed(self):
        f=Fixture(True)
        with self.assertRaises(TimeoutError):f.run()
        ops=[x[1]['operation'] for x in f.calls if x[1] and 'operation' in x[1]]
        self.assertEqual(ops.count('LOAD'),1);self.assertNotIn('ABORT',ops)
        self.assertIsNone(f.owner);self.assertEqual(f.state,'empty')
        self.assertFalse(any(k=='case_complete' for k,_ in f.evidence))
    def test_wrong_ap_refuses_before_login(self):
        f=Fixture();original=f.ap
        f.ap=lambda:dict(original(),associated=False)
        with self.assertRaises(ValueError):f.run()
        self.assertEqual(f.calls,[])
    def test_profile_generation_change_stops_before_login(self):
        f=Fixture();original=f.info
        f.info=lambda:dict(original(),provisioning_generation=2)
        with self.assertRaises(ValueError):f.run()
        self.assertEqual(f.calls,[])
    def test_caps_rejection_precedes_claim_and_load(self):
        f=Fixture();exchange=f.exchange
        def limited(*args):
            code,value,headers=exchange(*args)
            if args[1].endswith('capabilities'):value['wtp']['max_job_duration_ns']='1000000000'
            return code,value,headers
        f.exchange=limited
        with self.assertRaises(ValueError):f.run()
        ops=[x[1]['operation'] for x in f.calls if x[1] and 'operation' in x[1]]
        self.assertNotIn('CLAIM',ops);self.assertNotIn('LOAD',ops)


class LatencyTests(unittest.TestCase):
    def latency_scenario(self, latency=.13, refresh_latency=.21, renew_race=False):
        f=Fixture();original_info=f.info;original_ap=f.ap;original_exchange=f.exchange
        def info():f.now+=latency;return original_info()
        def ap():f.now+=latency;return original_ap()
        def refresh():f.now+=refresh_latency;f.refreshes.append(f.now)
        def sleep(seconds):
            if seconds<0:raise ValueError('negative sleep')
            f.now+=seconds
        def exchange(*args):
            if renew_race and args[0]=='GET' and args[1].endswith('status') and f.now-f.created>=49:
                f.now+=4.8
            return original_exchange(*args)
        with patch.object(r,'resource_health'):
            result=r.run(exchange,info,f.status,ap,refresh,f,'private','a'*40,'b'*32,
                         profile_generation=1,clock=lambda:f.now,sleeper=sleep)
        return f,result
    def test_observer_latency_crosses_minimum_age_without_replaying_jobs(self):
        f,result=self.latency_scenario()
        self.assertEqual(result['simulated_jobs'],3)
        ops=[body['operation'] for path,body,stamp in f.calls if body and 'operation' in body]
        for op,count in [('CLAIM',3),('LOAD',3),('ARM',2),('ABORT',2)]:
            self.assertEqual(ops.count(op),count)
        self.assertEqual(sum(kind=='case_complete' for kind,data in f.evidence),3)
        self.assertLess(f.now,260)
    def test_latency_still_rejects_total_deadline_and_renew_race(self):
        with self.assertRaisesRegex(ValueError,'total deadline'):self.latency_scenario(131,0)
        with self.assertRaisesRegex(ValueError,'renew must precede'):self.latency_scenario(renew_race=True)

class ProductionHistory(Fixture):
    def prune(self):
        if self.owner and self.now>=self.lease:
            self.owner=None
            if self.state=='loaded':self.job=None;self.state='empty'
        if self.state=='armed' and self.now>=self.begin:self.state='running'
        if self.state=='running' and self.now>=self.begin+self.duration:self.state='complete'
    def status(self):
        v=super().status()
        if v['state']=='aborted':v['terminal_records']=[dict(job_id=v['job_id'],state='aborted',output_active=False,ended_monotonic_ns='1')]
        return v

class TerminalHistoryTests(unittest.TestCase):
    def test_canonical_synthetic_terminal_passes_and_foreign_history_refused(self):
        v=dict(boot_id='b'*32,owner_id=None,state='aborted',job_id='known-job',output_active=False,
               terminal_records=[dict(job_id='known-job',state='aborted',output_active=False,ended_monotonic_ns='1')])
        r.reclaimed_status(v,v['boot_id'],v['job_id'])
        with self.assertRaises(ValueError):r.reclaimed_status(v,v['boot_id'],'foreign')
        bad=dict(v,terminal_records=[])
        with self.assertRaises(ValueError):r.reclaimed_status(bad,v['boot_id'],v['job_id'])
    def test_real_callback_all_three_with_retained_abort(self):
        f=ProductionHistory();v=f.run();self.assertEqual(v['simulated_jobs'],3)
        self.assertEqual(v['stages'],['loaded','armed','running']);self.assertLess(f.now,260)
        ops=[x[1]['operation'] for x in f.calls if x[1] and 'operation' in x[1]]
        self.assertEqual(ops.count('LOAD'),3);self.assertEqual(ops.count('ABORT'),2)
    def test_late_owner_free_sample_cannot_complete(self):
        class Slow(ProductionHistory):
            def status(self):
                v=super().status()
                if v['owner_id'] is None and self.calls:
                    self.now+=66
                return v
        f=Slow()
        with self.assertRaises(ValueError):f.run()
        self.assertEqual(sum(1 for _,b,_ in f.calls if b and b.get('operation')=='LOAD'),1)
    def test_ordered_selection_no_extra_jobs(self):
        f=ProductionHistory()
        from unittest.mock import patch
        with patch.object(r,'resource_health'):
            v=r.run(f.exchange,f.info,f.status,f.ap,lambda:None,f,'private','a'*40,'b'*32,profile_generation=1,clock=lambda:f.now,sleeper=lambda x:setattr(f,'now',f.now+x),stages=('running',))
        self.assertEqual(v['simulated_jobs'],1);self.assertEqual(v['stages'],['running'])
        self.assertEqual(sum(1 for _,b,_ in f.calls if b and b.get('operation')=='LOAD'),1)
    def test_bad_stage_selection_before_observation(self):
        def forbidden(*a):raise AssertionError('observation or mutation')
        for stages in [('running','loaded'),('running','running'),('foreign',),()]:
            with self.assertRaises(ValueError):r.run(forbidden,forbidden,forbidden,forbidden,forbidden,None,'private','a'*40,'b'*32,profile_generation=1,stages=stages)


class FailureRetentionTests(unittest.TestCase):
    def run_running(self,f):
        with patch.object(r,'resource_health'):
            return r.run(f.exchange,f.info,f.status,f.ap,lambda:None,f,
                'private','a'*40,'b'*32,profile_generation=1,clock=lambda:f.now,
                sleeper=lambda seconds:setattr(f,'now',f.now+seconds),stages=('running',))

    def operations(self,f):
        return [body['operation'] for _,body,_ in f.calls if body and 'operation' in body]

    def test_original_login_error_survives_failed_failure_record(self):
        f=ProductionHistory();primary=ValueError('original controlled login failure')
        original_exchange=f.exchange;original_record=f.record
        def exchange(*args):
            original_exchange(*args)
            raise primary
        def record(kind,**data):
            if kind=='case_failed':raise OSError('controlled private record failure')
            original_record(kind,**data)
        f.exchange=exchange;f.record=record
        with self.assertRaises(ValueError) as caught:self.run_running(f)
        self.assertIs(caught.exception,primary)
        self.assertEqual(self.operations(f),[]);self.assertEqual(len(f.calls),1)
        self.assertIsNone(f.owner)
        self.assertFalse(any(kind=='case_complete' for kind,_ in f.evidence))

    def test_original_uncertain_load_error_survives_log_failure_and_still_reclaims(self):
        f=ProductionHistory();primary=TimeoutError('original controlled LOAD uncertainty')
        original_exchange=f.exchange;original_record=f.record
        def exchange(*args):
            result=original_exchange(*args)
            if args[2] and args[2].get('operation')=='LOAD':raise primary
            return result
        def record(kind,**data):
            if kind=='case_failed':raise OSError('controlled private record failure')
            original_record(kind,**data)
        f.exchange=exchange;f.record=record
        with self.assertRaises(TimeoutError) as caught:self.run_running(f)
        self.assertIs(caught.exception,primary)
        ops=self.operations(f)
        self.assertEqual(ops.count('CLAIM'),1);self.assertEqual(ops.count('LOAD'),1)
        self.assertNotIn('ARM',ops);self.assertNotIn('ABORT',ops);self.assertNotIn('RELEASE',ops)
        self.assertIsNone(f.owner);self.assertEqual(f.state,'empty');self.assertLess(f.now,260)
        self.assertFalse(any(kind=='case_complete' for kind,_ in f.evidence))

    def test_original_body_error_survives_cleanup_and_record_failures(self):
        for failed_record in (False,True):
            with self.subTest(failed_record=failed_record):
                f=ProductionHistory();primary=TimeoutError('original controlled LOAD uncertainty')
                cleanup=RuntimeError('controlled cleanup observer failure');body_failed=[False];cleanup_calls=[]
                original_exchange=f.exchange;original_status=f.status;original_record=f.record
                def exchange(*args):
                    result=original_exchange(*args)
                    if args[2] and args[2].get('operation')=='LOAD':
                        body_failed[0]=True;raise primary
                    return result
                def status():
                    if body_failed[0]:cleanup_calls.append(f.now);raise cleanup
                    return original_status()
                def record(kind,**data):
                    if failed_record and kind in ('case_failed','case_cleanup_failed'):
                        raise OSError('controlled private record failure')
                    original_record(kind,**data)
                f.exchange=exchange;f.status=status;f.record=record
                with self.assertRaises(TimeoutError) as caught:self.run_running(f)
                self.assertIs(caught.exception,primary);self.assertEqual(len(cleanup_calls),1)
                self.assertTrue(any('lease cleanup failed: RuntimeError' in note for note in primary.__notes__))
                if failed_record:
                    self.assertIn('case failure record failed: OSError',primary.__notes__)
                    self.assertIn('cleanup failure record failed: OSError',cleanup.__notes__)
                else:self.assertEqual(sum(kind=='case_cleanup_failed' for kind,_ in f.evidence),1)
                ops=self.operations(f)
                self.assertEqual(ops.count('CLAIM'),1);self.assertEqual(ops.count('LOAD'),1)
                self.assertNotIn('ARM',ops);self.assertNotIn('ABORT',ops);self.assertNotIn('RELEASE',ops)
                self.assertIsNotNone(f.owner);self.assertEqual(f.state,'loaded')
                self.assertFalse(any(kind=='case_complete' for kind,_ in f.evidence))

    def test_cleanup_failure_after_success_is_primary_even_if_its_record_fails(self):
        for failed_record in (False,True):
            with self.subTest(failed_record=failed_record):
                f=ProductionHistory();cleanup=RuntimeError('controlled successful-body cleanup failure')
                body_complete=[False];cleanup_calls=[]
                original_status=f.status;original_record=f.record
                def status():
                    if body_complete[0]:cleanup_calls.append(f.now);raise cleanup
                    return original_status()
                def record(kind,**data):
                    if kind=='owner_grace_status_abort_pass':body_complete[0]=True
                    if failed_record and kind=='case_cleanup_failed':
                        raise OSError('controlled private cleanup record failure')
                    original_record(kind,**data)
                f.status=status;f.record=record
                with self.assertRaises(RuntimeError) as caught:self.run_running(f)
                self.assertIs(caught.exception,cleanup);self.assertEqual(len(cleanup_calls),1)
                if failed_record:self.assertIn('cleanup failure record failed: OSError',cleanup.__notes__)
                else:self.assertEqual(sum(kind=='case_cleanup_failed' for kind,_ in f.evidence),1)
                ops=self.operations(f)
                for op in ('CLAIM','LOAD','ARM','RENEW','ABORT'):self.assertEqual(ops.count(op),1)
                self.assertNotIn('RELEASE',ops);self.assertLess(f.now,260)
                self.assertFalse(any(kind=='case_complete' for kind,_ in f.evidence))

if __name__=='__main__':unittest.main()
