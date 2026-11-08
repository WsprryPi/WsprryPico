# Time and frequency correction

**UTC**, Coordinated Universal Time, is the worldwide time standard used for transmission starts. It has no local time zone or daylight-saving adjustment. **RF frequency correction** adjusts the radio signal's frequency. Correct start time and correct radio frequency are separate settings and measurements.

## Understand the output and reference options

Choose an RF output engine first, then configure the time source and any frequency correction needed for that hardware. GPS and PPS can be used with either RF engine.

| Option | What it does | When to use it |
| --- | --- | --- |
| **Direct GPIO / PIO** | Generates the RF signal using the Pico's clock and an RF GPIO. The validation setup uses GP2. | Select this engine when using the Pico's direct RF output. |
| **Si5351** | Generates RF with an external synthesizer and its own crystal or TCXO reference, controlled by the Pico over I²C. | Select this engine when using a supported Si5351 module. |
| **GPS serial input** | Supplies UTC date/time labels and position from the receiver. | Connect it together with PPS for GPS time and automatic GPS/PPS calibration. GPS is optional when another supported time source is available. |
| **PPS input** | Marks each second boundary. The associated GPS serial message identifies which UTC second it is. | Use it with the GPS serial input and a validated pulse association. |
| **Si5351 CLK2 loopback** | Lets the Pico measure the synthesizer reference separately from its own clock. | Required for automatic Si5351 frequency correction; also supports optional trusted-reference clock-rate assistance. |
| **Manual or automatic carrier correction** | Compensates for RF frequency error. With automatic correction enabled, manual correction becomes residual trim. | Use a measured manual correction, or GPS/PPS automatic correction after checking the result against a trustworthy reference. |

