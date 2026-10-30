"""Validate real portable timeout readbacks and closed write envelopes."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_wtp_contract import SchemaValidator

schema = json.loads((ROOT / 'engineering/protocol/transmitter-ntp-timeout-1.schema.json').read_text())
validator = SchemaValidator(schema)
schema2 = json.loads((ROOT / 'engineering/protocol/transmitter-ntp-timeout-2.schema.json').read_text())
validator2 = SchemaValidator(schema2)
for line in subprocess.check_output([sys.argv[1], '--emit'], text=True).splitlines():
    value = json.loads(line)
    selected, selected_schema = (validator2, schema2) if value['schema']=='transmitter-ntp-timeout/2' else (validator, schema)
    assert not selected.errors(value, selected_schema), selected.errors(value, selected_schema)
target = {'scope': 'member', 'device_id': 'a' * 32, 'boot_id': 'b' * 32}
for seconds in [60, 900, 3600, 86400]:
    assert not validator.errors({'schema': 'transmitter-ntp-timeout/1', 'target': target, 'timeout_s': seconds}, schema)
for seconds in [0, 59, 61, 86401, -60, True, None, '3600']:
    assert validator.errors({'schema': 'transmitter-ntp-timeout/1', 'target': target, 'timeout_s': seconds}, schema)
assert validator.errors({'schema': 'transmitter-ntp-timeout/1', 'target': target, 'timeout_s': 3600, 'extra': 1}, schema)
print('Real timeout readbacks and closed whole-minute envelopes satisfy schema v1.')

for seconds in [0, 60, 900, 3600, 86400]:
    assert not validator2.errors({'schema':'transmitter-ntp-timeout/2','target':target,'timeout_s':seconds}, schema2)
for seconds in [-60, 59, 61, 86401, True, None, '0']:
    assert validator2.errors({'schema':'transmitter-ntp-timeout/2','target':target,'timeout_s':seconds}, schema2)
for patch in [{'schema':'transmitter-ntp-timeout/1'}, {'schema':'transmitter-ntp-timeout/3'}, {'extra':1}, {'target':{'scope':'member'}}]:
    assert validator2.errors({'schema':'transmitter-ntp-timeout/2','target':target,'timeout_s':0,**patch},schema2)
print('Version 2 permits zero; historical version 1 and both closed envelope shapes remain strict.')
