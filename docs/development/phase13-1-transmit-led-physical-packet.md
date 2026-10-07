# P13.1 proposed physical acceptance packet

Prepared 2026-10-07. **NOT RUN.** Hardware authorization follows the user's
current setup statements under `AGENTS.md`: a named Pico connected to the SDR
authorizes RF tests and their necessary device-control/restoration steps.
No separate hardware/RF or per-job approval is required. The
[execution prompt](phase13-1-transmit-led-prompt.md) and
[software review](phase13-1-transmit-led-review.md) cover preparation only.
The [seven complete job bodies](phase13-1-transmit-led-cases.json) carry no
hardware authority. Historical Phase 11/12 budgets are not reused.

## Proposed bounded setup

Use Pico B, Pico 2 W / RP2350, USB serial `CDDBF8767C506C07`, device ID
`29f20b7342051ef947aa56cb9d4fab42`, on the previously recorded closed conducted
GP2 path into wspr5's RSP1B `2404058C60`. The receiver settings proposed from
the earlier setup are CF32, 250 ksample/s, 200 kHz bandwidth, center 3.550 MHz,
gain 20 dB, channel 0, AGC/bias tee off and the retained 60 dB Pico attenuation.
These are proposed identities/settings, not a current inventory. Before any
mutation, independently confirm the exact connected devices, RF path, input
levels, absence of an antenna and receiver configuration against the user's stated setup.

The proposed candidate is `WsprryPico-StandaloneRF`, 138 MHz/divider 1, direct
GP2, onboard indicator, consumer Plain LAN, no fault fixtures, and GP14 disabled.
Only USB WTP job control is proposed. Do not adopt credentials, enable schedules,
change security roots, fabricate clock authority or operate another Pico.
Use accepted SNTP through the ordinary station path; if it is unavailable,
stop before ARM and prepare an appropriate time-source action within the task
and the user's selected setup.

The inhibited restoration target is the matching standard `WsprryPico` image.
Both ELF/UF2 candidates are under ignored `build/phase13-1-pico/firmware/`.
The local `build/phase13-1-candidate-manifest.json` binds their hashes to the
source revision, SDK, picotool, toolchain and build options. Rebuild/re-hash
after committing; a dirty preparation image must not masquerade as a clean
commit image. Run `check_standalone_image.py` on both ELFs before loading.

## Untimed operator gates and finite accounting

The operator may respond whenever convenient. Once the user states that the
named Pico is connected to the SDR, proceed with the backup, two firmware loads
(RF candidate and inhibited restore), USB control and receiver capture. Use
the finite seven-job/240-second ceiling in this packet unless the user changes
the scope. Await recorder readiness only if operator action is needed to start
it; do not ask for RF authorization again. No countdown, short-lived Ready token
or timed button action is used.
The cases are autonomous; the operator need not watch their execution.

An optical recording of the onboard LED must cover activation and cutoff.
Synchronize it with independent RF detection/receiver evidence using a shared
recorded reference. A sufficiently sampled recording can establish only the
continuity and edge bounds supported by its resolution; do not claim calibrated
sub-frame timing. Review the recording later at leisure. If only live visual
plateau observation is selected, record that reduced scope and leave onset,
warmup-edge and cutoff continuity open. Receiver and software telemetry alone
cannot qualify a physical LED.

Keep RF off while awaiting any operator reply. Each job is finite in the
RP2350 plan, including the two 20-second abort cases. The full requested
duration sum is 222.592002892 seconds; the aggregate proposed RF ceiling is
240 seconds. Count every accepted ARM against the seven-job budget, including
the armed-abort case even if no RF occurs. There is no automatic retry. A failed
ARM/reply with ambiguous admission consumes a case; inspect and clean up,
never resend it as new work. A missed recording is incomplete, not a pass.

## Automated case sequence

