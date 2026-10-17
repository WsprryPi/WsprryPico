#!/usr/bin/env python3
"""Read-only campaign audit and sanitized matrix reduction; no device access."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from led_closeout.runner import require,sha256
from phase14.live import save
from phase14.plan import validate_capture,validate_physical
from phase15_13.plan import plan,repair_plan,fskcw_repair_plan,FREQUENCIES


def same_slice(parent,child,start,stop):
    with parent.open('rb') as source,child.open('rb') as target:
        source.seek(start*8)
        remaining=(stop-start)*8
        while remaining:
            count=min(1048576,remaining)
            require(source.read(count)==target.read(count),'derived samples differ from original capture')
            remaining-=count
        require(target.read(1)==b'','extra derived samples')


def report(first,second,final,focused):
    roots={'8m':first,'5m':final}
    rows=[];frames=[];parents={};armed=[]
    for root in (first,second,final,focused):
        for line in (root/'events.jsonl').read_text().splitlines():
            event=json.loads(line)
            if event['kind']=='planned_window_armed':armed.append(event['value']['id'])
    expected=[w['id'] for w in plan()['windows']]
    omitted=['P15.13-A-5m-WSPR-2','P15.13-A-5m-WSPR-3']
    diagnostic=[w['id'] for w in repair_plan()['windows']+fskcw_repair_plan()['windows']]
    require(sorted(armed)==sorted([v for v in expected if v not in omitted]+diagnostic) and
            len(set(armed))==16,'actual nominal/diagnostic window accounting differs from retained ARMs')
    for window in plan()['windows']:
        actual=window
        root=roots[window['band']]
        if window['band']=='5m' and window['mode']=='TONE':root=second
        if window['band']=='5m' and window['mode']=='WSPR':
            actual=repair_plan()['windows'][window['repetition']-1];root=focused
        if window['band']=='5m' and window['mode']=='FSKCW':
            actual=fskcw_repair_plan()['windows'][0];root=focused
        directory=root/(actual['id'] if window['mode']=='WSPR' else window['band']+'-'+window['mode'])
        physical=json.loads((directory/'physical.json').read_text())
        validate_physical(physical,band_frequencies=FREQUENCIES)
        require(physical['source_revision']=='165303458e49' and physical['firmware_sha256']==
                'cb6ccfa3e9354d84c5ca3c993f4965f70716ed8bd99b076011406199fa1850eb',
                'selected source/image differs from fresh candidate')
        require(physical['job']==actual['job'],'frozen nominal or focused-retest job changed')
        metadata=json.loads((directory/'capture.json').read_text())
        validate_capture(metadata,directory/'capture.cf32',physical['receiver_settings'])
        if window['mode']=='WSPR':
            derivation=metadata['derivation'];parent=Path(derivation['parent_path'])
            if parent not in parents:
                meta=json.loads((parent/'capture.json').read_text())
                validate_capture(meta,parent/'capture.cf32',physical['receiver_settings'])
                parents[parent]=meta
            require(derivation['parent_capture_sha256']==parents[parent]['output']['sha256'] and
                    derivation['parent_metadata_sha256']==sha256(parent/'capture.json'), 'parent hash substitution')
            same_slice(parent/'capture.cf32',directory/'capture.cf32',*derivation['sample_range'])
        nominal=json.loads((directory/'p15-13-assessment.json').read_text())
        selected=nominal;condition='nominal receiver audio tuning'
        if window['mode']=='WSPR':
            offset=125 if window['band']=='8m' else 200
            path=directory/('p15-13-receiver-plus'+str(offset)+'hz-assessment.json')
            if path.exists():
                selected=json.loads(path.read_text());condition='fixed +'+str(offset)+' Hz receiver audio translation of original IQ'
            frames.append(dict(window_id=actual['id'],planned_window_id=window['id'],
                nominal_receiver_tuning_passed=nominal['passed'],capture_role='focused_retest' if actual is not window else 'original',
                accepted_passed=selected['passed'],condition=condition,
                decoder=selected['details'],nominal_assessment_sha256=sha256(directory/'p15-13-assessment.json')))
        require(selected['window_id']==actual['id'] and selected['physical_sha256']==sha256(directory/'physical.json') and
                selected['capture_sha256']==metadata['output']['sha256'] and
                selected['metadata_sha256']==sha256(directory/'capture.json'),'assessment substitution')
        analysis=directory/selected['analysis_label']/'result.json'
        require(selected['analysis_sha256']==sha256(analysis),'assessment analysis changed')
        if window['mode']=='WSPR':
            details=selected['details'];require(details['decoder_exit_status']==0 or not selected['passed'],'decoder exit mismatch')
            require(sha256(details['audio_path'])==details['audio_sha256'],'decoder audio changed')
            for name,digest in details['decoder_files'].items():
                require(sha256(analysis.parent/name)==digest,'decoder receipt or stdout changed')
            from phase14.wspr_decode import assess as decode_assess
            decoded=decode_assess(json.loads(analysis.read_text()),json.loads((analysis.parent/'decode.json').read_text()),
                                  (analysis.parent/'wsprd.stdout').read_text())
            require(decoded['passed']==selected['details']['decode']['passed'] and
                    (not selected['passed'] or decoded['passed']),
                    'actual external decoding differs from selected assessment')
        rows.append(dict(window_id=actual['id'],planned_window_id=window['id'],diagnostic=actual is not window,
            band=window['band'],mode=window['mode'],
            boot_id=physical['boot_id'],source_revision=physical['source_revision'],firmware_sha256=physical['firmware_sha256'],
            frequency_hz=window['frequency_hz'],status='Qualified' if selected['passed'] else 'Unqualified',
            condition=condition,physical_sha256=sha256(directory/'physical.json'),capture_sha256=metadata['output']['sha256'],
            metadata_sha256=sha256(directory/'capture.json'),analysis_sha256=selected['analysis_sha256'],
            details=selected['details'],resources=selected['resources'],evidence_path=str(directory)))
    restoration=json.loads((focused/'restoration.json').read_text())
    require(restoration['settings_restored'] is True and not restoration['cleanup_errors'],'restoration incomplete')
    info=restoration['boards']['A'];other=restoration['boards']['B']
    require(info['status']['allow_unqualified_frequency'] is False and
            info['status']['allow_non_amateur_frequency'] is False and
            all(not v['status']['output_active'] and v['status']['owner_id'] is None and
                not v['status']['enabled'] for v in (info,other)),'final flags/ownership/output/scheduling mismatch')
    cells=[]
    for band in FREQUENCIES:
        for mode in ('TONE','WSPR','QRSS','FSKCW','DFCW'):
            observed=[r for r in rows if r['band']==band and r['mode']==mode]
            cells.append(dict(band=band,mode=mode,frequency_hz=FREQUENCIES[band],
                status='Qualified' if all(r['status']=='Qualified' for r in observed) else 'Unqualified',
                windows=[r['window_id'] for r in observed],condition=observed[0]['condition']))
    manifest_path=first.parents[2]/'manifest.json'
    manifest=json.loads(manifest_path.read_text())
    return dict(schema='phase15-13-result-matrix/1',source_revision='165303458e49feaac1de54c8344058f56578d533',
        source_artifact_manifest_sha256=sha256(manifest_path),sdk_commit=manifest['sdk'],
        toolchain=manifest['toolchain'].splitlines()[0],picotool_commit=manifest['picotool_source'],
        elf_sha256=manifest['artifacts']['WsprryPico-StandaloneRF.elf']['sha256'],
        firmware_version='0.0.0-devel',firmware_sha256=info.get('firmware_sha256',restoration['firmware_sha256']),
        board='A',serial='0BF4B4AEC9FFB344',device_id=info['device_id'],boot_id=info['status']['boot_id'],
        clock_hz=138000000,engine='pio-dma-gp2',gpio=2,cells=cells,observations=rows,wspr_frames=frames,
        boot_scope='Every observation retains its actual boot; top-level boot_id is the final retained state.',
        accounting=dict(nominal_planned=14,nominal_armed=12,nominal_control_complete=11,
                        nominal_untransmitted=omitted,nominal_invalid_capture=['P15.13-A-5m-WSPR-1'],
                        nominal_observer_aborted=['P15.13-A-5m-FSKCW-1'],
                        diagnostic_rf_windows=4,total_rf_windows=16,pre_arm_non_rf_load_failures=2,
                        note='The original 5 m sequence did not qualify: first RF frame completed, receiver acquisition became incomplete at the next LOAD, and two original slots were not transmitted. A separately planned three-frame waveform-equivalent diagnostic provides the accepted 5 m sequence; one FSKCW diagnostic follows its preserved RENEW-timeout observer abort.'),
        independent_raw_audit=dict(parent_captures=len(parents),child_slices_verified=6,
                                    all_capture_hashes_verified=True,all_child_samples_byte_identical=True),
        restoration=dict(receipt_sha256=sha256(focused/'restoration.json'),verified=True,
            A=dict(revision=info['revision'],clock_hz=info['system_clock_hz'],boot_id=info['status']['boot_id'],
                   enabled=False,owner=None,output_active=False,experimental_flags=False),
            B=dict(revision=other['revision'],boot_id=other['status']['boot_id'],used_for_rf=False)),
        limits=['Exact two conducted points on Pico A, unfiltered attenuator/combiner path.',
                'Receiver audio conditions are part of WSPR acceptance; nominal failures remain.',
                'No calibrated absolute RF/time/power, LPF, antenna, both-board or alternate-clock qualification.'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--first',type=Path,required=True);parser.add_argument('--second',type=Path,required=True)
    parser.add_argument('--final',type=Path,required=True)
    parser.add_argument('--focused',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=report(args.first,args.second,args.final,args.focused);save(args.output,result)
    print(json.dumps(dict(cells=result['cells'],accounting=result['accounting'])),flush=True)
