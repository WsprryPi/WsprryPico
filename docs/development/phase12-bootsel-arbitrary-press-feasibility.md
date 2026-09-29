# P12 arbitrary BOOTSEL press feasibility gate

Later decision: the operator selected a separate GP14 input (Pico 2 W physical
pin 19) with hold-time actions. The [separate GP14 diagnostic](phase12-gp14-button-diagnostic.md)
follows this gate. This record remains the reason the onboard BOOTSEL switch is
not used for arbitrary runtime capture; its release-only policy discussion and
unselected-GPIO candidate describe the earlier decision, not the current GP14
contract.

Status: **BLOCKED BEFORE DIAGNOSTIC LINK; NO TARGET TEST AUTHORIZED**
(2026-09-29). This is a source and hardware-interface assessment for Pico 2 W /
RP2350. It neither implements the selected button actions nor closes P12.7,
P12.11 or Phase 12.

## Decision

Do not build an arbitrary-press BOOTSEL diagnostic for the present flash/XIP
topology. A separate button on an ordinary GPIO, electrically independent of
the flash chip-select line, is required to test the selected always-available
gesture while both cores may use flash. A radically different RAM-resident
system would need a separate design and proof before reconsidering BOOTSEL;
merely moving the sampler or its interrupt handler to SRAM is insufficient.

The release-time policy in `src/provisioning/button_control.hpp` is unchanged:
debounced presses of at least 20 ms and under 1,000 ms request shutdown only;
1,000 through 9,000 ms inclusive do nothing; over 9,000 ms requests shutdown
and then setup AP after confirmed shutdown. No action is requested while held.
The production button input remains disconnected. This gate concerns capture
of an arbitrary physical gesture, not the portable classification.

## Exact obstruction

The Pico 2 W BOOTSEL switch pulls the external flash chip-select signal low.
The RP2350 can fetch instructions and data from that flash through XIP, on
either core; a cache miss drives a QSPI transaction. The button is asynchronous
to both cores and to the QSPI controller. Thus this sequence is possible:

1. Either core starts an XIP miss or a flash data read with CS active.
2. The operator presses BOOTSEL at that instant, changing the electrical CS
   state during the transaction.
3. A polling loop, GPIO interrupt or cross-core lockout observes the press
   only **after** the edge. A core blocked in an XIP fetch may not reach the
   observation or lockout point at all.

There is no software ordering between the physical edge and an already issued
flash access. An SRAM-resident observer can avoid *its own* subsequent flash
reads, but it cannot make the other core's in-flight fetch safe or guarantee
the fetched instruction/data. An interrupt handler in SRAM also has entry
latency, and an interrupt vector, handler dependency, literal, stack fault path
or higher-priority interrupt may still use XIP. Disabling interrupts while
polling protects only a deliberately entered safe zone. The SDK's
`flash_safe_execute()` coordinates both cores and disables interrupts
**before** it invokes its callback; it does not preempt a spontaneous button
edge. Keeping both cores permanently in a flash-safe zone would preclude the
requested representative flash activity at arbitrary press times and would
pause ordinary USB/network service. Alternating safe zones with flash-reading
intervals leaves exactly the unprotected edge above.

The existing `capture_runtime_bootsel_gesture()` is a prompted, blocking
whole-gesture window. It keeps both cores away from flash until a stable
release, but its safety starts only after a command has entered the window.
The previous background sampler returned to XIP while BOOTSEL could still be
held; an approximately 11-second physical hold ended with lost application
service and ROM bootloader enumeration. That record does not establish the
precise fault instruction or reset cause. Neither path meets the present
arbitrary-press requirement. A tiny single-core SRAM demonstration would
leave the other core and the edge during flash access unexamined.

The watchdog cannot repair the initial XIP collision. A stuck hold must keep
both cores out of flash for its entire duration. Stopping watchdog feeds can
reset into ROM while BOOTSEL is still down; that is loss of the application,
not press capture. Feeding forever leaves a hung service without a bounded
recovery. The previous prompted callback's bounded watchdog behavior is
appropriate only to its already-entered window. After an XIP fault, duration,
release classification and continuity cannot be guaranteed or necessarily
persisted for later inspection. Writing an evidence journal to flash while
CS is held would add another unsafe access. A watchdog scratch or SRAM record
could preserve some fault metadata only if its recording code actually runs;
it cannot prove that every failed press was observed.

These are source-level reasoning and the prior bounded target observations,
not a claim that every arbitrary BOOTSEL press must fail. The missing guarantee
is enough to reject a diagnostic whose stated purpose is to establish safe
arbitrary capture while both cores exercise flash.

## Rejected candidate and next design

The smallest tempting image would run a fast SRAM BOOTSEL poller, a flash-read
loop on each core, and switch both cores into SRAM for the held interval. It
can record a press only if the poller and lockout win a race against both
flash accesses. Faster polling, a GPIO IRQ, cache warming, a PIO edge signal,
or `flash_safe_execute()` after the edge changes the probability, not the
ordering. It is therefore intentionally **not linked** and has no UF2 or
image SHA-256. The older opt-in `BOOTSEL WINDOW` image remains a prompted
diagnostic; it must not be relabeled as the requested image.

A future, separate-GPIO, RF-inhibited diagnostic should have one ordinary
input dedicated to the button, with a defined inactive bias, debounced edge
timestamps, a release-only policy adapter, and no settings writer, RF engine
or AP adapter. Both cores can run independent flash code/data checksum loops
throughout unprompted gestures. A bounded RAM event ring can record press
start/end, duration, classification, each core's monotonic progress and
checksum before/during/after, watchdog/reset reason and fault registers.
After reboot, expose retained evidence through a read-only path and make
loss/overflow explicit. Source/link checks must establish the no-RF/no-write
topology, core stacks and fault-handler placement. The exact GPIO, electrical
connection, reset evidence retention and firmware design are **not selected**
here; they require review before any image or physical test.

