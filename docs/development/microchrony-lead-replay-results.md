# Captured Internet samples: μChrony versus Chrony 4.9

The completed October 19 lead-layout run exposed two remaining μChrony control
differences. Conditional regression errors now weight the controller while
joint covariance and path ambiguity remain in the public bounds. Path ranking
now ages each retained exchange from its own timestamp, instead of aging an
old low-delay exchange from the newest fit. Admission, source agreement,
freshness, launch, manual PPM and RF qualification gates are unchanged.

These fixes substantially close the software difference from Chrony 4.9.
They do not eliminate the captured Internet sources' millisecond-scale bias.
Chrony reproduces A's tendency to slow an already-late clock and B's initially
negative frequency estimate. The main adverse result is therefore not a sign
error or a large remaining μChrony/Chrony estimator disagreement.

The [sanitized numerical record](microchrony-lead-replay-results.json) preserves
the comparisons and provenance. The [physical run report](microchrony-lead-layout-results.md)
remains evidence of the firmware that actually ran. This investigation uses
retained files only: no device, GPIO, GPSDO, receiver or service operation,
new capture, reflash or monitor restart occurred.

## Comparable inputs and initialization

The comparison uses the closed campaign's 919 accepted originals, 484 retained
packet offers and 319 measured pulses per board. All inputs are bound to the
retrieval manifest SHA-256
`43a7609f74d14780c4802bef6fdc88f285b7d3bebefd8291272210059e3cc80a`.
The stable post-RF acceptance frontiers retain every new original after the
main-capture baseline. The missing earlier originals remain A 87 and B 94;
earlier offered-packet deficits remain A 322 and B 321. Missing boot observations
and controller state are not reconstructed.

The pooled comparison gives both controllers zero initial learned frequency
and the same synthetic initial RTC at the translated first retained sample.
This is a controlled common prior, not a restored live boot. Raw send/receive
ticks, server timestamps and quality fields are identical. Chrony's source API
receives the admitted originals; the extra packet-delay classifier is disabled
only in this post-admission test adapter. Production filtering remains enabled
and is tested separately at the actual packet-admission boundary.

Replay outputs are compared at the captured GPIO instants. UTC phase eligibility
is the common intersection of synchronization, age no greater than 90 seconds
and reported error no greater than 500 ms: 315 A probes and 319 B probes. The
same four A freshness failures remain excluded from that phase score. Frequency
disagreement compares all 319 reported pure corrections, including the four A
holdover probes; restricting frequency to qualified probes gives 0.271 ppb RMS
after the fix on A. Indicated phase is measured against
the host GPS/PPS GPIO timestamp path, whose delay is uncalibrated. Agreement
between software outputs can be resolved more finely than physical UTC accuracy.

| Common-prior pooled replay | A | B |
| --- | ---: | ---: |
| Before: frequency disagreement from Chrony, RMS over 319 probes | 8.099 ppb | 5.648 ppb |
| After: frequency disagreement from Chrony, RMS over 319 probes | 0.270 ppb | 0.351 ppb |
| Before: indicated UTC phase RMS | 4.774596 ms | 5.061138 ms |
| After: indicated UTC phase RMS | 4.745804 ms | 5.034030 ms |
| Chrony 4.9: indicated UTC phase RMS | 4.745812 ms | 5.034707 ms |
| Largest after-versus-Chrony phase difference | 179 ns | 1,954 ns |

These are conditional replays, not measurements of the new firmware applied
to hardware. The original live indicated RMS was 4.548 ms on A and 4.480 ms on
B; its earlier controller state differs from this common cold-subset prior.
The remaining frequency differences include the engine's integer-ppb reporting
and finite timestamp/coordinate arithmetic. Full daemon equivalence is not
claimed.

## Why the original corrections were adverse

At the first captured pulse, A was indicated approximately 2.859 ms late and
applied a pure correction of −1.723 ppm. The independent RF checkpoints place
its native oscillator near +1.4 ppm, so a compensating rate is approximately
−1.4 ppm. A more negative point estimate slows the clock past that approximate
compensation while it is already late. The short-horizon matched-phase forecasts
therefore worsen. This explains their direction; A's unbound outer RF API
triplets still forbid a qualified, precisely time-bound corrected-frequency
claim. The GPIO path allowance also remains uncertified.

A's selected source's raw-coordinate fit was −2.392 ppm at capture start;
other sources ranged from −0.773 to +0.567 ppm. Those fits disagree with one
another and with the approximate hardware rate within their broad statistical
bounds. Frequency-weighted combination and prior updates produced the live
−1.723 ppm point estimate. The common-prior Chrony replay starts the measured
pulse interval at −1.676 ppm, so it shows the same excessive slowing tendency.

B's independently measured native oscillator was close to zero. Its stable
initial RF checkpoint applied −0.429 ppm and inferred −0.484 to −0.396 ppm
UTC frequency error: overcorrection under the unchanged engineering allowances.
By the first captured pulse, the live estimate was −0.568 ppm. All four source
fits at that point were negative:

| B source slot | Raw-coordinate frequency fit | Conditional statistical skew |
| --- | ---: | ---: |
| 0 | −0.131 ppm | 2.560 ppm |
| 1 | −0.354 ppm | 3.206 ppm |
| 2 | −1.079 ppm | 2.842 ppm |
| 3 | −1.222 ppm | 2.606 ppm |

