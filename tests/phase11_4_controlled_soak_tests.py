#!/usr/bin/env python3
"""Hardware-free guards and observation schedule boundaries."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import phase11_4_controlled_soak as soak

class Tests(unittest.TestCase):
 def test_plan_does_not_access_root(self):
  p=subprocess.run([sys.executable,soak.__file__,'setup','--root','/nonexistent'],capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stderr)
 def test_optimized_execution_refused(self):
  p=subprocess.run([sys.executable,'-O',soak.__file__,'setup','--root','/nonexistent','--run'],capture_output=True,text=True)
  self.assertNotEqual(p.returncode,0);self.assertIn('enabled assertions',p.stderr)
 def test_quiet_windows(self):
  start=1000;end=start+28800
  for offset,quiet in [(0,True),(119.99,True),(120,False),(599.99,False),(600,True),(720,False),(28679,False),(28680,True),(28800,True)]:
   self.assertEqual(soak.old.quiet_window(start+offset,start,end),quiet,offset)
 def test_changed_boot_blocks_automatic_restore(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'hotspot-baseline.json').write_text(json.dumps({'status':{'boot_id':'old'}}))
   value={'device_id':soak.h.DEVICE,'revision':soak.REVISION,'deployment_identity_matches':True,'recovery_boot':False,
    'status':{'boot_id':'new','engine':'inhibited-standalone-simulator','output_active':False,'enabled':False,'storage_healthy':True}}
   with patch.object(soak,'ROOT',root),patch.object(soak,'BASE_CONSOLE',return_value=value) as command:
    with self.assertRaisesRegex(ValueError,'Unexpected boot'):soak.console('CONFIG {}')
    command.assert_called_once_with()

if __name__=='__main__':unittest.main()
