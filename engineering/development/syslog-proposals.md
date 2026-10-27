# Syslog prompts and execution authority

These prompts define selected unfinished work in the [consolidated backlog](consolidated-backlog.md#combined-ui--backend). The USB prompt covers coordinated feature implementation. The UDP prompt produces a separate reviewed proposal and implementation plan; UDP implementation remains pending. USB implementation is deployed with bounded acceptance recorded in the [USB logging contract](usb-logging.md); final full-CI disposition remains open. UDP proposal and implementation remain pending. Saving, reviewing, committing or pushing this document does not execute either task or authorize deployment by itself.

The [standing execution authority](#wsprry-development-session--standing-execution-authority) is part of both prompts. Include that complete section when copying either prompt for an explicitly assigned execution session. It grants authority within the assigned task and its stated session; it is not a project-wide replacement for future user instructions or technical permission boundaries.

Use **controller/member** for fleet control and **collector/sender** for logging. A Pico or Pi retains its stable origin identity, hostname, boot identity and sequence number; receiving and forwarding Pis add their own identities separately. A logging collector need not be the fleet controller. The UDP proposal includes member Pi to collector Pi forwarding of both native Pi and attached-Pico records.

## USB syslog execution prompt

Implement syslog over USB as one coordinated UI/backend feature across:

- /Users/lbussy/GitHub/WsprryPico
- /Users/lbussy/GitHub/WsprryPi
- /Users/lbussy/GitHub/WsprryPi/WsprryPi-UI, the first-party UI submodule
- /Users/lbussy/GitHub/WsprryPi-Docs

The shared “Wsprry Development Session — Standing Execution Authority” included with this prompt is part of this task. It authorizes necessary companion work, deployment, validation, Git operations and recovery within its boundaries. Do not treat WsprryPi or documentation changes as an unauthorized follow-up.

This prompt is proposed work until explicitly executed. Once executed, continue through investigation, design, implementation, adversarial review, repairs, validation, documentation, commit, push and reporting without routine approval gates.

### 1. Inspect and preserve the baseline

Read each repository’s applicable AGENTS.md and development instructions. For WsprryPico, read README.md, CONTRACT.md, engineering/architecture.md and engineering/development/README.md.

Inspect branches, upstreams, working trees, staged changes and recursive submodule state. Preserve existing user work and unpushed commits. Resolve actual repository locations rather than following stale documentation paths.

Inspect the Pico Console, WTP and USB management adapters; USB descriptors and discovery; configuration journals; shared browser API; current diagnostic tools; and relevant tests.

Inspect WsprryPi’s current logging initialization, USB discovery/management, Fleet integration, device identity, maintenance coordination, configuration lifecycle and service ownership.

Review the existing journald-backed Logs implementation, including WsprryPi-UI/API_syslog.md, data/log_stream.php, data/view_logs.js and the relevant views/styles. Verify actual behavior against the documentation.

Use the mandatory Impeccable workflow for UI design, implementation and rendered review. Preserve the established interface, light/dark themes and mobile behavior. Respect excluded UI files, including data/view_diag_logs.php unless the user explicitly changes that boundary.

### 2. Establish a shared logging identity contract

Use controller/member for fleet control roles and collector/sender for logging roles. A Pi may hold multiple roles. Collecting logs must not grant transmitter ownership or alter recurrence authority.

Define and document a common logical record model that can later support USB, UDP, native Pi events and forwarded events. Select exact field names and versions after inspecting existing contracts.

Every record must retain:

- Origin kind: Pico or Pi.
- Stable origin device/host identifier.
- Origin hostname or display name, treated as mutable presentation.
- Origin boot/session identity.
- Origin sequence number with documented reset/wrap behavior.
- Event code, severity, facility and bounded message.
- Origin UTC timestamp when valid, otherwise explicitly unavailable.
- Origin monotonic time where available.

A receiving or forwarding Pi must add its own host identity, receipt timestamp, ingress transport and bounded forwarding provenance separately. A Pico record must remain attributable to that Pico after journald ingestion or forwarding.

Reuse established stable Pi/Pico identities where suitable. If a host identity mechanism is missing, define its persistence, cloning, replacement and privacy behavior. Do not silently use hostname as immutable identity or expose unrelated machine identifiers.

Keep firmware sequence numbers, origin event time, host receipt time and journald cursors distinct. Use representations safe for JavaScript and 32-bit PHP. Claimed identity is not proof of authentication.

### 3. Design the USB record carrier

Use [RFC 5424](https://www.rfc-editor.org/rfc/rfc5424.html) message formatting with a documented project-specific USB serial mapping. Do not imply that an ordinary network syslog collector directly accepts USB.

Evaluate the existing Console against a separate CDC interface. Prefer preserving current descriptors and discovery unless evidence justifies changing them. Record the selected design and compatibility consequences.

Raw logs must never enter WTP or USB management framing. Defined management requests/replies may configure logging and report status through their documented resource semantics.

Define unambiguous framing and coexistence with startup text, INFO and administrative commands. Prevent interleaving within records or replies. Preserve existing Console behavior when streaming is disabled.

Specify start/stop, connection-local versus persisted state, early-boot behavior, partial/zero writes, DTR transitions, disconnects, reconnects, truncation and resynchronization. Operators must retain a reliable way to return to ordinary Console use.

Identify the intended device and Console role using verified identity and interface metadata, not tty ordering.

### 4. Implement bounded Pico logging

Separate portable records, filtering and formatting from SDK, USB, storage, browser and RF adapters.

Define concrete record, queue, memory, rate, burst and servicing budgets. Justify them against existing resource use. Specify overflow policy, severity handling, dropped counts and disconnected-host behavior.

Formatting and USB I/O must remain outside IRQs, core-1 RF execution and timing-sensitive paths. Transfer necessary events through a bounded mechanism compatible with existing ownership.

Cover useful lifecycle events without per-symbol or per-sample spam: startup/reset, transport transitions, clock-state transitions, configuration outcomes, ownership and job lifecycle/faults.

Exclude secrets, credentials, authentication proofs and complete request/configuration dumps. Protect against terminal-control, newline and HTML injection. Do not invent a private enterprise number for structured data.

USB logging must work without Wi-Fi or synchronized UTC. Logging failures must not block services, recursively generate failures, change clock discipline, enable schedules or alter accepted jobs.

### 5. Implement the WsprryPi collector and management integration

Implement the necessary Pi backend, configuration, lifecycle and UI changes as part of this feature.

Select a maintainable ingestion architecture using the existing service/process model. Define serial ownership, bounded reads, reconnection, parser limits and per-device resource budgets.

Support multiple attached Picos without mixing their identity, boot, sequence or stream state. Handle replacement devices and re-enumeration without silently trusting a new origin.

Coordinate Console ownership with existing tools, browser Console use, firmware maintenance, bootloader transitions and exclusive USB maintenance. Release and reacquire the correct interfaces without disrupting WTP or management unnecessarily.

Preserve native WsprryPi logging and its existing debug, journald and timestamp semantics. Map Pico severity explicitly rather than accidentally filtering remote records through unrelated host settings.

Choose and implement a journald ingestion/projection strategy. Preserve origin metadata without fabricating trusted journald fields.

The existing Logs path filters to wsprrypi.service. Explicitly resolve how imported Pico records become visible while retaining appropriately scoped access. Do not solve visibility by exposing every system unit.

Review API normalization, filters, pagination/backlog, SSE reconnection, cursor storage and journal rotation. Preserve origin metadata end to end. Journal cursors remain journal cursors; firmware sequence numbers must not replace them.

### 6. Deliver a complete operator workflow

Provide consistent Pico and Pi controls for supported enablement, severity/filter settings and status. Show saved versus active state, unsupported firmware, disconnected/busy Console, overflow and uncertain saves.

In the Pi Logs UI, distinguish local Pi records and each Pico source. Show source identity and meaningful timestamps without obscuring the message. Include bounded filtering, pause/resume, export and empty/error states where consistent with the existing interface.

Scope browser resume state to the selected source/filter context. Reconnecting must not silently resume another device’s history.

Keep settings in the correct authority domain. The Pico owns its logger settings; the Pi owns collection and forwarding policy. Use capability negotiation, independently versioned resources, target/revision checks and authoritative readback. Preserve legacy closed schemas and unrelated fields.

Closing a browser log view must not accidentally stop collection or affect transmitter operation.

### 7. Prepare for member-to-collector forwarding

Design the shared record and collector boundaries so a member Pi can later forward both its native records and attached Pico records through the separate UDP feature.

Preserve origin identity and event identity across forwarding. Identify the required extension points without implementing the UDP feature incidentally.

Specify how future duplicate suppression will handle the same Pico event arriving over USB and UDP. Untrusted UDP claims must not suppress trusted USB records.

### 8. Validate and review adversarially

Run meaningful deterministic tests for formatting, encoding, limits, redaction, injection resistance, saturation, short/zero writes, DTR changes, reconnects, command/reply coexistence and protocol isolation.

Test Pi ingestion, multi-device identity, hotplug/replacement, maintenance exclusion, configuration persistence, journal normalization, source filters, cursor scope, replay and UI failure recovery.

Use verified project commands. Run WsprryPi C++ validation on an identified Linux host, authorized Pi or Linux CI. Perform Impeccable review of applicable desktop/mobile and light/dark states.

Use finite physical USB tests where needed. Record exact host, board, source/image, boot identity and setup. Prefer RF-inhibited validation; perform RF tests only when needed and within the standing authority’s verified conducted-path requirements.

Perform an adversarial assessment of the complete cross-repository result. Challenge compatibility, authority, timing interference, resource bounds, identities, parser recovery, visibility, replay, privacy and operational recovery.

Track findings with severity, evidence, corrective action and closure criteria. Fix actionable issues and rerun affected checks. Perform another fresh adversarial assessment after repairs. Repeat until actionable findings are resolved. Do not count deferral or relabeling as closure. Identify genuine external blockers honestly.

### 9. Save both prompts and maintain combined TODO items

Save both complete USB and UDP prompts, including the shared standing authority, to a durable document such as engineering/development/syslog-proposals.md in WsprryPico. Preserve the reviewed architecture and implementation decisions alongside them.

Add both features to engineering/development/consolidated-backlog.md as combined UI/backend items:

- USB syslog: Pico logging/export, Pi collection, both UIs, identity, lifecycle, documentation and validation.
- UDP syslog: Pico and Pi senders, Pi collector, forwarding, both UIs, identity, loop/duplicate handling, documentation and validation.

Link each to its durable instructions. Record cross-repository ownership and dependencies. Use existing Pi and documentation work lists for linked deliverables where appropriate, without creating competing feature authorities.

Keep UDP pending. Mark USB complete only when its actual acceptance requirements are satisfied.

### 10. Document, commit, push and report

Update Pico operator/engineering guidance and the appropriate WsprryPi-Docs logging, Fleet, setup, maintenance and troubleshooting material. Explain current capabilities plainly. Keep future UDP behavior clearly proposed.

Build and verify documentation using each repository’s documented environment. Preserve Read the Docs publication.

Review all diffs and stage only task-authored changes. Treat the first-party UI submodule as a separate repository: review/test it, commit and push it first, then commit the reviewed parent pointer. Do not modify dependency submodules incidentally.

Commit and push validated changes in each affected repository to its verified intended remote/branch. Preserve unrelated staged work and unpushed commits. Do not force-push shared history.

Verify remote availability of every referenced submodule commit and report source-pair compatibility and CI results.

Report implemented behavior, important decisions, adversarial findings and closure, actual tests and visual evidence, hardware/deployment identity, documentation impact, commit SHAs, pushed branches, remote parity, remaining limitations and final repository/submodule states. Do not claim unperformed RF, service or release qualification.

## UDP syslog proposal prompt

Develop and adversarially review a separate implementation-ready proposal for syslog over UDP across WsprryPico, WsprryPi, its first-party WsprryPi-UI submodule, and WsprryPi-Docs.

The shared “Wsprry Development Session — Standing Execution Authority” included with this prompt is part of this task.

This is a proposal task: produce the complete coordinated design, required implementation changes, acceptance plan, durable instructions and combined TODO entries. Commit and push those reviewed artifacts. Feature implementation remains pending rather than being claimed complete.

### 1. Inspect current architecture and preserve work

Read applicable instructions and development contracts in every repository. Inspect branches, upstreams, dirty/staged work and submodules.

Review the USB syslog design or implementation, native Pi logging, Fleet/member identity, network ownership, configuration persistence, service lifecycle, journald ingestion and existing Logs/SSE behavior.

Use the mandatory Impeccable workflow for UI planning. Preserve the existing product language and design. Do not introduce Apache/PHP into Pico firmware.

Identify exact current integration points. WsprryPi companion work is required proposal scope, not an optional documentation follow-up.

### 2. Define the supported topologies

Use controller/member for fleet control and collector/sender for logging. These roles are independent: a collector need not control the transmitter, and a controller may also be a sender.

Cover at least:

- Pico → explicitly configured collector Pi.
- Pico → external syslog collector.
- Member Pi native logs → collector Pi.
- Member Pi → external syslog collector.
- Pico → USB-attached member Pi → collector Pi, preserving the Pico origin.
- Several member Pis and Picos reporting to one collector.

Define the initial supported topology and limits. Include a useful member-to-collector workflow without requiring a second scheduler, transmitter ownership or WTP changes.

Assess existing forwarding facilities versus an application-owned implementation. Select a justified architecture and identify package, service, installation and support implications. Do not require incidental replacement of the host’s logging stack.

### 3. Preserve origin and forwarding identity

Use the common identity model established for USB logging: origin kind, stable origin ID, mutable hostname, boot identity, sequence, event code, severity, event time and bounded message.

A forwarded Pico event must retain its Pico identity. A native member Pi event must retain that Pi’s identity. The receiving and forwarding host identities, receipt timestamps and transport provenance are additional metadata.

Define identity persistence, cloning/replacement handling and hostname changes. Reuse established member identities where suitable. Do not treat hostname, source IP, discovery labels or an unauthenticated payload’s claimed ID as authenticated identity.

Keep origin UTC, origin monotonic time, host receipt time, journal cursor and forwarding metadata separate. Preserve unavailable or uncertain origin time honestly.

Define a bounded event identity for duplicate handling across USB, direct UDP and forwarded UDP. Scope deduplication so spoofed traffic cannot suppress records from a more trusted ingress.

### 4. Specify the UDP transport

Use [RFC 5424](https://www.rfc-editor.org/rfc/rfc5424.html) formatting and [RFC 5426](https://www.rfc-editor.org/rfc/rfc5426.html) transport mapping: one message per datagram, without USB delimiters or additional transport framing.

Support destination port 514 and validated alternate ports. Recommend an initial IPv4 payload cap of 480 octets, with explicit analysis of formatting, truncation, interoperability and network MTU. Do not fragment one logical event into application datagrams.

Determine supported address families from the actual adapters. Select a justified initial scope rather than claiming unsupported IPv6.

Specify unicast destination validation, optional DNS behavior, caching, expiry, asynchronous failure and network-generation binding. Prevent unintended broadcast/multicast, self-directed loops and uncontrolled destination fan-out.

Define sender enablement, destination, port, severity, filters, rate and burst settings. Default export to disabled.

Distinguish configured, awaiting network, resolving, locally ready, local submission failure and unknown collector receipt. A successful send does not prove delivery.

### 5. Design the WsprryPi collector

Specify explicit opt-in listener configuration, bind interface/address, port, allowed peers, source classification, maximum datagram/record size and resource budgets.

Choose a least-privilege service model. Do not require a privileged listener merely because senders support port 514. Explain service installation, upgrades, enable/disable, recovery and removal.

Define parsing, malformed input handling, rate limiting, per-source fairness, journal ingestion, storage/retention impact and protection against log floods.

Preserve the existing Logs API’s compatibility while carrying origin metadata through normalization, filtering and rendering. Resolve its current wsprrypi.service filter explicitly; receiving a datagram alone does not make it visible.

Never fabricate trusted journald metadata. Distinguish transport-observed identity from payload claims and explain the trust limits of unauthenticated UDP.

A sender must not be enrolled as a transmitter controller simply because it submits logs.

### 6. Specify forwarding, loop prevention and outages

A member Pi must be able to send its own logs and selected attached-Pico logs to the chosen collector.

Define source-selection policy and preserve original severity, identity, event time and event ID. Add relay information separately. Avoid exporting the same record again merely because its ingestion created a local journal entry.

Prevent loops through explicit forwarding topology, bounded relay/hop policy, bounded deduplication and clear treatment of already-forwarded records. Analyze collector-to-member and multi-collector cycles.

Define queue size, memory, per-poll work, send rates, overflow, stale-event expiry and outage behavior. Reconnection must not produce an unbounded replay burst.

Keep USB collection, native logging, browser service, WTP control and RF timing independent of collector availability.

Specify local-send counters accurately. UDP supplies no acknowledgement, guaranteed order or reliable loss recovery. Do not present sequence gaps as complete accounting of network loss.

### 7. Design both management experiences

Specify Pico sender controls in the Pico UI and equivalent selected-member controls in WsprryPi where supported.

Specify Pi native sender, attached-Pico forwarding and collector settings in the appropriate Pi interface. Keep local-host settings distinct from settings saved on a selected member.

Provide source/device filters in Logs, with clear origin and forwarding provenance. Include unsupported members, empty history, invalid destinations, duplicate sources, outages, overflow, uncertain saves and permission failures.

Keep source/filter-specific replay and cursor state correct. Preserve safe text rendering, drafts, accessible controls, mobile behavior and both themes.

Use capability negotiation, versioned schemas, target/revision checks, atomic persistence and authoritative readback. Legacy clients must preserve settings they do not understand.

Explain plaintext, unauthenticated UDP near enablement. Recommend deliberately configured managed networks. Do not imply that Wi-Fi encryption authenticates the collector or protects every forwarding hop.

### 8. Produce the implementation plan and acceptance matrix

List required changes by repository and actual subsystem:

- Pico portable logger and UDP adapter.
- Pico configuration, schema/capabilities, persistence and UI.
- Pi native sender/forwarder and optional collector.
- Pi service/installer/configuration lifecycle.
- Pi member-management backend and first-party UI.
- Journald projection, SSE/API normalization and Logs rendering.
- Documentation, support tooling and meaningful tests.

Separate reusable USB groundwork from UDP-specific work. Include exact compatibility, deployment, migration and rollback considerations.

Define deterministic tests for parsing, record bounds, redaction, destination validation, DNS failures, network-generation changes, queue pressure, rate limiting, send failure, reconfiguration and reboot reconstruction.

Include multi-member and multi-Pico cases, duplicate arrival over different transports, hostile identity claims, forwarding cycles, spoofed datagrams, listener floods, journal rotation, source filters and replay.

Define finite integration tests for native member Pi → collector Pi and USB Pico → member Pi → collector Pi. Record exact source/image, host/device identity, configuration and received evidence.

Use the authorized hosts and devices where later execution requires them. Prefer RF-inhibited tests; logging integration does not automatically require transmission. Distinguish software simulation, packet receipt, physical networking and RF qualification.

### 9. Save the prompts and add combined TODO items

Save both full prompts, their shared standing authority, the UDP proposal and the coordinated implementation/validation plan in the durable syslog document. Preserve existing USB material and clearly identify proposed versus implemented behavior.

Ensure the canonical WsprryPico backlog has two combined UI/backend feature items for USB and UDP, each linked to its instructions and carrying cross-repository responsibilities. Maintain linked Pi/documentation deliverables under established conventions without duplicating feature authority.

Keep the UDP item pending implementation. Preserve unrelated TODO entries and statuses.

### 10. Review adversarially and iterate to closure

Perform an adversarial assessment of the full proposal, source assumptions, topology, required Pi changes, UI workflows, security model, persistence, resource bounds and acceptance plan.

Record actionable findings with severity, evidence, required correction and closure criteria. Repair the actual artifacts and rerun affected checks.

Perform another fresh adversarial assessment after repairs. Repeat until actionable findings are resolved. Do not count deferral or a limitation label as closure. Identify genuine external blockers and do not claim independent review unless it occurred.

Resolve ordinary engineering choices autonomously using the standing authority. Escalate only material decisions or blockers that meet its confirmation criteria, after completing independent work.

### 11. Validate, commit, push and report

Validate cross-repository references, anchors, TODO links, source references, compatibility claims and the separation of supported and proposed behavior. Run git diff --check and applicable documented checks.

Commit only task-authored proposal/TODO changes in each affected repository and push to verified intended remotes. If UI-submodule files change, publish that reviewed commit before publishing its parent pointer.

Report the proposed topologies and recommended architecture, complete required Pi/Pico/UI changes, identity and forwarding model, review findings and closure, checks actually performed, unresolved external blockers, documentation impact, commit SHAs, pushed branches, remote parity and final repository/submodule states.

State clearly that UDP feature implementation and its runtime acceptance remain pending.

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
