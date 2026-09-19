#!/usr/bin/env python3
"""Explicitly reconcile one held Phase 11.6 reservation after a stopped attempt."""

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from phase11_5_rf_reservation import Reservation
from phase11_5_inventory import exchange, exclusive_port
from phase11_6.live import (
    FIRMWARE_SOURCE,
    HOSTNAME,
    PEER_SHA256,
    PORT,
    Journal,
    NetworkPeer,
    resource_gate,
    settled_inventory,
    tls_context,
)
from phase11_6.plan import (
    PEER_DEVICE_ID,
    PEER_SERIAL,
    PICO_ACCEPTED_BOOT,
    PICO_DEVICE_ID,
    PICO_SERIAL,
)


def authenticated_browser_status(root: Path, journal: Journal) -> dict:
    """Read authoritative job state when the WTP listener cannot admit HELLO."""
    connection = http.client.HTTPSConnection(
        HOSTNAME,
        PORT,
        timeout=8,
        context=tls_context(root, "browser", "http/1.1"),
    )
    try:
        connection.connect()
        certificate = connection.sock.getpeercert(binary_form=True)
        if hashlib.sha256(certificate).hexdigest() != PEER_SHA256:
            raise ValueError("Phase 11.6 browser-status peer identity")
        connection.request("GET", "/api/v1/status", headers={"Connection": "close"})
        response = connection.getresponse()
        raw = response.read(131_073)
        if response.status != 200 or len(raw) > 131_072:
            raise ValueError("Phase 11.6 browser-status response bounds")
        value = json.loads(raw)
        job = value.get("job") or {}
        if job.get("boot_id") != PICO_ACCEPTED_BOOT:
            raise ValueError("Phase 11.6 browser-status boot identity")
        journal.emit(
            "authenticated_browser_status",
            {
                "body_sha256": hashlib.sha256(raw).hexdigest(),
                "job": job,
                "transport": value.get("transport"),
            },
        )
        return job
    finally:
        connection.close()


def release_safe(status: dict, expected_job_id: str | None = None) -> bool:
    if status.get("owner_id") is not None or status.get("output_active") is not False:
        return False
    if status.get("state") == "empty":
        return status.get("job_id") is None
    terminals = [record for record in status.get("terminal_records", [])
                 if record.get("job_id") == expected_job_id]
    return (
        expected_job_id is not None
        and status.get("state") in {"complete", "aborted", "missed"}
        and status.get("job_id") == expected_job_id
        and len(terminals) == 1
        and terminals[0].get("state") == status.get("state")
        and terminals[0].get("output_active") is False
    )


def console_abort_eligible(status: dict, expected_job_id: str | None) -> bool:
    """Limit identity-free physical ABORT to the exact known active job."""
    return (
        expected_job_id is not None
        and status.get("boot_id") == PICO_ACCEPTED_BOOT
        and status.get("job_id") == expected_job_id
        and status.get("state") in {"loaded", "armed", "running"}
        and type(status.get("output_active")) is bool
    )


def console_state_abort_eligible(status: dict) -> bool:
    """Console INFO has no job id; admit only an identity-checked active state."""
    return (
        status.get("boot_id") == PICO_ACCEPTED_BOOT
        and status.get("state") in {"loaded", "armed", "running"}
        and type(status.get("output_active")) is bool
        and (status.get("state") == "running") is status.get("output_active")
    )


def console_abort_acknowledged(status: dict, expected_job_id: str) -> bool:
    """Validate Console ABORT; exact job identity is proved before and after it."""
    return (
        status.get("ok") is True
        and status.get("boot_id") == PICO_ACCEPTED_BOOT
        and ("job_id" not in status or status.get("job_id") == expected_job_id)
        and status.get("state") == "aborted"
        and status.get("output_active") is False
        and status.get("owner_id") is None
    )


