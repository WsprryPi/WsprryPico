# Phase 2 — Prepare and qualify the exact WsprryPico RC.2 artifact

## Activation and intended outcome

**Execute this prompt only when the user explicitly invokes Phase 2.** Reading, saving, linking, reviewing, or printing it does not execute it. Its authoring request authorizes the prompt and checklist edit only.

This is item 2 of the [RC.2 release checklist](rc2-release-checklist.md). Prepare the exact `1.0.0-rc.2` firmware artifact, validate its installation and preservation behavior, run the maintained Qualification Harness against that exact image across the required Pico configurations and modes, resolve actionable findings, and retain a verifiable packet that Phase 3 can publish without rebuilding the tested firmware.

The result is a tested, privately retained release candidate and a factual readiness report. **Do not execute Phase 3.** Do not create or publish a GitHub release, upload public release assets, change the public devel firmware bookmark, mark a release latest, or update the operator manual's recommended firmware version. A deliberately selected immutable semantic version tag for the canonical RC.2 build is the narrowly scoped exception described below; tag creation triggers CI and must be recorded as a public Git effect.

## Final product decision: former item 21

The Si5351 automatic carrier-correction investigation is **closed as inconclusive and resolution-limited, with that answer final**. Automatic correction remains available for experimentation. A crystal reference might respond differently from the tested TCXO, but the existing work does not establish that benefit.

- Do not reopen item 21, start another correction-improvement investigation, redesign acquisition or calibration, disable the capability, or require automatic correction to outperform manual correction for this release.
- Verify correct operation, provenance, refusal behavior, and finite transmission with the selected correction policy. Report measured error and its uncertainty separately from any claim of improvement.
- Do not expand supported Si5351 hardware profiles to crystals or other modules merely to exercise the experimental capability. Use the current qualified profile or a separately selected explicit engineering build; an engineering image cannot substitute for qualification of the ordinary RC.2 image.
- Preserve the approved operator wording in `docs/reference/time.md` and the retained engineering evidence. In particular:

  > The Si5351 we tested was already close to the correct frequency. Automatic correction sometimes helped and sometimes made the error worse. The results varied too much, and the remaining errors were too small to measure precisely enough, to show a consistent benefit.
  >
  > Measure the carrier before and after enabling automatic correction. If it doesn’t help, leave it off or use a measured manual adjustment.

The practical launch-time goal remains approximately one second early or late under the accepted operating scope. Do not introduce a new precision-UTC or ppb-improvement completion gate. Existing product safety, valid time-source, ownership, engine/band, and explicitly selected Harness measurement gates remain mandatory.

## Phase 1 prerequisite and repository boundaries

Read the current [Pico RF qualification guide](pico-rf-qualification.md) and inspect its actual delivered implementation, commits, tests, and CI. A checkbox, old green run, generic `gpio`/`si5351` backend name, Pico installation lifecycle, or one-off historical campaign does not establish a production Pico RF adapter.

Before live qualification, confirm the maintained Harness actually supplies all four Pico engine/GPS configurations, five modes, correction subcases, production control, capture/analysis, failure classification, cleanup, and restoration required below. Use intended paired sources and installed tooling identities. If Phase 1 remains incomplete, stopped, unvalidated, or unavailable on the intended refs, retain item 2 as not complete. Finish independent source/artifact planning, then report the concrete prerequisite; do not silently execute Phase 1 or manufacture a replacement RF runner inside Phase 2.

Repository discovery leads:

- `/Users/lbussy/GitHub/WsprryPico`: firmware, contracts, installer, canonical build/publication tooling, checklist, and target-owned qualification summary.
- `/Users/lbussy/GitHub/WsprryPi`: intended companion client/coordinator and authoritative paired CI recipes.
- `/Users/lbussy/GitHub/WsprryPi-Docs`: coordinated operator documentation only where actually affected.
- `/Users/lbussy/GitHub/WsprryPi-Qualification-Harness`: maintained qualification, RF-disabled Pico lifecycle, and prepare-now/publish-later tooling. It remains an independent repository.

