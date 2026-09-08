# Phase 10 joint target review

Status: in progress. Host installation, operator documentation and inhibited
USB acceptance are delivered. Source 23376c2 passed all four shorter conducted
modes and one independently decoded WSPR frame. Consecutive WSPR exposed a
clock-refresh retry gap; after that repair, DFCW exposed a local-launch STATUS
race. The reviewed status repair needs final-source RF acceptance and restoration.
The old QRM channel is not a completion gate.

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

## Earlier repaired firmware checkpoint (superseded below)

The clean repaired source is `8b26cad0fccbad838af8dc6f8412a6ba41a6cc37`
(following `3bccf7339afa` and `4c35aaaf7a66`). All four
firmware images built with Pico SDK 2.3.0 at
`98a542c1a62fb549ffb5d66a3e5892b06276b670`, Arm toolchain 15.3.1, Release,
Pico 2 W and 138 MHz physical clock. ELF symbol inspection confirms the standard
image contains no physical Pico PIO/DMA launch implementation.

| Image | SHA-256 |
|---|---|
| Standard inhibited | `0636397544da1b5dc950dc56b028ac7a7d61ee8d6466a661d8b6ea6cb227efa3` |
| StandaloneRF | `2b24f7b184caf70687fa4ca89988e5ec04603b30276b306ea97b3a3e8d0c215d` |
| RFWTP | `1728d8620cb40c848386aff971e7fa1f826c1232e6f7cbc4100c5278cc62093a` |
| RFBench | `79452eff5fc42d375482af7470f85720ec3b7698c0fc8aa648d967811b766d4b` |

The standard and StandaloneRF images are staged on wspr5 at
`/home/pi/phase10-wtp-acceptance/`. Generated firmware and raw IQ are not tracked.
At that earlier target observation, source `3bccf7339afa` was still running
with state `failed`, output inactive, zero launch/DMA counters and persistently
disabled autonomous scheduling. Its local STOP/reboot idle guard refuses that
fault state. A physical Pico USB power cycle is required; do not clear or bypass
its fault latch through a remote ownership request. The user has been asked to
reconnect only the Pico USB cable. RF acceptance is paused pending that action.

After reconnection, recheck serial/device/boot and inactive disabled scheduling;
flash and verify the staged `8b26cad0fccb` StandaloneRF image. Repeat the bounded
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

## Source reassessment before resumed target testing

Adversarial inspection found that a leap transition announced after ARM also
needed the early timer adjustment included in the prelaunch exclusion check.
That check is repaired. Regressions now cover the exclusion boundary at
admission and after ARM, as well as budget growth and missed ticks. All 25 host,
17 sanitizer and 16 tests per alternate profile passed again. Source
reassessment found no further actionable defect in the changed paths.
All four final firmware images were then rebuilt from clean source
`8b26cad0fccb`. The image table above contains their final hashes. A generated
`final-firmware-manifest.json` under the local target-acceptance build directory
and on wspr5 records source, UF2/ELF hashes and physical-engine symbol checks.
No successful conducted run is claimed for this final image.

## Resumed target attempt on 2026-09-08

After the user-confirmed power cycle, source `8b26cad0fccb` StandaloneRF was
flashed and verified. New boot `fe39543cc9dcc0d698f11a2f12add15c` acquired SNTP
within the unchanged 500 ms budget; scheduling remained disabled. GPSDO outputs
were off, RP1 passed its maintained idle predicate, and the installed host
release identity remained unchanged.

The finite Tone now accepted LOAD and ARM, including the final-off marker and
fractional timestamp. The device reported launch and 42 DMA IRQs, then latched
a streaming failure. Host cleanup remained blocked; independent Console INFO
confirmed output inactive. The requested five-second Tone did not complete.
Receiver capture and cleanup succeeded with zero overflow/clipping, but offline
acceptance found no complete uninterrupted five-second burst. The failed case
is retained in `evidence/rf-tone-3/`; IQ SHA-256 is
`59b4de0e24b18e9bdeaaf0cf595ed200f72f89e3bf8836ea34894349ea23569a`.

The recorded `state_changed` sink diagnostic masked the preceding interrupt
fault. The sink now preserves its first named cause through subsequent failed
refill attempts and disable. Regressions cover that retention. StandaloneRF
INFO adds maximum running-loop, refill, USB-service and request-processing
times in microseconds; these are diagnostic observations, not calibrated timing.
The streaming root cause is still under investigation and is not claimed fixed.

