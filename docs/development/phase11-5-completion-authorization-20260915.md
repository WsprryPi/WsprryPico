Complete WsprryPico Phase 11.5 using bounded, evidence-driven work packages.

Execute this task. Do not stop after planning or preparing a prompt. Perform
adversarial review, repair actionable findings, run affected checks, and reassess
until no actionable finding remains within the completed scope. Commit and push
the attributable changes, independently verify remote parity, and report the
actual acceptance state.

1. Objective and scope

Complete all six Phase 11.5 acceptance families for the selected Pico 2 W
configuration: RP2350 Arm, 138 MHz, divider 1, GP2 PIO/DMA, RAM renderer,
network listener enabled.

Phase 11.5 covers target resources, contention and timing. Phase 11.6 owns
conducted per-band/per-mode RF acceptance. Phase 13 owns broad band × mode ×
clock comparison, filters, spectra, supported release configurations and final
qualification. Do not expand this task into those phases.

Preserve the implemented limits:
- 32 characters, including spaces, for QRSS, FSKCW and DFCW.
- Complete finite jobs up to 3,600 seconds within advertised capabilities.
- 512-event RF profile.
- Existing WSPR framing, protocol compatibility and local RP2350 timing.

These are tests and repairs of the user's own firmware, boards and isolated
laboratory fixture. Use the existing authenticated control paths. Precisely
describe test mechanisms; do not conceal their purpose or attempt to bypass
tool approval controls.

2. Repository and starting state

Primary repository:
  /Users/lbussy/GitHub/WsprryPico

Expected branch:
  devel

Last verified clean HEAD:
  d1a5a2e6171c9b8d84531fda0500a2046590cb6c
  Close bounded Pico LOAD replay validation under TLS

The previous task verified push and remote parity. Refresh local and remote
state rather than assuming that nothing changed.

Related repository:
  /Users/lbussy/GitHub/WsprryPi

Use SSH host:
  wspr5

Read the applicable AGENTS.md instructions. Before implementation read:
- README.md
- CONTRACT.md
- docs/architecture.md
- docs/development/README.md

Inspect working trees before editing. Preserve user changes. Do not reset,
stash, delete unrelated work, rewrite history or force-push. Make companion
WsprryPi changes only when a demonstrated Phase 11.5 dependency requires them.
Do not replace the installed WsprryPi application as a routine fixture step.

Use the existing local SDK/toolchain and documented build/test commands.
The latest qualified candidate used SDK 2.3.1 and GCC 15.3.1. Do not install or
upgrade SDKs or toolchains incidentally.

3. Read these records first

All paths below are relative to the WsprryPico repository:

- docs/implementation-plan.md
- docs/development/phase11-5-plan.md
- docs/development/phase11-5-acceptance-ledger.md
- docs/development/phase11-5-r3-complete-authorization-prompt.md
- docs/development/phase11-5-r3-v2-progress.md
- docs/development/phase11-5-r3-v2-capacity-coordination.md
- docs/development/phase11-5-r3-v2-campaign.json
- docs/development/phase11-5-r3-v2-component9-prompt.md
- docs/development/phase11-5-r3-v2-component9-result.json
- docs/development/phase11-5-r3-v2-component9-review.md

Follow their references for the exact evidence needed by each assertion.
Do not read every historical packet before making progress.

Several top-level documents retain old candidate identities and historical
“current” paragraphs. Reconcile them against the latest immutable results and
source-impact reviews. Preserve historical records; update current summaries
without rewriting old outcomes.

4. Actual acceptance position

Phase 11.5 remains OPEN: two of six acceptance families closed.

- R1 resources/baseline: CLOSED, 5/5, with documented evidence applicability.
- R2 normal RF execution: CLOSED, 7/7 jobs, with documented applicability.
- R3 saturation/reclamation: OPEN.
- R4 authority/interruption: OPEN.
- R5 network/storage/autonomous lifecycle: OPEN.
- R6 sustained mixed operation: OPEN.

R3 execution grouping:
- Group 1 controller/lifecycle: CLOSED at checkpoint 043.
- Group 2 capacity/pressure: OPEN.
- Group 3 retention/reclamation: OPEN.
- Group 4 closeout: OPEN.

The execution grouping does not replace the normative assertion matrix.
Preserve all required R3 groups and extended-feature checks.

R4 overlaps some existing lifecycle evidence. Assess that evidence before
scheduling duplicate physical tests.

5. Preserve the latest closed regression

Component 9 CLOSED the bounded retained-state/TLS LOAD-reply regression on
clean firmware source:
  98f5797d77fb2bc4c11a4e80f6ff35d7ad16a5b5

