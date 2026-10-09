#!/usr/bin/env python3
"""Retain exact external decodes and acquire only missing main-matrix WSPR frames."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from phase14.plan import BANDS,validate_physical,validate_capture
from phase14.wspr_decode import assess
from led_closeout.runner import require,sha256
from phase14.live import save


def collect(directory):
    observations=[];rows=[]
    for p in sorted(directory.rglob('physical.json')):
        v=json.loads(p.read_text())
        if v.get('mode')!='WSPR':continue
        validate_physical(v)
        require(v['clock_hz']==138000000 and v['source_revision']=='bd45bc1bb638' and
            v['action']=='complete' and v.get('workload','normal')=='normal' and
            v.get('engine_frequency_correction_ppb',0)==v.get('requested_frequency_compensation_ppb',0)==0,'original main-matrix configuration')
        a=p.parent/'analysis-acceptance/result.json';r=json.loads(a.read_text())
        require(r['physical_sha256']==sha256(p) and r['capture_sha256']==v['capture_sha256'] and
            r['metadata_sha256']==v['metadata_sha256'] and r['job_id']==v['job']['job_id'] and
            all(r[k]==v[k] for k in ('board','band','mode','clock_hz','source_revision','firmware_sha256','boot_id')),'original analysis substitution')
        meta=p.parent/'capture.json';metadata=json.loads(meta.read_text())
        validate_capture(metadata,p.parent/'capture.cf32',v['receiver_settings'])
        require(sha256(meta)==v['metadata_sha256'] and metadata['output']['sha256']==v['capture_sha256'],'original metadata/capture substitution')
        receipt=a.parent/'decode.json';stdout=a.parent/'wsprd.stdout'
        decoded=json.loads(receipt.read_text());command=decoded.get('command',[])
        require(len(command)==6 and command[:4]==['/usr/bin/wsprd','-d','-H','-f'] and
            command[4]==str((BANDS[v['band']]-1500)/1e6) and Path(command[5]).parent==a.parent,'original decoder invocation substitution')
        require(r['decoder_sha256']==sha256('/usr/bin/wsprd'),'original external decoder binary changed')
        accepted=assess(r,decoded,stdout.read_text())
        observations.append(dict(board=v['board'],band=v['band'],clock_hz=v['clock_hz'],job_id=v['job']['job_id'],
            physical_path=str(p),physical_sha256=sha256(p),analysis_sha256=sha256(a),capture_sha256=v['capture_sha256'],
            metadata_sha256=v['metadata_sha256'],decoder_receipt_sha256=sha256(receipt),decoder_stdout_sha256=sha256(stdout),
            decoder_sha256=r['decoder_sha256'],decoder_audio_sha256=sha256(command[5]),
            acceptance=accepted,resources_passed=r['resources']['passed'],legacy_disposition=r['disposition']))
    for board in ('A','B'):
        for band,f in BANDS.items():
            if f>=138000000//2-6:continue
            found=[v for v in observations if v['board']==board and v['band']==band]
            require(1<=len(found)<=3 and len({v['job_id'] for v in found})==len(found),'one to three unique original frames required')
            rows.append(dict(board=board,band=band,clock_hz=138000000,decoded_frames=sum(v['acceptance']['passed'] for v in found),
                accepted=all(v['acceptance']['passed'] for v in found),resources_passed=all(v['resources_passed'] for v in found),
                original_frames=len(found),missing_repetitions=3-len(found),observations=found))
    require(len(observations)==42 and len(rows)==26,'exact closed original WSPR matrix required')
    return dict(schema='phase14-wspr-amended-matrix/1',source_revision='bd45bc1bb638',script_sha256=sha256(__file__),
        original_matrix=str(directory),observations=len(observations),accepted_rows=sum(r['accepted'] for r in rows),
        missing_repetitions=sum(r['missing_repetitions'] for r in rows),rows=rows,release_qualified=False,
        method='Operator 2026-10-09 external expected-message decode acceptance; original RF diagnostic flags retained unchanged.')


def acquire(output,original,assessment):
    from phase14.candidate import candidate
    from phase14.live import Rig
    from phase14.analysis import analyze
    require(os.geteuid()==0 and sys.platform.startswith('linux'),'Linux exclusive bench owner')
    require(output.resolve().is_relative_to((ROOT/'build').resolve()),'private repetition evidence')
    r=json.loads(assessment.read_text())
    require(r['schema']=='phase14-wspr-amended-matrix/1' and r['original_matrix']==str(original.resolve()) and
        r['observations']==42 and r['accepted_rows']==26 and r['missing_repetitions']==36 and
        all(row['accepted'] and row['resources_passed'] for row in r['rows']),'accepted immutable original matrix required')
    for row in r['rows']:
        for o in row['observations']:
            p=Path(o['physical_path']);require(p.is_relative_to(original.resolve()) and sha256(p)==o['physical_sha256'],'original row binding changed')
    manifest,image,_=candidate(ROOT)
    require(manifest['source_commit'][:12]==r['source_revision'],'same runtime candidate required')
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    record=dict(schema='phase14-wspr-missing-repetitions/1',source_commit=manifest['source_commit'],firmware_sha256=image['sha256'],
        original_assessment_sha256=sha256(assessment),planned_jobs=36,jobs=[],result='PENDING',release_qualified=False)
    save(output/'result.json',record)
    for board in ('A','B'):
        rig=Rig(output/board,ROOT,board=board,receiver=True,reference=True)
        try:
            before=rig.idle(board);rig.idle('B' if board=='A' else 'A')
            require(before['revision']==manifest['source_commit'][:12] and before['system_clock_hz']==138000000,'same candidate source/clock')
            sequence=0
            for row in r['rows']:
                if row['board']!=board:continue
                for repeat in range(row['missing_repetitions']):
                    sequence+=1;p=rig.execute(board,138000000,row['band'],'WSPR',sequence,image_hash=image['sha256'])
                    analyze(p,'analysis-wspr-repetition')
                    v=json.loads((p/'analysis-wspr-repetition/result.json').read_text())
                    record['jobs'].append(dict(board=board,band=row['band'],path=str(p),analysis_sha256=sha256(p/'analysis-wspr-repetition/result.json'),
                        acceptance=v['wspr_decode_acceptance'],resources=v['resources'],legacy_disposition=v['disposition']))
                    save(output/'result.json',record)
                    require(v['wspr_decode_acceptance']['passed'] and v['resources']['passed'],'repeat decode/resource failure retained')
        except BaseException as error:
            record.update(result='FAILED',error=repr(error));save(output/'result.json',record);raise
        finally:rig.close()
    require(len(record['jobs'])==36,'missing repetition count')
    record['result']='CONTROL_ANALYSIS_COMPLETE';save(output/'result.json',record)
    return dict(result=record['result'],jobs=36,combined_decoded_frames=78,combined_three_frame_rows=26,release_qualified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('operation',choices=('collect','run'))
    p.add_argument('--original',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--assessment',type=Path);a=p.parse_args();os.umask(0o077)
    def interrupted(signum,frame):signal.signal(signum,signal.SIG_IGN);raise InterruptedError('signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    if a.operation=='collect':
        require(not a.output.exists(),'immutable matrix assessment exists');r=collect(a.original.resolve());save(a.output,r)
        print(json.dumps({k:r[k] for k in ('observations','accepted_rows','missing_repetitions','release_qualified')}))
    else:
        require(a.assessment is not None,'bound matrix assessment required')
        print(json.dumps(acquire(a.output,a.original,a.assessment)))
