#!/usr/bin/env python3

import copy
import collections
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(1, str(ROOT / "scripts"))

from phase11_6.plan import PICO_ACCEPTED_BOOT, compose  # noqa: E402
from phase11_6.live import BrowserSubmit, BrowserWatch  # noqa: E402
from run_phase11_6_wspr_batch import (  # noqa: E402
    prepare_attempts_root,
    reconciliation_binding,
)
from phase11_6.wspr_group import (  # noqa: E402
    SLOT_NS,
    UsbWsprCoordinator,
    WSPR_SLOT_PHASE_NS,
    _completed_predecessor,
    _terminal_poll_delay_s,
    _terminal_predecessor,
    _next_slot,
    _prepare_production_directory,
    _production_wtp_terminal,
    require_fixture_namespaces,
    _slice_capture,
    compose_group,
    group_digest,
    validate_group,
)


class Phase116WsprGroupTests(unittest.TestCase):
    def test_terminal_poll_enters_quiet_window_without_oversleep(self):
        deadline = 20_000_000_000
        self.assertEqual(
            _terminal_poll_delay_s([deadline], deadline - 2_496_000_000),
            0.496,
        )
        self.assertEqual(
            _terminal_poll_delay_s([deadline], deadline - 10_000_000_000),
            5.0,
        )
        self.assertEqual(
            _terminal_poll_delay_s([deadline], deadline - 1_500_000_000),
            0.025,
        )

    def test_fresh_batch_creates_private_attempt_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            attempts = prepare_attempts_root(root)
            self.assertEqual(attempts, root / "attempts")
            self.assertEqual(attempts.stat().st_mode & 0o777, 0o700)

    def test_reconciliation_reuses_partial_usb_owner_and_request_sequence(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "execution.jsonl"
            values = []
            for number, operation in ((9, "CLAIM"), (10, "LOAD")):
                body = {"owner_id": "2" * 32, "lease_ms": 60000}
                if operation == "LOAD":
                    body = {"job_id": "4" * 32, "events": []}
                values.append({
                    "kind": "usb_controller_exchange",
                    "value": {
                        "session_id": "2" * 32,
                        "request_id": f"{number:032x}",
                        "operation": operation,
                        "body": body,
                    },
                })
            path.write_text("\n".join(json.dumps(value) for value in values) + "\n")
            self.assertEqual(reconciliation_binding(path), {
                "session": "2" * 32,
                "request_number": 10,
                "expected_job_id": "4" * 32,
            })

    def test_reconciliation_selects_last_loading_principal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            execution = root / "execution.jsonl"
            values = []
            for session, number, operation, job_id in (
                ("2" * 32, 9, "LOAD", "4" * 32),
                ("5" * 32, 1, "CLAIM", None),
                ("5" * 32, 2, "RELEASE", None),
            ):
                body = ({"job_id": job_id, "events": []} if job_id else {})
                values.append({"kind": "usb_controller_exchange", "value": {
                    "session_id": session, "request_id": f"{number:032x}",
                    "operation": operation, "body": body,
                }})
            execution.write_text(
                "\n".join(json.dumps(value) for value in values) + "\n"
            )
            self.assertEqual(reconciliation_binding(execution), {
                "session": "2" * 32,
                "request_number": 9,
                "expected_job_id": "4" * 32,
            })

    def test_reconciliation_prefers_observed_browser_load(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            execution = root / "execution.jsonl"
            execution.write_text(json.dumps({
                "kind": "usb_controller_exchange",
                "value": {"session_id": "2" * 32, "request_id": "a" * 32,
                          "operation": "LOAD",
                          "body": {"job_id": "4" * 32}},
            }) + "\n")
            browser = root / "browser-result.json"
            requests = []
            for number, operation in enumerate(
                ("HELLO", "CLAIM", "LOAD", "ARM"), start=1
            ):
                body = {"job_id": "6" * 32} if operation in {"LOAD", "ARM"} else {}
                envelope = {"session_id": "7" * 32,
                            "request_id": f"{number:032x}",
                            "operation": operation, "body": body}
                requests.append({"postData": json.dumps(envelope)})
            browser.write_text(json.dumps({"requests": requests}))
            self.assertEqual(reconciliation_binding(execution, browser), {
                "session": "7" * 32,
                "request_number": 4,
                "expected_job_id": "6" * 32,
            })

    def test_reconciliation_rejects_malformed_browser_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            execution = root / "execution.jsonl"
            execution.write_text(json.dumps({
                "kind": "usb_controller_exchange",
                "value": {"session_id": "2" * 32, "request_id": "a" * 32,
                          "operation": "LOAD",
                          "body": {"job_id": "4" * 32}},
            }) + "\n")
            browser = root / "browser-result.json"
            browser.write_text(json.dumps({"requests": [{
                "session_id": "Z" * 32, "request_id": "b" * 32,
                "operation": "LOAD", "body": {"job_id": "6" * 32},
            }]}))
            with self.assertRaisesRegex(ValueError,
                                        "Invalid reconciliation principal"):
                reconciliation_binding(execution, browser)

    def test_browser_mutation_marker_rejects_malformed_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            submitter = BrowserSubmit(
                ROOT, directory,
                {"submission_path": "browser_raw",
                 "expected_job": {"job_id": "4" * 32}},
                10, mock.Mock(),
            )
            submitter.process = mock.Mock()
            submitter.process.poll.return_value = None
            (directory / "browser-mutations-complete.json").write_text(
                json.dumps({
                    "schema": "phase11.6-browser-mutations-v1",
                    "job_id": "4" * 32,
                    "predecessor_job_id": None,
                    "operations": ["HELLO", "CLAIM", "LOAD", "ARM"],
                    "session_id": "Z" * 32,
                    "last_request_id": "5" * 32,
                    "browser_arm_admission": {
                        "clock_state": "synchronized",
                        "uncertainty_ns": "1000000",
                        "accepted_arm_lead_ns": "8000000000",
                    },
                })
            )
            with self.assertRaisesRegex(ValueError,
                                        "Browser mutation acknowledgement"):
                submitter.wait_mutations(timeout=0.1)

    def test_fixture_namespace_admission_requires_mount_and_network_match(self):
        values = {
            "/proc/self/ns/mnt": "mnt:[1]",
            "/proc/42/ns/mnt": "mnt:[1]",
            "/proc/self/ns/net": "net:[2]",
            "/proc/42/ns/net": "net:[2]",
        }
        with mock.patch("phase11_6.wspr_group.os.readlink",
                        side_effect=lambda path: values[path]):
            self.assertEqual(
                require_fixture_namespaces(42),
                {"mnt": "mnt:[1]", "net": "net:[2]"},
            )

    def test_fixture_namespace_admission_rejects_host_namespace(self):
        def identity(path):
            if path == "/proc/42/ns/net":
                return "net:[fixture]"
            return "net:[host]" if path.endswith("/net") else "mnt:[same]"

        with mock.patch("phase11_6.wspr_group.os.readlink", side_effect=identity):
            with self.assertRaisesRegex(ValueError, "fixture net namespace"):
                require_fixture_namespaces(42)

    def _production_events(self):
        binding = {
            "job_id": "1" * 32,
            "session_id": "2" * 32,
            "owner_id": "3" * 32,
        }
        events = []
        for index, (state, output) in enumerate((
            ("loaded", False), ("armed", False),
            ("running", True), ("complete", False),
        )):
            events.append({
                "type": "event", "protocol": "WTP/1",
                "session_id": binding["session_id"],
                "boot_id": PICO_ACCEPTED_BOOT,
                "event_id": str(index), "event": "JOB_STATE",
                "body": {"job_id": binding["job_id"], "state": state,
                         "output_active": output},
            })
        return binding, events

    def test_production_terminal_uses_authenticated_complete_event(self):
        binding, events = self._production_events()
        terminal = _production_wtp_terminal(events, binding)
        self.assertEqual(terminal, {
            "job_id": binding["job_id"],
            "boot_id": PICO_ACCEPTED_BOOT,
            "state": "complete", "output_active": False,
            "event_id": "3", "authoritative": True,
            "source": "authenticated-wtp-job-state-event",
        })

    def test_production_terminal_rejects_missing_or_adverse_completion(self):
        binding, events = self._production_events()
        for changed in (events[:-1], copy.deepcopy(events)):
            if len(changed) == len(events):
                changed[-1]["body"].update(state="failed", output_active=False)
            with self.assertRaisesRegex(ValueError,
                                        "authenticated lifecycle"):
                _production_wtp_terminal(changed, binding)

    def test_production_terminal_rejects_identity_or_event_gap(self):
        binding, events = self._production_events()
        wrong_boot = copy.deepcopy(events)
        wrong_boot[-1]["boot_id"] = "f" * 32
        with self.assertRaisesRegex(ValueError, "event identity"):
            _production_wtp_terminal(wrong_boot, binding)
        event_gap = copy.deepcopy(events)
        event_gap[-1]["event_id"] = "4"
        with self.assertRaisesRegex(ValueError, "event order"):
            _production_wtp_terminal(event_gap, binding)

    def test_completed_predecessor_requires_exact_terminal_and_empty_authority(self):
        status = {
            "state": "empty", "job_id": None, "owner_id": None,
            "output_active": False,
            "terminal_records": [
                {"job_id": "prior", "state": "complete", "output_active": False}
            ],
        }
        self.assertTrue(_completed_predecessor(status, "prior"))
        terminal = copy.deepcopy(status)
        terminal.update({"state": "complete", "job_id": "prior",
                         "owner_id": "releasing-owner"})
        self.assertTrue(_terminal_predecessor(terminal, "prior"))
        self.assertFalse(_completed_predecessor(terminal, "prior"))
        for field, value in (("state", "running"), ("job_id", "other"),
                             ("owner_id", "owner"), ("output_active", True)):
            changed = copy.deepcopy(status)
            changed[field] = value
            self.assertFalse(_completed_predecessor(changed, "prior"))
        self.assertFalse(_completed_predecessor(status, "other"))

    def test_usb_event_gap_is_allowed_only_at_disconnect_boundary(self):
        journal = mock.Mock()
        coordinator = UsbWsprCoordinator(journal, threading.Event())

        def event(session, event_id):
            return {
                "type": "event", "protocol": "WTP/1",
                "session_id": session,
                "boot_id": PICO_ACCEPTED_BOOT,
                "event_id": str(event_id), "event": "JOB_STATE",
                "body": {"job_id": "4" * 32, "state": "complete",
                         "output_active": False},
            }

        first = types.SimpleNamespace(
            session="1" * 32,
            pending=collections.deque([event("1" * 32, 124)]),
        )
        coordinator._begin_event_connection(first, allow_first_gap=False)
        coordinator._consume_events(first)

        second = types.SimpleNamespace(
            session="2" * 32,
            pending=collections.deque([event("2" * 32, 127)]),
        )
        coordinator._begin_event_connection(second, allow_first_gap=True)
        coordinator._consume_events(second)
        self.assertEqual(coordinator.event_gaps, [{
            "previous_event_id": "124",
            "next_event_id": "127",
            "missing_event_count": 2,
            "reason": "deliberate-controller-transport-disconnect",
            "new_session_id": "2" * 32,
        }])

        second.pending.append(event("2" * 32, 129))
        with self.assertRaisesRegex(ValueError, "event order"):
            coordinator._consume_events(second)

    def test_usb_transition_uses_exact_claim_load_arm_and_guard(self):
        job_id = "4" * 32
        predecessor = "3" * 32
        status = {
            "state": "empty", "job_id": None, "owner_id": None,
            "output_active": False,
            "terminal_records": [{
                "job_id": predecessor, "state": "complete",
                "output_active": False,
            }],
        }
        peer = mock.Mock(session="2" * 32, sequence=0)
        peer.pending = []
        calls = []

        def request(operation, body, timeout=5):
            calls.append((operation, copy.deepcopy(body), timeout))
            peer.sequence += 1
            if operation == "LOAD":
                return {"job_id": job_id, "adjustments": []}
            if operation == "ARM":
                return {"job_id": job_id, "state": "armed", "clock": {
                    "state": "synchronized", "leap": "normal",
                    "uncertainty_ns": "1000000", "utc_now_ns": "2000000000",
                }}
            return {}

        peer.request.side_effect = request
        journal = mock.Mock()
        console_quiet = threading.Event()
        console_quiet.set()
        coordinator = UsbWsprCoordinator(
            journal, mock.Mock(), console_quiet=console_quiet
        )
        task = {
            "target_utc_ns": 20_000_000_000,
            "predecessor_job_id": predecessor,
            "job": {"expected_job": {"job_id": job_id, "events": []}},
        }
        clock = {"state": "synchronized", "leap": "normal",
                 "uncertainty_ns": "1000000", "utc_now_ns": "1000000000"}
        result = coordinator._arm_controller(
            peer, task, status, clock, time.monotonic_ns()
        )
        self.assertEqual([call[0] for call in calls],
                         ["CLAIM", "LOAD", "ARM"])
        self.assertGreater(calls[0][2], 1.5)
        self.assertLessEqual(calls[0][2], 2.0)
        self.assertEqual(calls[0][1], {"owner_id": "2" * 32, "lease_ms": 60000})
        self.assertEqual(calls[-1][1], {
            "job_id": job_id, "start_utc_ns": "20000000000",
            "max_start_uncertainty_ns": "500000000",
        })
        self.assertEqual(result["controller_session_id"], "2" * 32)
        self.assertFalse(console_quiet.is_set())
        journal.emit.assert_any_call("wspr_group_console_quiet", {
            "quiet": False,
            "reason": "time-critical-successor-mutation-handoff",
        })
        exchanges = [call.args[1] for call in journal.emit.call_args_list
                     if call.args[0] == "usb_controller_exchange"]
        self.assertEqual([value["operation"] for value in exchanges],
                         ["CLAIM", "LOAD", "ARM"])

    def test_usb_transition_quiets_console_two_seconds_before_handoff(self):
        stop = mock.Mock()
        stop.is_set.side_effect = [False, True]
        stop.wait.return_value = None
        journal = mock.Mock()
        console_quiet = threading.Event()
        coordinator = UsbWsprCoordinator(
            journal, stop, console_quiet=console_quiet
        )
        coordinator.transition = {
            "predecessor_job_id": "3" * 32,
            "predecessor_complete_utc_ns": 10_000_000_000,
        }
        coordinator._poll = mock.Mock(return_value=({
            "state": "running", "job_id": "3" * 32,
            "owner_id": "2" * 32, "output_active": True,
            "terminal_records": [],
        }, {
            "state": "synchronized", "leap": "normal",
            "uncertainty_ns": "1000000", "utc_now_ns": "1",
        }))
        with mock.patch(
            "phase11_6.wspr_group.time.time_ns", return_value=8_000_000_000
        ):
            with self.assertRaisesRegex(RuntimeError, "stopped before transition"):
                coordinator._before_transition(mock.Mock())
        self.assertTrue(console_quiet.is_set())
        journal.emit.assert_any_call("wspr_group_console_quiet", {
            "quiet": True,
            "reason": "time-critical-successor-mutation-handoff",
        })

    def test_usb_transition_rejects_less_than_eight_second_lead(self):
        predecessor = "3" * 32
        peer = mock.Mock(session="2" * 32, sequence=0, pending=[])
        clock = {
            "state": "synchronized", "leap": "normal",
            "uncertainty_ns": "1000000", "utc_now_ns": "12000000001",
        }
        coordinator = UsbWsprCoordinator(mock.Mock(), mock.Mock())
        with self.assertRaisesRegex(ValueError, "initial authority/lead"):
            coordinator._arm_controller(peer, {
                "target_utc_ns": 20_000_000_000,
                "predecessor_job_id": predecessor,
                "job": {"expected_job": {"job_id": "4" * 32}},
            }, {
                "state": "empty", "job_id": None, "owner_id": None,
                "output_active": False, "terminal_records": [{
                    "job_id": predecessor, "state": "complete",
                    "output_active": False,
                }],
            }, clock, time.monotonic_ns())

    def test_usb_transition_claims_immediately_after_terminal_busy_clears(self):
        predecessor = "3" * 32
        job_id = "4" * 32
        peer = mock.Mock(session="2" * 32, sequence=0, pending=[])
        responses = [RuntimeError({"code": "BUSY", "message": "occupied"}), {},
                     {"job_id": job_id, "adjustments": []},
                     {"job_id": job_id, "state": "armed", "clock": {
                         "state": "synchronized", "leap": "normal",
                         "uncertainty_ns": "1000000", "utc_now_ns": "2000000000",
                     }}]

        def request(operation, body, timeout=5):
            peer.sequence += 1
            value = responses.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value

        peer.request.side_effect = request
        status = {
            "state": "complete", "job_id": predecessor,
            "owner_id": "releasing-owner", "output_active": False,
            "terminal_records": [{"job_id": predecessor, "state": "complete",
                                  "output_active": False}],
        }
        journal = mock.Mock()
        coordinator = UsbWsprCoordinator(journal, threading.Event())
        clock = {"state": "synchronized", "leap": "normal",
                 "uncertainty_ns": "1000000", "utc_now_ns": "1000000000"}
        result = coordinator._arm_controller(peer, {
            "target_utc_ns": 20_000_000_000,
            "predecessor_job_id": predecessor,
            "job": {"expected_job": {"job_id": job_id, "events": []}},
        }, status, clock, time.monotonic_ns())
        self.assertEqual(result["job_id"], job_id)
        self.assertEqual(peer.request.call_args_list[0].args[0], "CLAIM")
        self.assertEqual(peer.request.call_args_list[1].args[0], "CLAIM")
        self.assertTrue(any(call.args[0] == "usb_controller_claim_busy"
                            for call in journal.emit.call_args_list))

    def test_usb_transition_aborts_if_arm_acknowledgement_is_too_late(self):
        predecessor = "3" * 32
        job_id = "4" * 32
        peer = mock.Mock(session="2" * 32, sequence=0, pending=[])
        responses = [
            {},
            {"job_id": job_id, "adjustments": []},
            {"job_id": job_id, "state": "armed", "clock": {
                "state": "synchronized", "leap": "normal",
                "uncertainty_ns": "1000000", "utc_now_ns": "12000000001",
            }},
            {},
            {},
        ]
        calls = []

        def request(operation, body, timeout=5):
            calls.append((operation, copy.deepcopy(body), timeout))
            peer.sequence += 1
            return responses.pop(0)

        peer.request.side_effect = request
        status = {
            "state": "empty", "job_id": None, "owner_id": None,
            "output_active": False, "terminal_records": [{
                "job_id": predecessor, "state": "complete",
                "output_active": False,
            }],
        }
        clock = {"state": "synchronized", "leap": "normal",
                 "uncertainty_ns": "1000000", "utc_now_ns": "1000000000"}
        coordinator = UsbWsprCoordinator(mock.Mock(), threading.Event())
        with self.assertRaisesRegex(ValueError, "immutable ARM lead"):
            coordinator._arm_controller(peer, {
                "target_utc_ns": 20_000_000_000,
                "predecessor_job_id": predecessor,
                "job": {"expected_job": {"job_id": job_id, "events": []}},
            }, status, clock, time.monotonic_ns())
        self.assertEqual([call[0] for call in calls],
                         ["CLAIM", "LOAD", "ARM", "ABORT", "RELEASE"])
        self.assertEqual(calls[-2][1], {"job_id": job_id})

    def test_usb_observer_claims_and_releases_completed_controller(self):
        job_id = "4" * 32
        peer = mock.Mock(session="5" * 32, sequence=0, pending=[])
        statuses = [
            {
                "boot_id": PICO_ACCEPTED_BOOT,
                "state": "complete", "job_id": job_id, "owner_id": None,
                "output_active": False, "terminal_records": [{
                    "job_id": job_id, "state": "complete",
                    "output_active": False,
                }],
            },
            {
                "boot_id": PICO_ACCEPTED_BOOT,
                "state": "empty", "job_id": None, "owner_id": None,
                "output_active": False, "terminal_records": [{
                    "job_id": job_id, "state": "complete",
                    "output_active": False,
                }],
            },
        ]
        clock = {"state": "synchronized", "leap": "normal",
                 "uncertainty_ns": "1000000", "utc_now_ns": "1"}
        calls = []

        def request(operation, body, timeout=5):
            calls.append((operation, copy.deepcopy(body)))
            peer.sequence += 1
            if operation == "GET_CLOCK":
                return clock
            if operation == "STATUS":
                return statuses.pop(0)
            return {}

        peer.request.side_effect = request
        stop = mock.Mock()
        stop.is_set.side_effect = [False, True]
        stop.wait.return_value = None
        coordinator = UsbWsprCoordinator(mock.Mock(), stop)
        next_browser = mock.Mock()
        next_browser.wait_mutations.return_value = {
            "schema": "phase11.6-browser-mutations-v1",
            "job_id": "6" * 32,
        }
        coordinator.transition = {
            "job": {"planned_duration_ns": 1},
            "target_utc_ns": 10,
            "next_target_utc_ns": 20,
            "next_duration_ns": 1,
            "predecessor_job_id": "3" * 32,
            "next_browser": next_browser,
        }
        coordinator._after_transition(peer, {
            "job_id": job_id, "controller_session_id": "2" * 32,
        })
        self.assertEqual([call[0] for call in calls],
                         ["GET_CLOCK", "STATUS", "CLAIM", "RELEASE"])
        self.assertEqual(coordinator.transition_result["terminal_release"][
            "session_id"], "5" * 32)
        authority = next_browser.authorize_predecessor.call_args.args[0]
        self.assertEqual(authority["predecessor_job_id"], job_id)
        self.assertEqual(
            authority["source"],
            "authenticated-usb-event-status-release",
        )
        self.assertTrue(coordinator.transition_done.is_set())
        next_browser.wait_mutations.assert_called_once_with()

    def test_browser_submit_packet_can_bind_exact_predecessor(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            journal = mock.Mock()
            submitter = BrowserSubmit(
                ROOT, directory, {"expected_job": {"job_id": "4" * 32}},
                10, journal,
            )
            submitter.process = mock.Mock()
            submitter.process.poll.return_value = None
            submitter.submit(
                20_000_000_000,
                predecessor_job_id="3" * 32,
                predecessor_complete_utc_ns=10_000_000_000,
            )
            self.assertEqual(json.loads((directory / "submit.json").read_text()), {
                "start_utc_ns": "20000000000",
                "predecessor_job_id": "3" * 32,
                "predecessor_complete_utc_ns": "10000000000",
            })

    def test_browser_submit_finish_requires_predecessor_page_overlap(self):
        predecessor = "3" * 32
        job_id = "4" * 32
        result = {
            "status": "PASS",
            "job_id": job_id,
            "predecessor_job_id": predecessor,
            "predecessor_manual_refresh_overlap": True,
            "predecessor_terminal": {
                "job_id": predecessor,
                "state": "complete",
                "output_active": False,
            },
            "predecessor_authority": {
                "source": "authenticated-usb-event-status-release",
                "predecessor_job_id": predecessor,
            },
            "browser_arm_admission": {
                "clock_state": "synchronized",
                "uncertainty_ns": "1000",
                "lead_ns": "9000000000",
                "accepted_arm_lead_ns": "8500000000",
            },
            "manual_refresh_overlap": True,
            "release_required": False,
            "operations": ["HELLO", "CLAIM", "LOAD", "ARM"],
            "terminal": {
                "job_id": job_id,
                "state": "complete",
                "output_active": False,
            },
            "final": {"owner_id": None, "output_active": False},
        }

        def finish(value):
            with tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                (directory / "browser-result.json").write_text(json.dumps(value))
                submitter = BrowserSubmit(ROOT, directory, {
                    "submission_path": "browser_raw",
                    "expected_job": {"job_id": job_id},
                }, 10, mock.Mock())
                submitter.predecessor_job_id = predecessor
                submitter.process = mock.Mock()
                submitter.process.wait.return_value = 0
                submitter.stdout = mock.Mock()
                submitter.stderr = mock.Mock()
                return submitter.finish()

        self.assertEqual(finish(result), result)
        changed = copy.deepcopy(result)
        changed["predecessor_manual_refresh_overlap"] = False
        with self.assertRaisesRegex(ValueError, "browser-owned submission"):
            finish(changed)

    def test_wildcard_browser_finish_waits_for_its_terminal_reducer(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            production = "a" * 32
            result = {
                "status": "PASS", "page_loaded": True,
                "manual_refresh_overlap": True,
                "job_ids": [production], "observed_job_id": production,
                "observed_terminal": {
                    "job_id": production, "state": "complete",
                    "output_active": False,
                },
                "final_job_id": production, "final_output_active": False,
            }
            (directory / "browser-result.json").write_text(json.dumps(result))
            journal = mock.Mock()
            watcher = BrowserWatch(ROOT, directory, None, 600, journal)
            watcher.process = mock.Mock()
            watcher.process.poll.return_value = None
            watcher.process.wait.return_value = 0
            watcher.stdout = mock.Mock()
            watcher.stderr = mock.Mock()
            self.assertEqual(watcher.finish(), result)
            watcher.process.wait.assert_called_once_with(timeout=18)
            self.assertFalse((directory / "browser-stop").exists())

    def test_usb_successors_wait_for_exact_production_browser_confirmation(self):
        predecessor = "a" * 32
        coordinator = UsbWsprCoordinator(mock.Mock(), threading.Event())
        coordinator.transition = {"predecessor_job_id": predecessor}
        with self.assertRaisesRegex(ValueError, "Exact predecessor"):
            coordinator.confirm_predecessor_browser("b" * 32)
        coordinator.confirm_predecessor_browser(predecessor)
        coordinator._wait_for_predecessor_browser()
        self.assertTrue(coordinator.predecessor_browser_done.is_set())

    def test_consecutive_transition_starts_at_production_binding(self):
        source = (ROOT / "src/phase11_6/wspr_group.py").read_text()
        callback = source.index("on_binding(binding)")
        production_finish = source.index('production_browser = production_watch.finish()')
        self.assertLess(callback, production_finish)
        self.assertIn("usb.schedule_transition(", source)
        self.assertIn("predecessor_job_id=armed[\"job_id\"]", source)
        self.assertIn(
            'production_browser.get("observed_job_id") == prod["binding"]["job_id"]',
            source,
        )
        orderly = source.index(
            'require(process.returncode == 0, "WSPR production orderly exit")'
        )
        terminal = source.index("terminal = _production_wtp_terminal")
        self.assertLess(orderly, terminal)
        self.assertNotIn("production_released.wait", source)
        self.assertIn(
            "peer, task, status, clock, self.starts[-1]",
            source,
        )
        browser_confirm = source.index("self._wait_for_predecessor_browser()")
        successor_submit = source.index('task["next_browser"].submit(')
        self.assertLess(browser_confirm, successor_submit)
        self.assertIn(
            'usb.confirm_predecessor_browser(prod["binding"]["job_id"])',
            source,
        )
        self.assertNotIn('task["next_browser"].start()', source)
        self.assertIn("        browser.start()", source)
        self.assertNotIn("controller_watch", source)
        self.assertIn("Production browser observer health", source)
        browser_source = (ROOT / "scripts/phase11_6_browser_submit.js").read_text()
        self.assertIn("predecessor_settled", browser_source)
        self.assertIn("predecessorOverlap", browser_source)
        self.assertIn("standby_refresh", browser_source)
        self.assertIn("ownStates", browser_source)
        self.assertIn("predecessor-authority.json", browser_source)

    def test_group_creates_slot_parents_before_browser_children(self):
        source = (ROOT / "src/phase11_6/wspr_group.py").read_text()
        parent_creation = source.index('directory / "production",')
        browser_start = source.index("production_watch.start()")
        self.assertLess(parent_creation, browser_start)
        self.assertIn("path.mkdir(mode=0o700)", source[parent_creation:browser_start])

    def test_production_slot_accepts_only_fresh_browser_observer(self):
        with tempfile.TemporaryDirectory() as temporary:
            slot = Path(temporary) / "production"
            slot.mkdir(mode=0o700)
            (slot / "browser").mkdir(mode=0o700)
            (slot / "browser/browser-ready").touch()
            _prepare_production_directory(slot)

            (slot / "unexpected").touch()
            with self.assertRaises(ValueError):
                _prepare_production_directory(slot)

    def test_production_slot_rejects_symlinked_browser_observer(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            slot = root / "production"
            slot.mkdir(mode=0o700)
            real_browser = root / "real-browser"
            real_browser.mkdir(mode=0o700)
            (slot / "browser").symlink_to(real_browser, target_is_directory=True)
            with self.assertRaises(ValueError):
                _prepare_production_directory(slot)

    def test_production_slot_can_create_missing_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            slot = Path(temporary) / "production"
            _prepare_production_directory(slot)
            self.assertTrue(slot.is_dir())
            self.assertEqual(slot.stat().st_mode & 0o777, 0o700)

    def _group(self, temporary: str):
        plan = compose()
        jobs = [job for packet in plan["packets"] for job in packet["jobs"]
                if job["band"] == "2200m" and job["mode"] == "WSPR"
                and job["purpose"] == "nominal"]
        attempts = []
        paths = []
        for index, job in enumerate(jobs):
            attempt = {
                "job_id": job["id"],
                "planned_rf_seconds": job["planned_duration_ns"] / 1e9,
                "sequence": index + 1,
            }
            path = Path(temporary) / f"attempt-{index}.json"
            path.write_text(json.dumps(attempt))
            attempts.append(attempt)
            paths.append(path)
        return plan, compose_group(plan, "2200m", attempts, paths, ROOT)

    def test_group_is_three_jobs_in_consecutive_execution_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan, group = self._group(temporary)
            jobs = validate_group(group, plan, ROOT)
        paths = {job["submission_path"]: job["id"] for job in jobs}
        self.assertEqual(
            group["execution_order"],
            [paths["production"], paths["controller_disconnect"], paths["browser_raw"]],
        )
        self.assertEqual(group["slot_spacing_ns"], str(SLOT_NS))
        self.assertEqual(group["slot_phase_ns"], str(WSPR_SLOT_PHASE_NS))
        self.assertEqual(group["planned_jobs"], 3)
        self.assertEqual(len(group_digest(group)), 64)

    def test_group_packet_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            plan, group = self._group(temporary)
            changed = copy.deepcopy(group)
            changed["slot_spacing_ns"] = "1"
            with self.assertRaises(ValueError):
                validate_group(changed, plan, ROOT)

    def test_next_slot_is_aligned_with_required_lead(self):
        now = 20 * SLOT_NS + 100
        with mock.patch("phase11_6.wspr_group.time.time_ns", return_value=now):
            target = _next_slot()
        self.assertEqual((target - WSPR_SLOT_PHASE_NS) % SLOT_NS, 0)
        self.assertGreaterEqual(target - now, 45_000_000_000)
        self.assertLess(target - now, 165_000_000_000)

    def test_next_slot_skips_a_too_close_wspr_phase(self):
        now = 20 * SLOT_NS + WSPR_SLOT_PHASE_NS - 1
        with mock.patch("phase11_6.wspr_group.time.time_ns", return_value=now):
            target = _next_slot()
        self.assertEqual(target, 21 * SLOT_NS + WSPR_SLOT_PHASE_NS)

    def test_capture_slice_keeps_provenance_outside_strict_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent"
            parent.mkdir()
            iq = np.arange(200, dtype=np.float32).view(np.complex64)
            iq.tofile(parent / "capture.cf32")
            metadata = {
                "helper_version": "test",
                "capture_id": "parent",
                "timestamps": {
                    "retained_capture_start_utc": "1970-01-01T00:00:00.000Z",
                    "retained_capture_complete_utc": "1970-01-01T00:00:05.000Z",
                },
                "elapsed_duration_s": 5.0,
                "actual_settings": {"sample_rate_hz": 10},
                "resolved_device": {"driver": "test", "serial": "test"},
                "requested_sample_count": 50,
                "retained_sample_count": 50,
                "output": {},
            }
            (parent / "capture.json").write_text(json.dumps(metadata))
            checked = []
            capture_metadata = types.ModuleType(
                "wsprrypi_qualification.capture_metadata"
            )

            def validate_metadata(path):
                value = json.loads(path.read_text())
                self.assertNotIn("derived_slice", value)
                checked.append(value)

            capture_metadata.load_capture_metadata = validate_metadata
            package = types.ModuleType("wsprrypi_qualification")
            job = {
                "id": "band:WSPR:0:production:nominal",
                "submission_path": "production",
                "planned_duration_ns": 1_000_000_000,
            }
            with mock.patch.dict(sys.modules, {
                "wsprrypi_qualification": package,
                "wsprrypi_qualification.capture_metadata": capture_metadata,
            }):
                result = _slice_capture(parent, [job], [3_000_000_000], root / "out")
            capture = root / "out/production/capture"
            self.assertEqual(len(checked), 1)
            self.assertTrue((capture / "capture-provenance.json").is_file())
            self.assertEqual(result[0]["sample_count"], 50)
            self.assertEqual(result[0]["derived_slice"]["sample_range"], [10, 60])
            self.assertEqual(checked[0]["timestamps"]["retained_capture_start_utc"],
                             "1970-01-01T00:00:01.000Z")


if __name__ == "__main__":
    unittest.main()