1. Before flashing, collect exact identity/INFO/WTP STATUS, clock, ownership,
   scheduler and storage health. Refuse any active/owned/armed/failed state.
   Save and hash a private full-flash backup and separate settings readback;
   retain credentials only under ignored private `build/` storage. B's last
   recorded Phase 12 state was an RF image with a latched safety stop, so
   neither current inhibition nor an earlier restoration is assumed.
2. Load the exact manifest-bound RF candidate without erasing journals. Re-identify
   serial/device/source/image/boot and verify GP2/onboard/138 MHz, healthy
   retained settings, schedules disabled, empty/inactive authority, and usable
   SNTP. Await recorder readiness with output inactive. This preparation packet
   does not implement a live campaign runner; task/setup instructions supply
   execution authority.
3. Use the repository's `rf_wtp.WtpPeer` framing/request implementation and the
   prepared complete job bodies. Establish HELLO/CAPS and identity before
   CLAIM/LOAD. LOAD must not assert `tx_indicator_requested`. Schedule complete
   finite jobs locally using the current CAPS lead/window/clock bounds; loaded
   and future-armed intervals must retain the non-TX cue. Poll/renew leases
   autonomously through WSPR completion. Do not use legacy `rf_wtp.py` CLI's USB
   clock-setting workflow on this consumer image.
4. Execute `warmup_tone`, then `wspr`, then `qrss`, `fskcw`, `dfcw` as listed.
   The first is an RF-producing 15-second warmup tone. It is not a claim of
   continuous warmup into the following WSPR frame. QRSS/DFCW include keyed-low
   intervals; this PIO engine remains enabled while emitting zeros, so the LED
   stays solid until the physical engine stops. The full WSPR body has 162
   symbols. The keyed message is `ET` using the maintained message planner.
5. In `active_abort`, send the owner's WTP ABORT automatically 10 seconds after
   confirmed Running; the target plan stops after 20 seconds even if that
   command is lost. In `armed_abort`, ABORT before its future start, without
   asking the operator to react. Verify no launch and no TX request in the
   armed-abort recording. Both count against the budget.
6. Request Identify/AP overlap only through an already admitted current surface.
   Consumer USB can refuse legacy Identify; refusal is not a priority pass.
   If no admitted Identify/AP path exists in the retained profile, leave that
   physical row open without altering credentials or pin settings. Deterministic
   priority checks already cover the controller. Do not use the historical
   GP14 RF cue runner: its Identify-over-TX timing assumption was removed.
7. After each case, save RF/optical/Console INFO/WTP evidence, terminal state,
   exact timestamps, request/job/session identities and budget charge. Verify
   output inactive and request cleared before the next case. STOP on a write
   fault, missed launch, capture failure, unexpected output/owner, reset,
   transport ambiguity or settings drift. No further jobs follow a STOP.
8. In a cleanup path that also runs after failure, request ABORT when identity
   and ownership permit, confirm independent output inactivity, release the
   lease, and load the manifest-bound inhibited restoration image. Preserve journals
   and compare settings/security/profile/watermark readbacks with backup.
   Verify inhibited engine, inactive output, disabled schedules, no owner/job,
   final firmware/boot identity and receiver/host restoration. If device control
   is unavailable, do not assert cleanup success; retain evidence and await an
   untimed power-isolation action before further work.

## Physical exclusions and completion rule

This first packet covers the onboard indicator on one conducted band and USB
WTP. It does not qualify external LED wiring/polarities, other GPIOs, calibrated
edge timing, spectra, broad mode/band/clock combinations, other transports or
fleet operation. Standalone scheduler STOP, GP14 cutoff and real hardware
fault injection are not exercised by this packet; deterministic checks cover
their shared engine-stop behavior. External configuration changes, GP14 stimuli
or injected failures need a prepared finite packet matching the user's selected
setup and task scope, without a redundant authorization prompt.

Record each requested physical assertion as PASS, FAIL, INCOMPLETE or EXCLUDED,
with the exact evidence scope. Physical P13.1 remains open until the operator
accepts the completed selected matrix or explicitly disposes the remaining
rows. Source/cross-link success alone does not close it.
