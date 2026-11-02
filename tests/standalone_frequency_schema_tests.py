"""Current frequency schema and independent whole-Hz limits."""
import sys
from control_schema_support import Validator, documents, closed
check=Validator('standalone-frequency')
samples=documents(sys.argv[1],'--samples')[0]
assert samples[0]['frequency_hz'] is None and samples[0]['configured'] is False
assert samples[1]['frequency_hz']==14095600 and samples[1]['configured'] is True
for value in samples:closed(value,check)
base={k:samples[1][k]for k in ('schema','target','frequency_hz')}
for value in (6503,98503,74998496,144489000,159998496,14095600):check.validate({**base,'frequency_hz':value})
for value in (0,6502,159998497,14095600.5,'14095600','14.0956MHz',True):
    assert check.errors({**base,'frequency_hz':value}),value
print('PASS unset/saved frequency and independent whole-Hz bounds')
