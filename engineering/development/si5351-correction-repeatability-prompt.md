# Item 21 execution prompt: Si5351 automatic carrier-correction repeatability

## Activation and objective

This is a saved execution prompt for unfinished backlog item 21. Saving or linking it does not execute it. Execute it only when the user explicitly invokes this task. The standing authority below applies to that execution and its reasonable dependencies.

Investigate why Si5351 automatic carrier correction varied between the recorded repeats. Establish the causal chain from calibration observations to selected estimates, frozen job correction, synthesizer register realization, and measured RF. Determine what needs fixing, implement justified fixes, and validate them. Do not assume there is a firmware defect, that longer observations alone solve it, or that a passing build establishes repeatable RF improvement. Distinguish proven causes, contributors, hypotheses, and remaining uncertainty.

Perform an adversarial review. Iterate through issues, close them, and run another adversarial assessment. When the work and required validation are done, commit and push the validated changes, then report.

## Scope, starting state, and evidence

Work primarily in `/Users/lbussy/GitHub/WsprryPico`. Authorized companion repositories are `/Users/lbussy/GitHub/WsprryPi` and `/Users/lbussy/GitHub/WsprryPi-Docs`; change them only where this task requires it. Inspect current branch, HEAD, remotes, divergence, worktrees, and tracked/untracked changes separately in each repository before editing. Preserve user work, and avoid bundling unrelated changes. Use a `codex/` branch under the established workflow unless the user's execution instructions specify another destination. Do not infer that historical revisions or connected hardware still describe current state.

Read applicable AGENTS.md files, README.md, CONTRACT.md, engineering/architecture.md, and engineering/development/README.md before implementation. Read these Pico documents and their relevant linked contracts:

