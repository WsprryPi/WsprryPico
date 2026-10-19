#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Score learned-rate versus phase-only control with independent known truth.

Both simulated controllers see identical physical events. Phase-only tightens
maxupdateskew so no learned frequency can be applied; it retains phase damping.
This is an offline counterfactual, never a proposed device configuration.
Internet cases may improve or worsen: do not select a favorable trace afterwards.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from compare_chrony49_loop import events, internet_queue_cases, run, summarize


def main():
    if sys.flags.optimize:
        raise RuntimeError('Run without -O')
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','engine','output'):p.add_argument(name,type=Path)
    args=p.parse_args()
    cases={'twenty_ppm':dict(ppm=20,noise_s=.0005),**internet_queue_cases()}
    report={'schema':'microchrony-known-truth-rate-benefit/1',
        'binaries_sha256':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in
                           [('chrony49',args.reference),('microchrony',args.engine)]},
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'cases':{}}
    for name,case in cases.items():
        payload=events(case,1);out={}
        for who,binary in [('chrony49',args.reference),('microchrony',args.engine)]:
            full=run(str(binary.resolve()),0,payload)
            phase_run=subprocess.run([str(binary.resolve()),'0','phase'],input=payload,
                text=True,capture_output=True,check=True,timeout=60)
            phase=[list(map(float,l.split())) for l in phase_run.stdout.splitlines()]
            assert len(phase)==len(full) and all(a[:2]==b[:2] for a,b in zip(phase,full))
            assert all(r[3]==0 for r in phase),who
            assert any(r[4]!=0 for r in phase), 'Phase-only path did not apply phase damping'
            full_score,phase_score=summarize(full,case),summarize(phase,case)
            gain=phase_score['last_hour_utc_rms_ms']-full_score['last_hour_utc_rms_ms']
            periods={}
            first=max(full_score['first_sync_s'],phase_score['first_sync_s'])
            for low,high in [(0,600),(600,3600),(3600,7200),(10800,14400)]:
                values={}
                for label,rows in [('full',full),('phase_only',phase)]:
                    errors=[(r[2]-r[0])/1e6 for r in rows
                            if r[1]==0 and max(low,first)<=r[0]/1e9<high and r[2]>-1e18]
                    assert errors
                    values[label+'_utc_rms_ms']=math.sqrt(sum(x*x for x in errors)/len(errors))
                values['rms_gain_us']=(values['phase_only_utc_rms_ms']-values['full_utc_rms_ms'])*1000
                periods[f'{low}_{high}_seconds']=values
            if name=='twenty_ppm':
                assert full_score['last_hour_utc_rms_ms'] < .2*phase_score['last_hour_utc_rms_ms']
            out[who]=dict(full=full_score,phase_only=phase_score,
                last_hour_utc_rms_gain_ms=gain,periods=periods,full_rows=full,phase_only_rows=phase)
        report['cases'][name]=dict(plant=case,input_sha256=hashlib.sha256(payload.encode()).hexdigest(),controllers=out)
        print(name,{who:round(v['last_hour_utc_rms_gain_ms']*1000,4) for who,v in out.items()},'us RMS gain',flush=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
