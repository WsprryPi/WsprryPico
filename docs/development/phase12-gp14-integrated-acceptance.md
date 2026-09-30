# GP14 renewed runtime and integrated acceptance

Status: **in progress** (2026-09-30). Executes the operator's approval for
remaining steps 1 and 2: deploy the DMA renewal code in the opt-in inhibited
runtime and test real input/flash overlap plus live AP retention and expiry.
Only B is available for GP14 contacts. Flashing either board is authorized;
A remains untouched unless a second device is needed. Real RF integration,
default enablement, P12.7, P12.11 and Phase 12 closure are outside this slice.

## Execution brief and acceptance criteria

Start from clean `devel` at `6105f9d8da2ee5d7fe1b4adfd1d0cb310543dcfb`.
Read the repository instructions and preceding
[diagnostic closeout](phase12-gp14-robustness-target.md). Preserve current
settings/evidence, use pinned local dependencies, and bind each device action
to serial, device ID, image revision and verified UF2. Do not download tools.

1. Build the current opt-in `WsprryPico` runtime with GP14 enabled, diagnostics
   disabled and physical RF inhibited. Verify host, linked memory/flash and
   shutdown gates. Preserve immutable artifacts and hashes.
2. Back up B afresh, flash/verify the reviewed runtime, compare reserved flash
   bytes, and verify at least 90 seconds of station Wi-Fi, capture and repeated
   hardware DMA renewal with no fault or settings change.
3. Monitor B before inviting a jumper between physical pin 19 (GP14) and pin
   18 (GND). Keep it held until at least 610 seconds of observed hold and
   600 seconds of continuous AP readiness. Require one stop, one accepted AP
   request and no reset/repeated action. On release, observe the unchanged
   ten-minute lease, AP withdrawal on a healthy station and post-expiry
   continuity. Use read-only page requests if a spare host interface is
   available; do not change phone/device settings to manufacture a pass.
4. Use a separately gated runtime test variant for actual GP14 input across
   flash-safe execution. Reserve scratch outside application/settings; never
   write a settings journal for this test. Record real pad levels before and
   after the blackout and distinguish the actual write interval from its
   deliberate extension. An edge must be bracketed by real level changes
   inside a callback, then replayed through the ordinary PIO/DMA/policy path.
   Mere GPIO low throughout an operation is not edge-capture evidence.
5. Restore the normal renewed runtime after the temporary writer. Compare
   scratch/settings bytes, verify network/capture recovery, record the actual
   installed images, review adversarially, repair findings, rerun affected
   checks, and commit/push the scoped result with remote parity verification.

## Normal runtime artifact and initial deployment

B is Pico 2 W / RP2350, USB serial `CDDBF8767C506C07`, device ID
`29f20b7342051ef947aa56cb9d4fab42`, 150 MHz, inhibited simulator engine.
Its fresh baseline retained profile generation 2, access generation 1,
healthy storage, released/fault-free GP14, empty inactive output and station
address `192.168.1.53`. A fresh verified full-flash backup again hashes to
`5c37e691e8a19cf5fcd8a5ba06a84af3d82791357cc8cf1b8d0f629fef400da6`.
It was copied privately to the Mac before the verified load. All 57,344 bytes
from `0x103f2000` through `0x103fffff` matched that backup after loading.

The clean normal runtime embeds `6105f9d8da2e`:

- UF2 SHA-256: `7d2df90f236a6e5d8b5626caac37a542783d50dbd0db81d3fffb4780f74f80ab`.
- ELF SHA-256: `fb06646610c07ad48ff9a0f8dfcf96c341e8354df03f78d80e7554ae36792531`.
- Private immutable files and evidence: `build/gp14-integrated-b-20260930/`;
  device-side evidence uses the matching directory under `/home/pi` on wspr5.

The source review's pinned configure command was used with
`-DWSPRRY_PICO_GP14_RUNTIME_BUTTON=ON -DWSPRRY_PICO_GP14_ROBUSTNESS=OFF`, then:

