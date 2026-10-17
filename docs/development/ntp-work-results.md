# NTP work results

Executed 2026-10-17 under the [saved prompt](ntp-work-execution-prompt.md).
Only consolidated backlog item 4 is selected. Software checks and linked
images do not establish physical UTC accuracy, carrier calibration or symbol
timing. The [evidence manifest](ntp-work-evidence.json) binds the final inputs,
test outputs, image identities and actual live budget.

## 1. Persistent standalone manual PPM

Configuration stores signed integer `manual_correction_ppb`, default zero,
bounded inclusively to ±100000 ppb. One ppm is 1000 ppb. The independently
advertised `transmitter-rf-calibration/1` resource at
`/api/v1/rf-calibration` presents a decimal **string** with at most three
fractional digits, canonical readback with three digits, and no exponents,
nonfinite values, whitespace, coercion or clamping. Positive means the Pico
source runs fast: +10.000 ppm selects +10000 ppb and reduces the NCO increment.
This is carrier correction; UTC acquisition, symbol sample counts and measured
RF power remain separate.

GET returns exact member/boot target, saved manual value/mode, storage health,
next selection and prepared selection/provenance. PUT requires the same target,
current `If-Match`, supported schema and existing authenticated management or
local USB physical authority. The body is
`{schema,target,calibration:{manual_ppm,mode}}`; modes are `manual` and `ntp`.
The settings form requires explicit saved-state readback before editing and
preserves the entry after an uncertain reply. Saves require idle/unowned state;
no save programs hardware, starts a job or establishes readiness. Configuration
must already exist; independent saved-progress schemas are unchanged.

The existing atomic 2048-byte journal and 1800-byte configuration ceiling are
unchanged. Nonzero/manual or automatic-mode records contain optional extension
fields; default zero/manual retains legacy canonical bytes. Old firmware that
does not recognize a nondefault extension rejects the record and fails closed;
it cannot safely downgrade and silently discard calibration. A deliberate
supported complete replacement/reset returns zero/manual. Legacy CONFIG,
legacy PUT and merge omission preserve both settings. Profile/network overlays
copy the underlying configuration and preserve them. No poll writes flash;
learned values are volatile. Page interruption tests distinguish an untouched
previous record from a torn record, which fails closed.

`FrequencyPolicyEngine` selects before every admitted preparation for all job
producers. It enforces adjustment consent even for an engine that would ignore
it, and validates all reported realized frequencies against the same policy.
The engine's prepared plan stays immutable. Type 2/3 scheduling explicitly
freezes the selection across both LOADs, including candidate-health changes.
Ordinary later jobs under one persistent owner select anew. Requested frequency,
reported realized NCO frequency, saved correction and prepared correction have
distinct meanings. A host supplying precompensated frequencies must select
zero/manual on the Pico or refuse frequency adjustment; WTP/1 has no field
that identifies an independently precompensated frequency.

## 2. NTP filtering and UTC rate discipline

`NtpSample` records observation ID, source/clock epoch, actual raw send/receive,
estimated receive UTC, uncertainty, full RTT, server reference/receive/transmit
timestamps, root delay/dispersion, precision, stratum and leap. Network status
supplies configured peer and resolved endpoint. The separately advertised
`transmitter-ntp-observations/1` GET resource binds those records to member,
boot, firmware/build revision, nominal RF clock and software-model generation.
Image SHA-256 association is supplied by the external acquisition/build
manifest, not manufactured by firmware. Packet admission, filter selection and
arbiter acceptance/anchor ID are separate fields. `last_accepted_measurement`
retains its identity when a later packet is rejected; aggregate counters and
latest RTT are not anchor evidence.

