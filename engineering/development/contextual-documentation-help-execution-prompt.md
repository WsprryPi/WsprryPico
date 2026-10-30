# Item 12 execution prompt — Contextual Read the Docs help

Status: saved execution prompt; not started. Saving, printing, reviewing or committing this document does not execute it. Execute only when explicitly assigned. Use the full standing execution authority below for that session.

Implement contextual Read the Docs help throughout the WsprryPico browser interface.

The objective is to let an operator open a thorough, relevant explanation directly from every major section and selected subsections or fields. Explain both the product and what the operator needs to make it work. Complete the implementation, documentation, validation, adversarial review, corrections, commit and push, then report.

1. Scope and starting state

Primary repository:
  /Users/lbussy/GitHub/WsprryPico

Companion repositories:
  /Users/lbussy/GitHub/WsprryPi
  /Users/lbussy/GitHub/WsprryPi-Docs

Keep the implementation focused on contextual help for the Pico’s own interfaces. Change companion repositories only where this task requires shared-component coordination, a companion correction, or a relevant documentation cross-link. This is not a general UI redesign, repository cleanup, protocol migration or hardware qualification task.

Read all applicable AGENTS.md files and the Pico README.md, CONTRACT.md, engineering/architecture.md and engineering/development/README.md before implementation.

A read-only orientation on October 30, 2026 found:
- WsprryPico: branch codex/control-contract-reset, HEAD e36f22f41cc48fc9ca5f741a024ebf12c5b79f6b.
- WsprryPi: branch codex/control-contract-reset, HEAD d9beda14f4387a538501fc3ed36f02986c9ed251.
- WsprryPi-Docs: branch codex/control-contract-reset, HEAD 17a179e940491c5a3d42cf007d4c5d423146e857.
- All three checkouts contain existing changes. Pico and Pi contain substantial coordinated control-contract work, including staged, unstaged and untracked files.
- The Pico and Pi branches had no configured upstream.
- These observations are orientation, not proof of the state when you execute this prompt. No implementation or runtime validation was performed for this contextual-help task.

Inspect and record the current branch, HEAD, upstream, staged changes, unstaged changes and untracked files in each affected repository before editing. Preserve the existing working tree and index. Do not treat pre-existing staged work as part of this task merely because it is staged.

Use the actual intended candidate sources, including relevant existing changes. Do not silently switch to an older clean HEAD or companion snapshot to obtain passing checks.

2. Review-informed implementation context

Verify these observations against current code:

- The admitted operator interface is in src/network/web/index.html, style.css, app.js and organization.js, with supporting modules.
- Station Control contains Transmitter status, WSPR Configuration, Time and calibration, Radio pins, CW Modes, conditional Review saved settings, and About this Pico / Diagnostics.
- Wi-Fi/Host contains Wi-Fi network, Pico password, Device hostname and Logging, including UDP and USB logging.
- Initial Wi-Fi setup, optional station commissioning and reset/recovery interfaces are in src/network/bootstrap_web/.
- LPF/band selector controls and UDP logging controls include dynamically generated content. Related components also exist in the Pi UI; inspect affected companion usage before changing shared interfaces.
- Current operator and setup HTML has no contextual Read the Docs help links.
- Non-status operator sections use native details/summary disclosures. Settings sit within disabled fieldsets when locked. Help must remain usable in the relevant locked, collapsed and unavailable states.
- organization.js handles area navigation, bookmarks, Top, History state and sensitive save/hostname continuation fragments. It also protects unsaved drafts during navigation.
- Recent changes merged station identity into WSPR Configuration, simplified message-schedule controls and recovery, refined locked presentation, and added zero as an unlimited NTP holdover selection.
- Some manual prose still uses older UI terminology. For example, configure.md and the first-WSPR walkthrough describe “Schedule period / phase,” while the current field reads “Schedule interval / offset (seconds).” Reconcile task-relevant wording against actual behavior.
- The Pico owns its standalone operator manual in WsprryPico/docs/. WsprryPi-Docs owns Pi connections, Fleet, controller scheduling, CLI/INI and Pi-managed installation.
- Pico documentation uses Sphinx/MyST, heading anchors, pinned requirements and .readthedocs.yaml.
- scripts/check_documentation.py checks local targets and built-site links, but deliberately skips external URLs. It does not establish that firmware help URLs or remote fragments resolve.
- scripts/build_operator_assets.mjs and scripts/generate_web_assets.py maintain and verify shipped minified scripts, source hashes, embedded documents and CSP hashes. Source-only browser checks do not establish shipped-asset correctness.

