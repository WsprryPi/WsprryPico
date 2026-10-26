# Operate

## Before transmitting

Open the Pico's [control page](connect.md#open-the-control-page), sign in and choose **Station/Transmission**. In **Transmitter status**, choose **Refresh**. Check the device identity, saved station and frequency, active pins, RF load/filter and clock. Resolve any restart or output-inhibit message before starting. **Output inhibit** means the Pico is blocking another transmission until the reported condition is resolved.

A **job** is one complete transmission, including its repeats and gaps. Its **owner** is the controller that reserved the Pico for that job: this browser, WsprryPi or the Pico's own scheduler. Signing in gives access to the page; submitting a job requests control of the transmitter. The browser handles that request automatically when you choose **Load and arm message** or **Load and arm job**. Another controller's job cannot be taken over by opening a new tab.

The **Owner** field identifies current control: **Pico schedule** for the Pico's local scheduler, **This browser** for this tab, and **Available** when no controller holds it. Other controllers may appear as session identifiers.

## Read the status console

The prominent state and explanation describe the accepted job. **Future transmissions** describes saved schedules separately: enabled, paused, expired, waiting for time, or awaiting recovery. A pause can let the current job finish; when it is awaiting a durable save, keep the Pico powered until confirmation. A saved schedule does not by itself mean a job is active.

Accepted message jobs show their original message, frequencies, timing, copies and duration. QRSS uses **Carrier**; FSKCW uses **Space** and **Mark**; DFCW uses **Dot** and **Dash**, even when Dot is the higher frequency. WSPR shows accepted nominal RF values separately from the saved standalone USB dial and RF center. Externally supplied RF-event jobs may have no original message text. The page labels it unavailable instead of guessing.

**Job running** remains active during an RF-off keyed gap. Estimated progress can reach 100 percent while the Pico still reports running; only a confirmed terminal state establishes completion. **Manual RF correction** separates the selected value for the next preparation from the value frozen for an accepted job. Network time synchronizes UTC; it does not measure RF frequency error.

**Browser local time**, **Pico-reported UTC** and **Observation time (UTC)** are separate. Pico UTC is the value at observation, not a browser-clock fallback. Status refreshes every five seconds without replacing form entries or moving focus. A failed read or observation older than 15 seconds makes live state unavailable and disables controls. Signed-out status remains read-only; message, schedule and correction details require login.

Choose **Reset Pico** in Transmitter status or Wi-Fi/Host for a normal restart with saved settings retained. Read the confirmation: enabled schedules may resume after clock and readiness checks; consumed occurrences are not replayed. Reset is unavailable during loaded or active jobs, ownership, faults, pending pause saves and recovery barriers. It cannot clear a latched RF fault. The page sends one request, retains drafts and checks for up to 90 seconds. Sign in again to confirm the same Pico and a new boot. A timeout or lost reply remains unconfirmed; the page never retries the reset automatically.

## Your first WSPR transmission

