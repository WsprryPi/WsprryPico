# Phase 12 Wi-Fi-only runtime BOOTSEL gate

Status: **SINGLE-CORE PRESS/RELEASE AND CORE-1 RELEASED/AP PROBES PASS;
TARGET GATE OPEN**. No credential-accepting HTTP route is enabled. The physical
press while core 1 is active remains unqualified.

## Candidate and source checks

- Board: Candidate A, Pico 2 W / RP2350, USB serial
  `0BF4B4AEC9FFB344`, device ID
  `fd6127d11d6aca42a9905fa3fb1bf1d5`; the comparator is out of scope.
- Diagnostic image: RF-inhibited `WsprryPico.uf2`, SHA-256
  `0bc63856a168f3f3a79544d0b1be4e01f3791f71dc7cd1213c111d4357313400`.
  A preserved copy is at `/private/tmp/wsprrypico-bootsel-probe-0bc63856.uf2`.
  This uncommitted-source diagnostic was built from `devel` base
  `fc9caab158b71d9dc0d430aafb7d5a22a24f092c` plus the current candidate
  patch; the image hash, not its shortened embedded revision, is the exact
  identity.
- Toolchain: Pico SDK 2.3.1 commit
  `079c6f39023649b154152db30f1d781e884879bc`, Arm GNU 15.3.1.
- The candidate `sample_chip_select` callback occupies 56 bytes in the
  ELF `.data` SRAM section at `0x20000120`. Its disassembly uses register and
  SRAM access only: it saves QSPI CS control, forces its output-enable low,
  waits 1,000 NOP-loop iterations, reads the CS input, restores the exact
  control word and returns. `flash_safe_execute` provides the safe-zone
  entry/exit; a failed result is never a usable button value.
- USB-local `BOOTSEL PROBE` is admitted only while the scheduler is idle and
  output is inactive. It reports `ok` (safe-zone success), `pressed`, elapsed microseconds and
  the SDK result. It grants no network credential authority.

## Bounded Candidate A result, 2026-09-26

The operator approved flashing the exact image above and running the
RF-inhibited probe on Candidate A. The preflash USB `INFO` showed the exact
device ID, unprovisioned generation 0, erased access journal, empty job and
inactive output. The USB-local `BOOTSEL` command was accepted; picotool then
read RP2350 chip ID `0x0bf4b4aec9ffb344`. The copied UF2 matched the hash
above on `wspr5`, and serial-targeted `picotool load -v -x` completed `OK`.

The running diagnostic reported revision `fc9caab158b7-dirty`, boot ID
`fb8a0352d3500e3d1ae8b8987b36a396` and the inhibited standalone
simulator. Ten released-button samples returned safe-zone result 0,
`pressed=false` and 33–37 microseconds. On isolated `wspr5` `wlan2`, the
open AP served `http://192.168.4.1/` with HTTP 200. Twenty more released
samples during concurrent AP requests returned result 0, `pressed=false`
and 36–37 microseconds; 77 AP GETs succeeded and none failed. The final USB
`INFO` retained unprovisioned generation 0, erased access generation 0,
healthy storage, empty job, `output_active=false`, zero allocator failures
and zero lwIP heap errors. The temporary NetworkManager connection on
`wlan2` was deactivated and deleted; `eth0` and `wlan1` remained connected.
The comparator was not operated.

This proves only the released-button single-core path under that bounded AP
load. It does not show a flash-write overlap or second-core coordination. No
station credentials were submitted and no RF job ran.

The operator then approved a separate exact RF-inhibited core-1 image, UF2
SHA-256 `fe574c9ad0cd1fbecf2063e9eeeec33b929e0b95975a30e74915c575e54d0f6d`,
and restoration of the standard diagnostic. Serial-targeted picotool load and
verify passed, but two USB-local `BOOTSEL PROBE` calls returned
`{"ok":false,"error":"core1_unready"}`. No BOOTSEL press was attempted on
that image. Source review found that its explicit core-1 stack was 4 KiB,
exactly the reserve required by `wsprry_stack_limit_for`: the guard rejects a
stack pointer at or below bottom plus 4 KiB before the diagnostic entry can
set its ready flag. This is a concrete defect in that diagnostic, not evidence
of a failed SDK flash lockout. The second-core gate stays open.

