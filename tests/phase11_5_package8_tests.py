"""No-hardware checks for the frozen Package 8 packet and schedule selection."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase11_5_package8 as package8


class Package8Tests(unittest.TestCase):
    def packet(self):
        identities = [f"{n:032x}" for n in range(1, 10)]
        return dict(schema="phase11.5-package8-fixture-v1", family="R5",
                    standing_authority="PHASE11.5-COMPLETION-20260915",
                    source_revision=package8.SOURCE, image_sha256=package8.IMAGE,
                    boot_id=package8.DEPLOYED_BOOT, b_boot_id=package8.B_BOOT,
                    host_boot_id=package8.HOST_BOOT, configuration_writes=2,
                    rf_jobs=2, rf_duration_ns=350_592_000_000,
                    controlled_reboots=1, flashes=0, bootsel=0, wifi_cycles=0,
                    network_runtime_seconds=7200, network_restoration_seconds=900,
                    address_change=[package8.OLD_ADDRESS, package8.NEW_ADDRESS],
                    external_link_loss_seconds=15,
                    schedule_base_frequency_nhz=package8.BASE_NHZ,
                    credentials={"controller": {"ca": "credentials/controller/client-ca.crt",
                        "cert": "credentials/controller/client.crt", "key": "credentials/controller/client.key"},
                        "browser": {"ca": "credentials/browser/client-ca.crt",
                        "cert": "credentials/browser/client.crt", "key": "credentials/browser/client.key"}},
                    storage_plan={"before_sequence": "68", "before_offset": 6144,
                        "record_size": 2048, "enabled_sequence": "69", "enabled_offset": 0,
                        "restored_sequence": "70", "restored_offset": 2048},
                    **dict(zip(("network_session", "network_owner", "network_job", "usb_session",
                        "post_network_session", "schedule_usb_session", "schedule_network_session",
                        "inventory_session", "b_session"), identities)))

    def test_exact_packet_and_budget(self):
        package8.validate(self.packet())
        amended = self.packet()
        amended["corrective_amendment"] = {
            "reason": "pre-CLAIM CAPS field-shape harness defect",
            "prior_packet_sha256": "44918000c592b5348179fbafb5d96432efd2a577f6c1f5b3b9d7fcf8e853724d",
            "prior_attempt_rf_submissions": 0, "additional_rf_jobs": 0,
            "additional_rf_duration_ns": 0}
        package8.validate(amended)
        for key, value in (("configuration_writes", 3), ("rf_jobs", 3),
                           ("schedule_base_frequency_nhz", "3570100000000000")):
            changed = self.packet(); changed[key] = value
            with self.assertRaises(ValueError):
                package8.validate(changed)

    def test_occurrence_is_even_minute_plus_one_and_at_least_240_seconds_ahead(self):
        for now in (0.0, 100.25, 86390.0, 1_789_604_200.5):
            occurrence, phase = package8.schedule_occurrence(now)
            self.assertGreaterEqual(occurrence - now, 240)
            self.assertEqual((occurrence - 1) % 120, 0)
            self.assertEqual(phase, (occurrence - 1) % 86400)


if __name__ == "__main__":
    unittest.main()
