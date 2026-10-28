# Item 5 execution prompt — Optional amplifier settling and lead/tail timing

Status: saved execution prompt; implementation not started. Saving, reviewing or committing this document does not execute it. Execute only when explicitly assigned. The complete standing execution authority below applies to that assigned session.

## Objective and scope

Implement optional, bounded amplifier settling and lead/tail timing around complete RF jobs, using the existing amplifier-enable output and member-local execution authority. Deliver coordinated configuration, persistence, capability negotiation, companion management, accurate status, tests and documentation. Defaults must preserve existing immediate amplifier-enable behavior.

This is item 5 in the [consolidated backlog](consolidated-backlog.md). LPF/band-selector control is item 4; Si5351, envelope shaping, RF warmup, amplifier drive regulation, new RF engines and PCB design remain separate work. Integrate with filter sequencing if it exists when execution begins, but do not require item 4 to be implemented or execute its prompt. No delay setting may introduce an unannounced RF interval or authorize a transmission.

## 1. Inspect the baseline and define the timing contract

Read applicable AGENTS.md files, README.md, CONTRACT.md, engineering/architecture.md and documented development/test recipes in every affected repository. Inspect branches, upstreams, staged/unstaged changes and submodule state; preserve unrelated work. Inspect the [amplifier-enable implementation contract](amplifier-enable.md), [pin-assignment contract](../pin-assignment-contract.md), [shared transmitter contract](../transmitter-application-contract.md), job/lease lifecycle, scheduler, PIO/DMA sink, clock admission, emergency recovery, hardware/configuration/progress schemas and actual Pi clients.

The baseline asserts enable immediately before physical RF, holds it through one complete finite job including keyed gaps, and deasserts before fallible DMA cleanup. Separate jobs, including Type 2/3 frames, deactivate between them. Confirm these facts in current code before modifying them. Preserve the distinction between scheduled RF onset, amplifier activation, RF completion and final safe cleanup.

Specify what settling, lead and tail mean before implementing fields. Prefer a small model where lead is the guaranteed amplifier-enabled, RF-off interval before RF onset and satisfies the amplifier's declared minimum settling requirement. If settling is separately configurable, define its exact relationship to lead, reject insufficient lead and avoid accidentally adding the same delay twice. Tail is the optional amplifier-enabled, RF-off dwell after confirmed normal RF completion. Do not use modulation gaps as individual lead/tail boundaries.

Choose and justify explicit finite ranges, integer units, resolution, rounding and timer error bounds from actual hardware requirements and current lifecycle budgets. Zero defaults reproduce the existing ordering. Reject negative, fractional where unsupported, nonfinite, overflowing and out-of-range values; avoid implicit signed/unsigned conversions. Do not invent measured amplifier readiness or numeric guarantees without evidence. Resolve ordinary engineering choices autonomously and document them.

## 2. Implement bounded member-local execution

Use one explicit state machine under the existing RF-chain owner, with observable preparation/lead, RF-running, normal-tail, inactive and failed/recovery states as needed. Keep the portable policy separate from Pico SDK/timer adapters. Bound work and storage; do not sleep, allocate, log, perform network/CYW43 operations or wait for another core in launch interrupts.

Freeze the selected boot pin/polarity and accepted timing policy for the complete job. LOAD and validation never energize the amplifier. Only an admitted, owned execution may schedule its lead interval. Keep RF physically inhibited during lead and tail. The application must not misreport amplifier-enabled lead/tail as actual RF activity or falsely announce idle/cleanup completion while an output remains energized.

Calculate deadlines with checked arithmetic and use a monotonic basis for elapsed intervals. Revalidate applicable clock/epoch, ownership, stop/inhibit and hardware conditions before amplifier activation and again before RF launch. Handle clock correction, stale timer callbacks, cancellation/rearm races, immediate jobs and already-too-late requests explicitly. A late scheduled job must fail safely rather than shorten required settling, shift its RF start silently or transmit early. Never block another required safety action to complete a delay.

Do not extend, shorten or alter encoded RF payload timing. Account for lead and tail in preparation deadlines, resource reservation, watchdogs, cleanup timeouts, ownership and terminal reporting. Preserve existing complete-job ceilings and advertised limits; if a closed contract must change, version and coordinate it. Define how back-to-back schedules and Type 2/3 pairs handle insufficient idle time. Do not overlap separate jobs or silently merge their amplifier intervals.

