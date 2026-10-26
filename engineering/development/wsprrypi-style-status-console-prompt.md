# WsprryPi-style status console execution prompt

Status: Numbered TODO item 6 is in progress, as reported by the user. This is the canonical execution prompt linked from [item 6](consolidated-backlog.md). Saving, printing, reviewing or committing the prompt does not start implementation. Coordinate with existing implementation work when assigned execution of item 6.

Implement a WsprryPi-style contextual status console in WsprryPico, with a guarded Reset Pico action.

Work from current WsprryPico devel and follow all applicable repository instructions. The full **Wsprry Development Session — Standing Execution Authority** at the end of this file is part of the execution assignment. Once execution is assigned, use that authority throughout implementation, diagnostics, deployment, review, correction, commit and push without routine approval gates.

## Objective

Replace or extend the existing Transmitter status presentation so it follows the useful layout, contextual information and state interpretation of the WsprryPi Operations console, while accurately representing WsprryPico capabilities.

The console must explain what the transmitter is doing, what happens next and which actions are available. Provide Reset Pico where appropriate instead of a Pi shutdown action.

Preserve the existing transmission engine, scheduling guarantees, authentication boundaries and settings. Implement the console as a presentation of authoritative device state, with explicitly guarded controls.

## 1. Establish the working state

- Inspect the current checkout, branch, upstream, worktrees and working-tree changes before editing.
- Use the current devel source and record the starting revision. Inspect local and remote divergence before choosing the established branch/worktree workflow; do not switch or reset a checkout carrying unrelated work.
- Preserve unrelated work and concurrent changes. Do not reset, stash, force-push or discard files.
- Read README.md, CONTRACT.md, engineering/architecture.md and engineering/development/README.md.
- Read applicable AGENTS.md instructions and relevant frontend skills.
- Locate existing status-console proposals, the consolidated backlog, browser API contracts, restart behavior and tests.
- Read `src/network/web/DESIGN.md` and preserve the embedded interface's established design conventions. Use any applicable frontend skill during implementation.
- Reuse this saved prompt and existing item 6. Do not create a second execution prompt or another status-console TODO.

Use the following source map as a starting point, verifying names and contracts against the checkout used for execution:

| Concern | Current sources and references |
| --- | --- |
| Pico operator page, style and state/rendering | `src/network/web/index.html`, `style.css`, `app.js`, `organization.js` and `device-presentation.js` |
| Public consumer reads and authenticated management wrapper | `src/network/bootstrap_web/radio-client.js`, `src/network/consumer_radio.cpp` and `engineering/protocol/Consumer-Radio-v1.md` |
| Shared status/restart authority | `src/network/api.cpp`, `api.hpp`, `engineering/browser-api.md` and the existing Pico restart adapter |
| Scheduling and finite-message status | `src/standalone/message_schedule.hpp`, existing scheduler/JobService implementations and the message-schedule section of `engineering/browser-api.md` |
| Identity, access and save recovery | `engineering/development/device-presentation.md`, `consumer-sessions.md`, `session-recovery.md` and `configuration-updates.md` |
| Clock, frequency and resource limits | `CONTRACT.md`, `engineering/development/clock-discipline.md`, `clock-support.md` and `band-support.md` |
| Shipped assets | `src/network/bootstrap_web/package.json`, `scripts/build_operator_assets.mjs` and `src/network/web/asset-build.json` |

At prompt preparation, WsprryPico was on devel at `94a7fa69d5a9db7867688c28729a099fd3bb4f6a`. The locally available WsprryPi devel reference was `5bc24e893646140d44f0bf9a20d61115d0eadda9`; its active checkout was main. These are research baselines, not a requirement to use old revisions. Refresh and record the actual revisions used when execution begins.

## 2. Research current WsprryPi devel

Inspect WsprryPi devel as the reference implementation. Use read-only revision inspection or a suitable existing worktree when its active checkout is on another branch. Record the exact source revision consulted. Reference reading does not require changing the Pi checkout.

Find the Operations console implementation, including its PHP/template layout, operation JavaScript, shared browser logic and corresponding status/control endpoints. Trace behavior through the source; use screenshots as secondary evidence of presentation.

