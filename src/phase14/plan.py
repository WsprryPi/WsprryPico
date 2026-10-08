"""Frozen source-derived candidate matrix and complete local jobs."""
from campaign.plan import BANDS, CLOCKS, MODES, GOLDEN37, make_job, digest

BOARDS = {'A': ('0BF4B4AEC9FFB344','fd6127d11d6aca42a9905fa3fb1bf1d5'),
          'B': ('CDDBF8767C506C07','29f20b7342051ef947aa56cb9d4fab42')}


def matrix():
    return [dict(clock_hz=clock,band=band,frequency_hz=frequency,mode=mode,
                 disposition='NOT_TESTED' if frequency < clock//2-6 else 'UNSUPPORTED_CONFIGURATION')
            for clock in CLOCKS for band,frequency in BANDS.items() for mode in MODES]


def job(mode, band, clock, token, duration_s=None):
    value=make_job(mode,BANDS[band],sample_rate_hz=clock,keyed_dot_ns=3000000000)
    if duration_s is not None:
        if mode!='TONE' or type(duration_s) is not int or not 1<=duration_s<=3600:
            raise ValueError('duration override requires finite Tone')
        value['events'][0]['duration_ns']=str(duration_s*1000000000)
        value['total_duration_ns']=value['events'][0]['duration_ns']
    value['job_id']=digest(dict(job=value,token=token))[:32]
    return value


def accepted_events(value, adjustments):
    import copy
    result=copy.deepcopy(value)
    seen=set()
    for a in adjustments:
        i=a['event_index']
        if (type(i) is not int or i in seen or not 0<=i<len(result['events']) or
            value['events'][i].get('frequency_nhz')!=a['requested_frequency_nhz']):
            raise ValueError('accepted adjustment identity')
        seen.add(i)
        result['events'][i]['frequency_nhz']=a['realized_frequency_nhz']
    return result


def validate_capture(metadata, iq, expected):
    from pathlib import Path
    import hashlib
    if (metadata.get('resolved_device')!={'driver':'sdrplay','serial':'2404058C60'} or
        metadata.get('actual_settings')!=expected or metadata.get('overflow_count')!=0 or
        metadata.get('clipping',{}).get('sample_count')!=0 or
        metadata.get('primary_outcome')!='success' or metadata.get('cleanup',{}).get('outcome')!='verified' or
        metadata.get('output',{}).get('complete') is not True):
        raise ValueError('receiver identity/settings/integrity')
    path=Path(iq)
    if path.stat().st_size!=metadata['retained_sample_count']*8 or path.stat().st_size!=metadata['output']['size_bytes']:
        raise ValueError('capture sample count')
    with path.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=metadata['output']['sha256']:
            raise ValueError('capture hash')
