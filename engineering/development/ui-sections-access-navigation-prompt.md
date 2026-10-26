# UI sections, access and navigation execution prompt

Status: Prompt saved only. Numbered TODO items 7–10 are not started. This is the shared execution prompt linked from those items in the [consolidated backlog](consolidated-backlog.md). Saving, printing, reviewing or committing this prompt does not start implementation. Execute the work below when the user assigns execution of items 7–10.

Implement the four related changes as one coherent WsprryPico interface slice. The full **Wsprry Development Session — Standing Execution Authority** included below is part of the later execution assignment. Use it for necessary investigation, implementation, correction, validation, Git operations and recovery without routine approval gates.

## 1. Required outcome and scope

The interface serves operators who need to monitor the Pico and occasionally change settings. Keep the completed contextual Transmitter status console immediately useful while making the rest of the page compact and easy to reach.

| TODO | Required interaction |
| --- | --- |
| 7 | Furl each operator section by default except Transmitter status. Furl means collapse its body behind an accessible disclosure; its heading remains discoverable. Transmitter status stays unfurled. |
| 8 | Put a locked or unlocked icon immediately before the observed hostname. Clicking the locked icon opens a password modal. Clicking the unlocked icon locks this browser's controls using the supported logout path. Replace the obtrusive inline access panel with this deliberate access workflow. |
| 9 | Provide logically grouped menu links to the furled sections. Selecting a link selects any required task area, unfurls the target and its ancestors, then scrolls to the section. |
| 10 | Add a link labelled **Top** to each non-status section. Selecting it re-furls all non-status sections, keeps Transmitter status unfurled and scrolls back to the top/status region. |

The user explicitly corrected the Top behavior: it must re-furl the other sections. A scroll-only Top link is not sufficient. The earlier Back to Status wording is superseded by the Top label and the behavior above.

Interpret the requested lock interaction as the access state of this browser session. It does not lock every client, alter the Pico password, change Wi-Fi, stop an accepted job, disable a schedule or change transmitter ownership. Preserve the distinction between login authority and JobService ownership.

WsprryPico is the primary implementation repository. The standing authority also covers WsprryPi and WsprryPi-Docs for necessary compatibility or documentation dependencies. Keep changes in those repositories justified by this slice; reference reading alone does not require companion edits. Do not implement syslog, LPF switching, amplifier timing, character-level progression, new RF engines or other backlog items.

## 2. Establish the current baseline

- Inspect branch, upstream, worktrees, dirty/staged paths and concurrent work in every repository that will be changed. Preserve user work. Use current devel and normal Git safeguards; do not reset, stash, discard files, force-push or bypass protections.
- Read applicable AGENTS.md instructions, README.md, CONTRACT.md, engineering/architecture.md and engineering/development/README.md before implementation. Use the documented toolchain, validation and publication workflow.
- Read the [browser-page contract](browser-pages.md), [device presentation](device-presentation.md), [consumer sessions](consumer-sessions.md), [session recovery](session-recovery.md), [status-console contract](status-console.md), [browser API](../browser-api.md) and relevant authentication protocol documents.
- Read `src/network/web/DESIGN.md` and the applicable frontend skill. This is a refinement of the existing embedded interface: preserve native controls, system fonts, light palette, flat sections, focus treatment and local assets. Do not use missing optional design metadata as a reason to replace the design or stop routine work.
- Inspect source, generated assets, tests and the actual served page before selecting DOM boundaries. Record the exact baseline revision and resource sizes. At prompt preparation the local devel baseline was `fec65373251ec4702f9fc84dd5bbfd8329d20b1f`; refresh that identity when execution begins.
- Keep the existing numbered items 1–18 and their completion states. Items 1 and 6 are complete. Reuse this shared prompt for 7–10 rather than creating duplicate tasks or restoring item 6's retired execution prompt.

Use this source map as a starting point and recheck it against the execution checkout:

