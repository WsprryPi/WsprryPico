# Output and band limits

One normal firmware image supports **Direct GPIO** and the qualified external **Si5351** setup. Select the RF engine in Radio pins.

(gpio-drive-strength)=
## Direct GPIO output

The direct engine generates **RF**, a radio-frequency signal, on the configured **GPIO output pin**. The factory selection is **GP2, physical pin 4**; see [hardware preparation](../start.md#hardware-connections) for wiring and other pin choices. The Pico uses a **138 MHz** system clock for this output.

The generator's numeric range is **100 kHz through 68,999,999 Hz**. **1 kHz is 1,000 Hz; 1 MHz is 1,000,000 Hz.** That range does not mean every frequency inside it is enabled or suitable for transmission. The firmware also checks permissions for the selected band and frequency.

| Range | Current operating boundary |
| --- | --- |
| 2200 m, 630 m, 160 m, 80 m, 60 m, 40 m, 30 m, 20 m, 17 m, 15 m, 12 m, 10 m, 6 m | Enabled by the normal frequency policy, subject to the chosen frequency, RF setup, and operating privileges |
| 8 m and 5 m experimental ranges | Disabled by default; require explicit advanced experimental-frequency permission |
| 4 m | Unavailable with direct GPIO in the normal 138 MHz firmware |
| 2 m | Unavailable with direct GPIO output |

For standalone WSPR, enter the whole-Hz USB dial in **WSPR dial frequency (Hz)**. The four RF tones surround dial +1,500 Hz, and every tone must fit the generator range and frequency permissions. On numeric engine limits alone, the normal 138 MHz engine allows dial values from 98503 through 68998496 Hz; frequency permissions also apply. The dial is a reference, not an emitted RF frequency.

### Measured bare-GPIO power

The following graphs show a bare **Pico 2 W GP2** sweep recorded on
**24 November 2026 (UTC)** by Lee Bussy [AA0NT]. GP2 was connected through a
coax adapter directly to an **HP 8482A power sensor** and **HP 437B power meter**,
without an output filter, amplifier, or attenuator chain. The sweep covered
13 frequency settings from **137,500 Hz to 50,294,500 Hz** at each of the
**2, 4, 8, and 12 mA** GPIO drive settings, with two readings averaged per point.

These are **meter-indicated power readings at the sensor input**, with the
recorded sensor calibration factors applied. The unfiltered output includes
harmonics, so the readings do not isolate power at the wanted frequency.
No additional fixture-loss correction, uncertainty estimate, or baseline
subtraction is included. The plots describe this measured setup; they do not
establish guaranteed output power, filtered antenna power, or emissions compliance.

![Meter-indicated bare GP2 power versus frequency setting, with separate curves for 2, 4, 8, and 12 mA GPIO drive. Power generally falls as frequency increases.](../_static/images/output/pico2w-bare-gpio-power-frequency.png)

*Power versus frequency setting.* Band labels identify the requested test
frequencies and are equally spaced; the horizontal axis is not a linear
frequency scale. At 12 mA, the mean indication was **28.0 mW** at 475,700 Hz,
**23.5 mW** at 14,097,100 Hz, and **14.2 mW** at 50,294,500 Hz.

![Meter-indicated bare GP2 power versus the four GPIO drive settings, with one curve per tested band from 2200 m through 6 m. Higher drive increases indicated power, with a smaller increase from 8 to 12 mA.](../_static/images/output/pico2w-bare-gpio-power-drive.png)

*Power versus GPIO drive setting.* Drive labels are equally spaced categories,
not a linear current scale. Increasing drive raised the indication at every
sampled frequency, with a smaller increase from 8 to 12 mA than from 4 to 8 mA.
GPIO drive remains an electrical setting, not a calibrated RF-power control.

The graphs are reproduced from the HP 437B Automation `report-revised-6`
bare-GPIO report, record `b38bd9c81f104aa3bdb36ea952c14835` (52 completed
points). Meter serial: `3125U22346`; sensor serial: `MY41094127`;
sensor-correction profile: `8482a-MY41094127-20261015`. These measurements
apply to direct GPIO output; the Si5351 results below use a separate RF path.

## Si5351 output

Ordinary firmware supports the [qualified QRP Labs Rev. 6 / 25 MHz TCXO setup](../configure.md#si5351-output-settings). RF comes from the module's CLK0 connector, rather than a Pico RF GPIO. The numeric synthesis range is **8 kHz–160 MHz**, subject to complete-plan validation; this is not qualification of every frequency or configuration in that range. Other module/reference/drive arrangements require an engineering build.

Conducted tone, WSPR, QRSS, FSKCW, and DFCW tests passed at each sampled RF frequency below. These are emitted RF frequencies, not WSPR USB dial settings.

| Band | Tested RF frequency (Hz) | Current operating boundary |
| --- | ---: | --- |
| 2200 m | 137500 | Enabled by the normal frequency policy |
| 630 m | 475700 | Enabled by the normal frequency policy |
| 160 m | 1838100 | Enabled by the normal frequency policy |
| 80 m | 3570100 | Enabled by the normal frequency policy |
| 60 m | 5288700 | Enabled by the normal frequency policy |
| 40 m | 7050000 | Enabled by the normal frequency policy |
| 30 m | 10140200 | Enabled by the normal frequency policy |
| 20 m | 14097100 | Enabled by the normal frequency policy |
| 17 m | 18106100 | Enabled by the normal frequency policy |
| 15 m | 21096100 | Enabled by the normal frequency policy |
| 12 m | 24926100 | Enabled by the normal frequency policy |
| 10 m | 28126100 | Enabled by the normal frequency policy |
| 8 m | 40001000 | Disabled by default; requires explicit advanced experimental-frequency permission |
| 6 m | 50294500 | Enabled by the normal frequency policy |
| 5 m | 60001000 | Disabled by default; requires explicit advanced experimental-frequency permission |
| 4 m | 70400000 | Disabled by default; requires explicit advanced experimental-frequency permission |
| 2 m | 144490500 | Disabled by default; requires explicit advanced experimental-frequency permission |

Every transmission remains subject to the chosen frequency, RF setup, and operating privileges. These results apply to the recorded Pico C engineering image and QRP Labs Rev. 6 / 25 MHz TCXO setup, using CLK0 at **8 mA**. They qualify the sampled points under those test conditions, rather than complete band ranges or other module/reference/drive configurations. All three consecutive WSPR frames decoded the expected message at each point; CW acceptance uses human-readable marks and frequency states. These results do not establish calibrated frequency, power, emissions, or absolute UTC timing.

## RF connections and permissions

The band names in metres describe approximate radio wavelengths. They are not frequency entries for the browser's Hz fields. Use a frequency appropriate for your chosen mode and operating privileges.

The RF output is **unfiltered**. It contains the wanted signal and unwanted frequencies, including **harmonics**, which are multiples of the intended frequency. Use a suitable output filter before connecting to an antenna. A **load** is the circuit or device receiving the output; use a suitable test load or measurement connection while checking the setup. **Attenuation** reduces signal level to suit the next device. Filtering, attenuation, the load, and any amplifier must suit the frequency and signal level.

**Reported WSPR power** is the power value sent in the beacon message. **GPIO drive** selects the output pin's electrical drive setting: **2, 4, 8, or 12 mA**, with **12 mA** for a new installation. Settings-preserving upgrades retain the saved drive strength. Neither control measures RF power. Measure the actual output with suitable equipment; a received signal level alone is not a transmitter-power measurement. Recheck the RF setup when changing drive, frequency, filtering, or amplification. The [radio defaults table](defaults.md#radio-pins-and-filtering) also lists the initial pin, amplifier, and filtering selections.

The optional **amplifier-enable** output is a separate logic control signal. It stays active for an entire job, including message gaps, and becomes inactive when the job stops. It does not supply amplifier power. Before connecting amplifier control circuitry, check its [pin and polarity settings](../configure.md#pins-and-drive).

The optional [LPF / band selector](../configure.md#lpf-and-band-selector) chooses one external filter for each complete job. Its output settles before amplifier enable and remains selected until after amplifier disable. Required selection checks every nominal and programmed RF frequency against declared ranges. Fixed/manual filtering leaves selector outputs inactive. These controls do not measure or certify the external filter.

Experimental frequency permissions are advanced configuration settings; the ordinary browser form does not edit them. They do not expand the generator's limits or bypass time, control ownership, pin, or output checks. Permission in firmware is not a statement of RF performance or local operating authority.
