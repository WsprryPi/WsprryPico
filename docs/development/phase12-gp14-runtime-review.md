# GP14 runtime source integration and adversarial review

Status: **OPT-IN RF-INHIBITED SOURCE CANDIDATE; NO PHYSICAL OR REAL-RF ACCEPTANCE**
(2026-09-29). This record executes the
[integration brief](phase12-gp14-runtime-integration-prompt.md) within the
safe linked-image boundary. The default `WsprryPico` image and the separate
GP14 diagnostic remain distinct; the new runtime path is selected only with
`WSPRRY_PICO_GP14_RUNTIME_BUTTON=ON`.

## Source design

`src/provisioning/pico/gp14_sampler.pio` samples GP14 once per millisecond.
Eight samples are packed into a word and moved by one DMA channel into an
8 KiB SRAM ring. The 2,048-word ring covers 16.384 seconds of samples;
the joined PIO receive FIFO adds up to eight pending words. Core 0 consumes
ordered samples through `ButtonSampleStream` and the existing 10 ms debounced
`ButtonDiagnostic` policy. `ButtonRuntime` sequences the resulting requests
through the Pico adapter on core 0. A complete short contact during a flash-write
blackout can therefore be replayed with its sampled duration. Ring overrun,
DMA stop, PIO receive stall or lack of producer progress marks capture faulty
and latches an output inhibit. The finite DMA count reaches its fail-closed
limit after about 397 days at the nominal rate; long-uptime renewal remains
for a later release-quality implementation.

The core-0 runtime dispatcher is ahead of `Scheduler::poll()` and transport
service. On the first stop or reset request it latches
`JobService::local_inhibit_output()` and suspends autonomous scheduling in the
same dispatch, aborts the current job regardless
of owner, disables the engine and verifies output inactivity. The interlock
rejects new `CLAIM`, `RENEW`, `LOAD` and `ARM` before replay lookup, while
read-only status remains available. A failed physical disable stops feeding
the watchdog and enters the existing inhibited recovery boot. A failed or
uncertain shutdown cannot admit manual SoftAP. A valid under-400 ms release
uses the existing normal watchdog reboot path after quiescence, retaining
settings and recording a bounded prior-reset marker and duration in scratch
registers. No BOOTSEL or flash writer path is connected to the button.

At 9 seconds the dispatcher requests the existing manual SoftAP lease only
after shutdown confirmation. The lease remains active while that gesture is
held; on release the existing 10-minute period starts. This prevents a
jumper held past 10 minutes from withdrawing the AP. The normal AP loop still
selects blank, pre-clock or provisioned surfaces and may report startup
failure independently of the button request. INFO adds read-only GP14 fault,
hold, action count, inhibit, shutdown and retained-reset fields.

## Deterministic and linked checks

All commands below were run from the repository root with existing local
dependencies. `scripts/xcode_env.sh` was sourced in the shell that builds
Pico helper tools; the first build attempt omitted that environment and its
host `pioasm`/picotool link failed against the Command Line Tools macOS SDK.
No SDK or tool was downloaded for this task.

```sh
bash scripts/check_host.sh
clang-format --dry-run --Werror src/provisioning/button_runtime.hpp \
  src/provisioning/button_sample_stream.hpp \
  src/provisioning/pico/gp14_capture.hpp \
  src/provisioning/pico/gp14_capture.cpp \
  src/provisioning/field_runtime.hpp src/provisioning/field_runtime.cpp \
  src/standalone/pico/main.cpp src/wtp/job_service.hpp src/wtp/job_service.cpp \
  tests/button_diagnostic_tests.cpp tests/core_tests.cpp tests/field_access_tests.cpp
git diff --check
PICO_SDK_PATH=/private/tmp/wsprrypico-sdk-profile-079c6f3 bash scripts/build_pico.sh
source scripts/xcode_env.sh
PICO_SDK_PATH=/private/tmp/wsprrypico-sdk-profile-079c6f3 \
  cmake -S . -B build/pico2-w-gp14-runtime -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DWSPRRY_PICO_BUILD_FIRMWARE=ON -DWSPRRY_PICO_BUILD_TESTS=OFF \
  -DWSPRRY_PICO_GP14_RUNTIME_BUTTON=ON -DPICO_BOARD=pico2_w \
  -DPICOTOOL_FETCH_FROM_GIT_PATH=/Users/lbussy/GitHub/WsprryPico/build/pico2-w/_deps
cmake --build build/pico2-w-gp14-runtime --target WsprryPico -j 4
python3 scripts/check_standalone_image.py \
  build/pico2-w-gp14-runtime/firmware/WsprryPico.elf
python3 scripts/check_stack_guards.py \
  build/pico2-w-gp14-runtime/firmware/WsprryPico.elf
python3 scripts/check_bootsel_topology.py \
  build/pico2-w-gp14-runtime/firmware/WsprryPico.elf
```

