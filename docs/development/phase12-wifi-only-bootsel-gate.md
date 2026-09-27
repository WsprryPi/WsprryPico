# Phase 12 Wi-Fi-only runtime BOOTSEL gate

Status: **CORE-1 PHYSICAL-PRESS GATE FAILED; SINGLE-CORE AP/PRESS PATH PASSED
WITHIN THE RECORDED SETUP**. No credential-accepting HTTP route is enabled.

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
there was no physical press on the core-1 image in that earlier run.

## Failed core-1 physical-press run, 2026-09-26

After the operator returned to Candidate A, they authorized a second flash of
the exact repaired core-1 UF2 above, a live BOOTSEL press/release probe with AP
traffic and final restoration. The preflash device remained generation 0 with
erased access, healthy storage, empty job and inactive output. The Pi copy's
SHA-256 matched; serial-targeted picotool verified chip ID
`0x0bf4b4aec9ffb344` and reported `OK` for load/verify/execute. The running
diagnostic was RF-inhibited, revision `192bfc028958-dirty`, boot ID
`1d1ae2ee61194a42efd3a7bb9ce82cac`.

The timed probe began with released-button result 0, advancing core-1 flash
reads and successful open-AP traffic on isolated `wspr5` `wlan2`. It observed
`pressed=true` once, with `ok=true`, result 0 and an advancing read counter.
The next USB `BOOTSEL PROBE` received no response. The same run recorded 116
HTTP 200 GETs and 12 failed AP requests. The probe exited nonzero; its script
then masked the primary USB timeout with an AP-failure exception, repaired in
source after the run. No release edge was observed by the diagnostic, so no
physical grant may be inferred.

Candidate A re-enumerated and reported `recovery_boot=true`, fault stage 5,
fault status `0x00020000` (RP2350 `UFSR.INVSTATE`), fault PC placeholder 1,
generation 0, erased access, healthy storage, empty job and inactive output.
The fault data does not identify which core failed or prove its cause. The
combination of the physical press and continuously flash-reading core 1 is
unsafe in this measured topology, regardless of the earlier released-button
and single-core passes. The gate is failed, not merely untested.

The already approved restore was completed before the operator directed future
work to **roll forward without restoring older images**. Serial-targeted
picotool load/verify/execute of the standard GET-only UF2 returned `OK`.
Candidate A now reports revision `fc9caab158b7-dirty`, boot ID
`c7cbd524bbe03db02c8b609e65bf5804`, `recovery_boot=false`, generation 0,
erased access, healthy storage, empty job, inactive output and a safe released
probe result 0 in 36 microseconds. The Pi test AP profile was deleted;
`wlan2` is disconnected while `eth0` and `wlan1` remain connected. The
comparator was untouched. No credentials or RF jobs were used.

## No-flash single-core AP/press run, 2026-09-26

The operator then authorized a separate BOOTSEL press/release with concurrent
AP traffic on the installed standard RF-inhibited image, with **no flash or
restore**. The linked standard ELF has the BOOTSEL callback in SRAM and no
`multicore_launch_core1`, `core1_wrapper` or diagnostic flash reader. Candidate
A began with revision `fc9caab158b7-dirty`, boot ID
`c7cbd524bbe03db02c8b609e65bf5804`, generation 0, erased access, healthy
storage, empty job and inactive output. Isolated `wspr5` `wlan2` joined the
open blank AP.

The 30-second probe completed all 60 safe-zone calls with result 0 and
36–37 microseconds, including seven consecutive `pressed=true` samples
followed by `pressed=false`. The Pi completed 424 AP HTTP 200 GETs with zero
failures. Final USB `INFO`/`STATUS` retained the same boot ID, no recovery,
generation 0, erased access, healthy storage, empty job, inactive output,
zero allocator failures and zero lwIP heap errors. The temporary Pi AP
connection was deleted; `wlan2` is disconnected and `eth0`/`wlan1` remain
connected. The standard GET-only image remains installed. The comparator,
station credentials and RF output were untouched.

This result supports only a **blank, RF-inhibited, core-1-absent** BOOTSEL
topology. The failed flash-reading diagnostic build option has been removed;
the StandaloneRF worker build returns `PICO_ERROR_NOT_PERMITTED` for BOOTSEL
sampling. The standard image link check rejects the known core-1 launcher and
flash-reader symbols; source review also confirms that the standard image does
not start core 1. The standard image cross-build passes the new link check; the
StandaloneRF sampler object cross-compiles to an immediate not-permitted
result. This new guarded source has not been flashed. The failed core-1 press
remains a failed row; the successful single-core run does not convert it to a
pass.

## Remaining target procedure

1. Review the narrowed blank/core-1-absent design and verify its new build and
   runtime guards. The core-1 physical press remains disallowed; do not repeat
   the failed run or enable credential POST in a core-1 image. The failed
   core-1 diagnostic was built from `devel` commit
   `192bfc028958f4726f6a2f849c2c30a7a1db9ab5`
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
2. Complete the remaining browser/session/transaction and station-join gates
   before enabling the physical-grant or encrypted submission path. The blank
   captive page stays read-only until those gates pass. Future authorized
   image changes move forward; the operator has withdrawn the routine
   restore-to-older-image practice.

The optional `WsprryPico-StandaloneRF` cross-build did not complete because
its shared main includes Field-GATT types while that RF diagnostic target
does not receive the production BTstack include/link configuration. The SDK
has BTstack sources, but this target is not the RF-inhibited diagnostic image
and is not flashed under this plan.