| Concern | Sources |
| --- | --- |
| Shared header, sections and current access markup | `src/network/web/index.html` and `style.css` |
| Authentication, actions, polling, save receipts and recovery | `src/network/web/app.js` |
| Areas, paths, History navigation and section shortcuts | `src/network/web/organization.js` |
| Hostname/title, identity and observation epochs | `src/network/web/device-presentation.js` |
| Delivered contextual status and reset interpretation | `src/network/web/operations.js` and `engineering/development/status-console.md` |
| Consumer login, logout and explicit retirement | `src/network/bootstrap_web/radio-client.js`, `src/network/consumer_radio.cpp` and `engineering/development/session-recovery.md` |
| Password-authenticated engineering SoftAP admission | `src/network/softap_api.cpp`, including existing `/local/v1/login`, `/local/v1/logout` and `/local/v1/status` routes |
| Browser build and shipped artifacts | `src/network/bootstrap_web/package.json`, `scripts/build_operator_assets.mjs` and `src/network/web/asset-build.json` |
| Existing behavioral coverage | Organization, network-browser, device-presentation, operations, consumer-session, session-recovery and saved-progress tests under `tests/` |

## 3. Define the section and navigation model

Inventory the current visible and conditional operator groups before changing markup. Record a compact mapping of each section's label, stable ID, parent task area, admission/visibility conditions, default disclosure state, menu group and Top destination.

Cover shared saved-settings/recovery, station identity, schedules/radio settings, message/job controls, Wi-Fi settings, Pico password, hostname and connection/setup guidance. Preserve appropriate nested technical disclosures and the existing Diagnostics access. The main Transmitter status console is the one always-unfurled operational section; detailed native disclosures inside it may retain their existing behavior without hiding the live summary.

Do not simply wrap existing forms in arbitrary nested sections. Avoid invalid nested forms, duplicate IDs, broken external `form` associations or duplicated editors. Retain one profile-appropriate editor for each field and existing save/apply authority.

Prefer native `details`/`summary` for ordinary disclosures when they fit the current markup. Otherwise implement a real button and controlled region with correct `aria-expanded`, `aria-controls`, keyboard behavior and hiding semantics. Keep headings, summary targets and visible focus usable on touch and narrow displays. Collapsed bodies must not remain focusable or be exposed as expanded content to assistive technology.

On a fresh ordinary page load, furl all managed non-status sections. A valid explicit section bookmark is an intentional exception: reveal that target and any ancestors. A save-recovery continuation must expose the necessary recovery instructions instead of hiding an unresolved result. Document these state-derived exceptions; do not silently refold the page during routine polling.

Opening one section need not close other sections. Preserve the operator's disclosure choices during normal status updates, typing, modal use and authentication transitions, except for deliberate Top activation or a necessary safety/recovery reveal. Do not persist authentication or passwords as presentation preferences. Avoid adding cross-visit disclosure persistence that defeats the requested defaults.

## 4. Item 7: furl sections without changing behavior

- Keep the shared contextual Transmitter status visible in both Station/Transmission and Wi-Fi/Host and while signed out. Preserve its accepted-job/future-schedule distinction, public projection, clocks, correction labels, stale-state treatment and guarded Reset Pico.
- Keep global errors, uncertain-save warnings and reset/reconnect outcomes visible or provide an obvious visible indication and a reveal action. A collapsed form must not conceal a failed mutation or an unsafe/unknown transmitter state.
- Furling and unfurling are local presentation operations. They must not submit forms, save settings, request ownership, renew a session by adding keepalives, stop polling, arm/abort a job or change schedules.
- Preserve nonsecret drafts, invalid entries, selected files, selection state and dirty/reconciliation flags by retaining the existing DOM and application state. Do not recreate forms on every disclosure toggle.
- If validation needs to focus an invalid field in a furled body, reveal its owning section and ancestors before focusing it. Avoid browser errors caused by invalid required controls being hidden or non-focusable.
- Keep existing date/time popovers, password-visibility controls and nested technical details usable. Closing a containing section must not leave focus in hidden content or a detached overlay open.

## 5. Item 8: hostname access control and password modal

### Meaning, placement and state

Place a native button with a local locked/unlocked SVG icon immediately before the hostname in the shared heading region. Preserve one H1 and the observed hostname text, title, identity and rename-pending behavior. The presentation controller currently writes `textContent` into `device-name`; separate the icon/button from that mutable text node so later observations cannot erase the control. Keep the icon out of the document title and hostname value.

Use an accessible action label such as **Unlock controls** or **Lock controls** plus a concise state description. Do not rely on the glyph, color or hover tooltip alone. Retain a minimum 44 px target, visible focus and wrapping for long or unavailable names. A disabled or unavailable authentication path must explain its state.

