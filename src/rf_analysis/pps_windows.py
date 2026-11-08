"""Independent, bounded PPS/count-window analysis for the RAM bench fixture."""

from fractions import Fraction
import math
import statistics


def analyze_windows(pulses, *, nominal_hz=1_000_000, pps_endpoint_us=10):
    """Analyze every nonoverlapping 10/30/60 s window and the full 300 s run.

    Rows are (index, raw_low_us, raw_high_us, count_low, count_high).
    Brackets enclose the observed electrical edge; neither serial arrival nor
    the raw Pico timer defines a UTC second. Bounds include one count plus the
    separately declared, conditional PPS endpoint allowance.
    """
    if (
        type(nominal_hz) is not int
        or nominal_hz <= 0
        or isinstance(pps_endpoint_us, bool)
        or not isinstance(pps_endpoint_us, (int, float))
        or not math.isfinite(pps_endpoint_us)
        or not 0 <= pps_endpoint_us <= 100
    ):
        raise ValueError("Invalid nominal frequency or PPS endpoint allowance")
    if len(pulses) != 301:
        raise ValueError("Exactly 301 PPS endpoints are required")
    for index, row in enumerate(pulses):
        if (
            len(row) != 5
            or any(type(v) is not int or v < 0 for v in row)
            or row[0] != index
            or not 0 <= row[2] - row[1] <= 100
            or not 0 <= row[4] - row[3] <= 100
        ):
            raise ValueError("Invalid or excessively wide edge bracket")
        if index:
            prior = pulses[index - 1]
            if (
                row[1] <= prior[2]
                or row[3] <= prior[4]
                or not 999_000 <= row[1] - prior[2] < 1_001_000
            ):
                raise ValueError("Missing, reversed, or discontinuous PPS edge")
    allowance = Fraction(str(pps_endpoint_us)) / 1_000_000
    rows = []
    for seconds in (10, 30, 60, 300):
        for start in range(0, 301 - seconds, seconds):
            a, b = pulses[start], pulses[start + seconds]
            count_low = b[3] - a[4] - 1
            count_high = b[4] - a[3] + 1
            count_mid = Fraction(b[3] + b[4] - a[3] - a[4], 2)
            raw_low = Fraction(b[1] - a[2], 1_000_000)
            raw_high = Fraction(b[2] - a[1], 1_000_000)
            reference = (count_mid / seconds / nominal_hz - 1) * 1_000_000_000
            reference_low = (
                count_low / (seconds + 2 * allowance) / nominal_hz - 1
            ) * 1_000_000_000
            reference_high = (
                count_high / (seconds - 2 * allowance) / nominal_hz - 1
            ) * 1_000_000_000
            rows.append(
                dict(
                    first_pps=start,
                    last_pps=start + seconds,
                    span_s=seconds,
                    reference_midpoint_ppb=float(reference),
                    reference_offset_ppb=[float(reference_low), float(reference_high)],
                    raw_timer_error_ppb=[
                        float(
                            (raw_low / (seconds + 2 * allowance) - 1) * 1_000_000_000
                        ),
                        float(
                            (raw_high / (seconds - 2 * allowance) - 1) * 1_000_000_000
                        ),
                    ],
                )
            )
    summaries = []
    for seconds in (10, 30, 60, 300):
        selected = [r for r in rows if r["span_s"] == seconds]
        midpoints = [r["reference_midpoint_ppb"] for r in selected]
        summaries.append(
            dict(
                span_s=seconds,
                windows=len(selected),
                mean_ppb=statistics.mean(midpoints),
                minimum_ppb=min(midpoints),
                maximum_ppb=max(midpoints),
                peak_to_peak_ppb=max(midpoints) - min(midpoints),
                sample_stdev_ppb=statistics.stdev(midpoints)
                if len(midpoints) > 1
                else None,
                maximum_half_interval_ppb=max(
                    (r["reference_offset_ppb"][1] - r["reference_offset_ppb"][0]) / 2
                    for r in selected
                ),
            )
        )
    return dict(
        pps_endpoint_allowance_us=pps_endpoint_us,
        nominal_hz=nominal_hz,
        summaries=summaries,
        windows=rows,
        scope="Conditional PPS/count brackets; not certified oscillator accuracy or production RF qualification.",
    )


