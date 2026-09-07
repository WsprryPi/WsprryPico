"""Mac USB / wspr5 SSH adapters for the bounded Pico campaign.

OS-specific I/O stays here; the portable plan and measurements never open devices.
"""

import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import time
import uuid

from analyze_rf_bench import load_capture
from check_usb_target import port
from rf_wtp import WtpPeer, read_line, synchronize, write_all
from campaign import analysis
from campaign.plan import RATE, classify, digest, initial_matrix, validate


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, value):
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


class FixtureError(RuntimeError):
    pass


class Rig:
    def __init__(self, args, output):
        self.args, self.output = args, output
        self.log = (output / "progress.jsonl").open("x", buffering=1)
        self.count = 0
        self.capture = None
        self.capture_log = None
        self.capture_deadline = 0
        self.time_fd = self.peer = None
        self.current_job = None
        self.reference_attempted = False

    def event(self, event, **body):
        record = dict(
            utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            event=event,
            **body,
        )
        line = json.dumps(record, allow_nan=False)
        self.log.write(line + "\n")
        print(line, flush=True)

    def remote(self, argv, timeout=30):
        result = subprocess.run(
            ["ssh", self.args.receiver_host, shlex.join(argv)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        self.count += 1
        save(
            self.output / f"remote-{self.count:04}.json",
            dict(
                argv=argv,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            ),
        )
        if result.returncode:
            raise FixtureError("Remote command failed; see retained diagnostic")
        return result.stdout

    def gps(self, operation="read", frequency=None):
        # Project-owned library, structured state including independent PPS.
        action = ""
        if operation == "off":
            action = "d.enable(False,False); d.set_pps(False); "
        elif operation == "on":
            channel = self.args.gpsdo_output
            action = (
                f"d.enable(False,False); d.set_pps(False); d.set_freq({channel - 1},{frequency},False); "
                f"d.set_level({channel - 1},True); d.enable({channel == 1},{channel == 2}); "
            )
        elif operation not in ("read", "active"):
            raise ValueError("invalid GPSDO operation")
        code = (
            "import sys,json; sys.path.insert(0,'/home/pi/lbgpsdo'); import lbe142x; "
            f"d=lbe142x.GPSDODevice.open(serial={self.args.gpsdo_serial!r}); "
            + action
            + "d.read(); print(json.dumps({k:getattr(d,k) for k in "
            "('serial','sat_lock','pll_lock','ant_ok','out1','out2','pps1','f1','f2')})); d.close()"
        )
        state = json.loads(
            self.remote(
                [
                    "timeout",
                    "--kill-after=2s",
                    "40s",
                    "sudo",
                    "-n",
                    "/home/pi/lbgpsdo/.venv/bin/python",
                    "-c",
                    code,
                ],
                45,
            )
        )
        if state["serial"] != self.args.gpsdo_serial:
            raise FixtureError("GPSDO identity mismatch")
        if operation in ("off", "read") and any(
            state[k] for k in ("out1", "out2", "pps1")
        ):
            raise FixtureError("GPSDO frequency or PPS output is active")
        if operation in ("on", "active"):
            ch = self.args.gpsdo_output
            if (
                not state["sat_lock"]
                or not state["pll_lock"]
                or state["pps1"]
                or state[f"f{ch}"] != frequency
                or state[f"out{ch}"] is not True
                or state[f"out{3 - ch}"]
            ):
                raise FixtureError("GPSDO lock, frequency or output state mismatch")
        return state

    def info(self):
        write_all(self.time_fd, b"INFO\n", time.monotonic() + 3)
        value = read_line(self.time_fd, time.monotonic() + 3)
        if (
            value.get("ok") is not True
            or value.get("device_id") != self.args.device_id
            or value.get("revision") != self.args.revision
            or value.get("sample_rate_hz") != RATE
        ):
            raise FixtureError("Pico identity, source revision or clock mismatch")
        return value

    def idle(self):
        value = self.info()
        if value.get("output_active") is not False or value.get("state") not in (
            "empty",
            "loaded",
            "complete",
            "aborted",
            "missed",
            "failed",
        ):
            raise FixtureError(
                "Pico output or execution state is not verified inactive"
            )
        return value

    def wait_until(self, deadline):
        next_progress = time.monotonic() + 30
        while time.time() < deadline:
            self.check_capture()
            time.sleep(min(0.2, max(0, deadline - time.time())))
            if time.monotonic() >= next_progress:
                self.event("waiting", remaining_s=round(deadline - time.time(), 1))
                next_progress = time.monotonic() + 30

    def check_capture(self):
        if self.capture is not None and self.capture.poll() is not None:
            raise FixtureError("Receiver ended before expected RF lifecycle completed")

    def start_capture(self, directory, frequency, seconds):
        if self.capture is not None:
            raise FixtureError("Capture already owned")
        self.directory = directory
        self.remote_dir = "/var/tmp/pico-campaign-" + uuid.uuid4().hex
        self.center = frequency - 25000
        self.samples = round(seconds * 250000)
        self.remote(["mkdir", self.remote_dir])
        self.remote(
            [
                "python3",
                "-c",
                "import shutil,sys; sys.exit(0 if shutil.disk_usage(sys.argv[1]).free>int(sys.argv[2]) else 1)",
                self.remote_dir,
                str(self.samples * 8 + 64000000),
            ]
        )
        argv = [
            self.args.capture_helper,
            "--enable-physical-sdr",
            "sdrplay",
            self.args.sdr_serial,
            str(self.center),
            str(self.samples),
            "20",
            "250000",
            "200000",
            "0",
            "false",
            "false",
            "100000",
            str(seconds + 10),
            self.remote_dir + "/capture.cf32",
            self.remote_dir + "/capture.json",
            directory.name,
        ]
        save(
            directory / "capture-request.json",
            dict(argv=argv, remote_directory=self.remote_dir),
        )
        self.capture_log = (directory / "receiver.log").open("x")
        self.capture = subprocess.Popen(
            ["ssh", self.args.receiver_host, shlex.join(argv)],
            stdout=self.capture_log,
            stderr=subprocess.STDOUT,
        )
        self.capture_deadline = time.monotonic() + seconds + 25
        code = (
            "import os,time,sys; p=sys.argv[1]; end=time.monotonic()+8\n"
            "while time.monotonic()<end:\n"
            " if os.path.exists(p) and os.path.getsize(p)>65536: sys.exit(0)\n"
            " time.sleep(.05)\nsys.exit(1)"
        )
        self.remote(
            ["python3", "-c", code, self.remote_dir + "/capture.cf32.incomplete"], 12
        )
        self.check_capture()
        self.event("capture_ready", directory=str(directory), seconds=seconds)

    def finish_capture(self):
        if self.capture is None:
            raise FixtureError("No owned capture")
        code = self.capture.wait(
            timeout=max(1, self.capture_deadline - time.monotonic())
        )
        self.capture_log.close()
        if code:
            raise FixtureError("Capture helper failed")
        for name in ("capture.cf32", "capture.json"):
            result = subprocess.run(
                [
                    "scp",
                    self.args.receiver_host + ":" + self.remote_dir + "/" + name,
                    str(self.directory / name),
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode:
                raise FixtureError("Capture transfer failed: " + result.stderr)
        from wsprrypi_qualification.capture_metadata import load_capture_metadata

        load_capture_metadata(self.directory / "capture.json")
        iq, meta, checksum = load_capture(
            self.directory / "capture.cf32", self.directory / "capture.json"
        )
        expected = dict(
            format="CF32",
            sample_rate_hz=250000,
            bandwidth_hz=200000,
            center_frequency_hz=self.center,
            gain_db=20,
            channel=0,
            agc=False,
            bias_tee=False,
        )
        if (
            meta["actual_settings"] != expected
            or meta["retained_sample_count"] != self.samples
            or meta["resolved_device"]
            != dict(driver="sdrplay", serial=self.args.sdr_serial)
            or meta.get("overflow_count") != 0
            or meta.get("clipping", {}).get("sample_count") != 0
            or meta.get("first_read", {}).get("discarded") is not True
        ):
            raise FixtureError(
                "Capture settings, count, receiver, clipping or overflow invalid"
            )
        self.capture = None
        return iq, meta, checksum

    def job(self, job, start):
        from wsprrypi_qualification.wtp_control import run_transaction, WtpControlError

        self.idle()
        self.gps("read")

        def before_arm():
            self.wait_until(start - 4)
            return synchronize(self.time_fd, 1000000)

        with port(self.args.wtp_port) as fd:
            time.sleep(0.25)
            # One logical campaign session bounds retained replay state on the
            # Pico. A fresh decoder drops old transport bytes; request counters
            # continue across reconnects so cached replies cannot alias new work.
            previous = self.peer
            peer = self.peer = WtpPeer(
                fd,
                session=previous.session if previous else None,
                sequence=previous.sequence if previous else 0,
            )
            try:
                record = run_transaction(
                    peer,
                    job,
                    device_id=self.args.device_id,
                    start_utc_ns=round(start * 1e6) * 1000,
                    before_arm=before_arm,
                    receiver_ready=self.check_capture,
                    verify_inactive=self.idle,
                )
            except WtpControlError as error:
                save(self.directory / "wtp-failure.json", error.evidence)
                raise
        self.event(
            "job_terminal", mode=job["mode"], state=record["status"].get("state")
        )
        return record

    def reference(self, band):
        directory = self.output / (band["band"] + "-reference")
        directory.mkdir()
        self.idle()
        self.reference_attempted = True
        try:
            before = self.gps("on", band["frequency_hz"])
            self.start_capture(directory, band["frequency_hz"], 5)
            iq, meta, checksum = self.finish_capture()
            after = self.gps("active", band["frequency_hz"])
            from measure_rf_bench import baseband, phase_fit, local_contrast

            bb, rate = baseband(iq, 250000, self.center, band["frequency_hz"])
            fit = phase_fit(
                bb[round(rate) : round(4 * rate)], rate, band["frequency_hz"]
            )
            fit["local_contrast_db"] = local_contrast(
                iq, 250000, self.center, band["frequency_hz"]
            )
            fit["nominal_error_hz"] = fit["indicated_hz"] - band["frequency_hz"]
            fit["usable"] = (
                fit["local_contrast_db"] >= 20
                and fit["phase_residual_rms_rad"] <= 0.15
                and abs(fit["nominal_error_hz"]) <= 100
                and fit["amplitude_min_ratio"] >= 0.5
            )
            save(
                directory / "reference.json",
                dict(
                    state=before,
                    after_capture_state=after,
                    measurement=fit,
                    capture_sha256=checksum,
                    limitation="sequential reference observation; sample-clock and drift uncertainty not calibrated",
                ),
            )
            return fit
        finally:
            self.gps("off")
            self.reference_attempted = False

    def cleanup(self):
        errors = []
        try:
            self.idle()
        except BaseException as error:
            errors.append("Pico inactive state unverified: " + str(error))
        try:
            self.gps("off")
        except BaseException as error:
            errors.append("GPSDO inactive state unverified: " + str(error))
        if self.capture is not None:
            try:
                # The remote helper has a hard deadline and owns SDR cleanup.
                code = self.capture.wait(
                    timeout=max(1, self.capture_deadline - time.monotonic())
                )
                self.capture = None
                metadata = json.loads(
                    self.remote(["cat", self.remote_dir + "/capture.json"])
                )
                if (
                    code != 0
                    or metadata.get("cleanup", {}).get("outcome") != "verified"
                ):
                    errors.append("receiver exit or cleanup metadata failed")
            except BaseException as error:
                errors.append("Receiver cleanup unverified: " + str(error))
        if self.capture_log is not None:
            self.capture_log.close()
        self.event("cleanup", errors=errors)
        return errors


def execute(plan, args):
    validate(plan)
    for token in (args.receiver_host, args.sdr_serial, args.gpsdo_serial):
        if not token or token.startswith("-") or any(c.isspace() for c in token):
            raise ValueError("Invalid host/device selector")
    if Path(args.time_port).resolve() == Path(args.wtp_port).resolve():
        raise ValueError("Console and WTP interfaces must differ")
    if not args.firmware.is_file() or not args.wsprd.is_file():
        raise ValueError("Firmware and independent decoder files are required")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    rig = Rig(args, output)
    matrix = initial_matrix(plan)
    result = dict(
        plan_sha256=digest(plan),
        matrix=matrix,
        complete=False,
        cleanup_verified=False,
        firmware_sha256=sha(args.firmware),
        decoder_sha256=sha(args.wsprd),
        device_id=args.device_id,
        revision=args.revision,
        scope=plan["scope"],
    )
    result["receiver_host"] = args.receiver_host
    result["receiver_serial"] = args.sdr_serial
    result["gpsdo_serial"] = args.gpsdo_serial
    result["gpsdo_output"] = args.gpsdo_output
    result["screen_only"] = args.screen_only
    root = Path(__file__).resolve().parents[2]
    source_files = [
        p
        for part in ("src", "firmware", "cmake", "scripts")
        for p in (root / part).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ]
    source_files += [root / "CMakeLists.txt", root / "CMakePresets.json"]
    result["source_sha256"] = {
        str(p.relative_to(root)): sha(p) for p in sorted(source_files)
    }
    import wsprrypi_qualification.wtp_control as controller

    result["harness_wtp_control_sha256"] = sha(controller.__file__)
    result["harness_carrier_sha256"] = sha(
        analysis.analyze_carrier.__code__.co_filename
    )
    save(output / "plan.json", plan)
    save(output / "result.json", result)
    try:
        with port(args.time_port) as rig.time_fd:
            try:
                time.sleep(0.25)
                result["initial_pico"] = rig.idle()
                result["initial_gpsdo"] = rig.gps("read")
                result["receiver_tools"] = rig.remote(
                    ["sha256sum", args.capture_helper, "/home/pi/lbgpsdo/lbe142x.py"]
                )
                # Screen all bands first, so a later slow WSPR pass does not hide
                # coverage information. Each reference is strictly sequential.
                for band in plan["bands"]:
                    if not band["supported"]:
                        continue
                    row = next(
                        r
                        for r in matrix
                        if r["band"] == band["band"] and r["mode"] == "TONE"
                    )
                    rig.event(
                        "screen", band=band["band"], frequency_hz=band["frequency_hz"]
                    )
                    reference = rig.reference(band)
                    directory = output / (band["band"] + "-TONE")
                    directory.mkdir()
                    rig.gps("read")
                    rig.start_capture(directory, band["frequency_hz"], 17)
                    tx = rig.job(band["jobs"]["TONE"], time.time() + 7)
                    save(directory / "transmitter.json", tx)
                    iq, meta, checksum = rig.finish_capture()
                    observed = analysis.tone(
                        iq, 250000, rig.center, band["frequency_hz"], directory
                    )
                    observed.update(
                        cleanup_verified=tx["cleanup_verified"],
                        fixture_ok=True,
                        capture_sha256=checksum,
                        reference=reference,
                    )
                    observed["passed"] &= tx["completed"]
                    save(directory / "observation.json", observed)
                    row["observations"].append(str(directory.relative_to(output)))
                    row["status"], row["reason"] = classify([observed], 1)
                    save(output / "result.json", result)
                    rig.event("screen_result", band=band["band"], status=row["status"])
                if args.screen_only:
                    return 0
                for band in plan["bands"]:
                    rows = [r for r in matrix if r["band"] == band["band"]]
                    if not band["supported"]:
                        continue
                    for row in rows[1:]:
                        if row["mode"] == "WSPR" and rows[0]["status"] != "qualified":
                            row["reason"] = "carrier screen did not pass"
                            continue
                        mode = row["mode"]
                        rig.event("mode", band=band["band"], mode=mode)
                        observations = []
                        rig.gps("read")
                        if mode == "WSPR":
                            first = (int(time.time() + 15) // 120 + 1) * 120 + 1
                            rig.wait_until(first - 8)
                            directory = output / (band["band"] + "-WSPR")
                            directory.mkdir()
                            rig.start_capture(directory, band["frequency_hz"], 370)
                            transmissions = []
                            for i in range(3):
                                tx = rig.job(band["jobs"][mode], first + i * 120)
                                transmissions.append(tx)
                                save(directory / f"transmitter-{i}.json", tx)
                                if not tx["completed"]:
                                    break
                            iq, meta, checksum = rig.finish_capture()
                            capture_start = datetime.datetime.fromisoformat(
                                meta["timestamps"][
                                    "retained_capture_start_utc"
                                ].replace("Z", "+00:00")
                            ).timestamp()
                            for i, tx in enumerate(transmissions):
                                dest = directory / str(i)
                                dest.mkdir()
                                # Capture wall time selects a generous window; all RF
                                # edges and timing checks use the retained sample axis.
                                left = max(0, first + i * 120 - capture_start - 3)
                                crop = iq[
                                    round(left * 250000) : round((left + 117) * 250000)
                                ]
                                observed = analysis.wspr(
                                    crop,
                                    250000,
                                    rig.center,
                                    band["frequency_hz"],
                                    dest,
                                    args.wsprd.resolve(),
                                    first + i * 120,
                                )
                                observed.update(
                                    cleanup_verified=tx["cleanup_verified"],
                                    fixture_ok=True,
                                    capture_sha256=checksum,
                                    crop_start_s=left,
                                )
                                observed["passed"] &= tx["completed"]
                                save(dest / "observation.json", observed)
                                observations.append(observed)
                                row["observations"].append(
                                    str(dest.relative_to(output))
                                )
                        else:
                            for i in range(3):
                                directory = output / (
                                    band["band"] + "-" + mode + "-" + str(i)
                                )
                                directory.mkdir()
                                job = band["jobs"][mode]
                                rig.start_capture(
                                    directory,
                                    band["frequency_hz"],
                                    int(job["total_duration_ns"]) / 1e9 + 12,
                                )
                                tx = rig.job(job, time.time() + 7)
                                save(directory / "transmitter.json", tx)
                                iq, meta, checksum = rig.finish_capture()
                                observed = analysis.keyed(
                                    iq, 250000, rig.center, band["frequency_hz"], job
                                )
                                observed.update(
                                    cleanup_verified=tx["cleanup_verified"],
                                    fixture_ok=True,
                                    capture_sha256=checksum,
                                )
                                observed["passed"] &= tx["completed"]
                                save(directory / "observation.json", observed)
                                observations.append(observed)
                                row["observations"].append(
                                    str(directory.relative_to(output))
                                )
                        row["status"], row["reason"] = classify(observations, 3)
                        save(output / "result.json", result)
                        rig.event(
                            "mode_result",
                            band=band["band"],
                            mode=mode,
                            status=row["status"],
                        )
                result["complete"] = True
            finally:
                errors = rig.cleanup()
                result["cleanup_verified"] = not errors
                result["cleanup_errors"] = errors
    except BaseException as error:
        result["error"] = str(error)
        rig.event("campaign_error", error=str(error))
        if isinstance(error, KeyboardInterrupt):
            result["error"] = "operator interrupted"
        else:
            raise
    finally:
        if not result["cleanup_verified"]:
            for row in matrix:
                if row["status"] in ("qualified", "failed"):
                    row.update(status="blocked", reason="campaign cleanup unverified")
        save(output / "result.json", result)
        rig.log.close()
        hashes = {
            str(p.relative_to(output)): sha(p)
            for p in sorted(output.rglob("*"))
            if p.is_file() and p != output / "artifacts.json"
        }
        save(output / "artifacts.json", hashes)
    return 0 if result["complete"] and result["cleanup_verified"] else 1
