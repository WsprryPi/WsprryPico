# Phase 10 joint target review

Status: in progress. Phase 10 is not complete until the remaining conducted RF,
installation/service and final delivery gates have evidence.

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
