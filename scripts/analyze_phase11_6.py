#!/usr/bin/env python3
"""Analyze one retained Phase 11.6 capture without opening hardware."""

import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
import platform
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

ANALYSIS_TOOLS = (
    "scripts/analyze_phase11_6.py",
    "src/phase11_6/analysis.py",
    "src/phase11_6/plan.py",
    "scripts/phase11_6_attempt.py",
    "scripts/analyze_rf_bench.py",
    "scripts/measure_rf_bench.py",
    "scripts/decode_rf_wspr.py",
    "src/campaign/analysis.py",
    "src/campaign/plan.py",
)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tool_provenance(harness_path: Path) -> dict:
    return {
        "schema": "phase11.6-analysis-tools-v1",
        "source_sha256": {
            **{relative: sha256(ROOT / relative) for relative in ANALYSIS_TOOLS},
            "wsprrypi_qualification/carrier.py": sha256(harness_path),
        },
        "python_version": platform.python_version(),
        "numpy_version": np.__version__,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--attempt-packet", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wsprd", type=Path)
    parser.add_argument("--qualification-src", type=Path, required=True)
    args = parser.parse_args()
    qualification_src = args.qualification_src.resolve(strict=True)
    sys.path.insert(0, str(qualification_src))
    harness_carrier = importlib.import_module("wsprrypi_qualification.carrier")
    harness_path = Path(harness_carrier.__file__).resolve(strict=True)
    if not harness_path.is_relative_to(qualification_src):
        raise ValueError("Qualification analyzer resolved outside the bound source root")
    from phase11_6.analysis import analyze
    from phase11_6.plan import validate
    from phase11_6_attempt import check as validate_attempt
    plan = validate(json.loads(args.plan.read_text()))
    jobs = [job for packet in plan["packets"] for job in packet["jobs"]
            if job["id"] == args.job_id]
    if len(jobs) != 1:
        raise ValueError("Exact Phase 11.6 job not found")
    attempt = json.loads(args.attempt_packet.read_text())
    validate_attempt(attempt, plan, args.plan.resolve().parent)
    if attempt["job_id"] != args.job_id:
        raise ValueError("Attempt packet job mismatch")
    job = copy.deepcopy(jobs[0])
    job["expected_job"] = copy.deepcopy(attempt["effective_job"])
    result = analyze(
        job, args.capture, args.metadata, args.output, args.wsprd,
        tool_provenance=tool_provenance(harness_path),
    )
    print(json.dumps({"passed": result["passed"], "job_id": result["job_id"]}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