The correlation nonce remains a wire token, never UTC T1. Receive UTC is
`T3 + (raw_RTT - (T3-T2))/2`, floored to the local offset grid. The original
full RTT + root-distance + 1.050999 ms bound remains; local receive/processing
delay stays inside RTT. Peer/port checks, malformed/correlation/replay/stale
rejection, server processing checks, supported 2025–2099 era window/2036 wrap,
precision/leap policy, KoD stop and bounded 2/2/64-second retry/backoff remain.
Accepted packets restore the ordinary 64-second poll. Server discovery and
ranking are unchanged. This restricted client is informed by
[RFC 5905 sections 10–12](https://www.rfc-editor.org/rfc/rfc5905.html#section-10);
it does not implement or claim a full NTP daemon.

The filter has eight fixed samples and selects minimum RTT plus age dispersion
at 50000 ppb, with newer ties preferred. Its selection-age ceiling is **26 s**,
leaving one ordinary 64-second poll interval within the existing 90-second
launch-age budget. An exploratory 90-second selection policy lost availability
on rising-delay input and was rejected before final acceptance. A reused sample
retains its original ID, raw time and uncertainty; repetition cannot refresh
the UTC anchor. At normal 64-second cadence filtering alone is neutral. It can
reduce short-interval queue transients; it cannot discover constant asymmetry.

A separate 32-record history learns only from accepted raw SNTP observations.
Even records train conservative, outward-rounded pairwise slope intervals;
odd records are withheld for validation. Qualification requires all 32 records,
at least 1800 seconds, at most 7200 seconds per fitted interval, UTC-per-raw
rate within ±100000 ppb, uncertainty at most 5000 ppb, overlapping disjoint
windows 0–14 and 16–30, and at most 2000 ppb difference between their centers.
Every withheld interval must overlap the model including source uncertainty.
Network asymmetry and server quality remain in endpoint bounds; residual RMS
does not replace them. Gaps over 90 seconds, peer/clock epoch changes and
incompatible steps reset history. Invalid or unstable fits select unit slope.
Source disagreement rejects the model, clears learning and retains the existing
two-consistent-observation reacquisition policy. Controller/browser time never
trains the fit.

The mapping is `UTC = U0 + floor((raw-M0)*(1e9+rate_ppb)/1e9)` with an integer
rational inverse rounded toward the first raw nanosecond at/after requested
UTC, then upward to the microsecond alarm grid. Checked quotient/remainder
arithmetic avoids epoch-sized floating point, 128-bit target assumptions and
overflow. Uncertainty retains the full original measurement bound and original
50000 ppb growth, adds fitted rate uncertainty and fractional/rounding coverage;
it is not reduced because a fit is smooth. The clock remains synchronized
through 90 s, holdover through 180 s; launch age remains at most 90 s and
uncertainty at most 500 ms, subject to tighter job limits. A cold boot has no UTC.

ARM inversion, local launch reprojection/deadline and rounded UTC-window checks,
nonlocal/inhibited launch checks, arbiter intervals, expiry/leap duration guards
and pair mapping checks use the rate model. The RF core receives only the small
fixed phase/rate/uncertainty clock through its existing mailbox and IRQ masking.
Filter/history/fit/JSON work stays on core 0. A running waveform does not change.

The reproducible replay and independent Python `Fraction` oracle are in
`tests/ntp_work_tests.cpp` and `tests/ntp_replay_tests.py`. All three modes receive
identical deterministic observations and probes 32 seconds after measurement.
Traces cover constant/varying/asymmetric delay, explicit receive processing,
spikes, loss, duplicates, outage, phase/drift/source changes and signed rates.
The constant-rate ±20 ppm traces demonstrate improved held-out projection with
unchanged availability and conservative coverage: median error is 640000 ns
with offset/filter-only and zero with qualified rate mapping. Improvement is
trace-specific: the drift-change trace temporarily increases maximum error
from 640000 ns to 1280000 ns while retaining complete declared-bound coverage. A 20 ms asymmetric bias
persists and cannot qualify a precise rate. A consistently wrong stepped server
can be reacquired after the established disagreement recovery; its actual error
then exceeds its false declared uncertainty. That trace is explicitly retained
as an absolute-accuracy limitation, not counted as covered truth.

## 3. NTP-derived RF calibration

For UTC-per-raw slope `s = 1 + rate_ppb/1e9`, oscillator error is
`(1/s - 1)*1e9 = -rate_ppb*1e9/(1e9+rate_ppb)`, rounded to integer ppb.
Positive, zero and negative tests verify reciprocal/sign handling. An estimate
whose reciprocal exceeds ±100000 ppb is refused, never clamped. RF uncertainty
uses a conservative reciprocal derivative bound plus integer rounding. No
disciplined UTC feedback or assumed 50 ppm allowance is used as calibration.

The pinned SDK `079c6f39023649b154152db30f1d781e884879bc` starts RP2350 timer
ticks from `clk_ref` with 12 cycles per nominal microsecond. Its clock startup
selects XOSC for undivided `clk_ref`; the normal application configures the
XOSC-referenced system PLL at nominal 138 MHz. The PIO adapter uses divider 1.
Source anchors are SDK `pico_runtime_init/runtime_init_clocks.c`,
`hardware_ticks/ticks.c`, `hardware_clocks/clocks.c`, `hardware_pll/pll.c`,
the SDK timer adapter, application `main.cpp` and `rf/pico/pico_pio_dma.cpp`.
Runtime admission inspects ref/system muxes/dividers, PLL lock/refdiv/bypass and
timer tick cycles/running state; alternate/inhibited topologies refuse NTP RF.
These are topology/configuration checks, not frequency-counter observations.

Saved `ntp_rf_calibration` explicitly requests qualified-NTP selection with
manual fallback. Manual zero never enables auto. Candidate value, uncertainty,
sample count/span/age/generation, reason, topology, next choice and frozen
prepared choice are exposed. Manual and NTP are alternative authorities and
are never added. Independent RF applicability for this image remains unverified;
the implementation keeps that physical gate false and selects manual fallback
even for a software-qualified candidate. There is no API bypass. Therefore this
part and item 4 remain ⏳. Physical NTP/RF accuracy is not accepted.

## Validation, evidence and restoration

Final check counts, image hashes, resource measurements and source binding are
recorded in the manifest. Final software disposition is summarized below; the
independent RF gate remains open.

| Part | Disposition | Evidence boundary |
| --- | --- | --- |
| Persistent standalone manual PPM | Accepted | Deterministic persistence/authority/sign/freeze tests and normal/inhibited linked builds; no new RF measurement |
| NTP filtering and UTC rate discipline | Accepted in software scope | 235 exact oracle cases, 15 identical three-way traces, scheduling/failure tests and coherent RF-core mapping; physical UTC accuracy unqualified |
| NTP-derived RF calibration | Software/gating complete; physical acceptance unresolved | Qualified-candidate/fallback/reciprocal/topology tests; automatic RF selection remains inhibited by the independent measurement gate | Reproduce without hardware:

```sh
source scripts/xcode_env.sh
cmake -S . -B build/ntp-work-20261017/host -G Ninja -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_FIRMWARE=OFF -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build build/ntp-work-20261017/host --parallel 4
ctest --test-dir build/ntp-work-20261017/host --output-on-failure
python3 tests/ntp_replay_tests.py build/ntp-work-20261017/host/ntp_work_tests build/ntp-work-20261017/replay.json
python3 scripts/validate_wtp_contract.py
```

Normal, explicit inhibited and compatibility RF targets use a fresh task-local
build with the retained pinned SDK/toolchain/picotool. An initial direct configure
attempted an unavailable picotool fetch; the retained local source was then
supplied. Host helper configuration initially used the broken default Apple
toolchain environment; full Xcode repaired it. A transient disk-full compilation
was retried with two jobs. An initial unqualified full-suite run also exposed
sandbox loopback restrictions and missing Xcode environment; final results
distinguish repaired reruns and any dependency skip.

New tests cover parsing/range/sign, atomic page interruptions/reboot/omission/
replacement, callback latency, era/rejection regressions, epochs/duplicates/
freshness, held-out stability/systematic bias, checked mapping/oracle boundaries,
rate-aware hardware-simulated launch/refinement, healthy-rate pair survival,
correction consent, immutable paired preparation, manual/auto fallback and UI
uncertain-save behavior. Linked-image checks preserve engine separation, reserved
flash, renderer placement, stack guards and heap hooks. They do not measure
target CPU timing, stack high-water use or RF output.

No board/reference/receiver was identified for live work in this execution.
Actual budget: **0 fresh NTP exchanges; 0 RF starts; 0 seconds RF**. No firmware
was loaded and no hardware settings, services or reference path were changed.
Restoration is not applicable; inactive physical output was not independently
observed. The two-hour/128-exchange and six-tone/30-second limits were unused.
Raw historical INFO was not reused as new calibration. Generated firmware,
logs and replay output remain in ignored task-local storage.

## Independent review

The separate read-only reviewer identified older-sample starvation, overly broad
ownership freezing, peer-reset diagnostic residue, epoch-before-duplicate order,
malformed portable sample bounds, repeated-setter LOAD replacement and rounded
target crossing a refined UTC window. Repairs preserve original ages, explicit
pair scope, current provenance, checked arithmetic, idempotent correction and
forward launch-window validation. The reviewer also challenged the filter's
availability tradeoff and duplicate processing trace; the 26-second guard and
distinct callback-latency/processing cases address those findings. Final fresh
assessment found no remaining actionable source, test or documentation finding
after affected checks. Final evidence review is bound to the manifest.
Later full review repaired the UI revision adapter and uncertain-save draft
handling, preserved calibration across legacy/current/amplifier progress apply,
matched replay reset behavior to production, cleared KoD/leap selection residue,
and retained clock-model generation in unsynchronized snapshots. A pre-existing
nanosecond-scale clock test exposed the new rate-age default; zero now inherits
the ordinary observation limit and preserves custom clock configurations.

The final complete-pair preflight also uses the inverse mapping before ownership
or reservation. A -100000 ppb boundary test proves that a unit-slope sum fitting
within the raw range cannot admit a pair whose correct inverse overflows. The
independent reviewer inspected this repair and the affected test passed.

Final independent evidence assessment passed: all 779 product inputs, ten test
sources, nine ELF/UF2/map bindings, six SDK clock-source hashes, final logs and
all replay metrics matched the retained files. The final suite has 187 passes,
zero failures and one unavailable-jsonschema dependency skip among 188 tests;
235 exact oracle cases, 15 replay traces and the WTP contract validator passed.
All three final targets and linked resource checks passed. No actionable
implementation, test, documentation or evidence finding remains. Only the
independent physical calibration acceptance gate remains unresolved.
