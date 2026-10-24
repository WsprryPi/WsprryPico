"""Check actual unset and saved resource responses against their public schema."""
import json
from pathlib import Path
import subprocess
import sys
from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parents[1]
schema = json.loads((root / 'engineering/protocol/transmitter-standalone-frequency-1.schema.json').read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator({'$ref': '#/$defs/read', '$defs': schema['$defs']})
samples = json.loads(subprocess.check_output([sys.argv[1], '--samples'], text=True))
assert samples[0]['frequency_hz'] is None and samples[0]['configured'] is False
assert samples[1]['frequency_hz'] == 14095600 and samples[1]['configured'] is True
for sample in samples:
    validator.validate(sample)
print('Unset and saved frequency responses conform to resource version 1')

write = Draft202012Validator({'$ref':'#/$defs/write','$defs':schema['$defs']})
base = {k:samples[1][k] for k in ('schema','target','frequency_hz')}
for value in (98503, 74998496, 14095600.0):
    write.validate(dict(base,frequency_hz=value))
for value in (0,98502,74998497,14095600.5,'14095600','14.0956MHz',True):
    assert not write.is_valid(dict(base,frequency_hz=value)), value
print('Schema integer-domain bounds checked independently of strict lexical parsing')
