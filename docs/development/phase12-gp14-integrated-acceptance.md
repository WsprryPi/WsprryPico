# GP14 renewed runtime and integrated acceptance

Status: **bounded deployment and integrated test complete** (2026-09-30). Executes the operator's approval for
remaining steps 1 and 2: deploy the DMA renewal code in the opt-in inhibited
runtime and test real input/flash overlap plus live AP retention and expiry.
Only B is available for GP14 contacts. Flashing either board is authorized;
A was untouched. Real RF integration,
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
   deliberate extension. Seek an edge bracketed by real level changes
   inside a callback, then replayed through the ordinary PIO/DMA/policy path.
   The narrower timing-based witness accepted below is explicitly distinguished
   from that original endpoint-level criterion.
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
was started before asking the operator to fit the jumper. The operator's
physical hold and expiry observation have completed below.

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
this bounded review. Physical probe evidence and its limits are recorded below.

The maintained console client exposes `gp14-flash` only with `--run`, an
explicit `--revision`, matching INFO identity and a healthy RF-inhibited
test-variant marker. The device also enforces its own admission and count
limit. The temporary probe was installed after the completed AP observation;
the real-pad flash-overlap result and restoration are recorded below.

## Reproducible probe build and execution bounds

The clean probe source commit is
`f2af9dd4eddeea94cdc6838b5d6f91141b5bc819`; its embedded revision is
`f2af9dd4edde`. The existing local SDK is 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`, with Arm GCC 15.3.1 and the
existing picotool dependency. No dependency was fetched. From the repository:

```sh
source scripts/xcode_env.sh
PICO_SDK_PATH="$PWD/build/local-sdk-079c6f3" cmake -S . \
  -B build/pico2-w-gp14-flash-probe -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DWSPRRY_PICO_BUILD_FIRMWARE=ON -DWSPRRY_PICO_BUILD_TESTS=OFF \
  -DPICO_BOARD=pico2_w \
  -DPICOTOOL_FETCH_FROM_GIT_PATH="$PWD/build/pico2-w/_deps" \
  -DFETCHCONTENT_FULLY_DISCONNECTED=ON \
  -DWSPRRY_PICO_GP14_RUNTIME_BUTTON=ON \
  -DWSPRRY_PICO_GP14_FLASH_PROBE=ON \
  -DWSPRRY_PICO_GP14_ROBUSTNESS=OFF
