"""Current timing schema: production documents and independent boundary cases."""
import copy
import sys
from control_schema_support import Validator, documents, closed
cap, response, request, observation = documents(sys.argv[1], '--timing-samples')
checks = [Validator('amplifier-timing'), Validator('amplifier-timing-resource'), Validator('amplifier-timing-resource'), Validator('amplifier-readback')]
for value, check in zip((cap,response,request,observation), checks, strict=True):
    closed(value, check)
for field in ('lead_ms', 'tail_ms'):
    for value in (-1, 0.5, 1001, True, None, '200', {}, []):
        bad = copy.deepcopy(request)
        bad['timing'][field] = value
        assert checks[2].errors(bad), (field, value)
for phase in ('lead', 'rf', 'tail'):
    assert checks[1].errors({**response, 'phase':phase, 'output_active':False})
print('PASS current amplifier timing documents and bounds')
