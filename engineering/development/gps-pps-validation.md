# GPS/PPS validation

Optional GPS UTC/PPS input, independent Pico and Si5351 oscillator estimates, automatic RF correction with manual residual trim, GPS location, day/night scheduling and transmission provenance are implemented. Software and conducted measurements establish the bounded behavior below. RF launch timing is complete and accepted for the agreed roughly one-second operating goal. The close-spaced carrier comparison establishes GP2 improvement at the selected 160 m, 60 m and 10 m points; Si5351 improvement varies between repeats. Each campaign retains its own image, capture and restoration identity below. [Backlog item 21](consolidated-backlog.md) records the specific Si5351 repeatability follow-up.

## Validated Si5351 implementation and checks

| Component | Validated revision |
| --- | --- |
| Pico | `c7d3b5befe90f7615c34f5b7583d6086cd3a1463` |
| Pi | `40c049c7f68767a1db316b471e35d15a2c5926e4` |

These revisions identify the validated implementation on `codex/gps-pps-integration`, not delivery on `devel` or `main`. Later documentation-only commits do not change this implementation pair or the installed image. No merge, tag or release formed part of this validation.

[Pico CI run 41562836673](https://github.com/WsprryPi/WsprryPico/actions/runs/41562836673) passed verification; publication was intentionally skipped. [Paired Pi CI run 41565967348](https://github.com/WsprryPi/WsprryPi/actions/runs/41565967348) passed all seven jobs with the Pico revision above selected explicitly. Both USB and network jobs recorded that exact source. The Pico preview merge checkout had the same tree as the validated feature revision.

| Requirement | Evidence | Boundary |
| --- | --- | --- |
| Bounded serial/PPS reception and separate time/position validity | Parser, actual SDK adapter and resource tests; ordinary GPS-only startup with no NTP admitted | Receiver and capture allowances remain explicit engineering assumptions |
| One UTC discipline, source arbitration and retained-rate holdover | Production clock/arbiter tests and six-case external Chrony 4.9 comparison covering fast/slow clocks, warmup, loss/reacquisition, restart and conflict | No live PPS cable-disconnection test was performed |
| Separate timer and synthesizer calibration | Known-error tests, coherent CLK2/PPS observations and independent timer/count acquisition baselines | Estimates retain original observation ages and conservative bounds |
| Manual residual once and frozen plans | Signed known-error tests, conducted residual-trim trial, accepted LOAD adjustments and paired transmission records | Short-window results do not prove consistent accuracy improvement |
| GPS location, day/night policy and paired WSPR snapshots | Stale/future/moving-position and polar/day-night tests; full Type 2/3 pair decoded with frozen GPS location/correction | Location and timing validity remain independent |
| Current Control/1 on both carriers | Production network runtime/interoperability/configuration and USB management/pair suites, native controls, source-selection proof and kernel reply routing | Hardware-free fixtures do not qualify physical installation or RF |
| Native controls and documentation | 202 local host checks, actual HTTP/crypto/journal browser checks, eight-plan Pi recovery workflow, strict Sphinx and 103 contextual-help targets | Precise GPS readback requires authentication or physical USB |
| Preserving ordinary deployment | Same-board shared-installer transaction, retained exact bundle, postboot verification and final five-second conducted tone | Full Pi service installation was not claimed; its original state was preserved |

The actual production pair recipes include `wtp-network-runtime-test`, `wtp-network-interop-test`, `wtp-config-interop-test`, the Pico `usb_management_driver`, `wtp-usb-pair-client-build`, `wtp-usb-management-test` and `WSPRRYPI_GPIO_DRIVE_REQUIRED=1 node WsprryPi-UI/tests/wtp_usb_pair_test.js CLIENT DRIVER`. The checked-in Pi `.github/workflows/debian-non-hardware.yml` supplies the complete recipes and additional browser/routing/source-selection gates. MbedTLS was pinned to `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`.

The external oracle entered Chrony 4.9 after receiver qualification through its reference-clock interface. It did not exercise a native hardware receiver driver or link Chrony into firmware. The comparison retained the documented policy difference between Pico's latched source conflict and Chrony's later source selection after expiry.

Local host verification used the existing configured build with `source scripts/xcode_env.sh`, `cmake --build build/gps-pps-integration/host --parallel 4` and `ctest --test-dir build/gps-pps-integration/host --output-on-failure --parallel 4`; all 202 checks passed in 54.49 seconds after the browser access correction. Native checks included `operator_cleanup_browser.mjs` and both consumer/engineering `ui_sections_browser.mjs` contexts. The final Pi recovery fixture supplied the current closed GPS resource and passed all eight station-plan cases, keyboard access, desktop/mobile layouts, light/dark themes and 200% text scaling. Production validators were not relaxed to accommodate fixtures.

## Delayed serial labels and control-path memory

PPS defines the second boundary. RMC serial arrival supplies a UTC label and does not set or move that boundary. Pico `6e3d809d3fead91b7836ca84720be8d29f88e7c8` retains five original captured edges and their loopback count snapshots, selecting exactly one edge inside the explicitly qualified receiver-delay window. Full capture-uncertainty intervals participate in selection; ambiguous or partially overlapping associations are rejected. Original observation timestamps and ages remain unchanged when a label arrives after a later PPS. The current Control/1 descriptor and strict Pico/Pi consumers describe this one current pairing contract.

The GP2 setup uses UTC second offset zero, PPS edge offset zero and a 600–1200 ms first-dollar delay window. This accommodates the observed asynchronous RMC arrival on either side of the following PPS without relabelling that following edge. Independent host brackets check the integer-second association; they do not establish 100 µs absolute UTC or RF launch timing. Known-error tests vary serial arrival across that PPS while retaining the original pulse intervals and oscillator estimate.

The original control-path headroom problem was corrected by separating the aligned 8 KiB loopback ring from its capture object and allocating optional activity-trace and Console buffers only when used. The final ordinary image provides 276,856 bytes of linked heap capacity, 32,284 bytes more than the original image. WTP decode workspace, the 32,768-byte safety reserve, replay retention and RF waveform buffers were preserved. A separate no-RF diagnostic reproduced pressure from creating a new logical WTP session for every job: the fourth LOAD failed while earlier sessions retained their replay responses. All eight LOAD/ABORT cycles passed when the controller resumed one logical session. The RF harness therefore resumes a session across jobs within each boot; it does not reduce production retention guarantees or establish unrestricted concurrent-client capacity.

All 202 local host checks passed in 59.62 seconds after the delayed-label change, using the configured host build and commands above. Ordinary and inhibited firmware links, actual HTTP/crypto/journal browser checks and strict documentation validation also passed. [Pico CI run 41637682581](https://github.com/WsprryPi/WsprryPico/actions/runs/41637682581) passed for this implementation. The matched physical Pi USB client was built from `c1b763be70c2a11debd68579b24f7400eff20049`; `d677d7f27570a7315aa9f7cdd08a5de20279696b` changes only its negative test assertions to expect the existing 409 capability refusal, with no production change or validator relaxation.

## Si5351 conducted setup

Board C was Pico 2 W/RP2350 serial `1545B6EFBF78028C`, device `c2a3a2a314c948b50a8562a1aeb69669`, at 138 MHz. QLG3 serial input used GP1/UART0 RX at 9600 baud; rising PPS used input-only GP3. CLK2 fed input-only GP7 for separate Si5351 loopback. RMC first-dollar delay was qualified over 600–999 ms, UTC second offset was zero and configured PPS edge offset was zero. Receiver and capture allowances were 100 µs each; the receiver allowance was not independently certified.

The Si5351 setup used the QRP Labs Rev. 6 external-XA 25 MHz TCXO profile, I²C GP4/GP5 at 100 kHz, address `0x60`, CLK0 at 8 mA and measurement-only reference policy. CLK0 and independently identified GPSDO output 1 entered a combiner, then the 60 dB path to the SDR. No antenna was used. The conducted range was 160 m through 4 m. GP2 was not connected or driven in this campaign.

The receiver was RSP1B serial `2404058C60`, at 250 ksps with 200 kHz bandwidth, gain 20, AGC off and bias supply off. The GPSDO was LBE1421 firmware 1.9, serial `0673ED0FA107`; satellite/PLL lock and antenna health were checked. Its original state was both outputs enabled at 10 MHz with LOW drive. LOW is a drive setting, not an output-off indication.

## Observations and measurement limits

### Practical launch timing and the current capture interface

The operational launch-time goal is RF onset reasonably close to scheduled UTC. Approximately one second early or late is acceptable for this validation; improved alignment is desirable, but submillisecond qualification is not a project completion requirement. Launch timing is accepted as complete for this scope; further precision-timing qualification, GPSDO USB PPS comparison and additional marker hardware are not required. wspr5 continues to use PPS from its onboard GPS. This comparison scale introduces no firmware setting, scheduling veto or protocol change. [TODO item 21](consolidated-backlog.md) retains the Si5351 carrier-correction follow-up; completed item 22 records the coarse timing assessment.

wspr5 provides an independent GPS/PPS-disciplined host clock. Inspection on 2026-11-03 found Chrony selecting the PPS reference, normal leap state, a 0.690 microsecond RMS offset and approximately 12.3 microseconds root dispersion. Those are reported synchronization statistics, not an independent calibration of receiver, antenna or cable delay. The configured receiver path is `/dev/ttyAMA0` at 9600 baud with the PPS device `/dev/pps-gps`; Chrony uses the PPS socket and keeps the serial NMEA reference unselected. Serial arrival does not define the second boundary.

The connected receiver is RSP1B serial `2404058C60`, using SDRplay API 3.15. Its live native Soapy probe reports `Timestamps: NO`. The installed SoapySDRPlay3 source revision `6cc31316b730503cee3e30906ff1975175a16400` does not populate `readStream`'s `timeNs` or set `SOAPY_SDR_HAS_TIME`. The SDRplay callback supplies `firstSampleNum`, a sample counter, but this adapter does not associate that counter with host UTC or PPS. A counter alone is not a UTC timestamp. The current capture helper also discards the returned timing fields. Its `configuration_start_utc`, `first_read_start_utc`, `first_read_complete_utc` and `retained_capture_start_utc` are host software timestamps; the last marks opening the retained output before subsequent reads, not the RF acquisition time of its first sample.

The existing interface therefore supplies host-time observations and sample-relative RF onset, but no direct PPS-tagged RF sample. A bounded absolute comparison would need a fresh stream's activation/read bounds, sample continuity, buffering and receiver delay accounted for explicitly. Merely adding an RF sample offset to `retained_capture_start_utc` does not establish that bound. The requested coarse assessment below uses existing captures without additional timing hardware. A direct hardware-timestamp qualification remains distinct from this practical check.

Retrospective analysis of existing successful captures compares `retained_capture_start_utc + RF onset offset` with each accepted ARM `start_utc_ns`. RF onset is the center of the first active 20 ms window at 50% of maximum window peak power within 700 Hz of the expected carrier; accepted signals exceed the median first-second noise power by at least 20 dB. Captures have zero reported overflows or clipping and verified receiver cleanup. The first read takes 65–66 ms, and configuration takes 519–537 ms in these records. These durations characterize host observations; neither is a certified receiver-delay bound.

| Existing scheduled launches | Count | Approximate host-anchored RF onset minus scheduled UTC |
| --- | --- | --- |
| Si5351 baseline/corrected tones, 160 m and 20 m | 4 | +44.9 to +53.4 ms |
| GP2 baseline/corrected/residual tones and one WSPR frame, 160 m, 60 m and 10 m | 8 | +39.2 to +65.0 ms |

The repeated observations are consistent with the requested roughly one-second operating goal. They do not prove a hard ±1 second bound or a submillisecond absolute RF-to-UTC error because receiver/driver latency is uncalibrated. The Si5351 and GP2 source/image identities remain those of their original campaigns below; this is reanalysis of those captures, not a fresh test of later firmware. Capture identities, raw hashes, scheduled UTC values, onset offsets and method are retained in `practical_launch_timing_assessment` in the [machine-readable record](gps-pps-validation.json). No new RF, Pico setting change, GPSDO change or service restart was performed for this assessment.

### Close-spaced carrier comparison

Pico C source `8abeb40aef71`, using the 138 MHz profile, completed 24 finite 12-second tones: two correction-off/on repeats for each engine at 1,840,100, 5,366,200 and 28,126,100 Hz. Si5351 CLK0, GP2 and GPSDO output 1 remained connected through the same combiner and 60 dB path to RSP1B `2404058C60`; one Pico RF engine was active at a time and no antenna was used. Si5351 drive remained 8 mA and GP2 drive remained 4 mA. The user reconfirmed this physical setup during the campaign. Current control helpers came from `29108844`; no firmware load or product-source change was needed.

GPS/PPS supplied the automatic correction, using GP1 serial RX, continuously connected GP3 PPS and CLK2 loopback into GP7 for Si5351. The receiver-delay window was temporarily 600–1200 ms, with manual location and zero manual residual. Separate engine controls selected correction off or GPS/PPS automatic correction. GPSDO LBE-1421 `0673ED0FA107` supplied a simultaneously recorded reference 500 Hz above nominal, with satellite/PLL lock and antenna health verified. Frequency changes were volatile; the complete original GPSDO state was retained for restoration. Receiver settings remained 250 ksps, 200 kHz bandwidth, gain 20, AGC off and bias supply off.

Analysis isolates the two tones from a ten-second interval inside each transmission and fits their differential phase after excluding one second at each filtered edge. Fifteen known-error synthetic cases cover noise, common receiver drift and sample-clock offsets. The declared engineering allowances are 100 ppm sample-rate error over the measured tone spacing, 10 ppb GPSDO error at its RF frequency, and the larger of 0.02 Hz or the greatest observed one-second differential-frequency departure from the fitted average. Their sum is the reported allowance. The GPSDO allowance is an engineering assumption, not a calibration certificate; the sample-rate contribution near 500 Hz is approximately 0.05 Hz, not the total measurement allowance.

| Engine | Band | Baseline errors, repeats 1 / 2 (Hz) | Corrected errors, repeats 1 / 2 (Hz) | Largest allowance among these four records (Hz) |
| --- | --- | --- | --- | --- |
| Si5351 | 160 m | −0.148 / −0.146 | +0.192 / +0.075 | ±0.089 |
| Si5351 | 60 m | −0.458 / −0.455 | +0.538 / +0.189 | ±0.127 |
| Si5351 | 10 m | −2.770 / −2.809 | +2.448 / +0.600 | ±0.431 |
| GP2 | 160 m | −1.959 / −2.066 | −0.244 / −0.036 | ±0.108 |
| GP2 | 60 m | −5.826 / −6.058 | −0.780 / −0.195 | ±0.200 |
| GP2 | 10 m | −30.888 / −31.921 | −0.537 / +1.000 | ±0.824 |

Allowances in the table are rounded outward; the machine-readable record retains each result's own allowance. Improvement is resolved only when the largest corrected absolute-error upper bound across both repeats is below the smallest baseline absolute-error lower bound across both repeats. GP2 passes that criterion on all three bands. Si5351 does not pass it consistently across the two repeats; its second corrected set is closer to nominal, while its first is comparable to the already small baseline error. The measurements identify Si5351 correction repeatability as the follow-up, rather than receiver availability. They do not establish performance over arbitrary temperature changes or certify the GPSDO.

All 24 receiver captures succeeded with zero reported clipping or overflows and verified cleanup. Commanded Pico RF was 288 seconds within the 300-second cap; an initial harness preflight refusal commanded no RF and was followed by exact restoration before the corrected campaign. Final same-board readback verified exact saved Pico settings, unchanged source, idle/unowned/inactive RF and CLK0 register-disabled. Original GPS settings, engine/pins, manual correction and automatic-calibration choices were restored. GPSDO frequency, output enables, drive flags and mode were restored exactly, and the original wspr5 service was active and enabled. The original private captures, calibration snapshots, and executable analysis were stored at `/home/pi/close-tone-20261103`. That directory was absent when checked on 2026-11-07, and the operator confirmed that no other copy remains. Sanitized hashes, measurements, reported LOAD adjustments, and restoration receipts remain under `close_spaced_carrier_comparison` in the [machine-readable record](gps-pps-validation.json). The original IQ analysis and per-job calibration endpoints cannot be independently replayed from that summary. LOAD adjustments describe reported engine realization and are not substituted for measured physical RF frequency.

### Si5351 frequency projection

The pinned Arm GNU 15.3.1 math library's `llround`/`llroundl` path loses a low-word carry for some large integer results. Exercising the exact routine from the RC.2 baseline ARM ELF in an instruction emulator converted `28126100000000000` to `28126095705032704` nanohertz: a loss of `4294967296` nanohertz, or 4.294967296 Hz. This matches the historical 28.1261 MHz baseline's reported LOAD adjustment. It does not describe a measured shift of the RF carrier.

The Si5351 engine rounds its nominal-reference achieved frequency in floating point before the independent unsigned-integer conversion. Register planning and oscillator estimation remain separate. A production-engine regression models the observed Arm library fault and compares reported frequency with independently decoded device-register writes at the three comparison frequencies and 70.4 MHz, with positive, negative, and zero correction. The original projection fails that comparison; the corrected projection passes. This software evidence covers LOAD and policy frequency projection, not physical RF repeatability.

The unaffected historical 160 m and 60 m LOAD projections imply an effective correction of approximately −185 ppb in the first corrected set and −121 ppb in the second. This is an inference from the retained projections and current unchanged planning arithmetic, rather than recovered calibration observations. The missing original endpoints, ages, and generations prevent attributing those estimate values to a particular observation window.

`rf_analysis.carrier_repeatability.compare_carriers` measures finite twelve-second tones with quiet margins and a simultaneous reference about 500 Hz away. It independently acquires both channels, rejects missing or ambiguous carriers, clipping, and interior dropouts, and fits differential phase over an eight-second interior. Nine synthetic known-error cases cover both signs, zero error, ±100 ppm sample-clock error, noise, and common receiver drift. Refusal cases cover invalid geometry, missing references, ambiguity, dropout, and missing quiet margins. Allowances retain the historical 100 ppm sample-clock, 10 ppb GPSDO, and maximum of 0.02 Hz or observed one-second departure assumptions. They are conditional engineering allowances.

### 2026-11-07 repeatability investigation

Pico C (`1545B6EFBF78028C`, device `c2a3a2a314c948b50a8562a1aeb69669`) completed 28 finite twelve-second tones: four balanced Si5351 off/on repeats at each original frequency, followed by two GP2 off/on controls at 5.3662 MHz. Manual residual was zero. The user confirmed CLK0 and GP2 through the combiner and 60 dB attenuation to RSP1B `2404058C60`, with no antenna, simultaneous LBE-1421 output 1 reference, QLG3 serial/PPS on GP1/GP3, and CLK2 on GP7. The receiver used 250 ksps, 200 kHz bandwidth, gain 20, AGC off, and bias off. GPSDO satellite/PLL/antenna state stayed healthy during each capture. All accepted captures had zero clipped samples and overflows and verified receiver cleanup.

The installed image was `9f929b27b724e096f4eb21aa17b186bb7a5fa5b2`, at 138 MHz, from the independent lifecycle branch. Its RF, estimation, and correction-selection sources match the RC.2 baseline. The divergent RC.2 candidate was not installed or merged. The projection fix above changes LOAD/policy reporting, not the RF register plan; its before/after reproducer is the exact Arm math-routine emulation and independent production-device register test.

| Engine / frequency (Hz) | Repeat | Baseline error ± allowance (Hz) | Frozen ppb / generation | Span (s) | Corrected error ± allowance (Hz) | Predicted / measured shift (Hz) |
| --- | --- | --- | --- | --- | --- | --- |
| gp2 / 5,366,200 | 1 | -2.290814 ± 0.205908 | -333 / 4 | 12 | -0.534472 ± 0.205271 | +1.786945 / +1.756342 |
| gp2 / 5,366,200 | 2 | -2.355354 ± 0.206099 | -405 / 12 | 21 | -0.169815 ± 0.198836 | +2.173312 / +2.185540 |
| si5351 / 1,840,100 | 1 | -0.097073 ± 0.088422 | +6 / 3 | 10 | -0.110268 ± 0.088423 | -0.011041 / -0.013195 |
| si5351 / 28,126,100 | 1 | -2.047755 ± 0.369569 | +45 / 53 | 11 | -3.322632 ± 0.351604 | -1.265674 / -1.274877 |
| si5351 / 5,366,200 | 1 | -0.314315 ± 0.123704 | -45 / 81 | 11 | -0.076999 ± 0.123681 | +0.241479 / +0.237316 |
| si5351 / 1,840,100 | 2 | -0.100814 ± 0.088422 | -100 / 86 | 10 | +0.083382 ± 0.088404 | +0.184010 / +0.184196 |
| si5351 / 28,126,100 | 2 | -2.088783 ± 0.351481 | +45 / 52 | 11 | -3.326372 ± 0.378739 | -1.265674 / -1.237589 |
| si5351 / 5,366,200 | 2 | -0.314474 ± 0.123704 | -150 / 3 | 10 | +0.491609 ± 0.123624 | +0.804930 / +0.806084 |
| si5351 / 1,840,100 | 3 | -0.101414 ± 0.088422 | -50 / 9 | 10 | -0.006272 ± 0.088413 | +0.092005 / +0.095142 |
| si5351 / 28,126,100 | 3 | -2.052357 ± 0.374368 | -337 / 46 | 11 | +7.438130 ± 0.392714 | +9.478499 / +9.490486 |
| si5351 / 5,366,200 | 3 | -0.313811 ± 0.123704 | -13 / 73 | 11 | -0.251209 ± 0.123698 | +0.069761 / +0.062602 |
| si5351 / 1,840,100 | 4 | -0.100873 ± 0.088422 | -29 / 93 | 10 | -0.044984 ± 0.088416 | +0.053363 / +0.055889 |
| si5351 / 28,126,100 | 4 | -2.072231 ± 0.405139 | +14 / 65 | 10 | -2.438825 ± 0.364954 | -0.393765 / -0.366594 |
| si5351 / 5,366,200 | 4 | -0.319536 ± 0.124665 | -150 / 28 | 10 | +0.486219 ± 0.123624 | +0.804930 / +0.805755 |

Displayed allowances are rounded outward; the criterion uses unrounded values. Each measured shift is paired with the baseline from its own repeat. Ideal nominal-reference shift is calculated independently as `frequency / (1 + frozen_ppb / 1e9) - frequency`; physical oscillator bias and temporal drift remain in the measurements. All shifts agree within the sum of their own baseline/corrected allowances, with a separate 0.001 Hz register-planning allowance. The machine-readable record retains unrounded measurements, capture hashes, per-second errors, original estimate ages, frozen generations, and individual allowances. A recovered first baseline retains its original postcapture controller metadata failure; its successful finite job, released ownership, raw capture, and reanalysis were checked independently. Two earlier preflight failures commanded no RF. Cumulative commanded RF was 336 seconds against the unchanged 360-second cap.

The twelve Si5351 selected values, generations, and original observation timestamps are reproduced by feeding the actual recorded PPS/count snapshots through production `PpsCalibration`. Missing count records are left absent; no observations are fabricated or filtered by the unrelated UTC-servo admission flag. An independent exact-rational calculation also reproduces each estimate from count delta, PPS raw span, count raw span, UTC span, and nominal CLK2 frequency. For example, repeat 3 at 28.1261 MHz selects −337 ppb from an eleven-second interval: 11,000,001 counts contribute +90.909 ppb before timestamp normalization; normalization contributes −428.091 ppb, giving −337.182 ppb before rounding. The resulting predicted +9.478499 Hz shift agrees with the measured +9.490486 Hz change. Sign, once-only application, and estimate-to-carrier realization explain that repeat without treating the faulty historical LOAD projection as RF evidence.

The independent Si5351 count sessions span ten or eleven seconds because reference acquisition restarts every twelve seconds and pauses for a prepared job. The Pico timer retains its separate, longer history. Controlled known-error replays demonstrate count/endpoint sensitivity comparable to the small uncorrected TCXO bias at these short spans. The observed selected estimates remain within their conservative declared bounds. This establishes a contributor mechanism and the complete recorded observation-to-estimate-to-carrier chain; it does not uniquely separate PPS timestamp jitter, counter endpoint error, and actual idle-to-transmit oscillator change. The delayed-ARM case preserves the frozen job correction/generation while a newer live timer estimate appears. No calibration threshold, correction policy, minimum span, protocol, or measurement allowance was changed.

None of the three Si5351 bands passes the unchanged repeatable-improvement criterion. On 160 m, the best baseline lower bound is already below the corrected measurement allowance, preventing a resolved improvement even for a carrier near zero error. The GP2 controls and exact numerical criterion are retained in the machine-readable record. Item 21 remains in progress: the projection defect is fixed, but repeatable Si5351 improvement and the physical contributions to the estimate noise remain unresolved. Further work must distinguish those contributions before selecting a justified calibration or quality-policy change; longer spans alone are not an established remedy.

Software source `d8bc0994f19f2529b45ed887f4a4f12edc76ec2e` and companion `5594964faae51b945e57f9c3b278c47ec7b5c51c` passed both actual [network and USB source-pair suites](https://github.com/WsprryPi/WsprryPi/actions/runs/42431769713), including their production handlers, parsing, crypto, framing, and journals. The [Pico preview suite](https://github.com/WsprryPi/WsprryPico/actions/runs/42431631967) passed 234 CTests and all eighteen required contexts, with 27 execution records and thirteen native-browser records, on synthetic merge `98a3a85594ef39512456f861b70377a5dea0a308`. That snapshot also contains newer `devel` installer/docs/pin/completion-policy changes; its RF source and regressions match the feature candidate. An optional direct feature-branch dispatch was refused by the existing artifact input policy before tests. No policy was relaxed to manufacture a source result. Exact commands are retained in the linked runs; focused local checks additionally cover eleven Linux and four macOS tests, ten analysis unittest cases, normal/inhibited linked firmware, generated companion freshness, and strict documentation/link validation.

The shared installer first completed a preserving same-image transaction using the exact retained original lifecycle developer bundle. Restoration loaded only that verified original full-board backup, compared all 4 MiB byte-for-byte (SHA-256 `636c5a9de30fe5e417e038715ac113e384eedda18dec942aae7438e897931d51`), verified the same-board installer reference, and checked original saved semantics. The original unconfigured state and `lifecycle-test.local` hostname were restored with idle, empty, unowned, inactive output. CLK0 was register-disabled after the final Si5351 job. GPSDO `0673ED0FA107` returned to its exact original enabled 10 MHz outputs and drive/mode settings. The retained original bundle is `/home/pi/.local/state/wsprrypi-qualification/pico-bench-20261107/lifecycle-feature-bundle-20261107`, with UF2 SHA-256 `43cf47135d55f7f264930bb2c03a7864fe47d9fd50c39cbe4a94e11b48b62e62`. The original `wsprrypi` service remains inactive, `sdrplay` active, and the receiver capture process is absent; no service state was changed. Raw IQ, failed controller attempts, original bundle/backups, and restoration records remain private on wspr5 under `/home/pi/.local/state/wsprrypi-qualification/si5351-repeatability-20261107`; temporary measurement settings are absent from the restored flash. No release publication or branch merge occurred.

### Existing-wiring counter diagnostic, 2026-11-07

Pico C completed two RAM-only 301-PPS captures using diagnostic source
`c1f96a5e3af3c42304b374929b43c3ec2b3470f5`, at 138 MHz, with CLK2 on GP7,
QLG3 PPS on GP3, and QLG3 serial on GP1. The user reconfirmed this setup.
The actual production GPS/reference adapters ran alongside independent GPIO
polling brackets on the same hardware counter. CLK2 used the fixture's integer
PLLA 900 MHz / MS900 plan, which differs from the ordinary PLLB plan. The
continuous counter also differs from ordinary twelve-second monitor restarts.
No CLK0/GP2 RF job, SDR capture, GPSDO control, or GPSDO-to-GPIO connection
was used. USB output alternated between quiet and bounded load every sixty
PPS edges, with the second capture reversing the initial state.

Both captures retained 301 consecutive PPS/UTC observations, maximum independent
poll gap 9 us, and zero UART-error, dropped-record, or capture-rejection increments
during capture. The quiet-first run retained 30 pre-capture UART errors; the
loaded-first run retained zero. Startup counters were not reset. Load writes
were 12,001 and 18,077. Ten and nine production count snapshots, respectively,
legitimately refused concurrent publication; those observations remain present.
Per run, 28/30 ten-second, 8/10 thirty-second, and 3/5 sixty-second windows had
coherent endpoints. Unavailable windows were neither shifted nor fabricated.
Every available production reconstruction agreed with independent count brackets.
Maximum absolute midpoint differences were 535.50/585.50 ppb at ten seconds,
116.67/100.00 ppb at thirty seconds, and 41.67/39.25 ppb at sixty seconds
(quiet-first/loaded-first). Midpoints are not exact acquisition errors. Windows
crossing or touching a load transition are labeled separately; the limited
interior windows do not establish a causal USB-load effect.

Independent ten-second reference midpoints ranged −550 to +500 ppb and −400
to +300 ppb. Thirty-second ranges narrowed to −166.67…+66.67 and
−183.33…+33.33 ppb; sixty-second ranges were −108.33…+8.33 and
−141.67…+8.33 ppb. Both complete 300-second estimates were −63.33 ppb,
with outward-rounded conditional half intervals of 90.01 ppb. These are
conditional on the explicit 10 us allowance per PPS endpoint, count quantization,
and retained GPIO/count brackets; this allowance is not a metrology certificate.
Longer windows reduce observed spread in these captures, but do not uniquely
separate oscillator variation, physical PPS variation, and acquisition effects.
Shared hardware-counter errors and rapid source changes during post-edge reads
are not independently resolved. This is not RF improvement evidence, and no
production calibration policy changed. Item 21 remains in progress.

An initial preflight failed on an unconfigured-profile assumption before RAM
loading. The first diagnostic capture was refused for aggregate UART errors;
its original image was restored and evidence retained. The accepted successor
starts the capture core before UART ingress, preserves a post-settling health
baseline, and rejects any error increment during capture. Stack-usage review
also replaced inadequate SDK defaults with separate 16 KiB/8 KiB stacks and
verified linker bounds. Both RAM variants were cross-built with pinned SDK
2.3.1 and Arm GNU 15.3.1; every UF2 payload address was checked to be SRAM.
The external GP9/GP11 variant was built but has not been physically run.

Before this session, another project had installed CI image
`0.1.0-ci.42429358845.1`, source
`922935f0097ed3014f8f20bef4bb0c9289645422`. Its exact published bundle was
retained and verified before RAM loading. The older local developer reference
was inapplicable to this CI image and was not edited. Final restoration verified
that all 4 MiB of flash remained unchanged (SHA-256
`6bb5e48bf27d528cdeec802fb229453092a933adfb6ec51b2e050ab61cc3c906`),
with no flash rewrite, the original CI image, equal saved semantics, an empty
unowned job queue, and inactive output. Pico C was released after verification.
The exact bundle, raw transcripts, original snapshots, failed attempts, controller,
and backups remain private under
`/home/pi/.local/state/wsprrypi-qualification/si5351-repeatability-stage1-20261107`.
Raw transcripts contain GPS status and are excluded from tracked source. The
adjacent JSON records sanitized measurements and capture hashes. The
[diagnostic instructions](../../tests/hardware/si5351-reference-truth/README.md)
define tomorrow's disabled-output wiring and preservation requirements.

### GPSDO GPIO routing diagnostic, 2026-11-08

Pico C used RAM fixture `9c0092aae381fa68b8b61a9b0840703e1ab81df5`, at
138 MHz, with LBE-1421 `0673ED0FA107` firmware 1.9 on GP9 clock / GP11 PPS.
Original GP7 CLK2, GP3 QLG3 PPS, and GP1 serial remained connected. The user
confirmed both-ended connections and supplied a photo showing GP9 and its
adjacent ground. Electrical probes subsequently verified both intended signal
bindings; no user wiring change was required.

The retained GPSDO utility's enable labels did not establish independent physical
output gating on this unit. Setting OUT1 to 5 Hz and OUT2 to 10 Hz distinguished
the paths without relying on the PWM frequency counter. Every probe lasted
2.2 seconds with input-only pads and quiet GP8/GP10/GP12/GP13:

| Requested frequency enables / PPS | GP9 hardware edges | GP11 polled rising edges |
| --- | --- | --- |
| Both off / PPS off | 0 | 0 |
| OUT2 only / PPS off | 0 | 0 |
| OUT1 only / PPS off | 22 | 11 |
| Both on / PPS off | 22 | 11 |
| Both on, OUT2 changed to 1 MHz / PPS off | 2,199,999 | 11 |
| Both off / PPS on | 0 | 2 |
| Both on, OUT2 1 MHz / PPS on, separate combined guard | 2,199,998 | 2 |

All interleaved all-off controls were quiet. The 5/10 Hz GPIO polling counts
independently establish the cable/pin bindings and show that the requested
OUT1-only state produces both programmed signals, while OUT2-only produces
neither. This is an observed utility/device interaction, not a diagnosed general
firmware defect. The corrected bench controller explicitly requests both
frequency enables and PPS, then verifies actual 1 MHz on GP9 and PPS on GP11.
Status readback alone is insufficient. No third-party repository was edited.
The [fixture instructions](../../tests/hardware/si5351-reference-truth/README.md)
record this unit-specific setup and its digital-validation limits.

An initial all-off probe correctly refused `input_only=0`: the fixture's SDK
function switch cleared its forced-input override. No GPSDO output had been
enabled. The successor changes only FUNCSEL and preserves the override; later
probes report input-only operation with a 1 us maximum polling gap. That refused
attempt, subsequent missing-clock probes under the earlier enable configuration,
and a mutation-free bundle-directory preflight refusal remain separate evidence.
None is counted as a calibration pass.

The simultaneous off/combined/off guard passed. The following quiet-first
five-minute capture retained all 301 independent PPS/count endpoints, maximum
poll gap 10 us, 12,001 USB load writes, and zero new UART, dropped-record, or
capture-rejection errors. Twenty-three reference-state checks, including start,
15-second checks, and end, retained antenna/satellite/PLL health and expected
source settings. However, the production GPS observation sequence jumps from
96 to 99 with the corresponding three-second UTC/raw interval: observations
97 and 98 are absent. The full production analyzer therefore refused continuity,
and the second capture did not start. No missing observations were fabricated,
no window was shifted to hide the gap, and the cause of the emission gap remains
unestablished by the retained final health counters.

Independent-only analysis remains separately useful: ten-second midpoint values
span -550 to +400 ppb, sixty-second values -75 to +33.33 ppb, and the full
300-second value is -6.67 ppb with an outward-rounded conditional half interval
of 90.01 ppb. These retain the explicit 10 us allowance per PPS endpoint and
count/edge brackets; they do not certify source accuracy or accept the refused
production capture. Native replay through the unchanged production learner uses
all original 299 observations, retaining the gap and its acquisition reset. It
produces 235 overlapping count-based updates spanning -169 to +235 ppb, all
within their own declared bounds. These are offline replay outputs for the
GPSDO input, not device-reported Si5351 calibrations or independent experimental
repeats. Shared counter errors, source relative jitter, and post-edge read-delay
variation remain unresolved. No production calibration policy or RF-improvement
criterion changed; item 21 remains in progress.

Final handback verified original CI image `0.1.0-ci.42429358845.1`, source
`922935f0097ed3014f8f20bef4bb0c9289645422`, equal saved semantics, idle/empty/
unowned/inactive output, and unchanged full flash SHA-256
`6bb5e48bf27d528cdeec802fb229453092a933adfb6ec51b2e050ab61cc3c906`.
No flash rewrite or CLK0/GP2 RF job occurred. Both GPSDO frequency enables and
PPS are verified off. Test frequencies 5 Hz / 1 MHz remain configured but disabled;
restoration of the original enabled RF-reference configuration is deferred while
GPIO leads remain attached. Private transcripts, tools, exact original bundles,
backups, refused attempts, and sanitized scalar analysis remain under
`/home/pi/.local/state/wsprrypi-qualification/si5351-repeatability-stage2-20261108`.

### Pairing trace and receiver-delay profile, 2026-11-08

The RAM fixture at `38c3f997384e4abbce29efb70249f5327376ee29` records a bounded, position-free snapshot of the production pairing state at 10 Hz and independently brackets the already connected QLG3 PPS on GP3 alongside the GPSDO PPS on GP11. The diagnostic decoder checks the complete current internal status shape, retains startup counters, and refuses unknown errors, overflow, stalled traces, and missing coverage. Its maximum measured decoding work in the first capture was 5,822 us; this additional work is part of the diagnostic conditions and does not qualify ordinary firmware timing.

The first instrumented five-minute capture was refused. Its 3,029 valid trace samples show two RMC arrivals 1,206.904–1,206.912 ms and 1,200.385–1,200.393 ms after the corresponding independent PPS brackets, beyond the fixture's 1,200 ms maximum. Each causes `unpaired_utc`, followed by `pairing_acquisition`, and two absent production observations. A native behavioral reproducer confirms that refusal/reacquisition sequence. UART, dropped-record, rejected-sentence, and capture-error counters did not increase; QLG3 minus GPSDO PPS brackets span −11 to +15 us. This identifies the instrumented capture's missing-label cause as the bench receiver profile excluding observed arrivals, rather than evidence of a missing clock or PPS connection. It does not retrospectively prove the cause of an older capture without this trace, or uniquely assign the arrival delay to receiver transmission versus ingress service.

Fixture source `df8de6a08617d6e40bde83f63969cfb29880c641` changes only the bench receiver profile to 600–1,250 ms. The 650 ms window still selects a unique second, and the complete uncertainty interval must fit. A regression accepts the measured 1,206.912 ms case with consecutive observations and refuses 1,250.001 ms. Production defaults, saved settings, public schemas, estimator policy, and RF allowances are unchanged. Earlier refused captures remain refused. Fresh quiet-first and loaded-first captures validate continuity under this profile; neither fresh run reproduced an arrival beyond 1,200 ms, so the measured late-arrival boundary itself is covered by the native regression rather than a fresh physical late event.

Two fresh captures using the exact audited RAM UF2 `09ec61e52ead06a7fb46741af02b799045f64c022db826abfc5ab7046b2ae3dd` pass the complete continuity/health analyzer. Each retains 301 consecutive production observations within the independent 301-PPS interval, plus two observations outside it, with no stalls or capture-time UART/drop/rejection increments. The quiet-first run preserves 101 startup UART errors; the loaded-first run preserves zero. Maximum independent polling gap was 10 us. Trace samples were 3,030/3,022, maximum decoding work 5,826/5,811 us, and load writes 12,000/18,011. QLG3 minus GPSDO PPS brackets span −11 to +15/16 us. Eight/six incoherent production snapshots remain present; none touches the selected comparison endpoints.

| Common-source capture | Independent 10 s midpoint range (ppb) | Independent 60 s midpoint range (ppb) | Complete 300 s midpoint ± conditional half interval (ppb) | Native learner replay range (ppb) |
| --- | --- | --- | --- | --- |
| Quiet first | −600…+550 | −41.67…+41.67 | −10 ± 93.34 | −169…+185 |
| Loaded first | −600…+700 | −33.34…+83.34 | 0 ± 93.34 | −260…+150 |

Displayed bounds round outward. Independent intervals retain the declared 10 us allowance per PPS endpoint, count quantization, and actual edge/count brackets; they are conditional engineering bounds. Native replay uses the unchanged production learner and all original observations, timestamps, and count bindings. Its 249/251 overlapping updates cover 10–60 s spans, with declared uncertainties of 6,950–42,115/41,743 ppb. Replay scope labels and generations are not device-reported boot/calibration metadata or independent repeated experiments. Comparable apparent variation with the Si5351 outside this measurement path shows that TCXO variation is not required to reproduce short-window spread. It does not uniquely separate source PPS/frequency variation, shared counter behavior, timestamp quantization, or post-edge count-read error.

All available 30/60 s reconstruction midpoints lie within the independent same-edge count brackets. At 10 s, 29/30 quiet-first and 30/30 loaded-first midpoints lie inside. The quiet-first PPS 100–110 midpoint difference interval is +35.50…+1,535.50 ppb; the midpoint is about +785.50 ppb. This comparison does not propagate the complete production observation/count uncertainty and is retained as a discrepancy rather than a universal reconstruction pass. The declared production calibration bounds are substantially wider. No USB-load causal effect, exact zero-relative-jitter reference, production-policy fix, or repeatable RF improvement follows from these captures. Item 21 remains in progress.

Final verification again found all 4 MiB of original flash byte-identical (SHA-256 `6bb5e48bf27d528cdeec802fb229453092a933adfb6ec51b2e050ab61cc3c906`), with no flash rewrite. Original CI image `0.1.0-ci.42429358845.1` / source `922935f0097ed3014f8f20bef4bb0c9289645422`, equal saved semantics, and an empty/unowned/inactive queue were verified. Pico C is released. Both frequency enables and PPS are off; 5 Hz/1 MHz remain configured but disabled while the GPIO leads are attached. No CLK0/GP2 RF job, SDR control, or ordinary candidate-image deployment occurred. Exact bundles, backups, controller sources, refused attempts, and raw GPS-bearing transcripts remain private under `/home/pi/.local/state/wsprrypi-qualification/si5351-repeatability-stage3-20261108`; the two accepted records are in its `profile-1250-01` child directory.

Software validation passed for Pico feature code `df8de6a08617d6e40bde83f63969cfb29880c641`: [Pico CI](https://github.com/WsprryPi/WsprryPico/actions/runs/42486702825) reports 234 CTests, zero skipped, eighteen required contexts, 27 execution records, and thirteen native-browser contexts. Its synthetic preview `1b9c6b87fbab2dbdd49ffa3ac5074bb13b67da86` adds thirteen installer/prepared-publication/docs/pin/completion-policy files from base `7d841b75`, with no RF/GPS, fixture, or analysis implementation difference. No preview/base merge was performed. All nine [Pi CI jobs](https://github.com/WsprryPi/WsprryPi/actions/runs/42487195354) passed against Pi `0a794eeb3eeddbf3fdbb74bcc04ca9f84c8fe030` on `devel`, explicitly selecting this full Pico feature SHA. Both actual network runtime/interoperability/configuration and USB management/pair suites passed. The former companion `5594964f` is retained in Pi `devel` following an external merge; its deleted CI branch was not recreated. The final feature successor changes only the backlog and these Markdown/JSON evidence records. Local checks passed 26 analysis cases, five focused GPS producer/adapter/browser/schema CTests, eight private controller/cleanup cases, both pinned RAM builds, SRAM/stack checks, strict Sphinx, 1,754 local-target checks, and whitespace validation. The original Pi worktree and unrelated user changes remain untouched. Pico PR 19 remains draft with auto-merge disabled. Item 21 remains in progress.

### Earlier conducted GPS/PPS observations

GPS-only startup collected 90 samples with networking disabled and zero NTP observations admitted from boot: 83 samples had valid UTC/PPS pairing, 82 selected GPS and 62 had both independent calibration estimates fresh. Four physical production Pi USB resource reads returned 200. A host USB time submission did not replace the selected GPS source. Maximum observed IRQ latency was 29.674 µs; the maximum reported corrected capture bound was 9.712 µs. These local timestamp results do not establish receiver absolute accuracy.

Independent host/PPS bracketing supported UTC second offset zero with an intersection approximately −18.15 to +22.36 ms. It excludes the observed alternative integer-second association but cannot establish a 100 µs absolute UTC or RF launch allowance. Source loss/recovery was covered in software as selected; disconnecting the PPS wire is neither a completed physical test nor a prerequisite for the selected GP2 transmission test. GP2 baseline/correction measurements can retain continuous PPS input.

Each baseline/corrected tone lasted five seconds, with a simultaneous GPSDO carrier 30 kHz above the nominal DUT frequency. Line differencing removed common receiver tuning error. Conditional allowances used 100 ppm sample-rate error over measured carrier spacing, reciprocal margin, two 0.25 Hz line allowances and a 10 ppb GPSDO bench allowance. A single reference carrier does not calibrate both SDR tuning and sample clocks. Accepted captures had zero clipped samples and overflows, with verified receiver cleanup.

| Nominal frequency (Hz) | Manual-zero baseline error (Hz) | GPS-corrected error (Hz) |
| --- | --- | --- |
| 1,840,100 | −0.181 ± 3.519 | +0.175 ± 3.519 |
| 14,097,100 | −1.454 ± 3.642 | −4.688 ± 3.642 |
| 70,400,000 | −7.363 ± 4.205 | +5.456 ± 4.204 |

The programmed shifts were +0.356979473 Hz, −3.185943810 Hz and +12.812811840 Hz, respectively; the measured changes agreed within the declared bounds. A +20,000 ppb manual residual trial at 14.0971 MHz produced approximately −281 Hz of error, consistent with once-only residual application within the combined measurement allowance. These results do not demonstrate consistently improved absolute carrier accuracy or 0.05 Hz measurement accuracy.

A complete locally scheduled `AA0NT/P` Type 2/3 WSPR pair decoded successfully. Its two receiver-envelope intervals measured 110.75 seconds at 0.25-second analysis resolution, 120.0 seconds apart; nominal frame duration was 110.592 seconds. The second decode contained the expected six-character GPS locator. USB records retained the same frozen locator/fix timestamp and correction/generation across the pair, with GPS time provenance. The raw capture SHA-256 was `00196f060088e34f47fac43ed391c28d68177852e1929d8f67d2f51dc8eb94a2`. Receiver-relative timing is not calibrated absolute RF launch UTC. Precise receiver coordinates and decoded locator text are excluded from the tracked record.

The nominal commanded DUT RF total, including an earlier complete Type 1 frame and the final installed-image tone, was 371.776 seconds against a declared finite 500-second budget. Failed/refused experiments were not counted as qualification passes. No calibrated output power, emissions, general all-band suitability or direct GPIO RF qualification follows from these measurements.

## GP2 conducted validation on 160 m, 60 m and 10 m

On 2026-11-03, board C used the clean ordinary Pico `6e3d809d3fead91b7836ca84720be8d29f88e7c8` image at 138 MHz, runtime engine `pio-dma-gp2` and 4 mA GPIO drive. GP2 entered the existing combiner alongside register-disabled Si5351 CLK0 and GPSDO output 1, then the 60 dB path to the same RSP1B receiver. No antenna was used. CLK2 remained connected to input-only GP7; serial RX and continuously connected PPS remained on GP1 and GP3. Only the three selected frequencies, 1,840,100, 5,366,200 and 28,126,100 Hz, were transmitted; this is neither a continuous band sweep nor qualification above 10 m. Receiver settings and reference allowances match the Si5351 measurements above.

The final matched pair was Pico `6e3d809d3fead91b7836ca84720be8d29f88e7c8` and Pi `d677d7f27570a7315aa9f7cdd08a5de20279696b`. [Paired CI run 41639480111](https://github.com/WsprryPi/WsprryPi/actions/runs/41639480111) passed every job, including the actual production network runtime/interoperability/configuration suite and USB management/pair suite, with this exact Pico source selected explicitly. The physical Pi client used the production-identical `c1b763be70c2a11debd68579b24f7400eff20049` source and returned 200 for configuration, GPS, Si5351 and application reads. An earlier CI run failed because new negative tests expected 502 instead of the existing 409 capability refusal; the test-only successor corrected that expectation and retained refusal before mutation.

Fresh preflight selected GPS without source disagreement, reported synchronized/settled time and a fresh PPS-derived timer estimate spanning at least 30 seconds. Eight independent UTC-label brackets passed with offset zero. Their intersection was -38.445 to +20.111 ms; observed serial delay from the selected original PPS ranged from 1005.298 to 1055.621 ms. All eight samples selected an edge earlier than the nearest preceding PPS. These brackets validate the integer-second label association, not a 100 µs absolute timing allowance.

Each baseline and corrected tone completed its five-second interval. Automatic direct-output correction selected `gps`; accepted LOAD adjustments and transmission records retained the frozen correction and generation. Both a delayed 60 m tone and the WSPR job observed a newer live timer generation before ARM while preserving the accepted plan. All eight final jobs completed and released ownership; receiver captures had zero overflows or clipped samples and verified cleanup.

| Nominal frequency (Hz) | Manual-zero baseline error (Hz) | GPS-corrected error (Hz) |
| --- | --- | --- |
| 1,840,100 | -1.020 ± 3.519 | +0.016 ± 3.519 |
| 5,366,200 | -2.960 ± 3.555 | +0.076 ± 3.554 |
| 28,126,100 | -15.457 ± 3.783 | -0.123 ± 3.782 |

The programmed baseline-to-corrected shifts were +1.188833267 Hz, +3.405846656 Hz, +16.964972019 Hz, respectively. Measured changes agreed within the combined declared bounds. A +20 ppm manual residual on top of GPS correction at 5.3662 MHz produced a -107.333 Hz change, versus -107.324 Hz for once-only application, within ±7.119 Hz. These conditional line-difference measurements do not establish consistently improved absolute accuracy or a full SDR sample-clock calibration.

One complete controller-encoded Type 1 WSPR frame decoded as `AA0NT EM18 37` at the 60 m point. The receiver envelope lasted 110.75 seconds at 0.25-second analysis resolution, against a nominal 110.592 seconds. Job-bound records identified GPS time, GPS correction and its frozen generation. `EM18` was supplied by the controller, not derived from receiver position; encoded 37 dBm is message content, not a measured RF power. Capture SHA-256 was `49e71ab6adc7c943ee0e90cc5f817d67b7b542b4607fd3fc81ebddf57c89411e`. Receiver-relative timing does not establish calibrated absolute RF launch UTC.

The final campaign commanded 145.592 seconds of DUT RF. Earlier failed resolution attempts had commanded 25 seconds of baseline tones; cumulative GP2 RF was 170.592 seconds against the declared 200-second budget. The original pre-ARM attempts and the LOAD/ABORT memory diagnostic commanded no RF. The first memory-fix campaign completed three baselines but refused late serial labels under the former 600–999 ms window; the delayed-label campaign completed two baselines before fresh-session replay retention exhausted LOAD headroom. Neither was counted as a correction/WSPR pass. Their capture and restoration evidence remains private in the existing work area; the final result uses `gp2-20261103-v6`.

Source loss/recovery remains covered by software as selected; no PPS wire was disconnected. No output-power, emissions, antenna operation, arbitrary client-capacity or all-band qualification follows from these measurements.

## Si5351 installed image and handback

The clean ordinary image used validated Pico revision `c7d3b5befe90f7615c34f5b7583d6086cd3a1463`, with source-input SHA-256 `5fa0dabb60f42916cf9bd7a5d1319ec321872c345e86bcf465defc62a426d0f7`. Its 6,222,336-byte UF2 SHA-256 was `b307528274f0d5294c000b99c3f9ae9be15492d26ed42b8262d5b255f15c9b41`. Build inputs were Pico SDK 2.3.1 at `079c6f39023649b154152db30f1d781e884879bc` and Arm GNU 15.3.1.

Full RF/GPS measurements used the candidate source-input SHA-256 `9b3f6086153af529ca6c02de8859a700c34b17e3eef3c567ac9bb2ee1c4f89ee`, based on Pico `4f9ca837e7161cf8fedc454746a63eece0d136b6` plus the then-uncommitted implementation. All 323 owned Pico C/C++/PIO production files were byte-identical to the validated revision above. Browser behavior, embedded assets and regression tests changed afterward; the final installed image separately passed its five-second conducted tone. Pi's 570 owned production C/C++/PIO files likewise matched the physically exercised source set; later provenance and fixture changes are identified by the validated Pi revision.

Programming used `scripts/usb_installer.py upgrade` with the exact generated normal developer bundle, same-board image reference and postboot verification. The transaction was retained on wspr5 at `/var/lib/wsprrypi/pico-usb/1545B6EFBF78028C-b9pyq1qz/transaction.json`. The exact bundle remains in `build/gps-pps-integration/bundle-final` on the development host and `/home/pi/gps-pps-integration-20261102/bundle-final` on wspr5; private raw captures and logs remain outside tracked source. Recovery assets were retained. No direct programming bypass was used.

At handback, the board was idle, unowned and output-inactive, with CLK0 register-disabled and the installed image/reference hashes verified. Original GPS absence, manual-zero/automatic-off correction, measurement-only reference policy, station/network settings, logging and disabled schedules were restored. Legitimate autonomous watermark advances were preserved. The original GPSDO state and active `wsprrypi` service were verified. Wiring documentation matched GP17 LED positive, physical pin 23 LED ground return and GP14 runtime switch.

## GP2 installed image and final handback

The clean ordinary image used Pico `6e3d809d3fead91b7836ca84720be8d29f88e7c8`, source-input SHA-256 `026dac6987041bf629cb91a2ebf800196d088499bef9ac624e5c9555bf3ba9ba`. Its 6,225,920-byte UF2 SHA-256 was `ce0c51790e35ded99514bc7bdd1ea49e2f0249e8efe16d26e14c77a5c6879fa5`. The shared installer completed its preserving same-board upgrade, retained the developer bundle in `build/gp2-gps-validation-20261103/bundle-late-label` locally and `/home/pi/gps-pps-integration-20261102/bundle-late-label` on wspr5, and recorded transaction `/var/lib/wsprrypi/pico-usb/1545B6EFBF78028C-u1kzdp7c/transaction.json`. The original and intermediate recovery bundles were retained. No direct programming bypass was used.

Final postcampaign checks verified the installed image/reference hashes, exact saved configuration semantics, idle/unowned/inactive RF, CLK0 register-disabled and CLK2 reference output enabled. Original Si5351 pins/reference policy, GPS absence, manual-zero/automatic-off correction, networking, logging, disabled schedules, 4 mA GPIO drive, GP14 button and GP17 LED were restored; the LED ground return remains physical pin 23. GPSDO outputs were restored exactly to their original enabled 10 MHz LOW-drive settings with healthy locks, and the original `wsprrypi` service was active. The isolated current Pi USB client was tested without claiming a full Pi service installation.

The adjacent [machine-readable record](gps-pps-validation.json) retains measurement scalars, source/image identities, capture hashes and restoration results. It contains no receiver coordinates, GPS-derived decoded locator text, credentials, firmware or raw capture data. The [GPS/PPS contract](gps-pps.md) specifies current behavior; [backlog item 14](consolidated-backlog.md) retains only the remaining independent measurement limits.
