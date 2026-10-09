"""Rebind closed clock rows before skipping their physical acquisition."""
import copy
import json
from pathlib import Path

from led_closeout.runner import require, sha256
from phase14.plan import BANDS, BOARDS, MODES, validate_capture, validate_physical


def resume_rows(path, source_commit, image_hashes):
    path = Path(path).resolve()
    source_root = path.parents[2]
    original = json.loads(path.read_text())
    require(type(original) is list and original, 'nonempty closed clock rows required')
    rows, seen = [], set()
    for row in original:
        key = (row['board'], row['clock_hz'], row['band'], row['mode'])
        board, clock, band, mode = key
        require(board in BOARDS and clock in (132000000, 150000000) and
                band in BANDS and mode in MODES and key not in seen, 'clock resume row identity')
        seen.add(key)
        if BANDS[band] >= clock // 2 - 6:
            require(row['disposition'] == 'UNSUPPORTED_CONFIGURATION' and not row.get('path'),
                    'clock resume unsupported boundary')
            rows.append(copy.deepcopy(row))
            continue
        require(isinstance(row.get('path'), str) and row['path'] and
                row.get('disposition') not in ('UNSUPPORTED_CONFIGURATION', 'ISOLATED_CONTROL_FAILURE',
                                               'ANALYSIS_UNRESOLVED'), 'closed analyzed clock row required')
        directory = Path(row['path'])
        if not directory.is_absolute():
            directory = source_root / directory
        directory = directory.resolve()
        require(directory.is_relative_to(path.parent), 'clock resume capture path escaped campaign')
        physical_path = directory / 'physical.json'
        physical = validate_physical(json.loads(physical_path.read_text()))
        require(tuple(physical[k] for k in ('board', 'clock_hz', 'band', 'mode')) == key and
                physical['source_revision'] == source_commit[:12] and
                physical['firmware_sha256'] == image_hashes[clock] and
                physical['action'] == 'complete' and physical.get('workload', 'normal') == 'normal' and
                not physical.get('output_route') and
                physical.get('engine_frequency_correction_ppb', 0) == 0 and
                physical.get('requested_frequency_compensation_ppb', 0) == 0,
                'clock resume physical/source/workload binding')
        metadata_path = directory / 'capture.json'
        metadata = json.loads(metadata_path.read_text())
        validate_capture(metadata, directory / 'capture.cf32', physical['receiver_settings'])
        require(physical['metadata_sha256'] == sha256(metadata_path) and
                physical['capture_sha256'] == metadata['output']['sha256'], 'clock resume raw binding')
        analysis_path = directory / 'analysis-clock-comparison/result.json'
        report = json.loads(analysis_path.read_text())
        require(report['physical_sha256'] == sha256(physical_path) and
                report['capture_sha256'] == physical['capture_sha256'] and
                report['metadata_sha256'] == physical['metadata_sha256'] and
                all(report[k] == physical[k] for k in
                    ('board', 'clock_hz', 'band', 'mode', 'boot_id', 'source_revision', 'firmware_sha256')) and
                report['job_id'] == physical['job']['job_id'], 'clock resume analysis binding')
        for name, digest in report['tools'].items():
            tool = (source_root / name).resolve()
            require(tool.is_relative_to(source_root) and sha256(tool) == digest,
                    'clock resume analysis tool substitution')
        restored = dict(board=board, clock_hz=clock, band=band, mode=mode,
                        path=str(directory), disposition=report['disposition'],
                        human_copy=report.get('human_copy'), resources=report['resources'],
                        release_qualified=False, reused_analysis_sha256=sha256(analysis_path))
        if mode == 'WSPR':
            restored['legacy_screen_disposition'] = restored['disposition']
            restored['wspr_decode_acceptance'] = report['wspr_decode_acceptance']
            restored['disposition'] = ('WSPR_EXTERNAL_DECODE_PASS' if report['wspr_decode_acceptance']['passed']
                                       else 'WSPR_EXTERNAL_DECODE_FAIL')
        rows.append(restored)
    return rows
