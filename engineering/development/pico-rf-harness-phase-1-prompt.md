# Phase 1 — Pico RF qualification support in the Qualification Harness

## Activation and intended outcome

**Execute this prompt only when the user explicitly invokes Phase 1.** Reading, saving, linking, reviewing, or printing it does not execute it. The request that created this document authorizes preparation of the prompt and checklist only.

When invoked, implement production Pico RF qualification support in `WsprryPi-Qualification-Harness`, with the coordinated product changes genuinely required to use existing supported Pico interfaces. Deliver working campaign composition, strict input/result contracts, production adapters, deterministic failure coverage, documentation, successful applicable CI, committed changes, and pushed branches.

This is item 1 of the [RC.2 release checklist](rc2-release-checklist.md). Do not execute item 2's release-artifact qualification campaign or item 3's publication as an incidental part of Phase 1. Do not create release tags, publish firmware/releases, change recommended firmware, merge unrelated work, or initiate a new Si5351 improvement investigation. Broad standing authority below supplies permissions within the assigned scope; it does not select later phases for execution.

## Product decision that must remain fixed

Former item 21 is **closed as inconclusive and resolution-limited, with that conclusion final**. Automatic Si5351 correction exists for experimentation. It might help a different reference, such as a crystal, but no such benefit is established by the retained TCXO measurements.

- Do not reopen item 21, treat it as outstanding, disable the feature, redesign the learner, increase acquisition windows, or make improved Si5351 accuracy a Phase 1 or release acceptance condition.
- Preserve the approved wording in Pico `docs/reference/time.md` and the existing sanitized measurement records and limits.
- Distinguish successful control/operation of automatic correction from demonstrated accuracy improvement. Record a valid measurement as inconclusive when its resolution cannot support a stronger conclusion.
- Do not broaden the currently supported Si5351 hardware profile to crystals or other boards merely to implement the Harness. Existing explicit engineering-build gates remain authoritative.

## Repository scope and initial discovery

The primary implementation repository for this assigned task is:

`/Users/lbussy/GitHub/WsprryPi-Qualification-Harness`

Task-specific development and Git work in that repository is part of the requested Pico Harness integration, in addition to the three companion repositories named in the standing authority. Keep each repository's authority, branches, commits, dependencies, and delivery claims separate. Product changes must be justified by an actual integration need; do not refactor unrelated Pi, Pico, or documentation code.

Before changing anything:

1. Read applicable `AGENTS.md` files. In the Harness, follow its required reading order: `CONTRACT.md`, `docs/AGENT_OPERATIONS.md`, `docs/CURRENT_WORKFLOWS.md`, `docs/CAPABILITY_MATRIX.md`, the relevant development guides, production modules, schemas, and tests. Read `docs/OPERATOR_SECURITY.md` before host access. Inspect current CLI help rather than copying commands from old logs.
2. In Pico, read `README.md`, `CONTRACT.md`, `engineering/architecture.md`, `engineering/development/README.md`, `engineering/protocol/WTP.md`, the USB management contract, shared browser/control API, `gps-pps.md`, `clock-discipline.md`, `si5351.md`, and applicable RF/band/finite-job guidance. Read companion instructions before editing companions.
3. Record paths, branches, HEADs, upstreams, remotes, worktrees, staged/unstaged changes, untracked files, and dependency versions. Fetch the needed refs without replacing user files. Create isolated worktrees or checkouts based on current intended `devel` refs when needed; preserve dirty original checkouts.
4. Recheck current capabilities in actual code. The inspected Harness RF campaign uses `WsprryPiShim` and Pi GPIO/Si5351/RP1 contracts. A backend named `gpio` or `si5351` does not establish Pico support. Existing Pico lifecycle recipes install and preserve firmware with RF disabled; they are not a Pico RF campaign.
5. Inventory reusable Harness WTP support, such as `wtp_control.py`, existing framing/transport implementations, exact-count capture, carrier analysis, WSPR decoding, keyed-mode analysis, process ownership, progress logs, result manifests, and cleanup. Reuse those components where their actual contracts fit.
6. Trace an entire current five-mode campaign from CLI/profile through plan, schema/semantic validation, adapter construction, transaction/capture, analysis, result validation, cleanup, and reporting. Produce a concise implementation plan and then execute it without routine approval pauses.

