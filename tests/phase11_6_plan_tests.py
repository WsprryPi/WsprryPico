#!/usr/bin/env python3
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.plan import (  # noqa: E402
    BANDS,
    LONG_MESSAGE,
    MESSAGE,
    MODES,
    NS,
    PICO_ACCEPTED_BOOT,
    PICO_PHASE115_BOOT,
    PICO_PREDECESSOR_BOOT,
    PREDECESSOR_PLAN_SHA256,
    SAMPLE_RATE_HZ,
    WSPR_LOWEST_OFFSET_NHZ,
    WSPR_SPACING_NHZ,
    WSPR_SYMBOL_NS,
    WSPR_SYMBOLS,
    compose,
    initial_matrix,
    message_events,
    realized_frequency_nhz,
    wspr_events,
    validate,
)


class Phase116PlanTests(unittest.TestCase):
    def test_authorized_repair_candidate_plan_amendment(self):
        plan = compose()
        self.assertEqual(
            plan["amendment"]["predecessor_plan_sha256"],
            PREDECESSOR_PLAN_SHA256,
        )
        self.assertFalse(plan["amendment"]["rf_job_payloads_changed"])
        self.assertFalse(plan["amendment"]["rf_waveform_changed"])
        self.assertEqual(
            plan["accepted_configuration"]["phase11_5_accepted_boot_id"],
            PICO_PHASE115_BOOT,
        )
        self.assertEqual(
            plan["accepted_configuration"]["accepted_boot_id"],
            PICO_ACCEPTED_BOOT,
        )
        self.assertNotEqual(PICO_PHASE115_BOOT, PICO_ACCEPTED_BOOT)
        self.assertEqual(
            plan["accepted_configuration"]["boot_transition"]["from_boot_id"],
            PICO_PREDECESSOR_BOOT,
        )
        self.assertTrue(
            plan["accepted_configuration"]["boot_transition"][
                "source_revision_unchanged"
            ]
        )
        self.assertTrue(
            plan["accepted_configuration"]["boot_transition"][
                "uf2_sha256_unchanged"
            ]
        )
        self.assertEqual(plan["amendment"]["controlled_reboots"], 1)
        self.assertFalse(plan["amendment"]["failed_sequence_retried"])
        self.assertEqual(
            plan["amendment"]["failed_sequences"],
            [67, 88, 94, 97, 100, 102, 106, 109, 113, 116, 119, 125, 128,
             131, 134, 137, 143, 144, 146, 149, 152],
        )
        self.assertEqual(
            plan["amendment"]["zero_rf_preflight_failures"],
            [91, 103, 104, 105, 122, 135, 140, 146],
        )
        self.assertEqual(
            plan["amendment"]["zero_rf_aborted_submissions"],
            [110, 117, 126, 132],
        )
        self.assertEqual(
            plan["amendment"]["aborted_rf_sequences"],
            [114, 120, 129, 138],
        )
        self.assertEqual(
            plan["amendment"]["abandoned_unsubmitted_sequences"],
            [89, 90, 92, 93, 95, 96, 98, 99, 101, 107, 108, 111, 112, 115,
             118, 121, 123, 124, 127, 130, 133, 136, 139, 141, 142, 145,
             147, 148, 150, 151, 153, 154],
        )
        self.assertEqual(plan["amendment"]["next_sequence"], 155)
        self.assertEqual(
            plan["amendment"]["fixture_namespace_repair"],
            {
                "required_namespaces": ["mount", "network"],
                "admission": (
                    "batch and physical group require their current namespace "
                    "identities to equal the supplied active fixture process"
                ),
                "admission_before_attempt_creation": True,
            },
        )
        self.assertEqual(
            plan["amendment"]["fixture_continuity_repair"],
            {
                "remote_ap": "reuse the active accepted AP attestation",
                "local_client": "fresh source and namespace root",
                "reason": (
                    "avoid another AP withdrawal while retaining immutable local "
                    "packet, namespace, capture, and observer evidence"
                ),
                "pico_mutations": 0,
            },
        )
        self.assertEqual(
            plan["amendment"]["wspr_transition_repair"],
            {
                "production_transport": "authenticated-network-wtp",
                "controller_transport": "usb-wtp",
                "browser_transport": "shipped-https-browser-page",
                "controller_disconnect": (
                    "close the USB WTP stream immediately after ARM without "
                    "disconnecting USB power"
                ),
                "production_cleanup_handoff": (
                    "after the exact inactive predecessor terminal, attempt the USB "
                    "successor CLAIM for at most two seconds while the releasing "
                    "owner settles; give the in-flight CLAIM the remaining deadline "
                    "rather than a fixed 0.5-second timeout, and retry only explicit "
                    "BUSY replies inside that envelope; companion c39fae3 accepts "
                    "that inactive successor after acknowledged RELEASE"
                ),
                "production_release_latency": (
                    "reuse the fresh exact terminal/inactive proof from successful "
                    "execution before RELEASE; monitor JOB_STATE without a continuous "
                    "STATUS transaction, pace long-job STATUS outside the final full "
                    "transaction allowance, retain a bounded post-completion fallback, "
                    "and require fresh post-RELEASE STATUS"
                ),
                "console_quiet_window": (
                    "suppress full Console INFO diagnostics from two seconds before "
                    "the predicted production terminal through successor ARM, then "
                    "resume at a fresh one-second cadence; authenticated WTP clock, "
                    "status, event, release, claim, load and ARM evidence remain active"
                ),
                "browser_predecessor_gate": (
                    "require the already-open page to overlap the exact controller "
                    "job while armed or running, then submit only after authenticated "
                    "USB terminal event plus current complete unowned inactive STATUS "
                    "and authenticated release authority"
                ),
                "disconnect_event_gap": (
                    "only the first event on the new authenticated post-disconnect "
                    "USB session may skip strictly increasing global event IDs; record "
                    "the exact missing range, require contiguous events thereafter, "
                    "and bridge lifecycle with accepted ARM plus current STATUS"
                ),
                "minimum_arm_lead_ns": "8000000000",
                "controller_clock_handoff": (
                    "project the immediately preceding synchronized device clock by "
                    "host monotonic elapsed time before CLAIM, after CLAIM, and "
                    "before ARM; omit redundant GET_CLOCK exchanges and require the "
                    "clock returned by ARM itself to retain the unchanged lead, "
                    "otherwise immediately ABORT and RELEASE"
                ),
                "controller_load_frequency_encoding": (
                    "exact 138 MHz NCO realized frequencies, strict admission, "
                    "identical increments to the nominal adjustment-allowed job; "
                    "adjacent identical tone cells are coalesced without changing "
                    "the RF waveform or total duration"
                ),
                "failed_group_reconciliation": (
                    "first reuse the exact retained USB principal when it remains "
                    "admissible; when an active disconnected session blocks WTP, "
                    "bind the exact job through authenticated browser status and "
                    "the boot/source/active state through physical Console INFO "
                    "before exactly one Console ABORT; validate the identity-free "
                    "Console acknowledgement against boot and inactive aborted "
                    "state, then prove the exact job terminal through fresh WTP "
                    "status"
                ),
                "production_browser_terminal": (
                    "bind the wildcard production observer to the first active job, "
                    "latch its exact retained complete inactive terminal, stop page "
                    "refreshes while successors run, and verify the observed id "
                    "against the authenticated production runtime binding"
                ),
                "production_browser_handoff": (
                    "pre-open the raw-browser successor while idle; after controller "
                    "ARM and USB disconnect, authorize that existing page only after "
                    "the wildcard production page exits by reducing its exact retained "
                    "terminal; the successor page must itself overlap the controller, "
                    "quiesce refreshes before predicted completion, and consume fresh "
                    "USB event-plus-STATUS terminal authority before submitting the "
                    "third slot"
                ),
                "browser_connection_budget": (
                    "pre-open exactly the production observer and raw-browser successor "
                    "while the target is idle; retain the successor page with bounded "
                    "standby refreshes because active RF pauses new network admission; "
                    "fail before RF if either browser exits"
                ),
            },
        )
        self.assertEqual(
            plan["repositories"]["WsprryPi"],
            "c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf",
        )
        self.assertEqual(
            plan["amendment"]["companion_binary_sha256"],
            "b8e63947e2e9780f43dc4247869db138f81cc6e2245c99c1fd02ad9de4b33ff6",
        )
        self.assertEqual(
            plan["amendment"]["production_ini"],
            {"loop_tx": False, "tx_iterations": 1},
        )
        self.assertEqual(plan["source_impact"]["firmware_runtime_changes"], 1)
        self.assertEqual(plan["source_impact"]["companion_runtime_changes"], 1)

    def test_complete_bounded_schedule(self):
        plan = compose()
        self.assertLessEqual(plan["planned_jobs"], 300)
        self.assertLessEqual(plan["planned_rf_seconds"], 18000)
        for packet in plan["packets"]:
            self.assertLessEqual(packet["planned_jobs"], 16)
            self.assertLessEqual(packet["planned_rf_seconds"], 1800)

    def test_supported_matrix_counts_and_unsupported_rows(self):
        plan = compose()
        matrix = initial_matrix(plan)
        self.assertEqual(len(matrix["rows"]), len(BANDS) * len(MODES))
        unsupported = [row for row in matrix["rows"]
                       if row["disposition"] == "UNSUPPORTED_CONFIGURATION"]
        self.assertEqual({row["band"] for row in unsupported}, {"4m", "2m"})
        self.assertEqual(len(unsupported), 10)
        integration = [job for packet in plan["packets"]
                       if packet["kind"] == "integration"
                       for job in packet["jobs"]]
        self.assertEqual(len(integration), 9)
        self.assertEqual({job["mode"] for job in integration}, set(MODES))
        self.assertEqual(
            {job["abort"]["mechanism"] for job in integration},
            {"owner", "foreign_then_owner", "console"},
        )

    def test_frozen_message_semantics(self):
        self.assertEqual(MESSAGE, "ET E")
        self.assertEqual(len(LONG_MESSAGE), 32)
        qrss = message_events("QRSS", 137_500)
        fskcw = message_events("FSKCW", 137_500)
        dfcw = message_events("DFCW", 137_500)
        self.assertEqual(sum(int(event["duration_ns"]) for event in qrss), 45 * NS + 1000)
        self.assertEqual(sum(int(event["duration_ns"]) for event in fskcw), 45 * NS + 1000)
        self.assertEqual(sum(int(event["duration_ns"]) for event in dfcw), 39 * NS + 1000)
        self.assertTrue(all(event["rf_on"] for event in fskcw[:-1]))
        self.assertTrue(any(not event["rf_on"] for event in qrss))
        self.assertEqual(
            sorted({int(event["frequency_nhz"]) for event in dfcw if event["rf_on"]}),
            [137_500 * NS, 137_505 * NS],
        )
        self.assertEqual(
            [int(event["frequency_nhz"]) for event in dfcw if event["rf_on"]],
            [137_505 * NS, 137_500 * NS, 137_505 * NS],
        )

    def test_wspr_uses_production_center_and_symbol_cells(self):
        events = wspr_events(137_500)
        self.assertEqual(len(events), 162)
        self.assertTrue(all(int(event["duration_ns"]) == WSPR_SYMBOL_NS
                            for event in events))
        self.assertEqual(int(events[0]["frequency_nhz"]),
                         137_500 * NS + WSPR_LOWEST_OFFSET_NHZ
                         + int(WSPR_SYMBOLS[0]) * WSPR_SPACING_NHZ)
        self.assertEqual(sum(int(event["duration_ns"]) for event in events),
                         162 * WSPR_SYMBOL_NS)

    def test_controller_wspr_uses_strict_identical_nco_realizations(self):
        plan = compose()
        jobs = [job for packet in plan["packets"] for job in packet["jobs"]
                if job["mode"] == "WSPR" and job["purpose"] == "nominal"]
        for job in jobs:
            expected = job["expected_job"]
            if job["submission_path"] != "controller_disconnect":
                self.assertTrue(expected["allow_frequency_adjustment"])
                continue
            self.assertFalse(expected["allow_frequency_adjustment"])
            nominal = wspr_events(job["nominal_frequency_hz"])
            self.assertLess(len(expected["events"]), len(nominal))
            self.assertEqual(
                sum(int(event["duration_ns"]) for event in expected["events"]),
                sum(int(event["duration_ns"]) for event in nominal),
            )
            strict_index = 0
            for requested in nominal:
                while (int(expected["events"][strict_index]["offset_ns"])
                       + int(expected["events"][strict_index]["duration_ns"])
                       <= int(requested["offset_ns"])):
                    strict_index += 1
                strict = expected["events"][strict_index]
                self.assertLessEqual(int(strict["offset_ns"]),
                                     int(requested["offset_ns"]))
                self.assertGreaterEqual(
                    int(strict["offset_ns"]) + int(strict["duration_ns"]),
                    int(requested["offset_ns"]) + int(requested["duration_ns"]),
                )
                self.assertEqual(
                    int(strict["frequency_nhz"]),
                    realized_frequency_nhz(int(requested["frequency_nhz"])),
                )
                requested_increment = (
                    int(requested["frequency_nhz"]) * (1 << 32)
                    + SAMPLE_RATE_HZ * NS // 2
                ) // (SAMPLE_RATE_HZ * NS)
                strict_increment = (
                    int(strict["frequency_nhz"]) * (1 << 32)
                    + SAMPLE_RATE_HZ * NS // 2
                ) // (SAMPLE_RATE_HZ * NS)
                self.assertEqual(strict_increment, requested_increment)

    def test_mutations_fail_closed(self):
        plan = compose()
        mutations = []
        changed = copy.deepcopy(plan)
        changed["planned_jobs"] -= 1
        mutations.append(changed)
        changed = copy.deepcopy(plan)
        changed["packets"][0]["jobs"][0]["planned_duration_ns"] += 1
        mutations.append(changed)
        changed = copy.deepcopy(plan)
        changed["packets"][0]["jobs"][0]["expected_job"]["events"][0][
            "frequency_nhz"
        ] = str(200_000 * NS)
        mutations.append(changed)
        changed = copy.deepcopy(plan)
        changed["packets"][0]["jobs"].append(copy.deepcopy(changed["packets"][0]["jobs"][0]))
        changed["packets"][0]["planned_jobs"] += 1
        changed["packets"][0]["planned_rf_seconds"] += 5
        changed["planned_jobs"] += 1
        changed["planned_rf_seconds"] += 5
        mutations.append(changed)
        for mutation in mutations:
            with self.subTest():
                with self.assertRaises(ValueError):
                    validate(mutation)


if __name__ == "__main__":
    unittest.main()
