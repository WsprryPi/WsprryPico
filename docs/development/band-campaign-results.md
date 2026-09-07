# Conducted PIO band campaign results

The sweep covered the requested 2200 m through 2 m matrix
across two interrupted runs and separate final band bundles. Statuses apply
only to the recorded operational criteria.
Each entry covers one listed frequency and the specified job parameters, not
every frequency or possible workload in the band.
The original run lost Pico control before its first 160 m WSPR ARM; its
cleanup failure blocks qualification from that run. The continuation later
lost control during its second 15 m WSPR LOAD, again before ARM. Completed
observations in both interrupted runs remain subject to that cleanup block.
The remaining band bundles used the same RF firmware and 138 MHz clock.
No additional 2200 m retest or reclocking was performed.
The identical RF image was restarted between completed final band bundles;
this bounds accumulated device state but does not establish a USB-stall fix.
These runs do not qualify uninterrupted long-campaign reliability.

## Configuration

- Pico 2 W / RP2350 A2, chip `0bf4b4aec9ffb344`, device `fd6127d11d6aca42a9905fa3fb1bf1d5`.
- Engine: PIO/DMA, GP2, 138 MHz system/PIO clock, 0 ppb correction.
- Tested RFWTP UF2 SHA-256: `c1e559eddfc2e4c9456d920e730c76445fe97edd017547c3a84e2e1d4b19d5b1`.
- Embedded source revision: `27791cf28048-dirty`; firmware built before the final commit.
- SDK 2.3.0, source `98a542c1a62fb549ffb5d66a3e5892b06276b670`; Arm toolchain 15.3.1.
- Receiver: RSP1B `2404058C60` on wspr5, 250 ksps CF32, 200 kHz bandwidth, 20 dB gain, AGC/bias tee off.
- Leo Bodnar GPSDO `0673ED0FA107`, connected Output 1, project-owned Python control.
- RF path: Pico GP2 and GPSDO Output 1 each through a separate operator-reported 60 dB attenuator into a common combiner and SDR; no antenna.
- Independent wsprd SHA-256: `8a5acb25fe8c7072f2157b03fadc1d21543f1ddf432f609fd6907f095dfba2a3`.

Sequential GPSDO observations are retained independently. No receiver frequency
or sample-clock calibration was applied. References marked unusable must not
be used to claim calibration. Power, path response, wideband emissions and
calibrated UTC/GPIO onset remain outside the qualification scope.

## Band and mode matrix

| Band | RF Hz | TONE | WSPR | QRSS | FSKCW | DFCW |
|---|---:|---|---|---|---|---|
| 2200m | 137500 | blocked | blocked | blocked | blocked | blocked |
| 630m | 475700 | blocked | blocked | blocked | blocked | blocked |
| 160m | 1838100 | blocked | blocked | blocked | blocked | blocked |
| 80m | 3570100 | blocked | blocked | blocked | blocked | blocked |
| 60m | 5288700 | blocked | blocked | blocked | blocked | blocked |
| 40m | 7040100 | blocked | blocked | blocked | blocked | blocked |
| 30m | 10140200 | blocked | blocked | blocked | blocked | blocked |
| 20m | 14097100 | blocked | blocked | blocked | blocked | blocked |
| 17m | 18106100 | blocked | blocked | blocked | blocked | blocked |
| 15m | 21096100 | qualified | failed | qualified | failed | qualified |
| 12m | 24926100 | qualified | failed | qualified | failed | qualified |
| 10m | 28126100 | qualified | failed | qualified | failed | failed |
| 6m | 50294500 | failed | blocked | failed | failed | failed |
| 4m | 70092500 | unsupported | unsupported | unsupported | unsupported | unsupported |
| 2m | 144490500 | unsupported | unsupported | unsupported | unsupported | unsupported |

46 blocked, 11 failed, 8 qualified, 10 unsupported.

