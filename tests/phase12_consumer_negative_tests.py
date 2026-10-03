#!/usr/bin/env python3
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import unittest
from unittest.mock import patch
import phase12_consumer_negative as runner
class Evidence:
    def __init__(self):self.rows=[]
    def record(self,kind,**value):self.rows.append((kind,value))
class Tests(unittest.TestCase):
    def exercise(self,case,uncertain=False,boundaries=False,reboot=False,wtp_enabled=True):
        clock=[0];slot=['none'];granted=[0];calls=[];evidence=Evidence()
        public=dict(device_id=runner.DEVICE,boot_id='a'*32,profile_source=5,generation='1',
                    station={'callsign':'N0CALL'},owner_exists=False,claim_available=True)
        def expire():
            if slot[0]!='none' and clock[0]-granted[0]>=60:slot[0]='none'
        def keys(generation):return dict(version=1,device_id=runner.DEVICE,browser_nonce='b'*32,
                                        browser_public_key='public',owner_public_key='owner'),None
        def seal(start,*args):return dict(boot_id=start['boot_id'],request_id='c'*32,tag=runner.b64(bytes(16)))
        def exchange(method,path,body,deadline):
            calls.append((method,path,body));expire()
            if path.endswith('public-status') or path.endswith('claim/status'):
                value=dict(public,claim_available=slot[0]=='none')
                if path.endswith('claim/status'):value['slot_state']=slot[0]
                code=200
            elif path.endswith('start'):
                if uncertain:raise TimeoutError('uncertain start')
                if body['device_id']!=runner.DEVICE:code=403;value={'error':{'code':'unavailable'}}
                elif body['owner_public_key']=='malformed':code=400;value={'error':{'code':'invalid_request'}}
                elif slot[0]!='none':code=409;value={'error':{'code':'busy'}}
                else:
                    slot[0]='granted';granted[0]=clock[0];code=200
                    value=dict(device_id=runner.DEVICE,boot_id='a'*32,browser_nonce=body['browser_nonce'],
                               browser_public_key=body['browser_public_key'],generation='1',slot_id='d'*32)
            else:
                if slot[0]=='granted':code=200;value={'state':'failed','generation':'0'};slot[0]='terminal';granted[0]=clock[0]
                else:code=403;value={'error':{'code':'unavailable'}}
            wirebody=b'' if body is None else json.dumps(body).encode()
            markers=b'Host: 192.168.4.1\r\n'
            if method=='POST':markers+=b'Origin: http://192.168.4.1\r\nContent-Type: application/json\r\nX-WsprryPico-Owner: 1\r\n'
            request=(method+' '+path+' HTTP/1.1\r\n').encode()+markers+b'\r\n'+wirebody
            response=('HTTP/1.1 '+str(code)+' Response\r\n\r\n').encode()+json.dumps(value).encode()
            return code,value,request,response
        info=dict(device_id=runner.DEVICE,revision='b'*12,provisioning_source='consumer_preclock',access_state='healthy',
                  status=dict(boot_id='a'*32,state='empty',engine='inhibited-standalone-simulator',enabled=False,
                              output_active=False,storage_healthy=True))
        def wtp():return dict(boot_id=public['boot_id'],state='empty',owner_id=None,job_id=None,output_active=False)
        def cancel():
            slot[0]='none'
            if reboot:
                old=public['boot_id'];public['boot_id']='e'*32;info['status']['boot_id']='e'*32
                return dict(boundary='REBOOT',before_boot_id=old,boot_id='e'*32,
                            profile_generation='1',reboot_attempts=1)
            return dict(boundary='AP_WITHDRAWAL',withdrawn=True,reactivated=True,boot_id='a'*32)
        def interrupted(path,body,deadline):
            return exchange('POST',path,body,deadline)[2]
        with patch.object(runner,'keys',side_effect=keys),patch.object(runner,'seal',side_effect=seal),patch.object(runner,'resource_health'):
            def action():return runner.run(case,exchange,lambda:(info,json.dumps(info).encode()),wtp if wtp_enabled else None,
                'b'*40,'a'*32,evidence,{},clock=lambda:clock[0],sleeper=lambda s:clock.__setitem__(0,clock[0]+s),
                cancel_boundary=cancel if boundaries else None,interrupted_start=interrupted if boundaries else None)
            if uncertain:
                with self.assertRaises(TimeoutError):action()
            else:result=action();self.assertEqual(result['status'],'PENDING' if case in ('CANCELLED','INTERRUPTED') and not boundaries else 'NEGATIVE_REVIEW_REQUIRED')
        return calls,evidence
    def test_source_exact_negatives_and_preservation(self):
        for case in ('WRONG_DEVICE','MALFORMED','COMPETING','EXPIRED','REPLAY'):
            with self.subTest(case=case):
                calls,evidence=self.exercise(case)
                self.assertEqual(evidence.rows[-1][0],'negative_case_complete')
                self.assertEqual(evidence.rows[-1][1]['generation'],'1')
    def test_cancel_named_boundary_and_interrupted_retention_semantics(self):
        for case in ('CANCELLED','INTERRUPTED'):
            calls,evidence=self.exercise(case,boundaries=True)
            self.assertEqual(evidence.rows[-1][0],'negative_case_complete')
            if case=='INTERRUPTED':
                row=next(v for k,v in evidence.rows if k=='interrupted_start_semantics')
                self.assertFalse(row['response_close_cancels'])
                self.assertEqual(sum(path.endswith('start') for _,path,_ in calls),1)

    def test_reboot_invalidates_old_packet_preserves_generation(self):
        calls,evidence=self.exercise('CANCELLED',boundaries=True,reboot=True)
        submit=next(body for method,path,body in calls if path.endswith('submit'))
        self.assertEqual(submit['boot_id'],'a'*32)
        receipt=next(value['receipt'] for kind,value in evidence.rows if kind=='cancel_boundary')
        self.assertEqual(receipt['boot_id'],'e'*32)
        self.assertEqual(receipt['reboot_attempts'],1)
        self.assertEqual(evidence.rows[-1][1]['generation'],'1')

    def test_uncertain_start_not_replayed(self):
        calls,evidence=self.exercise('EXPIRED',uncertain=True)
        self.assertEqual(sum(path.endswith('start') for _,path,_ in calls),1)
        self.assertFalse(any(path.endswith('submit') for _,path,_ in calls))
    def test_ap_only_scope_explicitly_leaves_wtp_authority_unverified(self):
        calls,evidence=self.exercise('EXPIRED',wtp_enabled=False)
        self.assertTrue(any(k=='wtp_authority_unverified' for k,v in evidence.rows))
        self.assertFalse(any(k=='actual_wtp_status' for k,v in evidence.rows))
        self.assertFalse(evidence.rows[-1][1]['wtp_owner_verified'])
        self.assertFalse(evidence.rows[-1][1]['wtp_job_identity_verified'])
    def test_missing_supported_boundaries_pending_without_mutation(self):
        for case in ('CANCELLED','INTERRUPTED'):
            calls,evidence=self.exercise(case)
            self.assertFalse(any(method=='POST' for method,_,_ in calls))
            self.assertEqual(evidence.rows[-1][0],'case_pending')
if __name__=='__main__':unittest.main()
