"""One current update schema against the production parser and negative requests."""
import copy
import json
import subprocess
import sys
from control_schema_support import Validator
check=Validator('config-update')
base={'contract':'Wsprry-Control/1','schema':'config-update','target':{'scope':'member','device_id':'a'*32,'boot_id':'0'*31+'1'},'mode':'merge','config':{'allow_unqualified_frequency':False}}
cases=[('explicit_false',base,True,200),('explicit_zero',{**base,'config':{'expires_utc_s':0}},True,200)]
for name,patch in [('unknown_mode',{'mode':'replace'}),('unknown_type',{'schema':'unsupported'}),('unknown_contract',{'contract':'Wsprry-Control/2'}),('extra',{'extra':1}),('empty_patch',{'config':{}}),('storage_version',{'config':{'version':1}}),('wrong_boolean',{'config':{'enabled':1}})]:
    cases.append((name,{**base,**patch},False,400))
for name,request,valid,status in cases:
    assert check.is_valid(request)==valid,name
    result=subprocess.run([sys.argv[1],'--raw-update'],input=json.dumps(request,separators=(',',':')),text=True,capture_output=True,check=True)
    observed=json.loads(result.stdout)
    assert observed['status']==status,(name,observed)
raw=json.dumps(base,separators=(',',':')).replace('"contract":','"contract":"Wsprry-Control/1","contract":')
result=subprocess.run([sys.argv[1],'--raw-update'],input=raw,text=True,capture_output=True,check=True)
assert json.loads(result.stdout)['status']==400
print('PASS canonical update shape/parser agreement and duplicate refusal')