Discovery hints from 2026-11-08, not assumptions about execution-time state:

- Pico `devel` was `f6c90a4925d02d60b7404487e24316f239c48e7c`; its 234-test canonical verification and both production Pi/Pico suites passed. Those runs did not perform live Pico RF qualification.
- The paired Pi revision was `f59bba741ff367d0652f6db03b0bf67d4d10444a`.
- Harness remote `devel` was `a6f9455ad8782021087559671b41102322c5edb6`. The local Harness checkout was older and dirty: `AGENTS.md`, `docs/development/helper-deployment.md`, and `src/wsprrypi_qualification/live_adapters.py` were modified; `chatgpt-context/` and `tests/unit/test_live_adapter_composition.py` were untracked. These are user-owned work, not a discard or commit allowlist. Reinspect before using them.
- Historical Pico C wiring, installed-image, SDR, GPSDO, service, and restoration records are not current physical setup evidence.

## Required campaign matrix

Implement four first-class, independently identified configurations:

| Configuration | Pico RF engine | GPS UTC/PPS input |
| --- | --- | --- |
| GPIO without GPS/PPS | Direct GPIO / RP2350 PIO-DMA | Disabled; explicitly selected supported non-GPS UTC source |
| GPIO with GPS/PPS | Direct GPIO / RP2350 PIO-DMA | Enabled and independently observed usable |
| Si5351 without GPS/PPS | Supported Pico Si5351 engine/profile | Disabled; explicitly selected supported non-GPS UTC source |
| Si5351 with GPS/PPS | Supported Pico Si5351 engine/profile | Enabled and independently observed usable |

Every row must compose **TONE, WSPR, QRSS, FSKCW, and DFCW** through the maintained campaign workflow, not a one-off shell runner. Select actual supported frequencies, GPIOs, I²C settings, mode limits, and output resources from the current product. Reuse existing mode-order, independent observation/count, decoder, and aggregation requirements; do not silently reduce them to make Pico fit.

GPS time discipline, automatic RF correction, manual PPM/residual trim, Si5351 CLK2 feedback, and receiver calibration are separate dimensions:

- Keep the four required engine/GPS rows clear. Within GPS-enabled rows, support explicitly selected automatic-correction off and on subcases, without pretending GPS enablement automatically selects RF correction.
- Require the supported qualified observation/provenance before a correction-on job. Represent missing, stale, mismatched, or conflicting observations as the product's defined refusal or fixture blockage, not as a silent manual fallback.
- A no-GPS row must establish that firmware GPS/PPS use is disabled; do not require physical cable removal merely to test the disabled path. Bind the actual non-GPS time source and observed freshness/quality. Do not revive unsupported NTP-derived RF calibration.
- Record selected and effective correction, estimate generation/age/uncertainty where available, manual trim, frozen job provenance, clock source, and receiver-only calibration independently. Do not modify transmitted frequency to compensate for receiver calibration.
- For Si5351 with correction on, admit the required input-only CLK2 allocation and current supported profile; reject missing/invalid feedback instead of inventing a substitute reference.
- Measurements can describe carrier error before/after correction, with proper bounds, but the campaign must not require correction to improve the carrier to classify an otherwise valid experimental feature as operational.

## Architecture and production control

