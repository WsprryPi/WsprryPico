# Item 29 execution prompt: Hardware settings saves while standalone operation is suspended

## Activation, scope, and starting state

This is a saved execution prompt for unfinished backlog item 29. Saving or linking it does not execute it. Execute only when the user explicitly invokes this task. The standing authority below applies to that execution and its reasonable dependencies. Implement this item only; adjacent backlog items have independent prompts. Reinspect the current tree because earlier items may have changed shared files by the time this prompt is invoked.

Work primarily in `/Users/lbussy/GitHub/WsprryPico`. Companion repositories `/Users/lbussy/GitHub/WsprryPi` and `/Users/lbussy/GitHub/WsprryPi-Docs` may be changed where this task requires it. Read applicable AGENTS.md files, README.md, CONTRACT.md, engineering/architecture.md, engineering/development/README.md, and the relevant current contracts before implementation. Inspect branch, HEAD, remotes, divergence, worktrees, and tracked/untracked changes separately in every affected repository. Preserve user work, including other saved prompts and unrelated backlog edits. Use the established branch workflow, with a `codex/` branch where appropriate. Do not reset, stash, delete, or include unrelated work to simplify the task.

Inspect the actual implementation and production call paths before deciding on changes. Paths below are discovery starting points, not proof of current behavior. Read `src/network/web/DESIGN.md` and the corresponding bootstrap UI conventions where relevant. Prefer existing components, validation, transaction boundaries, and generated-asset tooling. Keep operator documentation direct and impersonal, and publish project documentation through Read the Docs. Do not introduce GitHub Pages infrastructure.

## Objective and reported state

Investigate and fix the inability to save Si5351, GPS, PPS, LED, and button pin/configuration settings when Transmitter status says “Standalone operation is suspended. Future WSPR needs a saved dial before schedules can be enabled.” The reported state has no job, inactive RF output, and an available owner. Reproduce and identify the actual blocking condition; the status message alone does not establish the cause.

Allow otherwise valid hardware settings saves independently of a saved WSPR dial or schedule enablement while preserving access, ownership, output, pin-allocation, and validation checks. Make actual refusals specific and actionable. Do not fix this by inventing a saved dial, enabling schedules, resuming standalone operation, globally removing suspension guards, or weakening validation.

## Root-cause investigation

Trace the production UI save from displayed lock/disabled state and HTML form validation through payload creation, authority and revision checks, handler admission, portable validation, journal write, response serialization, and readback. Start with `src/network/web/app.js`, `saved-progress.js`, `config-validation.js`, GPS/Si5351/pin modules, `src/standalone`, provisioning handlers, and the current shared configuration contracts. Identify the actual resource/transaction used; do not infer the write boundary from UI section labels.

Read the current configuration-updates, saved-progress, pin-assignment, Si5351, GPS/PPS, browser API, and management-carrier contracts, plus `docs/configure.md`. The current documentation states independent WSPR and radio-pin saves and says a pin save may succeed while a schedule draft is invalid; confirm the implementation honors that promise. Inspect the production Pi client/coordinator and USB/network management consumers before changing shared admission or semantics.

Build a reproducible state matrix: suspended/not suspended; saved dial absent/present; valid/invalid unsaved WSPR draft; no schedules/disabled/enabled schedules; no job/accepted or running job; owner available/held by another controller; unlocked/expired login; healthy/unhealthy storage; restart already latched. Record exact request/response code and actual durable result for each relevant case. Establish whether the failure occurs before any request, in browser-only validation, in whole-document construction, at runtime admission, or in persistence. Distinguish saved state, active boot hardware, unsaved draft, and status interpretation.

## Implementation and acceptance

