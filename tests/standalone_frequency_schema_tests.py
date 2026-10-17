"""Check actual unset and saved resource responses against their public schema."""
import json
from pathlib import Path
import subprocess
import sys
from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parents[1]
schema = json.loads((root / 'docs/protocol/transmitter-standalone-frequency-1.schema.json').read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator({'$ref': '#/$defs/read', '$defs': schema['$defs']})
samples = json.loads(subprocess.check_output([sys.argv[1], '--samples'], text=True))
assert samples[0]['frequency_hz'] is None and samples[0]['configured'] is False
assert samples[1]['frequency_hz'] == 14097100 and samples[1]['configured'] is True
for sample in samples:
    validator.validate(sample)
print('Unset and saved frequency responses conform to resource version 1')