def recovery_release_evidence(values: dict, transition: tuple[str, str],
                              fault_stage: int, fault_hash: int,
                              allocation_bytes: int) -> dict:
    """Admit only the exact inactive watchdog recovery observed after failure."""
    old_boot, new_boot = transition
    a = values.get("a") or {}
    info = a.get("info") or {}
    status = (a.get("wtp") or {}).get("STATUS") or {}
    hello = (a.get("wtp") or {}).get("HELLO") or {}
    network = info.get("network") or {}
    console_status = info.get("status") or {}
    if not (
        old_boot == PICO_ACCEPTED_BOOT
        and new_boot != old_boot
        and info.get("device_id") == PICO_DEVICE_ID
        and info.get("revision") == FIRMWARE_SOURCE[:12]
        and info.get("deployment_identity_matches") is True
        and info.get("recovery_boot") is True
        and info.get("fault_stage") == fault_stage
        and info.get("fault_hash") == fault_hash
        and info.get("fault_allocation_recorded") is True
        and info.get("fault_allocation_request_bytes") == allocation_bytes
        and info.get("fault_allocation_returned_null") is True
        and network.get("initialized") is False
        and network.get("control_listening") is False
        and console_status.get("boot_id") == new_boot
        and console_status.get("state") == "empty"
        and console_status.get("output_active") is False
        and console_status.get("enabled") is False
        and hello.get("boot_id") == new_boot
        and status.get("boot_id") == new_boot
        and status.get("state") == "empty"
        and status.get("job_id") is None
        and status.get("owner_id") is None
        and status.get("output_active") is False
    ):
        raise ValueError("Exact inactive Pico A recovery evidence required")
    return {
        "device_id": PICO_DEVICE_ID,
        "from_boot_id": old_boot,
        "to_boot_id": new_boot,
        "fault_stage": fault_stage,
        "fault_hash": fault_hash,
        "fault_allocation_request_bytes": allocation_bytes,
        "state": "empty",
        "output_active": False,
    }