The existing Pico manual base is:
  https://wsprrypico.readthedocs.io/en/devel/

The existing companion manual base is:
  https://wsprry-pi.readthedocs.io/en/devel/

Live verification was unsuccessful during orientation: the web reader could not retrieve the pages, and an unsandboxed HTTP attempt returned 403. This is a verification limitation, not evidence that the public documentation is generally unavailable. Verify actual publication, redirects, pages and fragments during execution.

3. Inventory and documentation coverage

Before editing, inventory every rendered major section, meaningful nested group, modal and setup/recovery surface. Include dynamically mounted controls and relevant states. Map each help entry to a precise operator question and documentation destination.

Cover every major section. Add subsection or field links where they answer a distinct question; avoid repetitive links beside every straightforward input.

Use this initial mapping as a starting point. Inspect the content and rendered anchors before adopting a destination:

UI topic                              Candidate documentation
------------------------------------  ------------------------------------------
Getting started / requirements        start.html, install.html, connect.html
Transmitter status                    operate.html#read-the-status-console
Stop, ownership and connection loss   operate.html#status-stop-and-connection-loss
WSPR Configuration                    configure.html#wspr-configuration
Station identity                      configure.html#station-identity
WSPR dial and schedules               configure.html#frequency-and-schedules
Automatic WSPR message types          operate.html#automatic-wspr-plan
Time and calibration                  configure.html#time-and-calibration
NTP timeout and clock state           reference/time.html
Manual RF correction                 reference/time.html#manual-frequency-correction
Radio pins and drive                  configure.html#pins-and-drive
Amplifier control                     configure.html#amplifier-lead-and-tail
LPF / band selector                   configure.html#lpf-and-band-selector
LED and external button               configure.html#led-and-button-settings
CW Modes                              operate.html#send-qrss-fskcw-or-dfcw
Recurring message schedule            operate.html#repeat-a-message-on-a-schedule
Timing settings / job-file loading    Dedicated anchors within relevant operation guidance
Review saved settings                 configure.html#understand-what-was-saved
Uncertain save recovery               configure.html#recover-an-uncertain-save
About this Pico / Diagnostics         maintain.html#support-information
Wi-Fi setup                           connect.html#first-wi-fi-connection
Changing saved Wi-Fi                  maintain.html#change-wi-fi
Pico password                         maintain.html#change-the-pico-password
Occupied-login recovery               maintain.html#recover-an-occupied-login
Device hostname                       maintain.html#change-the-hostname
Logging overview                      Relevant overview linking USB and UDP procedures
UDP logging                           udp.html#configure-export
USB logging                           usb.html#usb-diagnostic-logging
Initial station commissioning         configure.html#station-identity
Reset and recovery                    maintain.html#recovery-and-reset
Access/security explanation           reference/security.html
Output requirements and limits        reference/output.html
Pi-controlled operation               wsprrypi.html and appropriate companion-manual topics

Do not link a narrow field to an unrelated broad page simply to claim coverage. Add substantive explanations and stable targets where the existing manual lacks an appropriate destination. Reuse existing pages where practical.

Particularly useful field/group explanations include:
- Callsign forms, four/six-character locators and the resulting WSPR plan.
- Reported WSPR dBm versus physical RF power and GPIO drive strength.
- WSPR USB dial versus RF center, and direct RF frequency in CW modes.
- Schedule interval, offset, UTC, expiry, enablement and application.
- Zero versus finite NTP timeout, initial synchronization and uncertainty.
- Manual ppm correction versus UTC synchronization.
- GPIO versus physical header numbers, exclusive roles and restart requirements.
- Amplifier polarity, lead/tail and external control circuitry.
- Filter coverage, selection policy, settling, modulation/correction coverage and external drivers.
- CW mode frequency meanings, shift, timing multipliers, repeats and repeat gaps.
- One complete job versus recurring schedules, duration/event limits and prepared job files.
- Saved drafts, complete configuration, applied settings, boot-active hardware and readiness.
- Pico password versus Wi-Fi password, hostname changes and reconnection.
- Independent USB/UDP logging settings, severity, network exposure and delivery uncertainty.

