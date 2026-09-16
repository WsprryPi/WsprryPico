#!/usr/bin/env python3
"""Console-only Package 5 application-quiet sampler; no WTP or HTTPS access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from phase11_5_inventory import exclusive_port, exchange, require
from phase11_5_package5_plan import BOOT, DEVICE, IMAGE, SOURCE


SERIAL = "0BF4B4AEC9FFB344"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_packet(packet):
    quiet = packet["post_quiet"]
    require((packet["source_revision"], packet["image_sha256"], packet["boot_id"]) ==
            (SOURCE, IMAGE, BOOT) and quiet["seconds"] == 360 and
            quiet["sample_interval_seconds"] == 30 and
            quiet["phase"] in {"normalizer", "cycle-1", "cycle-2", "cycle-3"},
            "Frozen Package 5 application-quiet packet")
    predecessor = packet.get("quiet_predecessor")
    if predecessor is not None:
        require(packet["schema"] == packet["scope"] == "phase11.5-package5-quiet-v1" and
                packet["runtime_seconds"] == 390 and
                packet["rf_jobs"] == packet["wifi_cycles"] == packet["flashes"] ==
                packet["configuration_writes"] == packet["controlled_reboots"] == 0 and
                set(predecessor) == {"root", "packet_sha256", "audit_sha256"} and
                all(isinstance(predecessor[key], str) and predecessor[key]
                    for key in predecessor) and
                all(len(predecessor[key]) == 64 and
                    all(c in "0123456789abcdef" for c in predecessor[key])
                    for key in ("packet_sha256", "audit_sha256")),
                "Bound quiet predecessor evidence")
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no device access.")
        return
    require(os.geteuid() == 0, "Package 5 quiet sampler runs as root")
    root = args.root.resolve(strict=True)
    require(digest(root / "packet.json") == args.packet_sha256, "Quiet packet changed")
    packet = validate_packet(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            time.monotonic_ns() + (packet["post_quiet"]["seconds"] +
            packet["restoration_seconds"]) * 1_000_000_000 <
            packet["fixture_deadline_monotonic_ns"], "Quiet fixture reserve")
    for name, sha in packet["stage_sha256"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and digest(path) == sha,
                "Quiet staged input changed")
    log = (root / "post-quiet.jsonl").open("x")
    sequence = 0

    def emit(kind, value):
        nonlocal sequence
        log.write(json.dumps(dict(sequence=sequence, kind=kind, value=value,
                                  monotonic_ns=time.monotonic_ns(),
                                  utc_ns=time.time_ns())) + "\n")
        log.flush()
        os.fsync(log.fileno())
        sequence += 1

    result = dict(status="RUNNING", phase=packet["post_quiet"]["phase"], samples=0)
    try:
        with exclusive_port(Path(f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00")) as fd:
            began = time.monotonic_ns()
            deadline = began + packet["post_quiet"]["seconds"] * 1_000_000_000
            emit("start", dict(packet_sha256=args.packet_sha256,
                               began_monotonic_ns=began, deadline_monotonic_ns=deadline))
            next_sample = began
            final = None
            while True:
                now = time.monotonic_ns()
                if now < next_sample:
                    time.sleep(min(1, (next_sample - now) / 1_000_000_000))
                    continue
                sample_began = time.monotonic_ns()
                info = exchange(fd, b"INFO\n", time.monotonic() + 5, emit, False)
                status = info["status"]
                require(info["device_id"] == DEVICE and info["revision"] == SOURCE[:12] and
                        status["boot_id"] == BOOT and status["state"] == "empty" and
                        status["output_active"] is False and status["enabled"] is False and
                        info["wtp_input_reserved_bytes"] == 0 and
                        int(info["allocator_failures"]) == 0 and
                        int(info["tls_allocation_failures"]) == 0 and
                        info["core0_stack_guard_valid"] == info["core1_stack_guard_valid"] == 1,
                        "Package 5 application-quiet device gate")
                host_boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
                throttle = subprocess.check_output(["vcgencmd", "get_throttled"],
                                                   text=True, timeout=2).strip()
                require(host_boot == packet["host_boot_id"] and throttle == "throttled=0x0",
                        "Package 5 application-quiet host gate")
                emit("info", dict(began_monotonic_ns=sample_began, value=info,
                                  host_boot=host_boot, throttled=throttle))
                result["samples"] += 1
                final = info
                if time.monotonic_ns() >= deadline:
                    break
                next_sample += packet["post_quiet"]["sample_interval_seconds"] * 1_000_000_000
            ended = time.monotonic_ns()
            require(ended - began >= packet["post_quiet"]["seconds"] * 1_000_000_000,
                    "Package 5 quiet interval shortened")
            result.update(status="PACKAGE5_APPLICATION_QUIET_CAPTURED",
                          began_monotonic_ns=began, ended_monotonic_ns=ended,
                          post_live_bytes=int(final["heap_allocated_bytes"]),
                          allocator_live_bytes=int(final["allocator_live_bytes"]),
                          allocator_failures=int(final["allocator_failures"]),
                          tls_allocation_failures=int(final["tls_allocation_failures"]),
                          heap_capacity_bytes=int(final["heap_capacity_bytes"]),
                          allocator_peak_bytes=int(final["allocator_peak_bytes"]),
                          final_device_monotonic_ns=int(final["status"]["monotonic_now_ns"]))
    except BaseException as error:
        result.update(status="STOPPED_REQUIRES_DIAGNOSIS",
                      error=type(error).__name__ + ": " + str(error))
        emit("failure", result["error"])
    finally:
        emit("finish", result)
        log.close()
        (root / "post-quiet-result.json").write_text(json.dumps(result, indent=2) + "\n")
    require(result["status"] == "PACKAGE5_APPLICATION_QUIET_CAPTURED",
            "Package 5 quiet capture incomplete")


if __name__ == "__main__":
    main()
