# Amplifier enable GPIO during transmissions

Execute only item 3 of the [Consolidated backlog](consolidated-backlog.md).
Implement basic optional amplifier-enable GPIO: assert the configured output
before local RF starts and return it inactive after completion, STOP, abort or
fault. Record the result and evidence closeout, perform independent adversarial
review, repair actionable findings and repeat affected checks/review, then
commit and push the scoped implementation.

This is a saved execution prompt. Preparing or publishing it does not start
implementation or hardware testing; item 3 remains not started until execution
is requested. Optional settling delays and amplifier lead/tail timing remain
future work.

## Entry and authority

Work in /Users/lbussy/GitHub/WsprryPico. Read AGENTS.md, README.md, CONTRACT.md,
docs/architecture.md, docs/development/README.md and the consolidated backlog
before implementation. Print the complete Finish now section, preserving its
order and NTP Work grouping, using ✅ finished, ⏳ in flight and ▧ not started.
The consolidated backlog is the sole current/future work list. Do not create
another roadmap, pending-work list or parallel status ledger.

Inspect the current branch, full HEAD, upstream, live remote devel tip, staged,
unstaged and untracked work before editing. At preparation, devel and the
queried remote tip were e5e6643954aef3775195b923ee108fe441ad8118, with ongoing
contract reconciliation and other documentation work. Refresh the actual
baseline and preserve concurrent work; these identities are not reset targets.
Change only item 3 to ⏳ when execution begins.

WsprryPico is the only implementation/publication repository authorized by this
prompt. Other WsprryPi-family repositories are independent read-only references.
Do not modify their clients, services, documentation, tests or compatibility
pins. Do not invoke repository or harness cleanup. Preserve historical evidence,
source/image identities, failed attempts and operator dispositions.

Do not implement LPF/band switching, Si5351, NTP work, RF calibration, Type 2/3
decode, an installer, deployment CI, release publication or a general UI review.
Do not add amplifier power regulation, drive-strength changes, automatic RF
warmup, user-adjustable delays, settling checks or lead/tail fields. Basic
polarity and inactive-state handling are part of this GPIO feature.

## Source boundaries to inspect

Read the [pin-assignment contract](../pin-assignment-contract.md),
[implemented pin allocation](pin-allocation.md), [GPIO drive](gpio-drive.md),
[standalone behavior](standalone.md), [browser API](../browser-api.md),
[configuration updates](configuration-updates.md),
[USB management](../protocol/USB-Management.md) and
[normal firmware selection](phase15-16-results.md).

Trace the actual implementation rather than copying the TX indicator:

- src/hardware/pins.hpp and pins.cpp: optional amplifier_gp, eligibility,
  exclusive ownership, parsing/serialization, operational support and choices.
- src/standalone/config.cpp, persistence/progress and their validators: complete
  saves, ordinary omission preservation, boot application and restart latches.
- src/network/api.cpp and src/application/resources.cpp: existing pin/config
  routes, capability/resource versions and authenticated management carriers.
- src/standalone/pico/main.cpp and adapters: validated boot plan, initialization,
  recovery, STOP/button paths and actual application wiring.
- src/rf/worker.hpp, worker.cpp and src/rf/pico/worker.cpp: local RF owner,
  mailbox/safety latch, watchdog/failure handling and core boundaries.
- src/rf/pio_dma_sink.cpp, src/rf/stream_engine.cpp and
  src/rf/pico/pico_pio_dma.cpp: launch admission, alarm retries, physical output
  enable, hardware completion, halt/release and partial-initialization cleanup.
- src/rf/indicator_gate.hpp and provisioning indicator code: distinct ownership
  and checked launch coordination that must remain correct.
- tests/pin_allocation_tests.cpp, tests/pio_dma_tests.cpp,
  tests/rf_worker_tests.cpp, tests/rf_worker_failure_tests.py and the relevant
  configuration, schema, indicator, shutdown and image checks.