The icon describes application access, not HTTPS, transport security, transmitter ownership or RF safety. The normal page uses the existing admitted transport. Do not claim that the icon encrypts page delivery or represents a global device lock.

Model locked, opening/login pending, authenticated/unlocked, locking and unavailable/expired states from the real client/session authority. Show unlocked only after confirmed authentication for the intended device/boot. Modal visibility, a reported hostname, a public status read or a saved password in an input does not establish authentication.

### Opening, submitting and closing

- On a fresh signed-out page, keep the modal closed and public status visible. Open it on deliberate locked-icon activation; ordinary polling, an expired session or a navigation hash must not repeatedly open it or steal focus.
- Use a native modal dialog where supported, with an accessible name, short explanation, masked password field, existing visibility control, explicit submit and Cancel/Close. Keep the current Pico-password semantics, limits and password-manager support.
- Focus the password field when the operator opens the modal. Keep focus inside the modal while open, support Enter submission and Escape/Cancel, and return focus to the icon on dismissal. Closing must not submit. Account for small viewports, zoom and the on-screen keyboard.
- This deliberately replaces the previous initial-load focus into an inline password field. Do not retain a hidden-field focus call that automatically opens a dialog or disrupts read-only monitoring.
- Reuse existing identity checks, login serialization, cryptography, context binding, rate limits and deadlines. Disable duplicate submission while a request is in flight; do not guess passwords, retry an ambiguous login automatically or allocate a session merely by opening the modal.
- On refusal, retain a useful inline error within the dialog, remain locked and allow an explicit corrected attempt. Distinguish wrong password, occupied capacity, pending login, device/boot change, timeout and unsupported surface without exposing secrets.
- On confirmed success, clear the password, close the modal, return focus sensibly and refresh through the existing authenticated readback path. Preserve drafts and existing save-review barriers; successful login alone cannot confirm an earlier save or enable a new mutation.
- Scrub password values and temporary proof material on success, cancel, expiry and failed/unconfirmed attempts as the existing contracts require. Never place credentials, keys or session tokens in URLs, logs, screenshots, DOM attributes, History state, local/session storage or IndexedDB.
- Bind dialog/login attempts to an epoch and intended device/boot. A late response after Cancel, logout or a newer attempt must not silently unlock the page. Use supported bounded cleanup for an abandoned successful login without affecting a later session; do not invent automatic retirement of another client.

### Clicking the unlocked icon

Lock this browser promptly: gate further privileged actions, clear privileged rendered observations and sensitive input state, cancel stale observation epochs and use the existing logout operation for this session. Consumer-Radio uses its existing logout request; password-authenticated SoftAP uses its supported local logout adapter. Reuse the underlying application flow rather than creating an independent visual boolean.

If another application request is in flight, show bounded locking progress and serialize cleanup with the existing one-request authority. Do not submit logout concurrently through a busy consumer client or wait indefinitely for a running RF job. Preserve the distinction between an accepted board mutation, a cancelled undelivered effect and an unknown outcome. Accepted jobs and durable writes survive as defined by the existing contract.

On lost logout response, clear local authority safely and report local locking with any remote-session uncertainty accurately. Do not claim that every device session has been revoked. Keep bounded nonsecret recovery context where already supported so the operator can later inspect and explicitly retire the relevant abandoned session. Other tabs, clients and controllers keep their independent authority.

Locking must not erase nonsecret operator drafts, reset the Pico, disconnect Wi-Fi, release another owner, stop an accepted job, pause schedules or change the password. Public status remains available. Logout, session expiry, password changes, boot changes and transport failure must all update the icon consistently.

### Less obtrusive recovery and carrier differences

Keep occupied-login recovery reachable as a secondary disclosure/action in the access workflow. Preserve explicit inspection, exact target selection, current-password proof, confirmation and accurate absent/unconfirmed results. Retiring a login and creating a replacement login remain separate explicit operations. Do not add automatic eviction, silent takeover, extra session slots or revised lifetime policy.

Inspect each admitted carrier. Consumer station/AP and password-authenticated SoftAP must use their real login/logout contracts. Certificate-authenticated engineering HTTPS cannot revoke an OS/browser client certificate through a page button; preserve its authority and present a truthful carrier-specific state/action or explanation. Do not add a fake security lock, route it through an unsupported password endpoint or weaken mTLS to make every surface look identical. Document and test this difference.