Maintain a compact coverage inventory during implementation. Record deliberate omissions of subsection/field links and their rationale.

4. Interaction and presentation requirements

Preserve the incumbent light interface, native controls, typography, spacing, focus treatment, navigation and responsive behavior. Use applicable Impeccable guidance for this focused extension without broadening into a redesign.

- Add recognizable, consistently placed contextual help links near their associated headings or controls.
- Preserve section-heading disclosure behavior. Do not replace the section toggle with documentation navigation.
- Keep section help discoverable while the section is collapsed.
- Use genuine anchors with meaningful accessible names. A compact visible label such as “Help” is acceptable when its accessible name identifies the topic.
- Preserve form labels and accessible descriptions. Avoid ambiguous icon-only links, interactive content inside labels, and arrangements that interfere with native summary behavior.
- Test the chosen summary/help arrangement using real pointer and keyboard interaction.
- Keep help available without authentication and when editing or transmission controls are disabled. Do not weaken those controls.
- Include appropriate help within access/recovery dialogs where the modal background is inert.
- Open documentation in a separate tab using native link behavior. Include rel="noopener noreferrer" and a clear, unobtrusive indication that help opens online in another tab.
- Preserve ordinary modifier-click, context-menu and copy-link behavior.
- Retain visible focus, readable contrast, adequate touch targets, wrapping and usable layout on narrow screens and at zoom.
- Preserve current local guidance about units, prerequisites, errors, recovery and operating consequences. External help supplements the instructions needed to use the device.
- Explain that online documentation needs Internet access, especially on setup Wi-Fi. Do not require Internet access for setup or operation.
- Do not add automatic documentation requests, prefetching, connectivity probes, remote scripts, fonts, analytics, embedded remote content or an Internet-dependent help loader.
- Do not expose device identity, local addresses, session material, receipt data, settings or entered values in documentation URLs, queries or referrers.
- Opening help must not submit a form, mutate configuration, authenticate, acquire ownership, renew a session, start a job, enable a schedule, reset the Pico or exercise logging.
- Opening help must preserve raw drafts, invalid input, selected files, disclosure state, current task area, session state and pending save/recovery continuations.
- Do not rewrite the existing #save= or #hostname-return= fragments or their History data to implement documentation links.

Provide a simple manual/getting-started entry point in addition to contextual links.

5. Documentation and URL design

Write complete operator explanations in direct, impersonal language. Use current UI labels and practical procedures. Define unfamiliar terms and units where first needed.

For each linked topic, explain:
- What the feature does.
- Required hardware, network, credentials or prior configuration.
- Meaning, units and applicable bounds of its settings.
- What Save, Apply, Restart and readback mean for that feature.
- Expected results and common reasons the action is unavailable.
- Appropriate recovery after refusal, lost connection or uncertain replies.
- Relevant limitations and prerequisites for actual operation.

Verify factual details against current production code and contracts. Correct task-relevant documentation drift; do not turn stale prose into a new product requirement.

Preserve the distinctions between software observations and measured hardware/RF behavior. Do not imply that reported power controls output power, clock synchronization calibrates RF, selected GPIO proves relay position, or a running job proves received RF.

Use HTTPS URLs to rendered Read the Docs HTML and precise fragments. Do not use repository Markdown URLs as operator help, relative device-hosted documentation paths, fabricated branch versions or unverified anchors.

Choose an explicit documentation-version policy appropriate to this development candidate. The current /en/devel/ base is the starting convention, not permission to assume every future firmware version has a corresponding RTD version. Centralize the base or mapping sufficiently to maintain it without scattering inconsistent URLs.

Do not derive documentation versions from the control major, arbitrary Git branch names or unvalidated runtime input. Do not introduce protocol fields or capability advertisements merely to carry help links.

Use stable explicit MyST/Sphinx targets for new help destinations where heading renames would otherwise break firmware links. Preserve existing published anchors when changing headings. Validate actual generated HTML IDs rather than guessing slugs.

Keep publication on Read the Docs. Do not introduce GitHub Pages, Pages workflows, publishing branches or related settings.

Respect documentation ownership:
- Pico standalone/browser/device instructions remain in WsprryPico/docs/.
- Pi/Fleet/controller instructions remain in WsprryPi-Docs.
- Cross-link the relevant task rather than duplicating whole procedures.
- Engineering contracts and implementation narratives remain outside operator help.

