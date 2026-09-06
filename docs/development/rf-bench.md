# Pico RF bench and initial target evidence

The separately built `WsprryPico-RFBench` image provides CPU benchmarks and finite
GP2 tones. It boots idle, uses USB CDC Commands, and reports
`monotonic-relative-only` with `utc_synchronized=false`. It has no WTP endpoint;
these commands neither change WTP nor establish UTC timing conformance. The
standard `WsprryPico` build remains the inhibited WTP endpoint. The operator
chooses transmissions and measurements.

The subsequent [full-frame validation](rf-frame-validation.md) adds `FRAME`,
intentional abort/rearm, higher-resolution analysis and simultaneous GPSDO
comparison. The initial results below remain tied to their original images.

## Build and connection

Follow the pinned inputs in [firmware foundation](firmware-foundation.md), then:

```sh
cmake --preset pico2-w
cmake --build build/pico2-w --target WsprryPico-RFBench --parallel
```

The UF2 is `build/pico2-w/firmware/WsprryPico-RFBench.uf2`. Build explicitly: the
bench target is excluded from the default build. Connect signal to **GP2,
physical pin 4**, return/shield to **GND, physical pin 3**. With USB at the top,
these are on the left from the component side and right from the underside.
Follow GP2/GND labels, not a side description alone. The power row is opposite.

The recorded board serial is `0BF4B4AEC9FFB344`. On the recorded Mac, Console is
`/dev/cu.usbmodem2101` and RFBench Commands is `/dev/cu.usbmodem2103`; paths can
change. The host client requires the expected board serial, firmware revision
and exact supplied UF2. Its hash records that file; USB INFO is not flash readback.

Example with the recorded image (use the actual current revision/image for a
new build and a new output directory for each invocation):

```sh
python3 scripts/rf_bench.py \
  --port /dev/cu.usbmodem2103 --serial 0BF4B4AEC9FFB344 \
  --revision d35dffce91a3-dirty \
  --firmware build/rf-target-evidence/image-9/WsprryPico-RFBench.uf2 \
  --output build/rf-target-evidence/new-benchmark benchmark --blocks 128
```

Actions are `status`, `stop`, `benchmark`, `run` and `bootloader`. A run accepts
`--tone 0..3`, `--duration-ms 1..10000`, `--delay-ms 100..10000`. Each action verifies
INFO/CAPS first. RUN and BENCH finish with STOP, including on errors/timeouts.
The firmware also stops on Commands disconnect. Failure to confirm stop is an
error, retained in the transcript. There is no automatic transmission retry.

Wire commands are newline-delimited `INFO`, `CAPS`, `STATUS`, `STOP`, `BOOTSEL`,
`BENCH <blocks>` and `RUN <tone> <duration_ms> <delay_ms>`. Responses are JSON lines.
Only one request may be outstanding. Firmware bounds input length and rejects
an overlong command through its newline. INFO reports cumulative IRQ count,
maximum IRQ callback duration, last observed launch, allocator arena statistics
and stack canary estimate. STATUS includes the last CPU benchmark metrics; they
are not a measurement of RUN rendering. Timer observations resolve microseconds.
The heap-free field is allocator arena space, not total available SRAM.

## Flashing without the button

The bench `bootloader` action sends STOP followed by software BOOTSEL entry. It
was exercised repeatedly. When the application is unavailable, holding BOOTSEL
while connecting USB remains the recovery path. Once BOOTSEL is entered, release
the button. A working application can enter BOOTSEL without another button press.

macOS sometimes enumerated RP2350 Boot without mounting its storage volume.
Direct USB flashing worked with a USB-enabled picotool built from the existing
pinned source and installed libusb 1.0.30:

```sh
cmake -S build/pico2-w/_deps/picotool-src -B build/picotool-usb \
  -DPICO_SDK_PATH="$PICO_SDK_PATH" -DPICOTOOL_NO_LIBUSB=OFF \
  -DCMAKE_BUILD_TYPE=Release
cmake --build build/picotool-usb --parallel
build/picotool-usb/picotool load -v -x \
  build/pico2-w/firmware/WsprryPico-RFBench.uf2 --ser 0BF4B4AEC9FFB344
```

