# μChrony A/B results after GPIO lead rearrangement

The finite October 19 comparison completed at **08:16:37 CDT**, before its
08:19:46 deadline. Both boards produced 319 main-capture pulses with **zero
unexpected GPIO events**. The rearranged leads supported a complete measurement
interval; this establishes no recurrence during this run, not a proven electrical
root cause or permanent repair.

The measurements do **not** establish a consistent UTC or RF accuracy improvement
on both boards. B's later rate updates improved some short forecasts relative
to its starting correction. A's short forecasts remained adverse. B's initial
learned frequency overcorrected its measured oscillator; the final frequency
comparison is unresolved within the engineering bounds. Both A RF checkpoints
crossed an API clock-model update and remain excluded from corrected-frequency
claims. All adverse and unqualified observations are retained.

The [sanitized numerical record](microchrony-lead-layout-results.json) binds the
private evidence and calculations. The earlier stopped runs and their results
remain in the [conformance report](microchrony-conformance-results.md).
The later [captured-input replay](microchrony-lead-replay-results.md) compares
these inputs with Chrony 4.9 and records software repairs; it does not replace
the observations of the firmware that ran here.

## Setup, bounds and restoration

Both Pico 2 W boards retained normal firmware `89738cad878c-dirty`, UF2 SHA-256
`dc779bbd3a354763a5dce3618ac636a7404eda6d5dd40b3370a69db7753c24fe`,
`pio-dma-gp2` and nominal 138 MHz. A is serial `0BF4B4AEC9FFB344`, boot
`c9d4f5bba4b5353bdd7c05e0a10553a2`; B is serial `CDDBF8767C506C07`, boot
`5e0eae1065aad8d8c5a43588ee9ff8f2`. Both use `pool.ntp.org`, manual
0.000 PPM in manual mode and disabled schedules. Neither Pico receives GPS/PPS
as a synchronization input. GP22 supplies measurement pulses to wspr5 GPIO22
for A and GPIO23 for B; wspr5's GPS HAT PPS on GPIO17 supplies the host reference.

The campaign ran from 07:19:46 through 08:16:37 CDT, including a three-pulse
wiring check on each board, two two-second RF checkpoints per board and
restoration. The main pulse interval was approximately 07:21:45–08:14:45.
The original one-hour deadline, 300-second final RF reserve, 333-pulse per-board
wiring-plus-main limit, query delta limit 800 and 512 MiB evidence cap were
preserved. Actual query deltas were A 210 and B 211. There were no reflashes,
resets, source or saved-setting changes, additional experiments or extensions.

All observer, deadline-guard and RF worker/guard processes actually exited.
The independent post-run check acquired the canonical locks and verified both
boards inactive/unowned, schedules disabled, identical boots/revisions/settings,
and fresh pool NTP: approximately 13.75 seconds old on A and 16.76 seconds on B.
The same boots and reported revision bind the previously verified image; no
post-run flash readback or reset was performed. GPIO22/23 were restored to their
original unused, no-pull state. GPSDO outputs returned to 10 MHz with both outputs
and PPS disabled; the host GPS/PPS reference remained selected. All four receiver
captures report verified stream/device cleanup.

## GPIO integrity and source visibility

The wiring request contains six pulses and twelve consecutive physical edges.
The separate main request contains 638 pulses and 1,276 consecutive edges;
global and per-line counters were verified independently for each request.
All physical edge order, width and raw-timer bracket checks passed. There are
3,237 main idle/context receipts plus seven wiring receipts, with no unexpected
events or control/pad configuration changes. Sampled current power-fault bits
were clear. Historical `0x50000` flags predate this run and were not cleared;
30-second power sampling cannot exclude a brief transient.

All 54 main duplicate requests per board have unchanged raw replies and zero
additional edges. Wiring duplicates also recorded equality and no edges, but
their raw duplicate replies were not retained; equality there is a runner
receipt rather than an independently recomputed raw-reply check.

The earlier runs failed after approximately eight and nineteen minutes with
nearly simultaneous falling-only events on both inputs. This run retained
approximately 53 minutes of clean main capture after the reported lead move.
That association supports the new layout for this finite test. It does not
distinguish coupling, ground/supply disturbance or interrupt/event reporting
without an independent electrical waveform.

