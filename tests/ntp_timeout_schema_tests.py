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
for line in subprocess.check_output([sys.argv[1], '--emit'], text=True).splitlines():
    value = json.loads(line)
    assert not validator.errors(value, schema), validator.errors(value, schema)
target = {'scope': 'member', 'device_id': 'a' * 32, 'boot_id': 'b' * 32}
for seconds in [60, 900, 3600, 86400]:
    assert not validator.errors({'schema': 'transmitter-ntp-timeout/1', 'target': target, 'timeout_s': seconds}, schema)
for seconds in [0, 59, 61, 86401, -60, True, None, '3600']:
    assert validator.errors({'schema': 'transmitter-ntp-timeout/1', 'target': target, 'timeout_s': seconds}, schema)
assert validator.errors({'schema': 'transmitter-ntp-timeout/1', 'target': target, 'timeout_s': 3600, 'extra': 1}, schema)
print('Real timeout readbacks and closed whole-minute envelopes satisfy schema v1.')