Read applicable `AGENTS.md` files and current owning guides before operations. In Pico, read `README.md`, `CONTRACT.md`, `engineering/architecture.md`, the development guide, WTP and USB-management contracts, shared control API, GPS/PPS and clock discipline contracts, Si5351 and band support, installer, CI, and prepared-publication guides. In the Harness, follow its required contract, agent-operation, workflow-router, capability-matrix, operator-security, and relevant lifecycle/RF/prepared-release reading order. Derive commands from inspected current entrypoints and CLI help; do not invent Phase 1 flags or copy obsolete private commands.

The standing repository list below names three product repositories. Use the Harness as the assigned qualification tool and honor any explicit current Harness development/Git grants. Do not treat the earlier approval for a particular Harness reconciliation as unlimited authority for unrelated Harness changes. If a necessary Harness repair lacks current repository authority, complete unaffected work and resolve that specific boundary; do not hide the change in another repository or bypass an approval rejection.

Starting-state hints from 2026-11-08, all requiring recheck:

- Pico `devel` was `f6c90a4925d02d60b7404487e24316f239c48e7c`, with 234 canonical tests and both production Pi/Pico suites passing. Those runs did not constitute the Phase 2 physical campaign or produce a semantic RC.2 qualification result.
- The paired Pi source was `f59bba741ff367d0652f6db03b0bf67d4d10444a`.
- Harness reconciliation was merged at `492a1bec4cd904c9a94d9ade949a916ecc4793c6`; the original Harness checkout was clean and synchronized. That reconciliation fixed transmitter-side wrapper verification; it did not add the Pico RF adapter or complete Phase 1.
- Pico's checklist and Phase 1 prompt were local planning files, and Phase 1 had been started then stopped without implementation. Do not assume that state persists or that later work is absent.
- Historical Pico C images, wiring, GPSDO outputs, SDR settings, service states, and restoration receipts are provenance, not current setup evidence or a reason to select C automatically.

## 1. Establish current source, tool, and bench truth

1. Inventory every selected checkout: branch, full SHA, upstream, remotes, worktrees, staged/unstaged changes, untracked files, and relevant dependency/tool versions. Preserve user work. Fetch relevant refs without replacing working files; use isolated clean task worktrees when needed. Do not reset, stash, clean, force-push, prune, or delete existing work to obtain a convenient baseline.
2. Identify the intended complete Pico candidate and compatible Pi/Harness sources, including necessary Phase 1 changes. Distinguish code on a side branch from code delivered on `devel`. Freeze actual source and dependency selections; do not substitute older peers to obtain green tests.
3. Inspect current releases/tags, canonical Actions workflows/inputs, artifact availability and expiry, required checks, source-bound completion policies, installed-package/tool provenance, and prepared-publication support. Verify permissions without creating a release or dispatching a publisher.
4. Select an authorized Pico 2 W / RP2350 and confirm exact board identity, serial/physical topology, installed image/version/source, installer reference, current ownership/jobs, saved settings, and recovery resources. Read-only inspection must not activate a schedule or RF output.
5. Inspect actual selected hosts for active users, processes, services, source edits, USB owners/locks, receiver activity, and other campaigns. Coordinate around existing work; do not stop foreign work or steal a lock. Use strict pinned SSH trust and non-interactive authorization, with no private-key copying or agent forwarding.
6. Verify the current conducted RF path for each selected output: engine/output pin or CLK0, wiring/combiner, antenna disconnection, termination, attenuation, filter state, receiver input/identity, and safe-input basis. Do not infer it from old documentation or a prior test. Collect all genuinely missing physical facts in one concise request before a necessary RF boundary; continue non-transmitting work meanwhile.
7. Inventory and retain original exact firmware/developer bundles, same-board backups if needed, settings snapshots, installer transaction/reference state, service configuration/state, and GPSDO/SDR configuration. Keep secrets, full GPS coordinates, raw transcripts, flash dumps, and IQ private and outside Git.

Before any physical mutation, specify a recoverable final handback state for each device/host. Prefer restoring the verified original image/settings when compatible. If that is incompatible with the candidate's storage, select and document a supported recovery/fresh-default handback rather than discovering an impossible downgrade at the end. Do not automatically resume transmissions or an enabled schedule outside the bounded campaign; preserve its saved intent with a documented safe suspension/handback policy.

