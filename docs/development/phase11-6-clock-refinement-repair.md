# Phase 11.6 clock-refinement repair and deployment record

Status: **REPAIR COMMITTED; CORRECTED IMAGE DEPLOYED; ZERO-RF CANDIDATE
GATES PASS; CORRECTIVE RF GATE PENDING; PHASE 11.6 OPEN**

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

The source-only, dirty-worktree build was deliberately provisional and was not
treated as a deployment identity. Its StandaloneRF UF2 SHA-256 was
`f98038e4bce0393c3b3ea68cadf8f79b80d266ab0916d4c9be0181a92f634562`;
the linked ELF SHA-256 was
`8f7854f16eb17fdbea609f6d848c0b5952f49fd19cc7accfe791fa23ca2f9cd3`.
A clean committed candidate was subsequently rebuilt and identified as
described below.

## First deployment attempt and retained stop

The operator authorized one clean Pico A deployment, affected Phase 11.5
candidate checks and at most one additional 45.000001-second 160 m QRSS
corrective attempt. Repair source `2eaa99945d21501cd4dbdac98c25be5fa146e479`
and the companion WsprryPi change `3b046ebe3eaa19ae764706d844fa7354033c32df`
were committed and verified at `origin/devel` before the build.

The first clean network-enabled image used the accepted 138 MHz, divider-1,
RAM-rendered, Pico A TLS configuration, but the build command omitted the
accepted `WSPRRY_PICO_STANDALONE_WSPR_BASE_FREQUENCY_HZ=135500` override. It
therefore compiled the generic 3,570,100 Hz standalone default. Its UF2
SHA-256 was
`04a4091dd8658711ea1f495b2284ed610214a712653ee039c0dae2222b279df4`;
its ELF SHA-256 was
`7255b07d834014ff1b1da4fd5c4117f3177f801686ee21203f9c82794b8347b7`.

The serial-bound deployment backed up the full pre-flash contents, loaded and
verified that UF2 once, and produced Pico A boot
`0839b9427c766e4a93f3e76c6a8ad718`. Post-flash inventory confirmed the repaired
source, 138 MHz/RAM/GP2 engine, valid stack guards, zero allocator, TLS and DMA
faults, retained station/schedules/watermark, configured network identity and
inactive output. The deployment gate nevertheless rejected the candidate
because `schedule_base_frequency_nhz` changed from `135500000000000` to
`3570100000000000`. Schedules remained disabled. No CONFIG write, RF job or
corrective attempt occurred.

The shared reservation remained HELD after that stop. Fresh authoritative A/B
inventories then proved both boards empty, inactive and unowned; the exact
authorized A boot/revision transition was reconciled and the reservation was
released. The installed image is not an accepted Phase 11.5 or 11.6 candidate.
The full private record is retained under mode 0700 at
`/home/pi/phase11-6-conducted-v3-20260918/repair-2eaa999-deployment` on wspr5;
the sanitized result is
[`phase11-6-clock-refinement-deployment-attempt1.json`](phase11-6-clock-refinement-deployment-attempt1.json).

## Corrected candidate and second deployment

A second clean build from the same repair source explicitly restores the
accepted 135,500 Hz standalone base while retaining the listener, 138 MHz
clock, divider 1 and RAM renderer. SDK 2.3.1 and Arm GCC 15.3.1 linked it; heap
hooks, stack guards, RF RAM placement and the reserved flash boundary passed.
The corrected, not-deployed hashes are:

- UF2: `af3f6917ba807a1526dca6e15f19fff1974410fc87ecc32fd6e9c4f07059525f`;
- ELF: `a8683a1b84a443e7ecfce5b894c26f1041146b13f6446a22a9e8d0d5431e27be`;
- map: `cbd9f66d852be055070aa3a291f86b129535694b9a7481dff35ff0a6ca117074`.

The first deployment authorization was spent by the rejected build. The
operator then explicitly authorized exactly one additional serial-bound flash
of this corrected UF2. The bounded deployment performed one BOOTSEL transition,
backed up the full installed flash, wrote and verified the exact UF2, and made
no CONFIG or RF request. The installed candidate is now:

- source `2eaa99945d21501cd4dbdac98c25be5fa146e479`;
- UF2 SHA-256
  `af3f6917ba807a1526dca6e15f19fff1974410fc87ecc32fd6e9c4f07059525f`;
- boot `b72fed2c17583cc7aba0f1345f76a3b2`;
- retained standalone base `135500000000000` nHz;
- Pico 2 W Arm, 138 MHz, divider 1, RAM renderer, `pio-dma-gp2` on GP2.

Fresh post-flash A/B inventories confirmed A empty, inactive, unowned and
schedule-disabled with valid stack guards, more than 32,768 bytes of heap
reserve and zero allocator, TLS, DMA and fault counters. Pico B retained source
`8921a7008183` and boot `6684b4b197d80cfa0ce83b3aaf205cb0` and was also
empty, inactive and unowned. The shared reservation was released. Authenticated
hostname/TLS WTP `HELLO`, `CAPS`, `STATUS`, `GET_CLOCK` and `PING` passed on the
new boot without a control mutation. The private record is under
`repair-2eaa999-deployment/corrected-deployment`; the sanitized record is
[`phase11-6-clock-refinement-deployment-attempt2.json`](phase11-6-clock-refinement-deployment-attempt2.json).

The remaining affected-candidate gate is the one authorized 45.000001-second
160 m QRSS corrective attempt. It must observe a newly accepted,
lower-uncertainty clock sample while the same job remains Armed, complete
without `MISSED_START`, retain the Phase 11.5 resource gates and pass independent
IQ analysis. If that sample is not observed, the campaign stops without an
automatic retry.
