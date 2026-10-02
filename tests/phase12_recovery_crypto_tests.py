#!/usr/bin/env python3
"""Python client interoperability with retained C++ Pico recovery vector."""
import base64
import sys
from pathlib import Path
import unittest
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

if __name__=='__main__':unittest.main()