## 2. Freeze and build the actual RC.2 artifact

### Canonical identity and version

Use the current owning release/version rules. The target semantic version is `1.0.0-rc.2`, with tag `v1.0.0-rc.2`. Confirm the source commit and firmware's embedded source/version independently of tag metadata.

Do not rename a `0.1.0-ci.RUN.ATTEMPT` UF2 or edit its manifest to call it RC.2. The semantic release must be built canonically with its real embedded RC.2 version. A PR preview or synthetic merge artifact is not the installation candidate.

Complete source/software prerequisite corrections and review before reserving the semantic tag. When Phase 2 is explicitly invoked and the source is ready, it authorizes creation and push of a missing immutable `v1.0.0-rc.2` tag at the selected commit solely to obtain the documented canonical semantic build. Inspect the tag-triggered workflow first and confirm publication stays disabled. Record the exact tag object, peeled source SHA, workflow/run/attempt, and resulting artifacts.

If the tag already exists, verify it and its actual artifact provenance. Never move, delete, force-update, or reuse it for different firmware. A wrong existing tag or a later required source change creates a concrete version-selection problem; resolve it explicitly rather than relabeling old bytes or silently choosing another release number.

### Build and software acceptance

- Use `.github/workflows/software-build.yml` and its actual declared inputs with publication disabled. Follow the exact selected run through completion; do not pick whichever concurrent run finishes last.
- Require all current source-declared contexts, exact framework/test counts, nonempty focused checks, generated assets, host/browser/crypto/installer/packaging checks, firmware identity/memory/flash checks, and fresh reproducibility requirements. Preserve exact pins, official hashes, `--require-hashes`, and binary-wheel requirements.
- The optional publication job may be skipped intentionally. Failed, cancelled, timed-out, skipped, empty, truncated, or wrong-source required verification is unresolved.
- Run both actual production source-pair suites using WsprryPi's current `.github/workflows/debian-non-hardware.yml` recipes against the exact final Pico source SHA and intended Pi revision: `wtp-network-loopback` and `wtp-usb-management-pair`. Include runtime/interop/config, actual Pico USB driver and Pi clients, framing/ACK, strict refusals, routing/source-selection, and required browser gates. Record pinned recursive dependencies and any tested uncommitted changes; a release candidate must have a clean, reproducible source selection.
- If source, schema, descriptors, units/limits, carrier, or protocol-facing semantics change, inspect/update every affected producer/consumer and paired adapter together. Preserve the one current control-major prerelease policy and independent WTP, transport, and storage versions; do not add compatibility fallbacks or weaken validators.

Retrieve and independently verify the exact successful canonical deployment/audit archives using the owning tools. Bind source, semantic version, branch/tag, run/attempt, jobs, artifact IDs/digests, payload hashes, manifest, dependency identities, and linked image. Retain the complete developer bundle used for installation, not just a loose UF2.

Choose durable private evidence storage outside source, installer-managed directories, and operating-system temporary storage. Record the UF2 hash and byte inventory before installation and compare them throughout the campaign. Firmware changes invalidate physical acceptance for the affected image; software fixes must not be substituted after a passing run without rebuilding, refreezing, and repeating affected acceptance.

## 3. Physical installation and preservation acceptance, RF disabled

Use the maintained Harness Pico lifecycle workflows, with exact baseline/candidate bundles and current production installer/schema/adapter identities. Derive current `lifecycle pico-plan`, plan, execute, status, and report syntax from the selected implementation. A lifecycle pass is installation/preservation evidence only.

Run both supported tracks using appropriate boards or a verified recoverable sequence:

- **Fresh track:** preserve any unique original state first, select the explicit guarded erase workflow, verify actual blank flash, install the exact candidate, check unconfigured defaults and idle/inactive output, perform the maintained synthetic-setting/reinstall/readback checks, and verify postboot identity/reference state.
- **Preserve track:** independently identify the real baseline image/bundle and compatible storage generation, seed the maintained distinctive synthetic settings, exercise identical-image reinstall and compatible upgrade to the exact candidate, compare saved semantics through production readback, exercise supported recovery cases, and verify final state.

