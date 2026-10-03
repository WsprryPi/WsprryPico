#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import unittest
from unittest.mock import patch
import phase12_engineering_sessions as runner
class Evidence:
    def __init__(self):self.rows=[]
    def record(self,kind,**value):self.rows.append((kind,value))
class Tests(unittest.TestCase):
    def test_actual_session_candidate_plain_compile_default_runtime_tls(self):
        candidate=dict(role='session_deadline',target='WsprryPico',fault_stage=0,
                       lan_mode='plain',uf2={'sha256':'c'*64})
        manifest=dict(candidates=[candidate],source_commit='b'*40)
        evidence=Evidence();evidence.close=lambda:None
        with patch.object(runner,'Evidence',return_value=evidence), patch.object(runner,'HTTPS'):
            with patch.object(runner,'campaign') as campaign:
                runner.run_device(candidate,manifest,'192.168.1.2','a'*32,'pico.example',
                                  '/unused','private','/unused',lambda:{},lambda:{},lambda:{})
                campaign.assert_called_once()

    def test_pressure_idle_absolute_and_no_jobs(self):
        self.pressure_idle_absolute_and_no_jobs(0)
    def test_absolute_expiry_with_one_second_http_latency(self):
        self.pressure_idle_absolute_and_no_jobs(1.01)
    def pressure_idle_absolute_and_no_jobs(self,latency):
        clock=[0];sessions={};counter=[0];calls=[];evidence=Evidence()
        def prune():
            for cookie,(start,last) in list(sessions.items()):
                if clock[0]-start>=60 or clock[0]-last>=15:del sessions[cookie]
        def observe():prune();return {'count':len(sessions)}
        def instant_exchange(method,path,body,cookie,session,deadline):
            calls.append((method,path,clock[0]));prune()
            if path.endswith('login'):
                if len(sessions)==4:return 409,{'error':{'code':'busy'}},{}
                counter[0]+=1;token='__Host-wsprrypico='+('%032x'%counter[0]);sessions[token]=(clock[0],clock[0])
                return 200,{'ok':True,'principal':'p'}, {'set-cookie':token+'; Path=/; Secure'}
            if cookie not in sessions:return 401,{'error':{'code':'authentication_required'}},{}
            if path.endswith('logout'):del sessions[cookie];return 200,{'ok':True},{}
            start,_=sessions[cookie];sessions[cookie]=(start,clock[0])
            return 200,{'device_id':runner.DEVICE,'principal':'p'},{}
        def exchange(*args):
            value=instant_exchange(*args);clock[0]+=latency;return value
        with patch.object(runner,'guard',side_effect=lambda info,*_:info['count']):
            runner.campaign(exchange,observe,evidence,'private','b'*40,'a'*32,'192.168.1.2',
                            clock=lambda:clock[0],sleeper=lambda seconds:clock.__setitem__(0,clock[0]+seconds),
                            observe_ap=lambda:{},observe_status=lambda:dict(boot_id='a'*32,output_active=False,owner_id=None,job_id=None,state='empty'))
        self.assertEqual(counter[0],6)
        self.assertEqual(len(sessions),0)
        self.assertEqual([kind for kind,_ in evidence.rows if kind.endswith('_pass')],
                         ['capacity_reclamation_pass','idle_expiry_pass','absolute_expiry_pass'])
        self.assertTrue(all(path.startswith('/local/v1/') for _,path,_ in calls))
    def test_uncertain_login_no_retry(self):
        calls=[];evidence=Evidence()
        def exchange(*args):calls.append(args);raise TimeoutError('uncertain')
        with patch.object(runner,'guard',return_value=0):
            with self.assertRaises(TimeoutError):runner.campaign(exchange,lambda:{},evidence,'secret','b'*40,'a'*32,'192.168.1.2',observe_ap=lambda:{},observe_status=lambda:dict(boot_id='a'*32,output_active=False,owner_id=None,job_id=None,state='empty'))
        self.assertEqual(len(calls),1)
        self.assertFalse(any(kind=='session_campaign_complete' for kind,_ in evidence.rows))
    def test_wrong_limits_and_identity_rejected(self):
        proof=dict(device_id=runner.DEVICE,boot_id='a'*32,source_commit='b'*40,
                   interface='wlan2',destination='192.168.4.1',associated=True,local_ipv4='192.168.4.2')
        info=dict(device_id=runner.DEVICE,revision='b'*12,provisioning_source='provisioned',
          lan_wtp_mode='engineering-tls',network={},softap_session_inactivity_ms="15000",
          softap_session_absolute_ms="60000",softap_session_capacity=4,softap_retained_sessions=0,
          access_state='healthy',status=dict(boot_id='a'*32,engine='inhibited-standalone-simulator',
          output_active=False,enabled=False,state='empty',storage_healthy=True))
        with patch.object(runner,'resource_health'):
            self.assertEqual(runner.guard(info,'b'*40,'a'*32,'192.168.4.1',proof),0)
            proof['associated']=False
            with self.assertRaises(ValueError):runner.guard(info,'b'*40,'a'*32,'192.168.4.1',proof)
            proof['associated']=True
            info['softap_session_absolute_ms']='43200000'
            with self.assertRaises(ValueError):runner.guard(info,'b'*40,'a'*32,'192.168.4.1',proof)
            info['softap_session_absolute_ms']='60000';info['device_id']='wrong'
            with self.assertRaises(ValueError):runner.guard(info,'b'*40,'a'*32,'192.168.4.1',proof)
if __name__=='__main__':unittest.main()
