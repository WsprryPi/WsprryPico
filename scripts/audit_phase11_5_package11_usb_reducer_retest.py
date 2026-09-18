#!/usr/bin/env python3
"""Validate the published Retry 3 host-only USB reducer retest."""

import argparse
import json
from pathlib import Path

from phase11_5_inventory import require


PACKET_SHA256 = "f2f0e684b658310038dd6b3a36b8b58ef285c1db6bd6fcbf05a9c4111b153dbd"
EVIDENCE = {
    "campaign.jsonl": "e67f3d0e17b25425352f01070710a52a2be277e0e143f964991f01a4da587c76",
    "campaign.log": "160ed356f86e9ef69930f4be811cf1335200862fb0f5321770e70c5b7adc9f81",
}
SOURCES = {
    "phase11_5_package9.py": "5d9b268b65f9dcc01c962217d620603c0a55363639dc03a14fbb2d55c3ca7a3c",
    "phase11_5_package11_usb_reducer_retest.py":
        "6ef024dc2848317fa77a36695593840221ae5e80c0a52ee8dd6f8d25374545a4",
}


def validate_result(value):
    require(value.get("schema") ==
            "phase11.5-package11-retry3-usb-reducer-retest-v1" and
            value.get("status") == "PASS_ZERO_RF_HOST_ONLY" and
            value.get("packet_sha256") == PACKET_SHA256 and
            value.get("evidence_sha256") == EVIDENCE and
            value.get("source_sha256") == SOURCES,
            "Retry 3 USB reducer retest identity")
    require(value.get("usb_status_samples") == 120 and
            value.get("usb_status_state_counts") ==
                {"empty": 95, "armed": 2, "running": 23} and
            value.get("usb_event_count") == 6 and
            value.get("usb_event_states") ==
                ["armed", "complete", "empty", "loaded", "running"] and
            value.get("maximum_status_gap_ns") == 5_000_065_331 and
            value.get("maximum_status_response_ns") == 954_628_630 and
            value["maximum_status_gap_ns"] <= 6_000_000_000 and
            value["maximum_status_response_ns"] <= 5_000_000_000,
            "Retry 3 USB reducer observations")
    require(value.get("matching_terminal_complete_output_inactive") is True and
            value.get("old_status_only_reducer_rejects") is True and
            value.get("repaired_event_and_status_reducer_accepts") is True,
            "Retry 3 USB reducer repair")
    require(value.get("pico_access") is False and
            value.get("usb_access") is False and
            value.get("network_access") is False and
            value.get("service_mutations") == 0 and
            value.get("reservation_access") is False and
            value.get("rf_jobs") == value.get("rf_duration_ns") == 0,
            "Retry 3 USB reducer zero-RF scope")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    validate_result(json.loads(args.result.read_text()))
    print("PASS")


if __name__ == "__main__":
    main()
