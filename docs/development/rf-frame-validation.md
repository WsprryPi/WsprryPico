# Full-frame bench validation and simultaneous reference

This Step 8 slice adds and exercises a complete local synthetic frame, an
intentional abort followed by rearm, and receiver-side frequency interpretation
against an in-window GPSDO. It does not encode a station message or integrate
UTC/WTP transmission. The standard firmware remains the inhibited WTP endpoint.

## Execution prompt and scope

Extend the bench on devel with a finite, locally timed 162-symbol four-tone
workload. Exercise full-frame output and abort/rearm on the existing GP2/GND
conducted setup into wspr5. Improve offline frequency, transition and in-band
spectral measurements; test misleading/noisy/interrupted evidence. Reuse the
existing Harness helper without changing its repository. Record exact firmware,
receiver and source identities. Review adversarially, repair software findings,
reassess, update the roadmap, then commit and push. Preserve physical limitations
and failed diagnostic criteria rather than promoting them to qualification.

The operator confirmed the existing 60 dB attenuation and subsequently directed
use of GPSDO output 1 through the combiner. Calibration-file research was stopped
at the operator's request; no frozen calibration file was applied. Simultaneous
reference comparison is recorded separately from formal receiver calibration.

## Implemented workload and controls

`FRAME <delay_ms>` accepts 100..10000 ms and constructs 162 RF-on events cycling
0,1,2,3. Each symbol lasts exactly 102,400,000 nominal samples at 150 MHz. Cumulative
nanosecond boundaries are rounded from n × 2048000000 / 3, avoiding accumulated
rounding error. Total duration is 110.592 seconds and 16,588,800,000 samples.
The entire event sequence is prepared before local launch. USB polling supplies
no symbol timing. CAPS advertises `frame: cycle4-162` and its exact duration.
The waveform remains phase-continuous across tone changes. This pattern is a
synthetic timing workload, not a decodable WSPR message.

The client adds `frame` and `--abort-after-ms`. Abort is sent after observing
Running for the requested interval; 50 ms host polling and USB latency are
additional. It requires an exercised abort and a stopped/inactive response,
then performs normal STOP cleanup. A frame that finishes before an intended
abort is reported as a failed test. Frame client timeouts cover the full job.

The capture coordinator adds `--frame`, `--abort-after-ms`, and the explicitly
selected `--gpsdo-reference`. The reference option uses wspr5's existing
project-owned `~/lbgpsdo` CLI with sudo, selects LBE-1421 serial `0673ED0FA107`,
output 1 at 3,580,000 Hz, LOW drive, and disables PPS. It does not save flash
configuration. It records status around the capture and attempts output-1
disable in cleanup, including after enable/capture/status failures. The
manifest distinguishes verified CLI disable from unconfirmed cleanup.
It leaves output 2 untouched. This option is specific to the documented bench.

## Reproduction

Build and flash the explicit RFBench target as described in [the bench guide](rf-bench.md).
Use the actual board, port, build revision and UF2 for a new execution. These
examples identify the image measured in this record; evidence directories must
be new:

```sh
python3 scripts/capture_rf_bench.py \
  --port /dev/cu.usbmodem2103 --serial 0BF4B4AEC9FFB344 \
  --revision 8ae2db830f92-dirty \
  --firmware build/rf-frame-evidence/image-1/WsprryPico-RFBench.uf2 \
  --output build/rf-frame-evidence/new-frame --attenuation-db 60 \
  --frame --gpsdo-reference
```

For abort coverage, omit the reference option and add `--abort-after-ms 500` to
`--frame`. For rearm, run a new capture using `--tone 3 --duration-ms 1000`.
For an unmodulated spectral measurement, use `--duration-ms 10000 --gpsdo-reference`.

```sh
../WsprryPi-Qualification-Harness/.venv/bin/python scripts/measure_rf_bench.py \
  build/rf-frame-evidence/new-frame/capture.cf32 \
  build/rf-frame-evidence/new-frame/capture.json \
  build/rf-frame-evidence/new-frame/measurement.json --frame --reference-hz 3580000
```

For the ten-second tone, replace `--frame` with `--duration-s 10`. Output JSON
is never overwritten. Exit 1 means diagnostic criteria were not met; it does
not erase measurements or imply an implementation crash. Exit 0 is also not
qualification. IQ hash, size, wire format, cleanup, overflow and clipping evidence
are checked. The existing coarse Harness analyzer remains independently usable.

Optional offline tests use the existing Harness Python/NumPy environment:

```sh
cmake -S . -B build-host \
  -DWSPRRY_PICO_HARNESS_PYTHON="$PWD/../WsprryPi-Qualification-Harness/.venv/bin/python"
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
```

## Measurement method and limits

The analyzer Hann-weights and decimates mixed IQ to approximately 1 kS/s. It
finds uninterrupted burst intervals using amplitude relative to the leading
baseline and peak. Per-symbol phase fits omit 80 ms at each edge; unmodulated
tones use windows no longer than 0.5 seconds to separate slow drift from loss of
coherence. Every segment and issue is retained. A separate symmetric 20 ms phase
difference and fitted ramp estimates each transition on a 0.1 ms search grid.
The grid is not a metrological uncertainty claim.

When a reference is supplied, every segment also requires a distinct spectral
feature at that reference in the original IQ, at least 20 dB above local
background, and a coherent reference phase fit. This prevents coherent alias
leakage from being mistaken for a missing reference. The simultaneous indicated
reference error is subtracted from the Pico's indicated frequency. Receiver
sample-rate scale, GPSDO uncertainty and the output network are not independently
calibrated. The stored `calibration_applied` and `qualification` remain false.

