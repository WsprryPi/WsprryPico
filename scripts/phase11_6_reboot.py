#!/usr/bin/env python3
"""Perform the one authorized Phase 11.6 Pico A recovery reboot.

The command is deliberately bound to the sequence-67 recovery checkpoint.  It
records fresh serial inventories of both boards, writes a durable one-shot
intent before sending ``REBOOT``, and never retries that mutation.  A successful
run proves the new boot retained the accepted configuration and cleared the
latched resource-failure counters without a flash, CONFIG write, or RF job.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from phase11_5_inventory import exchange, exclusive_port, require


SCHEMA = "phase11.6-reboot-after-0067-v1"
AUTHORIZATION = "PHASE11.6-REBOOT-AFTER-0067-20260918"
SERIAL_A = "0BF4B4AEC9FFB344"
DEVICE_A = "fd6127d11d6aca42a9905fa3fb1bf1d5"
SOURCE_A = "210599d907ac"
SOURCE_A_FULL = "210599d907acdb23278fc24244b674d62c820d7c"
UF2_A_SHA256 = "b01fecbe3d516dbe5a5e261955e376f062f92a9fe9f7c9b86135bb5f7e8b9811"
OLD_BOOT_A = "be52153ea21a03f75067129f2bc2245f"
SERIAL_B = "CDDBF8767C506C07"
DEVICE_B = "29f20b7342051ef947aa56cb9d4fab42"
BOOT_B = "6684b4b197d80cfa0ce83b3aaf205cb0"
HOST_BOOT = "220e53ca-ca95-4206-9581-dbe28aa1eeb8"
EXPECTED_PRE_FAILURES = {
    "allocator_failures": 428,
    "tls_allocation_failures": 214,
    "allocator_last_failure_request_bytes": 16693,
}


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def tool_identity(tool_root: Path) -> dict[str, str]:
    relatives = (
        "scripts/phase11_6_reboot.py",
        "scripts/phase11_5_inventory.py",
        "scripts/validate_wtp_contract.py",
        "scripts/wtp_monitor.py",
        "docs/protocol/wtp-1.schema.json",
    )
    identity = {}
    for relative in relatives:
        path = tool_root / relative
        require(path.is_file() and not path.is_symlink(), "Regular reboot tool input")
        identity[relative] = digest_bytes(path.read_bytes())
    return identity


def save_new(path: Path, value: object) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def load_inventory(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    require(rows and rows[0]["kind"] == "start", "Inventory start record")
    failures = [row for row in rows if row.get("kind") == "failure"]
    finishes = [row for row in rows if row.get("kind") == "finish"]
    require(not failures and len(finishes) == 1, "Complete successful inventory")
    value = finishes[0]["value"]
    require(value.get("result") == "READ_ONLY_INVENTORY", "Read-only inventory result")
    return value


def inventory_command(tool_root: Path, serial: str, device: str) -> list[str]:
    return [
        sys.executable,
        str(tool_root / "scripts/phase11_5_inventory.py"),
        "--serial", serial,
        "--device-id", device,
        "--run",
    ]


def run_inventory(
    tool_root: Path, evidence: Path, label: str, serial: str, device: str
) -> tuple[dict, Path]:
    path = evidence / f"{label}.jsonl"
    stderr = evidence / f"{label}.stderr"
    with path.open("x") as output, stderr.open("x") as errors:
        completed = subprocess.run(
            inventory_command(tool_root, serial, device),
            stdout=output,
            stderr=errors,
            timeout=75,
            check=False,
        )
        output.flush()
        os.fsync(output.fileno())
        errors.flush()
        os.fsync(errors.fileno())
    require(completed.returncode == 0, f"{label} inventory failed")
    return load_inventory(path), path


def retained_configuration(value: dict) -> dict:
    info = value["info"]
    status = info["status"]
    network = info["network"]
    return {
        "configured": status["configured"],
        "enabled": status["enabled"],
        "suspended": status["suspended"],
        "expires_utc_s": status["expires_utc_s"],
        "station": status["station"],
        "schedules": status["schedules"],
        "schedule_base_frequency_nhz": status["schedule_base_frequency_nhz"],
        "storage_healthy": status["storage_healthy"],
        "reboot_required": status["reboot_required"],
        "watermark_utc_ns": status["watermark_utc_ns"],
        "network_enabled": network["enabled"],
        "network_control_configured": network["control_configured"],
        "stable_hostname": network["stable_hostname"],
        "configured_hostname": network["configured_hostname"],
        "ntp_server": network["ntp_server"],
    }


def resource_counters(value: dict) -> dict:
    info = value["info"]
    return {
        "allocator_failures": int(info["allocator_failures"]),
        "tls_allocation_failures": int(info["tls_allocation_failures"]),
        "allocator_last_failure_request_bytes": int(
            info.get("allocator_last_failure_request_bytes", 0)
        ),
        "fault_stage": int(info["fault_stage"]),
        "fault_status": int(info["fault_status"]),
        "dma_errors": int(info["dma_errors"]),
        "refill_irq_unpaired": int(info["refill_irq_unpaired"]),
        "refill_invalid_reserves": int(info["refill_invalid_reserves"]),
    }


def assert_identity(value: dict, device: str, revision: str, boot: str) -> None:
    info, wtp = value["info"], value["wtp"]
    require(
        info["device_id"] == device
        and info["revision"] == revision
        and info["deployment_identity_matches"] is True
        and info["network"]["deployment_identity_matches"] is True,
        "Exact deployment identity",
    )
    require(
        info["status"]["boot_id"]
        == wtp["HELLO"]["boot_id"]
        == wtp["STATUS"]["boot_id"]
        == boot,
        "Exact boot identity",
    )


def assert_inactive(value: dict) -> None:
    status = value["wtp"]["STATUS"]
    require(
        status["state"] == "empty"
        and status["owner_id"] is None
        and status["job_id"] is None
        and status["output_active"] is False,
        "Board must be empty, inactive, and unowned",
    )
    require(
        all(
            record.get("state") in ("complete", "aborted", "expired")
            and record.get("output_active") is False
            for record in status["terminal_records"]
        ),
        "Retained terminal records must be inactive",
    )
    require(
        value["info"]["status"]["enabled"] is False
        and value["info"]["status"]["output_active"] is False,
        "Schedules disabled and output inactive",
    )


def assert_accepted_a(value: dict, boot: str) -> None:
    assert_identity(value, DEVICE_A, SOURCE_A, boot)
    info = value["info"]
    require(
        info["recovery_boot"] is False
        and info["system_clock_hz"] == 138_000_000
        and info["rf_render_in_ram"] is True
        and info["status"]["engine"] == "pio-dma-gp2"
        and info["status"]["schedule_base_frequency_nhz"] == "135500000000000",
        "Accepted Pico A image and RF configuration",
    )
    assert_inactive(value)
    terminal = value["wtp"]["STATUS"]["terminal_records"]
    if boot == OLD_BOOT_A:
        require(
            terminal
            and terminal[0]
            == {
                "job_id": "e91341f781eed88966020f2a205a9c34",
                "state": "complete",
                "ended_monotonic_ns": "3840975862000",
                "output_active": False,
            },
            "Retained sequence-67 terminal breadcrumb",
        )
    else:
        require(terminal == [], "Fresh boot must clear volatile terminal records")


def assert_peer_b(value: dict) -> None:
    assert_identity(value, DEVICE_B, "8921a7008183", BOOT_B)
    assert_inactive(value)


def assert_released_reservation(path: Path) -> dict:
    reservation = json.loads(path.read_text())
    require(
        reservation.get("state") == "RELEASED"
        and reservation.get("host_boot") == HOST_BOOT
        and reservation.get("boards", {}).get("a")
        == {
            "boot_id": OLD_BOOT_A,
            "device_id": DEVICE_A,
            "revision": SOURCE_A,
            "state": "empty",
        }
        and reservation.get("boards", {}).get("b")
        == {
            "boot_id": BOOT_B,
            "device_id": DEVICE_B,
            "revision": "8921a7008183",
            "state": "empty",
        },
        "Released shared RF reservation at sequence 67",
    )
    return reservation


def issue_reboot(evidence: Path, pre_a: dict) -> dict:
    intent = {
        "schema": SCHEMA,
        "authorization": AUTHORIZATION,
        "target_serial": SERIAL_A,
        "target_device_id": DEVICE_A,
        "from_boot_id": OLD_BOOT_A,
        "pre_inventory_sha256": digest_bytes(canonical(pre_a)),
        "utc_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "maximum_commands": 1,
        "automatic_retries": 0,
    }
    save_new(evidence / "reboot-intent.json", intent)

    journal_path = evidence / "reboot-console.jsonl"
    sequence = 0
    with journal_path.open("x") as journal:
        def emit(kind: str, value: object) -> None:
            nonlocal sequence
            row = {
                "sequence": sequence,
                "kind": kind,
                "utc_ns": time.time_ns(),
                "monotonic_ns": time.monotonic_ns(),
                "value": value,
            }
            journal.write(json.dumps(row, separators=(",", ":")) + "\n")
            journal.flush()
            os.fsync(journal.fileno())
            sequence += 1

        base = Path(
            "/dev/serial/by-id/usb-WsprryPi_WsprryPico_" + SERIAL_A + "-if00"
        )
        with exclusive_port(base) as fd:
            info = exchange(fd, b"INFO\n", time.monotonic() + 5, emit, False)
            require(
                info["device_id"] == DEVICE_A
                and info["revision"] == SOURCE_A
                and info["status"]["boot_id"] == OLD_BOOT_A
                and info["status"]["state"] == "empty"
                and info["status"]["output_active"] is False,
                "Last-moment reboot target authority",
            )
            response = exchange(fd, b"REBOOT\n", time.monotonic() + 10, emit, False)
            require(response.get("ok") is True, "Controlled reboot acknowledgement")
            emit("reboot_acknowledged", response)
    return {
        "intent_sha256": digest_bytes((evidence / "reboot-intent.json").read_bytes()),
        "console_sha256": digest_bytes(journal_path.read_bytes()),
    }


def wait_post_inventory(tool_root: Path, evidence: Path) -> tuple[dict, Path]:
    deadline = time.monotonic() + 120
    attempt = 0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        attempt += 1
        try:
            value, path = run_inventory(
                tool_root, evidence, f"post-a-read-{attempt}", SERIAL_A, DEVICE_A
            )
            boot = value["wtp"]["STATUS"]["boot_id"]
            if boot != OLD_BOOT_A:
                return value, path
            last_error = ValueError("old boot still present")
        except (OSError, subprocess.SubprocessError, TimeoutError, ValueError) as error:
            last_error = error
        time.sleep(1)
    raise TimeoutError(f"Fresh post-reboot inventory unavailable: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool-root", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--reservation", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run requires the explicit controlled-reboot authorization")
    require(sys.platform.startswith("linux") and os.geteuid() == 0, "Linux root required")
    require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() == HOST_BOOT,
            "Exact wspr5 host boot")
    evidence = args.evidence_dir.resolve(strict=True)
    tool_root = args.tool_root.resolve(strict=True)
    reservation_path = args.reservation.resolve(strict=True)
    require(
        evidence.is_dir()
        and not evidence.is_symlink()
        and evidence.stat().st_mode & 0o077 == 0
        and not any(evidence.iterdir()),
        "Fresh private evidence directory",
    )
    os.umask(0o077)
    service = subprocess.run(
        ["systemctl", "is-active", "wsprrypi.service"],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    require(service.stdout.strip() == "inactive", "WsprryPi service must be inactive")
    reservation = assert_released_reservation(reservation_path)
    tools = tool_identity(tool_root)

    pre_a, pre_a_path = run_inventory(tool_root, evidence, "pre-a", SERIAL_A, DEVICE_A)
    pre_b, pre_b_path = run_inventory(tool_root, evidence, "pre-b", SERIAL_B, DEVICE_B)
    assert_accepted_a(pre_a, OLD_BOOT_A)
    assert_peer_b(pre_b)
    require(resource_counters(pre_a) == {
        **EXPECTED_PRE_FAILURES,
        "fault_stage": 0,
        "fault_status": 0,
        "dma_errors": 0,
        "refill_irq_unpaired": 0,
        "refill_invalid_reserves": 0,
    }, "Exact sequence-67 resource-failure checkpoint")

    reboot_evidence = issue_reboot(evidence, pre_a)
    post_a, post_a_path = wait_post_inventory(tool_root, evidence)
    post_b, post_b_path = run_inventory(tool_root, evidence, "post-b", SERIAL_B, DEVICE_B)
    new_boot = post_a["wtp"]["STATUS"]["boot_id"]
    require(new_boot != OLD_BOOT_A, "Pico A boot must change exactly once")
    assert_accepted_a(post_a, new_boot)
    assert_peer_b(post_b)
    require(
        retained_configuration(post_a) == retained_configuration(pre_a),
        "Retained Pico A configuration",
    )
    require(
        resource_counters(post_a) == {
            "allocator_failures": 0,
            "tls_allocation_failures": 0,
            "allocator_last_failure_request_bytes": 0,
            "fault_stage": 0,
            "fault_status": 0,
            "dma_errors": 0,
            "refill_irq_unpaired": 0,
            "refill_invalid_reserves": 0,
        },
        "Cleared resource and RF failure counters",
    )

    paths = [pre_a_path, pre_b_path, post_a_path, post_b_path]
    result = {
        "schema": SCHEMA,
        "status": "PASS",
        "authorization": AUTHORIZATION,
        "sequence_boundary": {"failed_sequence": 67, "next_sequence": 68,
                              "sequence_67_retried": False},
        "identity": {
            "serial": SERIAL_A,
            "device_id": DEVICE_A,
            "source_revision": SOURCE_A,
            "source_commit": SOURCE_A_FULL,
            "uf2_sha256": UF2_A_SHA256,
            "from_boot_id": OLD_BOOT_A,
            "to_boot_id": new_boot,
            "peer_serial": SERIAL_B,
            "peer_device_id": DEVICE_B,
            "peer_boot_id": BOOT_B,
        },
        "pre_resource_counters": resource_counters(pre_a),
        "post_resource_counters": resource_counters(post_a),
        "retained_configuration": retained_configuration(post_a),
        "reservation": {
            "state": reservation["state"],
            "packet_sha256": reservation["packet_sha256"],
            "sha256": digest_bytes(reservation_path.read_bytes()),
        },
        "evidence": {
            path.name: digest_bytes(path.read_bytes()) for path in paths
        } | reboot_evidence,
        "tool_sha256": tools,
        "accounting": {
            "controlled_reboots": 1,
            "automatic_retries": 0,
            "flashes": 0,
            "bootsel_transitions": 0,
            "configuration_writes": 0,
            "rf_jobs": 0,
            "rf_seconds": 0,
        },
    }
    save_new(evidence / "result.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
