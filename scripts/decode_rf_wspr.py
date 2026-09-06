#!/usr/bin/env python3
"""Decode verified bench IQ independently with wsprd; no drift/time correction."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np
from analyze_rf_bench import load_capture
from measure_rf_bench import baseband


def audio_from_iq(iq, rate, center):
    # Keep received phase, frequency offset, drift and elapsed time unchanged.
    if rate < 10000 or abs(3570100 - center) > rate / 2 - 2000:
        raise ValueError('WSPR signal is outside usable capture span')
    bb, brate = baseband(iq, rate, center, 3570100)
    if brate != 1000:
        raise ValueError('Decoder conversion requires a 1000 Hz baseband rate')
    # Windowed-sinc interpolation using the existing NumPy dependency.
    taps = np.sinc(np.arange(-120, 121) / 12) * np.hanning(241)
    taps *= 12 / taps.sum()
    up = np.zeros(len(bb) * 12, dtype=np.complex128)
    up[::12] = bb
    up = np.convolve(up, taps, mode='same')
    audio = np.real(up * np.exp(2j * np.pi * 1500 * np.arange(len(up)) / 12000))
    if not np.isfinite(audio).all() or np.max(np.abs(audio)) == 0:
        raise ValueError('Invalid or silent audio')
    if len(audio) > 120 * 12000:
        raise ValueError('Capture exceeds a WSPR decode slot')
    audio = np.pad(audio, (0, 120 * 12000 - len(audio)))
    return np.round(audio / np.max(np.abs(audio)) * 28000).astype('<i2')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('iq', type=Path)
    p.add_argument('metadata', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--wsprd', type=Path, required=True)
    p.add_argument('--expect', nargs=3, required=True, metavar=('CALL', 'GRID', 'DBM'))
    args = p.parse_args()
    iq, meta, digest = load_capture(args.iq, args.metadata)
    if meta.get('overflow_count') != 0 or meta.get('clipping', {}).get('sample_count') != 0:
        raise ValueError('Capture overflow/clipping is absent or nonzero')
    settings = meta['actual_settings']
    audio = audio_from_iq(iq, settings['sample_rate_hz'], settings['center_frequency_hz'])
    args.output.mkdir(parents=True, exist_ok=False)
    wav = args.output.resolve() / '260906_0000.wav'
    with wave.open(str(wav), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(12000)
        stream.writeframes(audio.tobytes())
    command = [str(args.wsprd.resolve()), '-d', '-H', '-f', '3.568600', str(wav)]
    result = dict(decoded=False, matches=[],
                  expected=args.expect, command=command,
                  capture_sha256=digest, wav_sha256=hashlib.sha256(wav.read_bytes()).hexdigest(),
                  decoder_sha256=hashlib.sha256(args.wsprd.read_bytes()).hexdigest(),
                  utc_synchronization_test=False, qualification=False,
                  conversion='Hann decimate to 1 kHz, 241-tap Hann sinc upsample to 12 kHz, real 1500 Hz audio; amplitude normalization and trailing silence only. No drift, frequency or time correction. Filename is a synthetic slot label.')
    try:
        run = subprocess.run(command, cwd=args.output, capture_output=True, text=True, timeout=90)
        (args.output / 'wsprd.log').write_text(run.stdout + run.stderr)
        matches = [line for line in run.stdout.splitlines()
                   if len(line.split()) == 8 and line.split()[-3:] == args.expect]
        result.update(returncode=run.returncode, matches=matches,
                      decoded=run.returncode == 0 and bool(matches))
    except (OSError, subprocess.TimeoutExpired) as error:
        result['error'] = str(error)
        raise
    finally:
        (args.output / 'decode.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['decoded'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
