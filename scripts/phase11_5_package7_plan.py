#!/usr/bin/env python3
"""Frozen Package 7 target, fixture and RF-budget validation."""

from phase11_5_inventory import require


SCHEMA = "phase11.5-package7-v1"
AUTHORITY = "PHASE11.5-COMPLETION-20260915"
SOURCE = "2b25ca05c270819466a04498f9bc4894a4c5bace"
IMAGE = "16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51"
BOOT = "80d558e5804547749eca849c53ba27e1"
SERIAL = "0BF4B4AEC9FFB344"
DEVICE = "fd6127d11d6aca42a9905fa3fb1bf1d5"
B_SERIAL = "CDDBF8767C506C07"
B_DEVICE = "29f20b7342051ef947aa56cb9d4fab42"
B_BOOT = "6684b4b197d80cfa0ce83b3aaf205cb0"
HOST_BOOT = "220e53ca-ca95-4206-9581-dbe28aa1eeb8"
PEER_SHA = "06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016"
ADDRESS = "10.77.15.10"
HOSTNAME = "wsprrypico-0a60df.local"
WSPRRYPI_SOURCE = "820e6980e880ce8b20418a20c15f4ac2311f8ca0"
ROWS = [
    "claimed-empty-foreign-control", "claimed-empty-forbidden-storage",
    "loaded-foreign-control", "loaded-forbidden-storage",
    "armed-foreign-control", "armed-forbidden-storage",
    "running-foreign-control", "running-forbidden-storage",
    "production-armed-abort", "production-running-abort",
    "lost-load", "lost-arm", "lost-abort", "tcp-reset-eof",
    "resolver-failure",
]


def identity(value, label):
    require(isinstance(value, str) and len(value) == 32 and value != "0" * 32 and
            all(c in "0123456789abcdef" for c in value), label)
    return value


def validate(packet):
    require(packet["schema"] == packet["scope"] == SCHEMA and
            packet["standing_authority"] == AUTHORITY and
            packet["source_revision"] == SOURCE and packet["image_sha256"] == IMAGE and
            packet["boot_id"] == BOOT and packet["serial"] == SERIAL and
            packet["device_id"] == DEVICE and packet["b_boot_id"] == B_BOOT and
            packet["b_serial"] == B_SERIAL and packet["b_device_id"] == B_DEVICE and
            packet["host_boot_id"] == HOST_BOOT and
            packet["wsprrypi_source_revision"] == WSPRRYPI_SOURCE and
            packet["address"] == ADDRESS and packet["port"] == 18443 and
            packet["hostname"] == HOSTNAME and packet["peer_sha256"] == PEER_SHA,
            "Exact Package 7 identity")
    amended = packet.get("corrective_amendment")
    budget = ((packet["rf_jobs"], packet["rf_duration_ns"]) == (3, 78_000_000_000) or
              ((packet["rf_jobs"], packet["rf_duration_ns"]) == (9, 213_000_000_000) and
               amended == {"reason": "state-transition harness defects",
                           "additional_rf_jobs": 6,
                           "additional_rf_duration_ns": 135_000_000_000,
                           "standing_packet_ceiling_jobs": 16,
                           "standing_packet_ceiling_duration_ns": 14_400_000_000_000}))
    require(packet["rows"] == ROWS and budget and
            packet["direct_duration_ns"] == 12_000_000_000 and
            packet["production_duration_ns"] == 33_000_000_000 and
            packet["fixture_seconds"] == 7200 and packet["restoration_seconds"] == 900 and
            packet["configuration_writes"] == packet["flashes"] ==
            packet["controlled_reboots"] == packet["wifi_cycles"] ==
            packet["allocation_probes"] == 0, "Finite Package 7 budget")
    require(packet["credentials"] == {
        "controller": {"ca": "credentials/controller/client-ca.crt",
                       "cert": "credentials/controller/client.crt",
                       "key": "credentials/controller/client.key"},
        "browser": {"ca": "credentials/browser/client-ca.crt",
                    "cert": "credentials/browser/client.crt",
                    "key": "credentials/browser/client.key"}},
        "Frozen Package 7 credentials")
    names = ("network_session", "owner_id", "foreign_session", "direct_job_id",
             "production_armed_request", "production_running_request")
    require(len({identity(packet[name], name) for name in names}) == len(names),
            "Distinct Package 7 identities")
    if amended:
        tail = ("tail_network_session", "tail_owner_id", "tail_job_id")
        require(len({identity(packet[name], name) for name in tail}) == len(tail) and
                not set(packet[name] for name in tail) & set(packet[name] for name in names),
                "Distinct Package 7 corrective identities")
    return packet
