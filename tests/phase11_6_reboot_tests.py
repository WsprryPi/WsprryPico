#!/usr/bin/env python3

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase11_6_reboot import (  # noqa: E402
    BOOT_B,
    DEVICE_A,
    DEVICE_B,
    OLD_BOOT_A,
    SOURCE_A,
    assert_accepted_a,
    assert_peer_b,
    assert_released_reservation,
    load_inventory,
    resource_counters,
    retained_configuration,
)


def inventory(device, revision, boot):
    return {
        "result": "READ_ONLY_INVENTORY",
        "info": {
            "device_id": device,
            "revision": revision,
            "deployment_identity_matches": True,
            "recovery_boot": False,
            "fault_stage": 0,
            "fault_status": 0,
            "system_clock_hz": 138_000_000,
            "rf_render_in_ram": True,
            "allocator_failures": "0",
            "tls_allocation_failures": 0,
            "allocator_last_failure_request_bytes": 0,
            "dma_errors": 0,
            "refill_irq_unpaired": 0,
            "refill_invalid_reserves": 0,
            "network": {
                "deployment_identity_matches": True,
                "enabled": True,
                "control_configured": True,
                "stable_hostname": "wsprrypico-0a60df.local",
                "configured_hostname": "wsprrypico-0a60df.local",
                "ntp_server": "time.local",
            },
            "status": {
                "boot_id": boot,
                "engine": "pio-dma-gp2",
                "configured": True,
                "enabled": False,
                "suspended": False,
                "expires_utc_s": 0,
                "station": {"callsign": "AA0NT", "locator": "EM18", "power_dbm": 20},
                "schedules": [{"period_s": 120, "phase_s": 0}],
                "schedule_base_frequency_nhz": "135500000000000",
                "storage_healthy": True,
                "reboot_required": False,
                "watermark_utc_ns": "123",
                "state": "empty",
                "output_active": False,
            },
        },
        "wtp": {
            "HELLO": {"boot_id": boot},
            "STATUS": {
                "boot_id": boot,
                "state": "empty",
                "owner_id": None,
                "job_id": None,
                "output_active": False,
                "terminal_records": [],
            },
        },
    }


class Phase116RebootTests(unittest.TestCase):
    def test_exact_a_and_b_identity_and_inactive_state(self):
        a = inventory(DEVICE_A, SOURCE_A, OLD_BOOT_A)
        a["wtp"]["STATUS"]["terminal_records"] = [{
            "job_id": "e91341f781eed88966020f2a205a9c34",
            "state": "complete",
            "ended_monotonic_ns": "3840975862000",
            "output_active": False,
        }]
        b = inventory(DEVICE_B, "8921a7008183", BOOT_B)
        assert_accepted_a(a, OLD_BOOT_A)
        assert_peer_b(b)
        b["wtp"]["STATUS"]["output_active"] = True
        with self.assertRaisesRegex(ValueError, "empty, inactive"):
            assert_peer_b(b)

    def test_retained_configuration_ignores_ephemeral_network_state(self):
        before = inventory(DEVICE_A, SOURCE_A, OLD_BOOT_A)
        after = json.loads(json.dumps(before))
        after["info"]["network"]["ipv4"] = "0.0.0.0"
        self.assertEqual(retained_configuration(before), retained_configuration(after))
        after["info"]["status"]["station"]["callsign"] = "CHANGED"
        self.assertNotEqual(retained_configuration(before), retained_configuration(after))

    def test_resource_gate_is_explicit(self):
        value = inventory(DEVICE_A, SOURCE_A, OLD_BOOT_A)
        self.assertEqual(resource_counters(value)["allocator_failures"], 0)
        value["info"]["allocator_failures"] = "428"
        value["info"]["tls_allocation_failures"] = 214
        value["info"]["allocator_last_failure_request_bytes"] = 16693
        counters = resource_counters(value)
        self.assertEqual(counters["allocator_failures"], 428)
        self.assertEqual(counters["tls_allocation_failures"], 214)

    def test_inventory_requires_one_successful_finish(self):
        value = inventory(DEVICE_A, SOURCE_A, OLD_BOOT_A)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "inventory.jsonl"
            path.write_text(
                json.dumps({"kind": "start"}) + "\n"
                + json.dumps({"kind": "finish", "value": value}) + "\n"
            )
            self.assertEqual(load_inventory(path), value)
            path.write_text(
                json.dumps({"kind": "start"}) + "\n"
                + json.dumps({"kind": "failure", "value": {}}) + "\n"
                + json.dumps({"kind": "finish", "value": value}) + "\n"
            )
            with self.assertRaisesRegex(ValueError, "Complete successful"):
                load_inventory(path)

    def test_reservation_is_bound_to_sequence67_boots(self):
        value = {
            "state": "RELEASED",
            "host_boot": "220e53ca-ca95-4206-9581-dbe28aa1eeb8",
            "packet_sha256": "a" * 64,
            "boards": {
                "a": {"boot_id": OLD_BOOT_A, "device_id": DEVICE_A,
                      "revision": SOURCE_A, "state": "empty"},
                "b": {"boot_id": BOOT_B, "device_id": DEVICE_B,
                      "revision": "8921a7008183", "state": "empty"},
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reservation.json"
            path.write_text(json.dumps(value))
            self.assertEqual(assert_released_reservation(path), value)
            value["state"] = "HELD"
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "Released shared"):
                assert_released_reservation(path)

    def test_old_boot_requires_sequence67_breadcrumb_and_new_boot_clears_it(self):
        old = inventory(DEVICE_A, SOURCE_A, OLD_BOOT_A)
        with self.assertRaisesRegex(ValueError, "sequence-67 terminal"):
            assert_accepted_a(old, OLD_BOOT_A)
        old["wtp"]["STATUS"]["terminal_records"] = [{
            "job_id": "e91341f781eed88966020f2a205a9c34",
            "state": "complete",
            "ended_monotonic_ns": "3840975862000",
            "output_active": False,
        }]
        assert_accepted_a(old, OLD_BOOT_A)
        new = inventory(DEVICE_A, SOURCE_A, "f" * 32)
        assert_accepted_a(new, "f" * 32)
        new["wtp"]["STATUS"]["terminal_records"] = old["wtp"]["STATUS"]["terminal_records"]
        with self.assertRaisesRegex(ValueError, "clear volatile"):
            assert_accepted_a(new, "f" * 32)


if __name__ == "__main__":
    unittest.main()
