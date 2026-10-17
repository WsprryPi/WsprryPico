#!/usr/bin/env python3
"""Validate actual progress responses using the repository's bounded evaluator."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_wtp_contract import SchemaValidator
schema = json.loads((ROOT / 'docs/protocol/transmitter-progress-1.schema.json').read_text())
validator = SchemaValidator(schema)
samples = json.load(sys.stdin)
checks = 0
for value in samples:
    errors = validator.errors(value,schema)
    assert not errors, errors
    checks += 1
    for patch in ({'schema': 'transmitter-progress/2'}, {'extra': True}, {'last_outcomes': {'callsign': 'applied'}}):
        assert validator.errors({**value, **patch},schema)
        checks += 1
print(f'PASS progress structural schema versus production read/ack samples: {checks} checks')
