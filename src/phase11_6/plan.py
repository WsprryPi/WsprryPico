"""Deterministic Phase 11.6 packet plan; this module never accesses hardware."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import OrderedDict


SCHEMA = "phase11.6-plan-v3"
MATRIX_SCHEMA = "phase11.6-matrix-v3"
SAMPLE_RATE_HZ = 138_000_000
DIRECT_MAXIMUM_HZ = 68_999_999
FIRMWARE_SOURCE = "2eaa99945d21501cd4dbdac98c25be5fa146e479"
FIRMWARE_UF2_SHA256 = (
    "af3f6917ba807a1526dca6e15f19fff1974410fc87ecc32fd6e9c4f07059525f"
)
PICO_SERIAL = "0BF4B4AEC9FFB344"
PICO_DEVICE_ID = "fd6127d11d6aca42a9905fa3fb1bf1d5"
PICO_PHASE115_BOOT = "ff719d304f1ba4ac23fddd93561b26f0"
PICO_PREDECESSOR_BOOT = "d2f657c2099c67a7af2ef390426bda10"
PICO_ACCEPTED_BOOT = "b72fed2c17583cc7aba0f1345f76a3b2"
PREDECESSOR_PLAN_SHA256 = (
    "9324f6057ae8f4e552375919836bbe4e0c30176405eedaf3915f0ab67d929556"
)
PEER_SERIAL = "CDDBF8767C506C07"
PEER_DEVICE_ID = "29f20b7342051ef947aa56cb9d4fab42"
RECEIVER_SERIAL = "2404058C60"
WSPR_SYMBOLS = (
    "13200002302011100030232111300002223001230022201211203321000310302221301030323003003233"
    "2021321030223220203223221310310213010221110002210302110200222310303320011002"
)
MESSAGE = "ET E"
LONG_MESSAGE = "E T " * 8
MODES = ("TONE", "WSPR", "QRSS", "FSKCW", "DFCW")
BANDS = OrderedDict(
    (
        ("2200m", 137_500),
        ("630m", 475_700),
        ("160m", 1_838_100),
        ("80m", 3_570_100),
        ("60m", 5_288_700),
        ("40m", 7_040_100),
        ("30m", 10_140_200),
        ("20m", 14_097_100),
        ("17m", 18_106_100),
        ("15m", 21_096_100),
        ("12m", 24_926_100),
        ("10m", 28_126_100),
        ("6m", 50_294_500),
        ("4m", 70_092_500),
        ("2m", 144_490_500),
    )
)
MORSE = {
    "E": ".",
    "T": "-",
}
NS = 1_000_000_000
DOT_NS = 3 * NS
DASH_NS = 9 * NS
INTRA_NS = 3 * NS
CHARACTER_NS = 9 * NS
WORD_NS = 21 * NS
TAIL_NS = 1_000
SHIFT_NHZ = 5 * NS
WSPR_SPACING_NHZ = 1_464_843_750
WSPR_LOWEST_OFFSET_NHZ = -2_197_265_625
WSPR_SYMBOL_NS = 682_666_666


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _event(events: list[dict], duration_ns: int, frequency_nhz: int | None) -> None:
    offset = sum(int(item["duration_ns"]) for item in events)
    value = {
        "offset_ns": str(offset),
        "duration_ns": str(duration_ns),
        "rf_on": frequency_nhz is not None,
    }
    if frequency_nhz is not None:
        value["frequency_nhz"] = str(frequency_nhz)
    events.append(value)


def message_events(mode: str, frequency_hz: int, message: str = MESSAGE) -> list[dict]:
    """Mirror the maintained compact-message compiler for the frozen alphabet."""
    if mode not in ("QRSS", "FSKCW", "DFCW") or not 1 <= len(message) <= 32:
        raise ValueError("invalid message mode or length")
    if any(character not in "ET " for character in message):
        raise ValueError("planner message is outside its audited alphabet")
    mark = (frequency_hz * NS) + (SHIFT_NHZ if mode in ("FSKCW", "DFCW") else 0)
    space = frequency_hz * NS
    events: list[dict] = []
    for index, character in enumerate(message):
        if character == " ":
            continue
        code = MORSE[character]
        for element_index, element in enumerate(code):
            duration = DOT_NS if mode == "DFCW" or element == "." else DASH_NS
            frequency = space if mode == "DFCW" and element == "-" else mark
            _event(events, duration, frequency)
            if element_index + 1 < len(code):
                _event(events, INTRA_NS, space if mode == "FSKCW" else None)
        next_index = index + 1
        while next_index < len(message) and message[next_index] == " ":
            next_index += 1
        if next_index < len(message):
            gap = CHARACTER_NS if next_index == index + 1 else WORD_NS
            _event(events, gap, space if mode == "FSKCW" else None)
    if not events:
        raise ValueError("message has no marks")
    _event(events, TAIL_NS, None)
    return events


def wspr_events(frequency_hz: int) -> list[dict]:
    events: list[dict] = []
    base_nhz = frequency_hz * NS
    for tone in WSPR_SYMBOLS:
        _event(
            events,
            WSPR_SYMBOL_NS,
            base_nhz + WSPR_LOWEST_OFFSET_NHZ + int(tone) * WSPR_SPACING_NHZ,
        )
    return events


def raw_job(mode: str, frequency_hz: int, token: str, *, duration_ns: int | None = None,
            message: str = MESSAGE) -> dict:
    if frequency_hz > DIRECT_MAXIMUM_HZ:
        raise ValueError("unsupported direct-synthesis frequency")
    if mode == "TONE":
        events: list[dict] = []
        _event(events, duration_ns or 5 * NS, frequency_hz * NS)
    elif mode == "WSPR":
        events = wspr_events(frequency_hz)
    else:
        events = message_events(mode, frequency_hz, message)
    job = {
        "profile": "rf-events/1",
        "mode": mode.lower(),
        "events": events,
        "total_duration_ns": str(sum(int(item["duration_ns"]) for item in events)),
        "allow_frequency_adjustment": True,
    }
    job["job_id"] = hashlib.sha256(f"phase11.6:{token}".encode()).hexdigest()[:32]
    return job


def compact_job(mode: str, frequency_hz: int, token: str, *, message: str = MESSAGE) -> dict:
    job = raw_job(mode, frequency_hz, token, message=message)
    return {
        "job_id": job["job_id"],
        "mode": mode.lower(),
        "message": message,
        "frequency_nhz": str(
            frequency_hz * NS + (SHIFT_NHZ if mode in ("FSKCW", "DFCW") else 0)
        ),
        "space_frequency_nhz": str(frequency_hz * NS if mode != "QRSS" else 0),
        "timing": {
            "dot_ns": str(DOT_NS),
            "dash_ns": str(DOT_NS if mode == "DFCW" else DASH_NS),
            "intra_gap_ns": str(INTRA_NS),
            "character_gap_ns": str(CHARACTER_NS),
            "word_gap_ns": str(WORD_NS),
        },
        "repeat_count": 1,
        "repeat_gap_ns": "0",
        "allow_frequency_adjustment": True,
    }


def _planned_job(band: str, mode: str, index: int, path: str, *, matrix_credit: bool = True,
                 purpose: str = "nominal", message: str = MESSAGE,
                 duration_ns: int | None = None, abort: str | None = None) -> dict:
    frequency = BANDS[band]
    token = f"{band}:{mode}:{index}:{path}:{purpose}"
    expected = raw_job(mode, frequency, token, duration_ns=duration_ns, message=message)
    value = {
        "id": token,
        "band": band,
        "mode": mode,
        "nominal_frequency_hz": frequency,
        "purpose": purpose,
        "submission_path": path,
        "matrix_credit": matrix_credit,
        "planned_duration_ns": int(expected["total_duration_ns"]),
        "expected_job": expected,
        "browser_page_interaction": True,
        "controller_disconnect_after_arm": path == "controller_disconnect",
    }
    if path == "browser_compact":
        value["compact_request"] = compact_job(mode, frequency, token, message=message)
    if path == "production":
        value["runtime_job_id"] = True
        value["production_expectation"] = {
            "mode": mode,
            "message": message if mode in ("QRSS", "FSKCW", "DFCW") else None,
            "callsign": "AA0NT" if mode == "WSPR" else None,
            "grid": "EM18" if mode == "WSPR" else None,
            "power_dbm": 20 if mode == "WSPR" else None,
        }
    if abort:
        value.update(
            abort={
                "mechanism": abort,
                "foreign_principal_rejection": abort == "foreign_then_owner",
                "capture_through_trailing_quiet": True,
            }
        )
    return value


def _band_packet(band: str) -> dict:
    jobs = [
        _planned_job(band, "TONE", 0, "controller_disconnect"),
        _planned_job(band, "WSPR", 0, "production"),
        _planned_job(band, "WSPR", 1, "browser_raw"),
        _planned_job(band, "WSPR", 2, "controller_disconnect"),
    ]
    for mode in ("QRSS", "FSKCW", "DFCW"):
        jobs.extend(
            (
                _planned_job(band, mode, 0, "production"),
                _planned_job(band, mode, 1, "browser_compact"),
                _planned_job(band, mode, 2, "controller_disconnect"),
            )
        )
    if band == "20m":
        jobs.append(
            _planned_job(
                band,
                "QRSS",
                3,
                "browser_compact",
                matrix_credit=False,
                purpose="32-character-word-space-semantics",
                message=LONG_MESSAGE,
            )
        )
    return {
        "packet_id": f"band-{band}",
        "kind": "ordinary-band",
        "band": band,
        "jobs": jobs,
        "planned_jobs": len(jobs),
        "planned_rf_seconds": sum(job["planned_duration_ns"] for job in jobs) / NS,
    }


def _integration_packets() -> list[dict]:
    cases = (
        ("2200m", "TONE", "controller", "owner"),
        ("2200m", "QRSS", "browser_compact", "foreign_then_owner"),
        ("2200m", "FSKCW", "production", "console"),
        ("20m", "WSPR", "production", "owner"),
        ("20m", "DFCW", "controller", "foreign_then_owner"),
        ("20m", "TONE", "browser_raw", "console"),
        ("6m", "QRSS", "production", "owner"),
        ("6m", "FSKCW", "browser_compact", "foreign_then_owner"),
        ("6m", "DFCW", "controller", "console"),
    )
    packets = []
    for packet_band in ("2200m", "20m", "6m"):
        jobs = []
        for index, (band, mode, path, abort) in enumerate(cases):
            if band != packet_band:
                continue
            jobs.append(
                _planned_job(
                    band,
                    mode,
                    index,
                    path,
                    matrix_credit=False,
                    purpose="abort-authority-integration",
                    duration_ns=30 * NS if mode == "TONE" else None,
                    abort=abort,
                )
            )
        packets.append(
            {
                "packet_id": f"integration-{packet_band}",
                "kind": "integration",
                "band": packet_band,
                "jobs": jobs,
                "planned_jobs": len(jobs),
                "planned_rf_seconds": sum(job["planned_duration_ns"] for job in jobs) / NS,
            }
        )
    return packets


def compose() -> dict:
    packets = [_band_packet(band) for band, hz in BANDS.items() if hz <= DIRECT_MAXIMUM_HZ]
    packets.extend(_integration_packets())
    planned_jobs = sum(packet["planned_jobs"] for packet in packets)
    planned_seconds = sum(
        job["planned_duration_ns"] for packet in packets for job in packet["jobs"]
    ) / NS
    plan = {
        "schema": SCHEMA,
        "phase": "11.6",
        "repositories": {
            "WsprryPico": "8d84dbe567cdb4e3814281c4792c6d544ee2b711",
            "WsprryPi": "3b046ebe3eaa19ae764706d844fa7354033c32df",
        },
        "amendment": {
            "predecessor_plan_sha256": PREDECESSOR_PLAN_SHA256,
            "scope": "clock-refinement repair candidate identity and applicability gate",
            "rf_job_payloads_changed": False,
            "reason": (
                "operator-authorized repair of the armed UTC-to-monotonic projection "
                "defect preserved by Phase 11.6 attempt 41"
            ),
            "authorization_date": "2026-09-18",
            "deployment": "serial-bound corrected 135500 Hz UF2 flash",
            "configuration_writes": 0,
            "firmware_flashes": 1,
        },
        "accepted_configuration": {
            "pico_serial": PICO_SERIAL,
            "device_id": PICO_DEVICE_ID,
            "phase11_5_accepted_boot_id": PICO_PHASE115_BOOT,
            "accepted_boot_id": PICO_ACCEPTED_BOOT,
            "source_revision": FIRMWARE_SOURCE,
            "uf2_sha256": FIRMWARE_UF2_SHA256,
            "board": "Pico 2 W / RP2350 Arm",
            "system_clock_hz": SAMPLE_RATE_HZ,
            "pio_divider": 1,
            "engine": "pio-dma-gp2",
            "renderer": "RAM",
            "output": "GP2",
            "frequency_correction_ppb": 0,
            "boot_transition": {
                "from_boot_id": PICO_PREDECESSOR_BOOT,
                "to_boot_id": PICO_ACCEPTED_BOOT,
                "source_revision_unchanged": False,
                "uf2_sha256_unchanged": False,
                "hardware_configuration_unchanged": True,
                "postrestart_allocator_failures": 0,
                "postrestart_tls_allocation_failures": 0,
                "private_evidence_directory":
                    "repair-2eaa999-deployment/corrected-deployment",
            },
        },
        "peer": {"pico_serial": PEER_SERIAL, "device_id": PEER_DEVICE_ID},
        "receiver": {
            "driver": "sdrplay",
            "serial": RECEIVER_SERIAL,
            "format": "CF32",
            "sample_rate_hz": 250_000,
            "bandwidth_hz": 200_000,
            "gain_db": 20,
            "agc": False,
            "bias_tee": False,
            "correction_ppm": 0,
            "center_offset_hz": -25_000,
        },
        "rf_path_declaration": {
            "source": "operator-confirmed unchanged prior conducted setup",
            "pico_output": "GP2",
            "pico_attenuation_db": 60,
            "topology": "attenuated branch into common SDR combiner",
            "external_filter": "none",
            "antenna": False,
            "gpsdo_operations_authorized_by_packet": 0,
            "wsprrypi_gpio_rf_operations_authorized_by_packet": 0,
        },
        "content": {
            "message": MESSAGE,
            "word_space_message": LONG_MESSAGE,
            "wspr": {"callsign": "AA0NT", "grid": "EM18", "power_dbm": 20},
            "wspr_frequency_convention": (
                "listed nominal is RF center; tones are -2.197265625, "
                "-0.732421875, +0.732421875 and +2.197265625 Hz"
            ),
            "wspr_symbol_duration_ns": str(WSPR_SYMBOL_NS),
            "dot_ns": str(DOT_NS),
            "dash_ns": str(DASH_NS),
            "intra_gap_ns": str(INTRA_NS),
            "character_gap_ns": str(CHARACTER_NS),
            "word_gap_ns": str(WORD_NS),
            "shift_hz": 5,
            "fskcw_polarity": "mark high; keyed spaces low",
            "dfcw_polarity": (
                "reverse DFCW profile: dot high; dash low; conventional DFCW "
                "is dot low; dash high"
            ),
        },
        "tolerances": {
            "absolute_indicated_frequency_hz": 100.0,
            "common_receiver_offset_note": "not calibrated absolute frequency",
            "tone_duration_s": 0.02,
            "keyed_edge_s": 0.05,
            "keyed_spacing_hz": 0.2,
            "wspr_spacing_hz": 0.05,
            "wspr_symbol_residual_hz": 0.1,
            "minimum_contrast_db": 10.0,
            "minimum_leading_quiet_s": 1.0,
            "minimum_trailing_quiet_s": 1.0,
            "analysis_time_resolution_s": 0.001,
        },
        "limits": {
            "ordinary_packet_max_jobs": 16,
            "ordinary_packet_max_planned_rf_seconds": 1800,
            "campaign_max_jobs": 300,
            "campaign_max_planned_rf_seconds": 18000,
            "max_job_seconds": 3600,
            "max_events": 512,
        },
        "packets": packets,
        "planned_jobs": planned_jobs,
        "planned_rf_seconds": planned_seconds,
        "capture_estimate_bytes": int((planned_seconds + planned_jobs * 4) * 250_000 * 8),
        "source_impact": {
            "firmware_runtime_changes": 1,
            "decision": "reproject immutable UTC from the newest admissible armed clock sample",
            "phase11_5_applicability": (
                "R1.1/R1.5, the shared R2 launch path and R6 timing/resources require "
                "the documented repaired-candidate gate before transfer"
            ),
        },
    }
    validate(plan)
    return plan


def validate(plan: dict) -> dict:
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("invalid Phase 11.6 plan schema")
    packets = plan.get("packets")
    if not isinstance(packets, list) or not packets:
        raise ValueError("missing packet schedule")
    all_jobs = []
    for packet in packets:
        jobs = packet.get("jobs")
        if not isinstance(jobs, list) or packet.get("planned_jobs") != len(jobs):
            raise ValueError("packet job accounting mismatch")
        seconds = sum(job["planned_duration_ns"] for job in jobs) / NS
        if packet.get("planned_rf_seconds") != seconds:
            raise ValueError("packet duration accounting mismatch")
        if len(jobs) > 16 or seconds > 1800:
            raise ValueError("ordinary packet ceiling exceeded")
        all_jobs.extend(jobs)
    if len({job["id"] for job in all_jobs}) != len(all_jobs):
        raise ValueError("duplicate planned job identity")
    if plan.get("planned_jobs") != len(all_jobs) or len(all_jobs) > 300:
        raise ValueError("campaign job accounting mismatch")
    seconds = sum(job["planned_duration_ns"] for job in all_jobs) / NS
    if plan.get("planned_rf_seconds") != seconds or seconds > 18000:
        raise ValueError("campaign duration accounting mismatch")
    primary = [job for job in all_jobs if job["matrix_credit"]]
    for band, hz in BANDS.items():
        rows = [job for job in primary if job["band"] == band]
        if hz > DIRECT_MAXIMUM_HZ:
            if rows:
                raise ValueError("unsupported band has RF jobs")
            continue
        counts = {mode: sum(job["mode"] == mode for job in rows) for mode in MODES}
        if counts != {"TONE": 1, "WSPR": 3, "QRSS": 3, "FSKCW": 3, "DFCW": 3}:
            raise ValueError("primary matrix count mismatch")
        for mode in MODES:
            mode_jobs = [job for job in rows if job["mode"] == mode]
            if not any(job["controller_disconnect_after_arm"] for job in mode_jobs):
                raise ValueError("row lacks controller disconnect completion")
            if not all(job["browser_page_interaction"] for job in mode_jobs):
                raise ValueError("row lacks browser page interaction")
            if mode != "TONE" and not any(
                job["submission_path"] == "production"
                for job in all_jobs
                if job["band"] == band and job["mode"] == mode
            ):
                raise ValueError("row lacks production operation")
    if len(LONG_MESSAGE) != 32 or not LONG_MESSAGE.endswith(" "):
        raise ValueError("32-character word-space case changed")
    for job in all_jobs:
        expected = job["expected_job"]
        if job["planned_duration_ns"] != int(expected["total_duration_ns"]):
            raise ValueError("planned job duration differs from expected job")
        if len(expected["events"]) > 512 or job["planned_duration_ns"] > 3600 * NS:
            raise ValueError("device job limit exceeded")
        frequencies = [int(event["frequency_nhz"]) / NS for event in expected["events"]
                       if event["rf_on"]]
        if any(abs(frequency - job["nominal_frequency_hz"]) > 10 for frequency in frequencies):
            raise ValueError("mode offset exceeds frozen +/-10 Hz range")
    return copy.deepcopy(plan)


def initial_matrix(plan: dict) -> dict:
    validate(plan)
    rows = []
    for band, frequency in BANDS.items():
        for mode in MODES:
            supported = frequency <= DIRECT_MAXIMUM_HZ
            rows.append(
                {
                    "band": band,
                    "nominal_frequency_hz": frequency,
                    "mode": mode,
                    "disposition": "NOT TESTED" if supported else "UNSUPPORTED_CONFIGURATION",
                    "reason": (
                        "awaiting immutable physical packet"
                        if supported
                        else "outside direct 138 MHz/divider-1 synthesis range; no ARM/RF attempt"
                    ),
                    "attempts": [],
                    "assertions": {
                        "decoding_or_readability": None,
                        "frequency_spacing_and_timing": None,
                        "network_lifecycle": None,
                        "instrument_capture_validity": None,
                        "diagnostic_spectrum": None,
                    },
                }
            )
    return {
        "schema": MATRIX_SCHEMA,
        "plan_sha256": digest(plan),
        "phase_status": "OPEN",
        "rows": rows,
        "integration_cases": [],
        "accounting": {
            "attempted": 0,
            "accepted": 0,
            "rejected": 0,
            "aborted": 0,
            "uncertain": 0,
            "completed": 0,
            "charged_jobs": 0,
            "charged_planned_rf_seconds": 0,
        },
    }
