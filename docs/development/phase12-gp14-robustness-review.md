# GP14 unattended robustness source and build review

Status: **source/host/build work complete** (2026-09-30); subsequent device
execution is recorded in the [bounded B campaign](phase12-gp14-robustness-target.md).
Executes the [comprehensive brief](phase12-gp14-robustness-prompt.md).
Started from clean `devel` at `e39d1f4aab807e818b81d2ef803e74e5688111e5`.
P12.7, P12.11 and Phase 12 remain open. The standard image still defaults
GP14 off; the RF image has no GP14 integration. BOOTSEL remains disconnected
from runtime button policy.

## Target-discovered telemetry repair

The authorized 2026-09-30 B campaign on clean `ae6fd97d71a6` passed SHORT,
MIDDLE, LONG, STUCK, FLASH, DMA_STOP, PIO_STOP, OVERRUN, RESET, WATCHDOG and
FAULT, then stopped during BOOT_HELD. A USB status record lost a middle
chunk; its remaining bytes were valid JSON, but omitted `reads0` and other
required fields. The runner stopped with `KeyError` and did not produce a
success record. The private `campaign-01` failure and raw bytes are retained.

The diagnostic had a 1 ms USB stdout timeout. The pinned SDK discards the
remaining output chunk when that timeout expires; the observed missing bytes
are consistent with this path. Its diagnostic-only timeout is now 100 ms,
allowing ordinary host scheduling gaps while retaining a finite no-progress
wait. Capture still runs in PIO/DMA; the watchdog still limits a wedged main
loop. The runner validates every required telemetry field and integer type
before using it, so valid-but-incomplete JSON fails with an explicit message.
Malformed records are never silently skipped or retried as passing evidence.
Host negative checks exercise deletion of every field and invalid value types.
The firmware and runner repairs require a new clean diagnostic build and a
fresh full target campaign; the first attempt is not full acceptance.

Repair review checked the SDK's 128-byte printf chunks and timeout discard
path, continued autonomous PIO/DMA capture, watchdog behavior, explicit
schema failure and preservation of the failed run. The timeout change is
confined to the diagnostic target; production USB behavior is unchanged.
All 91 host tests, the eight focused runner/link tests, Python compilation,
whitespace checks and the pinned diagnostic cross-build/SRAM/stack/reserved
flash/RF-exclusion gates passed. Reassessment found no further actionable
repair issue before the new clean-image attempt. No C/C++ source changed.

## Renewal and capture design

The [RP2350 datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf),
section 12.6.2.2.1, defines `TRIGGER_SELF`: the DMA reloads its transfer count
and continues from its current addresses. Capture now uses 4,096-word blocks,
renewing every **32.768 seconds** at the nominal 125 words/second. IRQ quiet
is enabled; renewal needs no CPU interrupt, callback, or flash execution.
It retains one channel, the original 1 kHz PIO sampler, and the 8 KiB SRAM
ring. `ENDLESS` mode is rejected because its count does not decrement.

`Rp2350DmaProgress` unwraps the block position into a 64-bit producer count.
Both count zero and the reloaded full count represent the boundary, counted
once. A maximum eight-second observation gap is shorter than both the block
period and ring lifetime; a longer gap is rejected before ambiguous modulo
arithmetic can hide a lost block. Backwards time, wrong mode, impossible
count movement and arithmetic overflow are sticky failures. A ten-word burst
allowance covers the joined eight-word FIFO, a partial word and in-flight DMA.
The consumer is also 64-bit. A second progress check after copying a word
rejects overwrite during the copy. SRAM ordering barriers surround the load.

A transient BUSY drop at reload is not interpreted as channel failure.
Disabled DMA or bus errors fail immediately; no progress for 100 ms, PIO RX
stall, excessive backlog or invalid sample data also fail closed. The existing
runtime capture-fault path inhibits output. `INFO.gp14_dma_blocks` exposes
renewals. No ISR performs policy, network or reset operations. Sampling during
XIP blackout does not guarantee immediate foreground dispatch: real RF still
needs an independent, measured shutdown path.

## Separate image and automatic stimulus