1. Make the smallest coherent fix at the demonstrated boundary. An independent hardware save must validate and persist its own complete hardware allocation without requiring an unrelated valid WSPR draft, saved dial, schedule enablement, or automatic resume. Preserve omission semantics and unrelated saved fields exactly. Never manufacture a full document from stale defaults to bypass validation.
2. Maintain atomic validation of RF engine, Si5351 I²C/loopback resources, GPS UART/PPS/capture resources, LED, button, amplifier/filter pins, and all shared GPIO conflicts. Cover disabled/unassigned resources and both engine selections. Reject malformed, extra/missing, wrong-type, unsupported, out-of-range, and contradictory values before any write.
3. Preserve management authority, identity/boot/profile bindings, optimistic revision checks, owner/output restrictions, restart/output-inhibit latching, and immutable boot-applied hardware semantics, including A/B/A saves. A save does not program hardware, establish timing quality, grant ownership, or make RF ready. Keep accepted/running jobs protected under the actual documented policy.
4. Preserve suspended state and absence of a saved dial when saving hardware. Schedules must remain disabled or otherwise unchanged as specified by the contract. Conversely, WSPR enable/apply must still refuse missing prerequisites. Do not silently normalize or erase invalid unrelated drafts; preserve them for the operator to correct separately.
5. Return precise, actionable save errors based on the authoritative refusal: authentication, conflicting owner/job, active output, GPIO/resource conflict, invalid field, stale revision/identity, unhealthy storage, or required restart as applicable. Do not replace every error with the suspension message, expose secrets, or misclassify a successful save with pending restart as a failure.
6. Preserve bounded reply behavior, cancellation, uncertain-outcome reconciliation, and explicit readback/review before another save. Exercise committed writes with lost replies, session expiry during admission, concurrent saves, stale target/revision, reboot, and failed journal writes. Prove rejected requests leave durable settings unchanged and successful saves survive restart.
7. Add meaningful regressions using production handlers and journals, plus the actual UI workflow. Demonstrate each reported hardware group saves with no saved WSPR dial, no job, inactive output, available owner, and appropriate authentication. Test mixed valid hardware/invalid WSPR drafts and the reverse, ownership/output refusals, invalid shared allocations, and preserved disabled scheduling. Use simulated output for non-transmitting guard tests where possible.
8. Update paired consumers, strict validators, adapters, and current documentation if shared semantics change. This task concerns shared settings/admission behavior: run both mandatory actual network and USB source-pair suites for the intended candidates before completion, even if the first fix appears browser-only. Do not leave a companion mismatch unresolved or weaken a client to make integration green.

Adversarial targets include fixing only the disabled button while the server still refuses, globally bypassing scheduler admission, enabling schedules as a side effect, clobbering unrelated saved settings from a partial draft, accepting invalid pins while idle, changing boot hardware immediately, and reporting a committed lost reply as safely retryable. Completion requires a demonstrated root cause, independently valid durable hardware saves in the reported state, specific refusals for real blockers, and successful paired production integration.

## Validation and coordinated-source gate

Derive executable commands from the current development guide, CMake registrations, package scripts, and CI recipes; inspect opt-in tools before running them. Do not invent commands or treat empty test selection as success. Run meaningful affected host/browser checks, source and shipped-asset checks, generated-asset freshness, documentation/link checks, and `git diff --check`. Build affected firmware with the retained pinned SDK/toolchain dependencies where relevant. Exercise actual rendered interfaces with the production browser fixture, retaining useful screenshots and sanitized evidence in an ignored work area. Visual claims require rendered inspection. Reversible styling alone does not need tests that merely duplicate CSS; use behavior and geometry checks where they catch the actual failure.

If advertised capabilities, protocol-facing interfaces, schemas, limits, units, descriptors, carrier support, or session policy change, inspect the producer and every affected Pi consumer before implementation. Coordinate advertisements, descriptors, strict validation, runtime consumers, serialization, generated assets, paired adapters, and documentation in the same task. Preserve one current Control/1 prerelease representation, fixed major/identifier/namespace 1 before the explicit first stable transition, closed validation, identity/revision bindings, refusal before mutation, and independent WTP, transport/authentication, and storage versions. Do not add historical views, downgrade paths, permissive validators, or stale companion substitutions.

When that coordinated completion gate applies, both actual production source-pair suites must pass for the intended candidate trees, even if the change appears specific to one carrier. Use the checked-in WsprryPi `.github/workflows/debian-non-hardware.yml` recipes with the actual candidate Pico source and explicitly selected pinned dependencies:

- `wtp-network-loopback`: `wtp-network-runtime-test`, `wtp-network-interop-test`, and `wtp-config-interop-test`, including current required source-selection and routing checks.
- `wtp-usb-management-pair`: build the actual Pico `usb_management_driver`, `wtp-usb-pair-client-build`, and `wtp-usb-management-test`, and run `WsprryPi-UI/tests/wtp_usb_pair_test.js` through the production Pi/Pico pair.

