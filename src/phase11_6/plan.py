"""Deterministic Phase 11.6 packet plan; this module never accesses hardware."""

from __future__ import annotations

import copy
import hashlib
import json
from collections import OrderedDict


SCHEMA = "phase11.6-plan-v23"
MATRIX_SCHEMA = "phase11.6-matrix-v23"
SAMPLE_RATE_HZ = 138_000_000
DIRECT_MAXIMUM_HZ = 68_999_999
FIRMWARE_SOURCE = "7068b937240a7cbdfd0f0edbd7d347057604c0f0"
FIRMWARE_UF2_SHA256 = (
    "f1d437261cb7aa3f9668f7624dad5806346a248202a45f15c553617e12e74a47"
)
PICO_SERIAL = "0BF4B4AEC9FFB344"
PICO_DEVICE_ID = "fd6127d11d6aca42a9905fa3fb1bf1d5"
PICO_PHASE115_BOOT = "ff719d304f1ba4ac23fddd93561b26f0"
PICO_PREDECESSOR_BOOT = "1ab2d3ee391ec6c39fcd904f1c9dae01"
PICO_ACCEPTED_BOOT = "a12f61f7cd59557c1b5628b2568a52d5"
PREDECESSOR_PLAN_SHA256 = (
    "c3392251cac3f718655a8ae641ac164d185ce0d51dc3db7e86b4dea6e66bf601"
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


def realized_frequency_nhz(frequency_nhz: int) -> int:
    """Mirror the accepted 138 MHz NCO's exact integer quantization."""
    divisor = SAMPLE_RATE_HZ * NS
    increment = (frequency_nhz * (1 << 32) + divisor // 2) // divisor
    return (SAMPLE_RATE_HZ * increment * NS + (1 << 31)) >> 32


def strict_realized_job(job: dict) -> dict:
    """Preserve RF increments while minimizing a strict controller LOAD."""
    value = copy.deepcopy(job)
    for event in value["events"]:
        if event["rf_on"]:
            event["frequency_nhz"] = str(
                realized_frequency_nhz(int(event["frequency_nhz"]))
            )
    coalesced = []
    for event in value["events"]:
        if (coalesced
                and coalesced[-1]["rf_on"] == event["rf_on"]
                and coalesced[-1].get("frequency_nhz")
                    == event.get("frequency_nhz")
                and int(coalesced[-1]["offset_ns"])
                    + int(coalesced[-1]["duration_ns"])
                    == int(event["offset_ns"])):
            coalesced[-1]["duration_ns"] = str(
                int(coalesced[-1]["duration_ns"])
                + int(event["duration_ns"])
            )
        else:
            coalesced.append(copy.deepcopy(event))
    value["events"] = coalesced
    value["allow_frequency_adjustment"] = False
    return value


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
    if mode == "WSPR" and path == "controller_disconnect":
        # A raw WSPR adjustment reply repeats 162 mappings over USB after the
        # predecessor releases. Requesting the exact accepted NCO realizations
        # preserves every RF increment while returning an empty adjustment list.
        expected = strict_realized_job(expected)
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
            "WsprryPico": FIRMWARE_SOURCE,
            "WsprryPi": "c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf",
        },
        "amendment": {
            "predecessor_plan_sha256": PREDECESSOR_PLAN_SHA256,
            "scope": "post-sequence-164 TONE offline evidence recovery",
            "rf_job_payloads_changed": False,
            "rf_waveform_changed": False,
            "reason": (
                "sequences 155 and 156 completed their full WSPR emissions, but the "
                "browser raw LOAD for sequence 157 triggered a 33,335-byte transient "
                "allocation and watchdog recovery before LOAD acknowledgement or RF. "
                "Exact reconciliation preserved the failure, proved both boards "
                "inactive and released the reservation. BrowserApi::job now appends "
                "paged input directly into one pre-reserved envelope rather than "
                "constructing a second full-size temporary. The exact candidate was "
                "flashed once, then the shipped browser page completed the same raw "
                "LOAD under persistent Console and USB observation and was aborted "
                "113.99 seconds before launch. Zero allocator/TLS failures, 116,312 "
                "bytes of heap reserve, valid stack guards and authoritative inactive "
                "cleanup requalified the affected Phase 11.5 allocation/transport "
                "assertions. The first repeat then completed sequences 158 and 160, "
                "but sequence 159 stopped before browser mutation or RF because a "
                "five-second observer sleep crossed the two-second terminal polling "
                "window and left only 6.76 seconds of the unchanged eight-second ARM "
                "lead. The host-only repair caps that sleep at entry to the terminal "
                "window. The fresh 161-163 group proved that repair: exact predecessor "
                "authority arrived with 9.236 seconds of lead. The shipped browser then "
                "needed 6.798 seconds to complete HELLO/CLAIM/raw LOAD/ARM, so the accepted "
                "ARM retained only 2.439 seconds instead of the frozen eight seconds. The "
                "accepted job reached running before reconciliation aborted it. A WSPR "
                "frame leaves only 9.408 seconds between consecutive two-minute slots, "
                "and production WsprryPi preserves a 13.1-second preparation lead, so no "
                "ordering of the three required principals can satisfy the frozen gates. "
                "The WSPR row is retained failed and independent non-WSPR rows continue. "
                "RF job payloads, waveform, firmware, clock path, fixture, slot spacing, "
                "companion binary and acceptance thresholds did not change. Sequence "
                "164 then completed the 2200 m TONE controller-disconnect waveform, "
                "capture and browser overlap, but the host USB reducer rejected a "
                "safe retained predecessor whose authoritative terminal was aborted "
                "rather than complete. Offline recovery reconstructed every controller "
                "request from the retained wire hashes, matched network and independent "
                "USB terminal authority, revalidated the exact capture, and passed RF "
                "analysis without another transmission. The host-only reducer now "
                "accepts any inactive authoritative terminal outcome for earlier jobs "
                "while still requiring the current job to complete"
            ),
            "authorization_date": "2026-09-19",
            "deployment": (
                "one serial-bound Pico A repair flash; WsprryPi candidate unchanged"
            ),
            "configuration_writes": 0,
            "firmware_flashes": 1,
            "bootsel_transitions": 1,
            "controlled_reboots": 1,
            "failed_sequence_retried": False,
            "failed_sequences": [
                67, 88, 94, 97, 100, 102, 106, 109, 113, 116, 119, 125, 128,
                131, 134, 137, 143, 144, 146, 149, 152, 157, 159, 162, 164
            ],
            "zero_rf_preflight_failures": [
                91, 103, 104, 105, 122, 135, 140, 146, 159
            ],
            "zero_rf_aborted_submissions": [110, 117, 126, 132],
            "aborted_rf_sequences": [114, 120, 129, 138, 162],
            "abandoned_unsubmitted_sequences": [
                89, 90, 92, 93, 95, 96, 98, 99, 101, 107, 108, 111, 112, 115,
                118, 121, 123, 124, 127, 130, 133, 136, 139, 141, 142, 145,
                147, 148, 150, 151, 153, 154
            ],
            "completed_noncredit_sequences": [155, 156, 158, 160, 161, 163],
            "host_recovered_sequences": [164],
            "accepted_sequences": [164],
            "next_sequence": 165,
            "companion_source_revision":
                "c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf",
            "companion_binary_sha256":
                "b8e63947e2e9780f43dc4247869db138f81cc6e2245c99c1fd02ad9de4b33ff6",
            "production_ini": {
                "loop_tx": False,
                "tx_iterations": 1,
            },
            "terminal_evidence_repair": (
                "reduce the exact loaded, armed, running and complete events from "
                "the authenticated production WTP stream; retain any final host "
                "report as an additional consistency check"
            ),
            "usb_terminal_reducer_repair": {
                "sequence": 164,
                "failure": "Independent USB lifecycle/terminal authority",
                "cause": (
                    "the reducer required every retained predecessor terminal to be "
                    "complete even when an authoritative aborted, missed or failed "
                    "terminal was inactive and safely settled"
                ),
                "repair": (
                    "accept complete, aborted, missed or failed only for prior retained "
                    "jobs when output_active is false; retain exact complete and inactive "
                    "requirements for the current job"
                ),
                "retransmission": False,
                "rf_jobs_charged": 1,
                "rf_seconds_charged": 5.0,
                "runtime_job_id": "75ff8cebd469df39418a4ad42624eeeb",
                "capture_sha256":
                    "f6519744e998cbb2404f75ae594a9325ffb426b6ae69d3a22f46537344296d7b",
                "analysis_sha256":
                    "5d2f92b9b53a5b5e408849fa95b23ac1b8e6a2e9f97e6e8c6c9041851437bf91",
                "analysis_passed": True,
                "reservation_released": True,
            },
            "fixture_namespace_repair": {
                "required_namespaces": ["mount", "network"],
                "admission": (
                    "batch and physical group require their current namespace "
                    "identities to equal the supplied active fixture process"
                ),
                "admission_before_attempt_creation": True,
            },
            "fixture_continuity_repair": {
                "remote_ap": "reuse the active accepted AP attestation",
                "local_client": "fresh source and namespace root",
                "reason": (
                    "avoid another AP withdrawal while retaining immutable local "
                    "packet, namespace, capture, and observer evidence"
                ),
                "pico_mutations": 0,
            },
            "wspr_transition_repair": {
                "production_transport": "authenticated-network-wtp",
                "controller_transport": "usb-wtp",
                "browser_transport": "shipped-https-browser-page",
                "controller_disconnect": (
                    "close the USB WTP stream immediately after ARM without "
                    "disconnecting USB power"
                ),
                "production_cleanup_handoff": (
                    "after the exact inactive predecessor terminal, attempt the USB "
                    "successor CLAIM for at most two seconds while the releasing "
                    "owner settles; give the in-flight CLAIM the remaining deadline "
                    "rather than a fixed 0.5-second timeout, and retry only explicit "
                    "BUSY replies inside that envelope; companion c39fae3 accepts "
                    "that inactive successor after acknowledged RELEASE"
                ),
                "production_release_latency": (
                    "reuse the fresh exact terminal/inactive proof from successful "
                    "execution before RELEASE; monitor JOB_STATE without a continuous "
                    "STATUS transaction, pace long-job STATUS outside the final full "
                    "transaction allowance, retain a bounded post-completion fallback, "
                    "and require fresh post-RELEASE STATUS"
                ),
                "console_quiet_window": (
                    "suppress full Console INFO diagnostics from two seconds before "
                    "the predicted production terminal through successor ARM, then "
                    "resume at a fresh one-second cadence; authenticated WTP clock, "
                    "status, event, release, claim, load and ARM evidence remain active"
                ),
                "browser_predecessor_gate": (
                    "require the already-open page to overlap the exact controller "
                    "job while armed or running, then submit only after authenticated "
                    "USB terminal event plus current complete unowned inactive STATUS "
                    "and authenticated release authority"
                ),
                "disconnect_event_gap": (
                    "only the first event on the new authenticated post-disconnect "
                    "USB session may skip strictly increasing global event IDs; record "
                    "the exact missing range, require contiguous events thereafter, "
                    "and bridge lifecycle with accepted ARM plus current STATUS"
                ),
                "minimum_arm_lead_ns": "8000000000",
                "controller_clock_handoff": (
                    "project the immediately preceding synchronized device clock by "
                    "host monotonic elapsed time before CLAIM, after CLAIM, and "
                    "before ARM; omit redundant GET_CLOCK exchanges and require the "
                    "clock returned by ARM itself to retain the unchanged lead, "
                    "otherwise immediately ABORT and RELEASE"
                ),
                "controller_load_frequency_encoding": (
                    "exact 138 MHz NCO realized frequencies, strict admission, "
                    "identical increments to the nominal adjustment-allowed job; "
                    "adjacent identical tone cells are coalesced without changing "
                    "the RF waveform or total duration"
                ),
                "failed_group_reconciliation": (
                    "first reuse the exact retained USB principal when it remains "
                    "admissible; when an active disconnected session blocks WTP, "
                    "bind the exact job through authenticated browser status and "
                    "the boot/source/active state through physical Console INFO "
                    "before exactly one Console ABORT; validate the identity-free "
                    "Console acknowledgement against boot and inactive aborted "
                    "state, then prove the exact job terminal through fresh WTP "
                    "status"
                ),
                "production_browser_terminal": (
                    "bind the wildcard production observer to the first active job, "
                    "latch its exact retained complete inactive terminal, stop page "
                    "refreshes while successors run, and verify the observed id "
                    "against the authenticated production runtime binding"
                ),
                "production_browser_handoff": (
                    "pre-open the raw-browser successor while idle; after controller "
                    "ARM and USB disconnect, authorize that existing page only after "
                    "the wildcard production page exits by reducing its exact retained "
                    "terminal; the successor page must itself overlap the controller, "
                    "quiesce refreshes before predicted completion, and consume fresh "
                    "USB event-plus-STATUS terminal authority before submitting the "
                    "third slot"
                ),
                "browser_connection_budget": (
                    "pre-open exactly the production observer and raw-browser successor "
                    "while the target is idle; retain the successor page with bounded "
                    "standby refreshes because active RF pauses new network admission; "
                    "fail before RF if either browser exits"
                ),
                "terminal_poll_schedule": (
                    "cap each long observer wait at the entrance to the two-second "
                    "terminal polling window; the sequence-159 failure slept five "
                    "seconds from 2.496 seconds before completion and crossed the "
                    "frozen eight-second browser ARM-lead gate, while the repaired "
                    "calculation waits 0.496 seconds for that same observation"
                ),
                "retained_timing_gate": {
                    "repeat_group_sequences": [161, 162, 163],
                    "predecessor_authority_lead_ns": "9236268079",
                    "browser_mutation_to_arm_ns": "6797680079",
                    "accepted_arm_lead_ns": "2438588000",
                    "required_arm_lead_ns": "8000000000",
                    "consecutive_slot_gap_ns": "9408000108",
                    "production_preparation_lead_ns": "13100000000",
                    "browser_runtime_job_id":
                        "a4c3cae0c122fc55152f3a8d14c7d265",
                    "browser_terminal_state": "aborted",
                    "threshold_changed": False,
                    "disposition": (
                        "retain 2200m WSPR failed without another retry; the same "
                        "duration and control-path constraints block the remaining "
                        "WSPR primary rows on this exact configuration"
                    ),
                },
            },
            "browser_allocation_repair": {
                "failure_attempts": [155, 156, 157],
                "failed_sequence": 157,
                "failure_boot_id": "1ab2d3ee391ec6c39fcd904f1c9dae01",
                "fault_stage": 14,
                "fault_hash": 3833354787,
                "failed_allocation_request_bytes": 33335,
                "repair": (
                    "append paged HTTP InputView spans directly into one "
                    "pre-reserved WTP envelope"
                ),
                "deployment_packet_sha256":
                    "0609b44177e8e9e0c3c9673abbc0525fb023f0b84e7e0e729b352c5878439be1",
                "requalification_packet_sha256":
                    "60418607933b01ad4989c4d6a8643d42939ef202ca5ab555f9f3055e4ff61932",
                "requalification": {
                    "rf_jobs": 0,
                    "arms": 1,
                    "aborts": 1,
                    "allocator_largest_successful_request_bytes": 16718,
                    "allocator_failures": 0,
                    "tls_allocation_failures": 0,
                    "heap_reserve_bytes": 116312,
                    "console_samples": 41,
                    "usb_samples": 9,
                    "accepted_arm_lead_ns": 113986909000,
                    "terminal_state": "aborted",
                    "final_state": "empty",
                    "reservation_released": True,
                },
                "first_repeat_group_sequences": [158, 159, 160],
                "first_repeat_result": (
                    "production and controller-disconnect completed noncredit; browser "
                    "stopped before mutation or RF on the terminal-poll harness defect"
                ),
                "repeat_affected_row_from_sequence": 161,
                "second_repeat_group_sequences": [161, 162, 163],
                "second_repeat_result": (
                    "terminal polling repair passed, production and controller-disconnect "
                    "completed noncredit, and browser raw ARM was accepted 2.439 seconds "
                    "before launch then aborted after RF began; frozen eight-second gate "
                    "retained and no further WSPR retry justified"
                ),
                "automatic_retry": False,
            },
        },
        "accepted_configuration": {
            "pico_serial": PICO_SERIAL,
            "device_id": PICO_DEVICE_ID,
            "phase11_5_accepted_boot_id": PICO_PHASE115_BOOT,
            "accepted_boot_id": PICO_ACCEPTED_BOOT,
            "source_revision": FIRMWARE_SOURCE,
            "uf2_sha256": FIRMWARE_UF2_SHA256,
            "board": "Pico 2 W / RP2350 Arm Secure",
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
                    "phase11-6-repair-7068b93-deployment-20260919",
            },
            "failure_transition": {
                "from_boot_id": "e363bf9ae4528258563557b7d306efcd",
                "to_recovery_boot_id": PICO_PREDECESSOR_BOOT,
                "cause": "browser raw LOAD allocation failure before RF",
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
            "companion_runtime_changes": 1,
            "decision": (
                "retain the exact browser-envelope allocation repair and accepted "
                "firmware after zero-RF target requalification; retain the host "
                "terminal-poll and USB terminal-reducer repairs, preserve attempts "
                "155-164, keep the failed WSPR timing gate and unchanged thresholds, "
                "accept the recovered TONE evidence without retransmission, and "
                "continue independent modes"
            ),
            "companion_decision": (
                "import finite managed WSPR fields, consume the iteration and require "
                "orderly production exit; use event-driven execution monitoring with "
                "paced and post-completion STATUS fallbacks"
            ),
            "phase11_5_applicability": (
                "affected image identity, browser raw LOAD, allocation reserve, "
                "Console/USB contention, stack/fault and inactive-cleanup gates passed "
                "on the repaired exact candidate; RF synthesis evidence remains bound "
                "to its recorded image until the affected 11.6 row is repeated"
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
