#!/usr/bin/env python3
"""Freeze Package 10 after its private inputs have been staged."""

import argparse
import hashlib
import json
from pathlib import Path
import time
import uuid

import phase11_5_package9 as package9
from phase11_5_package10 import (ADDRESS, AUTHORIZED_RF_DURATION_NS, BOOT, B_BOOT,
    B_DEVICE, B_SERIAL, CUMULATIVE_RF_DURATION_NS, CUMULATIVE_RF_JOBS, DEVICE,
    FIXTURE_AP_IF, FIXTURE_CLIENT_IF,
    HOSTNAME, HOST_BOOT, IMAGE, PEER_SHA, PRIOR_ATTEMPT_PACKET_SHA256,
    PRIOR_ATTEMPT_RESULT_SHA256, PRIOR_ATTEMPT_RF_DURATION_NS,
    PRIOR_ATTEMPT_RF_JOBS, RF_DURATION_NS, RF_JOBS, SERIAL, SOURCE,
    NETWORK_READINESS_SECONDS, NETWORK_ROUTE_SECONDS, NETWORK_SETTLE_SECONDS,
    NORMALIZER_CONNECT_TIMEOUT_SECONDS, NORMALIZER_RETRY_SECONDS,
    TLS_KEY_EXCHANGE_GROUP, WSPRRYPI_SOURCE, browser_actions, digest, refresh_jobs,
    warmup_jobs)


STAGED_INPUTS = (
    "scripts/phase11_5_package10.py", "scripts/phase11_5_package10_launch.py",
    "scripts/phase11_5_package9.py",
    "scripts/phase11_5_inventory.py", "scripts/phase11_5_rf_reservation.py",
    "scripts/phase11_5_tls_observer_decoder.py",
    "scripts/phase11_5_network_fixture.py", "scripts/validate_wtp_contract.py",
    "scripts/rf_wtp.py", "scripts/wtp_monitor.py", "scripts/phase11_5_pilot.py",
    "scripts/phase11_5_join_diagnostics.py", "scripts/phase11_5_time_local.py",
    "scripts/phase11_4_hotspot.py", "docs/protocol/wtp-1.schema.json",
    "production-base.ini", "production-openssl.cnf",
)


