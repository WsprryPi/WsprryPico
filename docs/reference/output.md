# Output and band limits

Normal firmware uses direct GPIO PIO/DMA output with a **138 MHz** system clock.
Its native numeric range is **100 kHz through 68,999,999 Hz**. Numeric admission
does not establish RF quality or legal operating permission.

| Range | Current operating boundary |
| --- | --- |
| 2200 m, 630 m, 160 m, 80 m, 60 m, 40 m, 30 m, 20 m, 17 m, 15 m, 12 m, 10 m, 6 m | Ordinary admitted bands; conducted tone/WSPR/QRSS/FSKCW/DFCW results exist at recorded points |
| 8 m and 5 m experimental envelopes | Explicit unqualified-frequency opt-in required; tested 40.001/60.001 MHz points do not qualify the entire envelopes |
| 4 m | Unavailable at 138 MHz; a separate 150 MHz build can represent it but fails the required reliable-WSPR support gate for all release modes |
| 2 m | Native direct output unavailable |

The RF output is **unfiltered**. Use an appropriate output filter, attenuation,
load and any amplifier. Conducted results establish neither antenna-ready
emissions nor calibrated transmitter power. Relative received carrier levels
are not transmitter watts. Nondefault drive strengths have no inherited
all-band qualification.

**Reported WSPR power** is message content. **GPIO drive** is a pad-current
selection. Neither is an RF power measurement. The optional amplifier-enable
output covers one entire job, including keyed gaps, and returns inactive when
the job stops. Check polarity and inactive behavior before attaching an amplifier.

Experimental frequency permissions are off by default. They do not override
engine limits, ownership, time, pin conflicts or output inhibition, and do not
change qualification. Band envelopes do not grant operating privileges.

The engineering [conducted support record](https://github.com/WsprryPi/WsprryPico/blob/devel/engineering/development/band-support.md)
identifies boards, images, clocks, modes and receiver paths. It is point-scoped
evidence and is not a measurement of every current image or frequency.