1. Add a distinct Pico target/application adapter, with explicit target kind, identity, firmware/source/build information, RF engine, board, and control carrier. Do not disguise Pico as a Pi executable/backend or run Pi GPIO/DMA/I²C helper operations against the Pico host.
2. Keep portable planning, schemas, semantic validation, signal analysis, and reporting independent from OS, SSH, USB, and device adapters. Preserve macOS, Linux/Raspberry Pi OS, and native Windows portable-core support. Live platform limitations must be capability-detected and fail before mutation/RF; do not use WSL as native Windows USB qualification.
3. Use supported production Pico interfaces. USB CDC is the reference WTP transport, and USB management is a separate interface/authority. Reuse existing framing, ACK, discovery, negotiation, journals, and control clients where suitable. Select carrier explicitly; no hidden USB/network fallback. Do not create a third job protocol or firmware-only Harness command channel.
4. Submit complete bounded jobs to the Pico's existing JobService. RF timing remains local to RP2350. Do not stream per-symbol USB/network events or depend on host sleep timing for waveform edges.
5. Preserve independent management authority, transmitter ownership, lease/replay semantics, boot binding, configuration revisions, prepare/load/arm boundaries, job IDs, explicit reconciliation, abort, terminal state, and release. A timeout/disconnect is not proof that RF stopped or permission to replay a write/job.
6. Reuse actual Pico encoders/current compilation interfaces and maintained Harness analyzers. Keep expected reference generation independent enough to detect production defects; do not derive expected measurements solely by reading back the same erroneous implementation.
7. Support finite tone jobs and the existing WSPR/keyed-mode limits. Validate full event count, duration, repeats, frequency separation, message rules, overflow, and engine/band coverage before mutation/claim/ARM. Preserve current ownership and source-age checks.
8. Keep firmware installation separate from ordinary campaign execution. The adapter must not silently flash, erase, restart, provision, or switch engines in an unreviewed plan. Explicitly selected setup changes require snapshot, strict revision-bound writes, readback, restart handling, and restoration evidence.
9. Do not change Pico product contracts simply to accommodate a Harness shortcut. If a necessary existing capability is inaccessible, inspect all owning producers/consumers and implement the smallest coordinated change with strict validation and both required source-pair suites.

## Contracts, CLI, and evidence

- Integrate Pico into the maintained `complete-test`/turnkey/coordinator route according to the current architecture. Preserve the simple operator flow; keep internal hashes, source-binding mechanics, and plan implementation details out of ordinary user prompts where the maintained CLI already resolves them.
- Update all affected source and packaged JSON Schemas together, semantic validators, capability advertisements, configuration resolution, application/mode plans, authorization bindings, runtime adapters, result schemas, summaries, progress logs, tests, examples, and documentation. Use explicit extension/version rules of the owning Harness contracts; do not confuse Harness schema versions with Pico control, WTP, transport, or storage versions.
- Validate document shape before field access. Reject unknown target/engine/carrier, missing/extra fields, wrong types/units, unsupported versions, invalid identities, stale revisions, inconsistent returned descriptors, invalid frequency/message limits, and source/boot/profile mismatches before writes or RF.
- Report Pico-specific provenance rather than fabricated Pi process fields. Distinguish controller/helper identity, physical Pico identity, observed boot/firmware/image, engine/topology, actual settings, target source, receiver, analyzer, and capture identity. Record descriptive unknowns honestly; only safety/capability/identity bindings needed for correct operation are admission gates.
- Retain exact-count IQ metadata, continuity/truncation checks, capture hashes, full decoder stdout/stderr, analysis inputs/outputs, uncertainty/resolution, mode/job IDs, transaction boundaries, terminal observations, and cleanup/restoration results in schema-validated private result bundles outside Git.
- Preserve the existing independent observation requirements: do not count repeated messages within one transaction as separate independent captures when the contract requires three transactions. Do not fabricate absent captures or a passing aggregate for early-stop runs.
- Preserve finite command, readiness, acquisition, transmit, capture, analysis, cancellation, and cleanup deadlines. Maintain durable progress JSONL output and the exact viewer command before long-running work. Distinguish counting units, skipped/unattempted cases, and expected refusals.
- Results must distinguish transmitter failure, receiver/fixture blockage, unavailable prerequisite, abort, inconclusive measurement, and cleanup failure. Cleanup failure takes precedence over otherwise successful measurements. A decode is not spectral compliance, calibrated power, or general all-band qualification.

## Ownership, safety, and restoration

Implement the live path even though the full physical campaign belongs to Phase 2:

