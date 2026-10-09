#!/usr/bin/env python3
"""Two finite browser/FSKCW jobs with separate 45 s and cache-expired idle evidence."""
import argparse
import json
import os
from pathlib import Path
import signal
import statistics
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.live import Rig,save
from phase14.candidate import candidate
from phase14.plan import validate_physical
from phase14.profiles import durable_settings
from phase14_soak_analyze import browser_load
from led_closeout.runner import require,sha256


def compare(windows):
    require(len(windows)==2 and all(len(v)==3 for v in windows) and
        all(type(n) is int and n>=0 for v in windows for n in v),'two three-sample byte windows required')
    growth=statistics.median(windows[1])-statistics.median(windows[0])
    spreads=[max(v)-min(v) for v in windows]
    return dict(passed=growth<=1024 and max(spreads)<=1024,median_growth_bytes=growth,
        spreads_bytes=spreads,limit_bytes=1024)


def samples(rig,boot):
    values=[]
    for _ in range(3):
        v=rig.idle('B')
        require(v['status']['boot_id']==boot and v['system_clock_hz']==138000000 and
            v['revision']=='bd45bc1bb638','same-boot/source/clock idle samples required')
        values.append(v);time.sleep(1)
    return values


def acquire(output,credentials):
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    manifest,image,_=candidate(ROOT,138000000)
    require(manifest['source_commit'].startswith('bd45bc1bb638'),'unchanged campaign firmware required')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    record=dict(schema='phase14-idle-growth-followup/1',source_commit=manifest['source_commit'],
        firmware_sha256=image['sha256'],planned_jobs=2,jobs=[],result='PENDING',release_qualified=False,
        script_sha256=sha256(__file__),sampling_policy='Preserve 45 s windows and add >=350 s post-transport-closure windows; compare each policy separately at unchanged 1024-byte threshold.',
        original_failed_assessment_sha256='7bc2b0a0fc7f3c0bd5da2618057f2989a6d1f545ee355e69d3f8a78274018d49')
    save(output/'result.json',record);boot=None;settings=None
    for index in range(2):
        rig=Rig(output/str(index),ROOT,board='B',receiver=True,reference=True)
        try:
            before=rig.idle('B');rig.idle('A')
            require(before['provisioning_source']=='provisioned' and before['revision']==manifest['source_commit'][:12],
                'same engineering profile/source required')
            require(boot is None or before['status']['boot_id']==boot,'no restart between comparisons')
            require(settings is None or durable_settings(before)==settings,'unchanged persistent profile/settings required')
            settings=durable_settings(before)
            boot=before['status']['boot_id']
            directory=rig.execute('B',138000000,'80m','FSKCW',index,duration=3600,
                image_hash=image['sha256'],workload='max-events',browser_credentials=credentials)
            # execute closes its WTP peer and completes capture finalization.
            require(not rig.device.peers,'owned WTP peer must already be closed')
            ended=time.monotonic_ns();time.sleep(45)
            early=samples(rig,boot);save(rig.e.root/'idle-45.json',early)
            time.sleep(max(0,350-(time.monotonic_ns()-ended)/1e9))
            elapsed=(time.monotonic_ns()-ended)/1e9
            require(elapsed>=350 and not rig.device.peers,'declared replay-expiry observation boundary')
            settled=samples(rig,boot);save(rig.e.root/'idle-expired.json',settled)
            require(all(durable_settings(v)==settings for v in early+settled),'persistent settings changed during idle observations')
            entry=dict(index=index,path=str(directory),job_id=json.loads((directory/'physical.json').read_text())['job']['job_id'],
                boot_id=boot,post_transport_elapsed_s=elapsed,
                early_path=str(rig.e.root/'idle-45.json'),early_sha256=sha256(rig.e.root/'idle-45.json'),
                settled_path=str(rig.e.root/'idle-expired.json'),settled_sha256=sha256(rig.e.root/'idle-expired.json'))
            record['jobs'].append(entry);save(output/'result.json',record)
        except BaseException as error:
            record.update(result='FAILED',error=repr(error));save(output/'result.json',record);raise
        finally:rig.close()
    record['result']='CONTROL_COMPLETE';save(output/'result.json',record)