Start with `WsprryPi-UI/data/views/operation.php` and `WsprryPi-UI/data/operation.js` in the devel reference. Follow their runtime snapshot, WebSocket and backend dependencies. Inspect exact upstream provenance and attribution before reusing implementation code; prefer adapting behavior within Pico's architecture.

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

Trace `GET /api/v1/status` and `/api/v1/jobs` for authenticated state, and `GET /api/consumer/v1/status` for signed-out state. The current public resource is the strictly validated closed `transmitter-public-status/1` schema. Do not append unnegotiated fields to that shape or expose authenticated responses through it. If a new resource or version is necessary, define its bounded schema, discovery/selection, old-client behavior, disclosure rules and tests before using it. Preserve independently versioned resources and current carrier admission rules.

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

Derive precedence from authoritative Pico state rather than copying Pi labels mechanically. Cover observation unavailable/stale, fault/recovery inhibition, accepted active or armed work, pending management actions, schedule pause/expiry, incomplete configuration, clock readiness and idle waiting. Keep current-job state separate from next-occurrence blockers. An externally owned active job must remain visible even when the standalone station or schedule is not configured. Do not claim that a connected browser owns a job solely because it can read status.

Do not interpret RF-off as job completion. Do not label ordinary holdover a fault solely because time age exceeds 90 seconds; apply the configured timeout and current firmware policy.

On stale, failed or disconnected observations, show an explicit unavailable/stale state. Do not continue presenting old information as live, and do not leave destructive controls enabled.

Keep serialization, polling and rendering bounded. Console updates must not add per-symbol network traffic, blocking work or allocation pressure to the RF timing path.

Retain one polling authority with bounded in-flight work, request cancellation/epochs and out-of-order-response rejection. Bind observations to the intended device, boot and job; an old terminal record must not replace a newer job. Preserve existing memory admission reserves, connection limits and response deadlines. Polling and status reads must not write journals, alter schedules or acquire ownership.

## 4. Implement the contextual interface

Follow the useful visual hierarchy of the WsprryPi Operations console:

- A prominent current-state region with a short explanation.
- Mode and frequency summaries appropriate to the current context.
- Relevant schedule, job and progress information.
- Authenticated controls.
- Local and UTC clocks.
- Frequency-correction details when meaningful.
- A clearly labeled Reset Pico action.

Adapt the layout to Pico’s existing design and screen sizes. Preserve accessible labels, keyboard navigation, focus visibility and readable status text. Do not rely on color or icons alone.

Adopt the Pi console's information hierarchy and contextual behavior while retaining Pico's native controls, system fonts, flat sections and existing tokens. Do not add Bootstrap, PHP, a new UI framework, external fonts or a new visual identity to firmware. Keep the device identity and diagnostics shared across Station/Transmission and Wi-Fi/Host.

Keep read-only transmitter status visible when signed out. Preserve initial password focus on an unauthenticated page load without stealing focus during later refreshes.

Separate public status from authenticated controls and privileged details. Inspect existing security contracts before deciding which fields may be public. Never expose credentials, session tokens, Wi-Fi secrets or privileged ownership material.

Public visibility does not require public message text, callsigns, saved schedule configuration or owner identifiers. Keep such values unavailable when the admitted public projection does not disclose them. On sign-out or authentication expiry, clear privileged rendered values while preserving local operator drafts behind their existing protections. Use safe text rendering for device-provided strings and retain CSP and request-origin protections.

Avoid replacing or overwriting an operator’s in-progress form entries during polling.

Use restrained live announcements for meaningful state transitions rather than announcing every clock tick or poll. Label browser-local time, Pico-reported UTC and observation time distinctly. A browser clock fallback must not be presented as synchronized Pico UTC. Account for locale, midnight and daylight-saving changes without changing UTC scheduling semantics.

## 5. Present accurate mode-specific information

### WSPR

- Distinguish the configured USB dial frequency from the actual RF transmission frequency.
- Show current or next frame information only when supported by authoritative scheduler state.
- Describe an enabled schedule waiting for its next slot clearly.
- Preserve Pico’s frequency-selection semantics. Do not import Pi-only randomization or frequency offsets.
- Preserve the established example: standalone dial `14095600 Hz` has nominal RF center `14097100 Hz`, with four tones symmetrically spaced by `1.46484375 Hz`. Apply the standalone offset exactly once; externally supplied absolute jobs do not receive it.

