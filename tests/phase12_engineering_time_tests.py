#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_time as runner
from wsprrypico_ble import ClientError


class Evidence:
    def __init__(self): self.rows=[]
    def record(self, kind, **data): self.rows.append(dict(kind=kind, **data))


class Fixture:
    authorized=True
    expected_device_id=runner.DEVICE
    field_session='a'*32
    wtp_session='b'*32
    def __init__(self):
        self.now=0; self.base=0; self.source='none'; self.disagreement=False
        self.recovery=False; self.last_response=None; self.calls=[]; self.off=0
    def field_status(self):
        source=self.source
        if source=='controller' and self.now-self.base>90: source='none'
        return dict(time_source=source,time_disagreement=self.disagreement)
    def wtp_status(self, boot):
        return dict(boot_id=boot,state='empty',owner_id=None,job_id=None,output_active=False)
    def wtp_exchange(self, op, body):
        return dict(state='unsynchronized' if self.now-self.base>180 else 'synchronized',
                    utc_now_ns=str(int(1e12+self.now*1e9)),monotonic_now_ns=str(int(self.now*1e9)),
                    uncertainty_ns='1000000',sync_age_ns=str(int((self.now-self.base)*1e9)))
    def _field(self, op, **data):
        self.calls.append((op,data))
        if op=='time_challenge': return dict(nonce=data['nonce'])
        offset=int(data['utc_ns'])-int(1e12+self.now*1e9)
        error=None
        if self.source=='sntp': error='busy'
        elif offset:
            self.source='disagreement';self.disagreement=True;error='conflict'
        elif self.disagreement and not self.recovery:
            self.recovery=True;error='conflict'
        else:
            self.source='controller';self.disagreement=False;self.base=self.now
        self.last_response=dict(ok=False,error=error) if error else dict(ok=True,accepted=True)
        if error: raise ClientError(error)
        return self.last_response
    def sleep(self, seconds): self.now+=seconds
    def sntp_on(self): self.source='sntp';self.base=self.now
    def sntp_off(self): self.off+=1