Frame diagnostics fit base frequency, tone spacing and linear drift. The limits
are descriptive test criteria: duration within 20 ms, transitions within 10 ms,
phase RMS <=0.15 rad, minimum segment amplitude >=0.5 of its median, spacing within
0.05 Hz of 375/256 Hz, and maximum per-symbol frequency residual <=0.1 Hz.
They are not WTP requirements or transmission permissions. A residual exceeding
0.1 Hz remains a recorded failure even when all symbols are identifiable.

The tone FFT uses up to 2,097,152 raw samples, giving 0.119209 Hz bins at 250 kS/s.
The report retains the strongest other bin within ±90 kHz of receiver center,
excluding ±5 Hz around carrier and reference. Its dBc value is a windowed
peak-bin ratio, not integrated spur power or calibrated output power. The capture
does not establish harmonic suppression outside that receiver window.

## Actual target results

Recorded 2026-09-05 local / 2026-09-06 UTC. Pico 2 W / RP2350 serial
`0BF4B4AEC9FFB344`, GP2 physical 4, GND physical 3, clk_sys/sample clock 150 MHz;
SDK 2.3.0 and Arm GCC 15.3.1. Firmware revision `8ae2db830f92-dirty`;
UF2 SHA-256 `17488d5321b1d730af6a6abd28154bbfe89add4ebd95f1376cd524fdab840338`.
The final rebuilt UF2 matched this tested image byte-for-byte. Source hashes,
USB transcripts, GPSDO status and raw IQ remain in ignored
`build/rf-frame-evidence/`. No generated firmware or IQ is committed.

Receiver: wspr5 RSP1B serial `2404058C60`, center 3.55 MHz, 250 kS/s,
200 kHz bandwidth, gain 20 dB, AGC/bias tee off. Same native Harness helper as
the prior bench record. GPSDO: LBE-1421 `0673ED0FA107`, firmware 1.9, output 1 at
3.58 MHz LOW, satellite and PLL locked in the before/active/end/after records
for the reference-backed frame. Both outputs were disabled at final readback.
Lock observations bracket the capture; they are not continuous lock telemetry.

| Test | Observed result |
|---|---|
| Full frame without reference | Complete, STOP confirmed, 110.592 s burst, 31,642 DMA IRQs |
| Ten-second tone with reference | Complete; compared mean 3,570,107.8458 Hz; 0.1221 Hz peak-to-peak |
| Full frame with reference | Complete, STOP confirmed; all 162 symbols and 161 transitions measured |
| Frame transition timing | Maximum fitted error 0.5 ms relative to detected burst start |
| Frame tone spacing | 1.4660709 Hz versus nominal 1.46484375 Hz |
| Frame frequency fit | Base 3,570,107.8109 Hz; linear drift −0.0030102 Hz/s |
| Frame remaining diagnostic failure | Maximum residual 0.1229713 Hz exceeds 0.1 Hz criterion |
| Intentional frame abort | Stopped/inactive; captured RF burst 0.560 s |
| Rearm after abort | Tone 3 completed; captured duration 1.000 s |
| Memory observation | Stack canary maximum 9,644 of 16,384 bytes; not a heap high-water proof |

All five captures had verified hashes/counts/cleanup, zero timeouts, zero
overflows and zero clipping samples. Normal frame load included 50 ms USB STATUS
polling; heavier competing loads remain untested. The 500 ms abort timer starts
on host observation of Running; the 560 ms burst is consistent with that polling
path and is not a measurement of device STOP latency. An exact-500-ms tone
analysis therefore retains its duration mismatch. It is not used to claim a
500-ms locally timed job.

The strongest other in-window bin in the ten-second capture was approximately
3,514,311.96 Hz at −31.97 dBc. No conclusion is drawn here about whether it
originates in the generator, receiver, coupling, or output network. Frequency
is approximately +7.85 Hz (+2.20 ppm) above nominal in the reference comparison.
Neither offset correction nor spur remediation is implemented in this slice.

| Capture directory | IQ SHA-256 |
|---|---|
| frame-1 | 28805d00b8b8fe9bb0faf5d968619932a6b2a321ee24cebc02e18d2ae1331c24 |
| tone-reference-1 | da74f934eef5ca5be8f360a12cf6fc3699b64f35f681482e6b857f34c8c193b7 |
| frame-reference-1 | 016626954bfffbffd7cb4f015bb95b62ae4a79aa24fa01dbed44c78669727a1f |
| abort-1 | 7bf5e0ef893e1ba6d7225cc7a755219adcd3d10545e07acc08316546939fb016 |
| rearm-1 | dabc3050712f24909198a54356aecfbe378457175f9965481cc490b8727927e3 |

## Adversarial review and next boundary

Repaired findings: false reference detection through decimator alias leakage;
long-tone drift conflated with incoherence; noisy single-crossing transition
selection; abort marked successful without actually being exercised; cleanup
paths that needed explicit GPSDO-disable failure injection. Tests cover missing
reference, self-reference, reversed tones, a delayed boundary, interruptions,
noise, wrong duration, corrupted IQ, timeout/STOP and reference cleanup after
capture/final-status failures. Earlier analysis outputs remain alongside final
outputs; results were not overwritten to hide failures.

Final software validation: 14/14 Debug tests including optional analysis and
USB descriptors, 11/11 Release, 11/11 address/undefined-behavior sanitizer tests,
standard/bench/linkcheck firmware builds and both memory-layout checks passed.
Reassessment found no remaining actionable implementation finding in this
slice. The measured frequency offset, nonlinear residual and in-window spur
remain engineering findings for the next slice, not closed RF qualification.
Next work is controlled clock correction/drift and spur investigation, followed
by encoded WSPR verification and production UTC/WTP integration.
