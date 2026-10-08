#!/usr/bin/env python3
"""Cancel one armed job before launch; compare its RF capture with a live on baseline."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.live import Rig,save
from phase14.candidate import candidate
from phase14.analysis import analyze
from phase14.plan import validate_physical,validate_capture,resources,BANDS
from led_closeout.runner import require,sha256


def main():
    import numpy as np
    from analyze_rf_bench import load_capture
    from measure_rf_bench import baseband,phase_fit,local_contrast
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--board',choices=('A','B'),required=True);a=p.parse_args()
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(a.output.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    def interrupted(signum,frame):
        signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    manifest,image,_=candidate(ROOT);os.umask(0o077)
    rig=Rig(a.output,ROOT,board=a.board,receiver=True,reference=True)
    try:
        require(rig.idle(a.board)['revision']==manifest['source_commit'][:12],'cancel candidate source')
        on=rig.execute(a.board,138000000,'80m','TONE',1,image_hash=image['sha256'])
        analyze(on,'analysis-on-baseline')
        baseline=json.loads((on/'analysis-on-baseline/result.json').read_text())
        require(baseline['disposition']=='OPERATIONAL_SCREEN_PASS','receiver/on baseline not established')
        cancelled=rig.execute(a.board,138000000,'80m','TONE',2,action='cancel',image_hash=image['sha256'])
        physical=validate_physical(json.loads((cancelled/'physical.json').read_text()))
        on_physical=validate_physical(json.loads((on/'physical.json').read_text()))
        require(all(physical[k]==on_physical[k] for k in ('board','boot_id','source_revision','firmware_sha256','clock_hz','receiver_settings')),
                'on/cancel comparison identity/settings')
        settings=physical['receiver_settings'];rate=settings['sample_rate_hz'];center=settings['center_frequency_hz']
        meta=json.loads((cancelled/'capture.json').read_text());validate_capture(meta,cancelled/'capture.cf32',settings)
        iq,_,digest=load_capture(cancelled/'capture.cf32',cancelled/'capture.json')
        on_iq,_,on_digest=load_capture(on/'capture.cf32',on/'capture.json')
        require(digest==physical['capture_sha256'] and sha256(cancelled/'capture.json')==physical['metadata_sha256'] and
            on_digest==on_physical['capture_sha256']==baseline['capture_sha256'],'cancel/baseline capture substitution')
        on_bb,brate=baseband(on_iq,rate,center,BANDS['80m'])
        left,right=baseline['measurement']['intervals_s'][0]
        on_power=float(np.median(np.abs(on_bb[round((left+.1)*brate):round((right-.1)*brate)])**2))
        quiet,_=baseband(iq,rate,center,BANDS['80m']);quiet_power=np.abs(quiet)**2
        ref_hz=physical['reference']['f1'];ref,_=baseband(iq,rate,center,ref_hz)
        ref_fit=phase_fit(ref[round(brate):round(7*brate)],brate,ref_hz)
        ref_contrast=local_contrast(iq[round(rate):round(2*rate)],rate,center,ref_hz)
        require(ref_contrast>=20 and ref_fit['phase_residual_rms_rad']<=.15 and ref_fit['amplitude_min_ratio']>=.5,
                'cancel receiver reference not healthy')
        contrast=10*np.log10(on_power/max(float(quiet_power.max()),1e-300))
        require(contrast>=10,'cancelled RF resolved above off criterion')
        result=dict(schema='phase14-cancel-assessment/1',board=a.board,source_revision=physical['source_revision'],
            firmware_sha256=image['sha256'],boot_id=physical['boot_id'],job_id=physical['job']['job_id'],
            physical_sha256=sha256(cancelled/'physical.json'),capture_sha256=digest,
            on_baseline_physical_sha256=sha256(on/'physical.json'),on_baseline_analysis_sha256=sha256(on/'analysis-on-baseline/result.json'),
            reference_fit=ref_fit,reference_contrast_db=ref_contrast,
            minimum_on_to_cancelled_contrast_db=float(contrast),detector_sample_period_s=1/brate,
            resources=resources([on_physical['before'],physical['before'],physical['after']],138000000),
            script_sha256=sha256(__file__),release_qualified=False,
            limitation='No RF burst resolved by the 1 ms Hann detector at >=10 dB below the live baseline; no shorter-transient or calibrated UTC claim.')
        save(a.output/'assessment.json',result)
        print(json.dumps(dict(board=a.board,result='ARMED_CANCELLATION_ASSESSED',contrast_db=float(contrast),resources_passed=result['resources']['passed'])))
    finally:rig.close()


if __name__=='__main__':main()
