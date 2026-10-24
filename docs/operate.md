# Operate

## Before transmitting

Open the Pico's [control page](connect.md#open-the-control-page), sign in and choose **Station/Transmission**. In **Transmitter status**, choose **Refresh**. Check the device identity, saved station and frequency, active pins, RF load/filter and clock. Resolve any restart or output-inhibit message before starting. **Output inhibit** means the Pico is blocking another transmission until the reported condition is resolved.

A **job** is one complete transmission, including its repeats and gaps. Its **owner** is the controller that reserved the Pico for that job: this browser, WsprryPi or the Pico's own scheduler. Signing in gives access to the page; submitting a job requests control of the transmitter. The browser handles that request automatically when you choose **Load and arm message** or **Load and arm job**. Another controller's job cannot be taken over by opening a new tab.

## WSPR schedules

Follow [Frequency and schedules](configure.md#frequency-and-schedules) to enter a frequency and schedule, then save and apply **Enable standalone schedules**. This starts automatic WSPR operation; no **Load and arm** action is needed for each scheduled transmission.

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
4. Review the named carrier or both frequencies, calculated duration and event count below the fields. An **event** is a timed part of the transmission, such as a mark or gap. The whole job must fit **512 events and 60 minutes**, including repeats and end-of-job timing. A 32-character message can still exceed those limits.
5. Enter a future **Start time (UTC)** and choose **Load and arm message**. Enter UTC even if the date picker uses your computer's familiar date format; see [time settings](reference/time.md). **Armed** means accepted and waiting to start. Check the reported result and **Transmitter status** before submitting anything again.

QRSS sends dots and dashes at the entered carrier, with RF off for gaps. FSKCW sends dots and dashes at mark and uses the entered space frequency during intra-element, character and word gaps. DFCW sends dots at the entered frequency and dashes at the higher frequency; both have the selected dot length and gaps have RF off. Gaps between repeated messages have RF off in every mode.

For an entered frequency of `14096900 Hz` and shift of `5 Hz`, QRSS uses carrier `14096900 Hz`; FSKCW uses space `14096900 Hz` and mark `14096905 Hz`; DFCW uses dot `14096900 Hz` and dash `14096905 Hz`. These are requested nominal frequencies; the backend’s realizable frequency and saved manual correction remain separate.

Switching modes keeps the raw frequency, shift, message and timing entries while immediately changing their labels and preview. Reviewing a preview or changing modes does not submit a job or save settings. Correct invalid entries beside the form before submitting. A rejected or unconfirmed request keeps your entries and reports its result beside **Load and arm message**; refresh status before deliberately trying again.

Under **Timing settings**, **Dash length**, **Within a character**, **Between characters** and **Between words** are multiples of the dot length. With a three-second dot and the default values, a QRSS or FSKCW dash lasts nine seconds, gaps within a character last three seconds, gaps between characters last nine seconds and gaps between words last 21 seconds. DFCW keeps dots and dashes equally long. The separate **Gap between repeats** field remains in seconds.

For a finite test tone from WsprryPi, choose **Mode → Finite tone** in a supported [Fleet output schedule](https://wsprry-pi.readthedocs.io/en/devel/User_Interface/Setup/index.html#assign-an-output-schedule). Its continuous **Test Tone** control is unavailable for the Pico WTP backend. For an already prepared job, open **Load a job file**, select its **Job JSON file**, enter **Start time (UTC)** and choose **Load and arm job**. JSON is a structured text file; this route requires a complete `rf-events/1` job, at most 30,000 bytes, produced by compatible software. It does not accept an ordinary message text file. Use **Send a message** for the built-in Morse editor. All jobs use the same clock, frequency and control checks.

## Status, stop and connection loss

Use **Transmitter status → Refresh** to read the Pico's current report:

| Field | Meaning |
| --- | --- |
| Job | `empty` means no job is loaded; `loaded` means stored but not yet armed; `armed` means waiting for its accepted start; `running` means executing the job |
| Job, after execution | `complete` means finished; `aborted` means stopped early; `missed` means the start was missed; `failed` needs the reported fault resolved and output checked before another job |
| RF output | **Active**, **Inactive** or **Unknown** is the Pico's reported output state; a browser error leaves it unknown |
| Clock | Time synchronization state and the estimated timing error shown after `±`; see [clock status](reference/time.md#read-the-clock-status) |
| Owner | **Available** means no controller holds the transmitter; **This browser** identifies this tab's control; another identifier belongs to another controller |
| Engine | The firmware's RF signal generator; it is separate from the Wi-Fi connection and clock state |

A successful login alone does not mean the Pico is ready to transmit. A connection failure makes observations stale or unknown. Complete jobs execute locally; closing a browser or unplugging a controller does not stop them.

For a job owned by this browser, choose **Abort my job**, refresh and confirm **RF output: Inactive**, then choose **Release control**. Release frees the transmitter for another job; it does not disable standalone scheduling. After a completed browser job, release control when you have finished using it. Another owner's job must normally be stopped through its controller. Disable and apply standalone schedules separately to prevent later jobs.

When browser control is unavailable, the configured [external button](connect.md#request-setup-wi-fi-with-the-external-button) or the physical [USB Console stop command](usb.md#stop-output-from-the-console) can request shutdown. Check the resulting output state before touching the RF path.

After an abort, fault or restart, read current state before trying again. Resolve the reported cause, review configuration and ownership, and submit a new job deliberately. Neither reconnect nor refresh re-arms the old job.

A shutdown/STOP suspension survives configuration saves. To resume standalone operation, first review the saved schedule and frequency, confirm output is inactive and the Pico is idle, then explicitly **Restart device** in **Wi-Fi/Host**. Restart clears STOP; an enabled saved schedule can then run at the next eligible slot after time and other readiness checks pass. Leave it disabled before restart if automatic output is not intended.