Where RC.2 introduces new persisted fields or record versions relative to the selected baseline, add the maintained migration/default/round-trip scenarios. Ordinary preservation does not establish new-field migration or arbitrary downgrade support. Keep deterministic journal/fault coverage; do not introduce physical power-cut or destructive fault campaigns merely to expand this phase.

Use `scripts/usb_installer.py` with the generated exact developer bundle, production transaction, same-board image reference, and postboot verification. No direct `picotool load` substitute, receipt editing, identity rewriting, stale-reference deletion, or erase to conceal a preserve-mode refusal. Reconcile a stale reference only through the documented original-bundle/same-board comparison workflow.

Account for the fresh track's deliberate data destruction and the primary lifecycle tracks' synthetic settings. Restore or transition explicitly to the selected RF-test configuration; do not treat their default final state as original-settings restoration. Retain exact original bundles/backups until all handback duties close.

With the actual candidate installed and RF disabled, check the affected operator paths through supported physical USB and browser access: startup time/calibration feedback, hostname editing before station commissioning, authentication-lock explanations, radio-pin/GPS controls, local favicon delivery, and hardware-only saves while standalone operation is suspended. Verify authoritative saved/active readback and deliberate restart behavior, rather than inferring success from a screenshot. Keep WSPR enable/apply prerequisites and saved suspension/schedule intent intact. Reuse existing supported physical Pi/Pico identity/control handoff checks when that companion configuration is selected; distinguish those observations from a full coordinated-system/public acceptance claim. Do not install unrelated Pi/RP1 components or create a new operator workflow merely for this smoke check.

## 4. Freeze the conducted RF qualification matrix

All four required rows must use the **same qualified RC.2 firmware bytes**; runtime settings may differ and must be recorded. A special diagnostic or engineering image cannot supply a missing ordinary-image result.

| Required configuration | Engine | GPS/PPS use | RF correction subcases |
| --- | --- | --- | --- |
| GPIO without GPS/PPS | Direct GPIO / RP2350 PIO-DMA | Firmware GPS/PPS input disabled; explicit supported non-GPS UTC source | Manual policy, with measured/specified manual correction recorded |
| GPIO with GPS/PPS | Direct GPIO / RP2350 PIO-DMA | Enabled; usable serial/PPS association and UTC independently observed | Automatic RF correction off, and on with qualified Pico-oscillator provenance |
| Si5351 without GPS/PPS | Current supported Si5351 profile | Firmware GPS/PPS input disabled; explicit supported non-GPS UTC source | Manual policy, with measured/specified manual correction recorded |
| Si5351 with GPS/PPS | Current supported Si5351 profile | Enabled; usable serial/PPS association and UTC independently observed | Automatic RF correction off, and on with qualified Si5351 provenance and required CLK2 loopback |

Each row and selected correction subcase must cover **TONE, WSPR, QRSS, FSKCW, and DFCW** through the maintained Phase 1 production campaign route. Four engine/GPS rows are not a claim that only four executions suffice: the two GPS-enabled rows have explicit correction-off/on subcases, yielding six configuration variants and thirty mode/variant cells before the Harness's independent observation requirements and any selected band coverage.

Before RF, freeze a reviewable campaign manifest containing:

- exact board/serial/firmware source/version/UF2 hash, boot identity, system clock, RF engine/output, GPIO drive or Si5351 model/reference/drive, pin allocations, amplifier/filter selections, and runtime configuration revisions;
- selected representative band/frequency points justified by current support, engine limits, RC.2 changes, and retained evidence; coverage must be stated exactly, not generalized to every band or continuous frequency range;
- actual receiver/path, sample rate/bandwidth/gain, AGC/bias-tee state, exact-count capture and overflow policy, receiver calibration profile/validity/uncertainty, reference source/GPSDO configuration where used, decoder/analyzer identities, and stopping criteria;
- expected station identity, WSPR message/type/slot sequence, keyed message/timing/separation, finite TONE cadence, repetitions, independent transaction counts, and result thresholds from current contracts;
- GPS UTC discipline, location source, automatic RF correction selection, manual PPM/residual trim, learned estimate identity/age/bounds, effective correction, CLK2 feedback, and independent receiver-only calibration as distinct recorded facts;
- finite per-operation, acquisition, job, capture, decoder/analysis, cleanup, row, and overall campaign deadlines; finite total commanded RF budget; and bounded retry/diagnostic limits calculated from the actual selected job plans.

