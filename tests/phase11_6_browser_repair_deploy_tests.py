#!/usr/bin/env python3

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase11_6_browser_repair_deploy as deploy  # noqa: E402


class Phase116BrowserRepairDeployTests(unittest.TestCase):
    def inventory(self, *, board="a", after=False):
        if board == "a":
            revision = deploy.NEW_REVISION if after else deploy.PRIOR_REVISION
            boot = "9" * 32 if after else deploy.PRIOR_BOOT
            device = deploy.DEVICE
        else:
            revision = deploy.B_REVISION
            boot = deploy.B_BOOT
            device = deploy.B_DEVICE
        status = {
            "boot_id": boot, "state": "empty", "output_active": False,
            "owner_id": None,
        }
        info = {
            "device_id": device, "revision": revision,
            "recovery_boot": board == "a" and not after,
            "fault_stage": 14 if board == "a" and not after else 0,
            "fault_hash": 3833354787 if board == "a" and not after else 0,
            "fault_allocation_recorded": board == "a" and not after,
            "fault_allocation_request_bytes": (
                33335 if board == "a" and not after else 0
            ),
            "fault_allocation_returned_null": (
                True if board == "a" and not after else None
            ),
            "system_clock_hz": 138_000_000,
            "rf_render_in_ram": True,
            "core0_stack_guard_valid": 1,
            "core1_stack_guard_valid": 1,
            "fault_status": 0,
            "dma_errors": 0,
            "allocator_failures": "0",
            "tls_allocation_failures": 0,
            "heap_capacity_bytes": 220_000,
            "allocator_peak_bytes": 150_000,
            "network": {
                "control_configured": True, "control_listening": True,
                "configured_hostname": (
                    "wsprrypico-0a60df.local" if board == "a"
                    else "wsprrypico-0a9d89.local"
                ),
            },
            "status": {
                **status, "enabled": False, "engine": "pio-dma-gp2",
                "station": {"callsign": "AA0NT", "locator": "EM18",
                            "power_dbm": 20},
                "schedules": [{"period_s": 120, "phase_s": 0}],
                "schedule_base_frequency_nhz": (
                    "135500000000000" if board == "a" else None
                ),
                "storage_healthy": True,
                "watermark_utc_ns": "1789607761000000000" if board == "a" else "0",
            },
        }
        return {"info": info, "wtp": {"STATUS": status}}

    def test_exact_recovery_and_candidate_are_admitted(self):
        before = {name: self.inventory(board=name) for name in ("a", "b")}
        after = {name: self.inventory(board=name, after=True)
                 for name in ("a", "b")}
        deploy.validate_before(before)
        self.assertEqual(deploy.validate_after(before, after), "9" * 32)

    def test_wrong_recovery_allocation_is_rejected(self):
        before = {name: self.inventory(board=name) for name in ("a", "b")}
        before["a"]["info"]["fault_allocation_request_bytes"] = 33334
        with self.assertRaisesRegex(ValueError, "recovery baseline"):
            deploy.validate_before(before)

    def test_candidate_health_or_retained_change_is_rejected(self):
        before = {name: self.inventory(board=name) for name in ("a", "b")}
        for mutate in (
            lambda value: value["a"]["info"].update(allocator_peak_bytes=190_000),
            lambda value: value["a"]["info"]["status"]["station"].update(
                callsign="BAD"
            ),
            lambda value: value["b"]["wtp"]["STATUS"].update(
                boot_id="8" * 32
            ),
        ):
            after = {name: self.inventory(board=name, after=True)
                     for name in ("a", "b")}
            mutate(after)
            with self.assertRaises(ValueError):
                deploy.validate_after(before, after)

    def test_packet_is_exact_and_zero_rf(self):
        packet = deploy.expected_packet("f" * 64)
        self.assertEqual(packet["deployment_tool_sha256"], "f" * 64)
        self.assertEqual(packet["limits"], {
            "bootsel_transitions": 1,
            "firmware_flashes": 1,
            "configuration_writes": 0,
            "rf_jobs": 0,
            "retries": 0,
        })
        changed = copy.deepcopy(packet)
        changed["limits"]["retries"] = 1
        self.assertNotEqual(changed, packet)


if __name__ == "__main__":
    unittest.main()