1. Discover exact device/serial/physical topology and output resources before use. Check active owners, schedules, queued/armed/running jobs, current service state, and other work. Never stop another owner's job or take over an occupied board to make a test proceed.
2. Resolve the full RF path once for the selected engines/modes: exact output, antenna state, termination, attenuator/combiner/filter routing, receiver identity and safe-input basis. Use current reliable evidence. Do not infer safe termination from historical wiring notes. Collect genuinely missing physical facts in one concise request only when necessary.
3. Snapshot original firmware/bundle reference, settings and their domains, engine/pin allocation, time/correction selection, schedule/suspension state, and host/receiver/reference configuration before any selected mutation. Protect credentials and precise location; redact public summaries without weakening private evidence.
4. Register cleanup and ownership before any RF-capable effect. Establish receiver readiness and RF-off preamble before ARM, then capture the required post-job silence and independent Pico terminal/output evidence.
5. Abort only owned work through supported interfaces; reconcile ambiguous outcomes before issuing another job. Bound retries and never replay an uncertain ARM automatically. Verify idle, empty/unowned state as appropriate and engine-specific output inactivity; process exit or a missing USB handle is insufficient.
6. Handle Pico resets, changed boot identity, USB disconnect, partial/late responses, lost acknowledgements, receiver failure, decoder failure, controller cancellation, timeout, and restoration refusal. Retain original and cleanup errors together. Do not erase evidence to convert a refusal into a pass.
7. Restore only the changes the run owns, using production management/installer transactions and verified readback. Do not automatically resume a previously enabled transmission schedule without a deliberately specified handback policy. Report a restore-pending state truthfully if safe restoration is not established.
8. If firmware deployment becomes necessary for an explicitly selected development check, use Pico `scripts/usb_installer.py` and the exact generated developer bundle with same-board reference and postboot verification. Retain the bundle. Never substitute direct `picotool load`, edit installer receipts, or delete references to bypass a refusal.

## Implementation and test sequence

### A. Inventory and contract design

Trace reusable components, identify actual gaps, and choose the smallest coherent Pico integration. Describe how each of the four configurations reaches all five production mode coordinators and how GPS/correction subcases are bound. Record necessary design decisions in existing appropriate engineering documentation, not a replacement backlog or permanent execution diary.

### B. Implement the complete path

Implement plans, schemas, semantic validators, production WTP/management transport adapters, actual job submission/lifecycle, capture/analysis integration, result/aggregate reporting, cleanup/restoration, and CLI/capability routing together. Preserve existing Pi GPIO/Si5351/RP1 behavior and source-bound test inventories. Avoid empty scaffolding or an advertised Pico capability backed only by mocks.

### C. Deterministic and production-path validation

Derive exact commands from current registration and CLI help. Required coverage includes:

- all four engine/GPS configurations and all five modes; correction-off/on subcases where supported; independent manual, transmitter, and receiver corrections;
- valid complete jobs plus boundary/overflow/unsupported-frequency/message refusals;
- wrong device/boot/firmware binding, malformed/unknown descriptors or schemas, wrong field types/units, missing/extra fields, stale revisions, and refusal before writes;
- GPS disabled, usable GPS/PPS, missing serial/PPS, stale/unpaired/conflicting observations, missing CLK2 feedback, learned correction frozen per job, and explicit correction refusal without fallback;
- actual production Pico host drivers/handlers and maintained WTP/management clients for serialization, framing/ACK, negotiation, configuration, ownership, LOAD/ARM, status/event interpretation, ABORT, terminal reconciliation, and release;
- lost/delayed replies, partial frames, disconnect/reset, lease expiry, replay refusal, receiver readiness/capture failure, truncation, decoder failure, timeouts, cancellation, ownership conflicts, and failed cleanup/restoration;
- plan/rehearsal/schema validation that opens no devices and performs no host/network/service/RF effects; unsupported live platforms refuse before mutation;
- synthetic known-truth analysis and retained sanitized offline replay where appropriate, including inconclusive carrier comparisons when uncertainty exceeds the improvement being measured;
- separate capture/transaction identities and exact nonempty coverage; native Windows path forms and paths with spaces; no unsupported platform assumptions in the portable core;
- unchanged existing Pi five-mode, RP1, lifecycle, prepared-publication, calibration, and progress behavior.

