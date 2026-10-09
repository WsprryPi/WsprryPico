#!/usr/bin/env python3
"""Four finite B hour jobs requalifying repaired browser cadence; original soak retained."""
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
from phase14.plan import validate_physical,resources
from led_closeout.runner import require,sha256
from phase14_soak_analyze import browser_load


def idle_return(windows):
    if (len(windows)!=4 or any(len(w)!=3 for w in windows) or
        any(type(n) is not int or not 0<=n<2**64 for w in windows for n in w)):
        raise ValueError('four equivalent three-sample byte windows required')
    pairs=[]
    for first in (0,1):
        last=first+2;before,after=windows[first],windows[last]
        pairs.append(dict(first_job=first,last_job=last,median_growth_bytes=statistics.median(after)-statistics.median(before),
            before_spread_bytes=max(before)-min(before),after_spread_bytes=max(after)-min(after)))
    return dict(passed=all(p['median_growth_bytes']<=1024 and max(p['before_spread_bytes'],p['after_spread_bytes'])<=1024 for p in pairs),pairs=pairs)


def acquire(output,credentials,original):
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(output.resolve().is_relative_to((ROOT/'build').resolve()),'private repeat evidence')
    old=json.loads((original/'result.json').read_text())
    require(old['schema']=='phase14-soak/1' and old['result']=='CONTROL_COMPLETE' and
        old['planned_jobs']==len(old['jobs'])==8 and old['planned_rf_seconds']==28800,'closed original mixed soak required')
    manifest,image,_=candidate(ROOT);require(old['source_commit']==manifest['source_commit'] and old['firmware_sha256']==image['sha256'],'repeat candidate changed')
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    record=dict(schema='phase14-browser-soak-repeat/1',source_commit=manifest['source_commit'],firmware_sha256=image['sha256'],
        original_soak_summary_sha256=sha256(original/'result.json'),planned_jobs=4,planned_rf_seconds=14400,
        script_sha256=sha256(__file__),started_utc_ns=time.time_ns(),jobs=[],idle_windows=[],result='PENDING',release_qualified=False,
        purpose='Repeat only the four B browser-load cases; retain the original eight-hour mixed-soak failures and independent A evidence.')
    save(output/'result.json',record)
    for index,mode in enumerate(('TONE','FSKCW','TONE','FSKCW')):
        rig=Rig(output/str(index),ROOT,board='B',receiver=True,reference=True)
        try:
            before=rig.idle('B');rig.idle('A')
            require(before['revision']==manifest['source_commit'][:12] and before['system_clock_hz']==138000000 and before['provisioning_source']=='provisioned','repeat engineering source/clock/profile')
            p=rig.execute('B',138000000,'80m',mode,index,duration=3600,image_hash=image['sha256'],
                workload='max-events' if mode=='FSKCW' else 'normal',browser_credentials=credentials)
            v=json.loads((p/'physical.json').read_text());require(v['result']=='CONTROL_COMPLETE','repeat control failed')
            record['jobs'].append(dict(path=str(p),board='B',mode=mode,boot_id=v['boot_id'],job_id=v['job']['job_id'],
                capture_sha256=v['capture_sha256'],metadata_sha256=v['metadata_sha256'],browser_requests=len(v['browser_activity'])))
            time.sleep(45);samples=[]
            for sample in range(3):samples.append(rig.idle('B'));time.sleep(1)
            save(rig.e.root/'idle-window.json',samples)
            record['idle_windows'].append(dict(path=str(rig.e.root/'idle-window.json'),board='B',mode=mode,
                heap_allocated_bytes=[v['heap_allocated_bytes'] for v in samples],heap_available_bytes=[v['heap_available_bytes'] for v in samples]))
            save(output/'result.json',record)
        except BaseException as error:
            record.update(result='FAILED',error=repr(error),ended_utc_ns=time.time_ns());save(output/'result.json',record);raise
        finally:rig.close()
    record.update(result='CONTROL_COMPLETE',ended_utc_ns=time.time_ns());save(output/'result.json',record)
    return dict(result=record['result'],jobs=len(record['jobs']),rf_seconds=14400)


