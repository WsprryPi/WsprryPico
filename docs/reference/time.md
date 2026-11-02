# Time and frequency correction

**UTC**, Coordinated Universal Time, is the worldwide time standard used for transmission starts. It has no local time zone or daylight-saving adjustment. **RF frequency correction** adjusts the radio signal's frequency. Correct start time and correct radio frequency are separate settings and measurements.

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
| `synchronized` | The Pico has an accepted time source. A timed job must still pass its clock-age and uncertainty checks. |
| `using last time update` | Fresh time observations have stopped. The Pico estimates UTC from its last accepted time. A finite NTP timeout retains age and uncertainty limits; a zero timeout allows indefinite NTP holdover. Restore the time source when available. |
| **Unknown** or **Unavailable** | The browser has no current clock report. Restore the connection and refresh before relying on it. |

The value after **±** is the estimated timing uncertainty, in **ms** (milliseconds), not a countdown. With a finite NTP timeout, excessive uncertainty blocks new timed starts. Set the timeout in **Time and calibration**; **0** removes the Pico's NTP age and uncertainty cutoffs while keeping the uncertainty visible. An external controller can still request a stricter timing limit. After a restart, the Pico needs fresh time observations; saved clock-rate estimates do not preserve the current date and time.

## Use a trusted loopback while offline

With a supported Si5351 module and its loopback connected, **Trust local reference for Pico rate** can reduce timer drift after your phone supplies UTC through the authenticated Pico AP page. The phone supplies the date and time; the loopback helps maintain the clock rate. Configure its wiring and a known oscillator uncertainty in [Si5351 output settings](../configure.md#si5351-output-settings).

Loopback readings do not refresh the phone sample. Browser time still expires after at most one hour or when estimated uncertainty exceeds 500 ms. A lost loopback retains the learned rate under conservative uncertainty growth; removing trusted use returns to the uncorrected timer rate without stepping UTC. The initial phone-clock error remains. This does not provide GPS timing or calibrate RF frequency.

(manual-frequency-correction)=
## Manual frequency correction

**PPM** means parts per million. One ppm corresponds to 10 Hz at 10 MHz. **Manual correction (ppm)** compensates for a measured RF frequency error; its default is **0.000 ppm**. Leave it unchanged unless you have a measurement against an independent, trustworthy RF reference. Good network-clock status does not measure the RF carrier's frequency.

In **Station Control → Time and calibration → Carrier calibration**, the saved value loads automatically. Edit **Manual correction (ppm)**. Note the original value. Enter the measured correction, choose **Save calibration**, then measure the carrier again. The field accepts −100.000 through +100.000 ppm with up to three decimal places. The saved correction applies when a new job is prepared; it does not retune a job already running. Restore the original value if the adjustment is unsuccessful.

RF calibration does not change UTC or remove the normal clock, frequency, pin, and output checks.

## Browser time in the field

**Using browser time** means **Time supplied by this device’s clock**. The browser reads the operating-system clock of your phone, tablet, or computer; it does not independently verify UTC. Check the device’s clock before relying on it. Authentication is required, and another browser cannot replace a still-valid browser source simply by signing in.

The page refreshes time about every 30 seconds while active. Time updates do not extend the browser login’s inactivity timeout. A backgrounded, sleeping, disconnected, signed-out, or expired browser may stop supplying observations. The Pico then uses its last accepted time in holdover.

Browser holdover has a one-hour maximum. Its estimated uncertainty starts with a 250 ms device-clock allowance plus transfer and local processing allowances, then grows conservatively at 50 ppm (180 ms per hour). New starts require uncertainty no greater than 500 ms, or a stricter job limit. A slow initial transfer can therefore exhaust the budget before one hour. These are conservative software policy values, not a guarantee of the device clock’s accuracy or measured multi-day Pico holdover.

The NTP timeout setting, including zero, does not extend browser-time holdover or remove its uncertainty ceiling. Restart requires fresh observations. A valid higher-priority network or controller source retains authority. Conflicting source observations block new starts until consistent observations restore time. An already running job retains its local timing; an armed job that fails its launch clock check is missed.

The source display includes clock state, sample age, and estimated uncertainty. Restore an active authenticated AP page or another supported time source when time becomes unusable. Refreshing time does not enable schedules, clear a shutdown suspension, or replay missed occurrences.