Explicit Console REBOOT/BOOTSEL gains a guarded local recovery path for an
unowned failed state with inactive output, healthy storage and persistently
disabled scheduling. Engine disable and inactive verification remain mandatory.
WTP remote fault semantics are unchanged. Tests cover active output, enabled
scheduling, foreign ownership, lease expiry, and preservation of the fault latch
when merely querying reset eligibility.

A second Pico power cycle has been requested because the currently running
`8b26cad0fccb` image cannot perform this local fault recovery. After that action,
load the diagnostic build and repeat only the bounded Tone until its failure is
understood. Do not proceed to keyed/WSPR acceptance or mark Phase 10 complete.

The user confirmed that second power cycle. Boot
`ad86ace3b53d0088a866547772c8b73c` was verified empty/inactive with scheduling
disabled. The diagnostic/recovery changes passed all 25 host tests, 17 sanitizer
tests and 16 tests at each alternate clock. Source adversarial review checked
first-fault retention, owner/active/schedule guards and the delayed reset path;
no further actionable issue was found in that slice. The streaming defect itself
remains open pending target diagnosis.

## Current checkpoint: request servicing and RF baseline

Diagnostic source `6b413c156328` ran under boot
`d2c60ccb0e9dfb6e0f1aef547bd3c3d4`. Attempt `rf-tone-4` retained the first
failure as `pio_txstall` after 13 DMA IRQs, with output inactive. Maximum observed
request handling was 2546 us and refill was 2238 us, against approximately
3799 us per buffer. These maxima identify competing foreground work; they are
not a calibrated worst-case execution-time bound. Independent burst acceptance
also failed. The complete failed capture and device snapshot are retained.

The endpoint had no service point inside complete request processing. Source
`6c83982aca3a96582347cda770043e20d4f674df` polls the job service between JSON
parsing, request decoding, dispatch and response encoding. The outer loop still
services disconnected and backpressured execution. Immutable response snapshots,
replay, ownership and fault handling remain unchanged. A wire regression advances
an active job to completion through request receipt without an outer-loop poll
and verifies both the response and terminal event.

All 25 host tests, including actual WsprryPi client interoperability, and all
17 sanitizer tests passed. Validation used the build/CTest commands above for
`build/phase10-host` and `build/phase10-sanitize`; logs are retained under
`/private/tmp/phase10-cooperative-*.log`. Formatting and diff checks passed.
Adversarial reassessment checked clock progression between stages, replayed
snapshots, terminal-event ordering, malformed requests, lost connections and
local reset authority. No additional actionable source defect was found in this
slice. Large/adversarial traffic and long-duration physical operation are not
qualified by the finite Tone test.

The guarded Console BOOTSEL recovery succeeded from the inactive failed state
without another physical power cycle. Both current images were built from clean
source `6c83982aca3a` with the pinned inputs recorded above:

| Image | UF2 SHA-256 |
|---|---|
| Standard inhibited | `4299da07ef64556c007b40d2087c3f4dfc9511d8824fd1224c4fecea2a805a47` |
| StandaloneRF | `1574bcefae34c85555d84b1d64b79fb788c17d84b5d57cf8295966df6b6bb8ca` |

ELF symbol inspection confirms the physical engine is absent from the standard
image and present in StandaloneRF. The updated `final-firmware-manifest.json`
contains only these two current images; the earlier four-image manifest is
retained as `firmware-manifest-8b26cad0fccb.json`. Both are in the local
`build/phase10-target-acceptance/` directory and staged acceptance root on wspr5.

Attempt `rf-tone-5`, boot `c121fbc98092a9b25a43eac96378e9bf`, completed the
real host's five-second Tone and authoritative cleanup. Job ID was
`fef5dc7fcd89f5ec0000000000000001`, requested start UTC
`1788864169005494198` ns. The Pico recorded 1318 DMA IRQs, no engine/sink fault,
maximum refill 1681 us and maximum request duration 6004 us (now including
interleaved service calls). The source-bound host lifecycle passes; independent
RF acceptance does not. Capture SHA-256:
`ec69b490a2a1cbf38c977d8981e420140d8a172a1499f79059d67c9cac5bf449`.
Receiver cleanup, sample count/hash and zero overflow/clipping checks passed.
An initial analysis invocation preceded capture metadata completion and failed;
its log is retained separately from the completed-capture analysis.

The completed-capture analyzer found no qualifying uninterrupted burst. Offline
spectra show a strong carrier near 137501 Hz both before and after the commanded
job. The independent quiet-baseline gate was preserved; no threshold was relaxed.
Read-only checks reported both GPSDO outputs disabled and the RP1 maintained idle
predicate passed. No other transmitter/receiver process was found beyond the
installed inactive host daemon. This does not identify the physical carrier source.

