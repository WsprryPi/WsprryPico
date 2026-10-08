# P13.1 standalone STOP closeout

This executes the [step-1/5 follow-up prompt](phase13-1-standalone-stop-closeout-prompt.md)
on `devel`. B is the DUT; A is unchanged. External LEDs and GP14 qualification
remain outside this follow-up. No camera, new backups or operator attention is
required.

## Source change and adversarial review

The existing runner now charges an autonomous occurrence with unknown job ID
before SCHEDULE, then binds and persists the real ID from matching device/boot
Running authority before STOP. It accepts only that job's `aborted` state with
inactive output, released ownership, disabled schedules and cleared TX request,
then checks actual GPIO OFF. Empty/complete or another job cannot pass.

The existing behavioral adapter now reproduces the target's retained aborted
job and a scheduler ID different from the template. It checks on-disk charge
before SCHEDULE and actual ID before STOP. Adverse checks cover wrong terminal
state, active output, retained owner, changed job, enabled schedules, retained
TX request, pin stuck ON and malformed/foreign admitted authority. All failures
retain the charge, stop and restore; there is no automatic admission retry.

Source adversarial assessment checked ambiguity before job binding, boot/device
identity, persistence order, STOP authority, failure restoration and candidate
source binding. Both demonstrated findings are repaired. No additional source
finding remains within this slice; target execution and final assessment follow.

## Execution reservation

This newly requested follow-up selects exactly `standalone_stop`, once, with
one admission / 111.591999892 seconds reserved including warmup. The prior
campaign's 15 / 541.776002676 remains spent, without refunds or ledger edits.
If this single attempt stops, it is not automatically repeated. A complete
260-second managed SDR capture includes the finite occurrence and inactive tail.

Target results, exact firmware/setup, validation and restoration will be
recorded after execution. This preparation record does not claim target PASS.
