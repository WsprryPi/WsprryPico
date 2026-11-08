# Phase 3 — Review, publish, and verify WsprryPico RC.2

## Activation and intended outcome

**Execute this prompt only when the user explicitly invokes Phase 3.** Reading, saving, linking, reviewing, or printing it does not execute it. Its authoring request authorizes preparation of this prompt and the checklist link only.

This is item 3 of the [RC.2 release checklist](rc2-release-checklist.md). Review the completed Phase 2 evidence, resolve actionable release findings, finalize accurate release notes, publish the exact prepared and qualified `1.0.0-rc.2` bytes through the owning trusted workflow, verify public downloads and installer resolution, and update the operator documentation after public acceptance succeeds.

**When this phase is explicitly invoked, publication of this one Pico prerelease is authorized once its concrete acceptance gates pass.** This supersedes earlier preparation-only/no-publication instructions only for the selected RC.2 packet and the necessary release metadata/documentation. Do not ask again for routine permission to execute the selected publisher, finish matching partial drafts, run approved acceptance, or commit and push validated task changes.

It does not authorize publication of a stable release, changing GitHub's latest-stable selection, recreating or merging `main`, moving an existing tag, publishing unrelated Pi/RP1 components, merging Standard Feld research, changing the selected firmware behind the release name, or starting another RF research campaign. Keep this an independent Pico release unless the user explicitly selects a coordinated system release.

## Final disposition of former item 21

The Si5351 automatic carrier-correction investigation is **closed as inconclusive and resolution-limited, with that answer final**. The capability remains available for experimentation. A crystal reference might benefit differently from the tested TCXO, but no such improvement is established by the retained measurements.

- Do not reopen the investigation, call it unfinished, disable the feature, change calibration/acquisition policy, or require consistent automatic frequency improvement before publishing RC.2.
- Preserve the approved operator wording in `docs/reference/time.md` and the retained technical evidence and limits. Describe the release's experimental correction capability accurately without promising improved accuracy.
- Do not imply that other Si5351 references, crystals, modules, bands, drive strengths, timing accuracy, output power, or emissions are qualified merely because the software offers a setting.
- Distinguish an acceptable inconclusive improvement comparison from an unresolved operational, safety, installation, mode/decode, cleanup, or exact-artifact defect. The latter cannot be waived by citing item 21's closure.

## 1. Establish current repository and release truth

Read applicable `AGENTS.md` files and owning instructions. In Pico, read `README.md`, `CONTRACT.md`, `engineering/architecture.md`, the development/CI guide, prepared-publication guide, installer guide, current publication workflow/implementation and validators, release/version policy, operator installation/time/output guidance, and the retained Phase 2 qualification summary and packet. Read companion instructions before changing a companion repository.

For the Harness, follow its contract, agent-operation, workflow-router, capability-matrix, operator-security, lifecycle, and retained-release guides. Derive exact commands and effects from current source and inspected CLI help rather than old logs, copied examples, or this prompt's discovery hints.

Inventory branches, full source SHAs, upstreams, remotes, worktrees, staged/unstaged/untracked work, dependencies, installed tooling, and active operations. Fetch needed refs without replacing user files. Preserve unrelated work; use clean isolated task/publisher worktrees and independent frozen source copies where required. Do not reset, stash, clean, force-push, delete worktrees, or alter protected history to obtain a convenient checkout.

Relevant repositories are WsprryPico, WsprryPi, WsprryPi-Docs, and the independent WsprryPi-Qualification-Harness execution tool. The standing repository list below names the three product repositories. Honor any explicit current Harness development/Git grants; do not infer unlimited new Harness Git authority from an earlier approval for a particular reconciliation. Use maintained tooling first and resolve only a genuinely missing authority boundary if a necessary Harness repair is outside current grants.

Discovery hints from 2026-11-08, not execution-time facts:

