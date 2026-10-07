# Step 2: untimed onboard optical checks

## Executable prompt

Work on `devel`, preserve existing changes and follow the fixed steps 1–6.
The operator has no external LEDs yet and selected direct visual verification:
set each state and wait for their response with no expiration or countdown.
The named Picos are already authorized for necessary device control. Start with
the idle OFF baseline, record the actual operator response, then prepare a
steady RF-free ON state on one named board. Do not keep RF running while waiting.

Use the real onboard driver and indicator controller in an isolated inhibited
test image. Ordinary and RF images must not admit the untimed lamp commands.
Require exact device identity, healthy state, no ownership/output, idle scheduler,
disabled schedules and onboard selection. Preserve settings, retain a verified
full-flash backup and bind the image to a reviewed clean source commit. Refuse
other fixture actions while holding a lamp state. Check hardware write failures;
a rejected ON must attempt OFF. Hold ON/OFF until an explicit change or restart,
not until a timer expires. Restore ordinary inhibited firmware after observations.

Test long waits, ON/OFF despite AP/Identify cues, release back to normal cues,
fault handling and command isolation. Perform an adversarial review, close
actionable findings, retest and assess again. Commit and publish the reviewed
source before deploying the clean candidate. Retain private target evidence.
Stop after setting the next verified state and ask for the operator observation.
Do not claim the visual plateau establishes RF onset, warmup, shutdown edges,
all-mode continuity, external polarity or TX-only behavior. Leave those rows open.

## Observation record

- The installed-firmware idle baseline was checked on both identities, with
  schedules disabled, no owner/job and inactive output. The operator replied
  **“Both off”**. This accepts the visual OFF baseline only.
- On the clean inhibited test image, the operator replied **“B is on, A is off”**.
  This accepts B's visible steady ON plateau and A's continued OFF observation.
- After `LAMP OFF`, the operator replied **“Both are off”**. This accepts B's
  visible return to OFF. All three confirmations were untimed.

Result: **PASS_ONBOARD_RF_FREE_VISUAL_SUBSET**. This closes these visual plateaus
only. B was then restored to ordinary inhibited firmware; the full step-2
fixtures/recording setup and RF steps 3–6 remain open.

The lamp control is only compiled into the RF-inhibited acceptance image:
`LED TEST <exact-device-id> LAMP ON`, `LAMP OFF` and `LAMP RELEASE`. INFO reports
`led_lamp_supported=true` and state 0 (normal), 1 (OFF), or 2 (ON), alongside
the checked driver state. All RF jobs remain subject to finite budgets.

## Execution and adversarial reassessment

The initial assessment found that the lamp admission also needed explicit
health checks for standalone, profile and access storage. These checks were
added before deployment. Review also required failed OFF to remain a failure,
even if a later retry succeeds: the controller's fault stays latched and no
uncertain optical state is reported as verified. Behavioral tests cover failed
ON's actual OFF attempt and failed OFF's uncertainty/recovery.

The affected host group passed 4/4 (acceptance, real indicator driver, field
access and the 30-test closeout runner/setup suite). The changed acceptance test
also passed ASan/UBSan. It exercises the actual indicator controller through
ten-/twenty-day simulated waits, repeating ON without pulsing, OFF priority over
AP/Identify, normal-cue restoration, fixture exclusion and write failures.
All eight worktree firmware candidates passed linked-image checks, including
the ordinary Pico platform link check. Binary inspection found the lamp command
and support field only in the inhibited acceptance image; they were absent from
ordinary and all RF images. Worktree candidates are not deployable clean images.

The second adversarial assessment checked command identity/selection/ownership,
compile-time RF isolation, configuration preservation, long operator absence,
AP/Identify overlap, timeout independence, hardware write failures, failure
latching and overclaiming visual evidence. No actionable source finding remains
in this bounded optical fixture after the repair and retests. The source was
committed and published as `882964a81489b0c8f93364e711d5c23932d67a4d`; all eight
clean candidates were rebuilt, checked for lamp isolation and validated against
that clean HEAD before deployment. Private evidence and current device state
must be rechecked on every continuation, even though operator replies have no
deadline.

