from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))

import copy,unittest
from capacity_pending import assess,run
from inhibited_network_acceptance import https_authority
class Tests(unittest.TestCase):
 def test_pending_then_actual_reset_reclaims_and_timeout_never_passes(self):
  b=dict(boot='b',source='s',active=2,pending=0,pool=10,timeouts=0,rejected=0)
  p=dict(b,pending=1,pool=20);f=dict(b,timeouts=1)
  self.assertEqual(assess(b,[p,f],'reset',10.5)['status'],'OBSERVED_EXCESS_REFUSAL_AND_RECLAMATION')
  for changes,outcome in (({},'timeout'),({'pending':1},'reset'),({'boot':'foreign'},'reset'),({'active':1},'reset'),({'pool':20},'reset')):
   with self.assertRaises(ValueError):assess(b,[p,dict(f,**changes)],outcome,10.5)
 def test_one_connector_and_insufficient_budget_never_starts(self):
  calls=[];b=dict(boot='b',source='s',active=2,pending=0,pool=10,timeouts=0,rejected=0);count=[0]
  def observe():count[0]+=1;return dict(b,rejected=int(count[0]>1))
  def connect(deadline):calls.append(deadline);raise ConnectionResetError('actual')
  result=run(connect,observe,lambda d:None,lambda d:None,lambda *a:None,15,clock=lambda:0,sleeper=lambda d:None)
  self.assertEqual(len(calls),1)
  with self.assertRaises(ValueError):run(connect,observe,lambda d:None,lambda d:None,lambda *a:None,14,clock=lambda:0)
  self.assertEqual(len(calls),1)
class DelayedCleanupTests(unittest.TestCase):
 def test_peer_refuses_before_next_firmware_cleanup_observation(self):
  import threading
  event=threading.Event();calls=[];index=[0];now=[0.]
  baseline=dict(boot='b',source='s',active=2,pending=0,pool=10,timeouts=0,rejected=0)
  def connector(deadline):calls.append('connect');event.set();raise ConnectionResetError('original peer')
  def observe():
   index[0]+=1
   if index[0]==1:return dict(baseline)
   event.wait(1)
   if index[0]==2:return dict(baseline,pending=1,pool=20)
   return dict(baseline,timeouts=1)
  result=run(connector,observe,lambda d:None,lambda d:None,lambda *a:None,15,clock=lambda:now[0],sleeper=lambda d:now.__setitem__(0,now[0]+d))
  self.assertEqual(calls,['connect']);self.assertGreaterEqual(index[0],3);self.assertEqual(result['status'],'OBSERVED_EXCESS_REFUSAL_AND_RECLAMATION')
if __name__=='__main__':unittest.main()