All 2,704 private files, totaling 140,783,097 bytes, match the retrieved SHA-256
inventory. Its manifest SHA-256 is
`43a7609f74d14780c4802bef6fdc88f285b7d3bebefd8291272210059e3cc80a`.
The offered-packet ring retains 242 records per board, including 32 records
preceding its campaign baseline; 210 new offered records per board have no
post-baseline gaps. Unseen earlier offered records remain explicit: A 322,
B 321. Offered-response counts and query counters are distinct quantities.

Merged immutable source cohorts contain 458 accepted originals on A and 461
on B. Against this campaign's separate main-capture baseline, all **201 new A
and 203 new B accepts**, including the final RF period, match their stable
post-RF frontiers. The accepted-original pre-capture deficits remain A 87 and
B 94. These are different baselines and units from the offered-packet ring;
neither establishes complete boot-input visibility.

Independent API-before/INFO/API-after checks bind 110 of 118 retained triplets.
None was saved as bound while failing independent recomputation. Holdover and
model-transition triplets remain unqualified: seven crossed a model update and
one sampled holdover. A supplied four unqualified pulses
at ticks 311–314; capture continued through the time loss. Its other 315 pulses
and all 319 B pulses were clock-qualified. No freshness or launch gate changed.

## Measured UTC phase and incremental rate effects

The following differences are Pico UTC minus the host GPS/PPS-derived GPIO
timestamp. They include an uncalibrated host/GPIO path. RMS values summarize
indicated phase; they are not certified absolute UTC accuracy or an isolated
measure of frequency learning.

| Qualified-pulse phase | A | B |
| --- | ---: | ---: |
| First indicated midpoint | −2.859 ms | −3.323 ms |
| Last indicated midpoint | −4.679 ms | −4.429 ms |
| Indicated RMS | 4.548 ms | 4.480 ms |
| Last interval, 1 ms plus root distance allowance | −5.698 to −3.661 ms | −5.448 to −3.410 ms |
| Last interval, 5 ms plus root distance allowance | −9.698 to +0.339 ms | −9.448 to +0.590 ms |

Causal open-loop comparisons start from the same measured phase, preserve the
already scheduled finite phase slew and stop before any subsequent clock-model,
source-cohort or frequency update. They compare the applied pure frequency with
either zero learned frequency or the frequency frozen at this main capture's
first edge: A −1,723 ppb and B −568 ppb. They do not simulate a complete alternate
feedback controller, and their verdicts are conditional on the stated timestamp
path allowance.

| Approximately ten-second adjacent forecasts, improved / worsened / unresolved | A | B |
| --- | ---: | ---: |
| Applied versus zero frequency, 1 ms allowance | 0 / 266 / 0 | 0 / 113 / 156 |
| Updated versus frozen starting frequency, 1 ms allowance | 0 / 43 / 223 | 34 / 0 / 235 |
| Applied versus zero frequency, 5 ms allowance | 0 / 83 / 183 | 0 / 9 / 260 |
| Updated versus frozen starting frequency, 5 ms allowance | 0 / 5 / 261 | 7 / 0 / 262 |

Each allowance also includes the recorded host root distance, approximately
10–31 µs. The 266 A and 269 B eligible adjacent forecasts exclude new model
inputs and unqualified endpoints; they are a selected set of stable-model
intervals, not every interval of the run.

Across overlapping horizons through sixty seconds, B's updated-versus-frozen
comparison has 196 improved, 74 worsened and 598 unresolved results at 1 ms;
at 5 ms it has 91 improved and 777 unresolved, with none worsened. A has
29 improved, 433 worsened and 403 unresolved at 1 ms; at 5 ms it has zero
improved, 152 worsened and 713 unresolved. These counts are not independent
trials or a success percentage. The numerical record also retains every
zero-frequency comparison and exclusion.

The full run therefore adds some conditional late benefit on B relative to
its initially negative correction, while retaining substantial adverse A
results. It does not establish a consistent learned-frequency benefit over
zero correction on both boards. Slowing a clock that is already late can
worsen short-term phase even when it reduces oscillator-frequency error;
phase damping and frequency qualification require separate assessments.

## Independent RF measurements and UTC frequency inference

RSP1B `2404058C60` observed each Pico with the LBE-1421 GPSDO
`0673ED0FA107` through the user-confirmed combiner and separate 60 dB attenuation.
Temporary 40 kHz output supplied simultaneous 3.56 and 3.64 MHz reference
harmonics around each nominal 3.570100 MHz tone. Two references remove receiver
frequency offset and sample-scale error in the same coherent fit window.

