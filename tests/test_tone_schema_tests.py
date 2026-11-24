"""Validate actual Test Tone producer documents and closed negative cases."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parents[1]
schema = json.loads((root / 'engineering/protocol/control-1.schema.json').read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema)
with tempfile.TemporaryDirectory(prefix='pico-tone-schema-') as directory:
    output = Path(directory) / 'documents.json'
    subprocess.run([sys.argv[1], str(output)], check=True)
    documents = json.loads(output.read_text())
for document in documents:
    validator.validate(document)
    for changed in ({**document, 'extra': True}, {**document, 'contract': 'Wsprry-Control/2'}):
        assert not validator.is_valid(changed)
capabilities = documents[0]
for key, value in [('maximum_duration_ms', 120001), ('duration_units', 'seconds'),
                   ('drive_ma', [2, 4, 6, 8]), ('output_disable_timeout_ns', 100000000),
                   ('start', '/api/control/v1/jobs')]:
    changed = copy.deepcopy(capabilities)
    changed['test_tone'][key] = value
    assert not validator.is_valid(changed)
job = documents[2]
for key, value in [('carrier_hz', 5366200.5), ('duration_ms', 120001),
                   ('boot_drive_ma', 6), ('phase', 'idle'), ('scheduled_utc_ns', 1)]:
    changed = copy.deepcopy(job)
    changed['job'][key] = value
    assert not validator.is_valid(changed)
assert not any('test-tone' in value for value in schema['public_resources'])
assert not any('test-tone' in value for names in schema['controller_adapter']['pico_routes'].values() for value in names)
print('PASS current Test Tone schema, descriptors, and authority boundaries')
