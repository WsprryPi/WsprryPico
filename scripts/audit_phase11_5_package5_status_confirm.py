#!/usr/bin/env python3
"""Audit the focused authenticated Package 5 GET status confirmation."""
import argparse
import json
from pathlib import Path

from phase11_5_inventory import require
from phase11_5_package5_http import digest
from phase11_5_package5_plan import BOOT, PEER
from phase11_5_package5_status_confirm import validate


def audit(root, expected):
    require(digest(root / "packet.json") == expected, "Frozen Package 5 status packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    raw = (root / "status.jsonl").read_text()
    require(raw.endswith("\n"), "Truncated Package 5 status trace")
    rows = [json.loads(line) for line in raw.splitlines()]
    require([row["sequence"] for row in rows] == list(range(len(rows))) and
            [row["kind"] for row in rows] == ["start", "status_tx", "status_response", "finish"] and
            rows[-1]["value"]["status"] == "CAPTURED_REQUIRES_AUDIT",
            "Package 5 status trace/result")
    request = bytes.fromhex(rows[1]["value"]["request_hex"])
    response = rows[2]["value"]
    body = json.loads(bytes.fromhex(response["body_hex"]))
    job = body["job"]
    require(request.startswith(b"GET /api/v1/status HTTP/1.1\r\n") and
            response["status"] == 200 and response["peer_sha256"] == PEER and
            rows[2]["monotonic_ns"] - rows[1]["monotonic_ns"] <= 15_000_000_000 and
            job["boot_id"] == BOOT and job["state"] == "empty" and
            job["output_active"] is False and job["owner_id"] is None and job["job_id"] is None,
            "Package 5 authenticated final status/authority")
    return dict(status="PACKAGE5_RETAINED_STATUS_CONFIRMATION_VERIFIED",
                packet_sha256=expected, retained_packet_sha256=packet["retained_packet_sha256"],
                boot_id=BOOT, state="empty", output_active=False, authenticated_peer_sha256=PEER)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256), indent=2))


if __name__ == "__main__":
    main()