`WsprryPico-GP14Robustness` is an explicit `EXCLUDE_FROM_ALL` target enabled
by `WSPRRY_PICO_GP14_ROBUSTNESS=ON`. It links no network, RF engine, settings
adapter or runtime button dispatcher. Both cores traverse a 32 KiB XIP table
and call an XIP probe; telemetry records each core's progress. The diagnostic
reports policy requests, with actual resets confined to explicit reset/fault
commands. It does not raise an AP or qualify shutdown of real RF.

The test sampler substitutes `IN X,1 [31]` (X=1) and `IN NULL,1 [31]` for
`IN PINS,1 [31]`. Only the source of the bit changes. The same PIO cadence,
shift/autopush, FIFO, DMA, ring and portable policy remain in use. GP14 stays
an input; there is no output-enable or pad-level stimulus. This is **synthetic
PIO capture**, not evidence about pad routing, contact bounce or external
wiring. The test reports this distinction in every status record. Test hooks
are compiled out of the opt-in runtime and default images.

One bounded action requires `ARM <USB-serial> <clean-revision>` followed
within five seconds by `RUN <action>`. STATUS is read-only. No campaign starts
on ordinary boot. A BOOT_HELD command requests one normal reset; its retained
marker starts the next sampler low for 12 seconds, then releases it. The marker
is consumed before testing, avoiding a reset loop. Runtime policy actions are
not executed by this image. The physical under-400 ms reset result on B remains
in the [runtime evidence](phase12-gp14-runtime-review.md).

| Action | Bounded operation and required evidence |
| --- | --- |
| SHORT | 200 ms sample-low; one release and `would_reset` |
| MIDDLE | 600 ms sample-low; one stop on release; no reset/AP |
| LONG | 11 s sample-low; stop and AP requests observed while held; no repeats |
| STUCK | 610 s sample-low; the same two requests once, then post-release continuity |
| RELOAD | 70 s of both-core XIP work; at least two hardware reloads |
| FLASH | Scratch erase/program/verify/restore; a complete synthetic gesture while CPUs cannot service samples |
| DMA_STOP | Disable the channel; sticky fault code 7 |
| PIO_STOP | Stop PIO production; sticky no-progress fault code 9 |
| OVERRUN | Observe producer but suspend consuming for 17 s; sticky ring fault code 6 |
| RESET | Normal watchdog API reboot; new boot ID and matching breadcrumb |
| WATCHDOG | Withhold feeds; watchdog recovery, matching breadcrumb, no hardfault flag |
| FAULT | Undefined instruction; SRAM fault record and watchdog recovery |
| BOOT_HELD | One normal reboot, 12 s initial low, release with no policy action |

Fault cases include a separately armed RESET for recovery. After each action
and recovery the runner requires two seconds of both-core and sample progress,
unchanged settings checksum and no extra gesture or reboot. `RUN BOOTSEL`,
under the same ARM guard, is a maintenance-only return to ROM for restoring
a reviewed firmware image; it is deliberately absent from the campaign.
USB baud-rate and vendor reset entry points are disabled.

### Flash, IRQs and watchdog

The diagnostic linker ends application flash at `0x3f2000`, reserving exactly
one 4 KiB scratch sector `[0x3f2000,0x3f3000)`. All existing access, BTstack,
profile and standalone partitions begin at `0x3f3000` or above and retain their
original addresses. The ELF/UF2 checker excludes scratch and settings payload.
The only diagnostic writer has literal offset `0x3f2000` and length 4096;
USB cannot supply either. It copies original scratch bytes into SRAM, writes
and verifies a test pattern, then erases/restores/verifies the original bytes.
A reset or power loss before restoration can leave **scratch** changed. A
private full-flash backup is required before future device execution; the
runner does not silently restore a whole device or overwrite newer settings.

Both cores initialize the SDK flash-safe mechanism. `flash_safe_execute`
locks core 1 into its SRAM handler and masks core-0 interrupts. Its callback,
flash erase/program functions and hardfault handler are linked in SRAM.
The callback begins the synthetic low, waits 20 ms, erases/programs, waits
another 120 ms, then releases it before leaving the safe zone. PIO/DMA run
throughout; USB and both-core XIP work resume afterward. Thus the gesture can
be captured even though neither core polls or dispatches its edges during the
operation. Raw timings and classifications are retained for inspection.

