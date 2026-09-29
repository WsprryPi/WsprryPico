# GP14 runtime button integration: execution brief

Status: source execution recorded in the linked
[review](phase12-gp14-runtime-review.md); integrated RF/target gates remain
open. This brief authorizes no physical action.

Work on `devel` from the verified clean handoff. Read `AGENTS.md`, `README.md`,
`CONTRACT.md`, `docs/architecture.md`, the selected
[GP14 behavior](phase12-safari-open-setup-revision.md), the
[diagnostic design](phase12-gp14-button-diagnostic.md), and its
[physical record](phase12-gp14-button-flash-0a9d89.md). Preserve settings,
evidence and unrelated work. Keep the standalone diagnostic separate.

## Selected behavior

Use GP14 (Pico 2 W physical pin 19), pulled high internally and connected to
ground by a normally open switch. A stable 10 ms edge is required. Ignore a
low level present at boot until release. On a recognized release under 400 ms,
request a normal reset after safe output shutdown. A release from 400 ms to
under 900 ms requests transmission stop. A held press requests stop at 900 ms
and manual setup SoftAP at 9 seconds. Neither held action waits for release.
Emit each action once per gesture. A low level held past 10 seconds, including
past any manual AP lease, must not repeat actions or withdraw the AP. No action
erases settings, watermarks, ownership records or journals.

## Integration and failure contract

1. Capture GP14 independently of USB, network processing and core-0 flash
   write blackouts. Core 1 remains the RF worker. Measure and bound observation
   and dispatch gaps. If a buffered edge is lost, the clock rolls backward or
   capture resources fail, inhibit new RF output and report a fault. Do not
   treat a watcher task or timer interrupt alone as arbitrary-press proof:
   `flash_safe_execute` masks interrupts and the inhibited storage writers
   also mask them. Account for buffer exhaustion and long uptime.
2. Keep the portable debounce/classifier separate from Pico hardware. The
   hardware adapter must reconstruct ordered sample times after a blocked
   foreground interval, preserving short taps that occur wholly within it.
   Do not execute RF, reset, flash or CYW43 operations in an interrupt or PIO
   callback. Keep the BOOTSEL sampler disconnected.
3. On stop, latch a service-wide output inhibit and suspend autonomous
   scheduling in the same core-0 dispatch, covering USB, TCP, BLE, browser
   and autonomous requests.
   Abort any armed/running job regardless of owner, disable the physical
   engine, and verify inactive output and non-running service state. Do not
   interpret `Scheduler::command("STOP")` alone as completion; it can report
   `external_owner`. A stop failure stays inhibited and blocks AP admission.
4. At 9 seconds, request the existing manual SoftAP only after verified
   shutdown. Keep its lease retained throughout the same held gesture, then
   give the normal post-release lease. Do not restart it on every poll. Surface
   AP startup failure separately from successful shutdown. A short-reset
   request must also quiesce output before a normal reboot, without entering
   ROM bootloader or changing persistent data.
5. Make the production connection an explicit opt-in build variant until
   target timing and integrated behavior are accepted. Keep the default
   RF-inhibited image and the diagnostic image unchanged. Do not claim live
   RF shutdown or phone/SoftAP acceptance from source and host checks.

## Checks and review

Add deterministic host tests for exact 400/900/9000 ms boundaries, bounce,
boot-held input, indefinite hold, replay of a tap during a simulated flash
blackout, buffer overrun, clock fault, external WTP owner, output-disable
failure, no new RF admission after stop, reset quiescence and manual AP hold.
Test status/read-only service access while inhibited. Run the repository host
suite, formatting, linked-image checks and pinned Pico 2 W cross-build using
existing local dependencies only. Inspect SRAM/PIO/DMA resource use in both
the inhibited and opt-in RF targets. Stop before linking an image if the
capture or output interlock is not defensible; record the precise obstruction.

Perform an adversarial review of timing, producer/consumer races, flash-write
blackouts, multicore ownership, replay, watchdog/reset reason, AP lease and
failed output disable. Fix actionable findings, rerun affected checks and
reassess. Record exact commands, image hashes, remaining gates and the
repository state. Commit and push on `devel` only after source review.

No flashing, USB control, GPIO action or RF output is authorized here. Later
target work needs exact device/image/action authorization and separate
RF-inhibited integrated AP and conducted RF shutdown acceptance. P12.7,
P12.11 and Phase 12 remain open.