## Target execution, repaired finding and final state

Control host: `wspr5`; mode: RF-free lamp diagnostic. B's initial idle baseline
used revision `58afb2735c23` / PIO-DMA GP2 at 138 MHz with output inactive. The
lamp test and final ordinary inhibited image use source `882964a81489` at an
actual system clock of **150 MHz**. A stayed on `6c7b14321003` at 150 MHz.
Both are Pico 2 W / RP2350; the named conducted SDR setup stayed in place.
No RF job was admitted: **0 jobs, 0 charged RF time** throughout this subset.

The first target attempt returned STOP after B's ON write/check succeeded but
the helper reused A's old WTP connection after the flash/startup delay. A's
STATUS request received a connection reset. B was automatically returned to
verified ordinary inhibited firmware; the failed ledger remains retained.
The manual helper was repaired to close A's read-only connection immediately
after entry checks and establish a fresh identity-bound connection for the final
check. A separate optical attempt passed. Fresh connections independently
verified ON still held after helper disconnection before the operator confirmed
it. No ambiguous RF admission was retried.

The target checks also verified exact serial/device/source identity, double-read
full-flash backups, application payload and retained-journal readback, refusal
of a wrong device ID and AP fixture action while OFF was held, disabled schedules,
no owner/job and inactive output. After all observations, ordinary firmware
refused the test lamp command and retained checked OFF with no driver fault.

| Board | USB serial / device ID | Final firmware / engine | Final boot |
| --- | --- | --- | --- |
| A | `0BF4B4AEC9FFB344` / `fd6127d11d6aca42a9905fa3fb1bf1d5` | `6c7b14321003`, inhibited-standalone-simulator; unchanged | `e83cac69de154245a974a3efdf5fc8af` |
| B | `CDDBF8767C506C07` / `29f20b7342051ef947aa56cb9d4fab42` | `882964a81489`, ordinary inhibited-standalone-simulator; acceptance disabled | `31f4e361c3b67c7aa3941f407e73e0f7` |

Final Console/WTP checks found both idle, unowned, without a job, schedules
disabled and output inactive. B's driver reported known OFF with no fault.
All **53,248 reserved bytes** in the restoration readback matched the original
entry backup from before the whole session, including access, profile, BTstack,
standalone journals and the SDK boot reservation. A post-boot comparison also
matched access/provisioning generations and source, default-password state,
saved station, schedules, expiry/frequency/watermark/last-job configuration and
boot pins. All control connections were closed.

The final adversarial reassessment covered the actual failed attempt and repair,
fresh auxiliary connections after long operations, the three operator responses,
independent held-state reread, original retained-byte equality, post-boot settings
comparison, ordinary-command refusal and the RF/edge exclusions. No actionable
finding remains in this completed visual subset. External fixtures, camera and
electrical/optical RF timing are still prerequisites for the remaining work.

Private receipts are under ignored `build/phase13-led-step2/`, including
`manual-lamp-final-restore-882964a.json`, both settings/journal audits, operator
observations and the live assessment. Full-flash backups and detailed events
remain private on wspr5 under the diagnostic source's `build/`. The first STOP
is preserved separately. Firmware evidence is bound to source `882964a`; later
documentation commits do not change those tested images. Rebuild current-head
candidates before starting the full autonomous RF matrix.

## Continuation constraint

After this subset, the operator requested: **“Stop with the backups - they
waste time.”** Do not take new full-flash backups as routine test preparation.
The recovery images and retained snapshots already collected are available;
preserve current settings and perform the necessary identity/inactivity checks.
The existing runner's automatic snapshot path must be revised before using it
for further tests under this instruction. No further backup operation was
started after the request.
