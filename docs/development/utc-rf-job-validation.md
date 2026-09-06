# Step 8: USB UTC and WTP RF job integration

Status: implemented and experimentally validated on 2026-09-06. This record
closes the production-job integration software slice. It does not qualify the
USB host as a standalone time source or qualify an unfiltered RF output.

The selected execution prompt is [retained beside this record](step8-utc-rf-execution-prompt.md).
The work adds a portable UTC discipline, a diagnostic-CDC observation exchange,
and an explicitly built `WsprryPico-RFWTP` image joining WTP/1 to the existing
RP2350 PIO/DMA stream engine on GP2. The normal `WsprryPico` image remains RF
inhibited.

## Time and execution model

The host first asks the Pico to sample its monotonic clock. It associates that
exact sample with the midpoint of a host POSIX-clock exchange and submits the
UTC estimate, round-trip uncertainty and leap state. The discipline rejects
future, stale, repeated, overflowing or inconsistent observations. Its
uncertainty grows with age using a configured 50,000 ppb oscillator bound and
changes from synchronized to holdover and then unsynchronized.

This USB source is intentionally modest. Host wall-clock correctness and the
host's `NORMAL` leap declaration are trusted inputs. USB scheduling and midpoint
asymmetry are represented only by the measured round trip plus the supplied host
uncertainty. It is suitable for this controlled integration test, not a claim of
GNSS, NTP, autonomous UTC or leap-table authority.

The RF image advertises only `wspr` and `tone`, the `pio-dma-gp2` engine, and the
four realizable 3,570,100 Hz WSPR tone requests. A job is prepared completely
before ARM. PIO launches from the RP2350 monotonic timer and the DMA schedule
continues without per-symbol USB traffic. The client leaves the WTP connection
quiet while RF is active; the endpoint still accepts ABORT and reacts to physical
disconnect. All observed engine faults during development stopped output and
reported a terminal failure.

## Reproduction

Build and run the hardware-free checks first:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
python3 scripts/validate_wtp_contract.py
cmake --preset pico2-w
cmake --build build/pico2-w --target WsprryPico WsprryPico-RFBench WsprryPico-RFWTP rf_driver_linkcheck --parallel
```

`WsprryPico-RFWTP` is excluded from the default build and must be selected
explicitly. With the image loaded and the operator-selected RF path in place, a
single finite encoded integration job is submitted with:

```sh
python3 scripts/rf_wtp.py --run \
  --time-port /dev/cu.usbmodem2101 \
  --wtp-port /dev/cu.usbmodem2103 \
  --frequency-hz 3570100 --start-delay-s 3
```

The client validates an exact 162-symbol Type 1 golden message, creates a unique
job identifier, performs HELLO/CLAIM/LOAD, observes UTC, arms a future epoch and
waits for the asynchronous terminal event. `--info` reports retained engine
diagnostics. `--bootsel` is accepted only after output is confirmed inactive.

Long captures can be decoded through an explicitly recorded, at-most-120-second
window. Window selection does not change samples inside the window:

```sh
python3 scripts/decode_rf_wspr.py IQ METADATA OUTPUT \
  --wsprd /Applications/wsjtx.app/Contents/MacOS/wsprd \
  --expect AA0NT EM18 37 --start-offset-s 10