## 6. Item 9: logically grouped links to furled sections

Build the menu from the explicit section inventory. Keep labels operator-oriented and groups coherent, for example Station/Transmission, Wi-Fi/Host and shared recovery/diagnostics. Reuse the current `/station` and `/wifi-host` area model and supported aliases; navigation remains within the same control document and session.

For ordinary navigation use real, stable fragment links to the actual section IDs. Support copying a link, direct entry, reload, Back/Forward and modified-click/new-tab behavior. Revealing a section never grants authentication or submits a command. A protected section may show an appropriate unlock hint while its controls remain gated.

On activation, validate the target against a fixed allowlist, select any necessary parent task area, unfurl the target and its ancestors, then focus its heading/summary and scroll it into view. Opening a section before scrolling is essential; do not scroll to an element inside an area that remains hidden. Unknown IDs, malformed escapes, stale IDs and hostile fragments must fail harmlessly without selector injection, script execution, network mutations or endless navigation loops.

Preserve useful existing bookmarks, route admission and commissioning/recovery behavior. Initial pathname/fragment and actual connection classification must not be confused with API authority. Keep one document, existing DOM drafts and the admitted authentication context; do not navigate by full page reload for an ordinary in-page section click.

### Existing receipt fragments are a compatibility requirement

Current `organization.js` preserves `#save=...` and `#hostname-return=...` receipt bytes. `app.js` uses fragments to resume and reconcile uncertain saves. A URL has one fragment: do not replace a live receipt with a section anchor, concatenate a second fragment, reinterpret receipt contents as a selector or lose a continuation while changing area.

Define a bounded compatible representation for section navigation when a receipt is active. For example, retain its fragment byte-for-byte while recording only an allowlisted section ID in namespaced in-memory/History state. Merge presentation state without erasing existing History data. Document and test how reload, Back/Forward and ordinary fragment links behave while a receipt exists. Do not move credentials or recovery proofs into query parameters or browser storage. Section navigation is never evidence that a save succeeded.

## 7. Item 10: Top re-furls and returns to status

Add a plainly labelled **Top** link to each managed non-status section, in a consistent reachable location. Use a stable top/status anchor with compatible same-document behavior. Preserve the receipt rules above and any relevant task-area history.

On deliberate Top activation:

1. Close any transient section-owned popover safely and move focus out of content that will become hidden.
2. Re-furl every managed non-status section, including sections in either task area and managed nested disclosures. Do not leave other sections open simply because they were reached earlier by the menu.
3. Keep the main Transmitter status unfurled and shared, with monitoring still active.
4. Scroll back to the top/status region and place keyboard focus on the persistent status heading or another documented persistent destination without hiding the current state behind navigation chrome.

Top is a presentation action. It preserves drafts, files, dirty flags, uncertain-save evidence, authentication and application state. It does not log out, submit, cancel a board mutation, alter settings or stop a job. Respect reduced-motion preference; avoid motion that obstructs keyboard or touch use. Back/Forward must not accidentally replay Top's application-independent action as a board operation.

## 8. Architecture, accessibility and performance constraints

Preserve item 6's implemented console and reset authority, the closed public status projection and capability-negotiated authenticated operations resource. Do not expose private operations data while locked. Hiding a section or changing an icon is not an access-control boundary; backend authorization remains authoritative.

Keep the current serialized polling/action model, freshness epochs, one-shot restart behavior, saved-state reconciliation and same-device/new-boot checks. Do not add polling loops per section, renew sessions for mere navigation, add journal writes for UI preferences or disturb local RF timing. There must be no extra per-symbol traffic or UI-dependent execution timing.

Use local assets and current design tokens. Do not add remote icon fonts, Bootstrap, PHP, a new UI framework or broad dependencies to achieve a padlock and disclosures. Preserve CSP and safe rendering of device-provided strings. Update source and regenerate shipped/minified/embedded assets using the established build path.

Verify semantic headings, disclosure names, state/action labels, dialog focus/inert behavior, status announcements, contrast, 44 px touch targets, high zoom, narrow portrait/landscape layouts and long hostnames. Modal backdrop clicks must have deliberate, tested cancellation semantics. Background observations must not refocus the page or close an active password dialog unexpectedly.