- Pico `devel` was `f6c90a4925d02d60b7404487e24316f239c48e7c`. Green software checks at that source did not produce a semantic RC.2 physical qualification result.
- Harness reconciliation was merged at `492a1bec4cd904c9a94d9ade949a916ecc4793c6`. It corrected transmitter-side privilege-wrapper verification and private-context handling; it did not implement the Pico RF adapter or qualify RC.2.
- The checklist had Phase 1 unfinished/stopped, with Phases 2 and 3 not started. The operator manual recommended `1.0.0-rc.1`. Verify subsequent delivery rather than assuming these facts remain current.
- Public semantic version releases and the `ci-devel` download bookmark are separate selectors. Inspect current owning code before promising a selector change.

The current task includes no general repository/harness cleanup. Preserve private context imports, user edits, recovery bundles, firmware copies, captures, source/build environments, branches, and worktrees with a present duty. Never publish private account exports or raw target evidence incidentally.

## 2. Review actual Phase 1 and Phase 2 completion

Inspect the checklist, delivered source/PRs/CI, maintained implementation/docs, and actual retained artifacts. A marked checkbox, saved prompt, old green run, or historical board record is not acceptance evidence. The execution prompts may have been retired after their useful instructions were consolidated; do not require an obsolete prompt to remain as proof.

Before any public mutation, establish all of the following:

1. The production Harness Pico RF adapter and relevant companion changes exist on the intended available refs, with required software validation complete. Pi backend names, RF-disabled lifecycle tracks, mocks, or one-off private scripts are not substitutes.
2. Phase 2 selected an actual semantic `1.0.0-rc.2` firmware image and retained its exact source, embedded identity, UF2 hash, canonical build/run/attempt, dependency selections, tag object/peeled commit, deployment/audit archives, installer bundle, and prepared-publication state.
3. Required fresh/preserving installation and applicable migration checks passed using the exact candidate, real board identities, production installer/reference transactions, and independently verified final state.
4. The final candidate's physical matrix covers direct GPIO and Si5351, each with and without firmware GPS/PPS use, TONE/WSPR/QRSS/FSKCW/DFCW, correction-off/on subcases where selected, actual bands, and maintained independent observation counts. The two GPS-enabled rows' subcases must not be silently collapsed into four total executions.
5. Expected operational/mode/decode criteria, ownership, finite bounds, output inactivity, cleanup/restoration, and current physical setup evidence are satisfied. Legitimately inconclusive Si5351 improvement remains the final limited result; required operational failures, missing cells, wrong images, or unfinished handback remain blockers.
6. Both actual production Pi/Pico network and USB source-pair suites passed for the final selected Pico source and intended Pi revision, including required browser/source-selection/routing gates. Canonical Pico verification has the current source-bound contexts/counts, generated assets, packaging/crypto/installer, memory/flash/image identity, and reproducibility checks.
7. A complete retained publish-later packet exists in durable private storage and was verified in a separate process. The actual tested UF2 hash equals the prepared payload hash. The publisher/tool/controller implementation and exact fixed companions are identified, and external archive/provenance proof remains available.
8. Actionable adversarial findings were closed and reassessed. Failed, skipped, cancelled, timed-out, empty, truncated, stale-source, or unavailable required checks have not been counted as passes.

If a prerequisite is not established, complete independent review, notes, and read-only integrity work, then report the exact blocker. Do not publish to discover whether acceptance will work. Do not silently execute missing Phase 1 implementation or replace Phase 2's campaign with an unsupported shortcut.

Build a concise release acceptance ledger in private working evidence: each prerequisite, its exact source/artifact identity, command/result, and supporting path or CI URL. This is execution evidence, not another permanent backlog or public raw-log archive. Sanitize any maintained qualification summary and preserve the original private records separately.

## 3. Revalidate the exact packet and publication target

Use the retained Phase 2 state, not a fresh build from the latest `devel` head. Firmware source, publisher source, current documentation source, Harness/controller identity, and fixed companion source are distinct facts.

