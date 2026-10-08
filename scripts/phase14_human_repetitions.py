#!/usr/bin/env python3
"""Assess retained QRSS-family captures and finish missing human-copy repetitions."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.analysis import analyze
from phase14.candidate import candidate
from phase14.live import Rig,save
from phase14.plan import BANDS
from led_closeout.runner import require,sha256


def assess(directory):
    output=directory/'analysis-human-copy/result.json'
    if not output.exists():analyze(directory,'analysis-human-copy')
    report=json.loads(output.read_text());physical=json.loads((directory/'physical.json').read_text())
    require(report['physical_sha256']==sha256(directory/'physical.json') and
        report['capture_sha256']==physical['capture_sha256'] and report['metadata_sha256']==physical['metadata_sha256'] and
        all(report[k]==physical[k] for k in ('board','band','mode','clock_hz','source_revision','firmware_sha256','boot_id')) and
        report['job_id']==physical['job']['job_id'],'human repetition analysis substitution')
    require(report.get('human_copy',{}).get('schema')=='phase14-human-copy/1','explicit amended assessment absent')
    return dict(path=str(directory),physical_sha256=report['physical_sha256'],analysis_sha256=sha256(output),
        job_id=report['job_id'],boot_id=report['boot_id'],legacy_disposition=report['disposition'],
        human_copy_passed=report['human_copy']['overall_screen_passed'],issues=report['human_copy']['issues'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(a.output.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    source=a.input_root.resolve();rows=json.loads((source/'rows.json').read_text())
    require(len(rows)==104 and len({(r['board'],r['band'],r['mode']) for r in rows})==104,'finished predecessor matrix required')
    manifest,image,_=candidate(ROOT);os.umask(0o077)
    def interrupted(signum,frame):
        signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
    a.output.mkdir(parents=True,exist_ok=False,mode=0o700);results=[]
    for board in ('A','B'):
        physicals=[]
        for path in (source/board).glob('*/physical.json'):
            value=json.loads(path.read_text())
            if value['result']=='CONTROL_COMPLETE' and value['action']=='complete' and value['mode'] in ('QRSS','FSKCW','DFCW'):
                require(value['board']==board and value['clock_hz']==138000000 and
                    value['source_revision']==manifest['source_commit'][:12] and value['firmware_sha256']==image['sha256'] and
                    value.get('workload','normal')=='normal' and value.get('engine_frequency_correction_ppb',0)==0 and
                    value.get('requested_frequency_compensation_ppb',0)==0,'retained baseline candidate substitution')
                physicals.append((path.parent,value))
        rig=Rig(a.output/board,ROOT,board=board,receiver=True,reference=True)
        try:
            before=rig.idle(board);rig.idle('B' if board=='A' else 'A')
            require(before['revision']==manifest['source_commit'][:12] and before['system_clock_hz']==138000000,'live amended candidate')
            sequence=0
            for band in BANDS:
                if BANDS[band]>=138000000//2-6:continue
                for mode in ('QRSS','FSKCW','DFCW'):
                    retained=sorted((path for path,v in physicals if v['band']==band and v['mode']==mode),key=lambda x:int(x.name.split('-',1)[0]))
                    observations=[assess(path) for path in retained]
                    if all(v['human_copy_passed'] is True for v in observations):
                        for _ in range(max(0,3-len(observations))):
                            sequence+=1
                            try:directory=rig.execute(board,138000000,band,mode,sequence,image_hash=image['sha256'])
                            except (ValueError,TimeoutError,ConnectionError) as error:
                                rig.device.close_peer(board);rig.idle(board)
                                observations.append(dict(control_failure=repr(error),human_copy_passed=False));break
                            observation=assess(directory);observations.append(observation)
                            if observation['human_copy_passed'] is not True:break
                    row=dict(board=board,band=band,mode=mode,observations=observations,
                        result='REPEATED_HUMAN_COPY_SCREEN_PASS' if len(observations)>=3 and
                            all(v['human_copy_passed'] is True for v in observations) else 'HUMAN_COPY_FAILED_OR_UNRESOLVED',
                        release_qualified=False)
                    results.append(row);save(a.output/'rows.json',results);print(json.dumps(row),flush=True)
            rig.inventory([board])
        finally:rig.close()
    print(json.dumps(dict(result='FINITE_HUMAN_REPETITIONS_FINISHED',rows=len(results),release_qualified=False)))


if __name__=='__main__':main()
