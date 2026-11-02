#!/usr/bin/env python3
"""Offline relative frequency/frame measurements from verified bench IQ."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from analyze_rf_bench import load_capture

BASE = 3570100.0
SPACING = 375 / 256
SYMBOL = 8192 / 12000


def baseband(iq, rate, center, carrier=BASE, *, output_rate_hz=1000):
    """Hann-weighted integrate/decimate; preserve global oscillator phase."""
    if not np.isfinite(output_rate_hz) or not 0 < output_rate_hz <= rate:
        raise ValueError('Invalid analysis sample rate')
    factor = max(1, int(rate / output_rate_hz))
    weights = np.hanning(factor) if factor > 2 else np.ones(factor)
    weights /= weights.sum()
    count = len(iq) // factor
    result = np.empty(count, dtype=np.complex128)
    chunk = max(1, min(4096, 1048576 // factor))
    for block in range(0, count, chunk):
        first, last = block * factor, min(count, block + chunk) * factor
        indices = np.arange(first, last)
        mixed = iq[first:last] * np.exp(-2j * np.pi * (carrier - center) * indices / rate)
        result[block:last // factor] = mixed.reshape(-1, factor) @ weights
    return result, rate / factor


def acquired_baseband(iq, rate, center, carrier=BASE, *, enable_lf=True):
    """LF acquisition uses 20 Hz, timing/phase uses independent 100 Hz samples.

    A 1 kHz analysis aperture admits excessive LF receiver noise. Acquire the
    actual peak first so a narrow decimator cannot alias an off-frequency tone.
    Timing remains resolved at 10 ms; acquisition is never a UTC calibration.
    """
    if not enable_lf or carrier >= 1_000_000:
        bb, brate = baseband(iq, rate, center, carrier)
        return bb, brate, carrier, None, bb, brate
    n = 2 ** int(np.floor(np.log2(min(65536, rate * .25))))
    frequencies = center + np.fft.fftfreq(n, 1 / rate)
    selected = np.flatnonzero(np.abs(frequencies - carrier) < 1000)
    if not len(selected) or len(iq) < 4 * n:
        raise ValueError('Insufficient LF acquisition span')
    window = np.hanning(n)
    spectra = np.array([np.abs(np.fft.fft(iq[a:a+n] * window)[selected]) ** 2
                        for a in range(0, len(iq) - n + 1, n)])
    quiet_count = max(1, round(.5 * rate / n))
    quiet = np.mean(np.concatenate([spectra[:quiet_count], spectra[-quiet_count:]]), axis=0)
    floor = np.maximum(quiet, np.convolve(quiet, np.ones(5) / 5, mode='same'))
    added = np.maximum(np.quantile(spectra, .9, axis=0) - floor, 0)
    peaks=[i for i in range(len(added))
           if (i==0 or added[i]>=added[i-1]) and (i+1==len(added) or added[i]>=added[i+1])]
    peaks=sorted(peaks,key=lambda i:added[i],reverse=True)[:8]
    if not peaks:peaks=[int(np.argmax(added))]
    candidates=[];accepted=None
    for index in peaks:
        acquired=float(frequencies[selected[index]])
        narrow,narrow_rate=baseband(iq,rate,center,acquired,output_rate_hz=20)
        power=np.abs(narrow)**2
        noise=max(float(np.median(power[:max(1,round(.5*narrow_rate))])),1e-300)
        snr=float(10*np.log10(max(float(np.quantile(power,.85)),1e-300)/noise))
        candidates.append(dict(center_hz=acquired,added_spectral_power=float(added[index]),
                               acquisition_snr_db=snr,passed=bool(snr>=20)))
        if accepted is None:accepted=(acquired,narrow,narrow_rate,snr)
        if snr>=20:
            accepted=(acquired,narrow,narrow_rate,snr)
            break
    acquired,narrow,narrow_rate,snr=accepted
    bb, brate = baseband(iq, rate, center, acquired, output_rate_hz=100)
    acquisition = dict(method='dominant added peaks with independent 20 dB/20 Hz acquisition; independent 100 Hz timing aperture',
                       acquired_center_hz=acquired, acquisition_snr_db=snr,candidates=candidates,
                       maximum_candidate_peaks=8,
                       minimum_acquisition_snr_db=20, timing_resolution_s=1/brate,
                       minimum_resolved_burst_s=2/brate, passed=bool(snr >= 20))
    return bb, brate, acquired, acquisition, narrow, narrow_rate


def phase_fit(samples, rate, carrier=BASE):
    if len(samples) < 8 or not np.isfinite(samples).all() or np.median(np.abs(samples)) <= np.finfo(float).tiny:
        raise ValueError('Insufficient finite nonzero samples for phase fit')
    time = np.arange(len(samples)) / rate
    time -= time.mean()
    phase = np.unwrap(np.angle(samples))
    slope, intercept = np.polyfit(time, phase, 1)
    residual = phase - (slope * time + intercept)
    return dict(indicated_hz=float(carrier + slope / (2 * np.pi)),
                phase_residual_rms_rad=float(np.sqrt(np.mean(residual ** 2))),
                amplitude_min_ratio=float(np.min(np.abs(samples)) / np.median(np.abs(samples))))


def refine_lf_edge(iq, rate, center, bb, brate, analysis_center, rough, rising):
    """Fit a coherent on/off step through the known Hann integration aperture.

    The narrowband carrier establishes frequency/phase; independent 1 ms
    amplitude samples locate the edge. A 99% profile-likelihood support interval
    is retained rather than equating the narrow acquisition aperture with time.
    """
    left, right = (rough + .08, rough + .58) if rising else (rough - .58, rough - .08)
    # Frequency/coherence is estimated independently through the narrow
    # acquisition aperture; wide noisy phase is never unwrapped to time an edge.
    segment, frequency_rate = baseband(iq[max(0,round(left*rate)):round(right*rate)],
                                     rate, center, analysis_center, output_rate_hz=20)
    fit = phase_fit(segment, frequency_rate, analysis_center)
    if fit['phase_residual_rms_rad'] > .15 or fit['amplitude_min_ratio'] < .5:
        return dict(resolved=False, reason='incoherent LF edge interior')
    first = max(0, round((rough - .6) * rate))
    last = min(len(iq), round((rough + .6) * rate))
    local, local_rate = baseband(iq[first:last], rate, center, fit['indicated_hz'])
    times = first / rate + (np.arange(len(local)) + .5) / local_rate
    on = (times > left) & (times < right)
    qleft, qright = (rough - .58, rough - .08) if rising else (rough + .08, rough + .58)
    quiet = (times > qleft) & (times < qright)
    if np.count_nonzero(on) < 100 or np.count_nonzero(quiet) < 100:
        return dict(resolved=False, reason='insufficient LF edge baseline')
    baseline = np.mean(local[quiet]); amplitude = np.mean(local[on]) - baseline
    if abs(amplitude) <= np.finfo(float).tiny:
        return dict(resolved=False, reason='absent coherent LF edge')
    projection = np.real((local - baseline) * np.conj(amplitude) / abs(amplitude)**2)
    variance = max(float(np.var(projection[quiet])), float(np.var(projection[on])), 1e-12)
    use = (times > rough - .05) & (times < rough + .05)
    block_start = times[use] - .5 / local_rate
    candidates = rough + np.linspace(-.03, .03, 601)
    x = np.clip((candidates[:, None] - block_start[None, :]) * local_rate, 0, 1)
    fraction = 1 - x + np.sin(2 * np.pi * x) / (2 * np.pi)
    prediction = fraction if rising else 1 - fraction
    rss = np.sum((prediction - projection[None, use])**2, axis=1)
    best = int(np.argmin(rss)); support = np.flatnonzero(rss <= rss[best] + 6.635 * variance)
    observed = float(candidates[best]); uncertainty = float(max(observed-candidates[support[0]], candidates[support[-1]]-observed) + .0001)
    return dict(resolved=bool(support[0] > 0 and support[-1] < 600), observed_s=observed,
                uncertainty_s=uncertainty, confidence=.99,
                method='coherent amplitude step with Hann aperture, 1 ms samples, 99% profile likelihood')


def lf_phase_transition(bb, brate, analysis_center, expected, before, after, width=.30, context=None):
    """Fit phase through the known Hann aperture, retaining timing uncertainty.

    LF WSPR uses the independently verified tone/linear-drift model in a local
    multi-symbol window. This avoids amplifying receiver noise by differentiating
    phase; missing tones, phase steps and wrong timing remain visible residuals.
    """
    first, last = 0, len(bb)
    if context is not None:
        width=4*SYMBOL # Eight-symbol context resolves LF timing without widening limits.
        first=max(first,round((context['start']+.04)*brate))
        last=min(last,round((context['start']+162*SYMBOL-.04)*brate))
    a=max(first,round((expected-width)*brate)); b=min(last,round((expected+width)*brate))
    if b-a<20 or abs(after-before)<.1:
        return dict(resolved=False)
    phase=np.unwrap(np.angle(bb[a:b])); time=(np.arange(a,b)+.5)/brate
    candidates=np.linspace(-.04,.04,801)
    def integrated_ramp(distance):
        x=np.clip(.5-distance*brate,0,1)
        within=((1-x)**2/2-(1-np.cos(2*np.pi*x))/(4*np.pi**2))/brate
        return np.where(distance>=.5/brate,distance,np.where(distance<=-.5/brate,0,within))
    if context is None:
        t=time-expected
        prediction=2*np.pi*((before-analysis_center)*t[None,:]+
            (after-before)*integrated_ramp(t[None,:]-candidates[:,None]))
    else:
        t=time-context['start']
        model=(context['base_hz']-analysis_center)*t+.5*context['drift']*t*t
        for i in range(1,162):
            delta=context['spacing']*(context['tones'][i]-context['tones'][i-1])
            if delta:model+=delta*integrated_ramp(t-i*SYMBOL)
        relative=time-expected
        prediction=2*np.pi*(model[None,:]+(after-before)*(
            integrated_ramp(relative[None,:]-candidates[:,None])-integrated_ramp(relative)[None,:]))
    residual=phase[None,:]-prediction
    residual-=residual.mean(axis=1,keepdims=True)
    rss=np.sum(residual**2,axis=1);best=int(np.argmin(rss))
    variance=max(float(rss[best]/max(1,len(phase)-2)),1e-12)
    support=np.flatnonzero(rss<=rss[best]+6.635*variance)
    error=float(candidates[best]);uncertainty=float(max(error-candidates[support[0]],candidates[support[-1]]-error)+.0001)
    return dict(resolved=bool(support[0]>0 and support[-1]<800),observed_s=float(expected+error),
        error_s=error,uncertainty_s=uncertainty,confidence=.99,
        phase_residual_rms_rad=float(np.sqrt(rss[best]/len(phase))),
        method='Hann-integrated continuous phase; local tone model; 99% profile likelihood')


def local_contrast(iq, rate, center, frequency):
    n = min(len(iq), 262144)
    power = np.abs(np.fft.fft(iq[:n] * np.hanning(n))) ** 2
    bins = center + np.fft.fftfreq(n, 1 / rate)
    distance = np.abs(bins - frequency)
    signal = power[distance < 100]
    background = power[(distance > 500) & (distance < 1500)]
    if not len(signal) or not len(background):
        raise ValueError('Insufficient reference spectral span')
    return float(10 * np.log10(max(float(signal.max()), 1e-300) /
                              max(float(np.median(background)), 1e-300)))


def measure(iq, rate, center, *, frame=False, tone=0, duration_s=10, reference_hz=None, base_hz=BASE, symbols=None):
    if symbols is not None:
        if not frame or len(symbols) != 162 or any(type(x) is not int or x not in range(4) for x in symbols):
            raise ValueError('Expected 162 WSPR tone indexes with frame=True')
    tones = list(symbols) if symbols is not None else [i % 4 for i in range(162)]
    if not np.isfinite(base_hz):
        raise ValueError('Expected carrier must be finite')
    if rate < 10000 or abs(base_hz - center) > rate / 2 - 2000:
        raise ValueError('Requested signal is outside usable capture span')
    bb, brate, analysis_center, acquisition, frequency_bb, frequency_rate = acquired_baseband(
        iq, rate, center, base_hz, enable_lf=reference_hz is None)
    if len(bb) < brate:
        raise ValueError('Capture needs leading and trailing baseline')
    ref = None
    if reference_hz is not None:
        if (not np.isfinite(reference_hz) or abs(reference_hz - base_hz) < 2000 or
                abs(reference_hz - center) > rate / 2 - 2000):
            raise ValueError('Reference is outside usable capture span')
        ref, _ = baseband(iq, rate, center, reference_hz)
    power = np.abs(bb) ** 2
    noise = float(np.median(power[:int(brate / 2)]))
    threshold = max(noise * (10 if acquisition is not None else 100),
                    float(np.max(power)) * .05, np.finfo(float).tiny)
    active = np.flatnonzero(power > threshold)
    groups = np.split(active, np.flatnonzero(np.diff(active) > 1) + 1) if len(active) else []
    groups = [g for g in groups if len(g) >= max(2, round(.01 * brate))]
    intervals = [[float(g[0] / brate), float((g[-1] + 1) / brate)] for g in groups]
    expected = 162 * SYMBOL if frame else duration_s
    report = dict(version=1, qualification=False, calibration_applied=False,
                  workload=('encoded-162' if symbols is not None else 'cycle4-162') if frame else 'tone', intervals_s=intervals,
                  expected_duration_s=expected, expected_base_hz=base_hz, issues=[], measurements=[],
                  method='Hann integrate/decimate then per-interval linear unwrapped phase fit',
                  limitations=['Receiver clock and frequency axis are uncalibrated.',
                               'Decimator is diagnostic; adjacent interference can bias phase.',
                               'No absolute GPIO timing or out-of-band harmonic claim.'])
    if acquisition is not None:
        report['acquisition'] = acquisition
        report['method'] = acquisition['method'] + '; per-interval linear unwrapped phase fit'
        if not acquisition['passed']:
            report['issues'].append('Insufficient narrowband LF acquisition')
    if len(groups) != 1:
        report['issues'].append('Expected one uninterrupted burst')
    if not groups:
        report['relative_checks_passed'] = False
        return report
    group = max(groups, key=len)
    start, end = group[0] / brate, (group[-1] + 1) / brate
    if acquisition is not None:
        edges = [refine_lf_edge(iq, rate, center, bb, brate, analysis_center, start, True),
                 refine_lf_edge(iq, rate, center, bb, brate, analysis_center, end, False)]
        report['edge_measurements'] = edges
        if not all(e['resolved'] and e['uncertainty_s'] <= .01 for e in edges):
            report['issues'].append('LF timing edge unresolved within 10 ms')
            report['relative_checks_passed'] = False
            return report
        start, end = [e['observed_s'] for e in edges]
        report['intervals_s'] = [[start,end]]
    report['observed_duration_s'] = float(end - start)
    if start < .5 or len(bb) / brate - end < .5:
        report['issues'].append('Missing independent leading/trailing quiet interval')
    if abs(end - start - expected) > .02:
        report['issues'].append('Burst duration differs by more than 20 ms')
    segments = 162 if frame else max(1, int(np.ceil((expected - .16) / .5)))
    for index in range(segments):
        left = start + index * SYMBOL + .08 if frame else start + .08 + index * (expected - .16) / segments
        right = start + (index + 1) * SYMBOL - .08 if frame else start + .08 + (index + 1) * (expected - .16) / segments
        if right > end or right <= left:
            report['issues'].append(f'Missing segment {index}')
            break
        data = frequency_bb[int(round(left * frequency_rate)):int(round(right * frequency_rate))]
        result = phase_fit(data, frequency_rate, analysis_center)
        if ref is not None:
            reference = phase_fit(ref[int(round(left * brate)):int(round(right * brate))],
                                  brate, reference_hz)
            reference['local_contrast_db'] = local_contrast(
                iq[round(left * rate):round(right * rate)], rate, center, reference['indicated_hz'])
            result['reference'] = reference
            result['reference_compared_hz'] = result['indicated_hz'] - (reference['indicated_hz'] - reference_hz)
            if (reference['local_contrast_db'] < 20 or reference['phase_residual_rms_rad'] > .15 or reference['amplitude_min_ratio'] < .5 or
                    abs(reference['indicated_hz'] - reference_hz) > 100):
                report['issues'].append(f'Invalid reference in segment {index}')
        result.update(index=index, tone=tones[index] if frame else tone, interval_s=[left, right])
        report['measurements'].append(result)
        if (result['phase_residual_rms_rad'] > .15 or result['amplitude_min_ratio'] < .5 or
                abs(result['indicated_hz'] - base_hz) > 100):
            report['issues'].append(f'Incoherent, interrupted or out-of-range segment {index}')
    if frame and len(report['measurements']) == 162:
        field = 'reference_compared_hz' if ref is not None else 'indicated_hz'
        values = np.array([m[field] for m in report['measurements']])
        # Fit offset + tone spacing + linear drift; retain every segment residual.
        design = np.column_stack([np.ones(162), tones, np.arange(162) * SYMBOL])
        offset, spacing, drift = np.linalg.lstsq(design, values, rcond=None)[0]
        residuals = values - design @ np.array([offset, spacing, drift])
        report.update(frequency_basis=field, fitted_base_hz=float(offset), tone_spacing_hz=float(spacing),
                      linear_drift_hz_per_s=float(drift),
                      max_symbol_residual_hz=float(np.max(np.abs(residuals))))
        lf_context = None
        if acquisition is not None:
            a=round((start+.08)*brate); b=round((end-.08)*brate)
            t=(np.arange(a,b)+.5)/brate-start
            integral=tones[0]*t
            for i in range(1,162):
                integral+=(tones[i]-tones[i-1])*np.maximum(t-i*SYMBOL,0)
            phase_data=np.unwrap(np.angle(bb[a:b]))
            phase_design=np.column_stack([np.ones(len(t)),2*np.pi*t,2*np.pi*integral,np.pi*t*t])
            coefficients=np.linalg.lstsq(phase_design,phase_data,rcond=None)[0]
            phase_rms=float(np.sqrt(np.mean((phase_data-phase_design@coefficients)**2)))
            lf_context=dict(start=start,base_hz=float(analysis_center+coefficients[1]),
                            spacing=float(coefficients[2]),drift=float(coefficients[3]),tones=tones)
            report['lf_phase_model']={**{k:v for k,v in lf_context.items() if k!='tones'},
                                      'phase_residual_rms_rad':phase_rms}
            if phase_rms>.15 or abs(lf_context['spacing']-SPACING)>.05:
                report['issues'].append('LF whole-frame phase/tone model is incoherent')
        # Symmetric 20 ms phase difference locates HF transitions; LF uses
        # direct coherent phase with independently reported edge uncertainty.
        lag = max(1, round(brate * .01))
        phase = np.unwrap(np.angle(bb))
        instantaneous = analysis_center + (phase[2*lag:] - phase[:-2*lag]) * brate / (4*np.pi*lag)
        boundaries = []
        for index in range(1, 162):
            if tones[index-1] == tones[index]:
                continue  # No physical transition exists between equal symbols.
            expected_time = start + index * SYMBOL
            before = report['measurements'][index-1]['indicated_hz']
            after = report['measurements'][index]['indicated_hz']
            if acquisition is not None:
                # Use the independently checked whole-frame tone/drift fit;
                # noisy individual frequency estimates cannot become edge bias.
                before=lf_context['base_hz']+lf_context['spacing']*tones[index-1]+lf_context['drift']*index*SYMBOL
                after=lf_context['base_hz']+lf_context['spacing']*tones[index]+lf_context['drift']*index*SYMBOL
                boundary=lf_phase_transition(bb,brate,analysis_center,expected_time,before,after,context=lf_context)
                boundary['index'] = index
                boundaries.append(boundary)
                if not boundary['resolved']:
                    report['issues'].append(f'LF transition unresolved at symbol {index}')
                elif (abs(boundary['error_s']) + boundary['uncertainty_s'] +
                      report['edge_measurements'][0]['uncertainty_s'] > .01):
                    report['issues'].append(f'LF transition timing not resolved within 10 ms at symbol {index}')
                if boundary.get('phase_residual_rms_rad',1) > .15:
                    report['issues'].append(f'LF transition phase residual exceeds 0.15 rad at symbol {index}')
                continue
            lo = max(0, round((expected_time - .05) * brate) - lag)
            hi = min(len(instantaneous), round((expected_time + .05) * brate) - lag)
            times = (np.arange(lo, hi) + lag) / brate
            candidates = expected_time + np.linspace(-.04, .04, 801)
            # Fit the ramp induced by the symmetric phase-difference window;
            # a single noisy midpoint crossing must not choose the boundary.
            ramps = np.clip((times[None, :] - candidates[:, None] + lag/brate) /
                            (2*lag/brate), 0, 1)
            predicted = before + (after - before) * ramps
            mse = np.mean((predicted - instantaneous[None, lo:hi]) ** 2, axis=1)
            best = int(np.argmin(mse))
            observed = candidates[best]
            rms = float(np.sqrt(mse[best]))
            if best in (0, 800):
                report['issues'].append(f'Transition boundary unresolved at symbol {index}')
            if rms > .15:
                report['issues'].append(f'Transition fit residual exceeds 0.15 Hz at symbol {index}')
            boundaries.append(dict(index=index, observed_s=float(observed),
                                   error_s=float(observed - expected_time), fit_rms_hz=rms))
        report['transitions'] = boundaries
        if boundaries:
            report['max_transition_error_s'] = max(abs(b.get('error_s',1)) for b in boundaries)
            if report['max_transition_error_s'] > .01:
                report['issues'].append('Transition timing differs by more than 10 ms')
        if abs(spacing - SPACING) > .05 or np.max(np.abs(residuals)) > .1:
            report['issues'].append('Tone spacing/order residual exceeds diagnostic limits')
    if ref is not None:
        report['reference_hz'] = reference_hz
        report['reference_comparison'] = 'Subtract simultaneous indicated reference error; sample-rate scale not independently calibrated'
    if not frame and report['measurements']:
        left = report['measurements'][0]['interval_s'][0]
        right = report['measurements'][-1]['interval_s'][1]
        frequencies = [m.get('reference_compared_hz', m['indicated_hz']) for m in report['measurements']]
        report['tone_frequency_summary'] = dict(mean_hz=float(np.mean(frequencies)),
            peak_to_peak_hz=float(np.ptp(frequencies)),
            nominal_offset_hz=float(np.mean(frequencies) - (base_hz + tone * SPACING)),
            basis='reference_compared_hz' if ref is not None else 'indicated_hz')
        data = np.asarray(iq[round(left * rate):round(right * rate)])
        n = min(len(data), 2097152)
        spectrum = np.abs(np.fft.fft(data[:n] * np.hanning(n))) ** 2
        bins = center + np.fft.fftfreq(n, 1 / rate)
        carrier = report['measurements'][0]['indicated_hz']
        main = np.abs(bins - carrier) < 5
        eligible = (np.abs(bins - center) < min(90000, rate * .4)) & ~main
        if ref is not None:
            eligible &= np.abs(bins - report['measurements'][0]['reference']['indicated_hz']) > 5
        indexes = np.flatnonzero(eligible)
        strongest = indexes[np.argmax(spectrum[indexes])]
        report['in_band_spectrum'] = dict(fft_samples=n, bin_width_hz=rate/n,
            strongest_other_bin_hz=float(bins[strongest]),
            strongest_other_bin_dbc=float(10*np.log10(max(spectrum[strongest], 1e-300)/max(float(spectrum[main].max()), 1e-300))),
            limitation='Windowed peak-bin ratio in retained receiver band, excluding +/-5 Hz around source/reference; not harmonic or power qualification')
    report['relative_checks_passed'] = not report['issues']
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('iq', type=Path)
    p.add_argument('metadata', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--base-hz', type=float, default=BASE, help='Expected carrier for an intentional frequency-translation experiment')
    p.add_argument('--reference-hz', type=float, help='Known simultaneously present reference frequency')
    p.add_argument('--symbols', help='162 encoded tone digits; implies frame')
    p.add_argument('--frame', action='store_true')
    p.add_argument('--tone', type=int, choices=range(4), default=0)
    p.add_argument('--duration-s', type=float, default=10)
    args = p.parse_args()
    if not np.isfinite(args.duration_s) or args.duration_s <= .2:
        p.error('Tone duration must be finite and greater than 0.2 seconds')
    iq, meta, digest = load_capture(args.iq, args.metadata)
    settings = meta['actual_settings']
    result = measure(iq, settings['sample_rate_hz'], settings['center_frequency_hz'],
                     frame=args.frame or args.symbols is not None, symbols=None if args.symbols is None else [int(c) for c in args.symbols], tone=args.tone, duration_s=args.duration_s, reference_hz=args.reference_hz, base_hz=args.base_hz)
    if meta.get('overflow_count') != 0 or meta.get('clipping', {}).get('sample_count') != 0:
        result['issues'].append('Receiver overflow/clipping evidence is absent or nonzero')
        result['relative_checks_passed'] = False
    result.update(capture_sha256=digest, metadata_sha256=hashlib.sha256(args.metadata.read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('measurements', 'transitions')}, indent=2))
    return 0 if result['relative_checks_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
