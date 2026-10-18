"""Deterministic finite RF sample jobs for offline analysis tests."""
import copy
import hashlib
import json

MODES = ("TONE", "WSPR", "QRSS", "FSKCW", "DFCW")

RATE = 138000000

CLOCKS = (132000000, RATE, 150000000)

GOLDEN37 = (
    "13220200302213120030232311300200223201230220201213223121020110322221321030323001023231"
    "2023321232223022203021221110310011010221130002210302110202202112323320031202"
)

def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()

def make_job(mode, frequency, *, sample_rate_hz=RATE, keyed_dot_ns=700000000):
    """Canonical ETE keyed jobs, five-second carrier, or Type 1 WSPR AA0NT EM18 37."""
    if (
        type(keyed_dot_ns) is not int
        or keyed_dot_ns not in (700000000, 3000000000)
        or type(sample_rate_hz) is not int
        or sample_rate_hz not in CLOCKS
        or mode not in MODES
        or type(frequency) is not int
        or not 100005 <= frequency < sample_rate_hz // 2 - 6
    ):
        raise ValueError("Unsupported mode or direct-baseband frequency")
    events = []

    def emit(duration, hz):
        start = sum(int(e["duration_ns"]) for e in events)
        event = dict(
            offset_ns=str(start), duration_ns=str(duration), rf_on=hz is not None
        )
        if hz is not None:
            event["frequency_nhz"] = str(hz)
        events.append(event)

    base = frequency * 1000000000
    if mode == "WSPR":
        for i, tone in enumerate(GOLDEN37):
            begin = (i * 8192 * 1000000000 + 6000) // 12000
            end = ((i + 1) * 8192 * 1000000000 + 6000) // 12000
            emit(end - begin, base + int(tone) * 1464843750)
    elif mode == "TONE":
        emit(5000000000, base)
    else:
        # E T E. FSKCW marks high and spaces low. DFCW uses equal-duration
        # dot/high and dash/low elements with one-dot inter-character silence.
        dot = keyed_dot_ns
        emit(1000000000, None)
        for i, symbol in enumerate(".-."):
            emit(
                dot if mode == "DFCW" or symbol == "." else 3 * dot,
                base - 5000000000 if mode == "DFCW" and symbol == "-" else base,
            )
            if i != 2:
                emit(
                    dot if mode == "DFCW" else 3 * dot,
                    base - 5000000000 if mode == "FSKCW" else None,
                )
        emit(1000000000, None)
    job = dict(
        profile="rf-events/1",
        mode=mode.lower(),
        events=events,
        total_duration_ns=str(sum(int(e["duration_ns"]) for e in events)),
        allow_frequency_adjustment=True,
    )
    job["job_id"] = digest(job)[:32]
    return job