Use the configured SDK path. `-v` verifies written flash before `-x` reboots.
The SDK's existing file-only picotool may have USB disabled; it cannot substitute
for this build. These are device-writing operations, not build checks.

## SDR capture and Harness analysis

The recorded path is GP2/GND through **two 20 dB and two 10 dB attenuators,
60 dB total**, into wspr5's SDRplay RSP1B serial `2404058C60`. No additional
DC block, resistor network or filter was confirmed. Attenuation is recorded as
reported by the operator, not independently measured. Receiver gain is 20 dB,
center 3.55 MHz, sample rate 250 kS/s, bandwidth 200 kHz, channel 0, AGC off,
bias tee off. No GPSDO or receiver service configuration was changed.

The existing Harness checkout on wspr5 was clean at
`d69da41a4d5ae14fc6a451889e153c2aaf48ce09`. Its native helper was built outside
that checkout, without changing the Harness repository:

```sh
ssh wspr5 'cmake -S ~/WsprryPi-Qualification-Harness -B /tmp/wsprrypico-capture-build -DWSPQ_BUILD_SOAPY=ON -DWSPQ_BUILD_TESTS=ON -DCMAKE_BUILD_TYPE=Release'
ssh wspr5 'cmake --build /tmp/wsprrypico-capture-build --parallel 2'
ssh wspr5 'ctest --test-dir /tmp/wsprrypico-capture-build --output-on-failure'
```

Both native helper tests passed. The helper executable SHA-256 was
`b98de116d696846b88eea1b3ad3f1b2a471052fa2ca440f4234fec7087dc5a03`.
The capture coordinator uses that helper directly, waits for retained samples,
commands one finite Pico tone, waits for receiver cleanup, and downloads IQ and
metadata. It verifies hash, sample count, device and settings. It does not invent
a WsprryPi transmitter profile or promote evidence to a Harness qualification.

```sh
python3 scripts/capture_rf_bench.py \
  --port /dev/cu.usbmodem2103 --serial 0BF4B4AEC9FFB344 \
  --revision d35dffce91a3-dirty \
  --firmware build/rf-target-evidence/image-9/WsprryPico-RFBench.uf2 \
  --output build/rf-target-evidence/new-capture --attenuation-db 60 \
  --tone 0 --duration-ms 1000
```

The local POSIX client uses the Python standard library. Offline analysis needs
NumPy and the existing Harness Python environment. Run from this repository:

```sh
../WsprryPi-Qualification-Harness/.venv/bin/python scripts/analyze_rf_bench.py \
  build/rf-target-evidence/new-capture/capture.cf32 \
  build/rf-target-evidence/new-capture/capture.json \
  build/rf-target-evidence/new-capture/analysis --tone 0
../WsprryPi-Qualification-Harness/.venv/bin/python tests/rf_bench_analysis_tests.py
```

Analysis validates the raw capture, finds energy increases near the requested
tone, and passes a whole-window burst crop plus a leading quiet interval to the
Harness carrier analyzer. Every detected interval is retained; choosing the
strongest is diagnostic and could select unrelated interference. Cropping does
not trim quiet edges to manufacture a pass. The 4096-point FFT has 61.035 Hz bins
at this sample rate and cannot resolve 1.465 Hz WSPR spacing. Frequency and power
are uncalibrated. Reported carrier classifications remain unchanged.

## Recorded results, 2026-09-05 local / 2026-09-06 UTC

Board: Pico 2 W / RP2350, serial above, clk_sys 150 MHz, GP2 PIO/DMA engine.
Host: Lees-MacBook-Pro, macOS; SDK 2.3.0, Arm GCC 15.3.1. Images reported
`d35dffce91a3-dirty`; hashes below distinguish the revisions. Build artifacts,
source hashes, USB transcripts, raw IQ and metadata are retained under the
ignored `build/rf-target-evidence/` directory, not committed firmware/captures.

