# Phase 10 joint target review

Status: in progress. Host installation, operator documentation and bounded
inhibited USB acceptance are delivered. Conducted acceptance of the repaired
firmware remains open; a Pico power cycle is needed to clear the previous
firmware fault latch before flashing the next image.

## Physical interoperability finding

The first real WsprryPi finite Tone LOAD on source `eb6aa58` was rejected with
`FREQUENCY_REJECTED`, before ARM and with output inactive. The captured request
was a 5 s, 137500 Hz Tone followed by a 1 ns RF-off event, with explicit frequency
adjustment consent. The inhibited simulator had accepted this valid WTP shape;
its success did not establish physical waveform representability.

The physical planner required an exact sample boundary even at the end of the
final already-low interval. It now pads only that final RF-off endpoint upward
to a sample boundary. Every RF transition retains the exact representability
rule. No RF-on interval grows, no interior gap disappears, and the immutable WTP
job is unchanged. Stream completion accounting permits the planned low padding
only after the declared job end.

The regression covers the 1 ns terminal marker, generated zero padding,
malformed terminal frequency, an RF-on sub-sample event, an interior sub-sample
off gap, and streamed completion/disable. The lifecycle regression exposed the
completion-accounting issue during the first reassessment; that issue was fixed
and all affected checks rerun.

Validation after both fixes:

```sh
clang-format --dry-run --Werror src/rf/waveform.cpp src/rf/stream_engine.cpp tests/rf_stream_tests.cpp
cmake --build build/phase10-host --parallel 4
ctest --test-dir build/phase10-host --output-on-failure
cmake --build build/phase10-sanitize --parallel 4
ctest --test-dir build/phase10-sanitize --output-on-failure
cmake --build build/phase10-132 --parallel 4
ctest --test-dir build/phase10-132 --output-on-failure
cmake --build build/phase10-150 --parallel 4
ctest --test-dir build/phase10-150 --output-on-failure
```

All passed: 25 host tests, 17 sanitizer tests, and 16 tests for each alternate
clock profile. The optional host-client dependency remains pinned to the
reviewed WsprryPi source. Second source assessment found no further actionable
issue in the changed boundary handling: malformed jobs and nonterminal timing
remain rejected, frequency adjustment indexing is preserved, sample arithmetic
remains bounded, and no physical engine is added to the standard image.

The failed physical attempt remains under
`wspr5:/home/pi/phase10-wtp-acceptance/evidence/rf-tone/`, including exact wire
requests, receiver metadata, IQ hash and verified receiver cleanup. It is a
retained failed acceptance attempt, not an RF pass.

## Physical start-resolution finding

The next Tone attempt on `3bccf7339afa` accepted LOAD with its frequency
adjustment, then rejected ARM as DEVICE_FAULT without launching. The sink's
whole-microsecond requirement could not represent the real host's nanosecond
start. Evidence is retained under `evidence/rf-tone-2/` on wspr5. The host
correctly latched blocked cleanup; Console independently confirmed inactive RF.

The physical adapter now realizes the target at the preceding timer tick and
charges the sub-microsecond adjustment to the unchanged uncertainty ceiling.
Admission checks actual lead time and the expanded leap interval; the local
launch guard rechecks the combined error budget and refuses missed ticks.
WTP's exact reported clock mapping, immutable ARM request and client validation
remain unchanged. No protocol field or client acceptance check was relaxed.

Adversarial regression checks include a fractional clock mapping and host
request, exactly sufficient versus one-nanosecond-insufficient budgets,
uncertainty growth before launch, and a missed timer tick. An actual host-client
session now sends the captured finite Tone shape to the real physical waveform
planner and PIO sink using an admission-only fake hardware adapter. It verifies
LOAD, fractional ARM, ABORT and RELEASE; it cannot qualify target execution.
This closes the simulator-only coverage gap behind the two target findings.

The second source assessment checked overflow, minimum lead, leap exclusion,
exact host response validation, strict missed-start behavior and unaffected
inhibited defaults. All affected checks passed again: 25 host tests, 17 sanitizer tests and 16
tests at each alternate clock profile. Target acceptance remains pending.

## Delivered host and operator documentation

