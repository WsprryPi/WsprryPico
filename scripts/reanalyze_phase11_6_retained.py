#!/usr/bin/env python3
"""Fresh zero-RF analysis of a retained Phase 11.6 physical result.

The original analysis is never modified.  The retained run-result must already
bind the exact raw capture and metadata; this tool adds a new analysis bound to
that physical result's actual WTP job identity.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
from pathlib import Path
import platform
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

ANALYSIS_TOOLS = (
    "scripts/reanalyze_phase11_6_retained.py",
    "src/phase11_6/analysis.py",
    "scripts/analyze_rf_bench.py",
    "scripts/measure_rf_bench.py",
    "src/campaign/analysis.py",
    "src/campaign/plan.py",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


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
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--run-result", type=Path, required=True)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--qualification-src", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    require(hashlib.sha256(canonical(plan)).hexdigest() == args.plan_sha256,
            "historical plan digest")
    jobs = [job for packet in plan.get("packets", []) for job in packet.get("jobs", [])
            if job.get("id") == args.job_id]
    require(len(jobs) == 1 and jobs[0].get("mode") != "WSPR",
            "exact non-WSPR historical job")
    run = json.loads(args.run_result.read_text())
    capture_sha, metadata_sha = sha256(args.capture), sha256(args.metadata)
    actual = run.get("wtp_job_id")
    require(
        run.get("schema") == "phase11.6-job-result-v1"
        and run.get("job_id") == args.job_id
        and re.fullmatch(r"[0-9a-f]{32}", actual or "") is not None
        and run.get("capture", {}).get("capture_sha256") == capture_sha
        and run.get("capture", {}).get("metadata_sha256") == metadata_sha
        and run.get("released_status", {}).get("output_active") is False
        and run.get("released_status", {}).get("owner_id") is None,
        "retained physical result/capture/terminal binding",
    )
    metadata = json.loads(args.metadata.read_text())
    require(
        metadata.get("output", {}).get("sha256") == capture_sha
        and metadata.get("resolved_device")
            == {"driver": "sdrplay", "serial": "2404058C60"}
        and metadata.get("overflow_count") == 0
        and metadata.get("clipping", {}).get("sample_count") == 0,
        "retained receiver metadata binding",
    )
    qualification_src = args.qualification_src.resolve(strict=True)
    sys.path.insert(0, str(qualification_src))
    harness_carrier = importlib.import_module("wsprrypi_qualification.carrier")
    from phase11_6.analysis import analyze
    harness_path = Path(harness_carrier.__file__).resolve(strict=True)
    require(harness_path.is_relative_to(qualification_src),
            "qualification analyzer source root")
    job = copy.deepcopy(jobs[0])
    result = analyze(
        job,
        args.capture.resolve(strict=True),
        args.metadata.resolve(strict=True),
        args.output,
        tool_provenance=tool_provenance(harness_path),
        actual_wtp_job_id=actual,
        physical_result_sha256=sha256(args.run_result),
    )
    print(json.dumps({
        "passed": result["passed"],
        "job_id": result["job_id"],
        "wtp_job_id": result["wtp_job_id"],
        "physical_result_sha256": result["physical_result_sha256"],
    }, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
