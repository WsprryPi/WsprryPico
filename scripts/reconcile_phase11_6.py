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
from phase11_6.live import (
    HOSTNAME,
    PEER_SHA256,
    PORT,
    Journal,
    NetworkPeer,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--request-number", type=int, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--expected-job-id")
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
        try:
            peer.connect()
            before = peer.ask("STATUS")
            if before.get("owner_id") is None and before.get("state") == "loaded":
                peer.ask("CLAIM", {"owner_id": peer.session, "lease_ms": 60000})
                peer.ask("RELEASE")
            elif before.get("owner_id") is not None:
                peer.ask("RELEASE")
            after = peer.ask("STATUS")
            if after.get("output_active") is not False or after.get("owner_id") is not None:
                raise ValueError("Pico A remains active or owned")
        except (ConnectionError, OSError, TimeoutError, ValueError) as error:
            peer.close()
            before = authenticated_browser_status(root, journal)
            if not release_safe(before, args.expected_job_id):
                raise ValueError(
                    "WTP unavailable and authenticated browser status is not release-safe"
                ) from error
            after = before
            journal.emit(
                "wtp_reconciliation_fallback",
                {"error_type": type(error).__name__, "release_safe": True},
            )
        values = {
            "a": settled_inventory(root, "phase116-reconcile-a-" + uuid.uuid4().hex,
                                   PICO_SERIAL, PICO_DEVICE_ID, journal),
            "b": settled_inventory(root, "phase116-reconcile-b-" + uuid.uuid4().hex,
                                   PEER_SERIAL, PEER_DEVICE_ID, journal),
        }
        observed_ns = time.monotonic_ns()
        reservation = Reservation(args.packet_sha256,
            reconciliation=(values, observed_ns))
        try:
            reservation.release(values)
            state = json.loads(reservation.path.read_text())
            journal.emit("reservation_released", state)
        finally:
            reservation.close()
        result = {"status": "RECONCILED", "before": before, "after": after,
                  "reservation": state}
        with (args.output / "result.json").open("x") as stream:
            json.dump(result, stream, indent=2); stream.write("\n")
        return 0
    finally:
        peer.close(); journal.close()


if __name__ == "__main__":
    raise SystemExit(main())
