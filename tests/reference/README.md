# External Chrony 4.9 reference

μChrony is retained for UTC discipline. NTP RF calibration and the live
Pico-to-Pi GPIO pulse path are retired; existing captured-input tools operate
on historical files only. See the [closeout](../../docs/development/ntp-work-closeout.md).

These original MIT drivers keep the external GPL reference separate from
μChrony and the firmware. They download nothing, install nothing, adjust no
host clock, and perform no network or board operations. Keep upstream sources,
objects, reference executables and generated reports in private ignored build
directories. Preserve upstream licensing if distributing a reference binary.

The official [Chrony 4.9 release](https://chrony-project.org/releases/chrony-4.9.tar.gz)
archive used here has SHA-256
`4924c6f530105bcd5b9e9e33c48a2ae1bfd889222c8480bc41601110efc864d0`.
The independently obtained upstream tree was built with the existing host
toolchain and these options:

```sh
./configure --disable-readline --disable-sechash --disable-nts \
  --disable-cmdmon --disable-refclock --disable-rtc --disable-privdrop \
  --disable-ipv6 --disable-timestamping --without-nettle --without-gnutls \
  --without-nss --without-tomcrypt --with-ntp-era=1735689600
make -j4
```

## Reproduction

The recorded isolated validation uses the following existing external build.
Run from the WsprryPico checkout, after building its host tests. On
the recorded Mac, source `scripts/xcode_env.sh` before compiling. Assertions
must remain enabled; the comparison scripts reject Python `-O`.

```sh
source scripts/xcode_env.sh
reference=/Users/lbussy/GitHub/WsprryPico/build/ntp-statistical-20261018/chrony-4.9
receipts=build/microchrony-validation-20261018
python3 tests/reference/build_chrony49_oracle.py "$reference" "$receipts/chrony49-stats"
python3 tests/reference/build_chrony49_oracle.py "$reference" "$receipts/chrony49-control" control
python3 tests/reference/build_chrony49_oracle.py "$reference" "$receipts/chrony49-selection" selection
python3 tests/reference/compare_chrony49.py "$receipts/chrony49-stats" \
  "$receipts/host/microchrony_tests" "$receipts/stats-comparison.json"
python3 tests/reference/compare_chrony49_rules.py "$receipts/host/microchrony_tests" \
  "$receipts/chrony49-control" "$receipts/chrony49-selection" "$receipts/rule-comparison.json"
```

The linker helper checks the external version/license and hashes the existing
upstream objects, original harness and resulting executable. No upstream
source is linked into `microchrony`, `wsprrypico_core` or `WsprryPico`.

## Complete clock-control loops

`chrony49_loop.c` connects the unmodified external SST, SRC, REF, LCL and
SYS_Generic modules to an original in-process oscillator. It intercepts clock
reads and scheduler waits; its only IO is a private wake pipe and stdin/stdout.
Driver timeouts execute between physical events. The production μChrony engine
runs through `microchrony_loop.cpp`, registered as the host `microchrony_loop`
target. Identical raw oscillator ticks, server timestamps, path delays and loss
events drive both. Their resulting clocks feed subsequent measurements/control;
known truth scores actual UTC and pure frequency separately from phase slew.

The fixed polling schedule supplies four initial observations and then one
per source every 64 seconds. The Chrony adapter begins at the NTP sample API;
UDP parsing, authentication, packet admission and autonomous polling are outside
this comparison. All supplied replies pass production μChrony packet admission.
This tests the complete supported source-to-clock control path, rather than
only SST fits or an isolated phase helper. It does not certify the whole daemon
or a physical Pico/network clock.

With the existing external build and a configured host build:

```sh
receipts=build/microchrony-loop-20261018
python3 tests/reference/build_chrony49_oracle.py "$reference" "$receipts/chrony49-loop" loop
python3 tests/reference/compare_chrony49_loop.py "$receipts/chrony49-loop" \
  "$receipts/host/microchrony_loop" "$receipts/after.json"
python3 tests/reference/compare_chrony49_loop.py "$receipts/chrony49-loop" \
  "$receipts/host/microchrony_loop" "$receipts/quarter-second.json" --tick-s .25 \
  --cases noisy_frequency_step server_step_50ms heldout_ramp heldout_pool
python3 tests/reference/validate_chrony49_loop.py "$receipts/chrony49-loop" \
  "$receipts/host/microchrony_loop" "$receipts/after.json" \
  "$receipts/quarter-second.json" "$receipts/loop-validation.json"
python3 tests/reference/compare_chrony49_frequency.py "$receipts/chrony49-control" \
  "$receipts/host/microchrony_loop" "$receipts/frequency-update.json"
```

`test_microchrony_loop.py` provides ten known-truth CI cases without an external
reference, network or hardware. `plot_chrony49_loop.py BEFORE AFTER DIRECTORY`
uses installed gnuplot to plot raw truth errors from saved reports. The
[clock-loop record](../../docs/development/microchrony-clock-loop.md) specifies
the baseline identity, exact checks, results and remaining differences.

The adaptive-history/source-combination follow-up preserves the previous engine
and its comparison under ignored `build/microchrony-loop-20261018/adaptive-combination/before/`.
Its full comparison uses `--validation-seeds` for 25 four-hour traces. The CI
clock-loop test now checks ten known-truth cases, including three further pool
noise seeds and a majority with a falseticker; existing acceptance limits remain
and pool RMS checks are added.

`chrony49_combination.c` isolates unmodified SST/SRC objects by replacing only the
public REF output sink. It records every source estimate and the actual combined
arguments; it does not run the reference controller or prove daemon equivalence.
`compare_chrony49_adaptation.py` feeds those exact estimates to the production
combiner. It separately compares six 256-point histories through SST and Engine,
checking all active sample-count decisions and frequency differences. Timestamp
and measurement admission remain outside the scalar SST tests.

```sh
receipts=build/microchrony-loop-20261018/adaptive-combination
python3 tests/reference/build_chrony49_oracle.py "$reference" "$receipts/chrony49-stats"
python3 tests/reference/build_chrony49_oracle.py "$reference" "$receipts/chrony49-combination" combination
python3 tests/reference/compare_chrony49_adaptation.py "$receipts/chrony49-stats" \
  "$receipts/chrony49-combination" build/microchrony-loop-20261018/host/microchrony_tests \
  build/microchrony-loop-20261018/host/microchrony_loop "$receipts/adaptation.json"
python3 tests/reference/build_chrony49_oracle.py "$reference" "$receipts/chrony49-loop" loop
python3 tests/reference/compare_chrony49_loop.py "$receipts/chrony49-loop" \
  build/microchrony-loop-20261018/host/microchrony_loop "$receipts/after.json" --validation-seeds
python3 tests/reference/plot_chrony49_loop.py \
  "$receipts/before/build/microchrony-loop-20261018/after.json" \
  "$receipts/after.json" "$receipts/comparison" --adaptive
```

The optional `regression` harness calls only the public `RGR_FindBestRegression`
API. Its input is `n m minimum`, then `n+m` triples of x/y/variance weights;
output includes the resulting start index, active runs and degrees of freedom.
It supports independent diagnosis of sign-run thresholds and predecessor counts.
Setting `MICROCHRONY_DIAGNOSTICS=1` adds bounded per-update source diagnostics on
stderr for the loop drivers, or the public SST dump for the scalar driver.
The deterministic fixtures and process timeout bound this diagnostic output.
Each loop source diagnostic now includes its learned delay coefficient. The
reference coefficient uses local-minus-server phase; the engine's sign is the
opposite. The stdout protocol is unchanged.

`compare_chrony49_loop.py` also supplies three four-source variable-delay cases:
weak, forward and reverse queue asymmetry with known sub-ppm oscillator error.
The original ten CI cases and their limits remain; three further UTC/rate
acceptance cases exercise the new path-weighting and asymmetry behavior.
The [Internet diagnosis](../../docs/development/microchrony-internet-diagnosis.md)
records comparison results and the captured-pulse tradeoff.

For a privately retained completed pulse campaign, the pooled diagnostic checks
manifest hashes, stable board/boot/image/source identity and newly captured
original counts against that campaign's baseline. It keeps pre-capture deficits
explicit. Both controllers start with zero frequency correction and receive the
same retained original packets; this cannot reconstruct missing live history or
the Unix clock's different RTC acquisition. Physical pulse probes retain the
uncalibrated reference/path limitation. Full rows and diagnostics stay private.

```sh
python3 tests/reference/diagnose_chrony49_capture.py \
  build/microchrony-pulse-rate-rerun-20261018/terminal-evidence \
  "$receipts/microchrony-before" "$receipts/host/microchrony_loop" \
  "$receipts/chrony49-loop" "$receipts/pooled-replay.json"
```

## Packet admission and fixed-coordinate histories

The `packet` oracle runs the unmodified Chrony NCR request/reply parser,
correlation, validity and delay admission before observations reach SST.
Original deterministic IO, entropy, request-callback and clock-output adapters
replace external surfaces. It never opens sockets or adjusts the host clock.
Request times are supplied externally; autonomous polling and receive-timeout
policy remain outside this comparison. An omitted reply tests loss between
supplied requests, not the daemon's complete timeout policy.

```sh
python3 tests/reference/build_chrony49_oracle.py "$reference" "$receipts/chrony49-packet" packet
python3 tests/reference/compare_chrony49_packets.py "$receipts/chrony49-packet" \
  "$receipts/host/microchrony_loop" "$receipts/packets.json"
```

The reference first emits its actual request nonce and final offered wire reply;
the engine then receives those same bytes and raw send/receive events. Both
clock outputs are frozen for this admission comparison. Repeated oracle runs
must produce identical wire transcripts. Fixtures cover correlation, duplicates,
stale transmit timestamps, loss, malformed lengths/modes, era rollover,
unsynchronized sources, processing delays, queue directions and innovations
larger than a queue can explain. Expected stricter Pico-profile differences
are asserted separately from unexpected mismatches. Source usability after
admission is a separate stage; an NCR good-packet count is not synchronization.

The `raw` adapters normalize retained admitted measurements to server midpoint
UTC and peer RTT with common precision/dispersion, fixing the clock coordinate
and holding output frequency. This isolates adaptive history and the learned
queue coefficient from coupled controller/cooked-clock trajectories. It does
not replay the original wire admission or reconstruct missing boot inputs.
The cohort report must first pass manifest, identity and baseline checks.

```sh
python3 tests/reference/build_chrony49_oracle.py "$reference" "$receipts/chrony49-stats"
python3 tests/reference/compare_chrony49_histories.py \
  build/microchrony-pulse-rate-rerun-20261018/terminal-evidence \
  "$receipts/pooled-replay.json" "$receipts/chrony49-stats" \
  "$receipts/host/microchrony_loop" "$receipts/histories.json"
python3 tests/reference/compare_chrony49_ablations.py \
  0a7c05d1c41b7fd261db50a6fa267c4004e0c6e8 "$receipts/ablations"
python3 tests/reference/compare_chrony49_rate_benefit.py \
  "$receipts/chrony49-loop" "$receipts/host/microchrony_loop" "$receipts/rate-benefit.json"
```

Ablations transform only owned MIT code and retain generated source/compiler
and binary receipts privately. The weighting-only variant retains the baseline
asymmetry rules; the asymmetry-only variant retains root-distance weights.
The asymmetry factor includes its covariance and predecessor-horizon rules.
`phase` supplies ordinary six-column known-truth inputs with frequency updates
suppressed by a tighter offline maxupdateskew. Phase damping remains active.
The simulated alternative is scored against known truth; it is different from
a physical open-loop forecast over a short unchanged application model.

`captured` and `captured-phase` now explicitly disable the engine's additional
delay classifier in the test adapter because Chrony's corresponding adapter
enters after that classifier. Production admission remains exercised by the
separate `packet` comparison. `captured-rtc` gives both test clocks the same
synthetic initial RTC prior at the translated first-sample origin. That is a
controlled conditional prior, not a recovered live RTC or boot history.

## Offered packet diagnostics

### Closed lead-layout capture

The completed October 19 lead-layout run uses a retrieval manifest and a stable
post-RF accepted frontier. The replay supports those without rewriting the
closed evidence. Use the original manifest digest, a preserved before binary
and the newly built `microchrony_loop`:

```sh
receipts=build/microchrony-lead-replay-20261019
evidence=build/microchrony-lead-layout-20261019/terminal-evidence
engine=build/microchrony-conformance-20261019/host/microchrony_loop
python3 tests/reference/diagnose_chrony49_capture.py "$evidence" \
  "$receipts/microchrony-before" "$engine" \
  "$receipts/chrony49-loop-instrumented" "$receipts/pooled.json" \
  --segment pulse-history --manifest retrieval-manifest.json \
  --manifest-sha256 43a7609f74d14780c4802bef6fdc88f285b7d3bebefd8291272210059e3cc80a \
  --matched-rtc
python3 tests/reference/compare_chrony49_captured_packets.py "$evidence" \
  "$receipts/chrony49-packet" "$receipts/microchrony-before" \
  "$engine" "$receipts/packets.json" \
  --manifest-sha256 43a7609f74d14780c4802bef6fdc88f285b7d3bebefd8291272210059e3cc80a
python3 tests/reference/compare_chrony49_histories.py "$evidence" \
  "$receipts/pooled.json" "$receipts/chrony49-stats" \
  "$engine" "$receipts/histories.json"
python3 tests/reference/analyze_chrony49_path_bias.py "$evidence" \
  "$receipts/pooled.json" "$receipts/histories.json" "$receipts/path-bias.json"
```

The commands name the retained after executable; configure a fresh host build
as above when reproducing elsewhere. Source-API diagnostics (`C` for conditional engine errors and
`S` for external selection distances) describe weights, not independent truth.
The packet replay translates a common UTC origin and regenerates correlation
nonces; both implementations receive the resulting identical bytes. It preserves
original intervals and body quality fields, requires full retained basic packets
and reports differences from live verdicts separately from reference disagreement.
Missing boot state, autonomous polling and combined clock feedback are outside
that frozen-output boundary. The [result record](../../docs/development/microchrony-lead-replay-results.md)
retains the adverse source/path bias and incomplete pre-capture visibility.

`NTP PACKETS <cursor>` is a read-only USB Console command. Start with cursor
`0`, verify device/boot/firmware/revision, then use the returned decimal-string
`next_cursor`. Drain while `more` is true. Each response holds at most four
records and stays within 4,096 bytes; the separate ring retains 32 records.
Integer IDs, epochs, request/receive times, tokens and opaque endpoint identities
are decimal strings. `slot`, datagram `length` and booleans are ordinary JSON
values. The endpoint is the engine's opaque configured identity; a live INFO/
history source-cohort receipt supplies the corresponding network address.

Records retain immutable sequence/slot/endpoint/epoch, the most recently emitted
request timestamp/token for that cohort, receive raw time, accepted verdict,
reason, original datagram length and its first 48 bytes as lowercase hex.
The successful reason is `accepted`. Request metadata is cleared on cohort
reset; its presence alone does not establish a still-pending correlated request.
`truncated` explicitly marks longer datagrams, which cannot pass basic-packet
admission. Unknown address/port drops before association matching are excluded.
No authentication secrets or Wi-Fi credentials are logged.

`oldest_id`, `last_id` and `overwritten` describe the ring. `lost_before`
reports records between the requested cursor and its surviving first record.
Record an initial deficit as pre-capture missing evidence; a later gap forbids
a complete-visibility claim. Do not compare retained ring length with whole-boot
packet counts. Peer/reset changes preserve already logged identities and start
new source epochs; a cold boot changes the surrounding boot identity.

`src/rf_analysis/ntp_packets.py` validates pages transactionally without IO.
The caller saves the original response before validation and enforces finite
time/disk budgets. Its regression consumes pages emitted by the actual C++
`NtpClient` producer, including rejection and overflow. The library does not
invent raw bytes lost before collection or beyond the recorded prefix.

## Tested boundaries

The statistics comparison feeds eight identical 64-point timestamp, offset,
delay and dispersion streams through the public SST API and μChrony. Packet
delay admission is disabled in both drivers because SST receives measurements
after that stage. The cases cover both drift signs, zero drift, stationary
noise, both queue directions, drift change and correlated delay. Stationary
and queue cases have independent numerical tolerances. Drift-change recovery
must discard obsolete history and recover within eight admitted observations.
The correlated-delay case preserves μChrony's full joint covariance and must
cover the injected rate; a smaller upstream skew is not a reason to shrink it.
All rows, differences, inputs and executable hashes are retained.

The control driver invokes the unmodified public `REF_SetReference` API and
actual generic clock driver with private dummy clock operations. An in-process
pipe advances scheduler event time; timeout callbacks alone do not do that.
The 160 cases check correction-time calculation, signs, irregular intervals,
maximum slew and the one-second minimum correction duration. These are
phase-control rule tests, not a complete differential test of frequency
combination or the complete daemon servo.

The selection driver invokes the public SRC APIs with identical source data.
Its five traces check final choices for agreement, disagreement, stratum,
withdrawal and hysteresis, including the tested exact hysteresis switch event
and two numerical scores. Reports explicitly list startup rows with different
selected choices. The reference uses `maxunreach 0` for the bounded reach-loss
profile; this is not Chrony's default association lifetime. These checks do
not assert all-row selection equivalence.

Adaptive pruning, transient frequency, covariance and startup selection can
differ. Complete packet-admission, daemon selection/servo and leap-execution
equivalence remain unproven. The recorded upstream unit run passed 16 tests,
skipped nine and failed the socket test on the Mac; it was not a clean upstream
suite. The [results](../../docs/development/microchrony-results.md) describe
these limits and separate software checks from live application and RF claims.

## Captured NTP consistency

`analyze_microchrony_capture.py` validates private bounded USB history identities,
image/revision, token SHA, cursor coverage and immutable originals. It compares
per-slot visibility with accepted packet counters and replays each source
causally against its next original. Identical preceding inputs and common
available holdouts separate phase damping from learned-frequency benefit.
A later NTP reply is a consistency proxy, not independent absolute UTC truth.
The single-source counterfactual does not recreate target pool combination.

```sh
python3 tests/reference/analyze_microchrony_capture.py \
  "$receipts/live" "$receipts/host/microchrony_tests" "$receipts/live-analysis.json"
```

INFO-only mapping pairs are labeled unbound numerical consistency. When
management API/INFO/API brackets are present, the analyzer independently checks
active NTP authority, device/boot/image identity, stable application and μChrony
generations and the actually applied rate. The stored observer verdict does not
establish authority. Stable bound segments verify numerical application of the
reported rate. Finite-slew transition pairs are recorded separately because
INFO does not export the exact endpoint. A later authority check cannot bind
earlier observations.

Stable capture baselines separately identify missing pre-capture history and
require exact visibility of every newly accepted original. Whole-boot coverage
retains its original meaning. With a private, validated first-phase capture:

```sh
python3 tests/reference/test_capture_analysis.py "$receipts/live" \
  "$receipts/host/microchrony_tests"
```

The negative checks use temporary fixture links and leave the originals intact.
They reject an unsupported authority claim and a missing newly accepted input.

`compare_chrony49_captured_loop.py` replays each captured source through the
complete supported clock-control paths. Both adapters receive identical raw
send/receive ticks, server receive/send/reference timestamps, root delay,
dispersion, precision, stratum and leap fields. A common translation selects
an arbitrary UTC origin; no independent oscillator or UTC truth is introduced.
Each scored probe precedes admission of its own NTP reply. The comparison keeps
the existing 500 ms clock-error and 90-second age limits on common synchronized
probes. The external reference still enters at the NTP sample API.

```sh
python3 tests/reference/test_captured_loop.py "$receipts/host/microchrony_loop" \
  "$receipts/chrony49-loop"
python3 tests/reference/compare_chrony49_captured_loop.py "$receipts/live" \
  "$receipts/host/microchrony_loop" "$receipts/chrony49-loop" \
  "$receipts/live-analysis.json" "$receipts/captured-clock-loop.json"
```

The captured mode is an optional adapter argument; existing deterministic loop
inputs and output columns remain unchanged. The additional capture output fields
carry reported clock error and raw sample age. `captured-phase` suppresses
frequency updates only for an offline counterfactual; it changes no production
gate. The comparison scores μChrony's phase-only and full loops against full
Chrony. A Chrony phase-only control with suppressed frequency updates can retain
large clock uncertainty and is excluded from this qualified comparison.
An offset-only baseline holds the last admitted midpoint's UTC offset, using
the supported 100 ppm drift envelope. It shares the same age/error limits and
common probe set. The reference RTC initially shares the first sample's UTC
coordinate origin; μChrony acquires its epoch from a usable fit. That difference
remains in the conditional replay trajectory. A common coordinate translation
does not remove acquisition effects or reconstruct missing boot history.

The validated input manifest and stable per-slot capture baselines are required.
Raw baseline receipts independently confirm the initial accepted and captured
counts. Every new accepted original must be visible, including across source
cohorts; pre-capture gaps remain explicit. Separate cold source replays omit
persisted seeds, previous rejected packets and live pool combination, and do
not establish absolute UTC accuracy or live application-clock authority.

For the finite A/B crossover, the derived engineering record and figure are
reproducible from the verified private evidence and the two phase analyses:

```sh
python3 tests/reference/summarize_microchrony_live.py "$receipts/full-evidence" \
  "$receipts" docs/development/microchrony-live-comparison.json
python3 tests/reference/plot_microchrony_live.py \
  docs/development/microchrony-live-comparison.json \
  docs/development/figures/microchrony-live-convergence.png
```

The plot uses an already installed gnuplot. Its frequency estimates and
uncertainty curves are not measurements of residual oscillator error.


For the same-input source-estimator comparison on actual saved Pico originals:

```sh
python3 tests/reference/replay_chrony49_capture.py "$receipts"
```

The command verifies the existing capture and binary hashes and writes
`captured-source-comparison.json` in that private directory. It uses normalized
scalar observations and the existing portable host stats profile, not the full
Pico profile or a complete daemon feedback loop. Source-fit agreement is not an
independent accuracy measurement. The results document records the divergences.
