#!/usr/bin/env python3
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_consumer_busy_claim as r
from validate_wtp_contract import frame

class Tests(unittest.TestCase):
    def run_case(self,target='loaded',lost=None,accept=False,withdraw_fail=False):
        state=['empty'];owner=[None];job=[None];ops=[];http_calls=[];ticks=[0]
        def exchange(op,body,end):
            ops.append(op)
            if op=='CLAIM':owner[0]=body['owner_id']
            if op=='LOAD':
                self.assertEqual(int(body['total_duration_ns']),r.BUSY_DURATION_NS);self.assertEqual(int(body['events'][0]['duration_ns']),r.BUSY_DURATION_NS);job[0]=body['job_id'];state[0]='loaded'
            if op=='ARM':state[0]='armed'
            if op=='STATUS' and target=='running' and state[0]=='armed' and ops.count('STATUS')>3:state[0]='running'
            if op=='ABORT':state[0]='aborted'
            if op=='RELEASE':state[0]='empty';owner[0]=job[0]=None
            if op==lost:raise TimeoutError('delivered but response lost')
            value=dict(boot_id='a'*32,state=state[0],owner_id=owner[0],job_id=job[0],output_active=False)
            if op=='CAPS':value=dict(max_job_duration_ns='60000000000')
            if op=='GET_CLOCK':value=dict(state='synchronized',leap='normal',uncertainty_ns='100',utc_now_ns='100000000000')
            a=dict(protocol='WTP/1',type='request',op=op,request_id=f'{len(ops):032x}',session_id='b'*32,body=body);b=dict(a,type='response',ok=True,body=value)
            return frame(json.dumps(a).encode()),frame(json.dumps(b).encode())
        def observe(end):return dict(provisioning_generation='5',status=dict(boot_id='a'*32,output_active=False,state=state[0])),b'raw'
        def http(method,path,body,end):
            http_calls.append((method,path))
            if method=='POST':
                if accept:return 200,dict(slot_state='granted'),b'req',b'resp'
                raise ConnectionResetError('AP carrier withdrawn')
            return 200,dict(device_id=r.DEVICE,boot_id='a'*32,profile_source=5,generation='5',claim_available=True,slot_state='none'),b'req',b'resp'
        def withdraw(end):
            if withdraw_fail:raise ValueError('carrier remains present')
            return dict(scan_hex='00',link='Not connected.')
        plan=dict(boot_id='a'*32,generation=5,busy_state=target)
        with patch.object(r,'keys',return_value=({},None)):
            try:result=r.exercise(plan,observe,http,exchange,withdraw,lambda d:None,clock=lambda:0,sleeper=lambda d:None)
            except BaseException as error:return error,ops,http_calls
        return result,ops,http_calls
    def test_running_duration_covers_declared_observation_window(self):
        self.assertLessEqual(r.BUSY_DURATION_NS,60_000_000_000)
        # Withdrawal, START timeout, both WTP readbacks (5s each), and USB INFO.
        self.assertGreater(r.BUSY_DURATION_NS/1e9,r.WITHDRAW_SECONDS+r.START_SECONDS+10+5)
    def test_real_carrier_command_uses_remaining_deadline_and_bounds_output(self):
        import phase12_consumer_flash_status_dispatch as dispatcher
        from types import SimpleNamespace
        class Evidence:
            def record(self,*args,**kw):pass
        observed=[]
        def runner(argv,**kw):observed.append(kw['timeout']);return SimpleNamespace(returncode=0,stdout=b'Not connected.',stderr=b'')
        self.assertEqual(dispatcher.bounded_command(['iw','link'],10,Evidence(),clock=lambda:9.8,runner=runner),b'Not connected.')
        self.assertAlmostEqual(observed[0],.2)
        def excessive(argv,**kw):return SimpleNamespace(returncode=0,stdout=b'x'*32769,stderr=b'')
        with self.assertRaisesRegex(ValueError,'output bound'):dispatcher.bounded_command(['iw','scan'],10,Evidence(),clock=lambda:9,runner=excessive)

    def test_three_supported_states_one_job_no_submit(self):
        for state in ('loaded','armed','running'):
            result,ops,calls=self.run_case(state)
            self.assertIsInstance(result,dict);self.assertEqual(result['state'],state);self.assertEqual(ops.count('CLAIM'),1);self.assertEqual(ops.count('LOAD'),1);self.assertEqual(ops.count('ABORT'),1);self.assertEqual(ops.count('RELEASE'),1);self.assertEqual(sum(method=='POST' for method,path in calls),1);self.assertFalse(any(path.endswith('submit') for method,path in calls))
    def test_uncertain_abort_and_release_reconciled_without_replay(self):
        for op in ('ABORT','RELEASE'):
            result,ops,_=self.run_case(lost=op);self.assertIsInstance(result,dict);self.assertEqual(ops.count(op),1)
    def test_start_admission_fails_and_cleans_once(self):
        result,ops,_=self.run_case(accept=True);self.assertIsInstance(result,ValueError);self.assertEqual(ops.count('ABORT'),1);self.assertEqual(ops.count('RELEASE'),1)
    def test_timeout_without_actual_carrier_withdrawal_never_posts(self):
        result,ops,calls=self.run_case(withdraw_fail=True);self.assertIsInstance(result,ValueError);self.assertFalse(any(method=='POST' for method,path in calls));self.assertEqual(ops.count('ABORT'),1);self.assertEqual(ops.count('RELEASE'),1)
if __name__=='__main__':unittest.main()