The 2200 m through 17 m rows retain the interrupted runs' cleanup blockage;
the table does not promote their individually successful observations.
At 2200 m, TONE and
keyed measurements had already failed, and the TONE gate blocked WSPR. At the
selected sample clock, 4 m and 2 m are unsupported direct synthesis. Each
attempted WSPR mode contains three consecutive frame attempts, each independently
submitted to wsprd; each keyed mode contains three independent ETE observations.

## Observed frequency and decode results

| Band | TONE indicated offset Hz | WSPR decoded / attempted | WSPR RF-passing / attempted |
|---|---:|---:|---:|
| 2200m | 0.965 | 0/0 | 0/0 |
| 630m | 1.921 | 3/3 | 0/3 |
| 160m | 6.869 | 3/3 | 0/3 |
| 80m | 12.916 | 3/3 | 0/3 |
| 60m | 18.759 | 3/3 | 0/3 |
| 40m | 24.900 | 3/3 | 0/3 |
| 30m | 35.552 | 3/3 | 0/3 |
| 20m | 49.382 | 3/3 | 0/3 |
| 17m | 63.364 | 3/3 | 0/3 |
| 15m | 63.816 | 3/3 | 0/3 |
| 12m | 76.234 | 3/3 | 0/3 |
| 10m | 83.761 | 3/3 | 0/3 |
| 6m | 146.699 | 0/0 | 0/0 |
| 4m | — | 0/0 | 0/0 |
| 2m | — | 0/0 | 0/0 |

All 33 frames in the eleven completed three-frame sequences decoded; none
passed every RF criterion. The separate smoke trial and interrupted extra 15 m
frame are retained separately and excluded from that count.

The 6 m TONE offset of +146.699 Hz exceeded the 100 Hz placement gate, despite
a continuous 5.001-second detected burst and low phase-fit residuals. Its keyed
observations also exceeded the placement gate; some additionally failed phase
coherence, state consistency or transition-fit criteria. These are indicated
errors of this uncalibrated setup, not calibrated Pico oscillator errors.

Offsets are indicated on the uncalibrated receiver axis. Decode success does
not override transition, spacing, coherence, continuity or cleanup failures.
The third 10 m frame was split by the amplitude detector during a level dip
after a short peak. Its 12–24 second window remained about 60.7 dB above the
quiet baseline, while falling below the peak-relative detector threshold.
This is a failed detector/analysis criterion, not proof of transmitter silence.
The resulting longest detected interval and segment alignment must not be
interpreted as the physical frame duration or independently proven phase faults.
The bound diagnostic is retained outside the original bundle as
`build/pio-10m-20260907c-envelope-diagnostic.json`.
Failures characterize this conducted setup; these measurements alone do not
isolate firmware, clock, RF path or receiver as the cause.

## Failed and blocked observations

The principal failure categories below are derived from the retained numeric
measurements. The original logs used broad transition labels that combined fit
noise with timing; a later reporting repair separates them without changing limits.

| Band | Median WSPR transition fit RMS Hz (limit 0.150) | Maximum timing error ms (limit 10) | Worst symbol residual Hz (limit 0.100) |
|---|---:|---:|---:|
| 630m | 0.116 | 2.7 | 0.020 |
| 160m | 0.170 | 1.7 | 0.054 |
| 80m | 0.674 | 3.0 | 0.105 |
| 60m | 0.794 | 3.4 | 0.224 |
| 40m | 0.160 | 1.8 | 0.175 |
| 30m | 0.083 | 1.3 | 0.209 |
| 20m | 0.114 | 1.5 | 0.262 |
| 17m | 0.048 | 1.6 | 0.362 |
| 15m | 0.029 | 7.3 | 0.572 |
| 12m | 0.105 | 3.5 | 0.580 |
| 10m | 0.185 | 4.4 | 0.700 |

WSPR spacing is judged against 1.46484375 Hz with a 0.05 Hz tolerance.
FSKCW uses a 5 Hz separation, a 0.2 Hz state-consistency tolerance, a 20 ms
transition timing limit and the same 0.15 Hz transition-fit RMS limit.
TONE placement is limited to 100 Hz indicated offset. These fixed diagnostic
limits were not relaxed after failures. Spectrum remains diagnostic only.

