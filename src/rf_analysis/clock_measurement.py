"""Independent clock measurement arithmetic; no device access or policy changes.

Intervals are inclusive. Callers must establish reference validity, physical
identity, units and capture simultaneity before using these calculations.
Exact rational arithmetic avoids shrinking a bound through float rounding.
"""
# SPDX-License-Identifier: MIT
from fractions import Fraction


def interval(lower, upper):
    lower, upper = Fraction(lower), Fraction(upper)
    if lower > upper:
        raise ValueError('reversed measurement interval')
    return lower, upper


def subtract(left, right):
    return interval(left[0] - right[1], left[1] - right[0])


def multiply(left, right):
    values = [a * b for a in left for b in right]
    return min(values), max(values)


def divide(numerator, denominator):
    if denominator[0] <= 0 <= denominator[1]:
        raise ValueError('unresolved reference separation')
    return multiply(numerator, interval(1 / denominator[1], 1 / denominator[0]))


def absolute(value):
    low, high = interval(*value)
    return (0 if low <= 0 <= high else min(abs(low), abs(high)),
            max(abs(low), abs(high)))


def utc_bracket_error(device_utc_ns, before_utc_ns, after_utc_ns,
                      before_mono_ns, after_mono_ns, reference_error_ns,
                      maximum_clock_discrepancy_ns):
    """Device UTC minus reference UTC at a device capture inside a host bracket.

Positive means the device clock is fast. The response must contain a UTC
timestamp actually captured between these host calls. Do not use response
arrival as its timestamp or subtract half the RTT as an exact correction.
reference_error_ns includes the reference's absolute error and host timestamp
capture error; it cannot be inferred from Chrony RMS alone.
"""
    values = (device_utc_ns, before_utc_ns, after_utc_ns, before_mono_ns,
              after_mono_ns, reference_error_ns, maximum_clock_discrepancy_ns)
    if any(type(v) is not int or v < 0 for v in values):
        raise ValueError('timestamps and error bounds must be nonnegative integers')
    elapsed = after_mono_ns - before_mono_ns
    if elapsed < 0 or after_utc_ns < before_utc_ns:
        raise ValueError('regressed host clock')
    discrepancy = abs(after_utc_ns - before_utc_ns - elapsed)
    if discrepancy > maximum_clock_discrepancy_ns:
        raise ValueError('host realtime/monotonic discontinuity')
    return interval(device_utc_ns - after_utc_ns - reference_error_ns,
                    device_utc_ns - before_utc_ns + reference_error_ns)


def paired_utc_improvement(control_utc_ns, corrected_utc_ns, reference_utc):
    """Exact bound on |control-reference| - |corrected-reference|.

Both predictions must refer to the SAME board raw instant and reference
observation, with matched preceding NTP inputs. The common reference error is
correlated; treating it as two independent errors needlessly loses information.
Positive throughout the returned interval establishes smaller absolute error.
"""
    low, high = interval(*reference_utc)
    control, corrected = Fraction(control_utc_ns), Fraction(corrected_utc_ns)
    points = [low, high] + [x for x in (control, corrected) if low <= x <= high]
    values = [abs(control - x) - abs(corrected - x) for x in points]
    return min(values), max(values)


def paired_utc_interval_improvement(control_utc, corrected_utc, reference_utc):
    """Conservative gain for interval-valued predictions sharing a reference.

    Interior predictions matter when an interval contains true UTC. Extrema
    of the piecewise-linear distance envelopes occur at these breakpoints;
    testing only prediction corners can otherwise overstate a small benefit.
    """
    control, corrected, reference = [interval(*v) for v in
                                     (control_utc, corrected_utc, reference_utc)]
    points = [*reference]
    for values in (control, corrected):
        points.extend(x for x in (*values, sum(values)/2)
                      if reference[0] <= x <= reference[1])

    def distances(values, point):
        ends = [abs(x-point) for x in values]
        return (0 if values[0] <= point <= values[1] else min(ends), max(ends))

    bounds = []
    for point in points:
        cmin, cmax = distances(control, point)
        qmin, qmax = distances(corrected, point)
        bounds.append((cmin-qmax, cmax-qmin))
    return min(v[0] for v in bounds), max(v[1] for v in bounds)