The Pico was restored to the standard inhibited image and a ten-second
receiver-only baseline captured with identical receiver settings. The carrier
persisted near 137501 Hz at seconds 1, 4 and 8. Evidence is in
`evidence/rf-inhibited-baseline/`, including `baseline-analysis.json`; IQ SHA-256:
`06cc0982d5f5dc347ed32de0527fe99b2a83ac534c0899d42994ff370823fd17`.
Cleanup and hash checks passed. Receiver frequency remains uncalibrated.
Final Console observation is boot `f16780943aa7cb3a4e5c8294a6b41098`, source
`6c83982aca3a`, engine `inhibited-standalone-simulator`, state empty, output
inactive and autonomous scheduling disabled. Station configuration and watermark
remain unchanged. The installed host service was left running; the separate
installed-release acceptance supervisor was not started.

Further RF cases are paused while the user identifies any remaining source from
the other test. Do not change the confirmed wiring or substitute a passing retry
for these records. Once the baseline is understood and quiet, repeat finite Tone,
then run real installed-release QRSS/FSKCW/DFCW ETE cases and three independently
decoded WSPR frames. Use new suffix `6` or later and recheck source/receiver/clock
identity and exclusive ownership. Restore the inhibited image afterward and
complete the final joint assessment. Phase 10 remains open; Phases 11–13 remain
planned.

## Receiver retuning check

At the user's request, the SDR center frequency was moved down and up by 10 kHz
while the Pico remained on the same inhibited firmware and boot. Four sequential
five-second captures used the unchanged receiver, rate, bandwidth, gain and RF
wiring; the final capture restored the original center frequency.

| Case | SDR center (Hz) | Carrier peak (Hz) | Offset from center (Hz) |
|---|---:|---:|---:|
| Baseline | 112500 | 137501 | 25001 |
| Down 10 kHz | 102500 | 137501 | 35001 |
| Up 10 kHz | 122500 | 137501 | 15001 |
| Restored | 112500 | 137501 | 25001 |

Peaks are from the average power of three one-second Hann-windowed FFTs per
capture, with 1 Hz bin spacing on the uncalibrated receiver frequency axis.
The strong carrier did not follow receiver tuning. At the shifted centers,
the old +25 kHz offset contained only much weaker peaks, approximately 58–60 dB
below the carrier in this diagnostic FFT comparison. This is consistent with a
fixed RF-frequency signal and rules against a simple fixed-offset tuning spur;
it does not identify its source or exclude every internal receiver artifact.

All four captures passed exact settings/device checks, sample count and hash
verification, zero overflow/clipping and verified cleanup. Evidence and per-file
hashes are retained in `evidence/receiver-retune-carrier/results.json` on wspr5.
The receiver was closed after the final capture. No RF output, firmware change,
physical wiring change or scheduling change was made in this check. The quiet
baseline gate remains open.

## Clear-channel closeout and WSPR timeline finding

The user authorized completing the remaining acceptance at a nearby clear
conducted-test frequency. The execution prompt was rewritten around final
acceptance and closeout. A fresh inhibited capture found the 135500 Hz test
channel approximately 62 dB below the old carrier in the diagnostic FFT screen.
The wiring, receiver center/rate/bandwidth/gain and inactive reference sources
remained unchanged. Identifying the QRM source is no longer a completion gate.

On firmware 6c83982aca3a, final inhibited checks through the installed release
passed clock-budget rejection, armed/running cancellation and exact-interface
USB disconnect/reconciliation. These records have a `closeout-` prefix. The
clear-channel five-second Tone (`rf-tone-6`) passed the real host lifecycle,
authoritative cleanup and independent RF/carrier acceptance. IQ SHA-256:
`c4b0fde9ed17638ea2e1b6e1bc6eaddd93a20184925754b15851be74e9a8ae2e`.
This result remains bound to that pre-fix image and will be repeated after the
WSPR timeline repair below.

Source review then identified the real WsprryPi compiler's independently
truncated 682666666 ns WSPR symbols. The original physical planner only accepted
nanosecond encodings of exact sample endpoints. An added real-client admission
regression reproduced LOAD rejection without hardware. This gap was masked by
the earlier synthetic cumulative-boundary and inhibited tests.

The planner now realizes each absolute endpoint at its nearest sample, retaining
all events and rejecting any that collapse to zero samples. It does not round
individual durations cumulatively. Boundary error is bounded by half a sample;
frequency consent/adjustments and immutable WTP requests are unchanged. The
terminal already-low marker retains upward padding. Tests check all 162 real-host
symbol endpoints, both rounding directions and collapsed-event refusal.

