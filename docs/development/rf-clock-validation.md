# Sample-clock and settling comparison

Experimental Step 8 investigation, 2026-09-06. Carrier requests remain at
3.570100 MHz plus the four WSPR tone offsets. The simultaneous GPSDO reference
remains at 3.580000 MHz. The 132/138/150 MHz values below refer to the internal
RP2350 system/PIO sample clock, not the transmitted carrier frequency.

## Executed prompt

Work in devel. Compare supported sample-clock choices with an independent
sampled-waveform model, including nearby aliases, tone quantization and exact
symbol timing. Implement justified experimental choices without changing WTP or
production engine selection. Build, flash and benchmark the Pico, then perform
finite SDR/GPSDO comparisons and repeated full-frame settling measurements.
Compare an ordinary frame with sustained CPU activity before a frame. Preserve
failed diagnostics and exact image/capture identities. Proceed to encoded WSPR
verification only if the results justify it; otherwise record the specific
remaining RF engineering work. Review adversarially, repair and reassess,
validate, update the roadmap, commit and push devel.

## Clock implementation

`WSPRRY_PICO_RF_SAMPLE_RATE_HZ` is a CMake cache setting accepting 132000000,
138000000 (the new experimental default) or 150000000. Unsupported values fail configuration and have a C++
static assertion as a second check. It applies to the experimental RF library
and bench; the normal inhibited WTP firmware does not select this engine.

For an experimental build:

```sh
cmake -S . -B build/pico2-w -DWSPRRY_PICO_RF_SAMPLE_RATE_HZ=138000000
cmake --build build/pico2-w --target WsprryPico-RFBench --parallel
```

