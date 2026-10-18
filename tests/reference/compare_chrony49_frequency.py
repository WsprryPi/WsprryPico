#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Compare the independently derived frequency update against REF_SetReference."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

if sys.flags.optimize:
    raise RuntimeError('Validation requires assertions; run without -O')

control, engine, destination = sys.argv[1:]
rows = []
for old in (1e-6,3.5e-6,10e-6,100e-6):
    for new in (1e-6,3.5e-6,10e-6,100e-6,1000e-6):
        for innovation in (-20e-6,0,1e-6,20e-6):
            payload = (f'1800000000 0 .001 0 .000001 {old}\n'
                       f'1800000064 0 .001 {innovation} .000001 {new}\n')
            ref = subprocess.run([control],input=payload,text=True,capture_output=True,
                                 check=True,timeout=10).stdout.splitlines()[-1].split()
            mu = subprocess.run([engine,'frequency'],input=f'{old} {new} {innovation}\n',
                                text=True,capture_output=True,check=True,timeout=10).stdout.split()
            expected,actual = [float(ref[1]),float(ref[4])*1e6], [float(mu[0])*1e6,float(mu[1])*1e6]
            # REF's first update starts with a finite prior, not an exact input
            # skew; the tolerance covers that initialization and ppm arithmetic.
            assert abs(expected[0]-actual[0]) < .003, (old,new,innovation,expected,actual)
            assert abs(expected[1]-actual[1]) < .02, (old,new,innovation,expected,actual)
            rows.append({'old_skew':old,'new_skew':new,'innovation':innovation,
                         'reference_ppm':expected,'microchrony_ppm':actual})
report = {'schema':'microchrony-chrony49-frequency-update/1','cases':rows,
          'max_rate_difference_ppm':max(abs(r['reference_ppm'][0]-r['microchrony_ppm'][0]) for r in rows),
          'max_skew_difference_ppm':max(abs(r['reference_ppm'][1]-r['microchrony_ppm'][1]) for r in rows),
          'binaries_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [control,engine]}}
Path(destination).write_text(json.dumps(report,indent=2)+'\n')
print(len(rows),'frequency combinations passed;',report['max_rate_difference_ppm'],
      'ppm maximum rate delta;',report['max_skew_difference_ppm'],'ppm maximum skew delta')
