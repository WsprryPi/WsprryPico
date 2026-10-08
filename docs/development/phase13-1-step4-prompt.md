# P13.1 step 4: external transmit LED routing

Work on `devel`. Read README.md, CONTRACT.md, docs/architecture.md and AGENTS.md;
inspect and preserve the current work. Execute this prompt, repair actionable
adversarial findings, reassess, commit and push the reviewed result.

Close the one remaining selected LED check using the existing `external_high`
case. Board B has the operator-confirmed GP15 active-high LED. Both named Picos
are connected to the SDR and authorized for this task; use B and leave A
unchanged. External LED indication is exclusively for transmission. AP and
Identify must use the onboard LED. Existing timing, shutdown, failure and
software polarity evidence is accepted; do not repeat those campaigns.

Use the existing runner, managed SDR capture, retained recovery data and
installed build dependencies. No new harness, flash backup, camera, recording
setup, second LED, rewiring, GP14 stimulus or operator action is required.
Finite machine deadlines are allowed; no test may require a timed human reply.

Inspect the existing case before admission. Repair only demonstrated checker
gaps needed to establish this assertion. Require successful AP/Identify command
responses. Before RF, exercise each cue and sample actual external GPIO OFF and
actual onboard GPIO activity. During one finite 16-second TONE job, exercise
the cues, require actual GP15 ON while output is active and observe independent
onboard activity. After transmission, require inactive output, released owner,
cleared TX request and actual GP15 OFF while each cue remains onboard. Reject
unknown/error GPIO readback, refused commands, stuck onboard output, changed
device/boot/job identity, missing RF, active RF tail or uncertain cleanup.
Cached indicator state alone cannot establish physical pin state. Sampling
establishes functional routing, not calibrated optical edge timing.

Reproduce meaningful acceptance/rejection paths in the existing behavioral
tests, run affected checks and review the source adversarially. Repair findings
and rerun affected checks. Bind clean, reviewed firmware and runner identities;
prepare only the necessary ordinary inhibited restore and external-high images.
Verify serials, hashes, pins, clock, retained settings and receiver identity.
Keep captures, local paths and credentials in ignored/private evidence only.

Initially execute exactly `external_high` once. Reserve one admission / 17
seconds of RF including warmup; no automatic RF retry. If review demonstrates
a checker defect after definite terminal/verified inhibited restoration, the
user-requested repair iteration may use one separately recorded corrective
admission / 17 seconds. Preserve its predecessor as STOP, with no refund or
replay of an uncertain admission. Preserve preceding campaign ledgers
and their spent 16 admissions / 653.368002568 seconds. The separate current
reservation makes the aggregate 17 admissions / 670.368002568 seconds if charged;
one charged corrective admission makes 18 / 687.368002568 seconds.
Review the complete managed capture for actual RF and an inactive tail, with
exact count, receiver settings, artifact hashes and verified cleanup.

Restore B's ordinary inhibited firmware and original settings even on failure.
Verify final inactive, disabled, unowned/no-job state and GPIO OFF, and verify
A's identity, firmware, boot and settings unchanged. Perform an adversarial
evidence review; repair or explicitly retain an unresolved disposition without
replaying an uncertain RF admission. Reassess after each repair.

Record the actual result and exact evidence identities, update fixed steps
1–6 and linked current status documents, then commit and push on `devel` and
independently verify remote parity. Do not rewrite historical partial/failure
ledgers as PASS. Physical active-low wiring and GP14/mechanical qualification
remain outside the accepted LED scope. Report outcome, validation, restoration,
remaining scope and actual Git state concisely.
