# Time and frequency correction

UTC determines when a timed job starts. RF frequency correction determines
where its carrier appears. These are separate settings and measurements.

The Pico's **μChrony** engine disciplines UTC from the configured network time
server. A connected controller can supply time through its supported transport.
The Pico checks clock age and uncertainty before admitting a job that needs
UTC. A restart needs fresh time; a retained rate estimate is not restored UTC.

The initial setup suggests **pool.ntp.org** as the time server. Keep that value unless you need a different server; choosing your own is optional. The setup form requires a valid server value, so leave the suggestion in place rather than clearing the field. Change it later in **Wi-Fi/Host**. Check network reachability and the clock status if launches are refused. Schedules use UTC, with no local time zone or daylight-saving interpretation.

RF carrier correction uses the saved **manual PPM** value. In
**Station/Transmission**, use the **Carrier calibration** controls to read
**Read saved calibration** before editing **Manual correction (ppm)**. Measure the actual carrier against an
independent trustworthy RF reference, choose **Save calibration** and verify
the carrier again. The saved correction applies to future job preparation.
Retain the original value so an unsuccessful adjustment can be reversed.
An attached GPSDO or improved network-time status alone is not RF calibration.

Internet NTP-derived RF calibration, GPS/PPS input, automatic NTP-server
selection and amplifier settling/lead/tail timing are unavailable.
No calibration action removes frequency, clock, hardware or output guards.
