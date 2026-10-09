#!/usr/bin/env python3
"""Quick both-board 2 m WSPR pilot; frequency placement and drift are annotations."""
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
from phase14.wspr_segment import assess,pilot_decision
from led_closeout.runner import require,sha256


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    a.output=a.output.resolve()
    require(a.output.is_relative_to((ROOT/'build').resolve()),'private pilot evidence')
    from phase14.analysis import analyze
    # Invoke the existing reference CLI as a bounded child, retaining its complete receipts.
    import subprocess
    def reference(label):
        target=a.output/label
        subprocess.run([sys.executable,str(ROOT/'scripts/phase14_reference.py'),'--output',str(target),'--band','2m'],check=True,timeout=900)
        return target/'comparison.json'
    os.umask(0o077);a.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    manifest,image,_=candidate(ROOT,138000000)
    record=dict(schema='phase14-wspr-pilot/1',source_commit=manifest['source_commit'],firmware_sha256=image['sha256'],
        output_route=ROUTE,planned_frames_per_board=3,planned_jobs=6,jobs=[],result='PENDING',release_qualified=False,
        script_sha256=sha256(__file__),limitation='Short decode pilot; full qualification is conditional and native 2 m application mapping remains unimplemented.')
    save(a.output/'result.json',record)
    try:
        before=reference('reference-before')
        for board in ('A','B'):
            rig=Rig(a.output/board,ROOT,board=board,receiver=True,reference=True)
            try:
                info=rig.idle(board)
                require(info['revision']==manifest['source_commit'][:12] and info['system_clock_hz']==138000000,'138 MHz pilot candidate source/clock')
                for index in range(3):
                    directory=rig.execute(board,138000000,'2m','WSPR',index,image_hash=image['sha256'],output_harmonic=3)
                    analyze(directory,'analysis-wspr-pilot');r=json.loads((directory/'analysis-wspr-pilot/result.json').read_text())
                    entry=dict(board=board,path=str(directory),analysis_sha256=sha256(directory/'analysis-wspr-pilot/result.json'),
                        job_id=r['job_id'],boot_id=r['boot_id'],decode_passed=r['wspr_decode_acceptance']['passed'],resources_passed=r['resources']['passed'])
                    decoded=directory/'analysis-wspr-pilot'
                    entry['decoder_files_sha256']={name:sha256(decoded/name) for name in ('decode.json','wsprd.stdout','wsprd.stderr')}
                    wav=Path(r['decode']['command'][-1]).resolve()
                    require(wav.parent==decoded.resolve(),'pilot decoder audio binding')
                    entry['wav']=dict(path=str(wav),sha256=sha256(wav))
                    record['jobs'].append(entry);save(a.output/'result.json',record)
                    if not entry['decode_passed'] or not entry['resources_passed']:break
            finally:rig.close()
        after=reference('reference-after');refs=[json.loads(p.read_text()) for p in (before,after)]
        record['reference_brackets']=[dict(path=str(p),sha256=sha256(p)) for p in (before,after)]
        for entry in record['jobs']:
            path=Path(entry['path'])/'analysis-wspr-pilot/result.json'
            require(sha256(path)==entry['analysis_sha256'],'immutable pilot analysis changed')
            entry['segment']=assess(json.loads(path.read_text()),refs)
        record.update(result='CONTROL_ANALYSIS_COMPLETE',decision=pilot_decision(record['jobs']))
        save(a.output/'result.json',record)
        print(json.dumps(dict(result=record['result'],decision=record['decision'])))
    except BaseException as error:
        record.update(result='FAILED',error=repr(error));save(a.output/'result.json',record);raise


if __name__=='__main__':
    def interrupted(signum,frame):signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted);main()
