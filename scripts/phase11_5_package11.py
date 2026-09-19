#!/usr/bin/env python3
"""Execute the Package 11 corrected R6 packet on the two-host fixture."""

import argparse
import copy
import json
import os
from pathlib import Path
import time

from phase11_5_inventory import require
import phase11_5_package9 as package9
import phase11_5_package10 as package10


AUTHORIZED_RF_DURATION_NS = 480_000_000_000
AUTHORIZATION = "PACKAGE11-TWO-HOST-R6"
RETRY1_AUTHORIZATION = "PACKAGE11-TWO-HOST-R6-RETRY1"
RETRY2_AUTHORIZATION = "PACKAGE11-TWO-HOST-R6-RETRY2"
RETRY3_AUTHORIZATION = "PACKAGE11-TWO-HOST-R6-RETRY3"
RETRY4_AUTHORIZATION = "PACKAGE11-TWO-HOST-R6-RETRY4"
SCHEMA = "phase11.5-package11-fixture-v1"
ATTEMPT1_PACKET_SHA256 = "ed3255ba7811edef230a6e263e8de94cf13dbb0afbae6c51ee400a70f3622052"
ADMISSION_RESULT_SHA256 = "fe4d7a9b84ec97f256b09f187005399685d0aefd556b129648608ea2a4cb1214"
ADMISSION_ADVERSARIAL_SHA256 = "2b9e18c73cc7f53572f086b44c2d1fef9835009b129cb4b30c8b0c5db6317935"
ATTEMPT1_RESULT_SHA256 = "0bef1850d736535661e2c0ae1bc7519dbff2cfbf06ebacf1c64108b4831b6faf"
CLOCK_POLL_RETEST_RESULT_SHA256 = "92838e20c1de3a998bda67084f75b8deb728049633598ab9e2b5b18b2606fa68"
RETRY1_PACKET_SHA256 = "cc3bf2c66075112bccc93557173f256541c6fcecea9637972ada6e55312cec0a"
RETRY1_RESULT_SHA256 = "89a7a1f26b2aa084187d08b24749bde22bec95476a20cddfe397a62f25d9d1a7"
RETRY1_ADVERSARIAL_SHA256 = "f9c83b32542f0843ca262fcd041c5a8e89b96fcff526917008d50757d61e28b8"
CREDENTIAL_RETEST_RESULT_SHA256 = "b12474628bac9c07e93f86652f92f4c8dae47cb8464f00c06e93245e34aff59b"
RETRY2_PACKET_SHA256 = "6408d93a0d7b990c0cb40b5bafb8bc6bfd650b187bfb975984783572c898a1fb"
RETRY2_RESULT_SHA256 = "4f4eaf27cd1ad84a84d72b7669e4f72822c25402768d5acc20eb33cc7412c7e1"
RETRY2_ADVERSARIAL_SHA256 = "717a3aea894f10ae28881a98bc67b4cb12208a972bb30e1515593fc69a7330c5"
RETRY3_PACKET_SHA256 = "f2f0e684b658310038dd6b3a36b8b58ef285c1db6bd6fcbf05a9c4111b153dbd"
RETRY3_RESULT_SHA256 = "9b02a77258a36739a3076f68ddf9b525cb6edf32c54bf5408f02e8340f956598"
RETRY3_ADVERSARIAL_SHA256 = "5743412d23c14e59c0efa018b4071b94f4760bd7669878a159f7bd4f15cc3e1c"
USB_REDUCER_RETEST_RESULT_SHA256 = "9016f26d0f6d87c8743202cd2ffd4cba2be9473f6320c0e6f1064afe520f823b"
USB_REDUCER_RETEST_ADVERSARIAL_SHA256 = "e88f8ab10c8ad16e6fe80ed77990e299be7b7be67cdf56534ace86af2c252868"
RETRY4_CREDENTIAL_RETEST_RESULT_SHA256 = "0bf89b6046b6fd7f2eed6f410044ae5556b1b1a2997c8493bdc3518151d13f3c"
ATTEMPT1_RF_JOBS = 8
ATTEMPT1_RF_DURATION_NS = 8_000_000_000
RETRY1_RF_JOBS = 8
RETRY1_RF_DURATION_NS = 8_000_000_000
RETRY2_RF_JOBS = 0
RETRY2_RF_DURATION_NS = 0
RETRY3_RF_JOBS = 9
RETRY3_RF_DURATION_NS = 122_600_000_000
PRIOR_RF_JOBS = (ATTEMPT1_RF_JOBS + RETRY1_RF_JOBS + RETRY2_RF_JOBS +
                 RETRY3_RF_JOBS)
