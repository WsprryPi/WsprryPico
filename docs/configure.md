# Configure your station

Keep schedules disabled and output inactive while setting up. Sign in, choose
**Station/Transmission**, and read the saved settings before changing them.

## Station identity

1. Enter your **Callsign**, four- or six-character **Grid locator**, and
   **Reported WSPR power (dBm)**. Use your actual station details. The dBm
   field is encoded message content; it does not set physical power.
2. Choose **Save valid station fields** (or **Save station identity** on a
   complete-save firmware view). Read the per-field result. Valid draft
   fields can be retained even when another field is invalid.
3. When offered, choose **Apply saved station** to apply the saved complete
   station. Follow any trial/commit continuation shown for consumer setup.
4. Check the saved WSPR plan and readback. A compound call with a six-character
   locator can select two adjacent frames; see [WSPR operation](operate.md#wspr-schedules).

```{figure} _static/images/station-draft.jpg
:alt: Station identity editor showing an encodable saved draft, separate Save valid station fields and Apply saved station actions, and the standalone frequency section.
:width: 960px
:target: _static/images/station-draft.jpg

Current page with illustrative fixture data. An encodable saved draft is separate
from applied settings and transmit readiness. This is a software preview, not a
board acceptance result.
Select the image to open it at full size.
```

## Frequency and schedules

In **Standalone WSPR frequency**, enter a whole-Hz **Base frequency (Hz)**
appropriate for the band and your operating privileges. Save it while idle,
then confirm readback. Generic firmware selects no frequency. The saved value
is used by every standalone WSPR schedule, including both frames of a pair.
It does not change the frequency in an independently submitted message job.

In **Schedule period / phase (seconds)**, enter one pair per line, such as
`120 / 0` for every two minutes. Periods are even-minute
intervals from 120 through 86,400 seconds that divide a UTC day; phases are
even-minute offsets within the period. Up to eight nonoverlapping schedules
are supported. Use expiry to bound operation when appropriate. Review the
frequency, station and UTC status before deliberately enabling schedules.
Choose **Save valid fields** (or **Save schedules and pins** on a complete-save
view), read the outcome, then use **Apply saved settings** when offered.
Read back the applied enablement and schedule; a retained draft does not run.

## Pins and drive

Assign each GPIO one role. Check physical wiring before changing **Schedules
and radio pins**. The optional amplifier-enable pin has a selected active
polarity; it stays active for a complete job, including keyed gaps, and returns
inactive after stop, completion, abort or fault. Settling and lead/tail timing,
LPF switching and an external Si5351 output engine are unavailable.

Direct RF drive offers **2, 4, 8 or 12 mA**, with **4 mA** as the default.
This is a GPIO pad setting, not calibrated RF power. Different drive strengths
do not inherit all-band qualification.

Pin or drive changes require an **explicit restart** in **Wi-Fi/Host** before
transmitting. Saving does not program the running pad. Changing a value back
does not clear the restart requirement. Read saved and active settings separately.

## Understand what was saved

| Observation | Meaning |
| --- | --- |
| Saved progress or draft | Valid fields are retained; they are not necessarily applied |
| Complete configuration | Required values form an accepted configuration |
| Active hardware | Pins/drive selected at boot; may differ from saved settings |
| Ready to transmit | Clock, owner, frequency, hardware and output guards also allow a job |

A draft save does not arm a job. Explicitly saving/applying **Enable standalone
schedules** authorizes automatic transmissions at later eligible slots once
all readiness checks pass. A saved or complete configuration alone does not
establish RF readiness. Review [Operate](operate.md) before enabling it.

If a save reply is lost, use **Read saved settings and keep draft**, compare the
readback, then choose **I reviewed saved settings; enable a new save** only
after review. For commissioning, use **Check saved result** and its continuation.
Reconnect and sign in again if requested. Do not blindly repeat a save.
