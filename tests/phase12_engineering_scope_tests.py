import ast,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from phase12_recovery_orchestrator import private_write
from phase12_engineering_orchestrator import COMMON_HELPERS,COMMON_REPOSITORY_ASSETS,CREDENTIAL_ASSETS
SOURCE=Path(__file__).resolve().parents[1]/'scripts/phase12_engineering_orchestrator.py'
class Tests(unittest.TestCase):
 def test_isolated_cases_stages_common_schema_credentials_without_composition(self):
  tree=ast.parse(SOURCE.read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='cases')
  with tempfile.TemporaryDirectory() as d:
   calls=[]
   class Remote:
    backend=type('Backend',(),{'remote':'/private/no-access'})()
    def stage(self,path,name):calls.append(name);return 'hash'
    def invoke(self,*a,**kw):raise AssertionError('isolated must not compose')
   class Process:
    @staticmethod
    def run(*a,**kw):calls.append('schema-directory')
   args=type('Args',(),dict(scope='bond-revocation',preparation_manifest=Path(d)/'manifest',credential_root=Path(d)))()
   ns=dict(remote=Remote(),a=args,Path=Path,__file__=str(SOURCE),subprocess=Process,private_write=lambda *a:None,COMMON_HELPERS=COMMON_HELPERS,COMMON_REPOSITORY_ASSETS=COMMON_REPOSITORY_ASSETS,CREDENTIAL_ASSETS=CREDENTIAL_ASSETS)
   exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'private','exec'),ns)
   result=ns['cases']({'root':Path(d)})
   self.assertEqual(result['status'],'COMMON_INPUTS_STAGED')
   for name in ('docs/protocol/wtp-1.schema.json','owner-client.crt','owner-client.key','client-ca.crt','contender-client.crt','preparation-manifest.json'):self.assertIn(name,calls)
class SelectionTests(unittest.TestCase):
 def test_actual_cli_callback_selection_each_scope(self):
  tree=ast.parse(SOURCE.read_text());call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='execute' and any(k.arg=='scope' for k in n.keywords))
  for scope in ('all','composition','application','flash-status','journal','time-jobs','network','sessions','bond-revocation'):
   env=dict(a=type('Args',(),{'scope':scope})(),accelerated='accelerated',journal='journal',flash_status='flash',revoke='bond')
   selected={k.arg:eval(compile(ast.Expression(k.value),'private','eval'),env) for k in call.keywords if k.arg in ('accelerated','journal','flash_status','bond_revocation','scope')}
   self.assertEqual(selected['scope'],scope)
   self.assertEqual(selected['accelerated'] is not None,scope in ('all','time-jobs','network','sessions'))
   self.assertEqual(selected['journal'] is not None,scope in ('all','journal'))
   self.assertEqual(selected['flash_status'] is not None,scope in ('all','flash-status'))
   self.assertEqual(selected['bond_revocation'] is not None,scope in ('all','bond-revocation'))
 def test_actual_application_callback_routes_common_preparation_to_tls_idle_only(self):
  tree=ast.parse(SOURCE.read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='cases')
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);calls=[];collections=[]
   class Remote:
    backend=SimpleNamespace(remote='/private/no-access')
    def stage(self,path,name):return 'hash'
    def fixture(self,*a,**kw):raise AssertionError('application dispatch owns finite warm prerequisite')
    def invoke(self,name,payload,**kw):calls.append((name,payload,kw));return dict(status='application')
    def collect(self,names):collections.extend(names)
   env=dict(remote=Remote(),a=SimpleNamespace(scope='application',skip_accepted_time_cases=False,
     preparation_manifest=root/'manifest',credential_root=root),Path=Path,__file__=str(SOURCE),
     subprocess=SimpleNamespace(run=lambda *a,**kw:None),private_write=lambda *a:None,
     counter=lambda x,*a:int(x),sha=lambda x:'a'*64,preparation={'source_commit':'b'*40},
     AUTHORITY='authorized',server_sha256='c'*64)
   env.update(COMMON_HELPERS=COMMON_HELPERS,COMMON_REPOSITORY_ASSETS=COMMON_REPOSITORY_ASSETS,CREDENTIAL_ASSETS=CREDENTIAL_ASSETS)
   exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'actual-cases','exec'),env)
   result=env['cases'](dict(root=root,info=dict(status={'boot_id':'d'*32},provisioning_generation='7'),
     profile_path=root/'profile',engineering=dict(uf2={'sha256':'e'*64}),ble_address='required-only-by-preparation'))
   self.assertEqual(result,dict(status='application'));self.assertEqual(len(calls),1)
   name,payload,kw=calls[0];self.assertEqual(name,'phase12_engineering_dispatch.py')
   self.assertEqual(payload['scope'],'application');self.assertTrue(payload['skip_accepted_time_cases'])
   self.assertEqual(kw,dict(timeout=450,keepalive=True))
   self.assertIn('application-idle-wire.jsonl',collections);self.assertIn('application-cold-result.json',collections)
 def test_actual_accelerated_named_branches_select_only_requested(self):
  tree=ast.parse(SOURCE.read_text());f=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='accelerated')
  branches=[n for n in f.body if isinstance(n,ast.If) and 'a.scope' in ast.unparse(n.test)]
  for scope in ('all','time-jobs','network','sessions'):
   matched=[]
   for branch in branches:
    if eval(compile(ast.Expression(branch.test),'private','eval'),{'a':type('Args',(),{'scope':scope})()}):matched.append(ast.unparse(branch.test))
   self.assertEqual(len(matched),3 if scope=='all' else 2 if scope=='network' else 1)
