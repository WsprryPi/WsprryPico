#!/usr/bin/env python3
"""Summarize charged Package 9 ARM submissions without publishing private data."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from phase11_5_pilot import Decoder


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_decoder(path):
    spec = importlib.util.spec_from_file_location("package9_attempt_tls_decoder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def production_messages(path, decoder_module):
    records = decoder_module.decode(path.read_bytes())
    messages = []
    for connection in sorted({row["connection_id"] for row in records}):
        decoder = Decoder()
        for record in records:
            if record["connection_id"] == connection and record["kind"] == 3:
                messages.extend(decoder.feed(record["payload"]))
    return messages


def one(root, decoder_module):
    packet_path, journal_path = root / "packet.json", root / "campaign.jsonl"
    packet = json.loads(packet_path.read_text()) if packet_path.is_file() else {}
    records = ([json.loads(line) for line in journal_path.read_text().splitlines()]
               if journal_path.is_file() else [])
    jobs = {}
    requests = [row["value"]["request"] for row in records
                if row.get("kind") == "normalizer_tx"]
    loads = {request["body"]["job_id"]: int(request["body"]["total_duration_ns"])
             for request in requests if request.get("op") == "LOAD"}
    for request in requests:
        if request.get("op") == "ARM":
            job_id = request["body"]["job_id"]
            jobs[job_id] = {"path": "normalizer", "duration_ns": loads[job_id]}
    for path in sorted(root.glob("production-*-tls.bin")):
        try:
            messages = production_messages(path, decoder_module)
        except Exception:
            continue
        loads = {message["body"]["job_id"]: int(message["body"]["total_duration_ns"])
                 for message in messages if message.get("type") == "request" and
                 message.get("op") == "LOAD"}
        for message in messages:
            if message.get("type") == "request" and message.get("op") == "ARM":
                job_id = message["body"]["job_id"]
                jobs[job_id] = {"path": "production", "duration_ns": loads[job_id]}
    production_duration = packet.get("normal_load", {}).get("production", {}).get(
        "duration_ns", 0)
    for record in records:
        if record.get("kind") != "usb_status":
            continue
        status = record["value"]["value"]
        if status.get("job_id") and status.get("state") in ("armed", "running", "complete"):
            jobs.setdefault(status["job_id"], {"path": "production-observed",
                                               "duration_ns": production_duration})
    failures = [record["value"] for record in records if record.get("kind") == "failure"]
    deployment_path = root / "deployment.json"
    deployment = json.loads(deployment_path.read_text()) if deployment_path.is_file() else {}
    # A rejected post-flash image can stop before deployment.json is written.
    # Preserve that charged mutation when the frozen packet declares it and the
    # picotool load command was actually launched. A preflight-only failure has
    # no candidate-load artifact and remains zero-charge.
    attempted_flash = (root / "candidate-load.stdout").is_file()
    charged = deployment if deployment else packet if attempted_flash else {}
    result = {
        "attempt": root.name,
        "packet_sha256": digest(packet_path) if packet_path.is_file() else None,
        "journal_sha256": digest(journal_path) if journal_path.is_file() else None,
        "charged_rf_jobs": len(jobs),
        "charged_rf_duration_ns": sum(job["duration_ns"] for job in jobs.values()),
        "charged_paths": {name: sum(job["path"] == name for job in jobs.values())
                          for name in ("normalizer", "production", "production-observed")
                          if any(job["path"] == name for job in jobs.values())},
        "failure": failures[-1] if failures else None,
        "campaign_result": digest(root / "campaign-result.json")
            if (root / "campaign-result.json").is_file() else None,
        "flashes": charged.get("flashes", 0),
        "bootsel": charged.get("bootsel", 0),
        "configuration_writes": charged.get("configuration_writes", 0),
        "controlled_reboots": charged.get("controlled_reboots", 0),
        "wifi_cycles": charged.get("wifi_cycles", 0),
    }
    return result


def attempt_roots(base):
    """Include dated campaigns and separately named repair deployments."""
    return sorted((path for path in base.glob("phase11-5-package9*")
                   if path.is_dir()), key=lambda path: path.name)


def audit(base, decoder_path):
    decoder = load_decoder(decoder_path)
    roots = attempt_roots(base)
    attempts = [one(root, decoder) for root in roots]
    return {"schema": "phase11.5-package9-attempt-history-v1", "status": "PASS",
        "attempts": attempts, "attempt_count": len(attempts),
        "charged_rf_jobs": sum(value["charged_rf_jobs"] for value in attempts),
        "charged_rf_duration_ns": sum(value["charged_rf_duration_ns"] for value in attempts),
        "flashes": sum(value["flashes"] for value in attempts),
        "bootsel": sum(value["bootsel"] for value in attempts),
        "configuration_writes": sum(value["configuration_writes"] for value in attempts),
        "controlled_reboots": sum(value["controlled_reboots"] for value in attempts),
        "wifi_cycles": sum(value["wifi_cycles"] for value in attempts),
        "decoder_sha256": digest(decoder_path), "auditor_sha256": digest(Path(__file__))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--decoder", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.base.resolve(strict=True),
                           args.decoder.resolve(strict=True)), indent=2))


if __name__ == "__main__":
    main()