### QRSS

- Label the direct RF frequency as Carrier.
- Show the loaded or scheduled message, duration and timing where those values are retained and authoritative.

### FSKCW

- Distinguish Space and Mark frequencies.
- Show their configured shift and applicable timing.
- The browser's reference is Space; Mark is Space plus the positive shift. Show the actual accepted job values when available rather than deriving active output from a newly edited draft.

### DFCW

- Distinguish Dot and Dash frequencies.
- Show the configured shift and actual DFCW timing.
- Represent keyed gaps correctly.
- The browser's reference is Dot, with Dash at Dot plus its positive shift. Direct API jobs may use either valid Dot/Dash frequency orientation; label the supplied values correctly instead of assuming their order. Both elements use the accepted DFCW element duration.

### All message modes

- Distinguish message-internal repeats from recurring schedule occurrences.
- Show scheduled UTC start, recurrence interval, optional expiry and next eligible occurrence where applicable.
- Distinguish armed, running, complete, paused, expired and recovery-required states.
- Do not infer text or character progression from RF activity alone.
- Generic externally loaded RF-event jobs may not retain original message text. Show an honest unavailable value or event-level progress instead of inventing text.
- Support finite test tones and other externally loaded jobs honestly even when no message mode or original source text is retained. Separate prepared drafts, saved schedules, accepted jobs and actual RF observations.
- Treat elapsed time and percentages as estimates unless backed by an authoritative execution cursor. Reaching 100 percent cannot declare completion while JobService still reports running or the connection is unavailable.

If character progression requires additional telemetry, assess a compact compiler event-to-character mapping and an authoritative engine cursor. Implement it only if it fits Pico’s memory and timing constraints. Otherwise deliver accurate coarser progress and record the remaining enhancement as unfinished work.

## 6. Handle frequency correction truthfully

Research which correction values Pico actually supports and exposes.

The current contract uses persistent manual PPM for RF correction; μChrony disciplines UTC only. NTP-derived RF calibration is not supported. Inspect the existing RF-calibration resource and job preparation path. Do not resurrect a retired estimator, add automatic calibration, require new GPSDO work or imply that UTC synchronization measures RF frequency.

Distinguish selected/candidate correction from the correction committed to an accepted job when both exist. Explain application timing accurately.

Do not display unavailable Pi-only estimates, imply a measurement has occurred or show a candidate update as an active-job correction.

Use explicit unavailable states rather than fabricated zero values. Preserve calibration settings and existing correction behavior.

## 7. Implement Reset Pico through the supported restart path

Inspect and reuse the existing restart endpoint and firmware lifecycle. Do not create a parallel reset mechanism or introduce a shutdown action.

At the current baseline, restart is `POST /api/v1/restart` with the closed empty body `{}`, current opaque `If-Match` revision and authenticated management authority. Missing and stale revisions are refused; accepted requests return 202 before a deferred restart. Keep capability negotiation through `features.restart`. Verify the exact current carrier and response-delivery behavior before editing; do not add an invented target envelope to the existing empty-body request.

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
- Label this as a normal device restart, with saved settings retained, rather than a factory reset, credential erase or flash wipe. Explain existing schedule-resumption behavior accurately without introducing a new reboot policy.
- Use a concise product confirmation appropriate to a device reset.
- Prevent duplicate submissions and handle lost responses safely.

During restart, show a reconnecting state. Confirm recovery using a fresh observation and changed boot identity where available. A timeout must remain an unconfirmed outcome.

Preserve the response-acknowledgement/transaction-token boundary: an unrelated response, early disconnect or new owner must not trigger a queued reset. Recheck safe local authority immediately before reset. Retain one-shot submission and the existing bounded reconnection deadline, currently 90 seconds. Confirm the same device and a new boot through the supported authenticated recovery path; page reachability alone is insufficient. Never automatically repeat an ambiguous restart, including after reauthentication or a delayed response.

Expose one shared reset operation through the contextual console and existing settings location as appropriate. Reuse request state so two controls, two tabs or a stale ETag cannot create independent retries. Showing a product confirmation for a user-triggered reset is required UI behavior and is separate from development-session permission requests.

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