def compare_production(
    pulses, observations, *, first_loaded=False, nominal_hz=1_000_000
):
    """Compare production reconstruction with independently bracketed SAME edges.

    Physical PPS jitter and oscillator movement are common to both counts.
    Differences in cycles therefore need no assumed receiver timing allowance.
    This does not remove either method's count/edge bracket uncertainty.
    """
    analyze_windows(pulses, nominal_hz=nominal_hz)
    if type(first_loaded) is not bool:
        raise ValueError("Invalid load pattern")
    keys = {
        "seq",
        "raw_ns",
        "utc_ns",
        "uncertainty_ns",
        "coherent",
        "edges",
        "count_raw_ns",
        "count_bound_ns",
        "plan",
        "capture",
    }
    selected, outside = [], 0
    binding, last_coherent = None, None
    for o in observations:
        if (
            set(o) != keys
            or any(type(v) is not int or v < 0 for v in o.values())
            or not o["seq"]
            or not 0 < o["uncertainty_ns"] <= 200_000_000
        ):
            raise ValueError("Malformed production observation")
        matches = [
            p
            for p in pulses
            if p[1] * 1000 - o["uncertainty_ns"]
            <= o["raw_ns"]
            <= p[2] * 1000 + o["uncertainty_ns"]
        ]
        if not matches:
            if (
                o["raw_ns"] < pulses[0][1] * 1000 - o["uncertainty_ns"]
                or o["raw_ns"] > pulses[-1][2] * 1000 + o["uncertainty_ns"]
            ):
                outside += 1
                continue
            raise ValueError("Unmatched production PPS inside capture")
        if (
            len(matches) != 1
            or o["coherent"] not in (0, 1)
            or (
                o["coherent"] == 1
                and (
                    not o["plan"]
                    or not o["capture"]
                    or not 0
                    <= o["count_raw_ns"] - o["raw_ns"]
                    <= o["count_bound_ns"]
                    <= 1_000_000
                )
            )
        ):
            raise ValueError("Ambiguous or incoherent production capture")
        p = matches[0]
        if o["coherent"]:
            candidate_binding = (o["plan"], o["capture"])
            if binding is not None and candidate_binding != binding:
                raise ValueError("Changed count-session binding")
            if last_coherent is not None and (
                o["count_raw_ns"] <= last_coherent["count_raw_ns"]
                or o["edges"] <= last_coherent["edges"]
            ):
                raise ValueError("Reversed coherent count endpoint")
            binding, last_coherent = candidate_binding, o
        if selected:
            prior, prior_p = selected[-1]
            if (
                o["seq"] != prior["seq"] + 1
                or p[0] != prior_p[0] + 1
                or o["utc_ns"] - prior["utc_ns"] != 1_000_000_000
                or o["raw_ns"] <= prior["raw_ns"]
                or (
                    o["coherent"]
                    and prior["coherent"]
                    and (
                        o["count_raw_ns"] <= prior["count_raw_ns"]
                        or o["edges"] <= prior["edges"]
                        or (o["plan"], o["capture"])
                        != (prior["plan"], prior["capture"])
                    )
                )
            ):
                raise ValueError("Discontinuous production observation window")
        selected.append((o, p))
    if len(selected) < 295:
        raise ValueError("Insufficient production observations")
    rows = []
    for seconds in (10, 30, 60):
        for start in range(0, len(selected) - seconds, seconds):
            a, pa = selected[start]
            b, pb = selected[start + seconds]
            phase = pa[0] // 60
            loaded = (
                (first_loaded ^ bool(phase & 1)) if (pb[0] - 1) // 60 == phase else None
            )
            if not a["coherent"] or not b["coherent"]:
                rows.append(
                    dict(
                        span_s=seconds,
                        first_pps=pa[0],
                        last_pps=pb[0],
                        loaded=loaded,
                        available=False,
                        reason="incoherent_endpoint",
                    )
                )
                continue
            if (a["plan"], a["capture"]) != (b["plan"], b["capture"]):
                raise ValueError("Changed count-session binding")
            normalized = Fraction(
                (b["edges"] - a["edges"]) * (b["raw_ns"] - a["raw_ns"]),
                b["count_raw_ns"] - a["count_raw_ns"],
            )
            independent_low = pb[3] - pa[4] - 1
            independent_high = pb[4] - pa[3] + 1
            scale = Fraction(1_000_000_000, nominal_hz * seconds)
            difference = [
                float((normalized - independent_high) * scale),
                float((normalized - independent_low) * scale),
            ]
            phase = pa[0] // 60
            loaded = (
                (first_loaded ^ bool(phase & 1)) if (pb[0] - 1) // 60 == phase else None
            )
            rows.append(
                dict(
                    available=True,
                    span_s=seconds,
                    first_pps=pa[0],
                    last_pps=pb[0],
                    loaded=loaded,
                    production_estimate_ppb=float(
                        (normalized - nominal_hz * seconds) * scale
                    ),
                    acquisition_difference_ppb=difference,
                    acquisition_difference_midpoint_ppb=sum(difference) / 2,
                    consistent_with_independent_brackets=difference[0]
                    <= 0
                    <= difference[1],
                    pps_timestamp_error_change_ns=[
                        (b["raw_ns"] - pb[2] * 1000) - (a["raw_ns"] - pa[1] * 1000),
                        (b["raw_ns"] - pb[1] * 1000) - (a["raw_ns"] - pa[2] * 1000),
                    ],
                )
            )
    return dict(
        observations=len(selected),
        outside_capture=outside,
        incoherent_sequences=[o["seq"] for o, p in selected if not o["coherent"]],
        pps_timestamp_errors=[
            dict(
                pps=p[0],
                error_ns=[o["raw_ns"] - p[2] * 1000, o["raw_ns"] - p[1] * 1000],
            )
            for o, p in selected
        ],
        windows=rows,
        scope="Same-edge acquisition difference; physical PPS/oscillator changes cancel. Independent brackets remain conditional on coherent count extension and input identity.",
    )
