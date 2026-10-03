import ast, pathlib, unittest
P=pathlib.Path(__file__).resolve().parents[1]/'scripts/phase12_populated_dispatch.py'
class Tests(unittest.TestCase):
 def test_actual_station_branch_restarts_once_between_start_and_submit(self):
  tree=ast.parse(P.read_text());branch=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=="kind == 'station'" and any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='restart_trial_ap' for b in n.body for x in ast.walk(b)))
  calls=[]
  def exchange(method,path,body):
   calls.append(path)
   return {'boot_id':'b','generation':6,'state':'checking'}
  values=dict(kind='station',generation=6,boot='b',keys=lambda g:({},None),exchange=exchange,counter=lambda v,n:v,require=lambda ok,msg:self.assertTrue(ok,msg),restart_trial_ap=lambda kind:calls.append('restart:'+kind),seal=lambda *args:{},request={'station':{}})
  exec(compile(ast.fix_missing_locations(ast.Module(body=branch.body,type_ignores=[])),str(P),'exec'),values)
  self.assertEqual(calls,['/api/owner/v1/claim/start','restart:station','/api/owner/v1/claim/submit'])
 def test_actual_helper_one_restart_rejects_time_enabled_and_uncertainty(self):
  tree=ast.parse(P.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='restart_trial_carrier')
  def require(ok,msg):
   if not ok:raise ValueError(msg)
  namespace={'require':require};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(P),'exec'),namespace)
  class Evidence:
   def record(self,*a,**k):pass
  for kind in ('station','network'):
   for state in ('ok','time','uncertain'):
    calls=[]
    def invoke(request):
     calls.append(request)
     if state=='uncertain':raise TimeoutError('uncertain')
     return dict(status='OWNED_AP_RESTARTED_NO_SNTP',ntp_started=state=='time')
    if state=='ok':namespace['restart_trial_carrier']('/private/root','authority',kind,Evidence(),invoke=invoke)
    else:
     with self.assertRaises((ValueError,TimeoutError)):namespace['restart_trial_carrier']('/private/root','authority',kind,Evidence(),invoke=invoke)
    self.assertEqual(len(calls),1)

class ResponderTests(unittest.TestCase):
 def test_original_disabled_identity_and_refusals(self):
  import tempfile,json,hashlib
  f=P.parent/'phase12_engineering_fixture.py';tree=ast.parse(f.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify_disabled_ntp')
  def require(ok,msg):
   if not ok:raise ValueError(msg)
  ns=dict(Path=pathlib.Path,__file__=str(f),SERVER_DURATION_S=18000,ADDRESS='192.168.84.1',require=require,strict=lambda b:json.loads(b),hashlib=hashlib,private_write=lambda p,v:p.write_text(json.dumps(v)))
  exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),str(f),'exec'),ns)
  for fault in (None,'enabled','dead','foreign','roles','changed'):
   with self.subTest(fault=fault),tempfile.TemporaryDirectory() as d:
    root=pathlib.Path(d);proc=root/'proc';(proc/'42').mkdir(parents=True)
    pid=dict(pid=42,root=str(root),duration_s=18000,startup_token='token',roles_sha256='role');ready=dict(pid=42,startup_token='token',enabled=False,address='192.168.84.1',port=123,roles_sha256='role')
    for name,value in [('ntp-pid.json',pid),('ntp-ready.json',ready)]: (root/name).write_text(json.dumps(value))
    cmd=proc/'42'/'cmdline';cmd.write_bytes(b'python\0'+str(f.resolve()).encode()+b'\0--serve-ntp\0'+str(root).encode()+b'\0token\0')
    ns['verify_disabled_ntp'](root,{'sha256':'role'},process_root=proc)
    if fault=='enabled':(root/'ntp-enabled.json').write_text('{}')
    if fault=='dead':cmd.unlink()
    if fault=='foreign':cmd.write_bytes(b'foreign\0')
    if fault=='roles':ready['roles_sha256']='other';(root/'ntp-ready.json').write_text(json.dumps(ready))
    if fault=='changed':pid['startup_token']='other';(root/'ntp-pid.json').write_text(json.dumps(pid))
    if fault:
     with self.assertRaises((ValueError,FileNotFoundError)):ns['verify_disabled_ntp'](root,{'sha256':'role'},process_root=proc)
    else:ns['verify_disabled_ntp'](root,{'sha256':'role'},process_root=proc)

if __name__=='__main__':unittest.main()
