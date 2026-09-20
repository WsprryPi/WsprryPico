#!/usr/bin/env python3
"""Audit the bounded Phase 11.5 Package 6 R3 closeout publication."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


P1_SOURCE = "8dd6f0812292e9264c2a72745078a95ee606c191"
P24_SOURCE = "ca3c5dce40360b7eea2f9c45618232caa68cdbb6"
CURRENT_SOURCE = "2b25ca05c270819466a04498f9bc4894a4c5bace"
CURRENT_IMAGE = "16698dd36ac4b919a93e56e948499462cbe41b1ca20c9b20007512339ff35a51"
CURRENT_BOOT = "80d558e5804547749eca849c53ba27e1"
PHASE11_6_BROWSER_REPAIR_REVIEW = "3b8a6535d8a9a186d090d3105f056b9c52b2d268"

EVIDENCE_HASHES = {
    "phase11-5-r2-closure-result.json":
        "3d8d5d029ae51c8cd43109af98287488fccf4edc4f3a8530aaed24ec3297beaa",
    "phase11-5-r3-v2-validation-002.json":
        "2a48abfe8d71dbc9eb8ddca31b0296738f472cc1dccd9fe9e2c39f6be4c7e512",
    "phase11-5-r3-v2-validation-004.json":
        "8e0f37d65bee8dc23ec6770b43ade8a469490c5e0a6b9f23996878e9405fdc0c",
    "phase11-5-r3-v2-validation-006.json":
        "df9180a1335ab8fecd2df34bf0e4e95654fb4d488d4324c08212e4c957450ece",
    "phase11-5-r3-v2-validation-010.json":
        "a038d4e2068b9d28847474d399be9a549a55f7a81707f4df0a50f6aa20cb6cb8",
    "phase11-5-r3-v2-validation-012.json":
        "135298cfcd2079bce726e285c244002d1cc142e84c62680b5c74e2415d6a0af4",
    "phase11-5-r3-v2-validation-043.json":
        "5a503e872b2002758759e163cdcdd988699733bde4f1619840352ad3ed5728c2",
    "phase11-5-memory-pressure-result.json":
        "b81f3b1e5d527ef26fbbee5b96fc5d1bcd993886a3e463f122a23e1c5e0a0d43",
    "phase11-5-event-pages-result.json":
        "7821acc48e7fb56b04518019eb0f17c2b07bde20d10fc3d28b7c191a9e3f240c",
    "phase11-5-package3-result.json":
        "ecd8de77061c36422a95679ea4e83aafc27c9285a1e859f9a574e38632c17f9a",
    "phase11-5-package4-result.json":
        "afd16acff0e041d53119b5e2f788f5fd808feb502974f3f4525d0c9fb36d5621",
    "phase11-5-package4-unread-retest2-result.json":
        "fe55bd1335cd836cb293644d457bff8b2f5e0823cd3bfeb78b1da6b224c2b8d1",
    "phase11-5-package5-result.json":
        "840e0f6eb4a5f7e34b12481c3e2709cf31844ab168f40d43b48c0b6a9fbc4a4d",
}

P1_TO_P24_FILES = [
    "src/encoding/morse.hpp",
    "src/network/api.cpp",
    "src/rf/bench.cpp",
    "src/rf/waveform.cpp",
    "src/standalone/pico/main.cpp",
    "src/standalone/scheduler.cpp",
    "src/wtp/codec.cpp",
    "src/wtp/endpoint.hpp",
    "src/wtp/frame_parser.hpp",
    "src/wtp/inhibited_rf_engine.cpp",
    "src/wtp/inhibited_rf_engine.hpp",
    "src/wtp/job_service.cpp",
    "src/wtp/job_service.hpp",
]
P24_TO_CURRENT_FILES = [
    "src/network/api.cpp",
    "src/standalone/scheduler.cpp",
    "src/wtp/endpoint.cpp",
    "src/wtp/job_service.cpp",
    "src/wtp/job_service.hpp",
]

R3_GROUPS = {
    "JOB-MAX": ["2.1a", "2.1b", "2.1c"],
    "WTP-MAX": ["2.1d", "2.1e"],
    "HTTP-MAX": ["2.1f", "2.1g"],
    "COMBINED": ["2.2a", "2.2b"],
    "TLS-SLOW": ["2.2c"],
    "TLS-FAIL": ["2.2d"],
    "SLOT": ["2.2e"],
    "HTTP-PARTIAL": ["2.2f"],
    "PROGRESS": ["2.3a", "2.3b", "2.3c"],
    "USB": ["2.3d", "2.3e"],
    "TLS-VALID": ["R3.TLS-VALID"],
    "BROWSER-MAX": ["R3.BROWSER-MAX"],
    "RETAINED": ["R3.RETAINED.replay", "R3.RETAINED.session",
                 "R3.RETAINED.terminal"],
    "RECLAIM": ["R3.RECLAIM"],
}
FEATURE_IDS = [f"FEATURE.{number}" for number in range(1, 8)]
GROUP_EVIDENCE = {
    "JOB-MAX": ["phase11-5-memory-pressure-result.json",
                "phase11-5-r3-v2-validation-004.json",
                "phase11-5-r3-v2-validation-006.json",
                "phase11-5-r3-v2-validation-010.json",
                "phase11-5-r3-v2-validation-012.json",
                "phase11-5-package5-result.json"],
    "WTP-MAX": ["phase11-5-memory-pressure-result.json",
                "phase11-5-package5-result.json"],
    "HTTP-MAX": ["phase11-5-memory-pressure-result.json",
                 "phase11-5-event-pages-result.json",
                 "phase11-5-package5-result.json"],
    "COMBINED": ["phase11-5-event-pages-result.json",
                 "phase11-5-package5-result.json"],
    "TLS-SLOW": ["phase11-5-package3-result.json", "phase11-5-package5-result.json"],
    "TLS-FAIL": ["phase11-5-package3-result.json", "phase11-5-package5-result.json"],
    "SLOT": ["phase11-5-package3-result.json", "phase11-5-package5-result.json"],
    "HTTP-PARTIAL": ["phase11-5-package3-result.json",
                     "phase11-5-package5-result.json"],
    "PROGRESS": ["phase11-5-package3-result.json", "phase11-5-package5-result.json"],
    "USB": ["phase11-5-package4-result.json",
            "phase11-5-package4-unread-retest2-result.json",
            "phase11-5-package5-result.json"],
    "TLS-VALID": ["phase11-5-memory-pressure-result.json",
                  "phase11-5-package5-result.json"],
    "BROWSER-MAX": ["phase11-5-package3-result.json",
                    "phase11-5-package5-result.json"],
    "RETAINED": ["phase11-5-package5-result.json"],
    "RECLAIM": ["phase11-5-package5-result.json"],
}
FEATURE_EVIDENCE = {
    "FEATURE.1": ["phase11-5-r3-v2-validation-002.json"],
    "FEATURE.2": ["phase11-5-r3-v2-validation-004.json"],
    "FEATURE.3": ["phase11-5-memory-pressure-result.json",
                  "phase11-5-event-pages-result.json",
                  "phase11-5-package5-result.json"],
    "FEATURE.4": ["phase11-5-r3-v2-validation-006.json",
                  "phase11-5-r3-v2-validation-010.json",
                  "phase11-5-r3-v2-validation-012.json"],
    "FEATURE.5": ["phase11-5-r3-v2-validation-043.json"],
    "FEATURE.6": ["phase11-5-r3-v2-validation-002.json",
                  "phase11-5-r2-closure-result.json"],
    "FEATURE.7": ["phase11-5-event-pages-result.json",
                  "phase11-5-package5-result.json"],
}


def require(value, message):
    if not value:
        raise AssertionError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_output(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args], check=True, stdout=subprocess.PIPE
    ).stdout


def load_evidence(root):
    development = root / "docs" / "development"
    values = {}
    for name, expected_hash in EVIDENCE_HASHES.items():
        path = development / name
        require(path.is_file(), f"Missing immutable input: {name}")
        require(sha256(path) == expected_hash, f"Immutable input hash drift: {name}")
        values[name] = json.loads(path.read_text())
    return values


def validate_inputs(values):
    r2 = values["phase11-5-r2-closure-result.json"]
    require(r2["status"] == "PASS_WITH_EXPLICIT_ADMINISTRATIVE_AMENDMENT" and
            r2["family"] == "R2" and r2["family_closed"] is True and
            r2["completed_jobs"] == r2["required_jobs"] == 7 and
            any("Original OOM" in item for item in r2["limitations"]),
            "R2 mode and preserved-failure input")

    v002 = values["phase11-5-r3-v2-validation-002.json"]
    v004 = values["phase11-5-r3-v2-validation-004.json"]
    v006 = values["phase11-5-r3-v2-validation-006.json"]
    v010 = values["phase11-5-r3-v2-validation-010.json"]
    v012 = values["phase11-5-r3-v2-validation-012.json"]
    require(v002["checkpoint"] == "v2-002" and
            v002["status"] == "PASS_WITH_RECORDED_SCOPE" and
            v002["validation"]["host_ctest"]["count"] == 62,
            "Extended-feature software input")
    require(v004["checkpoint"] == "v2-004" and
            v004["status"] == "PASS_WITH_RECORDED_SCOPE" and
            {"events_513_atomic_rejection", "duration_3600_plus_ns_atomic_rejection",
             "events_512_duration_3600_idle_load"}.issubset(v004["physical_idle_assertions"]),
            "Job-boundary physical input")
    require(v006["checkpoint"] == "v2-006" and
            any("3600-second QRSS" in item for item in v006["validated_assertions"]) and
            v010["checkpoint"] == "v2-010" and
            any("3600-second FSKCW" in item for item in v010["validated_assertions"]) and
            v012["checkpoint"] == "v2-012" and
            any("3600-second, 32-character" in item
                for item in v012["validated_assertions"]),
            "Three physical-hour inputs")

    group1 = values["phase11-5-r3-v2-validation-043.json"]
    require(group1["checkpoint"] == "v2-043" and
            group1["execution_groups_newly_closed"] == [1] and
            any("exit-zero expectation remains FAILED" in item
                for item in group1["limitations"]),
            "Group 1 closure and retained failure")

    p1 = values["phase11-5-memory-pressure-result.json"]
    require(p1["status"] == "REPAIR_AND_BOUNDED_TARGET_RETEST_COMPLETE" and
            p1["source_revision"] == P1_SOURCE and
            set(p1["accepted_assertions"]) ==
            {"2.1a", "2.1d", "2.1e", "2.1f", "2.1g", "R3.TLS-VALID"} and
            p1["capacity"]["minimum_reserve_bytes"] >= 32768,
            "Package 1 capacity input")

    p2 = values["phase11-5-event-pages-result.json"]
    require(p2["status"] == "PACKAGE_2_ACCEPTED" and
            p2["package_assertions"] == {"2.2a": "ACCEPTED", "2.2b": "ACCEPTED"} and
            p2["target"]["source_revision"] == P24_SOURCE and
            p2["supported"]["status"] == "P2_SUPPORTED_VERIFIED" and
            p2["supported"]["http_status"] == 200 and
            p2["overload"]["status"] == "P2_OVERLOAD_VERIFIED" and
            p2["overload"]["http_status"] == 503 and
            p2["overload"]["http_error_code"] == "resource_exhausted" and
            p2["restoration"]["reservation_released"] is True,
            "Package 2 combined input")

    p3 = values["phase11-5-package3-result.json"]
    require(p3["status"] == "PACKAGE_3_ACCEPTED" and
            p3["target"]["source_revision"] == P24_SOURCE and
            set(p3["package_assertions"]) ==
            {"2.2c", "2.2d", "2.2e", "2.2f", "2.3a", "2.3b", "2.3c",
             "R3.BROWSER-MAX"} and
            set(p3["package_assertions"].values()) == {"ACCEPTED"} and
            p3["source_thresholds"]["established_progress_ms"] == 30000 and
            p3["source_thresholds"]["wtp_output_progress_ms"] == 5000 and
            p3["restoration"]["reservation_released"] is True,
            "Package 3 timeout/recovery input")

    p4 = values["phase11-5-package4-result.json"]
    p4e = values["phase11-5-package4-unread-retest2-result.json"]
    require(p4["source_revision"] == P24_SOURCE and
            p4["assertions"]["2.3d"] == "ACCEPTED" and
            p4e["status"] == "PACKAGE4_2_3E_ACCEPTED" and
            p4e["assertion"] == {"2.3e": "ACCEPTED"} and
            p4e["target"]["source_revision"] == P24_SOURCE and
            p4e["package4_status"] == "COMPLETE" and
            p4e["restoration"]["shared_rf_reservation"] == "RELEASED",
            "Package 4 USB inputs")

    p5 = values["phase11-5-package5-result.json"]
    require(p5["status"] == "PACKAGE5_COMPLETE" and
            (p5["source_revision"], p5["image_sha256"], p5["boot_id"]) ==
            (CURRENT_SOURCE, CURRENT_IMAGE, CURRENT_BOOT) and
            set(p5["assertions"]) ==
            {"R3.RETAINED.replay", "R3.RETAINED.session",
             "R3.RETAINED.terminal", "R3.RECLAIM"} and
            set(p5["assertions"].values()) == {"ACCEPTED"} and
            p5["reclamation"]["maximum_post_difference_bytes"] == 8 and
            p5["reclamation"]["required_post_tolerance_bytes"] == 1024 and
            p5["reclamation"]["post_live_growth_monotonic"] is False and
            len(p5["failed_attempts"]) == 4 and
            p5["hardware_charge"]["total"]["rf_jobs"] == 24 and
            p5["restoration"]["reservation_state"] == "RELEASED" and
            p5["restoration"]["host_interfaces_and_routes_restored"] is True,
            "Package 5 current-image/reclamation input")


def validate_source_impact(root, result):
    first = result["source_impact"]["p1_to_packages2_4"]
    second = result["source_impact"]["packages2_4_to_current"]
    final = result["source_impact"]["candidate_to_package6_head"]
    require(first["from"] == P1_SOURCE and first["to"] == P24_SOURCE and
            first["changed_production_files"] == P1_TO_P24_FILES and
            first["diff_sha256"] ==
            "d14c67925d6d426eaafe92671eb215a94ecf45950af276a0929383ed936d46d3",
            "Package 1 to Package 2-4 source-impact declaration")
    require(second["from"] == P24_SOURCE and second["to"] == CURRENT_SOURCE and
            second["changed_production_files"] == P24_TO_CURRENT_FILES and
            second["diff_sha256"] ==
            "0687c89609c7117f893e50b0c117f7506ee77c9d3a108a102d024cf22b40db7f",
            "Package 2-4 to current source-impact declaration")
    require(final == {
        "production_source_diff": "EMPTY",
        "checked_paths": ["src", "firmware", "cmake"],
        "top_level_cmake_diff_sha256":
            "eea78f80bc8bcb2b0b5ffefa0a6b6390fd6d1186d988aaa15e7f3c2b7a498f44",
        "top_level_cmake_change": "host-test-registration-only",
        "decision": "Post-candidate changes are documentation, host-test registration, auditors and hardware fixtures; firmware identity remains 2b25ca05c270.",
    }, "Candidate-to-closeout source-impact declaration")
    require("Packages 2-4 and later Package 5 evidence cover" in first["decision"] and
            "Package 5 physically covers" in second["decision"],
            "Source-impact decisions")

    first_diff = git_output(root, "diff", f"{P1_SOURCE}..{P24_SOURCE}", "--", "src")
    second_diff = git_output(root, "diff", f"{P24_SOURCE}..{CURRENT_SOURCE}", "--", "src")
    require(hashlib.sha256(first_diff).hexdigest() == first["diff_sha256"] and
            hashlib.sha256(second_diff).hexdigest() == second["diff_sha256"],
            "Source-impact diff hashes")
    first_names = git_output(
        root, "diff", "--name-only", f"{P1_SOURCE}..{P24_SOURCE}", "--", "src"
    ).decode().splitlines()
    second_names = git_output(
        root, "diff", "--name-only", f"{P24_SOURCE}..{CURRENT_SOURCE}", "--", "src"
    ).decode().splitlines()
    require(first_names == P1_TO_P24_FILES and second_names == P24_TO_CURRENT_FILES,
            "Source-impact changed-file lists")
    # Package 6 is a historical publication.  Keep this assertion bound to
    # the Phase 11.6 browser-repair review that consumed it; current-source
    # applicability belongs to the Phase 11.7 audit rather than to a moving
    # HEAD comparison here.
    later_names = git_output(
        root, "diff", "--name-only",
        f"{CURRENT_SOURCE}..{PHASE11_6_BROWSER_REPAIR_REVIEW}", "--",
        "src", "firmware", "cmake").decode().splitlines()
    if later_names:
        require(later_names == ["src/network/api.cpp",
                                "src/network/http.hpp",
                                "src/network/pico/server.cpp",
                                "src/network/pico/server.hpp",
                                "src/phase11_6/__init__.py",
                                "src/phase11_6/analysis.py",
                                "src/phase11_6/audit.py",
                                "src/phase11_6/live.py",
                                "src/phase11_6/plan.py",
                                "src/phase11_6/recovery.py",
                                "src/phase11_6/wspr_group.py",
                                "src/rf/pico/pico_pio_dma.cpp",
                                "src/rf/pico/pico_pio_dma.hpp",
                                "src/rf/pio_dma_sink.cpp",
                                "src/rf/pio_dma_sink.hpp",
                                "src/rf/stream_engine.cpp",
                                "src/rf/stream_engine.hpp",
                                "src/standalone/pico/adapters.cpp",
                                "src/standalone/pico/adapters.hpp",
                                "src/standalone/pico/main.cpp",
                                "src/standalone/scheduler.cpp",
                                "src/standalone/storage.hpp",
                                "src/usb/reply_priority.hpp"],
                "Later production drift requires exact Package 8/9 review")
        impact = json.loads((root / "docs/development/phase11-6-browser-"
                             "allocation-repair-source-impact.json").read_text())
        require(impact.get("schema") ==
                    "phase11.6-browser-allocation-repair-source-impact-v1"
                and impact.get("status") == "REQUALIFICATION_REQUIRED"
                and impact.get("firmware_linked_files") == ["src/network/api.cpp"]
                and impact.get("authorization") == {
                    "firmware_deployment": False,
                    "physical_requalification": False,
                    "phase11_6_rf_resume": False,
                }, "Later Phase 11.6 firmware drift must remain unqualified")
        from audit_phase11_5_package8 import validate_result as validate_package8
        package8 = json.loads((root / "docs/development/phase11-5-package8-result.json").read_text())
        validate_package8(package8)
        require(package8["source_impact"]["prior_candidate"] == CURRENT_SOURCE and
                package8["source_impact"]["later_pico_runtime_source_changes"] == 0,
                "Package 8 must carry Package 6 applicability forward")
        package9_path = root / "docs/development/phase11-5-package9-result.json"
        if package9_path.exists():
            from audit_phase11_5_package9 import (PRIOR_SOURCE,
                validate_published_result as validate_package9)
            package9 = json.loads(package9_path.read_text())
            validate_package9(package9)
            require(PRIOR_SOURCE == "7c5296471250cc06416c79a73c9627aed0eb3624" and
                    package9["source_impact"]["prior_candidate"] == PRIOR_SOURCE,
                    "Package 9 must carry Package 6 applicability forward")
    # Keep the Package 6 historical CMake assertion bound to its own closeout
    # commit. Later packages may add their own host-only test registrations.
    cmake_diff = git_output(
        root, "diff", f"{CURRENT_SOURCE}..5e6799c31a4b7a9d714ac1f9a620e6c826ca6459",
        "--", "CMakeLists.txt")
    require(hashlib.sha256(cmake_diff).hexdigest() == final["top_level_cmake_diff_sha256"] and
            sum(line.startswith(b"+    add_test(NAME phase11_5_package")
                for line in cmake_diff.splitlines()) == 2 and
            b"phase11_5_package5_tests" in cmake_diff and
            b"phase11_5_package6_tests" in cmake_diff,
            "Post-candidate CMake change is host-test registration only")


def validate(result, matrix, root):
    require(result["schema"] == "phase11.5-package6-result-v1" and
            result["status"] == "PACKAGE6_COMPLETE_R3_CLOSED",
            "Package 6 schema/status")
    expected_family_status = {
        "R1": "CLOSED 5/5 with recorded applicability",
        "R2": "CLOSED 7/7 with recorded applicability",
        "R3": "CLOSED with Package 6 applicability review",
        "R4": "OPEN", "R5": "OPEN", "R6": "OPEN"}
    require(result["phase11_5_status"] == "OPEN_3_OF_6" and
            result["accepted_configuration"] is None and
            result["family_status"] == expected_family_status,
            "Package 6 family and phase boundary")
    require(result["candidate"] == {
        "board": "Pico A 0BF4B4AEC9FFB344",
        "device_id": "fd6127d11d6aca42a9905fa3fb1bf1d5",
        "source_revision": CURRENT_SOURCE,
        "image_sha256": CURRENT_IMAGE,
        "boot_id": CURRENT_BOOT,
        "system_clock_hz": 138000000,
        "pio_divider": 1,
        "engine": "pio-dma-gp2",
        "renderer": "RAM",
        "network_listener": "configured",
    }, "Candidate identity/configuration")
    require(result["evidence_sha256"] == EVIDENCE_HASHES,
            "Immutable evidence hash manifest")
    values = load_evidence(root)
    validate_inputs(values)
    validate_source_impact(root, result)

    package11_path = root / "docs/development/phase11-5-package11-retry4-result.json"
    package9_path = root / "docs/development/phase11-5-package9-result.json"
    if package11_path.exists():
        from audit_phase11_5_package11 import validate_result as validate_package11
        package11 = validate_package11(json.loads(package11_path.read_text()))
        require(matrix["status"] == "CLOSED" and
                matrix["accepted_configuration"] == package11["accepted_configuration"] and
                matrix["candidate_source"] == package11["accepted_configuration"]
                    ["source_revision"] and
                all(matrix["family_status"][name].startswith("CLOSED")
                    for name in ("R1", "R2", "R3", "R4", "R5", "R6")),
                "Current closed family and accepted-configuration boundary")
    elif package9_path.exists():
        from audit_phase11_5_package9 import validate_published_result as validate_package9
        package9 = validate_package9(json.loads(package9_path.read_text()))
        require(matrix["status"] == "CLOSED" and
                matrix["accepted_configuration"] == package9["accepted_configuration"] and
                matrix["candidate_source"] == package9["accepted_configuration"]
                    ["source_revision"] and
                all(matrix["family_status"][name].startswith("CLOSED")
                    for name in ("R1", "R2", "R3", "R4", "R5", "R6")),
                "Current closed family and accepted-configuration boundary")
    else:
        failure9_path = root / "docs/development/phase11-5-package9-failure-result.json"
        if failure9_path.exists():
            from audit_phase11_5_package9_failure import validate_result as validate_failure9
            failure9 = validate_failure9(json.loads(failure9_path.read_text()))
            matrix_source = failure9["candidate"]["source_revision"]
        else:
            matrix_source = ("7c5296471250cc06416c79a73c9627aed0eb3624"
                             if (root / "docs/development/phase11-5-package8-result.json").exists()
                             else CURRENT_SOURCE)
        require(matrix["status"] == "OPEN" and matrix["accepted_configuration"] is None and
                matrix["candidate_source"] == matrix_source and
                all(matrix["family_status"][name] == expected_family_status[name]
                    for name in ("R1", "R2", "R3")) and
                all(name in matrix["family_status"] for name in ("R4", "R5", "R6")),
                "Current open family and accepted-configuration boundary")

    rows = {row["id"]: row for row in matrix["assertions"]}
    require(len(rows) == len(matrix["assertions"]), "Unique assertion IDs")
    expected_r3_ids = [item for members in R3_GROUPS.values() for item in members]
    require(len(expected_r3_ids) == 24 and
            all(rows[item]["classification"] == "accepted/applicable"
                for item in expected_r3_ids), "Twenty-four accepted R3 rows")
    require(all(rows[item]["classification"] == "accepted/applicable"
                for item in FEATURE_IDS), "Seven accepted extended features")
    require(rows["R1.4"]["classification"] == "accepted/applicable" and
            "phase11-5-package6-result.json" in rows["R1.4"]["evidence"],
            "Current-image R1.4 applicability")
    require("phase11-5-package6-result.json" in rows["FEATURE.3"]["evidence"] and
            "phase11-5-package6-result.json" in rows["FEATURE.7"]["evidence"],
            "Resolved feature evidence pointers")

    groups = result["r3_groups"]
    require(list(groups) == list(R3_GROUPS) and result["counts"] == {
        "r3_groups": 14, "r3_assertions": 24, "extended_features": 7,
        "families_closed": 3, "families_total": 6}, "Group/count summary")
    for name, members in R3_GROUPS.items():
        decision = groups[name]
        require(decision["assertions"] == members and
                decision["disposition"] == "ACCEPTED_APPLICABLE" and
                decision["physical_board"] == "Pico A 0BF4B4AEC9FFB344" and
                decision["evidence"] == GROUP_EVIDENCE[name] and
                len(decision["applicability"]) >= 40, f"R3 group decision: {name}")
        require(all(rows[item]["group"] == name for item in members),
                f"R3 group membership: {name}")

    features = result["extended_features"]
    require(list(features) == FEATURE_IDS and
            all(value["disposition"] == "ACCEPTED_APPLICABLE"
                for value in features.values()), "Extended-feature decisions")
    require(all(features[item]["evidence"] == FEATURE_EVIDENCE[item] and
                len(features[item]["resolution"]) >= 30 for item in FEATURE_IDS),
            "Extended-feature evidence assignments")
    require(features["FEATURE.3"]["resolution"] ==
            "Packages 1, 2 and 5 cover the changed maximum-event and per-path memory behavior" and
            features["FEATURE.7"]["resolution"] ==
            "Packages 2 and 5 cover shared-storage lifetime, expiry and equivalent-cycle reuse",
            "Affected extended-feature resolutions")
    require(result["r1_4_resolution"] == {
        "disposition": "ACCEPTED_APPLICABLE",
        "evidence": "phase11-5-package5-result.json",
        "maximum_post_difference_bytes": 8,
        "limit_bytes": 1024,
        "monotonic_growth": False,
    }, "R1.4 current-image resolution")

    require(result["failed_attempts_preserved"] is True and
            result["package5_failed_attempts"] == 4 and
            result["new_physical_acceptance_assertions"] == 0,
            "No failed-attempt promotion or invented physical credit")
    require(result["package6_review_repairs"] == [
        "Bind the complete candidate clock/engine/renderer/listener configuration.",
        "Bind each R3 group and extended feature to its exact immutable evidence list.",
        "Count only added CMake test-registration lines when classifying post-candidate build metadata.",
    ], "Package 6 review repairs")
    require(result["validation"] == {
        "host_configure": "PASS", "host_build": "PASS",
        "registered_ctest_groups": 76, "registered_ctest_failures": 0,
        "focused_package6_tests": 4, "focused_package6_failures": 0,
        "adversarial_mutations_rejected": 25,
        "python_syntax": "PASS", "json_validation": "PASS",
    }, "Package 6 validation summary")
    require(result["hardware_charge"] == {
        "rf_jobs": 0, "rf_duration_ns": 0, "flashes": 0,
        "bootsel_transitions": 0, "configuration_writes": 0,
        "controlled_reboots": 0, "wifi_cycles": 0, "fixture_mutations": 0,
    }, "Package 6 zero-hardware charge")
    require(result["restoration"] == {
        "basis": "Package 5 final authoritative evidence; Package 6 performed no device or fixture operation",
        "pico_a_state": "empty/inactive/unowned",
        "pico_b_state": "empty/inactive/unowned",
        "scheduling_disabled": True,
        "reservation_state": "RELEASED",
        "host_fixture_restored": True,
    }, "Package 6 inherited final state")
    require(result["remaining"] == [
        "Execute Package 7 and close R4 authority/interruption assertions.",
        "Keep R5, R6 and full Phase 11.5 open.",
        "Do not claim an accepted Phase 11.5 configuration before R4-R6 close.",
    ], "Remaining-scope boundary")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = json.loads(args.result.read_text())
    matrix = json.loads(args.matrix.read_text())
    validate(result, matrix, args.repo.resolve())
    print(json.dumps({
        "schema": "phase11.5-package6-audit-v1",
        "status": "PASS",
        "r3_groups": 14,
        "r3_assertions": 24,
        "extended_features": 7,
        "family_status": "R3_CLOSED",
    }, indent=2))


if __name__ == "__main__":
    main()