```

## Recorded conducted result

The tested source was dirty revision `85f896ea7812-dirty`. The exact
`WsprryPico-RFWTP.uf2` SHA-256 was
`d2665ec4ff1f8b8289ea767d16cd20fc6d24c09d3c223c8194f96b48088ad5fb`.
The Pico 2 W / RP2350 serial was `0BF4B4AEC9FFB344`; WTP device identity was
`fd6127d11d6aca42a9905fa3fb1bf1d5`. GP2 and GND fed the stated 60 dB
attenuator/combiner path to wspr5 RSP1B serial `2404058C60`.

The final run loaded `AA0NT EM18 37` at a 3,570,100 Hz base and requested UTC
start `2026-09-06T14:37:39.488744Z`. The USB observation round trip was
901,000 ns and conservative uncertainty was 1,451,000 ns; ARM reported
1,451,346 ns after aging. Requested monotonic launch was 52,687,768,000 ns.
The target diagnostic sampled launch completion at 52,687,774,000 ns, 6 us
later; this includes launch-call instrumentation overhead and is not a GPIO edge
measurement.

The wspr5 helper SHA-256 was
`b98de116d696846b88eea1b3ad3f1b2a471052fa2ca440f4234fec7087dc5a03`.
It recorded 36,000,000 CF32 samples at 250 kS/s, 200 kHz bandwidth, 3.55 MHz
center and 20 dB gain with AGC and bias tee off. Capture SHA-256 was
`2db5ed191f10dd0b51543651b8763449fe25f6690f169e607412dd88cb57362f`;
overflow and clipping counts were zero, and receiver cleanup was verified.

The capture detector placed RF at 16.279 seconds from its wall-clock-labelled
retained start, or about 102.3 ms after the requested UTC epoch. SDR buffering
and the helper timestamp path are not calibrated for absolute onset, so that
difference is reported rather than treated as transmitter error. The detected
duration was exactly 110.592 seconds. Against the simultaneous locked 3.580000
MHz GPSDO reference, the diagnostic fit reported 3,570,107.1046 Hz base,
1.46630 Hz tone spacing, -0.004684 Hz/s linear drift, 0.1055 Hz maximum symbol
residual and 0.8 ms maximum transition error. Duration and transition checks
passed; the residual exceeded the existing 0.1 Hz diagnostic target by 0.0055 Hz.
This result is retained rather than promoted to RF qualification.

Installed WSJT-X `wsprd` SHA-256
`8a5acb25fe8c7072f2157b03fadc1d21543f1ddf432f609fd6907f095dfba2a3`
independently decoded `AA0NT EM18 37` from samples 2,500,000 through 32,500,000.
No frequency or drift correction and no edits within that selected window were
applied. The power field is encoded message data, not measured transmitter power.

The terminal record was `complete` with `output_active:false`; no engine or sink
diagnostic was present. Device metrics were 29,111 DMA interrupts and a 40 us
maximum DMA callback. GPSDO
`0673ED0FA107` was reread locked with outputs 1 and 2 disabled after capture.

Two earlier captures are retained only as diagnostic evidence. Both transmitters
completed safely, but receiver acquisition and job preparation consumed more of
their capture spans than expected, leaving 20.421 and 12.794 seconds of their
frames uncaptured. Neither is decode or timing evidence.

## Adversarial assessment

The first review found and repaired a client syntax error and preservation of
multiple messages decoded from one USB read. It rejected a firmware-level plan
to defer all WTP input during RF because that would also defer ABORT; the final
loop keeps endpoint input live and removes routine client polling during the
frame. It restored the proven 16,384-word buffers after a larger-buffer image
made the endpoint unresponsive, and it added sink-level failure reasons to make
the observed fail-closed paths diagnosable.

Live review found two capture spans too short to contain the complete frame.
Neither was promoted. The decoder was extended with validated explicit window
selection, the affected tests were rerun, and a longer capture then passed hash,
sample-count, overflow, clipping, cleanup, frame-analysis and independent-decode
checks.

The second assessment also noticed that the first complete decode preceded the
last source rebuild. The current image was loaded and the same bounded run was
repeated; the results above come from that repeat. It then checked the WTP state machine, lease extension through a
running terminal state, connection-loss handling, clock and arithmetic bounds,
leap exclusion, default-image inhibit boundary, advertised mode/frequency limits,
BOOTSEL output checks, diagnostic escaping, capture identity and evidence claims.
No further actionable software finding remained. The small frequency-fit
residual miss, USB host UTC and helper wall-clock onset remain explicitly
nonqualifying; calibrated GPIO-edge timing, output network and band/filter
qualification remain future work.
