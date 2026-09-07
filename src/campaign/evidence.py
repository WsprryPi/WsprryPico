"""Read-only artifact and matrix validation for a retained Pico campaign."""

import json
from pathlib import Path

from campaign.plan import classify, digest, initial_matrix, validate
from wsprrypi_qualification.wtp_control import validate_transaction


def verify_pico_identity(transaction, result, plan):
    if transaction.get("hello", {}).get("device_id") != result["device_id"]:
        raise ValueError("WTP device differs from campaign identity")
    for key in ("initial_idle", "final_idle"):
        info = transaction.get(key, {})
        if (
            info.get("device_id") != result["device_id"]
            or info.get("revision") != result["revision"]
            or info.get("sample_rate_hz") != plan["sample_rate_hz"]
        ):
            raise ValueError("Pico source or clock differs from campaign identity")


def verify_receiver_identity(metadata, result, frequency):
    expected = dict(
        format="CF32",
        sample_rate_hz=250000,
        bandwidth_hz=200000,
        center_frequency_hz=frequency - 25000,
        gain_db=20,
        channel=0,
        agc=False,
        bias_tee=False,
    )
    if (
        metadata.get("resolved_device")
        != dict(driver="sdrplay", serial=result["receiver_serial"])
        or metadata.get("actual_settings") != expected
    ):
        raise ValueError("Receiver identity or settings differ from campaign")


def verify(directory):
    from campaign.live import sha

    root = Path(directory).resolve()
    index = json.loads((root / "artifacts.json").read_text())
    actual = {
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and p != root / "artifacts.json"
    }
    if set(index) != actual:
        raise ValueError("Artifact inventory mismatch")
    for name, expected in index.items():
        path = root / name
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(root)
            or sha(path) != expected
        ):
            raise ValueError("Artifact hash or containment mismatch: " + name)
    plan = validate(json.loads((root / "plan.json").read_text()))
    result = json.loads((root / "result.json").read_text())
    if result.get("plan_sha256") != digest(plan):
        raise ValueError("Campaign plan digest mismatch")
    if (
        result.get("scope") != plan["scope"]
        or type(result.get("complete")) is not bool
        or type(result.get("cleanup_verified")) is not bool
        or (result["complete"] and result.get("screen_only", False))
    ):
        raise ValueError("Campaign scope or lifecycle claim mismatch")
    expected = initial_matrix(plan)
    rows = result["matrix"]
    if len(rows) != len(expected):
        raise ValueError("Incomplete band/mode matrix")
    for row, requested in zip(rows, expected):
        if any(row[k] != requested[k] for k in ("band", "mode", "frequency_hz")):
            raise ValueError("Band/mode scope mismatch")
        if requested["status"] == "unsupported":
            if row["status"] != "unsupported" or row["observations"]:
                raise ValueError("Unsupported synthesis cannot have RF qualification")
            continue
        if result["complete"]:
            tone_row = next(
                r for r in rows if r["band"] == row["band"] and r["mode"] == "TONE"
            )
            required = plan["repetitions"][row["mode"]]
            if (
                row["mode"] == "WSPR"
                and not row["observations"]
                and tone_row["status"] != "qualified"
            ):
                required = 0
            if len(row["observations"]) != required:
                raise ValueError("Completed campaign has incorrect observation count")
        if len(set(row["observations"])) != len(row["observations"]):
            raise ValueError("Duplicate observation cannot satisfy repetition count")
        observations = []
        for index_number, name in enumerate(row["observations"]):
            path = root / name
            if not path.resolve().is_relative_to(root):
                raise ValueError("Observation escaped campaign")
            observation = json.loads((path / "observation.json").read_text())
            capture_root = path.parent if row["mode"] == "WSPR" else path
            transaction_path = (
                capture_root / f"transmitter-{index_number}.json"
                if row["mode"] == "WSPR"
                else path / "transmitter.json"
            )
            transaction = json.loads(transaction_path.read_text())
            validate_transaction(transaction)
            requested_job = next(b for b in plan["bands"] if b["band"] == row["band"])[
                "jobs"
            ][row["mode"]]
            if any(
                transaction["job"][k] != v
                for k, v in requested_job.items()
                if k != "job_id"
            ):
                raise ValueError("WTP job differs from the band/mode plan")
            if (
                observation.get("passed") is True
                and transaction.get("completed") is not True
            ):
                raise ValueError("Incomplete transmitter job cannot pass")
            if observation.get("cleanup_verified") is not transaction.get(
                "cleanup_verified"
            ):
                raise ValueError("Observation cleanup contradicts WTP evidence")
            from wsprrypi_qualification.capture_metadata import load_capture_metadata

            load_capture_metadata(capture_root / "capture.json")
            metadata = json.loads((capture_root / "capture.json").read_text())
            verify_receiver_identity(metadata, result, row["frequency_hz"])
            if (
                sha(capture_root / "capture.cf32") != observation["capture_sha256"]
                or metadata["output"]["sha256"] != observation["capture_sha256"]
                or metadata["overflow_count"] != 0
                or metadata["clipping"]["sample_count"] != 0
                or metadata["cleanup"]["outcome"] != "verified"
            ):
                raise ValueError("Observation does not bind valid receiver evidence")
            if row["mode"] == "WSPR" and observation.get("passed") is True:
                decoder = json.loads((path / "decode.json").read_text())
                expected = plan["wspr_identity"]
                matches = [
                    line
                    for line in (path / "wsprd.stdout").read_text().splitlines()
                    if len(line.split()) == 8 and line.split()[-3:] == expected
                ]
                if (
                    not observation.get("decoded")
                    or decoder.get("returncode") != 0
                    or not matches
                    or decoder.get("matches") != matches
                ):
                    raise ValueError(
                        "WSPR decode claim contradicts retained decoder output"
                    )
            observations.append(observation)
        status, _ = classify(observations, plan["repetitions"][row["mode"]])
        if not result["cleanup_verified"] and status in ("qualified", "failed"):
            status = "blocked"
        if row["status"] != status:
            raise ValueError("Matrix status contradicts observations")
        if row["mode"] == "WSPR" and row["status"] == "qualified":
            tx = [
                json.loads(
                    (
                        root / (row["band"] + "-WSPR") / f"transmitter-{i}.json"
                    ).read_text()
                )
                for i in range(3)
            ]
            starts = [t["start_utc_ns"] for t in tx]
            if (
                any(b - a != 120000000000 for a, b in zip(starts, starts[1:]))
                or starts[0] % 120000000000 != 1000000000
            ):
                raise ValueError("WSPR observations are not consecutive even UTC slots")
    transactions = 0
    for path in root.rglob("transmitter*.json"):
        transaction = json.loads(path.read_text())
        validate_transaction(transaction)
        verify_pico_identity(transaction, result, plan)
        transactions += 1
    return dict(
        valid=True,
        complete=result["complete"],
        cleanup_verified=result["cleanup_verified"],
        matrix_rows=len(rows),
        wtp_transactions=transactions,
        operational_qualified=sum(r["status"] == "qualified" for r in rows),
        scope=result["scope"],
        limitation="artifact and claim validation; does not independently rerun IQ analysis",
    )
