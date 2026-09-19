"""Three-consecutive-slot WSPR execution and retained-capture slicing."""

from __future__ import annotations

import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import threading
import time
import urllib.error
import uuid

import numpy as np

from phase11_5_inventory import exclusive_port, require
from phase11_5_package9 import ConsoleObserver, resource_gate

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
)
from phase11_6.plan import (FIRMWARE_SOURCE, PICO_ACCEPTED_BOOT, PICO_DEVICE_ID,
                            PICO_SERIAL, canonical, digest)


GROUP_SCHEMA = "phase11.6-wspr-group-v1"
SLOT_NS = 120_000_000_000
WSPR_SLOT_PHASE_NS = 1_000_000_000
USB_WTP_PORT = Path(
    f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{PICO_SERIAL}-if02"
)


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
        "slot_phase_ns": str(WSPR_SLOT_PHASE_NS),
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
    target = (
        (now - WSPR_SLOT_PHASE_NS + SLOT_NS - 1) // SLOT_NS * SLOT_NS
        + WSPR_SLOT_PHASE_NS
    )
    if target - now < 45_000_000_000:
        target += SLOT_NS
    return target


def require_fixture_namespaces(fixture_process: int) -> dict:
    """Fail before any attempt or RF unless running inside the live fixture."""
    require(type(fixture_process) is int and fixture_process > 1,
            "Active fixture process identifier")
    identities = {}
    for name in ("mnt", "net"):
        try:
            current = os.readlink(f"/proc/self/ns/{name}")
            fixture = os.readlink(f"/proc/{fixture_process}/ns/{name}")
        except OSError as error:
            raise ValueError("Active fixture namespace identity") from error
        require(current == fixture, f"Required fixture {name} namespace")
        identities[name] = current
    return identities


def _prepare_production_directory(directory: Path) -> None:
    """Accept only the fresh browser observer created for this WSPR slot."""
    if not directory.exists():
        directory.mkdir(mode=0o700)
        return
    require(
        directory.is_dir()
        and not directory.is_symlink()
        and stat.S_IMODE(directory.stat().st_mode) == 0o700
        and {path.name for path in directory.iterdir()} == {"browser"}
        and (directory / "browser").is_dir()
        and not (directory / "browser").is_symlink(),
        "Fresh production WSPR slot directory",
    )


def _production_wtp_terminal(received: list[dict], binding: dict) -> dict:
    """Reduce the authenticated production WTP stream to one terminal event."""
    events = [value for value in received if value.get("type") == "event"]
    require(events and all(
        value.get("protocol") == "WTP/1"
        and value.get("session_id") == binding["session_id"]
        and value.get("boot_id") == PICO_ACCEPTED_BOOT
        for value in events
    ), "Production WSPR event identity")
    event_ids = [value.get("event_id") for value in events]
    require(all(
        isinstance(value, str) and value.isdigit()
        and str(int(value)) == value
        for value in event_ids
    ) and [int(value) for value in event_ids]
        == list(range(int(event_ids[0]), int(event_ids[0]) + len(event_ids))),
        "Production WSPR event order")
    lifecycle = [value for value in events
                 if value.get("event") == "JOB_STATE"
                 and value.get("body", {}).get("job_id") == binding["job_id"]]
    require(
        [value.get("body", {}).get("state") for value in lifecycle]
        == ["loaded", "armed", "running", "complete"]
        and [value.get("body", {}).get("output_active") for value in lifecycle]
        == [False, False, True, False],
        "Production WSPR authenticated lifecycle",
    )
    terminal_event = lifecycle[-1]
    require("error" not in terminal_event["body"],
            "Production WSPR successful terminal event")
    return {
        "job_id": binding["job_id"],
        "boot_id": terminal_event["boot_id"],
        "state": terminal_event["body"]["state"],
        "output_active": terminal_event["body"]["output_active"],
        "event_id": terminal_event["event_id"],
        "authoritative": True,
        "source": "authenticated-wtp-job-state-event",
    }