PRIOR_RF_DURATION_NS = (ATTEMPT1_RF_DURATION_NS + RETRY1_RF_DURATION_NS +
                        RETRY2_RF_DURATION_NS + RETRY3_RF_DURATION_NS)
CUMULATIVE_RF_JOBS = PRIOR_RF_JOBS + package10.RF_JOBS
CUMULATIVE_RF_DURATION_NS = PRIOR_RF_DURATION_NS + package10.RF_DURATION_NS
TERMINAL_RETENTION_WAIT_SECONDS = 600
TERMINAL_RETENTION_SAMPLE_SECONDS = 15
TERMINAL_RETENTION_SESSIONS = 42
REMOTE_HOST = "wspr4"
REMOTE_AP_MAC = "e8:4e:06:ac:f3:87"
CLIENT_IF = "wlan2"
CLIENT_MAC = "e8:4e:06:ae:d7:09"
TIME_ADDRESS = "10.77.15.2"


def legacy_packet(packet):
    """Map unchanged workload fields through the reviewed Package 10 validator."""
    value = copy.deepcopy(packet)
    value["schema"] = "phase11.5-package10-fixture-v2"
    value["authorization"] = "PACKAGE10-480-RF-SECONDS"
    value["network_fixture_roles"] = {"ap": "wlan0", "client": "wlan2",
        "ap_mac": "2c:cf:67:62:76:66", "client_mac": CLIENT_MAC}
    value["authorized_rf_duration_ns"] = package10.AUTHORIZED_RF_DURATION_NS
    value["authorized_max_flashes"] = 2
    value["authorized_max_bootsel"] = 2
    value["cumulative_rf_jobs"] = package10.CUMULATIVE_RF_JOBS
    value["cumulative_rf_duration_ns"] = package10.CUMULATIVE_RF_DURATION_NS
    value["prior_attempt"] = {"packet_sha256": package10.PRIOR_ATTEMPT_PACKET_SHA256,
        "result_sha256": package10.PRIOR_ATTEMPT_RESULT_SHA256,
        "status": "STOPPED_PRE_GATE_SEQUENCE_MISMATCH",
        "charged_rf_jobs": package10.PRIOR_ATTEMPT_RF_JOBS,
        "charged_rf_duration_ns": package10.PRIOR_ATTEMPT_RF_DURATION_NS,
        "reservation_released": True, "fixture_restored": True}
    return value


