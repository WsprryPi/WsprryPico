"""Offline aborted-waveform envelope and remaining-silence analysis."""

def envelope(power,rate,requested_duration_s):
    import numpy as np
    if (not np.isfinite(rate) or rate<=0 or not np.isfinite(requested_duration_s) or
        requested_duration_s<=1 or len(power)<rate or not np.isfinite(power).all() or np.any(power<0)):
        raise ValueError('finite abort envelope required')
    threshold=max(float(np.median(power[:round(rate*.5)]))*100,float(np.max(power))*.05,np.finfo(float).tiny)
    active=np.flatnonzero(power>threshold)
    groups=np.split(active,np.flatnonzero(np.diff(active)>1)+1) if len(active) else []
    # Preserve all samples in the off comparison, including sub-10 ms bursts.
    groups=[g for g in groups if len(g)>=10]
    issues=[];intervals=[[float(g[0]/rate),float((g[-1]+1)/rate)] for g in groups]
    if len(intervals)!=1:return dict(passed=False,issues=['exactly one acquired abort burst required'],intervals_s=intervals)
    left,right=intervals[0];duration=right-left
    if left<.5 or len(power)/rate-right<.5:issues.append('independent leading/trailing quiet absent')
    if not .2<duration<requested_duration_s-.5:issues.append('abort did not truncate its requested waveform')
    on=power[round((left+.08)*rate):round((right-.08)*rate)]
    before=power[:max(0,round((left-.02)*rate))];after=power[round((right+.02)*rate):]
    if not len(on) or not len(before) or not len(after):issues.append('independent envelope windows absent');contrast=None
    else:
        contrast=float(10*np.log10(max(float(np.median(on)),1e-300)/max(float(np.max(before)),float(np.max(after)),1e-300)))
        if contrast<10:issues.append('RF resolved outside aborted interval')
    return dict(passed=not issues,issues=issues,intervals_s=intervals,observed_duration_s=duration,
        minimum_on_to_all_off_db=contrast,detector_sample_period_s=1/rate,
        edge_exclusion_s=.02,remaining_quiet_s=len(power)/rate-right)
