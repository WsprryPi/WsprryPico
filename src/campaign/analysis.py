"""Operational IQ measurements; no claim of calibrated power or emissions compliance."""

import json
from pathlib import Path
import subprocess
import wave

import numpy as np
from wsprrypi_qualification.carrier import CarrierParameters, analyze_carrier
from measure_rf_bench import baseband, measure, phase_fit
from decode_rf_wspr import audio_from_iq
from campaign.plan import GOLDEN37


def write(path, value):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def spectrum(iq, rate, center, frequencies, intervals):
    """Average non-overlapping Hann FFTs inside active RF intervals only."""
    n = 2 ** int(np.floor(np.log2(min(65536, rate * 0.25))))
    window = np.hanning(n)
    power = np.zeros(n)
    frames = 0
    for left, right in intervals:
        first, last = round((left + 0.02) * rate), round((right - 0.02) * rate)
        for offset in range(max(0, first), min(len(iq), last) - n + 1, n):
            power += np.abs(np.fft.fft(iq[offset : offset + n] * window)) ** 2
            frames += 1
    if not frames or not frequencies:
        return dict(available=False, reason="no complete active spectral windows")
    power /= frames
    bins = center + np.fft.fftfreq(n, 1 / rate)
    half_width = max(10, 3 * rate / n)
    main = np.zeros(n, dtype=bool)
    for frequency in frequencies:
        main |= np.abs(bins - frequency) <= half_width
    retained = np.abs(bins - center) < min(90000, rate * 0.4)
    indexes = np.flatnonzero(retained & ~main)
    if not np.any(main & retained) or not len(indexes):
        return dict(available=False, reason="insufficient main and comparison span")
    strongest = indexes[np.argmax(power[indexes])]
    return dict(
        available=True,
        fft_samples=n,
        averaged_windows=frames,
        bin_width_hz=rate / n,
        analyzed_span_hz=[float(bins[retained].min()), float(bins[retained].max())],
        source_exclusion_half_width_hz=half_width,
        strongest_other_bin_hz=float(bins[strongest]),
        strongest_other_bin_dbc=float(
            10
            * np.log10(
                max(power[strongest], 1e-300)
                / max(float(power[main & retained].max()), 1e-300)
            )
        ),
        limitation="relative average peak-bin ratio inside receiver span; no calibrated power, integrated emissions or out-of-span harmonic claim",
    )


def tone(iq, rate, center, frequency, directory):
    report = measure(iq, rate, center, duration_s=5, base_hz=frequency)
    # Let the temporal detector locate the burst, then independently assess
    # the complete interior with the Harness on/off carrier analyzer.
    if len(report["intervals_s"]) != 1:
        return dict(passed=False, measurement=report)
    start, end = report["intervals_s"][0]
    if start < 1 or len(iq) / rate - end < 0.5:
        return dict(passed=False, measurement=report, reason="missing quiet evidence")
    on, off = directory / "on.cf32", directory / "off.cf32"
    np.asarray(iq[round((start + 0.1) * rate) : round((end - 0.1) * rate)]).tofile(on)
    np.asarray(iq[: round((start - 0.1) * rate)]).tofile(off)
    carrier = analyze_carrier(
        off,
        on,
        CarrierParameters(rate, center, frequency),
        directory / "harness-carrier.json",
    )
    metrics = carrier["metrics"]
    passed = (
        report["relative_checks_passed"]
        and metrics["relative_acquisition_passed"]
        and metrics["nominal_offset_gate_passed"]
    )
    return dict(passed=bool(passed), measurement=report, carrier_metrics=metrics)


