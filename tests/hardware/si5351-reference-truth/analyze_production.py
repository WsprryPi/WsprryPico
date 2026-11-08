# SPDX-License-Identifier: MIT
"""Analyze private dual-core RAM diagnostic transcripts; emit no position data."""

import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from rf_analysis.pps_windows import analyze_windows, compare_production


def analyze(text):
    info = re.findall(
        r"^INFO serial=([0-9a-fA-F]{16}) clock_hz=(\d+) ram_only=1 pps_gp=(\d+) input_gp=(\d+) seconds=300 source=(si5351|known_ratio) production=1 input_only=1$",
        text,
        re.M,
    )
    if len(info) != 1 or int(info[0][1]) != 138000000:
        raise ValueError("Missing unique target identity")
    serial, _, pps, clock, source = info[0]
    if (int(pps), int(clock)) != ((3, 7) if source == "si5351" else (11, 9)):
        raise ValueError("Wrong source/pin binding")
    begin = re.findall(
        r"^BEGIN_PRODUCTION first_loaded=([01]) pattern=alternating_60pps$", text, re.M
    )
    end = re.findall(
        r"^END_PRODUCTION pulses=(\d+) observations=(\d+) coherent=([01]) max_gap_us=(\d+) restored=([01]) first_loaded=([01]) load_writes=(\d+)$",
        text,
        re.M,
    )
    if len(begin) != 1 or len(end) != 1:
        raise ValueError("Missing unique completed capture")
    count, observations, coherent, gap, restored, first_loaded, writes = map(
        int, end[0]
    )
    if (
        count != 301
        or coherent != 1
        or restored != 1
        or gap >= 400
        or first_loaded != int(begin[0])
        or not (16200 if first_loaded else 10800) <= writes <= 31000
    ):
        raise ValueError("Capture or register restoration failed")
    if len(re.findall(r"^LOAD ", text, re.M)) != writes:
        raise ValueError("USB load transcript is incomplete")
    pulses = [
        tuple(map(int, row))
        for row in re.findall(
            r"^PULSE i=(\d+) raw_low=(\d+) raw_high=(\d+) count_low=(\d+) count_high=(\d+)$",
            text,
            re.M,
        )
    ]
    records = []
    for line in text.splitlines():
        if line.startswith("PROD "):
            tokens = line[5:].split()
            if any(not re.fullmatch(r"[a-z_]+=[0-9]+", token) for token in tokens):
                raise ValueError("Malformed production record")
            pairs = [token.split("=") for token in tokens]
            if len({k for k, v in pairs}) != len(pairs):
                raise ValueError("Duplicate production field")
            records.append({k: int(v) for k, v in pairs})
    status = re.findall(r"^GPS_STATUS (.+)$", text, re.M)
    if len(records) != observations or len(status) != 1:
        raise ValueError("Incomplete production evidence")
    status = json.loads(status[0])
    baseline = re.findall(r"^GPS_BASELINE_STATUS (.+)$", text, re.M)
    if len(baseline) != 1:
        raise ValueError("Missing pre-capture UART health")
    baseline = json.loads(baseline[0])
    deltas = {
        k: status[k] - baseline[k]
        for k in ("uart_errors", "dropped", "capture_rejections")
    }
    if any(v != 0 for v in deltas.values()):
        raise ValueError("UART/capture records lost during defined capture")
    return dict(
        serial=serial,
        source=source,
        pins=dict(pps=int(pps), clock=int(clock)),
        pulses=count,
        max_gap_us=gap,
        restored=True,
        first_loaded=bool(first_loaded),
        load_writes=writes,
        health_before={
            k: baseline[k] for k in ("uart_errors", "dropped", "capture_rejections")
        },
        health_deltas=deltas,
        health={
            k: status[k]
            for k in (
                "uart_errors",
                "dropped",
                "capture_rejections",
                "maximum_irq_latency_ns",
                "capture_error_bound_ns",
            )
        },
        independent=analyze_windows(pulses, pps_endpoint_us=10),
        production=compare_production(pulses, records, first_loaded=bool(first_loaded)),
    )


if __name__ == "__main__":
    print(json.dumps(analyze(Path(sys.argv[1]).read_text()), indent=2))
