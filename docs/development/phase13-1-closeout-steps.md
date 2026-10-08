# LED closeout: fixed steps 1–6

Updated 2026-10-08 after the operator rejected redundant LED testing and further
stimulus development. Reuse the accepted timing/shutdown results, thirteen
passed target GPIO/RF cases, software polarity tests and confirmed GP15 lamp
wiring. One focused external TX-only cue check remains; no new harness is needed.

| Step | Work | Current status | Operator needed |
| --- | --- | --- | --- |
| 1 | Existing runner, finite cases, firmware/image checks and evidence collection. | Complete. Prepare only the image needed for the existing external-high case; no new GP14 stimulus or harness. | No |
| 2 | Confirm board identity and external LED wiring. | Complete. B's GP15 HIGH sketch lit the LED; operator confirmed it. B restored, A unchanged. | No further interaction |
| 3 | Onboard warmup, five modes, completion, active abort, armed cancellation and inhibited behavior. | Complete. Reuse the passed target evidence; do not repeat the timing matrix. | No |
| 4 | Confirm AP/Identify stay on the onboard output and never activate the external TX LED. | One existing `external_high` case, using the verified GP15 circuit and actual GPIO readback. This includes a short RF interval; it is not another timing campaign. | No |
| 5 | LED shutdown and failure handling. | Satisfied within the selected LED scope by the passed STOP/abort/failure evidence. Do not develop another GP14 stimulus for this closeout. Physical GP14/button qualification remains separate and is not marked PASS. | No for LED closeout |
| 6 | Restore, review the one remaining result, resolve actionable findings and publish closeout. | Pending the step-4 check. Reuse existing evidence and retain all original failed/partial ledgers. | No |

## The one remaining check

Use the existing external-high case on B's GP15. Before/after RF, observe the
external pin OFF while AP/Identify activity is confined to the onboard output.
During the short RF interval, observe the selected external pin ON while those
cues remain onboard. Use real GPIO readback; cached controller state alone is
not enough. Existing managed SDR collection and finite cleanup may be reused.
No optical recording or operator observation is required.

The selected case reserves one admission / 17 seconds including warmup, with
no automatic RF retry. Preserve prior spent accounting. Restoring firmware and
original settings, reviewing the result and recording the final scope complete
this LED closeout. This TODO edit does not execute or claim PASS for that case.

No second LED, reversal/rewiring, bias-resistor fixture, camera, recording setup,
button press, A-to-B stimulus wire or active-low target repeat is required here.
Software tests retain polarity coverage; a physically wired active-low lamp is
not newly qualified. Mechanical button/header checks and broader hardware/
release qualification remain outside this selected scope. The earlier proposal
for local GP14 stimulus was not implemented and is withdrawn from LED work.

## Existing evidence

The [original target record](phase13-1-gpio-validation-review.md) retains prior
passes and failures. The [standalone STOP closeout](phase13-1-standalone-stop-closeout-review.md)
repairs both checker findings and records a complete passing repeat. The
[operator setup record](phase13-1-step2-operator-setup.md) records the confirmed
GP15 lamp and verified inhibited restoration, with zero RF jobs for that wiring
check. Retain those results instead of repeating them.
