#!/usr/bin/env python3
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_engineering_network as run
class Evidence:
    def __init__(self):self.rows=[]
    def record(self,*a,**kw):self.rows.append((a,kw))
class Tests(unittest.TestCase):
    def setup_case(self):
        self.clock=0;self.up=True;self.ap_calls=0;self.actions=[];self.associations=[];self.e=Evidence()
        self.context=dict(source_commit='1'*40,boot_id='2'*32,profile_generation=7,ssid='WsprryPico-0a9d89',
            password='wspr-0a9d89',fixture_connection='owned',no_join_cookie_token_reply=True,
            interfaces={'wlan0':{'state':'disconnected','connection':None},'wlan2':{'connection':'owned'},
                        'eth0':{'state':'connected'},'wlan1':{'state':'connected'}})
    def fixture(self,action):self.actions.append(action);self.up=action=='station_up'
    def info(self):
        value=dict(device_id=run.DEVICE,revision='1'*12,provisioning_source='provisioned',access_state='healthy',
            lan_wtp_mode='engineering-tls',softap_session_inactivity_ms='900000',softap_session_absolute_ms='43200000',
            provisioning_generation='7',softap_retained_sessions=0,network={'link_status':3 if self.up else -1},
            status=dict(boot_id='2'*32,engine='inhibited-standalone-simulator',enabled=False,output_active=False,
                        storage_healthy=True,clock_state='synchronized'))
        return value,json.dumps(value).encode()
    def authority(self):return dict(boot_id='2'*32,output_active=False,state='empty',owner_id=None,job_id=None),b'actual-frame'
    def ap(self):
        self.ap_calls+=1
        if self.ap_calls==1:return dict(interface='wlan0',scan_fresh=True,link_observed=True,scan_ssids=[self.context['ssid']],associated_ssid=self.context['ssid'],socket_outcome='reply',http_raw=b'HTTP identity',http_device_id=run.DEVICE)
        return dict(interface='wlan0',scan_fresh=True,link_observed=True,scan_ssids=[],associated_ssid=None,socket_outcome='association_lost')
    def invoke(self):
        with patch.object(run,'resource_health'):
            return run.run(self.context,self.fixture,self.info,self.authority,self.associations.append,self.ap,self.e,
                clock=lambda:self.clock,sleeper=lambda s:setattr(self,'clock',self.clock+s))
    def test_supported_fallback_recovery_and_independent_withdrawal(self):
        self.setup_case();result=self.invoke()
        self.assertEqual(result['rf_jobs'],0);self.assertEqual(self.clock,92)
        self.assertEqual(self.actions,['station_down','station_up','station_up'])
        self.assertEqual(self.associations[0]['interface'],'wlan0');self.assertTrue(self.associations[0]['never_default'])
        self.assertEqual(self.associations[-1]['action'],'disconnect_owned')
    def test_timeout_and_absent_scan_do_not_prove_withdrawal(self):
        self.setup_case();original=self.ap
        def ap():
            value=original()
            if self.ap_calls>1:value['socket_outcome']='timeout'
            return value
        self.ap=ap
        with self.assertRaises(ValueError):self.invoke()
        self.assertTrue(self.up);self.assertEqual(self.associations[-1]['action'],'disconnect_owned')
    def test_management_or_busy_spare_rejected_before_host_change(self):
        self.setup_case();self.context['interfaces']['wlan0']['connection']='management'
        with self.assertRaises(ValueError):self.invoke()
        self.assertEqual(self.actions,[])
    def test_failed_fallback_identity_restores_owned_host(self):
        self.setup_case();original=self.ap
        def ap():
            value=original();value['http_device_id']='wrong';return value
        self.ap=ap
        with self.assertRaises(ValueError):self.invoke()
        self.assertTrue(self.up);self.assertEqual(self.associations[-1]['action'],'disconnect_owned')
class RadioComparisonTests(unittest.TestCase):
 def test_actual_network_callback_swapped_bindings(self):
   from phase12_fixture_roles import role_map
   f=Tests();f.setup_case();f.context['radio_roles']=role_map('swapped')
   f.context['interfaces']['wlan0'],f.context['interfaces']['wlan2']=f.context['interfaces']['wlan2'],f.context['interfaces']['wlan0']
   old=f.ap
   def ap():v=old();v['interface']='wlan2';return v
   f.ap=ap;result=f.invoke();self.assertEqual(result['rf_jobs'],0)
   self.assertEqual(f.associations[0]['interface'],'wlan2');self.assertEqual(f.clock,92)
 def test_foreign_connection_prevents_station_down(self):
   from phase12_fixture_roles import role_map
   f=Tests();f.setup_case();f.context['radio_roles']=role_map('swapped')
   f.context['interfaces']['wlan0'],f.context['interfaces']['wlan2']=f.context['interfaces']['wlan2'],f.context['interfaces']['wlan0']
   f.context['interfaces']['wlan0']['connection']='foreign'
   with self.assertRaises(ValueError):f.invoke()
   self.assertEqual(f.actions,[])

if __name__=='__main__':unittest.main()
