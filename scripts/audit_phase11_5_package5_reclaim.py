#!/usr/bin/env python3
"""Aggregate three exact Package 2 overload captures into Package 5 reclamation proof."""
import argparse
import json
from pathlib import Path

from audit_phase11_5_completion_combined import audit as audit_combined
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_package5_plan import BOOT, IMAGE, SOURCE
from phase11_5_pilot_supervisor import configuration, finished


def audit(root, expected):
    require(digest(root / "packet.json") == expected, "Frozen Package 5 reclamation packet")
    packet = json.loads((root / "packet.json").read_text())
    require(packet["schema"] == "phase11.5-package5-reclaim-v1" and
            (packet["source_revision"], packet["image_sha256"], packet["boot_id"]) ==
            (SOURCE, IMAGE, BOOT) and packet["cycles"] == [dict(number=n,
                root=packet["cycles"][n - 1]["root"],
                packet_sha256=packet["cycles"][n - 1]["packet_sha256"])
                for n in (1, 2, 3)] and
            packet["resource_return_tolerance_bytes"] == 1024 and
            packet["highest_resource_basis"] == dict(
                package2_result_sha256=packet["highest_resource_basis"]["package2_result_sha256"],
                supported_allocator_peak_bytes=148088,
                overload_allocator_peak_bytes=164296,
                selected="bounded-overload"), "Frozen Package 5 reclamation policy")
    require(digest(Path(packet["package2_result_path"])) ==
            packet["highest_resource_basis"]["package2_result_sha256"],
            "Package 2 highest-resource evidence changed")
    summaries = []
    posts = []
    for cycle in packet["cycles"]:
        cycle_root = Path(cycle["root"])
        result = audit_combined(cycle_root, cycle["packet_sha256"])
        require(result["status"] == "P2_OVERLOAD_VERIFIED" and
                result["combined"]["authenticated_recovery"] is True and
                result["combined"]["http_primary_status"] == 503 and
                result["combined"]["observed_resident_delta_bytes"] >= 32768,
                "Package 5 exact highest-resource cycle")
        before = finished(cycle_root / "before-a.stdout", "READ_ONLY_INVENTORY")
        after = finished(cycle_root / "final-a.stdout", "READ_ONLY_INVENTORY")
        require(configuration(before) == configuration(after) and
                before["wtp"]["STATUS"]["boot_id"] == after["wtp"]["STATUS"]["boot_id"] == BOOT and
                len(before["wtp"]["STATUS"]["terminal_records"]) ==
                len(after["wtp"]["STATUS"]["terminal_records"]) == 8 and
                after["wtp"]["STATUS"]["state"] == "empty" and
                after["wtp"]["STATUS"]["output_active"] is False and
                after["wtp"]["STATUS"]["owner_id"] is None,
                "Package 5 matched cycle identity/cardinality/authority")
        for key in ("ipv4", "ntp_address", "stable_hostname", "mdns_state", "control_listening"):
            require(before["info"]["network"][key] == after["info"]["network"][key],
                    "Package 5 matched cycle network state")
        pre = int(before["info"]["heap_allocated_bytes"])
        post = int(after["info"]["heap_allocated_bytes"])
        require(abs(post - pre) <= packet["resource_return_tolerance_bytes"] and
                int(after["info"]["allocator_failures"]) == 0 and
                int(after["info"]["tls_allocation_failures"]) == 0 and
                int(after["info"]["heap_capacity_bytes"]) -
                int(after["info"]["allocator_peak_bytes"]) >= 32768,
                "Package 5 per-cycle resource return/reserve")
        posts.append(post)
        summaries.append(dict(number=cycle["number"], packet_sha256=cycle["packet_sha256"],
                              pre_live_bytes=pre, post_live_bytes=post,
                              delta_bytes=post - pre, terminal_records=8,
                              maximum_allocator_peak_bytes=result["maximum_allocator_peak_bytes"],
                              authenticated_recovery=True))
    require(max(posts) - min(posts) <= packet["resource_return_tolerance_bytes"] and
            not (posts[0] < posts[1] < posts[2]),
            "Package 5 equivalent post-cycle no-growth/tolerance")
    return dict(status="PACKAGE5_THREE_CYCLE_RECLAMATION_VERIFIED", packet_sha256=expected,
                source_revision=SOURCE, image_sha256=IMAGE, boot_id=BOOT,
                cycles=summaries, post_live_bytes=posts,
                maximum_post_difference_bytes=max(posts) - min(posts),
                monotonic_retained_growth=False, selected_workload="bounded-overload")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--packet-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.root.resolve(strict=True), args.packet_sha256), indent=2))


if __name__ == "__main__":
    main()
