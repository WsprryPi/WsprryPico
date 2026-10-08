# Transmit LED backlog

Recorded: 2026-10-03. Updated: 2026-10-08.
Status: **CLOSED_SCOPED** for the operator-selected LED work. Source/host checks,
thirteen preceding target cases, reviewed standalone STOP and the
[external GP15 routing result](phase13-1-step4-review.md) pass. No operator work
remains; broader hardware/release qualification retains its separate scope.

The external GP15 lamp wiring is operator-confirmed. The final functional
check used GPIO/SDR evidence without another LED, camera, rewiring or operator
session; see the [completed six-step TODO](phase13-1-closeout-steps.md).
The existing external-high TX-only/AP/Identify case passed with actual GPIO,
complete SDR evidence and reviewed restoration. Timing/shutdown and software
polarity evidence is reused; no new GP14 stimulus or polarity campaign was
needed for closure. A separately wired active-low lamp and mechanical button/header
qualification are outside this selected scope and are not marked PASS.
Roadmap assignment: **Phase 13 / P13.1**, selected on 2026-10-05; see the
[feature backlog](../implementation-plan.md#phase-13-feature-backlog).
Final hardware/release qualification follows in Phase 14.
The operator authorized P13.1 implementation, review, commit and push on
2026-10-07. Live testing follows the current [project instructions](../../AGENTS.md):
the user's statement that a named Pico is connected to the SDR authorizes RF
testing and the routine device-control/restoration steps needed for this task.

Whenever the transmitter is hot (RF output active), the selected TX LED must
light solid for the entire active interval. This includes RF-producing warmup,
tones and all supported transmission modes, from output activation until output
is confirmed inactive after completion, stop, abort or failure. Queued, loaded
or armed work alone must not assert the TX indication. Follow actual local
RF-output activity, including any mode gaps that deactivate output, rather than
assuming that a running job is continuously hot.

When onboard TX is selected, solid TX takes priority over AP-ready and Identify
blink patterns; after confirmed inactivity the applicable cue may resume.
The operator clarified on 2026-10-07 that a selected external LED is **TX only**:
AP-ready and Identify continue on the onboard LED, never on the external pin.
Without an external selection, the current onboard LED supplies TX indication.
One controller owns both outputs so operational writes cannot blink or extinguish
external TX. The LED reports application/engine output state; it is not an
independent RF measurement. Do not show a simulated or RF-inhibited job as hot.

Preserve the [pin-assignment contract](../pin-assignment-contract.md): onboard
LED by default, configurable external GPIO/polarity, or explicitly disabled.
The solid indication requirement applies when the TX indicator is enabled.

## Historical foundation

At reviewed `devel` commit `dd419af`, `IndicatorController::desired()` in
`src/provisioning/field_runtime.cpp` returns solid on while `transmitting_`
is true, ahead of AP/Identify blink selection. The standalone main loop supplies
`engine.output_active()` through `indicator.transmitting()` and polls the same
owner. Boot-applied pin selection already supplies onboard, external or disabled
indicator output. `tests/field_access_tests.cpp` contains active-output priority
and disabled-indicator behavior checks. These are current source observations;
this documentation review does not run or newly qualify those tests.

The earlier note that solid indication and its production wiring were absent
is superseded. The P13.1 execution found an activation gap in this polling-only
foundation and an acceptance-only Identify-over-TX exception.

## Implemented source behavior

`WsprryPico-StandaloneRF` now requests a unique indicator acknowledgement only
at a valid local launch attempt. The selected TX output must have a checked
on state before PIO activation. Missing/failed writes keep RF inactive and
expire inside the existing start window. Disabled selection bypasses the gate.
The RF owner never writes CYW43 or waits on USB/network symbol delivery.

The request holds solid TX across the active engine interval and is released
only after checked physical inactivity, including delayed hardware completion
and failed shutdown. The normal onboard cue may resume at the next core-0
poll, so indication can briefly lead activation and lag confirmed inactivity.
Onboard and external checked state/faults are tracked separately; an onboard
AP flash cannot acknowledge external TX. Faults remain latched after retry
recovery. GPIO polarity and requested-level preload are host-tested through
the actual Pico indicator adapter. The standard simulator never requests TX.

The [execution prompt](phase13-1-transmit-led-prompt.md),
[adversarial review and validation](phase13-1-transmit-led-review.md),
[proposed physical packet](phase13-1-transmit-led-physical-packet.md) and
[complete finite jobs](phase13-1-transmit-led-cases.json) record this slice.
That original physical packet is historical; the selected functional acceptance
is now closed by the step-4 record. Legacy single-core RFBench/RFWTP diagnostic
images are outside this application indicator graph; their historical warmup
captures do not qualify the new application LED. External wiring, physical
edge timing and broader engine/mode/band/clock qualification require recorded
target evidence, with final release qualification remaining Phase 14.

The [GPIO execution record](phase13-1-gpio-validation-review.md) records actual
onboard readback, RF results, retained failed ledgers and restoration. No camera
or new backup is required for the operator-selected functional scope.
The [standalone STOP follow-up](phase13-1-standalone-stop-closeout-review.md)
closes both checker findings with complete target evidence; original partial
and failed records remain preserved.
