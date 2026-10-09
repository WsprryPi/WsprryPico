"""Frozen source-derived candidate matrix and complete local jobs."""
from campaign.plan import BANDS, CLOCKS, MODES, GOLDEN37, make_job, digest

BOARDS = {'A': ('0BF4B4AEC9FFB344','fd6127d11d6aca42a9905fa3fb1bf1d5'),
          'B': ('CDDBF8767C506C07','29f20b7342051ef947aa56cb9d4fab42')}


def matrix():
    return [dict(clock_hz=clock,band=band,frequency_hz=frequency,mode=mode,
                 disposition='NOT_TESTED' if frequency < clock//2-6 else 'UNSUPPORTED_CONFIGURATION')
            for clock in CLOCKS for band,frequency in BANDS.items() for mode in MODES]


def job(mode, band, clock, token, duration_s=None, workload="normal"):
    value=make_job(mode,BANDS[band],sample_rate_hz=clock,keyed_dot_ns=3000000000)
    if workload=='max-events':
        if mode!='FSKCW' or type(duration_s) is not int or not 128<=duration_s<=3600:
            raise ValueError('maximum-event workload requires finite FSKCW')
        total=duration_s*1000000000
        edges=[total*i//512 for i in range(513)]
        value['events']=[dict(offset_ns=str(a),duration_ns=str(b-a),rf_on=True,
            frequency_nhz=str((BANDS[band]-(5 if i%2 else 0))*1000000000))
            for i,(a,b) in enumerate(zip(edges,edges[1:]))]
        value['total_duration_ns']=str(total)
    elif workload!='normal':
        raise ValueError('unknown qualification workload')
    elif duration_s is not None:
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


def load_workspace_bytes(value):
    """Host preflight for the existing target frame/decode reserve, not a limit change."""
    import json
    request=dict(type='request',protocol='WTP/1',session_id='0'*32,
                 request_id='0'*32,op='LOAD',body=value)
    payload=json.dumps(request,separators=(',', ':'),allow_nan=False).encode()
    if not 1<=len(payload)<=65536:
        raise ValueError('LOAD exceeds fixed WTP payload limit')
    # Target keeps input resident beside its 32 KiB decoder workspace and
    # separate 32 KiB authority reserve. Allow another 4 KiB for HELLO/CLAIM
    # and paged allocation overhead. The input parser's independent 8 KiB INFO
    # allowance is already below the 32 KiB decode workspace and is not added
    # a second time. Target admission remains authoritative after preflight.
    return len(payload)+16+32768+32768+4096


def capture_elapsed_limit(sample_count, sample_rate_hz):
    """Bound sampling plus CF32 hashing/cleanup; never extend the local RF job.

    The capture helper checks its elapsed limit after hashing and cleanup too.
    Allow finalization at 32 MiB/s (below the observed roughly 99 MB/s), plus
    startup/cleanup margin. Small captures retain at least 30 seconds of margin.
    """
    if (type(sample_count) is not int or sample_count<=0 or
        type(sample_rate_hz) is not int or sample_rate_hz<=0):
        raise ValueError('positive integer capture count and rate required')
    seconds=(sample_count+sample_rate_hz-1)//sample_rate_hz
    hashing=(sample_count*8+32*1024*1024-1)//(32*1024*1024)
    return seconds+max(30,hashing+15)


def validate_capture(metadata, iq, expected):
    from pathlib import Path
    import hashlib
    if (metadata.get('resolved_device')!={'driver':'sdrplay','serial':'2404058C60'} or
        metadata.get('actual_settings')!=expected or metadata.get('overflow_count')!=0 or
        metadata.get('clipping',{}).get('sample_count')!=0 or
        metadata.get('primary_outcome')!='success' or metadata.get('cleanup',{}).get('outcome')!='verified' or
        metadata.get('output',{}).get('complete') is not True):
        raise ValueError('receiver identity/settings/integrity')
    if (type(metadata.get('requested_sample_count')) is not int or
        type(metadata.get('retained_sample_count')) is not int or
        metadata['requested_sample_count']<=0 or
        metadata['requested_sample_count']!=metadata['retained_sample_count']):
        raise ValueError('complete requested capture count required')
    path=Path(iq)
    if path.stat().st_size!=metadata['retained_sample_count']*8 or path.stat().st_size!=metadata['output']['size_bytes']:
        raise ValueError('capture sample count')
    with path.open('rb') as stream:
        if hashlib.file_digest(stream,'sha256').hexdigest()!=metadata['output']['sha256']:
            raise ValueError('capture hash')


def validate_spectral_window(before, after, boot_id, job_id):
    """A tuned on capture must remain inside one continuously running job."""
    for status in (before, after):
        if (status['state'] != 'running' or status['output_active'] is not True or
            status['boot_id'] != boot_id or status['job_id'] != job_id):
            raise ValueError('spectral capture extends outside its running job')


def validate_physical(value):
    """Reject substituted device, source, boot, workload and lifecycle evidence."""
    import re
    board=value['board']
    if (value['schema']!='phase14-physical/1' or board not in BOARDS or
        (value['serial'],value['device_id'])!=BOARDS[board] or
        value['clock_hz'] not in CLOCKS or value['band'] not in BANDS or
        value['mode'] not in MODES or value['divider']!=1 or value['rf_gp']!=2 or
        value['engine']!='pio-dma-gp2' or value['result']!='CONTROL_COMPLETE' or
        not re.fullmatch('[0-9a-f]{12}',value['source_revision']) or
        not re.fullmatch('[0-9a-f]{64}',value['firmware_sha256']) or
        not re.fullmatch('[0-9a-f]{32}',value['boot_id'])):
        raise ValueError('physical candidate/device identity')
    submitted=value['job'];accepted=value['accepted_job']
    if submitted['mode'].upper()!=value['mode']:
        raise ValueError('declared mode differs from submitted job')
    if accepted!=accepted_events(submitted,value['load']['adjustments']):
        raise ValueError('accepted workload binding')
    if 'output_route' in value:
        from phase14.harmonic import measurement_job
        measurement_job(value)
    if not re.fullmatch('[0-9a-f]{32}',submitted['job_id']):
        raise ValueError('submitted job identity')
    if value['load']['job_id']!=submitted['job_id'] or value['arm']['job_id']!=submitted['job_id']:
        raise ValueError('LOAD/ARM job identity')
    states=[v['status'] for v in value['status']]
    if value['action'] not in ('complete','abort','cancel','disconnect'):raise ValueError('unknown lifecycle action')
    expected='aborted' if value['action'] in ('abort','cancel') else 'complete'
    activity=(any(v['state']=='armed' for v in states) and not any(v['state']=='running' or v['output_active'] for v in states)
        if value['action']=='cancel' else any(v['state']=='running' for v in states))
    if (not states or not activity or
        any(v['boot_id']!=value['boot_id'] or v['job_id']!=submitted['job_id'] for v in states) or
        value['terminal']!=states[-1] or value['terminal']['state']!=expected or
        value['terminal']['output_active'] is not False):
        raise ValueError('terminal job/boot/output binding')
    for key in ('before','after'):
        info=value[key];status=info['status']
        if (info['device_id']!=value['device_id'] or info['revision']!=value['source_revision'] or
            info['system_clock_hz']!=value['clock_hz'] or status['boot_id']!=value['boot_id'] or
            status['engine']!=value['engine'] or status['output_active'] is not False or
            status['owner_id'] is not None or status['enabled'] is not False or
            status['state'] in ('loaded','armed','running','failed')):
            raise ValueError('candidate idle successor binding')
    if value.get('reference'):
        r=value['reference']
        if (r['serial']!='0673ED0FA107' or not all(r[k] for k in ('sat_lock','pll_lock','ant_ok','out1')) or
            r['pps1'] or r['f1']!=BANDS[value['band']]-40000):
            raise ValueError('reference identity/settings binding')
    return value


def resources(infos,clock):
    """Evaluate observed current-boot authority reserve and RF fault counters."""
    if not infos:raise ValueError('resource samples absent')
    fields=('allocator_failures','tls_allocation_failures','dma_errors','exhausted_successor_links',
            'refill_invalid_reserves','refill_irq_unpaired','core0_stack_fault_status','core1_stack_fault_status',
            'flash_read_failures','flash_erase_failures','flash_program_failures')
    import copy
    import re
    def counter(value):
        if type(value) is int and 0<=value<2**64:return value
        if type(value) is str and re.fullmatch('0|[1-9][0-9]*',value) and int(value)<2**64:return int(value)
        raise ValueError('invalid unsigned resource counter')
    infos=copy.deepcopy(infos)
    for info in infos:
        for field in fields+('heap_available_bytes','heap_allocated_bytes','max_refill_irq_to_ready_ns'):
            info[field]=counter(info[field])
    issues=[];baseline=infos[0]
    for info in infos:
        if info['system_clock_hz']!=clock or info['status']['boot_id']!=baseline['status']['boot_id']:
            raise ValueError('resource clock/boot substitution')
        for field in fields:
            if info[field]!=baseline[field]:issues.append('new '+field)
        if not info['core0_stack_guard_valid'] or not info['core1_stack_guard_valid']:
            issues.append('stack guard invalid')
        if info['heap_available_bytes']<32768:issues.append('authority reserve below 32 KiB')
        if info['max_refill_irq_to_ready_ns']>=16384*32*1000000000/clock:
            issues.append('refill misses full-buffer period')
    return dict(passed=not issues,issues=sorted(set(issues)),samples=len(infos),
        minimum_observed_heap_available_bytes=min(v['heap_available_bytes'] for v in infos),
        maximum_refill_irq_to_ready_ns=max(v['max_refill_irq_to_ready_ns'] for v in infos),
        full_buffer_period_ns=16384*32*1000000000/clock,
        idle_allocated_delta_bytes=infos[-1]['heap_allocated_bytes']-baseline['heap_allocated_bytes'],
        limitation='Observed INFO samples and cumulative per-boot high-water counters; same-shape normalized idle windows required for growth assertions.')
