"""Independent Phase 11.6 IQ analysis bound to the accepted job and band."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np

from analyze_rf_bench import load_capture
from campaign import analysis as established
from decode_rf_wspr import audio_from_iq
from measure_rf_bench import measure

from phase11_6.plan import WSPR_LOWEST_OFFSET_NHZ, WSPR_SYMBOLS


def save(path: Path, value: object) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def _waterfall(iq: np.ndarray, rate: int, center: float, expected: float,
               path: Path) -> dict:
    width = 512
    hop = max(width, len(iq) // 600)
    rows = []
    window = np.hanning(width)
    for offset in range(0, len(iq) - width + 1, hop):
        power = np.abs(np.fft.fftshift(np.fft.fft(iq[offset:offset + width] * window))) ** 2
        rows.append(10 * np.log10(np.maximum(power, 1e-300)))
    image = np.asarray(rows)
    low, high = np.percentile(image, [5, 99.5])
    pixels = np.clip((image - low) * 255 / max(high - low, 1e-12), 0, 255).astype(np.uint8)
    with path.open("xb") as stream:
        stream.write(f"P5\n{width} {len(pixels)}\n255\n".encode())
        stream.write(pixels.tobytes())
    bins = center + np.fft.fftshift(np.fft.fftfreq(width, 1 / rate))
    return {
        "path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "width": width,
        "height": len(pixels),
        "hop_samples": hop,
        "left_hz": float(bins[0]),
        "right_hz": float(bins[-1]),
        "expected_hz": expected,
        "scale": "per-row FFT magnitude, fixed 5th-to-99.5th percentile grayscale",
    }


def _envelope_svg(iq: np.ndarray, rate: int, path: Path) -> dict:
    width, height = 1200, 300
    blocks = np.array_split(np.abs(iq), width)
    envelope = np.array([float(np.max(block)) if len(block) else 0 for block in blocks])
    scale = max(float(np.max(envelope)), 1e-300)
    points = " ".join(
        f"{index},{height - 10 - value / scale * (height - 20):.2f}"
        for index, value in enumerate(envelope)
    )
    body = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="300" '
        'viewBox="0 0 1200 300"><rect width="1200" height="300" fill="white"/>'
        '<polyline fill="none" stroke="#006b78" stroke-width="1" points="'
        + points
        + '"/></svg>\n'
    )
    path.write_text(body)
    return {
        "path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bins": width,
        "seconds_per_bin": len(iq) / rate / width,
        "quantity": "maximum uncalibrated linear IQ magnitude per bin",
    }


def _decode_wspr(iq: np.ndarray, rate: int, center: float, frequency: int,
                 measurement: dict, directory: Path, wsprd: Path) -> dict:
    intervals = measurement.get("intervals_s", [])
    if len(intervals) != 1:
        return {"decoded": False, "reason": "expected one complete WSPR burst"}
    detected_start, detected_end = intervals[0]
    frame_seconds = sum(
        int(event["duration_ns"])
        for event in measurement["expected_job"]["events"]
    ) / 1e9
    capture_seconds = len(iq) / rate
    start = max(0.0, detected_start - 0.5)
    complete = (
        detected_start >= 1.0
        and detected_end + 1.0 <= capture_seconds
        and detected_end - detected_start >= frame_seconds - 0.15
        and start + frame_seconds <= capture_seconds
    )
    if not complete:
        return {
            "decoded": False,
            "reason": "complete frame plus leading/trailing quiet is not retained",
            "detected_interval_s": intervals[0],
            "capture_seconds": capture_seconds,
            "expected_frame_seconds": frame_seconds,
        }
    stop = min(len(iq), round((start + 120) * rate))
    selected = iq[round(start * rate):stop]
    audio = audio_from_iq(selected, rate, center, frequency)
    label = datetime.datetime.fromtimestamp(0, datetime.timezone.utc).strftime("%y%m%d_%H%M")
    wav = directory / (label + ".wav")
    with wave.open(str(wav), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(12_000)
        stream.writeframes(audio.tobytes())
    command = [
        str(wsprd),
        "-d",
        "-H",
        "-f",
        f"{(frequency - 1500) / 1e6:.9f}",
        str(wav),
    ]
    result = subprocess.run(command, cwd=directory, capture_output=True, text=True, timeout=90)
    (directory / "wsprd.stdout").write_text(result.stdout)
    (directory / "wsprd.stderr").write_text(result.stderr)
    matches = [
        line for line in result.stdout.splitlines()
        if len(line.split()) == 8 and line.split()[-3:] == ["AA0NT", "EM18", "20"]
    ]
    return {
        "decoded": result.returncode == 0 and bool(matches),
        "returncode": result.returncode,
        "matches": matches,
        "expected": ["AA0NT", "EM18", "20"],
        "command": command,
        "decoder_sha256": hashlib.sha256(wsprd.read_bytes()).hexdigest(),
        "wav_sha256": hashlib.sha256(wav.read_bytes()).hexdigest(),
        "selected_samples": [round(start * rate), stop],
        "complete_frame_verified_before_padding": True,
        "conversion": (
            "capture-relative unedited window; Hann decimate to 1 kHz, 241-tap Hann "
            "sinc interpolate to 12 kHz, translate actual RF to 1500 Hz audio, amplitude "
            "normalize and pad only after complete-frame verification; no drift/frequency correction"
        ),
    }


def analyze(job: dict, capture_path: Path, metadata_path: Path, directory: Path,
            wsprd: Path | None = None, *, tool_provenance: dict,
            actual_wtp_job_id: str, physical_result_sha256: str) -> dict:
    if (tool_provenance.get("schema") != "phase11.6-analysis-tools-v1"
            or not tool_provenance.get("source_sha256")):
        raise ValueError("Phase 11.6 analysis tool provenance")
    if (len(actual_wtp_job_id) != 32
            or any(character not in "0123456789abcdef"
                   for character in actual_wtp_job_id)
            or len(physical_result_sha256) != 64
            or any(character not in "0123456789abcdef"
                   for character in physical_result_sha256)):
        raise ValueError("Phase 11.6 physical result identity")
    directory.mkdir(mode=0o700)
    iq, metadata, capture_sha = load_capture(capture_path, metadata_path)
    settings = metadata["actual_settings"]
    rate = settings["sample_rate_hz"]
    center = settings["center_frequency_hz"]
    expected_settings = {
        "format": "CF32",
        "sample_rate_hz": 250_000,
        "bandwidth_hz": 200_000,
        "center_frequency_hz": job["nominal_frequency_hz"] - 25_000,
        "gain_db": 20,
        "channel": 0,
        "agc": False,
        "bias_tee": False,
    }
    if settings != expected_settings:
        raise ValueError("Phase 11.6 capture settings differ from frozen job")
    if metadata.get("overflow_count") != 0 or metadata.get("clipping", {}).get("sample_count") != 0:
        raise ValueError("Phase 11.6 capture overflow or clipping")
    mode = job["mode"]
    if mode == "TONE":
        result = established.tone(
            iq, rate, center, job["nominal_frequency_hz"], directory
        )
    elif mode == "WSPR":
        measurement = measure(
            iq,
            rate,
            center,
            frame=True,
            base_hz=job["nominal_frequency_hz"] + WSPR_LOWEST_OFFSET_NHZ / 1e9,
            symbols=[int(value) for value in WSPR_SYMBOLS],
        )
        measurement["expected_job"] = job["expected_job"]
        decode = _decode_wspr(
            iq,
            rate,
            center,
            job["nominal_frequency_hz"],
            measurement,
            directory,
            wsprd.resolve(strict=True) if wsprd is not None else Path("/missing/wsprd"),
        ) if wsprd is not None else {"decoded": False, "reason": "wsprd not supplied"}
        spectrum = established.spectrum(
            iq,
            rate,
            center,
            [item["indicated_hz"] for item in measurement.get("measurements", [])],
            measurement.get("intervals_s", []),
        )
        result = {
            "passed": bool(measurement.get("relative_checks_passed") and decode["decoded"]),
            "measurement": measurement,
            "decode": decode,
            "spectrum": spectrum,
        }
    else:
        # The compact compiler and WsprryPi adapter append an explicit 1 us
        # RF-off tail so the command stream ends in a defined off state.  It is
        # a control sentinel, not an independently resolvable on-air interval;
        # the retained capture's trailing quiet verifies its effect.  Keep the
        # exact tail bound in the report while excluding it from the 20 ms
        # keyed-event interior windows used by the established analyzer.
        analyzed_job = copy.deepcopy(job["expected_job"])
        events = analyzed_job["events"]
        terminal_tail_ns = 0
        if events and events[-1].get("rf_on") is False:
            terminal_tail_ns = int(events[-1]["duration_ns"])
            if terminal_tail_ns < 40_000_000:
                expected_offset = sum(int(event["duration_ns"]) for event in events[:-1])
                if int(events[-1]["offset_ns"]) != expected_offset:
                    raise ValueError("Non-contiguous terminal RF-off tail")
                events.pop()
        result = established.keyed(
            iq, rate, center, job["nominal_frequency_hz"], analyzed_job
        )
        result["terminal_rf_off_tail_ns"] = terminal_tail_ns
        observed = result.get("observed_intervals_s", [])
        if result.get("alignment_s", 0) < 1.0:
            result.setdefault("issues", []).append("less than one second leading quiet")
        if observed and len(iq) / rate - observed[-1][1] < 1.0:
            result.setdefault("issues", []).append("less than one second trailing quiet")
        result["passed"] = not result.get("issues")
    visuals = {
        "waterfall": _waterfall(
            iq, rate, center, job["nominal_frequency_hz"], directory / "waterfall.pgm"
        ),
        "envelope": _envelope_svg(iq, rate, directory / "envelope.svg"),
    }
    report = {
        "schema": "phase11.6-analysis-v1",
        "job_id": job["id"],
        "wtp_job_id": actual_wtp_job_id,
        "physical_result_sha256": physical_result_sha256,
        "band": job["band"],
        "mode": mode,
        "capture_sha256": capture_sha,
        "metadata_sha256": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        "expected_settings": expected_settings,
        "analysis_time_resolution_s": 0.001,
        "tool_provenance": tool_provenance,
        "result": result,
        "visuals": visuals,
        "passed": bool(result.get("passed")),
        "limitations": [
            "absolute frequency is receiver-indicated and uncalibrated",
            "spectrum is relative and in-band only; no harmonic, power or regulatory claim",
            "capture-relative timing does not independently calibrate UTC",
        ],
    }
    save(directory / "analysis.json", report)
    return report
