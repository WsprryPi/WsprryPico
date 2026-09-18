"""Fail-closed offline recovery for a completed Phase 11.6 production run.

Recovery is intentionally narrower than normal execution.  It accepts only the
known post-capture validator-import failure and reconstructs the result from
immutable raw evidence.  It never opens the network, USB device, SDR, or RF
path.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

from phase11_5_inventory import require
from phase11_5_package9 import resource_gate
from phase11_6.live import (
    CAPTURE_BANDWIDTH,
    CAPTURE_GAIN,
    CAPTURE_RATE,
    PEER_SHA256,
    RECEIVER_SERIAL,
    _tls_messages,
    save,
    sha256,
)
from phase11_6.plan import FIRMWARE_SOURCE, PICO_ACCEPTED_BOOT, digest


def _configure_capture_validator(source: Path) -> dict:
    """Bind the exact external validator while remaining old-run compatible."""
    source = source.resolve(strict=True)
    package = source / "wsprrypi_qualification"
    files = {
        "capture_metadata.py": package / "capture_metadata.py",
        "capture-metadata.schema.json":
            package / "schemas" / "capture-metadata.schema.json",
    }
    require(source.is_dir() and all(path.is_file() for path in files.values()),
            "Qualification Harness capture validator source")
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from wsprrypi_qualification.capture_metadata import load_capture_metadata
    require(callable(load_capture_metadata), "Qualification Harness validator import")
    return {name: sha256(path) for name, path in files.items()}


def _json(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), f"Regular evidence file: {path}")
    return json.loads(path.read_text())


def _jsonl(path: Path) -> list[dict]:
    require(path.is_file() and not path.is_symlink(), f"Regular evidence journal: {path}")
    raw = path.read_bytes()
    require(raw and raw.endswith(b"\n"), f"Complete evidence journal: {path}")
    rows = [json.loads(line) for line in raw.splitlines()]
    require([row.get("sequence") for row in rows] == list(range(len(rows))),
            f"Contiguous evidence journal: {path}")
    return rows


def _one(rows: list[dict], kind: str) -> dict:
    values = [row for row in rows if row.get("kind") == kind]
    require(len(values) == 1, f"Exactly one {kind} record")
    return values[0]


def _terminal(status: dict, job_id: str) -> dict:
    records = [record for record in status.get("terminal_records", [])
               if record.get("job_id") == job_id]
    require(len(records) == 1 and records[0].get("state") == "complete"
            and records[0].get("output_active") is False,
            "Matching authoritative complete terminal record")
    return records[0]


def _usb_completion(status_states: set[str], event_states: set[str],
                    status_jobs: set[str], event_jobs: set[str],
                    latest: dict, job_id: str) -> dict:
    """Historical-run-compatible copy of the repaired lifecycle reduction."""
    require(latest.get("boot_id") == PICO_ACCEPTED_BOOT,
            "Independent USB final boot identity")
    terminals = [record for record in latest.get("terminal_records", [])
                 if record.get("job_id") == job_id]
    prior_status_jobs = status_jobs - {job_id}
    prior_terminals = {record.get("job_id") for record in latest.get("terminal_records", [])
                       if record.get("job_id") in prior_status_jobs
                       and record.get("state") == "complete"
                       and record.get("output_active") is False}
    require({"loaded", "armed", "running", "complete"}.issubset(
                status_states | event_states)
            and event_jobs == {job_id}
            and job_id in status_jobs | event_jobs
            and prior_terminals == prior_status_jobs
            and latest.get("output_active") is False
            and latest.get("owner_id") is None
            and len(terminals) == 1
            and terminals[0].get("state") == "complete"
            and terminals[0].get("output_active") is False,
            "Independent USB lifecycle/terminal authority")
    return {"status_states": sorted(status_states),
            "event_states": sorted(event_states),
            "terminal": terminals[0], "final": latest}


def _capture(attempt_root: Path, job: dict, start: dict,
             helper: Path, qualification_source: Path,
             capture_lead_and_tail_s: float = 40.0) -> tuple[dict, dict]:
    validator = _configure_capture_validator(qualification_source)
    require(sha256(helper) == start["capture_helper_sha256"],
            "Capture helper identity")
    capture = attempt_root / "job/capture"
    iq = capture / "capture.cf32"
    metadata_path = capture / "capture.json"
    request_path = capture / "capture-request.json"
    require(iq.is_file() and not iq.is_symlink(), "Regular retained IQ file")
    from wsprrypi_qualification.capture_metadata import load_capture_metadata

    load_capture_metadata(metadata_path)
    metadata = _json(metadata_path)
    request = _json(request_path)
    duration_s = job["planned_duration_ns"] / 1e9
    capture_seconds = duration_s + capture_lead_and_tail_s
    expected_samples = round(capture_seconds * CAPTURE_RATE)
    expected_settings = {
        "format": "CF32",
        "sample_rate_hz": CAPTURE_RATE,
        "bandwidth_hz": CAPTURE_BANDWIDTH,
        "center_frequency_hz": job["nominal_frequency_hz"] - 25_000,
        "gain_db": CAPTURE_GAIN,
        "channel": 0,
        "agc": False,
        "bias_tee": False,
    }
    iq_hash = sha256(iq)
    argv = request.get("argv", [])
    require(
        metadata.get("evidence_type") == "capture_success"
        and metadata.get("primary_outcome") == "success"
        and metadata.get("process_exit_code") == 0
        and metadata.get("actual_settings") == expected_settings
        and metadata.get("resolved_device")
        == {"driver": "sdrplay", "serial": RECEIVER_SERIAL}
        and metadata.get("requested_sample_count") == expected_samples
        and metadata.get("retained_sample_count") == expected_samples
        and iq.stat().st_size == expected_samples * 8
        and metadata.get("overflow_count") == 0
        and metadata.get("clipping", {}).get("sample_count") == 0
        and metadata.get("first_read", {}).get("discarded") is True
        and metadata.get("output", {}).get("complete") is True
        and metadata.get("output", {}).get("sha256") == iq_hash
        and metadata.get("cleanup", {}).get("outcome") == "verified"
        and len(argv) >= 2 and Path(argv[0]).resolve() == helper.resolve()
        and Path(argv[-3]).resolve() == iq.resolve()
        and Path(argv[-2]).resolve() == metadata_path.resolve(),
        "Retained receiver identity/settings/integrity",
    )
    value = {
        "metadata_sha256": sha256(metadata_path),
        "capture_sha256": iq_hash,
        "sample_count": expected_samples,
        "bytes": iq.stat().st_size,
        "actual_settings": expected_settings,
        "resolved_device": metadata["resolved_device"],
        "overflow_count": 0,
        "clipping_samples": 0,
    }
    return value, validator


def _browser(attempt_root: Path, job_id: str) -> dict:
    directory = attempt_root / "job/browser"
    rows = _jsonl(directory / "browser.jsonl")
    require(_one(rows, "start")["value"]["job_id"] == "any",
            "Production browser watch")
    version = _one(rows, "version")["value"]
    require(str(version.get("product", "")).startswith("Chrome/"),
            "Actual Chrome page lifecycle")
    refreshes = [row for row in rows if row.get("kind") == "manual_refresh"]
    require(len(refreshes) >= 3, "Repeated manual browser refreshes")
    states = [row["value"]["state"] for row in refreshes]
    require(all(value.get("boot_id") == PICO_ACCEPTED_BOOT for value in states),
            "Browser accepted boot identity")
    armed = [value for value in states
             if value.get("job_id") == job_id and value.get("state") == "armed"
             and value.get("output_active") is False]
    running = [value for value in states
               if value.get("job_id") == job_id and value.get("state") == "running"
               and value.get("output_active") is True]
    completed = [value for value in states
                 if value.get("state") == "empty"
                 and value.get("output_active") is False
                 and value.get("owner_id") is None
                 and any(record.get("job_id") == job_id
                         and record.get("state") == "complete"
                         and record.get("output_active") is False
                         for record in value.get("terminal_records", []))]
    require(armed and running and completed, "Browser armed/running/terminal overlap")
    screenshots = {}
    for name in ("initial.png", "overlap-armed.png", "overlap-running.png"):
        path = directory / name
        require(path.is_file() and not path.is_symlink() and path.stat().st_size > 0,
                f"Browser screenshot: {name}")
        screenshots[name] = sha256(path)
    return {
        "status": "PASS",
        "page_loaded": True,
        "manual_refresh_overlap": True,
        "observed_job_id": job_id,
        "job_ids": [job_id],
        "refreshes": len(refreshes),
        "chrome": version,
        "journal_sha256": sha256(directory / "browser.jsonl"),
        "screenshots": screenshots,
    }


def _production(root: Path, attempt_root: Path, job: dict, attempt: dict,
                rows: list[dict], binary: Path) -> tuple[dict, dict, dict]:
    start = _one(rows, "start")["value"]
    binding = _one(rows, "production_binding")["value"]
    production_start = _one(rows, "production_start")["value"]
    require(sha256(binary) == start["production_binary_sha256"]
            == production_start["binary_sha256"], "Production binary identity")
    expected = copy.deepcopy(attempt["effective_job"])
    expected["job_id"] = binding["job_id"]
    written, received, wire = _tls_messages(
        root, attempt_root / "job/production-tls.bin"
    )
    requests = [value for value in written if value.get("type") == "request"]
    require(requests and len({value.get("request_id") for value in requests}) == len(requests)
            and len({value.get("session_id") for value in requests}) == 1,
            "Production request identity")
    mutations = [value for value in requests
                 if value.get("op") in {"CLAIM", "LOAD", "ARM", "ABORT", "RELEASE"}]
    require([value.get("op") for value in mutations]
            == ["CLAIM", "LOAD", "ARM", "RELEASE"],
            "Production mutation order/count")
    load, arm = mutations[1], mutations[2]
    require(load.get("body") == expected
            and arm.get("body", {}).get("job_id") == binding["job_id"]
            and int(arm.get("body", {}).get("start_utc_ns", "0"))
            == binding["start_utc_ns"],
            "Actual production LOAD/ARM differs from frozen job")
    for request in requests:
        matches = [value for value in received
                   if value.get("type") == "response"
                   and value.get("request_id") == request.get("request_id")
                   and value.get("session_id") == request.get("session_id")
                   and value.get("op") == request.get("op")]
        require(len(matches) == 1 and matches[0].get("ok") is True,
                "Production request response")
    log_path = attempt_root / "job/production.log"
    log = log_path.read_text()
    require("[INFO ] Completed transmission." in log
            and "[INFO ] WsprryPi exiting." in log
            and "[INFO ] Transmit backend: wtp" in log
            and "[INFO ] - Dot Freq: 137.505 kHz" in log
            and "[INFO ] - Dash Freq: 137.500 kHz" in log,
            "Production completion and explicit reverse-DFCW invocation")
    return binding, wire, {
        "actual_load": load["body"],
        "mutations": [value["op"] for value in mutations],
        "production_log_sha256": sha256(log_path),
    }


def recover(root: Path, plan: dict, job: dict, attempt: dict,
            attempt_packet_path: Path, attempt_root: Path,
            reconciliation_path: Path, helper: Path,
            qualification_source: Path, binary: Path, output: Path) -> dict:
    """Recover exactly one completed run from retained evidence."""
    attempt_root = attempt_root.resolve(strict=True)
    require(not attempt_root.is_symlink(), "Attempt root containment")
    require(not (attempt_root / "run-result.json").exists()
            and not (attempt_root / "job/result.json").exists(),
            "Recovery is only for an incomplete host result")
    rows = _jsonl(attempt_root / "execution.jsonl")
    failure = _one(rows, "failure")
    require(failure["value"] == {
        "type": "ModuleNotFoundError",
        "message": "No module named 'wsprrypi_qualification'",
    } and rows[-2] is failure and rows[-1].get("kind") == "reservation_left_held",
            "Exact recoverable post-capture failure")
    require(not any(row.get("kind") in {"capture_complete", "browser_complete", "finish"}
                    for row in rows), "No partially accepted result markers")
    start = _one(rows, "start")["value"]
    attempt_file_hash = sha256(attempt_packet_path)
    attempt_hash = hashlib.sha256(
        json.dumps(attempt, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    require(start.get("plan_sha256") == digest(plan)
            and start.get("job_id") == job["id"]
            and start.get("attempt_packet_sha256") == attempt_hash
            and start.get("attempt_packet_file_sha256") == attempt_file_hash,
            "Execution journal plan/attempt binding")
    acquired = _one(rows, "reservation_acquired")["value"]
    require(acquired.get("state") == "HELD"
            and acquired.get("packet_sha256") == attempt_hash
            and acquired.get("boards", {}).get("a", {}).get("state") == "empty"
            and acquired.get("boards", {}).get("b", {}).get("state") == "empty",
            "Dual-device reservation acquisition")

    binding, wire, production = _production(
        root, attempt_root, job, attempt, rows, binary
    )
    capture, validator = _capture(
        attempt_root, job, start, helper, qualification_source
    )
    browser = _browser(attempt_root, binding["job_id"])

    console = [row["value"]["value"] for row in rows
               if row.get("kind") == "console_info"]
    require(console, "Independent console observations")
    for value in console:
        resource_gate(value, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
    usb_status = [row["value"]["value"] for row in rows
                  if row.get("kind") == "usb_status"]
    usb_events = [row["value"]["value"] for row in rows
                  if row.get("kind") == "usb_event"]
    status_states = {value.get("state") for value in usb_status
                     if value.get("job_id") == binding["job_id"]}
    event_states = {value.get("body", {}).get("state") for value in usb_events
                    if value.get("event") == "JOB_STATE"
                    and value.get("body", {}).get("job_id") == binding["job_id"]}
    final_usb = usb_status[-1]
    terminal = _terminal(final_usb, binding["job_id"])
    require(all(value.get("boot_id") == PICO_ACCEPTED_BOOT for value in usb_status)
            and all(value.get("boot_id") == PICO_ACCEPTED_BOOT for value in usb_events)
            and {"armed", "running", "complete"}.issubset(status_states)
            and {"loaded", "armed", "running", "complete"}.issubset(event_states)
            and final_usb.get("state") == "empty"
            and final_usb.get("output_active") is False
            and final_usb.get("owner_id") is None,
            "Independent USB lifecycle and final authority")

    reconciliation = _json(reconciliation_path)
    before = reconciliation.get("before", {})
    after = reconciliation.get("after", {})
    reservation = reconciliation.get("reservation", {})
    require(reconciliation.get("status") == "RECONCILED"
            and before == after
            and after.get("state") == "empty"
            and after.get("output_active") is False
            and after.get("owner_id") is None
            and _terminal(after, binding["job_id"]) == terminal
            and reservation.get("state") == "RELEASED"
            and reservation.get("packet_sha256") == attempt_hash
            and reservation.get("boards", {}).get("a", {}).get("state") == "empty"
            and reservation.get("boards", {}).get("b", {}).get("state") == "empty",
            "Authoritative reconciliation and reservation release")

    result = {
        "schema": "phase11.6-job-result-v1",
        "plan_sha256": digest(plan),
        "job_id": job["id"],
        "wtp_job_id": binding["job_id"],
        "band": job["band"],
        "mode": job["mode"],
        "submission_path": "production",
        "planned_duration_ns": job["planned_duration_ns"],
        "target_utc_ns": binding["start_utc_ns"],
        "binding": binding,
        "production_binary_sha256": sha256(binary),
        "production_returncode": 0,
        "tls_wire": wire,
        "tls_mutations": production["mutations"],
        "actual_load": production["actual_load"],
        "terminal_records": [terminal],
        "released_status": after,
        "observer": {
            "console_samples": len(console),
            "usb_status_samples": len(usb_status),
            "usb_states": sorted(status_states),
            "usb_event_states": sorted(event_states),
            "console_final": console[-1],
            "usb_final": final_usb,
        },
        "capture": capture,
        "browser": browser,
        "recovery": {
            "kind": "offline-auditor-only",
            "original_failure": failure["value"],
            "no_network_usb_sdr_or_rf_access": True,
            "capture_validator_sha256": validator,
            "source_sha256": {
                "attempt_packet": attempt_file_hash,
                "execution_journal": sha256(attempt_root / "execution.jsonl"),
                "reconciliation": sha256(reconciliation_path),
                "production_tls": sha256(attempt_root / "job/production-tls.bin"),
                "production_log": production["production_log_sha256"],
                "browser_journal": browser["journal_sha256"],
                "capture_metadata": capture["metadata_sha256"],
                "capture_iq": capture["capture_sha256"],
            },
        },
        "disposition": "CAPTURED_REQUIRES_ANALYSIS",
    }
    output.mkdir(mode=0o700)
    require(not output.is_symlink() and not any(output.iterdir()),
            "Fresh private recovery output")
    save(output / "recovered-result.json", result)
    return result


def recover_browser(root: Path, plan: dict, job: dict, attempt: dict,
                    attempt_packet_path: Path, attempt_root: Path,
                    reconciliation_path: Path, helper: Path,
                    qualification_source: Path, output: Path) -> dict:
    """Recover the known post-capture USB reducer failure without hardware."""
    attempt_root = attempt_root.resolve(strict=True)
    require(not attempt_root.is_symlink(), "Attempt root containment")
    require(not (attempt_root / "run-result.json").exists()
            and not (attempt_root / "job/result.json").exists(),
            "Recovery is only for an incomplete host result")
    rows = _jsonl(attempt_root / "execution.jsonl")
    failure = _one(rows, "failure")
    require(failure["value"] == {
        "type": "ValueError", "message": "Browser independent USB lifecycle",
    } and rows[-2] is failure and rows[-1].get("kind") == "reservation_left_held",
            "Exact recoverable post-capture USB reducer failure")
    require(not any(row.get("kind") == "finish" for row in rows),
            "No partially accepted result marker")
    start = _one(rows, "start")["value"]
    attempt_file_hash = sha256(attempt_packet_path)
    attempt_hash = hashlib.sha256(
        json.dumps(attempt, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    job_id = attempt["effective_job"]["job_id"]
    require(start.get("plan_sha256") == digest(plan)
            and start.get("job_id") == job["id"]
            and start.get("wtp_job_id") == job_id
            and start.get("attempt_packet_sha256") == attempt_hash
            and start.get("attempt_packet_file_sha256") == attempt_file_hash,
            "Execution journal plan/attempt binding")
    acquired = _one(rows, "reservation_acquired")["value"]
    require(acquired.get("state") == "HELD"
            and acquired.get("packet_sha256") == attempt_hash
            and acquired.get("boards", {}).get("a", {}).get("state")
                in {"empty", "complete"}
            and acquired.get("boards", {}).get("b", {}).get("state") == "empty",
            "Dual-device reservation acquisition")

    capture, validator = _capture(
        attempt_root, job, start, helper, qualification_source, 18.0
    )
    require(start.get("capture_validator_sha256") == validator,
            "Execution-bound capture validator identity")
    capture_marker = _one(rows, "capture_complete")["value"]
    require(capture_marker == capture, "Capture completion marker")

    browser = _one(rows, "browser_submit_complete")["value"]
    browser_path = attempt_root / "job/browser/browser-result.json"
    require(browser == _json(browser_path), "Browser result marker/file identity")
    expected_operation = ("LOAD" if job["submission_path"] == "browser_raw"
                          else "LOAD_MESSAGE")
    base_operations = ["HELLO", "CLAIM", expected_operation, "ARM"]
    release_required = browser.get("release_required")
    expected_operations = base_operations + (["RELEASE"] if release_required else [])
    terminal = browser.get("terminal") or {}
    final = browser.get("final") or {}
    requests = browser.get("requests") or []
    require(browser.get("status") == "PASS"
            and browser.get("page_loaded") is True
            and browser.get("manual_refresh_overlap") is True
            and browser.get("peer_sha256") == PEER_SHA256
            and isinstance(release_required, bool)
            and browser.get("operations") == expected_operations
            and [request.get("operation") for request in requests] == expected_operations
            and len({request.get("request_id") for request in requests}) == len(requests)
            and len({request.get("session_id") for request in requests}) == 1
            and len(browser.get("responses") or []) == len(requests)
            and all(response.get("status") == 200
                    for response in browser.get("responses", []))
            and terminal.get("job_id") == job_id
            and terminal.get("state") == "complete"
            and terminal.get("output_active") is False
            and final.get("job_id") == job_id
            and final.get("output_active") is False
            and final.get("owner_id") is None,
            "Actual browser-owned submission lifecycle")
    submitted = requests[2]
    armed = requests[3]
    require(submitted.get("body") == attempt["effective_compact_request"]
            and armed.get("body", {}).get("job_id") == job_id
            and str(armed.get("body", {}).get("start_utc_ns", "")).isdigit(),
            "Exact browser LOAD_MESSAGE/ARM binding")
    browser_journal = _jsonl(attempt_root / "job/browser/browser.jsonl")
    refreshes = [row["value"]["state"] for row in browser_journal
                 if row.get("kind") == "manual_refresh"]
    require(any(value.get("job_id") == job_id and value.get("state") == "running"
                and value.get("output_active") is True for value in refreshes)
            and any(value.get("job_id") == job_id and value.get("state") == "complete"
                    and value.get("output_active") is False for value in refreshes),
            "Browser manual refresh RF/terminal overlap")

    console = [row["value"]["value"] for row in rows
               if row.get("kind") == "console_info"]
    require(console, "Independent console observations")
    for value in console:
        resource_gate(value, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
    usb_status = [row["value"]["value"] for row in rows
                  if row.get("kind") == "usb_status"]
    usb_events = [row["value"]["value"] for row in rows
                  if row.get("kind") == "usb_event"]
    require(usb_status
            and all(value.get("boot_id") == PICO_ACCEPTED_BOOT for value in usb_status)
            and all(value.get("boot_id") == PICO_ACCEPTED_BOOT for value in usb_events),
            "Independent USB observation identity")
    status_states = {value.get("state") for value in usb_status
                     if value.get("job_id") == job_id}
    event_states = {value.get("body", {}).get("state") for value in usb_events
                    if value.get("event") == "JOB_STATE"
                    and value.get("body", {}).get("job_id") == job_id}
    status_jobs = {value.get("job_id") for value in usb_status if value.get("job_id")}
    event_jobs = {value.get("body", {}).get("job_id") for value in usb_events
                  if value.get("event") == "JOB_STATE"
                  and value.get("body", {}).get("job_id")}
    usb = _usb_completion(status_states, event_states, status_jobs, event_jobs,
                          usb_status[-1], job_id)

    reconciliation = _json(reconciliation_path)
    after = reconciliation.get("after", {})
    reservation = reconciliation.get("reservation", {})
    reconciled_terminal = _terminal(after, job_id)
    require(reconciliation.get("status") == "RECONCILED"
            and after.get("output_active") is False
            and after.get("owner_id") is None
            and reconciled_terminal == usb["terminal"]
            and reservation.get("state") == "RELEASED"
            and reservation.get("packet_sha256") == attempt_hash
            and reservation.get("boards", {}).get("b", {}).get("state") == "empty",
            "Authoritative reconciliation and reservation release")

    result = {
        "schema": "phase11.6-job-result-v1",
        "plan_sha256": digest(plan), "job_id": job["id"], "wtp_job_id": job_id,
        "band": job["band"], "mode": job["mode"],
        "submission_path": job["submission_path"],
        "planned_duration_ns": job["planned_duration_ns"],
        "target_utc_ns": int(armed["body"]["start_utc_ns"]),
        "terminal_records": [usb["terminal"]], "released_status": after,
        "controller_disconnect_after_arm": False,
        "observer": {
            "console_samples": len(console), "usb_status_samples": len(usb_status),
            "usb_states": usb["status_states"],
            "usb_event_states": usb["event_states"],
            "console_final": console[-1], "usb_final": usb["final"],
        },
        "capture": capture, "browser": browser,
        "recovery": {
            "kind": "offline-auditor-only",
            "original_failure": failure["value"],
            "no_network_usb_sdr_or_rf_access": True,
            "capture_validator_sha256": validator,
            "source_sha256": {
                "attempt_packet": attempt_file_hash,
                "execution_journal": sha256(attempt_root / "execution.jsonl"),
                "reconciliation": sha256(reconciliation_path),
                "browser_result": sha256(browser_path),
                "browser_journal": sha256(attempt_root / "job/browser/browser.jsonl"),
                "capture_metadata": capture["metadata_sha256"],
                "capture_iq": capture["capture_sha256"],
            },
        },
        "disposition": "CAPTURED_REQUIRES_ANALYSIS",
    }
    output.mkdir(mode=0o700)
    require(not output.is_symlink() and not any(output.iterdir()),
            "Fresh private recovery output")
    save(output / "recovered-result.json", result)
    return result


def recover_postflight_inventory(root: Path, plan: dict, job: dict, attempt: dict,
                                 attempt_packet_path: Path, attempt_root: Path,
                                 reconciliation_path: Path, helper: Path,
                                 qualification_source: Path, output: Path) -> dict:
    """Recover a completed browser job whose postflight inventory saw BUSY."""
    attempt_root = attempt_root.resolve(strict=True)
    require(not attempt_root.is_symlink()
            and not (attempt_root / "run-result.json").exists(),
            "Recovery is only for an incomplete wrapper result")
    rows = _jsonl(attempt_root / "execution.jsonl")
    failure = _one(rows, "failure")
    attempt_file_hash = sha256(attempt_packet_path)
    attempt_hash = hashlib.sha256(
        json.dumps(attempt, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    expected_failure = "phase116-after-a-" + attempt_hash[:12] + " inventory"
    require(failure["value"] == {"type": "ValueError", "message": expected_failure}
            and rows[-2] is failure
            and rows[-1].get("kind") == "reservation_left_held"
            and not any(row.get("kind") == "finish" for row in rows),
            "Exact recoverable postflight inventory failure")

    start = _one(rows, "start")["value"]
    job_id = attempt["effective_job"]["job_id"]
    require(start.get("plan_sha256") == digest(plan)
            and start.get("job_id") == job["id"]
            and start.get("wtp_job_id") == job_id
            and start.get("attempt_packet_sha256") == attempt_hash
            and start.get("attempt_packet_file_sha256") == attempt_file_hash,
            "Execution journal plan/attempt binding")
    acquired = _one(rows, "reservation_acquired")["value"]
    require(acquired.get("state") == "HELD"
            and acquired.get("packet_sha256") == attempt_hash
            and acquired.get("boards", {}).get("a", {}).get("state")
                in {"empty", "complete"}
            and acquired.get("boards", {}).get("b", {}).get("state") == "empty",
            "Dual-device reservation acquisition")

    result_path = attempt_root / "job/result.json"
    result = _json(result_path)
    require(result.get("schema") == "phase11.6-job-result-v1"
            and result.get("plan_sha256") == digest(plan)
            and result.get("job_id") == job["id"]
            and result.get("wtp_job_id") == job_id
            and result.get("band") == job["band"]
            and result.get("mode") == job["mode"]
            and result.get("submission_path") == job["submission_path"]
            and result.get("planned_duration_ns") == job["planned_duration_ns"],
            "Completed job result binding")

    capture, validator = _capture(
        attempt_root, job, start, helper, qualification_source, 18.0
    )
    require(start.get("capture_validator_sha256") == validator
            and _one(rows, "capture_complete")["value"] == capture
            and result.get("capture") == capture,
            "Completed capture identity")
    browser = _one(rows, "browser_submit_complete")["value"]
    browser_path = attempt_root / "job/browser/browser-result.json"
    require(browser == _json(browser_path) == result.get("browser")
            and browser.get("status") == "PASS"
            and browser.get("job_id") == job_id
            and browser.get("manual_refresh_overlap") is True,
            "Completed browser result identity")

    console = [row["value"]["value"] for row in rows
               if row.get("kind") == "console_info"]
    require(console, "Independent console observations")
    for value in console:
        resource_gate(value, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
    usb_status = [row["value"]["value"] for row in rows
                  if row.get("kind") == "usb_status"]
    usb_events = [row["value"]["value"] for row in rows
                  if row.get("kind") == "usb_event"]
    require(usb_status
            and all(value.get("boot_id") == PICO_ACCEPTED_BOOT for value in usb_status)
            and all(value.get("boot_id") == PICO_ACCEPTED_BOOT for value in usb_events),
            "Independent USB observation identity")
    status_states = {value.get("state") for value in usb_status
                     if value.get("job_id") == job_id}
    event_states = {value.get("body", {}).get("state") for value in usb_events
                    if value.get("event") == "JOB_STATE"
                    and value.get("body", {}).get("job_id") == job_id}
    status_jobs = {value.get("job_id") for value in usb_status if value.get("job_id")}
    event_jobs = {value.get("body", {}).get("job_id") for value in usb_events
                  if value.get("event") == "JOB_STATE"
                  and value.get("body", {}).get("job_id")}
    usb = _usb_completion(status_states, event_states, status_jobs, event_jobs,
                          usb_status[-1], job_id)
    require(result.get("observer", {}).get("usb_final") == usb["final"]
            and result.get("observer", {}).get("console_final") == console[-1]
            and result.get("terminal_records") == [usb["terminal"]]
            and result.get("released_status", {}).get("owner_id") is None
            and result.get("released_status", {}).get("output_active") is False,
            "Completed observer/result identity")

    reconciliation = _json(reconciliation_path)
    after = reconciliation.get("after", {})
    reservation = reconciliation.get("reservation", {})
    require(reconciliation.get("status") == "RECONCILED"
            and after.get("state") == "complete"
            and after.get("job_id") == job_id
            and after.get("output_active") is False
            and after.get("owner_id") is None
            and _terminal(after, job_id) == usb["terminal"]
            and reservation.get("state") == "RELEASED"
            and reservation.get("packet_sha256") == attempt_hash
            and reservation.get("boards", {}).get("a", {}).get("state") == "complete"
            and reservation.get("boards", {}).get("b", {}).get("state") == "empty",
            "Authoritative reconciliation and reservation release")

    recovered = copy.deepcopy(result)
    recovered["recovery"] = {
        "kind": "offline-auditor-only-postflight-inventory",
        "original_failure": failure["value"],
        "no_network_usb_sdr_or_rf_access": True,
        "capture_validator_sha256": validator,
        "source_sha256": {
            "attempt_packet": attempt_file_hash,
            "execution_journal": sha256(attempt_root / "execution.jsonl"),
            "job_result": sha256(result_path),
            "reconciliation": sha256(reconciliation_path),
            "browser_result": sha256(browser_path),
            "capture_metadata": capture["metadata_sha256"],
            "capture_iq": capture["capture_sha256"],
        },
    }
    output.mkdir(mode=0o700)
    require(not output.is_symlink() and not any(output.iterdir()),
            "Fresh private recovery output")
    save(output / "recovered-result.json", recovered)
    return recovered