- WsprryPi `devel`: `e95932feebc44d84988c96df969c8f8203ed8c1c`, merging the
  reviewed `2819f0b8ccb05f12d7f978a4cee2cac830997bbf` feature. Their source tree
  is identical: `4c8f003140ffe970adf2eeb552bf0974c3665881`.
- Operator manual `devel`: `5bbce2d8c46243cc910f663f56397a8f32fdd2fb`.
  CLI, INI and Transmitter-tab guidance is published. Strict Sphinx rendering
  passed; desktop, tablet and mobile checks passed after repairing two anchors.
  The Pico UI development toggle remains default-off and browser-only.
- Real Linux semantics and all WTP protocol, plan, USB, backend, scheduler,
  status, application, production-runtime and UI suites passed on wspr5.
- The release executable was built in the clean detached host checkout at
  `/home/pi/phase10-wtp-acceptance/host-git`. Its exact source commit is exposed
  by the installed version API; detached `HEAD` labels are retained truthfully.

Installed executable SHA-256:
`f5759b678b668caa9a639430fcd9b54066a06be0107a58e3e8e8d90d5dca1bfb`.

Authorized installation used the maintained installer and its local-binary
validation path:

```sh
cd /home/pi/phase10-wtp-acceptance/host-git
rm -f /home/pi/finished
sudo env TERM=xterm INSTALL_RP1_GPCLK_DKMS=false ./scripts/install.sh \
  --binary-source local \
  --binary-path /home/pi/phase10-wtp-acceptance/host-git/src/build/bin/wsprrypi \
  --release --fail-on-ui-modifications && touch /home/pi/finished
```

The installer completed successfully, with service and Apache proxy readiness
verified and `/home/pi/finished` present. The first invocation exited before
mutation because noninteractive SSH supplied an unknown terminal type; its log
is retained separately. The successful log is `evidence/installed-release-2.log`.

GET `/wsprrypi/api/wtp` returns `{"selected":false}` under the preserved RP1
selection. POST `/wsprrypi/api/wtp/recover` returns HTTP 409 with
`Pico is not selected`. GET `/wsprrypi/version` reports clean source `e95932fe`
and compiled `wtp` support. These checks validate the installed proxy and refusal
path, not an installed-release RF execution.

The installer preserved every existing INI setting and added the seven WTP
settings. `Transmit=false`, `Enable on Boot=Never`, and `rp1-gpclk` selection
remain. The new INI hash is
`b51b37a073d8a2a59a1f2fcd003b1b582f6b59b1a683bc49f44776ee3c6d9352`;
`evidence/installer-config-diff.json` records no changed existing setting.
The boot configuration hash remained
`2ffa49332aea06b30d8dddb70cc3cf8246627ea8fdfc277a91bc60b1bf391594`.
The RP1 maintained read-only snapshot passed its idle predicate on route 1/GPIO4,
with output inhibited, as before installation. No provider update or route
activation ran. WsprryPi, Apache, gpsd and chrony are active; chrony remains
PPS-selected, stratum 1, normal leap state. No Pi reboot was performed.

## Bounded physical USB evidence

These completed checks bind to Pico source `eb6aa58`, inhibited image SHA-256
`fa662bc5b3cdc2d6c61622733c67665477b1db39eb7d7d2ba500bdc69e80e752`,
Pico 2 W/RP2350A2 serial `0BF4B4AEC9FFB344`, WTP device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, and the real host on wspr5.
They do not transfer physical RF qualification to either repaired image.

Evidence is under `/home/pi/phase10-wtp-acceptance/evidence/` on wspr5:

| Check | Evidence file | Result |
|---|---|---|
| Default 1 ms clock budget | `clock-rejection-2.jsonl` | Rejected before ARM; cleanup inactive |
| QRSS ETE | `qrss-complete.jsonl` | Complete |
| FSKCW ETE | `fskcw-complete.jsonl` | Complete |
| DFCW ETE | `dfcw-complete-3.jsonl` | Complete |
| Encoded WSPR | `wspr-complete.jsonl` | Complete |
| Finite 5 s Tone | `inhibited-tone.jsonl` | Complete |
| Stop while armed | `cancel-armed.jsonl` | Cancelled, inactive |
| Stop while running | `cancel-running.jsonl` | Cancelled, inactive |
| Exact WTP CDC detach/rebind | `inhibited-disconnect.jsonl` | Unknown state latched; explicit reconciliation and owned abort |
| Foreign ownership | `inhibited-foreign.jsonl` | Refused without adoption; finite lease expired |
| Console reboot | `inhibited-reboot.jsonl` | Changed boot identity latched, no job submission |
| Stale device time | `inhibited-clock-loss.jsonl` | Rejected before ARM; Wi-Fi restored |

