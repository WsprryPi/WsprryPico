#!/usr/bin/env python3
"""Run one bounded Package 7 production-owner abort packet."""

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_package7_plan import BOOT, DEVICE, SERIAL, validate
from phase11_5_package7_direct import http as pico_http
from rf_wtp import WtpPeer


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Journal:
    def __init__(self, path):
        self.stream = path.open("x")
        self.sequence = 0

    def emit(self, kind, value):
        row = dict(sequence=self.sequence, kind=kind, value=value,
                   utc_ns=time.time_ns(), monotonic_ns=time.monotonic_ns())
        self.stream.write(json.dumps(row, separators=(",", ":")) + "\n")
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.sequence += 1
        return row

    def close(self):
        self.stream.close()


def host_status(journal):
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
            "http://127.0.0.1:31425/api/v1/status", timeout=3) as response:
        data = response.read(131073)
    require(len(data) <= 131072, "Oversized production host status")
    value = json.loads(data)
    journal.emit("host_status", value)
    return value


def host_authority(journal, selected, timeout=20):
    deadline = time.monotonic() + timeout
    stable = {key: selected[key] for key in
              ("state", "job_id", "owner_id", "output_active")}
    while time.monotonic() < deadline:
        host = host_status(journal)["host"]
        remote = host.get("remote")
        if (host.get("owns") is True and host.get("lease_valid") is True and
                host.get("job_id") == selected["job_id"] and
                host.get("owner_id") == selected["owner_id"] and
                isinstance(host.get("session_id"), str) and
                len(host["session_id"]) == 32 and isinstance(remote, dict) and
                {key: remote.get(key) for key in stable} == stable):
            return host
        time.sleep(.05)
    raise TimeoutError("Production host authority did not reconcile")


def console_info(path, journal):
    def emit(kind, value):
        journal.emit("console_" + kind, value)
    with exclusive_port(path) as fd:
        value = exchange(fd, b"INFO\n", time.monotonic() + 5, emit, False)
    require(value["ok"] is True and value["device_id"] == DEVICE and
            value["status"]["boot_id"] == BOOT, "Production console identity")
    return value


def abort(job, session, request_id, journal):
    body = {"session_id": session, "request_id": request_id, "operation": "ABORT",
            "body": {"job_id": job}}
    encoded = json.dumps(body, separators=(",", ":")).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:31425/api/v1/jobs/{job}/abort", data=encoded, method="POST",
        headers={"Origin": "http://127.0.0.1:31425", "Content-Type": "application/json",
                 "X-WsprryPico-Request": "1"})
    journal.emit("browser_abort_tx", {"body": body, "bytes": len(encoded),
                 "write_complete": True})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(
                request, timeout=10) as response:
            data = response.read(131073)
            code = response.status
    except urllib.error.HTTPError as error:
        data, code = error.read(131073), error.code
    require(len(data) <= 131072, "Oversized production abort response")
    value = json.loads(data)
    journal.emit("browser_abort_response", {"status": code, "body": value})
    require(code == 200 and value["ok"] is True and
            value["request_id"] == request_id, "Production browser abort failed")
    return value


