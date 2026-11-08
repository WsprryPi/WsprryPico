"""Offline, simultaneous two-carrier differential phase measurement."""

import math
import numpy as np
from measure_rf_bench import baseband, phase_fit


def compare_carriers(iq, rate, center, signal_hz, reference_hz):
    """Measure a finite 12 s tone with quiet margins and a continuous reference.

    Error allowances retain the historical 100 ppm spacing, 10 ppb reference,
    and max(0.02 Hz, one-second departure) engineering assumptions.
    """
    iq = np.asanyarray(iq)
    if (
        not all(math.isfinite(v) for v in (rate, center, signal_hz, reference_hz))
        or rate < 10000
        or rate != int(rate)
        or int(rate) % 100
        or iq.ndim != 1
        or not np.iscomplexobj(iq)
        or len(iq) < 15 * rate
        or not np.isfinite(iq).all()
        or not 400 <= abs(reference_hz - signal_hz) <= 600
    ):
        raise ValueError("Invalid carrier geometry or finite capture")
    if np.max(np.maximum(abs(iq.real), abs(iq.imag))) >= 0.999:
        raise ValueError("Clipped capture")
    mid = len(iq) // 2
    segment = iq[mid - int(rate) // 2 : mid + int(rate) // 2]
    spectrum = abs(np.fft.fft(segment * np.hanning(len(segment)))) ** 2
    grid = center + np.fft.fftfreq(len(segment), 1 / rate)
    acquired = []
    for requested in (signal_hz, reference_hz):
        if not 200 < abs(requested - center) < rate / 2 - 200:
            raise ValueError("Channel intersects DC or captured bandwidth edge")
        indices = np.flatnonzero(abs(grid - requested) <= 150)
        peak = int(indices[np.argmax(spectrum[indices])])
        if spectrum[peak] < 1000 * max(float(np.median(spectrum[indices])), 1e-30):
            raise ValueError("Carrier not acquired with 30 dB contrast")
        others = indices[abs(grid[indices] - grid[peak]) > 8]
        if len(others) and spectrum[others].max() > 0.25 * spectrum[peak]:
            raise ValueError("Ambiguous carrier acquisition")
        acquired.append(float(grid[peak]))
    channels = []
    for frequency in acquired:
        bb, brate = baseband(iq, rate, center, frequency, output_rate_hz=100)
        channels.append(bb)
    dut, ref = channels
    power = abs(dut) ** 2
    quiet = max(float(np.median(power[: int(0.4 * brate)])), 1e-30)
    active = power > max(quiet * 100, float(np.median(power)) * 0.1)
    edges = np.flatnonzero(np.diff(np.r_[False, active, False]))
    intervals = [
        (int(a), int(b))
        for a, b in zip(edges[::2], edges[1::2])
        if b - a >= 11.5 * brate
    ]
    if (
        len(intervals) != 1
        or intervals[0][0] < 0.5 * brate
        or intervals[0][1] > (len(dut) - 0.5 * brate)
    ):
        raise ValueError("Missing finite carrier or quiet margins")
    start, stop = intervals[0]
    # Ten seconds inside RF; exclude one further second at each filtered edge.
    left = start + int(2 * brate)
    right = left + int(8 * brate)
    if right > stop - int(0.5 * brate):
        raise ValueError("Insufficient clean carrier interior")
    d = dut[left:right]
    r = ref[left:right]
    for channel in (d, r):
        if np.min(abs(channel)) < 0.5 * np.median(abs(channel)):
            raise ValueError("Carrier dropout in analysis interval")
    product = d * np.conj(r)
    nominal_difference = acquired[0] - acquired[1]
    fit = phase_fit(product, brate, nominal_difference)
    error = fit["indicated_hz"] + (reference_hz - signal_hz)
    seconds = [
        phase_fit(
            product[i * int(brate) : (i + 1) * int(brate)], brate, nominal_difference
        )["indicated_hz"]
        + (reference_hz - signal_hz)
        for i in range(8)
    ]
    estimator = max(0.02, max(abs(v - error) for v in seconds))
    spacing = reference_hz - signal_hz - error
    sample_allowance = abs(spacing) * 0.000100011
    reference_allowance = abs(reference_hz) * 1e-8
    return dict(
        measured_error_hz=float(error),
        observed_spacing_hz=float(spacing),
        one_second_errors_hz=seconds,
        estimator_allowance_hz=estimator,
        sample_clock_allowance_hz=sample_allowance,
        gpsdo_allowance_hz=reference_allowance,
        total_allowance_hz=estimator + sample_allowance + reference_allowance,
        residual_phase_rms_rad=fit["phase_residual_rms_rad"],
        minimum_relative_envelope=fit["amplitude_min_ratio"],
        analysis_start_s=left / brate,
        analysis_duration_s=8,
        detected_on_s=start / brate,
        detected_off_s=stop / brate,
        acquisition_hz=acquired,
        uncertainty_scope="Conditional engineering allowance; GPSDO10ppb, sample clock100ppm, empirical one-second departure. Not certified calibration.",
    )