Keep this slice focused on item 6. Items 2–5 and 7–18 remain separate work: do not implement syslog, LPF/band selection, amplifier timing, automatic section collapsing, the broader login/takeover redesign, grouped menu anchors, Back to Status links or future engines/calibration as incidental additions. Local UI adjustments necessary for a truthful, usable status console are within scope.

The standing authority covers WsprryPi, WsprryPi-Docs and WsprryPico. WsprryPico is the primary implementation repository; necessary compatibility, shared-contract or operator-documentation dependencies in the other authorized repositories may be completed within this task. Explain and validate each such change. Do not manufacture companion changes when reference reading is sufficient. Preserve each repository's ownership boundaries and Read the Docs publication workflow.

## 9. Validate the implementation

Use documented project commands and retained dependencies. Do not invent commands or perform an unnecessary dependency upgrade.

Start from `engineering/development/README.md` and test registrations. Run `npm test` and `npm run build` in `src/network/bootstrap_web` when those assets change; the build also invokes `scripts/build_operator_assets.mjs`. Maintain source files and regenerate the shipped bundles, embedded assets, manifest and CSP hashes through the established build path. Verify the served artifact, not only an edited source file.

Inspect and extend the relevant existing coverage, including `tests/network_browser_tests.js`, `tests/network_browser_render.js`, `tests/schedule_workflow_browser_tests.js`, message-schedule/frequency tests, device-presentation tests, restart/hostname tests and the consumer-radio/public-status tests. Select tests for behavior and failure paths rather than mirroring the implementation.

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

Check desktop and narrow layouts, signed-in and signed-out views, keyboard operation, clocks in multiple timezones and contextual status changes. Use an existing authorized browser session/profile; if Chrome requires profile selection, use Lee when available.

Capture representative screenshots and distinguish synthetic fixtures from live-device evidence.

Run affected tests, appropriate regression checks, firmware builds, resource-budget checks and documentation validation. Compare firmware RAM, flash, stack and request/polling costs against the baseline.

Use an identified Linux host, authorized Pi, container or Linux CI for C++ validation while the local macOS toolchain remains unqualified; do not repeatedly retry the known broken local compiler. Use documented retained Pico SDK/toolchain inputs for target builds. Record actual ELF/map/UF2 and generated-asset size changes and any headroom concern. Do not weaken firmware size limits or RF/memory reserves to make the UI fit.

Hardware validation is authorized when necessary:

- Identify each intended Pico by USB serial before control or programming.
- Preserve configuration and verify restoration.
- Use idle devices for reset tests.
- Do not interrupt unrelated active jobs.
- If a firmware update is needed, use the supported preserving upgrade path.
- Verify a current, appropriate conducted RF termination before any transmission.
- If physical RF safety cannot be established, complete non-transmitting validation and report the remaining RF-dependent check.
- Keep tests finite and record board, firmware, source, engine, clock and setup.
- Map Pico A/B/C to current physical USB serial and full device ID before choosing a target; record starting firmware/configuration and any connected controller. Verify a current recoverable upgrade/restore path and final inactive/ownership state. Preserve enabled schedules and other settings without unintentionally resuming a transmission on an unverified RF path.
- Keep ecm-mule's network unchanged under the user's existing restriction. Backlog item 1 is complete by operator confirmation; this task does not reopen that validation or require repeating Windows network changes.

Do not claim continuous RF verification or independent SDR decoding from periodic status observations.

## Acceptance criteria for item 6

