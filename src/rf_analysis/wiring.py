"""Strict acceptance of finite, input-only GPSDO wiring checks."""

import re


def analyze_wiring(text, phase):
    if phase not in ("off", "clock", "pps"):
        raise ValueError("Unknown wiring phase")
    lines = text.splitlines()
    if len(lines) != 8 or lines[-1] != "END_CHECK":
        raise ValueError("Incomplete wiring check")
    header = re.fullmatch(
        r"CHECK duration_us=(\d+) clock_edges=(\d+) max_gap_us=(\d+) coherent=1 input_only=1",
        lines[0],
    )
    if not header:
        raise ValueError("Invalid or incoherent wiring check")
    duration, edges, gap = map(int, header.groups())
    if not 2_200_000 <= duration <= 2_210_000 or gap >= 400:
        raise ValueError("Invalid wiring observation interval")
    pins = {}
    for expected, line in zip(range(8, 14), lines[1:7]):
        row = re.fullmatch(r"CHECK_PIN gp=(\d+) rises=(\d+) falls=(\d+)", line)
        if not row:
            raise ValueError("Malformed GPIO observation")
        gp, rises, falls = map(int, row.groups())
        if gp != expected:
            raise ValueError("Missing, duplicate, or unexpected GPIO")
        pins[gp] = dict(rises=rises, falls=falls)
    active = 9 if phase == "clock" else 11 if phase == "pps" else None
    if any((p["rises"] or p["falls"]) for gp, p in pins.items() if gp != active):
        raise ValueError("Unexpected signal on a quiet or neighbouring GPIO")
    frequency = edges * 1_000_000 / duration
    if phase == "clock":
        if not 995_000 <= frequency <= 1_005_000:
            raise ValueError("GP9 does not receive the selected 1 MHz clock")
    elif edges:
        raise ValueError("Unexpected GP9 clock edges")
    if phase == "pps" and not (
        2 <= pins[11]["rises"] <= 3 and 1 <= pins[11]["falls"] <= 3
    ):
        raise ValueError("GP11 does not receive the selected PPS")
    return dict(
        phase=phase,
        duration_us=duration,
        clock_edges=edges,
        approximate_clock_hz=frequency,
        maximum_gap_us=gap,
        pins=pins,
        scope="Digital routing only; no independent ground-lead continuity, voltage, waveform, or metrology qualification.",
    )