class PrerequisiteTests(unittest.TestCase):
 def test_real_exclusive_receipts_preserve_repeated_readiness_observations(self):
  tree=ast.parse(SOURCE.read_text());callback=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='cases')
  for scope in ('time-jobs','flash-status','journal','network','sessions'):
   with self.subTest(scope=scope),tempfile.TemporaryDirectory() as d:
    root=Path(d);count=[0];now=[0];actions=[]
    base=dict(status={'boot_id':'b','clock_state':'synchronized'},provisioning_source='provisioned',provisioning_generation=2)
    class Backend:
     remote='/private/campaign'
     def info(self):
      count[0]+=1
      return dict(base,network={'link_status':3 if count[0]==3 else 1,'ipv4':'192.168.84.2','accepted':1})
    class Remote:
     backend=Backend()
     def fixture(self,action,args):actions.append(action)
     def stage(self,path,name):return 'hash'
    def require(ok,msg):
     if not ok:raise ValueError(msg)
    env=dict(__file__=str(SOURCE),Path=Path,a=SimpleNamespace(scope=scope,preparation_manifest=Path('unused'),credential_root=Path('unused')),
     time=SimpleNamespace(monotonic=lambda:now[0],sleep=lambda s:now.__setitem__(0,now[0]+s)),remote=Remote(),
     subprocess=SimpleNamespace(run=lambda *a,**kw:None),private_write=private_write,safe_info=lambda *a:None,
     preparation={'source_commit':'a'*40},require=require,counter=lambda x,*a:int(x))
    env.update(COMMON_HELPERS=COMMON_HELPERS,COMMON_REPOSITORY_ASSETS=COMMON_REPOSITORY_ASSETS,CREDENTIAL_ASSETS=CREDENTIAL_ASSETS)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[callback],type_ignores=[])),'actual-cases','exec'),env)
    result=env['cases']({'backend':env['remote'].backend,'root':root,'info':base})
    self.assertEqual(result,dict(status='COMMON_INPUTS_STAGED',scope=scope))
    files=sorted(root.glob('isolated-warm-info-*.json'));self.assertEqual(len(files),3)
    self.assertEqual([json.loads(p.read_text())['network']['link_status'] for p in files],[1,1,3])
    self.assertEqual(actions,['bind_peer'] if scope=='time-jobs' else ['bind_peer','sntp_on'])
    original=files[0].read_bytes()
    with self.assertRaises(FileExistsError):private_write(files[0],{'replacement':True})
    self.assertEqual(files[0].read_bytes(),original)
 def test_actual_isolated_peer_binding_and_time_enable_selection(self):
  tree=ast.parse(SOURCE.read_text());cases=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='cases');outer=next(n for n in cases.body if isinstance(n,ast.If));warm=outer.body[0]
  for scope,mode in ((s,m) for s in ('time-jobs','flash-status','journal','network','sessions') for m in ('good','generation','source','late')):
   calls=[];now=[0]
   info=dict(status={'boot_id':'b','clock_state':'synchronized'},provisioning_source='provisioned',provisioning_generation=2,network={'link_status':3,'ipv4':'192.168.84.2','accepted':1})
   class Remote:
    def fixture(self,action,args):calls.append(action)
   class Backend:
    def info(self):
     now[0]=181 if mode=='late' else 0
     return dict(info,provisioning_generation=3 if mode=='generation' else 2,provisioning_source='consumer_preclock' if mode=='source' else 'provisioned')
   def require(ok,msg):
    if not ok:raise ValueError(msg)
   env=dict(a=type('Args',(),{'scope':scope})(),time=type('Clock',(),{'monotonic':staticmethod(lambda:now[0]),'sleep':staticmethod(lambda x:None)}),context={'backend':Backend(),'root':Path('/private/test'),'info':info},remote=Remote(),private_write=lambda *a:None,safe_info=lambda *a:None,preparation={'source_commit':'a'*40},require=require,counter=lambda x,*a:int(x))
   code=compile(ast.fix_missing_locations(ast.Module(body=[warm],type_ignores=[])),'private','exec')
   if mode=='good':
    exec(code,env);self.assertEqual(calls,['bind_peer'] if scope=='time-jobs' else ['bind_peer','sntp_on'])
   else:
    with self.assertRaises(ValueError):exec(code,env)
    self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
