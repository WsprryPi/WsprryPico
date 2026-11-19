"""Retired maintained commands refuse before enumeration, open, or RF."""
import contextlib,importlib,io,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
class Retirement(unittest.TestCase):
 def test_no_io(self):
  for name in ['rf_wtp','wtp_probe','wtp_monitor','usb_inventory','check_usb_target','inhibited_network_acceptance']:
   module=importlib.import_module(name)
   for arguments in [[],['--run'],['--list'],['/not-a-device']]:
    with self.subTest(name=name,args=arguments),patch.object(sys,'argv',[name,*arguments]),patch.object(module.os,'open') as opening,contextlib.redirect_stderr(io.StringIO()) as errors:
     with self.assertRaises(SystemExit) as outcome:module.main()
     self.assertEqual(outcome.exception.code,2);self.assertIn('WTP tooling is retired',errors.getvalue());opening.assert_not_called()
if __name__=='__main__':unittest.main()
