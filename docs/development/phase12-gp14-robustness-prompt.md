# GP14 unattended robustness execution brief

## Objective and authority

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`, starting from verified
clean `e39d1f4aab807e818b81d2ef803e74e5688111e5`. Read AGENTS.md, README.md,
CONTRACT.md, architecture and the GP14 runtime evidence first. Preserve all
settings, private evidence and previously reviewed firmware. Implement and
review source, build with existing pinned dependencies, commit and push.
This brief does not authorize flashing, USB control, GPIO changes or RF.

Remove the finite DMA lifetime and provide bounded automated tests that need
neither 25 days of waiting nor repeated hand-timed jumper contacts. Keep the
standard image's button opt-in and BOOTSEL disconnected. Keep P12.7, P12.11
and Phase 12 open. Do not reopen the physical half-second row or repeat B's
accepted tests on A solely for duplication.

## Implementation

1. Replace finite RP2350 DMA capture with hardware self-retriggering blocks.
   Prove progress accounting across reloads, including zero/count reload,
   missed-observation ambiguity, elapsed-clock faults, counter overflow and
   ring overwrite. Use 64-bit lifetime accounting. CPU interrupts must not
   renew the DMA during flash blackout. Retain sticky failure and output
   inhibition; expose completed blocks in runtime telemetry.
2. Extend deterministic host checks for repeated reloads, more than 25 days
   of logical operation, thresholds, boot-held input, delayed dispatch,
   stop failure, stuck holds beyond the AP lease and release/lease expiry.
   Exercise the actual portable policy/coordinator. Synthetic time does not
   qualify real elapsed-time networking behavior.
3. Add a separate, opt-in RF-inhibited robustness target, using the same
   capture adapter with both cores executing an XIP workload. Give it bounded
   USB commands for automatic PIO sample-override gestures, boot-held recovery,
   DMA stop, PIO no-progress, backlog overrun, normal reset, watchdog stall,
   fault recovery and a real scratch-sector erase/program/restore cycle.
   Sample override must leave GP14 an input and never drive any RF pin. Its
   evidence is synthetic capture evidence, not a physical pad/contact test.
4. Reserve a diagnostic-only scratch sector below every settings partition.
   Exclude it from ELF/UF2 application payload. Bound every flash write to
   that sector, preserve/restore its bytes, hash the reserved settings region
   before and after, and report restoration/readback failures. A reset during
   the operation may leave scratch altered; no settings address is writable.
   Use the SDK's multicore flash-safe lockout; audit linked SRAM placement.
5. Add a host runner with an inert default, exact USB serial/revision/image
   binding, explicit selected actions, private raw evidence, deadlines and
   reset reconnection. It must neither flash nor download dependencies. A
   reviewed image and exact physical actions require separate authorization.
6. Recheck the separate RF target's dependency obstruction. Repair narrowly
   if a coherent source-only fix is available; otherwise record the exact
   remaining build/safety dependency. Do not enable GP14 in the RF target or
   infer RF cutoff latency from sampling frequency or simulated shutdown.

## Verification and review

Run the documented deterministic host suite, format checks, Python checks,
pinned Pico 2 W cross-builds for default, opt-in runtime and robustness
targets, and linked flash/SRAM/RF-exclusion checks. Use only local SDK,
toolchain and picotool inputs. Record exact commands and hashes for the
reviewed images. Keep generated artifacts and credentials ignored.

Perform an adversarial review of counter reload races, flash access on both
cores, IRQ masking, watchdog recovery, buffer overflow, test-hook isolation,
settings preservation, runner identity checks and claims. Fix actionable
findings, rerun affected checks, then reassess. Record the findings and limits.

Provide a finite future device campaign that can run without manual presses:
short/middle/long/stuck synthetic holds, boot-held suppression, reloads under
both-core XIP activity, flash overlap, fault detection, watchdog reset and
post-reset continuity. Keep actual pad timing, ten-minute live SoftAP lease,
phone acceptance and active/armed RF shutdown as distinct physical gates.
Commit and push reviewed source on `devel`; verify remote parity and report
the actual checkout state and outstanding blockers.
