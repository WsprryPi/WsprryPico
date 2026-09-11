#!/usr/bin/env python3
"""Validate the Phase 11.5 acceptance register, never infer a physical pass.

Evidence entries are reviewed assertions, not substitutes for raw-data audit.
The checker rejects missing gates and cross-image/clock/device extrapolation.
It performs no network, USB, allocation probe or hardware operation.
"""

import argparse
from fractions import Fraction
import json
from pathlib import Path
import re


GATES = {
    "allocator", "core0_stack", "core1_stack", "refill", "launch_and_tail",
    "observer_overhead", "contention_a_f", "sustained_g", "restoration",
}
CASES = {f"{family}{number}" for family, count in
         (("A", 3), ("B", 4), ("C", 4), ("D", 4), ("E", 2), ("F", 2), ("G", 1))
         for number in range(1, count + 1)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def deadline(clock_hz):
    require(type(clock_hz) is int and clock_hz > 0, "invalid clock")
    return Fraction(16384 * 32 * 1_000_000_000, clock_hz)


def validate(document):
    require(document["schema"] == "wsprrypico-phase11.5-v1", "unknown schema")
    require(set(document["cases"]) == CASES, "incomplete case matrix")
    require(all(value in ("NOT_RUN", "PARTIAL", "PASS", "FAIL")
                for value in document["cases"].values()), "invalid case disposition")
    clocks = document["clocks"]
    selected = set()
    seen = set()
    for entry in clocks:
        clock = entry["sample_clock_hz"]
        period = deadline(clock)
        require(clock not in seen, "duplicate clock")
        seen.add(clock)
        require(entry["full_buffer_period_ns"] == [period.numerator, period.denominator],
                "deadline must be recalculated for each clock")
        require(type(entry["selected_for_11_6"]) is bool, "selection must be boolean")
        if entry["selected_for_11_6"]:
            selected.add(clock)
        require(entry["physical_status"] in ("UNTESTED", "OPEN", "ACCEPTED"),
                "invalid clock disposition")
    accepted_clocks = set()
    ids = set()
    for config in document["accepted_configurations"]:
        require(config["id"] not in ids, "duplicate configuration")
        ids.add(config["id"])
        clock = config["sample_clock_hz"]
        require(clock in selected, "accepted clock was not selected for 11.6")
        require(config["system_clock_hz"] == clock and config["pio_divider"] == [1, 1],
                "unsupported clock configuration; review the measurement model first")
        require(re.fullmatch(r"[0-9a-f]{64}", config["uf2_sha256"]) is not None,
                "missing exact image identity")
        require(re.fullmatch(r"[0-9a-f]{40}", config["source_revision"]) is not None,
                "missing source revision")
        require(re.fullmatch(r"[0-9a-f]{32}", config["device_id"]) is not None,
                "missing device identity")
        require(set(config["gates"]) == GATES, "incomplete acceptance gates")
        for name, gate in config["gates"].items():
            require(gate["status"] == "PASS", f"unresolved gate: {name}")
            require(gate["uf2_sha256"] == config["uf2_sha256"] and
                    gate["sample_clock_hz"] == clock and
                    gate["device_id"] == config["device_id"], f"identity mismatch: {name}")
            require(re.fullmatch(r"[0-9a-f]{32}", gate["boot_id"]) is not None,
                    f"missing boot: {name}")
            require(bool(gate["reviewed_evidence"]), f"missing evidence: {name}")
        require(all(state == "PASS" for state in config["cases"].values()) and
                set(config["cases"]) == CASES, "configuration has unaccepted cases")
        accepted_clocks.add(clock)
    require({e["sample_clock_hz"] for e in clocks if e["physical_status"] == "ACCEPTED"}
            == accepted_clocks, "clock status differs from accepted configuration list")
    if document["phase_status"] == "CLOSED":
        require(bool(selected) and selected <= accepted_clocks,
                "selected clock lacks acceptance")
        require(all(v == "PASS" for v in document["cases"].values()), "open joint cases")
    else:
        require(document["phase_status"] == "OPEN", "invalid phase status")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("register", type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.register.read_text())
        validate(document)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(1, f"Invalid Phase 11.5 register: {error}\n")
    print(f"Register valid; phase {document['phase_status']}; "
          f"{len(document['accepted_configurations'])} accepted configurations")


if __name__ == "__main__":
    main()
