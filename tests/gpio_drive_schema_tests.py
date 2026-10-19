"""Closed negotiated schemas checked against real portable service readback."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_wtp_contract import SchemaValidator, ValidationError, loads_strict

protocol = ROOT / 'engineering/protocol'
drive = json.loads((protocol / 'transmitter-gpio-drive-1.schema.json').read_text())
class Validator(SchemaValidator):
    def resolve(self, ref):
        if ref == 'transmitter-gpio-drive-1.schema.json#/$defs/read':
            return drive['$defs']['read']
        return super().resolve(ref)

schemas = {'transmitter-gpio-drive/1': drive}
for name, filename in [('transmitter-application/3','transmitter-application-3.schema.json'),
                       ('transmitter-progress/2','transmitter-progress-2.schema.json')]:
    schemas[name] = json.loads((protocol / filename).read_text())
result = subprocess.run([sys.argv[1], '--samples'], check=True, text=True, capture_output=True)
count = 0
for line in result.stdout.splitlines():
    value = loads_strict(line)
    errors = Validator(schemas[value['schema']]).errors(value, schemas[value['schema']])
    assert not errors, (value['schema'], errors)
    count += 1
vector = json.loads((protocol / 'transmitter-gpio-drive-1-vectors.json').read_text())
target = {'scope':'member','device_id':'a'*32,'boot_id':'b'*32}
validator = Validator(drive)
for value in vector['valid']:
    assert not validator.errors({'schema':'transmitter-gpio-drive/1','target':target,'gpio_drive_ma':value}, drive)
for value in vector['invalid']:
    assert validator.errors({'schema':'transmitter-gpio-drive/1','target':target,'gpio_drive_ma':value}, drive)
for raw in vector['invalid_raw']:
    try:
        value = loads_strict(raw)
    except (ValidationError, json.JSONDecodeError):
        continue
    assert validator.errors({'schema':'transmitter-gpio-drive/1','target':target,'gpio_drive_ma':value}, drive)
update = json.loads((protocol / 'transmitter-config-update-2.schema.json').read_text())
update_validator = Validator(update)
inherited = json.loads((protocol / 'transmitter-config-update-1-vectors.json').read_text())
for item in inherited['vectors']:
    raw = item['raw'].replace('transmitter-config-update/1', 'transmitter-config-update/2')
    if item['name'] == 'unsupported_schema':
        raw = raw.replace('transmitter-config-update/2', 'transmitter-config-update/99')
    try:
        value = loads_strict(raw)
        accepted = len(raw.encode()) <= 2048 and not update_validator.errors(value, update)
    except (ValidationError, json.JSONDecodeError):
        accepted = False
    assert accepted == item['structural_valid'], item['name']
    if accepted:
        for ma in (2, 4, 8, 12):
            extended = json.loads(json.dumps(value))
            extended['config']['gpio_drive_ma'] = ma
            assert not update_validator.errors(extended, update), (item['name'], ma)
for ma in vector['invalid']:
    request = {'schema':'transmitter-config-update/2','target':target,'mode':'merge','config':{'gpio_drive_ma':ma}}
    assert update_validator.errors(request, update), ma
print(f'GPIO drive schemas: {count} actual service responses, legal/invalid vectors and inherited closed update/2 envelopes passed')
