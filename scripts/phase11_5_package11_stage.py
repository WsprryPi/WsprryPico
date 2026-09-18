#!/usr/bin/env python3
"""Freeze a Package 11 admission or corrected-campaign packet on wspr5."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import time
import uuid

import phase11_5_package9 as package9
import phase11_5_package10 as package10
import phase11_5_package11 as package11
from audit_phase11_5_package11_retry1_failure import validate_result as validate_retry1
from audit_phase11_5_package11_retry2_failure import validate_result as validate_retry2
from audit_phase11_5_package11_retry3_failure import validate_result as validate_retry3
from audit_phase11_5_package11_usb_reducer_retest import (
    validate_result as validate_usb_reducer_retest)
from phase11_5_package10_stage import production_openssl_config
from phase11_5_package11_admission import (INTERVAL_SECONDS, OBSERVATION_SECONDS, SAMPLES,
    PICO_TIME_READINESS_SECONDS, STATUS_READINESS_SECONDS)


COMMON_INPUTS = (
    "scripts/phase11_5_package11.py", "scripts/phase11_5_package11_stage.py",
    "scripts/phase11_5_package11_admission.py",
    "scripts/phase11_5_package11_clock_poll_retest.py",
    "scripts/phase11_5_package11_launch.py", "scripts/phase11_5_package11_fixture.py",
    "scripts/phase11_5_package11_remote_ap.py",
    "scripts/phase11_5_package11_remote_stage.py",
    "scripts/audit_phase11_5_package11_admission.py",
    "scripts/adversarial_phase11_5_package11_admission.py",
    "scripts/audit_phase11_5_package11.py",
    "scripts/adversarial_phase11_5_package11.py",
    "scripts/audit_phase11_5_package11_retry1_failure.py",
    "scripts/adversarial_phase11_5_package11_retry1_failure.py",
    "scripts/audit_phase11_5_package11_retry2_failure.py",
    "scripts/adversarial_phase11_5_package11_retry2_failure.py",
    "scripts/audit_phase11_5_package11_retry3_failure.py",
    "scripts/adversarial_phase11_5_package11_retry3_failure.py",
    "scripts/phase11_5_package11_usb_reducer_retest.py",
    "scripts/audit_phase11_5_package11_usb_reducer_retest.py",
    "scripts/adversarial_phase11_5_package11_usb_reducer_retest.py",
    "scripts/phase11_5_package10.py", "scripts/phase11_5_package9.py",
    "scripts/phase11_5_inventory.py", "scripts/phase11_5_rf_reservation.py",
    "scripts/phase11_5_tls_observer_decoder.py", "scripts/validate_wtp_contract.py",
    "scripts/rf_wtp.py", "scripts/wtp_monitor.py", "scripts/phase11_5_pilot.py",
    "scripts/phase11_5_time_local.py", "scripts/phase11_4_hotspot.py",
    "docs/protocol/wtp-1.schema.json", "production-base.ini",
    "production-openssl.cnf")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def credential_digest(root, relative):
    """Hash one staged credential without following file or parent symlinks."""
    root = root.resolve(strict=True)
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Credential path must remain below the fixture root")
    parent = root
    for part in relative.parts[:-1]:
        parent /= part
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise ValueError("Credential parent must be a real directory")
    path = root / relative
    before = path.lstat()
    if not (stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and
            before.st_size > 0):
        raise ValueError("Credential must be one nonempty regular file")
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("Credential changed during secure open")
        hasher = hashlib.sha256()
        while True:
            block = os.read(fd, 65536)
            if not block:
                return hasher.hexdigest()
            hasher.update(block)
    finally:
        os.close(fd)


def canonical_wifi(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def identities(packet):
    packet.update({"source_revision": package10.SOURCE, "image_sha256": package10.IMAGE,
        "boot_id": package10.BOOT, "serial": package10.SERIAL,
        "device_id": package10.DEVICE, "b_boot_id": package10.B_BOOT,
        "b_serial": package10.B_SERIAL, "b_device_id": package10.B_DEVICE,
        "host_boot_id": package10.HOST_BOOT,
        "wsprrypi_source_revision": package10.WSPRRYPI_SOURCE,
        "address": package10.ADDRESS, "hostname": package10.HOSTNAME,
        "peer_sha256": package10.PEER_SHA})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--kind", choices=("admission", "campaign"), required=True)
    parser.add_argument("--binary", type=Path, default=Path("/usr/local/bin/wsprrypi"))
    parser.add_argument("--observer", type=Path)
    parser.add_argument("--admission-result", type=Path)
    parser.add_argument("--admission-adversarial", type=Path)
    parser.add_argument("--prior-attempt-result", type=Path)
    parser.add_argument("--clock-poll-retest-result", type=Path)
    parser.add_argument("--retry1-result", type=Path)
    parser.add_argument("--retry1-adversarial", type=Path)
    parser.add_argument("--credential-retest-result", type=Path)
    parser.add_argument("--retry2-result", type=Path)
    parser.add_argument("--retry2-adversarial", type=Path)
    parser.add_argument("--retry3-result", type=Path)
    parser.add_argument("--retry3-adversarial", type=Path)
    parser.add_argument("--usb-reducer-retest-result", type=Path)
    parser.add_argument("--usb-reducer-retest-adversarial", type=Path)
    parser.add_argument("--retry4-credential-retest-result", type=Path)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    if (root / "packet.json").exists():
        raise ValueError("Fresh Package 11 packet required")
    retained = root / "retained-wifi.json"
    credentials = root / "credentials"
    remote_ready_path = root / "remote-ready.json"
    if not retained.is_file() or not credentials.is_dir() or not remote_ready_path.is_file():
        raise ValueError("Retained Wi-Fi, credentials and remote readiness are required")
    wifi = json.loads(retained.read_text())
    wifi_hash = hashlib.sha256(canonical_wifi(wifi)).hexdigest()
    remote_ready = json.loads(remote_ready_path.read_text())
    if remote_ready.get("wifi_sha256") != wifi_hash:
        raise ValueError("Remote AP Wi-Fi differs from local retained input")
    binary = args.binary.resolve(strict=True)
    observer = (args.observer or (root / "observer.so")).resolve(strict=True)
    openssl = root / "production-openssl.cnf"
    openssl.write_text(production_openssl_config())
    schema = ("phase11.5-package11-admission-v1" if args.kind == "admission" else
              "phase11.5-package11-fixture-v1")
    packet = {"schema": schema, "family": "R6",
        "authorization": (package11.AUTHORIZATION if args.kind == "admission" else
                          package11.RETRY4_AUTHORIZATION), "root": str(root),
        "wifi": wifi, "retained_wifi_sha256": digest(retained),
        "retained_wifi_canonical_sha256": wifi_hash,
        "remote_ready": remote_ready, "client_if": package11.CLIENT_IF,
        "client_mac": package11.CLIENT_MAC, "remote_ap_mac": package11.REMOTE_AP_MAC,
        "client_address": "10.77.15.2",
        "time_authority_address": package11.TIME_ADDRESS,
        "network_fixture_roles": {"ap_host": "wspr4", "ap": "wlan1",
            "ap_mac": package11.REMOTE_AP_MAC, "client_host": "wspr5",
            "client": package11.CLIENT_IF, "client_mac": package11.CLIENT_MAC},
        "network_runtime_seconds": 1200 if args.kind == "admission" else 5400,
        "network_restoration_seconds": 900,
        "configuration_writes": 0, "controlled_reboots": 0, "flashes": 0,
        "bootsel": 0, "wifi_cycles": 0, "allocation_probes": 0,
        "rf_jobs": 0 if args.kind == "admission" else package10.RF_JOBS,
        "rf_duration_ns": 0 if args.kind == "admission" else package10.RF_DURATION_NS,
        "credentials": {"controller": {"ca": "credentials/controller/client-ca.crt",
            "cert": "credentials/controller/client.crt",
            "key": "credentials/controller/client.key"},
            "browser": {"ca": "credentials/browser/client-ca.crt",
            "cert": "credentials/browser/client.crt",
            "key": "credentials/browser/client.key"}},
        "tls_key_exchange_group": package10.TLS_KEY_EXCHANGE_GROUP,
        "normalizer_request_timeout_seconds": package9.NORMALIZER_REQUEST_TIMEOUT_SECONDS,
        "normalizer_connect_timeout_seconds": package10.NORMALIZER_CONNECT_TIMEOUT_SECONDS,
        "normalizer_retry_seconds": package10.NORMALIZER_RETRY_SECONDS,
        "binary": str(binary), "wsprrypi_binary_sha256": digest(binary),
        "observer": str(observer), "tls_observer_sha256": digest(observer),
        "production_openssl": openssl.name,
        "production_openssl_sha256": digest(openssl)}
    credential_paths = tuple(packet["credentials"][role][kind]
                             for role in ("controller", "browser")
                             for kind in ("ca", "cert", "key"))
    packet["credential_sha256"] = {name: credential_digest(root, name)
                                    for name in credential_paths}
    identities(packet)
    if args.kind == "admission":
        packet.update({"admission_only": True, "observation_seconds": OBSERVATION_SECONDS,
            "sample_count": SAMPLES, "sample_interval_seconds": INTERVAL_SECONDS,
            "status_readiness_seconds": STATUS_READINESS_SECONDS,
            "pico_time_readiness_seconds": PICO_TIME_READINESS_SECONDS,
            "readiness_sessions": [uuid.uuid4().hex for _ in range(SAMPLES)],
            "before_a_session": uuid.uuid4().hex, "before_b_session": uuid.uuid4().hex,
            "final_a_session": uuid.uuid4().hex, "final_b_session": uuid.uuid4().hex})
    else:
        if any(value is None for value in (args.admission_result,
                args.admission_adversarial, args.prior_attempt_result,
                args.clock_poll_retest_result, args.retry1_result,
                args.retry1_adversarial, args.credential_retest_result,
                args.retry2_result, args.retry2_adversarial, args.retry3_result,
                args.retry3_adversarial, args.usb_reducer_retest_result,
                args.usb_reducer_retest_adversarial,
                args.retry4_credential_retest_result)):
            raise ValueError("Admission, stopped-attempt and clock-retest results are required")
        admission_result = args.admission_result.resolve(strict=True)
        admission_adversarial = args.admission_adversarial.resolve(strict=True)
        prior_attempt_result = args.prior_attempt_result.resolve(strict=True)
        clock_poll_retest_result = args.clock_poll_retest_result.resolve(strict=True)
        retry1_result = args.retry1_result.resolve(strict=True)
        retry1_adversarial = args.retry1_adversarial.resolve(strict=True)
        credential_retest_result = args.credential_retest_result.resolve(strict=True)
        retry2_result = args.retry2_result.resolve(strict=True)
        retry2_adversarial = args.retry2_adversarial.resolve(strict=True)
        retry3_result = args.retry3_result.resolve(strict=True)
        retry3_adversarial = args.retry3_adversarial.resolve(strict=True)
        usb_reducer_retest_result = args.usb_reducer_retest_result.resolve(strict=True)
        usb_reducer_retest_adversarial = args.usb_reducer_retest_adversarial.resolve(
            strict=True)
        retry4_credential_retest_result = args.retry4_credential_retest_result.resolve(
            strict=True)
        admission_value = json.loads(admission_result.read_text())
        adversarial_value = json.loads(admission_adversarial.read_text())
        prior_value = json.loads(prior_attempt_result.read_text())
        clock_value = json.loads(clock_poll_retest_result.read_text())
        retry1_value = json.loads(retry1_result.read_text())
        retry1_adversarial_value = json.loads(retry1_adversarial.read_text())
        credential_retest_value = json.loads(credential_retest_result.read_text())
        retry2_value = json.loads(retry2_result.read_text())
        retry2_adversarial_value = json.loads(retry2_adversarial.read_text())
        retry3_value = json.loads(retry3_result.read_text())
        retry3_adversarial_value = json.loads(retry3_adversarial.read_text())
        usb_reducer_retest_value = json.loads(usb_reducer_retest_result.read_text())
        usb_reducer_retest_adversarial_value = json.loads(
            usb_reducer_retest_adversarial.read_text())
        retry4_credential_retest_value = json.loads(
            retry4_credential_retest_result.read_text())
        if (digest(admission_result) != package11.ADMISSION_RESULT_SHA256 or
                digest(admission_adversarial) !=
                    package11.ADMISSION_ADVERSARIAL_SHA256 or
                digest(prior_attempt_result) != package11.ATTEMPT1_RESULT_SHA256 or
                digest(clock_poll_retest_result) !=
                    package11.CLOCK_POLL_RETEST_RESULT_SHA256 or
                digest(retry1_result) != package11.RETRY1_RESULT_SHA256 or
                digest(retry1_adversarial) != package11.RETRY1_ADVERSARIAL_SHA256 or
                digest(credential_retest_result) !=
                    package11.CREDENTIAL_RETEST_RESULT_SHA256 or
                digest(retry2_result) != package11.RETRY2_RESULT_SHA256 or
                digest(retry2_adversarial) != package11.RETRY2_ADVERSARIAL_SHA256 or
                digest(retry3_result) != package11.RETRY3_RESULT_SHA256 or
                digest(retry3_adversarial) != package11.RETRY3_ADVERSARIAL_SHA256 or
                digest(usb_reducer_retest_result) !=
                    package11.USB_REDUCER_RETEST_RESULT_SHA256 or
                digest(usb_reducer_retest_adversarial) !=
                    package11.USB_REDUCER_RETEST_ADVERSARIAL_SHA256 or
                digest(retry4_credential_retest_result) !=
                    package11.RETRY4_CREDENTIAL_RETEST_RESULT_SHA256):
            raise ValueError("Package 11 retry dependency hash changed")
        if (admission_value.get("status") != "PASS_ZERO_RF" or
                admission_value.get("schema") !=
                    "phase11.5-package11-admission-result-v1" or
                adversarial_value.get("schema") !=
                    "phase11.5-package11-admission-adversarial-v1" or
                adversarial_value.get("status") != "PASS" or
                adversarial_value.get("all_mutations_rejected") is not True or
                adversarial_value.get("admission_result_sha256") !=
                    digest(admission_result)):
            raise ValueError("Package 11 admission did not pass")
        if (prior_value.get("schema") != "phase11.5-package11-attempt-failure-v1" or
                prior_value.get("status") != "STOPPED_PRE_CYCLE_CLOCK_POLL_ALIAS" or
                prior_value.get("packet_sha256") != package11.ATTEMPT1_PACKET_SHA256 or
                prior_value.get("actual_budget", {}).get("charged_rf_jobs") !=
                    package11.ATTEMPT1_RF_JOBS or
                prior_value.get("actual_budget", {}).get("charged_rf_duration_ns") !=
                    package11.ATTEMPT1_RF_DURATION_NS or
                prior_value.get("completed_scope", {}).get("r6_credit") is not False or
                prior_value.get("failure", {}).get("product_failure") is not False or
                prior_value.get("failure", {}).get("resource_result_accepted") is not False or
                prior_value.get("actual_budget", {}).get(
                    "automatic_retry_authorized") is not False or
                prior_value.get("restoration", {}).get(
                    "reservation_released_after_fresh_reconciliation") is not True or
                prior_value.get("restoration", {}).get(
                    "wspr5_fixture_restored") is not True or
                prior_value.get("restoration", {}).get(
                    "wspr4_fixture_restored") is not True):
            raise ValueError("Package 11 prior attempt is not safely accounted")
        if (clock_value.get("schema") !=
                "phase11.5-package11-clock-poll-retest-result-v1" or
                clock_value.get("status") != "PASS_ZERO_RF" or
                clock_value.get("budget", {}).get("rf_jobs") != 0 or
                clock_value.get("budget", {}).get("rf_duration_ns") != 0 or
                clock_value.get("finding", {}).get(
                    "transport_backoff_separated_from_healthy_stale_clock_polling") is not True or
                clock_value.get("finding", {}).get(
                    "fresh_pico_clock_window_observed") is not True or
                clock_value.get("restoration", {}).get(
                    "reservation_released_unchanged") is not True or
                clock_value.get("restoration", {}).get("wspr5_fixture_restored") is not True or
                clock_value.get("restoration", {}).get("wspr4_fixture_restored") is not True):
            raise ValueError("Package 11 clock-poll repair did not pass zero-RF retest")
        validate_retry1(retry1_value)
        if (retry1_adversarial_value.get("schema") !=
                "phase11.5-package11-retry1-adversarial-v1" or
                retry1_adversarial_value.get("status") != "PASS" or
                retry1_adversarial_value.get("all_mutations_rejected") is not True or
                retry1_adversarial_value.get("mutation_count", 0) < 1 or
                retry1_adversarial_value.get("result_sha256") != digest(retry1_result)):
            raise ValueError("Package 11 Retry 1 failure review did not pass")
        if (credential_retest_value.get("schema") !=
                "phase11.5-package11-credential-retest-v1" or
                credential_retest_value.get("status") != "PASS_ZERO_RF_HOST_ONLY" or
                credential_retest_value.get("files") != 6 or
                credential_retest_value.get("before_owner_uid") != 1000 or
                credential_retest_value.get("after_owner_uid") != 0 or
                credential_retest_value.get("mode") != "0600" or
                credential_retest_value.get("content_hashes_unchanged") is not True or
                credential_retest_value.get("fixture_source_sha256") !=
                    "fc3ea5e7ff8f4e8c3baa2573218ded881357198159f08482a42a1b2343581fdc" or
                any(credential_retest_value.get(name) not in (0, False) for name in
                    ("rf_jobs", "rf_duration_ns", "pico_access", "usb_access",
                     "network_mutations", "service_mutations", "reservation_access"))):
            raise ValueError("Package 11 credential repair did not pass host-only retest")
        validate_retry2(retry2_value)
        if (retry2_adversarial_value.get("schema") !=
                "phase11.5-package11-retry2-adversarial-v1" or
                retry2_adversarial_value.get("status") != "PASS" or
                retry2_adversarial_value.get("all_mutations_rejected") is not True or
                retry2_adversarial_value.get("mutation_count", 0) < 1 or
                retry2_adversarial_value.get("result_sha256") != digest(retry2_result)):
            raise ValueError("Package 11 Retry 2 failure review did not pass")
        validate_retry3(retry3_value)
        if (retry3_adversarial_value.get("schema") !=
                "phase11.5-package11-retry3-adversarial-v1" or
                retry3_adversarial_value.get("status") != "PASS" or
                retry3_adversarial_value.get("all_mutations_rejected") is not True or
                retry3_adversarial_value.get("mutation_count") != 35 or
                retry3_adversarial_value.get("result_sha256") != digest(retry3_result)):
            raise ValueError("Package 11 Retry 3 failure review did not pass")
        validate_usb_reducer_retest(usb_reducer_retest_value)
        if (usb_reducer_retest_adversarial_value.get("schema") !=
                "phase11.5-package11-retry3-usb-reducer-adversarial-v1" or
                usb_reducer_retest_adversarial_value.get("status") != "PASS" or
                usb_reducer_retest_adversarial_value.get(
                    "all_mutations_rejected") is not True or
                usb_reducer_retest_adversarial_value.get("mutation_count") != 22 or
                usb_reducer_retest_adversarial_value.get("result_sha256") !=
                    digest(usb_reducer_retest_result) or
                usb_reducer_retest_value.get("source_sha256", {}).get(
                    "phase11_5_package9.py") != digest(
                        Path(__file__).with_name("phase11_5_package9.py"))):
            raise ValueError("Package 11 USB reducer repair did not pass")
        if (retry4_credential_retest_value.get("schema") !=
                "phase11.5-package11-retry4-credential-retest-v1" or
                retry4_credential_retest_value.get("status") !=
                    "PASS_ZERO_RF_HOST_ONLY" or
                retry4_credential_retest_value.get("host") != "wspr5" or
                retry4_credential_retest_value.get("host_boot_id") !=
                    package10.HOST_BOOT or
                retry4_credential_retest_value.get("files") != 6 or
                retry4_credential_retest_value.get("before_owner_uid") != 1000 or
                retry4_credential_retest_value.get("after_owner_uid") != 0 or
                retry4_credential_retest_value.get("mode") != "0600" or
                retry4_credential_retest_value.get(
                    "content_hashes_unchanged") is not True or
                retry4_credential_retest_value.get("fixture_source_sha256") != digest(
                    Path(__file__).with_name("phase11_5_package11_fixture.py")) or
                any(retry4_credential_retest_value.get(name) not in (0, False)
                    for name in ("rf_jobs", "rf_duration_ns", "pico_access",
                                 "usb_access", "network_mutations", "service_mutations",
                                 "reservation_access"))):
            raise ValueError("Package 11 Retry 4 credential retest did not pass")
        seed = uuid.uuid4().hex
        packet.update({"authorized_rf_duration_ns": package11.AUTHORIZED_RF_DURATION_NS,
            "authorized_max_flashes": 0, "authorized_max_bootsel": 0,
            "historical_package10": {"charged_rf_jobs": 4,
                "charged_rf_duration_ns": 4_000_000_000,
                "status": "FIXTURE_BLOCKED_AFTER_STOPPED_ATTEMPT"},
            "admission_result_sha256": digest(admission_result),
            "admission_adversarial_sha256": digest(admission_adversarial),
            "admission": {"status": "PASS_ZERO_RF",
                "result_sha256": digest(admission_result),
                "adversarial_sha256": digest(admission_adversarial),
                "fixture_restored": True, "rf_jobs": 0, "rf_duration_ns": 0},
            "prior_attempt_result_sha256": digest(prior_attempt_result),
            "prior_package11_attempt": {
                "packet_sha256": package11.ATTEMPT1_PACKET_SHA256,
                "result_sha256": digest(prior_attempt_result),
                "status": "STOPPED_PRE_CYCLE_CLOCK_POLL_ALIAS",
                "charged_rf_jobs": package11.ATTEMPT1_RF_JOBS,
                "charged_rf_duration_ns": package11.ATTEMPT1_RF_DURATION_NS,
                "resource_result_accepted": False,
                "reservation_released": True, "fixture_restored": True},
            "clock_poll_retest_result_sha256": digest(clock_poll_retest_result),
            "clock_poll_retest": {"status": "PASS_ZERO_RF",
                "result_sha256": digest(clock_poll_retest_result),
                "rf_jobs": 0, "rf_duration_ns": 0,
                "reservation_unchanged": True, "fixture_restored": True},
            "retry1_attempt_result_sha256": digest(retry1_result),
            "retry1_adversarial_sha256": digest(retry1_adversarial),
            "retry1_package11_attempt": {
                "packet_sha256": package11.RETRY1_PACKET_SHA256,
                "result_sha256": digest(retry1_result),
                "adversarial_sha256": digest(retry1_adversarial),
                "status": "STOPPED_PRE_ARM_WSPRRYPI_TLS_CREDENTIAL_OWNER",
                "charged_rf_jobs": package11.RETRY1_RF_JOBS,
                "charged_rf_duration_ns": package11.RETRY1_RF_DURATION_NS,
                "production_jobs_armed": 0, "resource_result_accepted": False,
                "reservation_released": True, "fixture_restored": True},
            "credential_retest_result_sha256": digest(credential_retest_result),
            "credential_retest": {"status": "PASS_ZERO_RF_HOST_ONLY",
                "result_sha256": digest(credential_retest_result), "files": 6,
                "fixture_source_sha256": credential_retest_value[
                    "fixture_source_sha256"],
                "before_owner_uid": 1000, "after_owner_uid": 0, "mode": "0600",
                "content_hashes_unchanged": True, "rf_jobs": 0,
                "rf_duration_ns": 0, "pico_access": False, "usb_access": False,
                "network_mutations": 0, "service_mutations": 0,
                "reservation_access": False},
            "retry2_attempt_result_sha256": digest(retry2_result),
            "retry2_adversarial_sha256": digest(retry2_adversarial),
            "retry2_package11_attempt": {
                "packet_sha256": package11.RETRY2_PACKET_SHA256,
                "result_sha256": digest(retry2_result),
                "adversarial_sha256": digest(retry2_adversarial),
                "status": "STOPPED_PRE_RESERVATION_MEMORY_RETENTION_WINDOW",
                "charged_rf_jobs": package11.RETRY2_RF_JOBS,
                "charged_rf_duration_ns": package11.RETRY2_RF_DURATION_NS,
                "reservation_acquired": False, "resource_result_accepted": False,
                "reservation_released": True, "fixture_restored": True},
            "retry3_attempt_result_sha256": digest(retry3_result),
            "retry3_adversarial_sha256": digest(retry3_adversarial),
            "retry3_package11_attempt": {
                "packet_sha256": package11.RETRY3_PACKET_SHA256,
                "result_sha256": digest(retry3_result),
                "adversarial_sha256": digest(retry3_adversarial),
                "status": "STOPPED_AFTER_CYCLE1_USB_EVENT_REDUCTION",
                "charged_rf_jobs": package11.RETRY3_RF_JOBS,
                "charged_rf_duration_ns": package11.RETRY3_RF_DURATION_NS,
                "production_jobs": 1, "normal_cycles": 1, "post_n_windows": 0,
                "resource_result_accepted": False,
                "reservation_released": True, "fixture_restored": True},
            "usb_reducer_retest_result_sha256": digest(usb_reducer_retest_result),
            "usb_reducer_retest_adversarial_sha256": digest(
                usb_reducer_retest_adversarial),
            "usb_reducer_retest": {"status": "PASS_ZERO_RF_HOST_ONLY",
                "result_sha256": digest(usb_reducer_retest_result),
                "adversarial_sha256": digest(usb_reducer_retest_adversarial),
                "phase11_5_package9_source_sha256":
                    usb_reducer_retest_value["source_sha256"]["phase11_5_package9.py"],
                "repaired_event_and_status_reducer_accepts": True,
                "mutations_rejected": 22, "rf_jobs": 0, "rf_duration_ns": 0,
                "pico_access": False, "usb_access": False, "network_access": False,
                "service_mutations": 0, "reservation_access": False},
            "retry4_credential_retest_result_sha256": digest(
                retry4_credential_retest_result),
            "retry4_credential_retest": {"status": "PASS_ZERO_RF_HOST_ONLY",
                "result_sha256": digest(retry4_credential_retest_result), "files": 6,
                "fixture_source_sha256": retry4_credential_retest_value[
                    "fixture_source_sha256"],
                "before_owner_uid": 1000, "after_owner_uid": 0, "mode": "0600",
                "content_hashes_unchanged": True, "rf_jobs": 0,
                "rf_duration_ns": 0, "pico_access": False, "usb_access": False,
                "network_mutations": 0, "service_mutations": 0,
                "reservation_access": False},
            "cumulative_package11_rf_jobs": package11.CUMULATIVE_RF_JOBS,
            "cumulative_package11_rf_duration_ns":
                package11.CUMULATIVE_RF_DURATION_NS,
            "normalizer_seed": seed, "warmup_session": uuid.uuid4().hex,
            "warmup_owner": uuid.uuid4().hex, "refresh_session": uuid.uuid4().hex,
            "refresh_owner": uuid.uuid4().hex,
            "warmup_jobs": package10.warmup_jobs(seed),
            "refresh_jobs": package10.refresh_jobs(seed),
            "readiness_sessions": [uuid.uuid4().hex for _ in range(4)],
            "terminal_retention_preflight": {
                "timeout_seconds": package11.TERMINAL_RETENTION_WAIT_SECONDS,
                "sample_seconds": package11.TERMINAL_RETENTION_SAMPLE_SECONDS,
                "terminal_record_ttl_seconds": 3600,
                "maximum_terminal_records": 8,
                "sessions": [uuid.uuid4().hex for _ in range(
                    package11.TERMINAL_RETENTION_SESSIONS)]},
            "memory_preflight": {"timeout_seconds": package9.MEMORY_PREFLIGHT_SECONDS,
                "sample_seconds": package9.MEMORY_PREFLIGHT_SAMPLE_SECONDS,
                "minimum_heap_available_bytes": package9.MINIMUM_PREFLIGHT_HEAP_AVAILABLE_BYTES,
                "minimum_inventory_heap_available_bytes":
                    package9.MINIMUM_INVENTORY_HEAP_AVAILABLE_BYTES,
                "minimum_connected_heap_available_bytes":
                    package9.MINIMUM_CONNECTED_HEAP_AVAILABLE_BYTES,
                "reason": "expire prior WTP state before installing matched replay classes"},
            "network_route_seconds": package10.NETWORK_ROUTE_SECONDS,
            "network_settle_seconds": package10.NETWORK_SETTLE_SECONDS,
            "network_readiness_seconds": package10.NETWORK_READINESS_SECONDS,
            "normal_load": {"cycles": 3, "seconds_per_cycle": package9.NORMAL_SECONDS,
                "browser_intervals_per_cycle": 2,
                "browser_actions": package10.browser_actions(),
                "production": {"mode": "FSKCW", "message": "?" * 32,
                    "base_frequency_hz": 135500, "shift_hz": 5, "dot_seconds": 0.2,
                    "event_count": package10.EXPECTED_PRODUCTION_EVENTS,
                    "duration_ns": package10.PRODUCTION_DURATION_NS,
                    "start_offset_seconds": 90}},
            "quiet": {"baseline_seconds": package9.BASELINE_QUIET_SECONDS,
                "interleaved_seconds": [package9.INTERLEAVED_QUIET_SECONDS] * 3,
                "final_seconds": package9.FINAL_QUIET_SECONDS,
                "minimum_measured_seconds": 3438},
            "terminal_history": {"capacity": 8, "warmup_production_class": 3,
                "warmup_maximum_class": 5, "production_jobs": 3,
                "refresh_maximum_class": 5, "final_production_class": 3,
                "final_maximum_class": 5, "resource_return_limit_bytes": 1024},
            "source_impact": {"deployed_source_revision": package10.SOURCE,
                "repository_baseline_revision": "a19db5319520a7c609cd9947cb44942bace5a0f3",
                "runtime_source_changes": 0,
                "decision": "measurement-only replay-history normalization"}})
        for name in ("before_a_session", "before_b_session", "final_a_session",
                     "final_b_session", "usb_observer_session_1",
                     "usb_observer_session_2", "usb_observer_session_3"):
            packet[name] = uuid.uuid4().hex
    packet["absolute_host_deadline_monotonic_ns"] = time.monotonic_ns() + \
        (packet["network_runtime_seconds"] + packet["network_restoration_seconds"] + 300) * 1_000_000_000
    packet["stage_sha256"] = {name: digest(root / name) for name in COMMON_INPUTS}
    raw = (json.dumps(packet, indent=2) + "\n").encode()
    (root / "packet.json").write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    main()