def rf_error(target_indicated, references_indicated, references_true, requested_hz):
    """Bound carrier error using TWO simultaneous known reference lines.

All input intervals use Hz and the same coherent IQ window. Two references
bound both receiver frequency offset and sample-rate scale. One reference
alone cannot identify both. This method assumes an affine receiver frequency
axis over these three lines; acquisition/fit/systematic bounds belong in the
input intervals. It never changes a transmitter correction or quality gate.
"""
    if len(references_indicated) != 2 or len(references_true) != 2:
        raise ValueError('two known reference lines are required')
    requested_hz = Fraction(requested_hz)
    if requested_hz <= 0:
        raise ValueError('requested frequency must be positive')
    first, second = [interval(*x) for x in references_indicated]
    true_first, true_second = [interval(*x) for x in references_true]
    target = interval(*target_indicated)
    scale = divide(subtract(true_second, true_first), subtract(second, first))
    if scale[0] <= 0:
        raise ValueError('reference frequency ordering is inconsistent')
    displacement = multiply(subtract(target, first), scale)
    measured = interval(true_first[0] + displacement[0], true_first[1] + displacement[1])
    error = subtract(measured, interval(requested_hz, requested_hz))
    return {'measured_hz': measured, 'error_hz': error,
            'error_ppm': multiply(error, interval(Fraction(10**6, 1) / requested_hz,
                                                 Fraction(10**6, 1) / requested_hz)),
            'receiver_scale': scale}


def independent_improvement(control_error, corrected_error):
    """Conservative absolute-error reduction for separately measured treatments."""
    return subtract(absolute(control_error), absolute(corrected_error))


def residual_rate(raw_error_ppm, applied_rate_ppb):
    """Derived UTC rate error for a verified common raw-timer/RF clock source.

This excludes UTC epoch/phase accuracy. A pure frequency correction and a
phase slew must be evaluated separately; a deliberate phase slew need not
reduce instantaneous frequency error. Raw oscillator error must be measured
against the engine's nominal realized frequency, including NCO quantization.
"""
    low, high = interval(*raw_error_ppm)
    correction = Fraction(applied_rate_ppb, 1000)
    scale = 1 + correction / 10**6
    if scale <= 0:
        raise ValueError('nonpositive corrected clock rate')
    return interval(low * scale + correction, high * scale + correction)


def paired_rate_improvement(raw_error_ppm, applied_rate_ppb, control_rate_ppb=0):
    """Bound reduction in absolute rate error, sharing the same measured clock.

Positive means the applied correction is closer to true frequency. This is a
clock-domain inference, not evidence that an RF correction was programmed or
that absolute UTC phase improved.
"""
    low, high = interval(*raw_error_ppm)
    changes = [Fraction(x, 1000) for x in (control_rate_ppb, applied_rate_ppb)]
    if any(1 + x / 10**6 <= 0 for x in changes):
        raise ValueError('nonpositive corrected clock rate')
    roots = [-x / (1 + x / 10**6) for x in changes]
    points = [low, high] + [x for x in roots if low <= x <= high]
    values = [abs(x * (1 + changes[0] / 10**6) + changes[0]) -
              abs(x * (1 + changes[1] / 10**6) + changes[1]) for x in points]
    return min(values), max(values)


def verdict(improvement):
    low, high = interval(*improvement)
    return 'improved' if low > 0 else 'worsened' if high < 0 else 'unresolved'


