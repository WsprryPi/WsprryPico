#!/usr/bin/env python3
"""Eight finite one-hour jobs with mixed RF, network/browser load and retained IQ."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.live import Rig,save
from phase14.candidate import candidate
from led_closeout.runner import require


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--browser-credentials',type=Path,required=True);args=parser.parse_args()
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(args.output.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    manifest,image,_=candidate(ROOT);os.umask(0o077)
    args.output.mkdir(mode=0o700,parents=True,exist_ok=False)
    def interrupted(signum,frame):
        signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    summary=dict(schema='phase14-soak/1',source_commit=manifest['source_commit'],firmware_sha256=image['sha256'],
        planned_jobs=8,planned_rf_seconds=28800,started_utc_ns=time.time_ns(),jobs=[],idle_windows=[],result='PENDING',release_qualified=False)
    save(args.output/'result.json',summary)
    for index in range(8):
        board='A' if index%2==0 else 'B';mode='TONE' if (index//2)%2==0 else 'FSKCW'
        rig=Rig(args.output/str(index),ROOT,board=board,receiver=True,reference=True)
        try:
            before=rig.idle(board);rig.idle('B' if board=='A' else 'A')
            require(before['revision']==manifest['source_commit'][:12] and before['system_clock_hz']==138000000,'soak candidate source/clock')
            path=rig.execute(board,138000000,'80m',mode,index,duration=3600,image_hash=image['sha256'],
                workload='max-events' if mode=='FSKCW' else 'normal',browser_credentials=args.browser_credentials if board=='B' else None)
            physical=json.loads((path/'physical.json').read_text())
            require(physical['result']=='CONTROL_COMPLETE','soak job failed; isolate affected run')
            summary['jobs'].append(dict(path=str(path),board=board,mode=mode,boot_id=physical['boot_id'],job_id=physical['job']['job_id'],
                capture_sha256=physical['capture_sha256'],metadata_sha256=physical['metadata_sha256'],browser_requests=len(physical['browser_activity'])))
            # Identical post-release wait/sample cadence. Compare the mature same-mode
            # windows (jobs 0 vs 4, 1 vs 5, 2 vs 6, 3 vs 7), preserving cache history.
            time.sleep(45);samples=[]
            for sample in range(3):samples.append(rig.idle(board));time.sleep(1)
            save(rig.e.root/'idle-window.json',samples)
            summary['idle_windows'].append(dict(path=str(rig.e.root/'idle-window.json'),board=board,mode=mode,
                heap_allocated_bytes=[s['heap_allocated_bytes'] for s in samples],heap_available_bytes=[s['heap_available_bytes'] for s in samples]))
            save(args.output/'result.json',summary)
        except BaseException as error:
            summary.update(result='FAILED',error=repr(error),ended_utc_ns=time.time_ns());save(args.output/'result.json',summary);raise
        finally:rig.close()
    summary.update(result='CONTROL_COMPLETE',ended_utc_ns=time.time_ns());save(args.output/'result.json',summary)
    print(json.dumps(dict(result=summary['result'],jobs=len(summary['jobs']),rf_seconds=28800)))


if __name__=='__main__':main()
