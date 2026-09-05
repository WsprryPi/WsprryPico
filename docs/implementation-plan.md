# Implementation plan

Status: proposed sequence.

## Completed baseline

- Documented the accepted architectural decisions.
- Established draft WTP and browser API boundaries.
- Identified the static PIO divider resolution issue for a representative HF carrier.
- Kept firmware, hardware support and protocol compliance explicitly unimplemented.

## Next slice: hardware-free job service and WTP contract

First resolve the wire framing, exact job profile, state transitions, duplicate handling, ownership and clock policies listed in WTP.md. Implement a portable C/C++ job service with a virtual clock and mock RF engine. Use the same service for host-submitted and standalone-generated jobs.

Acceptance evidence must cover partial/malformed/oversized messages, unsupported versions and modes, duplicate ARM, concurrent owners, late starts, loss of clock validity, reconnect/reset, cancellation, and complete local timing without further transport traffic. This slice must not access RF hardware.

Before extracting encoder code, inspect WsprryPi licensing and dependencies and record source revision/attribution. Initial candidate files include src/scheduling.hpp, src/scheduling_runtime.cpp and src/tests/wspr_tone_regression_test.cpp; finding them is not a portability review.

## Subsequent slices

1. Pin Pico SDK/toolchain and add a reproducible Pico 2 W build with USB CDC and a non-RF engine. Verify firmware identity, bounded parsing and memory use.
2. Complete the mathematical RF feasibility comparison; prepare the selected engine and measurement plan.
3. Implement and validate an RF engine under separately explicit hardware/RF authorization.
4. Add standalone encoding, station configuration, persistent schedules and device time acquisition. Verify autonomous operation without WsprryPi.
5. Add WsprryPi client integration using the same conformance fixtures; plan changes in that repository independently.
6. Add Wi-Fi/TCP, shared JSON API adapters and embedded browser assets, followed by SoftAP provisioning.
7. Add BLE provisioning/local management with a documented recovery path.
8. Qualify supported engine/mode/band combinations and release WsprryPico-x.y.z.uf2 with reproducible build identity.

Sequence may evolve based on RF feasibility. Standalone operation remains a product requirement even though USB control is the first transport.

## Current boundaries

No firmware build, hardware test, RF transmission, commit, push or GitHub publication has occurred in this baseline. Licensing, target bands, RF engine and final protocol schemas remain open.