Where filter selection exists, confirm RF/amplifier inactive before switching, complete filter settling before amplifier lead, and keep the filter stable through RF and any safe normal tail. Distinguish filter settling from amplifier settling. Without filter support, preserve the existing path without inventing a dependency.

## 3. Make shutdown and failure behavior explicit

Normal completion may enter a bounded tail only after RF is confirmed inactive using the existing adapter's actual observation method. Emergency stop, shutdown, reset, maintenance, launch rejection, lost preparation authority and faults must cancel pending activation and force safe output promptly; optional tail must never delay emergency deassertion. Document which graceful cancellation paths, if any, permit tail and why; default fault behavior is immediate safe deassertion.

Preserve existing lease semantics: pre-arm expiration prevents activation, while armed/running terminal-extension policy is not replaced by a new transport-loss cancellation rule. Resolve lead/tail state membership explicitly and ensure ownership cannot transfer while the old execution can still affect hardware. Stale callbacks and late worker writes must not reactivate a canceled amplifier or start RF.

Clamp RF and attempt amplifier deassertion before any fallible or blocking cleanup, including DMA halt. Handle partial initialization, missed IRQs, stalled workers, adapter/register mismatches and repeated stop/recovery calls. Preserve emergency GPIO overrides and watchdog recovery. Unconfirmed safety retains inhibition and the required ownership/fault state; issuing a GPIO write does not prove amplifier shutdown or RF silence.

Honor optional/disabled amplifier configuration without GPIO access or artificial success observations. Verify active-high and active-low outputs, safe initialization and external reset/unpowered bias assumptions. Ordinary inhibited firmware must keep physical amplifier output inactive during simulated jobs. Any physical GPIO timing test must use an explicit controlled test path and verified wiring.

## 4. Coordinate management, persistence and compatibility

Treat changes to capabilities, API/protocol-facing schemas, timing limits or session behavior as coordinated Pi/Pico work. Inspect and update every affected producer, actual USB/network client, serializer, strict validator, runtime consumer, test adapter, generated asset and document together. Do not silently redefine transmitter-amplifier-enable/1 or any historical resource. Select explicit independently versioned extensions where needed; retain exact historical shapes, limits and semantics. Avoid adding GPIO/timing directives to WTP/1 when member-local hardware policy suffices.

Validate document shape before field access. Reject unknown versions/carriers, missing or extra fields, wrong types, inconsistent advertisements and invalid device/boot/profile/revision bindings before mutation. Legacy clients must preserve unrepresented timing or receive an explicit refusal. Do not relax validation, substitute older peers or add hidden downgrade behavior to pass tests.

Reuse atomic configuration and journal machinery. Define migration, omission preservation, explicit replacement defaults, reset domains and rollback compatibility. Cover corrupt/torn records and reboot reconstruction; never restore an energized lead/tail interval or resurrect superseded settings after reboot. Preserve station/access credentials, schedules, watermarks, calibration, logging and unrelated hardware settings.

Keep writes under the existing idle, unowned, RF-inactive, nonfaulted and revision-checked policy. Preserve pin/polarity restart latching, including A/B/A changes. Decide and document whether timing-only changes need restart; they must not alter an accepted execution. Keep saved values, immutable boot state and per-job effective timing distinct.

Provide only the management controls and status needed to configure this backend feature in the Pico interface and corresponding Pi selected-member workflow. Use the Impeccable workflow if editing UI. Preserve incumbent styling, authentication, drafts, explicit save/readback, uncertain-save recovery, collapsed sections and Top behavior. Show units, zero/default semantics, supported bounds, pending restart and lead/tail state accurately. Saving settings must not perform an output test. Preserve native Pi amplifier behavior; implement required companion negotiation without conflating Pico GP and Pi BCM GPIO numbering.

## 5. Validate behavior and the actual source pair

Use current checked-in commands and pinned dependencies. Add meaningful deterministic tests around production state transitions: zero/nonzero boundaries, disabled output, both polarities, insufficient lead, overflow, late/early callbacks, immediate and scheduled jobs, clock discontinuity, stale generations, repeated cancellation, pre-arm expiry, armed/running terminal extension, keyed gaps, adjacent jobs, normal tail and every emergency path. Inject failures before/after enable assertion and RF onset, during tail and during cleanup; verify refusal before writes or output where required.