The host suite passed 90/90. Focused tests cover packed-sample replay of a
104 ms tap delivered after a simulated 200 ms foreground blackout, held
stop/AP once through 11 seconds, ring accounting, service-wide inhibit with
an external WTP owner, pre-replay rejection of a prior ARM, output-disable
failure and status access, reset and AP gating on confirmed shutdown, and a
manual AP retained past 30 minutes then
released into a 10-minute lease. The pinned default image and the opt-in
RF-inhibited image cross-built. Linked flash reservation, stack guard and
BOOTSEL topology checks passed on the opt-in image. The default image has no
GP14 sampler/capture symbols; the opt-in image has them.

| Image | ELF SHA-256 | UF2 SHA-256 |
| --- | --- | --- |
| Opt-in RF-inhibited source candidate | To be recorded after a clean source commit | To be recorded after a clean source commit |

## Adversarial review and repair

The first pass found that `Scheduler::command("STOP")` can fail with an
external owner and cannot prevent a later transport from launching RF. The
shared `JobService` now latches the output inhibit before replay and verifies
physical disable. A rejected disable could otherwise leave output active
while the ordinary watchdog feed continued; that path now yields to watchdog
recovery. The existing 10-minute manual AP lease could expire during a
forgotten jumper hold; it now remains retained until release. The first new
host test used `g` in a protocol identifier, which is outside its hexadecimal
contract; that test was corrected and the full suite rerun.

The second source pass checked PIO/DMA producer accounting, first-sample boot
arming, debounced sample ordering, flash-write blackout replay, one-time
thresholds, delayed AP admission, reset scratch semantics and default-image
separation. Formatting, host suite, pinned/default and opt-in builds and
linked-image checks were rerun after the repairs. No remaining source finding
was promoted into physical timing or RF acceptance.

## Remaining gates and bounded physical procedure

The opt-in image has the dry-run engine. It cannot establish actual RF stop
latency, RF-core coordination or a working phone SoftAP. The existing
`WsprryPico-StandaloneRF` target currently fails to compile the shared main
(`cmake --build build/pico2-w-gp14-runtime --target WsprryPico-StandaloneRF -j 4`)
because it lacks `btstack.h` and the consumer field-service sources linked
only into the inhibited target. Adding GP14 capture to that incomplete RF
image would not form a defensible integrated RF/AP candidate, so no RF image
was linked or authorized here. The PIO/DMA capture topology and the maximum
foreground dispatch delay still need target measurement. PIO sampling itself
does not force RF off at the exact 900 ms edge while core 0 is busy; that
requires a separately reviewed RF-core safety path and a measured latency
bound before the selected immediate-stop behavior can be accepted.

For a later exact-device, exact-image authorization, first inspect the GP14
pin-19 to ground wiring, RF isolation, device identity and preserved settings.
Use read-only INFO to record idle capture samples and faults, then make
unprompted short, 2–3 second, 9+ second and stuck holds at arbitrary times.
Confirm one event per gesture, no boot-held loop, AP availability during a
held jumper and post-release continuity. Separately authorize a controlled
flash-write overlap to verify PIO/DMA survival and exact duration; preserve
the original settings and journal evidence. Only after the inhibited path is
accepted should a newly reviewed, conducted RF image test active and armed
job stop latency, watchdog recovery and AP admission after confirmed output
shutdown. No physical action was performed for this source task. P12.7,
P12.11 and Phase 12 remain open.