The combined negative estimate is a consequence of those noisy fits, not
reversed correction polarity. Chrony's first common-replay pulse estimate is
−0.590 ppm; the repaired μChrony value is −0.589 ppm. Matching the reference
does not make that point estimate accurate for B's much smaller hardware error.
The broad error bounds do not resolve that small rate from these data.

Interpolating the independent host GPIO timestamps between adjacent raw-clock
edges gives indicated NTP source/path bias, without extrapolating outside the
capture. A's source medians range from −8.065 to −3.706 ms; B's range from
−18.393 to −1.816 ms. During the measured interval, peer RTT spans approximately
48.6–234.2 ms across the eight cohorts. Individual midpoint errors vary by tens
of milliseconds, far more than the small hardware-rate correction being sought.
The interpolation assumes a locally linear raw clock over adjacent ten-second
edges and does not calibrate the timestamp path.

These observations identify noisy, biased source/path measurements as the
limiting input. They do not separate server clock error from one-way path
asymmetry, or establish which network leg caused a particular sample. The
documented Chrony [delay/asymmetry behavior](https://chrony-project.org/doc/4.9/chrony.conf.html)
does not provide an independent UTC reference. No future GPS/GPIO truth is
used to tune a past filter, force a correction, lower uncertainty or relax a gate.

## Repaired μChrony differences

The first difference mixed two different error quantities. The full joint
time/delay covariance and identifiable alternative path fit are necessary for
public uncertainty. They are not the conditional regression precision used
to weight source frequency and controller updates. Using the public bound as
that weight produced 5.6–8.1 ppb RMS disagreement with Chrony on these streams.
The engine now retains separate conditional rate, skew and offset errors for
controller weights. Every existing public covariance/path bound remains in
source usability, agreement, max-update-skew, clock-error and RF qualification.
All 919 fixed-coordinate public estimate rows are exactly unchanged from the
baseline, including their uncertainty fields.

The second difference made an old good path artificially young. Ranking formerly
used the smallest retained path distance and aged it from the latest fit's
timestamp. The correct causal comparison ages each candidate exchange by its
own elapsed time and conditional skew before choosing the best current distance.
Black-box source-API diagnostics exposed several-millisecond ranking-distance
differences, even when source fits and selected slots agreed. Correcting that
aging closes most of the remaining phase discrepancy.

New behavioral regressions ensure that an old retained low-delay path loses
preference to a fresh better source, and that a narrow conditional error cannot
open a frequency-update gate closed by the full public bound. Separate combination
checks retain the all-source frequency bound when controller precision changes.
The engine remains fixed-capacity at 32,712 bytes under its existing 32 KiB limit.
Implementation is original MIT code; Chrony implementation code is neither
copied nor linked into firmware.

## Admission, known error and review

All 484 offered packets match Chrony's admission decisions before and after
the fixes under common cold, fixed-output conditions. Their server epochs are
translated to a common origin and their nonce is regenerated; both implementations
receive the resulting identical bytes. Original raw intervals, body quality
fields and correlation-failure semantics are retained. The five differences
between this cold common replay and original live verdicts remain explicit;
missing earlier admission history and changed clock-control coordinates prevent
treating the cold replay as restored live filtering state.

All eight fixed-coordinate histories match Chrony's sample counts, adaptive
windows and asymmetry choices over 919 originals. Maximum fitted-frequency
disagreement is below 0.001 ppb. The 30 existing synthetic packet fixtures retain
their expectations, including the five deliberately stricter Pico-profile
differences. No classifier or quality threshold was loosened.

The 28 complete four-hour known-error traces, causal-prefix checks, finer
quarter-second probe grids and existing acceptance thresholds pass. Selected
final-hour actual-UTC RMS results are:

| Known-error Internet-delay trace | Repaired μChrony | Chrony 4.9 |
| --- | ---: | ---: |
| Weak queue | 0.765923 ms | 0.765845 ms |
| Forward queue | 0.447144 ms | 0.447142 ms |
| Reverse queue | 0.342605 ms | 0.342605 ms |

Closer reference agreement is not a promise that every true-error score
decreases. For example, the previous μChrony forward-queue result was
0.442854 ms, below both the repaired value and Chrony's. That adverse change
is retained rather than tuning the implementation to this seed or changing
the acceptance threshold.

All 121 host tests pass. The normal `WsprryPico` cross-build passes RF-engine,
reserved-flash, RAM/stack and linked-adapter checks using retained dependencies.
The resulting image remains private and was not loaded on A or B. The closed
hardware run and paused monitor remain unchanged.

Adversarial review independently recomputes pooled phase/frequency scores and
known-truth sums of squared error, checks manifest/source/binary bindings and
retains all unqualified records and adverse scores. Boundary checks reject a
changed manifest and assertion-disabled validation. This is a self-review with
independent calculations, not a new independent agent or human review. Review
also corrected the reproduction executable paths and made diagnostic helpers
reject mixed source cohorts rather than silently replacing or joining them.
The repeated assessment found no remaining actionable issue within this
captured-input scope. The
[reference guide](../../tests/reference/README.md) provides the reproduction
commands and scope. Physical UTC/RF qualification remains open.