## 9. Implement and validate in bounded slices

Use the documented build/test commands and retained dependencies from the development guide and existing test registrations. Do not install an SDK as an incidental formatting step or retry the known broken local macOS C++ toolchain. Use an identified authorized Linux host, Pi, container or Linux CI for C++ work when required.

Implement shared presentation state and disclosure boundaries first, then integrate the real authentication flow, fragment/history handling and Top behavior. Test interactions together before declaring any one item complete. Keep source, generated assets and the served artifact consistent. `npm test` and `npm run build` run from `src/network/bootstrap_web`; the latter invokes `scripts/build_operator_assets.mjs` for operator assets.

Extend meaningful behavioral coverage rather than writing tests that mirror helper functions. Inspect the existing organization route/browser tests, device-presentation tests, `tests/network_browser_tests.js`, `tests/operations_browser_tests.js`, consumer-session/recovery fixtures and saved-progress/hostname tests. Use real-browser fixtures for native disclosures, dialog focus, scrolling, validation and Back/Forward; a mocked DOM alone does not establish those behaviors.

| Scenario | Acceptance evidence |
| --- | --- |
| Fresh ordinary entry, signed out and authenticated | Non-status sections furled; main status visible; truthful access icon; no unsolicited modal. |
| Direct section link, parent area hidden or several sections already open | Correct area and ancestors revealed, target focused/scrolled, other drafts and authority preserved. |
| Top from each section in either area | Every managed non-status section re-furled, status remains visible, focus restored and drafts unchanged. |
| Valid/invalid/unknown fragments and legacy routes | Correct bounded reveal or harmless fallback, no duplicate document/session or mutation. |
| Active save or hostname-return receipt with menu, Top, reload and history | Receipt retained and reconciliation remains valid; navigation never confirms or repeats a save. |
| Locked-icon click, keyboard activation, Enter, Escape and Cancel | Accessible modal, correct focus/return, no accidental submission or password retention. |
| Correct/incorrect password, full capacity, rate limit, pending login and timeout | Existing protocol behavior, bounded single attempts, useful modal errors, no automatic eviction or retry. |
| Cancelled/late login, lock during pending action, failed logout or new boot | No ghost unlock, parallel protocol requests, stale privileged render or falsely confirmed cancellation/logout. |
| Explicit occupied-login recovery | Correct selected session only, current proof and confirmation, no implicit replacement login or job takeover. |
| Session expiry, password change, other tabs and certificate carrier | Truthful state and carrier behavior; each session's authority remains independent. |
| Invalid field in collapsed body, file/message drafts, nested UTC picker | Owning section revealed for errors; drafts/files/validation flags preserved; no hidden-focus or dangling overlay. |
| Loaded/armed/running/RF-off gap, paused schedules and reset feedback | Completed status/reset semantics retained; UI navigation/lock does not alter RF, ownership or schedules. |
| Desktop, mobile widths, zoom, long names, reduced motion and keyboard/screen reader | Usable control ordering, no overflow/focus traps outside the modal, restrained announcements and meaningful labels. |
| Source versus shipped artifact | Tests and browser checks exercise regenerated assets, CSP and actual served markup with acceptable flash/RAM/request costs. |

Run affected regressions, firmware/asset builds when inputs change and documentation/link/image checks where documentation changes require them. Compare baseline and final shipped-asset size, flash/BSS and relevant runtime costs. Do not weaken resource budgets or safety gates to accommodate the UI.

For physical validation, identify the chosen Pico by current USB serial and full device ID; record firmware, source, clock, carrier and configuration. Preserve unrelated controllers, credentials, schedules and device state. Use the scoped preserving installer if a firmware update is needed; avoid broad snapshots of sensitive configuration. Run finite browser/access/idle checks and restore the setup. Picos not selected for the test remain untouched. Keep ecm-mule's network unchanged under the existing restriction.

Most work is hardware-free or non-transmitting. If an RF-dependent regression test is actually necessary, use the embedded standing authority and verify current appropriate conducted termination first. Do not assume an old bench description establishes the present RF path. Separate fixture behavior, physical UI/session observations and independently measured RF evidence in the report. Missing physical evidence must not be represented as a completed live check.

## 10. Adversarial review, corrections and reassessment

