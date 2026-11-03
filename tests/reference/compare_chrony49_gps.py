#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Known-truth UTC-completed PPS through real Pairer/Engine and Chrony SRC_REFCLOCK.

The external oracle enters after receiver qualification, not through a hardware
RCL driver. Original MIT adapter code links only to the separately built GPL
reference. No OS clock, network, device, package install, or download is used.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

SECOND=1_000_000_000
EPOCH=1_800_000_000*SECOND
CASES=('fast','slow','warmup','loss_reacquire','restart_seed','source_conflict')

def events(case):
    entries=[(0,0,0,0,0,0)]
    def raw(t):
        if case=='warmup':
            x=min(t,600)
            extra=20e-6*(x-x*x/1200)
        else:
            extra=(-20e-6 if case=='slow' else 20e-6)*t
        return round((t+extra)*SECOND)
    def add(t,action,slot,utc=0,stratum=0):
        entries.append((round(t*SECOND),raw(t),action,slot,round(utc),stratum))
    for i in range(1,901):
        if case=='loss_reacquire' and 300<=i<420:
            add(i+.1,3,4)
        else:
            add(i,1,4)
            add(i+.1,4,4,EPOCH+i*SECOND)
        if case=='source_conflict' and (i in (8,10,12,14,16,18) or i%64==0):
            add(i+.3,1,0)
            if i<=320:
                add(i+.302,2,0,EPOCH+round((i+.301+2)*SECOND),1)
            else:
                add(i+.302,3,0)
    entries.sort()
    return ''.join(' '.join(str(v) for v in row)+'\n' for row in entries)

def run(binary,seed,payload):
    p=subprocess.run([str(binary),str(seed),'gps'],input=payload,text=True,
                     capture_output=True,timeout=30,check=True)
    result=[]
    for line in p.stdout.splitlines():
        row=[float(v) for v in line.split()]
        assert len(row)==9 and all(math.isfinite(v) for v in row),line
        result.append(row)
    assert result and result[0][7]==-1,'A restart seed cannot restore source authority'
    return result

def score(rows,case,external=False):
    usable=[r for r in rows if r[0]>=180*SECOND and r[2]>-1e18]
    if case=='source_conflict':
        assert any(r[7]==-1 and r[0]>120*SECOND for r in rows),'Known conflict was not detected'
        if not external:
            assert all(r[7]==-1 for r in rows if r[0]>400*SECOND),'Expiry cleared known GPS/NTP conflict'
        return {'conflict_detected':True,'late_selected':int(rows[-1][7]),'policy_difference':'Pico latches conflict through expiry; external Chrony source-stage selection is reported independently'}
    assert usable
    errors=[abs(r[2]-r[0]) for r in usable]
    # Synthetic source/capture allowance is 150 us. These finite algorithm
    # checks are declared before running, not hardware accuracy guarantees.
    limit=10_000_000 if case=='loss_reacquire' else 2_000_000
    assert max(errors)<=limit,(case,external,'UTC',max(errors),limit)
    final=[r for r in usable if r[0]>800*SECOND]
    assert final and all(r[7]==4 for r in final),(case,external,'reference reacquisition')
    expected=20/(1-20e-6) if case=='slow' else 0 if case=='warmup' else -20/(1+20e-6)
    frequency=max(abs(r[3]-expected) for r in final)
    assert frequency<=2,(case,external,'pure frequency ppm',frequency)
    if case=='loss_reacquire' and not external:
        assert all(r[7]==-1 for r in rows if 310*SECOND<r[0]<419*SECOND),'Lost PPS remained fresh'
    return {'maximum_utc_error_ns':max(errors),'maximum_final_frequency_error_ppm':frequency,
            'final_selected':int(rows[-1][7]),'rows':len(rows),'synthetic_utc_limit_ns':limit,
            'synthetic_final_frequency_limit_ppm':2}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('microchrony',type=Path)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--chrony',type=Path)
    mode.add_argument('--engine-only',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    assert __debug__,'Assertions must remain enabled'
    report={'schema':'gps-refclock-comparison/1','scope':__doc__,
            'microchrony_sha256':hashlib.sha256(args.microchrony.read_bytes()).hexdigest(),'cases':{}}
    if args.chrony:
        report['chrony_sha256']=hashlib.sha256(args.chrony.read_bytes()).hexdigest()
    for case in CASES:
        payload=events(case)
        seed=-20/(1+20e-6) if case=='restart_seed' else 0
        micro=run(args.microchrony,seed,payload)
        result={'input_sha256':hashlib.sha256(payload.encode()).hexdigest(),'microchrony':score(micro,case)}
        if args.chrony:
            external=run(args.chrony,-seed/(1+seed*1e-6),payload)
            result['chrony49']=score(external,case,True)
        report['cases'][case]=result
    text=json.dumps(report,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    print(text,end='')
if __name__=='__main__':main()
