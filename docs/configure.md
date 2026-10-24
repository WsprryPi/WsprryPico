# Configure your station

Station details are needed to configure transmissions. You can connect the Pico to Wi-Fi and sign in to its control page before entering them.

Keep schedules disabled and output inactive while setting up. Sign in, choose **Station/Transmission**, and read the saved settings before changing them.

The page has two useful read controls. **Reload saved settings** replaces the browser's entries with values stored on the Pico, discarding unsaved edits after confirmation. **Read saved settings and keep draft** keeps your entries and lets you compare them with the Pico's saved values. A **draft** is an edit or saved work in progress; **applied** settings are the accepted configuration used for operation. Pin changes also need a restart before they become active.

## Station identity

1. Enter your **Callsign**, four- or six-character **Grid locator**, and **Reported WSPR power (dBm)**. The locator is the Maidenhead position code for your transmitting location, such as `EM18` or `EM18ab`; use your own location. Reported power is the value broadcast in the WSPR message. The unit **dBm** expresses power relative to one milliwatt; for example, 30 dBm means one watt. Enter an appropriate value for your actual RF setup; this field does not set or measure physical power.
2. Choose **Save valid station fields**, or **Save station identity** if the page uses that label. Read the result for each field. Valid entries can be saved even when another field still needs correction.
3. When offered, choose **Apply saved station** to use the saved complete station. Follow any connection-check or reconnect instructions until the Pico confirms the result.
4. Check the saved **WSPR plan**, which describes the message type and number of frames the Pico will send. A callsign with a prefix or suffix separated by `/` can require two adjacent frames with a six-character locator; see [WSPR operation](operate.md#wspr-schedules).

```{image} _static/images/station-draft.jpg
:alt: Station identity editor showing an encodable saved draft, separate Save valid station fields and Apply saved station actions, and the standalone frequency section.
```

## Frequency and schedules

Complete station details, choose **Save valid station fields**, then explicitly choose **Apply saved station** and confirm its result before saving a dial. A complete saved station draft is still a draft; it does not enable **Save frequency**. The guidance beside the frequency controls identifies the missing step. You can enter a dial while station setup is incomplete; the page retains it when you save and apply the station. After application is confirmed, the frequency controls become ready without reloading the page.

In **Station/Transmission → Schedules and radio pins → Standalone WSPR frequency**, enter a **WSPR dial frequency (Hz)** appropriate for your band, RF setup and operating privileges. **Hz** means hertz; **1 MHz = 1,000,000 Hz**. Enter a whole number without commas or a unit suffix. Choose **Save frequency** while idle, then **Read saved frequency** to confirm it. A fresh installation has no selected WSPR dial frequency, so the field is blank. Standalone WSPR places four tones around a center 1,500 Hz above the dial, without random placement: enter `14095600` for a center of `14097100 Hz`. Both frames of a pair use one saved dial. A first selection leaves schedules disabled; later saves apply to the next job and preserve STOP. Read and Discard do not save a new value. An invalid or rejected save retains your entry for correction. Unsaved frequency text exists only in the current browser tab and is not a committed setting after a reload or reboot. If a reply is uncertain, read the saved frequency and review it before another explicit save; the page does not retry the write automatically. Individual message jobs have their own frequency field.

**Schedule period / phase (seconds)** controls when automatic WSPR jobs start. The **period** is the time between starts. The **phase** is an offset within that repeating period, measured from UTC midnight. **UTC** is the worldwide time standard; these settings do not use your computer's local time zone. The Pico starts transmission one second after the selected two-minute window begins.

Choose one of these alternative examples, or enter your own `period / phase` pair:

| Entry | Repetition | Example start times in UTC |
| --- | --- | --- |
| `120 / 0` | Every two minutes | 12:00:01, 12:02:01, 12:04:01 |
| `600 / 0` | Every ten minutes | 12:00:01, 12:10:01, 12:20:01 |
| `600 / 120` | Every ten minutes, offset by two minutes | 12:02:01, 12:12:01, 12:22:01 |

Enter one pair per line. Periods must be multiples of 120 seconds from 120 through 86,400 that divide evenly into one day. Phases must be multiples of 120, from zero up to less than the period. Up to eight schedules are supported, and their start windows must not overlap. A [two-frame WSPR plan](operate.md#automatic-wspr-plan) also occupies the following two-minute window; the Pico skips competing occurrences.

**Schedule expiry (UTC)** is an optional end date and time. Leave it blank to keep the schedule available indefinitely. The Pico starts only transmissions that can finish before expiry.

To save and start automatic WSPR:

1. Leave **Enable standalone schedules** unchecked while entering and reviewing station details, frequency and schedule times.
2. Choose **Save valid fields** or **Save schedules and pins**, read the result, and use **Apply saved settings** when offered. Check that the saved values match your intended setup. Complete any requested restart before enabling output.
3. When you are ready to transmit, check **Enable standalone schedules**, save and apply again, then **Refresh** the transmitter status. The Pico waits for the next eligible window and an acceptable clock; see [Operate](operate.md#wspr-schedules).

To prevent later automatic starts, uncheck **Enable standalone schedules**, save and apply, then confirm it is disabled. This is separate from aborting a job that is already accepted or running.

## Pins and drive

Assign each GPIO one role. Check physical wiring before changing **Schedules and radio pins**. The optional amplifier-enable pin has a selected active polarity; it stays active for a complete job, including keyed gaps, and returns inactive after stop, completion, abort or fault.

**Amplifier enable** is disabled by default. When configured, it is a logic control signal for suitable amplifier control circuitry; it does not supply amplifier power or carry the RF signal. **Active-high** means the output is high, about 3.3 V, when active and low when inactive. **Active-low** reverses those levels. The same polarity terms apply to an external LED. Match the selection to the wiring. The [hardware preparation guide](start.md#hardware-connections) lists available GPIOs and factory assignments.

Direct RF drive offers **2, 4, 8 or 12 mA**, with **4 mA** as the default. This controls the GPIO's electrical drive strength; it does not specify RF power. Check physical output with suitable measurement equipment when changing the drive setting or RF setup.

Pin or drive changes require an **explicit restart** in **Wi-Fi/Host** before transmitting. Saving does not program the running pad. Changing a value back does not clear the restart requirement. Read saved and active settings separately.

### LED and button settings

Open **Station/Transmission → Schedules and radio pins → Pin assignments** to inspect or change the transmit indicator and external button. The [hardware preparation guide](start.md#hardware-connections) lists the defaults, available GPIOs and example wiring. GPIO menus use **GP numbers**, not physical header pin numbers. Each GPIO can serve only one role; pins assigned to another role are unavailable.

1. Under **TX indicator**, keep **Onboard LED** for the built-in indicator, choose **External GPIO** for an external LED, or choose **Disabled**. For an external LED, select its **External indicator pin** and **Indicator polarity**. Available external pins are **GP0–GP22** and **GP26–GP28**, excluding pins already in use. The default indicator is **Onboard LED**; external polarity defaults to **Active-high**.
2. Under **Switch input**, read the saved button pin. The factory default is **GP14**, physical pin **19**. Choose an unused GPIO from the same ranges or **Disabled**. Wire a normally open push button between the selected GPIO and GND; the input uses an internal pull-up.
3. Save with **Save valid fields** or **Save schedules and pins**, read the result, and choose **Apply saved settings** when offered. Use **Wi-Fi/Host → Restart device** to activate changed pin settings. Read the saved and active assignments again after restart and confirm that they match the wiring before transmitting.

## Understand what was saved

| Observation | Meaning |
| --- | --- |
| Saved progress or draft | The Pico has stored valid entries, but some required values may still be missing or the changes may not yet be applied |
| Complete configuration | Required values form an accepted set of settings |
| Active hardware | The pins and drive setting loaded when the Pico last started; saved changes may need a restart |
| Ready to transmit | Settings are usable and the clock, output state and control ownership also permit a transmission |

### Keep incomplete progress

On firmware offering **Save valid station fields**, a callsign, locator or reported power can be saved independently. An invalid edited field stays in the browser as **Not saved** while other valid fields can be retained. Fields you do not edit keep their saved values. Clearing a callsign or locator and saving clears that draft field; it does not substitute the previous applied value. **0 dBm** is valid reported power; a blank choice is missing power.

Schedules save as one complete set, and radio pins as one complete allocation. An invalid schedule set or conflicting pin plan remains unsaved as a unit while unrelated valid edits can be retained. Consumer Wi-Fi and hostname changes use their own complete save workflows in [Wi-Fi/Host](maintain.md#rename-or-change-wi-fi).

After Wi-Fi setup, **Set your station details** can also retain incomplete progress with **Save valid fields**. Complete and save the missing values, then choose **Apply saved station settings** and check the setup result. Saved progress survives a page reload, a new login and a restart. Unsaved browser text does not; copy it before leaving a tab.

### Apply device-saved values

**Apply saved station** uses the values in the Pico's saved station summary, even if newer unsaved text is visible in the editor. Complete the saved station and review its WSPR plan first. An incomplete or unencodable station cannot be applied for local WSPR. A valid radio-settings draft can still apply using the previously complete station. QRSS, FSKCW, DFCW and externally prepared jobs have their own message, clock and frequency checks.

A draft save does not arm a job. Explicitly saving/applying **Enable standalone schedules** authorizes automatic transmissions at later eligible slots once all readiness checks pass. A saved or complete configuration alone does not establish RF readiness. Review [Operate](operate.md) before enabling it.

An already enabled schedule continues with its applied settings while you save progress. Saving an unchecked enable box alone does not disable that schedule; apply the change and confirm readback. Saving progress also leaves STOP and fault state intact. Completing a draft, logging in, refreshing or restarting never applies that draft automatically.

### Recover an uncertain save

If a save reply is lost, keep the tab open, sign in again if needed and use **Read saved settings and keep draft**. Compare the readback, then choose **I reviewed saved settings; enable a new save** only after review. During setup, draft recovery uses **Read saved progress; keep edits** followed by **I reviewed saved progress; enable a new save**. Use **Check saved result** and its continuation for an uncertain setup application.

The change may already be stored. Matching values do not identify which interrupted request committed. Follow the reported continuation without automatically repeating Save or Apply. **Reload saved settings** discards unsaved edits and adopts device-saved progress. Provisioning and full resets remove saved progress; read the [reset consequences](maintain.md#recovery-and-reset) before using them.