Mock faults are necessary but do not replace software integration through production source paths. Conversely, host drivers and synthetic IQ do not establish physical RF acceptance. The full real-board/receiver matrix remains Phase 2. Phase 1 completion does not require starting that matrix or an additional physical campaign; no current bench configuration is asserted by this saved prompt.

Run the current complete Harness acceptance set required for a cross-cutting change: formatting/lint, typing, Python tests, package build, native helper build/tests, schema/package consistency, installed-package verification, and supported-platform CI, using the checked-out instructions and actual workflow commands. Do not invent current counts or drop checks that fail.

For Pico/Pi changes, run the affected deterministic suites and canonical owning CI. Run both actual production source-pair suites for the final intended Pi/Pico pair, even if the implementation ultimately changes only the Harness. Any changed shared/control/protocol-facing integration must be included in those selected sources. Select intended candidate sources by full SHA and dependencies explicitly:

- WsprryPi `.github/workflows/debian-non-hardware.yml` `wtp-network-loopback`, including runtime, interop, configuration, source-selection, routing, and required browser gates;
- `wtp-usb-management-pair`, including the actual candidate Pico `usb_management_driver`, Pi pair-client build, management tests, and `WsprryPi-UI/tests/wtp_usb_pair_test.js`.

Preserve current control prerelease policy: one current major/namespace/contract at 1, strict closed validation, no historical control views, and independent WTP/transport/storage versions. Select the actual edited Pico source; do not qualify stale snapshots or relax validators to manufacture compatibility. Failed, cancelled, timed-out, skipped, empty, or wrong-source required checks remain unresolved.

For changed documentation, run current strict documentation/link checks and `git diff --check`. Inspect untracked text separately. Do not download SDKs or rebuild unrelated firmware merely for prose or formatting. Public operator documentation stays on Read the Docs; add no GitHub Pages deployment.

### D. Adversarial review, repair, and reassessment

**Perform an adversarial review.** Challenge whether Pico is truly a production target rather than a renamed Pi backend, whether every matrix row and mode reaches real control code, whether time/correction and receiver calibration are independent, and whether shutdown and restoration are independently observed.

Also challenge schema drift, hidden fallback, device/boot confusion, false no-write claims, asynchronous lifetimes, unsafe resource ownership, job replay after uncertainty, false capture readiness, incomplete transaction counts, overbroad RF claims, lost legacy coverage, fake platform support, secrets in artifacts, and accidental inclusion of user work.

**Iterate through issues, close them, and run another adversarial assessment.** Fix actionable findings, add meaningful defect/failure coverage, rerun affected checks, and reassess the corrected complete candidate. Do not call the work complete with an actionable finding, a required failed/skipped check, or an intended companion interface left unvalidated.

### E. Deliver Phase 1

**When done, commit and push. Then report.**

- Commit only understood task-owned changes in each affected repository. Preserve authorship and unrelated user edits. Use normal project branches/PR workflows, `codex/` branch names by default, no force pushes or branch-protection bypasses.
- Push the complete candidate without CI-skip markers, follow required CI through completion, fix failures, and rerun affected acceptance. A commit or green old run is not completion for the pushed candidate.
- Follow the owning repositories' normal merge requirements under the standing authority; no feature merge is required merely to satisfy the instruction to commit and push. Keep any PR reviewable and accurately describe its final scope, evidence, and remaining physical qualification. Do not merge unrelated work or publish a release. Report which refs contain every companion change; do not claim delivery on `devel` when changes exist only on a side branch.
- Update checklist item 1 to ⏳ during execution and ✅ only when its complete implementation and required software validation are finished. Leave items 2 and 3 ▧. Consolidate useful current instructions into maintained guides and retire this task-specific prompt when its completed handoff duty ends, repairing the checklist link rather than archiving it.
- The final report must include implementation/CLI changes, matrix and subcase coverage, exact source/dirty states and dependencies, exact commands/counts/results and CI links, adversarial findings and disposition, commits/pushes/PRs, any host/device effects and restoration, platform limits, and concrete blockers. State explicitly that Phase 2's exact-artifact physical campaign and Phase 3 publication have not been performed.

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

You have authority to operate and configure the GPS-disciplined oscillator associated with wspr5.  Authorized operations include:

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