- Run current offline integrity/status checks and fresh-process owning packet verification into new directories. Use the exact plan/prepared/packet digests from the validated records; never fill confirmation fields with placeholders or edit a sealed plan to acknowledge drift.
- Recheck schemas, file inventories, sizes/hashes, source/tool/controller seals, semantic version, canonical workflow/run/attempt/source/jobs, original archive IDs/digests, manifest/ELF/UF2 identity, tag binding, and available original proof. The current Pico public inventory has nine files; enforce the actual prepared source's inventory rather than assuming a historical count forever.
- Require version `1.0.0-rc.2` and tag `v1.0.0-rc.2`, a prerelease disposition, and `make_latest=false`. A devel CI image cannot be renamed or relabeled as semantic RC.2. A tag/source string alone does not establish the embedded image identity or qualification.
- Inspect public tags/releases/drafts/assets and canonical publisher runs before dispatch. Match the actual release by immutable identity, not a title or newest timestamp. Determine whether this is a new publication, an identical already-complete publication, or a supported partial continuation.
- Existing semantic tags are immutable. A missing or mismatching required semantic-build tag, conflicting asset, incompatible prepared state, unavailable canonical proof, moved source, or divergent dependency selection must refuse. Do not delete/recreate tags, force-update refs, overwrite/clobber assets, or change version numbers silently.
- Original Actions archive expiry or missing canonical proof is a real gate. A locally retained UF2 or ZIP does not bypass the owning verifier. Complete the supported re-preparation/acceptance work when necessary; never weaken provenance or claim the original handoff passed.
- Determine which files/source changes invalidate the retained controller or publisher implementation closure before editing code or documentation. Frozen source copies protect the tested candidate while normal checkouts advance, but they do not authorize falsified source or seal records.

Use the current read-only online publication-validation path before enabling publication. Current maintained families include owning `scripts/ci/prepared.py verify`, Harness `lifecycle release-status` and `release-publish --validate-only`, and trusted `publish-prepared.yml` with `publish=false`. Inspect current inputs and effect boundaries first.

A current validation result must identify the exact prepared digest and required public prerequisites. Local artifact integrity is not the same as online publication readiness. A missing permission or changed external state must be reported precisely, after unaffected work is finished.

## 4. Finalize release notes and documentation changes for review

Prepare concrete, reviewed text before publication. Derive changes from actual commits and final behavior since RC.1, with current Phase 2 applicability. Describe operator-visible improvements and known limits in plain language, without a session diary or copied execution authority.

At minimum, verify whether the final candidate includes the intended RC.2 work: time/calibration feedback and recovery links, captive hostname editing before station commissioning, authentication-lock explanations, radio-pin/GPS layout, shared favicon/attribution, hardware-only saves during standalone suspension, Si5351 realized-frequency projection, and the validated installer/dependency changes. Do not advertise a feature merely because it appeared in an earlier proposed list.

Release notes and operator guidance must state supported Pico 2 W/RP2350 use, direct GPIO and the actual supported Si5351 profile, selected GPS/PPS/correction behavior, installation/preservation requirements, meaningful known limitations, and exact physical qualification scope where relevant. Preserve item 21's final disposition and the experimental nature of automatic correction. Do not imply calibrated power, antenna-ready emissions, all-band suitability, generalized stability, native Windows USB support, or precision UTC qualification without corresponding evidence.

Keep public project documentation on Read the Docs. Use an existing appropriate release-notes destination; if none exists, add a concise current release-notes page to the established Sphinx tree/navigation rather than a placeholder, archive, or execution report. Keep technical measurement detail in engineering documentation and secrets/raw evidence out of both.

The current publisher generates a canonical GitHub release body and embeds a machine-readable publication receipt. Preserve its required identity/provenance text and receipt. Do not hand-edit the body or append metadata in a way that breaks exact-body checks, later continuation, or installer verification. If the owning publisher has no supported custom-notes mechanism, publish the human-readable notes in the operator manual and report their URL; do not bypass the publisher to decorate the release. A genuinely required publisher feature needs owning tests and fresh preparation if it changes the sealed closure.

Prepare the documentation recommendation change so that, **after RC.2 is publicly accepted**, the single `recommended_firmware_version` in Pico `docs/conf.py` becomes `1.0.0-rc.2` and the existing substitution-based installation commands/links select that exact version. Avoid hard-coded duplicate recommendations. Do not advertise unavailable downloads before publication succeeds.

Keep documentation-only changes separate from the tagged firmware's immutable source identity. A later docs commit is not a rebuilt or requalified RC.2 image. Inspect affected generated inputs and publication seals before assuming a change is documentation-only.

