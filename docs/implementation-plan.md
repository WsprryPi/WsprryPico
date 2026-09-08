# Implementation plan

Status: temporary development roadmap and progress record.

This file is useful while implementation is active. Remove roadmap sequencing,
completed-work narration and other progress material before the documentation is
treated as long-term product documentation.

## Current roadmap snapshot

1. **Complete:** architecture and protocol boundaries.
2. **Complete:** WTP/1 contract and validation fixtures.
3. **Complete:** portable job service and RF lifecycle.
4. **Complete:** Pico 2 W firmware foundation.
5. **Complete:** dual USB CDC transport.
6. **Complete:** strict USB WTP endpoint.
7. **Complete:** RF feasibility study and PIO/DMA selection.
8. **Complete:** physical RF engine and UTC-scheduled WTP integration, including
   GP2 output, encoded WSPR, comparative spectrum work, USB UTC synchronization,
   scheduled local execution, conducted SDR capture and independent decoding.
9. **Complete:** persistent station/schedules, device SNTP, retained watermark,
   Wi-Fi loss/reconnection and recovery controls, plus recurring standalone RF
   frames independently decoded after a wall-power boot without a USB host.
   This is bounded functional acceptance; final RF/reliability qualification
   remains in Phase 13.
10. **Complete:** WsprryPi client/backend integration, published operator manual,
    installed Linux release and bounded joint USB/conducted acceptance. Repaired
    physical timing, streaming, clock-refresh and launch-status findings were
    regression-tested and reassessed. Final source a3ec67d passed Tone, QRSS,
    FSKCW, DFCW and three consecutive independently decoded WSPR frames at the
    recorded 135500 Hz conducted setup. Final inhibited clock-loss, cancellation
    and USB reconciliation checks passed; inhibited firmware and original host
    services are restored. This is functional integration acceptance, with
    broader qualification retained in Phase 13. See the
    [target review](development/phase10-target-review.md) and
    [host acceptance guide](development/phase10-host-acceptance.md).
11. **Planned:** Wi-Fi/TCP and the shared browser API.
12. **Planned:** SoftAP and BLE provisioning.
13. **Planned:** final hardware qualification and release, including the output
    network and filters, calibrated GPIO-edge timing, supported mode/band
    combinations and a reproducible release UF2.

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

## Completed seventh Step 8 slice: encoded WSPR and RF warmup

The [encoded validation record](development/rf-wspr-validation.md) adds a
portable Type 1 encoder, a complete-message bench command, and independent
WSJT-X decoding of received RF from wspr5. Optional RF warmup improves the
measured frame settling. The final-data/tail acknowledgement path has additional
bounded recovery tests. Retained cold-frame diagnostic failures remain distinct
from successful decodes and repaired-image evidence.

The operator accepts better-than-WsprryPi close-in sidebands as a practical
benchmark. The earlier comparison meets that criterion; eliminating those
sidebands is not a prerequisite for further development. Planned output
filtering remains part of the final hardware assessment.

## Completed eighth Step 8 slice: USB UTC and RF job integration

The [UTC/WTP integration record](development/utc-rf-job-validation.md) adds a
portable bounded-uncertainty clock, a sampled USB time source and an explicitly
selected RF-capable WTP image. A future UTC job completed locally without
per-symbol USB traffic and independently decoded from a complete wspr5 capture.
The standard firmware remains inhibited. USB host time, receiver wall-clock
onset, the output network and calibrated filter/band behavior are not qualified.

## Step 9: standalone configuration, timing and physical operation

The [standalone guide](development/standalone.md) documents persistent station
identity and recurring schedules, an independent no-repeat watermark, Wi-Fi
SNTP acquisition and one-time Console provisioning. Standalone and USB WTP jobs
share the same job service. The standard image is RF-inhibited; an explicit
standalone RF image retains the experimental GP2 engine.

Deterministic and sanitizer tests cover autonomous simulated completion,
configuration/storage failures, restart/clock-step behavior, SNTP rejection and
host ownership. All firmware targets cross-link. The later
[inhibited bench record](development/standalone-physical-validation.md) adds real
configuration retention, autonomous SNTP, scheduled local simulation, Wi-Fi
outage/reconnection and watchdog recovery. The subsequent
[RF and wall-power record](development/standalone-rf-power-validation.md) adds
independently decoded recurring frames without USB job commands, a physical
separate-power boot, USB-host absence, and retained configuration/watermark.
This closes Phase 9's bounded functional acceptance. Calibrated timing,
output/filter performance, wider network compatibility and endurance remain
Phase 13 qualification work.

## Subsequent slices

1. Add Wi-Fi/TCP, shared JSON API adapters, embedded browser assets and network status/management.
2. Add SoftAP and BLE provisioning/local management with a documented recovery path.
3. Qualify supported engine/mode/band combinations, timing, RF and reliability; finish output networks/filters and release a reproducible WsprryPico-x.y.z.uf2.

Sequence may evolve based on RF feasibility. Standalone operation remains a product requirement even though USB control is the first transport.

## Current boundaries

The firmware builds for Pico 2 W. The portable core and WTP USB endpoint are
host-tested, and bounded target USB validation passes on the recorded Pico 2 W
and Mac. Bounded RF bench transmissions, UTC-scheduled WTP integration and CPU
timing measurements are now recorded. Supported bands, physical autonomous timing,
calibrated target timing and final engine promotion remain open. WTP/1 schemas are
normative; changes to them require an explicit protocol-contract revision.
