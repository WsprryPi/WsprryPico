#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from campaign.plan import compose, validate, classify, initial_matrix, make_job


class PlanTests(unittest.TestCase):
    def test_complete_matrix(self):
        plan = validate(compose())
        matrix = initial_matrix(plan)
        self.assertEqual(len(matrix), 75)
        self.assertEqual(sum(r["status"] == "unsupported" for r in matrix), 10)
        for band in plan["bands"]:
            for job in band["jobs"].values():
                offset = 0
                self.assertLessEqual(len(job["events"]), 162)
                for event in job["events"]:
                    self.assertEqual(int(event["offset_ns"]), offset)
                    self.assertGreater(int(event["duration_ns"]), 0)
                    offset += int(event["duration_ns"])
                    self.assertEqual("frequency_nhz" in event, event["rf_on"])
                self.assertEqual(offset, int(job["total_duration_ns"]))
                self.assertLessEqual(offset, 110592000000)

    def test_tampering(self):
        for field, value in [
            ("repetitions", {"WSPR": 1}),
            ("sample_rate_hz", 150000000),
            ("path", {}),
            ("thresholds", {"offset_hz": 9999}),
        ]:
            plan = compose()
            plan[field] = value
            with self.assertRaises(ValueError):
                validate(plan)
        for bands in [[], ["80m", "80m"], ["bad"]]:
            with self.assertRaises(ValueError):
                compose(bands)
        plan = compose(["80m"])
        plan["bands"][0]["jobs"]["TONE"]["total_duration_ns"] = "999999999999"
        with self.assertRaises(ValueError):
            validate(plan)

    def test_clock_specific_limits_and_legacy_identity(self):
        from campaign.plan import digest

        legacy = compose(["2200m"])
        self.assertEqual(legacy["version"], 1)
        self.assertEqual(
            digest(compose()),
            "37106fcbc39e190e642992f5fa8220fb4641a83b4220db974bbe6fa59a1f754d",
        )
        for rate, unsupported in [(132000000, 10), (138000000, 10), (150000000, 5)]:
            plan = validate(compose(sample_rate_hz=rate))
            self.assertEqual(
                sum(r["status"] == "unsupported" for r in initial_matrix(plan)),
                unsupported,
            )
            self.assertEqual(plan["bands"][0]["jobs"], legacy["bands"][0]["jobs"])
            altered = compose(["2200m"], sample_rate_hz=rate)
            self.assertEqual(altered["version"], 1 if rate == 138000000 else 2)
            if rate != 138000000:
                self.assertNotEqual(digest(altered), digest(legacy))
        for rate in (12000000, True, 138000000.0, 0):
            with self.assertRaises(ValueError):
                compose(sample_rate_hz=rate)
            with self.assertRaises(ValueError):
                make_job("TONE", 137500, sample_rate_hz=rate)

    def test_qrss3_jobs_keep_standard_ratios_and_explicit_identity(self):
        p = validate(compose(["2200m"], keyed_dot_ns=3000000000))
        self.assertEqual(p["version"], 2)
        for mode in ("QRSS", "FSKCW", "DFCW"):
            job = p["bands"][0]["jobs"][mode]
            lengths = [int(e["duration_ns"]) / 1e9 for e in job["events"]]
            self.assertEqual(
                lengths,
                [1, 3, 3, 3, 3, 3, 1] if mode == "DFCW" else [1, 3, 9, 9, 9, 3, 1],
            )
        p["keyed_dot_ns"] = 700000000
        with self.assertRaises(ValueError):
            validate(p)

    def test_precedence(self):
        good = dict(cleanup_verified=True, fixture_ok=True, passed=True)
        self.assertEqual(classify([good] * 3, 3)[0], "qualified")
        self.assertEqual(classify([good] * 2, 3)[0], "blocked")
        self.assertEqual(classify([dict(good, passed=False)], 3)[0], "failed")
        self.assertEqual(
            classify([dict(good, passed=False, fixture_ok=False)], 3)[0], "blocked"
        )
        self.assertEqual(
            classify([dict(good, cleanup_verified=False)], 1)[0], "blocked"
        )
        self.assertEqual(classify([{}], 1)[0], "blocked")

    def test_keyed_independent_reference(self):
        from wsprrypi_qualification.cw_defaults import hardware_free_keyed_protocol
        from wsprrypi_qualification.cw_reference import generate_expected_events

        for mode in ("QRSS", "FSKCW", "DFCW"):
            expected = generate_expected_events(
                dict(
                    mode=mode.lower(),
                    capture_contract=dict(sample_count=3000000, sample_rate_hz=250000),
                    protocol=hardware_free_keyed_protocol(
                        mode.lower(),
                        primary_frequency_hz=3570100,
                        pre_quiet_seconds=1,
                        post_quiet_seconds=1,
                    ),
                )
            )
            actual = make_job(mode, 3570100)["events"]
            self.assertEqual(len(expected), len(actual))
            for a, e in zip(actual, expected):
                self.assertEqual(int(a["offset_ns"]), round(e["start_s"] * 1e9))
                self.assertEqual(
                    int(a["duration_ns"]), round((e["end_s"] - e["start_s"]) * 1e9)
                )
                self.assertEqual(a["rf_on"], e["rf_state"] != "off")
                if a["rf_on"]:
                    self.assertEqual(
                        int(a["frequency_nhz"]), round(e["frequency_hz"] * 1e9)
                    )


if __name__ == "__main__":
    unittest.main()
