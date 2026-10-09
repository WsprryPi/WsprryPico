"""Explicit conducted 2 m third-harmonic trials using existing direct-frequency jobs."""
import copy
from campaign.plan import BANDS,CLOCKS,MODES,make_job,digest


ROUTE=dict(schema='phase14-output-route/1',kind='third-harmonic',harmonic=3,
    output_band='2m',requested_output_base_nhz=BANDS['2m']*1000000000,
    requested_engine_base_nhz=BANDS['2m']*1000000000//3,
    native_output_frequency_api=False)


def trial_job(mode,clock,token):
    value=make_job(mode,BANDS['2m']//3,sample_rate_hz=clock,keyed_dot_ns=3000000000)
    base=ROUTE['requested_engine_base_nhz']
    for event in value['events']:
        if event['rf_on']:
            delta=int(event['frequency_nhz'])-base
            rounded=(abs(delta)+1)//3
            event['frequency_nhz']=str(base+(rounded if delta>=0 else -rounded))
    value['job_id']=digest(dict(job=value,token=token,route=ROUTE))[:32]
    return value


def measurement_job(physical):
    """Map accepted engine frequencies onto the measured third-harmonic RF axis."""
    route=physical.get('output_route')
    if (route!=ROUTE or any(type(route[k]) is not type(ROUTE[k]) for k in ROUTE) or
        physical.get('band')!='2m' or physical.get('mode') not in MODES or physical.get('clock_hz') not in CLOCKS):
        raise ValueError('exact 2 m third-harmonic trial route required')
    if (physical.get('workload','normal')!='normal' or physical.get('action')!='complete' or
        physical.get('engine_frequency_correction_ppb',0)!=0 or physical.get('requested_frequency_compensation_ppb',0)!=0):
        raise ValueError('uncompensated natural-completion trial required')
    canonical=trial_job(physical['mode'],physical['clock_hz'],'validation')
    submitted=copy.deepcopy(physical['job']);canonical.pop('job_id');submitted.pop('job_id')
    if canonical!=submitted:raise ValueError('harmonic trial waveform substitution')
    from phase14.plan import accepted_events
    if physical['accepted_job']!=accepted_events(physical['job'],physical['load']['adjustments']):
        raise ValueError('harmonic trial accepted-frequency substitution')
    result=copy.deepcopy(physical['accepted_job'])
    for event in result['events']:
        if event['rf_on']:event['frequency_nhz']=str(3*int(event['frequency_nhz']))
    return result
