# Item 11 execution prompt — Page-wide submission feedback and concurrency recovery

Status: saved execution prompt; not started. Saving, printing, reviewing or committing this document does not execute it. Execute only when explicitly assigned. Use the full standing execution authority below for that session.

## Objective

Research and fix the reported behavior in which repeated button submissions may overlap and leave the controller unresponsive. Treat the race condition as a hypothesis until reproduced or supported by evidence. After an accepted submission, visibly dim/dither the entire page immediately and optionally show a spinner, with a clear operation message so the operator knows to wait. Prevent duplicate and conflicting actions through the actual action authority, recover correctly on every outcome, and preserve emergency control and uncertain-save recovery.

The primary scope is the WsprryPico operator browser interfaces and their real adapters. Inspect the corresponding WsprryPi member-management path when involved; repair demonstrated companion causes within the supplied authority. Do not turn this into an unrelated UI redesign or a protocol-version migration.

## 1. Orient and reproduce

Read current AGENTS.md, README.md, CONTRACT.md, engineering/architecture.md and documented development commands. Inspect branches, upstreams, dirty work and submodules in affected repositories. Preserve unrelated work. Read the [browser-pages contract](browser-pages.md), [session recovery](session-recovery.md), [web-service behavior](web-service.md) and current shared control policy before implementation.

Inventory the actual rendered pages, button/form handlers and shared request/action helpers, including station and Wi-Fi/host areas, login/logout/takeover, saved-state review, setup receipts, reset, firmware/disconnect flows, and relevant USB/network or Pi-hosted routes. Distinguish a frozen browser, stale busy flag, request-queue deadlock, exhausted sessions, stalled firmware service and transmitter ownership before diagnosing the controller lockup.

Reproduce with bounded rapid double-clicks, touch taps, Enter/Space and form submission, different buttons, modal actions, slow/lost replies, concurrent polling and disconnect/reconnect. Trace exact requests and action/session/generation ownership. Record the trigger, actual effect and affected source/route; redact credentials, session keys and proofs. Inspect existing shared action serialization and lock/logout behavior before adding another lock. If the original failure is not reproducible, state that and still deliver deterministic duplicate-prevention and recovery coverage without claiming a proven root cause.

## 2. Specify the operator experience

Use the Impeccable workflow and incumbent visual conventions. On an accepted asynchronous button/form submission, enter busy state synchronously before the first await or dispatch. Dim/dither the whole visible page, including header and settings, while keeping a legible foreground operation message. An optional spinner is secondary feedback; text must explain what is happening. Respect reduced motion and avoid flashing effects. Keep status legible rather than implying the device has frozen.

Define which actions acquire the global busy state. Mutations and explicit asynchronous operator actions must be covered consistently; local validation failure must not strand an overlay. Pure disclosure, password-visibility and local navigation controls do not need network busy behavior. Background status polling must not repeatedly dim the page or compete for the operator-action lock.

Block duplicate/conflicting activation through pointer, touch, keyboard, form submission, programmatic handlers and already-queued events. CSS pointer-events or a disabled submit button alone are insufficient. Use native disabled/inert behavior and an accessible busy/live announcement as appropriate, preserve focus intentionally, and restore the previous eligibility state rather than enabling every control blindly. Explain busy/refusal states without dropping drafts or clearing inputs.

Specify and test stacking with native dialogs, scrolling, narrow screens, both existing themes and assistive technology. Keep explicitly required stop/abort controls accessible and route them through a safe preemption policy. A full-page overlay must never make urgent shutdown unavailable. Preserve established lock/logout gating and bounded recovery; do not expose a generic bypass that can replay a mutation. Browser refresh/back/close cannot prove a dispatched operation was canceled.

## 3. Fix the action lifecycle and underlying race

Prefer one shared operation coordinator integrated with the existing authority rather than per-button booleans or nested independent mutexes. Acquire atomically before dispatch. Refuse additional conflicting intents with clear feedback instead of queueing stale operator mutations. Internal multi-step operations must retain one outer ownership token without deadlocking when they call shared helpers.

Define states for idle, pending, confirmed, refused, uncertain and recovering, plus deliberate emergency preemption where required. Bind completion to operation token, device/boot target, session epoch and configuration revision as applicable. A late result from an old operation must not clear a newer operation's busy state, restore a retired session, change the selected device or overwrite current drafts.

Release presentation state on all settled outcomes, including thrown errors, validation refusal, malformed replies, authentication failure, aborted fetch and page lifecycle changes. Use a bounded timeout/deadline consistent with the real adapter. Do not merely clear the overlay and re-enable writes while a server-side mutation may still be outstanding. On uncertain outcome, show the existing authoritative readback/receipt workflow; allow only the actions justified by that state. Retain a persistent result/recovery notice after removing the busy overlay.

Preserve sent-once transactions, original receipt bytes, replay protections, revision checks and uncertain-save semantics. No automatic mutation retry, blanket page reload, credential persistence or new session allocation per click. If the request was accepted but the reply was lost, do not report failure as proof that nothing changed. A fetch cancellation does not undo a durable write or accepted RF job.