cmake --build build/pico2-w-gp14-flash-probe --target WsprryPico -j 4
python3 scripts/check_shutdown_image.py build/pico2-w-gp14-flash-probe/firmware/WsprryPico.elf
```

The probe SRAM/flash checker and the ordinary image checks run after linking.
The normal runtime used the same configuration with build directory
`build/pico2-w-gp14-robustness` and `WSPRRY_PICO_GP14_FLASH_PROBE=OFF` at the
clean `6105f9d` source revision.

Probe UF2 SHA-256:
`487f0d8bf0ea5ef017b19b1e66906fe9722ea162e76d6aec9aa3ba05d1289324`.
Probe ELF SHA-256:
`7d8ba77a38cb7275cf834d3cf9b36b69d700143f4963d475b07eaf93dacb8154`.
The immutable artifacts and manifest are retained privately with the runtime
artifacts. The staged device-host UF2 hash matches the local manifest.

The real-pad procedure uses at most 16 two-second callbacks per boot while
the operator makes a casual 2–3 second contact. Each command is identity-bound
and checks scratch pattern/restoration. The original runner sought both edge
directions bracketed inside callbacks, ordinary captured release duration and
shutdown classification, then at least 60 seconds of capture/station progress.
An edge missed by the bounded observation is reported as unaccepted, never
inferred from a contact held across the entire callback. Actual erase/program
overlap is claimed only if the before/after-write pad samples differ.

The final temporary-image transition must read back the entire reserved
57,344-byte region, compare it byte for byte with the fresh backup, load and
verify the normal `6105f9d` runtime, repeat that comparison, and verify at least
60 seconds of unchanged settings and station/capture continuity. The probe
image must not be left installed after this campaign.

## Live hold and observation-boundary record

The operator connected physical pin 19 (GP14) to pin 18 (GND) on B. On the
normal `6105f9d` runtime, the first held INFO observation was at device time
1355.907596 seconds; AP readiness followed at 1364.820943 seconds. After
610.295847 seconds of observed hold and 601.382500 seconds of AP readiness,
the monitor reported that release was ready. The operator left the jumper
connected longer; the eventual captured duration was **1,520.711 seconds**.
Only one stop event, one setup event and one accepted AP request occurred;
there was no reset or capture fault.

The spare wspr5 `wlan2` interface associated with the observed open AP
`WsprryPico-0a9d89`, BSSID `88:A2:9E:0A:9D:89`. A temporary, non-autoconnecting
NetworkManager profile used neither a default route nor AP-supplied DNS;
existing Ethernet and station Wi-Fi connections remained in place. Read-only
GET requests for `/` and `/api/owner/v1/public-status` succeeded every twenty
seconds during the observed hold, including beyond ten minutes. The public
device/boot identity and generation matched USB. No form submission, claim,
controller-time request or settings write was made.

The original USB monitor's fixed 45-minute bound included the long wait before
the operator's press. It therefore ended while the pin was still held, at
device time 2799.267772 seconds. The independent HTTP observer stopped on
that timeout. Both failure records are retained; they are observer timeouts,
not evidence of a device reset or AP failure. Continuous USB/HTTP observation
through the resulting gap is not claimed.

After the operator reported release, a fresh identity-bound INFO read at
2924.877452 seconds showed the same boot, the retained 1,520.711-second
duration, released input, active unheld manual lease, healthy storage,
unchanged generation-2 profile/generation-1 access and no fault. A bounded
15-minute continuation resumed INFO and read-only HTTP checks. Release was
not directly timestamped over USB: the previous press bracket and retained
sampled duration give a conservative device-time release interval of
2873.510688–2878.618596 seconds, including a two-second allowance on either
edge for debounce/dispatch and observation uncertainty. The recorded maximum
backlog remains 131 words (1.048 seconds at nominal sample cadence). The
expiry report uses that interval rather than an invented exact release
timestamp.

The lease was last active at 3475.975534 seconds and first inactive at
3477.097540 seconds. With the conservative release bracket, the observed
expiry interval is **597.356938–603.586852 seconds after release**, consistent
with the unchanged 600-second lease. AP requested/adapter/service indicators
all cleared, with station Wi-Fi still connected. Read-only HTTP checks passed
after reconnect and during the lease, then stopped before expiry. A subsequent
AP HTTP request timed out as expected. The host driver still reported its
cached association at that point; this is not independent beacon/radio-off
measurement. The temporary host connection was deleted, and `wlan2` returned
to disconnected while the original Ethernet and station connections remained.

The continuation then observed **61.072610 seconds** of station-only service,
with no reboot, capture fault, repeated gesture or settings change. Across
the initial and resumed observations, capture advanced from 99,888 to
3,538,152 samples and DMA blocks from 3 to 107; maximum reported backlog was
131 words. This accepts bounded real-pad long-hold AP retention and lease
expiry on B, with the monitoring gap and timing uncertainty stated above.
It does not accept RF shutdown latency or continuous coverage of the gap.

## Temporary probe deployment

After both AP observers had stopped, an identity-bound USB command returned
B to ROM. Before loading the probe, the verified reserved-region readback
matched all 57,344 bytes of the fresh backup. The staged UF2 hash matched the
clean manifest. `picotool load -v` verified the new image, and another
reserved-region readback matched before application boot. B then reported
`f2af9dd4edde`, the probe marker, released/fault-free GP14, inhibited output,
healthy storage and unchanged profile/access generations. Boot ID:
`1040fbbb7e015916c87aa642b93f4d35`. The subsequent bounded probe run is recorded below.

The exact private transition command on wspr5 was:

```sh
python3 -u /home/pi/gp14-integrated-b-20260930/transition.py probe --run
```

The retained script binds B's serial/device identity, source and destination
revisions, UF2 and backup hashes. Its ROM operations are the existing
picotool's `save -r 0x103f2000 0x10400000 -v <private-file> -t bin`,
`load -v <verified-image>` and `reboot -a`, each with
`--ser CDDBF8767C506C07`. It performs both raw byte comparisons itself.
The corresponding `runtime --run` transition is prepared for final restoration.


## Real-pad flash result and adversarial reassessment

The operator made one casual contact; firmware measured **1.340 seconds**.
All sixteen probes completed pattern verification and scratch restoration.
Their flash-safe intervals were 1,999,999–2,000,000 microseconds; actual
writes took 8,524–8,648 microseconds. One shutdown request was recorded, with
no AP request, reset, capture fault or changed settings.

The original private runner ended with an evidence-criterion failure because
all three sampled pad endpoints were released; it had required both edge
directions to be directly bracketed. Its failure and raw records are retained.
Review identified a valid narrower witness: the captured gesture cannot fit
in either gap outside callback 12 and is shorter than the callback itself.
Thus at least one captured edge must be inside the callback. This does not
prove that both edges were inside, or that an edge coincided with actual
flash erase/program rather than the deliberate interrupt-masked extension.

Callback 12 began at 142,378,245 us, ended its actual write at 142,386,809 us
and ended the safe interval at 144,378,245 us. The preceding INFO was released,
with zero duration/stop events and 142,208 consumed samples; the following
INFO at 144,586,718 us was released with duration 1,340,000 us and one stop.
At 1 kHz, a nonnegative sample-clock origin and the 10 ms debounce give a
conservative earliest raw start of 142,197,000 us. The outside gaps are at
most 181,245 and 208,473 us. At least **950,282 us of the measured gesture
interval overlaps the callback**, and its 1,340,000 us duration cannot
surround a 2,000,000 us callback. No exact edge timestamp is invented.

The new offline `scripts/gp14_flash_overlap.py` checks this timing bound;
it performs no device I/O. Regression tests cover the actual record, gestures
that fit outside or surround the callback, equality boundaries, malformed or
impossible timestamps and exhaustive placements across the observation window.
Review added a check that the consumed sample cannot lie in the future.
Reassessment found no further actionable issue in the bounded inference.
The thirteen focused robustness tests and all **91 host tests** passed after
that repair (full host suite: 53.19 seconds), as did Python compilation and
whitespace checks. The earlier cross-build/SRAM/formatting gates remain valid:
this final change alters only offline evidence analysis, tests and documentation.

A separate read-only observation then confirmed **61.396109 seconds** of
healthy probe-runtime continuity, same boot/settings, station Wi-Fi, samples
312,824 → 374,216 and DMA blocks 9 → 11. Maximum backlog was 255 words during
the deliberate blackout. The result accepts real input capture across the
extended flash-safe service pause. **Exact erase/program edge coincidence and
real RF shutdown latency were not measured.** No repeat manual contact was
required merely to match the requested approximate hold duration.

## Final restoration and repository handoff

The normal renewed runtime `6105f9d8da2e` was restored using the prepared
`transition.py runtime --run`. Verified ROM reads before and after loading
again matched all 57,344 reserved bytes against the fresh backup. The full
campaign therefore has five byte-identical reserved-region comparisons:
initial runtime load, before/after probe load, and before/after restoration.
No settings partition was restored or rewritten by the procedure.

Final read-only verification covered **61.383312 seconds** on one normal boot,
`0bb7e96b3514358cd07a9750e829f227`, with samples 56,328 → 117,712 and DMA
blocks 1 → 3. The probe marker was absent; GP14 was released, all gesture
counters and AP flags were clear, no fault/recovery was present, and output
remained inactive under the inhibited simulator. Profile generation 2,
access generation 1, station/schedule/watermark fields and station address
`192.168.1.53` matched baseline. A was untouched. All monitors have finished;
no process needs the Mac to remain running for board safety.

Raw failed/successful observations, scripts, manifests, backup and readbacks
are retained privately under `build/gp14-integrated-b-20260930/` and the matching
wspr5 directory. They are excluded from Git. The scoped source/evidence work
is committed on `devel`; final commit and independently checked remote parity
are reported in the task handoff. GP14 remains opt-in. The RF build/integration,
active/armed RF shutdown measurements, default enablement, P12.7, P12.11 and
Phase 12 closure remain separate gates.

The complete private archive `gp14-integrated-b-20260930-evidence.tar.gz`
was copied to the Mac and independently inspected. Both hosts report SHA-256
`23bd525495da52f1be3ae2ce837d372840adc407b12ecd952c94f6428c4fcf51`.
Local archive inspection repeated all five raw reserved-byte comparisons and
verified the final restoration result. No test monitor remained running.