- **2200m TONE:** campaign cleanup unverified; observed: Burst duration differs by more than 20 ms; Expected one uninterrupted burst; missing complete measurement segment.
- **2200m WSPR:** carrier screen did not pass.
- **2200m QRSS:** campaign cleanup unverified; observed: carrier in commanded quiet interval; keyed carrier continuity, frequency or coherence failed; keyed envelope timing or extra transmission failed; missing leading quiet or unexpectedly early carrier; truncated event.
- **2200m FSKCW:** campaign cleanup unverified; observed: carrier in commanded quiet interval; frequency-transition boundary unresolved; frequency-transition fit RMS exceeded 0.15 Hz; frequency-transition timing exceeded 20 ms; keyed carrier continuity, frequency or coherence failed; keyed envelope timing or extra transmission failed; keyed frequency separation failed; keyed state frequency residual failed; missing leading quiet or unexpectedly early carrier; truncated event.
- **2200m DFCW:** campaign cleanup unverified; observed: carrier in commanded quiet interval; keyed carrier continuity, frequency or coherence failed; keyed envelope timing or extra transmission failed; keyed frequency separation failed; keyed state frequency residual failed; missing leading quiet or unexpectedly early carrier; truncated event.
- **630m TONE:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **630m WSPR:** campaign cleanup unverified; observed: frequency-transition fit RMS exceeded 0.15 Hz.
- **630m QRSS:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **630m FSKCW:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **630m DFCW:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **160m TONE:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **160m WSPR:** campaign cleanup unverified; observed: frequency-transition fit RMS exceeded 0.15 Hz.
- **160m QRSS:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **160m FSKCW:** campaign cleanup unverified; observed: frequency-transition fit RMS exceeded 0.15 Hz.
- **160m DFCW:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **80m TONE:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **80m WSPR:** campaign cleanup unverified; observed: frequency-transition fit RMS exceeded 0.15 Hz; individual WSPR symbol residual exceeded 0.100 Hz.
- **80m QRSS:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **80m FSKCW:** campaign cleanup unverified; observed: frequency-transition fit RMS exceeded 0.15 Hz.
- **80m DFCW:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **60m TONE:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **60m WSPR:** campaign cleanup unverified; observed: frequency-transition fit RMS exceeded 0.15 Hz; individual WSPR symbol residual exceeded 0.100 Hz.
- **60m QRSS:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **60m FSKCW:** campaign cleanup unverified; observed: frequency-transition fit RMS exceeded 0.15 Hz.
- **60m DFCW:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **40m TONE:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **40m WSPR:** campaign cleanup unverified; observed: frequency-transition fit RMS exceeded 0.15 Hz; individual WSPR symbol residual exceeded 0.100 Hz.
- **40m QRSS:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **40m FSKCW:** campaign cleanup unverified; observed: frequency-transition fit RMS exceeded 0.15 Hz.
- **40m DFCW:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **30m TONE:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **30m WSPR:** campaign cleanup unverified; observed: individual WSPR symbol residual exceeded 0.100 Hz.
- **30m QRSS:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **30m FSKCW:** campaign cleanup unverified; observed: keyed state frequency residual failed.
- **30m DFCW:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **20m TONE:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **20m WSPR:** campaign cleanup unverified; observed: individual WSPR symbol residual exceeded 0.100 Hz.
- **20m QRSS:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **20m FSKCW:** campaign cleanup unverified; observed: keyed state frequency residual failed.
- **20m DFCW:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **17m TONE:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **17m WSPR:** campaign cleanup unverified; observed: individual WSPR symbol residual exceeded 0.100 Hz.
- **17m QRSS:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **17m FSKCW:** campaign cleanup unverified; observed: keyed state frequency residual failed.
- **17m DFCW:** campaign cleanup unverified; observed: individual observations passed their criteria.
- **15m WSPR:** frequency-transition fit RMS exceeded 0.15 Hz; individual WSPR symbol residual exceeded 0.100 Hz.
- **15m FSKCW:** keyed state frequency residual failed.
- **12m WSPR:** frequency-transition fit RMS exceeded 0.15 Hz; individual WSPR symbol residual exceeded 0.100 Hz.
- **12m FSKCW:** keyed state frequency residual failed.
- **10m WSPR:** Burst duration differs by more than 20 ms; Expected one uninterrupted burst; frequency-transition fit RMS exceeded 0.15 Hz; incoherent, interrupted or out-of-range segment; individual WSPR symbol residual exceeded 0.100 Hz; missing complete measurement segment.
- **10m FSKCW:** keyed state frequency residual failed.
- **10m DFCW:** keyed state frequency residual failed.
- **6m TONE:** indicated placement +146.699 Hz exceeds the 100 Hz limit; the retained broad segment label does not establish an interruption.
- **6m WSPR:** carrier screen did not pass.
- **6m QRSS:** keyed carrier continuity, frequency or coherence failed.
- **6m FSKCW:** frequency-transition fit RMS exceeded 0.15 Hz; keyed carrier continuity, frequency or coherence failed; keyed state frequency residual failed.
- **6m DFCW:** keyed carrier continuity, frequency or coherence failed; keyed state frequency residual failed.

