"""Informational frequency placement; never determine mode or band acceptance."""
import math
from campaign.plan import GOLDEN37
from phase14.calibration import quantities

WINDOW_HZ=(144490400,144490600)
HALF_MAIN_LOBE_HZ=375/512


def assess(report,references):
    measurement=report.get('measurement',{});fits=measurement.get('measurements',[])
    result=dict(schema='phase14-frequency-placement-annotation/1',window_hz=list(WINDOW_HZ),traceable_calibration=False,
        observed_relation='not_measured',qualification_effect='informational_only_no_band_exclusion',
        calibration_method_selected=False,pass_fail_determination=None,
        method='Union of per-symbol simultaneous-reference frequencies on both bracketed receiver sample scales; retain engineering frequency-estimator bounds and half-symbol-rate main-lobe guard.',
        limitations=['Wanted WSPR-component frequency envelope, not all unfiltered GPIO emission or a spectral mask.',
            'An engineering estimate with explicit reference assumption and estimator allowance, not certified frequency accuracy.',
            'Excludes 80 ms around symbol edges in the underlying phase fits; transition residual and fitted drift enter the guard.',
            'Reliability is bounded to observed boards, settings and time interval; no unlimited-temperature or elapsed-time guarantee.'])
    if len(references)!=2 or len(fits)!=162 or [f.get('index') for f in fits]!=list(range(162)):
        result['issues']=['complete 162-symbol fits and two reference brackets required'];return result
    if [f.get('tone') for f in fits]!=[int(t) for t in GOLDEN37] or measurement.get('reference_hz')!=144450500:
        raise ValueError('2 m symbol/reference substitution')
    for reference in references:
        if reference.get('band')!='2m' or reference.get('center_hz')!=144490500:raise ValueError('2 m reference bracket required')
    axes=[quantities(measurement,r) for r in references]
    if any(len(a.get('reference_subtracted_frequencies',[]))!=162 for a in axes):
        result['issues']=['simultaneous GPSDO frequency comparison absent'];return result
    estimator=[]
    for f in fits:
        duration=f['interval_s'][1]-f['interval_s'][0];r=f['reference']
        values=[duration,f['phase_residual_rms_rad'],r['phase_residual_rms_rad'],f['amplitude_min_ratio'],r['amplitude_min_ratio']]
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in values) or duration<=0:
            raise ValueError('finite frequency-estimator inputs required')
        if min(f['amplitude_min_ratio'],r['amplitude_min_ratio'])<.5 or r['phase_residual_rms_rad']>.15 or r.get('local_contrast_db',0)<20:
            result['issues']=['insufficient mark/reference quality for frequency-placement measurement'];return result
        estimator.append((f['phase_residual_rms_rad']+r['phase_residual_rms_rad'])/(math.pi*duration))
    transition=max((v['fit_rms_hz'] for v in measurement.get('transitions',[])),default=0)
    drift=measurement.get('linear_drift_hz_per_s',0)
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (transition,drift)):
        raise ValueError('finite transition/drift diagnostics required')
    estimator_bound=max(1.0,2*transition,max(estimator))
    points=[p for a in axes for p in a['reference_subtracted_frequencies']]
    frequencies=[p['frequency_hz_true_axis'] for p in points]
    reference_bound=max(p['sampling_repeatability_bound_hz']+p['reference_assumption_bound_hz'] for p in points)
    if not all(type(v) in (int,float) and math.isfinite(v) for v in frequencies+[reference_bound]) or reference_bound<0:
        raise ValueError('finite frequency/reference bounds required')
    within_symbol_drift=max(abs(drift)/(a['sampling_scale']**2)*(8192/12000)/2 for a in axes)
    guard=HALF_MAIN_LOBE_HZ+estimator_bound+reference_bound+within_symbol_drift
    observed=[min(frequencies),max(frequencies)];occupied=[observed[0]-guard,observed[1]+guard]
    margins=[occupied[0]-WINDOW_HZ[0],WINDOW_HZ[1]-occupied[1]]
    inside=min(margins)>=0
    outside=observed[0]+estimator_bound+reference_bound<WINDOW_HZ[0] or observed[1]-estimator_bound-reference_bound>WINDOW_HZ[1]
    result.update(observed_relation='estimates_inside_window' if inside else 'estimates_extend_outside_window' if outside else 'boundary_overlap_under_engineering_bound',
        observed_tone_range_hz=observed,estimated_occupied_range_hz=occupied,
        edge_clearance_hz=dict(lower=margins[0],upper=margins[1]),minimum_edge_clearance_hz=min(margins),
        observed_frequency_span_hz=observed[1]-observed[0],fitted_drift_hz_s_true_axes=[drift/a['sampling_scale']**2 for a in axes],
        estimator_allowance_hz=estimator_bound,reference_and_sampling_bound_hz=reference_bound,
        half_main_lobe_guard_hz=HALF_MAIN_LOBE_HZ,within_symbol_drift_guard_hz=within_symbol_drift,
        reference_accuracy_assumption_ppb=[a['reference_accuracy_assumption_ppb'] for a in axes],issues=[])
    result['drift_annotation']='Measured fitted drift and edge clearance are descriptive; calibration is undecided, so no drift or segment pass/fail judgement or band exclusion follows.'
    return result


