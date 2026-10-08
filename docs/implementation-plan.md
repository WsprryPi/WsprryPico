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
   remains in Phase 14.
10. **Complete:** WsprryPi client/backend integration, published operator manual,
    installed Linux release and bounded joint USB/conducted acceptance. Repaired
    physical timing, streaming, clock-refresh and launch-status findings were
    regression-tested and reassessed. Final source a3ec67d passed Tone, QRSS,
    FSKCW, DFCW and three consecutive independently decoded WSPR frames at the
    recorded 135500 Hz conducted setup. Final inhibited clock-loss, cancellation
    and USB reconciliation checks passed; inhibited firmware and original host
    services are restored. This is functional integration acceptance, with
    broader qualification retained in Phase 14. See the
    [target review](development/phase10-target-review.md) and
    [host acceptance guide](development/phase10-host-acceptance.md).
11. **Complete within documented scope:** optional mutually authenticated
    TLS WTP/TCP, browser API v1, embedded UI, network management and local
    certificate lifecycle. Host tests and firmware cross-linking are recorded in
    the [Phase 11 review](development/phase11-review.md). WsprryPi 11.1 host
    software is implemented independently. [11.2 concurrent management](development/phase11-2-review.md)
    supplies software isolation and instrumentation, with later bounded physical
    applicability recorded by 11.5/11.6 rather than an unrestricted timing claim.
    [11.3 DHCP/mDNS/hostname certificates](development/phase11-3-plan.md) is closed
    within its joint software/integration scope. [11.4 inhibited physical acceptance](development/phase11-4-plan.md)
    is closed within its bounded matrix, including the reviewed eight-hour soak.
    [11.5 target resource/contention acceptance](development/phase11-5-plan.md)
    is closed 6/6 for 138 MHz/divider 1. 11.6 is `CLOSED_SCOPED` at exactly
    13 accepted conducted rows, with no WSPR row accepted and all failures,
    blocked/untested work and 4 m/2 m configuration boundaries retained. The
    [11.7 joint review](development/phase11-7-review.md) reconciles current source,
    evidence applicability, regressions and documentation and closes Phase 11
    within those boundaries.
    The [selected QRSS-group limits](#planned-qrss-group-message-and-duration-limits)
    are implemented; affected 11.5 resource and extended-job physical acceptance
    are complete for the recorded 138 MHz/divider-1 configuration before 11.6
    acceptance of those jobs. Package 9 completed the R6 workload but failed its
    1,024-byte matched resource-return gate. Package 11 preserved that failure,
    qualified a separate two-host fixture and repaired the clock-poll,
    credential-owner, retained-terminal/memory and event-reducer harness paths
    exposed by four stopped attempts. Retry 4 then completed the exact fresh
    campaign. Its five matched windows pass the unchanged limit with a 520-byte
    post-N span and no monotonic growth; heap, stack, timing, fault, capture and
    restoration gates also pass. The independent
    [result](development/phase11-5-package11-retry4-result.json) and
    [review](development/phase11-5-package11-retry4-review.md) close R6 and
    Phase 11.5 at 6/6 families for that configuration.
    An alternative clock selected during 11.6 must repeat affected 11.5 checks.
    The systematic band x mode x clock comparison, final supported configurations,
    filters, spectral qualification and release firmware belong to Phase 14.
12. **Closed within selected scope:** Phase 12 provisioning/local control and consumer commissioning.
    The [Phase 12 plan](development/phase12-plan.md), operator-selected
    [field contract](development/phase12-field-access-contract.md) and
    [production review](development/phase12-production-acceptance-review.md)
    define the current boundary. The frozen
    [Field-GATT/1 contract](protocol/Field-GATT.md) and
    [conformance vectors](protocol/Field-GATT-v1-vectors.json) bind the custom
    BLE wire surface across firmware, Bluefy, the native-Pi client and host
    tests. Bounded profile activation and the later
    [automatic closeout](development/phase12-orchestratable-closeout-results.md)
    are accepted within their recorded scopes. All four declared automatic
    workstreams are complete. The operator accepted the final frozen scope
    dispositions on 2026-10-06; the phase is **CLOSED_SCOPED**. Broader
    interoperability and RF/release qualification remain unqualified.

    P12.1/P12.2 provide the portable profile journal and provisioning state
    machine. P12.4/P12.5 provide strict command decoding, delivery-safe
    activation coordination and shared PSA ownership. P12.6 enables the
    provisioning-only GATT service, network-only activator and indicator in the
    standard RF-inhibited image and builds an integrity-inventoried offline
    Bluefy release. Candidate adoption, preserved operational state and BLE
    advertising have partial physical evidence. The subsequent
    [BLE local-control continuation](development/phase12-ble-local-control-review.md)
    production-connects controller time, Identify/status and a separate
    unchanged WTP/1 stream to the same authorized GATT session and one
    `JobService`. Its clean committed standard image has verified Candidate A
    load/boot, preserved state and final RF-inhibited restoration. Later bounded
    iPhone 17 Pro Max/iOS 27.0/Bluefy 3.9.3 evidence accepts retained-bond
    authorization, one controller-time exchange, Identify LED/field status and
    WTP `HELLO` plus read-only `STATUS`. The native-Pi BLE subset and provisioned
    SoftAP control subset have separate bounded Candidate A evidence.

    The separate blank-device Wi-Fi-only encrypted SoftAP transaction is
    implemented at `fb091f8`; its RF-inhibited Candidate A open-AP preflight
    and selected-iPhone network-only generation-one reboot readback passed;
    final phone-page and AP-return rows were open at that checkpoint in the
    [target record](development/phase12-wifi-only-physical-result.md).
    The 2026-09-27 Safari/SoftAP selection and
    [P12.7 physical-owner decision](development/phase12-7-decision.md) are
    historical. The [revised open setup contract](development/phase12-safari-open-setup-revision.md)
    selects Wi-Fi first and optional station details without a retained phone
    owner or button ceremony. P12.9 is closed under its selected manual
    fixed-address portal gate; final consumer acceptance is in the current
    matrix. The earlier
    BLE/Bluefy evidence remains bounded engineering evidence. The later
    automatic closeout accepts credential-journal recovery, reset/old-peer
    refusal, engineering carrier/API composition, the two-hour resource capture
    and consumer Save/STATUS overlap. The later selected commissioning, LED,
    physical-cut and member results are retained in the
    [current matrix](development/phase12-closure-matrix.md), together with the
    operator's explicit timing/peer/fleet exclusions. Final RF accounting is
    19 acquisition attempts/13 charged jobs. G7 retains a measured cutoff and
    later same-boot usable portal; strict 50 ms/90 s assertions remain unqualified
    and GP14 production default enablement is deferred. Stage B and Phases 13
    and 14 remain separate; this closeout starts no new feature work.

13. **Planned:** feature completion before final qualification: complete
    solid RF-active transmit LED acceptance using the existing source wiring,
    and implement external Si5351 transmission support.
    This phase is open for additional user-selected features; see the
    [Phase 13 feature backlog](#phase-13-feature-backlog).
14. **Planned:** final hardware qualification and release, including the output
    network and filters, calibrated GPIO-edge timing, supported mode/band
    combinations and a reproducible release UF2.

## Phase 13 feature backlog

Selected on 2026-10-05 to follow Phase 12 and precede final qualification.
P13.1 now has a checked launch handshake and TX-only external routing through
the shared indicator owner. The operator-selected functional acceptance is
[CLOSED_SCOPED](development/phase13-1-step4-review.md), with fourteen target
GPIO/RF case results and verified restoration. Calibrated optical, physical
active-low wiring and mechanical GP14/header qualification remain separate.
External Si5351 implementation remains deferred. Additional features can be
added here as the user identifies them; no further feature scope is selected.

| Milestone | Selected work | Status |
| --- | --- | --- |
| P13.1 — Transmit LED | [Solid TX indication](development/transmit-led-backlog.md) across RF activation and cleanup; selected external LED is TX-only with operational cues onboard, or shared onboard TX takes priority over blinking. | CLOSED_SCOPED; source/host and 14 selected target case results accepted; no operator work remains |
| P13.2 — Si5351 engine | [External Si5351 transmission](development/si5351-transmission-backlog.md) through the shared job service for standalone and WsprryPi-controlled jobs, with local RP2350 timing, exclusive I²C ownership and engine failure/shutdown handling. | Planned |

Each feature includes its implementation and applicable behavior/target
acceptance. Phase 14 retains the final supported engine/mode/band/clock matrix,
calibrated timing, RF, reliability, filters and release qualification.

Numbering changed on 2026-10-05: the former Phase 13 qualification/release work
is now Phase 14. Historical acceptance records and execution prompts retain
their original numbering; their references to Phase 13 qualification mean
the current Phase 14.

<a id="planned-qrss-group-message-and-duration-limits"></a>

## QRSS-group message and duration limits

Decision: selected by the user on 2026-09-13. Implemented in Pico source
`7d183978d08d` and Pi companion `bba4024`. Phase 11.5 later accepted the limits
within its recorded 138 MHz/divider-1 physical scope; wider reliability and
configuration qualification remain in Phase 14.

- Apply one uniform maximum message length of **32 characters, including
  spaces**, to QRSS, FSKCW and DFCW. Every supported character counts equally;
  do not expose a different character limit based on Morse complexity or mode.
- Allow complete finite transmission jobs of up to **60 minutes (3,600 seconds)**,
  including any repetitions and gaps within the job. Message length and total
  duration are independent limits; show the calculated transmission duration.
- Preserve WSPR framing and the existing supported Morse alphabet. This decision
  selects neither a new alphabet nor additional punctuation or prosigns.
- Budget internal event capacity for the worst-case supported 32-character
  message in every QRSS-group mode, plus required job-boundary events. Resolve
  repeated-message representation separately within the finite-job, advertised
  event and payload limits; do not assume the character cap bounds expanded
  repetitions or introduce per-symbol transport delivery.
- Retain fixed waveform buffers and local RP2350 execution. Assess peak memory
  across parsing, job copies and RF planning; audit duration/sample arithmetic,
  advertised capabilities and companion client validation. WsprryPi changes
  remain independently scoped in that repository.
- Validate 32/33-character and 60-minute duration boundaries, worst-case Morse
  expansion, completion, cancellation, disconnect handling and sustained resource
  use. Hardware-free checks precede separately authorized physical acceptance;
  long-duration endurance qualification remains in Phase 14.

The implemented RF profile advertises 512 events and 3,600 seconds. The compact
message compiler expands finite repeats within both bounds; it never streams
symbol timing after ARM. Worst 32-character plans require 383 events, plus one
final off event for compact browser submissions. See the
[extended-job design](development/phase11-5-extended-job-design.md).
E0a has independently verified idle maximum admission and S0 has completed a
32-character, 384-event QRSS plan lasting 143.250001 seconds on the new image.
Actual QRSS, FSKCW and DFCW physical hours are recorded in checkpoints 006/010/012,
with their original observation limits preserved. Later Package 11 Retry 4
closed saturation/reclamation and Phase 11.5 at 6/6 for the recorded
configuration. The [current completion matrix](development/phase11-5-completion-matrix.md)
records source applicability and affected checks. The
[incremental ledger](development/phase11-5-acceptance-ledger.md#incremental-v2-validation)
preserves each applicable passing assertion without resetting unrelated checks.

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
Phase 14 qualification work.

## Subsequent slices

1. Phase 11 is closed within its documented software, bounded physical and
   scoped conducted-RF acceptance; do not broaden that result into release
   qualification.
2. Phase 12: finish the accepted BLE/SoftAP engineering boundary and the
   separately gated Safari/SoftAP consumer contract, offline controller UTC,
   indicator behavior and recovery acceptance.
3. Phase 13: complete transmit LED acceptance using existing source and
   implement/accept the external Si5351 engine;
   collect additional user-selected features in the
   [feature backlog](#phase-13-feature-backlog).
4. Phase 14: qualify supported engine/mode/band/clock combinations, timing, RF
   and reliability; finish output networks/filters and release a reproducible
   WsprryPico-x.y.z.uf2.

Sequence may evolve based on RF feasibility. Standalone operation remains a product requirement even though USB control is the first transport.

## Current boundaries

The firmware builds for Pico 2 W. The portable core and WTP USB endpoint are
host-tested, and bounded target USB validation passes on the recorded Pico 2 W
and Mac. Bounded RF bench transmissions, UTC-scheduled WTP integration and CPU
timing measurements are now recorded. Phase 11 adds its bounded inhibited,
resource/contention and scoped conducted-RF acceptance. Final supported
mode/band/clock combinations, calibrated timing and release engine promotion
remain open in Phase 14. WTP/1 schemas are
normative; changes to them require an explicit protocol-contract revision.
