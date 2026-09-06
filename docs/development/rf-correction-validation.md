# Frequency correction, drift and alias investigation

Recorded 2026-09-05. Step 8 remains incomplete. This is experimental conducted
bench evidence, not an encoded WSPR decode, calibrated timing qualification or
production engine promotion.

## Executed prompt

Work on devel. Measure generator repeatability and settling against the
simultaneous GPSDO reference using the existing wspr5 SDR capture helper. Add an
explicit, bounded frequency correction to the bench engine and validate its
sign, all four tones, reported state and rejection paths. Compare uncorrected,
corrected, receiver-retuned and gain-changed captures, then a full synthetic
frame. Investigate the nearby spectral feature with an independent sampled
waveform model and a reference-only control. Preserve exact image and capture
identity and report failed criteria without changing their thresholds. Review
adversarially, repair actionable implementation findings, reassess and run the
applicable checks. Update the roadmap, commit and push devel. Encoding and
production UTC/WTP integration remain subsequent work.

## Implementation

`CORRECTION <ppb>` accepts integers from -100000 to 100000. Positive values mean
the source clock runs fast: each nominal 32-bit NCO increment is divided by
`1 + ppb/1e9`, using rounded integer arithmetic. The increment resolution is
approximately 0.034925 Hz at the nominal 150 MHz sample rate. All four tone
increments are corrected. This does not alter symbol sample counts or correct
the physical sample clock itself.

Correction is volatile, defaults to zero at boot and survives STOP. It can only
change while the engine is idle without a prepared job or active output. The
bench client verifies STOP and the exact accepted correction before proceeding.
CAPS reports the supported range; STATUS records the selected value. Specify
`--correction-ppb` explicitly for reproducible experiments; omission retains the
current device setting. Standard WTP firmware remains RF-inhibited and has no
new wire command. Planner realized-frequency reports use nominal sample-clock
arithmetic, not a calibrated prediction of the physical corrected output.

Each Waveform owns 34,816 bytes of lookup tables keyed by its four increments.
Tables rebuild during preparation when increments change, never during render.
Independent instances cannot overwrite each other's correction. The engine
object is bounded to 180 KiB including its tables and two 64 KiB buffers; the
bench CPU waveform has its own tables and buffer. No render-time allocation was
added. Corrected target BENCH 128 measured a worst refill of 1.402 ms versus the
3.495 ms block budget. Observed stack canary use reached 9,848 of 16,384 bytes;
this is a workload observation, not a worst-case proof.

## Setup and identity

- Pico 2 W / RP2350, serial `0BF4B4AEC9FFB344`, GP2 physical pin 4 and GND
  physical pin 3. Operator-confirmed 60 dB attenuation (20+20+10+10 dB) and
  combiner; no additional filter or DC block is assumed.
- Experimental PIO/DMA engine, 150 MHz nominal clock, monotonic relative launch.
  Synthetic cycle4-162 workload; no UTC synchronization or encoded message.
- wspr5 RSP1B serial `2404058C60`, 250 ksample/s CF32, 200 kHz bandwidth,
  AGC and bias tee off. Default center 3,550,000 Hz and gain 20 dB.
- LBE-1421 `0673ED0FA107`, output 1 at 3,580,000 Hz, LOW, on the combiner.
  Project-owned lbgpsdo CLI recorded lock/readback and disabled output 1 after
  every capture. No frozen receiver calibration profile was applied. The
  analysis subtracts simultaneous indicated reference error; sample-rate scale
  is not independently calibrated.
- Firmware revision `001226ce2c6e-dirty`, SDK 2.3.0, Arm GCC 15.3.1 Release.
  UF2 SHA-256: `cbf57ed56dccce1a33ebe5af3f98279309ce68ff3883479bf870fbf21c5d0f7d`.
  Local image and raw evidence are under ignored `build/rf-correction-evidence/`.
  Source hash manifest accompanies `image-1/`. This measured image predates the
  final commit identity; do not substitute a later build's identity.

## Measurements

Ten-second tone 0 runs, relative to 3,570,100 Hz after GPSDO comparison:

| Capture | Correction ppb | Center Hz / gain dB | Mean error Hz | Peak-to-peak Hz |
| --- | ---: | ---: | ---: | ---: |
| uncorrected-2 | 0 | 3550000 / 20 | +7.973726 | 0.122073 |
| corrected-1 | 2222 | 3550000 / 20 | +0.011814 | 0.112708 |
| retuned-1 | 2222 | 3520000 / 20 | +0.001770 | 0.122886 |
| gain-1 | 2222 | 3550000 / 30 | -0.002610 | 0.118293 |