def assess(directory):
    from phase14.analysis import analyze
    record=json.loads((directory/'result.json').read_text())
    require(record['schema']=='phase14-browser-soak-repeat/1' and record['result']=='CONTROL_COMPLETE' and
        record['planned_jobs']==len(record['jobs'])==len(record['idle_windows'])==4 and record['planned_rf_seconds']==14400,'closed four-job repeat absent')
    reports=[];windows=[];boot=None
    for index,item in enumerate(record['jobs']):
        mode=('TONE','FSKCW','TONE','FSKCW')[index];p=Path(item['path']).resolve()
        require(p.parent==directory/str(index) and p.is_relative_to(directory),'repeat path substitution')
        v=validate_physical(json.loads((p/'physical.json').read_text()))
        require(v['board']==item['board']=='B' and v['mode']==item['mode']==mode and v['clock_hz']==138000000 and
            v['source_revision']==record['source_commit'][:12] and v['firmware_sha256']==record['firmware_sha256'] and
            v['action']=='complete' and int(v['accepted_job']['total_duration_ns'])==3600000000000 and
            len(v['accepted_job']['events'])==(512 if mode=='FSKCW' else 1) and
            v['capture_sha256']==item['capture_sha256'] and v['metadata_sha256']==item['metadata_sha256'] and
            v['boot_id']==item['boot_id'] and v['job']['job_id']==item['job_id'] and
            v.get('engine_frequency_correction_ppb',0)==v.get('requested_frequency_compensation_ppb',0)==0,'repeat workload substitution')
        require(boot is None or boot==v['boot_id'],'B restarted within repeat');boot=v['boot_id']
        require(item['browser_requests']==len(v['browser_activity']) and all(s['response']['status']==200 for s in v['browser_activity']),'repeat browser count/response substitution')
        traffic=browser_load([s['utc_ns'] for s in v['browser_activity']])
        require(all(type(s.get('started_monotonic_ns')) is int and type(s.get('completed_monotonic_ns')) is int and
            s['started_monotonic_ns']<=s['completed_monotonic_ns'] for s in v['browser_activity']),'request-start cadence evidence absent')
        a=p/'analysis-browser-repeat/result.json'
        if not a.exists():analyze(p,'analysis-browser-repeat')
        report=json.loads(a.read_text())
        require(report['physical_sha256']==sha256(p/'physical.json') and report['capture_sha256']==item['capture_sha256'] and
            report['metadata_sha256']==item['metadata_sha256'] and report['job_id']==item['job_id'] and
            all(report[k]==v[k] for k in ('board','band','mode','clock_hz','source_revision','firmware_sha256','boot_id')),'repeat analysis substitution')
        idle=record['idle_windows'][index];idle_path=Path(idle['path']).resolve()
        require(idle_path==directory/str(index)/'idle-window.json' and idle['board']=='B' and idle['mode']==mode,'repeat idle substitution')
        samples=json.loads(idle_path.read_text())
        require(len(samples)==3 and all(s['device_id']==v['device_id'] and s['revision']==v['source_revision'] and
            s['status']['boot_id']==boot and s['status']['output_active'] is False and s['status']['owner_id'] is None and
            s['status']['enabled'] is False for s in samples),'repeat idle boundary')
        allocated=[s['heap_allocated_bytes'] for s in samples]
        require(allocated==idle['heap_allocated_bytes'] and [s['heap_available_bytes'] for s in samples]==idle['heap_available_bytes'],'repeat idle counter substitution')
        windows.append(allocated);idle_resources=resources([v['before'],*samples],138000000)
        reports.append(dict(index=index,mode=mode,physical_sha256=sha256(p/'physical.json'),analysis_sha256=sha256(a),idle_sha256=sha256(idle_path),
            browser_load=traffic,resources=report['resources'],idle_resources=idle_resources,disposition=report['disposition'],human_copy=report.get('human_copy')))
    growth=idle_return(windows)
    result=dict(schema='phase14-browser-soak-repeat-assessment/1',summary_sha256=sha256(directory/'result.json'),script_sha256=sha256(__file__),
        jobs=reports,idle_growth=growth,browser_load_passed=all(r['browser_load']['passed'] for r in reports),
        resources_passed=growth['passed'] and all(r['resources']['passed'] and r['idle_resources']['passed'] for r in reports),
        rf_human_aware_passed=all(r['human_copy']['overall_screen_passed'] if r['mode']=='FSKCW' else r['disposition']=='OPERATIONAL_SCREEN_PASS' for r in reports),
        release_qualified=False,limitation='Four additional one-hour B jobs; does not relabel the original eight-hour soak as passing its browser-load assertion.')
    target=directory/'assessment.json';require(not target.exists(),'immutable repeat assessment exists');save(target,result)
    return {k:result[k] for k in ('browser_load_passed','resources_passed','rf_human_aware_passed','release_qualified')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('run','analyze'));p.add_argument('--output',type=Path,required=True)
    p.add_argument('--browser-credentials',type=Path);p.add_argument('--original-soak',type=Path);a=p.parse_args();os.umask(0o077)
    def interrupted(signum,frame):signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    if a.operation=='run':
        require(a.browser_credentials is not None and a.original_soak is not None,'credentials and closed original soak required')
        print(json.dumps(acquire(a.output,a.browser_credentials,a.original_soak)))
    else:print(json.dumps(assess(a.output.resolve())))
