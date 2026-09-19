#!/usr/bin/env python3
"""Stage and run the exact zero-RF admission for the Phase 11.6 closure slice."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import phase11_6_browser_repair_requal as base  # noqa: E402
from phase11_6.live import (CAPTURE_HELPER_SHA256, configure_capture_validator,
                            require_capture_helper, sha256)  # noqa: E402
from phase11_6.plan import (COMPANION_BINARY_SHA256, COMPANION_SOURCE,
                            FIRMWARE_SOURCE, FIRMWARE_UF2_SHA256,
                            PEER_ACCEPTED_BOOT, PICO_ACCEPTED_BOOT, compact_job,
                            digest, validate)  # noqa: E402


CLOSURE_PLAN_SHA256 = (
    "4733941d6dd6b7ff80b8dceaa819397c12b6e49bd0512df0f902df44cb29b0fe"
)
MATRIX_SHA256 = "f5dc043da0cf3b0e398777d07e5e6146b2faf76b5e94c7fed8797a5cbb33467f"
DEPLOYMENT_RESULT = "phase11-6-status-repair-corrected-deployment-20260919"


def save_new(path: Path, value: object) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def command(args: list[str]) -> str:
    result = subprocess.run(args, capture_output=True, text=True, timeout=30,
                            check=False)
    base.require(result.returncode == 0, "Admission command failed: " + args[0])
    return result.stdout.strip()


def stage(args: argparse.Namespace) -> tuple[Path, str]:
    fixture = args.root.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(mode=0o700)
    base.require(output.stat().st_mode & 0o077 == 0 and not any(output.iterdir()),
                 "Fresh private admission output required")
    plan_path = fixture / "plan.json"
    closure_path = fixture / "closure-plan.json"
    matrix_path = fixture / "matrix.json"
    plan = validate(json.loads(plan_path.read_text()))
    closure = json.loads(closure_path.read_text())
    matrix = json.loads(matrix_path.read_text())
    base.require(
        sha256(closure_path) == CLOSURE_PLAN_SHA256
        and sha256(matrix_path) == MATRIX_SHA256
        and closure.get("matrix") == "phase11-6-matrix.json"
        and closure.get("current_candidate", {}).get("source_revision")
            == FIRMWARE_SOURCE
        and closure.get("current_candidate", {}).get("uf2_sha256")
            == FIRMWARE_UF2_SHA256
        and closure.get("current_candidate", {}).get("boot_id")
            == PICO_ACCEPTED_BOOT
        and closure.get("companion", {}).get("source_revision")
            == COMPANION_SOURCE
        and closure.get("companion", {}).get("binary_sha256")
            == COMPANION_BINARY_SHA256
        and closure.get("peer", {}).get("boot_id") == PEER_ACCEPTED_BOOT
        and matrix.get("phase_status") == "OPEN",
        "Frozen closure plan and matrix binding",
    )
    fixture_state = json.loads((fixture / "fixture-state.json").read_text())
    remote_ready = json.loads((fixture / "remote-ready.json").read_text())
    base.require(
        fixture_state.get("ready") is True
        and fixture_state.get("restored") is not True
        and remote_ready.get("host") == "wspr4"
        and remote_ready.get("host_boot_id")
            == "5fbac52a-9d54-497f-8623-1476a380fcad"
        and (fixture / "installed-paused.txt").read_text()
            == "MainPID=0\nActiveState=inactive\n",
        "Exact active fixture and schedule exclusion required",
    )
    helper = require_capture_helper(args.capture_helper)
    validator = configure_capture_validator(args.qualification_src)
    binary = args.production_binary.resolve(strict=True)
    companion = args.companion_checkout.resolve(strict=True)
    base.require(
        sha256(binary) == COMPANION_BINARY_SHA256
        and command(["git", "-C", str(companion), "rev-parse", "HEAD"])
            == COMPANION_SOURCE,
        "Exact companion source and binary required",
    )
    deployment = args.deployment_root.resolve(strict=True)
    deployment_result = json.loads((deployment / "deployment-result.json").read_text())
    base.require(
        deployment.name == DEPLOYMENT_RESULT
        and sha256(deployment / "candidate.uf2") == FIRMWARE_UF2_SHA256
        and deployment_result.get("source_revision") == FIRMWARE_SOURCE[:12]
        and deployment_result.get("image_sha256") == FIRMWARE_UF2_SHA256
        and deployment_result.get("new_boot_id") == PICO_ACCEPTED_BOOT
        and deployment_result.get("result") == "PASS",
        "Exact retained image, board deployment and boot evidence required",
    )
    receiver = command([
        "/usr/bin/SoapySDRUtil", "--find=driver=sdrplay,serial=2404058C60",
    ])
    base.require(
        receiver.count("Found device") == 1
        and re.search(r"(?m)^\s*driver = sdrplay$", receiver) is not None
        and re.search(r"(?m)^\s*serial = 2404058C60$", receiver) is not None,
        "Exact sole SDRplay RSP1B receiver required",
    )
    reservation = json.loads(
        Path("/home/pi/phase11-5-shared-rf-reservation.json").read_text()
    )
    base.require(
        reservation.get("state") == "RELEASED"
        and reservation.get("boards", {}).get("a", {}).get("boot_id")
            == PICO_ACCEPTED_BOOT
        and reservation.get("boards", {}).get("b", {}).get("boot_id")
            == PEER_ACCEPTED_BOOT,
        "Released shared reservation with exact A/B identities required",
    )
    prerequisites = {
        "schema": "phase11.6-closure-admission-prerequisites-v1",
        "plan_sha256": digest(plan),
        "plan_file_sha256": sha256(plan_path),
        "closure_plan_file_sha256": sha256(closure_path),
        "matrix_file_sha256": sha256(matrix_path),
        "source_revision": FIRMWARE_SOURCE,
        "uf2_sha256": FIRMWARE_UF2_SHA256,
        "boot_id": PICO_ACCEPTED_BOOT,
        "board": "Pico 2 W / RP2350 Arm Secure",
        "system_clock_hz": 138_000_000,
        "pio_divider": 1,
        "engine": "pio-dma-gp2",
        "renderer": "RAM",
        "output": "GP2",
        "peer_boot_id": PEER_ACCEPTED_BOOT,
        "companion_source_revision": COMPANION_SOURCE,
        "companion_binary_sha256": sha256(binary),
        "capture_helper_sha256": sha256(helper),
        "capture_validator_sha256": validator,
        "receiver_inventory_sha256": hashlib.sha256(receiver.encode()).hexdigest(),
        "receiver": {
            "driver": "sdrplay", "serial": "2404058C60",
            "sample_rate_hz": 250_000, "bandwidth_hz": 200_000,
            "gain_db": 20, "agc": False, "bias_tee": False,
            "frequency_correction_ppm": 0,
        },
        "rf_path": plan["rf_path_declaration"],
        "reservation": reservation,
        "fixture_pid": args.fixture_pid,
        "automatic_retries": 0,
    }
    prerequisites_path = output / "prerequisites.json"
    save_new(prerequisites_path, prerequisites)
    (output / "receiver-inventory.txt").write_text(receiver + "\n")
    job = compact_job("FSKCW", 137_500, "closure-zero-rf-" + uuid.uuid4().hex)
    save_new(output / "job.json", job)
    shutil.copy2(fixture / "scripts/phase11_6_browser_submit.js",
                 output / "browser-submit.js")
    base.FIXTURE = fixture
    base.SOURCE = FIRMWARE_SOURCE
    base.BOOT = PICO_ACCEPTED_BOOT
    base.FIXTURE_PID = args.fixture_pid
    base.PACKET_SCHEMA = "phase11.6-closure-zero-rf-admission-v1"
    base.AUTHORIZATION = "PHASE11.6-FINAL-REMAINING-RF-20260919"
    base.RESULT_SCHEMA = "phase11.6-closure-zero-rf-admission-result-v1"
    base.IMAGE_SHA256 = FIRMWARE_UF2_SHA256
    base.SUBMISSION_KIND = "compact"
    base.EXTRA_PACKET_FIELDS = {
        "prerequisites_sha256": sha256(prerequisites_path),
        "closure_plan_file_sha256": CLOSURE_PLAN_SHA256,
        "matrix_file_sha256": MATRIX_SHA256,
        "plan_sha256": digest(plan),
        "companion_source_revision": COMPANION_SOURCE,
        "companion_binary_sha256": COMPANION_BINARY_SHA256,
        "capture_helper_sha256": CAPTURE_HELPER_SHA256,
    }
    base.__file__ = __file__
    packet = {
        "schema": base.PACKET_SCHEMA,
        "authorization": base.AUTHORIZATION,
        "source_revision": base.SOURCE,
        "boot_id": base.BOOT,
        "image_sha256": base.IMAGE_SHA256,
        "submission_kind": base.SUBMISSION_KIND,
        "browser_script_sha256": sha256(output / "browser-submit.js"),
        "runner_sha256": sha256(Path(__file__).resolve()),
        "job_sha256": sha256(output / "job.json"),
        "fixture_pid": args.fixture_pid,
        "limits": {"rf_jobs": 0, "arms": 1, "aborts": 1, "flashes": 0,
                   "bootsel": 0, "configuration_writes": 0, "retries": 0},
        **base.EXTRA_PACKET_FIELDS,
    }
    save_new(output / "packet.json", packet)
    return output, sha256(output / "packet.json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixture-pid", type=int, required=True)
    parser.add_argument("--capture-helper", type=Path, required=True)
    parser.add_argument("--qualification-src", type=Path, required=True)
    parser.add_argument("--production-binary", type=Path, required=True)
    parser.add_argument("--companion-checkout", type=Path, required=True)
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--run", action="store_true", required=True)
    args = parser.parse_args()
    base.require(os.geteuid() == 0 and args.fixture_pid > 1,
                 "Linux root and exact fixture PID required")
    output, packet_hash = stage(args)
    sys.argv = [str(Path(__file__).resolve()), "--root", str(output),
                "--packet-sha256", packet_hash, "--run"]
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
