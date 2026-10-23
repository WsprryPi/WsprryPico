# Time and frequency correction

**UTC**, Coordinated Universal Time, is the worldwide time standard used for transmission starts. It has no local time zone or daylight-saving adjustment. **RF frequency correction** adjusts the radio signal's frequency. Correct start time and correct radio frequency are separate settings and measurements.

## Set the time source

The Pico sets and maintains its clock from the configured **time server**, using NTP, the Network Time Protocol. Its clock software is called **μChrony**. A connected WsprryPi controller can also supply time over a supported connection, including USB.

The initial setup suggests **pool.ntp.org** as the time server. Keep that value unless you need a different server. The setup form requires a valid server value, so leave the suggestion in place rather than clearing the field. Change it later in **Wi-Fi/Host**.

An Internet time server needs Internet access from the Pico. For an isolated network, use a reachable local NTP server or a supported controller-time connection. Opening the Pico's browser page does not by itself set its clock.

Enter every **Start time (UTC)** and **Schedule expiry (UTC)** as UTC, even if the browser uses your usual date format. For example, a desired start of 12:10 UTC is entered as 12:10; do not substitute the time shown by your local clock. The [schedule examples](../configure.md#frequency-and-schedules) show UTC start times.

## Read the clock status

In **Transmitter status**, choose **Refresh** and read **Clock**:

| Status | Meaning and action |
| --- | --- |
| `unsynchronized` | The Pico has no currently usable UTC estimate. Check its network and time server, or the controller-time connection, and allow fresh synchronization. |
| `synchronized` | The Pico has an accepted time source. A timed job must still pass its clock-age and uncertainty checks. |
| `holdover` | Fresh time observations have stopped. The Pico is estimating time from its previously synchronized clock; new starts are allowed only while its age and uncertainty remain within limits. Restore the time source. |
| **Unknown** or **Unavailable** | The browser has no current clock report. Restore the connection and refresh before relying on it. |

The value after **±** is the estimated timing uncertainty, in **ms** (milliseconds), not a countdown. If that error estimate grows too large, the Pico refuses new timed starts. After a restart it needs fresh time observations; saved clock-rate estimates do not preserve the current date and time.

## Manual frequency correction

**PPM** means parts per million. One ppm corresponds to 10 Hz at 10 MHz. **Manual correction (ppm)** compensates for a measured RF frequency error; its default is **0.000 ppm**. Leave it unchanged unless you have a measurement against an independent, trustworthy RF reference. Good network-clock status does not measure the RF carrier's frequency.

In **Station/Transmission → Carrier calibration**, choose **Read saved calibration** before editing **Manual correction (ppm)**. Keep a note of the original value. Enter the measured correction, choose **Save calibration**, then measure the carrier again. The field accepts −100.000 through +100.000 ppm with up to three decimal places. The saved correction applies when future jobs are prepared; it does not retune a job already running. Restore the original value if the adjustment is unsuccessful.

RF calibration does not change UTC or remove the normal clock, frequency, pin and output checks.