## Evidence and validation

- Original sweep: `build/pio-full-20260907a/` (incomplete, Pico cleanup unverified).
- Continuation: `build/pio-remaining-20260907b/` (incomplete, Pico cleanup unverified).
- Final band bundles: `build/pio-15m-20260907c/`, `build/pio-12m-20260907c/`, `build/pio-10m-20260907c/`, `build/pio-6m-20260907c/` (complete, cleanup verified).
- Interrupted 80 m trial: `build/pio-smoke80-20260907a/` (separate evidence).
- Recovery evidence: `build/campaign-recovery-20260907b/` and `build/campaign-recovery-20260907c/`.
- Matching continuation source snapshot: `build/pio-remaining-20260907b-source.tar.gz`.

Original artifact index SHA-256: `9467c2efcf77380cacf10332f39bc7f767c67c3d326a1c0ffcf691fd21f04407`.
Continuation artifact index SHA-256: `3d8fd3e5b71fed4dea0f5ca21d28d4c820f8c04b7a5e2688d8b5d880ece7721a`.
Original plan SHA-256: `37106fcbc39e190e642992f5fa8220fb4641a83b4220db974bbe6fa59a1f754d`.
Continuation plan SHA-256: `5d7281d5b56ce05dd0be840b7b44a32d818f32994bce57d640dca7a647952f5d`.
Interrupted continuation Harness controller SHA-256: `7156b1377778ba35a4ed5c76dbd5c6096d9ef23362d88e69b32a4c0b15f1ac8f`.
Continuation source archive SHA-256: `91bf1fa6a3750656397ae8bc803f2c500d7ffcb0eb569d6b21ff3c2baefd5e9c`.

Each bundle contains exact plan/source/tool hashes, WTP transactions, IQ, native
capture metadata, decoder logs, measurements and an artifact index. Generated
firmware and captures remain outside Git. The original records were not rewritten
to turn an interrupted run into a successful one. See the [adversarial review](band-campaign-review.md) for repairs, validation and the unresolved USB diagnosis.

## Final band evidence anchors

