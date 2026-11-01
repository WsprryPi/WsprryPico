"""Standards-compliant validation of actual current producer documents and malformed leaves."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'engineering/protocol/control-1.schema.json').read_text())
Draft202012Validator.check_schema(SCHEMA)
def documents(driver, *args):
    text = subprocess.check_output([driver, *args], text=True)
    values = []
    while text.strip():
        text = text.lstrip()
        value, end = json.JSONDecoder().raw_decode(text)
        values.append(value)
        text = text[end:]
    return values

def validator(family):
    return Draft202012Validator({'$defs': SCHEMA['$defs'], '$ref': '#/$defs/' + family})

def valid(family, value):
    validator(family).validate(value)

def invalid(family, value):
    assert not validator(family).is_valid(value), (family, value)

core = documents(sys.argv[1], '--samples')
for family, value in zip(['capabilities', 'config-read', 'status', 'management'], core, strict=True):
    valid(family, value)
    Draft202012Validator(SCHEMA).validate(value)
    invalid(family, {**value, 'unknown': True})
    invalid(family, {**value, 'contract': 'Wsprry-Control/2'})
caps, config, status, management = core
for path, bad in [(('gpio_drive', 'values'), [None]), (('amplifier_enable', 'default_pin'), {}), (('wtp', 'profiles'), [None]), (('wtp', 'frequency_ranges'), [{}]), (('message_jobs', 'modes'), [None])]:
    value = copy.deepcopy(caps)
    assert path[0] in value, 'Sample must exercise optional message capability'
    value[path[0]][path[1]] = bad
    invalid('capabilities', value)
value = copy.deepcopy(config); value['config']['wifi']['password'] = {}; invalid('config-read', value)
value = copy.deepcopy(config); value['config']['pins']['amplifier_gp'] = {}; invalid('config-read', value)
value = copy.deepcopy(config); value['config']['schedules'] = [None]; invalid('config-read', value)
value = copy.deepcopy(status); value['job']['terminal_records'] = [None]; invalid('status', value)
value = copy.deepcopy(status); value['transport'] = {}; invalid('status', value)
for rows in [[1], management['carriers'][:-1], [management['carriers'][0]] * 5, [*management['carriers'][:-1], {**management['carriers'][-1], 'carrier': 'future'}]]:
    invalid('management', {**management, 'carriers': rows})
valid('management', {**management, 'carriers': list(reversed(management['carriers']))})
value = copy.deepcopy(management); value['carriers'][0]['extra'] = True; invalid('management', value)

samples = documents(sys.argv[2], '--samples')[0]
for name, value in samples.items():
    valid('application', value)
for value in documents(sys.argv[3], '--samples'):
    valid({'application': 'application', 'hardware': 'application', 'progress': 'progress', 'amplifier-enable': 'amplifier-enable'}[value['schema']], value)
    if value['schema'] == 'progress':
        bad = copy.deepcopy(value); bad['wspr_plan'] = {}; invalid('progress', bad)
for family, value in zip(['filter-selector-capabilities', 'filter-selector-resource', 'filter-selector', 'filter-selector-resource'], documents(sys.argv[4], '--documents'), strict=True):
    valid(family, value)
for value in documents(sys.argv[5], '--samples')[0].values():
    valid('application', value)

# Inputs retain documented polarity omission; canonical readback makes it explicit.
hardware = samples['hardware']
pins = copy.deepcopy(hardware['saved'])
assert isinstance(pins, dict) and 'amplifier_active_high' in pins
pins.pop('amplifier_active_high')
valid('application', {'contract': 'Wsprry-Control/1', 'schema': 'hardware',
                      'target': hardware['target'], 'pins': pins})
valid('config-update', {'contract': 'Wsprry-Control/1', 'schema': 'config-update',
                        'target': hardware['target'], 'mode': 'merge', 'config': {'pins': pins}})
valid('progress', {'contract': 'Wsprry-Control/1', 'schema': 'progress',
                   'target': hardware['target'], 'request_id': '1' * 32, 'fields': {'pins': pins}})
for key in ['saved', 'active']:
    bad = copy.deepcopy(hardware); bad[key].pop('amplifier_active_high'); invalid('application', bad)
bad = copy.deepcopy(config); bad['config']['pins'].pop('amplifier_active_high'); invalid('config-read', bad)
for value in documents(sys.argv[3], '--samples'):
    if value.get('schema') == 'progress':
        bad = copy.deepcopy(value)
        bad['fields']['pins'] = copy.deepcopy(hardware['saved'])
        valid('progress', bad)
        bad['fields']['pins'].pop('amplifier_active_high')
        invalid('progress', bad)

# Imported WTP definitions are verbatim canonical definitions except reference relocation.
wtp = json.loads((ROOT / 'engineering/protocol/wtp-1.schema.json').read_text())['$defs']
def rebase(value):
    if isinstance(value, dict):
        return {key: ('#/$defs/wtp/$defs/' + item.split('/')[-1] if key == '$ref' else rebase(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [rebase(item) for item in value]
    return value
assert SCHEMA['$defs']['wtp']['$defs'] == rebase(wtp)
# No placeholder broad unions or unclosed application objects remain.
def inspect(value, path=()):
    if isinstance(value, dict):
        assert not isinstance(value.get('type'), list), path
        if value.get('type') == 'object' and '$defs' not in value:
            assert value.get('additionalProperties') is False or 'const' in value or path == ('capabilities', 'properties', 'features') or path[-1:] == ('contains',), path
        for key, item in value.items(): inspect(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value): inspect(item, path + (index,))
for name, definition in SCHEMA['$defs'].items():
    if name != 'wtp': inspect(definition, (name,))
print('PASS Draft 2020-12 actual producer documents, closed leaves, carrier sets, negative mutations, unchanged WTP definitions')
