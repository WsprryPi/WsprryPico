# Step 8: encoded WSPR and frame stability

Encoded RF now decodes independently on wspr5 captures. The final repaired image
completed warmup and measurement cleanly; its 0.03724 Hz settling residual and
0.4 ms transition error pass the existing relative diagnostics.

## Execution prompt

Work on `devel` in WsprryPico, preserving unrelated changes. Read the project
contracts. Implement a bounded portable Type 1 WSPR encoder (ordinary callsign,
four-character locator, exact supported power), separate from SDK and RF
adapters. Inspect and retain source provenance. Add a bench command that encodes
and prepares all 162 symbols before local RP2350 launch. Preserve synthetic
frames, STOP/recovery, correction, USB disconnect cleanup and standard inhibited
firmware; do not change WTP or add production UTC scheduling in this slice.

Test known vectors, invalid inputs, job/sample boundaries and bench recovery.
Build the Pico 2 W 138 MHz image, record its exact identity, flash using software
BOOTSEL, and run finite encoded frames on GP2/GND through the reported 60 dB
attenuation/combiner into the RSP1B on wspr5. Use the authorized simultaneous
GPSDO output 1 reference. Decode captured RF using independent WSJT-X wsprd,
recording all IQ-to-audio transformations and exact expected message matching.
Use repeated RF-loaded frames to assess settling and compare their frequency
residuals. Do not disguise offline compensation as generator improvement.

Accept the measured better-than-WsprryPi close-in sidebands as the operator's
practical benchmark. Planned output filtering remains part of final hardware;
no claim is made that a low-pass filter removes 120 Hz sidebands. Preserve failed
measurements and distinguish successful decoding from UTC or broad RF
qualification. Perform adversarial review, repair actionable defects, rerun
checks and reassess. Stop Pico output and disable the reference after tests.
Update the roadmap with actual results, commit attributable changes, push devel,
and report tests, evidence, limitations and repository state.

## Implementation and evidence setup

The portable encoder lives in `src/encoding/`, uses strict Type 1 validation and
fixed-size symbol arrays, and is linked independently of Pico SDK. The bench
converts its complete output into the existing event job before preparation and
local launch. Standard WTP firmware remains inhibited; no protocol changes.
The operator can select one additional RF warmup frame in the capture client;
this is not an automatic transmission policy or a runtime drift compensation law.

Target: Pico 2 W/RP2350 `0BF4B4AEC9FFB344`, GP2 physical pin 4 and GND pin 3,
138 MHz PIO/DMA, correction 2222 ppb, source revision `4a065fe77faa-dirty`.
Verified flash UF2 SHA-256:
`686c8389145b3e971b0bbc57f9235f3952194f587d8212b02f47d593d82605a7`.
The image predates the final documentation/test commit and is not relabeled.
Its path is `build/rf-wspr-evidence/image/WsprryPico-RFBench.uf2`.

The reported 60 dB attenuator/combiner path feeds wspr5 RSP1B `2404058C60`.
Capture uses CF32, 250 kS/s, 200 kHz bandwidth, 3.55 MHz center, 20 dB gain,
channel 0, AGC/bias off. The existing receiver helper was rehashed:
`b98de116d696846b88eea1b3ad3f1b2a471052fa2ca440f4234fec7087dc5a03`.
GPSDO `0673ED0FA107` output 1 supplies 3.580000 MHz at low level, with SAT/PLL
lock recorded. Reference error subtraction is used only for diagnostic frequency
measurements. No correction is applied to the audio sent to wsprd.

Independent decoder: installed WSJT-X `wsprd`, SHA-256
`8a5acb25fe8c7072f2157b03fadc1d21543f1ddf432f609fd6907f095dfba2a3`.
IQ is Hann-decimated to complex 1 kHz, interpolated with a 241-tap Hann-windowed
sinc to 12 kHz, translated to real 1500 Hz audio, amplitude-normalized, and padded
with trailing silence to 120 seconds. There is no frequency/drift correction or
time shift. The filename is a synthetic slot label, not UTC evidence. Decoder
arguments are `-d -H -f 3.568600 WAV`; expected message matching follows decoding.
The dBm field is encoded metadata, not calibrated transmitter power.

