# Output and band limits

The normal firmware generates **RF**, a radio-frequency signal, directly on the configured **GPIO output pin**. The factory selection is **GP2, physical pin 4**; see [hardware preparation](../start.md#hardware-connections) for wiring and other pin choices. The Pico uses a **138 MHz** system clock for this output.

The generator's numeric range is **100 kHz through 68,999,999 Hz**. **1 kHz is 1,000 Hz; 1 MHz is 1,000,000 Hz.** That range does not mean every frequency inside it is enabled or suitable for transmission. The firmware also checks the selected band and frequency permissions.

| Range | Current operating boundary |
| --- | --- |
| 2200 m, 630 m, 160 m, 80 m, 60 m, 40 m, 30 m, 20 m, 17 m, 15 m, 12 m, 10 m, 6 m | Enabled by the normal frequency policy, subject to the chosen frequency, RF setup and operating privileges |
| 8 m and 5 m experimental ranges | Disabled by default; require explicit advanced experimental-frequency permission |
| 4 m | Unavailable in the normal 138 MHz firmware |
| 2 m | Unavailable with direct GPIO output |

For standalone WSPR, enter the whole-Hz USB dial in **WSPR dial frequency (Hz)**. The four RF tones surround dial +1,500 Hz, and every tone must fit the generator range and frequency permissions. The normal 138 MHz engine allows dial values from 98503 through 68998496 Hz on numeric engine limits alone; frequency permissions also apply. The dial is a reference, not an emitted RF frequency.

The band names in metres describe approximate radio wavelengths. They are not frequency entries for the browser's Hz fields. Use a frequency appropriate for your chosen mode and operating privileges.

The RF output is **unfiltered**. It contains the wanted signal and unwanted frequencies, including **harmonics**, which are multiples of the intended frequency. Use a suitable output filter before an antenna connection. A **load** is the circuit or device receiving the output; use a suitable test load or measurement connection while checking the setup. **Attenuation** reduces signal level to suit the next device. Filtering, attenuation, the load and any amplifier must suit the frequency and signal level.

**Reported WSPR power** is the power value sent in the beacon message. **GPIO drive** selects the output pin's electrical drive setting, in milliamps. Neither control measures RF power. Measure the actual output with suitable equipment; a received signal level alone is not a transmitter-power measurement. Recheck the RF setup when changing drive, frequency, filtering or amplification.

The optional **amplifier-enable** output is a separate logic control signal. It stays active for an entire job, including message gaps, and becomes inactive when the job stops. It does not supply amplifier power. Check its [pin and polarity settings](../configure.md#pins-and-drive) before connecting amplifier control circuitry.

The optional [LPF / band selector](../configure.md#lpf-and-band-selector) chooses one external filter for each complete job. Its output settles before amplifier enable and remains selected until after amplifier disable. Required selection checks every nominal and programmed RF frequency against declared ranges. Fixed/manual filtering leaves selector outputs inactive. These controls do not measure or certify the external filter.

Experimental frequency permissions are advanced configuration settings; the ordinary browser form does not edit them. They do not expand the generator's limits or bypass time, control ownership, pin or output checks. Permission in firmware is not a statement of RF performance or local operating authority.

The engineering [conducted support record](https://github.com/WsprryPi/WsprryPico/blob/devel/engineering/development/band-support.md) identifies the exact boards, firmware, clocks, modes, frequencies and measurement connections used for its results. Those measurements do not establish performance for every installation or frequency.
