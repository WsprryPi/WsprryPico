# Conducted band and mode support

Support applies to the recorded conducted test points and source/image scopes,
not every frequency within a band or the currently installed firmware. The
normal application clock is 138 MHz; 132/150 MHz are separately built images.
The [clock policy](clock-support.md) distinguishes synthesis availability from
qualification. Experimental consent cannot override engine limits.

- **Qualified:** Meets the recorded conducted carrier, decode or human-copy
  criterion for the identified board, source/image, clock and setup.
- **Unqualified:** Does not meet the applicable criterion. The required
  reliable-WSPR gate applies the 4 m disposition to all five modes.
- **Unavailable:** The native engine cannot construct the requested output.
- **Untested:** No result within the identified scope.

The 13-band A/B RF matrix uses direct GP2 PIO/DMA, divider 1 and RAM
rendering, source `119477a9c8c891db6f50c7a7dab7c9fbd2e16fac`, firmware version
`0.1.0-rc.2`. Its engineering UF2 SHA-256 identities are:

| System clock | UF2 SHA-256 |
| --- | --- |
| 132 MHz | `32dbb9ffcc3864c7f3d16804fedb8cacc3b9a0c4cf6568b2f88277b5c1957bdf` |
| 138 MHz | `7a73b0598c037a28edcc5886078a891701f1f76a3b26b1c4fc4c68868ab998a3` |
| 150 MHz | `ebef8cb7ce57e9421a48ae92140e3138b6a540791d0c1ac15852379105cff247` |

Pico A is USB `0BF4B4AEC9FFB344`, WTP identity
`fd6127d11d6aca42a9905fa3fb1bf1d5`; Pico B is USB `CDDBF8767C506C07`,
WTP identity `29f20b7342051ef947aa56cb9d4fab42`. The wspr5 conducted path uses
RSP1B `2404058C60` and GPSDO `0673ED0FA107`. Each source enters its own
20 dB attenuator, then the combiner and 40 dB attenuation to the SDR: nominal
60 dB source loss, no antenna or LPF. Receiver settings are CF32 at 250 ksps,
200 kHz bandwidth, gain 20, AGC/bias off, center carrier minus 25 kHz.
The shared reference comparison does not calibrate SDR sample time or absolute
UTC. Raw recordings are not retained for fresh reanalysis.

The separately selected 138 MHz consumer image has runtime SHA-256
`c96eeeeb4871bdcec40aa5b8fbc1dce42507b5fac6b00ee3a8b41838d5836d64`,
UF2 `17065bc7945a91d210bf3e48aedf1c6f5772f4386e7b26c04f364553afc6adad`,
and matching runtime/build/test source in commit
`74c73d548e2e05cf6f61978817d7de264da961ff` (compiled identity
`dda8a6eb1e69-dirty`). Its source-impact assessment and bounded smoke tests
retain their narrower scope. The older RF matrix is not relabelled as a
measurement of this consumer image or an arbitrary current rebuild.

Relative power is received fundamental carrier at 138 MHz relative to each
board's 80 m result, averaged across A/B in linear power. It includes the receiver
and path response; it is not calibrated transmitter watts/dBm. The 6 m increase
is not isolated as increased transmitter output.

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
| 8 m | — | 138 (A) | Qualified† | Qualified†‡ | Qualified† | Qualified† | Qualified† |
| 6 m | +13.7 | 132, 138, 150 | Qualified | Qualified* | Qualified | Qualified | Qualified |
| 5 m | — | 138 (A) | Qualified† | Qualified†‡ | Qualified† | Qualified† | Qualified† |
| 4 m | — | None accepted for release | Unqualified | Unqualified | Unqualified | Unqualified | Unqualified |
| 2 m | — | None available for native direct output | Unavailable | Unavailable | Unavailable | Unavailable | Unavailable |

*The 6 m WSPR result includes Pico A/138 MHz receiver-only +125 Hz retuning;
nominal receiver failures are not converted into nominal-tuning passes.*

† The 8 m/5 m scope is only Pico A, USB `0BF4B4AEC9FFB344`, GP2, 138 MHz,
source `165303458e49feaac1de54c8344058f56578d533`, UF2
`cb6ccfa3e9354d84c5ca3c993f4965f70716ed8bd99b076011406199fa1850eb`, at
40.001 and 60.001 MHz on the same identified A/GPSDO/attenuator/combiner/RSP1B
path, receiver channel 0 with a simultaneous GPSDO reference at base minus
40 kHz. Receiver helper v0.2.0 is SHA-256
`b98de116d696846b88eea1b3ad3f1b2a471052fa2ca440f4234fec7087dc5a03`, harness
source `62aa6e2ffa904a10b674bb1792a3bd66ba8afea6`. Pico B, other clocks and broad admission envelopes are
unqualified by those results. Experimental opt-in remains required.

‡ WSPR decodes `AA0NT EM18 37` with fixed receiver-audio translations +125 Hz
at 8 m and +200 Hz at 5 m. Nominal tuning passes 1/3 and 0/3 of the same accepted
sequences. The 5 m sequence requires known-inactive reboot and complete jobs
with exact realized NCO frequencies and merged equal-frequency events (127
events, the same sampled 162-symbol waveform). This does not guarantee that
every 162-event request admits under retained history. The
[point matrix](band-test-points.json) preserves refusals, invalid/partial
observations and the acceptance conditions.

138 MHz keyed modes include repeated trials; 132/150 MHz are single screens.
WSPR means external expected-message decoding. Keyed modes use human-copy
criteria. Native direct 4 m is unavailable at 132/138 MHz; at 150 MHz it remains
Unqualified under the reliable-WSPR gate. Native direct 2 m is unavailable at
all three clocks. Manually mapped third-harmonic pilots do not implement a
native route or qualify 2 m.

These results establish no LPF, calibrated power/frequency/launch timing,
antenna-ready emissions, general reliability or release qualification.
Nondefault GPIO drive inherits no all-band qualification. The
[machine-readable support catalog](band-support.json) carries these
scoped dispositions; numeric admission and legal operating permission remain
separate.
