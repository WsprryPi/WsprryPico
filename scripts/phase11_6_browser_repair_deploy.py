#!/usr/bin/env python3
"""Deploy the exact Phase 11.6 browser-allocation repair to Pico A once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


SERIAL = "0BF4B4AEC9FFB344"
DEVICE = "fd6127d11d6aca42a9905fa3fb1bf1d5"
B_SERIAL = "CDDBF8767C506C07"
B_DEVICE = "29f20b7342051ef947aa56cb9d4fab42"
PRIOR_REVISION = "210599d907ac"
PRIOR_BOOT = "1ab2d3ee391ec6c39fcd904f1c9dae01"
NEW_REVISION = "7068b937240a"
B_REVISION = "8921a7008183"
B_BOOT = "6684b4b197d80cfa0ce83b3aaf205cb0"
IMAGE_SHA256 = "f1d437261cb7aa3f9668f7624dad5806346a248202a45f15c553617e12e74a47"
HOST_BOOT = "220e53ca-ca95-4206-9581-dbe28aa1eeb8"
PICOTOOL = Path("/home/pi/phase11-4-e1/picotool-build/picotool")
PICOTOOL_SHA256 = "4a68cfd7fc36002e80857802c8192c9f24c751357c6cb26ad13ad7f38c227921"
FIXTURE = Path("/home/pi/phase11-6-conducted-v30-20260919")
INVENTORY_SHA256 = "348d3028d666732b79c94715bbc187342aa6e2a664d866679d56a3c0e3f069fb"
RESERVATION_SHA256 = "53e8a3013a8d390b4f444a79ae022497ea88006ffdda1b571aa2817a27a235ef"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path: Path, value: object) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


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


def inactive(value: dict) -> None:
    info = value["info"]
    status = value["wtp"]["STATUS"]
    require(
        status["state"] in {"empty", "complete", "aborted", "missed"}
        and status["state"] == info["status"]["state"]
        and status["output_active"] is False
        and info["status"]["output_active"] is False
        and status["owner_id"] is None
        and info["status"]["enabled"] is False,
        "Board must be inactive, unarmed, unowned and schedule-disabled",
    )


def retained(value: dict) -> dict:
    status = value["info"]["status"]
    return {key: status.get(key) for key in (
        "station", "schedules", "schedule_base_frequency_nhz",
        "storage_healthy", "watermark_utc_ns",
    )}


def validate_before(values: dict) -> None:
    require(set(values) == {"a", "b"}, "Both Pico inventories required")
    for value in values.values():
        inactive(value)
    a = values["a"]
    b = values["b"]
    info = a["info"]
    require(
        info["device_id"] == DEVICE
        and info["revision"] == PRIOR_REVISION
        and a["wtp"]["STATUS"]["boot_id"] == PRIOR_BOOT
        and info["recovery_boot"] is True
        and info["fault_stage"] == 14
        and info["fault_hash"] == 3833354787
        and info["fault_allocation_recorded"] is True
        and info["fault_allocation_request_bytes"] == 33335
        and info["fault_allocation_returned_null"] is True,
        "Unexpected Pico A recovery baseline",
    )
    require(
        b["info"]["device_id"] == B_DEVICE
        and b["info"]["revision"] == B_REVISION
        and b["wtp"]["STATUS"]["boot_id"] == B_BOOT,
        "Unexpected Pico B baseline",
    )


def validate_after(before: dict, after: dict) -> str:
    require(set(after) == {"a", "b"}, "Both final Pico inventories required")
    for value in after.values():
        inactive(value)
    a = after["a"]
    b = after["b"]
    info = a["info"]
    status = a["wtp"]["STATUS"]
    boot = status["boot_id"]
    require(
        boot != PRIOR_BOOT
        and info["device_id"] == DEVICE
        and info["revision"] == NEW_REVISION
        and info["status"]["boot_id"] == boot
        and info["recovery_boot"] is False
        and info["system_clock_hz"] == 138_000_000
        and info["status"]["engine"] == "pio-dma-gp2"
        and info["rf_render_in_ram"] is True
        and info["core0_stack_guard_valid"] == 1
        and info["core1_stack_guard_valid"] == 1
        and info["fault_status"] == 0
        and info["dma_errors"] == 0
        and int(info["allocator_failures"]) == 0
        and info["tls_allocation_failures"] == 0
        and info["network"]["control_configured"] is True
        and info["network"]["control_listening"] is True
        and info["network"]["configured_hostname"]
            == "wsprrypico-0a60df.local"
        and info["heap_capacity_bytes"] - info["allocator_peak_bytes"]
            >= 32_768,
        "Pico A candidate identity, health or accepted configuration mismatch",
    )
    require(retained(a) == retained(before["a"]),
            "Pico A retained configuration changed")
    require(
        b["info"]["device_id"] == B_DEVICE
        and b["info"]["revision"] == B_REVISION
        and b["wtp"]["STATUS"]["boot_id"] == B_BOOT
        and retained(b) == retained(before["b"]),
        "Pico B identity, boot or retained configuration changed",
    )
    return boot


def expected_packet(tool_sha256: str) -> dict:
    return {
        "schema": "phase11.6-browser-allocation-repair-deployment-v1",
        "authorization": "PHASE11.6-BROWSER-ALLOCATION-REPAIR-20260919",
        "serial": SERIAL,
        "device_id": DEVICE,
        "prior_revision": PRIOR_REVISION,
        "prior_boot_id": PRIOR_BOOT,
        "new_revision": NEW_REVISION,
        "image_sha256": IMAGE_SHA256,
        "host_boot_id": HOST_BOOT,
        "picotool_sha256": PICOTOOL_SHA256,
        "inventory_helper_sha256": INVENTORY_SHA256,
        "reservation_helper_sha256": RESERVATION_SHA256,
        "deployment_tool_sha256": tool_sha256,
        "limits": {
            "bootsel_transitions": 1,
            "firmware_flashes": 1,
            "configuration_writes": 0,
            "rf_jobs": 0,
            "retries": 0,
        },
    }


def enter_bootsel(exclusive_port, exchange) -> None:
    path = Path(
        f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00"
    )
    with exclusive_port(path) as descriptor:
        response = exchange(
            descriptor, b"BOOTSEL\n", time.monotonic() + 10,
            lambda _kind, _value: None, False,
        )
    require(response.get("ok") is True and response.get("rebooting") is True,
            "Serial-bound BOOTSEL was not acknowledged")
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        for serial_file in Path("/sys/bus/usb/devices").glob("*/serial"):
            try:
                if (serial_file.read_text().strip().upper() == SERIAL
                        and (serial_file.parent / "idVendor").read_text().strip()
                            == "2e8a"
                        and (serial_file.parent / "idProduct").read_text().strip()
                            == "000f"):
                    return
            except OSError:
                pass
        time.sleep(0.2)
    raise ValueError("Serial-bound Pico A BOOTSEL enumeration missing")


def run_picotool(root: Path, label: str, *arguments: object) -> None:
    with (root / f"{label}.stdout").open("xb") as stdout, \
            (root / f"{label}.stderr").open("xb") as stderr:
        result = subprocess.run(
            [str(PICOTOOL), *map(str, arguments)], stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, timeout=180, check=False,
        )
        stdout.flush()
        os.fsync(stdout.fileno())
        stderr.flush()
        os.fsync(stderr.fileno())
    require(result.returncode == 0, f"{label} failed; do not retry")


def wait_application() -> None:
    path = Path(
        f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{SERIAL}-if00"
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not path.exists():
        time.sleep(0.2)
    require(path.exists(), "Pico A application USB did not enumerate")
    time.sleep(10)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run requires the explicit one-flash authorization")
    require(sys.platform.startswith("linux") and os.geteuid() == 0,
            "Run as root on wspr5")
    root = args.root.resolve(strict=True)
    packet_path = root / "packet.json"
    tool_path = Path(__file__).resolve()
    packet = json.loads(packet_path.read_text())
    require(
        digest(packet_path) == args.packet_sha256
        and packet == expected_packet(digest(tool_path)),
        "Exact deployment packet mismatch",
    )
    require(
        Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT
        and digest(PICOTOOL) == PICOTOOL_SHA256
        and digest(root / "candidate.uf2") == IMAGE_SHA256
        and digest(FIXTURE / "scripts/phase11_5_inventory.py")
            == INVENTORY_SHA256
        and digest(FIXTURE / "scripts/phase11_5_rf_reservation.py")
            == RESERVATION_SHA256,
        "Host, flash tool, helper or candidate changed",
    )
    require(not (root / "flash-intent.json").exists(),
            "Deployment packet already consumed")

    sys.path.insert(0, str(FIXTURE / "scripts"))
    from phase11_5_inventory import exclusive_port, exchange
    from phase11_5_rf_reservation import Reservation

    before = {
        "a": inventory(root, "deploy-before-a", SERIAL, DEVICE),
        "b": inventory(root, "deploy-before-b", B_SERIAL, B_DEVICE),
    }
    validate_before(before)
    reservation = Reservation(args.packet_sha256)
    reservation.acquire(before)
    save_new(root / "reservation-acquired.json",
             json.loads(reservation.path.read_text()))
    reservation.close()

    try:
        save_new(root / "flash-intent.json", {
            "serial": SERIAL,
            "image_sha256": IMAGE_SHA256,
            **packet["limits"],
        })
        enter_bootsel(exclusive_port, exchange)
        run_picotool(root, "before-flash-save", "save", "-a", "-v",
                     root / "before-flash.bin", "-t", "bin", "--ser", SERIAL)
        run_picotool(root, "candidate-load", "load", "-v", "-x",
                     root / "candidate.uf2", "--ser", SERIAL)
        wait_application()
        after = {
            "a": inventory(root, "deploy-after-a", SERIAL, DEVICE),
            "b": inventory(root, "deploy-after-b", B_SERIAL, B_DEVICE),
        }
        new_boot = validate_after(before, after)
        reservation = Reservation(
            args.packet_sha256,
            reconciliation=(after, time.monotonic_ns()),
            authorized_boot_changes={"a": (PRIOR_BOOT, new_boot)},
            authorized_revision_changes={
                "a": (PRIOR_REVISION, NEW_REVISION),
            },
        )
        reservation.release(after)
        save_new(root / "reservation-released.json",
                 json.loads(reservation.path.read_text()))
        reservation.close()
        result = {
            "result": "PASS",
            "source_revision": NEW_REVISION,
            "image_sha256": IMAGE_SHA256,
            "prior_boot_id": PRIOR_BOOT,
            "new_boot_id": new_boot,
            "b_boot_id": B_BOOT,
            "before_flash_sha256": digest(root / "before-flash.bin"),
            "retained_configuration_preserved": True,
            "network_identity_configured": True,
            "reservation_released": True,
            **packet["limits"],
        }
        save_new(root / "deployment-result.json", result)
        print(json.dumps(result, sort_keys=True))
        return 0
    except BaseException as error:
        save_new(root / "deployment-failure.json", {
            "result": "STOPPED_REQUIRES_RECONCILIATION",
            "type": type(error).__name__,
            "message": str(error),
        })
        raise


if __name__ == "__main__":
    raise SystemExit(main())
