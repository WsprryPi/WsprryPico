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


def collect(root,source_revision=None):
    import re
    if source_revision is not None and not re.fullmatch('[0-9a-f]{12}',source_revision):
        raise ValueError('exact 12-character firmware source required')
    root=Path(root).resolve();observations=[];attempts=[]
    for path in sorted(root.rglob('physical.json')):
        value=json.loads(path.read_text());attempt=dict(path=str(path.relative_to(root)),sha256=digest(path),
            result=value['result'],board=value['board'],band=value['band'],mode=value['mode'],clock_hz=value['clock_hz'],
            source_revision=value['source_revision'],firmware_sha256=value['firmware_sha256'],boot_id=value['boot_id'],
            job_id=value['job']['job_id'],action=value['action'],workload=value.get('workload','normal'),
            engine_frequency_correction_ppb=value.get('engine_frequency_correction_ppb',0),
            requested_frequency_compensation_ppb=value.get('requested_frequency_compensation_ppb',0))
        attempts.append(attempt)
        analyses=sorted(path.parent.glob('analysis*/result.json'))
        for analysis in analyses:
            report=json.loads(analysis.read_text())
            if report['physical_sha256']!=attempt['sha256']:raise ValueError('analysis/physical substitution')
            if any(report[key]!=attempt[key] for key in ('board','band','mode','clock_hz','source_revision','firmware_sha256','boot_id','job_id')):
                raise ValueError('analysis candidate/job substitution')
            m=report.get('measurement',report);fits=m.get('measurements',[])
            observation=dict(attempt_path=attempt['path'],analysis_path=str(analysis.relative_to(root)),
                analysis_sha256=digest(analysis),disposition=report['disposition'],board=report['board'],
                band=report['band'],mode=report['mode'],clock_hz=report['clock_hz'],source_revision=report['source_revision'],
                firmware_sha256=report['firmware_sha256'],boot_id=report['boot_id'],job_id=report['job_id'],
                action=attempt['action'],workload=attempt['workload'],
                engine_frequency_correction_ppb=attempt['engine_frequency_correction_ppb'],
                requested_frequency_compensation_ppb=attempt['requested_frequency_compensation_ppb'],
                capture_sha256=report['capture_sha256'],metadata_sha256=report['metadata_sha256'],
                decoded=report.get('decoded'),issues=m.get('issues',[]),spectrum=report.get('spectrum'),
                resources=report.get('resources'),limitations=report['limitations'],tools=report['tools'])
            if report.get('human_copy'):
                human=report['human_copy']
                observation['human_copy']={k:human[k] for k in ('schema','passed','overall_screen_passed','issues',
                    'operator_amendment','legacy_screen_passed','diagnostic_issues','method','limitations') if k in human}
                observation['human_copy']['frequency_state_pairs']=[{k:pair[k] for k in
                    ('before_event_index','after_event_index','expected_jump_hz','observed_jump_hz','before_interval_s','after_interval_s')
                    if k in pair} for pair in human.get('frequency_state_pairs',[])]
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
        row['observations']=[n for n,v in enumerate(observations) if all(v[k]==row[k] for k in ('band','mode','clock_hz')) and
            v['action']=='complete' and v['workload']=='normal' and v['engine_frequency_correction_ppb']==0 and
            v['requested_frequency_compensation_ppb']==0 and (source_revision is None or v['source_revision']==source_revision)]
        if row['disposition']!='UNSUPPORTED_CONFIGURATION' and row['observations']:
            # Operational screens are checkpoints; this index cannot promote release support.
            legacy='SCREEN_FAIL' if any(observations[n]['disposition']=='OPERATIONAL_SCREEN_FAIL' for n in row['observations']) else 'SCREEN_PASS_RELEASE_UNQUALIFIED'
            row['legacy_screen_disposition']=legacy
            if row['mode'] in ('QRSS','FSKCW','DFCW'):
                assessed=[n for n in row['observations'] if 'human_copy' in observations[n]]
                row['human_copy_observations']=assessed
                row['disposition']=('HUMAN_COPY_NOT_ASSESSED' if not assessed else
                    'HUMAN_COPY_SCREEN_PASS_RELEASE_UNQUALIFIED' if all(observations[n]['human_copy'].get('overall_screen_passed') is True for n in assessed) else
                    'HUMAN_COPY_SCREEN_FAIL')
            else:row['disposition']=legacy
    return dict(schema='phase14-public-index/1',phase14_complete=False,release_qualified=False,
        path='each Pico GP2 and GPSDO -20 dB -> combiner -> -40 dB -> RSP1B; no antenna; no LPF',
        filtering_responsibility='operator',selected_matrix_source_revision=source_revision,
        matrix_policy='Baseline natural-completion normal workloads with zero correction/compensation only; all historical and special-workload observations remain separately retained.',
        attempts=attempts,observations=observations,matrix=rows)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--source-revision');a=p.parse_args();value=collect(a.root,a.source_revision)
    with a.output.open('x') as out:json.dump(value,out,indent=2,allow_nan=False);out.write('\n')
    print(json.dumps(dict(attempts=len(value['attempts']),analyses=len(value['observations']),rows=len(value['matrix']))))


if __name__=='__main__':main()
