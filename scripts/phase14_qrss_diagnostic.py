#!/usr/bin/env python3
"""Offline QRSS phase/filter/edge diagnostics; preserve original screening result."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
import numpy as np


def narrow_fir(samples,rate,cutoff):
    # Independent windowed-sinc FIR and linear FFT convolution using the
    # retained NumPy runtime. The halo excludes convolution boundary effects.
    taps=4097;index=np.arange(taps)-(taps-1)/2
    kernel=2*cutoff/rate*np.sinc(2*cutoff/rate*index)*np.kaiser(taps,8.6);kernel/=kernel.sum()
    count=len(samples)+taps-1;size=1<<(count-1).bit_length()
    full=np.fft.ifft(np.fft.fft(samples,size)*np.fft.fft(kernel,size))[:count]
    return full[taps//2:taps//2+len(samples)]


def polynomial(samples,rate):
    t=np.arange(len(samples))/rate;t-=t.mean();phase=np.unwrap(np.angle(samples))
    line=np.polyfit(t,phase,1);curve=np.polyfit(t,phase,2)
    return dict(linear_phase_rms_rad=float(np.sqrt(np.mean((phase-np.polyval(line,t))**2))),
        quadratic_phase_rms_rad=float(np.sqrt(np.mean((phase-np.polyval(curve,t))**2))),
        fitted_frequency_drift_hz_per_s=float(curve[0]/np.pi),
        fitted_drift_across_interval_hz=float(curve[0]/np.pi*(len(samples)-1)/rate))


def diagnostic(directory):
    from analyze_rf_bench import load_capture
    from measure_rf_bench import baseband,phase_fit
    from phase14.plan import validate_physical,validate_capture,BANDS
    from phase14.live import save
    from led_closeout.runner import require,sha256
    directory=Path(directory).resolve();physical=validate_physical(json.loads((directory/'physical.json').read_text()))
    require(physical['mode']=='QRSS' and physical['action']=='complete','completed QRSS diagnostic required')
    original=json.loads((directory/'analysis-acceptance/result.json').read_text())
    require(original['physical_sha256']==sha256(directory/'physical.json'),'original QRSS source binding')
    meta=json.loads((directory/'capture.json').read_text());validate_capture(meta,directory/'capture.cf32',physical['receiver_settings'])
    iq,_,capture_sha=load_capture(directory/'capture.cf32',directory/'capture.json')
    require(capture_sha==physical['capture_sha256']==original['capture_sha256'],'QRSS capture substitution')
    rate=meta['actual_settings']['sample_rate_hz'];center=meta['actual_settings']['center_frequency_hz'];frequency=BANDS[physical['band']]
    bb,brate=baseband(iq,rate,center,frequency);reference=None
    if physical.get('reference'):reference,_=baseband(iq,rate,center,physical['reference']['f1'])
    reports=[]
    for event in physical['accepted_job']['events']:
        if not event['rf_on']:continue
        left=original['alignment_s']+int(event['offset_ns'])/1e9;right=left+int(event['duration_ns'])/1e9
        value=dict(interval_s=[left,right],edge_trim_tests=[],independent_filters=[])
        for trim in (.02,.1,.5,1):
            if right-left<=2*trim+.1:continue
            a,b=round((left+trim)*brate),round((right-trim)*brate)
            fit=phase_fit(bb[a:b],brate,frequency);fit.update(polynomial(bb[a:b],brate));fit['trim_s']=trim
            rolling=[]
            for start in np.arange(left+trim,right-trim-.499,.5):
                x,y=round(start*brate),round((start+.5)*brate)
                pf=phase_fit(bb[x:y],brate,frequency)
                if reference is not None:
                    rf=phase_fit(reference[x:y],brate,physical['reference']['f1'])
                    pf['reference_subtracted_hz']=pf['indicated_hz']-(rf['indicated_hz']-physical['reference']['f1'])
                rolling.append(dict(center_s=float(start+.25),**pf))
            fit['half_second_fits']=rolling
            if reference is not None:
                paired=bb[a:b]*np.conj(reference[a:b])/np.maximum(np.abs(reference[a:b]),1e-300)
                fit['paired_reference_phase']=polynomial(paired,brate)
            value['edge_trim_tests'].append(fit)
        # Entire mark plus halo; a different FIR implementation rejects distant
        # carriers/images. Retune only analysis mixing, not the physical source.
        at=max(0,round((left-.5)*rate));end=min(len(iq),round((right+.5)*rate))
        carrier=phase_fit(bb[round((left+.02)*brate):round((right-.02)*brate)],brate,frequency)['indicated_hz']
        mixed=np.asarray(iq[at:end])*np.exp(-2j*np.pi*(carrier-center)*np.arange(at,end)/rate)
        for cutoff in (25,100):
            filtered=narrow_fir(mixed,rate,cutoff)
            first,last=round((left+.02)*rate)-at,round((right-.02)*rate)-at
            data=filtered[first:last:250]
            value['independent_filters'].append(dict(cutoff_hz=cutoff,taps=4097,carrier_hz=carrier,
                fit=phase_fit(data,rate/250,carrier),phase=polynomial(data,rate/250)))
        reports.append(value)
    output=dict(schema='phase14-qrss-diagnostic/1',source_revision=physical['source_revision'],firmware_sha256=physical['firmware_sha256'],
        board=physical['board'],boot_id=physical['boot_id'],job_id=physical['job']['job_id'],capture_sha256=capture_sha,
        original_analysis_sha256=sha256(directory/'analysis-acceptance/result.json'),original_disposition=original['disposition'],
        script_sha256=sha256(__file__),marks=reports,original_screen_unchanged=True,
        limitations=['Quadratic phase fit diagnoses slow drift; it does not replace the frozen linear-phase screen.',
            'Filter/edge tests assess analysis sensitivity; they do not qualify a physical LPF or calibrated UTC.'])
    require(not (directory/'qrss-diagnostic.json').exists(),'immutable QRSS diagnostic already exists')
    save(directory/'qrss-diagnostic.json',output)
    return [{"duration_s":v['interval_s'][1]-v['interval_s'][0],"linear_phase_rms_rad":v['edge_trim_tests'][0]['linear_phase_rms_rad'],
             "quadratic_phase_rms_rad":v['edge_trim_tests'][0]['quadratic_phase_rms_rad'],
             "drift_hz_per_s":v['edge_trim_tests'][0]['fitted_frequency_drift_hz_per_s'],
             "narrow_filter_phase_rms_rad":v['independent_filters'][0]['phase']['linear_phase_rms_rad']} for v in reports]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    print(json.dumps(diagnostic(p.parse_args().directory)))