At preparation, PinPlan stores amplifier_gp but operational() rejects any
configured amplifier, and adapter_support.amplifier is false. It has indicator
polarity but no amplifier-polarity field. The RP2350 RF driver's constructor
does not touch peripherals; launch/halt belong to its dedicated RF core. These
are entry observations to refresh, not declarations that the feature exists.

The selected pin contract mentions eventual filter settling and amplifier
lead/tail sequencing. Implement only immediate ordered enable/disable here;
qualify the current subset without promoting those future timing features.

## Configuration and compatible management

Reuse optional amplifier_gp and existing eligible GP numbers and exclusive pin
ownership. Disabled/null remains the default and must cause no amplifier GPIO
access. Do not hard-code an enable pin, reuse the RF pin or indicator/button,
or enable unimplemented LPF/I2C adapters merely to admit the amplifier.

Represent active-high and active-low polarity explicitly and independently of
indicator_active_high. A small optional amplifier_active_high boolean with a
true default is a proposed implementation approach, not an existing contract.
Choose and document the smallest compatible representation after inspecting
actual closed schemas and strict consumers. Support both polarities without
adding timing fields or inferring polarity from another resource.

Preserve existing default canonical bytes and legacy saves where possible.
Ordinary partial/legacy updates must preserve omitted amplifier configuration;
explicit complete replacement/reset follows documented defaults. Reject
malformed polarity, ineligible/conflicting pins and unsupported combinations
atomically, without sibling saves or journal/revision changes. Do not silently
drop a saved enable pin or fall back to a default pin after a decode failure.
Document any required version/rollback boundary honestly.

Pin/polarity changes remain idle/unowned/RF-inactive/nonfaulted, target/revision
checked and boot-applied. Saving never asserts a GPIO. A real hardware change
latches restart-required/output inhibition for the boot, including A/B/A;
unrelated edits and reverting a draft cannot clear it. Separate saved settings
from the immutable active boot plan. Progress/draft saving is not activation.

Update only the necessary existing pin editor, capability and API descriptions
to expose implemented support and supported activation. Preserve closed legacy
resource shapes; use explicit version/capability negotiation where necessary
instead of breaking strict clients. Unsupported clients must not be presented
as configured or compatible. Other management settings must continue working.
WTP/1 and Field-GATT framing remain unchanged; auxiliary-pin configuration is
member management, not another WTP command or execution authority.

## Local output lifecycle

Place the portable lifecycle policy behind a narrow adapter and deterministic
fake output; keep Pico SDK operations in the RP2350 adapter. Use one local RF
authority below all job producers: standalone schedules, USB/network WTP and
browser-origin jobs must not implement their own amplifier state machines.

Initialize a validated configured output inactive without an active glitch.
Inspect the pinned SDK's latch/function/direction ordering and preload the
inactive level before enabling output. Do not drive a guessed pin from invalid
storage or trust unvalidated configuration. External bias is responsible for
reset, boot-ROM, unpowered and other periods software cannot control; do not
claim a software guarantee across them.

Keep the enable inactive during boot, idle, validation, LOAD/preparation and
the potentially long ARM wait. Assert only on the final admissible local launch
path, after existing clock, ownership, RF-drive, safety and indicator gates,
and before physical RF output can become active. There is no intentional
settling interval or configurable early lead. A failed assertion or uncertain
readiness must prevent RF launch. Recheck the existing inhibit/cancel guards
around this boundary; a STOP cannot be bypassed by a late enable write.

Assertion must not depend on USB/network delivery or a delayed core-0 UI poll.
Do not perform blocking CYW43, allocation, logging, storage or network work in
the RF launch interrupt. Preserve current UTC deadlines, RF renderer placement,
PIO/DMA refill behavior, GP14 safety and indicator handshake. If cross-core
coordination is necessary, use bounded, generation/epoch-bound acknowledgements;
an old job's delayed assertion/acknowledgement cannot authorize a later launch.

