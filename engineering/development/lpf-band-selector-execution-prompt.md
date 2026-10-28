# Item 4 execution prompt — LPF/band-selector control

Status: saved execution prompt; implementation not started. Saving, reviewing or committing this prompt does not execute it. Execute only when explicitly assigned. Item 4 remains conditional on economic usefulness.

## Objective and scope

Assess and, if justified, implement optional LPF/band-selector control as a coordinated WsprryPico, WsprryPi and operator-documentation feature. Deliver safe member-local selection, configuration, persistence, both management interfaces, compatibility and meaningful validation. Use the complete standing execution authority below for that assigned session.

Preserve the existing Pico 2 W/RP2350 architecture and Pi behavior. Item 5 amplifier lead/tail timing, item 11 Si5351, new RF engines, PCB design and filter construction are separate work. Necessary filter settling belongs to this slice; it must not silently introduce amplifier lead/tail controls. Software selector control and declared coverage do not establish physical filter response, RF power or antenna-ready emissions.

## 1. Inspect the baseline and determine usefulness

Read applicable AGENTS.md files, README.md, CONTRACT.md, engineering/architecture.md, the development guide, and the [pin-assignment](../pin-assignment-contract.md), [shared transmitter](../transmitter-application-contract.md), [pin allocation](pin-allocation.md) and [amplifier-enable](amplifier-enable.md) contracts. Inspect current branches, upstreams, working changes, submodules and available test recipes in each affected repository. Preserve unrelated work.

Inspect the actual Pico pin planner, hardware schemas, persistence, RF sink/launch/cleanup paths and browser editor. Inspect Pi Band GPIO mappings, frequency-suffix compatibility, job preparation, production USB/network member clients and first-party UI before designing changes. Do not assume Pi BCM numbering or Pi band tables define Pico support.

Record a bounded usefulness assessment: operator benefit over fixed/manual filtering, available selector hardware, GPIO budget, driver/bias needs, parts cost, implementation/support cost, firmware resources and test-equipment availability. Verify current prices/specifications from primary sources when making concrete claims; distinguish existing equipment from hypothetical purchases. Prefer a small, useful direct-GPIO implementation consistent with the selected contracts. Do not add expanders or a general relay framework without demonstrated need.

If the assessment supports implementation, select and document the smallest useful design and proceed autonomously. If evidence shows it is not economically useful, save the rationale and recommendation, commit and push that assessment, and report item 4 as deferred rather than implemented. Do not remove or mark the feature complete solely because an assessment was written. Missing physical hardware permits independent software work but remains an explicit hardware-validation blocker where required.

## 2. Define the selector and filter model

Separate named physical selector resources from band/frequency mappings. A selector owns its GPIO once; several bands may reference the same resource. Specify bounded counts, names/IDs, polarity, inactive state, frequency units, coverage intervals and settling limits. Justify numerical bounds against current resources and real hardware requirements; do not invent measured performance.

Use eligible Pico GP numbers and exclusive role allocation. Reject overlaps with RF output, switch, amplifier, indicator, I²C and board-reserved resources, duplicate owners, conflicting polarity, malformed ranges and unsupported topologies. Validate atomically in firmware on every entry path, including persisted records. No UI-only safety rules.

Define explicit disabled/fixed-manual and required-selector policies. Defaults preserve existing installations without enabling new outputs. Required selection with no valid mapping must reject admission. Fixed/manual filtering must not be displayed as verified automatic coverage. Resolve overlapping coverage deterministically or reject ambiguity; never guess from band names.

Select one filter suitable for every RF-on frequency in the complete accepted job, including modulation shifts, sweep/event frequencies where supported, planner-realized frequencies and applicable correction semantics. Document nominal versus programmed frequency handling and coverage margins. Reject jobs requiring mid-job switching. Preserve native engine and frequency-qualification limits independently of filter selection.

Retain Pi Band GPIO and frequency-suffix compatibility where already supported. Do not append GPIO commands to WTP/1 jobs, transplant Pi GPIO numbers onto a Pico, or turn existing selector mappings into claims of measured LPF coverage.