def physical_console_abort(journal: Journal, expected_job_id: str,
                           authenticated_status: dict) -> dict:
    """Read identity, then issue exactly one physical ABORT if still required."""
    if not console_abort_eligible(authenticated_status, expected_job_id):
        raise ValueError("Authenticated status is not the exact authorized active job")
    path = Path(
        f"/dev/serial/by-id/usb-WsprryPi_WsprryPico_{PICO_SERIAL}-if00"
    )
    with exclusive_port(path) as descriptor:
        info = exchange(
            descriptor, b"INFO\n", time.monotonic() + 5,
            lambda kind, value: journal.emit("console_reconciliation_" + kind, value),
            False,
        )
        resource_gate(info, PICO_ACCEPTED_BOOT, FIRMWARE_SOURCE)
        before = info.get("status", {})
        if before.get("state") == "empty" and before.get("output_active") is False:
            journal.emit("console_abort_not_required", {"status": before})
            return {"sent": False, "before": before, "acknowledgement": None}
        if (before.get("job_id") == expected_job_id
                and before.get("state") in {"complete", "aborted", "missed"}
                and before.get("output_active") is False):
            journal.emit("console_abort_not_required", {"status": before})
            return {"sent": False, "before": before, "acknowledgement": None}
        if not console_state_abort_eligible(before):
            raise ValueError("Console status is not an identity-checked active state")
        acknowledgement = exchange(
            descriptor, b"ABORT\n", time.monotonic() + 5,
            lambda kind, value: journal.emit("console_reconciliation_" + kind, value),
            False,
        )
        if not console_abort_acknowledged(acknowledgement, expected_job_id):
            raise ValueError("Physical Console ABORT acknowledgement")
        value = {"sent": True, "expected_job_id": expected_job_id,
                 "authenticated_status": authenticated_status, "before": before,
                 "acknowledgement": acknowledgement}
        journal.emit("physical_console_abort", value)
        return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--request-number", type=int, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--expected-job-id")
    parser.add_argument("--authorize-console-abort", action="store_true")
    parser.add_argument("--authorized-a-recovery-boot",
                        help="Exact prior:new Pico A boot transition")
    parser.add_argument("--expected-recovery-fault-stage", type=int)
    parser.add_argument("--expected-recovery-fault-hash", type=int)
    parser.add_argument("--expected-recovery-allocation-bytes", type=int)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true", required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise ValueError("Linux root required")
    root = args.root.resolve(strict=True)
    args.output.mkdir(mode=0o700)
    journal = Journal(args.output / "reconciliation.jsonl")
    peer = NetworkPeer(root, journal, session=args.session,
                       request_number=args.request_number)
    try:
        recovery_fields = (
            args.authorized_a_recovery_boot,
            args.expected_recovery_fault_stage,
            args.expected_recovery_fault_hash,
            args.expected_recovery_allocation_bytes,
        )
        if any(value is not None for value in recovery_fields):
            if not all(value is not None for value in recovery_fields):
                raise ValueError("Complete recovery reconciliation authority required")
            parts = args.authorized_a_recovery_boot.split(":")
            if len(parts) != 2 or any(len(value) != 32 for value in parts):
                raise ValueError("Exact prior:new Pico A boot transition required")
            transition = (parts[0], parts[1])
            values = {
                "a": settled_inventory(
                    root, "phase116-reconcile-a-" + uuid.uuid4().hex,
                    PICO_SERIAL, PICO_DEVICE_ID, journal,
                ),
                "b": settled_inventory(
                    root, "phase116-reconcile-b-" + uuid.uuid4().hex,
                    PEER_SERIAL, PEER_DEVICE_ID, journal,
                ),
            }
            recovery = recovery_release_evidence(
                values, transition, args.expected_recovery_fault_stage,
                args.expected_recovery_fault_hash,
                args.expected_recovery_allocation_bytes,
            )
            before = after = values["a"]["wtp"]["STATUS"]
            authorized_boot_changes = {"a": transition}
            journal.emit("authorized_recovery_reconciliation", recovery)
        else:
            try:
                peer.connect()
                before = peer.ask("STATUS")
                if before.get("owner_id") is None and before.get("state") == "loaded":
                    peer.ask("CLAIM", {"owner_id": peer.session, "lease_ms": 60000})
                    peer.ask("RELEASE")
                elif before.get("owner_id") is not None:
                    peer.ask("RELEASE")
                after = peer.ask("STATUS")
                if (after.get("output_active") is not False
                        or after.get("owner_id") is not None):
                    raise ValueError("Pico A remains active or owned")
            except (ConnectionError, OSError, TimeoutError, ValueError) as error:
                peer.close()
                before = authenticated_browser_status(root, journal)
                if release_safe(before, args.expected_job_id):
                    after = before
                    journal.emit(
                        "wtp_reconciliation_fallback",
                        {"error_type": type(error).__name__, "release_safe": True},
                    )
                elif (args.authorize_console_abort
                      and console_abort_eligible(before, args.expected_job_id)):
                    physical_console_abort(
                        journal, args.expected_job_id, before
                    )
                    peer = NetworkPeer(root, journal, session=uuid.uuid4().hex,
                                       request_number=0)
                    peer.connect()
                    after = peer.ask("STATUS")
                    if not release_safe(after, args.expected_job_id):
                        raise ValueError("Post-abort WTP status is not release-safe")
                    journal.emit(
                        "wtp_reconciliation_fallback",
                        {"error_type": type(error).__name__, "release_safe": True,
                         "physical_console_abort": True},
                    )
                else:
                    raise ValueError(
                        "WTP unavailable and authenticated browser status is not release-safe"
                    ) from error
            values = {
                "a": settled_inventory(
                    root, "phase116-reconcile-a-" + uuid.uuid4().hex,
                    PICO_SERIAL, PICO_DEVICE_ID, journal,
                ),
                "b": settled_inventory(
                    root, "phase116-reconcile-b-" + uuid.uuid4().hex,
                    PEER_SERIAL, PEER_DEVICE_ID, journal,
                ),
            }
            authorized_boot_changes = None
        observed_ns = time.monotonic_ns()
        reservation = Reservation(args.packet_sha256,
            reconciliation=(values, observed_ns),
            authorized_boot_changes=authorized_boot_changes)
        try:
            reservation.release(values)
            state = json.loads(reservation.path.read_text())
            journal.emit("reservation_released", state)
        finally:
            reservation.close()
        result = {"status": "RECONCILED", "before": before, "after": after,
                  "recovery": recovery if authorized_boot_changes else None,
                  "reservation": state}
        with (args.output / "result.json").open("x") as stream:
            json.dump(result, stream, indent=2); stream.write("\n")
        return 0
    finally:
        peer.close(); journal.close()


if __name__ == "__main__":
    raise SystemExit(main())
