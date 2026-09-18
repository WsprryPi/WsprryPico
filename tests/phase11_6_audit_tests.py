#!/usr/bin/env python3

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from phase11_6.audit import audit_document
from phase11_6.plan import compose, digest


def job_digest(job):
    return hashlib.sha256(json.dumps(job["expected_job"], sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()


def intact_document(plan):
    packet = plan["packets"][0]
    rows = []
    for index, job in enumerate(packet["jobs"]):
        mode = job["mode"]
        analysis = dict(passed=True, wrong_message_rejected=True,
            wrong_band_rejected=True, truncation_rejected=True,
            extra_burst_rejected=True)
        if mode == "WSPR":
            analysis.update(decoded_identity=["AA0NT", "EM18", "20"],
                complete_frame_before_padding=True, tone_spacing_passed=True,
                symbol_progression_passed=True)
        elif mode in {"QRSS", "FSKCW", "DFCW"}:
            polarity = (plan["content"]["dfcw_polarity"] if mode == "DFCW" else
                plan["content"]["fskcw_polarity"] if mode == "FSKCW" else
                "single-frequency marks; silent commanded gaps")
            analysis.update(message="ET E", expected_event_sha256=job_digest(job),
                envelope_timing_passed=True, no_missing_or_extra_elements=True,
                polarity=polarity)
        else:
            analysis.update(one_uninterrupted_interval=True,
                            no_residual_or_extra_burst=True)
        lifecycle = dict(
            boot_id=plan["accepted_configuration"]["accepted_boot_id"],
            terminal_output_active=False, authoritative_terminal=True,
            reservation_held=True, schedules_disabled_a=True,
            schedules_disabled_b=True, browser_page_loaded=True,
            browser_manual_refresh_overlap=True, hostname_authenticated_tls=True,
            production_wsprrypi=job["submission_path"] == "production",
            browser_owned_submission=job["submission_path"].startswith("browser"),
            controller_disconnected_after_arm=job["controller_disconnect_after_arm"],
            usb_power_continuous=True, reconciled_without_duplicate_submission=True)
        rows.append(dict(id=job["id"], band=job["band"], mode=mode,
            submission_path=job["submission_path"],
            planned_duration_ns=job["planned_duration_ns"],
            expected_job_sha256=job_digest(job), disposition="PASS",
            capture=dict(sha256=f"{index + 1:064x}", complete=True,
                metadata_complete=True, overflow_count=0, clipping_samples=0,
                sample_count=1000, leading_quiet_s=1.1, trailing_quiet_s=1.1),
            lifecycle=lifecycle, analysis=analysis,
            resources=dict(heap_reserve_bytes=32768, stack_guards_valid=True,
                faults=0, dma_errors=0, refill_irq_unpaired=0,
                refill_invalid_reserves=0)))
    return dict(schema="phase11.6-packet-evidence-v1", plan_sha256=digest(plan),
        packet_id=packet["packet_id"],
        identity=dict(device_id=plan["accepted_configuration"]["device_id"],
            source_revision=plan["accepted_configuration"]["source_revision"],
            uf2_sha256=plan["accepted_configuration"]["uf2_sha256"],
            boot_id=plan["accepted_configuration"]["accepted_boot_id"],
            system_clock_hz=138000000, pio_divider=1, engine="pio-dma-gp2",
            renderer="RAM"), receiver=plan["receiver"], tolerances=plan["tolerances"],
        jobs=rows, accounting=dict(attempted=len(rows), completed=len(rows), aborted=0,
            rejected=0, uncertain=0, charged_jobs=len(rows),
            charged_planned_rf_seconds=packet["planned_rf_seconds"]),
        final=dict(a_output_active=False, a_owner_id=None, b_output_active=False,
            b_owner_id=None, a_schedules_disabled=True, b_schedules_disabled=True,
            reservation_released_after_authoritative_inactive=True,
            wspr4_restored=True, wspr5_restored=True, installed_service_active=True))


class Phase116AuditTests(unittest.TestCase):
    def test_intact_and_adversarial_mutations(self):
        plan = compose()
        intact = intact_document(plan)
        self.assertTrue(audit_document(intact, plan)["valid"])
        changes = (
            ("wrong identity", lambda v: v["identity"].__setitem__("boot_id", "0" * 32)),
            ("wrong band", lambda v: v["jobs"][0].__setitem__("band", "80m")),
            ("wrong message", lambda v: v["jobs"][5]["analysis"].__setitem__("message", "EEE")),
            ("truncated metadata", lambda v: v["jobs"][0]["capture"].__setitem__("metadata_complete", False)),
            ("polarity reversal", lambda v: v["jobs"][11]["analysis"].__setitem__("polarity", "reversed")),
            ("missing quiet", lambda v: v["jobs"][0]["capture"].__setitem__("trailing_quiet_s", .2)),
            ("page did not overlap", lambda v: v["jobs"][0]["lifecycle"].__setitem__("browser_manual_refresh_overlap", False)),
            ("duplicate capture", lambda v: v["jobs"][1]["capture"].__setitem__("sha256", v["jobs"][0]["capture"]["sha256"])),
            ("premature release", lambda v: v["jobs"][0]["lifecycle"].__setitem__("reservation_held", False)),
            ("threshold drift", lambda v: v["tolerances"].__setitem__("keyed_edge_s", .5)),
            ("accounting drift", lambda v: v["accounting"].__setitem__("charged_jobs", 1)),
        )
        for label, mutation in changes:
            with self.subTest(label=label):
                changed = copy.deepcopy(intact)
                mutation(changed)
                with self.assertRaises(ValueError):
                    audit_document(changed, plan)


if __name__ == "__main__":
    unittest.main()