The enable covers one finite RF job, including that job's normal keyed gaps;
it is not per-symbol relay keying. Deassert between separate jobs, including
the two jobs of a Type 2/3 pair. No amplifier tail hold or post-job dwell is
introduced. If that interpretation conflicts with an accepted current contract,
resolve the concrete conflict before implementing a different policy.

Completion, explicit STOP, ABORT, lease expiry, missed launch, failed preparation,
engine/DMA fault, disconnect-driven cleanup, restart/recovery and resource-release
paths must converge on bounded cleanup. A transport disconnect does not
independently cancel a job that the existing ownership policy permits to
continue; retain that policy and clean up when its actual job terminates.

On cleanup, stop/force RF inactive and deassert amplifier enable without an
intentional tail. Attempt amplifier deassert even when RF halt or another
cleanup step fails. In particular, do not leave it asserted behind an early
return or a fallible DMA wait. Cover no-open/partially-open driver paths,
repeated cleanup, stale alarms/IRQs, rearm and rejection immediately after
assertion. Do not rely solely on eventual destructor or UI-loop execution.

Keep fault/output-unknown ownership when cleanup is unconfirmed; never report
success, clear safety latches or admit another transmission merely because a
GPIO command was issued. Distinguish commanded level, SDK/register observation
and independently observed physical level. A GPIO getter does not establish
that an external amplifier stopped producing RF.

The explicit WsprryPico-Inhibited variant must never assert amplifier enable
for simulated jobs. Define its safe inactive initialization/capability behavior
consistently without linking the physical RF worker or treating simulation as
physical GPIO evidence. A disabled amplifier retains the existing RF behavior
and does not require a fake acknowledgement to transmit.

## Validation and finite target evidence

Start with deterministic hardware-free tests that observe ordering and failure
behavior, not private implementation details. Cover at least:

- Disabled/no-touch behavior, both polarities, inactive initialization, every
  pin overlap class, invalid data and atomic persistence failure.
- Omission/replacement defaults, reload/round-trip, boot versus saved state,
  restart inhibition including A/B/A, capability/version compatibility and
  simulated-image refusal to assert.
- No assertion for LOAD, long ARM wait, refused/missed launches or a failed
  launch gate; successful assertion before the first RF activation.
- Normal completion, STOP, ABORT, lease expiration and relevant fault cleanup;
  assertion failure, failed RF halt, failed/unconfirmed deassert, partial init,
  idempotent stop and recovery/rearm.
- Stale callbacks/epochs and cancel-versus-launch races, with no late reassert
  after cleanup. Separate jobs must deassert between them.
- All job sources sharing the same policy; existing LED, RF-drive, button,
  scheduler, timing, storage and ownership behavior remaining intact.

Use actual commands registered in docs/development/README.md and CMake. Existing
entry points include bash scripts/check_host.sh and
python3 scripts/validate_wtp_contract.py. Inspect CTest registration before
selecting focused names. Run affected tests, then the justified regression
suite; rerun only affected checks after review repairs unless a new concern
warrants broader testing. Add meaningful failure regressions for new behavior.

Build the normal WsprryPico and explicit WsprryPico-Inhibited targets, plus the
compatibility RF target if its shared wiring changes. Retain normal 138 MHz,
existing SDK/toolchain/picotool pins, language standards and all image/stack/
heap/flash/renderer guards. Use retained local dependencies and fresh task-local
ignored build directories. Do not install tools or download an SDK incidentally.
Record actual source/build inputs, generated identity, ELF/UF2 hashes, results,
skips and environmental blockers; a successful link is not physical evidence.

For target testing, follow the operator's current connected-board/setup
statements and AGENTS.md authorization without redundant per-job approval.
The earlier conducted RF-chain statement does not identify an amplifier-enable
pin, attached load, polarity or measurement fixture. Verify those concrete facts
before driving a newly assigned pin. Do not assume a real amplifier is present,
connect one, or infer physical enable behavior from an SDR capture alone.

