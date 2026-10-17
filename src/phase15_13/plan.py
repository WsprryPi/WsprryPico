"""The fourteen-window plan. No hardware access or historical matrix changes."""
from campaign.plan import make_job, digest, MODES

FREQUENCIES = {'8m': 40001000, '5m': 60001000}
CLOCK = 138000000
RATE = 250000


def plan():
    windows = []
    groups = []
    for band, frequency in FREQUENCIES.items():
        for mode in MODES:
            jobs = []
            for repetition in range(3 if mode == 'WSPR' else 1):
                value = make_job(mode, frequency, keyed_dot_ns=3000000000)
                token = f'P15.13-A-{band}-{mode}-{repetition+1}'
                value['job_id'] = digest(dict(job=value, token=token))[:32]
                window = dict(id=token, band=band, mode=mode, repetition=repetition+1,
                              job=value, frequency_hz=frequency)
                windows.append(window)
                jobs.append(window)
            # WSPR first start is 8 s after capture readiness, subsequent
            # requested UTC starts are exactly 120 s apart. Capture includes all three frames.
            seconds = 370 if mode == 'WSPR' else int(value['total_duration_ns'])//1000000000 + 25
            groups.append(dict(band=band, mode=mode, windows=jobs,
                               capture_seconds=seconds, capture_bytes=seconds*RATE*8))
    return dict(schema='phase15-13-plan/1', board='A', clock_hz=CLOCK, gpio=2,
                expected_wspr=['AA0NT', 'EM18', '37'], keyed_message='ETE',
                dot_ns=3000000000, shift_hz=5, groups=groups, windows=windows,
                nominal_rf_windows=len(windows), diagnostic_rf_windows=0,
                capture_bytes=sum(g['capture_bytes'] for g in groups),
                capture_seconds=sum(g['capture_seconds'] for g in groups),
                storage_reserve_bytes=2*1024**3,
                minimum_intergroup_quiet_s=5,
                applicability='Exact conducted test points; no jurisdictional or broad-interval approval')


def validate(value):
    if digest(value) != digest(plan()):
        raise ValueError('Plan differs from the frozen fourteen-window contract')
    return value


def compact_realized_job(job,token):
    """Same sampled waveform; omit redundant boundaries and adjustment replies."""
    import copy
    result=copy.deepcopy(job);events=[]
    divisor=CLOCK*1000000000
    for event in result['events']:
        if event['rf_on']:
            increment=(int(event['frequency_nhz'])*(1<<32)+divisor//2)//divisor
            event['frequency_nhz']=str((CLOCK*increment*1000000000+(1<<31))//(1<<32))
        if events and event['rf_on']==events[-1]['rf_on'] and event.get('frequency_nhz')==events[-1].get('frequency_nhz'):
            events[-1]['duration_ns']=str(int(events[-1]['duration_ns'])+int(event['duration_ns']))
        else:events.append(event)
    result['events']=events;result['allow_frequency_adjustment']=False
    result['job_id']=digest(dict(job=result,token=token))[:32]
    return result


def repair_plan():
    """Exactly one three-frame diagnostic, after the preserved 5 m LOAD failure."""
    original=next(g for g in plan()['groups'] if g['band']=='5m' and g['mode']=='WSPR')
    import copy
    group=copy.deepcopy(original)
    for index,window in enumerate(group['windows']):
        window['id']=f'P15.13-DIAG-A-5m-WSPR-{index+1}'
        window['job']=compact_realized_job(window['job'],window['id'])
    return dict(schema='phase15-13-focused-retest/1',diagnostic_rf_windows=3,groups=[group],windows=group['windows'],
        hypothesis='Reducing complete WTP request/reply/history memory allows the same sampled waveform to finish its three consecutive frames.',
        firmware_change=False,clock_change=False,further_rf_retry=False)


def fskcw_repair_plan():
    import copy
    group=copy.deepcopy(next(g for g in plan()['groups'] if g['band']=='5m' and g['mode']=='FSKCW'))
    window=group['windows'][0];window['id']='P15.13-DIAG-A-5m-FSKCW-1'
    window['job']['job_id']=digest(dict(job=window['job'],token=window['id']))[:32]
    return dict(schema='phase15-13-fskcw-retest/1',diagnostic_rf_windows=1,groups=[group],windows=group['windows'],
        hypothesis='The original observer aborted a 35-second local job after an unnecessary RENEW timed out; a 60-second claim already covers preparation, eight-second lead and the whole job.',
        firmware_change=False,clock_change=False,further_rf_retry=False)