def validate(packet):
    require(packet.get("schema") == SCHEMA and packet.get("family") == "R6" and
            packet.get("authorization") == RETRY4_AUTHORIZATION and
            packet.get("authorized_rf_duration_ns") == AUTHORIZED_RF_DURATION_NS and
            packet.get("rf_jobs") == package10.RF_JOBS and
            packet.get("rf_duration_ns") == package10.RF_DURATION_NS and
            packet.get("cumulative_package11_rf_jobs") == CUMULATIVE_RF_JOBS and
            packet.get("cumulative_package11_rf_duration_ns") ==
                CUMULATIVE_RF_DURATION_NS and
            package10.RF_DURATION_NS <= AUTHORIZED_RF_DURATION_NS and
            packet.get("configuration_writes") == packet.get("controlled_reboots") ==
                packet.get("flashes") == packet.get("bootsel") ==
                packet.get("wifi_cycles") == packet.get("allocation_probes") == 0 and
            packet.get("time_authority_address") == TIME_ADDRESS,
            "Finite Package 11 campaign")
    require(packet.get("network_fixture_roles") == {
        "ap_host": REMOTE_HOST, "ap": "wlan1", "ap_mac": REMOTE_AP_MAC,
        "client_host": "wspr5", "client": CLIENT_IF, "client_mac": CLIENT_MAC},
        "Package 11 two-host roles")
    require(packet.get("source_impact") == {
            "deployed_source_revision": package10.SOURCE,
            "repository_baseline_revision":
                "a19db5319520a7c609cd9947cb44942bace5a0f3",
            "runtime_source_changes": 0,
            "decision": "measurement-only replay-history normalization"},
            "Package 11 Retry 4 source impact")
    retention = packet.get("terminal_retention_preflight", {})
    sessions = retention.get("sessions", [])
    require(retention.get("timeout_seconds") == TERMINAL_RETENTION_WAIT_SECONDS and
            retention.get("sample_seconds") == TERMINAL_RETENTION_SAMPLE_SECONDS and
            retention.get("terminal_record_ttl_seconds") == 3600 and
            retention.get("maximum_terminal_records") == 8 and
            len(sessions) == TERMINAL_RETENTION_SESSIONS and
            len(set(sessions)) == len(sessions) and
            all(package9.identity(value, "Retention session") == value
                for value in sessions),
            "Package 11 retained-terminal preflight")
    ready = packet.get("remote_ready", {})
    require(ready.get("host") == REMOTE_HOST and ready.get("ap_mac") == REMOTE_AP_MAC and
            ready.get("channel") == 11 and ready.get("wifi_sha256") ==
                packet.get("retained_wifi_canonical_sha256"),
            "Package 11 remote AP readiness")
    require(packet.get("admission") == {"status": "PASS_ZERO_RF",
            "result_sha256": packet.get("admission_result_sha256"),
            "adversarial_sha256": packet.get("admission_adversarial_sha256"),
            "fixture_restored": True, "rf_jobs": 0, "rf_duration_ns": 0},
            "Package 11 zero-RF admission dependency")
    require(packet.get("admission_result_sha256") == ADMISSION_RESULT_SHA256 and
            packet.get("admission_adversarial_sha256") ==
                ADMISSION_ADVERSARIAL_SHA256 and
            packet.get("prior_attempt_result_sha256") == ATTEMPT1_RESULT_SHA256 and
            packet.get("clock_poll_retest_result_sha256") ==
                CLOCK_POLL_RETEST_RESULT_SHA256 and
            packet.get("retry1_attempt_result_sha256") == RETRY1_RESULT_SHA256 and
            packet.get("retry1_adversarial_sha256") == RETRY1_ADVERSARIAL_SHA256 and
            packet.get("credential_retest_result_sha256") ==
                CREDENTIAL_RETEST_RESULT_SHA256 and
            packet.get("retry2_attempt_result_sha256") == RETRY2_RESULT_SHA256 and
            packet.get("retry2_adversarial_sha256") == RETRY2_ADVERSARIAL_SHA256 and
            packet.get("retry3_attempt_result_sha256") == RETRY3_RESULT_SHA256 and
            packet.get("retry3_adversarial_sha256") == RETRY3_ADVERSARIAL_SHA256 and
            packet.get("usb_reducer_retest_result_sha256") ==
                USB_REDUCER_RETEST_RESULT_SHA256 and
            packet.get("usb_reducer_retest_adversarial_sha256") ==
                USB_REDUCER_RETEST_ADVERSARIAL_SHA256 and
            packet.get("retry4_credential_retest_result_sha256") ==
                RETRY4_CREDENTIAL_RETEST_RESULT_SHA256,
            "Package 11 exact retry dependencies")
    prior = packet.get("prior_package11_attempt", {})
    require(prior.get("packet_sha256") == ATTEMPT1_PACKET_SHA256 and
            prior.get("result_sha256") == packet.get("prior_attempt_result_sha256") and
            prior.get("status") == "STOPPED_PRE_CYCLE_CLOCK_POLL_ALIAS" and
            prior.get("charged_rf_jobs") == ATTEMPT1_RF_JOBS and
            prior.get("charged_rf_duration_ns") == ATTEMPT1_RF_DURATION_NS and
            prior.get("resource_result_accepted") is False and
            prior.get("reservation_released") is True and
            prior.get("fixture_restored") is True,
            "Package 11 prior-attempt accounting")
    retry1 = packet.get("retry1_package11_attempt", {})
    require(retry1.get("packet_sha256") == RETRY1_PACKET_SHA256 and
            retry1.get("result_sha256") == packet.get("retry1_attempt_result_sha256") and
            retry1.get("adversarial_sha256") == packet.get("retry1_adversarial_sha256") and
            retry1.get("status") == "STOPPED_PRE_ARM_WSPRRYPI_TLS_CREDENTIAL_OWNER" and
            retry1.get("charged_rf_jobs") == RETRY1_RF_JOBS and
            retry1.get("charged_rf_duration_ns") == RETRY1_RF_DURATION_NS and
            retry1.get("production_jobs_armed") == 0 and
            retry1.get("resource_result_accepted") is False and
            retry1.get("reservation_released") is True and
            retry1.get("fixture_restored") is True,
            "Package 11 Retry 1 accounting")
    retry2 = packet.get("retry2_package11_attempt", {})
    require(retry2.get("packet_sha256") == RETRY2_PACKET_SHA256 and
            retry2.get("result_sha256") == packet.get("retry2_attempt_result_sha256") and
            retry2.get("adversarial_sha256") == packet.get("retry2_adversarial_sha256") and
            retry2.get("status") == "STOPPED_PRE_RESERVATION_MEMORY_RETENTION_WINDOW" and
            retry2.get("charged_rf_jobs") == RETRY2_RF_JOBS and
            retry2.get("charged_rf_duration_ns") == RETRY2_RF_DURATION_NS and
            retry2.get("reservation_acquired") is False and
            retry2.get("resource_result_accepted") is False and
            retry2.get("reservation_released") is True and
            retry2.get("fixture_restored") is True,
            "Package 11 Retry 2 accounting")
    retry3 = packet.get("retry3_package11_attempt", {})
    require(retry3.get("packet_sha256") == RETRY3_PACKET_SHA256 and
            retry3.get("result_sha256") == packet.get("retry3_attempt_result_sha256") and
            retry3.get("adversarial_sha256") == packet.get("retry3_adversarial_sha256") and
            retry3.get("status") == "STOPPED_AFTER_CYCLE1_USB_EVENT_REDUCTION" and
            retry3.get("charged_rf_jobs") == RETRY3_RF_JOBS and
            retry3.get("charged_rf_duration_ns") == RETRY3_RF_DURATION_NS and
            retry3.get("production_jobs") == 1 and
            retry3.get("normal_cycles") == 1 and
            retry3.get("post_n_windows") == 0 and
            retry3.get("resource_result_accepted") is False and
            retry3.get("reservation_released") is True and
            retry3.get("fixture_restored") is True,
            "Package 11 Retry 3 accounting")
    reducer = packet.get("usb_reducer_retest", {})
    require(reducer == {"status": "PASS_ZERO_RF_HOST_ONLY",
            "result_sha256": packet.get("usb_reducer_retest_result_sha256"),
            "adversarial_sha256": packet.get(
                "usb_reducer_retest_adversarial_sha256"),
            "phase11_5_package9_source_sha256":
                "5d9b268b65f9dcc01c962217d620603c0a55363639dc03a14fbb2d55c3ca7a3c",
            "repaired_event_and_status_reducer_accepts": True,
            "mutations_rejected": 22, "rf_jobs": 0, "rf_duration_ns": 0,
            "pico_access": False, "usb_access": False, "network_access": False,
            "service_mutations": 0, "reservation_access": False},
            "Package 11 Retry 3 USB reducer repair evidence")
    credential_retest = packet.get("retry4_credential_retest", {})
    require(credential_retest == {"status": "PASS_ZERO_RF_HOST_ONLY",
            "result_sha256": packet.get("retry4_credential_retest_result_sha256"),
            "files": 6, "fixture_source_sha256": packet.get("stage_sha256", {}).get(
                "scripts/phase11_5_package11_fixture.py"),
            "before_owner_uid": 1000, "after_owner_uid": 0,
            "mode": "0600", "content_hashes_unchanged": True,
            "rf_jobs": 0, "rf_duration_ns": 0, "pico_access": False,
            "usb_access": False, "network_mutations": 0,
            "service_mutations": 0, "reservation_access": False},
            "Package 11 credential repair evidence")
    clock = packet.get("clock_poll_retest", {})
    require(clock.get("status") == "PASS_ZERO_RF" and
            clock.get("result_sha256") == packet.get("clock_poll_retest_result_sha256") and
            clock.get("rf_jobs") == clock.get("rf_duration_ns") == 0 and
            clock.get("reservation_unchanged") is True and
            clock.get("fixture_restored") is True,
            "Package 11 clock-poll repair evidence")
    package10.validate(legacy_packet(packet))
    credential_paths = tuple(packet["credentials"][role][kind]
                             for role in ("controller", "browser")
                             for kind in ("ca", "cert", "key"))
    require(set(packet.get("credential_sha256", {})) == set(credential_paths) and
            all(package10.digest(Path(packet["root"]) / name) ==
                packet["credential_sha256"][name] for name in credential_paths),
            "Package 11 credential content binding")
    return packet