The repository HEAD and deployed firmware source are intentionally different.
Do not identify the deployed firmware as d1a5a2e.

The primary 512-event LOAD, byte-identical replay and same-job fresh-ID replay
each returned all 512 exact adjustments with valid framing and identity.

Measured exchange durations, including request writes:
- Primary: 2.245072864 seconds.
- Identical replay: 2.260196109 seconds.
- Fresh-ID replay: 2.297352585 seconds.

Each request wrote 52,105 bytes; each response payload contained 54,916 bytes.
The 90-second TLS observation and four HTTPS status reads passed.
Peak allocator headroom was 36,960 bytes against the unchanged 32,768-byte
reserve. Allocation failures, faults and RF activity were zero.

This closes that bounded idle LOAD/replay regression. It does not establish
maximum simultaneous workload, RF coexistence or complete Group 2 acceptance.

Do not repeat this completed regression without a source-impact reason or a
new failure. Preserve previous failed attempts.

Relevant repairs include paged input handling, shared immutable LOAD adjustment
storage, and removing the temporary 512-element JSON-view vector during decoding.
Read the actual diffs and tests before assessing their impact.

6. Last recorded hardware, signal path and restoration state

Both Picos are fully capable validation targets. Either may perform firmware,
configuration, transport, lifecycle, scheduling and finite RF tests within
Section 7. Neither device is restricted to read-only or zero-RF work.

Pico A:
- USB serial: 0BF4B4AEC9FFB344
- Device ID: fd6127d11d6aca42a9905fa3fb1bf1d5
- Last recorded firmware source:
  98f5797d77fb2bc4c11a4e80f6ff35d7ad16a5b5
- Last recorded boot: b1c0af7bef6ef0bef8f5e44130182149
- ELF SHA-256:
  ff594d831ef3e98d0ac3e062260d7c2ed8c9b81ab206eff7c941230b96b85f71
- UF2 SHA-256:
  b6d5ab7610a0e19e9de91ce78dde4eb7c63b9192343dd86af4f7bcb857838733

Pico B:
- USB serial: CDDBF8767C506C07
- Device ID: 29f20b7342051ef947aa56cb9d4fab42
- Last recorded firmware source: 8921a7008183
- Last recorded boot: 6684b4b197d80cfa0ce83b3aaf205cb0

At the last independently verified restoration:
- Both boards were Empty, inactive and unowned.
- Autonomous scheduling was disabled.
- Configuration was unchanged.
- A retained the repaired candidate.
- Temporary host fixture state was restored.
- Protected services, files, management interfaces and radio state were restored.
- Installed WsprryPi PID 1957 and executable hash were unchanged.

These are recorded identities, not a substitute for fresh device inventory.
Reconcile changed boots, firmware and naturally expired retained records.
Do not assume that the two boards currently run equivalent firmware.

The user explicitly confirms that both Picos use the existing unchanged
attenuated conducted signal path. Accept that confirmation as the current setup
declaration. Do not pause for another wiring confirmation, inspect the physical
path as a prerequisite, or repeat signal-path qualification.

Preserve the documented attenuation, cabling, filters, receiver settings,
reference configuration, drive strength and selected clock. The shared path
permits RF from either Pico but never from both simultaneously.

Continue ordinary device identity, ownership, scheduling and output-state checks.
These establish execution authority; they do not reopen signal-path validation.

7. Authorization, two-device coordination and finite execution

By submitting this prompt, I authorize execution of the remaining Phase 11.5
work on both Pico A and Pico B, including necessary implementation, test tooling,
reviewed firmware updates, configuration changes, target validation, finite RF,
autonomous scheduling checks, adversarial review, scoped repairs, affected
retests, restoration, commit and push.

Carry forward the accepted R3-COMPLETE-20260913-v2 standing authorization and
subsequent clarifications. This prompt supersedes earlier restrictions that
made Pico B read-only, prohibited B from ARM/RF/scheduling, or reserved all
physical acceptance for A.

Historical packets and results retain their original scope and accounting.
Do not modify or reuse a consumed packet. Prepare fresh reviewed finite packets
under this standing authorization without asking for routine approval again.

This prompt extends execution through the R4–R6 checks in phase11-5-plan.md,
including:
- Required owner/foreign-session and interrupted-operation checks.
- Controlled loss and restoration of the isolated target network path.
- Bounded address/lease recovery and idle Wi-Fi recovery checks.
- Configuration persistence through ordinary supported APIs.
- The smallest measured write sequence crossing one journal rotation.
- A finite autonomous scheduled job and subsequent schedule disablement.
- The prescribed R6 mixed-operation run.