| Scenario | Required result |
| --- | --- |
| Signed-out or expired session | Bounded read-only status remains usable; privileged fields and all mutations stay protected; initial login focus and drafts are preserved. |
| Idle, disabled, waiting, paused or expired schedule | Accurate current/next context and reason; no invented next job, frequency or transmit authority. |
| Armed/running work, including an RF-off keyed gap | Accepted job remains active; its identity and mode-specific nominal frequencies/progress remain correctly labelled; reset stays unavailable. |
| WSPR, QRSS, FSKCW, DFCW, tone and generic external jobs | Correct units/reference semantics and honest unavailable values; no fabricated text, RF measurements or character position. |
| Fault, clock limitation or recovery barrier | Clear blocker and truthful available actions; no weakening of admission, ownership or recovery gates. |
| Stale, wrong-device, new-boot or out-of-order observation | Obsolete live values and controls are invalidated; old jobs or private data cannot overwrite the current context. |
| Idle authenticated reset | One guarded request through the existing restart lifecycle with settings preserved. The successful path confirms the same device and a new boot; an uncertain response remains explicitly unconfirmed. |
| Reset races, stale revision, logout, cancellation or lost response | Server refuses or cancels ineligible work; no request replay, ownership takeover or false success. |
| Desktop, narrow screen and keyboard/screen-reader use | Readable hierarchy, accessible controls, wrapping values and restrained announcements with preserved focus and drafts. |
| Build, shipped artifacts and target costs | Affected tests/builds pass, shipped assets match source, budgets remain sound and evidence distinguishes fixtures from physical results. |

Treat these as completion criteria rather than optional suggestions. Close a missing telemetry need with an honest supported display and documented limitation when the criterion permits it; do not silently drop required behavior. An external blocker leaves the corresponding criterion and item 6 explicitly unfinished.

## 10. Perform adversarial review and iterate

Perform an adversarial review of the completed change, examining implementation, API contracts, security, runtime cost, persistence, lifecycle races and UI interpretation.

Maintain a working finding ledger with identifier, severity, affected source/behavior, reproduction or reasoning, correction, regression evidence and closure status. Summarize closures in the final report. Use an independent reviewer when available and authorized; otherwise perform a distinct adversarial self-assessment and identify it accurately. Review both source and shipped behavior, including any companion changes.

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

Every substantive correction must be followed by the affected tests and another adversarial assessment of the resulting state, including new regressions introduced by the fix. Do not treat the first review, a list of intended fixes or a passing unrelated suite as closure. Resolve actionable task findings before final commit/push; report any blocked finding explicitly and leave item 6 incomplete when it prevents acceptance.

State whether the assessment was self-review or independently performed. Do not claim independent review without an actual independent reviewer.

## 11. Update documentation and the TODO list

Update current operator and engineering documentation to explain the delivered behavior directly.

Update the existing numbered item 6 under UI in `engineering/development/consolidated-backlog.md`. Preserve all item numbers and unrelated completion states. Do not add another status-console entry.

Keep the item's reference accurate as this prompt is maintained or retired. Mark item 6 complete only when its acceptance criteria are satisfied. Keep any remaining selected enhancement explicitly unfinished, with an accurate description. Do not create duplicate entries or leave completed work presented as pending.

Keep this prompt linked while work remains unfinished. At completion, apply the repository's execution-prompt retirement rules: consolidate needed technical content into maintained documentation and repair the backlog reference if the completed prompt is removed. Use concise current-product prose; do not create an archive of execution narratives. Keep credentials, private captures and generated firmware out of source control; publish only necessary sanitized documentation images under the existing image policy.

## 12. Commit, push and report

Inspect the final diff and repository state. Stage only this task’s files.

Commit and push the completed task changes to devel using the established workflow. Preserve concurrent work, do not force-push and do not bypass protections.

Commit this task's final prompt/backlog disposition, source, generated browser artifacts, tests and documentation in each repository actually changed. Do not stage unrelated files or rewrite shared history. If the remote advances, reconcile it using normal safeguards, rerun affected checks and push the validated result. Necessary Git operations are already authorized for execution of this assignment.

Inspect relevant CI results, correct task-related failures and verify the final remote commit identity. Recheck pushed content, branch parity, the final working tree and any deployed device state. A failed push, blocked required check or unclosed acceptance issue is not completion; continue independent repairs and report the actual remaining blocker.

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

## Wsprry Development Session — Standing Execution Authority

### 1. General Authority

For this Codex session, you have standing authorization to perform all operations reasonably necessary to complete the assigned task within the systems and repositories listed below.

This authorization supplements permissions already granted. It is intended to minimize unnecessary interruptions, repeated approval requests, and routine clarification questions.

Operate autonomously. Do not request confirmation for actions explicitly authorized here unless a higher-priority policy or technical permission boundary requires it.

