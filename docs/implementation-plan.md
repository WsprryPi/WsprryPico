# Implementation plan

Status: proposed sequence.

## Completed baseline

- Documented the accepted architectural decisions.
- Established draft WTP and browser API boundaries.
- Identified the static PIO divider resolution issue for a representative HF carrier.
- Kept firmware, hardware support and protocol compliance explicitly unimplemented.

## Completed WTP/1 contract

- Defined framing, exact representations, envelopes and operation schemas.
- Defined finite job limits, state transitions, ownership and clock rules.
- Defined retry, replay, reconnect, reset, error and transport behavior.
- Added machine-readable contract data, normative vectors and a dependency-free
  hardware-free validator.

## Completed hardware-free job service

The portable C++20 core now provides bounded frame parsing, SHA-256 replay
identity, typed request dispatch, ownership leases, immutable jobs, clock-aware
arming, lifecycle management, retained results and output-safe cancellation.
Deterministic tests use a virtual clock and mock RF engine.

Host evidence covers partial, malformed and oversized frames, unsupported
versions and modes, duplicate requests and ARM, concurrent owners, late starts,
clock rejection, reconnect/reset behavior, cancellation, output-disable
failure, and local execution without further requests. It is not target or RF
evidence.

## Next slice: Pico firmware shell and USB adapter

Pin the Pico SDK and target toolchain, add a reproducible Pico 2 W build, and
adapt USB CDC to the portable frame and job-service boundaries. Add strict JSON
request decoding, response/event encoding and a non-RF engine. Keep all target
and USB device activity separately opt-in.

Before extracting encoder code, inspect WsprryPi licensing and dependencies and record source revision/attribution. Initial candidate files include src/scheduling.hpp, src/scheduling_runtime.cpp and src/tests/wspr_tone_regression_test.cpp; finding them is not a portability review.

## Subsequent slices

1. Complete the mathematical RF feasibility comparison; prepare the selected engine and measurement plan.
2. Implement and validate an RF engine under separately explicit hardware/RF authorization.
3. Add standalone encoding, station configuration, persistent schedules and device time acquisition. Verify autonomous operation without WsprryPi.
4. Add WsprryPi client integration using the same conformance fixtures; plan changes in that repository independently.
5. Add Wi-Fi/TCP, shared JSON API adapters and embedded browser assets, followed by SoftAP provisioning.
6. Add BLE provisioning/local management with a documented recovery path.
7. Qualify supported engine/mode/band combinations and release WsprryPico-x.y.z.uf2 with reproducible build identity.

Sequence may evolve based on RF feasibility. Standalone operation remains a product requirement even though USB control is the first transport.

## Current boundaries

No firmware build, hardware test or RF transmission has occurred. The portable
core is host-tested but is not a complete WTP endpoint. Licensing, target bands
and RF engine remain open. WTP/1 schemas are normative; changes to them require
an explicit protocol-contract revision.