Do not invent universal bands, accuracy thresholds, or numerical budgets from historical prompts. Select reasonable bounded values from the current product/Harness contracts and actual setup, explain material choices, and proceed under the standing authority. Physical configuration facts must be established before their relevant RF effect. If required coverage cannot be performed, retain that precise limitation rather than silently shrinking the matrix.

## 5. Execute through the maintained Harness

1. Validate plans and rehearse the complete composition without devices/RF first. Verify current installed-package/module identity on every executing host so an old installed Harness cannot impersonate the candidate tool source.
2. Use explicit live/RF opt-in and the maintained authorization boundary. Do not add an extra approval prompt at each mode when current authority and the verified setup already cover it. Print the durable progress JSONL path and exact viewer command before long-running work.
3. Acquire exact device/host/receiver ownership; verify no competing jobs or schedules can start. Register cleanup before receiver/service/device effects and before any RF enable. Preserve original state and protect credentials/location-bearing records.
4. Establish the actual receiver and retained-output readiness plus the required RF-off preamble before arming. Use supported production WTP/management interfaces, strict current descriptors, target/boot/profile/revision binding, and complete locally timed Pico jobs. No per-symbol network/USB streaming or Pi hardware commands against Pico.
5. For no-GPS rows, verify firmware GPS/PPS use is disabled and observe the selected non-GPS UTC source; no physical cable removal is required solely for that row. For GPS rows, verify real UART/PPS pairing, qualified UTC, current source/age and relevant oscillator estimate before correction-on jobs. A GPSDO reference tone alone is not proof that firmware uses GPS/PPS.
6. GPS time, GPS location, Pico oscillator correction, Si5351 reference correction, manual trim, and receiver calibration remain independent. Missing/expired/conflicting correction prerequisites must produce the defined refusal, not a hidden manual fallback or an adjusted acceptance threshold.
7. Exercise finite TONE cadence and quiet periods; WSPR's maintained consecutive complete-frame/decode requirement; and QRSS/FSKCW/DFCW's maintained independent transaction/capture count. Do not count repeats in one job as separate independent observations where three transactions are required.
8. Retain exact IQ counts, first-read discard, actual sample settings, overflow/clipping/cancellation state, UTC/sample-relative timing applicability, complete decoder logs and artifacts, generated plans/expected events, analysis outputs, and full transmitter terminal/ownership evidence. Reject malformed, truncated, wrong-device, wrong-source, or ambiguous evidence.
9. Verify actual engine output inactivity and required post-job silence independently of process exit or a disconnected USB handle. A successful completion response does not establish RF silence. Reconcile lost replies or resets before another write/job; never replay an uncertain ARM automatically.
10. Keep receiver/fixture blockage separate from transmitter failure. Capture or decoder failure, overload, ambiguous signals, and insufficient resolution do not become transmitter unqualification merely to fill the table. Preserve failed/refused attempts and actual skipped/unattempted cells; no cherry-picking passing repeats into a fictitious complete campaign.
11. Exercise the supported bounded failure/recovery paths appropriate to the candidate and actual rig. Reuse deterministic tests for disruptive failures that would require unsafe wiring changes, uncontrolled RF, or unrelated host destruction. State the distinction between simulated failure coverage and live observations.
12. Record every selected cell and independently required repetition. A measurement failure or inconclusive result retains its proper classification. Follow maintained stop/continue precedence; cleanup failure, loss of ownership, unsafe path, fixture blockage, or abort must not be ignored to continue transmitting.

Automatic correction need not improve the Si5351 carrier to complete this phase. A valid inconclusive comparison consistent with former item 21 must remain inconclusive. This does not waive mode correctness, finite-job safety, supported engine/band operation, required decodes, meaningful signal/measurement gates, or verified cleanup. Distinguish the closed research question from a new actionable product defect.

## 6. Correct defects and requalify the final bytes

Investigate failures autonomously within scope, preserve original evidence, and choose bounded reasonable diagnostics. Fix actionable firmware, installer, companion, test, or documentation defects in their owning authorized repository. Do not weaken schema validation, decoder expectations, measurement bounds, required counts, cleanup checks, or test inventories to turn a failure green.