- 15m matching source archive: `build/pio-15m-20260907c-source.tar.gz`, SHA-256 `2bf7410c50fa1fd2037546712f12a0aee70691ec55bfe53cd288b002fe02cc53`.
- 15m: artifact index SHA-256 `3c18e7b97c49cce9d0fb0a82f1327de85ba166b31d3299bface31402d4b7d08f`; plan `6d1b57e11ab0ddc2879ee28d45466896d3d583d8925626d7628e0cda4e76c037`; execution Harness controller `fa406e62e9ba8b4f28b2da542a7925a2fdacc4209357cfaa6e89a31a2cca662e`.
- 12m matching source archive: `build/pio-12m-20260907c-source.tar.gz`, SHA-256 `24fc8e2402dfc0fb3875fb9b4769660753cacb98d78cd5f0346b5332e59a0492`.
- 12m: artifact index SHA-256 `74e7b9ccd0b08630400e21a42512587bfc3927bbbe106a5bd4f82062583109f0`; plan `76c36ee5f30234ff5d832328925e00f5b1efedca1773fab0805d5ce9eeb456a5`; execution Harness controller `fa406e62e9ba8b4f28b2da542a7925a2fdacc4209357cfaa6e89a31a2cca662e`.
- 10m matching source archive: `build/pio-10m-20260907c-source.tar.gz`, SHA-256 `6fe6f3527aff296001da0dfc9c4a4c8c12d50ffa71881f6b2eb2836e11455d04`.
- 10m: artifact index SHA-256 `761152ae00369834fecd901e11729a80044aace398c13e61ddadbf28adb1f352`; plan `65876624ea2bd3483a6fbbf01b94dedfe288c1c515cefa4d216b2ff38925836c`; execution Harness controller `fa406e62e9ba8b4f28b2da542a7925a2fdacc4209357cfaa6e89a31a2cca662e`.
- 6m matching source archive: `build/pio-6m-20260907c-source.tar.gz`, SHA-256 `f18ef387b519c206bdcc093a0e50e5ebdc7a52a9927a3006e08cb6b658e58e91`.
- 6m: artifact index SHA-256 `68b77ee195a47bd332ea15a7d83511d3d348ec6343a8e944b6a76089d77bce35`; plan `2adda1e7c757d640139432e611b77378d147c07b500ab2383c81a64d6adc0549`; execution Harness controller `fa406e62e9ba8b4f28b2da542a7925a2fdacc4209357cfaa6e89a31a2cca662e`.


## Final validation and hardware state

The final hardware-free acceptance set passed: 23 Pico CTest checks, WTP
contract fixtures, 1,611 Harness pytest cases, Ruff formatting/lint, mypy on
66 source files, wheel/sdist packaging and two native Harness checks. The pinned
firmware cross-builds and image memory-layout checks also passed. Hardware-free
success is separate from the RF dispositions above.

Current artifact/claim validation produced the following results. Validation
reports are retained alongside, outside, each immutable run directory.

| Bundle | Valid | Complete | Cleanup verified | Completed transaction records |
|---|---|---|---|---:|
| pio-smoke80-20260907a | True | False | True | 5 |
| pio-full-20260907a | True | False | False | 34 |
| pio-remaining-20260907b | True | False | False | 96 |
| pio-15m-20260907c | True | True | True | 13 |
| pio-12m-20260907c | True | True | True | 13 |
| pio-10m-20260907c | True | True | True | 13 |
| pio-6m-20260907c | True | True | True | 10 |

After the final 6 m bundle, guarded BOOTSEL and picotool flash verification
restored `WsprryPico.uf2`. INFO, HELLO, CAPS and STATUS verified the same board,
the `inhibited-standalone-simulator` engine and empty/inactive output. A separate
GPSDO read verified both frequency outputs and independent PPS disabled.

Restored inhibited UF2 SHA-256: `30ec34dad612f6243f0f6abd15284868cb92b672946cb2785317fabc8d5c505d`.

Final evidence `build/pio-final-state-20260907/pico-restored.json` SHA-256: `3f7811bb68028c0192cce9711ab8d1f866182c735119d332713ff9a703c640ec`.

Final evidence `build/pio-final-state-20260907/gpsdo-off.json` SHA-256: `004f3d3abc10d2ee6279059de5f86b8b658fe4a62a9e14fc7c108a4aeaf09ac4`.

Final evidence `build/pio-10m-20260907c-envelope-diagnostic.json` SHA-256: `d28000c4a95d3f4c95eeebe7f85f6a8073c08f92eb26d4f02adae5da85436e51`.