For R5, inspect the selected device's actual journal position and storage
implementation first. Freeze the exact required write count and restoration
allowance before writing. Do not erase journals, reset counters or perform
write-endurance testing. This prompt separately authorizes the minimal reviewed
R5 rotation/scheduling sequence beyond the older R3 two-save baseline limit.

Two-device execution rules:

- Either board may perform any required function or acceptance test.
- Assign tests according to readiness, retained state, firmware applicability
  and opportunities for useful parallel work.
- Run independent builds, analysis, functional checks and preparation alongside
  physical work when they do not disturb its declared host/network workload.
- Each controller opens only its assigned board's endpoints and uses that
  board's actual device, boot, session, owner and job identities.
- Keep credentials and firmware image hashes device-specific.
- Preserve evidence separately for each device and workload.
- Do not treat a pass on one board as proof of another board's memory history,
  resource state, firmware identity or timing behavior.
- Keep each required three-cycle reclamation sequence on one selected device,
  using the same firmware and boot throughout.
- Keep comparable R6 resource windows on one selected device with a consistent
  firmware, boot and declared workload.
- Do not duplicate every test on both boards. Use either board's applicable
  evidence where the acceptance contract permits it, with an explicit rationale.
- Retain useful tested images. Update a board when a demonstrated defect,
  necessary affected retest or required candidate alignment justifies it.
  Do not alternate images merely for routine cleanup.

Shared RF reservation:

- At most one Pico may be Armed for an impending transmission, execute RF,
  or have an enabled autonomous schedule capable of starting RF.
- Enforce one shared RF reservation across all runners and both boards.
- Acquire the reservation before ARM or before enabling a schedule that can
  prepare/start RF. Include RF-capable diagnostic operations in this rule.
- Before granting the reservation, establish that the other board is
  authoritatively inactive, has no armed job and has scheduling disabled.
- Hold the reservation through Armed/Running states and schedule-triggered
  preparation until authoritative completion or cancellation confirms inactive
  output and no pending armed or scheduled start.
- Release it only after that reconciliation.
- A disconnect, missing acknowledgment, process exit or expired lock does not
  establish inactive output and must not automatically transfer the reservation.
- An uncertain output state blocks RF on both devices until reconciled.
- While one board holds the reservation, the other may perform bounded work
  that cannot start RF and does not disturb the active acceptance workload.
- A failed reservation attempt must not silently drop, reschedule or alter a
  test whose timing is part of its acceptance criteria.

Operational limits:

- RF remains at nominal 135,500 Hz, with native shifts within
  135,490–135,510 Hz.
- Each finite RF job is at most 3,600 seconds and within the selected device's
  advertised and verified CAPS.
- Each packet permits at most 16 RF jobs and 14,400 total planned RF seconds,
  counted across both boards if the packet uses both.
- Charge full planned duration for failed or uncertain submissions.
- Each packet permits at most one flash sequence, one BOOTSEL transition and
  one additional controlled software reboot, targeting the declared board.
  Updating both boards requires separately reviewed packets.
- Each packet permits at most three justified idle Wi-Fi OFF/ON cycles,
  with the target device and actual count recorded.
- Read-only allocation metrics are the default. A necessary diagnostic probe
  follows the accepted R3 idle-only bounds and states its hypothesis.
- Configuration saves are zero by default. Necessary baseline changes and the
  explicitly authorized R5 sequence require frozen counts and restoration
  reserves for each affected board.
- Each fixture session is at most eight hours execution plus 15 minutes
  reserved for cleanup. Freeze a smaller window whenever sufficient.
- Use one coordinated session deadline and cleanup plan for shared fixture
  resources. Concurrent packets do not multiply or extend that deadline.
- Independently supervise cleanup. Do not extend an expired deadline.
- Use only the named devices and established isolated fixture on wspr5.
- Preserve management access, permanent host configuration and the installed
  WsprryPi application.

These are ceilings, not targets. Before each packet, freeze its assertion IDs,
device assignments, exact counts/rates, jobs, identities, hashes, expected
transitions, RF reservation behavior, observations, deadlines and cleanup.

Review the executable packet, then execute it. Multiple justified finite packets
are authorized through completion; historical packet exhaustion does not cancel
this standing authorization.

Do not use arbitrary repeated traffic or RF attempts as diagnosis. If an action
exceeds this scope, prepare the concrete additional requirement and explain the
exact missing authorization while continuing independent authorized work.

If automatic approval review rejects an operation, accurately report the
operation and stated reason. Do not disguise or bypass the rejection.

8. Execute these work packages

Package 0 — Reconcile and freeze the current assertion matrix.

