# Phase 14 band, clock and mode results

Accepted conducted evidence on both Pico A and B; final release qualification remains in progress. These results retain their actual old source/image identities. The clean experimental-frequency candidate is installed on both boards; engineering flag persistence/default admission passed, and current-image RF baselines are in progress. The table remains historical evidence under its recorded source identities.

Relative power is the received **fundamental carrier**, at the 138 MHz Pico clock, relative to each board's own 80 m result (0 dB), then averaged across A and B in linear power before conversion to dB. They include SDR, attenuator and cable response; they are not calibrated transmitter watts/dBm. The large 6 m increase is not isolated as higher transmitter output.

| Band | Average relative carrier power (dB vs 80 m) | Clocks with accepted RF results (MHz) | Tone | WSPR | QRSS | FSKCW | DFCW |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2200 m | -5.2 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 630 m | -3.1 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 160 m | +0.1 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 80 m | 0.0 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 60 m | -0.4 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 40 m | -0.1 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 30 m | +0.9 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 20 m | +0.7 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 17 m | +0.3 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 15 m | 0.0 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 12 m | -0.1 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 10 m | -0.4 | 132, 138, 150 | Pass | Pass | Pass | Pass | Pass |
| 8 m | — | None tested | Untested | Untested | Untested | Untested | Untested |
| 6 m | +13.7 | 132, 138, 150 | Pass | Pass* | Pass | Pass | Pass |
| 5 m | — | None tested | Untested | Untested | Untested | Untested | Untested |
| 4 m | — | None accepted for release | Excluded | Excluded | Excluded | Excluded | Excluded |
| 2 m | — | None accepted for release | Excluded | Excluded | Excluded | Excluded | Excluded |

*The 6 m WSPR asterisk identifies separately reviewed A/138 MHz receiver-only +125 Hz retune acceptance. The transmitted waveform and original nominal failed flags remain unchanged.*

138 MHz keyed modes have repeated trials; 132/150 MHz have single screens. WSPR means actual external expected-message decoding; keyed modes use the reviewed human-copy criteria.

4 m is directly representable only at 150 MHz, but required WSPR reliability failed and the operator excluded every mode. Direct 2 m is outside all three clocks' limits; 138 MHz third-harmonic pilots failed WSPR decoding and every mode is excluded. 8 m and 5 m were outside the agreed qualification matrix and remain untested.

The power reduction reuses the audited 26 post-clock Tone recordings, unchanged 20 dB SDR gain/250 ksample/s/no AGC/bias-T disabled, and the already selected 4.194304-second on/off Hann windows. It integrates power within ±25 Hz of the previously measured carrier, subtracts the matched off-window contribution and computes 10 log10(Pband/P80m). No capture, decoder trial, RF, calibration or original result changed. Four method controls passed. The independent review rechecked arithmetic, every small-file binding and unchanged raw identities without repeating the full raw audit.

Clock reconciliation: `build/phase14-accepted-clock-reconciliation-20261011.json`, SHA-256 `612ba1f6496cde361e194001d1d21123e221da3cf7cf3a86558c68294e4f4ff4`. Support dispositions: [phase14-band-support.json](phase14-band-support.json). Relative-power result: `/home/pi/phase14-qualification-20261008/build/resume-tools-e95334a-internal-first/build/relative-carrier-power-20261011T1710/result.json`, SHA-256 `48405182601257a95ea071c9f3c569b9d01c6e7cf2267e43a681341f04bf9224`. Independent review SHA-256 `c0d776c63d03eff65391a50b679a118bd2fef1a1170ffbb0d3b76d0368eb268c` in the same directory. Local retained metadata is `build/phase14-relative-power-reviewed-20261011.json`.
