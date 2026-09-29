# GP14 runtime source integration and adversarial review

Status: **FIRST TARGET LOAD FAILED CLOSED; REPAIRED OPT-IN SOURCE AWAITS TARGET RETEST;
NO REAL-RF ACCEPTANCE**
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
through the Pico adapter on core 0. The stream is designed to replay a
complete short contact during a flash-write blackout with its sampled
duration; target capture remains unverified. Ring overrun,
DMA stop, PIO receive stall or lack of producer progress marks capture faulty
and latches an output inhibit. RP2350's 28-bit normal transfer count reaches
its fail-closed limit after about 24.85 days at the nominal rate; long-uptime
renewal remains for a later release-quality implementation.

The core-0 runtime dispatcher is ahead of `Scheduler::poll()` and transport
service. On the first stop or reset request it latches
`JobService::local_inhibit_output()` and suspends autonomous scheduling in the
same dispatch. It aborts the current job regardless of owner, disables the
engine and verifies output inactivity. The interlock
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
manual AP retained past 30 minutes then released into a 10-minute lease.
The pinned default image and the opt-in
RF-inhibited image cross-built. Linked flash reservation, stack guard and
BOOTSEL topology checks passed on the opt-in image. The default image has no
GP14 sampler/capture symbols; the opt-in image has them.

| Image | ELF SHA-256 | UF2 SHA-256 |
| --- | --- | --- |
| Opt-in RF-inhibited source candidate from `f6cb413bd469a5fb28443b0010a7ff4166de6093` | `75c90851c6c9788b7366042ed353d35d8a8f4a023947f8330ebfe995f5becd5d` | `9e733c791e791b00ec62cf1427874862c390d01fef432ec43116a80dec406268` |

The hashes above were measured after configuring and building with a clean
`f6cb413` worktree. The later documentation-only record commit changes Git
HEAD; a fresh configure from that later HEAD embeds a different revision and
will yield different image hashes. The linked opt-in ELF used 1,725,720
bytes of text and 136,652 bytes of BSS according to `arm-none-eabi-size`.

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
linked-image checks were rerun after the repairs. It also moved the PIO input
direction setup after state-machine initialization and placed the service-wide
output latch before scheduler cleanup. A clean `f6cb413` opt-in rebuild and
the linked-image checks passed after this reassessment. No remaining source
finding was promoted into physical timing or RF acceptance.

## First Candidate B target load and source repair

On 2026-09-29 the operator authorized the exact RF-inhibited runtime image on
Candidate B (`0a9d89`, chip/USB serial `CDDBF8767C506C07`, application device ID
`29f20b7342051ef947aa56cb9d4fab42`). The existing GP14 diagnostic first
reported `held=0` and increasing XIP read counts on both cores. It lacked a
compatible USB reset interface, so the operator manually entered ROM BOOTSEL
mode by power cycling B with BOOTSEL held. ROM reported RP2350 QFN60, ARM,
4,096 KiB flash and the expected chip ID. The other Pico remained enumerated.

Before load, `picotool save -a -v` saved and verified all 4,194,304 bytes of
B's flash. Private mode-600 copies on `wspr5` and in the ignored local
`build/gp14-runtime-b-20260929/` directory both have SHA-256
`136c58506802dbe7ced310040b0999283e95da79e8e6f829a2116ee42ddf53ca`.
The prior full-flash backup remains separate. The staged UF2 matched
`9e733c791e791b00ec62cf1427874862c390d01fef432ec43116a80dec406268`
on both hosts. The exact load command on `wspr5`
was:

```sh
/home/pi/phase11-4-e1/picotool-build/picotool load -v -x \
  /home/pi/gp14-runtime-b-20260929/runtime-gp14-rf-inhibited.uf2 \
  --ser CDDBF8767C506C07
```

