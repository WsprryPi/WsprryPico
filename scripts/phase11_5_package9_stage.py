#!/usr/bin/env python3
"""Freeze the Package 9 packet after its private inputs have been staged."""

import argparse
import hashlib
import json
from pathlib import Path
import time
import uuid

from phase11_5_package9 import (ADDRESS, BOOT, B_BOOT, B_DEVICE, B_SERIAL, DEVICE,
    HOSTNAME, HOST_BOOT, IMAGE, MEMORY_PREFLIGHT_SAMPLE_SECONDS,
    MEMORY_PREFLIGHT_SECONDS, MINIMUM_CONNECTED_HEAP_AVAILABLE_BYTES,
    MINIMUM_INVENTORY_HEAP_AVAILABLE_BYTES, MINIMUM_PREFLIGHT_HEAP_AVAILABLE_BYTES,
    NORMALIZER_REQUEST_TIMEOUT_SECONDS, PEER_SHA, RF_DURATION_NS, SERIAL, SOURCE,
    WSPRRYPI_SOURCE, browser_actions, digest, normalizer_jobs)


STAGED_INPUTS = (
    "scripts/phase11_5_package9.py", "scripts/phase11_5_inventory.py",
    "scripts/phase11_5_rf_reservation.py", "scripts/phase11_5_tls_observer_decoder.py",
    "scripts/phase11_5_network_fixture.py", "scripts/validate_wtp_contract.py",
    "scripts/rf_wtp.py", "scripts/wtp_monitor.py", "scripts/phase11_5_pilot.py",
    "scripts/phase11_5_join_diagnostics.py", "scripts/phase11_5_time_local.py",
    "scripts/phase11_4_hotspot.py", "docs/protocol/wtp-1.schema.json",
    "production-base.ini",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--observer", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    binary = args.binary.resolve(strict=True)
    observer = args.observer.resolve(strict=True)
    if (root / "packet.json").exists():
        raise ValueError("Fresh Package 9 packet required")
    retained = root / "retained-wifi.json"
    credentials = root / "credentials"
    if not retained.is_file() or not credentials.is_dir() or not (root / "production-base.ini").is_file():
        raise ValueError("Retained Wi-Fi, credentials and production base are required")
    seed = uuid.uuid4().hex
    packet = {
        "schema": "phase11.5-package9-fixture-v1", "family": "R6",
        "standing_authority": "PHASE11.5-COMPLETION-20260915",
        "root": str(root), "source_revision": SOURCE, "image_sha256": IMAGE,
        "boot_id": BOOT, "serial": SERIAL, "device_id": DEVICE,
        "b_boot_id": B_BOOT, "b_serial": B_SERIAL, "b_device_id": B_DEVICE,
        "host_boot_id": HOST_BOOT, "wsprrypi_source_revision": WSPRRYPI_SOURCE,
        "binary": str(binary), "wsprrypi_binary_sha256": digest(binary),
        "observer": str(observer), "tls_observer_sha256": digest(observer),
        "address": ADDRESS, "hostname": HOSTNAME, "peer_sha256": PEER_SHA,
        "network_runtime_seconds": 5400, "network_restoration_seconds": 900,
        "configuration_writes": 0, "controlled_reboots": 0, "flashes": 0,
        "bootsel": 0, "wifi_cycles": 0, "allocation_probes": 0,
        "rf_jobs": 11, "rf_duration_ns": RF_DURATION_NS,
        "memory_preflight": {
            "timeout_seconds": MEMORY_PREFLIGHT_SECONDS,
            "sample_seconds": MEMORY_PREFLIGHT_SAMPLE_SECONDS,
            "minimum_heap_available_bytes": MINIMUM_PREFLIGHT_HEAP_AVAILABLE_BYTES,
            "minimum_inventory_heap_available_bytes":
                MINIMUM_INVENTORY_HEAP_AVAILABLE_BYTES,
            "minimum_connected_heap_available_bytes":
                MINIMUM_CONNECTED_HEAP_AVAILABLE_BYTES,
            "reason": "expire retained WTP response/session memory before the maximum warm-up LOAD",
        },
        "time_server_mdns": True, "time_server_dns": False,
        "retained_wifi_sha256": digest(retained),
        "credentials": {"controller": {"ca": "credentials/controller/client-ca.crt",
            "cert": "credentials/controller/client.crt", "key": "credentials/controller/client.key"},
            "browser": {"ca": "credentials/browser/client-ca.crt",
            "cert": "credentials/browser/client.crt", "key": "credentials/browser/client.key"}},
        "normalizer_seed": seed, "normalizer_session": uuid.uuid4().hex,
        "normalizer_owner": uuid.uuid4().hex, "normalizer_jobs": normalizer_jobs(seed),
        "normalizer_request_timeout_seconds": NORMALIZER_REQUEST_TIMEOUT_SECONDS,
        "readiness_sessions": [uuid.uuid4().hex for _ in range(4)],
        "normal_load": {"cycles": 3, "seconds_per_cycle": 600,
            "browser_intervals_per_cycle": 2, "browser_actions": browser_actions(),
            "production": {"mode": "FSKCW", "message": "?" * 32,
                "base_frequency_hz": 135500, "shift_hz": 5, "dot_seconds": 0.2,
                "event_count": 383, "duration_ns": 114_600_000_000,
                "start_offset_seconds": 90}},
        "quiet": {"baseline_seconds": 360, "interleaved_seconds": [306, 306, 306],
                  "final_seconds": 360, "minimum_measured_seconds": 3438},
        "source_impact": {"deployed_source_revision": SOURCE,
            "current_repository_revision": SOURCE,
            "later_runtime_source_changes": 0},
    }
    for name in ("before_a_session", "before_b_session", "final_a_session",
                 "final_b_session", "usb_observer_session_1",
                 "usb_observer_session_2", "usb_observer_session_3"):
        packet[name] = uuid.uuid4().hex
    packet["absolute_host_deadline_monotonic_ns"] = time.monotonic_ns() + 6600 * 1_000_000_000
    packet["stage_sha256"] = {name: digest(root / name) for name in STAGED_INPUTS}
    raw = (json.dumps(packet, indent=2) + "\n").encode()
    path = root / "packet.json"
    path.write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    main()