Prevent background read results from overwriting edits or clearing action state. Coordinate polling without holding request resources needed by the action itself; coalesce or pause only where justified and resume after correct reconciliation. Diagnose server/client starvation or lock-order problems if evidenced. Keep backend target/revision/ownership checks authoritative, including for multiple tabs, clients and carriers; browser serialization is not a security or cross-client concurrency boundary.

Emergency stop must invalidate obsolete continuations without falsely claiming cancellation of completed writes. Preserve the exact supported shutdown semantics and ensure a late normal action cannot restart output or dismiss recovery. Do not weaken firmware guards or suppress exceptions merely to remove the visible lockup.

## 4. Preserve current contracts and integration

Prefer a presentation/action-lifecycle fix without schema changes when sufficient. Inspect actual production Pi/Pico consumers before any protocol-facing change. The shared settings/control contract supports one current major. Read engineering/protocol/control-policy.json and its checker: before its first stable release, evolve the coordinated current Wsprry-Control/1 schema within major 1 and /api/control/v1/, without historical control views. If the release state changes, follow its stable transition rules. Keep independently versioned WTP, authentication/transport and storage formats separate.

Maintain exact closed validation, shape-before-access, advertised/returned consistency and rejection of unsupported/superseded versions, extra/missing fields, wrong types and invalid target/revision bindings before mutation. No fallback to older peers or relaxed validators. Update actual companions, generated assets, fixtures and documentation together whenever interfaces change.

For affected capability/API/protocol behavior, both production network and USB integration suites must pass on the intended source pair. Follow WsprryPi .github/workflows/debian-non-hardware.yml recipes for wtp-network-loopback and wtp-usb-management-pair, including wtp-network-runtime-test, wtp-network-interop-test, wtp-config-interop-test, actual Pico usb_management_driver, wtp-usb-pair-client-build, wtp-usb-management-test and WsprryPi-UI/tests/wtp_usb_pair_test.js. Select source revisions and pinned dependencies explicitly. A mock-only pass, stale companion, skipped/canceled/timed-out test or unmerged required companion update does not satisfy this gate.

## 5. Validate the complete behavior

Add deterministic production-handler/browser tests proving exactly one accepted mutation under repeated activation, no conflicting-button dispatch, no nested-action deadlock, correct token/epoch behavior, no leaked busy state, and safe uncertainty/recovery. Cover login/logout/takeover, reset/reboot, setup receipt continuation, save/readback, local invalid input, network timeout, delayed success after timeout, malformed replies, multiple tabs and pending polling. Preserve drafts, saved-state comparisons, section navigation, Top behavior and access gating.

Use controlled delayed responses and real production scripts rather than arbitrary sleeps or a separate test-only coordinator. Verify keyboard/touch behavior, dialog overlay stacking, focus, live announcements, reduced motion and responsive/light/dark rendering. Confirm that visually blocked controls cannot dispatch and that required emergency/recovery actions remain usable. Bound visual review passes while fixing all actionable correctness findings.

Run documented affected browser, adapter, resource and firmware checks as appropriate to changed files; regenerate assets through the checked-in tools and verify served assets match sources. Demonstrate the reported reproduction is fixed when available, and distinguish that from synthetic regression coverage. Record exact commands/results, source pairs and tested dirty changes. No RF transmission is required merely to test a busy overlay; use inhibited or non-transmitting validation wherever sufficient.

If deployment is needed, identify the intended physical device and preserve settings. Use scripts/usb_installer.py with its generated developer bundle, transaction, same-board image reference and postboot verification. Retain the exact bundle; do not substitute direct picotool programming. Reconcile stale references only with the original bundle and exact same-board comparison through upgrade --installed-bundle. Restore services and test state, and report final device/RF state. Any necessary RF test must satisfy the standing authority's current termination checks.

## 6. Adversarial review, fixes and reassessment

Perform an adversarial review of the complete fix. Challenge synchronous reentry, keyboard bypass, queued events, nested ownership, late completion, timeout uncertainty, stale session/device binding, polling starvation, emergency access, backend concurrent writers, lost receipts and misleading success or idle indications.

Record findings with severity, evidence, corrective action and closure criteria. Fix each actionable issue, rerun affected checks, close it with evidence, then run another fresh adversarial assessment. Repeat until actionable issues are resolved. Do not treat a deferred required test or relabeled defect as closure. Claim independent review only if it occurred; report genuine external blockers after completing independent work.

## 7. Document, commit, push and report

Update the maintained browser/action/recovery documentation with actual behavior, cause findings and validation limits. Keep public documentation on Read the Docs. Mark UI item 11 complete only when the agreed behavior and required checks pass. Consolidate enduring content and retire this completed execution prompt with reference repairs. Preserve unrelated checklist entries and numbering.

Review the final diff, run git diff --check and applicable documented checks, commit only task changes, and push to verified intended remotes. Publish required first-party UI submodule commits before parent pointers. Deliver required companion changes on the intended paired refs, inspect applicable CI, resolve failures and verify remote parity. Use normal Git safeguards; preserve unrelated work.

Report the diagnosed cause or remaining uncertainty, page-wide busy behavior, actual concurrency/recovery fix, adversarial findings and closure, exact checks and CI links, source/commit identities, pushed branches, final working-tree/device state and unresolved limitations. Distinguish visible feedback from prevention of duplicate mutation and from proof of controller responsiveness.

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