The bench calls the SDK's `set_sys_clock_khz` before starting USB or claiming RF
peripherals. INFO reports the configured system clock; CAPS reports the planned
sample rate, and the driver requires agreement before starting. The SDK clock
report is configuration readback, not an independent frequency measurement.
See the [official clock API](https://www.raspberrypi.com/documentation/pico-sdk/hardware.html).
The pinned SDK's `vcocalc.py 138` gives REFDIV 1, feedback 115, VCO 1380 MHz,
post-dividers 5 and 2; no overclock is used.

NCO increments are recalculated to preserve the requested carrier. The existing
ppb correction still acts on those increments, not the PLL. Timestamp conversion
uses the reduced sample-clock/nanosecond ratio to avoid overflow. Each WSPR
symbol has exactly 90,112,000 / 94,208,000 / 102,400,000 samples at 132 / 138 /
150 MHz respectively. Frame duration remains 110.592 nominal seconds. A physical
oscillator error still affects physical time and frequency.

## Model and limits

`scripts/compare_rf_clocks.py` compares 120–150 MHz in 3 MHz steps, showing legal
integer PLL settings and odd-harmonic aliases through harmonic 10001 within
100 kHz of tone 0. The strongest ideal individual coefficient is approximately
-32.26 dBc at 150 MHz, -63.17 dBc at 132 MHz and -66.06 dBc at 138 MHz. The
finite search does not bound the sum of aliases or analog clock/power noise.
The selected 138 MHz clock is also tested with an independent per-sample
32-bit accumulator model, not the optimized C++ word lookup implementation.
This study is for the recorded carrier; it does not establish band coverage.

## Setup and evidence

Same Pico 2 W `0BF4B4AEC9FFB344`, GP2 physical pin 4/GND physical pin 3,
operator-confirmed 60 dB attenuation and combiner as the
[preceding comparison](rf-correction-validation.md). Receiver: wspr5 RSP1B
`2404058C60`, CF32 250 ksample/s, 200 kHz bandwidth, center 3.55 MHz, gain 20 dB,
AGC and bias tee off. GPSDO LBE-1421 `0673ED0FA107`, output 1 LOW at 3.58 MHz,
locked before testing and disabled after each capture. No frozen calibration
profile is applied; frequency comparison subtracts the simultaneous indicated
reference error, with no independent sample-rate calibration.

Raw captures, manifests and image files are retained locally under ignored
`build/rf-clock-evidence/`. Firmware build revision is `39a144935f72-dirty`,
SDK 2.3.0 and Arm GCC 15.3.1 Release. Image hashes distinguish the clock builds;
a later commit identity must not be substituted for the measured image.

The first full-frame attempt (`frame-1`) completed on the Pico but the receiver
reported `io_or_source_error`. Its `/tmp` tmpfs had only 116 MB available versus
233 MB required for a complete capture; no completed receiver metadata was
available. Storage exhaustion is the supported explanation, not a timing pass.
The capture wrapper now uses disk-backed `/var/tmp` and checks required space
plus 32 MiB before any reference or transmitter work. Existing captures were
preserved. A free-space check cannot prevent another process filling the disk
later, so capture completeness checks remain necessary.

## Full-frame and preheat observations

The 138 MHz bench measured a worst CPU refill of 1.529 ms against a 3.799 ms
block period. Both successfully received full frames lasted 110.592 s. Their
original diagnostic checks failed: all 161 transition fits were flagged as
ambiguous, and linear frequency residuals exceeded 0.1 Hz. Strong close-in
sidebands were present; fitted transition coordinates are therefore not timing
qualification.

| 138 MHz frame | Maximum linear residual Hz | Descriptive transient Hz | Fitted time constant s | Held-out maximum residual Hz |
| --- | ---: | ---: | ---: | ---: |
| ordinary (`frame-2`) | 0.104003 | 0.347664 | 47.18 | 0.037736 |
| after CPU activity (`frame-preheated-1`) | 0.111970 | 0.334578 | 43.06 | 0.028183 |

Preheat comprised ten BENCH 4096 invocations: 61.57 s measured generation work
spread across 112.33 s wall time, followed by 18.67 s before the frame client
started (plus its launch delay). It did not materially reduce the fitted
transient in this protocol. It was not continuous RF warm-up, did not reproduce
the GPIO load, and included idle gaps. It does not rule out an uninterrupted
RF preamble or another controlled warm-up procedure. No compensation law was
inferred from these fits and no failed threshold was loosened.

The user confirmed no USB power or wiring change since the preceding session
and requested a carrier translation to distinguish fixed-frequency QRM from
features following the transmitter. The test changes only the NCO correction
from 2222 to -80000 ppb, moving the actual carrier approximately 294 Hz upward,
then restores 2222 ppb. The large negative setting is an intentional diagnostic
frequency offset, not an accepted clock calibration. Receiver tuning, hardware
sample clock, GPSDO and wiring stay fixed during this pair.

## Carrier translation and Pi comparison

Same one-million-sample Hann FFT beginning two seconds into each capture;
peak-bin ratios within 5 Hz of each expected feature are relative to that
capture's carrier. Bin spacing is 0.238419 Hz. These are diagnostic peak ratios,
not calibrated integrated power or emissions qualification.

| Source | Lower 120 Hz sideband dBc | Upper 120 Hz sideband dBc |
| --- | ---: | ---: |
| Pico 138 MHz, shifted carrier | -26.71 | -27.95 |
| Pico 138 MHz, restored carrier | -25.06 | -25.66 |
| Pico 132 MHz | -25.13 | -26.13 |
| Pico 150 MHz, successful repeat | -26.54 | -26.79 |
| wspr2 GPIO4 | -21.66 | -21.49 |

On the repaired 138 MHz image, indicated carrier peaks moved from
3,570,398.378 Hz back to 3,570,104.885 Hz. The sidebands moved with the carrier,
remaining approximately +/-120 Hz away. This argues against fixed-frequency
QRM. The frequency-analysis tool now accepts an explicit `--base-hz` for these
intentional translations, remixes about that value and retains the existing
coherence/range criteria. The shifted test used 3,570,393.56 Hz as its expected
base; original failed analyses were preserved rather than overwritten.

The user authorized wspr2 GPIO4 and confirmed its combiner connection. wspr2
was Raspberry Pi Zero 2 W Rev 1.0, installed WsprryPi
`3.2.0-devel+7b92f69`, GPIO4, GPIO drive level 7, manual PPM zero. Executable
SHA-256: `b56fa888935fee346c7c12eb84955e0745cdba6871b6a6b10a810fdc3e6f13f8`.
Its running service was temporarily stopped for a direct 3.570100 MHz CLI tone,
then restored. A 12-second SIGINT timeout ended the run; the application logged
11.951998 seconds of transmission, cancellation and clean exit. GPIO auxiliary
controls were disabled for this invocation. No Pi configuration or source was
changed.

The Pi carrier was substantially weaker at the receiver than the Pico. Its
sidebands nevertheless stood 24–26 dB above their local median noise floors, so
these are detected features, not noise-floor upper limits. The standard burst
analyzer did not acquire the weak Pi burst; the Pi comparison therefore uses
an explicitly bounded spectral window, not a passed phase/timing result. Pi-leg
attenuation was not independently specified. Close-in carrier-relative ratios
are useful here, but absolute levels cannot be compared as transmitter power.

The Pi shows the same pattern, roughly 4–5 dB worse than the Pico captures.
The GPSDO's corresponding bins were around -69 to -71 dBc relative to the Pico
carrier, much lower. Power/ground coupling is a candidate explanation, not a
proved cause; receiver/source interactions are not fully excluded.

The original 3.513971 MHz alias measured -33.82 dBc in the fresh 150 MHz control.
At its former location the 138 MHz restored capture was -77.82 dBc, a roughly
44 dB reduction of that feature. Other aliases move when the sample clock
changes; this is not a 44 dB improvement in the worst spur across all bands.
The 138 MHz profile is selected for the experimental bench because it removes
that alias without creating the observed close-in pattern, which also exists
at 150 MHz and on the Pi. The remaining close-in sidebands and failed frame
checks prevent any RF qualification claim. Encoding/decoding and production
UTC integration remain subsequent work.

## Review repairs and validation

Review and target testing found remaining 150 MHz assumptions in sink progress
and sample limits; these now use the selected clock. A target end-of-run
acknowledgement race is covered by a bounded 100 microsecond tail-completion
allowance, restricted to fully generated/submitted jobs at their final reported
sample. A missing tail still fails and stops output. Tests inject delayed and
missing acknowledgements and check progress at a fixed elapsed time for all
three profiles. No waveform samples or SDR diagnostic thresholds were added.

One original shifted run stopped with `completion_deadline`; its RF spectrum
was retained as diagnostic evidence and the repaired image repeated the test
successfully. One 150 MHz control missed its local launch and reported
`sink_state` with no launch observation; its successful repeat is reported
separately. An initial flash attempt preceded bootloader enumeration; verification
succeeded after enumeration. No failed attempt is counted as passing hardware
evidence.

Debug 138 MHz tests passed 15/15, Release 132 MHz 11/11, and Address/Undefined
Behavior sanitizer 150 MHz 11/11. Affected tests were rerun after review changes.
All three bench images built and passed the 16 KiB stack/heap layout check;
standard firmware and driver link-check targets also built. WTP contract checks,
C++ formatting, Python compilation and documentation links passed. A second
adversarial assessment found no remaining actionable implementation defects in
this slice. The physical sideband and settling findings remain open.

## Retained artifact identities

| Capture | CF32 SHA-256 | Image |
| --- | --- | --- |
| tone-1 | `4e0dee23512c1a58d3dd9292eb7b33f31683bb7adb6013e7780b408b86d2ddfa` | image-1 |
| frame-2 | `c38f5e83aaf7892e39b77d65e4ab83577c25a619895542eafb49768dbd96ff42` | image-1 |
| frame-preheated-1 | `37dd123ba23f1d63f8eafd82708ba254187de05ef2ead70b676bed10516c0e41` | image-1 |
| tone-shift-138-r2 | `a005dc2ae3473524ff6dc5de9b7031932da2934996fc59228b632ca0aa525ca7` | image-138-r2 |
| tone-restore-138-r2 | `d4225dc67d9d36404373bf8b4030a2e02474cc97a11c780f4a4f71247fbd775a` | image-138-r2 |
| tone-132-r2 | `3a59e4fbbd3edbba2c0dcf6e29476c8f724c1732c7f6715d550d71e18d5dc6f4` | image-132-r2 |
| tone-150-r3 | `ccbb54ce6ad13cd7fad4c5e11908421987e98792133ae2c0b604c8173f39f96f` | image-150-r2 |
| pi-gpio4 | `85f046229f9bdd615bf7841f1fc971b9bd623beadd088581f92cd7fa95e56c15` | installed Pi executable |

| Image | UF2 SHA-256 |
| --- | --- |
| image-1 | `952d5ebe1feea57b6c01ab940a793d9a4094d5450e18305aa3ecd7628b89196c` |
| image-138-r2 | `aaad42d25247969ebd70ee6f979fe69519ed465c3b0777e36efb81d74e326b37` |
| image-132-r2 | `e7cb5973e1a806de9ba0c641866ea66057669258a13dd786587b4990327a05b6` |
| image-150-r2 | `fe15c0cd76d953187067ca60ca89d924198c93bf9320d6044b00622fa8b0ce84` |

The full-frame captures precede the progress/tail review repairs. The repaired
138 MHz image was verified by short shifted/restored tones and host full-frame
checks; those earlier failed physical frame checks are not relabeled as final
image qualification. The final flash matches image-138-r2 byte for byte. Final
STATUS reports 138 MHz, correction 2222 ppb, stopped and output inactive. The Pi
test tone exited, its prior service was restored, and GPSDO output 1 was disabled.
