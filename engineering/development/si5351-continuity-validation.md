# Si5351 continuity validation

This evidence covers the no-GPS rate-assistance implementation developed from Pico `b5678828f5d4455d60a6d0b6a6a124a4701a56ba` and Pi `3e2f64b20f5774e4698a491529e50ab4a4fd125e` on `codex/si5351-execution`. Final paired revisions, commands, logs, CI runs, installer receipts and image identities belong in the retained developer bundle's validation report. This document does not close the remaining environmental and absolute-timing qualification gates in the [backlog](consolidated-backlog.md#si5351-backlog).

## Software behavior

Frequency observations change the existing UTC mapping's slope continuously. They preserve epoch-source age and accumulated phase uncertainty. The complete rate-error bound adds estimate/reference error to the independent Pico drift allowance; statistical estimator skew remains separate for source selection. Lower-quality loopback cannot displace a better independent network estimate. Independent disagreement remains a source-validity failure. Loss of capture retains the learned center, while explicit removal of trust restores an independent network estimate or nominal rate. A retained replay watermark prevents policy cycling from accepting an old sample.

UTC phase uncertainty is informational in first-party Pico/Pi scheduling. No additional operator setting is introduced. Source age, authentication, leap, ownership, hardware admission and explicit external WTP request limits remain enforced. USB time-observation quality admission is independently versioned and unchanged. Manual RF correction remains separate; automatic RF calibration and production GPS ingestion are absent.

Deterministic checks exercise both signs of a known 20 ppm timer error, phone epochs, jittery/intermittent NTP, full 110.592-second WSPR intervals, repeated gaps, 1,800/3,600-second continuity, reference loss/reacquisition, malformed/stale/future/duplicated/generation-mismatched inputs, disagreement, policy removal and restart seeds. They establish software policy, not physical one-hour performance.

## Independent physical observation

Board C, USB serial `1545B6EFBF78028C`, used the QRP Labs Rev. 6 module and fitted QRP Labs 25 MHz TCXO, with CLK2 into GP7. QLG3 serial GP1 and PPS GP3 were receive-only test equipment. Pico ran at 138 MHz. The operator confirmed CLK0 connected directly to the SDR through 60 dB attenuation, with no GPSDO. This RAM-only diagnostic kept transmit outputs disabled. All 4 MiB of flash compared byte-identically before and after, original ordinary image `b5678828` and saved settings were restored, and the controller service resumed.

The accepted finite run captured 301 PPS edges over 300 intervals, with maximum polling gap and raw endpoint bracket both 4 µs, zero UART/checksum errors, 301 valid RMC and GGA fixes, and successful register restoration. The final reported fix used 13 satellites. Private NMEA coordinates and flash backups are excluded from source control. Earlier trials with a count-bracketing defect or a startup UART error are diagnostic failures, not accepted evidence.

The analysis includes count quantization, both capture endpoints, and a conditional 10 µs engineering allowance per PPS endpoint. The receiver's typical timing figure does not establish a guaranteed maximum. Under that condition the whole-run fitted-reference offset interval is −183.34 to −29.99 ppb, rounded outward; raw timer error is −300.01 to −146.66 ppb. Every 60-second reference interval fits within ±500 ppb during this run. That value is an observed conditional result, not a requirement or a total TCXO specification.

Temperature and supply were not independently logged. This warmed bench observation does not qualify cold startup, temperature range, supply range, aging, a one-hour wander bound, absolute UTC-second pairing, or ordinary-firmware RF launch accuracy. The vendor's temperature-stability graph is not a complete initial-tolerance/error budget. Measurement-only remains the handback policy.

## Production-code replay

`si5351_continuity_replay` uses these physical raw/count brackets through the actual reference measurement, NTP adapter, phone arbiter and UTC mapping. It uses an explicit conditional 5,000 ppb reference allowance and a common synthetic phone epoch. It never refreshes that epoch. This is an offline replay of physical data, not a target ordinary-image timing measurement or an RF transmission.

| Observation pattern | Observations | Indicated absolute error at 300 s | Maximum indicated assisted error | Reported uncertainty at 300 s |
| --- | ---: | ---: | ---: | ---: |
| Unassisted raw timer | 0 | 67.000 µs | — | — |
| Every 20 PPS intervals | 15 | 31.009 µs | 31.009 µs | 266.559 ms |
| WSPR-shaped gaps, at 20/160/280 s | 3 | 2.002 µs | 11.201 µs | 266.561 ms |
| One capture at 20 s, then 280 s retained | 1 | 44.999 µs | 44.999 µs | 266.555 ms |

The indicated errors use PPS midpoint truth; interpret improvements with the stated endpoint allowance. In particular, the 22 µs retained-case improvement is comparable to measurement-path uncertainty and does not independently establish an absolute improvement of that size. Every replayed error is covered by the reported uncertainty, including the conditional truth allowance. The initial 250 ms phone assumption dominates the absolute bound. The original epoch age at completion is `299999933000` ns in all cases.

The supported software policy retains the rate center across acquisition pauses and adds the existing independent 50 ppm Pico drift allowance. For an illustrative 5 ppm reference plus 1 ppm capture bound, rate uncertainty grows by 6.19 ms per WSPR frame or 201.6 ms per hour, plus initial epoch error. A tighter physically qualified drift model and full environmental TCXO allowance remain open gates. No GPS is required to use an explicitly bounded independent reference.

## Adversarial corrections

Review found and corrected retroactive shrinkage of accumulated phase uncertainty, use of a maximum instead of addition for independent error terms, unfair comparison of reference quality against an NTP-only drift floor, and trust-removal/replay behavior. A subsequent pass found that an NTP discipline update could reconsider the internally retained watermark after trust removal; an explicit inactive-state check and regression now prevent that. Delayed-ARM hardware testing exposed reference service resuming while a prepared engine still reported Idle. The retained plan now excludes capture from LOAD preparation through cleanup; a full-slot wait and cleanup/reacquisition regression cover this authority boundary. Review also tightened physical-capture endpoint validation and replay allowance parsing. The native browser fixture now selects current application uncertainty policy and admits a five-second-uncertainty job through the actual scheduler and shipped UI. Required final-pair integration, native rendering, ordinary image, installer and RF results must accompany delivery; these software and replay results cannot substitute for them.
