import ast,pathlib,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase12_final_collection import collect_final
class Tests(unittest.TestCase):
 def test_stale_preserved_final_retrieved(self):
  with tempfile.TemporaryDirectory() as d:
   class Remote:
    root=Path(d)
    def collect(self,names):
     for n in names:(self.root/n).write_text('REMOVED')
   r=Remote();(r.root/'virtual.json').write_text('AVAILABLE');collect_final(r,('virtual.json',))
   self.assertEqual((r.root/'before-final-virtual.json').read_text(),'AVAILABLE');self.assertEqual((r.root/'virtual.json').read_text(),'REMOVED')
 def test_collision_symlink_and_invalid_preserve_original(self):
  for kind in ('collision','symlink','invalid'):
   with tempfile.TemporaryDirectory() as d:
    class Remote:
     root=Path(d)
     def collect(self,names):raise AssertionError('must not collect')
    r=Remote();p=r.root/'virtual.json';p.write_text('AVAILABLE')
    if kind=='collision':(r.root/'before-final-virtual.json').write_text('old')
    if kind=='symlink':p.unlink();p.symlink_to(r.root/'secret')
    with self.assertRaises(ValueError):collect_final(r,('../escape',) if kind=='invalid' else ('virtual.json',))
    if kind!='symlink':self.assertEqual(p.read_text(),'AVAILABLE')
 def test_collection_failure_preserves_early_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   class Remote:
    root=Path(d)
    def collect(self,names):raise OSError('transport failure')
   r=Remote();(r.root/'virtual.json').write_text('AVAILABLE')
   with self.assertRaises(OSError):collect_final(r,('virtual.json',))
   self.assertEqual((r.root/'before-final-virtual.json').read_text(),'AVAILABLE')
class SilentTests(unittest.TestCase):
 def test_actual_silent_missing_transfer_cannot_pass(self):
  with tempfile.TemporaryDirectory() as d:
   class Remote:
    root=Path(d)
    def collect(self,names):pass
   r=Remote();(r.root/'virtual.json').write_text('AVAILABLE')
   with self.assertRaisesRegex(ValueError,'missing'):collect_final(r,('virtual.json',))
   self.assertEqual((r.root/'before-final-virtual.json').read_text(),'AVAILABLE')
class NtpLifecycleTests(unittest.TestCase):
 def test_original_zero_reply_lifecycle_needs_no_per_response_metrics(self):
  import json
  for replies in (0,1):
   with self.subTest(replies=replies),tempfile.TemporaryDirectory() as directory:
    class Remote:
     root=Path(directory)
     def collect(self,names):
      (self.root/'ntp-stopped.json').write_text(json.dumps(dict(requests=replies,replies=replies)))
      (self.root/'ntp-server.log').write_text('')
    remote=Remote();(remote.root/'ntp-ready.json').write_text('{}')
    names=('ntp-stopped.json','ntp-metrics.json','ntp-server.log')
    if replies:
     with self.assertRaisesRegex(ValueError,'positive responder'):collect_final(remote,names)
    else:collect_final(remote,names)

class ParentTests(unittest.TestCase):
 def test_finish_and_final_collection_failures_do_not_skip_restoration(self):
  import importlib.util,sys
  from unittest.mock import patch
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
  spec=importlib.util.spec_from_file_location('private_populated',Path(__file__).resolve().parents[1]/'scripts/phase12_populated_orchestrator.py')
  parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
  for finish_failure in (False,True):
   with self.subTest(finish_failure=finish_failure),tempfile.TemporaryDirectory() as d:
    calls=[]
    class Backend:
     def __init__(self,plan,*args):self.root=Path(args[2]);self.remote='/home/pi/phase12-recovery-'+plan['campaign_id']
     def setup(self):return {}
     def snapshot(self,name):
      path=self.root/name;path.write_bytes(b'original exact baseline');return dict(path=name,sha256=parent.sha(path),inspection={})
     def restore(self,baseline,name):
      self.root.joinpath(name).write_bytes(self.root.joinpath(baseline['path']).read_bytes());calls.append(('restore',name));return {'readback':name}
     def stable_restore(self,*a):return {'samples':5}
     def cleanup(self):calls.append(('cleanup',))
    class Remote:
     def __init__(self,root):self.root=root
     def stage(self,*a):return 'a'*64
     def invoke(self,*a,**kw):return {}
     def collect(self,names):
      calls.append(('collect',tuple(names)))
      if 'fixture-management-after.json' in names:raise OSError('final transport failed')
     def fixture(self,action,args):
      calls.append(('fixture',action))
      if finish_failure and action=='finish':raise RuntimeError('original finish failed')
    def builder(*a,**kw):raise ValueError('body failed')
    root=Path(d)/'campaign'
    with patch.object(parent,'safe_info',lambda *a:None):
     result=parent.execute({'source_commit':'a'*40},d,root,root/'unused',root/'unused',backend_factory=Backend,remote_factory=Remote,builder=builder,cases='station')
    finish_index=calls.index(('fixture','finish'))
    final_index=next(i for i,c in enumerate(calls) if c[0]=='collect' and 'fixture-management-after.json' in c[1])
    self.assertLess(finish_index,final_index);self.assertIn(('restore','final-restoration.bin'),calls);self.assertEqual(calls[-1],('cleanup',))
    self.assertEqual((root/'baseline.bin').read_bytes(),(root/'final-restoration.bin').read_bytes())
    self.assertEqual(result['error']['message'],'body failed')
