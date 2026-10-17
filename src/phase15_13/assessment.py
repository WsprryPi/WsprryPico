"""Selected acceptance, retaining older frequency/coherence diagnostics intact."""
import json
from pathlib import Path
from led_closeout.runner import require, sha256
from phase14.plan import validate_physical, validate_capture
from phase14.live import save
from phase15_13.plan import FREQUENCIES, RATE, plan, repair_plan, fskcw_repair_plan


def assess(directory, label='analysis'):
    directory=Path(directory)
    physical=validate_physical(json.loads((directory/'physical.json').read_text()),
                               band_frequencies=FREQUENCIES)
    expected=next(w for w in plan()['windows']+repair_plan()['windows']+fskcw_repair_plan()['windows'] if w['id']==physical['window_id'])
    require(physical['job']==expected['job'] and physical['band']==expected['band'] and
            physical['mode']==expected['mode'], 'frozen workload substitution')
    meta=json.loads((directory/'capture.json').read_text())
    validate_capture(meta,directory/'capture.cf32',physical['receiver_settings'])
    result=json.loads((directory/label/'result.json').read_text())
    require(result['physical_sha256']==sha256(directory/'physical.json') and
            result['capture_sha256']==meta['output']['sha256'] and
            result['metadata_sha256']==sha256(directory/'capture.json'), 'analysis input binding')
    issues=[]
    if not result['resources']['passed']:issues.append('resource checks failed')
    mode=physical['mode'];measurement=result.get('measurement',result)
    intervals=measurement.get('intervals_s',measurement.get('observed_intervals_s',[]))
    duration=meta['retained_sample_count']/RATE
    if not intervals or intervals[0][0]<.5 or duration-intervals[-1][1]<.5:
        issues.append('independent leading/trailing silence absent')
    details={}
    if mode in ('TONE','WSPR'):
        requested=int(physical['job']['total_duration_ns'])/1e9
        if len(intervals)!=1 or abs(intervals[0][1]-intervals[0][0]-requested)>.02:
            issues.append('complete uninterrupted envelope/timing failed')
    if mode=='TONE':
        import numpy as np
        from measure_rf_bench import local_contrast,baseband
        iq=np.memmap(directory/'capture.cf32',dtype='<c8',mode='r')
        fits=measurement['measurements']
        contrasts=[local_contrast(iq[round(m['interval_s'][0]*RATE):round(m['interval_s'][1]*RATE)],
                    RATE,physical['receiver_settings']['center_frequency_hz'],m['indicated_hz']) for m in fits]
        bb,rate=baseband(iq,RATE,physical['receiver_settings']['center_frequency_hz'],
                         FREQUENCIES[physical['band']])
        amplitude=np.abs(bb[round((intervals[0][0]+.02)*rate):round((intervals[0][1]-.02)*rate)])
        ratio=float(amplitude.min()/np.median(amplitude))
        if not contrasts or min(contrasts)<10:issues.append('carrier contrast below 10 dB')
        if ratio<.5:issues.append('carrier interior continuity failed')
        reference=[m['reference_compared_hz']-FREQUENCIES[physical['band']] for m in fits]
        indicated=[m['indicated_hz']-FREQUENCIES[physical['band']] for m in fits]
        details=dict(minimum_contrast_db=min(contrasts),interior_amplitude_min_ratio=ratio,
            indicated_offset_mean_hz=float(np.mean(indicated)),reference_compared_offset_mean_hz=float(np.mean(reference)),
            observed_reference_compared_offset_range_hz=[min(reference),max(reference)],
            empirical_half_range_hz=float(np.ptp(reference)/2),absolute_uncertainty_hz=None,
            frequency_acceptance='descriptive only; no selected calibrated absolute-error gate',
            uncertainty='Empirical range is repeatability plus drift, not combined uncertainty. Simultaneous reference subtraction uses the nominal SDR sample axis; absolute/sample-scale calibration is unavailable.')
    elif mode=='WSPR':
        from phase14.wspr_decode import assess as decode_assess
        receipt=json.loads((directory/label/'decode.json').read_text())
        acceptance=decode_assess(result,receipt,(directory/label/'wsprd.stdout').read_text())
        if not acceptance['passed']:issues.extend(acceptance['issues'])
        wav=Path(receipt['command'][-1])
        details=dict(decode=acceptance,decoder_command=receipt['command'],
            decoder_exit_status=receipt['returncode'],decoder_sha256=result['decoder_sha256'],
            audio_sha256=sha256(wav),audio_path=str(wav),
            decoder_files={name:sha256(directory/label/name) for name in ('decode.json','wsprd.stdout','wsprd.stderr')})
    else:
        if not result['human_copy']['overall_screen_passed']:issues.extend(result['human_copy']['issues'])
        details=result['human_copy']
    value=dict(schema='phase15-13-assessment/1',window_id=physical['window_id'],band=physical['band'],mode=mode,
        passed=not issues,issues=issues,details=details,source_revision=physical['source_revision'],
        firmware_sha256=physical['firmware_sha256'],board=physical['board'],boot_id=physical['boot_id'],
        job_id=physical['job']['job_id'],legacy_screen_passed=result['passed'],
        analysis_sha256=sha256(directory/label/'result.json'),physical_sha256=sha256(directory/'physical.json'),
        capture_sha256=meta['output']['sha256'],metadata_sha256=sha256(directory/'capture.json'),
        resources=result['resources'],analysis_label=label)
    value['assessment_tools']={str(p.relative_to(Path(__file__).resolve().parents[2])):sha256(p) for p in
        (Path(__file__).resolve(),Path(__file__).with_name('plan.py'))}
    save(directory/('p15-13-assessment.json' if label=='analysis' else 'p15-13-'+label+'-assessment.json'),value)
    return value
