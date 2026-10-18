#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Hardware-free, known-truth acceptance of the production Engine clock loop."""
import sys

from compare_chrony49_loop import events, run, summarize

if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')

executable = sys.argv[1]
cases = {
    'uncompensated_20ppm': {'ppm':20},
    'noise': {'ppm':20, 'noise_s':.0005},
    'drift_step': {'ppm':-20, 'after_ppm':20, 'switch_s':3600, 'noise_s':.0005},
    'wrong_restart_seed': {'ppm':20, 'seed_ppm':-60},
    'holdover': {'ppm':20, 'noise_s':.0001, 'loss_start_s':3600, 'loss_end_s':4800},
    'pool': {'ppm':35, 'sources':4, 'forward_ns':10_000_000, 'backward_ns':10_000_000,
             'noise_s':.005, 'noise_seed':314159},
}
for seed in [271828, 918273, 161803]:
    cases[f'pool_{seed}'] = dict(cases['pool'],noise_seed=seed)
cases['majority'] = {'ppm':20,'sources':3,'noise_s':.0001,'falseticker':True}
pool_rms_limits = {'pool':.440,'pool_271828':.273,'pool_918273':.338,'pool_161803':.164}
for name, case in cases.items():
    seed = case.get('seed_ppm', 0)
    rows = run(executable, -seed/(1+seed/1e6), events(case, 1))
    result = summarize(rows,case)
    assert result['first_sync_s'] <= 8, (name,result)
    assert result['last_hour_utc_max_abs_ms'] < 1, (name,result)
    assert result['last_hour_frequency_max_abs_ppm'] < .5, (name,result)
    assert result['frequency_settles_1ppm_s'] <= (1800 if name.startswith('pool') else 600), (name,result)
    if name in pool_rms_limits:
        assert result['last_hour_utc_rms_ms'] < pool_rms_limits[name], (name,result)
    if name == 'holdover':
        assert result['valid_probe_count'] > result['synchronized_probe_count']
        assert any(r[7] == -1 and 4200e9 < r[0] < 4800e9 for r in rows)
        assert rows[-1][7] >= 0
    # The applied clock stays monotonic after its initial epoch assignment.
    valid = [r for r in rows if r[2] > -10**18]
    assert all(b[2] >= a[2] for a,b in zip(valid,valid[1:])), name
print(f'{len(cases)} complete Engine loops passed known UTC/rate truth, recovery and holdover checks')
