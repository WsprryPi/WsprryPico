# WsprryPi-style status console execution prompt

Status: Not started. Saving, reviewing or committing this prompt does not authorize its implementation. Execute it only when separately instructed by the user.

Implement a WsprryPi-style contextual status console in WsprryPico, with a guarded Reset Pico action.

Work on WsprryPico devel. Follow the standing execution authority granted for this session and all applicable repository instructions. This prompt is for later execution; a request to print or review it does not authorize implementation.

## Objective

Replace or extend the existing Transmitter status presentation so it follows the useful layout, contextual information and state interpretation of the WsprryPi Operations console, while accurately representing WsprryPico capabilities.

The console must explain what the transmitter is doing, what happens next and which actions are available. Provide Reset Pico where appropriate instead of a Pi shutdown action.

Preserve the existing transmission engine, scheduling guarantees, authentication boundaries and settings. Implement the console as a presentation of authoritative device state, with explicitly guarded controls.

## 1. Establish the working state

- Inspect the current checkout, branch, upstream, worktrees and working-tree changes before editing.
- Use the current devel source. Do not implement against the older detached pico-schedule-build snapshot.
- Preserve unrelated work and concurrent changes. Do not reset, stash, force-push or discard files.
- Read README.md, CONTRACT.md, engineering/architecture.md and engineering/development/README.md.
- Read applicable AGENTS.md instructions and relevant frontend skills.
- Locate existing status-console proposals, the consolidated backlog, browser API contracts, restart behavior and tests.
- Consult the earlier private operations-console research if available, but verify its conclusions against current source. Do not depend on that private file as the only specification.
- Save this comprehensive prompt in an appropriately named file under engineering/development/, following existing naming conventions. Reuse an existing matching prompt rather than creating duplicates.

## 2. Research current WsprryPi devel

Inspect WsprryPi devel read-only. Record the exact source revision consulted.

Find the Operations console implementation, including its PHP/template layout, operation JavaScript, shared browser logic and corresponding status/control endpoints. Trace behavior through the source rather than reproducing the supplied screenshot alone.

Document:

- State precedence and explanatory text.
- Mode-dependent cards and labels.
- Current and next frequency selection.
- Active transmission and message progress.
- Paused, disabled, waiting, completed, fault and recovery states.
- WSPR plan information.
- Transmit control and stop behavior.
- Reboot-policy controls.
- Local and UTC clocks.
- Candidate and committed frequency-correction information.
- Restart and shutdown controls.

Build a compact mapping of each relevant Pi behavior to existing Pico telemetry and controls. Identify information Pico cannot currently provide.

Use this mapping to guide implementation. Do not copy Pi-specific backend logic, Linux lifecycle behavior, shutdown semantics or unsupported fields into Pico firmware.

## 3. Define authoritative console state

Inspect the current Pico browser API and internal runtime model before choosing the implementation.

Prefer a coherent, bounded operations snapshot derived from existing authoritative state. Extend the existing status resource when that fits its contract; introduce a documented versioned resource only when needed.

Avoid assembling a misleading state from unrelated polling responses captured at different times.

The snapshot and browser model should distinguish, where applicable:

- Device identity, boot identity and observation freshness.
- Effective operating mode.
- Current job identity and lifecycle.
- Ownership and whether local controls are permitted.
- Actual RF/output activity.
- Armed or waiting jobs.
- Enabled, paused, expired and recovery-blocked schedules.
- Next eligible occurrence.
- Pending control changes, including a pause awaiting durable persistence.
- Time readiness and configured holdover.
- Faults or recovery requirements.
- Current and next frequency information.
- Available actions and reasons an action is unavailable.

Define explicit state precedence and cover contradictory-looking combinations. A job can remain active while RF is off during a keyed gap. An accepted job can finish while future occurrences are paused. A saved schedule can exist while disabled.

Do not interpret RF-off as job completion. Do not label ordinary holdover a fault solely because time age exceeds 90 seconds; apply the configured timeout and current firmware policy.

On stale, failed or disconnected observations, show an explicit unavailable/stale state. Do not continue presenting old information as live, and do not leave destructive controls enabled.

Keep serialization, polling and rendering bounded. Console updates must not add per-symbol network traffic, blocking work or allocation pressure to the RF timing path.

## 4. Implement the contextual interface

Follow the useful visual hierarchy of the WsprryPi Operations console:

- A prominent current-state card with a short explanation.
- Mode and frequency cards appropriate to the current context.
- Relevant schedule, job and progress information.
- Authenticated controls.
- Local and UTC clocks.
- Frequency-correction details when meaningful.
- A clearly labeled Reset Pico action.

Adapt the layout to Pico’s existing design and screen sizes. Preserve accessible labels, keyboard navigation, focus visibility and readable status text. Do not rely on color or icons alone.

Keep read-only transmitter status visible when signed out. Preserve initial password focus on an unauthenticated page load without stealing focus during later refreshes.

Separate public status from authenticated controls and privileged details. Inspect existing security contracts before deciding which fields may be public. Never expose credentials, session tokens, Wi-Fi secrets or privileged ownership material.

Avoid replacing or overwriting an operator’s in-progress form entries during polling.

## 5. Present accurate mode-specific information

### WSPR

- Distinguish the configured USB dial frequency from the actual RF transmission frequency.
- Show current or next frame information only when supported by authoritative scheduler state.
- Describe an enabled schedule waiting for its next slot clearly.
- Preserve Pico’s frequency-selection semantics. Do not import Pi-only randomization or frequency offsets.

### QRSS

- Label the direct RF frequency as Carrier.
- Show the loaded or scheduled message, duration and timing where those values are retained and authoritative.

### FSKCW

- Distinguish Space and Mark frequencies.
- Show their configured shift and applicable timing.

### DFCW

- Distinguish Dot and Dash frequencies.
- Show the configured shift and actual DFCW timing.
- Represent keyed gaps correctly.

### All message modes

- Distinguish message-internal repeats from recurring schedule occurrences.
- Show scheduled UTC start, recurrence interval, optional expiry and next eligible occurrence where applicable.
- Distinguish armed, running, complete, paused, expired and recovery-required states.
- Do not infer text or character progression from RF activity alone.
- Generic externally loaded RF-event jobs may not retain original message text. Show an honest unavailable value or event-level progress instead of inventing text.

If character progression requires additional telemetry, assess a compact compiler event-to-character mapping and an authoritative engine cursor. Implement it only if it fits Pico’s memory and timing constraints. Otherwise deliver accurate coarser progress and record the remaining enhancement as unfinished work.

## 6. Handle frequency correction truthfully

Research which correction values Pico actually supports and exposes.

Distinguish selected/candidate correction from the correction committed to an accepted job when both exist. Explain application timing accurately.

Do not display unavailable Pi-only estimates, imply a measurement has occurred or show a candidate update as an active-job correction.

Use explicit unavailable states rather than fabricated zero values. Preserve calibration settings and existing correction behavior.

## 7. Implement Reset Pico through the supported restart path

Inspect and reuse the existing restart endpoint and firmware lifecycle. Do not create a parallel reset mechanism or introduce a shutdown action.

Reset must:

- Require authentication and existing request protections.
- Be bound to the intended device and current boot/revision as supported by the API.
- Revalidate eligibility on the server immediately before acting.
- Reject reset while a job is loaded, armed, running or otherwise occupied according to the current restart contract.
- Treat RF-off keyed gaps as part of an active job.
- Respect ownership, pending persistence, flash activity and recovery constraints.
- Preserve settings, recurrence watermarks and in-flight recovery barriers.
- Preserve existing reboot and schedule behavior.
- Clearly describe the action and its expected consequence before submission.
- Use a concise product confirmation appropriate to a device reset.
- Prevent duplicate submissions and handle lost responses safely.

During restart, show a reconnecting state. Confirm recovery using a fresh observation and changed boot identity where available. A timeout must remain an unconfirmed outcome.

Test stale tabs, expired sessions, competing clients, a job becoming active between rendering and clicking, and ambiguous network responses.

Do not add WsprryPi’s three reboot-policy options as decorative controls. Include such options only if Pico already implements equivalent supported semantics. Any new reboot-policy behavior is a separate product change and must remain a proposal in this slice.

## 8. Preserve existing behavior and contracts

Maintain:

- Standalone operation and WsprryPi hardware-backend operation.
- USB CDC reference transport and device-local RF timing.
- One authoritative JobService/RF control path.
- Existing one-shot and recurring message behavior.
- WSPR/message scheduling exclusivity.
- Durable consumed-start watermarks and recovery barriers.
- Safe pause behavior and accepted-job completion.
- Existing configuration, upgrade and persistence guarantees.
- WTP’s device-neutral, independently versioned contract.
- Current UTC date/time controls and message-duration display.