## 3. Implement local sequencing and recovery

Use the existing member-local execution authority and validated immutable boot pin plan. Assignment/polarity changes require the existing idle, unowned, RF-inactive, nonfaulted, revision-checked transaction. Preserve restart/output-inhibit latching, including A/B/A saves. Define whether mapping-only changes require restart; they must never alter an already accepted job's frozen selection.

Initialize validated selector outputs inactive with safe latch/direction ordering. External bias and suitable drivers must establish safe reset/unpowered behavior; never drive relay coils directly from GPIO. Document 3.3 V interface requirements without claiming software controls power-up glitches.

Implement break-before-make: confirm RF and amplifier inactive, deactivate the previous selection, activate the chosen resource, satisfy the configured settling interval, then allow existing local RF launch. Account for preparation and settling before scheduled deadlines. Late or interrupted preparation must fail safely rather than shift the promised launch or emit an unannounced RF interval. Use bounded local timing, not browser/network delivery or blocking waits that disrupt service.

Keep selection stable across one complete job and its keyed gaps. On completion, cancellation, missed launch, relevant lease expiry, reset, shutdown, maintenance and faults, stop RF, deactivate the amplifier and return selectors to defined safe states through the existing cleanup authority. Preserve existing armed/running lease terminal-extension semantics. Unconfirmed cleanup inhibits further transmission; commanded/read-back GPIO levels are not proof of relay position or RF silence.

Keep portable selection/state logic separate from Pico SDK adapters. Bound memory and per-service work, preserve core ownership and avoid heap allocation or logging in timing-critical paths. The inhibited image must not unexpectedly energize selectors or amplifier outputs; use an explicit controlled test path for physical GPIO validation.

## 4. Coordinate schemas, persistence and companion clients

Inspect every affected producer and consumer before changing a closed contract. Update capabilities, descriptors, independently versioned schemas, serializers, strict validators, runtime consumers, paired adapters, generated assets and documentation together. Introduce explicit versions where required; preserve exact historical shapes, limits and semantics. WTP/1 remains device-neutral and unchanged unless a separately justified protocol need is established.

Validate shape before access and reject unsupported versions/carriers, extra or missing fields, wrong types, invalid bounds and mismatched device/boot/profile/revision bindings before writes. No hidden downgrade, relaxed validator or older-peer substitution. An old client must preserve settings it cannot represent or receive an explicit refusal.

Reuse atomic configuration/journal machinery with safe migration and rollback behavior. Cover erased/corrupt/torn records, reset domains, omission preservation and reboot reconstruction. Unsupported stored selection must inhibit affected RF admission instead of silently falling back to another pin or filter. Preserve credentials, station settings, schedules, watermarks, calibration and logging settings.

Ensure both Pico-local and Pi-selected-member management reach the same validation and lifecycle policy over actual USB and network carriers. Keep local Pi hardware settings distinct from a selected Pico's settings. Publish any required first-party UI submodule changes before the parent pointer, and deliver required companion changes on the intended paired refs.

## 5. Deliver the operator workflow

Use the Impeccable workflow for planning and reviewing the existing interfaces. Extend the incumbent Radio pins/hardware controls and selected-member Pi editor; preserve their established styling and interaction conventions. The operator's task is to name a filter, assign a supported selector, declare coverage/settling and understand whether the saved setup can be used.

Show GPIO ownership/conflicts, polarity, coverage units, selection policy, saved versus boot-applied state, restart required, current selection and precise admission failures. Distinguish declared coverage from physical qualification. Unsupported firmware must explain availability without showing functional controls.

Preserve authenticated access, device/boot/revision binding, explicit save/readback, uncertain-save recovery, drafts, receipts, collapsed sections, grouped anchors and Top re-furl behavior. Test stale selection, access lock, disconnect, concurrent edits, invalid inputs and pending restart. Provide accessible labels, keyboard/focus behavior, readable narrow layouts and both existing themes. Configuration save must never start a transmission or perform an unrequested relay test.

## 6. Validate software, integration and physical behavior