The [RF output engine](../configure.md#rf-output-engine), [Si5351 output settings](../configure.md#si5351-output-settings), and [GPS and PPS](../configure.md#gps-and-pps) sections explain the controls and wiring. A GPSDO used to measure the transmitted carrier is external test equipment; it is not required for normal operation.

## Set the time source

The Pico sets and maintains its clock from the configured **time server** using NTP (the Network Time Protocol). Its clock software is called **μChrony**. A connected WsprryPi controller can also supply time over a supported connection, including USB.

The initial setup suggests **pool.ntp.org** as the time server. Keep that value unless you need a different server. The setup form requires a valid server value, so leave the suggestion in place rather than clearing the field. Change it later in **Wi-Fi/Host**.

An Internet time server needs Internet access from the Pico. For an isolated network, use a reachable local NTP server or a supported controller-time connection. After authentication on the Pico’s AP, the control page automatically supplies browser time if no usable higher-priority source is available. Merely opening an unauthenticated page does not establish transmit-ready time.

**Start time (UTC)** and **Schedule expiry (UTC)** have UTC **Date** and **Time** controls. If either component is empty, opening either picker fills both with the current UTC date and time. Once both are valid, selecting a date preserves the time and selecting a time preserves the date. **Today (UTC)** and **Now (UTC)** update only their respective component. The pickers use the Pico's most recently observed UTC clock when available, advanced by elapsed browser time; otherwise they use the browser's UTC clock. These defaults do not replace the Pico's clock admission checks.

The text field accepts `YYYY-MM-DD HH:MM:SS`, with a 24-hour clock. Enter a future UTC time for a transmission start; the page rejects a past start before requesting transmitter ownership. Observation timestamps also use UTC. For example, a desired start of 12:10 UTC is entered as 12:10. The [schedule examples](../configure.md#frequency-and-schedules) show UTC start times.

(read-the-clock-status)=
## Read the clock status

In **Transmitter status**, choose **Refresh** and read **Clock**:

| Status | Meaning and action |
| --- | --- |
| `unsynchronized` | The Pico has no currently usable UTC estimate. Check its network and time server, or the controller-time connection, and allow fresh synchronization. |
| `synchronized` | The Pico has an accepted time source. Timed jobs still require a valid source age and safe leap state. |
| `using last time update` | Fresh time observations have stopped. The Pico estimates UTC from its last accepted time. A finite NTP timeout retains its source-age limit; a zero timeout allows indefinite NTP holdover. Restore the time source when available. |
| **Unknown** or **Unavailable** | The browser has no current clock report. Restore the connection and refresh before relying on it. |

The value after **±** is the estimated timing uncertainty, in **ms** (milliseconds), not a countdown. UTC uncertainty is displayed for your judgment and does not automatically block first-party transmissions. Set the source-age timeout in **Time and calibration**; **0** allows indefinite NTP holdover while keeping uncertainty visible. An external WTP controller can explicitly request its own timing limit. After a restart, the Pico needs fresh time observations; saved clock-rate estimates do not preserve the current date and time.

## Use GPS time without a network

An optional GPS receiver can supply UTC through separate serial and PPS inputs after its pulse association has been independently validated. Configure it under [Radio pins → GPS and PPS](../configure.md#gps-and-pps). Time, position, and RF calibration have separate validity: a missing position does not automatically invalidate usable UTC, and serial reception does not prove PPS timing. GPS holdover is at most one hour; the NTP timeout setting, including zero, does not extend it.

PPS defines the second boundary; the serial message supplies its UTC label. Serial messages can arrive after another PPS, so the Pico selects the original captured edge using the receiver's qualified delay window. Serial arrival does not move that edge or set the oscillator measurement interval.

GPS/PPS can measure the Pico oscillator, while PPS plus CLK2 loopback measures the independent Si5351 reference. The clock's UTC rate and these two oscillator errors are different quantities. Manual correction stays separate and becomes residual trim when automatic correction is enabled. The page reports each calibration's age and estimated bound. PPS capture also reports IRQ latency separately from the corrected timestamp error bound; neither value establishes the receiver's absolute UTC accuracy. Fresh measurements are required after restart, and improved clock statistics alone do not establish carrier accuracy.

## GPS/PPS validation scope

Conducted checks on the validation platform exercised Si5351 CLK0 output with CLK2 loopback, GPS-only startup without NTP, correction behavior and a complete paired WSPR transmission. They do not establish calibrated absolute RF launch timing or consistently improved absolute carrier accuracy.

GP2 is the separate direct GPIO RF output. GPS/PPS automatic correction improved its measured carrier accuracy at the selected 160 m, 60 m and 10 m test points in two off/on comparisons per point. Si5351 correction did not show consistent improvement across both comparisons. Check carrier accuracy for the hardware and settings in use; automatic correction does not guarantee that every oscillator becomes more accurate. Launch timing is accepted for the intended operating needs, with roughly one second early or late acceptable; this is not a precision UTC timing guarantee. PPS remained connected. Loss and reacquisition are covered by software checks; physically removing the PPS wire is outside the selected test scope.

### Measured carrier-error examples

These examples show why measuring before and after enabling automatic correction is useful. They use Pico C, a QRP Labs Si5351 module with a 25 MHz TCXO, and the direct GP2 output. Each selected RF output was measured alongside a GPSDO reference tone with an SDRplay RSP1B. The reference was 500 Hz away, and each tone lasted 12 seconds. No antenna was used.

**Correction off** uses zero manual correction. **GPS/PPS correction on** uses automatic correction with zero manual residual. Each range below covers two repeats. Negative error means the measured carrier is below its nominal frequency; positive error means it is above. Each cell shows **Hz**, with **PPM in parentheses** below it. PPM means parts per million: `PPM = error in Hz ÷ nominal frequency in Hz × 1,000,000`. The nominal test frequencies are **1.840100 MHz** on 160 m, **5.366200 MHz** on 60 m, and **28.126100 MHz** on 10 m. Both units are calculated from unrounded measurements, then rounded for display.

| RF output | Band | Correction off | GPS/PPS correction on | Largest measurement allowance |
| --- | --- | --- | --- | --- |
| Si5351 | 160 m | −0.148 to −0.146<br>(−0.0805 to −0.0791) | +0.075 to +0.192<br>(+0.0406 to +0.1043) | ±0.09<br>(±0.0481) |
| Si5351 | 60 m | −0.458 to −0.455<br>(−0.0853 to −0.0847) | +0.189 to +0.538<br>(+0.0353 to +0.1002) | ±0.13<br>(±0.0237) |
| Si5351 | 10 m | −2.809 to −2.770<br>(−0.0999 to −0.0985) | +0.600 to +2.448<br>(+0.0213 to +0.0870) | ±0.44<br>(±0.0153) |
| GP2 | 160 m | −2.066 to −1.959<br>(−1.1225 to −1.0648) | −0.244 to −0.036<br>(−0.1328 to −0.0198) | ±0.11<br>(±0.0584) |
| GP2 | 60 m | −6.058 to −5.826<br>(−1.1289 to −1.0856) | −0.780 to −0.195<br>(−0.1454 to −0.0363) | ±0.20<br>(±0.0373) |
| GP2 | 10 m | −31.921 to −30.888<br>(−1.1349 to −1.0982) | −0.537 to +1.000<br>(−0.0191 to +0.0355) | ±0.83<br>(±0.0293) |

The last column gives the largest declared measurement allowance across the four measurements in each row, rounded outward separately in Hz and PPM. It includes the GPSDO reference, SDR sample-rate and frequency-estimation allowances. The ranges show variation between repeats; they are not uncertainty bounds. These are results for the tested hardware and settings, not guaranteed errors for other boards.

GP2 improved beyond the measurement allowances on all three bands in both repeats.

The Si5351 we tested was already close to the correct frequency. Automatic correction sometimes helped and sometimes made the error worse. The results varied too much, and the remaining errors were too small to measure precisely enough, to show a consistent benefit.

Measure the carrier before and after enabling automatic correction. If it doesn’t help, leave it off or use a measured manual adjustment.

## Use a trusted loopback while offline

With a supported Si5351 module and its loopback connected, **Trust local reference for Pico rate** can reduce timer drift after your phone supplies UTC through the authenticated Pico AP page. The phone supplies the date and time; the loopback helps maintain the clock rate. Configure its wiring and a known oscillator uncertainty in [Si5351 output settings](../configure.md#si5351-output-settings).

Reference hardware, its uncertainty allowance and hardware qualification are local operator decisions. The displayed uncertainty applies the configured reference allowance and software drift assumptions; shared bench results do not certify an oscillator or guarantee absolute UTC accuracy.

Loopback readings do not refresh the phone sample. Browser time still expires after at most one hour. UTC uncertainty remains visible throughout that interval. A lost loopback retains the learned rate under conservative uncertainty growth; removing trusted use returns browser UTC to the uncorrected timer rate, while NTP UTC returns to its independent network-rate estimate. Neither change steps UTC. The initial phone-clock error remains. The displayed bound includes the reference allowance, capture error and conservative Pico drift; a more accurate reference does not erase the error already accumulated. This does not provide GPS timing or calibrate RF frequency.

(manual-frequency-correction)=
## Manual frequency correction

**PPM** means parts per million. One ppm corresponds to 10 Hz at 10 MHz. **Manual correction (ppm)** compensates for a measured RF frequency error; its default is **0.000 ppm**. Leave it unchanged unless you have a measurement against an independent, trustworthy RF reference. Good network-clock status does not measure the RF carrier's frequency.

In **Station Control → Time and calibration → Carrier calibration**, the saved value loads automatically. Edit **Manual correction (ppm)**. Note the original value. Enter the measured correction, choose **Save calibration**, then measure the carrier again. The field accepts −100.000 through +100.000 ppm with up to three decimal places. The saved correction applies when a new job is prepared; it does not retune a job already running. Restore the original value if the adjustment is unsuccessful.

RF calibration does not change UTC or remove the normal clock, frequency, pin, and output checks.

## Browser time in the field

**Using browser time** means **Time supplied by this device’s clock**. The browser reads the operating-system clock of your phone, tablet, or computer; it does not independently verify UTC. Check the device’s clock before relying on it. Authentication is required, and another browser cannot replace a still-valid browser source simply by signing in.

The page refreshes time about every 30 seconds while active. Time updates do not extend the browser login’s inactivity timeout. A backgrounded, sleeping, disconnected, signed-out, or expired browser may stop supplying observations. The Pico then uses its last accepted time in holdover.

Browser holdover has a one-hour maximum. Its estimated uncertainty starts with a 250 ms device-clock allowance plus transfer and local processing allowances, then grows conservatively at 50 ppm (180 ms per hour). Uncertainty does not impose an additional first-party start cutoff. These are conservative software policy values, not a guarantee of the device clock’s accuracy or measured multi-day Pico holdover.

The NTP timeout setting, including zero, does not extend browser-time holdover. Restart requires fresh observations. A valid higher-priority network or controller source retains authority. Conflicting source observations block new starts until consistent observations restore time. An already running job retains its local timing; an armed job that fails its launch clock check is missed.

The source display includes clock state, sample age, and estimated uncertainty. Restore an active authenticated AP page or another supported time source when time becomes unusable. Refreshing time does not enable schedules, clear a shutdown suspension, or replay missed occurrences.
