"""Canonical saved progress read/ack structural checks."""
import json
import sys
from control_schema_support import Validator, closed
check=Validator('progress')
samples=json.load(sys.stdin)
for value in samples:
    closed(value,check)
    assert check.errors({**value,'last_outcomes':{'callsign':'applied'}})
print(f'PASS {len(samples)} current progress samples')