The watchdog is eight seconds and is fed only while core 1 makes progress.
Intentional fault/withheld-feed cases do not touch flash. Scratch registers
0–3 hold diagnostic identity, action, sequence and fault status; SDK watchdog
markers remain separate. Status distinguishes normal reset from watchdog
recovery and includes a random per-boot ID. Every status checksums the settings
region up to (excluding) the E10 boot sector using FNV-1a. This is a continuity
check, not a cryptographic or byte-for-byte backup comparison.

## Deterministic checks and evidence limits

The host count test advances **4.4 billion words**, over 400 logical days,
through over a million hardware-block positions. It crosses the old 28-bit
DMA limit and 32-bit software word boundary. Other checks cover reload zero
and full-count observations, wrong mode, impossible count reset, stale
observations, backwards clocks, sticky faults and 64-bit backlog arithmetic.
Existing packed-sample tests retain the complete short tap during a simulated
blackout, debounce, all policy boundaries, boot-held suppression, stopped
output prerequisites and failure admission. The AP coordinator test now also
holds for 400 logical days, then verifies the unchanged ten-minute lease
expires exactly after release without modifying the access journal.

These tests use the production lease and portable policy with synthetic time.
They do not shorten the production lease and do not establish ten minutes of
real Wi-Fi/AP continuity. A 610-second **PIO** hold is likewise not a live AP
test. RF timing and actual/armed-job shutdown remain separate gates.

Runner tests reject wrong devices/images/clocks, missing releases, wrong
faults/resets, loss of either core's progress, settings changes and UF2 writes
in scratch/settings. Its default prints a plan without importing serial or
opening a device. Execution requires an exact USB serial, clean 12-digit
revision, local UF2 and matching SHA-256, explicit `--run`, and a fresh private
evidence directory. Device status binds serial/revision/variant; the local
UF2 hash must also be bound by the separate verified flash procedure. Status
alone cannot prove the installed flash's cryptographic hash.

## Exact local build/check commands

The old `/private/tmp/wsprrypico-sdk-profile-079c6f3` checkout had been cleared.
A fresh **local-only** clone in ignored `build/local-sdk-079c6f3` was reconstructed
from `/Users/lbussy/GitHub/pico-sdk` and its local submodule object stores.
SDK `079c6f39023649b154152db30f1d781e884879bc` (2.3.1), GCC 15.3.1,
all pinned SDK submodules including BTstack, and existing pinned picotool
`6f6458d792b93685a11423b244a585eaa99eafcf` were verified. The neighboring SDK
checkout was unchanged. No tool or dependency was downloaded.

```sh
bash scripts/check_host.sh
source scripts/xcode_env.sh
PICO_SDK_PATH="$PWD/build/local-sdk-079c6f3" cmake -S . \
  -B build/pico2-w-gp14-robustness -G Ninja \
  -DCMAKE_BUILD_TYPE=Release -DWSPRRY_PICO_BUILD_FIRMWARE=ON \
  -DWSPRRY_PICO_BUILD_TESTS=OFF -DPICO_BOARD=pico2_w \
  -DPICOTOOL_FETCH_FROM_GIT_PATH="$PWD/build/pico2-w/_deps" \
  -DFETCHCONTENT_FULLY_DISCONNECTED=ON \
  -DWSPRRY_PICO_GP14_RUNTIME_BUTTON=ON -DWSPRRY_PICO_GP14_ROBUSTNESS=ON
cmake --build build/pico2-w-gp14-robustness \
  --target WsprryPico WsprryPico-GP14Robustness -j 4
python3 scripts/check_standalone_image.py \
  build/pico2-w-gp14-robustness/firmware/WsprryPico.elf
python3 scripts/check_shutdown_image.py \
  build/pico2-w-gp14-robustness/firmware/WsprryPico.elf
python3 scripts/check_gp14_robustness_image.py \
  build/pico2-w-gp14-robustness/firmware/WsprryPico-GP14Robustness.elf
```