- Map every mandatory R1–R6 and extended-feature assertion to its evidence.
- Classify each as accepted/applicable, affected and needing retest, missing,
  or failed.
- Distinguish unchanged functional logic from changed layout, allocation,
  lifetime and timing behavior.
- Preserve existing physical-hour, mode and closed LOAD/replay evidence where
  justified.
- Reconcile the actual firmware, capabilities and retained state of both boards.
- Allocate remaining tests to either board, identifying useful parallel work,
  shared fixture dependencies and RF reservation requirements.
- Record exact remaining tests and package closure criteria.
- Repair misleading current summaries while keeping historical results intact.
- Do not reopen signal-path confirmation.

Package 1 — Maximum capacity during RF.

- Cover the maximum 512-event job and required candidate completion.
- Cover maximum WTP payload and oversize rejection/recovery during RF.
- Cover maximum HTTP body and oversize rejection/authenticated recovery.
- Assess existing boundary and extended-job evidence before repeating it.
- Use either board for RF acceptance; use the other for independent functional
  preparation or diagnosis where compatible with the frozen workload.
- BUSY from an ownership rule does not prove maximum allocation succeeded.

Package 2 — Supported combined load and bounded overload.

- Freeze the supported simultaneous resident workload and overlap timing on
  the selected device.
- Demonstrate its actual success under independent RF observation.
- Separately exercise one declared unsupported combination and its intended
  refusal/closure path.
- Verify owner preservation, RF continuity and authenticated recovery.
- Keep the required combined workload on the device being qualified; distributing
  its components across two boards does not prove single-device capacity.
- A failure of supported input cannot be credited as expected overload.

Package 3 — Network timeouts and resource recovery.

- Reuse applicable TLS/HTTP lifetime, failure and slot evidence.
- Complete affected slow-handshake, partial-header/body and stalled-I/O paths.
- Complete distinct WTP inactivity, incomplete-input and no-output-progress
  mechanisms.
- Confirm thresholds in current source and the accepted plan.
- Score each distinct path and its recovery independently.
- Distribute independent cases between boards where evidence applicability
  permits. Serialize shared network disruptions and all RF activity.

Package 4 — USB pressure.

- Exercise actual parser pressure and unread-output pressure during finite RF.
- Maintain an independent authoritative observation path.
- Verify RF continuity, transport recovery and final ownership/output state.
- Use board-specific endpoints and prevent cross-device observer/control errors.
- Reconcile Packages 1–4 against every remaining Group 2 assertion.

Package 5 — Retention and reclamation.

- Derive terminal, replay and session limits from current source/CAPS.
- Cover normal reuse, capacity, intended exhaustion, eviction and real expiry.
- Select the measured highest-resource representative workload.
- Pass all three equivalent reclamation cycles on one selected Pico, using
  the same firmware and boot throughout. Do not split them across boards.
- Preserve that device's declared state and observation conditions while the
  other board performs compatible independent work.
- Do not insert unrelated traffic or fixture changes into measured quiet or
  expiry windows.
- Compare equivalent states, accounting for caches, retention and TLS lifetimes.
- Do not infer fragmentation or largest allocatable block from aggregate
  free-memory samples.

Package 6 — Close R3.

- Reconcile all normative groups and extended-feature assertions.
- Audit applicability of earlier RF/resource evidence to the selected candidate.
- State which board supplied each physical assertion and why it is applicable.
- Complete missing affected checks and adversarial reassessment.
- Close R3 only when every mandatory assertion is supported.

Package 7 — R4 authority and interruption.

- Reuse qualifying Group 1 and other recorded evidence.
- Complete required foreign-control and forbidden-write checks across states.
- Complete required browser/production owner aborts in Armed and Running.
- Cover lost LOAD/ARM/ABORT replies, session replay and transport interruption.
- Verify no duplicate execution and authoritative state reconciliation.
- Distribute independent cases between boards while respecting the shared
  RF reservation.
- Close R4 only when all mandatory assertions are supported.

Package 8 — R5 lifecycle, split into two bounded runs.

A. Network recovery:
- External link loss during RF.
- Lease/address and certified-name recovery.
- Idle Wi-Fi management and DNS/SNTP competition.
- Coordinate fixture changes so they do not invalidate another active test.

B. Storage and autonomy:
- Configuration persistence.
- One actual journal rotation using the smallest reviewed write sequence.
- Time-validity admission.
- An autonomous schedule that prepares and completes a finite local RF job.
- Acquire the shared RF reservation before enabling the schedule; keep the
  other board unable to start RF until the schedule is disabled and the
  selected device is authoritatively inactive.

