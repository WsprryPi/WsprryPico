"""Current GPS resource from production UART/PPS adapter and BrowserApi."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from jsonschema import Draft202012Validator
root=Path(__file__).resolve().parents[1]
schema=json.loads((root/'engineering/protocol/control-1.schema.json').read_text())
validator=Draft202012Validator({'$defs':schema['$defs'],'$ref':'#/$defs/gps'})
sample=json.loads(subprocess.check_output([sys.argv[1]],text=True))
validator.validate(sample)
for change in (
 lambda v:v.update(contract='Wsprry-Control/2'),
 lambda v:v.update(extra=True),
 lambda v:v['saved'].update(tx_gp=0),
 lambda v:v['saved'].update(rx_gp=2),
 lambda v:v['saved'].update(pps_gp=6),
 lambda v:v['saved'].update(receiver='unknown'),
 lambda v:v['saved'].update(automatic_rf_calibration='true'),
 lambda v:v['runtime'].update(extra=False),
 lambda v:v['runtime'].update(observation_raw_ns=2_000_000_000),
 lambda v:v['runtime'].pop('capture_error_bound_ns'),
 lambda v:v['runtime'].update(capture_rejections=-1),
 lambda v:v.update(boot_active=None),
 lambda v:v['boot_active'].update(enabled=False),
 lambda v:v['boot_active'].update(pairing_qualified=False),
 lambda v:v.update(storage_healthy=False),
 lambda v:v['runtime']['position'].update(locator='ZZ99AA'),
 lambda v:v['runtime'].update(timer_calibration={'oscillator_error_ppb':0,'uncertainty_ppb':100002,'observed_raw_ns':'1','age_ns':'0','span_ns':'10000000000','generation':'1','fresh':True}),
):
 bad=copy.deepcopy(sample);change(bad);assert not validator.is_valid(bad),bad
print('Actual GPS producer passes the closed current schema; malformed versions, settings, units and quality refused')