def foreign_and_storage(root, packet, usb, selected, journal, case):
    expected = {"CLAIM": "BUSY", "RELEASE": "NOT_OWNER", "ABORT": "NOT_OWNER"}
    stable = {key: selected[key] for key in
              ("state", "job_id", "owner_id", "output_active")}
    for op, body in (("CLAIM", {"owner_id": os.urandom(16).hex(), "lease_ms": 60000}),
                     ("RELEASE", {}), ("ABORT", {"job_id": selected["job_id"]})):
        try:
            usb.request(op, body)
        except RuntimeError as error:
            require(error.args[0]["code"] == expected[op],
                    "Production foreign control result")
            journal.emit("foreign_rejected", {"state": case, "op": op,
                         "error": error.args[0]})
        else:
            raise ValueError("Production foreign operation succeeded: " + op)
        after = usb.request("STATUS", {})
        require({key: after[key] for key in stable} == stable,
                "Production foreign rejection changed authority")
    code, headers, before = pico_http(root, packet, journal, "GET", "/api/v1/config")
    require(code == 200 and before["config"] is not None and "ETag" in headers,
            "Production configuration baseline")
    code, _, rejected = pico_http(root, packet, journal, "PUT", "/api/v1/config",
                                  before["config"], {"If-Match": headers["ETag"]})
    require(code == 409 and rejected["error"]["code"] == "busy",
            "Production busy storage write")
    code, after_headers, after = pico_http(root, packet, journal, "GET", "/api/v1/config")
    final = usb.request("STATUS", {})
    require(code == 200 and after == before and after_headers["ETag"] == headers["ETag"] and
            {key: final[key] for key in stable} == stable,
            "Production rejected storage write changed state")
    journal.emit("storage_rejected", {"state": case, "etag": headers["ETag"],
                 "job_id": selected["job_id"], "owner_id": selected["owner_id"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=("armed", "running"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no process, device, network or RF accessed.")
        return
    require(os.geteuid() == 0, "Package 7 production packet requires root")
    root = args.root.resolve(strict=True)
    require(root.is_dir() and root.stat().st_mode & 0o077 == 0, "Private production root")
    packet = validate(json.loads((root.parent / "packet.json").read_text()))
    plan = json.loads((root / "case.json").read_text())
    expected_request = packet[f"production_{args.case}_request"]
    require(plan["case"] == args.case and plan["request_id"] == expected_request and
            plan["boot_id"] == BOOT and plan["device_id"] == DEVICE and
            plan["planned_duration_ns"] == 33_000_000_000 and
            plan["start_utc_ns"] > time.time_ns() + 30_000_000_000 and
            os.readlink("/proc/self/ns/net") == plan["netns"] and
            os.readlink("/proc/self/ns/mnt") == plan["mountns"], "Frozen production case")
    binary, ini, observer = (Path(plan[name]) for name in ("binary", "ini", "observer"))
    require(digest(binary) == plan["binary_sha256"] and digest(ini) == plan["ini_sha256"] and
            digest(observer) == plan["observer_sha256"], "Production input identity")
    paused = (root.parent / "installed-paused.txt").read_text()
    require("MainPID=0" in paused and "ActiveState=inactive" in paused and
            "SubState=dead" in paused, "Installed service pause record")
    os.umask(0o077)
    journal = Journal(root / "production.jsonl")
    base = Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}")
    process = None
    try:
        with (root / "production.log").open("xb") as output, \
                exclusive_port(Path(str(base) + "-if02")) as fd, \
                (root / "usb-frames.jsonl").open("x") as wire:
            usb = WtpPeer(fd)
            with contextlib.redirect_stdout(wire):
                hello = usb.request("HELLO", {"versions": ["WTP/1"],
                                    "client_name": f"phase11-5-package7-{args.case}",
                                    "client_version": "1"})
                require(hello["device_id"] == DEVICE and hello["boot_id"] == BOOT,
                        "Production observer identity")
                initial = usb.request("STATUS", {})
                require(initial["state"] == "empty" and initial["owner_id"] is None and
                        initial["output_active"] is False, "Production RF admission")
                env = dict(os.environ, LD_PRELOAD=str(observer),
                           PHASE115_TLS_LOG=str(root / "production-tls.bin"))
                process = subprocess.Popen([str(binary), "--backend", "wtp", "-i", str(ini),
                    "--socket-loopback-only", "--socket-loopback-family", "ipv4",
                    "--allow-unqualified-frequency", "--allow-non-amateur-frequency"],
                    cwd=root, stdout=output, stderr=subprocess.STDOUT, env=env)
                journal.emit("production_start", {"pid": process.pid,
                             "binary_sha256": plan["binary_sha256"],
                             "ini_sha256": plan["ini_sha256"],
                             "observer_sha256": plan["observer_sha256"]})
                ready_deadline = time.monotonic() + 40
                current = None
                while time.monotonic() < ready_deadline:
                    require(process.poll() is None, "Production exited before readiness")
                    try:
                        current = host_status(journal)
                    except OSError:
                        time.sleep(.1)
                        continue
                    identity = current.get("host", {}).get("identity")
                    if identity:
                        require(identity["device_id"] == DEVICE and identity["boot_id"] == BOOT,
                                "Production host identity")
                        break
                    time.sleep(.1)
                require(current and current.get("host", {}).get("identity"),
                        "Production host not ready")
                target_deadline = time.monotonic() + 120
                selected = None
                while time.monotonic() < target_deadline:
                    require(process.poll() is None, "Production exited before abort state")
                    selected = usb.request("STATUS", {})
                    state = selected["state"]
                    if args.case == "armed" and state == "armed" and not selected["output_active"]:
                        break
                    if args.case == "running" and state == "running" and selected["output_active"]:
                        info = console_info(Path(str(base) + "-if00"), journal)
                        require(info["status"]["state"] == "running" and
                                info["status"]["output_active"] is True,
                                "Independent production Running authority")
                        break
                    require(state in ("empty", "loaded", "armed"),
                            "Unexpected production pre-abort state")
                    time.sleep(.05)
                else:
                    raise TimeoutError("Production abort state not observed")
                require(selected["owner_id"] and selected["job_id"],
                        "Production owner/job absent")
                host = host_authority(journal, selected)
                journal.emit("production_selected_state", {"case": args.case,
                             "status": selected, "host": host})
                if args.case == "running":
                    foreign_and_storage(root.parent, packet, usb, selected, journal, args.case)
                    host = host_authority(journal, selected)
                abort(selected["job_id"], host["session_id"], expected_request, journal)
                cleanup_deadline = time.monotonic() + 20
                terminal = None
                final = None
                while time.monotonic() < cleanup_deadline:
                    observed = usb.request("STATUS", {})
                    matches = [r for r in observed["terminal_records"]
                               if r["job_id"] == selected["job_id"]]
                    if matches:
                        require(len(matches) == 1 and matches[0]["state"] == "aborted" and
                                matches[0]["output_active"] is False,
                                "Production terminal outcome")
                        terminal = matches[0]
                    if (terminal and observed["state"] == "empty" and
                            observed["owner_id"] is None and observed["job_id"] is None and
                            observed["output_active"] is False):
                        final = observed
                        break
                    time.sleep(.05)
                require(terminal is not None and final is not None,
                        "Production did not abort, release and become inactive")
                report_deadline = time.monotonic() + 10
                report = None
                while time.monotonic() < report_deadline:
                    host = host_status(journal)["host"]
                    candidate = host.get("last_report")
                    if (candidate and candidate.get("job_id") == selected["job_id"] and
                            candidate.get("outcome") == "cancelled"):
                        report = candidate
                        break
                    time.sleep(.05)
                require(report is not None, "Production cancellation report absent")
                journal.emit("production_pass", {"case": args.case,
                             "planned_duration_ns": 33_000_000_000,
                             "job_id": selected["job_id"], "owner_id": selected["owner_id"],
                             "session_id": host["session_id"], "terminal": terminal,
                             "last_report": report, "final": final})
    finally:
        if process is not None and process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                journal.emit("production_forced_stop", {"exit": process.returncode})
        if process is not None:
            journal.emit("production_exit", {"exit": process.returncode})
        final_info = console_info(Path(str(base) + "-if00"), journal)
        journal.emit("production_cleanup", final_info)
        journal.close()


if __name__ == "__main__":
    main()