All four RF captures pass the unchanged requirements: contrast at least 30 dB,
phase residual RMS below 0.15 rad, minimum/median amplitude at least 0.5,
half-window frequency difference at most 0.1 Hz, no overflow/clipping, and
verified receiver/reference/ownership cleanup. The intervals below include
±0.05 Hz per fitted line and a 10 ppb GPSDO engineering allowance. Those
allowances are not an independently certified uncertainty budget.

| Board and checkpoint | Native oscillator error versus realized NCO nominal | Pure learned UTC correction | Inferred corrected UTC frequency error |
| --- | ---: | ---: | ---: |
| A start | +1.396 to +1.484 ppm | Excluded | API triplet crossed a model update |
| A end | +1.389 to +1.477 ppm | Excluded | API triplet crossed a model update |
| B start | −0.055 to +0.033 ppm | −0.429 ppm | −0.484 to −0.396 ppm: worse |
| B end | −0.103 to −0.015 ppm | +0.151 ppm | +0.048 to +0.136 ppm: unresolved versus native |

The native transmitted carrier remains manual-corrected by 0.000 PPM. No
NTP-derived RF correction was programmed. The inferred UTC-frequency rows use
the verified common timer/RF oscillator relationship; they are not measured
changes to the transmitted carrier or proof of absolute UTC phase. For B,
intentional phase slew contributes another +23 ppb initially and +416 ppb at
the end; that component is separate from the pure learned frequency above.
Including that scheduled slew, B's inferred instantaneous UTC frequency error
is −0.461 to −0.373 ppm initially and +0.464 to +0.552 ppm at the end. Its pure
frequency term worsens instantaneous rate error relative to the corresponding
phase-slew-only term at both checkpoints. A temporary catch-up slew can still
reduce late UTC phase; instantaneous frequency error and phase improvement
are different measurements.
A's physical RF measurements remain usable, but the unbound outer API reads
prevent assigning one qualified applied UTC model to either checkpoint.

## Adversarial review and reproducibility

Separate self-review passes recompute the raw-to-UTC piecewise mapping and
6,932 treatment/allowance comparisons with independent rational arithmetic,
including reference endpoints, prediction boundaries and a 65-position
reference grid. Independent event counting checks both request sequences and
raw main-duplicate replies. RF residual-rate arithmetic is recomputed separately
from the fit/scoring helper. This is not represented as a new independent
agent or human review.

The review preserves three consequential limits: A's unbound RF triplets cannot
be rescued by matching inner snapshot generations; wiring duplicate equality
cannot be independently recomputed without its missing raw reply; and the full
run's 5 ms sensitivity results differ from the earlier interim prefix. The
terminal tables replace no historical evidence and retain both benefit and harm.
The private audit's initial lookup of main context under the history subdirectory
was corrected to the actual root-level context file before reassessment.
The reassessment passes all 17 measurement-arithmetic and seven probe tests,
source-hash and finite-budget checks, exact table/count reconciliation, 35 local
link/anchor checks and whitespace validation. No actionable analysis finding
remains within this scope. **Assessment: share with caveats**; the stated
physical qualification and measurement-path limits remain open.

Reproduction uses the retained private campaign directory under ignored
`build/microchrony-lead-layout-20261019/`, with `terminal-evidence/` beside the
hash-bound offline helpers:

```sh
python3 build/microchrony-lead-layout-20261019/verify_evidence.py \
  build/microchrony-lead-layout-20261019/terminal-evidence --complete \
  --output build/microchrony-lead-layout-20261019/terminal-independent-verification.json
python3 build/microchrony-lead-layout-20261019/analyze_pulses.py
python3 build/microchrony-lead-layout-20261019/analyze_rf.py
python3 build/microchrony-lead-layout-20261019/audit_terminal.py
python3 tests/clock_measurement_tests.py
python3 tests/clock_pulse_probe_tests.py
```

The checks establish the reported finite observations and conditional arithmetic.
Physical absolute UTC accuracy, general RF calibration and an electrical root
cause remain unqualified. The completed campaign is not restarted or extended.
Future [GPS UTC/PPS reuse of μChrony](consolidated-backlog.md#remain-in-backlog-for-future)
retains the same separation between source observations, clock discipline,
manual PPM and independent RF acceptance.