def _production_wspr(root: Path, plan: dict, job: dict, directory: Path,
                     binary: Path, journal: Journal, expected_target: int,
                     watch: BrowserWatch, on_binding) -> dict:
    _prepare_production_directory(directory)
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
                and (binding["start_utc_ns"] - WSPR_SLOT_PHASE_NS) % SLOT_NS == 0,
                "Production WSPR consecutive-slot binding")
        journal.emit("wspr_group_production_binding", binding)
        on_binding(binding)
        watch.resume()
        deadline = time.monotonic() + max(
            30.0, (expected_target - time.time_ns()) / 1e9
            + job["planned_duration_ns"] / 1e9 + 30.0
        )
        while time.monotonic() < deadline:
            if process.poll() is not None:
                require(process.returncode == 0, "WSPR production child failure")
                break
            require(watch.process is not None and watch.process.poll() is None,
                    "Production browser observer health")
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
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired as error:
                raise TimeoutError(
                    "WSPR production did not exit after its finite configured iteration"
                ) from error
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
        terminal = _production_wtp_terminal(received, binding)
        report_job = (report or {}).get("job") or {}
        if report is not None:
            require(report.get("outcome") == "complete"
                    and report.get("job_id") == binding["job_id"]
                    and report_job.get("job_id") == binding["job_id"]
                    and report_job.get("boot_id") == PICO_ACCEPTED_BOOT
                    and report_job.get("authoritative") is True
                    and report_job.get("state") == "complete"
                    and report_job.get("output_active") is False
                    and report_job.get("device_output_active") is False,
                    "Production WSPR authoritative completion report")
        journal.emit("wspr_group_production_released", {
            "job_id": binding["job_id"],
            "returncode": process.returncode,
            "release_authenticated": True,
            "terminal_event_id": terminal["event_id"],
        })
        return {"binding": binding, "report": report, "wire": wire,
                "actual_load": load["body"], "terminal": terminal,
                "final": {"source": terminal["source"]},
                "binary_sha256": sha256(binary),
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


def _completed_predecessor(status: dict, job_id: str) -> bool:
    if not _terminal_predecessor(status, job_id):
        return False
    return (status.get("state") == "empty"
            and status.get("job_id") is None
            and status.get("owner_id") is None)


def _terminal_predecessor(status: dict, job_id: str) -> bool:
    """Prove exact inactive completion even while its owner is releasing."""
    terminals = [item for item in status.get("terminal_records", [])
                 if item.get("job_id") == job_id]
    current = ((status.get("state") == "complete"
                and status.get("job_id") == job_id)
               or (status.get("state") == "empty"
                   and status.get("job_id") is None))
    return bool(len(terminals) == 1
                and terminals[0].get("state") == "complete"
                and terminals[0].get("output_active") is False
                and current
                and status.get("output_active") is False)


class UsbWsprCoordinator(threading.Thread):
    """Observe all three jobs and perform the time-critical USB handoff."""

    def __init__(self, journal: Journal, stop: threading.Event, cycle: int = 116,
                 console_quiet: threading.Event | None = None):
        super().__init__(name="phase116-wspr-usb")
        self.journal, self.stop, self.cycle = journal, stop, cycle
        self.console_quiet = console_quiet
        self.failure: str | None = None
        self.failure_exception: BaseException | None = None
        self.starts: list[int] = []
        self.latest: dict | None = None
        self.clock: dict | None = None
        self.clock_observed_monotonic_ns: int | None = None
        self.ready = threading.Event()
        self.transition_scheduled = threading.Event()
        self.transition_done = threading.Event()
        self.predecessor_browser_done = threading.Event()
        self.transition: dict | None = None
        self.transition_result: dict | None = None
        self.last_event_id: int | None = None
        self.event_session: str | None = None
        self.first_event_can_gap = False
        self.events_seen_on_connection = 0
        self.event_gaps: list[dict] = []

    def _set_console_quiet(self, quiet: bool) -> None:
        if self.console_quiet is None or self.console_quiet.is_set() == quiet:
            return
        if quiet:
            self.console_quiet.set()
        else:
            self.console_quiet.clear()
        self.journal.emit("wspr_group_console_quiet", {
            "quiet": quiet,
            "reason": "time-critical-successor-mutation-handoff",
        })

    def schedule_transition(self, *, job: dict, target_utc_ns: int,
                            predecessor_job_id: str,
                            predecessor_complete_utc_ns: int,
                            next_browser: BrowserSubmit,
                            next_target_utc_ns: int,
                            next_duration_ns: int) -> None:
        require(self.transition is None and not self.transition_scheduled.is_set(),
                "Single USB WSPR transition")
        self.transition = {
            "job": copy.deepcopy(job),
            "target_utc_ns": target_utc_ns,
            "predecessor_job_id": predecessor_job_id,
            "predecessor_complete_utc_ns": predecessor_complete_utc_ns,
            "next_browser": next_browser,
            "next_target_utc_ns": next_target_utc_ns,
            "next_duration_ns": next_duration_ns,
        }
        self.journal.emit("wspr_group_usb_transition_scheduled", {
            key: value for key, value in self.transition.items()
            if key not in {"job", "next_browser"}
        })
        self.transition_scheduled.set()

    def wait_transition(self, timeout: float) -> dict:
        require(self.transition_done.wait(timeout),
                "USB WSPR transition worker deadline")
        if self.failure_exception is not None:
            raise self.failure_exception
        require(isinstance(self.transition_result, dict),
                "USB WSPR transition result")
        return self.transition_result

    def confirm_predecessor_browser(self, job_id: str) -> None:
        task = self.transition
        require(task is not None
                and task["predecessor_job_id"] == job_id,
                "Exact predecessor browser confirmation")
        self.journal.emit("wspr_group_predecessor_browser_confirmed", {
            "job_id": job_id,
        })
        self.predecessor_browser_done.set()

    def _wait_for_predecessor_browser(self) -> None:
        deadline = time.monotonic() + 20.0
        while not self.predecessor_browser_done.wait(0.05):
            require(not self.stop.is_set(),
                    "USB WSPR stopped before predecessor browser confirmation")
            require(time.monotonic() < deadline,
                    "USB WSPR predecessor browser confirmation deadline")

    def wait_settled(self, job_id: str, timeout: float = 15.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.failure_exception is not None:
                raise self.failure_exception
            if self.latest is not None and _completed_predecessor(self.latest, job_id):
                return self.latest
            time.sleep(0.025)
        raise TimeoutError("USB WSPR final settlement deadline")

    def _consume_events(self, peer) -> None:
        while peer.pending:
            value = peer.pending.popleft()
            require(value.get("type") == "event"
                    and value.get("session_id") == peer.session
                    and value.get("boot_id") == PICO_ACCEPTED_BOOT,
                    "USB WSPR event identity")
            raw_id = value.get("event_id")
            require(isinstance(raw_id, str) and raw_id.isdigit()
                    and str(int(raw_id)) == raw_id,
                    "USB WSPR event order")
            event_id = int(raw_id)
            if self.last_event_id is not None:
                expected = self.last_event_id + 1
                if event_id != expected:
                    require(
                        self.first_event_can_gap
                        and self.events_seen_on_connection == 0
                        and event_id > expected,
                        "USB WSPR event order",
                    )
                    gap = {
                        "previous_event_id": str(self.last_event_id),
                        "next_event_id": raw_id,
                        "missing_event_count": event_id - expected,
                        "reason": "deliberate-controller-transport-disconnect",
                        "new_session_id": peer.session,
                    }
                    self.event_gaps.append(gap)
                    self.journal.emit("usb_event_gap", gap)
            self.first_event_can_gap = False
            self.events_seen_on_connection += 1
            self.last_event_id = event_id
            require(value.get("event") in {"JOB_STATE", "OWNER_RELEASED"},
                    "USB WSPR adverse event")
            self.journal.emit("usb_event", {"cycle": self.cycle, "value": value})

    def _begin_event_connection(self, peer, *, allow_first_gap: bool) -> None:
        require(
            self.event_session is None or self.event_session != peer.session,
            "Distinct USB WSPR event session",
        )
        prior_session = self.event_session
        self.event_session = peer.session
        self.first_event_can_gap = allow_first_gap
        self.events_seen_on_connection = 0
        self.journal.emit("usb_event_connection", {
            "cycle": self.cycle,
            "session_id": peer.session,
            "prior_session_id": prior_session,
            "allow_first_gap": allow_first_gap,
            "last_event_id": (None if self.last_event_id is None
                              else str(self.last_event_id)),
        })

    def _request(self, peer, operation: str, body: dict, *,
                 timeout: float = 5.0, mutation: bool = False) -> dict:
        request_id = f"{peer.sequence + 1:032x}"
        try:
            result = peer.request(operation, body, timeout=timeout)
        except BaseException:
            self._consume_events(peer)
            raise
        if mutation:
            self.journal.emit("usb_controller_exchange", {
                "session_id": peer.session,
                "request_id": request_id,
                "operation": operation,
                "body": body,
                "response_body": result,
            })
        self._consume_events(peer)
        return result

    def _hello(self, peer, label: str) -> dict:
        hello = self._request(peer, "HELLO", {
            "versions": ["WTP/1"],
            "client_name": f"phase11-6-wspr-{label}",
            "client_version": "1",
        })
        require(hello.get("device_id") == PICO_DEVICE_ID
                and hello.get("boot_id") == PICO_ACCEPTED_BOOT,
                "USB WSPR observer identity")
        self.journal.emit("usb_wspr_hello", {
            "cycle": self.cycle, "label": label,
            "session_id": peer.session, "value": hello,
        })
        return hello

    def _poll(self, peer) -> tuple[dict, dict]:
        began = time.monotonic_ns()
        clock = self._request(peer, "GET_CLOCK", {})
        status = self._request(peer, "STATUS", {})
        ended = time.monotonic_ns()
        require(status.get("boot_id") == PICO_ACCEPTED_BOOT,
                "USB WSPR observer boot")
        self.clock, self.latest = clock, status
        self.clock_observed_monotonic_ns = began
        self.starts.append(began)
        self.ready.set()
        self.journal.emit("usb_clock", {"cycle": self.cycle, "value": clock})
        self.journal.emit("usb_status", {
            "cycle": self.cycle, "began_monotonic_ns": began,
            "ended_monotonic_ns": ended, "value": status,
        })
        return status, clock

    @staticmethod
    def _clock_admits(clock: dict, target: int, observed_monotonic_ns: int) -> bool:
        elapsed = time.monotonic_ns() - observed_monotonic_ns
        return (
            elapsed >= 0
            and clock.get("state") == "synchronized"
            and clock.get("leap") == "normal"
            and int(clock.get("uncertainty_ns", "999999999")) <= 500_000_000
            and target - (int(clock.get("utc_now_ns", "0")) + elapsed)
                >= 8_000_000_000
        )

    def _claim_after_terminal(self, peer, task: dict, status: dict) -> dict:
        require(_terminal_predecessor(status, task["predecessor_job_id"]),
                "USB WSPR exact inactive predecessor terminal")
        claim_body = {"owner_id": peer.session, "lease_ms": 60000}
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            try:
                return self._request(
                    peer, "CLAIM", claim_body, timeout=remaining, mutation=True
                )
            except RuntimeError as error:
                detail = error.args[0] if error.args else None
                if not isinstance(detail, dict) or detail.get("code") != "BUSY":
                    raise
                self.journal.emit("usb_controller_claim_busy", {
                    "predecessor_job_id": task["predecessor_job_id"],
                    "error": detail,
                })
                self.stop.wait(0.01)
        raise TimeoutError("USB WSPR predecessor owner release deadline")

    def _arm_controller(self, peer, task: dict, status: dict,
                        initial_clock: dict,
                        clock_observed_monotonic_ns: int) -> dict:
        try:
            target = task["target_utc_ns"]
            job = task["job"]
            job_id = job["expected_job"]["job_id"]
            require(self._clock_admits(
                        initial_clock, target, clock_observed_monotonic_ns),
                    "USB controller WSPR initial authority/lead")
            self.clock = initial_clock
            self.journal.emit("usb_clock", {
                "cycle": self.cycle, "value": initial_clock,
                "source": "immediately-preceding-terminal-poll",
            })
            claim = self._claim_after_terminal(peer, task, status)
            require(self._clock_admits(
                        initial_clock, target, clock_observed_monotonic_ns),
                    "USB controller WSPR post-CLAIM authority/lead")
            loaded = self._request(peer, "LOAD", job["expected_job"],
                                   timeout=30, mutation=True)
            require(loaded.get("job_id") == job_id, "USB controller WSPR LOAD")
            require(self._clock_admits(
                        initial_clock, target, clock_observed_monotonic_ns),
                    "USB controller WSPR pre-ARM authority/lead")
            arm_body = {
                "job_id": job_id, "start_utc_ns": str(target),
                "max_start_uncertainty_ns": "500000000",
            }
            armed = self._request(peer, "ARM", arm_body, mutation=True)
            arm_clock = armed.get("clock") or {}
            try:
                require(arm_clock.get("state") == "synchronized"
                        and arm_clock.get("leap") == "normal"
                        and int(arm_clock.get("uncertainty_ns", "999999999"))
                            <= 500_000_000
                        and target - int(arm_clock.get("utc_now_ns", "0"))
                            >= 8_000_000_000,
                        "USB controller WSPR immutable ARM lead")
            except BaseException:
                self._request(peer, "ABORT", {"job_id": job_id}, mutation=True)
                self._request(peer, "RELEASE", {}, mutation=True)
                raise
            self.clock = arm_clock
            self.journal.emit("usb_clock", {
                "cycle": self.cycle, "value": arm_clock,
                "source": "authoritative-arm-acknowledgement",
            })
            return {
                "job_id": job_id,
                "claim_response": claim,
                "loaded_adjustments": loaded.get("adjustments"),
                "arm_response": armed,
                "arm_clock": arm_clock,
                "controller_session_id": peer.session,
            }
        finally:
            self._set_console_quiet(False)

    def _before_transition(self, peer) -> dict:
        while not self.stop.is_set():
            task = self.transition
            if (task is not None
                    and time.time_ns()
                    >= task["predecessor_complete_utc_ns"] - 2_000_000_000):
                # Stop the large Console INFO transfer before issuing the
                # time-critical terminal GET_CLOCK/STATUS pair.
                self._set_console_quiet(True)
            status, clock = self._poll(peer)
            task = self.transition
            if task is not None and _terminal_predecessor(
                    status, task["predecessor_job_id"]):
                return self._arm_controller(
                    peer, task, status, clock, self.starts[-1]
                )
            if task is None:
                self.transition_scheduled.wait(5.0)
                continue
            quiet_start = task["predecessor_complete_utc_ns"] - 2_000_000_000
            remaining = (quiet_start - time.time_ns()) / 1e9
            if remaining <= 0:
                self._set_console_quiet(True)
            self.stop.wait(0.025 if remaining <= 0 else min(5.0, remaining))
        raise RuntimeError("USB WSPR coordinator stopped before transition")

    def _after_transition(self, peer, armed: dict) -> None:
        task = self.transition
        require(task is not None, "USB WSPR transition state")
        controller_id = armed["job_id"]
        controller_terminal = None
        cleanup = None
        while not self.stop.is_set():
            controller_deadline = (
                task["target_utc_ns"] + task["job"]["planned_duration_ns"]
            )
            if time.time_ns() >= controller_deadline - 2_000_000_000:
                # Do not let a large Console INFO transfer contend with the
                # terminal handoff or the browser's HELLO/CLAIM/LOAD/ARM burst.
                self._set_console_quiet(True)
            status, clock = self._poll(peer)
            terminals = [record for record in status.get("terminal_records", [])
                         if record.get("job_id") == controller_id]
            if terminals:
                require(terminals[0].get("state") == "complete"
                        and terminals[0].get("output_active") is False,
                        "USB controller WSPR terminal")
                controller_terminal = terminals[0]
            if (controller_terminal is not None
                    and status.get("state") == "complete"
                    and status.get("job_id") == controller_id
                    and status.get("owner_id") is None
                    and status.get("output_active") is False):
                claim = self._request(peer, "CLAIM", {
                    "owner_id": peer.session, "lease_ms": 5000,
                }, mutation=True)
                released = self._request(peer, "RELEASE", {}, mutation=True)
                cleanup = {
                    "session_id": peer.session,
                    "pre_release_status": status,
                    "claim_response": claim,
                    "release_response": released,
                }
                task["next_browser"].authorize_predecessor({
                    "schema": "phase11.6-browser-predecessor-authority-v1",
                    "source": "authenticated-usb-event-status-release",
                    "predecessor_job_id": controller_id,
                    "terminal": controller_terminal,
                    "status": status,
                    "clock": clock,
                    "clock_observed_monotonic_ns": str(
                        self.clock_observed_monotonic_ns
                    ),
                    "release_response": released,
                    "event_stream_gaps": copy.deepcopy(self.event_gaps),
                })
                browser_mutations = task["next_browser"].wait_mutations()
                self._set_console_quiet(False)
                self.transition_result = {
                    **armed,
                    "terminal": controller_terminal,
                    "final": {
                        "source": "authenticated-usb-release-acknowledgement",
                        "response": released,
                    },
                    "terminal_release": cleanup,
                    "controller_disconnect_after_arm": True,
                    "controller_transport": "usb-wtp",
                    "predecessor_job_id": task["predecessor_job_id"],
                    "next_browser_submitted_utc_ns": task["next_target_utc_ns"],
                    "next_browser_mutations": browser_mutations,
                    "event_stream_gaps": copy.deepcopy(self.event_gaps),
                }
                self.transition_done.set()
            deadlines = [
                task["target_utc_ns"] + task["job"]["planned_duration_ns"],
                task["next_target_utc_ns"] + task["next_duration_ns"],
            ]
            near_terminal = any(
                -1_000_000_000 <= deadline - time.time_ns() <= 2_000_000_000
                for deadline in deadlines
            )
            self.stop.wait(0.025 if near_terminal else 5.0)

    def run(self) -> None:
        try:
            from rf_wtp import WtpPeer
            with exclusive_port(USB_WTP_PORT) as fd:
                initial = WtpPeer(fd, session=uuid.uuid4().hex)
                self._begin_event_connection(initial, allow_first_gap=False)
                self._hello(initial, "controller-observer")
                armed = self._before_transition(initial)
            task = self.transition
            require(task is not None, "USB WSPR scheduled transition")
            self.journal.emit("wspr_group_controller_disconnected", {
                "job_id": armed["job_id"],
                "target_utc_ns": task["target_utc_ns"],
                "transport": "usb-wtp",
            })
            self._wait_for_predecessor_browser()
            task["next_browser"].submit(
                task["next_target_utc_ns"],
                predecessor_job_id=armed["job_id"],
                predecessor_complete_utc_ns=(
                    task["target_utc_ns"]
                    + task["job"]["planned_duration_ns"]
                ),
            )
            with exclusive_port(USB_WTP_PORT) as fd:
                observer = WtpPeer(fd, session=uuid.uuid4().hex)
                self._begin_event_connection(observer, allow_first_gap=True)
                self._hello(observer, "post-disconnect-observer")
                self._after_transition(observer, armed)
        except BaseException as error:
            self.failure_exception = error
            self.failure = f"{type(error).__name__}: {error}"
            self.ready.set()
            self.transition_done.set()
            self.journal.emit("observer_failure", {
                "observer": "usb-wspr", "cycle": self.cycle,
                "error": self.failure,
            })
            self.stop.set()
        finally:
            self._set_console_quiet(False)


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
    for path in (
        directory / "production",
        directory / "controller_disconnect",
        directory / "browser_raw",
    ):
        path.mkdir(mode=0o700)
    stop = threading.Event()
    console_quiet = threading.Event()
    console = ConsoleObserver(journal, stop, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE,
                              pause=console_quiet)
    usb = UsbWsprCoordinator(journal, stop, console_quiet=console_quiet)
    production_watch = BrowserWatch(root, directory / "production/browser", None,
                                    600, journal, refresh_interval_s=10.0)
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
        browser.start()
        target = _next_slot()
        targets = [target, target + SLOT_NS, target + 2 * SLOT_NS]
        while target - time.time_ns() > 75_000_000_000:
            require(
                production_watch.process is not None
                and production_watch.process.poll() is None
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

        def start_transition(binding: dict) -> None:
            usb.schedule_transition(
                job=controller,
                target_utc_ns=targets[1],
                predecessor_job_id=binding["job_id"],
                predecessor_complete_utc_ns=(
                    targets[0] + production["planned_duration_ns"]
                ),
                next_browser=browser,
                next_target_utc_ns=targets[2],
                next_duration_ns=browser_job["planned_duration_ns"],
            )

        prod = _production_wspr(root, plan, production,
                                directory / "production", binary, journal, targets[0],
                                production_watch, start_transition)
        production_browser = production_watch.finish()
        require(production_browser.get("observed_job_id") == prod["binding"]["job_id"],
                "Production browser runtime binding")
        usb.confirm_predecessor_browser(prod["binding"]["job_id"])
        control = usb.wait_transition(
            controller["planned_duration_ns"] / 1e9 + 75
        )
        browser_value = browser.finish()
        usb.wait_settled(browser_job["expected_job"]["job_id"])
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
                status_states, event_states, status_jobs, {job_id}, statuses[-1],
                job_id,
                mutation_states=(
                    {control["arm_response"]["state"]}
                    if job is controller else set()
                ),
            )
        require([targets[1] - targets[0], targets[2] - targets[1]] == [SLOT_NS, SLOT_NS],
                "Three consecutive nominal WSPR slots")
        results = []
        details = {
            production["id"]: {"production": prod, "browser": production_browser},
            controller["id"]: {"controller": control, "browser": {
                "page_loaded": browser_value["page_loaded"],
                "manual_refresh_overlap": browser_value[
                    "predecessor_manual_refresh_overlap"
                ],
                "observed_job_id": browser_value["predecessor_job_id"],
                "observed_terminal": browser_value["predecessor_terminal"],
                "peer_sha256": browser_value["peer_sha256"],
                "source": "preopened-successor-page",
            }},
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
        production_watch.terminate(); browser.terminate()
