# Pico RF bench

The separately built `WsprryPico-RFBench` image provides CPU benchmarks and finite
GP2 tones. It boots idle, uses USB CDC Commands, and reports
`monotonic-relative-only` with `utc_synchronized=false`. It has no WTP endpoint;
these commands neither change WTP nor establish UTC timing conformance. The
standard `WsprryPico` build remains the inhibited WTP endpoint. The operator
chooses transmissions and measurements.

The subsequent [stream completion contract](rf-stream.md#completion-and-local-state-observations) adds `FRAME`,
intentional abort/rearm, higher-resolution analysis and simultaneous GPSDO
comparison. Reference ratios remain tied to their identified source and setup.

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
  --firmware build/rf-bench/firmware/WsprryPico-RFBench.uf2 \
  --output build/rf-bench/benchmark benchmark --blocks 128
```

Actions are `status`, `stop`, `benchmark`, `run`, `frame`, `wspr` and `bootloader`. A run accepts
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


## Encoded WSPR

The portable `encoding::wspr_type1` encoder accepts uppercase ordinary Type 1
callsigns (3–6 characters, with the digit normalized to position three), exactly
four locator characters (`AA00`–`RR99`), and the standard powers 0–60 dBm ending
in 0, 3 or 7. Unsupported inputs are rejected; Types 2/3, slashes, six-character
locators and lowercase normalization are not implemented. The power is a
message field, not a measurement or adjustment of GPIO output power.

`WSPR <call> <grid> <dbm> <delay_ms>` prepares all 162 symbols before local launch.
The host action is `wspr --call AA0NT --grid EM18 --dbm 20`, using the same
identity/output arguments shown above. `FRAME <delay_ms>` remains the synthetic
cycle4 workload. Both last 110.592 seconds and use the existing STOP, disconnect
and error recovery paths. `CAPS` advertises `wspr: "type1"`.

For capture, add `--wspr AA0NT EM18 20` to `capture_rf_bench.py` instead of
`--frame`. Optional `--rf-warmup` transmits **one additional full frame** before
starting the measured capture, retaining a separate warmup transcript. It is
available only for complete frames and stops if that warmup fails. This is an
operator-selected experiment, not automatic idle RF or a transmission condition.

The offline `decode_rf_wspr.py IQ METADATA OUTPUT --wsprd PATH --expect CALL GRID
DBM` command uses the existing Harness Python environment and independently
installed WSJT-X decoder. It verifies capture hashes, completion, overflow and
clipping; converts to 12 kHz mono audio; and requires an exact decoded message.
Audio preserves captured elapsed time, frequency error and drift. The synthetic
WAV slot name and trailing silence do not establish UTC alignment. For encoded
frequency measurements, pass the 162 tone digits using `measure_rf_bench.py
--symbols DIGITS`; equal adjacent symbols have no physical transition to test.
The [bounded Type 2/3 decode scope](wspr-planning.md#conducted-type-23-applicability) is
independent of this bench tool.

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
  --firmware build/rf-bench/firmware/WsprryPico-RFBench.uf2 \
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

## Validation boundary

The bench is an opt-in experimental tool. Use installed dependencies and the
[development checks](README.md#deterministic-validation) for generator, sink,
controller failure/STOP and offline capture-analysis behavior. Neither a
cross-link nor a fake peripheral proves IRQ timing or electrical output. The
[clock policy](clock-support.md) defines build-selected rates; the
[band support guide](band-support.md) bounds conducted applicability. Bench
relative time is unsynchronized and does not establish WTP UTC conformance.

## Conducted reference benchmark

The close-in analysis tool uses a fixed Pi GPIO4 diagnostic reference of
**-21.66 dBc at the lower 120 Hz feature** and **-21.49 dBc at the upper
120 Hz feature**. The reduction uses a 1,048,576-sample Hann FFT at 250 ksample/s
(0.238419 Hz bins), starting two seconds into a capture, with peak searches
within five Hz of each expected feature relative to that capture's carrier.
These are peak-bin ratios, not calibrated integrated power or emissions limits.

The reference is Raspberry Pi Zero 2 W Rev 1.0 on wspr2, WsprryPi
`3.2.0-devel+7b92f69`, GPIO4 drive level 7, manual PPM zero, nominal 3.570100 MHz,
executable SHA256 `b56fa888935fee346c7c12eb84955e0745cdba6871b6a6b10a810fdc3e6f13f8`.
Its confirmed conducted combiner path, different RF windows/measurement date
and uncalibrated receiver/path remain limitations. Passing this numerical
comparison does not establish an absolute spectral limit or qualify a new image.