* Make reasonable technical decisions independently.
* Investigate, implement, test, debug, correct, and retest without asking permission at each stage.
* Do not ask for permission to inspect files, run commands, access authorized hosts, restart services, or execute tests.
* If an approach fails, investigate and attempt reasonable alternatives.
* Prefer established project conventions and existing architecture.
* Do not repeatedly ask questions already answered in the current session, repository documentation, or prior execution results.
* Continue through intermediate problems without stopping unnecessarily.
* Report significant decisions and results, but do not turn ordinary progress updates into requests for approval.
* This authority applies to the assigned task and its reasonable dependencies, not unrelated projects or operations.

### 2. Authorized Repositories

You have full development and Git operational authority over:

* WsprryPi
* WsprryPi-Docs
* WsprryPico

Authorized operations include:

* Read, create, modify, rename, and delete project files.
* Refactor code and modify build configurations.
* Install, remove, and update dependencies.
* Build, compile, test, package, and execute software.
* Create and modify branches, commits, tags, and pull requests.
* Fetch, pull, merge, rebase, cherry-pick, and push changes.
* Run, inspect, and troubleshoot CI workflows.
* Review CI logs, resolve failures, and rerun workflows.
* Update project documentation and tests as appropriate.
* Push validated changes to the configured project remotes.

Use normal Git safeguards. Do not overwrite remote history, force-push shared branches, disable branch protections, or delete remote repositories without separate authorization.

### 3. Docker and Container Infrastructure

You have authority to manage Docker infrastructure related to the authorized projects.

This includes:

* Start, stop, restart, create, inspect, modify, and remove containers.
* Build, rebuild, pull, and remove images.
* Create and modify Dockerfiles and Compose configurations.
* Manage networks, volumes, environment variables, and mounts.
* Execute commands inside containers.
* Inspect logs, processes, resource consumption, and network connectivity.
* Replace or recreate containers when needed.
* Install dependencies and modify container configurations.

Preserve persistent data and configurations that are not safely reproducible. Destruction of unrelated containers, persistent volumes containing unique data, or unrelated host resources requires separate authorization.

### 4. Authorized Raspberry Pi Hosts

You have full operational authority over the following hosts:

* wspr5
* wspr4
* wspr2
* wspr1

You may use SSH and other existing management interfaces to:

* Inspect and modify operating-system and application configurations.
* Install, upgrade, remove, compile, and execute software.
* Start, stop, enable, disable, restart, and modify systemd services.
* Modify service definitions, scripts, configuration files, and scheduled jobs.
* Inspect logs, processes, networking, permissions, and hardware interfaces.
* Update deployed project files and binaries.
* Reboot hosts when necessary.
* Perform hardware and software diagnostics.
* Configure and test GPIO, I2C, SPI, UART, USB, and other supported interfaces.
* Collect diagnostic data and logs.
* Deploy and validate WsprryPi and WsprryPico components.

Treat these systems as an authorized development and testing environment.

Preserve unrelated services, access credentials, and persistent data.

### 5. Authorized Raspberry Pi Pico Devices

You have authority to control, program, and test:

* Pico A
* Pico B
* Pico C

Authorized operations include:

* Compile and build firmware.
* Install, replace, and update firmware.
* Reset, reboot, and recover devices.
* Enter and exit bootloader modes.
* Use supported USB, serial, SWD, and debugging interfaces.
* Inspect and modify device configuration.
* Test GPIO, PIO, DMA, RF generation, timing, and peripheral interfaces.
* Execute functional, integration, and regression tests.
* Capture and analyze device output.
* Repeat firmware deployment and testing cycles as necessary.

Identify the intended physical device before programming it.

### 6. RF Transmission Authority

You are authorized to initiate and control RF transmissions using the local WsprryPi and WsprryPico development equipment.

Before enabling transmission, verify that the intended transmitter has a valid, appropriate RF termination.

Permitted test configurations include:

* A suitable attenuator and dummy load.
* A verified attenuation path connected to the SDR.
* Another verified, appropriately terminated conducted RF test configuration.

Do not assume a safe RF path solely from prior documentation, software configuration, or a previous test.

Validate the actual connection or use reliable, current evidence of the physical RF configuration.

Once the RF path is verified, you may:

* Initiate and terminate transmissions.
* Set and adjust test frequencies, tones, and timing.
* Execute repeated transmission tests.
* Measure frequency accuracy, stability, and timing.
* Test calibration and frequency-correction routines.
* Exercise transmit scheduling and control functions.
* Perform unattended test cycles within the verified configuration.