class Tests(unittest.TestCase):
    def exercise(self, fixture=None, observer=None):
        f=fixture or Fixture();e=Evidence()
        info=dict(status=dict(boot_id='c'*32),phase12_fault_stage=0)
        for key in ('allocator_failures','tls_allocation_failures','core0_stack_fault_status',
                    'fault_stage','fault_hash','fault_pc','fault_status','flash_read_failures',
                    'flash_erase_failures','flash_program_failures'): info[key]='0'
        observe=observer or (lambda:(info,json.dumps(info).encode()+b'\n'))
        with patch.object(runner,'safe_info'):
            result=runner.run(f,observe,'d'*40,'c'*32,e,f.sntp_on,f.sntp_off,
                              clock=lambda:f.now,sleeper=f.sleep,
                              utc=lambda:int(1e12+f.now*1e9))
        return f,e,result
    def test_bounded_four_cases_and_no_job_mutations(self):
        f,e,result=self.exercise()
        self.assertEqual(result['cases'],['T1','T2','T3','T4'])
        self.assertFalse(result['t3_arm_refusal_tested'])
        self.assertEqual(len([x for x in f.calls if x[0]=='time_submit']),5)
        self.assertEqual([x['age_s'] for x in e.rows if x['kind']=='age_boundary'],[89,91,181])
        self.assertEqual(f.off,2)
        self.assertLess(f.now,300)
    def test_timeout_is_not_expected_rejection_and_not_retried(self):
        f=Fixture();original=f._field
        def fail(op,**data):
            if op=='time_submit': raise ClientError('timeout')
            return original(op,**data)
        f._field=fail
        with self.assertRaises(Exception): self.exercise(f)
        self.assertEqual(f.off,2)
        self.assertEqual(len(f.calls),1)
    def test_realistic_transaction_latency_preserves_original_age_windows(self):
        class Slow(Fixture):
            def field_status(self):self.now+=1.2;return super().field_status()
            def wtp_status(self,boot):self.now+=1.2;return super().wtp_status(boot)
            def wtp_exchange(self,op,body):self.now+=1.2;return super().wtp_exchange(op,body)
        f,e,result=self.exercise(Slow())
        rows=[x for x in e.rows if x['kind']=='age_boundary']
        self.assertEqual([x['age_s'] for x in rows],[89,91,181])
        for row in rows:
            self.assertLessEqual(row['age_s']*1_000_000_000,int(row['clock']['sync_age_ns']))
            self.assertLessEqual(int(row['clock']['sync_age_ns']),(row['age_s']+3)*1_000_000_000)
        self.assertEqual(result['cases'],['T1','T2','T3','T4'])
        self.assertEqual(len([x for x in f.calls if x[0]=='time_submit']),5)
        self.assertLess(f.now,300)
    def test_aging_clock_regression_or_late_response_stops_without_submission(self):
        for late in (False,True):
            with self.subTest(late=late):
                f=Fixture();original=f.wtp_exchange;calls=0
                def bad_clock(op,body):
                    nonlocal calls
                    calls+=1
                    if calls==10 and late:f.now=301
                    value=original(op,body)
                    if calls==10 and not late:value['monotonic_now_ns']='0'
                    return value
                f.wtp_exchange=bad_clock
                with self.assertRaisesRegex(ValueError,'clock response deadline' if late else 'monotonic regression'):self.exercise(f)
                self.assertEqual(len([x for x in f.calls if x[0]=='time_submit']),4)
                self.assertEqual(f.off,2)
    def test_multisecond_transport_retains_nonoverlap_proof(self):
        f=Fixture();original=f.wtp_exchange;calls=0
        def delayed(op,body):
            nonlocal calls
            calls+=1
            if calls in (4,5):f.now+=4
            return original(op,body)
        f.wtp_exchange=delayed
        _,e,result=self.exercise(f)
        bound=next(x for x in e.rows if x['kind']=='nonoverlap_bound')
        self.assertEqual(int(bound['bracket_ns']),4_000_000_000)
        self.assertGreater(int(bound['difference_ns']),int(bound['uncertainty_and_bracket_ns']))
        conflict=next(x for x in e.rows if x['kind']=='time_stimulus' and x['expected']=='conflict')
        self.assertEqual(conflict['offset_ns'],60_000_000_000)
        self.assertEqual(result['cases'],['T1','T2','T3','T4'])
        self.assertLess(f.now,300)
    def test_final_bookend_clock_regression_or_late_result_stops(self):
        for late in (False,True):
            with self.subTest(late=late):
                f=Fixture();original=f.wtp_exchange;expired_seen=False
                def bad_bookend(op,body):
                    nonlocal expired_seen
                    bad=expired_seen and f.source!='sntp'
                    if bad and late:f.now=301
                    value=original(op,body)
                    if bad and not late:value['monotonic_now_ns']='0'
                    if f.now-f.base>=181:expired_seen=True
                    return value
                f.wtp_exchange=bad_bookend
                with self.assertRaisesRegex(ValueError,'T3 final guard'):self.exercise(f)
                self.assertEqual(len([x for x in f.calls if x[0]=='time_submit']),4)
                self.assertEqual(f.off,2)
    def test_excessive_bracket_stops_without_replaying_conflict(self):
        f=Fixture();original=f.wtp_exchange;calls=0;e=Evidence()
        def delayed(op,body):
            nonlocal calls
            calls+=1
            if calls==5:f.now+=35
            return original(op,body)
        f.wtp_exchange=delayed
        with patch.object(sys.modules[__name__],'Evidence',return_value=e):
            with self.assertRaisesRegex(ValueError,'T1 nonoverlap not proven'):self.exercise(f)
        self.assertEqual(len([x for x in f.calls if x[0]=='time_submit']),2)
        bound=next(x for x in e.rows if x['kind']=='nonoverlap_bound')
        self.assertLessEqual(int(bound['difference_ns']),int(bound['uncertainty_and_bracket_ns']))
        self.assertFalse(any(x.get('case')=='T1' for x in e.rows))
        self.assertEqual(f.off,2)
    def test_boot_change_stops_before_mutation(self):
        f=Fixture()
        with self.assertRaises(Exception):
            self.exercise(f,lambda:({'status':{'boot_id':'wrong'}},b'actual\n'))
        self.assertEqual(f.calls,[])
        self.assertEqual(f.off,2)
    def test_sntp_interference_invalidates_aging(self):
        f=Fixture();sleep=f.sleep
        def interfere(seconds):
            sleep(seconds)
            if f.now>10: f.source='sntp'
        f.sleep=interfere
        with self.assertRaises(Exception): self.exercise(f)
        self.assertEqual(f.off,2)
    def test_raw_tap_preserves_error_before_mapping(self):
        e=Evidence();client=runner.EvidenceClient(object(),evidence=e)
        response={'ok':False,'error':'conflict'}
        with patch.object(runner.Client,'_wait',return_value=response):
            self.assertIs(client._wait({},'a'*32,'timeout'),response)
        self.assertIs(client.last_response,response)
        self.assertEqual(e.rows[0]['response'],response)
    def test_fabricated_decoding_rejected(self):
        with self.assertRaises(Exception):
            self.exercise(observer=lambda:({'status':{'boot_id':'c'*32}},b'{}\n'))
    def test_owned_status_stops_before_time_mutation(self):
        f=Fixture()
        f.wtp_status=lambda boot:dict(boot_id=boot,state='empty',owner_id='a'*32,
                                      job_id=None,output_active=False)
        with self.assertRaises(Exception): self.exercise(f)
        self.assertEqual(f.calls,[])
        self.assertEqual(f.off,2)


if __name__=='__main__': unittest.main()