def describe(report,job,mode,reference_hz=None,window_hz=None):
    """Nominal receiver-axis observation, with optional simultaneous reference.

    A QRSS operating window must be supplied explicitly; the WSPR bench point
    is not silently treated as a QRSS segment. Bracketed sample-scale bounds
    belong to assess(), rather than this descriptive nominal-axis report.
    """
    result=dict(schema='phase14-frequency-placement-annotation/1',mode=mode,
        window_hz=list(window_hz) if window_hz else None,
        observed_relation='not_measured',qualification_effect='informational_only_no_band_exclusion',
        calibration_method_selected=False,pass_fail_determination=None,
        reliability_implication='No drift reliability threshold has been selected; report the observed frequency excursion without a pass/fail determination.',
        limitations=['Nominal receiver sampling scale; no absolute calibration claim.',
            'Per-symbol/mark mean frequencies exclude edges and do not bound every intra-mark excursion or unfiltered emission.'])
    measurements=report.get('measurement',report).get('measurements',[])
    references=report.get('reference_diagnostics',[])
    points=[]
    for index,fit in enumerate(measurements):
        event=job['events'][fit.get('event_index',fit.get('index',index))]
        expected=int(event['frequency_nhz'])/1e9
        interval=fit.get('interval_s')
        value=fit.get('reference_compared_hz',fit['indicated_hz'])
        basis='simultaneous_reference_nominal_sample_axis' if 'reference_compared_hz' in fit else 'receiver_indicated_nominal_axis'
        if reference_hz is not None and len(references)==len(measurements):
            ref=references[index];value-=ref['indicated_hz']-reference_hz
            interval=ref['interval_s'];basis='simultaneous_reference_nominal_sample_axis'
        if interval is None:
            interval=[int(event['offset_ns'])/1e9,(int(event['offset_ns'])+int(event['duration_ns']))/1e9]
        if not all(type(v) in (int,float) and math.isfinite(v) for v in (value,expected,*interval)):
            raise ValueError('finite frequency observation required')
        points.append(dict(event_index=fit.get('event_index',fit.get('index',index)),
            time_s=sum(interval)/2,frequency_hz=value,requested_offset_hz=value-expected,basis=basis))
    if not points:return result
    values=[p['frequency_hz'] for p in points];offsets=[p['requested_offset_hz'] for p in points]
    mean_t=sum(p['time_s'] for p in points)/len(points);mean_f=sum(offsets)/len(points)
    denom=sum((p['time_s']-mean_t)**2 for p in points)
    slope=sum((p['time_s']-mean_t)*(p['requested_offset_hz']-mean_f) for p in points)/denom if denom else None
    result.update(observed_relation='window_unspecified' if window_hz is None else
        'mean_frequencies_inside_window' if min(values)>=window_hz[0] and max(values)<=window_hz[1] else 'mean_frequencies_extend_outside_window',
        observations=points,observed_mean_frequency_range_hz=[min(values),max(values)],
        requested_offset_range_hz=[min(offsets),max(offsets)],requested_offset_excursion_hz=max(offsets)-min(offsets),
        fitted_offset_drift_hz_per_s=slope,measurement_span_s=max(p['time_s'] for p in points)-min(p['time_s'] for p in points))
    if window_hz:
        result['mean_frequency_edge_clearance_hz']=[min(values)-window_hz[0],window_hz[1]-max(values)]
    else:result['limitations'].append('QRSS operating segment has not been assigned in this bench workload; no segment-confinement inference.')
    return result


