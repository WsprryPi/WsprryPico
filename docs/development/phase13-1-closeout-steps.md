# LED closeout: fixed steps 1–6

Updated 2026-10-08. **CLOSED_SCOPED**: accepted timing/shutdown results, thirteen
preceding target GPIO/RF cases, software polarity coverage, confirmed GP15 lamp
wiring and the [passing external TX-only cue check](phase13-1-step4-review.md)
close the selected LED work. No operator action remains.

| Step | Work | Current status | Operator needed |
| --- | --- | --- | --- |
| 1 | Existing runner, finite cases, firmware/image checks and evidence collection. | Complete. Only restore/high images prepared for the final case; no new GP14 stimulus or harness. | No |
| 2 | Confirm board identity and external LED wiring. | Complete. B's GP15 HIGH sketch lit the LED; operator confirmed it. B restored, A unchanged. | No further interaction |
| 3 | Onboard warmup, five modes, completion, active abort, armed cancellation and inhibited behavior. | Complete. Reuse the passed target evidence; do not repeat the timing matrix. | No |
| 4 | Confirm AP/Identify stay on the onboard output and never activate the external TX LED. | Complete. Actual GP15 OFF for each non-RF cue; ON during RF while onboard GPIO changes independently. Complete SDR evidence reviewed. | No |
| 5 | LED shutdown and failure handling. | Satisfied within the selected LED scope by the passed STOP/abort/failure evidence. Do not develop another GP14 stimulus for this closeout. Physical GP14/button qualification remains separate and is not marked PASS. | No for LED closeout |
| 6 | Restore, review the final result, resolve actionable findings and publish closeout. | Complete within selected scope. B restored inhibited/settings preserved, A unchanged, review findings repaired and reassessed. Original STOP/partial ledgers retained. | No |

## Final check and accepted scope

The existing external-high case passed on B's GP15. Before/after RF, actual
external GPIO was OFF while each AP/Identify cue changed the onboard GPIO.
During RF, GP15 was ON in all 27 active observations while the onboard GPIO
changed independently. Managed SDR evidence passed and restoration was verified.
No optical recording or operator observation was required.

The initial attempt stopped on an insufficient onboard-activity observation.
After the checker repair and verified restoration, one separately reserved
corrective run passed. Both admissions remain charged: 34 seconds including
warmup, making the aggregate 18 admissions / 687.368002568 seconds across the
separate campaigns. No automatic RF retry or refund occurred.

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