Coordinate publication so newly shipped help links resolve to published content. A local Sphinx build or a pushed feature branch does not establish that /en/devel/ contains new targets.

6. Implementation constraints

Prefer the smallest maintainable implementation consistent with complete coverage.

- Keep links declarative where possible.
- Use a small auditable topic mapping or build-time mechanism if it usefully prevents duplication. Avoid a new runtime help service or framework.
- Cover static HTML, generated controls and embedded/shipped documents.
- Prefer placing presentation links in the Pico’s composition layer when that avoids unnecessary changes to shared component interfaces.
- If a shared component interface must change, inspect and update every affected Pi/Pico consumer and meaningful test adapter together.
- Preserve firmware resource bounds and CSP protections. External navigation is not a reason to loosen connect-src, script-src, form-action or other security policy.
- Rebuild generated assets using the checked-in pinned tooling when their sources change. Do not hand-edit minified output or manifests.
- Do not change schemas, authentication, session policies, persistence, scheduling, carrier negotiation, job admission or RF behavior as part of adding help.

If a necessary change reaches advertised capabilities, protocol/API schemas, descriptors, carrier support, wire formats, limits/units, session policies or protocol-facing interfaces, apply the complete coordinated Pi/Pico gate in AGENTS.md. Do not evade it by calling the change cosmetic.

Preserve Wsprry-Control/1 and the current prerelease policy. Do not add historical compatibility views, relaxed validation, arbitrary version ranges or hidden fallback.

7. Validation

Derive commands from current checked-in development guidance and workflows. Record exact source revisions and tested uncommitted changes.

Add meaningful regression coverage for:
- Coverage of every major section and the selected deeper topics.
- Valid HTTPS host, intended documentation version, page and fragment.
- Destination existence against an independently built current manual.
- Static, dynamically rendered and shipped/embedded links.
- Help availability in locked, collapsed, setup, recovery and unavailable states.
- Native keyboard/pointer activation, focus and summary behavior.
- Preservation of drafts, invalid text, selected files and pending continuations.
- Absence of application mutations caused by help activation.
- Absence of automatic external requests and sensitive URL/referrer data.
- Mobile layout, zoom, long headings and accessible naming.
- Useful failure when a page or anchor is renamed or removed.

Do not rely solely on tests that compare a mapping to itself. Validate emitted URLs against generated documentation. Remote HTTP success alone does not validate a fragment, because fragments are not sent to the server.

Reuse and extend relevant existing tests, including:
- tests/operator_asset_build_tests.py
- tests/ui_access_browser_tests.js
- tests/ui_sections_browser.mjs
- tests/organization_browser_integration.mjs
- tests/operator_cleanup_browser.mjs
- Relevant setup/recovery and dynamic-component tests.

Exercise consumer and engineering operator surfaces through the existing production-handler fixtures. Keep fixed-port fixture runs sequential where required.

Use the existing pinned bootstrap package for relevant tests and asset regeneration:
  npm --prefix src/network/bootstrap_web test
  npm --prefix src/network/bootstrap_web run build

For the Pico manual, use the existing documentation environment:
  docs/.venv/bin/python -m sphinx -E -a -n -W --keep-going -b html docs docs/_build/html
  docs/.venv/bin/python scripts/check_documentation.py
  docs/.venv/bin/python tests/test_image_delivery.py

If companion documentation changes, follow that repository’s environment and build instructions, including activating docs/.venv before Sphinx commands.

Validate the exact shipped assets through the established generator/build checks. Reuse retained dependencies; do not download an SDK as an incidental formatting or documentation step.

Inspect one batched desktop/mobile visual review of the implementation, fix the concrete defects found, and perform a confirmation pass. Additional passes should follow substantive changes or unresolved defects.

Check live Read the Docs destinations and fragments after publication through the normal authorized workflow. Do not hide a failed check by dropping the fragment or routing all help to the manual root.

Run git diff --check and inspect newly created files separately.

If the coordinated contract gate applies, both production source-pair suites must pass for the intended candidate:
- WsprryPi .github/workflows/debian-non-hardware.yml:
  wtp-network-loopback
  wtp-usb-management-pair
- Network coverage includes wtp-network-runtime-test,
  wtp-network-interop-test and wtp-config-interop-test.