def pilot_decision(jobs):
    boards={b:[j for j in jobs if j['board']==b] for b in ('A','B')}
    if any(j['board'] not in boards for j in jobs):raise ValueError('named pilot boards required')
    if len({j['job_id'] for j in jobs})!=len(jobs):raise ValueError('unique pilot frames required')
    for rows in boards.values():
        if len(rows)>3:raise ValueError('at most three pilot frames per board')
    reliable=len(jobs)==6 and all(j['decode_passed'] is True for j in jobs)
    resources=len(jobs)==6 and all(j['resources_passed'] is True for j in jobs)
    return dict(schema='phase14-wspr-pilot-decision/1',expected_frames=6,frames=len(jobs),
        correct_decodes=sum(j['decode_passed'] is True for j in jobs),reliable_decode_passed=reliable,
        resources_passed=resources,expand_full_qualification=reliable and resources,
        frequency_annotations=[j.get('segment',{}).get('observed_relation','not_measured') for j in jobs],
        policy='Six of six expected-message decodes, three unique frames per named board, permit expansion after independent resource/control validity. Frequency placement and drift are informational only and never gate expansion or exclude a band.')


def verified_pilot(path,root,source_commit,image_hash):
    """Recheck retained pilot evidence before authorizing a larger RF batch."""
    import json
    from pathlib import Path
    from led_closeout.runner import require,sha256
    from phase14.plan import validate_physical,validate_capture
    from phase14.harmonic import ROUTE
    from phase14.wspr_decode import assess as decode_assess
    path=Path(path).resolve();root=Path(root).resolve()
    require(path.is_relative_to(root/'build'),'private pilot binding')
    pilot=json.loads(path.read_text())
    require(pilot['schema']=='phase14-wspr-pilot/1' and pilot['result']=='CONTROL_ANALYSIS_COMPLETE' and
        pilot['source_commit']==source_commit and pilot['firmware_sha256']==image_hash and
        pilot['output_route']==ROUTE,'completed exact pilot source/route binding')
    require(len(pilot['reference_brackets'])==2,'both pilot reference brackets required')
    for bracket in pilot['reference_brackets']:
        reference_path=Path(bracket['path']).resolve()
        require(reference_path.is_relative_to(path.parent) and sha256(reference_path)==bracket['sha256'],'pilot reference bracket changed')
    for entry in pilot['jobs']:
        directory=Path(entry['path']).resolve()
        require(directory.is_relative_to(path.parent),'pilot job path binding')
        analysis_path=directory/'analysis-wspr-pilot/result.json'
        require(sha256(analysis_path)==entry['analysis_sha256'],'immutable pilot analysis')
        analysis=json.loads(analysis_path.read_text())
        physical=validate_physical(json.loads((directory/'physical.json').read_text()))
        require(physical['result']=='CONTROL_COMPLETE' and physical['board']==entry['board'] and
            physical['band']=='2m' and physical['mode']=='WSPR' and physical['clock_hz']==138000000 and
            physical['source_revision']==source_commit[:12] and physical['firmware_sha256']==image_hash and
            physical['output_route']==ROUTE and physical['job']['job_id']==entry['job_id'] and
            physical['boot_id']==entry['boot_id'],'pilot physical identity')
        require(all(analysis[key]==physical[key] for key in
            ('board','boot_id','clock_hz','source_revision','firmware_sha256','band','mode','output_route')) and
            analysis['job_id']==entry['job_id'],'pilot analysis identity')
        validate_capture(json.loads((directory/'capture.json').read_text()),directory/'capture.cf32',physical['receiver_settings'])
        for key,name in (('capture_sha256','capture.cf32'),('metadata_sha256','capture.json'),('physical_sha256','physical.json')):
            require(analysis[key]==sha256(directory/name),'pilot analysis capture/physical binding')
        receipt=json.loads((analysis_path.parent/'decode.json').read_text())
        require(set(entry['decoder_files_sha256'])=={'decode.json','wsprd.stdout','wsprd.stderr'} and
            all(sha256(analysis_path.parent/name)==digest for name,digest in entry['decoder_files_sha256'].items()),'pilot decoder files changed')
        wav=Path(entry['wav']['path']).resolve()
        require(wav.parent==analysis_path.parent and wav.suffix=='.wav' and
            sha256(wav)==entry['wav']['sha256'] and receipt['command']==
            ['/usr/bin/wsprd','-d','-H','-f',str((144490500-1500)/1e6),str(wav)],'pilot actual decoder command/audio')
        acceptance=decode_assess(analysis,receipt,(analysis_path.parent/'wsprd.stdout').read_text())
        require(acceptance['passed'] is entry['decode_passed'] and
            analysis['wspr_decode_acceptance']['passed'] is entry['decode_passed'] and
            analysis['resources']['passed'] is entry['resources_passed'],'actual pilot decode/resource evidence')
        require(analysis['decoder_sha256']==sha256('/usr/bin/wsprd'),'pilot decoder binary binding')
    decision=pilot_decision(pilot['jobs'])
    require(pilot['decision']==decision and decision['expand_full_qualification'],'reliable both-board pilot required')
    return pilot