Picotool verified the load with `OK` and rebooted the application. Its private
load log has SHA-256 `1cb3345250cf60d37170a434be62f81fc8b2bfa9a5bb285a5d120d87ca9845c9`.
Read-only INFO then matched the application ID and embedded source revision
`f6cb413bd469`, showed healthy access generation 1 and network-only profile
generation 1, but reported `gp14_capture_fault=true`, `gp14_samples=0`,
`gp14_output_inhibited=true`, `gp14_stop_verified=false`, and no button events.
Read-only STATUS reported the `inhibited-standalone-simulator` engine,
`state=empty`, `output_active=false`, and healthy storage. The private INFO
and STATUS responses have SHA-256 `2df25408e47454b1417012c9b79b7762c89e283c3467240dc8c1f43d06ab3b74`
and `edf4253e500ab44fe64bfccf0201c36e4d35144dda9772dbbff6be2a4dfab735`.
No GP14 contact, settings command, GP2 transmission or SoftAP acceptance test
was performed after the fault. B remains on this RF-inhibited, fail-closed
image pending an exact-image retest or authorized restoration.

Source inspection found that the sampler passed `0xffffffff` as RP2350's DMA
transfer count. In the pinned SDK, bits 31:28 select DMA mode and this value
selects endless mode, whose count never decreases. The no-progress fault after
100 ms is consistent with the observed zero samples; no live DMA register
trace was captured. The repair uses the SDK-encoded maximum 28-bit normal
count, derives completed words from that field, and rejects non-normal mode.
It adds a deterministic host regression for the initial, decrementing, zero
and endless-mode values. INFO now exposes a numeric fault code (0 none, 1
already started, 2 PIO claim, 3 DMA claim, 4 clock, 5 DMA count, 6 ring
overrun, 7 DMA stopped, 8 RX stall, 9 no progress, 10 sample stream). The
repaired source passed 90/90 host tests, then the focused button test after
the decoder move, formatting, the default and opt-in Pico 2 W cross-builds,
and linked flash/stack/BOOTSEL checks. This is a source repair;
the repaired PIO/DMA path has not yet run on the board.

The repair review checked normal/endless mode decoding against the pinned
RP2350 register definitions, SDK transfer-count encoding, decrement and
producer/consumer monotonicity, ring exhaustion, DMA completion, fault
reporting, default-image separation and preserved storage bounds. It found a
hardware-specific decoder in the portable gesture stream; that decoder was
moved to a Pico-specific header, and the focused host test, formatting,
opt-in cross-build and linked checks passed again. The count's 24.85-day
limit remains an explicit fail-closed diagnostic boundary. Target capture,
flash-write overlap, AP service and real-RF cutoff remain open.

The repaired candidate was configured from clean source commit
`c806890fc361d7ac64f525b84a79d0d0dfcdc275` using the opt-in CMake
command above, then built with
`cmake --build build/pico2-w-gp14-runtime --target WsprryPico -j 4`.
The ELF embeds revision `c806890fc361`; linked text is 1,725,920 bytes and
BSS is 136,652 bytes. Immutable copies in the ignored private local evidence
directory preserve this image even when a later documentation commit changes
Git HEAD. Its build log has SHA-256
`003891f96447493b56ef826c0fb086ee3eb093bbef9729aaf7ad6221cd9e35f6`.

| Repaired candidate artifact | SHA-256 |
| --- | --- |
| `build/gp14-runtime-b-20260929/repaired-c806890.elf` | `1a08c7034b31af0010d35aaf6848d1552dc2656b2ec25a069803afef763321d5` |
| `build/gp14-runtime-b-20260929/repaired-c806890.uf2` | `10e7ff2a99bce561eb0cbbea7cf95bff91f8f3c52b4c4077be504108cc910252` |

No load of this repaired image is authorized by the earlier exact-image
approval. Candidate B still runs the fail-closed `f6cb413` image. A new
authorization must identify B, this UF2 hash and the bounded retest action.

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
