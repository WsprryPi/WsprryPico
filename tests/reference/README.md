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

INFO-only mapping pairs are labeled unbound numerical consistency. Separate
management API receipts must establish active NTP authority, application and
μChrony generations, and the actually applied rate at each new bracketed point.
A later authority check cannot retroactively bind earlier observations.


For the same-input source-estimator comparison on actual saved Pico originals:

```sh
python3 tests/reference/replay_chrony49_capture.py "$receipts"
```

The command verifies the existing capture and binary hashes and writes
`captured-source-comparison.json` in that private directory. It uses normalized
scalar observations and the existing portable host stats profile, not the full
Pico profile or a complete daemon feedback loop. Source-fit agreement is not an
independent accuracy measurement. The results document records the divergences.
