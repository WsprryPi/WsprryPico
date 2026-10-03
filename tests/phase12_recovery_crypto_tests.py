#!/usr/bin/env python3
"""Python client interoperability with retained C++ Pico recovery vector."""
import base64
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase12_recovery_device as d
try:
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    AVAILABLE=True
except ImportError: AVAILABLE=False

@unittest.skipUnless(AVAILABLE,'existing cryptography required; run on retained wspr5 environment')
class Crypto(unittest.TestCase):
    def test_exact_pico_reference_vector(self):
        original=d.DEVICE
        try:
            d.DEVICE='0102030405060708090a0b0c0d0e0f10'
            start=dict(device_id=d.DEVICE,boot_id='1112131415161718191a1b1c1d1e1f20',slot_id='2122232425262728292a2b2c2d2e2f30',pico_public_key='3p7bfXt9wbTTW2HC7OQ1Nz-DQ8hbeGdNrfx-FG-IK08')
            private=X25519PrivateKey.from_private_bytes(bytes.fromhex('77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a'))
            v=d.seal_recovery('full',dict(device_id=d.DEVICE,status=dict(boot_id=start['boot_id'])),start,private,'7172737475767778797a7b7c7d7e7f80','bebc2fdea279d2ed7e088e650db7b759',d.unb64('fzCMy0ZhMgOmufn-'))
            self.assertEqual(v['ciphertext'],'2V7II_EJRlVc');self.assertEqual(v['tag'],'UhQFkPvLV4R69Td1YgnKvg')
            start['boot_id']='0'*32
            with self.assertRaises(ValueError): d.seal_recovery('full',dict(device_id=d.DEVICE,status=dict(boot_id='1'*32)),start,private,'7'*32,'8'*32,b'\0'*12)
        finally: d.DEVICE=original
    def test_strict_decoding(self):
        with self.assertRaises(ValueError):d.strict('{"a":1,"a":2}')
        with self.assertRaises(ValueError):d.strict('{"a":NaN}')
        with self.assertRaises(ValueError):d.unb64('YQ==')

class RecoverySecurity(unittest.TestCase):
 def info(self):return dict(provisioning_source='provisioned',access_default_password=True,access_state='healthy',local_suffix='0a9d89',revision='a'*12,phase12_fault_stage=1,phase12_fault_consumed=False)
 def request(self):return dict(interface='wlan2',connection='p12-recovery-'+'b'*32,revision='a'*12,stage=1)
 @unittest.skipUnless(AVAILABLE,'existing cryptography required for actual prepare imports')
 def test_provisioned_secured_mode_before_single_activation_actual_prepare(self):
  class Stop(Exception):pass
  calls=[]
  def execute(argv,timeout):calls.append((argv,timeout))
  with patch.object(d,'console',return_value=self.info()),patch.object(d,'healthy',side_effect=lambda x:x),patch.object(d,'execute',execute),patch.object(d,'http',side_effect=Stop):
   with self.assertRaises(Stop):d.prepare(Path('/home/pi/phase12-recovery-'+'b'*32),self.request())
  self.assertEqual(len(calls),2);self.assertIn('modify',calls[0][0]);self.assertEqual(calls[0][1],10)
  argv=calls[0][0]
  for key,value in [('wifi-sec.key-mgmt','wpa-psk'),('wifi-sec.proto','rsn'),('wifi-sec.pairwise','ccmp'),('wifi-sec.group','ccmp')]:self.assertEqual(argv[argv.index(key)+1],value)
  self.assertEqual(calls[1],(['sudo','-n','nmcli','connection','up',self.request()['connection']],35))
 def test_open_source_unchanged_and_unowned_or_custom_access_refused(self):
  with patch.object(d,'execute') as execute:
   info=self.info();info['provisioning_source']='consumer_preclock';d.configure_recovery_security(Path('/home/pi/phase12-recovery-'+'b'*32),info,self.request());execute.assert_not_called()
   for changes in ({'connection':'management'},{'connection':'p12-recovery-'+'c'*32},{'interface':'wlan1'}):
    with self.assertRaises(ValueError):d.configure_recovery_security(Path('/home/pi/phase12-recovery-'+'b'*32),self.info(),dict(self.request(),**changes))
   info=self.info();info['access_default_password']=False
   with self.assertRaises(ValueError):d.configure_recovery_security(Path('/home/pi/phase12-recovery-'+'b'*32),info,self.request())
   execute.assert_not_called()

class RecoveryTerminalRestore(unittest.TestCase):
 def info(self,state='aborted',**changes):
  return dict(device_id=d.DEVICE,access_state='healthy',status=dict(engine='inhibited-standalone-simulator',output_active=False,enabled=False,state=state,owner_id=None,job_id='retained-known-job',storage_healthy=True,**changes))
 def test_terminal_retained_job_accepts_only_repair(self):
  for state in ('aborted','complete'):
   v=self.info(state);self.assertIs(d.healthy(v,allow_fault=True,repair=True),v)
   with patch.object(d,'resource_health'):
    with self.assertRaises(ValueError):d.healthy(v,allow_fault=True)
   del v['status']['owner_id'];self.assertIs(d.healthy(v,allow_fault=True,repair=True),v)
 def test_unsafe_states_owners_output_engine_enable_refused(self):
  for state in ('loaded','armed','running','missed','unknown'):
   with self.assertRaises(ValueError):d.healthy(self.info(state),allow_fault=True,repair=True)
  for key,value in [('owner_id','actual-owner'),('output_active',True),('enabled',True),('engine','pio'),('engine','unknown')]:
   v=self.info();v['status'][key]=value
   with self.assertRaises(ValueError):d.healthy(v,allow_fault=True,repair=True)
 def test_existing_empty_failed_and_nonrepair_conservatism(self):
  for state in ('empty','failed'):
   v=self.info(state);v['status']['job_id']=None
   self.assertIs(d.healthy(v,allow_fault=True,repair=True),v)
   with patch.object(d,'resource_health'):self.assertIs(d.healthy(v,allow_fault=True),v)
   v['status']['job_id']='unexpected'
   with self.assertRaises(ValueError):d.healthy(v,allow_fault=True,repair=True)
 def test_actual_rom_terminal_calls_one_supported_bootsel(self):
  calls=[]
  def console(command):
   calls.append(command);return self.info() if command=='INFO' else {'ok':True,'rebooting':True}
  with patch.object(d.Path,'exists',return_value=True),patch.object(d,'console',console),patch.object(d.time,'sleep'),patch.object(d,'execute',return_value=''):
   d.rom(repair=True)
  self.assertEqual(calls,['INFO','BOOTSEL'])

if __name__=='__main__':unittest.main()
