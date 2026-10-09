#!/usr/bin/env python3
"""Finite both-board 2 m third-harmonic trial at all supported clocks; no firmware change."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.live import Rig,save
from phase14.candidate import candidate
from phase14.harmonic import ROUTE
from phase14.wspr_segment import verified_pilot
from led_closeout.runner import require,sha256


def main():
    from phase14.analysis import analyze
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--pilot',type=Path,required=True);a=p.parse_args()
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(a.output.resolve().is_relative_to((ROOT/'build').resolve()),'private harmonic evidence')
    manifest,image,_=candidate(ROOT,138000000)
    pilot=verified_pilot(a.pilot,ROOT,manifest['source_commit'],image['sha256'])
    os.umask(0o077);a.output.mkdir(parents=True,mode=0o700,exist_ok=False)
    record=dict(schema='phase14-harmonic-trial/1',output_route=ROUTE,script_sha256=sha256(__file__),
        planned_initial_rows=30,maximum_new_jobs=40,pilot_sha256=sha256(a.pilot),jobs=[],rows=[],result='PENDING',release_qualified=False,
        limitation='Receive-axis harmonic qualification trial; native 2 m application frequency mapping remains unimplemented.')
    save(a.output/'result.json',record)
    for clock in (138000000,132000000,150000000):
        manifest,image,uf2=candidate(ROOT,clock)
        for board in ('A','B'):
            rig=Rig(a.output/(str(clock)+'-'+board),ROOT,board=board,receiver=True,reference=True)
            try:
                rig.image_hash=image['sha256']
                if rig.idle(board)['system_clock_hz']!=clock:rig.deploy(board,uf2,manifest['source_commit'])
                require(rig.idle(board)['revision']==manifest['source_commit'][:12],'harmonic runtime source binding')
                sequence=0
                for mode in ('TONE','WSPR','QRSS','FSKCW','DFCW'):
                    if clock==138000000 and mode=='WSPR':
                        reused=[entry for entry in pilot['jobs'] if entry['board']==board]
                        record['rows'].append(dict(board=board,clock_hz=clock,mode=mode,observations=len(reused),
                            accepted=True,resources_passed=True,required_repetitions=3,release_qualified=False,
                            reused_pilot_observations=reused))
                        save(a.output/'result.json',record);continue
                    assessments=[];repeats=3 if clock==138000000 and mode!='TONE' else 1
                    for repeat in range(repeats):
                        sequence+=1;directory=rig.execute(board,clock,'2m',mode,sequence,image_hash=image['sha256'],output_harmonic=3)
                        analyze(directory,'analysis-third-harmonic');r=json.loads((directory/'analysis-third-harmonic/result.json').read_text())
                        accepted=(r['wspr_decode_acceptance']['passed'] if mode=='WSPR' else
                            r['human_copy']['overall_screen_passed'] if mode!='TONE' else r['disposition']=='OPERATIONAL_SCREEN_PASS')
                        entry=dict(board=board,clock_hz=clock,mode=mode,path=str(directory),analysis_sha256=sha256(directory/'analysis-third-harmonic/result.json'),
                            accepted=accepted,resources=r['resources'],wspr_decode_acceptance=r.get('wspr_decode_acceptance'),
                            human_copy=r.get('human_copy'),legacy_disposition=r['disposition'])
                        record['jobs'].append(entry);assessments.append(entry);save(a.output/'result.json',record)
                        if not accepted:break
                    record['rows'].append(dict(board=board,clock_hz=clock,mode=mode,observations=len(assessments),
                        accepted=all(v['accepted'] for v in assessments),resources_passed=all(v['resources']['passed'] for v in assessments),
                        required_repetitions=repeats,release_qualified=False))
                    save(a.output/'result.json',record)
                rig.inventory([board])
            except BaseException as error:
                record.update(result='FAILED',error=repr(error));save(a.output/'result.json',record);raise
            finally:rig.close()
    manifest,image,uf2=candidate(ROOT,138000000)
    for board in ('A','B'):
        rig=Rig(a.output/('return-138-'+board),ROOT,board=board,receiver=True)
        try:rig.image_hash=image['sha256'];rig.deploy(board,uf2,manifest['source_commit']);rig.inventory([board])
        finally:rig.close()
    record['result']='FINITE_HARMONIC_TRIAL_COMPLETE';save(a.output/'result.json',record)
    print(json.dumps(dict(result=record['result'],jobs=len(record['jobs']),rows=len(record['rows']),release_qualified=False)))


if __name__=='__main__':
    def interrupted(signum,frame):signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted);main()
