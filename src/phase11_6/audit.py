"""Independent fail-closed auditor for immutable Phase 11.6 packet evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from phase11_6.plan import (
    FIRMWARE_SOURCE,
    FIRMWARE_UF2_SHA256,
    PICO_DEVICE_ID,
    RECEIVER_SERIAL,
    digest,
    validate,
)


SCHEMA = "phase11.6-packet-evidence-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _expected_job_digest(job: dict) -> str:
    return hashlib.sha256(
        json.dumps(job["expected_job"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def audit_document(document: dict, plan: dict) -> dict:
    plan = validate(plan)
    require(document.get("schema") == SCHEMA, "packet evidence schema")
    require(document.get("plan_sha256") == digest(plan), "plan digest")
    packets = [packet for packet in plan["packets"]
               if packet["packet_id"] == document.get("packet_id")]
    require(len(packets) == 1, "packet identity")
    packet = packets[0]
    identity = document.get("identity", {})
    accepted = plan["accepted_configuration"]
    require(
        identity.get("device_id") == PICO_DEVICE_ID
        and identity.get("source_revision") == FIRMWARE_SOURCE
        and identity.get("uf2_sha256") == FIRMWARE_UF2_SHA256
        and identity.get("boot_id") == accepted["accepted_boot_id"]
        and identity.get("system_clock_hz") == accepted["system_clock_hz"]
        and identity.get("pio_divider") == accepted["pio_divider"]
        and identity.get("engine") == accepted["engine"]
        and identity.get("renderer") == accepted["renderer"],
        "accepted device/image/configuration identity",
    )
    receiver = document.get("receiver", {})
    require(
        receiver.get("driver") == "sdrplay"
        and receiver.get("serial") == RECEIVER_SERIAL
        and receiver.get("sample_rate_hz") == 250_000
        and receiver.get("bandwidth_hz") == 200_000
        and receiver.get("gain_db") == 20
        and receiver.get("agc") is False
        and receiver.get("bias_tee") is False
        and receiver.get("correction_ppm") == 0,
        "receiver identity and frozen settings",
    )
    require(document.get("tolerances") == plan["tolerances"], "frozen tolerances")
    expected_jobs = {job["id"]: job for job in packet["jobs"]}
    jobs = document.get("jobs")
    require(
        isinstance(jobs, list)
        and len(jobs) == len(expected_jobs)
        and {job.get("id") for job in jobs} == set(expected_jobs),
        "complete packet job set",
    )
    capture_hashes: set[str] = set()
    completed = aborted = rejected = uncertain = attempted = 0
    charged_ns = 0
    for observed in jobs:
        expected = expected_jobs[observed["id"]]
        attempted += 1
        require(
            observed.get("band") == expected["band"]
            and observed.get("mode") == expected["mode"]
            and observed.get("submission_path") == expected["submission_path"]
            and observed.get("planned_duration_ns") == expected["planned_duration_ns"]
            and observed.get("expected_job_sha256") == _expected_job_digest(expected),
            "job band/mode/path/content binding",
        )
        charged_ns += expected["planned_duration_ns"]
        disposition = observed.get("disposition")
        require(disposition in {"PASS", "FAIL", "ABORTED", "REJECTED", "UNCERTAIN"},
                "job disposition")
        completed += disposition in {"PASS", "FAIL"}
        aborted += disposition == "ABORTED"
        rejected += disposition == "REJECTED"
        uncertain += disposition == "UNCERTAIN"
        if disposition != "REJECTED":
            capture = observed.get("capture", {})
            capture_hash = capture.get("sha256")
            require(
                isinstance(capture_hash, str)
                and len(capture_hash) == 64
                and capture_hash not in capture_hashes
                and capture.get("complete") is True
                and capture.get("metadata_complete") is True
                and capture.get("overflow_count") == 0
                and capture.get("clipping_samples") == 0
                and capture.get("sample_count", 0) > 0
                and capture.get("leading_quiet_s", 0)
                >= plan["tolerances"]["minimum_leading_quiet_s"]
                and capture.get("trailing_quiet_s", 0)
                >= plan["tolerances"]["minimum_trailing_quiet_s"],
                "unique complete capture and quiet",
            )
            capture_hashes.add(capture_hash)
        lifecycle = observed.get("lifecycle", {})
        require(
            lifecycle.get("boot_id") == accepted["accepted_boot_id"]
            and lifecycle.get("terminal_output_active") is False
            and lifecycle.get("authoritative_terminal") is True
            and lifecycle.get("reservation_held") is True
            and lifecycle.get("schedules_disabled_a") is True
            and lifecycle.get("schedules_disabled_b") is True
            and lifecycle.get("browser_page_loaded") is True
            and lifecycle.get("browser_manual_refresh_overlap") is True,
            "authority, browser overlap and schedule exclusion",
        )
        if expected["controller_disconnect_after_arm"]:
            require(
                lifecycle.get("controller_disconnected_after_arm") is True
                and lifecycle.get("usb_power_continuous") is True
                and lifecycle.get("reconciled_without_duplicate_submission") is True,
                "controller disconnect completion",
            )
        if expected["submission_path"] == "production":
            require(lifecycle.get("production_wsprrypi") is True
                    and lifecycle.get("hostname_authenticated_tls") is True,
                    "production WsprryPi path")
        if expected["submission_path"].startswith("browser"):
            require(lifecycle.get("browser_owned_submission") is True
                    and lifecycle.get("hostname_authenticated_tls") is True,
                    "browser-owned submission")
        if disposition == "PASS":
            analysis = observed.get("analysis", {})
            require(
                analysis.get("passed") is True
                and analysis.get("wrong_message_rejected") is True
                and analysis.get("wrong_band_rejected") is True
                and analysis.get("truncation_rejected") is True
                and analysis.get("extra_burst_rejected") is True,
                "independent analysis and negative controls",
            )
            mode = expected["mode"]
            if mode == "WSPR":
                require(
                    analysis.get("decoded_identity") == ["AA0NT", "EM18", "20"]
                    and analysis.get("complete_frame_before_padding") is True
                    and analysis.get("tone_spacing_passed") is True
                    and analysis.get("symbol_progression_passed") is True,
                    "WSPR frame/decode assertions",
                )
            elif mode in {"QRSS", "FSKCW", "DFCW"}:
                require(
                    analysis.get("message") == plan["content"]["message"]
                    or expected["purpose"] == "32-character-word-space-semantics",
                    "keyed message",
                )
                polarity = (
                    plan["content"]["dfcw_polarity"] if mode == "DFCW" else
                    plan["content"]["fskcw_polarity"] if mode == "FSKCW" else
                    "single-frequency marks; silent commanded gaps"
                )
                require(
                    analysis.get("expected_event_sha256") == _expected_job_digest(expected)
                    and analysis.get("envelope_timing_passed") is True
                    and analysis.get("no_missing_or_extra_elements") is True
                    and analysis.get("polarity") == polarity,
                    "keyed timing/content/polarity",
                )
            else:
                require(analysis.get("one_uninterrupted_interval") is True
                        and analysis.get("no_residual_or_extra_burst") is True,
                        "Tone interval and quiet")
        resources = observed.get("resources", {})
        require(
            resources.get("heap_reserve_bytes", 0) >= 32_768
            and resources.get("stack_guards_valid") is True
            and resources.get("faults") == 0
            and resources.get("dma_errors") == 0
            and resources.get("refill_irq_unpaired") == 0
            and resources.get("refill_invalid_reserves") == 0,
            "retained Phase 11.5 health gates",
        )
    accounting = document.get("accounting", {})
    require(
        accounting == {
            "attempted": attempted,
            "completed": completed,
            "aborted": aborted,
            "rejected": rejected,
            "uncertain": uncertain,
            "charged_jobs": attempted - rejected,
            "charged_planned_rf_seconds": charged_ns / 1e9,
        },
        "packet accounting",
    )
    final = document.get("final", {})
    require(
        final.get("a_output_active") is False
        and final.get("a_owner_id") is None
        and final.get("b_output_active") is False
        and final.get("b_owner_id") is None
        and final.get("a_schedules_disabled") is True
        and final.get("b_schedules_disabled") is True
        and final.get("reservation_released_after_authoritative_inactive") is True
        and final.get("wspr4_restored") is True
        and final.get("wspr5_restored") is True
        and final.get("installed_service_active") is True,
        "final authority, reservation and host restoration",
    )
    return {"valid": True, "packet_id": packet["packet_id"], "jobs": len(jobs),
            "passed": sum(job["disposition"] == "PASS" for job in jobs),
            "charged_planned_rf_seconds": charged_ns / 1e9}


def audit_directory(root: Path) -> dict:
    root = root.resolve(strict=True)
    require(not root.is_symlink(), "evidence root symlink")
    index = json.loads((root / "evidence-index.json").read_text())
    actual = {str(path.relative_to(root)) for path in root.rglob("*")
              if path.is_file() and path.name != "evidence-index.json"}
    require(index.get("schema") == "phase11.6-evidence-index-v1"
            and set(index.get("files", {})) == actual, "evidence inventory")
    for name, expected in index["files"].items():
        path = root / name
        require(not path.is_symlink() and path.resolve().is_relative_to(root)
                and hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                "evidence file hash/containment")
    return audit_document(json.loads((root / "packet-evidence.json").read_text()),
                          json.loads((root / "plan.json").read_text()))
