"""Read-only pairing-state diagnostics; never accepts a calibration capture."""

import re
from collections import Counter
import itertools

ERRORS = {
    "none",
    "capture_lost",
    "invalid_pps",
    "pps_discontinuity",
    "unqualified_pairing",
    "invalid_utc",
    "ambiguous_utc",
    "unpaired_utc",
    "invalid_pps_offset",
    "future_pps_epoch",
    "pairing_acquisition",
    "receiver_command_failed",
    "ambiguous_pps_edge",
    "pps_counter_unarmed",
    "capture_uncertainty_exceeded",
    "pps_counter_wrap",
    "pps_capture_clock_changed",
    "pps_capture_bracket_invalid",
}
KEYS = {
    "i",
    "raw_ns",
    "candidate_utc_ns",
    "candidate_raw_ns",
    "candidate_pps_ns",
    "observation_raw_ns",
    "observations",
    "rejected",
    "uart_errors",
    "dropped",
    "capture_rejections",
    "flags",
    "error",
}


def diagnose_pairing(text):
    headers = re.findall(
        r"^BEGIN_PAIRING_TRACE samples=(\d+) valid=([01]) period_ns=100000000 max_work_us=(\d+)$",
        text,
        re.MULTILINE,
    )
    lines = text.splitlines()
    if not headers and not any(
        l.startswith(("BEGIN_PAIRING_TRACE", "PAIRING ", "END_PAIRING_TRACE"))
        for l in lines
    ):
        return None
    if len(headers) != 1 or text.splitlines().count("END_PAIRING_TRACE") != 1:
        raise ValueError("Incomplete pairing trace")
    count, valid, work = map(int, headers[0])
    if not 0 <= count <= 3200 or (valid and not count):
        raise ValueError("Invalid pairing trace count")
    rows = []
    begin = next(i for i, l in enumerate(lines) if l.startswith("BEGIN_PAIRING_TRACE "))
    end = lines.index("END_PAIRING_TRACE")
    if end <= begin or any(
        l.startswith("PAIRING ") for l in lines[:begin] + lines[end + 1 :]
    ):
        raise ValueError("Misordered pairing trace")
    for line in lines[begin + 1 : end]:
        if not line.startswith("PAIRING "):
            raise ValueError("Unexpected pairing trace row")
        pairs = [token.split("=") for token in line[8:].split()]
        if (
            any(len(p) != 2 for p in pairs)
            or len(pairs) != len(KEYS)
            or {p[0] for p in pairs} != KEYS
        ):
            raise ValueError("Malformed pairing record")
        d = dict(pairs)
        if d["error"] not in ERRORS or any(
            not re.fullmatch(r"[0-9]+", v) for k, v in d.items() if k != "error"
        ):
            raise ValueError("Invalid pairing record value")
        d = {k: v if k == "error" else int(v) for k, v in d.items()}
        if (
            d["i"] != len(rows)
            or not d["raw_ns"]
            or d["flags"] > 15
            or any(v > 2**64 - 1 for k, v in d.items() if k != "error")
            or any(
                d[k] > 2**32 - 1
                for k in (
                    "observations",
                    "rejected",
                    "uart_errors",
                    "dropped",
                    "capture_rejections",
                )
            )
        ):
            raise ValueError("Invalid pairing record bounds")
        if rows and (
            d["raw_ns"] <= rows[-1]["raw_ns"]
            or any(
                d[k] < rows[-1][k]
                for k in (
                    "observations",
                    "rejected",
                    "uart_errors",
                    "dropped",
                    "capture_rejections",
                )
            )
        ):
            raise ValueError("Reversed pairing trace")
        rows.append(d)
    if len(rows) != count:
        raise ValueError("Missing pairing samples")
    changes = [
        d
        for i, d in enumerate(rows)
        if i == 0
        or any(
            d[k] != rows[i - 1][k]
            for k in (
                "error",
                "observations",
                "candidate_utc_ns",
                "flags",
                "rejected",
                "uart_errors",
                "dropped",
                "capture_rejections",
            )
        )
    ]
    stalls = []
    start = 0
    for i in range(1, len(rows)):
        if rows[i]["observations"] != rows[start]["observations"]:
            if rows[i]["raw_ns"] - rows[start]["raw_ns"] >= 1_500_000_000:
                stalls.append(
                    {
                        "first_raw_ns": rows[start]["raw_ns"],
                        "last_raw_ns": rows[i]["raw_ns"],
                        "observations": rows[start]["observations"],
                        "errors": sorted({r["error"] for r in rows[start:i]}),
                    }
                )
            start = i
    if rows and rows[-1]["raw_ns"] - rows[start]["raw_ns"] >= 1_500_000_000:
        stalls.append(
            {
                "first_raw_ns": rows[start]["raw_ns"],
                "last_raw_ns": rows[-1]["raw_ns"],
                "observations": rows[start]["observations"],
                "errors": sorted({r["error"] for r in rows[start:]}),
                "open_end": True,
            }
        )
    aux = []
    aux_headers = re.findall(
        r"^BEGIN_AUX_PPS gp=3 pulses=(\d+) valid=([01])$", text, re.MULTILINE
    )
    if aux_headers or any(l.startswith(("AUX_PPS ", "END_AUX_PPS")) for l in lines):
        if len(aux_headers) != 1 or lines.count("END_AUX_PPS") != 1:
            raise ValueError("Incomplete auxiliary PPS trace")
        expected, aux_valid = map(int, aux_headers[0])
        if expected > 320 or not aux_valid:
            raise ValueError("Invalid auxiliary PPS trace")
        for i, low, high in re.findall(
            r"^AUX_PPS i=(\d+) raw_low_us=(\d+) raw_high_us=(\d+)$", text, re.MULTILINE
        ):
            i, low, high = map(int, (i, low, high))
            if (
                i != len(aux)
                or not 0 <= high - low <= 100
                or (aux and low * 1000 <= aux[-1][1])
            ):
                raise ValueError("Invalid auxiliary PPS bracket")
            aux.append((low * 1000, high * 1000))
        if len(aux) != expected:
            raise ValueError("Missing auxiliary PPS endpoints")
    primary = [
        (int(low) * 1000, int(high) * 1000)
        for low, high in re.findall(
            r"^PULSE i=\d+ raw_low=(\d+) raw_high=(\d+) count_low=\d+ count_high=\d+$",
            text,
            re.MULTILINE,
        )
    ]
    for row in changes:
        candidate = row["candidate_raw_ns"]
        for name, pulses in (("primary_delays_ns", primary), ("qlg3_delays_ns", aux)):
            row[name] = [
                [candidate - high, candidate - low]
                for low, high in pulses
                if 0 <= candidate - low <= 2_000_000_000
            ]
    phase = []
    for low, high in primary:
        if aux:
            a, b = min(aux, key=lambda p: abs(sum(p) - low - high))
            if abs((a + b - low - high) / 2) < 600_000_000:
                phase.append(((a - high), (b - low)))
    return {
        "qualification": "not_evaluated",
        "valid": bool(valid),
        "samples": count,
        "first_raw_ns": rows[0]["raw_ns"] if rows else None,
        "last_raw_ns": rows[-1]["raw_ns"] if rows else None,
        "maximum_sample_gap_ns": max(
            (b["raw_ns"] - a["raw_ns"] for a, b in itertools.pairwise(rows)), default=0
        ),
        "maximum_work_us": work,
        "error_sample_counts": dict(Counter(r["error"] for r in rows)),
        "observation_stalls": stalls,
        "state_changes": changes,
        "auxiliary_pps_pulses": len(aux),
        "qlg3_minus_primary_phase_ns": [
            min(p[0] for p in phase),
            max(p[1] for p in phase),
        ]
        if phase
        else None,
    }
