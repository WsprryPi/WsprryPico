#!/usr/bin/env python3

import copy
import configparser
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "scripts"))

from phase11_6.plan import PICO_ACCEPTED_BOOT, compose  # noqa: E402
from phase11_6.live import (BROWSER_ARM_LEAD_NS, MINIMUM_ARM_LEAD_NS,
                            CORRECTIVE_MAXIMUM_SYNC_AGE_NS,
                            CORRECTIVE_MINIMUM_SYNC_AGE_NS,
                            SETTLED_CLOCK_UNCERTAINTY_NS,
                            NetworkPeer, RetryableWtpBusy,
                            armed_clock_refinement, configure_capture_validator,
                            production_command,
                            render_production_ini, settled_inventory,
                            usb_completion,
                            wait_observer_readiness)  # noqa: E402
import phase11_5_package9 as package9  # noqa: E402
from validate_wtp_contract import frame  # noqa: E402
from phase11_6_attempt import (  # noqa: E402
    DIRECT_TOOLS,
    attempt_job_id,
    effective_compact_request,
    effective_job,
                           )
from reconcile_phase11_6 import release_safe  # noqa: E402


class Phase116AttemptTests(unittest.TestCase):
    def test_physical_readiness_waits_for_freshly_settled_clock(self):
        console = mock.Mock(failure=None, latest={"ok": True})
        usb = mock.Mock(
            failure=None,
            latest={"state": "empty"},
            clock={"state": "synchronized", "leap": "normal",
                   "uncertainty_ns": str(SETTLED_CLOCK_UNCERTAINTY_NS + 1)},
        )
        with self.assertRaises(TimeoutError):
            wait_observer_readiness(console, usb, timeout=0)
        usb.clock["uncertainty_ns"] = str(SETTLED_CLOCK_UNCERTAINTY_NS)
        wait_observer_readiness(console, usb, timeout=0.01)

    def test_corrective_readiness_uses_bounded_sample_age_without_relaxing_default(self):
        console = mock.Mock(failure=None, latest={"ok": True})
        usb = mock.Mock(
            failure=None,
            latest={"state": "empty"},
            clock={"state": "synchronized", "leap": "normal",
                   "uncertainty_ns": "38000000",
                   "sync_age_ns": str(CORRECTIVE_MINIMUM_SYNC_AGE_NS)},
        )
        with self.assertRaises(TimeoutError):
            wait_observer_readiness(console, usb, timeout=0)
        wait_observer_readiness(
            console, usb, timeout=0.01, maximum_uncertainty_ns=500_000_000,
            minimum_sync_age_ns=CORRECTIVE_MINIMUM_SYNC_AGE_NS,
            maximum_sync_age_ns=CORRECTIVE_MAXIMUM_SYNC_AGE_NS,
        )
        usb.clock["sync_age_ns"] = str(CORRECTIVE_MAXIMUM_SYNC_AGE_NS + 1)
        with self.assertRaises(TimeoutError):
            wait_observer_readiness(
                console, usb, timeout=0, maximum_uncertainty_ns=500_000_000,
                minimum_sync_age_ns=CORRECTIVE_MINIMUM_SYNC_AGE_NS,
                maximum_sync_age_ns=CORRECTIVE_MAXIMUM_SYNC_AGE_NS,
            )

    def test_clock_refinement_requires_better_accepted_sample_while_armed(self):
        def row(sequence, accepted, state, utc, monotonic, uncertainty, age):
            return {
                "sequence": sequence, "kind": "console_info",
                "monotonic_ns": monotonic,
                "value": {"value": {
                    "network": {"accepted": accepted},
                    "status": {
                        "state": state, "utc_now_ns": str(utc),
                        "monotonic_now_ns": str(monotonic),
                        "uncertainty_ns": str(uncertainty),
                        "sync_age_ns": str(age),
                    },
                }},
            }

        rows = [
            row(1, 34, "armed", 1_000_000_000_000, 10_000, 38_000_000,
                63_000_000_000),
            row(2, 35, "armed", 1_001_000_000_000, 1_010_000_000, 3_700_000,
                500_000_000),
        ]
        value = armed_clock_refinement(rows, "a" * 32)
        self.assertEqual(value["uncertainty_reduction_ns"], 34_300_000)
        self.assertEqual(value["job_id"], "a" * 32)
        changed = copy.deepcopy(rows)
        changed[1]["value"]["value"]["status"]["state"] = "running"
        with self.assertRaisesRegex(ValueError, "while Armed"):
            armed_clock_refinement(changed, "a" * 32)

    def test_phase116_usb_observer_refreshes_clock_each_status_cycle(self):
        source = (ROOT / "scripts/phase11_5_package9.py").read_text()
        loop = source[source.index("while not self.stop.is_set():",
                                   source.index("class UsbStatusObserver")):]
        self.assertLess(loop.index('peer.request("GET_CLOCK"'),
                        loop.index('peer.request("STATUS"'))

    def test_retryable_wtp_busy_has_a_distinct_pre_submission_disposition(self):
        response = {
            "type": "response",
            "protocol": "WTP/1",
            "session_id": "1" * 32,
            "request_id": "0" * 31 + "1",
            "op": "HELLO",
            "ok": False,
            "error": {"code": "BUSY", "message": "BUSY", "retryable": True},
        }

        class Stream:
            def sendall(self, _wire):
                pass

            def settimeout(self, _timeout):
                pass

            def recv(self, _size):
                return frame(json.dumps(response, separators=(",", ":")).encode())

        class Journal:
            def emit(self, _kind, _value):
                pass

        peer = NetworkPeer(Path("/fixture"), Journal(), session="1" * 32)
        peer.stream = Stream()
        with self.assertRaises(RetryableWtpBusy):
            peer.ask("HELLO")

    def test_postflight_inventory_wait_is_bounded_and_preserves_failed_probe(self):
        class Journal:
            def __init__(self):
                self.rows = []

            def emit(self, kind, value):
                self.rows.append((kind, value))

        journal = Journal()
        expected = {"result": "READ_ONLY_INVENTORY"}
        with mock.patch("phase11_6.live.inventory",
                        side_effect=[ValueError("probe busy"), expected]), \
                mock.patch("phase11_6.live.time.monotonic",
                           side_effect=[0.0, 1.0, 1.0]), \
                mock.patch("phase11_6.live.time.sleep"):
            value = settled_inventory(
                Path("/fixture"), "postflight", "serial", "device", journal
            )
        self.assertEqual(value, expected)
        self.assertEqual([row[0] for row in journal.rows],
                         ["inventory_wait", "inventory_complete"])
        self.assertEqual(journal.rows[0][1]["evidence_label"],
                         "postflight-read-1")
        self.assertEqual(journal.rows[1][1]["evidence_label"],
                         "postflight-read-2")

    def test_browser_preview_does_not_return_bigint_active_plan_through_cdp(self):
        source = (ROOT / "scripts/phase11_6_browser_submit.js").read_text()
        self.assertIn("notice:$('notice').textContent})", source)
        self.assertNotIn("notice:$('notice').textContent,activePlan})", source)

    def test_browser_path_has_compile_and_submission_lead_and_fails_fast(self):
        source = (ROOT / "scripts/phase11_6_browser_submit.js").read_text()
        self.assertGreater(BROWSER_ARM_LEAD_NS, MINIMUM_ARM_LEAD_NS)
        self.assertIn("browser submission rejected: HTTP", source)

    def test_browser_observers_retain_transient_status_unavailability(self):
        for name in ("phase11_6_browser_submit.js", "phase11_6_browser_watch.js"):
            source = (ROOT / "scripts" / name).read_text()
            self.assertIn("snapshot?.job??null", source)
            self.assertIn("manual_refresh_unavailable", source)
            self.assertIn("requiredRefresh", source)

    def test_production_browser_is_quiesced_during_wtp_admission(self):
        live = (ROOT / "src/phase11_6/live.py").read_text()
        production = live[live.index("def execute_production_job"):]
        self.assertLess(production.index("browser.pause()"),
                        production.index("subprocess.Popen"))
        self.assertLess(production.index('require(binding is not None'),
                        production.index("browser.resume()"))
        self.assertIn("refresh_interval_s=10.0", production)
        group = (ROOT / "src/phase11_6/wspr_group.py").read_text()
        self.assertIn("production_watch.start(); production_watch.pause()", group)
        self.assertIn("watch.resume()", group)

    def test_usb_observer_preserves_adverse_terminal_event(self):
        class Journal:
            def __init__(self):
                self.rows = []

            def emit(self, kind, value):
                self.rows.append((kind, value))

        observer = package9.UsbStatusObserver(
            Journal(), mock.Mock(), "2" * 32, 116, PICO_ACCEPTED_BOOT
        )
        job = "a" * 32
        observer.last_event_id = 40

        class Peer:
            pending = __import__("collections").deque([{
                "type": "event", "boot_id": PICO_ACCEPTED_BOOT,
                "event_id": "41", "event": "JOB_STATE",
                "body": {"state": "aborted", "job_id": job,
                         "output_active": False},
            }])

        observer.consume_events(Peer())
        self.assertEqual(observer.event_states, {"aborted"})
        self.assertEqual(observer.event_jobs, {job})

    def test_browser_terminal_auto_release_is_explicitly_audited(self):
        source = (ROOT / "scripts/phase11_6_browser_submit.js").read_text()
        live = (ROOT / "src/phase11_6/live.py").read_text()
        self.assertIn("release_required:releaseRequired,terminal,final", source)
        self.assertIn('and final.get("owner_id") is None', live)
        self.assertIn('terminal.get("output_active") is False', live)

    def test_usb_reducer_uses_ordered_events_for_brief_armed_state(self):
        job = "a" * 32
        prior = "b" * 32
        final = {
            "boot_id": PICO_ACCEPTED_BOOT,
            "state": "complete", "output_active": False, "owner_id": None,
            "job_id": job,
            "terminal_records": [{"job_id": job, "state": "complete",
                                  "output_active": False},
                                 {"job_id": prior, "state": "complete",
                                  "output_active": False}],
        }
        value = usb_completion(
            {"running", "complete"},
            {"loaded", "armed", "running", "complete"},
            {job, prior}, {job}, final, job,
        )
        self.assertEqual(value["terminal"]["job_id"], job)
        with self.assertRaises(ValueError):
            usb_completion({"running", "complete"}, {"loaded", "running", "complete"},
                           {job}, {job}, final, job)

    def test_each_attempt_has_fresh_identity_and_identical_rf_content(self):
        plan = compose()
        job = plan["packets"][0]["jobs"][0]
        first = effective_job(plan, job, 1)
        second = effective_job(plan, job, 2)
        self.assertNotEqual(first["job_id"], job["expected_job"]["job_id"])
        self.assertNotEqual(first["job_id"], second["job_id"])
        expected = copy.deepcopy(job["expected_job"])
        expected["job_id"] = first["job_id"]
        self.assertEqual(first, expected)
        self.assertEqual(first["job_id"], attempt_job_id(plan, job, 1))

    def test_attempt_binds_transitive_observer_and_protocol_tools(self):
        self.assertIn("scripts/phase11_5_package9.py", DIRECT_TOOLS)
        self.assertIn("scripts/rf_wtp.py", DIRECT_TOOLS)
        self.assertIn("scripts/phase11_5_rf_reservation.py", DIRECT_TOOLS)
        self.assertIn("scripts/validate_wtp_contract.py", DIRECT_TOOLS)

    def test_browser_compact_identity_matches_raw_expansion(self):
        plan = compose()
        job = next(job for packet in plan["packets"] for job in packet["jobs"]
                   if job["submission_path"] == "browser_compact")
        raw = effective_job(plan, job, 7)
        compact = effective_compact_request(plan, job, 7)
        self.assertEqual(compact["job_id"], raw["job_id"])
        self.assertEqual(compact["job_id"], attempt_job_id(plan, job, 7))

    def test_production_identity_is_runtime_bound_without_changing_rf_body(self):
        plan = compose()
        job = next(job for packet in plan["packets"] for job in packet["jobs"]
                   if job["submission_path"] == "production")
        self.assertEqual(effective_job(plan, job, 9), job["expected_job"])

    def test_production_ini_requests_transmit_and_preserves_it_at_startup(self):
        plan = compose()
        job = next(job for packet in plan["packets"] for job in packet["jobs"]
                   if job["submission_path"] == "production"
                   and job["mode"] == "DFCW")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "production-base.ini").write_text(
                "[Operation]\n"
                "[Calibration]\n"
                "[Experimental]\n"
                "[WSPR]\n"
                "[CW]\n"
            )
            directory = root / "attempt"
            directory.mkdir()
            path = render_production_ini(root, directory, job, 31_425)
            parser = configparser.ConfigParser(interpolation=None)
            parser.read(path)
            self.assertEqual(parser["Operation"]["Transmit"], "true")
            self.assertEqual(parser["Operation"]["Enable on Boot"], "Follow")

            command = production_command(Path("/candidate"), path, job)
            dot = command.index("--dfcw-dot-frequency")
            dash = command.index("--dfcw-dash-frequency")
            self.assertEqual(int(command[dot + 1]), job["nominal_frequency_hz"] + 5)
            self.assertEqual(int(command[dash + 1]), job["nominal_frequency_hz"])

    def test_reconciliation_browser_fallback_is_empty_state_only(self):
        empty = {"state": "empty", "owner_id": None, "output_active": False}
        self.assertTrue(release_safe(empty))
        for change in (
            {"state": "loaded"},
            {"owner_id": "some-owner"},
            {"output_active": True},
        ):
            candidate = dict(empty)
            candidate.update(change)
            self.assertFalse(release_safe(candidate))

        job = "a" * 32
        complete = {
            "state": "complete", "owner_id": None, "output_active": False,
            "job_id": job,
            "terminal_records": [{"job_id": job, "state": "complete",
                                  "output_active": False}],
        }
        self.assertTrue(release_safe(complete, job))
        self.assertFalse(release_safe(complete))
        self.assertFalse(release_safe(complete, "b" * 32))

    def test_capture_validator_dependency_is_explicit_and_hashed(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            package = source / "wsprrypi_qualification"
            schema = package / "schemas"
            schema.mkdir(parents=True)
            (package / "__init__.py").write_text("")
            (package / "capture_metadata.py").write_text(
                "def load_capture_metadata(path):\n    return path\n"
            )
            (schema / "capture-metadata.schema.json").write_text("{}\n")
            identity = configure_capture_validator(source)
            self.assertEqual(
                set(identity),
                {"capture_metadata.py", "capture-metadata.schema.json"},
            )
            self.assertTrue(all(len(value) == 64 for value in identity.values()))

    def test_analysis_binds_transitive_source_tools(self):
        source = (ROOT / "scripts/analyze_phase11_6.py").read_text()
        for relative in (
            "scripts/analyze_phase11_6.py",
            "src/phase11_6/analysis.py",
            "scripts/analyze_rf_bench.py",
            "scripts/measure_rf_bench.py",
            "scripts/decode_rf_wspr.py",
            "src/campaign/analysis.py",
            "src/campaign/plan.py",
        ):
            self.assertIn(f'"{relative}"', source)
        self.assertIn('"wsprrypi_qualification/carrier.py"', source)
        self.assertNotIn("import wsprrypi_qualification.carrier as", source)
        self.assertIn('parser.add_argument("--qualification-src"', source)
        for name in ("run_phase11_6_batch.py", "run_phase11_6_wspr_batch.py"):
            runner = (ROOT / "scripts" / name).read_text()
            self.assertIn('"--qualification-src", str(args.qualification_src)', runner)


if __name__ == "__main__":
    unittest.main()