Perform an adversarial review of the implementation, source and served artifacts. Use an independent reviewer when available and authorized; otherwise conduct a distinct adversarial self-assessment and report that accurately. Follow any applicable bounded visual-review process while continuing to close substantive engineering findings.

Challenge at least these failure cases:

- A displayed unlocked state with expired, wrong-device or merely cosmetic local authority.
- A lock that leaves privileged actions enabled, discards an uncertain-save barrier, silently stops a job or claims remote revocation without evidence.
- A cancelled login whose late reply unlocks a newer or signed-out page, or cleanup that retires the wrong session.
- Hidden errors, reset outcomes, required invalid fields or important status; focus remaining inside a newly furled body.
- Menu/Top handlers destroying receipt bytes, drafts, files, History state or carrier binding.
- Hostname rendering erasing the icon, icon text contaminating the hostname/title, or a forged fragment becoming an unsafe selector/HTML insertion.
- Public/private observation races leaking stale authenticated context, and navigation/polling retaining secrets or renewing session policy unintentionally.
- Duplicate requests, handlers or polling loops; modal reopens/focus theft; mobile/keyboard interactions that differ from mocked tests.
- Regression of item 6's accepted-job versus future-schedule presentation or authenticated one-shot Reset Pico.

Maintain a working issue ledger containing identifier, severity, evidence/reproduction, correction, regression coverage, retest and closure status. Fix every actionable issue within scope, rerun the affected checks and close it with evidence. Then perform another adversarial assessment of the corrected result, including regressions introduced by fixes. Repeat issue closure, testing and reassessment until no actionable task findings remain or a concrete external blocker prevents completion.

Do not substitute an initial review, an intended-fix list or unrelated passing tests for closure. Keep blocked findings explicit, complete independent work and leave any affected TODO item unfinished when its acceptance criteria are unmet. Do not claim independent review without an actual independent reviewer.

## 11. Documentation and numbered TODO completion

Update current operator instructions, the browser-page/access/navigation contracts, `src/network/web/DESIGN.md` and other affected engineering references to describe the delivered behavior directly. Preserve Read the Docs as the publication system and existing image/privacy policy. Remove obsolete inline-login, focus, fragment or Top descriptions that the implementation supersedes; repair local links and anchors.

Update the existing numbered TODO items 7, 8, 9 and 10 individually only when their acceptance criteria and shared regressions are satisfied. Preserve numbers and unrelated states, including completed items 1 and 6. Keep unresolved selected work explicit; do not create duplicate entries or invent completion for an omitted carrier or failure path.

Keep this prompt linked while execution is unfinished. When complete, follow AGENTS.md prompt-retirement rules, consolidate durable technical content into maintained guides and repair the TODO reference when the execution prompt is retired. Do not create an archive of execution narratives or commit credentials, private captures, machine-specific configuration or generated firmware.

## 12. Commit, push and report when execution is done

Inspect the final changes and actual repository state. Stage only this task's source, generated browser assets, tests, documentation and final prompt/TODO disposition. Commit and push validated changes to the appropriate devel branch under the established workflow in each repository actually changed. These execution Git operations are authorized by the standing authority. Do not force-push or bypass protections; reconcile remote advances safely and rerun affected checks.

Inspect relevant CI, correct task-related failures, push the validated result and verify exact local/remote commit parity. Recheck deployed firmware identity, final device/controller state and working trees. A failed push, blocked required check or unresolved material acceptance issue must be reported accurately instead of marked done.

Then report concisely:

- What was delivered for each of items 7–10, including the exact Top re-furl behavior and carrier-specific lock semantics.
- How default disclosures, menu links, modal focus, login/logout and occupied-login recovery behave.
- How receipt/history compatibility, drafts, status/reset authority, security and resource budgets were preserved.
- Tests/builds/browser and physical observations, their actual evidence boundaries, adversarial findings and closure/reassessment results.
- Documentation and TODO changes, prompt disposition, commit IDs, push/CI results, remote parity and final working-tree state.
- Any deployed Pico/host identities, settings/restoration state, limitations, outstanding findings or required user action.

Operate autonomously within the authority below. Continue through ordinary failures, select reasonable diagnostics independently and complete unaffected work before raising a material blocker. A user-triggered product login dialog is part of the application; it is not a development-session approval gate.

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
