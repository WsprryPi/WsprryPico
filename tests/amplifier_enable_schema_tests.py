"""Current amplifier-aware application, hardware, progress and update schemas."""
import copy
import sys
from control_schema_support import Validator, documents, closed
samples=documents(sys.argv[1],'--samples')
assert len(samples)==5
for value in samples:
    family={'application':'application','hardware':'application','progress':'progress','amplifier-enable':'amplifier-enable'}[value['schema']]
    closed(value,Validator(family))
hardware=samples[1]
assert hardware['saved']['amplifier_gp']==18
assert hardware['saved']['amplifier_active_high'] is False
assert hardware['active']['amplifier_gp'] is None
check=Validator('config-update')
for polarity in (True,False):
    request={'contract':'Wsprry-Control/1','schema':'config-update','target':hardware['target'],'mode':'merge','config':{'pins':{**hardware['saved'],'amplifier_active_high':polarity}}}
    check.validate(request)
    for bad in (None,0,1,'true',[],{}):
        malformed=copy.deepcopy(request)
        malformed['config']['pins']['amplifier_active_high']=bad
        assert check.errors(malformed),bad
    assert check.errors({**request,'mode':'replace'})
print('PASS current amplifier-aware documents and strict polarity/update contract')
