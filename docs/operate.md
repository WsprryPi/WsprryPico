# Operate

Before starting, check the full device identity, saved frequency and station,
active pins, output load/filter, time readiness and ownership. Resolve any
restart or output-inhibit message first.

## WSPR schedules

Enable the reviewed standalone schedule in **Station/Transmission**. Occurrences
use UTC period boundaries plus the selected phase and a one-second launch
offset. The Pico reserves each occurrence before transmitting. It does not
catch up missed windows or replay consumed slots after a restart or failure.

An ordinary callsign uses Type 1 with a four-character on-air locator. Supported
compound calls use Type 2 with a four-character locator, or Type 2 followed by
Type 3 in adjacent two-minute windows with a six-character locator. A bracketed
call selects Type 3 only and requires six locator characters. Read the planner's
accepted result; unsupported identities are refused rather than shortened.

Type 2 contains no locator. Type 3 carries a callsign hash, so receivers may
need the preceding Type 2 or other callsign context to display the full call.
A cold receiver can show `<...>` with grid and power. Some suffix encodings
are ambiguous (`/Q`–`/Z` overlap `/00`–`/09`); hash collisions are possible.
The recorded successful Type 2/3 pair is one board/image/payload at 3.570100 MHz,
not a general guarantee for every receiver or compound call.

## Send QRSS, FSKCW or DFCW

1. Choose **Send a message**, select the mode and enter the message, frequency,
   shift where applicable, dot duration, repeats and gaps.
2. Review the compiled preview. Messages accept up to **32 characters including
   spaces**. The entire job, including repeats, gaps and tails, must fit
   **512 events and 60 minutes**; 32 characters can still exceed those limits.
3. Enter **Start time (UTC)** and choose **Load and arm message**. A UTC-timed
   job needs an acceptable clock. Watch the shared status for admission or
   refusal; a button click alone is not confirmation of output.

QRSS keys the carrier on and off. FSKCW keeps it active and shifts it downward
during gaps. DFCW distinguishes dots and dashes by frequency.

For a finite test tone, use WsprryPi's tone control or prepare a complete encoded
tone job. The Pico page has no dedicated tone editor. Open **Load a job file**,
select its **Job JSON file**, enter **Start time (UTC)** and choose **Load and
arm job**. These advanced jobs use the same readiness/ownership checks; invalid
or oversized plans are refused before execution.

## Status, stop and connection loss

Use **Refresh** to read job state, output, clock, owner and engine. A connection
failure makes observations stale or unknown. Complete jobs execute locally;
closing a browser or unplugging a controller does not prove output inactive.

For a job owned by this browser, choose **Abort my job**, refresh and confirm
output inactive before **Release control**. A foreign owner must stop through
its controller. Disable standalone schedules separately to prevent later jobs.
The configured external button can request shutdown when browser control is
unavailable; see [button gestures](connect.md#request-setup-wi-fi-with-the-external-button).

After an abort, fault or restart, read current state before trying again.
Resolve the reported cause, review configuration and ownership, and submit a
new job deliberately. Neither reconnect nor refresh re-arms the old job.

A shutdown/STOP suspension survives configuration saves. To resume standalone
operation, first review the saved schedule and frequency, confirm output is
inactive and the Pico is idle, then explicitly **Restart device** in
**Wi-Fi/Host**. Restart clears STOP; an enabled saved schedule can then run at
the next eligible slot after time and other readiness checks pass. Leave it
disabled before restart if automatic output is not intended.
