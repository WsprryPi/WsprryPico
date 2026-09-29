# Phase 12 BOOTSEL button source attempt and adversarial review

Status: **DISCONNECTED SOURCE CANDIDATE VALIDATED; PRODUCTION BUTTON PATH
BLOCKED; P12.7 AND PHASE 12 OPEN** (2026-09-29).

The first assessment below records the original immediate-stop/restart request.
The operator then changed the decision to release-time classification. The
current policy and revised risk assessment are recorded at the end of this
document; the original attempt remains historical evidence.

The [execution brief](phase12-bootsel-button-execution-prompt.md) was run on
`devel` with no device action. The pre-existing four documentation edits
recording the operator-selected button behavior were preserved and included.

## Implemented slice

- `ButtonControl` is portable gesture policy. A debounced press requests
  shutdown immediately; release before ten seconds requests restart, and
  release after at least ten seconds requests a setup AP. It requires a
  complete shutdown indication covering scheduler, `JobService` and engine;
  missing confirmation or time rollback latches a fault. A bounce-length
  press cannot request restart or AP.
- `SoftApCoordinator` has a ten-minute manual setup lease. It refuses a new
  lease without shutdown confirmation, keeps the AP requested on a healthy
  station, retains an active setup reply after lease expiry, and then returns
  to the existing automatic policy. It does not write a profile or reset the
  device.
- No Pico BOOTSEL sampler calls this policy or lease. The standard linked
  image still has no runtime sampler or core-1 diagnostic reader. Consequently
  neither gesture is advertised as working firmware.

## First adversarial assessment and repairs

| Finding | Resolution |
| --- | --- |
| A manual AP lease could be requested with output state unknown if the API accepted only a timestamp. | Added a required `shutdown_complete` admission argument; a failed admission leaves the AP off. The host test exercises this path. |
| A mere inactive GPIO indication would not prove an armed autonomous schedule or `JobService` was stopped. | Renamed the policy input to `shutdown_complete` and documented that it includes scheduler, service and physical engine. Production integration must establish that composite state before using an action. |
| A short press could be restarted before a ten-second hold was distinguished, or a boundary could classify both actions. | The policy decides only on release. Host cases cover 9,999 ms, 10,000 ms, bounce, repeated press, held press, failed shutdown, clock rollback and wrap. |

## Second adversarial assessment: blocking integration facts

1. `capture_runtime_bootsel_gesture()` executes a RAM callback inside
   `flash_safe_execute()`. That excludes flash use on core 1 until release.
   The real `WorkerEngine::disable()` sends an RPC to core 1 and waits for its
   response. Calling that normal stop path from the callback would deadlock;
   waiting until release could leave PIO/DMA output active for the full hold.
   An independently reviewed SRAM-level emergency output cutoff and
   post-release reconciliation are required before this can be wired into an
   RF-capable image.
2. The old 100 ms background sample returned to XIP while BOOTSEL was held;
   its [physical long-hold incident](phase12-safari-open-setup-review.md)
   remains a failed gate. The prompted five-second
   [whole-gesture diagnostic](phase12-8-bootsel-window-target.md) does not
   prove an arbitrary unprompted ten-second hold, concurrent network service,
   or actual RF interruption. Reusing either unmodified is not accepted.
3. The manual AP lease is volatile. If a future adapter must reboot to obtain
   a safe AP state, it needs a bounded boot-continuation marker
   that survives only that restart. No such marker is implemented here.
4. Autonomous rearm prevention and exact settings preservation across a
   device restart cannot be tested in this disconnected source slice. The
   host test confirms the manual AP lease does not write the access record,
   but a production adapter must stop the scheduler and prove reboot behavior.

These are acceptance blockers, not closed findings. The reassessment finds no
additional actionable issue in the disconnected portable policy and AP lease.
The production sampler remains absent by design, so there is no new physical
button path to flash or test. This source attempt does **not** satisfy the
operator's requested gestures yet.

## Checks and next gate

After the API repairs: `clang-format --dry-run --Werror` on the four changed
C++ files and `git diff --check` passed. The focused `field_access_tests`
passed; `bash scripts/check_host.sh` passed 89/89 CTest cases. With the
locally retained Pico SDK 2.3.1, `PICO_SDK_PATH=/private/tmp/wsprrypico-sdk-profile-079c6f3
bash scripts/build_pico.sh` and a subsequent `cmake --build
build/pico2-w-local --target WsprryPico -j 4` completed. The linked-image
checker reported `BOOTSEL topology: no runtime sampler or core-1 reader
linked`. `python3 scripts/check_standalone_image.py
build/pico2-w-local/firmware/WsprryPico.elf` passed the primary-stack and
flash-reservation checks. The changed-document local-link check found zero
missing links. These are source, host and cross-build results only.

Next, design and inspect a RAM-only emergency cutoff that can force the RF
pin inactive while core 1 is parked, then build an opt-in RF-inhibited Pico 2 W
button diagnostic with a full-press safe zone. Before any feature claim,
separately authorize and record an exact device/image/button test; actual
transmission stop also needs a separately authorized conducted RF test. A
failure at either gate leaves the production gesture disabled and may require
a separate GPIO input.

## Release-time correction and reassessment

The selected action is now determined only on release: a valid hold shorter
than one second requests shutdown, a hold longer than nine seconds requests
shutdown followed by setup AP, and a hold from one through nine seconds does
nothing. The short action does not request a restart. `ButtonControl` now emits
no action while held. On an actionable release it requests shutdown, and only
after the caller confirms scheduler, `JobService` and engine shutdown can a
long hold request AP admission. A failed shutdown latches a fault. The AP lease
retains its separate shutdown guard.

This removes the need to call `WorkerEngine::disable()` while core 1 is parked
inside a whole-gesture BOOTSEL capture. The normal worker stop can run after
release, once flash and core 1 are restored. It does **not** prove that the
complete gesture is safe: the stock BOOTSEL button grounds flash CS, the
withdrawn sampler failed a physical long hold, and the existing prompted
capture pauses core 1 plus USB/network service for the whole window. During an
active RF job, that pause may leave PIO/DMA output without normal worker
service. An arbitrary unprompted press still lacks a safe production capture
path. The source candidate remains disconnected and P12.7/P12.11 remain open.

The next gate is a source-reviewed capture architecture that handles arbitrary
press timing, XIP on both cores, and RF output behavior during a hold without
resuming flash access while BOOTSEL is down. Follow it with an explicitly
authorized RF-inhibited target trial and separately authorized conducted RF
stop validation. A restart, if actually needed for AP entry, also needs a
bounded continuation marker. No physical action was performed in this
correction.

The revised policy passed `bash scripts/check_host.sh` (89/89), then a focused
`field_access_tests` rerun after an added long-hold shutdown-failure case.
`clang-format --dry-run --Werror` on the changed C++ files and
`git diff --check` passed. Cases now cover no action while held, releases at
999/1,000/9,000/9,001 ms, bounce, repeated presses, pending shutdown,
failed short/long shutdown and time rollback/wrap. The earlier cross-build
result is historical; this disconnected header is not linked into firmware.

The final adversarial reassessment found no policy path that opens AP before
confirmed shutdown. The production path remains blocked by arbitrary runtime
capture and hold-time flash/RF behavior, so these tests provide no button or
RF acceptance on a Pico 2 W.