def wspr(iq, rate, center, frequency, directory, decoder, slot_utc):
    report = measure(
        iq,
        rate,
        center,
        frame=True,
        base_hz=frequency,
        symbols=[int(c) for c in GOLDEN37],
    )
    decoded = False
    if report.get("intervals_s"):
        start = max(0, report["intervals_s"][0][0] - 1)
        window = iq[round(start * rate) : round((start + 120) * rate)]
        audio = audio_from_iq(window, rate, center, frequency)
        import datetime

        label = datetime.datetime.fromtimestamp(
            slot_utc - 1, datetime.timezone.utc
        ).strftime("%y%m%d_%H%M")
        wav = directory / (label + ".wav")
        with wave.open(str(wav), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(12000)
            stream.writeframes(audio.tobytes())
        command = [
            str(decoder),
            "-d",
            "-H",
            "-f",
            str((frequency - 1500) / 1e6),
            str(wav),
        ]
        result = subprocess.run(
            command, cwd=directory, capture_output=True, text=True, timeout=90
        )
        (directory / "wsprd.stdout").write_text(result.stdout)
        (directory / "wsprd.stderr").write_text(result.stderr)
        matches = [
            line
            for line in result.stdout.splitlines()
            if len(line.split()) == 8 and line.split()[-3:] == ["AA0NT", "EM18", "37"]
        ]
        decoded = result.returncode == 0 and bool(matches)
        write(
            directory / "decode.json",
            dict(
                command=command,
                returncode=result.returncode,
                matches=matches,
                decoded=decoded,
                window_start_s=start,
                limitation="burst-relative decode alignment; UTC onset independently reported, not calibrated",
            ),
        )
    spectral = spectrum(
        iq,
        rate,
        center,
        [m["indicated_hz"] for m in report["measurements"]],
        report["intervals_s"],
    )
    return dict(
        spectrum=spectral,
        passed=bool(report["relative_checks_passed"] and decoded),
        decoded=decoded,
        measurement=report,
    )


def keyed(iq, rate, center, frequency, job):
    bb, brate = baseband(iq, rate, center, frequency)
    power = np.abs(bb) ** 2
    noise = max(float(np.median(power[: round(0.5 * brate)])), 1e-300)
    threshold = max(noise * 10, float(np.max(power)) * 0.05)
    active = power > threshold
    expected = [e for e in job["events"] if e["rf_on"]]
    indexes = np.flatnonzero(active)
    issues = []
    if len(indexes) < 10:
        return dict(passed=False, issues=["no acquired keyed carrier"])
    # Align once to the first detected edge; do not realign individual marks.
    offset = indexes[0] / brate - int(expected[0]["offset_ns"]) / 1e9
    if offset < 0.5:
        issues.append("missing leading quiet or unexpectedly early carrier")
    measurements = []
    observed = []
    groups = np.split(indexes, np.flatnonzero(np.diff(indexes) > 1) + 1)
    observed = [[g[0] / brate, (g[-1] + 1) / brate] for g in groups if len(g)]
    envelope = []
    for event_index, event in enumerate(job["events"]):
        left = offset + int(event["offset_ns"]) / 1e9
        right = left + int(event["duration_ns"]) / 1e9
        if left < 0 or right > len(bb) / brate:
            issues.append("truncated event")
            continue
        if event["rf_on"]:
            if envelope and abs(envelope[-1][1] - left) < 1e-8:
                envelope[-1][1] = right
            else:
                envelope.append([left, right])
        a, b = round((left + 0.02) * brate), round((right - 0.02) * brate)
        if b <= a:
            issues.append("event too short")
            continue
        if event["rf_on"]:
            expected_hz = int(event["frequency_nhz"]) / 1e9
            measurement = phase_fit(bb[a:b], brate, frequency)
            measurement["event_index"] = event_index
            measurement["expected_hz"] = expected_hz
            measurement["contrast_db"] = float(
                10 * np.log10(np.median(power[a:b]) / noise)
            )
            measurements.append(measurement)
            if (
                not np.all(active[a:b])
                or measurement["contrast_db"] < 10
                or measurement["phase_residual_rms_rad"] > 0.15
                or abs(measurement["indicated_hz"] - expected_hz) > 100
            ):
                issues.append("keyed carrier continuity, frequency or coherence failed")
        elif np.any(active[a:b]):
            issues.append("carrier in commanded quiet interval")
    if len(envelope) != len(observed) or any(
        abs(a - b) > 0.02
        for exp, obs in zip(envelope, observed)
        for a, b in zip(exp, obs)
    ):
        issues.append("keyed envelope timing or extra transmission failed")
    if len(bb) / brate - observed[-1][1] < 0.5 or np.any(
        active[round(observed[-1][1] * brate) + 20 :]
    ):
        issues.append("missing final silence")
    means = {}
    for m in measurements:
        means.setdefault(m["expected_hz"], []).append(m["indicated_hz"])
    spacing = None
    if len(means) == 2:
        low, high = sorted(means)
        spacing = float(np.mean(means[high]) - np.mean(means[low]))
        if abs(spacing - (high - low)) > 0.2:
            issues.append("keyed frequency separation failed")
        # Check each mark/space against its state after removing one common offset.
        offsets = [m["indicated_hz"] - m["expected_hz"] for m in measurements]
        if max(offsets) - min(offsets) > 0.2:
            issues.append("keyed state frequency residual failed")
    transitions = []
    fitted = {m["event_index"]: m for m in measurements}
    lag = max(1, round(brate * 0.01))
    phase = np.unwrap(np.angle(bb))
    instantaneous = frequency + (phase[2 * lag :] - phase[: -2 * lag]) * brate / (
        4 * np.pi * lag
    )
    for i in range(1, len(job["events"])):
        previous, current = job["events"][i - 1 : i + 1]
        if (
            not previous["rf_on"]
            or not current["rf_on"]
            or previous["frequency_nhz"] == current["frequency_nhz"]
        ):
            continue
        if i - 1 not in fitted or i not in fitted:
            issues.append("missing frequency transition interior")
            continue
        expected_time = offset + int(current["offset_ns"]) / 1e9
        lo = max(0, round((expected_time - 0.05) * brate) - lag)
        hi = min(len(instantaneous), round((expected_time + 0.05) * brate) - lag)
        times = (np.arange(lo, hi) + lag) / brate
        candidates = expected_time + np.linspace(-0.04, 0.04, 801)
        ramps = np.clip(
            (times[None, :] - candidates[:, None] + lag / brate) / (2 * lag / brate),
            0,
            1,
        )
        before, after = fitted[i - 1]["indicated_hz"], fitted[i]["indicated_hz"]
        mse = np.mean(
            (before + (after - before) * ramps - instantaneous[None, lo:hi]) ** 2,
            axis=1,
        )
        best = int(np.argmin(mse))
        error = float(candidates[best] - expected_time)
        residual = float(np.sqrt(mse[best]))
        transitions.append(dict(event_index=i, error_s=error, fit_rms_hz=residual))
        if best in (0, 800):
            issues.append("keyed frequency transition boundary unresolved")
        if abs(error) > 0.02:
            issues.append("keyed frequency transition timing failed")
        if residual > 0.15:
            issues.append("keyed frequency transition fit residual exceeds 0.15 Hz")
    return dict(
        passed=not issues,
        issues=issues,
        spectrum=spectrum(
            iq, rate, center, [m["indicated_hz"] for m in measurements], observed
        ),
        alignment_s=float(offset),
        observed_intervals_s=observed,
        measurements=measurements,
        spacing_hz=spacing,
        transitions=transitions,
        limitation="relative carrier/channel tests; uncalibrated UTC and spectrum",
    )
