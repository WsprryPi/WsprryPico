"""Current drive documents and independent pad-current boundaries."""
import sys
from control_schema_support import Validator, documents, closed
samples=documents(sys.argv[1],'--samples')
for value in samples:
    family={'application':'application','progress':'progress','gpio-drive':'gpio-drive'}[value['schema']]
    closed(value,Validator(family))
check=Validator('gpio-drive')
base={'contract':'Wsprry-Control/1','schema':'gpio-drive','target':{'scope':'member','device_id':'a'*32,'boot_id':'b'*32}}
for ma in (2,4,8,12):check.validate({**base,'gpio_drive_ma':ma})
for ma in (0,1,3,5,16,-1,True,None,'4',[],{}):assert check.errors({**base,'gpio_drive_ma':ma}),ma
print('PASS current drive snapshots and current limits')

# Validate real station-free GET settings independently of station-write inputs.
import copy
from control_schema_support import SCHEMA
read = SCHEMA['$defs']['config-update']['$defs']['read']
check = Validator('config-update')
for sample in documents(sys.argv[1], '--station-free-samples'):
    assert not check.errors(sample, read), check.errors(sample, read)
    assert sample['config']['station']['callsign'] == ''
    for field, value in [('callsign','AA0NT'),('locator','EM18'),('power_dbm',1)]:
        bad=copy.deepcopy(sample); bad['config']['station'][field]=value
        assert check.errors(bad, read)
    bad=copy.deepcopy(sample); bad['config']['enabled']=True
    assert check.errors(bad, read)
    bad=copy.deepcopy(sample); bad['config']['extra']=False
    assert check.errors(bad, read)
print('PASS station-free saved settings are closed, typed, and WSPR-disabled')