The default build uses the same configure command with
`-B build/pico2-w-gp14-default-check`, omitting both GP14 options; build target
`WsprryPico`, then run the standalone and shutdown checkers on that ELF.
Both build directories run their linked stack/heap/BOOTSEL gates automatically;
the separate diagnostic runs both-core stack and diagnostic link gates.
Formatting uses `clang-format --dry-run --Werror` on all changed C++ files;
`git diff --check`, Python byte-compilation and the host runner tests also run.

## Adversarial review and reassessment

Review covered instruction cadence, autonomous reload, observation ambiguity,
DMA BUSY transitions, flash-copy races, 64-bit arithmetic, both-core lockout,
SRAM callback dependencies, scratch/settings boundaries, watchdog breadcrumbs,
boot-held behavior, test isolation, runner identity/deadlines and evidence scope.
Actionable findings and resolutions:

- Do not infer stopped DMA from a BUSY pulse at reload: check EN/errors and
  progress timeout instead.
- Do not trust a ring word copied while DMA can overwrite it: recheck producer
  against the still-unconsumed position before dispatch.
- An after-release result cannot prove threshold execution while held: require
  observed stop and AP requests while held in LONG/STUCK.
- A command completion is not recovery evidence: require post-action sample
  and both-core progress, no extra actions and unchanged settings checksums.
- Long runs can wrap 32-bit XIP probe counters: compare bounded successive
  observations, while lifetime sample/DMA counters remain 64-bit.
- Preserve actual synthetic release timestamps and allow the final debounce
  interval after a delayed release; do not expose an internal deadline sentinel
  as a release timestamp.
- A reset during scratch writing cannot guarantee scratch restoration: reserve
  the sector outside application/settings, require a prior backup, and never
  report interruption as successful restoration.
- The test image needs a remote restoration route: add guarded maintenance
  BOOTSEL, excluded from automatic tests, with automatic USB reset routes off.

The full deterministic suite passed **91/91**. The seven diagnostic runner/link
negative tests and affected button/field checks passed again after repairs.
Pinned default, opt-in runtime and diagnostic builds and their linked gates
passed; formatting, Python compilation and whitespace checks passed.
Affected host, build and link checks were rerun after repairs. Reassessment
found no remaining actionable source issue in this bounded slice. Physical
results are not inferred from these checks.

## RF obstruction and remaining acceptance

The explicit command
`cmake --build build/pico2-w-gp14-robustness --target WsprryPico-StandaloneRF -j 4`
still fails at `src/provisioning/pico/gatt_transport.hpp:3`: `btstack.h` missing.
Shared main now uses field services, while BTstack, field/consumer adapters
and shutdown trace dependencies are configured for the inhibited image.
The RF target also retains a 16 KiB stack versus the inhibited field image's
32 KiB stack. Adding a header include is insufficient. A coherent integration
must reconcile these dependencies, memory/stack budget, active-job admission,
core-1 flash coordination and the independent GP14 safety path. This source
slice leaves that RF target unmodified and records the obstruction. No RF
candidate was linked or claimed accepted.

## Future bounded device procedure

The operator subsequently allowed flashing either board if needed. No board
was needed to establish the source/build results recorded here. The new fault,
flash-write and reset campaign remains an explicit device action: bind B's
serial `CDDBF8767C506C07`, the exact clean diagnostic artifact/hash below and
selected actions before executing it. Preserve B's current generation-2
profile and generation-1 access record with a new private full-flash backup;
do not reuse or restore a stale generation-1 profile backup. Preserve the
currently accepted `fce8776` UF2 for restoration. A can keep that candidate.

1. Record board/serial, reviewed UF2 hash, 150 MHz, no RF engine, disconnected
   RF output and current settings. Back up full flash and hash it privately.
2. Flash only the reviewed diagnostic payload and verify it. Inspect STATUS
   for `gp14-robustness`, matching serial/revision, `synthetic=1`, `rf_output=0`,
   started capture and both-core progress. Do not attach a GP14 jumper.
