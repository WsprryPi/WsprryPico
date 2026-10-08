#!/usr/bin/env python3
"""Bounded adaptive 138 MHz mode acceptance; failed screens stop that expensive row."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.live import Rig,save
from phase14.analysis import analyze
from phase14.plan import BANDS
from led_closeout.runner import require,sha256
from check_standalone_image import validate_uf2


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--wait-for',type=Path);p.add_argument('--wait-seconds',type=int,default=3600)
    a=p.parse_args();require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux bench owner')
    require(a.output.resolve().is_relative_to((ROOT/'build').resolve()),'private evidence')
    require(0<a.wait_seconds<=3600,'bounded predecessor wait')
    def interrupted(signum,frame):raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    if a.wait_for:
        end=time.monotonic()+a.wait_seconds
        while not a.wait_for.exists():
            require(time.monotonic()<end,'predecessor did not complete; no dependent RF');time.sleep(2)
        # Inventory publication is atomic; allow its device handles to close.
        time.sleep(2)
    from phase14.candidate import candidate
    manifest,image,_=candidate(ROOT);os.umask(0o077)
    a.output.mkdir(mode=0o700,parents=True,exist_ok=False);results=[]
    for board in ('A','B'):
        rig=Rig(a.output/board,ROOT,board=board,receiver=True,reference=True)
        try:
            before=rig.idle(board);rig.idle('B' if board=='A' else 'A')
            require(before['revision']==manifest['source_commit'][:12] and before['system_clock_hz']==138000000,'candidate source/clock')
            sequence=0
            for band in ('80m','2200m','630m','160m','60m','40m','30m','20m','17m','15m','12m','10m','6m'):
                for mode in ('WSPR','QRSS','FSKCW','DFCW'):
                    dispositions=[]
                    for repeat in range(3):
                        sequence+=1
                        try:
                            directory=rig.execute(board,138000000,band,mode,sequence,image_hash=image['sha256'])
                        except (ValueError,TimeoutError,ConnectionError) as error:
                            # Preserve the failed capture/control attempt. Only a
                            # verified inactive, unowned board permits independent
                            # rows to continue; uncertain RF still stops the batch.
                            rig.device.close_peer(board);rig.idle(board)
                            dispositions.append('CONTROL_ATTEMPT_FAILED')
                            rig.e.event('isolated_control_failure',dict(band=band,mode=mode,error=repr(error)))
                            break
                        try:
                            result=analyze(directory,'analysis-acceptance')
                        except ValueError as error:
                            result=dict(board=board,band=band,mode=mode,clock_hz=138000000,
                                        disposition='ANALYSIS_UNRESOLVED',error=str(error))
                            save(directory/'analysis-unresolved.json',result)
                        dispositions.append(result['disposition'])
                        print(json.dumps(result),flush=True)
                        # Initial 80 m WSPR settling repeats are explicitly required.
                        if result['disposition']!='OPERATIONAL_SCREEN_PASS' and not (band=='80m' and mode=='WSPR'):
                            break
                    row=dict(board=board,band=band,mode=mode,clock_hz=138000000,dispositions=dispositions,
                             result='REPEATED_SCREEN_PASS' if len(dispositions)==3 and all(x=='OPERATIONAL_SCREEN_PASS' for x in dispositions) else 'FAILED_SCREEN_EXCLUDED',
                             release_qualified=False)
                    results.append(row);save(a.output/'rows.json',results)
            rig.inventory([board])
        finally:rig.close()
    print(json.dumps(dict(result='BOUNDED_ACCEPTANCE_BATCH_FINISHED',rows=len(results),release_qualified=False)))


if __name__=='__main__':main()
