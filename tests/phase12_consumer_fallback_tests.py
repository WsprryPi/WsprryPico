import ast,tempfile,unittest,sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(HERE))

def extracted(path,name):
 tree=ast.parse(path.read_text());f=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
 return compile(ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[])),'actual_source','exec')
def require(value,message):
 if not value:raise ValueError(message)
class LossTests(unittest.TestCase):
 def test_actual_ordinary_info_without_gp14_fields_and_continuous_loss(self):
  for mode,expected in [('loss',60),('reconnect',85),('late',None),('generation',None),('boot',None),('regression',None)]:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
    now=[0];calls=[];receipts=[];number=[0]
    class Remote:
     def fixture(self,action,args):calls.append(action)
    class Backend:
     def info(self):
      number[0]+=1
      if mode=='late':now[0]=121
      stamp=int(now[0]*1e9)
      if mode=='regression' and number[0]>1:stamp=-1
      return dict(provisioning_source='consumer_preclock',provisioning_generation=6 if mode=='generation' else 5,status=dict(boot_id='different' if mode=='boot' else 'same',monotonic_now_ns=str(stamp)),network=dict(link_status=3 if mode=='reconnect' and 20<=now[0]<25 else -2))
    env=dict(remote=Remote(),backend=Backend(),clock=lambda:now[0],end=1200,bounded=lambda:None,require=require,counter=lambda x,*a:int(x),safe_info=lambda x,*a:x,exercise={'source_commit':'a'*40},root=Path(directory),private_write=lambda p,v:receipts.append((p,v)),sleeper=lambda s:now.__setitem__(0,now[0]+s))
    exec(extracted(HERE/'phase12_consumer_flash_status_orchestrator.py','fallback_ready'),env)
    deployed={'info':{'status':{'boot_id':'same'},'provisioning_generation':5}}
    if expected is None:
     with self.assertRaises(ValueError):env['fallback_ready'](deployed,'case')
    else:
     binding=env['fallback_ready'](deployed,'case');self.assertEqual(now[0],expected);self.assertEqual(binding['initial_join_seconds'],30);self.assertEqual(int(binding['initial_target_deadline_ns']),120_000_000_000)
     proof=receipts[-1][1];self.assertEqual(proof['status'],'STATION_LOSS_60S_OBSERVED_AP_PROOF_PENDING');self.assertEqual(int(proof['last_down_ns'])-int(proof['first_down_ns']),60_000_000_000)
    self.assertEqual(calls,['station_ap_down'])
class CarrierTests(unittest.TestCase):
 def test_actual_scan_http_proof_precedes_one_station_return(self):
  tree=ast.parse((HERE/'phase12_consumer_flash_status_dispatch.py').read_text());body=next(n for n in ast.walk(tree) if isinstance(n,ast.Try) and any(isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='initial_budget' for t in x.targets) for x in n.body)).body
  start=next(i for i,x in enumerate(body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='initial_budget' for t in x.targets));stop=next(i for i,x in enumerate(body[start:],start) if isinstance(x,ast.FunctionDef) and x.name=='retained_associate');fn=ast.FunctionDef(name='scenario',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body[start:stop+1],decorator_list=[]);code=compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'actual_source','exec')
  for mode in ('good','budget','lateinfo','generation','notdown','foreignap','apgeneration','unavailable','latehttp','lateup','transfer','regressedtime','responselatency'):
   with self.subTest(mode=mode):
    now=[0];calls=[]
    class Clock:
     @staticmethod
     def monotonic():return now[0]
    class Evidence:
     def record(self,*a,**kw):calls.append('evidence')
    def observe(deadline):
     now[0]=31 if mode=='lateinfo' else 20 if mode=='responselatency' else 1
     return dict(status=dict(monotonic_now_ns=str(121_000_000_000 if mode=='transfer' else -1 if mode=='regressedtime' else 1_000_000_000)),network={'link_status':3 if mode=='notdown' else -2},provisioning_generation=6 if mode=='generation' else 5,provisioning_source='consumer_preclock'),b'actual'
    def http(*args):
     calls.append('http');now[0]=31 if mode=='latehttp' else now[0]
     return 200,dict(device_id='B',boot_id='different' if mode=='foreignap' else 'same',profile_source=5,generation=6 if mode=='apgeneration' else 5,claim_available=mode!='unavailable'),b'request',b'reply'
    env=dict(case=True,time=Clock,end=100,observe=observe,http=http,DEVICE='B',evidence=Evidence(),counter=lambda x,*a:int(x),require=require,request=dict(generation=5,authority='x',boot_id='same',initial_join_seconds=0 if mode=='budget' else 30,fallback_monotonic_ns='0',initial_target_deadline_ns='11000000000' if mode=='responselatency' else '120000000000'),associate=lambda deadline,**kwargs:calls.append('associate'),fixture_action=lambda args:(calls.append('up'),now.__setitem__(0,41 if mode=='lateup' else now[0])),root=Path('/private/test'))
    if mode=='good':
     exec(code,env);env['scenario']();self.assertEqual(calls.count('up'),1);self.assertLess(calls.index('associate'),calls.index('http'));self.assertLess(calls.index('http'),calls.index('up'))
    else:
     with self.assertRaises(ValueError):
      exec(code,env);env['scenario']()
     self.assertEqual(calls.count('up'),1 if mode=='lateup' else 0)
