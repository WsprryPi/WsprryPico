import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from phase11_5_package5_plan import (BOOT, DEVICE, IMAGE, NORMALIZER_POLICY, POLICY,
    RETAINED_BOOT, RETAINED_IMAGE, RETAINED_SOURCE, SOURCE, expiry_cases,
    normalizer_jobs, retention_cases, terminal_jobs, validate_expiry,
    validate_normalizer, validate_retention, validate_terminal)
from phase11_5_package5_continuation_wifi_recovery import (
    ACTIVE_FIXTURE_PACKET, BLOCKED_FIXTURE_PACKET, HYPOTHESIS, POLICY as WIFI_POLICY,
    SERIAL as WIFI_SERIAL, validate as validate_continuation_wifi)
from adversarial_phase11_5_package5 import validate as validate_publication


class Package5PolicyTests(unittest.TestCase):
    def retained(self):
        seed, owner = "a" * 32, "b" * 32
        return dict(policy=POLICY, source_revision=RETAINED_SOURCE,
                    image_sha256=RETAINED_IMAGE, boot_id=RETAINED_BOOT,
                    device_id=DEVICE, runtime_seconds=1500, restoration_seconds=150,
                    configuration_writes=0, controlled_reboots=0, wifi_cycles=0, flashes=0,
                    rf_jobs=0, retention=dict(seed=seed, owner_id=owner,
                        cases=retention_cases(seed, owner), replay_entries_per_session=8,
                        maximum_sessions=16, replay_session_ttl_seconds=300,
                        initial_quiet_seconds=360, expiry_quiet_seconds=360))

    def test_retention_exact_capacity_lru_and_expiry(self):
        packet = self.retained()
        validate_retention(packet)
        cases = {case["label"]: case for case in packet["retention"]["cases"]}
        self.assertEqual(len([name for name in cases if name.startswith("session-") and
                              name[8:].split("-")[0].isdigit()]), 20)
        self.assertEqual(cases["session-16-overflow"]["error_code"], "BUSY")
        self.assertEqual(cases["replay-conflict"]["error_code"], "REQUEST_ID_REUSE")
        self.assertEqual(cases["session-0-expired"]["error_code"], "HELLO_REQUIRED")
        for key, value in (("maximum_sessions", 15), ("initial_quiet_seconds", 300),
                           ("expiry_quiet_seconds", 300), ("replay_entries_per_session", 9)):
            changed = copy.deepcopy(packet)
            changed["retention"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_retention(changed)

    def terminal(self):
        seed = "c" * 32
        return dict(closure_policy="phase115-package5-terminal-capacity-v1",
                    source_revision=SOURCE, image_sha256=IMAGE, boot_id=BOOT,
                    terminal_seed=seed, jobs=terminal_jobs(seed), runtime_seconds=720,
                    restoration_seconds=150, maximum_renewals=2,
                    maximum_initial_terminal_records=0, initial_a_state="empty",
                    initial_a_job_id=None, terminal_capacity=dict(entries=8,
                        touch_after_completions=8, evicted_job_index=1,
                        retained_job_indexes=[8, 0, 7, 6, 5, 4, 3, 2]))

    def test_terminal_requires_nine_completions_and_lru_touch(self):
        packet = self.terminal()
        validate_terminal(packet)
        for path, value in (("jobs", packet["jobs"][:8]),
                            ("terminal_capacity", dict(packet["terminal_capacity"], entries=9)),
                            ("maximum_renewals", 3)):
            changed = copy.deepcopy(packet)
            changed[path] = value
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_terminal(changed)

    def expiry(self):
        seed = "d" * 32
        records = [dict(job_id=f"{n + 1:032x}", state="complete",
                        ended_monotonic_ns=str(n + 1), output_active=False) for n in range(8)]
        return dict(policy="phase115-package5-terminal-expiry-v1", source_revision=SOURCE,
                    image_sha256=IMAGE, boot_id=BOOT, device_id=DEVICE, runtime_seconds=3900,
                    restoration_seconds=150, configuration_writes=0, controlled_reboots=0,
                    wifi_cycles=0, flashes=0, rf_jobs=0, terminal_expiry=dict(seed=seed,
                        cases=expiry_cases(seed), terminal_entries=8, source_ttl_seconds=3600,
                        quiet_seconds=3660, authenticated_recovery_seconds=15,
                        initial_terminal_records=records))

    def test_terminal_expiry_is_real_and_not_shortened(self):
        packet = self.expiry()
        validate_expiry(packet)
        self.assertEqual([case["label"] for case in packet["terminal_expiry"]["cases"]],
                         ["after-hello"])
        self.assertTrue(all(case["request"]["operation"] != "STATUS"
                            for case in packet["terminal_expiry"]["cases"]))
        for key, value in (("quiet_seconds", 3600), ("source_ttl_seconds", 300),
                           ("authenticated_recovery_seconds", 30)):
            changed = copy.deepcopy(packet)
            changed["terminal_expiry"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_expiry(changed)

    def test_normalizer_is_eight_one_second_maximum_event_jobs(self):
        seed = "c" * 32
        jobs = normalizer_jobs(seed)
        packet = dict(closure_policy=NORMALIZER_POLICY, source_revision=SOURCE,
                      image_sha256=IMAGE, boot_id=BOOT, normalizer_seed=seed,
                      jobs=jobs, runtime_seconds=720, restoration_seconds=150,
                      maximum_renewals=2, maximum_initial_terminal_records=0,
                      initial_terminal_records=[], initial_a_state="empty",
                      initial_a_job_id=None, normalization=dict(entries=8,
                          events_per_job=512, duration_ns="1000000000",
                          event_duration_ns="1953125", frequencies_nhz=
                          ["135500000000000", "135495000000000"]),
                      post_quiet=dict(seconds=360, sample_interval_seconds=30,
                                      phase="normalizer"))
        validate_normalizer(packet)
        self.assertEqual(len(jobs), 8)
        self.assertTrue(all(len(job["events"]) == 512 and
                            job["total_duration_ns"] == "1000000000"
                            for job in jobs))
        self.assertIsNot(jobs[0]["events"], jobs[1]["events"])
        for label, mutate in (
                ("event-count", lambda v: v["jobs"][0]["events"].pop()),
                ("duration", lambda v: v["jobs"][0].update(total_duration_ns="999999999")),
                ("quiet", lambda v: v["post_quiet"].update(seconds=359))):
            changed = copy.deepcopy(packet)
            mutate(changed)
            with self.subTest(label=label), self.assertRaises(ValueError):
                validate_normalizer(changed)

    def test_continuation_wifi_recovery_is_one_exact_cycle(self):
        packet = dict(schema=WIFI_POLICY, scope=WIFI_POLICY, source_revision=SOURCE,
                      image_sha256=IMAGE, boot_id=BOOT, device_id=DEVICE,
                      serial=WIFI_SERIAL, hypothesis=HYPOTHESIS,
                      blocked_fixture_packet_sha256=BLOCKED_FIXTURE_PACKET,
                      active_fixture_packet_sha256=ACTIVE_FIXTURE_PACKET,
                      runtime_seconds=300, restoration_seconds=150,
                      maximum_wifi_cycles=1, wifi_cycles=1, rf_jobs=0, flashes=0,
                      configuration_writes=0, controlled_reboots=0)
        validate_continuation_wifi(packet)
        for key, value in (("maximum_wifi_cycles", 2), ("wifi_cycles", 0),
                           ("active_fixture_packet_sha256", "0" * 64),
                           ("blocked_fixture_packet_sha256", "0" * 64)):
            changed = copy.deepcopy(packet)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_continuation_wifi(changed)

    def test_complete_publication_matches_frozen_evidence_summary(self):
        result = Path("docs/development/phase11-5-package5-result.json")
        validate_publication(json.loads(result.read_text()))


if __name__ == "__main__":
    unittest.main()
