# Phase 12 Wi-Fi-only runtime BOOTSEL gate

Status: **SINGLE-CORE RELEASED-BUTTON PROBE PASS; TARGET GATE OPEN**. No
credential-accepting HTTP route is enabled. A physical press/release and the
second-core interaction remain unqualified.

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
load. It does not show a physical press edge, grant, flash-write overlap or
second-core coordination. The diagnostic remains flashed and exposes the
same GET-only blank AP. No station credentials were submitted and no RF job
ran.

## Remaining target procedure

1. Have the operator press and release BOOTSEL; probe while held and after
   release. Require safe completion, correct transitions, restored USB/AP
   service and no flash/journal corruption or reboot.
2. Repeat with the second core running a flash-using idle diagnostic and its
   SDK flash-safe victim initialized. The current standard RF-inhibited image
   does not start core 1; the single-core probe cannot by itself close this
   row. A separate exact RF-inhibited diagnostic image and authority are
   needed if the static audit cannot prove the second-core interaction.
3. Record exact timings, flash/core/radio result and final restoration before
   enabling the physical-grant or encrypted submission path. A failed or
   inconclusive run keeps the blank captive page read-only.

The optional `WsprryPico-StandaloneRF` cross-build did not complete because
its shared main includes Field-GATT types while that RF diagnostic target
does not receive the production BTstack include/link configuration. The SDK
has BTstack sources, but this target is not the RF-inhibited diagnostic image
and is not flashed under this plan.
