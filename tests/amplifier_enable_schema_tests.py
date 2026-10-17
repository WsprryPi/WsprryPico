"""Validate negotiated closed views and legacy refusal against actual API output."""
import copy
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_wtp_contract import SchemaValidator, loads_strict

protocol = ROOT / 'docs/protocol'
def schema(name):
    return json.loads((protocol / (name + '.schema.json')).read_text())

drive = schema('transmitter-gpio-drive-1')
class Validator(SchemaValidator):
    def resolve(self, ref):
        if ref == 'transmitter-gpio-drive-1.schema.json#/$defs/read':
            return drive['$defs']['read']
        return super().resolve(ref)

application = schema('transmitter-application-4')
progress = schema('transmitter-progress-3')
descriptor = schema('transmitter-amplifier-enable-1')
update = schema('transmitter-config-update-3')
schemas = {'transmitter-application/4': application, 'transmitter-hardware/3': application,
           'transmitter-progress/3': progress, 'transmitter-amplifier-enable/1': descriptor}
result = subprocess.run([sys.argv[1], '--samples'], check=True, text=True, capture_output=True)
samples = [loads_strict(line) for line in result.stdout.splitlines()]
assert len(samples) == 5
for value in samples:
    s = schemas[value['schema']]
    assert not Validator(s).errors(value, s), (value['schema'], Validator(s).errors(value, s))
    extra = copy.deepcopy(value)
    extra['unknown'] = True
    assert Validator(s).errors(extra, s)
hardware = samples[1]
pins = hardware['saved']
assert pins['amplifier_gp'] == 18 and pins['amplifier_active_high'] is False
assert hardware['active']['amplifier_gp'] is None
target = hardware['target']
assert samples[3]['capabilities']['management_carrier'] == 'usb_physical'
for high in (True, False):
    plan = {**pins, 'amplifier_active_high': high}
    request = {'schema': 'transmitter-config-update/3', 'target': target, 'mode': 'merge',
               'config': {'pins': plan}}
    assert not Validator(update).errors(request, update)
    type3 = copy.deepcopy(request)
    type3['config']['station'] = {'callsign': '<K1ABC>', 'locator': 'FN42AB', 'power_dbm': 10}
    assert not Validator(update).errors(type3, update)
    for bad in (None, 0, 1, 'true', [], {}):
        malformed = copy.deepcopy(request)
        malformed['config']['pins']['amplifier_active_high'] = bad
        assert Validator(update).errors(malformed, update), bad
    for old in ('transmitter-config-update-1', 'transmitter-config-update-2'):
        legacy = schema(old)
        incompatible = copy.deepcopy(request)
        incompatible['schema'] = 'transmitter-config-update/' + old[-1]
        assert Validator(legacy).errors(incompatible, legacy)
for old in ('transmitter-application-1', 'transmitter-application-2', 'transmitter-application-3'):
    legacy = schema(old)
    incompatible = copy.deepcopy(hardware)
    incompatible['schema'] = legacy['$defs']['hardware_read']['properties']['schema']['const']
    if old != 'transmitter-application-3':
        incompatible.pop('gpio_drive')
    assert Validator(legacy).errors(incompatible, legacy)
print('Amplifier negotiated service views, closed schemas, polarity and legacy rejection passed')
