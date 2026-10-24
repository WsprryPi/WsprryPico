#!/usr/bin/env python3
"""Offline, context-preserving wsprd decode of one verified captured native pair."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import time
import wave


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def matches(output, frame_type, call, grid, power):
    """Parse the two wsprd message formats separately, after independent decoding."""
    result = []
    for line in output.splitlines():
        words = line.split()
        if len(words) != (7 if frame_type == 2 else 8) or not re.fullmatch(r'\d{4}', words[0]):
            continue
        try:
            if not all(math.isfinite(float(v)) for v in words[1:5]):
                continue
        except ValueError:
            continue
        expected = [call, str(power)] if frame_type == 2 else ['<' + call + '>', grid, str(power)]
        if words[5:] == expected:
            result.append(line)
    return result


def frequency_mapping(dial_hz):
    """Whole-Hz standalone WSPR USB dial to nominal RF center, without a fit."""
    if type(dial_hz) is not int or not 98503 <= dial_hz <= 74998496:
        raise ValueError('Expected a whole-Hz WSPR dial frequency')
    return dial_hz + 1500


def validate_dial(physical, dial_hz):
    center_hz = frequency_mapping(dial_hz)
    if physical['ready']['status'].get('schedule_dial_frequency_nhz') != str(dial_hz * 10**9):
        raise ValueError('Capture/standalone dial identity mismatch')
    return center_hz


def validate_windows(intervals, rate, sample_count):
    if len(intervals) != 2:
        raise ValueError('Exactly two complete RF intervals required')
    a, b = intervals
    if (any(len(v) != 2 or v[0] < rate or v[1] > sample_count or v[1] <= v[0]
            or abs((v[1] - v[0]) / rate - 110.592) > .05 for v in intervals)
            or abs((b[0] - a[0]) / rate - 120) > .05 or a[1] >= b[0]
            or b[0] - rate + 120 * rate > sample_count):
        raise ValueError('Missing, truncated, overlapping or mistimed pair')


def native_pair_terminal(info, second_job):
    status = info['status']
    return (status['state'] in ('empty', 'complete') and status['owner_id'] is None
            and status['output_active'] is False and status['wspr_pair_pending'] is False
            and status['last_job'] == second_job and status['wspr_frame'] == 2
            and status['wspr_frames'] == 2 and status['last_error'] is None
            and status['enabled'] is True and status['suspended'] is False
            and info.get('dma_errors') == 0 and info.get('fault_stage') == 0
            and info.get('engine_diagnostic') == '')


def validate_order(physical):
    slots = physical['slots_utc_s']
    expected = ['eeeeeeeeeeeeeeee' + format(t * 10**9, '016x') for t in slots]
    # RELEASE clears a completed job to Empty. Preserve and explicitly assess
    # the original wrapper's overly strict Complete-only termination failure.
    expected_wrapper_error = "ValueError('receiver ended before complete pair')"
    corrected = physical['status'] == 'FAILED' and physical['errors'] == [expected_wrapper_error]
    if (len(slots) != 2 or slots[1] - slots[0] != 120
            or physical['job_ids'] != expected or physical['actual_rf_starts'] != 2
            or not (corrected or physical['status'] == 'CAPTURED' and not physical['errors'])
            or physical['restoration'].get('verified') is not True):
        raise ValueError('Native pair identity/order/completion/restoration is not verified')
    observed = []
    boot = physical['ready']['status']['boot_id']
    for sample in physical['samples']:
        status = sample['info']['status']
        if status['boot_id'] != boot:
            raise ValueError('Capture boot changed')
        if status['state'] == 'running' and status['job_id'] not in observed:
            observed.append(status['job_id'])
    if observed != expected:
        raise ValueError('Missing half or wrong observed order')
    terminal = [s for s in physical['samples'] if native_pair_terminal(s['info'], expected[1])]
    if not terminal:
        raise ValueError('No attributable normal native pair completion before STOP')
    return dict(native_completion_verified=True, original_workflow_status=physical['status'],
                original_workflow_errors=physical['errors'], controller_termination_corrected=corrected,
                explanation='Scheduler sees the second Complete, cancel_pair(None) RELEASEs it, and JobService clear_job changes state to Empty.',
                terminal_host_utc_ns=terminal[0]['host_utc_ns'],
                source='src/standalone/scheduler.cpp poll_pair/cancel_pair; src/wtp/job_service.cpp RELEASE/clear_job')


def table_state(directory):
    path = directory / 'hashtable.txt'
    return dict(exists=path.exists(), sha256=digest(path) if path.exists() else None,
                content=path.read_text() if path.exists() else None)


def associate(intervals, rate, metadata, physical):
    """Associate sample intervals with observed jobs using the receiver host clock.

    The helper records software read boundaries, without an SDR hardware time
    stamp. The explicit 2 s screen establishes job attribution, not launch timing.
    """
    origin = datetime.fromisoformat(metadata['timestamps']['retained_capture_start_utc'].replace('Z', '+00:00')).timestamp()
    result = []
    previous = None
    for sample in physical['samples']:
        if previous:
            delta = (sample['host_utc_ns'] - previous['host_utc_ns']) - (sample['host_monotonic_ns'] - previous['host_monotonic_ns'])
            if abs(delta) > 250000000:
                raise ValueError('Receiver host UTC jumped relative to monotonic time')
        previous = sample
    for interval, job, slot in zip(intervals, physical['job_ids'], physical['slots_utc_s']):
        start, end = [origin + v / rate for v in interval]
        running = [s['host_utc_ns'] / 1e9 for s in physical['samples']
                   if s['info']['status']['state'] == 'running' and s['info']['status']['job_id'] == job]
        if (abs(start - slot) > 2 or not running
                or min(running) < start - 2 or max(running) > end + 2):
            raise ValueError('RF sample interval does not match the observed native job time')
        result.append(dict(job_id=job, slot_utc_s=slot, approximate_rf_utc_s=[start, end],
                           observed_running_host_utc_s=[min(running), max(running)], tolerance_s=2,
                           launch_timing_qualification=False))
    return result


def run_decoder(executable, wav, directory, dial_mhz, timeout=90):
    if not math.isfinite(dial_mhz) or dial_mhz <= 0:
        raise ValueError('Expected a finite positive WSPR dial in MHz')
    before = table_state(directory)
    command = [str(executable.resolve()), '-d', '-a', str(directory.resolve()),
               '-f', f'{dial_mhz:.6f}', str(wav.resolve())]
    record = dict(command=command, cwd=str(directory.resolve()), timeout_s=timeout,
                  before=before, started_utc_ns=time.time_ns(), returncode=None)
    try:
        run = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=timeout)
        record.update(returncode=run.returncode, stdout=run.stdout, stderr=run.stderr)
    except (OSError, subprocess.TimeoutExpired) as error:
        def partial(value):
            return value.decode(errors='replace') if isinstance(value, bytes) else value or ''
        record.update(error=type(error).__name__, stdout=partial(getattr(error, 'stdout', '')),
                      stderr=partial(getattr(error, 'stderr', '')), exception=str(error))
    record.update(ended_utc_ns=time.time_ns(), after=table_state(directory))
    return record


def fresh_directory(path):
    path.mkdir(exist_ok=False)
    if table_state(path)['exists']:
        raise ValueError('Preexisting decoder hash state')


def convert_audio(iq, rate, capture_center_hz, wspr_center_hz):
    """Deterministic IQ conversion; preserve received frequency, drift and time."""
    import numpy as np
    from measure_rf_bench import baseband
    if rate < 10000 or abs(wspr_center_hz - capture_center_hz) > rate / 2 - 2000:
        raise ValueError('WSPR RF center is outside usable capture span')
    bb, brate = baseband(iq, rate, capture_center_hz, wspr_center_hz)
    if brate != 1000:
        raise ValueError('Expected exactly 1000 Hz intermediate rate')
    taps = np.sinc(np.arange(-120, 121) / 12) * np.hanning(241)
    taps *= 12 / taps.sum()
    up = np.zeros(len(bb) * 12, dtype=np.complex128)
    up[::12] = bb
    up = np.convolve(up, taps, mode='same')
    audio = np.real(up * np.exp(2j * np.pi * 1500 * np.arange(len(up)) / 12000))
    peak = float(np.max(np.abs(audio)))
    if not np.isfinite(audio).all() or not math.isfinite(peak) or peak <= 0 or len(audio) > 120 * 12000:
        raise ValueError('Invalid, silent or oversized real capture audio')
    padding = 120 * 12000 - len(audio)
    audio = np.pad(audio, (0, padding))
    parameters = dict(input_samples=len(iq), intermediate_rate_hz=brate, output_rate_hz=12000,
                      frequency_translation_hz=wspr_center_hz - capture_center_hz, audio_mapping_hz=1500,
                      decimator_hann_samples=int(rate / 1000), interpolation_taps=241,
                      interpolation_taps_float64_le_sha256=hashlib.sha256(taps.astype('<f8').tobytes()).hexdigest(),
                      audio_peak_before_normalization=peak, normalization_multiplier=28000 / peak,
                      trailing_zero_samples=padding, time_stretch=1, fitted_frequency_correction_hz=0)
    return np.round(audio * (28000 / peak)).astype('<i2'), parameters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('iq', 'metadata', 'physical', 'output', 'wsprd'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--dial-hz', type=int, required=True, help='Whole-Hz standalone WSPR USB dial; center is dial + 1500 Hz')
    parser.add_argument('--expect', nargs=3, required=True, metavar=('CALL', 'GRID', 'POWER'))
    args = parser.parse_args()
    import numpy as np
    from analyze_rf_bench import load_capture
    from measure_rf_bench import baseband
    physical = json.loads(args.physical.read_text())
    completion = validate_order(physical)
    iq, metadata, capture_hash = load_capture(args.iq, args.metadata)
    if metadata.get('overflow_count') != 0 or metadata.get('clipping', {}).get('sample_count') != 0:
        raise ValueError('Capture overflow or clipping is absent/nonzero')
    settings = metadata['actual_settings']
    if (settings != physical['receiver_settings']
            or metadata.get('resolved_device') != {'driver': 'sdrplay', 'serial': '2404058C60'}
            or metadata.get('requested_sample_count') != metadata['retained_sample_count']
            or metadata['retained_sample_count'] != int(physical['capture_argv'][5])
            or physical.get('capture_sha256', capture_hash) != capture_hash):
        raise ValueError('Capture/physical identity mismatch')
    rate, capture_center_hz = settings['sample_rate_hz'], settings['center_frequency_hz']
    wspr_center_hz = validate_dial(physical, args.dial_hz)
    dial_mhz = args.dial_hz / 1e6
    bb, brate = baseband(iq, rate, capture_center_hz, wspr_center_hz)
    power = np.abs(bb)**2
    threshold = max(float(np.median(power[:1000])) * 100, float(np.quantile(power, .95)) * .05)
    active = np.flatnonzero(power > threshold)
    groups = np.split(active, np.flatnonzero(np.diff(active) > 20) + 1)
    groups = [g for g in groups if len(g) > 30000]
    intervals = [[round(g[0] * rate / brate), round((g[-1] + 1) * rate / brate)] for g in groups]
    validate_windows(intervals, rate, len(iq))
    associations = associate(intervals, rate, metadata, physical)
    args.output.mkdir(exist_ok=False)
    completion.update(physical_sha256=digest(args.physical), capture_sha256=capture_hash,
                      rf_intervals_samples=intervals, job_associations=associations)
    (args.output / 'completion-assessment.json').write_text(json.dumps(completion, indent=2) + '\n')
    result = dict(schema='short-wspr-type23-decode/1', capture_sha256=capture_hash,
                  decoder_sha256=digest(args.wsprd), dial_hz=args.dial_hz, wspr_center_hz=wspr_center_hz, capture_center_hz=capture_center_hz, dial_mhz=dial_mhz,
                  job_associations=associations,
                  completion_assessment=completion,
                  detector=dict(threshold=threshold, intervals_samples=intervals,
                                method='1 kHz Hann baseband power; merge gaps up to 20 ms; retain intervals over 30 s'),
                  conversion='120 s real IQ windows starting 1 s before detected RF onset; fixed WSPR-center translation, Hann integrate/decimate to 1 kHz, 241-tap Hann-sinc interpolation to 12 kHz, real 1500 Hz mapping, peak normalization to 28000 and trailing silence only. No frequency/drift fit, time stretch, expected symbols, or offset search.',
                  windows=[], decodes=[], controls={}, passed=False)
    wavs = []
    for index, (first, last) in enumerate(intervals):
        start = first - rate
        stop = start + 120 * rate
        audio, parameters = convert_audio(iq[start:stop], rate, capture_center_hz, wspr_center_hz)
        # A filename labels the observed slot; UTC evidence is in the retained physical log.
        label = time.strftime('%y%m%d_%H%M', time.gmtime(physical['slots_utc_s'][index] - 1))
        wav = args.output / (label + '.wav')
        with wave.open(str(wav), 'wb') as stream:
            stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(12000)
            stream.writeframes(audio.tobytes())
        wavs.append(wav)
        result['windows'].append(dict(frame_type=index + 2, job_id=physical['job_ids'][index],
                                      samples=[start, stop], rf_interval_samples=[first, last],
                                      conversion=parameters,
                                      wav=wav.name, wav_sha256=digest(wav)))
    primary, cold = args.output / 'primary', args.output / 'cold'
    fresh_directory(primary); fresh_directory(cold)
    call, grid, dbm = args.expect
    for frame_type, wav in zip((2, 3), wavs):
        decoded = run_decoder(args.wsprd, wav, primary, dial_mhz)
        decoded['frame_type'] = frame_type
        decoded['matches'] = matches(decoded['stdout'], frame_type, call, grid, dbm)
        result['decodes'].append(decoded)
        (args.output / f'decode-type{frame_type}.json').write_text(json.dumps(decoded, indent=2) + '\n')
    control = run_decoder(args.wsprd, wavs[1], cold, dial_mhz)
    control['resolved_matches'] = matches(control['stdout'], 3, call, grid, dbm)
    control['unresolved_matches'] = matches(control['stdout'], 3, '...', grid, dbm)
    control['behavior'] = ('decoder_failure' if control['returncode'] != 0 else
                           'resolved' if control['resolved_matches'] else
                           'unresolved' if control['unresolved_matches'] else 'no_matching_frame')
    result['controls']['cold_type3'] = control
    wrong = []
    for wrong_call, wrong_grid, wrong_power in ((call + 'X', grid, dbm), (call, 'AA00AA', dbm), (call, grid, str(int(dbm) + 3))):
        accepted = bool(matches(result['decodes'][0]['stdout'], 2, wrong_call, wrong_grid, wrong_power)
                        and matches(result['decodes'][1]['stdout'], 3, wrong_call, wrong_grid, wrong_power))
        wrong.append(dict(call=wrong_call, grid=wrong_grid, power=wrong_power, accepted=accepted))
    result['controls']['wrong_expectations'] = wrong
    result['passed'] = (all(d['returncode'] == 0 and d['matches'] for d in result['decodes'])
                        and control['returncode'] == 0 and not any(c['accepted'] for c in wrong))
    (args.output / 'decode.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(passed=result['passed'], outputs=[d['stdout'] for d in result['decodes']], cold=control['stdout'])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
