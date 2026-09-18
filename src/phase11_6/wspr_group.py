"""Three-consecutive-slot WSPR execution and retained-capture slicing."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
import urllib.error
import uuid

import numpy as np

from phase11_5_inventory import require
from phase11_5_package9 import ConsoleObserver, UsbStatusObserver, resource_gate

from phase11_6.live import (
    BrowserSubmit,
    BrowserWatch,
    Capture,
    Journal,
    NetworkPeer,
    _tls_messages,
    host_status,
    render_production_ini,
    save,
    sha256,
    usb_completion,
    wait_observer_readiness,
    wait_for_terminal,
)
from phase11_6.plan import FIRMWARE_SOURCE, PICO_ACCEPTED_BOOT, canonical, digest


GROUP_SCHEMA = "phase11.6-wspr-group-v1"
SLOT_NS = 120_000_000_000


def group_digest(value: dict) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _expected_group_jobs(plan: dict, band: str) -> list[dict]:
    jobs = [job for packet in plan["packets"] for job in packet["jobs"]
            if job["band"] == band and job["mode"] == "WSPR"
            and job["purpose"] == "nominal"]
    require(len(jobs) == 3
            and [job["submission_path"] for job in jobs]
            == ["production", "browser_raw", "controller_disconnect"],
            "Frozen WSPR group jobs")
    return jobs


def compose_group(plan: dict, band: str, attempts: list[dict],
                  attempt_paths: list[Path], tool_root: Path) -> dict:
    jobs = _expected_group_jobs(plan, band)
    require(len(attempts) == len(attempt_paths) == 3, "Three WSPR attempts")
    bindings = []
    for job, attempt, path in zip(jobs, attempts, attempt_paths):
        require(attempt.get("job_id") == job["id"]
                and attempt.get("planned_rf_seconds")
                == job["planned_duration_ns"] / 1e9,
                "WSPR attempt/job binding")
        bindings.append({
            "job_id": job["id"],
            "submission_path": job["submission_path"],
            "attempt_packet": str(path.resolve()),
            "attempt_packet_sha256": hashlib.sha256(canonical(attempt)).hexdigest(),
            "attempt_packet_file_sha256": sha256(path),
        })
    tools = [
        "src/phase11_6/live.py",
        "src/phase11_6/wspr_group.py",
        "scripts/run_phase11_6_wspr_group.py",
        "scripts/phase11_6_browser_watch.js",
        "scripts/phase11_6_browser_submit.js",
    ]
    return {
        "schema": GROUP_SCHEMA,
        "plan_sha256": digest(plan),
        "band": band,
        "execution_order": [jobs[0]["id"], jobs[2]["id"], jobs[1]["id"]],
        "slot_spacing_ns": str(SLOT_NS),
        "planned_jobs": 3,
        "planned_rf_seconds": sum(job["planned_duration_ns"] for job in jobs) / 1e9,
        "automatic_retries": 0,
        "attempts": bindings,
        "tool_sha256": {name: sha256(tool_root / name) for name in tools},
    }


def validate_group(group: dict, plan: dict, tool_root: Path) -> list[dict]:
    require(group.get("schema") == GROUP_SCHEMA
            and group.get("plan_sha256") == digest(plan), "WSPR group schema/plan")
    jobs = _expected_group_jobs(plan, group.get("band"))
    paths = [Path(item["attempt_packet"]) for item in group.get("attempts", [])]
    attempts = [json.loads(path.read_text()) for path in paths]
    expected = compose_group(plan, group["band"], attempts, paths, tool_root)
    require(group == expected, "Immutable WSPR group packet")
    return jobs


def _next_slot() -> int:
    now = time.time_ns()
    target = ((now + SLOT_NS - 1) // SLOT_NS) * SLOT_NS
    if target - now < 45_000_000_000:
        target += SLOT_NS
    return target


def _production_wspr(root: Path, plan: dict, job: dict, directory: Path,
                     binary: Path, journal: Journal, expected_target: int,
                     watch: BrowserWatch) -> dict:
    directory.mkdir(mode=0o700)
    port = 31_425
    ini = render_production_ini(root, directory, job, port)
    tls_log = directory / "production-tls.bin"
    command = [
        str(binary), "--backend", "wtp", "-i", str(ini),
        "--socket-loopback-only", "--socket-loopback-family", "ipv4",
        "--allow-unqualified-frequency", "--allow-non-amateur-frequency",
    ]
    environment = dict(os.environ, TZ="UTC", LD_PRELOAD=str(root / "observer.so"),
                       PHASE115_TLS_LOG=str(tls_log))
    openssl = root / "production-openssl.cnf"
    if openssl.is_file():
        environment["OPENSSL_CONF"] = str(openssl)
    output = (directory / "production.log").open("xb")
    process = subprocess.Popen(command, cwd=directory, stdout=output,
                               stderr=subprocess.STDOUT, env=environment)
    binding = None
    report = None
    host_rows = []
    try:
        journal.emit("wspr_group_production_start", {
            "pid": process.pid, "argv": command, "binary_sha256": sha256(binary),
            "ini_sha256": sha256(ini), "expected_target_utc_ns": expected_target,
        })
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            require(process.poll() is None, "WSPR production exited before binding")
            try:
                value = host_status(port, journal)["host"]
            except OSError:
                time.sleep(0.1)
                continue
            host_rows.append(value)
            if value.get("job_id") and int(value.get("start_utc_ns", "0")) > 0:
                binding = {key: value[key] for key in (
                    "job_id", "owner_id", "session_id", "start_utc_ns",
                    "dispatch_utc_ns", "phase")}
                binding["start_utc_ns"] = int(binding["start_utc_ns"])
                binding["dispatch_utc_ns"] = int(binding["dispatch_utc_ns"])
                break
            time.sleep(0.1)
        require(binding is not None
                and binding["start_utc_ns"] == expected_target
                and binding["start_utc_ns"] % SLOT_NS == 0,
                "Production WSPR consecutive-slot binding")
        journal.emit("wspr_group_production_binding", binding)
        watch.resume()
        deadline = time.monotonic() + max(
            30.0, (expected_target - time.time_ns()) / 1e9
            + job["planned_duration_ns"] / 1e9 + 30.0
        )
        while time.monotonic() < deadline:
            if process.poll() is not None:
                require(process.returncode == 0, "WSPR production child failure")
                break
            try:
                value = host_status(port, journal)["host"]
            except (OSError, urllib.error.URLError):
                try:
                    code = process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    raise
                require(code == 0, "WSPR production listener/child failure")
                break
            host_rows.append(value)
            require(value.get("recovery_required") is False
                    and value.get("safety_fault") is False,
                    "WSPR production host safety state")
            candidate = value.get("last_report") or {}
            remote = value.get("remote") or {}
            if candidate.get("job_id") == binding["job_id"]:
                require(candidate.get("outcome") != "failed", "WSPR production report")
                if candidate.get("outcome") == "complete" \
                        and remote.get("output_active") is False \
                        and value.get("owns") is False:
                    report = candidate
                    break
            time.sleep(0.2)
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=15)
        require(process.returncode == 0, "WSPR production orderly exit")
        output.close()
        written, received, wire = _tls_messages(root, tls_log)
        requests = [value for value in written if value.get("type") == "request"]
        mutations = [value for value in requests
                     if value.get("op") in {"CLAIM", "LOAD", "ARM", "ABORT", "RELEASE"}]
        require([value.get("op") for value in mutations]
                == ["CLAIM", "LOAD", "ARM", "RELEASE"],
                "Production WSPR mutation sequence")
        load, arm = mutations[1:3]
        expected = copy.deepcopy(job["expected_job"])
        expected["job_id"] = binding["job_id"]
        require(load.get("body") == expected
                and arm.get("body", {}).get("job_id") == binding["job_id"]
                and int(arm.get("body", {}).get("start_utc_ns", "0")) == expected_target,
                "Production WSPR exact LOAD/ARM")
        for request in mutations:
            matches = [value for value in received
                       if value.get("type") == "response"
                       and value.get("request_id") == request.get("request_id")
                       and value.get("op") == request.get("op")]
            require(len(matches) == 1 and matches[0].get("ok") is True,
                    "Production WSPR mutation response")
        peer = NetworkPeer(root, journal).connect()
        final = peer.ask("STATUS")
        peer.close()
        terminals = [item for item in final.get("terminal_records", [])
                     if item.get("job_id") == binding["job_id"]]
        require(terminals and terminals[-1].get("state") == "complete"
                and terminals[-1].get("output_active") is False
                and final.get("owner_id") is None
                and final.get("output_active") is False,
                "Production WSPR terminal/release")
        return {"binding": binding, "report": report, "wire": wire,
                "actual_load": load["body"], "terminal": terminals[-1],
                "final": final, "binary_sha256": sha256(binary),
                "ini_sha256": sha256(ini), "returncode": process.returncode}
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
        if not output.closed:
            output.close()


def _controller_wspr(root: Path, job: dict, target: int,
                     watch: BrowserWatch, journal: Journal) -> dict:
    peer = NetworkPeer(root, journal).connect()
    try:
        status = peer.ask("STATUS")
        clock = peer.ask("GET_CLOCK")
        require(status.get("owner_id") is None and status.get("output_active") is False
                and clock.get("state") == "synchronized"
                and int(clock.get("uncertainty_ns", "999999999")) <= 500_000_000
                and target - int(clock["utc_now_ns"]) >= 8_000_000_000,
                "Controller WSPR inter-slot authority/lead")
        peer.ask("CLAIM", {"owner_id": peer.session, "lease_ms": 60000})
        loaded = peer.ask("LOAD", job["expected_job"])
        require(loaded.get("job_id") == job["expected_job"]["job_id"],
                "Controller WSPR LOAD")
        peer.ask("ARM", {"job_id": job["expected_job"]["job_id"],
                 "start_utc_ns": str(target),
                 "max_start_uncertainty_ns": "500000000"})
        session, request_number = peer.session, peer.request_number
        peer.close()
        journal.emit("wspr_group_controller_disconnected", {
            "job_id": job["expected_job"]["job_id"], "target_utc_ns": target})
        watch.resume()
        terminal, peer = wait_for_terminal(
            root, journal, session, request_number,
            job["expected_job"]["job_id"], job["planned_duration_ns"] / 1e9)
        peer.ask("RELEASE")
        final = peer.ask("STATUS")
        require(final.get("owner_id") is None and final.get("output_active") is False,
                "Controller WSPR release")
        return {"loaded_adjustments": loaded.get("adjustments"),
                "terminal": terminal, "final": final,
                "controller_disconnect_after_arm": True}
    finally:
        peer.close()


def _slice_capture(parent_directory: Path, jobs: list[dict], targets: list[int],
                   output: Path) -> list[dict]:
    metadata_path = parent_directory / "capture.json"
    iq_path = parent_directory / "capture.cf32"
    metadata = json.loads(metadata_path.read_text())
    start_text = metadata["timestamps"]["retained_capture_start_utc"]
    start_utc = datetime.datetime.fromisoformat(start_text.replace("Z", "+00:00")).timestamp()
    rate = metadata["actual_settings"]["sample_rate_hz"]
    parent = np.memmap(iq_path, mode="r", dtype="<c8")
    parent_capture_sha256 = sha256(iq_path)
    parent_metadata_sha256 = sha256(metadata_path)
    results = []
    for job, target in zip(jobs, targets):
        directory = output / job["submission_path"] / "capture"
        directory.mkdir(mode=0o700, parents=True)
        first = round(((target / 1e9) - start_utc - 2.0) * rate)
        count = round((job["planned_duration_ns"] / 1e9 + 4.0) * rate)
        last = first + count
        require(first >= 0 and last <= len(parent), "Scheduled WSPR slice containment")
        path = directory / "capture.cf32"
        np.asarray(parent[first:last]).tofile(path)
        digest_value = sha256(path)
        derived = copy.deepcopy(metadata)
        slice_start = datetime.datetime.fromtimestamp(
            start_utc + first / rate, datetime.timezone.utc
        )
        slice_complete = datetime.datetime.fromtimestamp(
            start_utc + last / rate, datetime.timezone.utc
        )
        derived["helper_version"] += "+phase11.6-slice-v1"
        derived["capture_id"] = job["id"]
        derived["timestamps"]["retained_capture_start_utc"] = (
            slice_start.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        )
        derived["timestamps"]["retained_capture_complete_utc"] = (
            slice_complete.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        )
        derived["elapsed_duration_s"] = count / rate
        derived["requested_sample_count"] = count
        derived["retained_sample_count"] = count
        derived["output"] = {
            "path": str(path), "present": True, "complete": True,
            "size_bytes": count * 8, "sha256": digest_value,
            "removed_incomplete_size_bytes": 0,
            "removed_incomplete_sha256": None,
        }
        provenance = {
            "schema": "phase11.6-derived-capture-v1",
            "job_id": job["id"],
            "parent_capture": str(iq_path),
            "parent_metadata": str(metadata_path),
            "parent_capture_sha256": parent_capture_sha256,
            "parent_metadata_sha256": parent_metadata_sha256,
            "sample_range": [first, last],
            "window_rule": "scheduled target minus 2 s through commanded frame plus 2 s",
            "target_utc_ns": str(target),
        }
        derived_path = directory / "capture.json"
        save(derived_path, derived)
        provenance_path = directory / "capture-provenance.json"
        save(provenance_path, provenance)
        from wsprrypi_qualification.capture_metadata import load_capture_metadata
        load_capture_metadata(derived_path)
        results.append({
            "capture_sha256": digest_value,
            "metadata_sha256": sha256(derived_path),
            "sample_count": count, "bytes": count * 8,
            "actual_settings": derived["actual_settings"],
            "resolved_device": derived["resolved_device"],
            "overflow_count": 0, "clipping_samples": 0,
            "leading_quiet_s": 2.0, "trailing_quiet_s": 2.0,
            "derived_slice": provenance,
            "derived_slice_sha256": sha256(provenance_path),
        })
    return results


def execute_wspr_group(root: Path, plan: dict, jobs: list[dict], directory: Path,
                       helper: Path, binary: Path, journal: Journal) -> dict:
    """Execute production, disconnected-controller, browser in consecutive slots."""
    production = next(job for job in jobs if job["submission_path"] == "production")
    browser_job = next(job for job in jobs if job["submission_path"] == "browser_raw")
    controller = next(job for job in jobs
                      if job["submission_path"] == "controller_disconnect")
    ordered = [production, controller, browser_job]
    directory.mkdir(mode=0o700)
    stop = threading.Event()
    console = ConsoleObserver(journal, stop, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
    usb = UsbStatusObserver(journal, stop, uuid.uuid4().hex, 116,
                            PICO_ACCEPTED_BOOT, observe_clock=True)
    production_watch = BrowserWatch(root, directory / "production/browser", None,
                                    600, journal, refresh_interval_s=10.0)
    controller_watch = BrowserWatch(
        root, directory / "controller_disconnect/browser",
        controller["expected_job"]["job_id"], 600, journal)
    browser = BrowserSubmit(root, directory / "browser_raw/browser", browser_job,
                            600, journal)
    capture = None
    try:
        console.start(); usb.start()
        wait_observer_readiness(console, usb)
        status, clock = usb.latest, usb.clock
        require(status.get("boot_id") == PICO_ACCEPTED_BOOT
                and status.get("owner_id") is None
                and status.get("output_active") is False
                and clock.get("state") == "synchronized"
                and clock.get("leap") == "normal"
                and int(clock.get("uncertainty_ns", "999999999")) <= 500_000_000,
                "WSPR group preflight authority/clock")
        production_watch.start(); production_watch.pause()
        controller_watch.start(); controller_watch.pause()
        browser.start()
        target = _next_slot()
        targets = [target, target + SLOT_NS, target + 2 * SLOT_NS]
        while target - time.time_ns() > 75_000_000_000:
            require(
                production_watch.process is not None
                and production_watch.process.poll() is None
                and controller_watch.process is not None
                and controller_watch.process.poll() is None
                and browser.process is not None
                and browser.process.poll() is None,
                "WSPR browser observers remain ready before capture",
            )
            time.sleep(0.25)
        capture_seconds = ((targets[-1] - time.time_ns()) / 1e9
                           + browser_job["planned_duration_ns"] / 1e9 + 15.0)
        require(400.0 <= capture_seconds <= 450.0, "Finite WSPR group capture")
        capture = Capture(root, directory / "capture", helper,
                          production["nominal_frequency_hz"], capture_seconds, journal)
        capture.start()
        prod = _production_wspr(root, plan, production,
                                directory / "production", binary, journal, targets[0],
                                production_watch)
        production_browser = production_watch.finish()
        control = _controller_wspr(root, controller, targets[1],
                                   controller_watch, journal)
        controller_browser = controller_watch.finish()
        probe = NetworkPeer(root, journal).connect()
        empty, fresh = probe.ask("STATUS"), probe.ask("GET_CLOCK")
        probe.close()
        require(empty.get("owner_id") is None and empty.get("output_active") is False
                and targets[2] - int(fresh["utc_now_ns"]) >= 8_000_000_000,
                "Browser WSPR inter-slot authority/lead")
        browser.submit(targets[2])
        browser_value = browser.finish()
        final_peer = NetworkPeer(root, journal).connect()
        final = final_peer.ask("STATUS")
        final_peer.close()
        require(final.get("owner_id") is None and final.get("output_active") is False,
                "WSPR group final authority")
        capture_parent = capture.finish()
        slices = _slice_capture(directory / "capture", ordered, targets, directory)
        stop.set(); console.join(10); usb.join(10)
        require(not console.is_alive() and not usb.is_alive()
                and console.failure is None and usb.failure is None
                and console.latest is not None and usb.latest is not None,
                "WSPR group observer health")
        resource_gate(console.latest, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
        journal_path = Path(journal.stream.name)
        journal_rows = [json.loads(line)
                        for line in journal_path.read_text().splitlines()]
        statuses = [row["value"]["value"] for row in journal_rows
                    if row.get("kind") == "usb_status"]
        events = [row["value"]["value"] for row in journal_rows
                  if row.get("kind") == "usb_event"]
        status_jobs = {value.get("job_id") for value in statuses if value.get("job_id")}
        reductions = {}
        for job in ordered:
            job_id = (prod["binding"]["job_id"] if job is production
                      else job["expected_job"]["job_id"])
            status_states = {value.get("state") for value in statuses
                             if value.get("job_id") == job_id}
            event_states = {value.get("body", {}).get("state") for value in events
                            if value.get("event") == "JOB_STATE"
                            and value.get("body", {}).get("job_id") == job_id}
            reductions[job["id"]] = usb_completion(
                status_states, event_states, status_jobs, {job_id}, statuses[-1], job_id)
        require([targets[1] - targets[0], targets[2] - targets[1]] == [SLOT_NS, SLOT_NS],
                "Three consecutive nominal WSPR slots")
        results = []
        details = {
            production["id"]: {"production": prod, "browser": production_browser},
            controller["id"]: {"controller": control, "browser": controller_browser},
            browser_job["id"]: {"browser": browser_value},
        }
        for job, slot, capture_value in zip(ordered, targets, slices):
            runtime_id = (prod["binding"]["job_id"] if job is production
                          else job["expected_job"]["job_id"])
            results.append({
                "schema": "phase11.6-job-result-v1", "plan_sha256": digest(plan),
                "job_id": job["id"], "wtp_job_id": runtime_id,
                "band": job["band"], "mode": "WSPR",
                "submission_path": job["submission_path"],
                "planned_duration_ns": job["planned_duration_ns"],
                "target_utc_ns": slot, "capture": capture_value,
                "capture_parent": capture_parent, "details": details[job["id"]],
                "observer": {"console_samples": len(console.starts),
                             "usb_status_samples": len(usb.starts),
                             "usb": reductions[job["id"]],
                             "console_final": console.latest},
                "disposition": "CAPTURED_REQUIRES_ANALYSIS",
            })
        value = {"schema": "phase11.6-wspr-group-result-v1",
                 "band": production["band"], "targets_utc_ns": targets,
                 "slot_spacing_ns": str(SLOT_NS), "jobs": results,
                 "capture_parent": capture_parent, "final_status": final}
        save(directory / "group-result.json", value)
        return value
    finally:
        stop.set()
        if console.is_alive(): console.join(10)
        if usb.is_alive(): usb.join(10)
        if capture is not None: capture.terminate()
        production_watch.terminate(); controller_watch.terminate(); browser.terminate()