First and second frames both decoded `AA0NT EM18 20`. Their measured durations
were exactly 110.592 seconds at the receiver's nominal sample rate. First-frame
linear frequency-fit residual was 0.112776 Hz; the second was 0.103548 Hz. Both
slightly exceed the unchanged 0.1 Hz diagnostic limit. All actual tone
transitions were resolved, with maximum errors 1.2 ms and 0.5 ms respectively.
The 69.230 second idle gap makes this a repeat test, not continuous RF warmup.
The first frame's descriptive exponential fit had amplitude 0.53157 Hz and
58.94 second time constant; this is not proof of a thermal cause.

A wrong-message control requested `AA0NT EM18 37` against the first capture. It
correctly returned failure even though wsprd exited successfully and decoded
`AA0NT EM18 20`. No expected symbols are supplied to the independent decoder.

## Reproduction

Use a new output directory and the exact currently flashed revision/image. The
recorded tight-warmup experiment is:

```sh
python3 scripts/capture_rf_bench.py \
  --port /dev/cu.usbmodem2103 --serial 0BF4B4AEC9FFB344 \
  --revision 4a065fe77faa-dirty \
  --firmware build/rf-wspr-evidence/image-r3/WsprryPico-RFBench.uf2 \
  --output build/rf-wspr-evidence/new-warm \
  --attenuation-db 60 --correction-ppb 2222 --gpsdo-reference \
  --wspr AA0NT EM18 37 --rf-warmup
```

This explicitly requests two finite 110.592-second transmissions. Decode its
`capture.cf32` and `capture.json` with `scripts/decode_rf_wspr.py`, a new output
directory, the installed wsprd path, and `--expect AA0NT EM18 37`. Run offline
analysis with the existing Harness virtual environment, which provides NumPy
and the capture reader's Harness imports. No new packages were installed.

## Adversarial assessment

Review checked encoder length/range validation, 50 payload plus 31 tail bits,
convolution/interleave ordering, exact power handling, callsign padding and
all-symbol job construction. Tests include both retained upstream vectors,
invalid/unsupported identities, grid and power limits, complete event mapping,
STOP/rearm and lost-command cleanup. The firmware image passed its 16 KiB stack
layout check and the first two target frames reported no engine diagnostic failure.

Measurement review repaired handling of repeated adjacent symbols and verified
that IQ-to-audio conversion preserves frequency offset and quiet intervals.
An initial SciPy dependency was removed in favor of the existing NumPy runtime.
Decoder success requires an exact expected message, not simply exit status;
the mismatched-power control fails as intended. Decoder execution failure writes
a failed evidence record. Capture warmup failure prevents the measured frame and
still disables the reference; this path is failure-injected in host tests.

A second review checks the final implementation and retained target evidence,
with failed cold-frame diagnostics preserved separately from successful decodes.
The sideband benchmark is operator-accepted; it is not used to prevent progress.

## Completion-race repair

The first tight-warmup capture (`frame-warm`) decoded the changed message
`AA0NT EM18 37` and passed the unchanged relative RF diagnostics: maximum
frequency residual 0.043500 Hz, transition error 0.6 ms, duration 110.592 s.
However its transmitter returned `completion_deadline` at nominal end +61 us.
It is retained as successful received RF with a failed firmware lifecycle, not
as an entirely successful run.

Review found the old 100 us allowance required all final-data IRQ progress to
already be acknowledged. A pending final-data IRQ can leave conservative progress
at the previous block even after nominal RF completion. The repair permits
that final block's acknowledgement to be outstanding only when the complete
waveform has been generated and every block submitted. The 100 us bound is
unchanged. Missing acknowledgements still stop/fail after it, and two outstanding
blocks cannot use the allowance. Tests inject late final-data and zero-tail
acknowledgements independently, missing acknowledgements and excess pending work.

