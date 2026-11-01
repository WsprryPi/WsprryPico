"""Validate actual Si5351 producer output and independent malformed documents."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parents[1]
schema = json.loads((root / 'engineering/protocol/control-1.schema.json').read_text())
validator = Draft202012Validator({'$defs': schema['$defs'], '$ref': '#/$defs/si5351'})
value = json.loads(subprocess.check_output([sys.argv[1], '--samples'], text=True))
validator.validate(value)
assert value['physically_qualified'] is False
assert value['runtime']['reference_measurement']['local_rate_ppb'] is None
for change in (
    lambda v: v.update(contract='Wsprry-Control/2'),
    lambda v: v.update(extra=True),
    lambda v: v['saved'].update(address=97),
    lambda v: v['saved'].update(reference_hz='25000000'),
    lambda v: v['saved'].update(loopback_output=0),
    lambda v: v['saved'].update(loopback_output=None),
    lambda v: v['saved'].update(crystal_load_pf=8),
    lambda v: v['saved'].update(automatic_calibration=True),
    lambda v: v['runtime'].update(unknown=False),
    lambda v: v['runtime'].update(clock_reference_state='gps'),
    lambda v: v['runtime']['reference_measurement'].update(duration_ns=10_000_000_000),
    lambda v: v['runtime']['reference_measurement'].update(ratio_error_ppb='nan'),
    lambda v: v['runtime']['reference_measurement'].update(uncertainty_ppb=-1),
):
    bad = copy.deepcopy(value)
    change(bad)
    assert not validator.is_valid(bad), bad
print('Actual Si5351 readback passes the current closed schema; malformed units/types/versions refused')