The approved standard UF2 `0bc63856...` was restored with serial-targeted
load and verify. The final running image reported revision
`fc9caab158b7-dirty`, boot ID `150e65b6c16005a9f6727459584bd676`,
unprovisioned generation 0, erased access generation 0, healthy storage,
empty job, inactive output, zero allocator failures and zero lwIP heap errors.
The operator held and released BOOTSEL while the 50-second USB-local probe ran
on this restored image. Nine consecutive samples reported `pressed=true`,
followed by `pressed=false`; all 100 safe-zone calls returned `ok=true`, SDK
result 0 and 33–38 microseconds. This qualifies the single-core press/release
transition for this exact RF-inhibited image, without AP traffic during the
press. The blank AP remains GET-only; the comparator was untouched.

The source repair supplies 8 KiB to the opt-in core-1 diagnostic, retaining
4 KiB beyond the project guard reserve. Its cross-build and linked heap/both-
core stack checks pass. The repaired candidate UF2 SHA-256 is
`e35431ef397ffd5ee6ebc3405e9d5f165c1db76f6ef7329aedcd86ed963570b6`.
The operator approved flashing that exact RF-inhibited image, testing the
released-button path with AP traffic and restoring the prior image. The copied
UF2 on `wspr5` matched the hash; serial-targeted picotool read RP2350 chip ID
`0x0bf4b4aec9ffb344` and load/verify/execute succeeded. The running diagnostic
reported revision `192bfc028958-dirty`, boot ID
`281143e2fd97104691de2df73e886edc`, inhibited standalone simulator,
healthy generation-0/erased state, empty job and inactive output. One initial
released-button probe returned `ok=true`, result 0, 84 microseconds and an
advancing core-1 read counter. On isolated `wspr5` `wlan2`, twenty further
released-button safe-zone probes returned result 0 and 82–85 microseconds while
the flash-reading core counter advanced across every call. Concurrent blank-AP
traffic completed 52 HTTP 200 GETs with zero failures. The final core-1 image
read retained generation 0, erased access, healthy storage, empty job, inactive
output and zero allocator failures. No credential POST or RF job ran.

The temporary Pi AP profile was deleted and `wlan2` left disconnected;
`eth0` and `wlan1` remained connected. The approved standard GET-only UF2
`0bc63856...` was then serial-targeted loaded and Candidate A booted it with
revision `fc9caab158b7-dirty`, boot ID
`120ff9cfac570eb33fcc68b6ec790e94`, generation 0, erased access, healthy
storage, empty job, inactive output and zero allocator failures. A final
released-button probe returned result 0 in 36 microseconds. The comparator was
untouched. This bounds the second-core result to released-button/AP activity;
there was no physical press on the core-1 image.

## Remaining target procedure

1. Under a separate exact-image authorization and with the operator at the
   device, repeat the press/release transition while the repaired core-1
   diagnostic runs and AP traffic continues. Require safe completion, correct
   transitions, resumed core-1 reads, restored USB/AP service, no reboot and
   preserved journal. The current standard RF-inhibited image does not start
   core 1; the separate opt-in `WSPRRY_PICO_BOOTSEL_CORE1_DIAGNOSTIC` image is
   RF-inhibited and has no HTTP write route. It uses an 8-KiB explicit core-1
   stack, repeated XIP flash reads, SDK `flash_safe_execute_core_init()` on
   core 1 and a progress counter in `BOOTSEL PROBE`. The repaired diagnostic
   was built from `devel` commit `192bfc028958f4726f6a2f849c2c30a7a1db9ab5`
   plus the repaired core-1 candidate patch (`git diff` over
   `firmware/CMakeLists.txt` and `src/standalone/pico/main.cpp`, SHA-256
   `a415c0d32425c7f11ae485680c3911288c721d829298b66e1c38f6379e0dabaa`),
   Pico SDK 2.3.1 commit
   `079c6f39023649b154152db30f1d781e884879bc` and Arm GNU 15.3.1.
   Its linked image contains the SDK multicore lockout handler and the
   56-byte SRAM BOOTSEL callback; heap and both-core stack link checks pass.
   The build required the full Xcode 26.5 SDK environment for SDK-hosted
   `pioasm` and picotool; the default command-line SDK failed those host
   linker probes. The final build passed with `DEVELOPER_DIR` and `SDKROOT`
   pointed at Xcode.
2. Record exact timings, flash/core/radio result and final restoration before
   enabling the physical-grant or encrypted submission path. A failed or
   inconclusive run keeps the blank captive page read-only.

The optional `WsprryPico-StandaloneRF` cross-build did not complete because
its shared main includes Field-GATT types while that RF diagnostic target
does not receive the production BTstack include/link configuration. The SDK
has BTstack sources, but this target is not the RF-inhibited diagnostic image
and is not flashed under this plan.
