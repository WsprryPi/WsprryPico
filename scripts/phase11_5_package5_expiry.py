#!/usr/bin/env python3
"""Opt-in Package 5 real terminal-TTL and authenticated-reuse capture."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_package5_http import digest, exchange as http_exchange, get_status, save
from phase11_5_package5_plan import BOOT, DEVICE, NAME, PEER, validate_expiry


SERIAL = "0BF4B4AEC9FFB344"


def client(root, packet):
    require(os.readlink("/proc/self/ns/net") == packet["client_netns"] and
            os.readlink("/proc/self/ns/mnt") == packet["client_mountns"],
            "Package 5 expiry client namespace")
    plan = packet["terminal_expiry"]
    log = (root / "expiry-http.jsonl").open("x")
    sequence = 0
    last_response = None

    def emit(kind, value):
        nonlocal sequence, last_response
        row = dict(sequence=sequence, kind=kind, value=value,
                   monotonic_ns=time.monotonic_ns(), utc_ns=time.time_ns())
        log.write(json.dumps(row) + "\n")
        log.flush()
        os.fsync(log.fileno())
        sequence += 1
        if kind in ("http_response", "status_response"):
            last_response = row["monotonic_ns"]

    result = dict(status="RUNNING", passed=[])
    try:
        emit("start", dict(packet_sha256=digest(root / "packet.json")))
        before = get_status(root, packet, emit, name=NAME, peer_sha=PEER, device=DEVICE)
        result["passed"].append("before-status")
        require(last_response is not None, "Missing terminal pre-expiry response")
        quiet = dict(packet_sha256=digest(root / "packet.json"), began_monotonic_ns=last_response,
                     seconds=plan["quiet_seconds"])
        save(root / "terminal-expiry-quiet.json", quiet)
        deadline = last_response / 1_000_000_000 + plan["quiet_seconds"]
        while time.monotonic() < deadline:
            time.sleep(min(1, max(0, deadline - time.monotonic())))
        for case in [case for case in plan["cases"] if case["phase"] == "after"]:
            http_exchange(root, packet, case, emit, name=NAME, peer_sha=PEER, device=DEVICE)
            result["passed"].append(case["label"])
        after = get_status(root, packet, emit, name=NAME, peer_sha=PEER, device=DEVICE)
        result["passed"].append("after-status")
        result["before_job"] = before["job"]
        result["after_job"] = after["job"]
        result["status"] = "CAPTURED_REQUIRES_AUDIT"
    except BaseException as error:
        result.update(status="STOPPED_REQUIRES_DIAGNOSIS",
                      error=type(error).__name__ + ": " + str(error))
        emit("failure", result["error"])
    finally:
        emit("finish", result)
        log.close()
        save(root / "expiry-client-result.json", result)
    require(result["status"] == "CAPTURED_REQUIRES_AUDIT", "Package 5 expiry client incomplete")


def run(root, packet):
    deadline = time.monotonic() + packet["runtime_seconds"]
    result = dict(status="RUNNING", console_samples=0)
    log = (root / "expiry.jsonl").open("x")
    sequence = 0
    process = None

    def emit(kind, value):
        nonlocal sequence
        log.write(json.dumps(dict(sequence=sequence, kind=kind, value=value,
                                  monotonic_ns=time.monotonic_ns(), utc_ns=time.time_ns())) + "\n")
        log.flush()
        os.fsync(log.fileno())
        sequence += 1

    def sample(fd):
        began = time.monotonic_ns()
        info = exchange(fd, b"INFO\n", min(deadline, time.monotonic() + 5), emit, False)
        status = info["status"]
        require(info["device_id"] == DEVICE and info["revision"] == packet["source_revision"][:12]
                and status["boot_id"] == BOOT and status["state"] == "empty" and
                status["output_active"] is False and int(info["allocator_failures"]) == 0 and
                int(info["tls_allocation_failures"]) == 0,
                "Package 5 expiry Console identity/resource gate")
        emit("info", dict(began_monotonic_ns=began, value=info))
        result["console_samples"] += 1
        return info

    try:
        emit("start", dict(packet_sha256=digest(root / "packet.json")))
        with exclusive_port(Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")) as fd:
            sample(fd)
            command = ["nsenter", "-t", str(packet["client_pid"]), "-m", "-n", "python3",
                       str(root / "scripts/phase11_5_package5_expiry.py"), "--root", str(root),
                       "--packet-sha256", digest(root / "packet.json"), "--client", "--run"]
            emit("client_start", dict(program="phase11_5_package5_expiry.py"))
            with (root / "expiry-client.stdout").open("xb") as out, \
                    (root / "expiry-client.stderr").open("xb") as err:
                process = subprocess.Popen(command, stdout=out, stderr=err)
            while process.poll() is None:
                require(time.monotonic() < deadline, "Package 5 expiry runtime")
                sample(fd)
                for _ in range(30):
                    if process.poll() is not None:
                        break
                    time.sleep(1)
            require(process.returncode == 0, "Package 5 expiry client failed")
            final = sample(fd)
        result.update(status="CAPTURED_REQUIRES_AUDIT", final_info=final)
    except BaseException as error:
        result.update(status="STOPPED_REQUIRES_DIAGNOSIS",
                      error=type(error).__name__ + ": " + str(error))
        emit("failure", result["error"])
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        emit("finish", result)
        log.close()
        save(root / "expiry-result.json", result)
    require(result["status"] == "CAPTURED_REQUIRES_AUDIT", "Package 5 expiry capture incomplete")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--client", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no host, network or device access.")
        return
    require(os.geteuid() == 0, "Package 5 expiry runs as root on wspr5")
    root = args.root.resolve(strict=True)
    require(digest(root / "packet.json") == args.packet_sha256, "Package 5 expiry packet changed")
    packet = validate_expiry(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            time.monotonic_ns() + (packet["runtime_seconds"] + packet["restoration_seconds"]) * 10**9 <
            packet["fixture_deadline_monotonic_ns"], "Package 5 expiry fixture reserve")
    for name, sha in packet["stage_sha256"].items():
        require((root / name).resolve().is_relative_to(root) and digest(root / name) == sha,
                "Package 5 expiry staged input changed")
    if args.client:
        client(root, packet)
    else:
        run(root, packet)


if __name__ == "__main__":
    main()
