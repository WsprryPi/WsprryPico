#!/usr/bin/env python3
"""Finite alternative-clock mode/band screens with affected contention checks."""
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
from led_closeout.runner import require


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--browser-credentials',type=Path,required=True)
    p.add_argument('--resume-rows',type=Path);a=p.parse_args()
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(a.output.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    rows=[]
    if a.resume_rows:
        from phase14.clock_resume import resume_rows
        manifests={clock:candidate(ROOT,clock) for clock in (132000000,150000000)}
        require(len({v[0]['source_commit'] for v in manifests.values()})==1,'clock candidates differ in source')
        rows=resume_rows(a.resume_rows,manifests[132000000][0]['source_commit'],
                         {clock:value[1]['sha256'] for clock,value in manifests.items()})
    reused={(r['board'],r['clock_hz'],r['band'],r['mode']) for r in rows}
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    if a.resume_rows:
        from led_closeout.runner import sha256
        save(a.output/'resumption.json',dict(rows_sha256=sha256(a.resume_rows),rows_path=str(a.resume_rows.resolve()),
            reused_rows=len(rows),original_evidence_unchanged=True,release_qualified=False))
        save(a.output/'rows.json',rows)
    def interrupted(signum,frame):
        signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    for clock in (132000000,150000000):
        manifest,image,uf2=candidate(ROOT,clock)
        for board in ('A','B'):
            rig=Rig(a.output/(str(clock)+'-'+board),ROOT,board=board,receiver=True,reference=True)
            try:
                rig.image_hash=image['sha256'];rig.deploy(board,uf2,manifest['source_commit'])
                sequence=0
                for band,frequency in BANDS.items():
                    if frequency>=clock//2-6:
                        for mode in ('TONE','WSPR','QRSS','FSKCW','DFCW'):
                            if (board,clock,band,mode) in reused:continue
                            rows.append(dict(board=board,clock_hz=clock,band=band,mode=mode,disposition='UNSUPPORTED_CONFIGURATION'))
                        save(a.output/'rows.json',rows);continue
                    for mode in ('TONE','WSPR','QRSS','FSKCW','DFCW'):
                        if (board,clock,band,mode) in reused:continue
                        sequence+=1
                        try:directory=rig.execute(board,clock,band,mode,sequence,image_hash=image['sha256'])
                        except (ValueError,TimeoutError,ConnectionError) as error:
                            rig.device.close_peer(board);rig.idle(board)
                            row=dict(board=board,clock_hz=clock,band=band,mode=mode,disposition='ISOLATED_CONTROL_FAILURE',error=repr(error))
                        else:
                            try:analyze(directory,'analysis-clock-comparison')
                            except ValueError as error:
                                rig.idle(board)
                                row=dict(board=board,clock_hz=clock,band=band,mode=mode,path=str(directory),
                                    disposition='ANALYSIS_UNRESOLVED',error=repr(error),release_qualified=False)
                                save(directory/'analysis-unresolved.json',row)
                            else:
                                report=json.loads((directory/'analysis-clock-comparison/result.json').read_text())
                                row=dict(board=board,clock_hz=clock,band=band,mode=mode,path=str(directory),
                                    disposition=report['disposition'],human_copy=report.get('human_copy'),resources=report['resources'],release_qualified=False)
                                row['path']=str(directory.resolve())
                                if mode=='WSPR':
                                    row['legacy_screen_disposition']=row['disposition']
                                    row['wspr_decode_acceptance']=report['wspr_decode_acceptance']
                                    row['disposition']='WSPR_EXTERNAL_DECODE_PASS' if report['wspr_decode_acceptance']['passed'] else 'WSPR_EXTERNAL_DECODE_FAIL'
                        rows.append(row);save(a.output/'rows.json',rows);print(json.dumps(row),flush=True)
                sequence+=1
                directory=rig.execute(board,clock,'80m','FSKCW',sequence,image_hash=image['sha256'],duration=128,
                    workload='max-events',browser_credentials=a.browser_credentials if board=='B' else None)
                analyze(directory,'analysis-clock-contention');rig.inventory([board])
            finally:rig.close()
    # Keep the selected useful candidate installed on both boards, preserving
    # settings; final release builds and smoke remain separate work.
    manifest,image,uf2=candidate(ROOT,138000000)
    for board in ('A','B'):
        rig=Rig(a.output/('return-138-'+board),ROOT,board=board,receiver=True)
        try:
            rig.image_hash=image['sha256'];rig.deploy(board,uf2,manifest['source_commit']);rig.inventory([board])
        finally:rig.close()
    print(json.dumps(dict(result='FINITE_CLOCK_COMPARISON_COMPLETE',rows=len(rows),release_qualified=False)))


if __name__=='__main__':main()
