"""Canonical saved progress read/ack structural checks."""
import json
import sys
from control_schema_support import Validator, closed
check=Validator('progress')
samples=json.load(sys.stdin)
for index,value in enumerate(samples):
    try:
        closed(value,check)
    except AssertionError as error:
        raise AssertionError((index, {kind:check.errors(value,rule) for kind,rule in
                              check.definition['$defs'].items() if kind in ('read','ack')})) from error
    assert check.errors({**value,'last_outcomes':{'callsign':'applied'}})
print(f'PASS {len(samples)} current progress samples')