Use either board for either run. Share a run with another assertion only when
both are independently observed. Restore each changed board's retained baseline
and disabled scheduling. Close R5 only when all mandatory lifecycle assertions
are supported.

Package 9 — R6 and Phase 11.5 closure.

- Start only after R1–R5 have applicable acceptance evidence.
- Select one board and freeze its candidate, boot, configuration and workload.
- Execute the existing prescribed workload: 30 cumulative minutes of normal
  management load, at most 20 minutes RF, interleaved quiet observations,
  and at least three comparable post-warm-up resource windows.
- Keep the other board's activity from changing the declared workload or
  contaminating the comparisons.
- Apply the unchanged resource-growth and timing gates.
- Perform the final six-family applicability review, including evidence
  assembled from both boards.
- Record any board-specific limits explicitly.
- Close Phase 11.5 only for the exact configuration supported by the evidence.

Execute independent preparation and analysis concurrently where useful.
Physical concurrency must preserve workload validity and the global prohibition
on simultaneous RF. Do not create duplicate tests merely because two boards
are available.

9. Failure handling and evidence discipline

Check the harness offline before hardware, including parsing recorded field
types, deadlines, partial I/O, observer scheduling, evidence bounds and cleanup.

On an unexpected failure:
- Stop dependent stimuli and preserve raw evidence.
- Establish authoritative output/ownership state.
- Classify firmware, harness, fixture/network and observation failures
  separately.
- Diagnose the smallest concrete mechanism.
- Implement the smallest justified repair and add a meaningful regression.
- Review its impact, then perform only justified affected retests in a fresh
  finite packet where needed.
- Preserve independent passing assertions.

Do not relax thresholds, replace failed records, reset accounting, infer
inactivity from a disconnect, or promote simulated results to target evidence.

The historical C4 missed launch has supporting clock-mapping/guard evidence;
do not claim its exact historical interrupt branch was proved.
The external router reset was user-reported context.
Neither fact grants acceptance to a failed workload.

A package is complete when its named assertions pass and its review/restoration
requirements are met. A prepared script, successful build or committed report
does not close a physical assertion.

10. Adversarial review and iteration

For each package, challenge:
- Whether the intended code/resource path was actually exercised.
- Device, boot, firmware, owner, job and request identity.
- Complete request writes and response framing/schema/CRC where applicable.
- Real workload overlap, pressure and retained-state comparability.
- Deadlines and observer coverage, including partial exchanges.
- Correct supported-input versus overload classification.
- Evidence reuse after firmware/layout changes.
- RF continuity, state authority, configuration and fixture restoration.
- False acceptance when observations are absent, stale or contradictory.

Use raw evidence independently of runner summaries. Add targeted altered-
evidence rejection tests where they materially protect acceptance claims.

Repair actionable findings, rerun affected checks and perform another
adversarial assessment. Continue until no actionable finding remains or a
specific external blocker prevents further authorized progress.

Perform a final review across all packages before claiming Phase 11.5 closed.

11. Artifacts, publication and reporting

Maintain:
- A current assertion-level completion matrix.
- A concise progress record showing package and family status.
- Immutable execution results with source/image/helper/configuration hashes.
- Source-impact and evidence-reuse decisions.
- Review findings, repairs and reassessment results.
- Exact budgets, charges and independently verified restoration.

Keep credentials, captures, generated firmware and private configuration out
of Git. Publish sanitized results and hashes. Avoid duplicative historical
narratives and contradictory “current” summaries.

Checkpoint completed packages with scoped commits and requested pushes.
Use ordinary non-force integration. Run documented checks appropriate to the
changes; broaden testing when source impact warrants it. Independently verify
remote branch SHA after pushing.

Remain responsive during execution. Give concise progress updates identifying
what closed, what failed, what remains and the next bounded action.

Final report:
- Phase 11.5 CLOSED or OPEN, with exact accepted configuration if closed.
- R1–R6 status and newly closed assertions.
- Remaining failures/blockers without euphemisms.
- Firmware/tooling changes and validation performed.
- Adversarial review findings and final reassessment.
- Final board, configuration, schedule and host restoration state.
- Artifact paths, commits, push outcome and independently verified remote parity.
- Working-tree state for every changed repository.

Begin with Package 0 and continue through the authorized work. Do not ask
whether I want you to execute this prompt.
## Subsequent evidence-transfer authorization

The user subsequently stated: “You are authorized to exfil authenticated traffic
and payloads from this lab environment if it speeds things up.” This authorizes
retrieval of the named laboratory captures for local auditing. Captures remain
private in ignored build storage; publication contains sanitized results and
hashes.
