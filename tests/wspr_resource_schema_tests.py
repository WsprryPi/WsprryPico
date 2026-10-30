"""Canonical application output includes current WSPR formats."""
import copy
import json
import sys
from control_schema_support import Validator, documents, closed, SCHEMA
check=Validator('application')
samples=documents(sys.argv[1],'--samples')[0]
for name,value in samples.items():
    closed(value,check)
    assert len(json.dumps(value,separators=(',',':')).encode())<=4096
    bad=copy.deepcopy(value)
    bad['wspr_plan']['frame_types']=['type99']
    assert check.errors(bad),name
print(f'PASS {len(samples)} current WSPR application snapshots')
