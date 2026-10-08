#!/usr/bin/env python3
"""Independent IQ analysis for actual standalone and native-controller producers."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.plan import validate_capture,accepted_events,resources
from led_closeout.runner import require,sha256
from analyze_rf_bench import load_capture
from campaign.analysis import keyed,wspr
from measure_rf_bench import baseband
from phase14.live import save


def analyze(directory,deployment=None):
    directory=Path(directory).resolve();record=json.loads((directory/'result.json').read_text())
    require(record['result']=='CONTROL_COMPLETE','producer control incomplete')
    before=record['before'];after=record['after'];boot=before['status']['boot_id']
    firmware=record.get('firmware_sha256');deployment_binding=None
    if firmware is None:
        require(deployment is not None,'producer requires its actual firmware deployment binding')
        path=Path(deployment)/'events.jsonl'
        matching=[entry['value'] for entry in (json.loads(line) for line in path.read_text().splitlines())
            if entry['kind']=='deployment_verified' and entry['value']['info']['device_id']==before['device_id'] and
            entry['value']['info']['status']['boot_id']==boot and entry['value']['info']['revision']==before['revision'] and
            entry['value']['info']['system_clock_hz']==before['system_clock_hz']]
        require(len(matching)==1,'producer deployment/device/source/boot mismatch')
        firmware=matching[0]['sha256'];deployment_binding=dict(path=str(path),sha256=sha256(path))
    require(before['device_id']==after['device_id'] and before['revision']==after['revision'] and
        after['status']['boot_id']==boot and not after['status']['enabled'] and
        not after['status']['output_active'] and after['status']['owner_id'] is None,'producer inactive successor/source')
    meta=json.loads((directory/'capture.json').read_text());validate_capture(meta,directory/'capture.cf32',record['receiver_settings'])
    require(record['capture_sha256']==sha256(directory/'capture.cf32') and record['metadata_sha256']==sha256(directory/'capture.json'),'producer capture binding')
    iq,_,capture_sha=load_capture(directory/'capture.cf32',directory/'capture.json')
    settings=record['receiver_settings'];rate=settings['sample_rate_hz'];center=settings['center_frequency_hz']
    output=directory/'analysis-producer';output.mkdir(mode=0o700)
    reports=[]
    if record['schema']=='phase14-controller/1':
        from phase14.relay import transaction
        submitted=transaction((directory/'client-to-device.bin').read_bytes(),(directory/'device-to-client.bin').read_bytes(),
            json.loads((ROOT/'docs/protocol/wtp-1.schema.json').read_text()),before['device_id'],boot,record['job_id'])
        require(submitted==record['wtp_transaction'],'controller transaction substitution')
        job=accepted_events(submitted['load_request']['body'],submitted['load_reply']['body']['adjustments'])
        frequency=next(int(v['frequency_nhz'])/1e9 for v in job['events'] if v['rf_on'])
        report=wspr(iq,rate,center,frequency,output,Path('/usr/bin/wsprd'),0,reference_hz=record['reference']['f1']) if record['mode']=='WSPR' else keyed(iq,rate,center,frequency,job)
        reports.append(report)
    elif record['schema']=='phase14-standalone/1':
        import numpy as np
        frequency=int(before['status']['schedule_base_frequency_nhz'])/1e9
        bb,brate=baseband(iq,rate,center,frequency);power=np.abs(bb)**2
        threshold=max(float(np.median(power[:round(brate*.5)]))*100,float(power.max())*.05)
        indices=np.flatnonzero(power>threshold)
        groups=np.split(indices,np.flatnonzero(np.diff(indices)>1)+1) if len(indices) else []
        groups=[g for g in groups if len(g)>brate]
        require(len(groups)==record['frames'],'standalone frame count/extra RF')
        for index,group in enumerate(groups):
            left=max(0,round((group[0]/brate-1)*rate));right=min(len(iq),round(((group[-1]+1)/brate+1)*rate))
            target=output/str(index);target.mkdir(mode=0o700)
            report=wspr(iq[left:right],rate,center,frequency,target,Path('/usr/bin/wsprd'),record['slots_utc_s'][index],reference_hz=record['reference']['f1'])
            report['capture_sample_interval']=[left,right];reports.append(report)
        require(not np.any(power[round((groups[-1][-1]+1)/brate*brate)+20:]>threshold),'standalone final RF tail')
    else:raise ValueError('unknown producer evidence')
    infos=[before]+[v['info'] for v in record['status']]+[after]
    require(all(v['revision']==before['revision'] and v['status']['boot_id']==boot for v in infos),'producer source/boot continuity')
    assessment=resources(infos,before['system_clock_hz'])
    result=dict(schema='phase14-producer-analysis/1',result_sha256=sha256(directory/'result.json'),
        capture_sha256=capture_sha,source_revision=before['revision'],firmware_sha256=firmware,
        deployment_binding=deployment_binding,boot_id=boot,device_id=before['device_id'],
        reports=reports,resources=assessment,passed=all(r['passed'] for r in reports) and assessment['passed'],
        release_qualified=False,tools={str(Path(__file__).relative_to(ROOT)):sha256(__file__)},
        limitations=['Nominal receiver axes; reference subtraction does not discipline Pico frequency.',
            'Retained operational screens and raw failures; no filtered-output or calibrated power claim.'])
    save(output/'result.json',result)
    return dict(passed=result['passed'],frames=len(reports),source_revision=before['revision'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('--deployment',type=Path)
    args=parser.parse_args();print(json.dumps(analyze(args.directory,args.deployment)))