## Bounded later physical procedure, not authorized by this record

Only after a separately reviewed image and exact-device authorization:

1. Record board identity, wiring, ELF/UF2 hash, clock, both-core workload,
   flash checksum locations, watchdog settings, reset-state baseline, RF
   inhibition and unchanged settings. Start the workload without a USB prompt
   or capture window; use USB only for later readback.
2. At unpredictable phases of both cores' flash loops, perform separate
   released short (<1 s), middle (1–9 s inclusive), and long (>9 s) holds.
   Include the 1 s and 9 s boundaries. Compare release classification with
   independent timing and verify no action was emitted before release.
3. Repeat with a stuck hold longer than the expected watchdog interval.
   The independent-GPIO design should keep feeding while the input is held;
   a held button by itself must not force a reset. Separately inject a
   reviewed, opt-in missed-feed fault with no button press, verify watchdog
   reset-cause readback and automatic recovery, then repeat that fault with
   the button held and verify that boot and capture resume. Any ROM entry,
   lost service, unrecorded press, checksum mismatch or unexplained reset is
   a failed row.
4. After each release, inspect core progress/checksums, fault record, reset
   reason, read-only event history and service continuity. Verify settings
   and evidence are preserved. Repeat around flash activity on **both** cores;
   a single-core success is not acceptance.

This future diagnostic would test capture and classification only. Actual
scheduler/`JobService`/RF shutdown and integrated SoftAP admission remain
separate source, RF-inhibited target and conducted acceptance gates.

## Source references

- [Pico 2 W schematic](https://datasheets.raspberrypi.com/picow/pico-2-w-schematic.pdf), BOOTSEL switch and QSPI_SS wiring.
- [Pico 2 W datasheet](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf), BOOTSEL/ROM boot and external XIP flash.
- [RP2350 datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf), section 4.4, XIP cache miss and QSPI transaction.
- [Raspberry Pi BOOTSEL example](https://github.com/raspberrypi/pico-examples/blob/master/picoboard/button/button.c), SRAM/IRQ precautions and concurrent-flash warning.
- [Pico SDK flash-safe API](https://github.com/raspberrypi/pico-sdk/blob/master/src/rp2_common/pico_flash/include/pico/flash.h), prearranged multicore lockout contract.
- [Long-hold incident](phase12-safari-open-setup-review.md), [prompted window review](phase12-8-bootsel-window-review.md), [physical window record](phase12-8-bootsel-window-target.md), and [button policy review](phase12-bootsel-button-review.md).

## Validation record

The 2026-09-29 source review tried to defeat the obstruction with an SRAM
poller, an SRAM interrupt, SDK core lockout and a wholly RAM-executed monitor.
Each leaves either an in-flight XIP transaction at the asynchronous button
edge or removes the required arbitrary-time flash activity. A watchdog reset
during a hold also risks ROM BOOTSEL and cannot guarantee a complete event
record. The first draft of the later procedure did not explicitly require a
watchdog fault injection; that omission was repaired above. Reassessment found
no source-supported architecture for the requested image and no executable
diagnostic source to format, link or flash. The block is an acceptance finding,
not a successful BOOTSEL diagnostic.

Hardware-free checks on the unchanged production path:

```sh
bash scripts/check_host.sh
PICO_SDK_PATH=/private/tmp/wsprrypico-sdk-profile-079c6f3 bash scripts/build_pico.sh
python3 scripts/check_bootsel_topology.py build/pico2-w-local/firmware/WsprryPico.elf
python3 scripts/check_standalone_image.py build/pico2-w-local/firmware/WsprryPico.elf
shasum -a 256 build/pico2-w-local/firmware/WsprryPico.elf build/pico2-w-local/firmware/WsprryPico.uf2
```

`check_host.sh` passed 89/89 CTest cases. The standard RF-inhibited
cross-build linked with the local pinned SDK 2.3.1 commit
`079c6f39023649b154152db30f1d781e884879bc`, Arm GNU 15.3.1,
`PICO_BOARD=pico2_w`, and
`WSPRRY_PICO_BOOTSEL_WINDOW_DIAGNOSTIC=OFF`. The explicit linked checks passed:
no runtime sampler or core-1 reader linked; the 32 KiB primary stack and
reserved flash journals do not overlap the image. This baseline build used
source revision `16b72d97111e0d61be4959cf958a16abaa245f75`; it is **not**
the requested arbitrary-press diagnostic. Its ELF SHA-256 is
`a83d20e973a1654b44b05dcd7d47c3bd54bba576ad1ba83a8bcd1066f3d7fcb8`;
its UF2 SHA-256 is
`47d5d80c6afe6d5f8c553856db9380385ce8de4d9a91374d68670cca6ee1d782`.
`clang-format --dry-run --Werror` passed on the inspected button policy and
BOOTSEL callback sources; no C/C++ source was changed. The same check on the
unchanged `src/rf/pico/worker.cpp` reports a pre-existing indentation
violation at line 69, outside this documentation slice. Markdown local links,
trailing whitespace and `git diff --cached --check` passed after the procedure
repair.
No arbitrary-press diagnostic image exists, so there is no diagnostic hash or
diagnostic linked-image/SRAM pass. No physical test or settings action occurred.