def wait_for_terminal_retention(root, packet, journal):
    """Wait for prior complete terminal records before the fixed heap gate."""
    config = packet["terminal_retention_preflight"]
    deadline = time.monotonic() + config["timeout_seconds"]
    for index, session in enumerate(config["sessions"], start=1):
        value = package9.inventory(root, packet, f"retention-{index}",
                                   package10.SERIAL, package10.DEVICE, session)
        status = value["wtp"]["STATUS"]
        clock = value["wtp"]["GET_CLOCK"]
        records = status["terminal_records"]
        record_ids = [record["job_id"] for record in records]
        require(status["boot_id"] == package10.BOOT and
                status["owner_id"] is None and status["output_active"] is False and
                value["info"]["status"]["enabled"] is False and
                len(records) <= config["maximum_terminal_records"] and
                len(record_ids) == len(set(record_ids)) and
                all(record["state"] == "complete" and
                    record["output_active"] is False for record in records),
                "Package 11 retained-terminal authority")
        now_ns = int(clock["monotonic_now_ns"])
        remaining = [max(0, int(record["ended_monotonic_ns"]) +
                         config["terminal_record_ttl_seconds"] * 1_000_000_000 - now_ns)
                     for record in records]
        require(max(remaining, default=0) <=
                config["timeout_seconds"] * 1_000_000_000,
                "Terminal retention exceeds authorized wait")
        journal.emit("terminal_retention_preflight", {
            "attempt": index, "terminal_records": len(records),
            "maximum_remaining_ns": max(remaining, default=0),
            "all_complete_output_inactive": True})
        if not records:
            return value
        left = deadline - time.monotonic()
        require(left > 0 and index < len(config["sessions"]),
                "Terminal retention preflight deadline")
        time.sleep(min(config["sample_seconds"], left))
    raise ValueError("Terminal retention preflight session limit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print("Plan only; no host, network, USB or RF access.")
        return
    require(os.geteuid() == 0 and os.name == "posix", "Linux root required")
    root = args.root.resolve(strict=True)
    require(root.stat().st_mode & 0o077 == 0 and
            package10.digest(root / "packet.json") == args.packet_sha256,
            "Private Package 11 root/packet")
    packet = validate(json.loads((root / "packet.json").read_text()))
    require(packet["root"] == str(root) and
            Path("/proc/sys/kernel/random/boot_id").read_text().strip() == package10.HOST_BOOT and
            os.readlink("/proc/self/ns/net") != os.readlink("/proc/1/ns/net") and
            os.readlink("/proc/self/ns/mnt") != os.readlink("/proc/1/ns/mnt"),
            "Package 11 client namespaces")
    os.umask(0o077)
    journal = package9.Journal(root / "campaign.jsonl")
    try:
        journal.emit("start", {"packet_sha256": args.packet_sha256,
            "package": 11, "remote_ap": packet["remote_ready"]})
        result = package10.run(root, packet, journal, wait_for_terminal_retention)
        journal.emit("finish", result)
    except BaseException as error:
        journal.emit("failure", {"type": type(error).__name__, "error": str(error)})
        raise
    finally:
        journal.close()


if __name__ == "__main__":
    main()
