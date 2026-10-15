# Phase 14 band, clock and mode results

Phase 14 is complete within its declared scope. All 390 retained
board/band/mode/clock cells and 602 accepted observations are consolidated at
closed proof `912ea1c2...`; all nine workstreams are closed. The selected
Phase 14 consumer artifact is C96/138 MHz. Engineering measurements below keep
their actual source/image identities; 132/150 MHz remain historical comparisons.
This record does not assert the currently installed firmware. See the
[closeout ledger](phase14-closeout-ledger.md).

The catalog terminology was aligned with WsprryPi on 2026-10-15. This changes
reporting only; original observations, flags, receipts and the operator's
all-mode release decision remain unchanged. The machine-readable `catalog` in
[phase14-band-support.json](phase14-band-support.json) records the same statuses.

- **Qualified:** Met the applicable conducted carrier, decode or human-copy
  requirements within the recorded board, clock, source/image and setup scope.
- **Unqualified:** Did not meet the applicable qualification requirement. The
  4 m all-mode status follows the operator's required reliable-WSPR gate; it
  does not label every individual Tone or keyed observation a failure.
- **Unavailable:** The native engine cannot construct the requested output;
  experimental frequency consent cannot override its numeric limits.
- **Untested:** Outside the agreed matrix, with no qualification result.

Qualification and availability are distinct: 4 m is Unqualified at the
representable 150 MHz clock and Unavailable at 132/138 MHz. Native direct 2 m is
Unavailable at all three clocks. Manually mapped third-harmonic 2 m experiments
remain Unqualified evidence and do not establish native 2 m support.

Relative power is the received **fundamental carrier**, at the 138 MHz Pico clock, relative to each board's own 80 m result (0 dB), then averaged across A and B in linear power before conversion to dB. They include SDR, attenuator and cable response; they are not calibrated transmitter watts/dBm. The large 6 m increase is not isolated as higher transmitter output.

| Band | Average relative carrier power (dB vs 80 m) | Clocks with accepted RF results (MHz) | Tone | WSPR | QRSS | FSKCW | DFCW |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2200 m | -5.2 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 630 m | -3.1 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 160 m | +0.1 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 80 m | 0.0 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 60 m | -0.4 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 40 m | -0.1 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 30 m | +0.9 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 20 m | +0.7 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 17 m | +0.3 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 15 m | 0.0 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 12 m | -0.1 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 10 m | -0.4 | 132, 138, 150 | Qualified | Qualified | Qualified | Qualified | Qualified |
| 8 m | — | None tested | Untested | Untested | Untested | Untested | Untested |
| 6 m | +13.7 | 132, 138, 150 | Qualified | Qualified* | Qualified | Qualified | Qualified |
| 5 m | — | None tested | Untested | Untested | Untested | Untested | Untested |
| 4 m | — | None accepted for release | Unqualified | Unqualified | Unqualified | Unqualified | Unqualified |
| 2 m | — | None available for native direct output | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

*The 6 m WSPR asterisk identifies separately reviewed A/138 MHz receiver-only +125 Hz retune acceptance. The transmitted waveform and original nominal failed flags remain unchanged.*

138 MHz keyed modes have repeated trials; 132/150 MHz have single screens. WSPR means actual external expected-message decoding; keyed modes use the reviewed human-copy criteria.

4 m is directly representable only at 150 MHz, but required WSPR reliability
failed and the operator applied that qualification failure to every release
mode. Direct 2 m is outside all three clocks' limits; 138 MHz third-harmonic
pilots failed WSPR decoding, and no native harmonic mapping is implemented.
8 m and 5 m were outside the agreed qualification matrix and remain Untested.
These unfiltered conducted results establish neither calibrated transmitter
power nor antenna-ready emissions.

The power reduction reuses the audited 26 post-clock Tone recordings, unchanged 20 dB SDR gain/250 ksample/s/no AGC/bias-T disabled, and the already selected 4.194304-second on/off Hann windows. It integrates power within ±25 Hz of the previously measured carrier, subtracts the matched off-window contribution and computes 10 log10(Pband/P80m). No capture, decoder trial, RF, calibration or original result changed. Four method controls passed. The independent review rechecked arithmetic, every small-file binding and unchanged raw identities without repeating the full raw audit.

Clock reconciliation: `build/phase14-accepted-clock-reconciliation-20261011.json`, SHA-256 `612ba1f6496cde361e194001d1d21123e221da3cf7cf3a86558c68294e4f4ff4`. Support dispositions: [phase14-band-support.json](phase14-band-support.json). Relative-power result: `/home/pi/phase14-qualification-20261008/build/resume-tools-e95334a-internal-first/build/relative-carrier-power-20261011T1710/result.json`, SHA-256 `48405182601257a95ea071c9f3c569b9d01c6e7cf2267e43a681341f04bf9224`. Independent review SHA-256 `c0d776c63d03eff65391a50b679a118bd2fef1a1170ffbb0d3b76d0368eb268c` in the same directory. Local retained metadata is `build/phase14-relative-power-reviewed-20261011.json`.
