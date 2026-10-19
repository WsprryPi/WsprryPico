# Independent Internet NTP clock measurements

Current disposition: [NTP work is closed](ntp-work-closeout.md). μChrony is
retained for UTC discipline and future GPS/PPS input; NTP-derived RF calibration
is rejected. The Pico-to-Pi GPIO pulse path is retired. Results below describe
their recorded images and evidence, not current operating instructions.

Independent physical RF measurements resolve oscillator frequency error on both
boards. Applying each measured oscillator error to the contemporaneous UTC
clock mapping distinguishes a useful learned frequency correction from a
statistical uncertainty estimate. Absolute UTC phase remains unresolved with
the current USB measurement path. No NTP-derived RF correction was applied.

At the final checkpoint, A's learned frequency component reduced the inferred
rate-error magnitude from about 0.86 to 0.17 ppm; B improved from about 0.97
to 0.65 ppm. B's earlier estimates substantially overcorrected before
narrowing. This establishes an instantaneous frequency benefit at the final
measurements, with the reference assumptions below; it does not establish a
uniform benefit throughout startup or smaller absolute UTC phase error.

## Physical measurement and clock binding

The RF measurements below used normal Pico 2 W firmware `0.0.0-devel`, source
`46c4a9e5a4a64912caed1c20ceb3399b4aa5b53d`, normal UF2 SHA-256
`416da27b8bba8a05516948d9441b65b4f597b55d16880289f048488769fec851`,
`pio-dma-gp2` at nominal 138 MHz. A is USB `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`; B is USB `CDDBF8767C506C07`, device
`29f20b7342051ef947aa56cb9d4fab42`. The source image is unchanged from the
[earlier crossover](microchrony-live-comparison.md).

Both boards use `pool.ntp.org`. B changed from `time.local` with a saved-setting
readback and software restart at approximately 14:38:37 CDT on October 18,
2026. A retained its existing pool association and older history. Checkpoint
labels refer to elapsed time after B's restart; they are not A's boot age.
Other saved settings, manual `0.000` PPM, disabled schedules and all production
quality gates remained unchanged. Boards were unowned/inactive between the
finite two-second tone jobs.

The user-confirmed conducted path combines A, B and GPSDO, each with nominal
60 dB attenuation, into RSP1B `2404058C60` on wspr5. The LBE-1421 GPSDO
`0673ED0FA107` had satellite/PLL lock and antenna OK. Its temporary 40 kHz
Output 1 supplies simultaneous harmonics at 3.56 and 3.64 MHz, bracketing a
Pico tone requested at 3.5701 MHz. Two references identify both receiver
frequency offset and sample-rate scale in the same coherent IQ interval.
No single-line offset subtraction or unverified SDR TCXO specification is
used as a complete calibration.

Recordings use CF32 at 250 kS/s, center 3.55 MHz, 200 kHz bandwidth, gain 20,
channel 0, AGC and bias tee off. Complete sample hashes, exact settings,
receiver identity, zero overflow/clipping and verified receiver cleanup are
checked. Fits exclude 0.3 seconds at either tone edge. Every included line
retains contrast >=30 dB, phase residual RMS <0.15 rad and minimum/median
amplitude >=0.5. A half-window frequency difference above 0.1 Hz refuses the
measurement. The 3.48 MHz harmonic failed the phase criterion and is excluded.

Displayed intervals propagate explicit +/-0.05 Hz line-fit and +/-10 ppb
GPSDO engineering allowances with exact rational interval arithmetic. The
allowances, receiver-axis linearity and reference harmonic identification
have not been independently certified; these are conditional engineering
measurement intervals, not traceable absolute calibration certificates.
Only this frequency and conducted setup were measured.

The accepted NCO realization is 3,570,100.004319102 Hz at nominal clock rate.
The raw oscillator error uses this realized value rather than the requested
frequency. Firmware register checks bind RF SYS/PLL and the raw TIMER0
reference to the same XOSC. This establishes clock topology, not its absolute
frequency; the simultaneous GPSDO reference supplies that measurement.

For measured raw error r in ppm and UTC rate u in ppb:

```text
UTC frequency error (ppm) = r * (1 + u / 1,000,000,000) + u / 1,000
```

API-before / INFO / API-after snapshots bind board boot, source revision,
active SNTP arbiter, source disagreement, clock generation and estimator
generation. The 15/30-minute tones additionally contain running GET_CLOCK
snapshots, matched to the actual tone's raw interval. UTC/raw finite
differences must agree with the reported applied rate using a conservative
2 microsecond endpoint-difference allowance. The pure learned frequency
component is separated from intentional phase slew. An initial A measurement
spanned a model update and is excluded from correction-benefit verdicts.

A frozen-phase comparison removes only the learned frequency component from
the current mapping while keeping its current phase-slew rate. It measures
instantaneous incremental frequency effect. It is not a causal replay of a
phase-only controller's entire prior history or proof of smaller UTC epoch
error. Phase slew can deliberately increase instantaneous frequency error
while removing a phase offset.

## Retired GPIO measurement and current scope

The former Pico-to-Pi GPIO output measurement path is removed from maintained
firmware and host tools. It is not required wiring and supplies no Pico clock
input. The [retirement record](clock-pulse-probe.md) and
[last attempt](microchrony-control-fixes-results.md) retain the unresolved
measurement fault and the evidence limits. The Pi GPS/PPS setup remains unchanged.

The RF observations above are historical measurements of the recorded image.
Their inferred corrected UTC frequency is not a measurement of corrected RF
output. The current product uses μChrony for UTC discipline and saved manual
PPM for RF. NTP-derived RF calibration is rejected and item 4.3 is closed by
[decision](ntp-work-closeout.md), not by a claim of physical acceptance.

Future GPS/PPS input will reuse μChrony's estimator and controller through the
reference-input work in the [backlog](consolidated-backlog.md#remain-in-backlog-for-future).
That work must separately qualify input latency, UTC pairing, holdover and any
future physical RF application. No GPS/PPS input or RF calibration capability
is implied by the retained NTP software comparisons.
