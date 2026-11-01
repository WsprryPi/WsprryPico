"""Canonical application schemas versus configured/blank/pending/fault responses."""
import json
import sys
from control_schema_support import Validator, documents, closed
samples=documents(sys.argv[1],'--samples')[0]
for name,value in samples.items():
    closed(value,Validator('application'))
    assert len(json.dumps(value,separators=(',',':')).encode())<=4096,name
assert samples['blank']['hardware']['active'] is None
assert samples['unhealthy']['station']['station'] is None
assert samples['unhealthy']['hardware']['saved'] is None
assert samples['pending']['pending_restart'] is True
assert samples['pending']['active']['rf_gp']==2
assert samples['pending']['saved']['rf_gp']==28
fault=documents(sys.argv[1],'--fault')[0]
closed(fault,Validator('application'))
assert fault['application_error']=='output_disable_failed' and fault['pending_restart'] is True
print('PASS canonical configured/blank/pending/unhealthy and cleanup-fault resources')
