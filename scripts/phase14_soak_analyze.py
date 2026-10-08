#!/usr/bin/env python3
"""Assess every finite soak job and equivalent idle windows without promoting RF failures."""
import argparse
import json
from pathlib import Path
import statistics
import re
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]


def idle_growth(windows):
    if len(windows)!=8 or any(len(w)!=3 for w in windows):
        raise ValueError('eight equivalent three-sample windows required')
    if any(type(n) is not int or not 0<=n<2**64 for w in windows for n in w):
        raise ValueError('unsigned allocated-byte observations required')
    pairs=[]
    for first in range(4):
        last=first+4;before=windows[first];after=windows[last]
        pairs.append(dict(first_job=first,last_job=last,before_bytes=before,after_bytes=after,
            median_growth_bytes=statistics.median(after)-statistics.median(before),
            before_spread_bytes=max(before)-min(before),after_spread_bytes=max(after)-min(after)))
    issues=[]
    for pair in pairs:
        if max(pair['before_spread_bytes'],pair['after_spread_bytes'])>1024:
            issues.append('idle observations unstable: '+str(pair['first_job']))
        if pair['median_growth_bytes']>1024:
            issues.append('equivalent idle allocation growth exceeds 1024 bytes: '+str(pair['first_job']))
    return dict(passed=not issues,issues=issues,pairs=pairs,
        method='Compare median of three samples after identical 45-second idle; reject spreads or positive growth above 1024 bytes.')


def assess(directory,analysis_name='analysis-soak',assessment_name='assessment'):
    from phase14.analysis import analyze
    from phase14.plan import validate_physical,resources
    from phase14.live import save
    from led_closeout.runner import require,sha256
    require(re.fullmatch('[a-z][a-z0-9-]{0,63}',analysis_name),'safe immutable analysis label')
    require(re.fullmatch('[a-z][a-z0-9-]{0,63}',assessment_name),'safe immutable assessment label')
    directory=directory.resolve();summary=json.loads((directory/'result.json').read_text())
    require(summary['schema']=='phase14-soak/1' and summary['result']=='CONTROL_COMPLETE' and
        summary['planned_jobs']==8 and summary['planned_rf_seconds']==28800 and
        len(summary['jobs'])==len(summary['idle_windows'])==8,'complete finite soak absent')
    reports=[];windows=[];boots={}
    for index,item in enumerate(summary['jobs']):
        path=Path(item['path']).resolve();board='A' if index%2==0 else 'B'
        mode='TONE' if (index//2)%2==0 else 'FSKCW'
        require(path.parent==directory/str(index) and path.is_relative_to(directory),'soak path substitution')
        physical=validate_physical(json.loads((path/'physical.json').read_text()))
        require(physical['board']==item['board']==board and physical['mode']==item['mode']==mode and
            physical['source_revision']==summary['source_commit'][:12] and
            physical['firmware_sha256']==summary['firmware_sha256'] and physical['clock_hz']==138000000 and
            physical['action']=='complete' and int(physical['accepted_job']['total_duration_ns'])==3600000000000 and
            physical.get('engine_frequency_correction_ppb',0)==physical.get('requested_frequency_compensation_ppb',0)==0 and
            physical['capture_sha256']==item['capture_sha256'] and physical['metadata_sha256']==item['metadata_sha256'] and
            physical['boot_id']==item['boot_id'] and physical['job']['job_id']==item['job_id'],'soak workload identity')
        require(len(physical['accepted_job']['events'])==(512 if mode=='FSKCW' else 1),'soak event limit workload')
        require(board not in boots or boots[board]==physical['boot_id'],'soak board restarted')
        boots[board]=physical['boot_id']
        if board=='B':
            require(item['browser_requests']==len(physical['browser_activity']) and item['browser_requests']>=300,
                'sustained browser activity absent')
            times=[v['utc_ns'] for v in physical['browser_activity']]
            require(times[-1]-times[0]>=3500000000000,'browser activity does not span the hour')
        output=path/analysis_name/'result.json'
        if not output.exists():analyze(path,analysis_name)
        report=json.loads(output.read_text())
        require(report['physical_sha256']==sha256(path/'physical.json') and
            report['capture_sha256']==physical['capture_sha256'] and
            report['metadata_sha256']==physical['metadata_sha256'] and
            all(report[k]==physical[k] for k in ('board','band','mode','clock_hz','source_revision','firmware_sha256','boot_id')) and
            report['job_id']==physical['job']['job_id'],'soak analysis substitution')
        idle=summary['idle_windows'][index];idle_path=Path(idle['path']).resolve()
        require(idle_path==directory/str(index)/'idle-window.json' and idle['board']==board and idle['mode']==mode,
                'idle window substitution')
        samples=json.loads(idle_path.read_text());require(len(samples)==3,'idle sample count')
        require(all(s['device_id']==physical['device_id'] and s['revision']==physical['source_revision'] and
            s['status']['boot_id']==physical['boot_id'] and s['status']['output_active'] is False and
            s['status']['owner_id'] is None and s['status']['enabled'] is False for s in samples),'idle identity/output')
        allocated=[s['heap_allocated_bytes'] for s in samples]
        require(allocated==idle['heap_allocated_bytes'] and [s['heap_available_bytes'] for s in samples]==idle['heap_available_bytes'],
                'idle resource substitution')
        windows.append(allocated)
        idle_resources=resources([physical['before'],*samples],138000000)
        reports.append(dict(index=index,board=board,mode=mode,physical_sha256=sha256(path/'physical.json'),
            analysis_sha256=sha256(output),disposition=report['disposition'],resources=report['resources'],
            idle_resources=idle_resources,idle_sha256=sha256(idle_path),browser_requests=item['browser_requests'],
            human_copy=report.get('human_copy'),
            waveform_issues=report.get('measurement',report).get('issues',[])))
    growth=idle_growth(windows)
    result=dict(schema='phase14-soak-assessment/1',source_commit=summary['source_commit'],
        firmware_sha256=summary['firmware_sha256'],summary_sha256=sha256(directory/'result.json'),
        script_sha256=sha256(__file__),jobs=reports,idle_growth=growth,
        resources_passed=growth['passed'] and all(r['resources']['passed'] and r['idle_resources']['passed'] for r in reports),
        all_rf_screens_passed=all(r['disposition']=='OPERATIONAL_SCREEN_PASS' for r in reports),
        all_rf_human_aware_screens_passed=(all(r['human_copy']['overall_screen_passed'] if r['mode']=='FSKCW' else
            r['disposition']=='OPERATIONAL_SCREEN_PASS' for r in reports) if
            all(r['human_copy'] is not None for r in reports if r['mode']=='FSKCW') else None),
        release_qualified=False)
    output=directory/(assessment_name+'.json');require(not output.exists(),'immutable soak assessment already exists')
    save(output,result)
    return {k:result[k] for k in ('resources_passed','all_rf_screens_passed','all_rf_human_aware_screens_passed','release_qualified')}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    p.add_argument('--analysis-name',default='analysis-soak')
    p.add_argument('--assessment-name',default='assessment');a=p.parse_args()
    print(json.dumps(assess(a.directory,a.analysis_name,a.assessment_name)))