The repaired image is `build/rf-wspr-evidence/image-r2/WsprryPico-RFBench.uf2`,
verified flash SHA-256
`a3d106bd01e720ecc37771a4e78b245f803304477b00b75973472af8f592f80f`.
Both images advertise the same pre-commit revision string; their SHA-256 hashes
are distinct and authoritative for these records.

The first r2 warmup attempt stopped with `sink_state` about 66 us after launch;
the capture coordinator did not start the measured frame and disabled the
reference. Review identified mixed observations: `PioDmaSink::poll` could return
an armed snapshot, then its unlock admitted the launch IRQ, after which the
engine queried live output activity and falsely treated the launch as early.
The final repair snapshots output activity with sink state/time under the same
lock. An injected alarm on snapshot unlock now returns a consistent armed
snapshot and progresses to running on the next poll without failure. This does
not relax the hardware launch deadline.

Final r3 image verified flash SHA-256:
`56256143b088f78598323bd3357aa138ec7766b1725f900be8cffe985e838131`,
path `build/rf-wspr-evidence/image-r3/WsprryPico-RFBench.uf2`.
All failed attempts remain in the ignored evidence directory.

## Final results and reassessment

The final r3 warmup and measured frame both completed with empty engine
diagnostics. The gap was 2.30441 s. The measured message decoded as
`AA0NT EM18 37`; duration was 110.592 s, fitted spacing 1.466935 Hz, maximum
linear-fit frequency residual **0.037243 Hz**, and maximum transition error
**0.4 ms**. All existing relative checks passed without changing thresholds.
The warmup comparison reduced the residual from the first cold frame's
0.112776 Hz by about 67%. This is measured settling improvement in this setup,
not automatic frequency compensation or proof of a temperature model. Fitted
reference-compared base was 3570098.700240 Hz; fixed correction 2222 ppb is not
claimed to be an absolute calibration across temperature or power cycles.

The final snapshot reports stopped/output inactive, 138 MHz, correction
2222 ppb, 58,222 DMA IRQs over the two complete frames, maximum IRQ callback
37 us, and stack canary use 9,908 bytes of 16,384 reserved. The GPSDO reference
was disabled and verified. The wspr2 service/configuration was not changed in
this task. Captures have verified hashes/settings, zero overflow and zero
clipped samples. Captures, logs and firmware remain ignored under
`build/rf-wspr-evidence/` and captures also remain in recorded wspr5 `/var/tmp`
directories.

| Capture | CF32 SHA-256 | Image | Outcome |
| --- | --- | --- | --- |
| frame-1 | `e312c0091c9a485ef893bbd7a01b6e6d1d91529d4a3af4d2f8e0d20c0600e9ac` | initial | Decoded 20; cold residual fails |
| frame-2 | `7f9b192613c1451f31f7e1843596775cfcb96b16c2f546469c5f91147f60565e` | initial | Decoded 20; residual fails |
| frame-warm | `d0a849204bfb4b9f53f259ad1126416f1a414690d6dcc07fd76fa036762cf401` | initial | Decoded 37; RF checks pass; lifecycle fails |
| frame-warm-r3 | `e2e9c5d11b1f51403b0f4a6e244ba816835fc5d83e304d7f4b70afaa96bb6c89` | r3 | Decoded 37; RF checks and lifecycle pass |

After both IRQ repairs, final adversarial reassessment found no remaining
actionable implementation defects in this slice. Debug 138 MHz passed 15/15,
Release 132 MHz 11/11 and ASan/UBSan 150 MHz 11/11. Tests were rerun after the
repairs. Bench, standard firmware and driver link-check targets build; the final
bench UF2 remains byte-identical to the flashed r3 artifact. C++ formatting,
Python compilation, WTP contract validation and local Markdown links pass.

Step 8 remains open for production UTC/time uncertainty and RF job-service
integration. These successful bench decodes do not establish UTC alignment,
out-of-band harmonic performance, calibrated sample timing or filtered band
qualification. The operator-accepted better-than-WsprryPi close-in sideband
benchmark is retained as the practical baseline.