3. Preview `python3 scripts/gp14_robustness_campaign.py`. After exact action
   authorization, execute with `--run --serial CDDBF8767C506C07 --revision
   <12-digit-revision> --image <reviewed.uf2> --sha256 <hash> --evidence
   <new-private-directory>`. `--actions` limits the campaign. Every fault case
   includes normal-reset cleanup. The full default campaign takes roughly
   fourteen minutes; STUCK is 610 seconds. Stop on the first assertion failure.
4. Inspect private raw JSONL, result/failure record, settings checksums, fault
   causes, durations, while-held requests, DMA reloads and post-release/reset
   continuity. Compare settings partitions byte-for-byte with the backup
   using an explicitly authorized ROM readback; FNV alone is not that proof.
5. Under the existing flash authorization, ARM and RUN BOOTSEL, restore the
   reviewed RF-inhibited runtime image without replacing settings, and verify
   identity, station connection, profile/access generations and inactive output.
   Record the actual final image on each board; never leave a diagnostic
   installed while describing it as the field candidate.

A later live SoftAP campaign can use normal INFO telemetry to verify held
retention, release/expiry, network recovery and phone behavior. It must bind
its own reviewed image and actions. Actual pad/contact overlap needs a real
contact or separately authorized pulse source; synthetic PIO does not cover
that path. Conducted active/armed RF latency and physical watchdog output
safety are later RF gates. No Phase 12 row is closed by this build.

## Clean source artifacts and final repository handoff

Source commit: `ae6fd97d71a63b16248bade1fe71923454e18e5c`.
All three images embed clean revision `ae6fd97d71a6`. They were rebuilt after
that commit, with a clean checkout, using the configure options recorded
above. Both CMake directories were explicitly reconfigured to refresh Git
identity; `cmake --build` alone must not be relied on to refresh that identity.
This artifact-record commit changes documentation only and does not change
the firmware source represented by these hashes.

Immutable local copies, `.bin`, ELF maps, linked-check logs and a machine-readable
manifest are in ignored `build/gp14-robustness-ae6fd97/`. No firmware or private
evidence is committed.

| Image file in that directory | ELF SHA-256 | UF2 SHA-256 |
| --- | --- | --- |
| `diagnostic-ae6fd97` | `e52cf0a966139c9144ad7c0588ecfa9769a0f9322cad4664e373013d2fba2101` | `d32f6b29005161f578ca6cd41f85a3ce21f78575705fb8aaa8ccaa0b9bbd7ed8` |
| `runtime-ae6fd97` | `ecec101b92b825cda5268ee3cc62c6124c97304fd7156290be410724c68974b5` | `5d53db0eb6303b83d295c8215f7b5131e51cd3a36e2ed72ff6cfccf2a8431c8f` |
| `default-ae6fd97` | `ee64c23cbbcba6b9524921522b71f82568f30ee0b92a4d3824a63f7fb95017aa` | `38d8fcd7932f6c0f1f1309df1dadde237c946f6dc7f9654d15b72ad7afa039c8` |

Diagnostic linked text is 93,348 bytes, BSS 35,784 bytes and initialized data
zero; stack/link reservation checks passed. Runtime/default standalone flash,
stack, heap, shutdown and BOOTSEL topology gates passed on the clean images.
Symbol checks confirmed test injection hooks are absent from both field
images, and GP14 capture itself is absent from the default image. The clean
diagnostic passed the two-core XIP, SRAM callback/lockout/fault, fixed scratch
address, UF2 reservation and RF/network exclusion checks. The seven host
runner/link tests include negative callback branches, wrong scratch address
and forbidden RF symbols.

At the end of that source campaign, no device I/O, flashing, RF output or
settings mutation had occurred. A and B had not been live-inspected or changed;
their last accepted installed state was the separate `fce8776` evidence record.
The operator subsequently authorized the prepared B campaign, recorded in the
[target result](phase12-gp14-robustness-target.md), including the initial failed
attempt and telemetry repair above. Consult that record for actual device
results and restoration; real AP/RF acceptance remains separate.
