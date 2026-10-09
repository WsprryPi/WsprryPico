#!/usr/bin/env python3
"""Separately assess deliberate early abort and full remaining RF silence."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]


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


def assess(directory,source=ROOT):
    sys.path[:0]=[str(source/'src'),str(source/'scripts')]
    from phase14.plan import validate_physical,validate_capture,resources,BANDS
    from led_closeout.runner import require,sha256
    from phase14.live import save
    from analyze_rf_bench import load_capture
    from measure_rf_bench import baseband,phase_fit,local_contrast
    from validate_wtp_contract import frame,loads_strict,SchemaValidator
    import numpy as np
    directory=directory.resolve();physical=validate_physical(json.loads((directory/'physical.json').read_text()))
    require(physical['action']=='abort' and physical['mode']=='TONE' and
        len(physical['accepted_job']['events'])==1 and physical['accepted_job']['events'][0]['rf_on'],'single Tone abort case required')
    meta=json.loads((directory/'capture.json').read_text());validate_capture(meta,directory/'capture.cf32',physical['receiver_settings'])
    iq,_,digest=load_capture(directory/'capture.cf32',directory/'capture.json')
    require(digest==physical['capture_sha256'] and sha256(directory/'capture.json')==physical['metadata_sha256'],'abort IQ/metadata binding')
    schema=json.loads((source/'docs/protocol/wtp-1.schema.json').read_text());validator=SchemaValidator(schema)
    log=directory.parent/'events.jsonl';requests=[];infos=[physical['before']]
    for line in log.read_text().splitlines():
        e=json.loads(line)
        if e['kind']=='tx':
            wire=bytes.fromhex(e['value']['hex'])
            if wire[:4]==b'WTPF':
                require(len(wire)>=16 and wire==frame(wire[16:]),'abort wire framing/CRC')
                v=loads_strict(wire[16:].decode())
                if v['op']=='ABORT' and v['body'].get('job_id')==physical['job']['job_id']:
                    require(not validator.errors(v,schema) and v['session_id']==physical['session_id'],'abort request identity')
                    requests.append(dict(request=v,utc_ns=e['utc_ns'],monotonic_ns=e['monotonic_ns']))
        elif e['kind']=='info' and e['value']['board']==physical['board']:
            i=e['value']['info']
            if i['status']['boot_id']==physical['boot_id'] and i['status']['job_id']==physical['job']['job_id']:infos.append(i)
    require(len(requests)==1,'one actual same-job abort request required')
    running=[e for e in physical['status'] if e['status']['state']=='running' and e['status']['output_active']]
    require(running and running[0]['monotonic_ns']<requests[0]['monotonic_ns']<physical['status'][-1]['monotonic_ns'],'abort wire outside running/terminal bracket')
    settings=physical['receiver_settings'];rate=settings['sample_rate_hz'];center=settings['center_frequency_hz'];frequency=BANDS[physical['band']]
    bb,brate=baseband(iq,rate,center,frequency);assessment=envelope(np.abs(bb)**2,brate,int(physical['accepted_job']['total_duration_ns'])/1e9)
    require(assessment['passed'],'abort envelope did not establish early shutdown/full silence')
    left,right=assessment['intervals_s'][0];fit=phase_fit(bb[round((left+.08)*brate):round((right-.08)*brate)],brate,frequency)
    require(fit['phase_residual_rms_rad']<=.15 and fit['amplitude_min_ratio']>=.5,'abort burst continuity')
    require(physical.get('reference') is not None,'abort simultaneous reference required')
    ref_hz=physical['reference']['f1'];ref,_=baseband(iq,rate,center,ref_hz);ref_fit=phase_fit(ref[round((right+.1)*brate):round((right+.4)*brate)],brate,ref_hz)
    contrast=local_contrast(iq[round((right+.1)*rate):round((right+.4)*rate)],rate,center,ref_hz)
    require(contrast>=20 and ref_fit['phase_residual_rms_rad']<=.15 and ref_fit['amplitude_min_ratio']>=.5,'healthy reference after RF shutdown')
    infos.append(physical['after']);resource=resources(infos,physical['clock_hz'])
    result=dict(schema='phase14-abort-assessment/1',board=physical['board'],source_revision=physical['source_revision'],
        firmware_sha256=physical['firmware_sha256'],boot_id=physical['boot_id'],job_id=physical['job']['job_id'],
        physical_sha256=sha256(directory/'physical.json'),capture_sha256=digest,metadata_sha256=sha256(directory/'capture.json'),
        events_sha256=sha256(log),script_sha256=sha256(__file__),abort_request=requests[0],envelope=assessment,
        burst_fit=fit,reference_fit=ref_fit,reference_contrast_db=contrast,resources=resource,passed=resource['passed'],
        release_qualified=False,limitations=['Deliberate truncation is assessed separately; the original full-duration screen stays unchanged.',
            'Receiver-visible early shutdown and full captured off interval at 1 ms detector cadence; no absolute request-to-GPIO 100 ms latency qualification.'])
    output=directory/'abort-assessment.json';require(not output.exists(),'immutable abort assessment already exists');save(output,result)
    return dict(board=result['board'],passed=result['passed'],envelope=assessment)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--source',type=Path,default=ROOT);a=p.parse_args()
    print(json.dumps(assess(a.directory,a.source.resolve())))
