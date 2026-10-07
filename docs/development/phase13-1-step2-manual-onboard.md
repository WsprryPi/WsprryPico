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
- The steady ON check remains pending. Lamp states are volatile test state;
  they do not rewrite retained configuration or establish RF acceptance.

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
in this bounded optical fixture after the repair and retests. Before live ON,
publish the reviewed source and rebuild/bind clean firmware. Target ON observation
and final ordinary inhibited restoration are still pending; neither is implied
by these software checks. The full step-2 wiring/recording and steps 3–6 remain
open. Private evidence and the current device state must be rechecked on every
continuation, even though the operator response has no deadline.
