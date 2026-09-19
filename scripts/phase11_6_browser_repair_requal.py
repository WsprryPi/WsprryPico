#!/usr/bin/env python3
"""Zero-RF physical requalification of the repaired browser raw-LOAD path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid


FIXTURE = Path("/home/pi/phase11-6-conducted-v30-20260919")
SERIAL = "0BF4B4AEC9FFB344"
DEVICE = "fd6127d11d6aca42a9905fa3fb1bf1d5"
B_SERIAL = "CDDBF8767C506C07"
B_DEVICE = "29f20b7342051ef947aa56cb9d4fab42"
SOURCE = "7068b937240a7cbdfd0f0edbd7d347057604c0f0"
BOOT = "a12f61f7cd59557c1b5628b2568a52d5"
B_REVISION = "8921a7008183"
B_BOOT = "6684b4b197d80cfa0ce83b3aaf205cb0"
FIXTURE_PID = 1243702


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".pending")
    with temporary.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def finished(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    result = next((row for row in reversed(rows)
                   if row.get("kind") == "finish"), None)
    require(result is not None
            and result["value"].get("result") == "READ_ONLY_INVENTORY",
            f"Incomplete inventory: {path.name}")
    return result["value"]


def inventory(root: Path, label: str, serial: str, device: str) -> dict:
    output = root / f"{label}.jsonl"
    error = root / f"{label}.stderr"
    command = [
        sys.executable, str(FIXTURE / "scripts/phase11_5_inventory.py"),
        "--serial", serial, "--device-id", device,
        "--session-id", uuid.uuid4().hex, "--run",
    ]
    with output.open("xb") as stdout, error.open("xb") as stderr:
        result = subprocess.run(
            command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            timeout=90, check=False,
        )
        stdout.flush()
        os.fsync(stdout.fileno())
        stderr.flush()
        os.fsync(stderr.fileno())
    require(result.returncode == 0, f"Inventory failed: {label}")
    return finished(output)


def exact_inactive(values: dict, resource_gate) -> None:
    require(set(values) == {"a", "b"}, "Both Pico inventories required")
    for value in values.values():
        info = value["info"]
        status = value["wtp"]["STATUS"]
        require(
            status["state"] in {"empty", "complete", "aborted", "missed"}
            and status["output_active"] is False
            and status["owner_id"] is None
            and info["status"]["enabled"] is False
            and info["status"]["output_active"] is False,
            "Inactive, unarmed, unowned and schedule-disabled boards required",
        )
    resource_gate(values["a"]["info"], BOOT, SOURCE)
    require(
        values["a"]["info"]["revision"] == SOURCE[:12]
        and values["a"]["wtp"]["STATUS"]["boot_id"] == BOOT
        and values["b"]["info"]["revision"] == B_REVISION
        and values["b"]["wtp"]["STATUS"]["boot_id"] == B_BOOT,
        "Exact repaired A and unchanged B identities required",
    )


def browser_command(root: Path, packet: dict) -> list[str]:
    output = root / "browser"
    return [
        "bwrap", "--ro-bind", "/", "/", "--bind", str(output), str(output),
        "--bind", str(FIXTURE / "browser-home"), "/root",
        "--setenv", "HOME", "/root", "--ro-bind",
        str(FIXTURE / "chromium-etc"), "/etc/chromium", "--tmpfs", "/tmp",
        "--dev", "/dev", "--proc", "/proc", "--unshare-pid",
        "--die-with-parent", "node", str(root / "browser-submit.js"),
        "--root", str(output), "--kind", "raw", "--job", str(root / "job.json"),
        "--boot-id", BOOT, "--abort-after-mutations", "--run",
    ]


def wait_for_observers(console, usb, stop: threading.Event) -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        require(console.failure is None and usb.failure is None,
                "Independent observer failed during readiness")
        clock = usb.clock or {}
        if (console.latest is not None and usb.latest is not None
                and clock.get("state") == "synchronized"
                and clock.get("leap") == "normal"
                and int(clock.get("uncertainty_ns", "999999999"))
                    <= 10_000_000):
            return
        stop.wait(0.05)
    raise TimeoutError("Requalification observer/clock readiness deadline")


def journal_window(path: Path) -> tuple[int, int]:
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    begin = next(row["monotonic_ns"] for row in rows
                 if row["kind"] == "submission_begin")
    end = next(row["monotonic_ns"] for row in rows
               if row["kind"] == "mutations_complete")
    require(begin < end, "Browser mutation timing window")
    return begin, end


def validate_browser(root: Path, console, usb) -> dict:
    browser = root / "browser"
    result = json.loads((browser / "browser-result.json").read_text())
    marker = json.loads(
        (browser / "browser-mutations-complete.json").read_text()
    )
    submission = json.loads((browser / "submit.json").read_text())
    require(
        result.get("status") == "PASS"
        and result.get("expected_abort") is True
        and result.get("operations")
            == ["HELLO", "CLAIM", "LOAD", "ARM", "ABORT", "RELEASE"]
        and "aborted" in result.get("own_states", [])
        and not ({"running", "complete", "missed", "failed"}
                 & set(result.get("own_states", [])))
        and result.get("terminal", {}).get("state") == "aborted"
        and result.get("terminal", {}).get("output_active") is False
        and result.get("final", {}).get("output_active") is False
        and result.get("final", {}).get("owner_id") is None
        and marker.get("operations") == ["HELLO", "CLAIM", "LOAD", "ARM"]
        and all(response.get("status") == 200
                for response in result.get("responses", []))
        and len(result.get("responses", [])) == 6,
        "Actual browser raw LOAD/ARM/ABORT/RELEASE lifecycle",
    )
    accepted = result["responses"][3]["body"]["result"]["clock"]
    lead = int(submission["start_utc_ns"]) - int(accepted["utc_now_ns"])
    require(lead >= 60_000_000_000, "Prelaunch abort safety lead")
    begin, end = journal_window(browser / "browser.jsonl")
    require(
        console.starts and min(console.starts) < begin < end
        and max(console.starts) > end
        and usb.starts and min(usb.starts) < begin < end
        and max(usb.starts) > end,
        "Independent Console and USB observers must span browser mutations",
    )
    return {
        "job_id": result["job_id"],
        "operations": result["operations"],
        "accepted_arm_lead_ns": lead,
        "mutation_begin_monotonic_ns": begin,
        "mutation_end_monotonic_ns": end,
        "console_samples": len(console.starts),
        "usb_samples": len(usb.starts),
        "terminal": result["terminal"],
        "final": result["final"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run requires the authorized zero-RF physical check")
    require(sys.platform.startswith("linux") and os.geteuid() == 0,
            "Run as root on wspr5")
    root = args.root.resolve(strict=True)
    packet_path = root / "packet.json"
    packet = json.loads(packet_path.read_text())
    require(digest(packet_path) == args.packet_sha256,
            "Immutable requalification packet")
    require(packet == {
        "schema": "phase11.6-browser-allocation-repair-requalification-v1",
        "authorization": "PHASE11.6-BROWSER-ALLOCATION-REPAIR-20260919",
        "source_revision": SOURCE,
        "boot_id": BOOT,
        "image_sha256":
            "f1d437261cb7aa3f9668f7624dad5806346a248202a45f15c553617e12e74a47",
        "browser_script_sha256": digest(root / "browser-submit.js"),
        "runner_sha256": digest(Path(__file__).resolve()),
        "job_sha256": digest(root / "job.json"),
        "fixture_pid": FIXTURE_PID,
        "limits": {"rf_jobs": 0, "arms": 1, "aborts": 1,
                   "flashes": 0, "bootsel": 0, "configuration_writes": 0,
                   "retries": 0},
    }, "Exact repair requalification packet")
    require(
        os.readlink("/proc/self/ns/net")
            == os.readlink(f"/proc/{FIXTURE_PID}/ns/net")
        and os.readlink("/proc/self/ns/mnt")
            == os.readlink(f"/proc/{FIXTURE_PID}/ns/mnt"),
        "Accepted fixture mount/network namespace required",
    )

    sys.path.insert(0, str(FIXTURE / "scripts"))
    from phase11_5_package9 import (ConsoleObserver, Journal, UsbStatusObserver,
                                   resource_gate)
    from phase11_5_rf_reservation import Reservation

    before = {
        "a": inventory(root, "before-a", SERIAL, DEVICE),
        "b": inventory(root, "before-b", B_SERIAL, B_DEVICE),
    }
    exact_inactive(before, resource_gate)
    reservation = Reservation(args.packet_sha256)
    reservation.acquire(before)
    save_new(root / "reservation-acquired.json",
             json.loads(reservation.path.read_text()))

    stop = threading.Event()
    journal = Journal(root / "observers.jsonl")
    console = ConsoleObserver(journal, stop, expected_boot=BOOT,
                              expected_source=SOURCE)
    usb = UsbStatusObserver(journal, stop, uuid.uuid4().hex, "repair-requal",
                            expected_boot=BOOT, observe_clock=True)
    process = None
    stdout = stderr = None
    try:
        console.start()
        usb.start()
        wait_for_observers(console, usb, stop)
        browser = root / "browser"
        browser.mkdir(mode=0o700)
        stdout = (browser / "runner.stdout").open("x")
        stderr = (browser / "runner.stderr").open("x")
        process = subprocess.Popen(browser_command(root, packet),
                                   stdout=stdout, stderr=stderr)
        ready_deadline = time.monotonic() + 50
        while time.monotonic() < ready_deadline:
            require(process.poll() is None,
                    "Browser exited before readiness")
            if (browser / "browser-ready").exists():
                break
            time.sleep(0.1)
        require((browser / "browser-ready").exists(),
                "Browser readiness deadline")
        target = ((time.time_ns() + 120_000_000_000 + 999_999_999)
                  // 1_000_000_000) * 1_000_000_000
        save_new(browser / "submit.json", {"start_utc_ns": str(target)})
        code = process.wait(timeout=120)
        require(code == 0, "Browser repair requalification failed")
        # Keep both persistent observers alive for at least the next scheduled
        # sample so the mutation window is bracketed rather than inferred.
        time.sleep(6)
        stop.set()
        console.join(10)
        usb.join(10)
        require(not console.is_alive() and not usb.is_alive()
                and console.failure is None and usb.failure is None,
                "Independent observer completion")
        browser_result = validate_browser(root, console, usb)
        final = {
            "a": inventory(root, "final-a", SERIAL, DEVICE),
            "b": inventory(root, "final-b", B_SERIAL, B_DEVICE),
        }
        exact_inactive(final, resource_gate)
        info = final["a"]["info"]
        require(
            int(info["allocator_failures"]) == 0
            and info["allocator_largest_successful_request_bytes"] >= 16_000
            and info["heap_capacity_bytes"] - info["allocator_peak_bytes"]
                >= 32_768,
            "Repaired browser allocation/resource gate",
        )
        reservation.release(final)
        save_new(root / "reservation-released.json",
                 json.loads(reservation.path.read_text()))
        result = {
            "schema": "phase11.6-browser-allocation-repair-requalification-result-v1",
            "result": "PASS",
            "source_revision": SOURCE,
            "boot_id": BOOT,
            "browser": browser_result,
            "allocator_largest_successful_request_bytes":
                info["allocator_largest_successful_request_bytes"],
            "allocator_failures": info["allocator_failures"],
            "tls_allocation_failures": info["tls_allocation_failures"],
            "heap_reserve_bytes":
                info["heap_capacity_bytes"] - info["allocator_peak_bytes"],
            "stack_guards_valid": (
                info["core0_stack_guard_valid"]
                == info["core1_stack_guard_valid"] == 1
            ),
            "rf_jobs": 0,
            "arms": 1,
            "aborts": 1,
            "reservation_released": True,
        }
        save_new(root / "result.json", result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except BaseException as error:
        stop.set()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        console.join(10) if console.ident is not None else None
        usb.join(10) if usb.ident is not None else None
        save_new(root / "failure.json", {
            "result": "STOPPED_REQUIRES_RECONCILIATION",
            "type": type(error).__name__, "message": str(error),
        })
        raise
    finally:
        stop.set()
        if stdout is not None:
            stdout.close()
        if stderr is not None:
            stderr.close()
        journal.close()
        reservation.close()


if __name__ == "__main__":
    raise SystemExit(main())
