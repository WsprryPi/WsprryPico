"""Validate current production selector documents against the shipped schemas."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parents[1]
documents = list(map(json.loads, subprocess.check_output([sys.argv[1], '--documents'], text=True).splitlines()))
names = ['transmitter-filter-selector-capabilities.schema.json', 'transmitter-filter-selector-resource-1.schema.json', 'transmitter-filter-selector-1.schema.json', 'transmitter-filter-selector-resource-1.schema.json']
for document, name in zip(documents, names, strict=True):
    schema = json.loads((root / 'engineering/protocol' / name).read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(document)
    assert list(validator.iter_errors({**document, 'extra': 0}))
    for key in document:
        bad = copy.deepcopy(document)
        del bad[key]
        assert list(validator.iter_errors(bad)), key
    assert list(validator.iter_errors({**document, 'schema': 'transmitter-filter-selector/2'}))
print('Current production selector capability, readback, request and saved response schemas passed')
