"""Bounded clock-specific PIO qualification plans; no device or process access."""

import copy
import hashlib
import json

BANDS = dict(
    zip(
        (
            "2200m",
            "630m",
            "160m",
            "80m",
            "60m",
            "40m",
            "30m",
            "20m",
            "17m",
            "15m",
            "12m",
            "10m",
            "6m",
            "4m",
            "2m",
        ),
        (
            137500,
            475700,
            1838100,
            3570100,
            5288700,
            7040100,
            10140200,
            14097100,
            18106100,
            21096100,
            24926100,
            28126100,
            50294500,
            70092500,
            144490500,
        ),
    )
)
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


def compose(bands=None, *, sample_rate_hz=RATE, keyed_dot_ns=700000000):
    if type(sample_rate_hz) is not int or sample_rate_hz not in CLOCKS:
        raise ValueError("Unsupported PIO sample clock")
    if type(keyed_dot_ns) is not int or keyed_dot_ns not in (700000000, 3000000000):
        raise ValueError("Unsupported keyed dot duration")
    selected = list(BANDS) if bands is None else list(bands)
    if (
        not selected
        or len(set(selected)) != len(selected)
        or any(b not in BANDS for b in selected)
    ):
        raise ValueError(
            "Bands must be a nonempty unique subset of the campaign band list"
        )
    plan = dict(
        version=1 if sample_rate_hz == RATE and keyed_dot_ns == 700000000 else 2,
        sample_rate_hz=sample_rate_hz,
        engine="pio-dma-gp2",
        gpio=2,
        frequency_correction_ppb=0,
        wspr_identity=["AA0NT", "EM18", "37"],
        path=dict(
            pico_attenuation_db=60,
            gpsdo_attenuation_db=60,
            topology="separate attenuators into common combiner and SDR",
            attenuation_basis="operator reported",
            antenna=False,
            filter="not characterized",
        ),
        thresholds=dict(
            offset_hz=100,
            contrast_db=10,
            duration_s=0.02,
            wspr_spacing_hz=0.05,
            wspr_residual_hz=0.1,
            keyed_spacing_hz=0.2,
            keyed_timing_s=0.02,
        ),
        bands=[
            dict(
                band=b,
                frequency_hz=BANDS[b],
                supported=BANDS[b] < sample_rate_hz // 2 - 6,
                jobs={
                    m: make_job(
                        m,
                        BANDS[b],
                        sample_rate_hz=sample_rate_hz,
                        keyed_dot_ns=keyed_dot_ns,
                    )
                    for m in MODES
                }
                if BANDS[b] < sample_rate_hz // 2 - 6
                else {},
            )
            for b in selected
        ],
        repetitions=dict(TONE=1, WSPR=3, QRSS=3, FSKCW=3, DFCW=3),
        scope="operational conducted criteria; spectrum diagnostic; no emissions, power or calibrated UTC qualification",
    )

    if keyed_dot_ns != 700000000:
        plan["keyed_dot_ns"] = keyed_dot_ns
    return plan


def validate(plan):
    """Permit only supported clock and band selection, never arbitrary live jobs."""
    if not isinstance(plan, dict) or not isinstance(plan.get("bands"), list):
        raise ValueError("Invalid plan")
    try:
        expected = compose(
            [b["band"] for b in plan["bands"]],
            sample_rate_hz=plan.get("sample_rate_hz"),
            keyed_dot_ns=plan.get("keyed_dot_ns", 700000000),
        )
    except (KeyError, TypeError) as error:
        raise ValueError("Invalid band entries") from error
    if digest(plan) != digest(expected):
        raise ValueError("Plan differs from the bounded campaign contract")
    return copy.deepcopy(plan)


def initial_matrix(plan):
    validate(plan)
    return [
        dict(
            band=b["band"],
            frequency_hz=b["frequency_hz"],
            mode=m,
            status="blocked" if b["supported"] else "unsupported",
            reason="not yet measured"
            if b["supported"]
            else f"outside direct {plan['sample_rate_hz'] // 1000000} MHz PIO baseband",
            observations=[],
        )
        for b in plan["bands"]
        for m in MODES
    ]


def classify(observations, required):
    if any(o.get("cleanup_verified") is not True for o in observations):
        return "blocked", "cleanup or output state unverified"
    if any(o.get("fixture_ok") is not True for o in observations):
        return "blocked", "receiver or fixture evidence invalid"
    if any(o.get("passed") is False for o in observations):
        return "failed", "measured operational gate failed"
    if len(observations) != required or any(
        o.get("passed") is not True for o in observations
    ):
        return "blocked", "missing complete passing observations"
    return "qualified", "recorded operational criteria passed; spectrum diagnostic only"
