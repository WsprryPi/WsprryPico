#!/usr/bin/env python3
"""Offline assertion-level audit for the Phase 11.7 joint closure record."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


PICO_TESTED = "95aac22bf7cc31b67fe5773761708d743d8a6473"
PICO_CANDIDATE = "0e85ff90571c800450073f7b0bfafd70266f1f44"
PI_BASE = "c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf"
PI_TESTED = "2298a268d8139409ed650d2311d794b3813d99ab"
PICO_LATER_FILES = {
    "cmake/network_client_interop.cmake",
    "cmake/network_host_tests.cmake",
    "src/phase11_6/live.py",
    "src/phase11_6/plan.py",
    "src/phase11_6/reconciliation.py",
}
PI_LATER_FILES = {
    "src/tests/network/CMakeLists.txt",
    "src/tests/network/pico-reference-revision.txt",
}
EXPECTED_COUNTS = {
    "PASS": 13,
    "FAIL": 9,
    "BLOCKED": 12,
    "NOT TESTED": 31,
    "UNSUPPORTED_CONFIGURATION": 10,
}
EXPECTED_PHASES = {f"11.{number}" for number in range(1, 8)}
EXPECTED_VALIDATIONS = {
    "pico_host_ctest", "pico_wtp_contract", "pico_sanitizers", "pi_core_suites",
    "pi_network_interop", "pi_sanitizers", "offline_closure_audit",
    "adversarial_mutations",
}
EXPECTED_OPERATIONS = {
    "hardware_operations", "rf_operations", "device_connections", "fixture_operations",
    "trust_store_changes", "service_or_network_changes",
}
RUNTIME_PATHS = [
    "firmware",
    "src/encoding",
    "src/network",
    "src/rf",
    "src/standalone",
    "src/time",
    "src/usb",
    "src/wtp",
]
PI_RUNTIME_PATHS = ["src/WTP-Client", "src/wtp_integration", "src/WSPR-Transmitter"]


def require(value, message):
    if not value:
        raise AssertionError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_names(root, older, newer, paths):
    return subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", f"{older}..{newer}", "--", *paths],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()


def working_names(root, older, paths):
    return subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", older, "--", *paths],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.splitlines()


def matrix_pass_rows(matrix):
    rows = []
    for row in matrix["rows"]:
        if row["disposition"] != "PASS":
            continue
        accepted_sequences = [
            attempt["sequence"]
            for attempt in row["evidence"]["attempts"]
            if "analysis_sha256" in attempt
        ]
        rows.append(
            {
                "band": row["band"],
                "mode": row["mode"],
                "frequency_hz": row["nominal_frequency_hz"],
                "lineages": row["evidence"]["source_lineages"],
                "sequences": accepted_sequences,
            }
        )
    return rows


def validate(root, result, pi_root=None):
    development = root / "docs" / "development"
    matrix = json.loads((development / "phase11-6-matrix.json").read_text())
    scope = json.loads((development / "phase11-6-scope-disposition.json").read_text())

    require(result["schema"] == "phase11.7-joint-closure-v1", "Phase 11.7 schema")
    require(result["status"] == "CLOSED_SCOPED", "Phase 11.7 final status")
    require(result["phase11_7_closed"] is True, "Phase 11.7 closure flag")
    require(result["phase11_closed_within_documented_scope"] is True,
            "Scoped Phase 11 closure flag")
    require(result["repositories"]["pico"]["tested_revision"] == PICO_TESTED,
            "Pico tested revision")
    require(result["repositories"]["pi"]["tested_revision"] == PI_TESTED,
            "Pi tested revision")
    require(result["repositories"]["pico"]["interop_pi_pin"] == PI_BASE,
            "Pico companion pin")
    require(result["repositories"]["pi"]["interop_pico_pin"] == PICO_TESTED,
            "Pi companion pin")

    require(result["phase11_6"]["status"] == "CLOSED_SCOPED", "11.6 scope status")
    require(result["phase11_6"]["disposition_counts"] == EXPECTED_COUNTS,
            "11.6 disposition counts")
    require(matrix["disposition_counts"] == EXPECTED_COUNTS, "Authoritative matrix counts")
    require(scope["counts"] == {
        "accepted": 13, "removed_supported": 52, "configuration_boundary": 10,
    }, "Scope-decision counts")
    require(result["phase11_6"]["accepted_rows"] == matrix_pass_rows(matrix),
            "Exact accepted row, lineage and attempt bindings")
    require(len(result["phase11_6"]["accepted_rows"]) == 13, "Exactly 13 accepted rows")
    require(not any(row["mode"] == "WSPR" for row in result["phase11_6"]["accepted_rows"]),
            "No accepted WSPR row")
    require(result["phase11_6"]["wspr_rows_accepted"] == 0, "WSPR count remains zero")
    require(result["phase11_6"]["last_sequence"] == 177 and
            result["phase11_6"]["remaining_unexecuted_jobs"] == 80 and
            result["phase11_6"]["campaign_authority_consumed"] is True and
            result["phase11_6"]["further_rf_authorized"] is False,
            "Consumed Phase 11.6 campaign authority")

    for name, identity in result["phase11_6"]["lineages"].items():
        authoritative = matrix["evidence_lineages"][name]
        for key in ("source_revision", "uf2_sha256", "boot_id"):
            require(identity[key] == authoritative[key], f"{name} {key} identity")
    require(result["phase11_6"]["lineages"]["status_admission_current"]
            ["matrix_credit_from_requalification"] is False,
            "Repair requalification earns no matrix credit")

    for relative, expected in result["historical_artifact_sha256"].items():
        path = root / relative
        require(path.is_file() and digest(path) == expected,
                f"Immutable artifact identity: {relative}")

    ledger = result["assertion_ledger"]
    require({entry["id"] for entry in ledger} == EXPECTED_PHASES,
            "One closure assertion for each Phase 11 slice")
    required_fields = {
        "id", "claim", "owner", "supporting_artifacts", "source_configuration",
        "evidence_type", "subsequent_relevant_changes", "applicability", "limitations",
    }
    for entry in ledger:
        require(required_fields == set(entry), f"Complete assertion ledger entry {entry.get('id')}")
        require(all(entry[field] for field in required_fields),
                f"Nonempty assertion ledger entry {entry['id']}")
    require(next(entry for entry in ledger if entry["id"] == "11.7")["applicability"] ==
            "APPLICABLE_SCOPED", "11.7 final applicability")

    source_changes = set(git_names(root, PICO_CANDIDATE, PICO_TESTED,
                                   ["CMakeLists.txt", "firmware", "src", "cmake"]))
    require(source_changes == PICO_LATER_FILES, "Pico candidate-to-tested source file set")
    require(not working_names(root, PICO_TESTED, RUNTIME_PATHS),
            "No later Pico production-runtime drift")
    require(PI_BASE in (root / "cmake/network_client_interop.cmake").read_text() and
            PI_BASE in (root / "scripts/verify_wsprrypi_client.py").read_text(),
            "Pico integration checks share the Pi pin")

    if pi_root is not None:
        pi_root = Path(pi_root).resolve(strict=True)
        require(set(git_names(pi_root, PI_BASE, PI_TESTED,
                              ["src/WTP-Client", "src/wtp_integration",
                               "src/WSPR-Transmitter", "src/tests/network"])) == PI_LATER_FILES,
                "Pi base-to-tested source file set")
        require(not working_names(pi_root, PI_TESTED, PI_RUNTIME_PATHS),
                "No later Pi production-runtime drift")
        require((pi_root / "src/tests/network/pico-reference-revision.txt").read_text().strip()
                == PICO_TESTED, "Pi canonical Pico pin")

    validations = result["fresh_validation"]
    require(set(validations) == EXPECTED_VALIDATIONS, "Exact fresh-validation inventory")
    require(all(value["status"] in {"PASS", "PASS_WITH_DOCUMENTED_SKIP"}
                for value in validations.values()), "All fresh validation entries pass")
    require(validations["pico_host_ctest"]["groups"] >= 79,
            "Complete Pico CTest group count")
    require(validations["adversarial_mutations"]["count"] >= 15,
            "Adversarial mutation coverage")

    external = result["external_operator_documentation"]
    require(external["modified_by_phase11_7"] is False and
            external["blocks_phase11_closure"] is False and
            len(external["follow_ups"]) == 6 and
            all(item["classification"].startswith("NONBLOCKING")
                for item in external["follow_ups"]),
            "External operator-documentation disposition")
    require(set(result["operations"]) == EXPECTED_OPERATIONS and
            set(result["operations"].values()) == {0},
            "No hardware or external mutations")
    require(result["future_work"]["phase12"].startswith("OPEN") and
            result["future_work"]["phase13"].startswith("OPEN"),
            "Phases 12 and 13 remain open")
    language = json.dumps(result).lower()
    require("disconnect proves output inactive" not in language and
            "terminal event proves output inactive" not in language and
            "host tests prove target timing" not in language,
            "No false output-authority or host-to-target qualification claim")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path,
                        default=Path("docs/development/phase11-7-result.json"))
    parser.add_argument("--pi-root", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = json.loads(args.result.read_text())
    validate(root, result, args.pi_root)
    print(json.dumps({
        "schema": "phase11.7-offline-audit-v1",
        "status": "PASS",
        "accepted_rows": 13,
        "wspr_rows_accepted": 0,
        "hardware_operations": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
