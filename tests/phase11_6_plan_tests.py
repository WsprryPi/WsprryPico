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
    PREDECESSOR_PLAN_SHA256,
    WSPR_LOWEST_OFFSET_NHZ,
    WSPR_SPACING_NHZ,
    WSPR_SYMBOL_NS,
    WSPR_SYMBOLS,
    compose,
    initial_matrix,
    message_events,
    wspr_events,
    validate,
)


class Phase116PlanTests(unittest.TestCase):
    def test_authorized_boot_only_plan_amendment(self):
        plan = compose()
        self.assertEqual(
            plan["amendment"]["predecessor_plan_sha256"],
            PREDECESSOR_PLAN_SHA256,
        )
        self.assertFalse(plan["amendment"]["rf_job_payloads_changed"])
        self.assertEqual(
            plan["accepted_configuration"]["phase11_5_accepted_boot_id"],
            PICO_PHASE115_BOOT,
        )
        self.assertEqual(
            plan["accepted_configuration"]["accepted_boot_id"],
            PICO_ACCEPTED_BOOT,
        )
        self.assertNotEqual(PICO_PHASE115_BOOT, PICO_ACCEPTED_BOOT)

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