def project_clock(snapshot, raw_ns, frequency_change_ppb=0):
    """Forward projection with the firmware's integer rounding and finite slew.

    frequency_change_ppb changes the pure frequency term in both pieces while
    preserving the starting phase and already scheduled phase slew. It does
    not simulate a controller receiving later observations.
    """
    start = int(snapshot['monotonic_now_ns'])
    utc = int(snapshot['utc_now_ns'])
    end = int(snapshot['rate_until_monotonic_ns'])
    if type(raw_ns) is not int or raw_ns < start:
        raise ValueError('forward raw time required')
    rate = int(snapshot['rate_ppb']) + frequency_change_ppb
    later = int(snapshot['subsequent_rate_ppb']) + frequency_change_ppb
    if type(frequency_change_ppb) is not int or min(rate, later) <= -10**9:
        raise ValueError('invalid clock rate')
    if start <= end < raw_ns:
        return (utc + (end-start)*(10**9+rate)//10**9 +
                (raw_ns-end)*(10**9+later)//10**9)
    return utc + (raw_ns-start)*(10**9+rate)//10**9


def pulse_holdout(first, last, reference_allowance_ns, control_frequency_ppb=0):
    """Causal open-loop holdout before the next clock-model update.

    Both forecasts start at the same measured phase and use only first's
    known rates/slew end. The independent last GPIO timestamp is held out.
    A changed boot/model/source cohort refuses this comparison. The control
    replaces the learned frequency, keeping the starting phase and scheduled
    slew; this is not a replay of a whole phase-only feedback controller.
    Reference allowance must include GPIO/reference path error. The caller
    must state whether that allowance has independent calibration support.
    """
    if type(reference_allowance_ns) is not int or reference_allowance_ns < 0:
        raise ValueError('invalid reference allowance')
    a, b = first['pico'], last['pico']
    for value in (a, b):
        if (value.get('clock_valid') is not True or
                value.get('source_sntp') is not True or
                value.get('source_disagreement') is not False):
            raise ValueError('unqualified clock record')
    for key in ('device_id', 'boot_id', 'revision', 'source_epoch', 'ntp_generation'):
        if a[key] != b[key]:
            raise ValueError('holdout binding changed')
    anchor = a['rise_before']
    if anchor['model_generation'] != b['rise_before']['model_generation']:
        raise ValueError('clock model changed during holdout')
    if a['frequency_ppb'] != b['frequency_ppb']:
        raise ValueError('frequency changed during holdout')
    low, high = int(b['rise_raw_lower_ns']), int(b['rise_raw_upper_ns'])
    if low <= int(a['rise_raw_upper_ns']) or high < low:
        raise ValueError('invalid holdout raw bounds')
    applied = interval(project_clock(anchor, low), project_clock(anchor, high))
    observed = interval(int(b['rise_utc_lower_ns']), int(b['rise_utc_upper_ns']))
    # Both endpoints carry the 1 us firmware timer quantum. Refuse a mapping
    # mismatch instead of silently attributing an unseen phase update to rate.
    mapping_difference = max(abs(applied[i]-observed[i]) for i in (0, 1))
    if mapping_difference > 2000:
        raise ValueError('reported clock disagrees with forward projection')
    change = control_frequency_ppb-int(a['frequency_ppb'])
    # Judge the measured mapping, carrying any admitted projection mismatch
    # into the control envelope instead of silently treating it as zero.
    applied = observed
    control = interval(project_clock(anchor, low, change)-mapping_difference,
                       project_clock(anchor, high, change)+mapping_difference)
    host = last['events'][0]['timestamp_ns']
    truth = interval(host-reference_allowance_ns, host+reference_allowance_ns)
    # Keep every admitted prediction/reference value, including interior
    # points where a prediction can coincide with true UTC.
    gain = paired_utc_interval_improvement(control, applied, truth)
    return {'duration_raw_ns': low-int(a['rise_raw_lower_ns']),
            'applied_utc_ns': applied, 'control_utc_ns': control,
            'reference_utc_ns': truth,
            'applied_error_ns': subtract(applied, truth),
            'control_error_ns': subtract(control, truth),
            'absolute_improvement_ns': gain, 'verdict': verdict(gain)}