The Linux aliases are the same exact serial with `-if00` for Console and `-if02`
for WTP; VID/PID is `0xcafe:0x4012`. The disconnect test detached only the
verified WTP CDC function, leaving Console and other USB devices alone.
Earlier observer/setup failures are retained, including attempted web editing
of an INI-only experimental policy and cancelled reload/scheduling observations.
Corrected observers were rerun; those attempts are not counted as passes.

## Repaired firmware and remaining target work

The clean repaired source is `4c35aaaf7a66` (following `3bccf7339afa`). All four
firmware images built with Pico SDK 2.3.0 at
`98a542c1a62fb549ffb5d66a3e5892b06276b670`, Arm toolchain 15.3.1, Release,
Pico 2 W and 138 MHz physical clock. ELF symbol inspection confirms the standard
image contains no physical Pico PIO/DMA launch implementation.

| Image | SHA-256 |
|---|---|
| Standard inhibited | `dc8478fe15e47fde18ef80386d2a79c2af8e1f0c3d31c429ff080b171863c7bf` |
| StandaloneRF | `c6dc45f32b942d60377758a49f60da2837e523dacd07d8966628a4e7deb2ba0c` |
| RFWTP | `6f3bb9d818f833e9ff67f2b6533aaefd2619b0c64f159eca8c036eb7faf77cee` |
| RFBench | `fab32a65e9a8893e5d6e8bb983d185aec63096800ddbca1b43946e3bb58308ec` |

The standard and StandaloneRF images are staged on wspr5 at
`/home/pi/phase10-wtp-acceptance/`. Generated firmware and raw IQ are not tracked.
At the last verified target observation, source `3bccf7339afa` was still running
with state `failed`, output inactive, zero launch/DMA counters and persistently
disabled autonomous scheduling. Its local STOP/reboot idle guard refuses that
fault state. A physical Pico USB power cycle is required; do not clear or bypass
its fault latch through a remote ownership request. The user has been asked to
reconnect only the Pico USB cable. RF acceptance is paused pending that action.

After reconnection, recheck serial/device/boot and inactive disabled scheduling;
flash and verify the staged `4c35aaaf7a66` StandaloneRF image. Repeat the bounded
five-second Tone, real-host QRSS/FSKCW/DFCW ETE jobs and three WSPR frames at
137500 Hz. Bind each run to Pico GP2, its confirmed 60 dB attenuation and common
SDR combiner; keep GPSDO Output 1 and wspr5 GPIO4 inactive. The exact receiver is
RSP1B `2404058C60`, centered at 112500 Hz, 250 ksps/200 kHz bandwidth, gain 20,
AGC and bias tee off. Retain leading/trailing quiet and independent RF analysis
and WSPR decoding. Restore the inhibited firmware afterward and verify inactive
output and disabled scheduling. Repeat affected installed-release checks and
perform the final adversarial assessment before closing Phase 10.

The current scope does not qualify calibrated UTC/GPIO timing, RF power or
emissions, external output filters, all bands/clocks, broad reliability or a
reproducible production release. Phases 11–13 remain planned.

## Final source reassessment

Adversarial inspection found that a leap transition announced after ARM also
needed the early timer adjustment included in the prelaunch exclusion check.
That check is repaired. Regressions now cover the exclusion boundary at
admission and after ARM, as well as budget growth and missed ticks. All 25 host,
17 sanitizer and 16 tests per alternate profile passed again. Source
reassessment found no further actionable defect in the changed paths.
The next firmware build must include this last correction before target use;
the preceding `4c35aaaf7a66` image table is retained until that build is recorded.
