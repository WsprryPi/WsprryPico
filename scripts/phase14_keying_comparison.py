#!/usr/bin/env python3
"""Finite paired Tone/QRSS captures and equal-length offline phase diagnostics."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]


def run(output):
    from phase14.candidate import candidate
    from phase14.live import Rig,save
    from phase14.analysis import analyze
    from led_closeout.runner import require
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux bench owner')
    require(output.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    manifest,image,_=candidate(ROOT);os.umask(0o077)
    rig=Rig(output,ROOT,board='A',receiver=True,reference=True)
    records=[]
    try:
        for pair in range(3):
            # Balance order, preserving identical pre-job idle duration. This
            # controls elapsed time/history without claiming thermal equilibrium.
            for mode in (('TONE','QRSS') if pair%2==0 else ('QRSS','TONE')):
                before=rig.idle('A');rig.idle('B')
                require(before['revision']==manifest['source_commit'][:12] and before['system_clock_hz']==138000000,
                        'keying comparison source/clock')
                time.sleep(45)
                directory=rig.execute('A',138000000,'80m',mode,len(records)+1,
                    duration=35 if mode=='TONE' else None,image_hash=image['sha256'])
                report=analyze(directory,'analysis-keying-comparison')
                records.append(dict(pair=pair,mode=mode,path=str(directory),disposition=report['disposition']))
                save(output/'jobs.json',records)
    finally:rig.close()
    print(json.dumps(dict(result='FINITE_COMPARISON_CAPTURED',jobs=len(records),release_qualified=False)))


def diagnose(directory):
    import numpy as np
    from analyze_rf_bench import load_capture
    from measure_rf_bench import baseband,phase_fit
    from phase14.plan import validate_physical,validate_capture,BANDS
    from phase14.live import save
    from phase14_qrss_diagnostic import polynomial,narrow_fir
    from led_closeout.runner import require,sha256
    physical=validate_physical(json.loads((directory/'physical.json').read_text()))
    require(physical['board']=='A' and physical['band']=='80m' and physical['mode'] in ('TONE','QRSS') and
            physical['action']=='complete' and physical['clock_hz']==138000000 and
            physical.get('engine_frequency_correction_ppb',0)==0 and
            physical.get('requested_frequency_compensation_ppb',0)==0 and
            int(physical['accepted_job']['total_duration_ns'])==35000000000,'matched keying candidate')
    path=directory/'analysis-keying-comparison/result.json'
    original=json.loads(path.read_text())
    require(original['physical_sha256']==sha256(directory/'physical.json'),'comparison analysis identity')
    require(all(original[k]==physical[k] for k in ('board','band','mode','clock_hz','source_revision','firmware_sha256','boot_id')) and
            original['job_id']==physical['job']['job_id'],'comparison candidate/job substitution')
    meta=json.loads((directory/'capture.json').read_text())
    validate_capture(meta,directory/'capture.cf32',physical['receiver_settings'])
    iq,_,capture_sha=load_capture(directory/'capture.cf32',directory/'capture.json')
    require(capture_sha==physical['capture_sha256']==original['capture_sha256'],'comparison capture identity')
    rate=meta['actual_settings']['sample_rate_hz'];center=meta['actual_settings']['center_frequency_hz']
    frequency=BANDS['80m'];reference_hz=physical['reference']['f1']
    if physical['mode']=='TONE':
        intervals=original['measurement']['intervals_s']
        require(len(intervals)==1 and abs(intervals[0][1]-intervals[0][0]-35)<.02,'complete 35-second Tone')
        origin=intervals[0][0]
    else:
        require(original.get('alignment_s') is not None,'QRSS alignment absent')
        origin=original['alignment_s']
        marks=[e for e in physical['accepted_job']['events'] if e['rf_on']]
        require(any(int(e['offset_ns'])==13000000000 and int(e['duration_ns'])==9000000000 for e in marks),
                'expected nine-second QRSS dash absent')
    # Identical nine-second interval at offset 13; preserve the frozen 20 ms
    # edge exclusion and original full-job flags, including any failures.
    left,right=origin+13+.02,origin+22-.02
    bb,brate=baseband(iq,rate,center,frequency)
    reference,_=baseband(iq,rate,center,reference_hz)
    a,b=round(left*brate),round(right*brate)
    source=bb[a:b];ref=reference[a:b]
    paired=source*np.conj(ref)/np.maximum(np.abs(ref),1e-300)
    carrier=phase_fit(source,brate,frequency)['indicated_hz']
    first,last=round((left-.5)*rate),round((right+.5)*rate)
    mixed=np.asarray(iq[first:last])*np.exp(-2j*np.pi*(carrier-center)*np.arange(first,last)/rate)
    filtered=narrow_fir(mixed,rate,25)
    lo,hi=round(left*rate)-first,round(right*rate)-first
    result=dict(schema='phase14-keying-comparison/1',mode=physical['mode'],board=physical['board'],
        source_revision=physical['source_revision'],firmware_sha256=physical['firmware_sha256'],
        boot_id=physical['boot_id'],job_id=physical['job']['job_id'],physical_sha256=sha256(directory/'physical.json'),
        capture_sha256=capture_sha,original_analysis_sha256=sha256(path),
        original_disposition=original['disposition'],interval_s=[left,right],
        source=polynomial(source,brate),reference=polynomial(ref,brate),
        reference_paired=polynomial(paired,brate),independent_25hz=polynomial(filtered[lo:hi:250],rate/250),
        source_fit=phase_fit(source,brate,frequency),reference_fit=phase_fit(ref,brate,reference_hz),
        script_sha256=sha256(__file__),fir_script_sha256=sha256(ROOT/'scripts/phase14_qrss_diagnostic.py'),
        release_qualified=False,original_screen_unchanged=True,
        limitations=['Equal-length phase comparison diagnoses preceding RF state; it does not establish a thermal cause.',
                    'Pre-job idle duration is controlled; board temperature is unmeasured.'])
    target=directory/'keying-comparison.json';require(not target.exists(),'immutable comparison exists')
    save(target,result)
    return {k:result[k] for k in ('mode','source','reference_paired','independent_25hz')}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='op',required=True)
    r=sub.add_parser('run');r.add_argument('--output',type=Path,required=True)
    d=sub.add_parser('diagnose');d.add_argument('directory',type=Path)
    a=p.parse_args()
    def interrupted(signum,frame):
        signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    if a.op=='run':run(a.output)
    else:print(json.dumps(diagnose(a.directory)))


if __name__=='__main__':main()
