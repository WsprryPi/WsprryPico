# Phase 12 BOOTSEL button execution brief

Status: **EXECUTED HISTORICAL BRIEF; BUTTON TIMING SUPERSEDED; PHYSICAL BUTTON
AND RF ACCEPTANCE OPEN**
(2026-09-29). Work on `devel`. The objective below records the original
request; the operator subsequently changed classification to occur only on
release, with stop for under one second and stop plus AP for over nine seconds.
The current behavior is in the
[P12.7 revision](phase12-safari-open-setup-revision.md). This brief does not
authorize flashing, a physical button press, GPIO operation or RF output.

## Objective

Implement and assess a safe path for the Pico 2 W's only onboard button:

1. On a short press, stop any current and autonomous transmission, confirm
   output inactive, then restart the application without erasing settings.
2. On a continuous press reaching ten seconds, stop transmission promptly,
   then present the setup SoftAP after release. Restart only if required for a
   safe AP state. A long press never also triggers the short-press restart.
3. Neither gesture alters Wi-Fi, station, schedule, watermark or access
   journals. The AP must remain usable during a healthy station connection
   long enough to complete a settings transaction.

## Source and safety work

- Preserve the current tree, Phase 11 closure and P12.9 accepted scope. Review
  the old BOOTSEL long-hold incident, whole-gesture diagnostic, RF worker,
  `JobService`/scheduler shutdown, reboot path and `SoftApCoordinator` first.
- Keep gesture policy portable under `src/` and host-test threshold, bounce,
  short/long exclusivity, time wrap, repeated/stuck press, shutdown failure,
  rearm prevention and preserved settings. Keep Pico SDK register handling in
  its adapter. Use no boot-time hold as an application command: ROM intercepts
  it.
- Never restore XIP or let either core use flash while a sampled press still
  requires flash isolation. Do not reintroduce the withdrawn short background
  sampler. Bound watchdog and stalled-button behavior and inspect linked SRAM
  callbacks for flash references and calls out of SRAM.
- On detected press, establish a safe stop path before waiting for the
  ten-second classification. For the real PIO/DMA engine, prove that flash
  isolation cannot leave output active while the worker is paused; otherwise
  disable the feature for that image and mark the requirement open. Treat an
  unknown output state as failure, not permission to reboot normally or open
  setup.
- Give a manual AP request a bounded lease that survives a healthy station
  and a restart if one is necessary. Preserve automatic blank-profile and
  station-loss fallback and any active setup reply. Fail closed on resource,
  network, watchdog or journal errors; do not turn a failed button action into
  profile erase or RF authority.

## Validation and acceptance

- Run affected deterministic host tests, formatting, `git diff --check`,
  documentation-link checks and pinned Pico 2 W cross-build plus linked-image
  safety checks if the local tools are available. Report each exact command.
- Review the result adversarially for XIP/core-1 races, ten-second hold,
  watchdog expiry, active-RF shutdown, reset ordering, AP lease, station
  coexistence, settings preservation and unexpected button actions. Repair
  actionable findings, rerun affected checks and reassess.
- Source checks and RF-inhibited cross-builds cannot close physical button or
  actual-transmission acceptance. Record the exact remaining target tests and
  hardware/RF authorization boundary. Do not advertise the gestures in the
  production image until those gates pass. If no safe architecture for an
  arbitrary unprompted press is supported by the evidence, stop before wiring
  a production gesture and report that blocker explicitly.

Commit the reviewed source and documentation on `devel`, push the commit, and
report the actual remote result and remaining gates. Do not close P12.7,
P12.8, P12.11, P12.12 or Phase 12 based only on this source execution.

## Execution result

The [adversarial review](phase12-bootsel-button-review.md) records the original
source attempt and the later release-time correction. The prompt's fail-closed
rule stopped production gesture wiring before an unsafe sampler could be
introduced.