```sh
cmake --build build/pico2-w-gp14-robustness --target WsprryPico -j 4
python3 scripts/check_standalone_image.py build/pico2-w-gp14-robustness/firmware/WsprryPico.elf
python3 scripts/check_shutdown_image.py build/pico2-w-gp14-robustness/firmware/WsprryPico.elf
bash scripts/check_host.sh
```

All 91 host checks and linked stack/heap/flash/BOOTSEL/shutdown checks passed.
B booted this image; its initial 90-second INFO-only observation passed,
with station Wi-Fi connected and multiple DMA renewals. The live hold monitor
was started before asking the operator to fit the jumper. Hold/expiry results
are pending.

## Temporary real-input flash probe

`WSPRRY_PICO_GP14_FLASH_PROBE=ON` is a separate build variant of the inhibited
runtime and requires the GP14 runtime option. It is off by default. Only this
variant reserves `[0x3f2000,0x3f3000)` for scratch and exposes an identity-bound
USB `GP14 FLASH <device-id>` command. It refuses non-idle/owned activity,
pending reboot, capture failure, any preceding probe failure and more than
16 probes per boot. There is no host-supplied flash address or data.

The probe saves the 4 KiB scratch sector to SRAM, writes/verifies a fixed
pattern and restores/verifies the original bytes. A reset or power loss in
the middle can alter scratch; the fresh backup and final ROM byte comparison
are mandatory. No settings partition is a test target. Linked-image checks
require the reserved boundary and UF2 exclusion, a RAM callback with only
the RAM erase/program calls, and absence of RF engines and synthetic GPIO
injection. The regular runtime contains neither the command nor writer.

The first flash-safe callback records real GP14 input before the erase/program,
immediately afterward and at the end of a two-second interrupt-masked interval.
It uses only SRAM, peripheral registers and SDK RAM flash routines. The
eight-second watchdog is never fed in the callback. PIO and DMA continue;
foreground dispatch, USB and Wi-Fi pause and resume afterward. The extension
makes a manual jumper overlap practical and is explicitly distinguished from
the much shorter erase/program interval. This is not RF shutdown latency
evidence. The inhibited runtime has no core-1 RF worker; the preceding
two-core diagnostic and future real-RF integration remain separate evidence.

## Review, target results and remaining gates

Source review checked fixed scratch bounds, RAM placement and arguments,
watchdog budget, input-only SIO observations, command identity/admission,
bounded wear, restoration failures and compile-time isolation. It replaced
timer-helper calls with inline peripheral reads, made probe failure sticky,
and excluded recovery/failed runtime states from command admission. The
two-second callback includes a deliberate service blackout; that interval
must never be presented as the erase/program duration or RF latency.

Build review found and repaired a post-build ordering issue (the checker ran
before UF2 generation) and a symbol lookup ambiguity caused by ordinary
XIP-to-SRAM SDK veneers. The checker now runs after UF2 generation and checks
the exact SDK function symbols. Negative tests retain rejection of XIP calls,
indirect calls, XIP literals, wrong scratch/reservation and synthetic input.

All 91 host tests passed after the firmware additions. The affected nine
probe/runner/link tests and four console tests passed after the remaining
checker/client repairs. Formatting, Python compilation and whitespace checks
passed. Pinned probe, normal opt-in runtime and default builds passed their
linked memory, heap, stack, BOOTSEL and shutdown gates. The probe's SRAM
callback calls only `flash_range_erase` and `flash_range_program`, both with
literal 4 KiB size and offset `0x3f2000`. Symbol inspection confirmed the
writer is absent from normal/default images and GP14 capture remains absent
from the default image. No further actionable source finding remained in
this bounded review. Physical probe acceptance is pending.

The maintained console client exposes `gp14-flash` only with `--run`, an
explicit `--revision`, matching INFO identity and a healthy RF-inhibited
test-variant marker. The device also enforces its own admission and count
limit. The temporary probe has not yet been installed. The AP hold/expiry
test on the normal `6105f9d` runtime is awaiting the operator's contact.
