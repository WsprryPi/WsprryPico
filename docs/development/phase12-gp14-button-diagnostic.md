# P12 GP14 arbitrary-press diagnostic

Status: **SOURCE DIAGNOSTIC ONLY; NO DEVICE TEST OR PRODUCTION BUTTON PATH**
(2026-09-29). This opt-in Pico 2 W / RP2350 image evaluates whether an ordinary
GPIO input can be observed through unprompted presses while both cores keep
executing and reading external flash. It has no RF engine, Wi-Fi stack, AP,
settings writer or flash journal. The production BOOTSEL path remains
disconnected. This record does not close P12.7, P12.11 or Phase 12.

## Selected input and timing

The selected hardware input is GP14, Pico 2 W physical pin 19, with a normally
open switch to ground (physical pin 18 is adjacent ground). The image enables
the internal pull-up; low means pressed. [Pico 2 W pinout](https://datasheets.raspberrypi.com/picow/pico-2-w-pinout.pdf)
and [schematic](https://datasheets.raspberrypi.com/picow/pico-2-w-schematic.pdf)
identify the connection. Actual wiring and voltage levels require inspection
on the authorized device before any physical test. The prior BOOTSEL switch
grounds external flash chip select and is rejected for this test by the
[feasibility gate](phase12-bootsel-arbitrary-press-feasibility.md).

The portable diagnostic accepts an edge only after a 10 ms stable level.
Recognized releases before 400 ms report `would_reset`; releases from 400 to
under 900 ms report `would_stop` on release. At 900 ms of continuous low, it
reports `would_stop` once without waiting for release.
At 9,000 ms of the same hold, it reports `would_setup_ap` once. A jumper left
on GP14 for 30 seconds or longer produces no repeated request; a debounced
release rearms the next gesture. A low input present at boot is ignored until
release, so watchdog recovery with a fitted jumper does not restart the
gesture or loop on a reset request. The reported AP request is independent of
subsequent pin level. A production adapter must wait for confirmed shutdown
before admitting AP and must keep AP available during an indefinite hold.

The diagnostic reports *would* actions. It never resets on a short press,
stops real RF or starts SoftAP. Those paths require separate source, physical
and conducted acceptance. In particular this image cannot prove that an
actual AP stays usable with a jumper fitted.

## Image design and evidence

`src/provisioning/pico/gp14_button_diagnostic.cpp` starts core 1 with a
dedicated 8 KiB stack and a stack guard. Each core continuously calls
`flash_probe_step()` from XIP and reads a 32 KiB const flash table, larger than
the RP2350 16 KiB XIP cache. Core 0 samples GP14 between batches of 256 reads;
core 1 never parks for the gesture. The image records a monotonically
increasing read count and digest for each core at each button event and in
periodic USB read-only reports. A button edge can arrive at any point in
either core's flash workload; there is no capture command or prepared window.
The max observed gap between core-0 samples is reported as
`max_poll_gap_us`. A large gap or stopped read count is a failed timing or
continuity row, even if a later classification looks right. Host timing tests
establish state-machine boundaries only; no source or build check establishes
target polling latency.

The 16-entry RAM event ring reports `press`, threshold requests, `release`
with measured duration and `post_release` after one second of continued work.
It prints only events not previously sent while USB CDC is connected, and
reports a count if earlier ring entries were overwritten. USB is an observer,
not a trigger; reporting has a 1 ms SDK write timeout and a 2 ms stdio lock
timeout, and USB reset commands are disabled. The event ring is volatile and
is lost on reboot. Watchdog
scratch registers retain the last press duration (milliseconds, saturated at
29 bits), action flags, last read counts, boot count, fault word and Cortex-M
HFSR across a watchdog reset. The fault word's high bit marks HardFault and
its remaining bits hold CFSR; other named values mark a stalled core, clock
fault or deliberate missed feed. These are a bounded last-event summary,
not a durable journal. A fault before handler installation may leave only the
watchdog reset reason. Power loss does not preserve them. A 4-second watchdog
is fed only while core 0 samples and core 1's read count advances. A stalled
core 1, clock rollback or HardFault stops feeding; the next boot reports the
watchdog reason and retained markers. A compiled opt-in injection mode stops
feeding once, 15 seconds after its first boot, to exercise recovery without a
USB command. It is off in the normal diagnostic image.

The linked-image script requires the XIP function, both core entry points and
large const table to be in flash, the HardFault handler in SRAM with no
outbound branch, multicore/watchdog calls, and no linked RF, Wi-Fi, flash
writer or BOOTSEL sampler symbols. The stack-guard linker check runs as well.
These checks are topology evidence, not physical timing evidence. The input is
ordinary GPIO and has no electrical tie to flash chip select, so both cores
can continue using XIP while it is held. No interrupt or core lockout is
needed for the input; the watchdog guards loss of progress rather than
attempting to make BOOTSEL safe.

## Source and build record

The target is separate from the standard image and excluded from the default
build. It uses the already local pinned Pico SDK 2.3.1 checkout and local
picotool source; no tool was downloaded. Exact configure and build commands:

```sh
bash scripts/check_host.sh
source scripts/xcode_env.sh
PICO_SDK_PATH=/private/tmp/wsprrypico-sdk-profile-079c6f3 \
  cmake -S . -B build/pico2-w-gp14 -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DWSPRRY_PICO_BUILD_FIRMWARE=ON -DWSPRRY_PICO_BUILD_TESTS=OFF \
  -DWSPRRY_PICO_GP14_BUTTON_DIAGNOSTIC=ON -DPICO_BOARD=pico2_w \
  -DPICOTOOL_FETCH_FROM_GIT_PATH=/Users/lbussy/GitHub/WsprryPico/build/pico2-w/_deps
cmake --build build/pico2-w-gp14 --target WsprryPico-GP14ButtonDiag -j 4
PICO_SDK_PATH=/private/tmp/wsprrypico-sdk-profile-079c6f3 bash scripts/build_pico.sh
python3 scripts/check_gp14_button_image.py \
  build/pico2-w-gp14/firmware/WsprryPico-GP14ButtonDiag.elf
python3 scripts/check_stack_guards.py \
  build/pico2-w-gp14/firmware/WsprryPico-GP14ButtonDiag.elf --physical
```

The opt-in watchdog-injection variant was built from the same clean source
commit in a separate directory:

```sh
source scripts/xcode_env.sh
PICO_SDK_PATH=/private/tmp/wsprrypico-sdk-profile-079c6f3 \
  cmake -S . -B build/pico2-w-gp14-inject -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DWSPRRY_PICO_BUILD_FIRMWARE=ON -DWSPRRY_PICO_BUILD_TESTS=OFF \
  -DWSPRRY_PICO_GP14_BUTTON_DIAGNOSTIC=ON \
  -DWSPRRY_PICO_GP14_DIAG_INJECT_WATCHDOG=ON -DPICO_BOARD=pico2_w \
  -DPICOTOOL_FETCH_FROM_GIT_PATH=/Users/lbussy/GitHub/WsprryPico/build/pico2-w/_deps
cmake --build build/pico2-w-gp14-inject --target WsprryPico-GP14ButtonDiag -j 4
```

Both images embed the clean source commit
`17851aee2db1d68e69c40d75ad2ee1d7f293c7e1` (program description
`17851aee2db1`). The final documentation-only commit does not change image
source; a later fresh configure from a different HEAD will change this
embedded revision and therefore its image hash.

| Artifact | SHA-256 |
| --- | --- |
| `build/pico2-w-gp14/firmware/WsprryPico-GP14ButtonDiag.elf` | `70d5b2a7274c6334034d246d57a804911a2a82cf2301cc397cf24189c91a15cd` |
| `build/pico2-w-gp14/firmware/WsprryPico-GP14ButtonDiag.uf2` | `d1a97341ddad1e9b526968db84f0f6ac2a236f1672f02e4310a620c916ef28a2` |
| `build/pico2-w-gp14-inject/firmware/WsprryPico-GP14ButtonDiag.elf` | `06b47a5d3d13f6e0e741cade3bece70a87ad8df71e83b6abe2756cd71311e5f1` |
| `build/pico2-w-gp14-inject/firmware/WsprryPico-GP14ButtonDiag.uf2` | `3ac2a641c831933de9773f664b8b4bb44562f68f5588ef2d6c4874a1601af6b9` |

`bash scripts/check_host.sh` passed 90/90 deterministic host groups. The
pinned `bash scripts/build_pico.sh` standard image cross-build passed. Both
GP14 image modes passed the post-link XIP/RF/storage topology and physical
stack-guard checks; the GP14 checker correctly rejected the standard image
as a negative case. `clang-format --dry-run --Werror` on changed C/C++ and
`git diff --check` passed. No board, USB, GPIO or RF action was performed.
The SDK/picotool sources were already local; no tool was downloaded. Physical
use of either hash needs exact-device and exact-action authorization.

## Adversarial source review

The review challenged the image as if a press arrived between either core's
XIP fetch and the next GPIO poll. GP14 is independent of flash chip select, so
an in-flight transaction remains electrically valid. The poll can still be
late; `max_poll_gap_us`, threshold event timestamps and external timing make
that observable in a physical test. USB logging uses short write/lock timeouts
and sends only new events, avoiding a growing per-loop print delay. A connected
but stalled host can still perturb polling; no sub-second target latency is
claimed from a cross-build.

The first link-check draft matched `main` as a substring of SDK and core-1
symbols. It now requires the exact `main` symbol and an actual call from each
core's disassembly to the XIP flash probe. Applying warnings-as-errors to the
whole diagnostic target also rejected an SDK C source; the CMake rule now
applies that policy to the owned diagnostic source only. The first reset
record omitted the action classification; the watchdog scratch summary now
retains duration and reset/stop/AP flags, with a distinct HardFault marker.
The injection build uses a different scratch magic so switching from the
normal image starts a fresh one-shot injection sequence. After these repairs,
both image modes, host tests, formatting, linked-image and stack checks are
rerun. Physical press timing, USB continuity, watchdog recovery and actual AP
behavior remain unverified until the bounded authorized procedure.

The operator then clarified the 400–<900 ms interval as stop-on-release and
confirmed that this step remains diagnostic only. The portable policy,
boundary tests and contract text were corrected before final rebuild; the
earlier clean image hashes were invalidated.

## Bounded later physical procedure (not authorized)

1. Select one exact Pico 2 W, inspect its GP14-to-ground wiring, isolate its RF
   output, record settings/evidence baseline, clock and power setup, and match
   the ELF/UF2 SHA-256 to the reviewed image. Obtain explicit authorization
   for that device, image and each flash, USB-read and button/jumper action.
2. Start the image with GP14 high and without a host command to arm capture.
   Observe both core read counts and digests advancing before any gesture.
   Apply presses at unpredictable phases of their flash loops. Use an external
   timer for at least five repetitions each of a recognized <400 ms tap,
   400–<900 ms stop-on-release press, 900 ms–<9 s stop hold and 9–12 s long hold.
   Include samples near both thresholds. For each, compare event time,
   duration and one-time classification with the external record.
3. Keep a jumper fitted for at least 30 seconds, including after the 9-second
   threshold. Check that `would_stop` and `would_setup_ap` each occur once,
   both flash read counts/digests keep changing, USB reports remain available,
   no reset occurs and the measured poll gap stays within a separately chosen
   acceptance bound. Release and verify the one-second `post_release` event,
   then make another press to prove rearming. This tests the requested
   indefinite-hold input behavior; it does not test a real SoftAP.
4. With a separately reviewed and hashed injection image, repeat the run once
   with GP14 high and once with a jumper already fitted at the injection time.
   Inspect the next boot's watchdog reason, fault marker, retained duration and
   action flags, both prior read counts, and subsequent read-count progress.
   Verify a held-at-boot input causes no reset or repeated AP request, then
   release and repeat a fresh gesture. Any unexpected ROM enumeration, lost
   service, unrecorded gesture, nonadvancing core, unexplained reset or
   overwritten evidence needed for the row fails that row.
5. Preserve the original settings and test evidence. Separately qualify actual
   scheduler/`JobService`/RF shutdown, shutdown confirmation, integrated AP
   startup and AP service under an indefinite hold. Conducted RF proof and
   P12.7/P12.11/Phase 12 closure remain later gates.
