# External Chrony 4.9 reference

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
coordinate origin; μChrony acquires its epoch from a usable fit. This excludes
RTC/boot acquisition from the accuracy comparison.

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
