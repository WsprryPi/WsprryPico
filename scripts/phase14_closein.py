#!/usr/bin/env python3
"""Bind matched close-in spectral diagnostics to an immutable Tone capture."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.plan import validate_physical,validate_capture
from phase14.closein import compare
from analyze_rf_bench import load_capture
from phase14.live import save
from led_closeout.runner import require,sha256


def analyze(directory,analysis,output,fft_samples=1048576):
    directory=directory.resolve();require(not output.exists(),'immutable close-in result exists')
    physical=validate_physical(json.loads((directory/'physical.json').read_text()))
    require(physical['mode']=='TONE' and physical['action']=='complete','complete Tone required')
    report=json.loads(analysis.read_text());require(report['physical_sha256']==sha256(directory/'physical.json'),'close-in physical substitution')
    require(all(report[k]==physical[k] for k in ('board','band','mode','clock_hz','source_revision','firmware_sha256','boot_id')) and
        report['job_id']==physical['job']['job_id'],'close-in source/job substitution')
    meta=json.loads((directory/'capture.json').read_text());validate_capture(meta,directory/'capture.cf32',physical['receiver_settings'])
    iq,_,digest=load_capture(directory/'capture.cf32',directory/'capture.json')
    require(digest==physical['capture_sha256']==report['capture_sha256'] and
        sha256(directory/'capture.json')==physical['metadata_sha256']==report['metadata_sha256'],'close-in IQ substitution')
    measurement=report['measurement'];intervals=measurement['intervals_s']
    require(len(intervals)==1 and measurement['measurements'],'one acquired Tone interval required')
    carrier=sum(m['indicated_hz'] for m in measurement['measurements'])/len(measurement['measurements'])
    settings=physical['receiver_settings'];result=compare(iq,settings['sample_rate_hz'],settings['center_frequency_hz'],carrier,intervals[0],fft_samples)
    require(result['carrier_on_minus_off_db']>=10,'source on/off attribution inadequate')
    result.update(board=physical['board'],band=physical['band'],clock_hz=physical['clock_hz'],
        source_revision=physical['source_revision'],firmware_sha256=physical['firmware_sha256'],boot_id=physical['boot_id'],
        job_id=physical['job']['job_id'],capture_sha256=digest,metadata_sha256=physical['metadata_sha256'],
        physical_sha256=report['physical_sha256'],original_analysis_sha256=sha256(analysis),
        original_disposition=report['disposition'],release_qualified=False,
        tools={str(p.relative_to(ROOT)):sha256(p) for p in (Path(__file__),ROOT/'src/phase14/closein.py')})
    if physical['band']=='80m' and settings['sample_rate_hz']==250000 and fft_samples==1048576:
        result['historical_pi_benchmark']=dict(source='docs/development/rf-clock-validation.md',
            lower_120_dbc=-21.66,upper_120_dbc=-21.49,
            relative_peak_bin_comparison_passed=result['lower_120']['peak_dbc']<=-21.66 and result['upper_120']['peak_dbc']<=-21.49,
            limitation='Matched 0.238419 Hz Hann bins against the retained Pi comparison; different measurement dates and uncalibrated path/receiver attribution remain.')
    save(output,result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--fft-samples',type=int,choices=(500000,1048576),default=1048576);a=p.parse_args()
    print(json.dumps(analyze(a.directory,a.analysis,a.output,a.fft_samples)))