Follow any broader mandatory acceptance requirements in the current CI execution contract. Record exact commands, results, both source revisions, tested uncommitted differences, dependency identities, and relevant CI links. Failed, cancelled, timed-out, skipped, or unavailable required checks remain unresolved. Fix inherited companion mismatches that block validation; do not claim completion with a deferred companion fix or present an unmerged feature branch as delivery on `devel` or `main`. For a strictly presentation-only change, document why the protocol gate does or does not apply and run the affected production browser/asset checks; do not change a contract merely to simplify the UI.

Hardware-free deterministic validation is the default. These tasks do not inherently require RF transmission. If device deployment is necessary, verify physical identity, snapshot settings and installed image/bundle references, and use `scripts/usb_installer.py` with the exact generated developer bundle, same-board transaction, and postboot verification. Retain the bundle, preserve settings, and restore or explicitly document final device/service state. Never bypass a stale reference by editing identities or deleting receipts. Any necessary RF test must first establish the actual currently terminated conducted path under the authority below; use finite tests and verify inactive output on handback. Report host, build, CI, physical USB, installation, timing, and RF evidence separately.

## Adversarial review and closure loop

Perform an adversarial review. Examine the implementation, requirements, production paths, generated assets, tests, documentation, and claimed evidence. Challenge the task-specific failure cases above and the assumptions behind apparent success. Maintain a concise issue ledger with severity, evidence, corrective action, and a closure check.

Iterate through issues, close them with evidence, and run another adversarial assessment. Fix every actionable in-scope finding, rerun affected checks, and reassess the revised final work. Repeat until no actionable findings remain. A second assessment must actively seek new failures rather than repeat the first review. Do not close missing evidence or failed required validation as accepted risk merely to finish. Complete independent work before reporting a genuine blocker. This instruction calls for adversarial assessment; it does not require spawning additional agents.

Update current operator/engineering documentation only where behavior warrants it. Preserve stable backlog numbers. Mark this item complete only when its acceptance criteria and required checks pass. At completion of the invoked task, consolidate durable technical information, remove this temporary execution prompt, and repair its backlog reference in accordance with the repository cleanup rules; do not retain a completed prompt solely because a checklist links to it.

## Delivery: commit, push, then report

When done, commit and push. Then report. This instruction authorizes Git delivery during execution of this prompt, not while it is merely being written or linked.

After adversarial closure and successful required checks, inspect the complete final diff and repository state. Stage only task-owned changes, commit with a focused message, and push to the configured intended remote under the established workflow. Preserve unrelated staged or unstaged work; do not include it accidentally. Do not force-push shared history, bypass protections, or publish a release as an incidental step. Push any required companion changes to their intended refs and report integration/merge status accurately. Check required CI for the pushed revisions, resolve failures, and rerun affected validation after fixes. Verify the tested sources correspond to the final pushed commits, identifying any documentation-only differences explicitly.

Report the user-visible result, root cause or design decision, files/repositories changed, adversarial findings and their closure, exact commands/results, source-pair evidence where required, CI links, commits, pushed branches/remotes, final tracked/untracked state, deployment/restoration state, and remaining limitations. Say explicitly when no hardware was used. If delivery or required checks are blocked, report the actual incomplete state and cause rather than claiming success.

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

You have authority to manage Docker infrastructure related to the authorized projects. This includes:

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

You have full operational authority over the SDR connected to wspr5. Authorized operations include:

* Start, stop, and configure SDR software.
* Select frequencies, bandwidths, gains, and sample rates.
* Record and analyze IQ data.
* Capture spectra, waterfalls, and diagnostic measurements.
* Measure frequency error, stability, modulation, and timing.
* Execute automated receiver tests.
* Integrate SDR measurements into development and CI test workflows.
* Restart SDR-related services and processes as necessary.

### 8. GPSDO Authority — wspr5

You have authority to operate and configure the GPS-disciplined oscillator associated with wspr5. Authorized operations include:

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

You are authorized to use available computer-control and browser capabilities for development, testing, research, and diagnostics. This includes:

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
