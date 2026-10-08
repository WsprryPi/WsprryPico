#!/usr/bin/env python3
"""Finite GPSDO-only ABBA receiver scale comparison; preserves reference settings."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from phase14.live import Rig,CAPTURE,save
from phase14.plan import BANDS,validate_capture
from led_closeout.runner import require,sha256

GPSPY='/home/pi/lbgpsdo/.venv/bin/python'
FIELDS=('serial','sat_lock','pll_lock','ant_ok','out1','out2','pps1','f1','f2','out1low','out2low')


def gps(frequency=None):
    code=('import sys,json;sys.path.insert(0,"/home/pi/lbgpsdo");import lbe142x;'
          'd=lbe142x.GPSDODevice.open(serial="0673ED0FA107");')
    if frequency is not None:code+='d.set_freq(0,'+str(frequency)+',False);'
    code+='d.read();print(json.dumps({k:getattr(d,k) for k in '+repr(FIELDS)+'}));d.close()'
    value=json.loads(subprocess.check_output([GPSPY,'-c',code],text=True,timeout=20))
    require(value['serial']=='0673ED0FA107' and value['sat_lock'] and value['pll_lock'] and value['ant_ok'],
            'reference identity/readiness')
    if frequency is not None:require(value['f1']==frequency,'reference frequency readback')
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--band',choices=BANDS,default='80m');args=p.parse_args()
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(args.output.resolve().is_relative_to((ROOT/'build').resolve()),'private build evidence required')
    os.umask(0o077);rig=Rig(args.output,ROOT,receiver=True);before=None
    try:
        boards={b:rig.idle(b) for b in ('A','B')};before=gps()
        require(before['out1'] and not before['pps1'],'measurement output 1 must already be in RF mode')
        center=BANDS[args.band];values=[]
        save(rig.e.root/'before.json',dict(boards=boards,reference=before))
        settings=dict(format='CF32',sample_rate_hz=250000,bandwidth_hz=200000,
                      center_frequency_hz=center,gain_db=20,channel=0,agc=False,bias_tee=False)
        # Symmetric ABBA ordering cancels first-order tuner/reference drift.
        for index,frequency in enumerate((center-20000,center+20000,center+20000,center-20000)):
            reference=gps(frequency)
            require(all(reference[k]==before[k] for k in ('out1','out2','pps1','f2','out1low','out2low')),
                    'unrelated reference setting changed')
            directory=rig.e.root/str(index);directory.mkdir(mode=0o700)
            argv=[CAPTURE,'--enable-physical-sdr','sdrplay','2404058C60',str(center),'2000000',
                  '20','250000','200000','0','false','false','100000','20',str(directory/'capture.cf32'),
                  str(directory/'capture.json'),'phase14-ref-'+args.band+'-'+str(index)]
            with (directory/'capture.log').open('x') as log:
                subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=25)
            meta=json.loads((directory/'capture.json').read_text());validate_capture(meta,directory/'capture.cf32',settings)
            from analyze_rf_bench import load_capture
            from measure_rf_bench import baseband,phase_fit,local_contrast
            import numpy as np
            iq,_,capture_sha=load_capture(directory/'capture.cf32',directory/'capture.json')
            bb,rate=baseband(iq,250000,center,frequency)
            fitted=[phase_fit(bb[int(left*rate):int((left+1)*rate)],rate,frequency) for left in range(1,7)]
            contrast=local_contrast(iq[250000:500000],250000,center,frequency)
            require(contrast>=30 and all(v['phase_residual_rms_rad']<.15 for v in fitted),'reference acquisition/coherence')
            value=dict(frequency_hz=frequency,reference=reference,fits=fitted,contrast_db=contrast,
                       mean_indicated_hz=float(np.mean([v['indicated_hz'] for v in fitted])),
                       capture_sha256=capture_sha,metadata_sha256=sha256(directory/'capture.json'))
            values.append(value);save(directory/'fit.json',value)
        low=np.mean([values[i]['mean_indicated_hz'] for i in (0,3)])
        high=np.mean([values[i]['mean_indicated_hz'] for i in (1,2)])
        scale=float((high-low)/40000)
        pair_scales=[(values[1]['mean_indicated_hz']-values[0]['mean_indicated_hz'])/40000,
                     (values[2]['mean_indicated_hz']-values[3]['mean_indicated_hz'])/40000]
        uncertainty=max(abs(pair_scales[0]-pair_scales[1])/2,
                        4*max(np.std([f['indicated_hz'] for f in v['fits']]) for v in values)/40000,1e-8)
        require(abs(scale-1)<100e-6,'implausible receiver sampling scale')
        save(rig.e.root/'comparison.json',dict(schema='phase14-reference/1',band=args.band,center_hz=center,
             scale_nominal_to_true_time=scale,actual_sample_rate_hz=250000/scale,
             scale_ppm=(scale-1)*1e6,repeatability_bound_ppm=float(uncertainty*1e6),
             reference_accuracy_assumption_ppb=1,traceable_calibration=False,
             method='Locked GPSDO output 1, 40 kHz frequency difference, four 8 s same-tuning captures in ABBA order; six independent 1 s phase fits per capture.',
             limitations=['1 ppb is an explicit conservative engineering reference assumption, not a calibration certificate.',
                          'Receiver scale may drift; bracket long campaigns and report repeatability separately.',
                          'Sequential reference comparison does not calibrate absolute UTC onset.'],values=values))
        print(json.dumps(dict(band=args.band,scale_ppm=(scale-1)*1e6,repeatability_bound_ppm=float(uncertainty*1e6))))
    finally:
        try:
            if before:
                restored=gps(before['f1']);require(restored==before,'reference restoration readback')
                save(rig.e.root/'after.json',dict(reference=restored,boards={b:rig.idle(b) for b in ('A','B')}))
        finally:
            rig.close()


if __name__=='__main__':main()