class NtpTests(unittest.TestCase):
 def test_actual_warmed_process_identity_preserved_and_changed_pid_rejected(self):
  import importlib.util,sys,json
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
  spec=importlib.util.spec_from_file_location('private_fixture',Path(__file__).resolve().parents[1]/'scripts/phase12_engineering_fixture.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'campaign';root.mkdir();proc=Path(d)/'proc';(proc/'12').mkdir(parents=True);roles={'sha256':'a'*64}
   pid=dict(pid=12,root=str(root),startup_token='b'*32,roles_sha256=roles['sha256']);ready=dict(pid=12,startup_token='b'*32,roles_sha256=roles['sha256'],address=m.ADDRESS,port=123)
   (root/'ntp-pid.json').write_text(json.dumps(pid));(root/'ntp-ready.json').write_text(json.dumps(ready));(root/'ntp-enabled.json').write_text('{}')
   path=proc/'12'/'cmdline';path.write_bytes(b'python\0'+str(Path(m.__file__).resolve()).encode()+b'\0--serve-ntp\0'+str(root).encode()+b'\0'+b'b'*32+b'\0')
   original=m.verify_warmed_ntp(root,roles,process_root=proc);self.assertEqual(original,m.verify_warmed_ntp(root,roles,process_root=proc))
   path.write_bytes(b'foreign process')
   with self.assertRaises(ValueError):m.verify_warmed_ntp(root,roles,process_root=proc)
class ExistingRestartTests(unittest.TestCase):
 def test_disabled_populated_restart_does_not_require_warmed_responder(self):
  import importlib.util,sys
  from unittest.mock import patch
  root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'scripts'))
  spec=importlib.util.spec_from_file_location('private_fixture_restart',Path(__file__).resolve().parents[1]/'scripts/phase12_engineering_fixture.py');fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
  spec=importlib.util.spec_from_file_location('original_populated_tests',root/'tests/phase12_populated_tests.py');tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
  old=tests.fixture;tests.fixture=fixture
  try:
   with patch.object(fixture,'verify_warmed_ntp',side_effect=AssertionError('disabled restart must not require warm')):
    tests.Tests().test_owned_restart_preserves_receipt_and_launches_no_responder()
  finally:tests.fixture=old
from types import SimpleNamespace
import importlib.util
_spec=importlib.util.spec_from_file_location('association_helper',HERE/'phase12_populated_dispatch.py')
helper=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(helper)

class AssociationOrderTests(unittest.TestCase):
 def test_actual_scan_then_once_callback_then_once_activation(self):
  for mode in ('good','empty','uncertain','late'):
   with self.subTest(mode=mode):
    calls=[];now=[0]
    def runner(argv,**kw):
     calls.append('scan' if 'scan' in argv else 'activation' if 'nmcli' in argv else 'link')
     raw=b'BSS 88:a2:9e:0a:9d:89(on wlan0)\n\tfreq: 2422.0\n\tSSID: WsprryPico-0a9d89\n' if 'scan' in argv else b'Connected to 88:a2:9e:0a:9d:89\n\tSSID: WsprryPico-0a9d89\n\tfreq: 2422\n'
     if mode=='empty':raw=b''
     return SimpleNamespace(returncode=0,stdout=raw,stderr=b'')
    def callback(deadline):
     calls.append('station_up')
     if mode=='uncertain':raise TimeoutError('lost UP reply')
     if mode=='late':now[0]=31
    class Evidence:
     def record(self,*a,**k):pass
    def invoke():helper.associate_observer('owned','WsprryPico-0a9d89',30,Evidence(),single_channel=True,before_activation=callback,clock=lambda:now[0],runner=runner,sleeper=lambda d:now.__setitem__(0,now[0]+d))
    if mode=='good':invoke();self.assertEqual(calls,['scan','station_up','activation','link'])
    else:
     with self.assertRaises((ValueError,TimeoutError)):invoke()
     self.assertNotIn('activation',calls);self.assertEqual(calls.count('station_up'),0 if mode=='empty' else 1)
 def test_actual_child_default_and_optin_order_and_uncertainty(self):
  tree=ast.parse((HERE/'phase12_consumer_flash_status_dispatch.py').read_text());body=next(n.body for n in ast.walk(tree) if isinstance(n,ast.Try) and any(isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='early_return' for t in x.targets) for x in n.body))
  start=next(i for i,x in enumerate(body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='early_return' for t in x.targets));stop=next(i for i,x in enumerate(body[start:],start) if isinstance(x,ast.FunctionDef) and x.name=='retained_associate')
  fn=ast.FunctionDef(name='scenario',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body[start:stop+1],decorator_list=[])
  code=compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'actual','exec')
  for early,mode in ((False,'good'),(True,'good'),(True,'uncertain'),(True,'foreign')):
   calls=[];now=[0]
   class Clock:
    monotonic=staticmethod(lambda:now[0])
   class Evidence:
    def record(self,*a,**k):pass
   def associate(deadline,before_activation=None):
    calls.append('exact_beacon')
    if before_activation:before_activation(deadline)
    calls.append('activation')
   def fixture(value):
    calls.append('station_up')
    if mode=='uncertain':raise TimeoutError('lost')
   def http(*args):calls.append('HTTP');return 200,dict(device_id='wrong' if mode=='foreign' else 'B',boot_id='boot',profile_source=5,generation=6,claim_available=True),b'',b''
   def require(ok,msg):
    if not ok:raise ValueError(msg)
   env=dict(request=dict(station_up_after_beacon=early,authority='a',boot_id='boot',generation=6),case=True,end=100,initial_end=30,root=Path('/private/test'),time=Clock,evidence=Evidence(),associate=associate,fixture_action=fixture,http=http,DEVICE='B',counter=lambda x,*a:int(x),require=require)
   exec(code,env)
   if mode=='good':env['scenario']();self.assertEqual(calls,['exact_beacon','station_up','activation','HTTP'] if early else ['exact_beacon','activation','HTTP','station_up'])
   else:
    with self.assertRaises((ValueError,TimeoutError)):env['scenario']()
   self.assertEqual(calls.count('station_up'),1)

if __name__=='__main__':unittest.main()