class TeardownTests(unittest.TestCase):
 def test_actual_both_parent_finally_preserves_finish_error_and_restores(self):
  import ast
  for name in ('phase12_populated_orchestrator.py','phase12_consumer_flash_status_orchestrator.py'):
   tree=ast.parse((Path(__file__).resolve().parents[1]/'scripts'/name).read_text());execute=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
   block=next(n for n in execute.body if isinstance(n,ast.Try)).finalbody
   for finish_failure in (False,True):
    with self.subTest(parent=name,finish_failure=finish_failure),tempfile.TemporaryDirectory() as d:
     root=Path(d);(root/'baseline.bin').write_bytes(b'exact baseline');calls=[]
     class Remote:
      def __init__(self):self.root=root
      def collect(self,names):
       calls.append(('collect',tuple(names)))
       if 'fixture-management-after.json' in names:raise OSError('final transfer')
      def invoke(self,*a,**kw):return {}
      def fixture(self,action,args):
       calls.append(('finish',action))
       if finish_failure:raise RuntimeError('original finish')
     class Backend:
      remote='/home/pi/private'
      def restore(self,baseline,name):
       (root/name).write_bytes((root/'baseline.bin').read_bytes());calls.append(('restore',));return {'readback':name}
      def stable_restore(self,*a):return {'samples':5}
      def cleanup(self):calls.append(('cleanup',))
     class Ledger:
      def record(self,*a,**kw):pass
     values=dict(remote=Remote(),backend=Backend(),root=root,ledger=Ledger(),primary=None,restoration=None,baseline={},fixture=True,helper_staged=True,staged=True,save_cases=('station',),collect_final=collect_final,cleanup_failures=[])
     helper=next(n for n in execute.body if isinstance(n,ast.FunctionDef) and n.name=='record_cleanup_failure')
     exec(compile(ast.fix_missing_locations(ast.Module(body=[helper],type_ignores=[])),name,'exec'),values)
     values['baseline']={'path':'baseline.bin'}
     exec(compile(ast.fix_missing_locations(ast.Module(body=block,type_ignores=[])),name,'exec'),values)
     self.assertEqual((root/'final-restoration.bin').read_bytes(),b'exact baseline');self.assertEqual(calls[-1],('cleanup',))
     self.assertEqual(values['primary']['message'],'fixture cleanup failed' if finish_failure else 'final fixture evidence collection failed')
     self.assertTrue(any(c[0]=='collect' and 'fixture-management-after.json' in c[1] for c in calls))
class CleanupPersistenceTests(unittest.TestCase):
 def test_actual_finally_keeps_primary_records_failures_and_restores(self):
  for name in ['phase12_consumer_flash_status_orchestrator.py','phase12_populated_orchestrator.py','phase12_engineering_orchestrator.py']:
   t=ast.parse((Path(__file__).resolve().parents[1]/'scripts'/name).read_text());f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='execute');body=next(n for n in f.body if isinstance(n,ast.Try)).finalbody
   failures=['fixture','host'] if name=='phase12_engineering_orchestrator.py' else ['observer','fixture','final','host']
   for fault,ledger_raises in [(fault,raises) for fault in failures for raises in (False,True)]:
    with self.subTest(parent=name,fault=fault),tempfile.TemporaryDirectory() as d:
     calls=[];events=[];root=pathlib.Path(d);(root/'baseline.bin').write_bytes(b'exact')
     def fail(stage):
      if stage==fault:raise RuntimeError('independent cleanup failure')
     class Remote:
      def collect(self,*a):pass
      def invoke(self,*a,**k):fail('observer')
      def fixture(self,*a):fail('fixture')
     class Backend:
      remote='/private/retained'
      def restore(self,baseline,name):calls.append('restore');(root/name).write_bytes((root/'baseline.bin').read_bytes());return {'readback':name}
      def stable_restore(self,*a):return {'samples':5}
      def cleanup(self):calls.append('host');fail('host')
     class Ledger:
      def record(self,event,*a,**k):
       events.append(event)
       if ledger_raises and event.endswith('_failed'):raise OSError('ledger unavailable')
     primary={'message':'original body failure'}
     ns=dict(remote=Remote(),backend=Backend(),root=root,ledger=Ledger(),primary=primary,restoration=None,baseline={'path':'baseline.bin'},fixture=True,fixture_attempted=True,helper_staged=True,staged=True,save_cases=('station',),collect_final=lambda *a,**k:fail('final'),cases_attempted=False,sleeper=lambda _:None)
     if name=='phase12_engineering_orchestrator.py':ns['fixture']=lambda *a:fail('fixture')
     helper=next(n for n in f.body if isinstance(n,ast.FunctionDef) and n.name=='record_cleanup_failure')
     ns['cleanup_failures']=[]
     exec(compile(ast.fix_missing_locations(ast.Module(body=[helper,*body],type_ignores=[])),name,'exec'),ns)
     self.assertEqual(ns['primary'],primary);self.assertIn('restore',calls);self.assertEqual(calls[-1],'host');self.assertEqual((root/'final-restoration.bin').read_bytes(),b'exact')
     expected={'observer':'observer_cleanup_failed','fixture':'fixture_cleanup_failed','final':'final_collection_failed','host':'host_cleanup_failed'}[fault];self.assertIn(expected,events)
     failure=next(x for x in ns['cleanup_failures'] if x['event']==expected)
     self.assertEqual(failure.get('ledger_error_type'), 'OSError' if ledger_raises else None)
     result_node=next(n.value for n in f.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='result' for t in n.targets))
     fallback=next(k.value for k in result_node.keywords if k.arg=='cleanup_failures')
     self.assertIn(failure,eval(compile(ast.Expression(fallback),name,'eval'),ns))
if __name__=='__main__':unittest.main()