## 5. Perform an adversarial prepublication review

**Perform an adversarial review.** Challenge at least:

- a version/tag/source that looks correct but identifies untested or rebuilt firmware;
- stale Phase 1 claims, missing physical cells/subcases/observations, a diagnostic image substituted for the ordinary image, or an old green run presented as the final candidate;
- a private packet that differs from canonical archives, lacks proof, expired externally, or cannot be continued in a fresh process;
- public assets/drafts with the same filenames but different bytes, an already-published version being overwritten, duplicate release candidates, or a race with another publisher;
- confusion between firmware source, publisher implementation, documentation commit, Harness version, and fixed Pi companion;
- wrong prerelease/latest flags, unintended stable/main publication, accidental Pi/RP1 release effects, tag movement, or default-selector changes;
- missing or forged original-build/later-publisher receipt binding, invalid source ordering, or manual release-body edits that break verification;
- claims that broaden GPS/PPS, Si5351 correction, RF/timing/band/drive/platform qualification, or reopen former item 21;
- private account context, credentials, coordinates, raw IQ/flash dumps, local paths, recovery bundles, or unrelated user changes being staged/uploaded;
- operator instructions that recommend the wrong selector, a dead URL, an unavailable release, an incorrect preserving-upgrade path, or GitHub Pages publication.

**Iterate through issues, close them, and run another adversarial assessment.** Repair actionable findings, rerun affected tests/validators, and reassess the complete concrete candidate before the first public mutation. Do not relax validation, widen limits, rewrite vectors, remove required checks, or hide failures to obtain readiness.

If a necessary correction changes firmware, its dependencies, generated firmware inputs, or the tested payload, the affected Phase 2 qualification/preparation must be re-established for truthful version/artifact identities before publication. Never rebuild a replacement during the publication step. Metadata/tooling fixes still need their owning tests, valid intended refs, and fresh preparation when their implementation seal changes.

## 6. Publish the tested bytes through the trusted owning path

Proceed autonomously after the selected packet, acceptance ledger, notes, current authority, and read-only online gates are established. Explicit invocation of this phase is the publication instruction; no additional routine confirmation question is required.

Use one maintained publication route:

- Prefer the retained Harness independent-Pico continuation when Phase 2 produced that state: inspect current `lifecycle release-publish` help, confirm the exact prepared digest, and enable publication for that one selected component.
- If Phase 2 retained the standalone owning Pico packet, use the trusted manual `.github/workflows/publish-prepared.yml` on the verified public `devel` publisher source, with the exact `prepared_plan`, `packet_sha256`, `publisher_source`, and deliberate `publish=true` inputs from that packet. Recheck the live workflow schema before dispatch.

Do not invoke both routes independently for the same publication. Do not use the ordinary build-and-publish path if it would compile replacement firmware. Do not publish by manually creating/uploading a release outside the owning verifier. Use structured arguments and input files where supported; do not put credentials, private evidence, or unrelated local state in workflow inputs or release metadata.

The intended public result is one non-draft **prerelease** at `v1.0.0-rc.2`, with the exact tested public file inventory and successful canonical publisher provenance. It must not become latest stable. The semantic tag must remain at the qualified source.

Record dispatch intent and the unambiguous canonical run ID before treating the action as started. Bind repository/workflow/ref/source, input digest, run/attempt, job IDs, and final receipt. Follow the actual selected run through completion; failed/cancelled/timed-out/skipped publication is unresolved even if some assets became visible.

Preserve the owner's draft-until-complete behavior, missing-identical-asset continuation, exact asset hashing, tag checks, publisher receipt, and concurrency/source-ordering guards. Never disable protection/concurrency or replace the workflow with an ad hoc uploader to get a green result.

## 7. Verify public release and actual consumer resolution

After the publisher succeeds, independently re-read authenticated public state and download to fresh destinations through the normal consumer paths.

### Public identity and byte acceptance