def production_openssl_config():
    return ("openssl_conf = openssl_init\n\n[openssl_init]\nssl_conf = ssl_sect\n\n"
            "[ssl_sect]\nsystem_default = system_default_sect\n\n"
            "[system_default_sect]\nGroups = X25519\n")


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
        raise ValueError("Fresh Package 10 packet required")
    retained = root / "retained-wifi.json"
    credentials = root / "credentials"
    if not retained.is_file() or not credentials.is_dir() or not (root / "production-base.ini").is_file():
        raise ValueError("Retained Wi-Fi, credentials and production base are required")
    seed = uuid.uuid4().hex
    openssl = root / "production-openssl.cnf"
    openssl.write_text(production_openssl_config())
    packet = {
        "schema": "phase11.5-package10-fixture-v2", "family": "R6",
        "authorization": "PACKAGE10-480-RF-SECONDS",
        "root": str(root), "source_revision": SOURCE, "image_sha256": IMAGE,
        "boot_id": BOOT, "serial": SERIAL, "device_id": DEVICE,
        "b_boot_id": B_BOOT, "b_serial": B_SERIAL, "b_device_id": B_DEVICE,
        "host_boot_id": HOST_BOOT, "wsprrypi_source_revision": WSPRRYPI_SOURCE,
        "binary": str(binary), "wsprrypi_binary_sha256": digest(binary),
        "observer": str(observer), "tls_observer_sha256": digest(observer),
        "address": ADDRESS, "hostname": HOSTNAME, "peer_sha256": PEER_SHA,
        "network_runtime_seconds": 5400, "network_restoration_seconds": 900,
        "network_fixture_roles": {"ap": FIXTURE_AP_IF, "client": FIXTURE_CLIENT_IF,
            "ap_mac": "2c:cf:67:62:76:66", "client_mac": "e8:4e:06:ae:d7:09"},
        "configuration_writes": 0, "controlled_reboots": 0, "flashes": 0,
        "bootsel": 0, "wifi_cycles": 0, "allocation_probes": 0,
        "authorized_max_flashes": 2, "authorized_max_bootsel": 2,
        "authorized_rf_duration_ns": AUTHORIZED_RF_DURATION_NS,
        "rf_jobs": RF_JOBS, "rf_duration_ns": RF_DURATION_NS,
        "cumulative_rf_jobs": CUMULATIVE_RF_JOBS,
        "cumulative_rf_duration_ns": CUMULATIVE_RF_DURATION_NS,
        "prior_attempt": {"packet_sha256": PRIOR_ATTEMPT_PACKET_SHA256,
            "result_sha256": PRIOR_ATTEMPT_RESULT_SHA256,
            "status": "STOPPED_PRE_GATE_SEQUENCE_MISMATCH",
            "charged_rf_jobs": PRIOR_ATTEMPT_RF_JOBS,
            "charged_rf_duration_ns": PRIOR_ATTEMPT_RF_DURATION_NS,
            "reservation_released": True, "fixture_restored": True},
        "memory_preflight": {
            "timeout_seconds": package9.MEMORY_PREFLIGHT_SECONDS,
            "sample_seconds": package9.MEMORY_PREFLIGHT_SAMPLE_SECONDS,
            "minimum_heap_available_bytes": package9.MINIMUM_PREFLIGHT_HEAP_AVAILABLE_BYTES,
            "minimum_inventory_heap_available_bytes":
                package9.MINIMUM_INVENTORY_HEAP_AVAILABLE_BYTES,
            "minimum_connected_heap_available_bytes":
                package9.MINIMUM_CONNECTED_HEAP_AVAILABLE_BYTES,
            "reason": "expire prior WTP state before installing matched replay classes",
        },
        "time_server_mdns": True, "time_server_dns": False,
        "retained_wifi_sha256": digest(retained),
        "credentials": {"controller": {"ca": "credentials/controller/client-ca.crt",
            "cert": "credentials/controller/client.crt", "key": "credentials/controller/client.key"},
            "browser": {"ca": "credentials/browser/client-ca.crt",
            "cert": "credentials/browser/client.crt", "key": "credentials/browser/client.key"}},
        "normalizer_seed": seed, "warmup_session": uuid.uuid4().hex,
        "warmup_owner": uuid.uuid4().hex, "refresh_session": uuid.uuid4().hex,
        "refresh_owner": uuid.uuid4().hex, "warmup_jobs": warmup_jobs(seed),
        "refresh_jobs": refresh_jobs(seed),
        "normalizer_request_timeout_seconds": package9.NORMALIZER_REQUEST_TIMEOUT_SECONDS,
        "normalizer_connect_timeout_seconds": NORMALIZER_CONNECT_TIMEOUT_SECONDS,
        "normalizer_retry_seconds": NORMALIZER_RETRY_SECONDS,
        "tls_key_exchange_group": TLS_KEY_EXCHANGE_GROUP,
        "production_openssl": openssl.name,
        "production_openssl_sha256": digest(openssl),
        "network_route_seconds": NETWORK_ROUTE_SECONDS,
        "network_settle_seconds": NETWORK_SETTLE_SECONDS,
        "network_readiness_seconds": NETWORK_READINESS_SECONDS,
        "readiness_sessions": [uuid.uuid4().hex for _ in range(4)],
        "normal_load": {"cycles": 3, "seconds_per_cycle": 600,
            "browser_intervals_per_cycle": 2, "browser_actions": browser_actions(),
            "production": {"mode": "FSKCW", "message": "?" * 32,
                "base_frequency_hz": 135500, "shift_hz": 5, "dot_seconds": 0.2,
                "event_count": 383, "duration_ns": 114_600_000_000,
                "start_offset_seconds": 90}},
        "quiet": {"baseline_seconds": 360, "interleaved_seconds": [306, 306, 306],
                  "final_seconds": 360, "minimum_measured_seconds": 3438},
        "terminal_history": {"capacity": 8, "warmup_production_class": 3,
            "warmup_maximum_class": 5, "production_jobs": 3,
            "refresh_maximum_class": 5, "final_production_class": 3,
            "final_maximum_class": 5, "resource_return_limit_bytes": 1024},
        "source_impact": {"deployed_source_revision": SOURCE,
            "repository_baseline_revision": "e22c86c83ceb161080c218748baf5d3eaa892652",
            "runtime_source_changes": 0,
            "decision": "measurement-only replay-history normalization"},
    }
    for name in ("before_a_session", "before_b_session", "final_a_session",
                 "final_b_session", "usb_observer_session_1",
                 "usb_observer_session_2", "usb_observer_session_3"):
        packet[name] = uuid.uuid4().hex
    packet["absolute_host_deadline_monotonic_ns"] = time.monotonic_ns() + 6600 * 1_000_000_000
    packet["stage_sha256"] = {name: digest(root / name) for name in STAGED_INPUTS}
    raw = (json.dumps(packet, indent=2) + "\n").encode()
    (root / "packet.json").write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    main()
