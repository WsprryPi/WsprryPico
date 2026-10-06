# Transmit LED backlog

Recorded: 2026-10-03. Updated: 2026-10-05.
Status: selected requirement; source foundation present, completion/acceptance deferred.
Roadmap assignment: **Phase 13 / P13.1**, selected on 2026-10-05; see the
[feature backlog](../implementation-plan.md#phase-13-feature-backlog).
Final hardware/release qualification follows in Phase 14.
This entry authorizes documentation only, not firmware changes or hardware tests.

Whenever the transmitter is hot (RF output active), the selected TX LED must
light solid for the entire active interval. This includes RF-producing warmup,
tones and all supported transmission modes, from output activation until output
is confirmed inactive after completion, stop, abort or failure. Queued, loaded
or armed work alone must not assert the TX indication. Follow actual local
RF-output activity, including any mode gaps that deactivate output, rather than
assuming that a running job is continuously hot.

Solid TX indication takes priority over AP-ready and Identify blink patterns.
After confirmed RF inactivity, the existing non-TX pattern may resume. Use one
indicator owner so competing writers cannot blink or extinguish the LED during
active output. The LED reports application/engine output state; it is not an
independent RF measurement. Do not show a simulated or RF-inhibited job as hot.

Preserve the [pin-assignment contract](../pin-assignment-contract.md): onboard
LED by default, configurable external GPIO/polarity, or explicitly disabled.
The solid indication requirement applies when the TX indicator is enabled.

## Current source finding

At reviewed `devel` commit `dd419af`, `IndicatorController::desired()` in
`src/provisioning/field_runtime.cpp` returns solid on while `transmitting_`
is true, ahead of AP/Identify blink selection. The standalone main loop supplies
`engine.output_active()` through `indicator.transmitting()` and polls the same
owner. Boot-applied pin selection already supplies onboard, external or disabled
indicator output. `tests/field_access_tests.cpp` contains active-output priority
and disabled-indicator behavior checks. These are current source observations;
this documentation review does not run or newly qualify those tests.

The earlier note that solid indication and its production wiring were absent
is superseded. Phase 13 must reuse this foundation and assess the full selected
RF-active interval, engine/mode coverage, write-failure behavior and physical
timing. Source wiring alone does not establish complete target/RF acceptance.

## Deferred implementation and acceptance

- Recheck the current source before implementation; reuse any implementation
  added since this review rather than introduce another LED owner.
- Verify the existing shared indicator owner follows authoritative local
  RF-output state across standalone and all job-control transports, including
  warmup and cleanup; repair any demonstrated gaps.
- Add deterministic checks for active/inactive transitions, queued/armed work,
  inhibited/simulated execution, mode gaps, stop/abort/failure cleanup, LED write
  failures and priority over simultaneous AP/Identify patterns. Never report
  successful shutdown solely because the LED was switched off.
- Verify the existing onboard and external active-high/active-low selection
  and exclusive pin ownership across the selected acceptance cases.
- Separately authorize opt-in target/RF verification. Record exact board,
  firmware, engine, clock, mode and setup; host checks alone cannot qualify
  physical LED timing or RF cutoff.