Verify the release ID/URL, tag object/peeled source, non-draft prerelease flag, latest-stable state, expected asset names/count/sizes/hashes, and required original-build/later-publisher provenance. Compare every public file to the sealed prepared inventory and the actual Phase 2 tested bytes, including UF2, manifest, checksum file, notices, original audit/deployment archives, and publication proof as declared by the owning source.

Use the owning published-bundle retrieval and USB installer's non-programming resolver/plan operation with **explicit `--version 1.0.0-rc.2`**. Verify anonymous HTTPS download where the normal operator path supports it, safe extraction, schema/identity checks, source/run/attempt/publisher proof, correct board profile, complete bundle, and refusal without hidden fallback. Authenticated `gh` success alone does not demonstrate that an ordinary operator download works.

Check the actual manifest and embedded-image identity, not only a release title or checksum comparison copied from the uploader. Retain the public consumer's receipts and compare its payload to the Phase 2 UF2 hash. No USB device needs to be opened for this mandatory software acceptance step.

### Selector semantics

Treat semantic RC.2 recommendation and the devel CI bookmark separately. At the inspected owning implementation, semantic `branch: release` publication does **not** advance `ci-devel`; that bookmark accepts CI-version records, not `1.0.0-rc.2` records. Recheck current code and test actual selectors.

- Explicit `--version 1.0.0-rc.2` must resolve the published tested RC.2 bytes.
- The operator manual's recommendation must select RC.2 explicitly after its documentation update.
- `--branch devel` must continue to resolve the actual valid source-ordered published CI selection. Report what it selects; do not claim it selects RC.2 merely because RC.2 was published.
- Do not move the `ci-devel` tag, rewrite its index as a semantic release, publish an unrelated new CI image, change a fixed Pi dependency, or modify Pi's default Pico selection just to make these selectors appear identical. If the selected release requirements genuinely demand a broader default-policy change, resolve that material scope/contract decision with coordinated validation.

### Physical public acceptance when selected

Review the Phase 2 handoff's selected public-consumer obligations. If it requires a physical public installation/preservation or Pi/Pico handoff check, run that bounded **RF-disabled** maintained lifecycle check against the newly downloaded exact public bundle, with fresh board/host identity, original-state protection, shared installer transaction/reference, and independently verified restoration. Current standing authority covers necessary selected device/host operations; do not ask again for each routine step.

Do not rerun the RF matrix merely because public URLs now exist when bytes and setup-independent proofs are unchanged. If physical public acceptance was not selected/performed, state that limit and do not claim it from software resolution. A required selected physical acceptance remains a gate until it passes. Restore any state changed during public acceptance and retain its exact bundles and receipts.

## 8. Publish the documentation recommendation and finish delivery checks

Only after actual public RC.2 acceptance succeeds:

1. Apply the reviewed `recommended_firmware_version = "1.0.0-rc.2"` change in Pico `docs/conf.py`, finalized release notes, and necessary current operator corrections. Preserve token-based exact-version commands, current protocol/hardware limits, copyright/attribution, and item 21 wording.
2. Validate locally with the current documented commands, including strict `make -C docs html`, `docs/.venv/bin/python scripts/check_documentation.py`, relevant image/help/generated-asset checks, and `git diff --check`. Inspect untracked text and new navigation/anchors separately.
3. Commit and push only task-owned validated changes under normal repository/PR requirements. Merge required documentation delivery through the normal permitted path when necessary, preserving unrelated work and protected history. Do not use publication as authority to merge unrelated work or promote `main`.
4. Follow applicable code/documentation CI and Read the Docs publication through completion. Verify the actual served operator manual and release-note URL, rendered RC.2 version, release/download/checksum links, install/upgrade/plan examples, navigation, and meaningful limits. A local Sphinx build does not establish public-site delivery.
5. If a documentation commit triggers another ordinary devel firmware build, do not publish that new CI image or substitute it for RC.2. The original semantic artifact/source remains the qualified release; record current docs/publisher sources separately.
6. Re-read public release identity/assets/receipts and normal consumer resolution after final documentation/tooling changes so a late mutation or incomplete continuation is not missed. Verify no stable/latest/default-policy change occurred outside the selected scope.

A defect found after public publication must be handled truthfully through supported continuation or a new corrected candidate/release decision. Do not delete/replace immutable assets or move tags to conceal it. Retain the unsuccessful result, actual public state, and supported recovery path.

