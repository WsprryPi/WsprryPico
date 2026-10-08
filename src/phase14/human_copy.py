"""Operator-amended human-copy assessment, separate from legacy phase/drift screens."""
import math

DIAGNOSTICS={
    'keyed carrier continuity, frequency or coherence failed',
    'keyed state frequency residual failed',
    'keyed frequency separation failed',
    'keyed frequency transition fit residual exceeds 0.15 Hz',
}


def assess(report,job):
    issues=[v for v in report.get('issues',[]) if v not in DIAGNOSTICS]
    marks=[(i,e) for i,e in enumerate(job['events']) if e['rf_on']]
    measurements=report.get('measurements',[])
    if not marks or not report.get('observed_intervals_s') or report.get('alignment_s') is None:
        issues.append('complete aligned RF envelope required')
    if [m['event_index'] for m in measurements]!=[i for i,_ in marks]:
        issues.append('every requested RF mark must be measured')
    for m in measurements:
        if m.get('active_interior_complete') is not True:
            issues.append('interrupted RF mark or continuity not assessed')
        for key in ('contrast_db','amplitude_min_ratio','indicated_hz'):
            if not math.isfinite(m[key]):issues.append('nonfinite mark measurement')
        if m['contrast_db']<10 or m['amplitude_min_ratio']<.5:
            issues.append('RF mark contrast or amplitude inadequate')
    states={e['frequency_nhz'] for _,e in marks}
    pairs=report.get('human_frequency_state_pairs',[])
    mode=job['mode'].upper()
    if mode in ('FSKCW','DFCW'):
        if len(states)!=2:issues.append('two distinct accepted frequency states required')
        expected_pairs=[(a,b) for (a,e),(b,f) in zip(marks,marks[1:]) if e['frequency_nhz']!=f['frequency_nhz']]
        if [(p['before_event_index'],p['after_event_index']) for p in pairs]!=expected_pairs or not pairs:
            issues.append('frequency-state distinction not assessed')
        for pair in pairs:
            a,b=pair['before_event_index'],pair['after_event_index']
            requested=(int(job['events'][b]['frequency_nhz'])-int(job['events'][a]['frequency_nhz']))/1e9
            observed=pair['observed_jump_hz']
            if pair['expected_jump_hz']!=requested:issues.append('frequency-state job substitution')
            # The requested 5 Hz states must remain visibly ordered and retain
            # at least half their separation near each change. Common smooth
            # drift across the complete message is reported independently.
            if not math.isfinite(observed) or requested*observed<=0 or abs(observed)<abs(requested)/2:
                issues.append('frequency states collapsed, reversed or insufficiently distinct')
    elif mode!='QRSS':raise ValueError('human-copy assessment requires QRSS family')
    return dict(schema='phase14-human-copy/1',passed=not issues,issues=sorted(set(issues)),
        operator_amendment='2026-10-08: QRSS, FSKCW and DFCW are copied by humans; drift is not an immediate failure.',
        legacy_screen_passed=report.get('passed',False),legacy_issues=report.get('issues',[]),
        diagnostic_issues=[v for v in report.get('issues',[]) if v in DIAGNOSTICS],
        frequency_state_pairs=pairs,
        method='Retain 20 ms envelope/transition timing, acquired continuous marks, >=10 dB contrast, amplitude >=0.5 and independent final silence; locally ordered frequency states retain >=half requested separation.',
        limitations=['Evidence of reproduced human-copy marks/states; no formal human listening study.',
                    'Phase residual, smooth drift and nominal carrier error remain separate diagnostics; no calibrated absolute-frequency claim.'])
