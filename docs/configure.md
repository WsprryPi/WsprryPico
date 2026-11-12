# Configure your station

You need station details to configure transmissions. You can connect the Pico to Wi-Fi and sign in to its control page before entering them.

Keep schedules disabled and output inactive while setting up. Use the hostname lock to sign in, choose **Station Control**, and open the required section using its heading. Saved values load automatically. If a save needs recovery, follow the **Review saved settings** link.

Reloading the page replaces unsaved browser entries with device-saved values. When a save needs reconciliation, **Review saved settings** preserves your entries and compares them with the Pico’s saved values. A **draft** is an edit or saved work in progress; **applied** settings are the accepted configuration used for operation. Pin changes also require a restart before they take effect.

A new installation prefills **N0CALL**, **ZZ99**, and **0 dBm**. Replace both placeholders with your station details before applying settings. Automatic WSPR schedules are disabled, with a ten-minute interval aligned to UTC :00, :10, :20, :30, :40, and :50. Settings-preserving upgrades retain existing selections, including an unset dial or an empty schedule list. A provisioning-only reset preserves operating settings.

(wspr-configuration)=
## WSPR configuration

The [factory defaults reference](reference/defaults.md#station-wspr-and-time) lists the initial station, dial, schedule, and time values, along with radio, connection, logging, and CW editor defaults.

(station-identity)=
### Station identity

1. Enter your **Callsign**, four- or six-character **Grid locator**, and **Reported WSPR power (dBm)**. The locator is the Maidenhead position code for your transmitting location, such as `EM18` or `EM18ab`; use your own location. Reported power is the value broadcast in the WSPR message. The unit **dBm** expresses power relative to one milliwatt; for example, 30 dBm means one watt. Enter an appropriate value for your actual RF setup; this field does not set or measure physical power.
2. Choose **Save valid station fields**, or **Save station identity** if the page uses that label. Read the result for each field. You can save valid entries even when another field still needs correction.
3. When offered, choose **Apply saved station** to use the saved complete station. Updating an already configured station keeps the web console and existing logins available and needs no restart. New transmissions use the applied details; accepted jobs retain their original settings. Initial station setup may still show connection-check or reconnect instructions.
4. Check the saved **WSPR plan**, which describes the message type and number of frames the Pico will send. A callsign with a prefix or suffix separated by `/` can require two adjacent frames with a six-character locator; see [WSPR operation](operate.md#wspr-schedules).

```{image} _static/images/station-settings.png
:alt: WSPR Configuration containing station identity, the saved message type, and the frequency controls.
```

(frequency-and-schedules)=
### Frequency and schedules

For a complete start-to-finish example, follow [Your first WSPR transmission](operate.md#your-first-wspr-transmission).

Complete station details, choose **Save valid station fields**, then explicitly choose **Apply saved station** and confirm its result before saving a dial. A complete saved station draft is still a draft; it does not enable **Save frequency**. The guidance beside the frequency controls identifies the missing step. You can enter a dial while station setup is incomplete; the page retains it when you save and apply the station. After the Pico confirms application, the frequency controls become ready without reloading the page.

In **Station Control → WSPR Configuration**, enter a **WSPR dial frequency (Hz)** appropriate for your band, RF setup, and operating privileges. **Hz** means hertz; **1 MHz = 1,000,000 Hz**. Enter a whole number without commas or a unit suffix. Keep the default frequency or, after editing it, choose **Save frequency** while idle. Use **Read saved frequency** to confirm the saved value.

New station settings default to a `14095600` Hz WSPR dial, with schedules disabled. Existing saved frequencies, including an unset frequency, are preserved on upgrade.

Standalone WSPR places four tones around a center 1,500 Hz above the dial, without random placement: enter `14095600` for a center of `14097100 Hz`. Both frames of a pair use one saved dial.

A first selection leaves schedules disabled; later saves apply to the next job and preserve STOP. Read and Discard do not save a new value.

An invalid or rejected save retains your entry for correction. Unsaved frequency text exists only in the current browser tab and is not a committed setting after a reload or reboot. If a reply is uncertain, read the saved frequency and review it before another explicit save; the page does not retry the write automatically. Individual message jobs have their own frequency field.

**Schedule interval / offset (seconds)** controls when automatic WSPR jobs start. The **interval** is the time between starts. The **offset** selects the start within that repeating interval, measured from UTC midnight. **UTC** is the worldwide time standard; these settings do not use your computer's local time zone. The Pico starts transmission one second after the selected two-minute window begins.

Choose one of these alternative examples, or enter your own `interval / offset` pair:

| Entry | Repetition | Example start times in UTC |
| --- | --- | --- |
| `120 / 0` | Every two minutes | 12:00:01, 12:02:01, 12:04:01 |
| `600 / 0` | Every ten minutes | 12:00:01, 12:10:01, 12:20:01 |
| `600 / 120` | Every ten minutes, offset by two minutes | 12:02:01, 12:12:01, 12:22:01 |

Enter one pair per line. Intervals must be multiples of 120 seconds from 120 through 86,400 that divide evenly into one day. Offsets must be multiples of 120, from zero up to less than the interval. Up to eight schedules are supported, and their start windows must not overlap. A [two-frame WSPR plan](operate.md#automatic-wspr-plan) also occupies the following two-minute window; the Pico skips competing occurrences.

**Schedule expiry (UTC)** is an optional end date and time. Leave it blank to keep the schedule available indefinitely. The Pico starts only transmissions that can finish before expiry.

To save and start automatic WSPR:

1. Leave **Enable standalone schedules** unchecked while entering and reviewing station details, frequency, and schedule times.
2. Choose **Save WSPR configuration**, read the result, and use **Apply WSPR configuration** when offered. Check that the saved values match your intended setup. Complete any requested restart before enabling output.
3. When you are ready to transmit, check **Enable standalone schedules**, save and apply again, then **Refresh** the transmitter status and confirm standalone WSPR is enabled. The Pico waits for the next eligible window and an acceptable clock; see [Operate](operate.md#wspr-schedules).

A confirmed frequency save or settings application refreshes the settings revision while preserving browser edits. If Save or Apply is disabled, read the guidance beside the schedule buttons. When a saved-state review is required, the **Review saved settings** panel appears. Read and compare the values, then choose **I reviewed these settings; enable saving**. Neither **Read saved frequency** nor **Refresh** in transmitter status completes that review.

To prevent later automatic starts, uncheck **Enable standalone schedules**, save and apply, then confirm it is disabled. This is separate from aborting a job that is already accepted or running.

(time-and-calibration)=
## Time and calibration

These settings apply to WSPR, Morse modes, and test tones. Open **Station Control → Time and calibration**. Saved values load automatically; a read button appears only if recovery needs a fresh observation.

See [output and reference options](reference/time.md#understand-the-output-and-reference-options) for how Direct GPIO, Si5351, GPS, PPS, and loopback work together. The [measured carrier-error examples](reference/time.md#measured-carrier-error-examples) compare manual-zero operation with GPS/PPS automatic correction.

(ntp-update-timeout)=
### NTP update timeout

The **NTP update timeout: Continue without a valid NTP update for (minutes).** control sets how long previously synchronized NTP time remains usable without a new valid update. The default is **60 minutes**. Enter **1–1440 whole minutes**, or **0** to keep using the last synchronized time indefinitely. This setting does not extend browser-time holdover. Zero removes the Pico's NTP source-age cutoff; uncertainty remains visible and time can drift. A valid initial time is still required after startup, and an external controller's stricter per-job timing limit still applies. Choose **Save timeout** while idle, then restart the Pico to activate the change. UTC uncertainty does not automatically pause first-party transmissions; an accepted transmission finishes.

**Carrier calibration** corrects RF frequency in every mode. Edit **Manual correction (ppm)** and choose **Save calibration**; the saved correction applies when the Pico prepares the next job. Network time disciplines UTC separately. See [Time and frequency correction](reference/time.md#manual-frequency-correction) for measuring the correction.

(automatic-beacon-schedule)=
### Automatic beacon schedule

In **Advanced Scheduling**, use **Automatic beacon schedule** to limit when the Pico starts scheduled WSPR and repeating keyed-message transmissions.

- **24 hours** (default): Allow scheduled starts at any time of day or night. This option adds no GPS requirement.
- **Daylight only (saved grid)** and **Night only (saved grid)** use the center of the applied [station grid locator](#station-identity). Choose one of these for a fixed station with or without GPS.
- **Daylight only (GPS)** and **Night only (GPS)** use the current GPS latitude and longitude. Choose one of these if the beacon moves and should follow its current position.

Use the daylight or night options to compare reception under different conditions or to limit an unattended beacon to the part of the day you want to monitor. The Pico follows seasonal changes in sunrise and sunset without a local time zone or daylight-saving setting. It skips occurrences outside the selected period and does not make them up later. This setting does not enable a schedule, change its interval, or stop a transmission that has already been accepted.

For a two-frame WSPR occurrence, both frame starts must fall inside the selected period. The Pico skips the whole occurrence if the second start would cross the solar boundary.

All daylight and night options need usable UTC, which can come from NTP or another supported time source. Daylight runs from calculated sunrise to sunset, and night runs from calculated sunset to sunrise. The saved grid options accept four or six characters. The Pico uses the full applied locator even when the WSPR message sends only four characters. Six characters narrow the estimated position. The result is approximate and does not account for the local terrain or horizon obstructions.

The GPS options also require GPS input to be enabled and a usable GPS fix. The Pico skips occurrences when the fix is absent, invalid, or too old. The schedule choice is independent of which grid the WSPR message sends.

The USB installer requires an image that supports the current GPS storage format whenever GPS settings or a beacon policy are saved. The WsprryPi firmware panel checks the selected image against its own settings contract before offering installation.

Choose **Save beacon schedule**, then restart explicitly to activate a changed policy. Save GPS input separately in **Radio pins** before choosing a GPS schedule. To disable GPS input while a GPS schedule is saved, first save a saved grid option or **24 hours**.

For repeating keyed messages, the schedule status identifies when the next occurrence falls outside the selected beacon window or when the policy is waiting for a current GPS fix.

(gray-line-scheduling)=
### Gray-line scheduling

In **Advanced Scheduling**, use **Gray-line scheduling** to give morning and evening their own operating periods and frequencies. Both periods are disabled by default.

Solar elevation describes how far the Sun's center is above or below the horizon. Negative values mean it is below the horizon; positive values mean it is above it. At 0°, its center is on the horizon.

**Lower elevation** and **Upper elevation** set the Sun positions that define each period. The lower number must be smaller than the upper number. The defaults are −6° and +6°, covering the time when the Sun is close to the horizon.

With those defaults:

- The **morning** period begins when the rising Sun reaches 6° below the horizon and ends when it reaches 6° above it.
- The **evening** period begins when the setting Sun drops below 6° above the horizon and ends when it drops below 6° below it.

Choose where the Pico gets the location used for these calculations: **Saved locator center** uses the center of your station's saved grid locator; **Fresh GPS position** uses a current GPS position. For GPS, enable GPS input and make sure a current position is available. The Pico does not switch to the other location source if your choice is unavailable. It also needs a usable UTC clock, but no Internet connection, local time zone, or daylight-saving adjustment.

For each period, you can enter a different **WSPR dial** frequency or **Mark** frequency for Morse messages. Enter frequencies in Hz as whole numbers, without decimal places. Leave a field blank to keep using the frequency already saved for that type of transmission. For FSKCW and DFCW, changing **Mark** moves both tones together: the distance between them and which tone is higher stay the same.

The Pico checks new frequencies before saving them. Your selected RF output, band, and frequency permissions still apply. Gray-line scheduling adds no band restrictions and does not establish that an RF setup is suitable for use. If a saved frequency later becomes unavailable under those checks, the Pico skips new transmissions that would use it.

Your existing WSPR schedule or repeating Morse-message settings still decide when transmissions are due. Gray-line scheduling chooses which period's settings to use at those times; it does not create extra transmissions or change how often they repeat.

Choose **Read saved gray-line settings**, edit the morning and evening periods, then choose **Save gray-line settings**. Saved changes apply to future scheduled transmissions without a restart. You still need to enable the WSPR schedule or repeating message separately.

Reading saved settings keeps your unsaved edits. Choose **Discard gray-line entries** to replace them with the values from the last read. If a save reply is lost or unclear, read the saved settings again before saving. If the entries were kept from another Pico or from before a restart, review them and choose **Use entries for this Pico** before reusing them.

When a transmission is due, an enabled morning or evening period takes priority over the usual day/night settings. Outside those periods, the usual day/night settings apply. If the clock or location needed to check the gray-line periods is unavailable, the Pico waits instead of starting a new scheduled transmission, even if the day/night settings would otherwise allow it. Turning off both gray-line periods removes this extra requirement; the usual day/night requirements still apply.

A transmission the Pico has already accepted finishes even if the period changes. Skipped transmissions are not sent later to catch up.

For a two-frame WSPR message, the Pico checks both planned start times before starting either frame. Both must use the same morning or evening period, or both must use the usual day/night settings. If the settings would change between the two starts, the Pico skips the whole message.

Near the poles, the Pico follows the Sun's calculated position even on days without sunrise or sunset. Status shows when the Sun stays within a period's elevation limits all day. Morning and evening still belong to separate halves of the local solar day, divided at solar noon and midnight. A two-frame WSPR message that crosses either dividing time is skipped.

These calculations do not account for weather, terrain, or obstructions. A gray-line period may offer useful propagation, but it does not guarantee reception or identify the best Sun angle.

These settings apply only to WSPR schedules and repeating Morse messages that the Pico runs itself. They do not control when an external WTP controller sends a job, and they do not add gray-line scheduling to WsprryPi's Fleet or other Pi-run schedules.

(pins-and-drive)=
## Pins and drive

Assign each GPIO one role. Check physical wiring before changing **Radio pins**. The optional amplifier-enable pin has a selected active polarity; it stays active for a complete job, including keyed gaps, with configurable lead before RF and tail after normal completion. Stop, abort, and faults bypass the tail.

**Amplifier enable** is disabled by default, with **Active-low** polarity preselected. When configured, it is a logic control signal for suitable amplifier control circuitry; it does not supply amplifier power or carry the RF signal. **Active-high** means the output is high (about 3.3 V) when active and low when inactive. **Active-low** reverses those levels. The same polarity terms apply to an external LED. Match the selection to the wiring. The [hardware preparation guide](start.md#hardware-connections) lists available GPIOs and factory assignments.

Direct RF drive offers **2, 4, 8, or 12 mA**, with **12 mA** as the default. This controls the GPIO's electrical drive strength; it does not specify RF power. Check physical output with suitable measurement equipment when changing the drive setting or RF setup.

Pin or drive changes require an **explicit restart** in **Station Control → Transmitter status** before transmitting. Saving does not program the running pad. Changing a value back does not clear the restart requirement. Read saved and active settings separately.

(rf-output-engine)=
### RF output engine

Select **Direct GPIO / PIO** for the Pico's RF GPIO, or **Si5351** for an external synthesizer. The same ordinary firmware supports both engines. Si5351 controls appear immediately after you select the engine. Other pin roles follow them. Choose **Save RF output settings**, then restart explicitly to apply changes.

(si5351-output-settings)=
### Si5351 output settings

Choose **Si5351** under **RF Output** to configure an external Si5351A 10-MSOP module at address **0x60**. Select the complete I²C SDA/SCL pair, the fitted **25 MHz** or **27 MHz** reference, its source, and the transmit clock. Passive crystals also require their specified **6, 8, or 10 pF** load. An external clock or TCXO uses the supported **XA** arrangement; selecting it does not select CLKIN. Output drive is **2, 4, 6, or 8 mA**, independent of reported WSPR power.

Hardware selection, the reference uncertainty allowance, and hardware qualification are operator responsibilities. A supported settings-profile match does not identify or certify the connected module; shared bench results describe their recorded test conditions.

Loopback is **None**, **CLK0**, **CLK1**, or **CLK2**, with a distinct transmit output and an eligible counter-input GPIO. None releases the input and disables dependent trusted use. **Measure only** reports the clock ratio and its uncertainty. **Trust local reference for Pico rate** requires an explicit reference-uncertainty allowance; a TCXO label is insufficient. It can reduce Pico timer drift after NTP or phone time has been accepted. For phone-set time, the allowance must be below **50,000 ppb (50 ppm)** to select it over the ordinary timer estimate. The original phone-sample age, uncertainty, and validity limits remain in force. It supplies no UTC epoch or automatic RF calibration. Manual correction is in **ppb**; a positive value lowers programmed RF for a fast reference. Direct GPIO correction is retained separately.

Choose **Save RF output settings** to save the complete engine allocation. Draft edits do not touch hardware. Restart explicitly to activate saved hardware changes. Selecting Direct GPIO restores its controls and retains inactive Si5351 settings. Each connected wire still needs a distinct GPIO, including external devices whose software is not enabled.

Ordinary firmware supports the tested **QRP Labs Rev. 6 module with its 25 MHz TCXO**, using **External clock / TCXO into XA**, **SDA GP4 / SCL GP5**, **CLK0**, and **8 mA**. Loopback may be **None** or **CLK2 → GP7**; leave the **Independent RF gate GPIO** at **None wired**. This profile uses the normal **138 MHz** Pico clock. Other configurations require an explicit engineering build. The same normal image also supports Direct GPIO; changing engines does not require a different firmware image. Runtime readback distinguishes verified register state from unknown; neither proves physical RF inactivity or absolute accuracy. A separately powered module may continue through Pico reset or a failed bus transaction. Engineering operation requires a verified conducted RF path, verified 100 kHz I²C operation, and appropriate electrical levels. Optional GPS/PPS input can supply time and calibrate the independent reference through CLK2; see [GPS and PPS](#gps-and-pps).

(gps-and-pps)=
External XA requires compatible module wiring, electrical levels, and grounding; it does not select CLKIN. An independent RF gate requires an inactive hardware bias. Si5351 output drive is electrical current, not measured RF power or reported WSPR dBm. Saving settings alone does not enable an output. A separately powered module can continue producing output while the Pico resets or after a failed bus transaction.

Positive manual correction lowers programmed RF for a fast reference. Loopback measures a clock ratio and does not establish UTC or absolute RF accuracy. Trusted reference use requires a known uncertainty and can reduce timer drift after an accepted UTC observation; it does not extend time validity. See [trusted local reference](reference/time.md#use-a-trusted-loopback-while-offline). Automatic Si5351 correction requires enabled GPS, validated UTC/PPS association, and a separate CLK2 loopback measurement.

### GPS and PPS

Open **Station Control → Radio pins → GPS and PPS**. GPS is optional and disabled by default. Select the receiver, then open **GPS wiring and timing** to match the separate serial RX and PPS input pins, baud rate, and pulse polarity to the physical wiring. The [validation platform](reference/pico-validation-platform.md#gpspps-configuration) records QLG3 on GP1 and GP3, with no receiver-configuration output. GP numbers are GPIO names, not physical header numbers. PPS uses an input-only hardware counter and requires an offered odd GPIO. Its complete PWM slice must be separate from the Si5351 loopback slice; the saved configuration checks aliases and pin numbers. Save the complete RF output settings while idle and unowned, then restart explicitly.

(gps-wiring-and-timing)=
#### GPS wiring and timing

The QLG3 connects receiver TX to Pico RX and has no receiver RX header; keep its optional configuration output at **None**. PPS is always an input to the Pico. The E108 profile permits a matching-UART configuration output only when a supported receiver's RX is connected.

PPS marks the second boundary; serial UTC supplies its label and need not arrive at that boundary. Configure a measured serial-delay range narrower than one second, with endpoints from 0 to 1,999 ms. A range crossing the next PPS edge still labels the original captured pulse. Ambiguous associations are refused.

The **RMC second offset** labels the selected captured pulse: **0** uses the sentence's timestamp, **−1** assigns one second earlier, and **+1** assigns one second later. A positive **PPS edge delay from UTC boundary (ns)** means the electrical edge arrives after the UTC boundary. Measure these relationships for the actual receiver and wiring. PPS alone supplies no date.

(validated-utc-pps-association)=
#### Validated UTC/PPS association

**Leave this Disabled unless you have independently validated the actual receiver and capture setup.** Enable it only when the pulse edge, RMC second offset, measured message-delay window, and conservative receiver/capture error allowances match that setup. This is your declaration that the association has been checked; enabling it does not run a validation procedure.

With the option disabled, GPS serial and position observations remain available, but GPS cannot supply qualified UTC or automatic PPS-derived RF correction. NTP or authenticated controller/browser time can still supply UTC under their own rules. To use GPS as the time source, validate the setup first, enable this option, save RF output settings, and restart. Keep automatic RF correction disabled until its separate oscillator and loopback requirements are also met.

Receiving serial data or finding satellites does not establish the UTC/PPS association. Enter conservative timing allowances for the receiver and cable, and a separate timestamp error allowance. The hardware counter measures IRQ delivery latency and removes it from the PPS timestamp. Status reports the latest and maximum IRQ latency, the timestamp error bound, and rejected captures. A counter wrap, an interrupt gap, or a changed clock configuration forces a fresh acquisition.

The location selection controls which grid locator standalone WSPR sends:

- **Use saved manual locator** sends the grid entered under [Station identity](#station-identity). Use it when operating at a known location, including without GPS.
- **Use current GPS location** derives the grid from the GPS fix. Use it when the station moves between locations. The Pico keeps the manual locator saved but withholds new GPS-located WSPR transmissions when the fix is absent, invalid, or too old.

A complete WSPR plan, including both frames of a pair, keeps its original locator. Choose the location for daylight or night calculations separately under [Automatic beacon schedule](#automatic-beacon-schedule).

**Automatic direct GPIO RF correction** requires qualified PPS and a verified shared oscillator. For the Si5351 engine, use its separate automatic-correction control and a configured CLK2 loopback. The GPS section reports Pico clock and Si5351 reference measurements separately. A positive error means a fast oscillator. With automatic correction enabled, the saved manual correction is a residual trim; it is applied once when the job is prepared. Missing, expired, or conflicting calibration prevents a new job from starting. An accepted job or WSPR pair keeps its correction.

Read serial, PPS, UTC pairing, position, satellite, and calibration status separately. GPS time retains its learned rate for at most one hour after observations stop, with growing uncertainty. NTP timeout zero does not extend this interval. This receive-only profile has no advance leap announcement: GPS time pauses for five seconds on either side of a UTC month boundary and reacquires afterward; jobs crossing that boundary are refused. Restart always needs fresh time and RF calibration observations. Independent measurements are still needed to establish UTC or carrier accuracy.

(amplifier-lead-and-tail)=
### Amplifier lead and tail

Open **Station Control → Radio pins → Amplifier control**. Saved values load automatically. Set **Amplifier enable**, **Pin polarity**, **Enable before RF (ms)**, and **Disable after RF (ms)**, then choose **Save amplifier config** while the Pico is idle and unowned. This saves amplifier pin, polarity, and timing edits while preserving other radio-pin drafts. Both values default to **200 ms** and accept **0–1000 whole milliseconds**. Restart the Pico to activate changes; saved and active values are shown separately. Changing timing requires a restart even if the amplifier pin is disabled.

Lead lets the amplifier settle before the scheduled RF start. Tail holds it enabled after normal RF completion. These intervals surround the transmission window and do not change the message duration or shift its scheduled RF start. Zero removes the corresponding interval; a disabled amplifier pin uses neither interval. A job submitted too late to provide its lead is refused. Stop and fault cleanup do not wait for tail. Settings readback shows the phase observed at the last read; it does not measure amplifier readiness or RF power.

(lpf-and-band-selector)=
### LPF and band selector

An optional **LPF / band selector** controls an external low-pass filter bank. Leave **Selection policy** at **Fixed / manual filtering** if you use a fixed filter or switch it yourself. **Require a declared filter for every job** refuses a transmission unless one selector covers every RF frequency in the whole job, including modulation and frequency correction. Empty required mappings refuse every job.

Open **Station Control → Radio pins → LPF / band selector** and choose **Read saved selectors**. Add a named selector, choose an unused **Pico GPIO** and its **Active-high** or **Active-low** polarity. Add named frequency ranges referring to that selector, with whole-Hz **From** and **Through** values. Several ranges may use the same selector. Different selectors cannot have overlapping ranges. Use the filter's usable RF coverage, allowing margin for all transmitted tones and correction; a WSPR dial is below the emitted tones.

Up to five selector outputs and ten ranges are supported. Names accept 1–16 letters, numbers, spaces, `/`, `_`, or `-`. **Release before selection (ms)** and **Settle after selection (ms)** each accept 0–250 whole milliseconds and default to 20 ms. Set them for the actual driver and filter bank. Read the saved pin owners before choosing a GP; each pin serves one role. Large settings may exceed available saved space; shorten names or remove unused ranges if the save reports that limit.

Choose **Save selectors** while idle and unowned, then explicitly **Reset Pico** and read again. Saving changes requires a restart even if you change a value back. Readback separates saved settings, active settings for this boot, and the selector observed at the last read. Reads and failed saves keep your entries; **Discard entries** restores the last-read values. After a lost reply, read saved selectors and review them before another deliberate save. A save never exercises the outputs or starts a transmission.

The selected filter settles before amplifier enable. It stays selected through message gaps and amplifier tail, then releases after amplifier disable. The Pico refuses a job submitted too late for filter and amplifier preparation. Stop and fault cleanup immediately attempt RF off, amplifier off, and selectors off.

Connect GPIO only to suitable **3.3 V logic drivers** with external bias that holds the bank inactive during reset or loss of Pico power. Never drive relay coils directly from GPIO. Declaring a range does not measure filter response, power handling, or RF emissions. Verify the actual RF path before operating.

(led-and-button-settings)=
### LED and button settings

Open **Station Control → Radio pins** to inspect or change the transmit indicator and external button. The [hardware preparation guide](start.md#hardware-connections) lists the defaults, available GPIOs, and example wiring. GPIO menus use **GP numbers**, not physical header pin numbers. Each GPIO can serve only one role; pins assigned to another role are unavailable.

1. Under **TX LED**, keep **Onboard LED** for the built-in indicator, choose **External GPIO** for an external LED, or choose **Disabled**. For an external LED, select its **External LED Pin** and **LED Polarity**. Available external pins are **GP0–GP22** and **GP26–GP28**, excluding pins already in use. The default indicator is **Onboard LED**; external polarity defaults to **Active-high**.
2. Under **Button**, read the saved button pin. The factory default is **GP14** (physical pin **19**). Choose an unused GPIO from the same ranges or **Disabled**. Wire a normally open push button between the selected GPIO and GND; the input uses an internal pull-up.
3. Choose **Save RF output settings** and read the result. Use **Station Control → Transmitter status → Reset Pico** to activate changed pin settings. After restart, read the saved and active assignments again and confirm that they match the wiring before transmitting.

(understand-what-was-saved)=
## Understand what was saved

| Observation | Meaning |
| --- | --- |
| Saved progress or draft | The Pico has stored valid entries, but some required values may still be missing, or the changes may not yet be applied |
| Complete configuration | Required values form an accepted set of settings |
| Active hardware | The pins and drive setting loaded when the Pico last started; saved changes may need a restart |
| Ready to transmit | Settings are usable, and the clock, output state, and control ownership also permit a transmission |

### Keep incomplete progress

On firmware offering **Save valid station fields**, you can save a callsign, locator, or reported power independently. An invalid edited field stays in the browser as **Not saved** while other valid fields can be retained. Fields you do not edit keep their saved values. Clearing a callsign or locator and saving clears that draft field; it does not substitute the previously applied value. **0 dBm** is valid reported power; a blank choice is missing power.

Schedules save as one complete set through **Save WSPR configuration**; **Apply WSPR configuration** applies only saved schedule enablement, periods, and expiry. **Save RF output settings** saves the complete radio pin, Si5351, and GPS/PPS allocation independently. Changed hardware requires an explicit restart to activate it. Neither action applies drafts from the other section. A pin save can succeed while a schedule draft is invalid. A saved WSPR dial is not required to save radio pins, Si5351, or GPS/PPS settings. Standalone suspension and saved schedule preferences remain unchanged; saving hardware does not resume operation or enable a schedule. Conflicting pin assignments remain unsaved. Consumer Wi-Fi and hostname changes use their own complete save workflows in [Wi-Fi/Host](maintain.md#rename-or-change-wi-fi).

After Wi-Fi setup, **Set your station details** can also retain incomplete progress with **Save valid fields**. Complete and save the missing values, then choose **Apply saved station settings** and check the setup result. Saved progress survives a page reload, a new login, and a restart. Unsaved browser text does not; copy it before leaving a tab.

### Apply device-saved values

**Apply saved station** uses the values in the Pico's saved station summary, even if newer unsaved text is visible in the editor. Complete the saved station and review its WSPR plan first. You cannot apply an incomplete or unencodable station for local WSPR. A valid radio-settings draft can still apply using the previously complete station. QRSS, FSKCW, DFCW, and externally prepared jobs have their own message, clock, and frequency checks.

A draft save does not arm a job. Explicitly saving/applying **Enable standalone schedules** authorizes automatic transmissions at later eligible slots once all readiness checks pass. A saved or complete configuration alone does not establish RF readiness. Review [Operate](operate.md) before enabling it.

An already enabled schedule continues with its applied settings while you save progress. Saving an unchecked enable box alone does not disable that schedule; apply the change and confirm readback. Saving progress also leaves STOP and fault state intact. Completing a draft, logging in, refreshing, or restarting never applies that draft automatically.

(recover-an-uncertain-save)=
### Recover an uncertain save

If a save reply is lost or settings change elsewhere, keep the tab open and unlock controls if needed. Follow the **Review saved settings** link; this recovery panel appears when review is needed. Compare the readback, then choose **I reviewed these settings; enable saving** only after review. During setup, choose **Read saved progress; keep edits**, then **I reviewed saved progress; enable a new save** to recover a draft. For an uncertain Wi-Fi or station setup application, **Check saved result** and any reconnection instructions appear beside that save. They remain available while the request needs confirmation.

The change may already be stored. Matching values do not identify which interrupted request committed. Follow the reported continuation without automatically repeating Save or Apply. Reloading the page discards unsaved edits and adopts device-saved progress. An uncertain save still requires readback and explicit review. A change made elsewhere after comparison requires another readback before you can confirm the review. Provisioning and full resets remove saved progress; read the [reset consequences](maintain.md#recovery-and-reset) before using them.