def assess(output):
    from phase14.analysis import analyze
    record=json.loads((output/'result.json').read_text())
    require(record['schema']=='phase14-idle-growth-followup/1' and record['result']=='CONTROL_COMPLETE' and
        len(record['jobs'])==record['planned_jobs']==2,'two completed follow-up jobs required')
    early=[];settled=[];jobs=[];boot=None
    for index,entry in enumerate(record['jobs']):
        directory=Path(entry['path']).resolve();require(directory.parent==output/str(index),'follow-up path binding')
        v=validate_physical(json.loads((directory/'physical.json').read_text()))
        require(v['board']=='B' and v['mode']=='FSKCW' and v['band']=='80m' and v['clock_hz']==138000000 and
            v['firmware_sha256']==record['firmware_sha256'] and v['source_revision']==record['source_commit'][:12] and
            v['boot_id']==entry['boot_id'] and (boot is None or boot==v['boot_id']) and
            v['job']['job_id']==entry['job_id'] and len(v['accepted_job']['events'])==512 and
            v['accepted_job']['total_duration_ns']=='3600000000000' and v['action']=='complete','follow-up workload/identity binding')
        boot=v['boot_id']
        require(entry['post_transport_elapsed_s']>=350,'cache-expiry boundary absent')
        for key,target in (('early',early),('settled',settled)):
            path=Path(entry[key+'_path']).resolve();require(path.parent==directory.parent and
                sha256(path)==entry[key+'_sha256'],'idle snapshot binding')
            values=json.loads(path.read_text())
            require(len(values)==3 and all(s['status']['boot_id']==boot and not s['status']['output_active'] and
                not s['status']['enabled'] and s['status']['owner_id'] is None and s['revision']==v['source_revision'] and
                s['system_clock_hz']==138000000 for s in values),'unchanged inactive idle identity')
            target.append([s['heap_allocated_bytes'] for s in values])
        analyze(directory,'analysis-idle-followup');a=directory/'analysis-idle-followup/result.json';r=json.loads(a.read_text())
        traffic=browser_load([s['utc_ns'] for s in v['browser_activity']])
        require(all(s['response']['status']==200 for s in v['browser_activity']),'successful browser responses required')
        jobs.append(dict(job_id=entry['job_id'],analysis_sha256=sha256(a),browser_load=traffic,
            resources_passed=r['resources']['passed'],human_copy_passed=r['human_copy']['overall_screen_passed']))
    result=dict(schema='phase14-idle-growth-followup-assessment/1',summary_sha256=sha256(output/'result.json'),
        jobs=jobs,original_45_second_policy=compare(early),expiry_normalized_policy=compare(settled),
        other_checks_passed=all(j['browser_load']['passed'] and j['resources_passed'] and j['human_copy_passed'] for j in jobs),
        release_qualified=False,limitation='Separate diagnostic/validation method. Does not relabel the original 2696-byte failure; final resource acceptance needs assessment of retention-contract applicability.')
    require(not (output/'assessment.json').exists(),'immutable assessment already exists');save(output/'assessment.json',result)
    print(json.dumps({k:result[k] for k in ('original_45_second_policy','expiry_normalized_policy','other_checks_passed')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('run','analyze'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--browser-credentials',type=Path);a=p.parse_args()
    a.output=a.output.resolve();require(a.output.is_relative_to((ROOT/'build').resolve()),'private evidence required');os.umask(0o077)
    def interrupted(signum,frame):signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    if a.operation=='run':require(a.browser_credentials is not None,'existing browser credentials required');acquire(a.output,a.browser_credentials)
    else:assess(a.output)
