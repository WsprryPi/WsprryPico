# Phase 12 BOOTSEL button source attempt and adversarial review

Status: **DISCONNECTED SOURCE CANDIDATE VALIDATED; PRODUCTION BUTTON PATH
BLOCKED; P12.7 AND PHASE 12 OPEN** (2026-09-29).

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
| A short press could be restarted before a ten-second hold was distinguished, or a boundary could classify both actions. | The policy decides only on release. Host cases cover 9,999 ms, 10,000 ms, bounce, failed shutdown and clock rollback. |

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