- USB coverage includes the actual Pico usb_management_driver,
  wtp-usb-pair-client-build, wtp-usb-management-test and
  WsprryPi-UI/tests/wtp_usb_pair_test.js.
- Select the actual candidate Pico source and required pinned dependencies explicitly.
- Use the checked-in recipes, including recursive MbedTLS
  0bebf8b8c7f07abe3571ded48a11aa907a1ffb20 where required.
- Failed, skipped, cancelled or timed-out required checks remain unresolved.

These are hardware-free software checks. Hardware deployment and RF testing are not required merely to add documentation links. If hardware becomes necessary, follow the standing authority and existing installer/device-identification requirements.

8. Adversarial review and correction cycle

Perform an adversarial review of the implementation and documentation.

Challenge at least:
- Missing sections or hidden dynamic controls.
- Superficial destinations that do not answer the operator’s question.
- Incorrect labels, units, limits, prerequisites or save/apply behavior.
- Wrong documentation product or version.
- Missing, unstable or unpublished fragments.
- Help unavailable precisely when controls are locked or setup has failed.
- Summary toggling, form submission or focus changes caused by link activation.
- Lost drafts, selected files, receipts or recovery state.
- Sensitive data disclosure.
- Unexpected Internet dependencies or weakened CSP.
- Source/generated asset disagreement.
- Shared-component regressions and unintended companion changes.
- Tests that miss production paths or merely reproduce implementation assumptions.
- Accidental inclusion of pre-existing work in commits.

Track actionable findings with severity, evidence, correction and verification. Keep temporary review notes outside maintained product documentation.

Fix the findings, rerun affected checks and close each issue with evidence. Then perform another adversarial assessment against the corrected result.

Repeat when substantive findings remain. Do not claim completion while an actionable in-scope defect, broken required link or required validation failure is unresolved. Clearly distinguish an external blocker from a completed task.

9. Commit, push and report

After implementation, documentation, applicable checks and the final adversarial assessment succeed:
- Inspect the final task diff and generated outputs.
- Commit only validated changes belonging to this task.
- Preserve pre-existing staged and unstaged work, including overlapping files.
- Do not use blanket staging or commit unrelated staged changes.
- Use safe isolation where needed without discarding or rewriting the original working tree/index.
- If task-only commits depend on uncommitted prerequisite work that cannot be safely separated, identify the precise delivery blocker rather than absorbing that work without authorization.
- Push to the appropriate configured project remote using normal safeguards and the established workflow.
- Resolve the observed lack of upstream deliberately; do not guess a remote destination or overwrite shared history.
- Inspect relevant resulting CI and RTD builds, fix task-caused failures and rerun affected checks.
- Do not claim delivery on devel or main when changes exist only on another branch.
- Do not create a stable release or flash devices merely to finish this help-link task.

Then report concisely:
- What changed and where.
- Section/subsection/field coverage and deliberate omissions.
- Documentation destinations, version policy and publication status.
- Important review findings and how they were closed.
- Exact checks and results, source-pair identities where applicable, and CI/RTD links.
- Commit IDs, pushed branches and actual repository state.
- Remaining unrelated user changes.
- Any limitations or unresolved blockers.
- Whether any devices, services or hardware were changed.

The following standing authority applies when executing this prompt, within the task scope above.

Wsprry Development Session — Standing Execution Authority

1. General Authority

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

2. Authorized Repositories

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

3. Docker and Container Infrastructure

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

4. Authorized Raspberry Pi Hosts

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

5. Authorized Raspberry Pi Pico Devices

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

6. RF Transmission Authority

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

7. SDR Authority — wspr5

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

8. GPSDO Authority — wspr5

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

9. Computer, Browser, and Developer Tools

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

10. Autonomous Execution and Recovery

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

11. When Human Confirmation Is Required

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

12. Communication Expectations

Operate with minimal interruption.

* Do not request permission for routine authorized operations.
* Do not repeatedly seek reassurance that a chosen implementation is acceptable.
* Do not pause after each intermediate step.
* Do not convert progress reports into approval gates.
* Provide concise progress updates for significant milestones.
* Surface material blockers, safety concerns, or irreversible decisions promptly.
* At completion, provide a concise summary of work performed, verification evidence, Git state, deployed devices, and outstanding issues.

Default operating principle: If the action is necessary for the assigned task, within the explicitly authorized scope, technically reversible or reasonably safe, and not prohibited by a higher-priority policy, proceed without asking.
