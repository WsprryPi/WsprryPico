#!/usr/bin/env python3
"""Real legacy Pi producer -> actual Pico handler/journal; hardware-free."""
import json
import pathlib
import subprocess
import sys

driver, node = sys.argv[1:]
root = pathlib.Path(__file__).resolve().parent
context = subprocess.check_output([driver, '--pi-context'], text=True)
captured = subprocess.check_output([node, str(root / 'legacy_pi_config_request.js')],
                                   input=context, text=True)
request = json.loads(captured)
assert request['method'] == 'PUT' and request['path'] == '/api/v1/config'
assert request['body']['station']['callsign'] == 'K1ABC'
assert request['body']['wifi']['password'] is None
for extension in ('pins', 'allow_unqualified_frequency', 'allow_non_amateur_frequency'):
    assert extension not in request['body'], extension
result = json.loads(subprocess.check_output([driver, '--request'], input=captured, text=True))
assert result['status'] == 200 and result['extensions_preserved']
assert result['body']['config']['station']['callsign'] == 'K1ABC'
assert result['body']['config']['wifi']['password'] is None
print('Actual legacy Pi Save request preserved Pico extensions, password and journal cursor')