If suitable observation is available, use one identified Pico and the existing
conducted path, preserving RF drive, correction, attenuation, cables and receiver
state. Use at most six finite RF jobs of at most one second each, no more than
six seconds total RF. Freeze the job/fixture plan before starting; charge every
actual RF start, including failed capture. Use zero-RF prelaunch cancellation
where possible. No WSPR frame, frequency sweep, second board or unlimited retry
is needed. Additional RF requires an explicit budget extension.

Record the actual enabled GPIO and polarity, board/boot, exact newly built
uninhibited firmware/source/hash, RF engine/clock/frequency and observation
method. Capture enable and RF start/end ordering with an appropriate independent
fixture when available; register readback or software timestamps alone cannot
prove edge ordering. Exercise only finite, controlled fault paths supported by
the fixture; do not intentionally wedge cores or provoke uncontrolled RF.
Reuse captures for offline reassessment without consuming more RF budget.

If the required physical fixture is unavailable, finish implementation, host
tests, builds and review, and explicitly retain the physical evidence limitation.
Do not invent measurements or label the complete physical assertion verified.
Completion language and item 3's status must match the acceptance actually met.

## Evidence closeout and adversarial review

Record the feature contract and scoped outcome in amplifier-enable-results.md
with a sanitized machine-readable manifest if target evidence is collected.
Include changed paths, chosen configuration/version behavior, local owner and
launch/cleanup ordering, failure semantics, actual checks and failures, source/
artifact identities, hardware observations and limits. Keep raw captures,
generated images, credentials and private backups untracked under task-local
build paths. Add focused links to maintained pin/API/build documentation;
do not rewrite historical failures or copy another pending-work list.

After any target work, confirm RF inactive, enable inactive, no pending test
job/ownership and restored configuration/firmware/services/receiver state as
applicable. Preserve watermark advancement and use supported restoration rather
than whole-flash rollback. Record restoration failures honestly. Do not claim
external amplifier, reset-state or RF qualification from this GPIO feature.

Use a separate read-only adversarial reviewer for the final implementation,
tests, documentation, evidence and backlog closure wording. Require specific
findings with source/evidence and consequence. Challenge unsafe boot polarity,
closed-schema compatibility, missing job/termination paths, RF-before-enable,
long ARM assertion, stale/late reassertion, cleanup early returns, failed halt
masking amplifier deassert, cross-core/IRQ latency, disabled/inhibited regressions,
unconfirmed cleanup and overstated physical claims. Confirm future timing and
other backlog work have not been implemented implicitly.

Repair every actionable in-scope finding, rerun affected checks and obtain a
fresh independent assessment of the repaired final diff. Iterate until no
actionable finding remains. Respect the finite RF budget during repairs; report
a material unresolved blocker rather than claiming completion or silently
expanding this task.

## Commit and push

Update only item 3's canonical status and preserve its saved-prompt link and
all other items. Mark ✅ only when the requested feature and required checks/
review are complete with accurate evidence limits. If a required acceptance
assertion is still blocked, retain ⏳ and state exactly what remains unverified.

Review the full and staged diffs. Stage only attributable implementation,
tests, documentation/evidence and item 3 changes. Use partial staging when
the backlog or another file also contains unrelated work. Run git diff --check
for the scoped diff and git diff --cached --check. Commit and non-force push
the scoped result to origin/devel; these actions are explicitly authorized on
execution without another routine confirmation. Preserve concurrent commits
and user work; do not reset, stash, clean, force push or absorb unrelated edits.
Do not tag, publish a release, create a PR or publish a documentation site.

Independently query the remote devel tip after push and compare with local HEAD
and upstream. Report what changed, checks/skips, review findings and repairs,
hardware budget/evidence/restoration, limitations, actual commit/push/parity
and remaining working-tree state. Reprint the complete canonical punchlist with
✅/⏳/▧. Stop after item 3.