- [Backlog item 21](consolidated-backlog.md).
- [GPS/PPS validation and close-spaced comparison](gps-pps-validation.md#close-spaced-carrier-comparison).
- [Machine-readable measurement record](gps-pps-validation.json), especially `close_spaced_carrier_comparison`.
- [GPS/PPS contract](gps-pps.md), [Si5351 implementation](si5351.md), [continuity validation](si5351-continuity-validation.md), and [UTC/RF contract](clock-discipline.md).
- [Software/build CI contract](software-build-ci.md), plus the current Pi `.github/workflows/debian-non-hardware.yml` source-pair recipes.

Historical evidence: the comparison used Pico C source `8abeb40aef71`, control helpers `29108844`, a 138 MHz profile, and 24 finite 12-second tones, with two off/on repeats per engine at 1,840,100, 5,366,200, and 28,126,100 Hz. Historical captures, snapshots, and analysis were retained on wspr5 at `/home/pi/close-tone-20261103`; locate and inspect them read-only first. Verify hashes, source identities, sequence, and timestamps against the tracked record. Missing raw evidence must be reported; do not silently reconstruct observations from summaries.

The recorded Si5351 baseline/corrected errors in Hz were:

| Band | Baseline repeats 1 / 2 | Corrected repeats 1 / 2 | Largest recorded allowance |
| --- | --- | --- | --- |
| 160 m | -0.148 / -0.146 | +0.192 / +0.075 | ±0.089 Hz |
| 60 m | -0.458 / -0.455 | +0.538 / +0.189 | ±0.127 Hz |
| 10 m | -2.770 / -2.809 | +2.448 / +0.600 | ±0.431 Hz |

GP2 passed the comparison's improvement criterion on all three bands. Si5351 did not demonstrate consistent improvement beyond the declared allowances. GPS/PPS implementation, Si5351 support, and the accepted roughly one-second launch-timing scope are complete; this task does not reopen them without specific causal evidence. The RSPduo, additional PPS hardware, broad temperature qualification, and submillisecond launch timing are not prerequisites.

## Investigation: explain the variation before changing policy

1. Reconstruct a chronological per-job ledger from the actual captures and control responses. Include board/boot/image identity, engine, nominal frequency, off/on mode, observation start/end and original ages, pulse/count deltas, capture bounds, estimate value/units/sign/uncertainty/span, generation, quality/admission decisions, selected source, manual residual, frozen LOAD plan, ARM state, reported adjustment, programmed register plan, and measured error/allowance. Explicitly mark unavailable fields. Keep sensitive position, credentials, and raw captures out of tracked files.
2. Trace the real producer and every consumer. Starting points include `src/time/gps_calibration.*`, `src/rf/calibration.*`, `src/rf/si5351_observation.*`, `src/rf/si5351_plan.*`, `src/rf/si5351_job.*`, `src/rf/si5351_engine.*`, `src/rf/si5351_device.*`, SDK capture adapters, and application selection/freezing paths. Discover the actual call graph rather than assuming filenames prove responsibility. Compare relevant historical implementation with the current candidate and identify intervening changes.
3. Check calibration estimates independently: Pico timer versus Si5351 TCXO source, CLK2 nominal versus actual configured reference frequency/dividers, coherent PPS/count snapshots, counter wrap/overflow, tick scale, integer-second association, missed/ambiguous edges, clock-domain conversion, sign and ppb/ppm/Hz conversions, rounding/overflow, original observation ages, generation changes, uncertainty propagation, stale/reacquired sources, and warmup/reset behavior. Check whether the RF/CLK2 plan changes perturb the measurement source or acquisition baseline.
4. Check observation spans: actual elapsed span versus declared/minimum span, sample count and PPS interval, retained history, short-window quantization, capture jitter, span-dependent uncertainty, source settling, and scheduling sequence. Determine whether different spans or generations quantitatively explain the different correction magnitudes. Replay known-error observations and deliberately vary arrival delay, span, age, and phase while retaining the original edges. Do not use serial arrival time as the PPS boundary or relabel old observations as fresh.
5. Check selection and frozen state: estimator output versus selected correction versus accepted LOAD correction, manual residual applied exactly once, independent engine settings, no NTP-derived RF correction, no Pico-rate substitution for Si5351-rate correction, and no live-generation replacement of a frozen job. Inspect delayed ARM, subsequent estimate updates, repeat jobs, reset/restart, and interrupted acquisition.
6. Check engine realization with an independent calculation: derive output frequency from the actual PLL/multisynth/R-divider register values and reference estimate. Check rational approximations, integer/fractional modes, unit/sign conversion, fixed-width arithmetic, range constraints, rounding, cache invalidation, register write order, PLL reset/settling, and CLK0/CLK2 shared-resource effects. Distinguish requested correction, ideal predicted physical output, nominal-reference register realization, reported LOAD adjustment, and measured RF. A reported adjustment is not a physical carrier measurement.
7. Revalidate the measurement method before blaming firmware. Reproduce differential-phase fits from retained IQ, check carrier identity, filtering/edge exclusion, phase unwrap, signal/noise, sample continuity, clipping/overflows, reference lock and simultaneous capture, sequence-dependent drift, and each allowance. Preserve the distinction between common SDR tuning error and sample-rate error over tone spacing. The prior approximately 0.05 Hz sample-rate contribution was not the total uncertainty. Treat GPSDO accuracy as its declared assumption unless independently calibrated.
8. Quantify the explanation. For each corrected repeat, compare the independently predicted shift with the observed shift and combined allowances, including pairing/temporal drift. Use controlled replay or a targeted counterexample to distinguish competing hypotheses. State whether the issue lies in estimation, quality selection, job freezing, register realization, harness/analysis, actual oscillator variation, or a combination. Stable baselines and variable corrections are evidence to explain, not sufficient proof of a cause.

## Fix and deterministic validation

Make the smallest coherent production fix supported by the causal evidence. Do not hide the issue by weakening measurement allowances, disabling correction, changing the target, choosing only favorable repeats, adding undocumented fallback, or forcing a constant/manual trim. If no production defect is established, correct only demonstrated harness/analysis/documentation faults and clearly state what remains unknown.

Add meaningful regressions that fail for the demonstrated defect and exercise observable behavior through the production paths. Use independent expected values rather than duplicating the implementation. Include relevant positive/negative known oscillator errors, representative bands, span/quantization boundaries, ambiguity/loss/recovery, stale/short observations, original timestamps, sign/units, once-only residual, delayed ARM and frozen generations, plus register realization and CLK2 continuity where implicated. Cover GP2 against regressions without turning this into broad new qualification.

Use documented commands and inspect scripts before running opt-in tools. Select retained pinned dependencies explicitly; record the actual SDK/toolchain/MbedTLS identities. Run affected host tests, required full checks under the current CI execution contract, normal and inhibited firmware builds where affected, generated web checks if changed, and documentation/link validation. Do not call an optional subset a full pass.

For protocol-facing or management changes, inspect and coordinate both repositories before implementation. Update descriptors, strict validators, consumers, serialization, generated assets, paired adapters, and documentation together. Preserve the one current Control/1 prerelease policy, exact closed validation, identity/revision bindings, refusal before mutation, and independent WTP/transport/storage versions. Do not add compatibility views, relax validators, or substitute stale peer sources.

Before completion of this task, run both actual production source-pair suites from the current WsprryPi workflow against the intended candidate sources, even if the fix appears confined to one engine or carrier:

- `wtp-network-loopback`, including `wtp-network-runtime-test`, `wtp-network-interop-test`, and `wtp-config-interop-test`, plus current required routing/source-selection/browser gates.
- `wtp-usb-management-pair`, building the actual candidate Pico `usb_management_driver`, `wtp-usb-pair-client-build`, and `wtp-usb-management-test`, and running `WsprryPi-UI/tests/wtp_usb_pair_test.js` through the production pair, plus current required settings/gates.

Select the actual edited Pico tree and intended Pi source explicitly, with required pinned recursive dependencies. Record both revisions and any uncommitted tested differences. Failed, skipped, timed-out, or cancelled required checks remain unresolved. Resolve inherited companion mismatches rather than leaving an unvalidated follow-up. Verify final pushed refs correspond to the tested source pair; documentation-only differences must be identified explicitly.

## Conducted confirmation and restoration

Complete all useful offline investigation first. Inventory the current Pico, SDR, GPSDO, wiring, and services. Historical Pico C identity was serial `1545B6EFBF78028C`, device `c2a3a2a314c948b50a8562a1aeb69669`; verify current identity before device control or deployment. Historical wiring used GP1 UART RX, GP3 PPS, GP7 CLK2 input, GP4/GP5 I²C, and Si5351 CLK0 through a combiner/60 dB path to RSP1B with a simultaneous GPSDO reference. These facts are discovery aids, not proof of current connections.

Verify the actual appropriately terminated conducted RF path from reliable current evidence before transmitting. If verification is unavailable, continue non-transmitting work, and ask only when RF confirmation becomes necessary. Never transmit into an antenna under this authority. Snapshot current settings, flash/bundle identity, ownership/output state, services, GPSDO output/drive/mode/frequency, and SDR settings before changes. Inspect test harnesses for session lifetime, resource ownership, cleanup, and bounded requests. Use one resumed logical session per boot when appropriate rather than exhausting retained replay state with a new session per job.

Use `scripts/usb_installer.py` and the exact generated developer bundle for ordinary firmware deployment, preserving same-board references and postboot verification. Retain the bundle. Do not bypass installer refusals or leave a stale installed-image reference after low-level programming.

Predeclare a finite campaign with tone durations, repetition count, cumulative RF cap, abort conditions, test ordering, and analysis/acceptance criteria. Start with the three historical frequencies and zero manual residual. Include enough independent calibration windows and balanced/interleaved off/on repeats to distinguish estimator variation from oscillator/receiver drift; justify the count from observed variability and budget. Keep a matched before/after comparison or equivalent demonstrated reproducer. Log estimates, spans, generations, accepted plans, actual register realization where safely available, and simultaneous reference captures for each job. Additional instrumentation must be bounded and must not perturb capture/launch behavior without accounting for that effect.

Apply the historical improvement rule using each record's own allowance: the worst corrected absolute-error upper bound across repeats must be below the best baseline absolute-error lower bound. Separately establish that corrected repeat variation agrees with the modeled estimator, realization, and measurement bounds. If an already accurate baseline prevents resolving improvement, report that limit; do not manufacture a pass. Explain whether the causal defect is fixed and whether repeatable improvement is physically demonstrated as separate conclusions. Require RF evidence before claiming RF repeatability is established.

Abort on unexpected output, lost reference lock, clipping/overflows, identity mismatch, unsafe termination, or loss of control. Always perform bounded cleanup and restoration, including failures. Verify idle/unowned/inactive RF, CLK0 disabled, correct final same-board image/reference, saved settings restored, GPSDO state restored, receiver released, and original services restored. If intentionally handing back an updated image, record that choice, exact retained bundle, preserved settings, and successful installer/postboot checks. Record board, firmware, engine, clock, pins, drive, mode, reference, receiver, actual RF path, and final device/service states.

## Adversarial review and closure loop

Perform an adversarial review of the root-cause argument, production changes, tests, measurement method, paired-source proof, hardware restoration, and documentation. Actively seek disproof: confounding drift, wrong estimate/source/generation, insufficient span, stale identity, error cancellation, sign mistakes, duplicated algorithms, optimistic uncertainty, cherry-picked repeats, shared-PLL effects, false test success, and claims exceeding the evidence.

Maintain a concise issue ledger with severity, evidence, corrective action, and the check needed to close each issue. Fix every actionable finding in scope, rerun affected checks, and close issues with evidence. Then run another adversarial assessment against the revised result. Repeat until no actionable findings remain. A repeated assessment must challenge the final work; merely restating the first review is insufficient. Do not label an unavailable required check or unresolved causal question as closed. Complete independent work before reporting a genuine blocker.

Update the validation guide and machine-readable record with sanitized reproducible evidence, uncertainty, commands, source/image identities, and restoration results. Keep operator prose focused on current capabilities, and retain published documentation on Read the Docs. Preserve item numbers. Mark item 21 complete only if its remaining question is resolved with evidence; otherwise retain the unresolved status and state the exact remaining work and blocker. Once this execution prompt is completed or superseded, consolidate durable findings, remove the temporary prompt, and repair its backlog link rather than archiving it solely to retain the link.

## Delivery: commit, push, then report

After final adversarial closure and successful required validation, inspect the complete diff and repository state, stage only task-owned files, commit, and push to the configured intended remotes under the established workflow. This execution explicitly authorizes those Git operations. Do not force-push shared history, bypass protections, merge to a protected branch merely to claim delivery, publish a release, or modify unrelated work. If paired changes are required, push all intended companion refs and report their integration/merge status accurately. Monitor required CI for the final candidate pair and resolve failures before declaring completion; if fixes change code, repeat affected validation and adversarial review before the final commit/push/report.

The final report must state:

- The cause of the differing Si5351 corrections, with per-repeat quantitative evidence and confidence; identify any remaining uncertainty plainly.
- What needed fixing, what changed, and why it addresses the demonstrated cause.
- Before/after measurements, per-record allowances, calibration spans/generations, predicted versus observed realization, and whether repeatable improvement was established.
- Exact validation commands/results, both source revisions and tested differences, required network/USB results, CI links, and the final adversarial issue disposition.
- Commits, pushed branches, actual Git state in every touched repository, and delivery boundaries; do not claim `devel`/`main` delivery from a side branch.
- Installed/restored device image and bundle identities, final hardware/service/settings state, and any unresolved blockers or limitations.

Do not stop at a proposed fix when implementation and validation remain authorized and feasible. Do not claim completion solely because the investigation produced a plausible hypothesis.

---

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