These means describe these short runs, not long-frame frequency accuracy. The
corrected full frame lasted 110.592 s, with maximum estimated transition error
1.2 ms and fitted spacing 1.465942 Hz. Its original linear model residual was
0.115518 Hz, exceeding the unchanged 0.1 Hz diagnostic limit. That check failed.

A separate descriptive exponential fit, trained on every third symbol and
checked on the remaining symbols, found approximately 0.397 Hz transient,
46.91 s time constant, 1.466469 Hz spacing and 0.029502 Hz maximum held-out
residual. Its extrapolated asymptote was 3,570,099.645856 Hz. The prior uncorrected
frame similarly fitted a 0.397 Hz transient and 43.80 s time constant. These are
consistent with settling during transmission; without temperature or power
measurements they do not establish thermal causation. No automatic transient
compensation or replacement pass criterion was introduced.

## Nearby feature

The strongest nearby feature moved from 3,514,312.196 Hz to 3,513,971.257 Hz
when correction changed from zero to 2222 ppb: -340.939 Hz. The independent
per-sample MSB waveform model predicts -340.899 Hz movement for the folded
43rd harmonic at a nominal 150 MHz sample rate. Its simulated peak is roughly
-33 dBc, matching the observed approximate -32 to -34 dBc range.

Retuning the receiver by 30 kHz left the feature at 3,513,971.229 Hz; changing
gain left it at 3,513,971.138 Hz. In a reference-only control with Pico stopped,
local peak-to-background contrast near that feature fell from 63.24 to 8.31 dB;
the GPSDO remained strongly visible. Contrast uses the first 262144 samples
starting two seconds into each capture, a Hann FFT, peak within 100 Hz and
median background 500–1500 Hz away. It is not a calibrated power measurement.

Together these observations strongly identify an intrinsic sampled-square-wave
alias. It remains present. Peak-bin dBc varies with bin alignment and drift;
these measurements do not qualify integrated spur power or out-of-band output.
Reducing the alias requires further generator/clock or output-path engineering.
A simple low-pass filter cannot be assumed to remove a feature this close below
the desired carrier.

## Capture hashes

SHA-256 of each CF32 file:

| Capture | SHA-256 |
| --- | --- |
| uncorrected-2 | `56603380d941650e34fe2168be72b9219167d6c1f0456045f7deef046d3da5b6` |
| corrected-1 | `6f1abf112bdcd67940d52aa3340bd7035018ac50bb6f76d7b6078e96bbc3d8c5` |
| retuned-1 | `f8be30a263a0e5ba6f87c926fceb8bbed7f648bbad3fc7b1bef2ad5e3e849630` |
| gain-1 | `28cd435ecc3f6a6eda71593a8da89e701adae14cb12ebb25e14e11f208ab9b8f` |
| frame-corrected-1 | `f0cc0874e8db23da21e0b454515a748d200bd64c92bff9e2b95ef6d44b7372cb` |
| reference-only-2 | `9c53a5305ac99567a4bce78beecf698171879b4a98ece64f8e7790f78c2955ac` |

Each directory contains capture settings, transmitter identity/state and GPSDO
readbacks. An initial reference-only attempt failed at sandbox SSH resolution
before device work; reference-only-2 is the completed control. Final Pico status
was stopped/output inactive and GPSDO output 1 disable was verified by the CLI.

## Review and validation

Adversarial review repaired stale STOP acceptance before correction, rejected
incompatible receive-only/frame/abort options before I/O, guarded invalid helper
arguments and rejected drift fits with unidentifiable tone coefficients. Tests
cover correction bounds/sign, all four tones against an independent bit oracle,
interleaved waveform isolation, prepared/active rejection, client failure paths,
reference cleanup, model prediction and held-out drift behavior. A second review
found no remaining actionable implementation defects in this slice. The measured
settling and alias findings remain explicit engineering work, not closed RF
qualification issues.

Validation passed: Debug 15/15 tests (including optional analysis and USB
descriptors), Release 11/11 and Address/UndefinedBehavior sanitizer 11/11.
Affected Python tests were rerun after review repairs. Standard firmware, RF
bench and driver link-check targets built; both firmware image memory checks,
WTP contract validation, C++ formatting, Python compilation and Markdown links
passed.

Run offline analysis tests using an existing NumPy-capable Python configured as
`WSPRRY_PICO_HARNESS_PYTHON`. `scripts/predict_rf_spurs.py` writes the independent
model; `scripts/analyze_rf_drift.py` writes a separate descriptive result from a
frame measurement. Both refuse to overwrite an existing output file. Raw
capture and firmware files stay outside source control.

Next: investigate alias reduction and long-frame settling, then verify an
encoded WSPR frame and integrate production UTC/job-service operation. The
operator determines subsequent hardware experiments.