Use documented commands and pinned dependencies. Exercise selector allocation, shared-resource mappings, coverage boundaries, whole-job rejection, polarity, atomic replacement, restart latches, migration, deadline/settling accounting, break-before-make and every cleanup path. Inject adapter failures and verify refusal before outputs or writes. Test the production implementation rather than a duplicate test-only model.

Both actual network and USB production-path integration suites are mandatory for any affected capability/API/protocol surface. Follow WsprryPi .github/workflows/debian-non-hardware.yml recipes for wtp-network-loopback and wtp-usb-management-pair. Include wtp-network-runtime-test, wtp-network-interop-test, wtp-config-interop-test, the actual Pico usb_management_driver, wtp-usb-pair-client-build, wtp-usb-management-test and WsprryPi-UI/tests/wtp_usb_pair_test.js through the production pair. Explicitly select the intended candidate sources and pinned dependencies. Record both revisions and tested dirty changes. Cover valid historical/current contracts and malformed/version/identity/limit failures. Failed, cancelled, timed-out or skipped required checks remain unresolved.

Run affected browser workflows, firmware builds, linked-image/resource audits, documentation and link checks. Record flash, RAM, stack and timing-budget changes. Preserve production RF settings and assess potential timing interference; passing host tests does not establish physical timing.

Use finite physical tests on identified authorized equipment when available. Verify wiring, driver compatibility, external bias and actual GPIO identities before toggling outputs. Measure inactive startup, polarity, break-before-make, settling and cleanup with suitable independent instrumentation. Prove selector stability during representative keyed gaps and successive jobs. RF tests additionally require current verified termination; GPIO traces alone do not qualify filter response. Record exact board, source/image, engine, clock, pins, mode, load and instrumentation, with explicit acceptance bounds and evidence limits.

Deploy ordinary development firmware through scripts/usb_installer.py and its generated developer bundle, preserving transactions, same-board image references and postboot verification. Retain the exact bundle. After low-level programming tests, restore the verified original image or finish a shared-installer deployment. Reconcile a stale reference only using the original bundle and exact same-board flash comparison through upgrade --installed-bundle; never edit/delete identities to bypass refusal. Preserve settings and restore services, policies and test wiring/state as agreed. Report final devices and RF state.

## 7. Perform adversarial review, fix and reassess

Perform an adversarial assessment of the complete result, including economic assumptions, electrical defaults, mapping ambiguity, whole-job coverage, switching glitches, timing, cleanup, concurrency, migration, historical contracts, actual companion paths and operator error recovery.

Record each actionable finding with severity, evidence, correction and closure criteria. Fix the actual cause, rerun affected checks and close each finding with evidence. Then perform another fresh adversarial assessment. Repeat until actionable issues are resolved; deferral or relabeling does not close a required acceptance failure. Claim independent review only when it occurred. Keep aesthetic polishing bounded while continuing necessary correctness and safety repairs.

Complete independent work before escalating a genuine external blocker under the standing authority. Do not mark item 4 complete while required integration or physical acceptance remains unresolved.

## 8. Document, commit, push and report

Document implemented behavior, wiring/driver requirements, configuration, limitations, migration and recovery in maintained contracts and operator guides. Keep public documentation on Read the Docs. Mark item 4 complete only after justified implementation and its required acceptance pass; otherwise report its exact pending/deferred state. Preserve other checklist items and numbering.

Consolidate enduring technical content into a maintained LPF/selector contract, retire this completed execution prompt and repair references. Do not archive a completed prompt solely to retain a checklist link.

Review the final diff, run git diff --check and applicable checks, commit only task changes, and push to verified intended remotes using normal Git safeguards. Ensure required Pi/Pico/UI changes are available on the intended paired branches; an unmerged companion branch does not establish delivery. Inspect relevant CI, resolve failures and verify remote parity.

Report the usefulness decision, implemented behavior, repository/source pairs, review findings and closure, exact validation commands/results and CI links, hardware evidence and limitations, firmware/resource changes, deployment/restoration state, commit SHAs, pushed branches, working-tree state and outstanding issues. Do not imply RF/filter qualification beyond the recorded measurements.

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
