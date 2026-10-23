# Configure your station

Station details are needed to configure transmissions. You can connect the Pico to Wi-Fi and sign in to its control page before entering them.

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

```{image} _static/images/station-draft.jpg
:alt: Station identity editor showing an encodable saved draft, separate Save valid station fields and Apply saved station actions, and the standalone frequency section.
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

### LED and button settings

Open **Station/Transmission → Schedules and radio pins → Pin assignments** to inspect or change the transmit indicator and external button. The [hardware preparation guide](start.md#hardware-connections) lists the defaults, available GPIOs and example wiring. GPIO menus use **GP numbers**, not physical header pin numbers. Each GPIO can serve only one role; pins assigned to another role are unavailable.

1. Under **TX indicator**, keep **Onboard LED** for the built-in indicator, choose **External GPIO** for an external LED, or choose **Disabled**. For an external LED, select its **External indicator pin** and **Indicator polarity**. Available external pins are **GP0–GP22** and **GP26–GP28**, excluding pins already in use. The default indicator is **Onboard LED**; external polarity defaults to **Active-high**.
2. Under **Switch input**, read the saved button pin. The factory default is **GP14**, physical pin **19**. Choose an unused GPIO from the same ranges or **Disabled**. Wire a normally open push button between the selected GPIO and GND; the input uses an internal pull-up.
3. Save with **Save valid fields** or **Save schedules and pins**, read the result, and choose **Apply saved settings** when offered. Use **Wi-Fi/Host → Restart device** to activate changed pin settings. Read the saved and active assignments again after restart and confirm that they match the wiring before transmitting.

## Understand what was saved

| Observation | Meaning |
| --- | --- |
| Saved progress or draft | Valid fields are retained; they are not necessarily applied |
| Complete configuration | Required values form an accepted configuration |
| Active hardware | Pins/drive selected at boot; may differ from saved settings |
| Ready to transmit | Clock, owner, frequency, hardware and output guards also allow a job |

### Keep incomplete progress

On firmware offering **Save valid station fields**, a callsign, locator or
reported power can be saved independently. An invalid edited field stays in
the browser as **Not saved** while other valid fields can be retained. Fields
you do not edit keep their saved values. Clearing a callsign or locator and
saving clears that draft field; it does not substitute the previous applied
value. **0 dBm** is valid reported power; a blank choice is missing power.

Schedules save as one complete set, and radio pins as one complete allocation.
An invalid schedule set or conflicting pin plan remains unsaved as a unit while
unrelated valid edits can be retained. Consumer Wi-Fi and hostname changes use
their own complete save workflows in [Wi-Fi/Host](maintain.md#rename-or-change-wi-fi).

After Wi-Fi setup, **Set your station details** can also retain incomplete
progress with **Save valid fields**. Complete and save the missing values,
then choose **Apply saved station settings** and check the setup result.
Saved progress survives a page reload, a new login and a restart. Unsaved
browser text does not; copy it before leaving a tab.

### Apply device-saved values

**Apply saved station** uses the values in the Pico's saved station summary,
even if newer unsaved text is visible in the editor. Complete the saved station
and review its WSPR plan first. An incomplete or unencodable station cannot
be applied for local WSPR. A valid radio-settings draft can still apply using
the previously complete station. QRSS, FSKCW, DFCW and externally prepared jobs
have their own input and admission requirements.

A draft save does not arm a job. Explicitly saving/applying **Enable standalone
schedules** authorizes automatic transmissions at later eligible slots once
all readiness checks pass. A saved or complete configuration alone does not
establish RF readiness. Review [Operate](operate.md) before enabling it.

An already enabled schedule continues with its applied settings while you save
progress. Saving an unchecked enable box alone does not disable that schedule;
apply the change and confirm readback. Saving progress also leaves STOP and
fault state intact. Completing a draft, logging in, refreshing or restarting
never applies that draft automatically.

### Recover an uncertain save

If a save reply is lost, keep the tab open, sign in again if needed and use
**Read saved settings and keep draft**. Compare the readback, then choose
**I reviewed saved settings; enable a new save** only after review. During
setup, draft recovery uses **Read saved progress; keep edits** followed by
**I reviewed saved progress; enable a new save**. Use **Check saved result**
and its continuation for an uncertain setup application.

The change may already be stored. Matching values do not identify which
interrupted request committed. Follow the reported continuation without
automatically repeating Save or Apply. **Reload saved settings** discards
unsaved edits and adopts device-saved progress. Provisioning and full resets
remove saved progress; read the [reset consequences](maintain.md#recovery-and-reset)
before using them.
