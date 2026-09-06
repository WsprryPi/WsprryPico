# Implementation plan

Status: proposed sequence.

## Completed baseline

- Documented the accepted architectural decisions.
- Established draft WTP and browser API boundaries.
- Identified the static PIO divider resolution issue for a representative HF carrier.
- Recorded initial implementation and qualification boundaries; current status
  is detailed below.

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

## Completed Pico firmware foundation

The Pico SDK, Arm toolchain and picotool inputs are pinned. The Pico 2 W build
links the portable service to an unsynchronized target clock, fresh boot
identity, stable device identity and RF-inhibited engine. Two USB CDC interfaces
separate text diagnostics from bounded WTP framing. CMake presets and VS Code
metadata provide the same repository-root build.

## Completed dual USB CDC transport

Dedicated Console/WTP APIs provide bounded RX/TX, partial-write handling,
connection resets, distinct descriptor identities and deterministic isolation
checks. Hardware USB validation remains separately opt-in.

## Completed strict WTP USB adapter

Strict JSON request decoding, response/event encoding and typed job-service
routing now run on the WTP CDC interface. Connection negotiation, replayed
snapshots, logical closure and bounded ordered transmission are host-tested
against normative fixtures, the independent schema validator and monitor decoder.
An opt-in read-only probe is supplied. Bounded target USB checks pass for the
[recorded board, image and host](development/usb-target-validation.md); general
WTP conformance and RF qualification are not claimed.
See the [endpoint guide](development/wtp-endpoint.md).

## Completed RF feasibility and candidate selection

The [hardware-free comparison](rf-feasibility.md) and
[reproducible calculations](rf-calculations.md) compare static dividers,
PLL retuning, PIO/DMA synthesis and Si5351. PIO/DMA packed-bit GPIO synthesis
is selected for experimental implementation, initially at the 80 m study point,
with generation throughput, job lifecycle behavior and spectra still to assess. Si5351 remains
an alternative. This is candidate selection, not engine implementation or RF
qualification. The [bounded measurement plan](development/rf-measurement-plan.md)
remains broader than the initial bench measurements.

## Completed first Step 8 software slice

The [portable stream](development/rf-stream.md) implements bounded initial-tone
planning, packed waveform generation and a streaming engine behind an abstract
sink. Host tests cover sample accuracy, phase continuity, timing, ownership,
faults and job-service integration; the library also cross-compiles for Arm.
The [output/inhibit design](development/rf-output-design.md) is a proposal,
with electrical/filter details and qualification still pending.

## Completed second Step 8 software slice

The [PIO/DMA driver](development/pio-dma-driver.md) implements GP2 output,
finite buffer handoff, final zero clearing and local timer launch. The job service
can prearm local engines while preserving existing WTP clock and missed-start
semantics. Host fault/sequence tests pass and the actual SDK driver links for
Pico 2 W. No physical transmission was performed for this slice.

## Completed third Step 8 slice: bench integration and initial measurements

The separate [RF bench](development/rf-bench.md) implements finite relative-time
tones, CPU benchmarks, observed IRQ/stack metrics and software BOOTSEL. Exact word
lookup reduced worst measured refill from 22.092 ms to 1.507 ms with the same
checksum. Two preloaded data DMA channels and a dedicated final stop channel
resolved observed underruns. Recorded 100 ms and 1 s tones completed and were
received using the Harness capture helper on wspr5 through 60 dB attenuation.
Coarse carrier analysis remains inconclusive for qualification.

## Completed fourth Step 8 slice: frame and reference measurements

The [frame validation record](development/rf-frame-validation.md) covers two
complete 162-symbol synthetic frames, a ten-second tone against the GPSDO on
the combiner, and intentional abort/rearm. All 161 transitions were located;
maximum estimated timing error was 0.5 ms. The compared carrier was about
+7.85 Hz high, and frame frequency residual exceeded the 0.1 Hz diagnostic
criterion at 0.123 Hz. An in-window feature measured about -32 dBc. These remain
physical engineering findings; no WSPR message was encoded or decoded.

## Completed fifth Step 8 slice: correction and alias diagnosis

The [correction record](development/rf-correction-validation.md) validates
volatile frequency correction: short-run mean error fell from +7.974 Hz to
approximately +0.012 Hz with 2222 ppb correction. Retune, gain and reference-only
controls support an intrinsic sampled-square-wave alias near -33 dBc. The full
frame still fails the linear residual limit; a separate fit describes a roughly
0.40 Hz settling transient. Neither finding is silently promoted to a pass.

## Completed sixth Step 8 slice: clock and comparison experiments

The [clock validation record](development/rf-clock-validation.md) adds tested
132/138/150 MHz profiles and selects 138 MHz for the experimental bench. It
removes the original roughly -33 dBc alias at the recorded frequency. The
stronger +/-120 Hz sidebands follow a translated carrier and also occur on
wspr2 GPIO4. CPU activity before a frame did not materially improve settling
in the tested protocol. Progress arithmetic, completion acknowledgement and
capture storage checks were repaired and tested.

## Next slice: close-in sidebands and stable frame timing

Investigate the shared 120 Hz pattern with controlled power/ground and receiver
comparisons, and resolve full-frame settling/transition diagnostics. Then
verify an encoded WSPR message and integrate production UTC/job-service
operation. No encoded message was tested in this slice. Step 8 remains open;
the operator chooses hardware experiments and transmissions.

Before extracting encoder code, inspect WsprryPi licensing and dependencies and record source revision/attribution. Initial candidate files include src/scheduling.hpp, src/scheduling_runtime.cpp and src/tests/wspr_tone_regression_test.cpp; finding them is not a portability review.

## Subsequent slices

1. Implement and validate the physical RF engine with operator-directed hardware testing.
2. Add standalone encoding, station configuration, persistent schedules and device time acquisition. Verify autonomous operation without WsprryPi.
3. Add WsprryPi client integration using the same conformance fixtures; plan changes in that repository independently.
4. Add Wi-Fi/TCP, shared JSON API adapters and embedded browser assets, followed by SoftAP provisioning.
5. Add BLE provisioning/local management with a documented recovery path.
6. Qualify supported engine/mode/band combinations and release WsprryPico-x.y.z.uf2 with reproducible build identity.

Sequence may evolve based on RF feasibility. Standalone operation remains a product requirement even though USB control is the first transport.

## Current boundaries

The firmware builds for Pico 2 W. The portable core and WTP USB endpoint are
host-tested, and bounded target USB validation passes on the recorded Pico 2 W
and Mac. Bounded RF bench transmissions and CPU timing measurements are now
recorded. Supported bands, calibrated target timing and final engine promotion
remain open. WTP/1 schemas are
normative; changes to them require an explicit protocol-contract revision.
