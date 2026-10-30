"""One current timeout schema includes explicit unlimited zero."""
import sys
from control_schema_support import Validator, documents, closed
check=Validator('ntp-timeout')
for value in documents(sys.argv[1],'--emit'):closed(value,check)
base={'contract':'Wsprry-Control/1','schema':'ntp-timeout','target':{'scope':'member','device_id':'a'*32,'boot_id':'b'*32},'timeout_s':0}
for seconds in (0,60,900,3600,86400):check.validate({**base,'timeout_s':seconds})
for seconds in (-60,59,61,86401,True,None,'0'):
    assert check.errors({**base,'timeout_s':seconds}),seconds
for patch in ({'schema':'unsupported'},{'unknown':1},{'target':{'scope':'member'}}):
    assert check.errors({**base,**patch})
print('PASS current timeout schema, zero and whole-minute boundaries')