## 9. Partial publication, interruption, and recovery

Use the retained state and exact original digests. Inspect actual drafts/assets, canonical run/attempts, tag/source, consumer outcomes, and controller locks before retrying. Do not dispatch another publisher blindly when the first run identity is ambiguous.

The maintained continuation may add only missing identical draft assets and append valid publisher-attempt receipt history. It must not clobber a mismatching asset, silently rebuild, move a version tag, rewrite sealed proof, or force an invalid branch bookmark. An identical already-complete release can be reverified and accepted without duplicate upload.

Use documented `--resume` or canonical rerun behavior only after proving the current continuation state. Do not steal a live controller lock or erase pending receipts. Verify owned process/container/helper cleanup and independently observed host/device state; foreign resources remain untouched.

Public effects can succeed before a final receipt or consumer check fails. Report that actual partially published state accurately and keep completion pending until supported recovery and mandatory acceptance pass. Never describe a cancelled run or visible asset subset as complete delivery.

If original archives, tool/controller seals, permissions, publication proofs, or immutable version selections prevent safe continuation, finish unaffected review/documentation preparation and report the concrete blocker. Do not bypass the refusal or promise that a future rebuild will preserve the tested bytes.

## 10. Final adversarial assessment, commit/push, and report

Reassess the actual delivered public state, not just the prepublication plan. Challenge whether the release is accessible anonymously, both manifests/receipts and bytes match qualification, recommendation and default selectors are represented honestly, published docs have finished, private data remained private, and any selected physical public acceptance and restoration are complete.

**Iterate through issues, close them, and run another adversarial assessment.** Repair actionable findings through supported owning workflows, rerun affected checks/consumer acceptance, and repeat the assessment. Do not declare completion with unresolved required checks, a partially delivered public packet, broken documentation, false qualification, or an unknown final device/service state.

**When done, commit and push. Then report.**

- Commit/push all validated task-owned source, tests, current engineering summaries, release-note, recommendation, and checklist changes that are required for actual delivery. Respect each repository's authority and normal review/merge requirements. Follow final required CI through completion; no force pushes, branch-protection bypasses, or CI-skip markers for required acceptance.
- Mark checklist item 3 ⏳ when execution starts and ✅ only after release publication, exact-byte consumer acceptance, intended documentation delivery, final review, and any required restoration are verified. Do not retroactively mark Phases 1 or 2 complete without their own evidence.
- Consolidate useful enduring instructions into maintained guides and retire this completed task-specific prompt when its handoff duty ends. Repair checklist and other prompt references; do not create an archive, replacement backlog, or permanent execution diary.
- Preserve retained prepared/public packets, private qualification evidence, original/candidate recovery bundles, relevant tool/controller environments, branches, and worktrees with a current duty. This phase does not select broad cleanup.

The final factual report must include:

1. Public RC.2 release/tag/asset and release-note/manual URLs, release ID, draft/prerelease/latest flags, immutable tag object/peeled firmware source, embedded version/source, and published UF2 hash.
2. Exact Phase 2 tested packet identity, public file inventory/hash comparison, retained state paths/digests, canonical build and later publisher source/run/attempt/job identities, and direct CI/publication links.
3. Intended Pi/Harness/dependency identities and what was actually qualified, including engine/GPS/correction/mode/band coverage and the final inconclusive Si5351 improvement disposition without broader claims.
4. Actual public installer/download verification commands/results, anonymous-access result, explicit RC.2 selection, observed devel CI/default selection, recommended-version delivery, and any selected physical public acceptance/restore result.
5. Release-note, documentation, source/test/validator changes, adversarial findings and closure, commits/pushes/PR states, Read the Docs result, and all failed/cancelled/refused attempts relevant to current readiness.
6. Actual local checkout/upstream/clean-dirty state in every changed repository, unchanged protected tags/history/stable policy, preserved unrelated work/private data, remaining recovery/material retention duties, and concrete unresolved blockers.

Do not claim completion while required public acceptance, documentation delivery, qualification binding, or handback remains unresolved.

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
