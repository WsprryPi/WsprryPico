#!/usr/bin/env python3
"""Aggregate three exact Package 2 overload captures into Package 5 reclamation proof."""
import argparse
import json
from pathlib import Path

from audit_phase11_5_completion_combined import audit as audit_combined
from audit_phase11_5_package5_quiet import audit as audit_quiet
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
            set(packet["normalizer"]) == {"root", "packet_sha256",
                "rf_packet_sha256"} and
            packet["resource_return_tolerance_bytes"] == 1024 and
            packet["highest_resource_basis"] == dict(
                package2_result_sha256=packet["highest_resource_basis"]["package2_result_sha256"],
                supported_allocator_peak_bytes=148088,
                overload_allocator_peak_bytes=164296,
                selected="bounded-overload"), "Frozen Package 5 reclamation policy")
    for name, sha in packet["stage_sha256"].items():
        path = (root / name).resolve()
        require(path.is_relative_to(root) and digest(path) == sha,
                "Package 5 reclamation staged input changed")
    require(digest(Path(packet["package2_result_path"])) ==
            packet["highest_resource_basis"]["package2_result_sha256"],
            "Package 2 highest-resource evidence changed")
    normalizer_root = Path(packet["normalizer"]["root"])
    normalizer_packet = json.loads((normalizer_root / "packet.json").read_text())
    predecessor = normalizer_packet["quiet_predecessor"]
    predecessor_root = Path(predecessor["root"])
    require(predecessor["packet_sha256"] == packet["normalizer"]["rf_packet_sha256"] and
            digest(predecessor_root / "packet.json") == predecessor["packet_sha256"] and
            digest(predecessor_root / "normalizer-audit.json") == predecessor["audit_sha256"],
            "Package 5 normalizer RF/quiet predecessor binding")
    normalizer = audit_quiet(normalizer_root,
                             packet["normalizer"]["packet_sha256"])
    require(normalizer["phase"] == "normalizer" and normalizer["samples"] >= 13 and
            normalizer["allocator_failures"] == normalizer["tls_allocation_failures"] == 0,
            "Accepted normalized application-quiet baseline")
    normalized_live = normalizer["post_live_bytes"]
    summaries = []
    posts = []
    maximum_job_ids = {job["job_id"] for job in
                       json.loads((predecessor_root / "packet.json").read_text())["jobs"]}
    prior_records = finished(predecessor_root / "final-a.stdout",
                             "READ_ONLY_INVENTORY")["wtp"]["STATUS"]["terminal_records"]
    for cycle in packet["cycles"]:
        cycle_root = Path(cycle["root"])
        result = audit_combined(cycle_root, cycle["packet_sha256"])
        quiet = audit_quiet(cycle_root, cycle["packet_sha256"])
        require(result["status"] == "P2_OVERLOAD_VERIFIED" and
                result["combined"]["authenticated_recovery"] is True and
                result["combined"]["http_primary_status"] == 503 and
                result["combined"]["observed_resident_delta_bytes"] >= 32768,
                "Package 5 exact highest-resource cycle")
        require(quiet["phase"] == f"cycle-{cycle['number']}" and quiet["samples"] >= 13,
                "Package 5 equivalent application-quiet cycle")
        before = finished(cycle_root / "before-a.stdout", "READ_ONLY_INVENTORY")
        after = finished(cycle_root / "final-a.stdout", "READ_ONLY_INVENTORY")
        cycle_packet = json.loads((cycle_root / "packet.json").read_text())
        maximum_job_ids.update(job["job_id"] for job in cycle_packet["jobs"])
        require(configuration(before) == configuration(after) and
                before["wtp"]["STATUS"]["terminal_records"] == prior_records and
                before["wtp"]["STATUS"]["boot_id"] == after["wtp"]["STATUS"]["boot_id"] == BOOT and
                len(before["wtp"]["STATUS"]["terminal_records"]) ==
                len(after["wtp"]["STATUS"]["terminal_records"]) == 8 and
                all(record["job_id"] in maximum_job_ids and record["state"] == "complete" and
                    record["output_active"] is False
                    for record in after["wtp"]["STATUS"]["terminal_records"]) and
                after["wtp"]["STATUS"]["state"] == "empty" and
                after["wtp"]["STATUS"]["output_active"] is False and
                after["wtp"]["STATUS"]["owner_id"] is None and
                after["wtp"]["STATUS"]["job_id"] is None,
                "Package 5 matched cycle identity/cardinality/authority")
        prior_records = after["wtp"]["STATUS"]["terminal_records"]
        for key in ("ipv4", "ntp_address", "stable_hostname", "mdns_state", "control_listening"):
            require(before["info"]["network"][key] == after["info"]["network"][key],
                    "Package 5 matched cycle network state")
        pre = normalized_live
        post = quiet["post_live_bytes"]
        require(abs(post - normalized_live) <= packet["resource_return_tolerance_bytes"] and
                quiet["allocator_failures"] == 0 and
                quiet["tls_allocation_failures"] == 0 and
                quiet["heap_capacity_bytes"] -
                int(after["info"]["allocator_peak_bytes"]) >= 32768,
                "Package 5 per-cycle resource return/reserve")
        posts.append(post)
        summaries.append(dict(number=cycle["number"], packet_sha256=cycle["packet_sha256"],
                              normalized_live_bytes=pre, post_live_bytes=post,
                              delta_bytes=post - pre, terminal_records=8,
                              maximum_allocator_peak_bytes=result["maximum_allocator_peak_bytes"],
                              authenticated_recovery=True))
    require(max(posts) - min(posts) <= packet["resource_return_tolerance_bytes"] and
            not (posts[0] < posts[1] < posts[2]),
            "Package 5 equivalent post-cycle no-growth/tolerance")
    return dict(status="PACKAGE5_THREE_CYCLE_RECLAMATION_VERIFIED", packet_sha256=expected,
                source_revision=SOURCE, image_sha256=IMAGE, boot_id=BOOT,
                cycles=summaries, post_live_bytes=posts,
                normalized_live_bytes=normalized_live,
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