Use this walkthrough after [installing firmware](install.md), [connecting the Pico to your home Wi-Fi](connect.md) and preparing the [RF connections and load](start.md#hardware-connections). Keep standalone schedules disabled until the final enable step. Use your own callsign, location, reported power and permitted band; the frequency below is an example.

1. Open the control page, sign in and select **Station/Transmission**. Choose **Reload saved settings** to begin with the Pico's saved values. This discards unsaved browser edits after confirmation; if you need to keep them, choose **Read saved settings and keep draft**, review the comparison, then **I reviewed saved settings; enable a new save** instead.
2. Under **Station identity**, enter your **Callsign**, **Grid locator** and **Reported WSPR power (dBm)**. Choose **Save valid station fields**, check that all three fields saved, then **Apply saved station**. A saved draft alone cannot transmit. If the Pico reconnects or restarts, follow the displayed continuation, sign in again and choose **Check saved result** until the station application is confirmed. Review the saved WSPR plan: an ordinary callsign normally uses one frame; some compound callsigns need two adjacent frames.
3. Under **Schedules and radio pins → Standalone WSPR frequency**, choose **Read saved frequency**, enter the whole-Hz **WSPR dial frequency**, then **Save frequency**. For example, `14095600` selects a center of `14097100 Hz`. Wait for the saved-frequency confirmation and use **Read saved frequency** to verify it. The first frequency save leaves schedules disabled. A confirmed save refreshes the settings needed by the schedule controls while keeping your other edits.
4. Leave **Enable standalone schedules** unchecked. Enter `240 / 0` on one line in **Schedule period / phase (seconds)** and leave **Schedule expiry (UTC)** blank. For a one-frame plan, this trial repeats every four minutes until disabled, leaving time to inspect completion and disable the schedule before another job is prepared. For a two-frame plan, use `600 / 0` instead to allow both frames to finish and leave time to disable. Keep the existing pin assignments if they match your wiring. Choose **Save valid fields**, check the field results, then **Apply saved settings**. If a restart is required, use **Wi-Fi/Host → Reset Pico**, reconnect and sign in before continuing.
5. In **Transmitter status**, choose **Refresh**. Check the clock, inactive output and available ownership, and resolve any STOP, storage or restart message. When ready for automatic transmission, check **Enable standalone schedules**, choose **Save valid fields**, then **Apply saved settings**. Choose **Refresh** and confirm that the standalone WSPR status says it is enabled. The checkbox is a browser edit until it has been saved and applied; there is no separate **Load and arm** action for scheduled WSPR.
6. Wait for the next eligible UTC window. With `240 / 0`, example starts are **12:00:01**, **12:04:01** and **12:08:01 UTC**. For `600 / 0`, example starts are **12:00:01** and **12:10:01 UTC**. Allow a full selected cycle, four or ten minutes, if the Pico was enabled too close to a boundary. **Job: empty** is normal before the Pico prepares its scheduled job; it does not mean scheduling is disabled. Status is an observation, so choose **Refresh** shortly before and during the expected window to see **armed**, then **running**, and later **complete**. One frame lasts about 111 seconds; a two-frame plan also uses the following window. A configured TX indicator stays lit during RF output; an external LED needs the correct GPIO and polarity under **Schedules and radio pins**. Check reception with your receiver if available; a reported running job alone does not establish received or decoded RF.
7. To finish the trial, wait for the complete transmission, uncheck **Enable standalone schedules**, choose **Save valid fields**, then **Apply saved settings**. Refresh and confirm standalone WSPR is disabled and RF output is inactive. Disabling prevents future starts; use the [stop controls](#status-stop-and-connection-loss) if you need to stop an already accepted job.

If Save or Apply is disabled, read the guidance beside the schedule buttons. When saved-state review is required, choose **Read saved settings and keep draft** in **Saved settings and recovery**, review the comparison, then **I reviewed saved settings; enable a new save**. Your checkbox and other browser edits stay in place. Reading only the frequency or refreshing transmitter status does not complete this review. A lost reply can mean the change was already saved; review readback before deliberately trying again.

If an entire expected window passes without a transmission, refresh and check the standalone WSPR status, clock, applied enable setting, saved frequency, expiry, ownership and restart/STOP messages. Correct the reported cause and wait for the next window; missed windows are skipped. See [Schedule does not transmit](troubleshoot.md#other-symptoms).

## WSPR schedules

For initial setup, follow [Your first WSPR transmission](#your-first-wspr-transmission). [Frequency and schedules](configure.md#frequency-and-schedules) describes the individual settings. Save and apply **Enable standalone schedules** to start automatic WSPR operation; no **Load and arm** action is needed for each scheduled transmission.

WSPR uses two-minute transmission windows, also called **slots**. The Pico starts one second after the selected window begins. It must be ready before that start, so enabling a schedule just before or after a boundary can leave it waiting for the next window. The clock must be usable, the frequency and station must be complete, the transmitter must be available and no STOP or restart requirement may be active.

Before preparing a scheduled job, the Pico saves a record that its slot has been used. A missed, interrupted or failed occurrence is skipped; restarting or reconnecting does not replay it. To prevent later starts, disable, save and apply the standalone schedule. Use the [stop controls](#status-stop-and-connection-loss) separately for an accepted or running job.

### Automatic WSPR plan

The Pico chooses a **WSPR plan** from the applied callsign and locator. A **frame** is one WSPR message sent in a two-minute window. Type 1 sends a basic callsign, four-character locator and reported power. Type 2 sends a callsign with a supported prefix or suffix and reported power. Type 3 sends a short callsign identifier, called a **hash**, with a six-character locator and reported power. WsprryPi plans the jobs it submits separately.

| Callsign and locator | Pico standalone plan |
| --- | --- |
| Basic callsign accepted by the form, four-character locator | Type 1 single |
| Basic callsign, six-character locator | Type 1 single; first four locator characters on air, all six retained |
| Supported compound call, four-character locator | Type 2 single; no locator in that frame |
| Supported compound call, six-character locator | Type 2 then Type 3 in adjacent two-minute windows |
| Explicit `<CALL>`, six-character locator | Type 3 single; brackets excluded from the hash |
| Explicit `<CALL>`, four-character locator, or unsupported syntax | Refused for complete station saves or local WSPR application |

A **compound callsign** has a prefix or suffix separated from the base call by `/`. Supported prefixes contain one to three letters or digits; suffixes contain one letter or digit, or two decimal digits. For example, `W1A/AA0NT` is a supported prefix form, while `<W1A/AA0NT>` explicitly requests Type 3 only. Use your actual callsign. The complete entry accepts 3–12 plain-text characters including brackets; malformed brackets, spaces, multiple slashes and unsupported prefixes or suffixes are refused. Follow the plan and any validation message shown by the Pico before applying the station.

Type 2 contains no locator. A Type 3 hash does not contain the full callsign, so a receiver may need the preceding Type 2 or another message to resolve it. A receiver without that context can show `<...>` with grid and power. Different callsigns can share a hash. Two-digit suffixes `/00`–`/09` share Type 2 encodings with `/Q`–`/Z`; a paired Type 3 uses the requested full callsign when calculating its hash.

Standalone WSPR uses the saved whole-Hz USB dial frequency. Its four tones lie at center −2.197265625, −0.732421875, +0.732421875 and +2.197265625 Hz, where center is dial +1500 Hz. For dial `14095600`, the tones are `14097097.802734375`, `14097099.267578125`, `14097100.732421875` and `14097102.197265625 Hz`. There is no random placement. Individual jobs and Pi Fleet WSPR RF-center entries retain their own frequency references.

A pair starts its second frame 120 seconds after the first. The Pico reserves both windows and keeps control between frames. Other scheduled occurrences that would overlap the pair are skipped. STOP, restart, changed settings, lost clock or control, or a failure can prevent the second frame; the Pico does not later resume the pair or automatically retry it. If output cannot be confirmed inactive, resolve that condition before another transmission.

## Send QRSS, FSKCW or DFCW

1. Under **Station/Transmission → Send a message**, select the mode and enter your **Message**. Letters, numbers, spaces and `/ ? . , - + =` are supported. Spaces count toward the **32-character** limit.
2. Enter the mode’s direct RF frequency in hertz: **Carrier frequency (Hz)** for QRSS, **Space frequency (Hz)** for FSKCW or **Dot frequency (Hz)** for DFCW. For FSKCW and DFCW, enter a positive **Frequency shift (Hz)**; mark is above space and dash is above dot by that amount. QRSS leaves shift unused and keeps its entry for another mode. Frequency and shift accept up to nine decimal places. Each requested frequency must fit the engine ranges and saved frequency permissions. These inputs do not use the standalone WSPR dial, add a WSPR offset or choose random placement.
3. Set **Dot length (seconds)**, **Repeat count** and **Gap between repeats (seconds)**. A repeat count of **1** sends the message once; **2** sends it twice in total. The repeat gap is in seconds and output is off between repeats, including in FSKCW.
4. Review **Transmission length** below the message, shown in minutes and seconds with repeats and gaps included. Review the named carrier or both frequencies and event count below the timing fields. An **event** is a timed part of the transmission, such as a mark or gap. The whole job must fit **512 events and 60 minutes**, including repeats and end-of-job timing. A 32-character message can still exceed those limits.
5. Use the UTC **Date** and **Time** controls or enter a future **Start time (UTC)** as `YYYY-MM-DD HH:MM:SS`, then choose **Load and arm message**. Opening either picker fills both parts when either is empty; subsequent date and time selections preserve the other valid part. See [time settings](reference/time.md). **Armed** means accepted and waiting to start. Check the reported result and **Transmitter status** before submitting anything again.

QRSS sends dots and dashes at the entered carrier, with RF off for gaps. FSKCW sends dots and dashes at mark and uses the entered space frequency during intra-element, character and word gaps. DFCW sends dots at the entered frequency and dashes at the higher frequency; both have the selected dot length and gaps have RF off. Gaps between repeated messages have RF off in every mode.

For an entered frequency of `14096900 Hz` and shift of `5 Hz`, QRSS uses carrier `14096900 Hz`; FSKCW uses space `14096900 Hz` and mark `14096905 Hz`; DFCW uses dot `14096900 Hz` and dash `14096905 Hz`. These are requested nominal frequencies; the backend’s realizable frequency and saved manual correction remain separate.

Switching modes keeps the raw frequency, shift, message and timing entries while immediately changing their labels and preview. Reviewing a preview or changing modes does not submit a job or save settings. Correct invalid entries beside the form before submitting. A rejected or unconfirmed request keeps your entries and reports its result beside **Load and arm message**; refresh status before deliberately trying again.

Under **Timing settings**, **Dash length**, **Within a character**, **Between characters** and **Between words** are multiples of the dot length. With a three-second dot and the default values, a QRSS or FSKCW dash lasts nine seconds, gaps within a character last three seconds, gaps between characters last nine seconds and gaps between words last 21 seconds. DFCW keeps dots and dashes equally long. The separate **Gap between repeats** field remains in seconds.

For a finite test tone from WsprryPi, choose **Mode → Finite tone** in a supported [Fleet output schedule](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/index.html#assign-an-output-schedule). Its continuous **Test Tone** control is unavailable for the Pico WTP backend. For an already prepared job, open **Load a job file**, select its **Job JSON file**, enter **Start time (UTC)** and choose **Load and arm job**. JSON is a structured text file; this route requires a complete `rf-events/1` job, at most 30,000 bytes, produced by compatible software. It does not accept an ordinary message text file. Use **Send a message** for the built-in Morse editor. All jobs use the same clock, frequency and control checks.

### Repeat a message on a schedule

Choose **Repeat on a schedule** in **Delivery** to save the complete message for automatic transmission with the browser closed. Set **Start time (UTC)** as the first start and **Repeat interval (minutes)** from 1 to 1440. The interval is measured from one planned start to the next, including across midnight; it is not a delay after completion. For example, a first start of 12:05 UTC and a 20-minute interval gives 12:05, 12:25 and 12:45 UTC. **Repeat count** still controls copies inside each complete transmission.

Leave **Schedule end (UTC, optional)** empty to continue without expiry, or enter an end that allows the complete final transmission to finish. The complete transmission plus preparation time must fit inside the interval. Disable and apply standalone WSPR schedules before enabling a message schedule. Each Pico stores one message schedule; saving it does not change the WSPR dial frequency, station or pin settings.

Choose **Save and start schedule** while the transmitter is available. Check **Saved message schedule** for confirmed saved settings, state and the next UTC start. **Read saved schedule** preserves the form; **Use saved message** deliberately fills it from readback. A past first start keeps its original timing grid and selects the next eligible occurrence. Missed, occupied and clock-unready starts are skipped, without catch-up transmissions. A usable clock and the existing output and ownership checks remain required.

Choose **Pause future transmissions** to prevent later starts while allowing an accepted current job to finish. Keep the Pico powered until the page confirms the pause was saved; a pending pause is not durable until the job finishes and flash can be written. Reset or loss of an accepted job's final outcome blocks recurrence as **Recovery required**. Once output is inactive and control is released, explicitly pause to acknowledge that outcome, then deliberately save an enabled schedule to resume. No accepted occurrence is replayed. Use the immediate stop controls separately if a transmission must be interrupted.

A failed or lost save reply can mean the profile was already saved. Read the saved schedule and review it before another explicit save. Your form entries remain available. Before firmware updates, pause message scheduling and resolve any pending or recovery state. Updating preserves a confirmed saved profile; older firmware does not understand the new stored profile and is not a preserving downgrade path.


## Status, stop and connection loss

Use **Transmitter status → Refresh** to read the Pico's current report:

| Field | Meaning |
| --- | --- |
| Job | `empty` means no job is loaded; `loaded` means stored but not yet armed; `armed` means waiting for its accepted start; `running` means executing the job |
| Standalone WSPR status | Reports whether the applied schedule is disabled, waiting for a window or blocked by an observed condition; refresh to update it. `Job: empty` can be normal between scheduled transmissions. |
| Job, after execution | `complete` means finished; `aborted` means stopped early; `missed` means the start was missed; `failed` needs the reported fault resolved and output checked before another job |
| RF output | **Active**, **Inactive** or **Unknown** is the Pico's reported output state; a browser error leaves it unknown |
| Clock | Time synchronization state and the estimated timing error shown after `±`; see [clock status](reference/time.md#read-the-clock-status) |
| Owner | **Available** means no controller holds the transmitter; **This browser** identifies this tab's control; another identifier belongs to another controller |
| Engine | The firmware's RF signal generator; it is separate from the Wi-Fi connection and clock state |

A successful login alone does not mean the Pico is ready to transmit. A connection failure makes observations stale or unknown. Complete jobs execute locally; closing a browser or unplugging a controller does not stop them.

For a job owned by this browser, choose **Abort my job**, refresh and confirm **RF output: Inactive**, then choose **Release control**. Release frees the transmitter for another job; it does not disable standalone scheduling. After a completed browser job, release control when you have finished using it. Another owner's job must normally be stopped through its controller. Disable and apply standalone schedules separately to prevent later jobs.

When browser control is unavailable, the configured [external button](connect.md#request-setup-wi-fi-with-the-external-button) or the physical [USB Console stop command](usb.md#stop-output-from-the-console) can request shutdown. Check the resulting output state before touching the RF path.

After an abort, fault or restart, read current state before trying again. Resolve the reported cause, review configuration and ownership, and submit a new job deliberately. Neither reconnect nor refresh re-arms the old job.

A shutdown/STOP suspension survives configuration saves. To resume standalone operation, first review the saved schedule and frequency, confirm output is inactive and the Pico is idle, then explicitly **Reset Pico** in **Wi-Fi/Host**. Restart clears STOP; an enabled saved schedule can then run at the next eligible slot after time and other readiness checks pass. Leave it disabled before restart if automatic output is not intended.

The signed-out operator page shows read-only transmitter state, RF output, clock, availability and engine, refreshed every five seconds. Unavailable readings show unknown. The Pico password field receives initial focus; signing in is required to change settings or submit a job.