| Workload | Result |
|---|---|
| Original BENCH 128, image-1 | Worst render 22.092 ms; checksum 4503602371141397 |
| Optimized BENCH 128, image-9 | Worst render 1.507 ms; total rendering 189.886 ms; same checksum |
| Image-9 RUN 0 100 1000, capture-6 | Complete; output inactive; STOP confirmed; 30 DMA IRQs |
| Image-9 RUN 0 1000 1000, capture-7 | Complete; output inactive; STOP confirmed; 288 additional DMA IRQs |
| Image-9 RUN 3 100 1000, capture-8 | Complete; output inactive; final capture coordinator checks passed |
| Recorded image-9 workload | Maximum observed DMA callback 37 us; stack canary 9652 / 16384 bytes |
| Capture-6, 1,525,000 samples | Hash/count/cleanup verified; zero timeout, overflow or clipping samples |
| Capture-7, 1,750,000 samples | Hash/count/cleanup verified; zero timeout, overflow or clipping samples |

Original image-1 UF2 SHA-256:
`a9f13dc919b9ceaab94cc165f285c27ba45c9de80fc4234b2fe6e866523f344e`.
Tested image-9 UF2 SHA-256:
`6ac2e13fae05a7c2ad2e4e7c1ef92200d853cc7e4d0d54fa9e5c607046932c10`.
Capture-6 IQ SHA-256:
`a7e4d48b1e52621ffdd86ee0d3c51c1810256c05c06acb3069ae5c599516911a`.
Capture-7 IQ SHA-256:
`da678011460084fb4c75adf745713fadecdada5d1e3aa7b91f1dfde785c40298`.

The final benchmark used no additional DMA IRQs and reported output inactive.
Its 1.507 ms maximum is below both the 3.495253 ms buffer-consumption time and
the proposed 1.747626 ms render budget for this workload. It does not bound all
jobs or competing loads. The bench holds only a tone job, not a full 162-event
WTP workload. Launch observations were 4 us after requested timer epochs;
completion observations were 66 us and 63 us after nominal ends. Neither is an
independent measurement of pin-edge timing.

SDR analysis detected intervals 1.212416–1.327104 s and 1.212416–2.228224 s
relative to the respective captures, with approximately 65 dB detector contrast.
Whole detector windows include quiet edges. The Harness noise guard classified
both crops **inconclusive**, and relative acquisition did not pass. The strongest
coarse bin was 3,570,141.6015625 Hz; this is not a calibrated carrier frequency.
No band, spectral mask, tone spacing, absolute timing or WSPR decode is qualified.

The final capture coordinator was additionally exercised with tone 3 for 100 ms
(capture-8), with successful terminal state, STOP and receiver verification.
Its IQ SHA-256 is
`3d865dc5847288938e53bda9700a5945ca382d1c4f5fe665bd8dee0815b4e004`.
This checks selection of another tone, not the spacing between tones.

Validation: 11/11 Debug tests including actual USB descriptors, 10/10 Release
and 10/10 address/undefined-behavior sanitizer tests, five optional offline
analysis tests, WTP contract validation, both firmware memory-layout checks,
standard/bench/linkcheck Arm builds, formatting and Markdown links passed.
Reassessment after repairs found no remaining actionable issue in this bounded
bench slice; the qualification limitations above remain explicit.

## Findings resolved and remaining work

Target iteration exposed an over-budget generator, a double timer-read launch
race, an interrupt handoff slower than the FIFO reserve, a late final-drain
underrun, and startup autopull TXSTALL. Exact lookup, one launch-time observation,
two preloaded data channels, the hardware final-stop channel and OSR priming
resolved those observed failures. Earlier failed tone transcripts remain evidence;
they are not counted as successful runs.

Adversarial review also removed a coordinator timeout that could kill the client
before STOP, tightened capture identity/format validation, and preserved manifests
through cleanup errors. Host tests cover waveform boundaries, controller failures,
client timeout/STOP behavior and malformed captures. Hardware-free tests do not
prove peripheral timing. The next work is adequate-resolution frequency analysis
with a verified receiver reference, output spectra/filter characterization,
full-frame and abort/load coverage, and production UTC/WTP integration.

The [frequency correction and alias investigation](rf-correction-validation.md) records the
`CORRECTION` bench command, corrected measurements, remaining frame settling
and identified sampled-square-wave alias.
