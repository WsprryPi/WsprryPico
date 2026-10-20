# Operate

Before starting, check the full device identity, saved frequency and station,
active pins, output load/filter, time readiness and ownership. Resolve any
restart or output-inhibit message first.

## WSPR schedules

Enable the reviewed standalone schedule in **Station/Transmission**. Occurrences
use UTC period boundaries plus the selected phase and a one-second launch
offset. The Pico reserves each occurrence before transmitting. It does not
catch up missed windows or replay consumed slots after a restart or failure.

### Automatic WSPR plan

The Pico chooses its standalone plan from the applied callsign and locator.
WsprryPi's host planning preferences and prepared jobs remain separate.

| Callsign and locator | Pico standalone plan |
| --- | --- |
| Ordinary encodable call, four characters | Type 1 single |
| Ordinary call, six characters | Type 1 single; first four locator characters on air, all six retained |
| Supported compound call, four characters | Type 2 single; no locator in that frame |
| Supported compound call, six characters | Type 2 then Type 3 in adjacent two-minute windows |
| Explicit `<CALL>`, six characters | Type 3 single; brackets excluded from the hash |
| Explicit `<CALL>`, four characters, or unsupported syntax | Refused for complete station saves or local WSPR application |

Supported compound prefixes contain one to three alphanumeric characters before
an encodable base call; suffixes contain one alphanumeric or two decimal digits
after it. `W1A/AA0NT` is a supported prefix form even though `W1A` is itself
a valid base call. `<W1A/AA0NT>` requests Type 3 only. The complete station token
accepts 3–12 ASCII characters including brackets. Malformed brackets, whitespace,
multiple slashes and out-of-range affixes are refused without truncation.
Locators use A–R, two digits and, for six characters, an A–X subsquare.
Older firmware may accept only Type 1 station writes; use the installed
firmware's reported planning support.

Type 2 contains no locator. Type 3 carries a callsign hash, so receivers may
need the preceding Type 2 or other callsign context to display the full call.
A cold receiver can show `<...>` with grid and power. Two-digit suffixes
`/00`–`/09` share Type 2 encodings with `/Q`–`/Z`; a paired Type 3 hashes the
requested full callsign. Hash collisions are possible. The recorded successful
Type 2/3 pair is one board/image/payload at 3.570100 MHz, not a general guarantee for
every receiver or compound call.

A pair starts its second frame 120 seconds after the first. The Pico reserves
both slots before the first frame and holds one ownership lease across the
pair. Intersecting schedule occurrences are consumed conservatively. STOP,
restart, changed configuration, lost clock/ownership or failure cannot resume
a stray second frame or replay the first. There is no catch-up or automatic
retry. A failed output cutoff requires recovery and confirmed inactive output.

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

For a finite test tone from WsprryPi, choose **Mode → Finite tone** in a
supported [Fleet output schedule](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/index.html#assign-an-output-schedule).
Its continuous **Test Tone** control is unavailable for the Pico WTP backend.
Alternatively, prepare a complete encoded tone job. The Pico page has no
dedicated tone editor. Open **Load a job file**,
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