Any firmware/source/build-input change requires a new canonical artifact with truthful identity and independent validation. Preserve the unsuccessful candidate record. Reconcile semantic-version/tag constraints without moving existing tags or relabeling payloads. Re-run applicable software acceptance and every affected physical cell; justify any reuse with exact unchanged source/artifact/setup identities. The final matrix and readiness report must identify one actual final RC.2 UF2, not a mixture of predecessor images.

Harness/controller/analyzer changes must be bound separately from firmware changes. Revalidate their schemas, package/runtime identities, affected regression checks, and result interpretation; reanalyze retained captures only through supported authenticated replay. Reanalysis does not become a new live transmission or erase the original result. If a changed controller or publisher invalidates a sealed preparation, create a new preparation rather than editing its proof.

## 7. Prepare the publish-later packet and prove the handoff

Use the current maintained Pico prepared-publication and Harness retained-release interfaces. Current command families include `scripts/ci/prepared.py prepare/verify` and Harness `lifecycle release-session-plan`, `release-prepare`, `release-status`, and `release-publish --validate-only`; inspect actual help and effect boundaries first.

- Select **independent Pico scope** unless the user explicitly selects a coordinated system release. Identify the fixed Pi companion and relevant dependencies without building/publishing unrelated Pi or RP1 releases.
- For the semantic RC.2 artifact, use the owning release-stream provenance and exact successful run/attempt/source/version. Do not pass a devel CI version as a semantic-release shortcut.
- Retain the complete original deployment/audit archives, independently verified developer bundle, exact intended public file inventory, manifests/checksums, source/dependency/build identity, prepared JSON/digests, tool/controller/source copies, durable progress records, and private physical qualification index. Current tooling retains nine Pico public files; discover and enforce the actual source-declared inventory rather than hard-coding an obsolete count.
- Bind the physical campaign's installed UF2 hash to the prepared packet's payload hash, firmware embedded identity, canonical build run, and selected semantic tag. Demonstrate byte equality; matching filenames or version strings are insufficient.
- Exit preparation and verify the retained handoff in a fresh process/environment using supported commands and a new verification directory. Exercise `release-status` and online read-only publication validation where supported. Do not execute `--enable-publication`, `publish=true`, release asset upload, release creation, or bookmark updates.
- Record original Actions artifact availability/expiry and external proof requirements. Retained local bytes do not bypass missing/expired canonical validation proof. If current online publication readiness cannot be assessed, say so; local integrity alone is not permission or proof of future readiness.
- Produce concrete Phase 3 inputs: durable state/packet paths, exact digests, expected publisher source/implementation identity, version/tag/source/run/attempt, public-file hashes, qualification summary/index, fixed companion selection, current remaining public-consumer acceptance steps, and any unresolved prerequisite. No promise of a future rebuild may replace the tested packet.

After Phase 2, public RC.2 download/installer acceptance remains unperformed because the release is unpublished. Record it as a Phase 3 obligation, not a failed prepublication test or a fabricated pass.

## 8. Restore and independently verify handback

Stop only owned RF/jobs/captures/helpers, release owned leases and locks through supported protocols, and verify empty/unowned/idle and inactive output as appropriate. Restore the selected device image/settings or documented supported handback image through the shared installer. Compare saved semantics and same-board references, retaining exact bundles for future upgrades from another account/host.

Restore only services, receiver settings, GPSDO outputs/configuration, and other state the campaign actually changed. Preserve unrelated work and persistent data. Do not unlink another account's USB lock, change its ownership, relax Linux protection, or bypass a refused identity lease. Verify actual final host/device/reference state rather than repeating an old restoration claim.

Retain original images/backups, candidate packets, source/build environments, failed attempts, raw IQ, and private records with an identified verification/recovery duty. This phase is not general repository/harness cleanup and does not authorize deleting branches, worktrees, captures, shared tools, or unrelated environments. Cleanup or restoration failure overrides successful measurements and prevents a completion claim until resolved or clearly reported as a blocker.

## 9. Adversarial review, iteration, and delivery

**Perform an adversarial review.** Challenge at least:

- whether Phase 1 is actually delivered and the installed Harness controls a Pico rather than a Pi shim;
- whether the image on every required board/cell is exactly the final semantic RC.2 payload, with real source/build identity and compatible fixed companions;
- whether fresh and preserving installation, new-field migration where applicable, current serial/topology, settings readback, and installer references were independently verified;
- whether all four rows, correction subcases, five modes, selected bands, and independent observations ran rather than being inferred or skipped;
- whether firmware GPS/PPS, non-GPS time, manual/automatic transmitter correction, Si5351 CLK2 input, and receiver-only calibration were actually distinguished;
- whether the RF path and receiver/reference facts are current, the capture truly preceded RF, all bounds held, raw evidence is authentic, and decode/analysis output supports the claimed result;
- whether failed/refused/ambiguous results, UTC/sample timing limits, and former item 21's final inconclusive disposition remain truthful;
- whether output shutdown, ownership release, original-state restoration, host services, SDR/GPSDO configuration, and private evidence protection are verified;
- whether retained packet bytes equal tested bytes and can be verified in a later process without rebuilding, weakening provenance, or prematurely publishing;
- whether all code/documentation changes, generated assets, source-pair suites, canonical contexts/counts, intended refs, and final CI results belong to the actual final candidate.

**Iterate through issues, close them, and run another adversarial assessment.** Fix actionable findings, rerun affected checks/qualification, and review the corrected final candidate again. Do not mark complete while a required check/cell is failed, cancelled, timed out, skipped, wrong-source, missing, or supported only by mocks; explicitly separate the legitimate inconclusive Si5351 improvement question from required operational acceptance.

**When done, commit and push. Then report.**

- Commit only task-owned, reviewed code, tests, sanitized current engineering summaries, and appropriate documentation in their owning authorized repositories. Keep raw IQ, full-board dumps, credentials, precise location-bearing logs, private account context, machine-specific paths, and retained firmware/publication packets out of source control.
- Use normal branches/PR requirements and safeguards. Push validated changes without CI-skip markers, follow applicable CI through completion, and fix failures. Report actual commits/refs/PR states; do not claim `devel` delivery for side-branch-only fixes. Do not publish the release as part of Git delivery.
- Update checklist item 2 to ⏳ when execution starts and ✅ only after exact-artifact preparation, required software and physical acceptance, packet handoff verification, restoration, and final adversarial review are complete. Do not mark Phase 1 complete merely by running this prompt. Leave item 3 ▧.
- Consolidate enduring operator/engineering information into current maintained documentation, keeping public documentation on Read the Docs. Do not create another checklist, evidence dump, archive, or permanent execution diary. Retire this task-specific prompt when its completed handoff duty ends and repair its checklist reference.

The final report must give:

1. Final Pico/Pi/Harness and tooling revisions, dirty-state identities where relevant, tag object/peeled source, embedded firmware version/source, UF2 hash, canonical run/attempt, dependency selections, and direct CI links.
2. Installation fresh/preserve/migration results, baseline/candidate bundle identities, exact boards/serials, and actual final image/reference/settings state.
3. A cell-by-cell engine/GPS/correction/mode/band result table with independent transaction/capture/decode counts, commands, durable evidence paths/digests, numerical measurement bounds, and all failures/refusals/inconclusive/unattempted cases.
4. Current RF path, clock/drive/output profile, receiver/calibration/GPSDO facts, time/correction provenance, actual RF duration versus budget, and what those measurements do and do not qualify.
5. Adversarial findings and disposition, code/documentation changes, commits/pushes/PRs, required check results, and concrete blockers.
6. Verified host/device/service/reference restoration, retained recovery materials, private data handling, and any unresolved handback duty.
7. Exact publish-later state/packet paths and digests, fresh-process/online validation results, artifact-expiry dependencies, and the remaining Phase 3 publication/public-consumer steps.
8. Explicit confirmation that former item 21 remains finally closed as inconclusive, the experimental capability remains available, and no RC.2 release/assets/bookmark publication occurred. List any deliberately created semantic tag as a separate preparation effect.

Do not claim completion while a required operational acceptance, exact-byte binding, restoration, or retained-packet prerequisite remains unresolved.

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
