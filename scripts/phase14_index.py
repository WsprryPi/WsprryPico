#!/usr/bin/env python3
"""Export an allowlisted public Phase 14 index, retaining failed and pending attempts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from phase14.plan import matrix


def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def collect(root):
    root=Path(root).resolve();observations=[];attempts=[]
    for path in sorted(root.rglob('physical.json')):
        value=json.loads(path.read_text());attempt=dict(path=str(path.relative_to(root)),sha256=digest(path),
            result=value['result'],board=value['board'],band=value['band'],mode=value['mode'],clock_hz=value['clock_hz'],
            source_revision=value['source_revision'],firmware_sha256=value['firmware_sha256'],boot_id=value['boot_id'],
            job_id=value['job']['job_id'])
        attempts.append(attempt)
        analyses=sorted(path.parent.glob('analysis*/result.json'))
        for analysis in analyses:
            report=json.loads(analysis.read_text())
            if report['physical_sha256']!=attempt['sha256']:raise ValueError('analysis/physical substitution')
            m=report.get('measurement',report);fits=m.get('measurements',[])
            observation=dict(attempt_path=attempt['path'],analysis_path=str(analysis.relative_to(root)),
                analysis_sha256=digest(analysis),disposition=report['disposition'],board=report['board'],
                band=report['band'],mode=report['mode'],clock_hz=report['clock_hz'],source_revision=report['source_revision'],
                firmware_sha256=report['firmware_sha256'],boot_id=report['boot_id'],job_id=report['job_id'],
                capture_sha256=report['capture_sha256'],metadata_sha256=report['metadata_sha256'],
                decoded=report.get('decoded'),issues=m.get('issues',[]),spectrum=report.get('spectrum'),
                resources=report.get('resources'),limitations=report['limitations'],tools=report['tools'])
            for key in ('observed_duration_s','expected_duration_s','spacing_hz','fitted_spacing_hz',
                        'max_symbol_residual_hz','max_transition_error_s','fitted_drift_hz_s','alignment_s','transitions'):
                if key in m:observation[key]=m[key]
            if fits:
                indicated=[f['indicated_hz'] for f in fits]
                observation.update(indicated_frequency_range_hz=[min(indicated),max(indicated)],
                    maximum_linear_phase_residual_rad=max(f['phase_residual_rms_rad'] for f in fits))
                compared=[f['reference_compared_hz'] for f in fits if 'reference_compared_hz' in f]
                if compared:observation['reference_subtracted_frequency_range_hz']= [min(compared),max(compared)]
            observations.append(observation)
    rows=matrix()
    for row in rows:
        row['observations']=[n for n,v in enumerate(observations) if all(v[k]==row[k] for k in ('band','mode','clock_hz'))]
        if row['disposition']!='UNSUPPORTED_CONFIGURATION' and row['observations']:
            # Operational screens are checkpoints; this index cannot promote release support.
            row['disposition']='SCREEN_FAIL' if any(observations[n]['disposition']=='OPERATIONAL_SCREEN_FAIL' for n in row['observations']) else 'SCREEN_PASS_RELEASE_UNQUALIFIED'
    return dict(schema='phase14-public-index/1',phase14_complete=False,release_qualified=False,
        path='each Pico GP2 and GPSDO -20 dB -> combiner -> -40 dB -> RSP1B; no antenna; no LPF',
        filtering_responsibility='operator',attempts=attempts,observations=observations,matrix=rows)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();value=collect(a.root)
    with a.output.open('x') as out:json.dump(value,out,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps(dict(attempts=len(value['attempts']),analyses=len(value['observations']),rows=len(value['matrix']))))


if __name__=='__main__':main()