Exercise persistence, historical/current negotiation, unsupported views, omission/replacement, drafts, stale revisions and reboot behavior through production handlers. Run affected browser workflows, complete relevant host tests, firmware builds, linked-image/stack/heap/resource audits and documentation/link checks. Report resource and timing-budget changes; do not equate host tests with target timing.

Both actual network and USB integration suites must pass for the intended candidate sources. Follow WsprryPi .github/workflows/debian-non-hardware.yml recipes for wtp-network-loopback and wtp-usb-management-pair. Include wtp-network-runtime-test, wtp-network-interop-test, wtp-config-interop-test, the actual Pico usb_management_driver, wtp-usb-pair-client-build, wtp-usb-management-test and WsprryPi-UI/tests/wtp_usb_pair_test.js through the production pair. Select both source revisions and pinned dependencies explicitly. Cover historical/current contracts and negative version, shape, bounds and identity cases before mutation. Failed, cancelled, skipped or timed-out required checks remain unresolved; fix or rerun them.

## 6. Validate hardware and preserve the installation

Define finite acceptance bounds before measurement. Identify the physical board, source/image, engine, clock, GPIO/polarity, driver/load, instrumentation and configuration. Verify the actual wiring and electrical compatibility before toggling outputs. Use independent timing observations to measure enable-to-RF lead, RF-off-to-disable tail, startup inactivity, jitter, cancellation, fault cleanup and representative modes/keyed gaps. GPIO readback establishes commanded logic state, not amplifier readiness, power or measured RF silence. Use appropriate measurements for each claim.

Verify current suitable RF termination before any transmission. Do not assume a previous campaign's wiring is unchanged. Complete independent non-transmitting work if physical access or RF verification is unavailable, then report the specific remaining acceptance blocker. Do not claim the timing feature physically qualified using only mock or simulator evidence.

Deploy ordinary development firmware with scripts/usb_installer.py and its generated developer bundle, retaining the exact bundle, transaction, same-board reference and postboot verification. Do not substitute direct picotool programming that leaves a stale installer reference. After low-level programming tests, restore the verified original image or complete a shared-installer deployment. Reconcile stale references only with the original bundle and exact same-board flash comparison through upgrade --installed-bundle; never edit/delete identities to bypass refusal.

Preserve persistent settings and unrelated services. Restore test policies, schedules, wiring and services to the agreed state, with amplifier inactive and RF off. Record exact final firmware/device state and any intentional deployment changes. Do not flash every device merely because authority includes all three.

## 7. Perform adversarial review, fixes and reassessment

Perform an adversarial assessment of the complete implementation and evidence. Challenge unsafe early assertion, timing arithmetic, shortened settling, silent launch shifts, prolonged enable during faults, stale callbacks, ownership transfer, filter coordination, boot/reset behavior, migration, closed-contract compatibility, actual companion integration and misleading status.

Record actionable findings with severity, evidence, required correction and closure criteria. Fix the underlying issues and rerun affected checks. Close findings with evidence, then perform another fresh adversarial assessment. Repeat until actionable issues are resolved. A deferred required test or relabeled limitation is not closure; report genuine external blockers accurately. Claim independent review only if it occurred. Keep cosmetic polishing bounded while continuing necessary correctness/safety repairs.

Use the standing authority to resolve ordinary engineering choices and failures autonomously. Complete independent work before requesting help for a blocker that meets its confirmation criteria.

## 8. Document, commit, push and report

Update maintained amplifier, lifecycle, API, persistence and operator documentation to describe current behavior and exact limits. Keep public documentation on Read the Docs. Mark item 5 complete only after implementation and required software/integration/physical acceptance pass. Preserve other checklist items, numbering and unrelated work.

Consolidate enduring content into the maintained amplifier contract, retire this completed execution prompt and repair its references. Do not retain a completed prompt merely to preserve a checklist link.

Review the final diff, run git diff --check and applicable checks, commit only task changes and push to the verified intended remotes using normal Git safeguards. Publish required first-party UI submodule changes before the parent pointer. Ensure companion updates are available on the intended paired refs; an unmerged side branch does not establish delivery on devel or main. Inspect relevant CI, resolve failures and verify remote parity.

Report implemented semantics/defaults, source revisions and tested uncommitted changes, review findings and closure, exact validation commands/results and CI links, physical timing evidence and limits, resource changes, installed/restored device and service state, commit SHAs, pushed branches, final working-tree state and outstanding issues. Do not claim amplifier readiness or RF qualification beyond the recorded evidence.

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