Do not intentionally transmit into an antenna or unverified RF load under this standing authorization.

If the physical RF path cannot be verified, continue all non-transmitting work and request confirmation only when transmission becomes necessary.

### 7. SDR Authority — wspr5

You have full operational authority over the SDR connected to wspr5.

Authorized operations include:

* Start, stop, and configure SDR software.
* Select frequencies, bandwidths, gains, and sample rates.
* Record and analyze IQ data.
* Capture spectra, waterfalls, and diagnostic measurements.
* Measure frequency error, stability, modulation, and timing.
* Execute automated receiver tests.
* Integrate SDR measurements into development and CI test workflows.
* Restart SDR-related services and processes as necessary.

### 8. GPSDO Authority — wspr5

You have authority to operate and configure the GPS-disciplined oscillator associated with wspr5.

Authorized operations include:

* Inspect and modify supported operating configurations.
* Read status, lock state, and diagnostic measurements.
* Select and configure supported reference outputs.
* Perform reference-frequency measurements.
* Use the GPSDO as a frequency and timing reference.
* Execute calibration, verification, and stability testing.
* Restart device interfaces or supporting services as necessary.
* Collect logs and measurement results.

Preserve known-good configuration settings when practical.

Do not perform irreversible hardware calibration or persistent reference changes without a verified recovery procedure.

### 9. Computer, Browser, and Developer Tools

You are authorized to use available computer-control and browser capabilities for development, testing, research, and diagnostics.

This includes:

* Controlling the integrated browser.
* Using browser developer tools and JavaScript consoles.
* Inspecting network requests, responses, logs, and browser storage.
* Running browser automation.
* Accessing authorized project management and development websites.
* Using HTTP clients, APIs, and command-line network utilities.
* Downloading required documentation, development tools, and dependencies.
* Using web-based development, debugging, and diagnostic interfaces.

Use existing authenticated sessions and credentials where supported and authorized.

Do not disclose credentials or transmit unrelated private information.

### 10. Autonomous Execution and Recovery

When executing an assigned task:

1. Inspect the relevant state and available documentation.
2. Determine the required implementation and validation steps.
3. Execute the work using the standing authority above.
4. Diagnose and correct failures independently.
5. Repeat build, deployment, and testing cycles as needed.
6. Validate the final result using available tools and hardware.
7. Update relevant documentation and tests.
8. Commit and push validated changes when consistent with the assigned task and established repository workflow.
9. Report the final result, including important findings, changes, validation evidence, and any unresolved problems.

Do not stop simply because an intermediate command, build, test, deployment, or diagnostic attempt fails.

Do not ask which reasonable diagnostic step to attempt next. Select and execute it.

### 11. When Human Confirmation Is Required

Interrupt the user only when:

* An action exceeds the systems or scope authorized in this document.
* Required credentials, physical access, or permissions are unavailable.
* A higher-priority safety or security policy requires confirmation.
* An action would irreversibly destroy unique or unrelated data.
* A proposed action would overwrite protected Git history or bypass branch protections.
* RF safety cannot be established before a required transmission test.
* An irreversible hardware operation cannot be safely recovered.
* A material product, architecture, or requirements decision cannot reasonably be derived from existing instructions.
* The operation presents a meaningful risk that cannot be mitigated within this authority.

For ordinary engineering ambiguity, choose a reasonable course consistent with project conventions and document the decision.

When a blocker requires confirmation, complete any remaining independent work before asking.

### 12. Communication Expectations

Operate with minimal interruption.

* Do not request permission for routine authorized operations.
* Do not repeatedly seek reassurance that a chosen implementation is acceptable.
* Do not pause after each intermediate step.
* Do not convert progress reports into approval gates.
* Provide concise progress updates for significant milestones.
* Surface material blockers, safety concerns, or irreversible decisions promptly.
* At completion, provide a concise summary of work performed, verification evidence, Git state, deployed devices, and outstanding issues.

Default operating principle: If the action is necessary for the assigned task, within the explicitly authorized scope, technically reversible or reasonably safe, and not prohibited by a higher-priority policy, proceed without asking.
