#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check simulator resolution, causal prefixes, truth scores and source bias."""
import hashlib
import json
from pathlib import Path
import sys

from compare_chrony49_loop import events, run

if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')
reference, engine, capture, quarter, output = sys.argv[1:]
r,q = json.loads(Path(capture).read_text()),json.loads(Path(quarter).read_text())
assert hashlib.sha256(Path(reference).read_bytes()).hexdigest() == r['reference_sha256']
assert hashlib.sha256(Path(engine).read_bytes()).hexdigest() == r['microchrony_sha256']
assert q['reference_sha256'] == r['reference_sha256'] and q['microchrony_sha256'] == r['microchrony_sha256']
grid = {}
for name,case in q['cases'].items():
    grid[name]={}
    for who in ['reference_rows','microchrony_rows']:
        full={tuple(row[:2]):row for row in r['cases'][name][who]}
        pairs=[(full[tuple(row[:2])],row) for row in case[who]
               if tuple(row[:2]) in full and row[7]>=0]
        utc=max(abs(a[2]-b[2]) for a,b in pairs)
        frequency=max(abs(a[3]-b[3]) for a,b in pairs)
        assert utc <= 1000 and frequency <= .001, (name,who,utc,frequency)
        grid[name][who]={'max_utc_delta_ns':utc,'max_frequency_delta_ppm':frequency}
prefix={}
case=r['cases']['noisy_frequency_step']
payload=''.join(line+'\n' for line in events(case['plant'],1).splitlines()
                if int(line.split()[0]) <= 7200*10**9)
for who,exe in [('reference_rows',reference),('microchrony_rows',engine)]:
    shortened=run(exe,0,payload)
    full=[row for row in case[who] if row[0]<=7200*10**9]
    assert shortened == full, who
    prefix[who]=len(full)
for name,target_ms in [('heldout_bias',2),('server_step_50ms',50)]:
    for who in ['chrony49','microchrony']:
        error=r['cases'][name]['summary'][who]['final_utc_error_ms']
        assert abs(error-target_ms)<.005,(name,who,error)
for who in ['reference_rows','microchrony_rows']:
    assert r['cases']['majority'][who][-1][7] in [0,1]
for case in r['cases'].values():
    assert len(case['reference_rows']) == len(case['microchrony_rows'])
    for who in ['chrony49','microchrony']:
        assert case['summary'][who]['first_sync_s'] <= 8
for name,case in r['cases'].items():
    if name in ['heldout_pool','heldout_ramp','majority'] or name.startswith('verification_'):
        a,b=case['summary']['chrony49'],case['summary']['microchrony']
        assert abs(a['last_hour_utc_rms_ms']-b['last_hour_utc_rms_ms']) < .001,(name,a,b)
        assert a['frequency_settles_1ppm_s'] == b['frequency_settles_1ppm_s'],(name,a,b)
report={'schema':'microchrony-chrony49-clock-loop-validation/1','grid':grid,
        'identical_causal_prefix_rows':prefix,'known_bias_checks_passed':True,
        'complete_event_streams':len(r['cases']),
        'pool_ramp_majority_rms_agree_within_1us':True,
        'pool_ramp_majority_frequency_settling_agrees':True}
Path(output).write_text(json.dumps(report,indent=2)+'\n')
print(len(r['cases']),'complete event streams; exact causal prefixes;',
      '1 s / 0.25 s probe grids agree within timestamp precision; known bias checks passed')