Adversarial assessment found two dependent checks to update: completion must
use the realized sample endpoint, and the local leap guard must include that
endpoint. Both are repaired, with lifecycle and leap-edge regressions. Local
fault recovery, ownership, missed-start checks and output inhibition are retained.
The hardware granularity is documented in rf-stream.md; it is not a calibrated
GPIO timing claim. No host source change or protocol schema change is needed.

The user's original host checkout advanced independently during this work.
Pinned client validation correctly refused it. Tests now use a separate detached
checkout of the original reviewed 2819f0b source, preserving the user's checkout
and the installed e95932f host identity. This is test dependency isolation, not
an upgrade or rollback of the installed application.

## Source 23376c2 acceptance campaign

Clean source `23376c296c7d4220bebe58763f9fe2f151439a76` passed 25 host tests,
17 sanitizer tests and 16 tests at each of 132 and 150 MHz. Second adversarial
assessment found no further actionable issue in the repaired boundary,
completion and leap checks. All four firmware targets built with the same
pinned inputs as earlier. Final standard image SHA-256:
`b55a4944d4e7e012b74de764f409304aaba11162911f54e2f3ffccff2c77a988`.
Final StandaloneRF image SHA-256:
`337a5270a5627c12864a434f1a15a2306ce447de2193b5fbf3503dc51719bc3c`.
The final four-image manifest records ELF hashes and physical-engine symbol
checks; the preceding 6c83982 manifest is archived separately.

The verified RF boot is `9a5146113f3a453b30cf40ca8b8e36b7`. It retained the
configured station and disabled schedule. The actual installed release remains
`e95932feebc44d84988c96df969c8f8203ed8c1c`, executable SHA-256
`f5759b678b668caa9a639430fcd9b54066a06be0107a58e3e8e8d90d5dca1bfb`.
The private bounded supervisor starts `/usr/local/bin/wsprrypi` directly using
the isolated acceptance INI and restores the original service in its finalizer.
Tone uses the real host application/client and compiler through its separately
built finite driver. Installed-release keyed/WSPR jobs use the private HTTP API.
No product host source changes were made during this closeout.

| Source 23376c2 mode | Independent result | Capture SHA-256 |
|---|---|---|
| Tone | Pass; 5.000 s burst and carrier acquisition | `3336a090fcca3f95bdebadbc8c035ceeca4c7784a0d7dd796802f6afc34d8785` |
| QRSS ETE | Pass; 3/9/3 s marks and 9 s character gaps | `b919caeea08bb9da62eb320f29451b8710724e423ff5a43b438b228def0c8d3b` |
| FSKCW ETE | Pass; 33 s continuous envelope, 5.013 Hz separation | `e489f110ccf22d38b44822af7669593d68926b66c467110245c9e3fbc122c594` |
| DFCW ETE | Pass; equal 3 s marks/gaps, 5.012 Hz separation | `51f4dd3511f4de678d15831601ed254f3bd3fd311fdbec519bc8c83f6fa67fca` |

All four host lifecycles completed with authoritative inactive cleanup. Every
capture passed exact receiver settings/device, sample count/hash, zero overflow
and clipping, and verified cleanup. Independent analysis retained leading/trailing
quiet and used unchanged acceptance thresholds. Evidence is in the respective
`evidence/rf-<mode>-7/` directories; installed-release JSONL records sit beside
them. These are operational results for this conducted frequency and exact build,
not on-air band coverage or calibrated timing/power/emissions qualification.

The WSPR host setting is dial 134000 Hz, which produces center 135500 Hz with
its configured 1500 Hz offset. Canonical WSPR symbols are centered around that
frequency, so independent analysis uses lowest tone 135497.802734375 Hz. This
mapping was reviewed before capture; no post-hoc frequency or drift correction
is applied to obtain decoding. Three-frame results and final restoration follow.

## Consecutive WSPR clock-refresh finding

The first full WSPR job on 23376c2 completed with authoritative inactive cleanup.
The next job was refused before ARM with `WTP device clock is not admissible`;
its report confirmed no ARM handoff and successful cleanup. This is a failed
three-frame campaign, retained as `evidence/rf-wspr-7/` and its adjacent JSONL.
The first job started at UTC nanoseconds 1788867121000000000; the refused next
slot was 1788867241000000000. Console diagnostics showed no DMA/sink fault and
an unsynchronized clock with a 221.6 s old sample. Subsequent ordinary polling
recovered synchronization without a reset.

