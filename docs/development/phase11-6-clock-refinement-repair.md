# Phase 11.6 clock-refinement repair preparation

Status: **PREPARED, NOT DEPLOYED; PHASE 11.6 OPEN**

## Preserved failure

Phase 11.6 attempt 41 is retained as a failed 160 m QRSS production attempt,
not replaced by this repair. Job `0469a3439addf59e0000000000000001`
received a successful `ARM` for monotonic target `1789758507376197814`. The
Pico was armed about 11.79 seconds before that target. During the armed
interval, an accepted SNTP sample reduced reported uncertainty from about 38
ms to 3.7 ms and changed the UTC-to-monotonic mapping by about 9 ms. The
deployed guard treated disagreement with the immutable ARM-time monotonic
projection as a missed start. No launch was recorded.

The attempt remains charged at its full planned 45.000001 seconds under the
campaign's conservative accounting rule. Cumulative Phase 11.6 accounting is
41 attempts and 1200.000028 planned RF seconds. Both Picos were independently
verified inactive before the shared reservation was released.

## Defect and repair

The requested UTC timestamp, not its first local timer projection, is the
immutable scheduling contract. A newer admissible clock sample must refine the
local projection without requiring a second WTP `ARM`:

- if the refined target is still in the future, replace the local hardware
  alarm and remain Armed;
- if refinement shows that the requested instant has just passed, launch as
  soon as possible only while still inside the admitted UTC second; and
- continue to reject an invalid clock, excessive uncertainty, unsafe leap
  interval, an expired UTC window, a target at or beyond the original
  monotonic deadline, or an invalid driver launch observation.

`StreamEngine` now projects the immutable UTC request from the freshest
admissible clock snapshot. `PioDmaSink` distinguishes launched, rescheduled and
rejected alarm outcomes. `PicoPioDma` may replace the hardware-alarm target from
its callback; Pico SDK 2.3.1 clears the completed callback's pending bit before
invocation and documents that setting a target replaces the prior target. A
successful launch still occurs at most once and anchors the unchanged sample
timeline to its observed launch.

No job event, frequency, duration, waveform, sample clock, divider, renderer,
DFCW polarity or WTP client request changes. Existing `alarm_irqs` and
`launch_target_ns` telemetry expose a later re-arm and the final reprojected
target without increasing the INFO response.

## Source impact and required candidate checks

This is a physical RF launch-path and clock-behavior change. Phase 11.5's exact
accepted source/image identity does not transfer automatically to a deployed
candidate.

- `R1.1` and `R1.5`: linked layout/stack checks are affected by the new code.
  The provisional physical image adds 144 text bytes relative to the retained
  local Package 9 build and has identical BSS; linked heap, stack-guard and RAM
  renderer checks pass. Fresh target heap/stack observations remain required.
- `R2.1` through `R2.7`: only their shared prelaunch mapping and alarm path are
  affected. Mode compilation, frequencies, durations, rendering and postlaunch
  DMA/refill behavior are unchanged. Preserve their original physical evidence;
  require a repaired-candidate launch/refinement check before transferring the
  shared launch-path applicability.
- `R6.gates`: the timing/resource portion is affected. Require fresh inactive
  baselines, clock/launch telemetry, heap reserve, stack guards and
  allocator/TLS/DMA/fault counters around the bounded corrective job. The
  allocation and retention design is unchanged, so the 1,800-second resource
  campaign is not automatically repeated.
- R3-R5 authority, replay, network and storage implementations are unchanged.
  A deployment still requires fresh source/image/boot inventory and an
  authenticated control-path check; historical results retain only their
  recorded image scope.

The minimum physical gate before resuming the matrix is one identified Pico A
deployment, fresh inactive inventory, an observed armed-interval clock
refinement that does not produce `MISSED_START`, and one bounded conducted
corrective QRSS job with the affected target metrics. If the intended
refinement is not observed, stop rather than retry automatically. Pico B is not
part of this deployment.

## Software and build evidence

- The historical C4 25.805 ms earlier-target replay now launches inside the
  admitted UTC second. An unchanged-mapping control also launches.
- The opposite 25.805 ms correction re-arms the local alarm and then launches
  exactly once. A fabricated early driver observation fails closed.
- Hardware-free Linux affected/full-exclusion suite: 63/63 passed. The five
  excluded full-suite cases are four Git-history archive checks that cannot run
  in the history-free snapshot and one host-platform-calibrated reply-reserve
  group; all other reply target tests passed.
- Phase 11.5 Package 9 and Phase 11.6 focused Python checks: 44/44 passed.
- WTP artifact validation: 23 schema, seven raw JSON, one framing and eight
  transition cases passed.
- C/C++ format and `git diff --check` passed for the repair.
- Pico 2 W physical target linked with SDK 2.3.1 and Arm GCC 15.3.1. Linked
  heap hooks, stack guards and RAM renderer checks passed.

The current source-only, dirty-worktree build is deliberately provisional and
must not be treated as a deployment identity. Its StandaloneRF UF2 SHA-256 is
`f98038e4bce0393c3b3ea68cadf8f79b80d266ab0916d4c9be0181a92f634562`;
the linked ELF SHA-256 is
`8f7854f16eb17fdbea609f6d848c0b5952f49fd19cc7accfe791fa23ca2f9cd3`.
A clean committed candidate must be rebuilt and identified before any flash.

## Authorization boundary

No flash, reboot, BOOTSEL action, CONFIG write or additional RF attempt was
performed while preparing this repair. Deployment and the bounded corrective
RF gate require fresh explicit operational authorization.