Do not broaden this task into syslog, transmitter-engine redesign, unrelated scheduler changes or changes to other repositories.

## 9. Validate the implementation

Use documented project commands and retained dependencies. Do not invent commands or perform an unnecessary dependency upgrade.

Add meaningful deterministic coverage for:

- State precedence and action eligibility.
- Public versus authenticated status.
- Active keyed gaps.
- Armed jobs and future starts.
- WSPR and each message mode.
- Recurrence, expiry, pending pause and recovery barriers.
- Ownership conflicts.
- Missing, stale, malformed and disconnected status.
- Frequency labels and correction semantics.
- Reset authentication and server-side race rejection.
- Reconnection and boot identity.
- Form preservation during polling.

Exercise source and shipped browser assets as appropriate.

Check desktop and narrow layouts, signed-in and signed-out views, keyboard operation, clocks in multiple timezones and contextual card changes. If Chrome requires profile selection, use Lee.

Capture representative screenshots and distinguish synthetic fixtures from live-device evidence.

Run affected tests, appropriate regression checks, firmware builds, resource-budget checks and documentation validation. Compare firmware RAM, flash, stack and request/polling costs against the baseline.

Hardware validation is authorized when necessary:

- Identify each intended Pico by USB serial before control or programming.
- Preserve configuration and verify restoration.
- Use idle devices for reset tests.
- Do not interrupt unrelated active jobs.
- If a firmware update is needed, use the supported preserving upgrade path.
- Verify a current, appropriate conducted RF termination before any transmission.
- If physical RF safety cannot be established, complete non-transmitting validation and report the remaining RF-dependent check.
- Keep tests finite and record board, firmware, source, engine, clock and setup.

Do not claim continuous RF verification or independent SDR decoding from periodic status observations.

## 10. Perform adversarial review and iterate

Perform an adversarial review of the completed change, examining implementation, API contracts, security, runtime cost, persistence, lifecycle races and UI interpretation.

Specifically challenge:

- Whether displayed state can contradict actual job or RF authority.
- Whether anonymous requests reveal privileged information.
- Whether stale observations enable inappropriate controls.
- Whether reset can occur during a keyed gap or after a race.
- Whether restart can replay an accepted recurring occurrence.
- Whether pending changes are falsely presented as durable.
- Whether frequencies, text progression or correction values overstate available telemetry.
- Whether polling or serialization can disturb timing or exhaust resources.
- Whether browser errors preserve drafts and recover predictably.
- Whether layouts and controls remain usable on small screens.

Fix every actionable finding within scope. Add appropriate regression coverage, rerun affected checks and close each finding with evidence.

Then perform another adversarial assessment against the corrected result. Continue until no actionable findings remain or a concrete external blocker prevents closure.

State whether the assessment was self-review or independently performed. Do not claim independent review without an actual independent reviewer.

## 11. Update documentation and the TODO list

Update current operator and engineering documentation to explain the delivered behavior directly.

When implementation and review are done, add or reconcile a single item under the existing UI section of the consolidated TODO/backlog for the WsprryPi-style contextual status console with Reset Pico.

Link the saved prompt. Mark the item complete only when its acceptance criteria are satisfied. Keep any remaining selected enhancement explicitly unfinished, with an accurate description. Do not create duplicate entries or leave completed work presented as pending.

Retain the saved prompt as requested, with its execution status and relevant commit/evidence references. Keep credentials, screenshots, raw captures and generated firmware out of source control.

## 12. Commit, push and report

Inspect the final diff and repository state. Stage only this task’s files.

Commit and push the saved prompt, UI TODO item, implementation, tests and documentation to devel using the established workflow. Preserve concurrent work, do not force-push and do not bypass protections.

Inspect relevant CI results, correct task-related failures and verify the final remote commit identity.

Then report:

- What changed and how the contextual console behaves.
- How Reset Pico is guarded.
- Which WsprryPi behaviors were adopted and which remain unavailable.
- Validation results, adversarial findings and their closure.
- Actual device deployment/reset activity and final device state.
- Material limitations or unresolved work.
- Saved prompt and UI TODO paths.
- Commit IDs, push result, CI result and final working-tree state.

Operate autonomously within the granted standing authority. Complete independent work before raising a material blocker. Do not turn routine progress updates into approval requests.
