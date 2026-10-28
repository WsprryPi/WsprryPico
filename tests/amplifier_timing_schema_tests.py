"""Validate production timing documents and reject closed-contract violations."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from jsonschema import Draft202012Validator
root = Path(__file__).resolve().parents[1]
cap, response, request, observation = map(json.loads, subprocess.check_output([sys.argv[1], '--timing-samples'], text=True).splitlines())
def validator(name):
    schema = json.loads((root / 'engineering/protocol' / name).read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)
descriptor = validator('transmitter-amplifier-timing-1.schema.json')
resource = validator('transmitter-amplifier-timing-resource-1.schema.json')
descriptor.validate(cap)
resource.validate(response)
resource.validate(request)
validator('amplifier-readback-1.schema.json').validate(observation)
for document, check in ((cap, descriptor), (response, resource), (request, resource)):
    for patch in ({'extra': 0}, {'schema': 'transmitter-amplifier-timing/2'}):
        assert list(check.iter_errors({**document, **patch}))
    for key in document:
        bad = copy.deepcopy(document)
        del bad[key]
        assert list(check.iter_errors(bad)), key
for value in (-1, 0.5, 1001, True, None, '200', {}, []):
    bad = copy.deepcopy(request)
    bad['timing']['lead_ms'] = value
    assert list(resource.iter_errors(bad)), value
for phase in ('lead', 'rf', 'tail'):
    bad = {**response, 'phase': phase, 'output_active': False}
    assert list(resource.iter_errors(bad))
print('Production amplifier timing descriptor/resource and closed negative shapes passed')