RF deliberately defers network polling throughout a frame. Previously a lost
first post-frame SNTP exchange waited another 64 s, missing the 9.408 s interframe
refresh opportunity. The network adapter now retries twice at 2 s intervals,
then backs off for 64 s. Only a correlated accepted observation restores the
normal 64 s polling interval. Link restoration resets the retry schedule; a
server's KoD denial remains effective for the boot. No clock uncertainty, age,
RTT, leap or ARM gate is relaxed, and network polling remains deferred during RF.

Adversarial assessment checked stale/replayed responses, sustained loss, send
allocation failure, link recovery, monotonic reversal/overflow and server denial.
The regression includes a delayed pre-frame response, a lost post-frame request
and a stale response to that request followed by a valid retry response. Only
the valid correlated response restores synchronization. The second assessment
found no additional actionable issue. All 25 host and 17 sanitizer tests pass.
Live acceptance must still establish that this policy recovers in the actual
interframe window; the software regression alone does not close that gate.

The retained first WSPR capture independently decoded with no measurement issues:
SHA-256 `873898b1e79a0004e22e4ec5f61a586c0ef350eb112eb04c246d7c53fb9e3d0f`,
interval 69.950–180.542 s. Its separate `partial-frame-analysis.json` explicitly
marks the three-frame campaign failed. No passing retry replaces this evidence.

## Clock-retry source acceptance

Clean source `1ec70e7c891cfcb4d40ee1c929232989fce86db5` contains the reviewed
retry policy. All 25 host and 17 sanitizer tests passed after the added real-SNTP
correlation/recovery regression. All four firmware targets were explicitly built:

```sh
cmake -S . -B build/phase10-target-build
cmake --build build/phase10-target-build --target WsprryPico WsprryPico-StandaloneRF WsprryPico-RFWTP WsprryPico-RFBench --parallel 6
```

The RF targets are excluded from the default build. A pre-flash artifact check
caught that the first default-only build left their older binaries untouched;
all were explicitly rebuilt and their embedded 1ec70e7c891c revision verified
before flashing. ELF symbol inspection again confirmed physical launch is absent
from the standard image and present in the three explicit RF targets. The final
manifest replaced the preliminary mixed-build manifest before any RF flash/test.

Standard UF2 SHA-256:
`3704ab866d4a852fa82f47362a2f7b39ff30a99fce52a4db8d9debd64dde30d3`.
StandaloneRF UF2 SHA-256:
`0479f4b9dc97983fab3c55433ff791eef8b5bab1beb851ffb4df388859a0d189`.
RF boot: `4bf3d65518da3fc4c1674ceafdfd6df5`. Station settings, disabled scheduling
and watermark were retained. Source 23376c2's manifest is archived separately.
All final-source captures use suffix `8`; exact receiver, path, installed host,
mode settings and acceptance thresholds are unchanged from the preceding run.


## Local launch STATUS race

On 1ec70e7, Tone, QRSS and FSKCW passed again. DFCW emitted only 75 ms before
the host latched a remote safety fault and aborted. Evidence remains in
`evidence/rf-dfcw-8/` (IQ SHA-256
`9e498e07454d0b19f38c09ba85812f716fe9da43cc562f96f244596baf331d9c`).
This is failed acceptance, including the host's blocked cleanup. Console later
confirmed output inactive, aborted state and no engine/sink fault. The bounded
supervisor restored the original installed service; no subsequent RF was started.

Source analysis identified another launch boundary race: the local timer can
assert physical output after the foreground poll captured Armed/inactive, before
STATUS separately reads live output. That mixed observation is Armed/active,
which correctly latches the real host client's safety fault. The deterministic
regression reproduces that exact ordering and failed on the old implementation.

STATUS now reports Running when live output establishes launch of the current
locally scheduled Armed job. It samples output once, retains actual output truth,
and does not change job authority, launch timing, immutable ARM replies, terminal
completion, shutdown or host safety checks. Nonlocal Armed/active and Failed/active
observations remain visible. Terminal/fault processing still runs through the
engine report and verified disable path. Tests cover both local/nonlocal engines,
initial inactive Armed state, the interrupt gap, immutable STATUS responses and
subsequent active/inactive failure observations. The existing real PIO sink test
already fires its launch interrupt at snapshot-unlock and verifies a coherent
engine report; this regression closes the additional job-service observation gap.


Second adversarial assessment found no further actionable issue in the STATUS
repair: it applies only to a retained locally scheduled Armed job with physically
active output, cannot turn Failed into Running, and does not report inactive
output or terminal success. The host remains unchanged. All 25 host and 17
sanitizer tests pass after the active-failure regression; formatting and diff
checks pass. Repeat target acceptance is required on this exact repaired source.
