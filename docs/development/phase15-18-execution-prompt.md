# P15.18 USB installer execution prompt

Prepared and updated 2026-10-17. **Saved for future execution.** Execute item 7
of the [Consolidated backlog](consolidated-backlog.md); current status and order
are recorded only there. The P15.18 filename retains the historical slice ID.
Preparing this prompt changes documentation only. Do not implement, build,
flash, install tools, operate devices, stage, commit or push until the operator
invokes it for execution. The instructions below then define the bounded task.

## Objective and execution authority

Implement USB installation and settings-preserving firmware upgrades for
**WsprryPico on Pico 2 W / RP2350**, with two access paths:

- A standalone host tool, accessible through a maintained `curl | bash`
  bootstrap and a directly runnable local entry point, without WsprryPi.
- WsprryPi access for the selected locally USB-connected Pico, using the same
  installer implementation and preservation rules.

Default to the latest verified, compatible normal CI image from the canonical
WsprryPico devel workflow, including CI testing builds; a stable release is not
required. A GitHub release may provide public download transport for those
exact CI bytes. Support explicit version/stable selection and optional local
compilation through an explicit developer path. Preserve saved settings and
other durable state during upgrades. OTA is ruled out by operator direction
(2026-10-17) because its flash-layout tradeoff sacrifices too much flexibility;
do not reserve an OTA partition or implement an OTA path.

When invoked, this prompt authorizes bounded implementation, tests and
development documentation in these repositories, plus attributable commits
and non-force pushes to their existing accepted branches/upstreams:

- `/Users/lbussy/GitHub/WsprryPico`: installer core, bootstrap, packaging/build
  integration, focused tests, current instructions and acceptance evidence.
- `/Users/lbussy/GitHub/WsprryPi`: only the companion installer entry point,
  selected-Pico runtime/UI integration, lifecycle/permissions integration,
  deployment of the shared installer, and related tests/development docs.
  Components such as `WsprryPi-UI` remain parent-repository content.

It also authorizes publishing and removing installer-specific CI download/test
releases in WsprryPi/WsprryPico when needed for this path, including draft,
asset-upload, publish and cleanup operations, and creating/pushing unique
pre-1.0.0 tags at the exact CI source commit. Apply the bounded publication and
removal rules below; routine actions within this authority need no further
confirmation. Do not publish a 1.0.0-or-later or stable release, move/delete an
existing tag, replace published bytes, or remove unrelated releases.

It also authorizes a separate read-only reviewer/subagent for independent
adversarial review and reassessment. Other family repositories remain outside
the write scope. Do not create a new protocol repository or PR, modify
repository settings, start the separate web UI review or documentation site.
Hardware/service operations follow current operator
setup statements and each repository's `AGENTS.md`; this saved prompt is not evidence of a connected
test setup. Do not run the WsprryPi system installer merely to test Pico flashing.

## 1. Verify prerequisites and inspect both repositories

Start in `/Users/lbussy/GitHub/WsprryPico`. Read its `AGENTS.md`, `README.md`,
`CONTRACT.md`, `docs/architecture.md`, `docs/development/README.md`,
`docs/development/consolidated-backlog.md` and the completed acceptance in
`docs/implementation-plan.md`.
Read Pi's root and applicable component instructions before work there.

Verify accepted completion of this sequence using actual result records:

1. P15.14 USB control, including USB management/time and exact-pair evidence.
2. P15.15 persisted GPIO drive strength and its Pico/Pi compatibility behavior.
3. P15.16 uninhibited normal default and explicitly selected inhibited variant.
4. Current item 6 software/build CI acceptance, with actual successful run and
   artifact identities, normal UF2, canonical versioned manifest and SHA-256
   inventory from the [CI handoff](software-build-ci-execution-prompt.md).

Saved prompts, checklist intentions and successful builds alone do not establish
acceptance. Read the accepted USB/drive/normal-target and CI result records and
exact supported source pair. Item 9's testing prerelease is not a prerequisite:
this installer task may publish the CI download assets needed for its own
acceptance without executing or claiming completion of item 9.
If a prerequisite is incomplete, report it and stop before implementation;
do not absorb the missing phase into P15.18.

Preparation snapshot only: Pico `devel` was
`2aef1edeca30e86deb412f4bbb59ec53462bee78`; Pi `devel` was
`eafae380bdcd9438612c42f2a86f046c748acce2`. The Pico checkout already contained
uncommitted P15.17 prompt/index/checklist preparation. P15.15–P15.19 were Not
started. Refresh this at execution; these are not the future accepted baselines.

Inspect full HEAD, branch/upstream/remotes, staged/unstaged/untracked changes
and relevant nested instructions in both repositories. Preserve existing work,
builds and private evidence. Do not reset, stash, clean, switch branches or
absorb unrelated changes. Record the accepted firmware/Pi/release identities
before editing. Read-only inspection grants no additional write scope.

## 2. Freeze the shared installer design

Keep one maintained installer implementation owned by WsprryPico. The Pi
entry point calls or deploys an identified version of that implementation;
do not fork its device selection, release resolution, UF2 validation, flashing
or preservation logic into an independent updater.

Inspect at least these existing sources and contracts before choosing files:

- `CMakeLists.txt`, `CMakePresets.json`, `firmware/CMakeLists.txt`,
  `scripts/build_pico.sh`, `cmake/verify_pico_dependencies.cmake` and the accepted
  P15.16 target/build recipes.
- `src/standalone/pico/flash_layout.hpp`,
  `cmake/standalone_link/memory_flash.incl`,
  `scripts/check_standalone_image.py`, `tests/flash_layout_tests.cpp` and the
  canonical CI manifest schema/validator, verified CI artifacts and any existing
  corresponding public download assets. Reuse item 6's format; do not create a
  competing installer/release manifest.
- `docs/development/usb-cdc.md`, `docs/protocol/USB-Management.md`,
  `docs/development/usb-local-configuration.md`,
  `docs/development/configuration-updates.md`,
  `docs/development/saved-progress.md` and the current shared application API.
- Pi's selected-member USB discovery, management client, runtime bridge,
  `src/wtp_integration/`, `src/wtp_runtime_bridge.hpp`, source-owned
  `WsprryPi-UI/` controls, and existing installation/permission patterns.

Inspect historical bench tools for useful mechanisms, but do not turn a
fixture/provisioning/full-erase script into a production updater by renaming it.
For example, `scripts/phase12_flash_preservation.py` checks a specific historical
transaction; it is not a general firmware-update preservation proof.

Record a short implementation decision covering the core language/dependencies,
CLI and structured result contract, supported host/architecture matrix,
picotool acquisition/version, Pi deployment boundary and interrupted-operation
recovery. Use existing project conventions; do not add a framework to wrap a
small host tool. Installer/build helpers belong under `scripts/` or `cmake/`,
owned compiled implementation under `src/`, and tests under `tests/`.

Linux/Raspberry Pi is required for Pi access. Verify and document each
standalone platform claimed, including macOS if offered. Bash availability
alone does not establish native Windows/WSL USB support. Resolve routine choices
within this scope and mark unsupported platforms honestly.

## 3. Provide standalone bootstrap and local entry points

Deliver a small maintained `curl | bash` bootstrap that obtains an identified
installer version and invokes its ordinary CLI. Also support downloading,
inspecting and running the same entry point directly. Document the actual
published URL after the code is pushed; do not invent a working URL beforehand.

Bind bootstrap payloads and dependencies to a resolved revision/version so a
moving branch cannot mix files from different revisions. Use HTTPS, checked
download failures, bounded timeouts, private temporary directories and cleanup.
Treat release/API/manifest content as data, not shell code. Avoid shell string
construction from URLs, paths, tags, device names or manifest fields.

Expose explicit operations for discovery/planning, initial installation,
preserving upgrade, default latest-CI selection, explicit version/stable
selection and local-build use.
Choose final command names during implementation and document exact examples.
The default CI download path must not require Git, a compiler, the Pico SDK
or an operator's GitHub account/token.
It may require narrowly documented USB/picotool/runtime dependencies.

Handle missing dependencies and USB permissions with clear actionable errors.
Do not run the whole bootstrap as root or silently install a full SDK/toolchain.
Where dependency installation is offered, show and scope the operation; use
privilege only for the specific operation that requires it. Verify tool sources,
versions, checksums and redistribution obligations rather than bundling an
unidentified local executable.

Keep confirmation/input usable when stdin is the downloaded script. Define
noninteractive flags explicitly; unattended execution must require an explicit
device and requested operation. Provide useful exit codes and machine-readable
results for Pi integration. Help/discovery/planning must not flash, reset,
install packages, change services, write device settings or acquire RF ownership.

## 4. Select, publish when necessary and validate CI firmware

Ordinary resolution selects the newest successful eligible canonical devel CI
build for the normal Pico 2 W application, with every required job/check passed.
Define deterministic ordering by source/build identity; rerunning an older
commit or republishing its assets must not make it newer than a later accepted
source. Verify trusted workflow/repository/branch, full source SHA, run ID and
attempt, profile, embedded version and manifest/checksum identity. Exclude PR/
fork/unreviewed workflows and inhibited/bench/provisioned variants. Resolve once
per transaction and pin that immutable bundle even if newer CI completes while
the installer runs. Show the chosen CI source/run/version and any newer failed
or incomplete run honestly.

The default includes verified CI prereleases without a separate testing opt-in.
Explicit version, older compatible image and stable selections remain available,
with the same validation and downgrade checks. Do not use GitHub's stable
`releases/latest` endpoint as the latest-CI resolver: its
[full-release semantics](https://docs.github.com/en/rest/releases/releases#get-the-latest-release)
exclude prereleases. Do not scrape HTML, select the first UF2 or order candidates
solely by release publication time. Missing, expired or invalid latest assets
must produce an actionable refusal, never silent fallback to stable, older
bytes, an inhibited image or local compilation.

Consume the schema actually accepted in item 6 rather than defining a competing
manifest. At original preparation, planned assets were
`WsprryPico-<version>-pico2_w.uf2`, `release-manifest.json` and `SHA256SUMS`.
Validate product, Pico 2 W/RP2350 board/family, normal uninhibited variant,
version/tag/source agreement, supported protocol/Pi pair, persistent-storage
compatibility, asset size and SHA-256. Confirm asset and release metadata agree
about CI/testing status. Refuse unsupported manifest/storage versions.

Verify that the default installer can fetch its metadata and payload anonymously
over HTTPS. Ordinary [Actions artifact downloads](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts)
require GitHub sign-in/read access; do not turn that into an end-user token
requirement. If a verified existing public distribution path suffices, use it.
Otherwise publishing the exact verified CI bundle as an installer download
prerelease is authorized here, without waiting for item 9.

If release assets are needed, provide a small maintained promotion/discovery
path for subsequent eligible CI builds, not only a one-time manual upload.
Reuse item 6's successful build and exact artifacts. Publication credentials
belong only in the authorized maintainer/CI context; ordinary installer runs
must never publish/delete releases or request write credentials. Keep any
publication workflow narrowly scoped to trusted canonical CI output, with
only required permissions and no privileged execution of fork/PR payloads.

Before publication, freeze and review the complete CI bundle, checksum inventory,
required notices and notes. Verify source F is clean, committed and remotely
available. Choose a collision-free version/tag below 1.0.0 under the existing
convention, normally a v0.x.y development/testing identity. Embedded version,
manifest and tag mapping must be consistent with the declared CI version policy.
If another version is needed, arrange it before a new qualifying CI run; do not
edit/rebuild downloaded UF2s locally or relabel bytes to invent agreement.
Create an annotated tag explicitly at F, push only that tag and independently
verify its remote object and peeled commit. Never tag a moving branch name or
let a release tool silently select the repository's default branch.

Use a draft with an explicit asset allowlist and notes file, verify its complete
uploaded assets against the frozen CI hashes, then publish as a prerelease with
latest=false. Download the published assets afresh without authentication and
rerun manifest/checksum/UF2 validation. Record the release/asset IDs, URLs, tag,
source/run/attempt and hashes. Publishing only supplies download transport; it
does not add RF, installer or whole-product qualification. Make the candidate
discoverable through the maintained latest-CI resolver only after this audit;
do not update a default pointer to an incomplete draft or missing release.

Release removal for an installer-created temporary, failed or superseded CI
download/test release is authorized when necessary. Capture its identity and
sanitized disposition first, and ensure no maintained default/documented path
is left pointing at removed assets: retain or verify a replacement distribution
before retiring a live default. Deletion tests may use an explicitly selected
temporary candidate without replacing the live default. Keep completed download
transactions bound to their verified cached bytes; new resolutions must handle
removal honestly. Preserve historical source/result evidence and unrelated
releases. Use the [release deletion operation](https://cli.github.com/manual/gh_release_delete)
without tag cleanup; release deletion is separate from tag deletion. Retain the
tag and never reuse its identity for different bytes. Record/verify the actual
post-removal state; partial publication or failed cleanup is not a success.

Download only the selected payload and required metadata/notices. Bound sizes,
validate safe asset names and reject traversal, ambiguous duplicates, missing
fields, malformed checksums, partial downloads and unexpected payloads. Verify
integrity before any destructive device action. Checksums are not signatures;
retain the project's HTTPS/repository trust boundary without inventing signing.

Parse the actual UF2 and validate all flash write/erase extents, not merely its
filename or declared size. Enforce the accepted application/storage boundaries
and the exact pinned RP2350 boot-workaround treatment. Review historical
validator compatibility allowances before reuse: accepting an older image for
inspection is not permission to install it over current saved-progress storage.
Do not accept unknown flags/blocks or address alias/wraparound as a bypass.

Use the same validated cached bytes throughout a transaction. Prevent replacing
the checked file between validation and privileged flashing. Cache by immutable
identity/digest, verify cache hits and record the selected source and artifact
in the result. GitHub outage, rate limits and unavailable assets must leave the
device untouched; support a previously verified local bundle where practical.

## 5. Support explicit local builds

Make local compilation an explicit advanced/developer selection. Use the
accepted P15.16 normal target and dependency/toolchain pins, fresh task-specific
build directories, truthful source/dirty identity and applicable linked-image
checks. Recheck pins at execution rather than copying preparation values.

Support an identified local source checkout or immutable source revision using
documented existing build helpers. A dirty development build must be clearly
labelled and explicitly selected; never present it as the official release.
Do not include local credentials, station identity or provisioning headers in
a generic installer-built image. Do not overwrite the user's build outputs.

Generate local metadata sufficient for the same board, variant, image-extent
and storage-compatibility checks. Feed the output into the same installation
and preservation transaction as a release image. A successful compiler exit
alone is insufficient. No download/SDK installation should occur on the ordinary
release path, and no local-build failure may trigger an implicit alternate image.

## 6. Bind the exact USB device and quiesce ownership

Use the existing USB identity/role contract. Console, WTP and management have
different CDC roles; tty ordering and friendly names are not stable identity.
Bind physical parent/USB serial, application device identity and current
boot/session as available. The USB serial and WTP device ID are not the same
identifier. Do not rely on the development VID/PID alone.

If several devices are present, require explicit selection. Revalidate identity
when handles reopen and across application-to-BOOTSEL-to-application transitions.
Do not flash whichever board happens to re-enumerate first. Detect disappearance,
replacement, serial conflicts, wrong family, access denial and concurrent opens.
Take an exclusive per-device updater lock used by both entry points.

For a running application, verify authoritative state and coordinate with the
existing local scheduler, WTP owner and pending management transactions. Refuse
an active/armed/uncertain job by default; do not steal ownership, abort a frame
or clear STOP/fault state as an incidental update step. Integrate Pi scheduling
and reconnection suppression for only the selected member. Do not suspend the
entire fleet or change unrelated Pi GPIO/backends/services.

Verify actual bootloader entry support. The preparation USB contract explicitly
states that a 1200-baud touch does not invoke a reset-to-bootloader handler.
Do not assume a CDC baud toggle, picotool force option or network reboot can
enter BOOTSEL on the accepted image. Provide a clear deliberate BOOTSEL procedure
for first installation and recovery. Automatic entry is optional and must be
supported and validated; any necessary firmware change must remain a minimal
USB-local, idle/ownership-guarded maintenance operation with focused tests.
Do not extend WTP with firmware-transfer commands.

## 7. Preserve all durable state during upgrades

Define initial install and preserving upgrade distinctly. A board already in
BOOTSEL is not necessarily blank. Read and classify existing storage using an
identified source/layout; unreadable or unknown data is not permission to erase.
Normal install/upgrade must not reset, reprovision or write saved settings.
Factory reset, incompatible migration and destructive recovery are outside the
ordinary workflow and must never be an automatic fallback.

Derive the authoritative layout from accepted source, linked-image checks and
manifest compatibility. Preparation offsets on the supported 4 MiB flash were:

| Region | Flash offsets, end exclusive |
| --- | --- |
| Application | `0x000000..0x3f0000` |
| Saved progress | `0x3f0000..0x3f2000` |
| Diagnostic scratch | `0x3f2000..0x3f3000` |
| Access state | `0x3f3000..0x3f5000` |
| BTstack bonds/state | `0x3f5000..0x3f7000` |
| Profiles | `0x3f7000..0x3fb000` |
| Standalone configuration and watermark state | `0x3fb000..0x3ff000` |
| Reserved boot-workaround sector | `0x3ff000..0x400000` |

These are offsets, not XIP addresses. Re-derive and test actual picotool/ROM
address and erase behavior, including the special UF2 workaround block; do not
assume a numeric address comparison alone proves which physical sectors change.
Retain settings, hostname, Wi-Fi credentials, station/application configuration,
schedules, pins/drive strength, frequency opt-ins, profiles, access/bonds,
drafts, STOP/suspension semantics and consumed-slot/watermark state. Do not
change saved enablement or advance progress as part of upgrading.

Before writing a preserving upgrade, capture a verified same-board backup of
all reserved durable regions and enough old-image identity for recovery.
Record hashes and compatibility privately. A redacted API JSON export alone
cannot restore passwords, bonds or private access material. Store sensitive
backups outside Git/web roots with owner-only permissions and bounded retention;
never emit their bytes in logs, URLs, browser storage, receipts or reports.
Do not transplant a backup to another device.

Fail before programming if required backup/readback/compatibility checks cannot
be completed. Restrict ordinary programming/erase operations to approved image
extents; no mass erase or rewritten configuration banks. Verify preserved bytes
before application boot where feasible, then verify semantic state after boot.
Distinguish actual legitimate firmware journal changes from installer writes
with precise source/evidence; no broad allowance for arbitrary changed storage.

Do not silently implement a storage migration or promise arbitrary downgrades.
Explicit old-version selection remains subject to layout/schema compatibility;
reject unsupported rollback. Ordinary recovery reuses an identified compatible
image and retained storage. The installer cannot promise atomic rollback after
power loss; there are no A/B firmware slots in this scope.

## 8. Program, reconnect and handle interrupted operations

Use a verified picotool version and supported RP2350 USB workflow. Verify the
actual command semantics from pinned local source/help and official upstream
documentation when needed. Construct subprocess arguments directly. Scope any
privileged helper to validated device/image operations rather than arbitrary
commands or browser-provided paths.

Implement bounded stages: resolve/validate, select/quiesce, enter BOOTSEL,
back up, program/verify, reconnect, verify identity/version/settings, finish.
Expose useful progress and cancellation boundaries. Cancellation before writing
leaves firmware/state unchanged; cancellation during programming must produce
an honest recovery-needed result, not a success message or blind rollback.

Use a private host transaction record with device identity, source/artifact
digests and completed stage. Avoid claiming exactly-once behavior across host
or power loss. Retry/resume must re-identify the same board, revalidate bytes
and determine actual device state. Never automatically erase/reflash another
device after timeout or blindly replay ambiguous settings operations.

After programming, verify the written image with the supported tool, reconnect
with fresh USB sessions, and check immutable identity, firmware version/build,
management compatibility and retained public settings/revisions. Preserve
secret-state evidence through the appropriate private flash checks. USB presence
or a successful subprocess exit alone does not establish successful upgrade.

Coordinate Pi maintenance release only after verification. On failure, retain
an explicit recoverable state for that member and explain the next USB/BOOTSEL
step; do not silently restore normal scheduling against an unknown image.
On success, retain existing saved enablement and admission semantics. Account
for standalone scheduling after reboot; never claim that verification is RF-free
unless the actual setup/maintenance state establishes it. Updating must not
enable a disabled transmitter, clear STOP or promote frequency qualification.

## 9. Integrate WsprryPi access without duplicating authority

Add an operator entry point for the selected Pico using existing runtime/UI
patterns. Show device identity, installed/selected CI version and source/run,
default latest-CI versus explicit version/stable selection, preserving-upgrade
intent, progress, result and recoverable failure. Distinguish downloaded,
programmed and verified states.
Expose local builds as an advanced host workflow, not a browser SDK installation.

The Pi backend invokes the identified shared installer through a bounded
contract and validates structured output. Preserve existing authentication,
authorization, CSRF/target binding and local privileged-operation boundaries.
Browser clients must not supply arbitrary commands, local paths or download
URLs to a privileged process. Conflicting requests from another browser, CLI
or scheduler must respect the same selected-device lock and maintenance state.

A remote network-connected Pico must not be offered a USB update unless it is
also explicitly bound to the Pi's local USB device. The feature does not tunnel
firmware over TCP/BLE/Wi-Fi or require Pico networking. Preserve unrelated
fleet members and selected-device USB-management settings behavior.

Follow Pi's mandatory Impeccable skill before UI changes, preserve its current
design language and inspect rendered desktop/mobile success, pending, refusal,
failure and reconnect states. Test actual source-owned UI and runtime integration,
not a copied installed web root or a placeholder button without a working path.
Deploy the shared installer through the established Pi packaging mechanism with
a pinned compatible installer identity; no runtime dependency on a sibling
development checkout and no silent download of unreviewed code for each click.

## 10. Validate real behavior and failure paths

Use deterministic host tests by default. Inspect current recipes before running
them. Existing Pico entry points include:

```sh
bash scripts/check_host.sh
python3 scripts/validate_wtp_contract.py
```

The maintained alternative is `cmake --preset host-debug`,
`cmake --build --preset host-debug --parallel`, then `ctest --preset host-debug`.
Use accepted P15.16 recipes only when firmware/local-build changes require
cross-builds. Verify the normal and explicit inhibited variants where affected.
Do not install tools or download SDKs as incidental documentation validation.

For Pi, use current documented focused tests and exact-pair USB/management/UI
coverage. Inspect targets before execution. Do not attempt local macOS C++
compilation/linking without explicit authorization that the toolchain is repaired;
use an identified Linux host or Linux CI for required Pi C++ validation.

Exercise production installer orchestration against controlled release/API and
USB/picotool substitutes, with bounded failures and observable write attempts.
Cover at least:

- Default latest successful eligible CI selection including prereleases, explicit
  stable/version selection, no stable release, older-source reruns, incomplete/
  failed/untrusted runs, concurrent newer CI, expired/removed artifacts, anonymous
  download and offline/cache behavior. Cover HTTP/rate-limit/partial-download
  errors, invalid metadata and refusal without silent fallback.
- CI-to-release byte identity, unique pre-1.0.0 tag/source/version mapping,
  interrupted draft/upload/publication, public-download verification, safe
  temporary-release removal and default discovery after removal/replacement.
- Wrong board/variant/family, malformed UF2/manifest/checksum, reserved-region
  overlap, invalid workaround payloads, incompatible storage and downgrade refusal.
- No device, multiple devices, wrong/replaced device during re-enumeration,
  permission failure, wrong CDC role, exclusive-lock conflicts and stale sessions.
- Busy/armed/uncertain device, pending management writes and selected-member
  scheduling exclusion, preserving other fleet members and local standalone rules.
- Backup/readback failures, nonblank BOOTSEL boards, secret redaction/permissions,
  bounded temporary/cache handling, and programming that preserves all banks.
- Failure/cancellation at every destructive boundary, disconnect/power-loss
  recovery state, verification/version/settings mismatch and honest exit status.
- Both front ends using the same core; piped stdin, noninteractive selection,
  paths with spaces/metacharacters, local-build failure and successful local-build
  artifacts passing the same image/preservation checks.
- Plan/help paths without device/settings/service/package mutation, plus Pi UI
  and backend authorization/result handling and desktop/mobile presentation.

Use behavior and actual data/operation assertions rather than source-string
tests that merely mirror implementation. Run shell/static checks appropriate
to added languages and existing repository tooling. Complete required checks;
repeat or broaden only after changes, failures or unresolved concerns justify it.

Physical installation/upgrade acceptance requires a current authorized board
setup. Historical A/B records are not standing authorization. If available,
record exact board/USB identity, starting image/settings, selected artifact,
clock/engine and RF path; keep operations finite and restore the agreed original
image/state after tests. Exercise initial install, preserving upgrade, recovery
and the real Pi entry point within the authorized setup. Avoid RF jobs merely
to prove installation. Do not erase a configured board to create a blank test
fixture without separate destructive-test authority and a verified restoration.

If physical/platform validation is unavailable, finish independent software
work and report precise gaps. Mocks/cross-linking do not qualify USB programming,
state retention, service lifecycle or RF. Leave whole-feature acceptance open
until its required installation/preservation evidence is established.

## 11. Record results and update current instructions

Create a focused P15.18 development record with exact source pairs, installer
version, CI run/attempt/artifact and release/tag identities, public download
verification, release-removal dispositions, supported platform matrix,
commands and pass/fail/skip outcomes, preservation/recovery evidence, independent findings,
repairs and reassessments. Keep raw flash, credentials, generated firmware and
private captures out of source control.

Document exact standalone bootstrap/local CLI commands, default latest-CI and
explicit stable/version/local-build selection, dependency/USB permissions,
settings preservation, backup privacy, BOOTSEL/manual recovery, compatible
versions, limitations and Pi access.
Update affected current Pico/Pi developer/user-facing instructions in the
authorized repositories. Review external operator-documentation impact without
editing a separate docs repository or building P15.20's Read the Docs site.
Pi's required final report must include Documentation Impact.

Update only item 7 in the consolidated work list for the actual acceptance
scope. Do not mark it complete from tests alone if required physical preservation
or either entry point remains unvalidated. Preserve historical evidence and
every other item's current status. Include all substantive acceptance/checklist/docs
changes in the final independently reviewed diff.

## 12. Obtain independent adversarial review and close findings

After implementation and required checks, use a separate reviewer/subagent that
did not implement the change. Give it both complete diffs, accepted prerequisite
records, requirements, actual installer/release/Pi identities, test commands,
results, private-evidence summaries and claimed limitations. The reviewer is
read-only: no device/service operations, Git mutations or publication.

Require adversarial review of device confusion, latest-CI ordering/provenance,
anonymous downloads, CI-to-release byte identity, pre-1.0.0 tags, release-removal
scope/default continuity, release/channel selection,
untrusted metadata/command injection, privilege boundaries, shared-core drift,
bootstrap/deployment reproducibility, image/erase bounds, secret-bearing backups,
all durable banks, boot-workaround handling, ownership/scheduler races,
post-reset enablement, interrupted-operation recovery and false success claims.
Include the actual Pi UI/backend flow, local builds, documentation, supported
pair/platform claims and retained historical RF/qualification boundaries.

For every actionable finding within P15.18, record it, implement the repair and
rerun the affected checks. Return the revised complete result to an independent
reviewer. Repeat repair, retest and fresh adversarial reassessment until no
actionable findings remain and all required checks pass on final source/artifacts.
The implementer's self-review is not an independent review.

Bind the final assessment to the final diffs and artifacts after the last fix.
Any substantive later code/docs change requires affected retesting and renewed
independent reassessment before commit. Report genuine out-of-scope blockers
without broadening the task. Missing required review/validation remains a gap;
do not describe a partial result as complete or waive an actionable finding.

## 13. Commit, push and report the completed slice

After the required checks and independent reassessment are clean, inspect both
repositories' full dirty/staged state and run applicable diff checks. Stage
only attributable P15.18 files/hunks, inspect the exact staged diffs and preserve
unrelated work. Include this saved handoff and its links only if still
uncommitted and clearly attributable; do not absorb earlier P15.17 preparation.

Commit the Pico installer and the necessary Pi integration as separate parent-
repository commits. Preserve their existing accepted branch/upstream boundaries;
at preparation both were `devel` tracking `origin/devel`. Recheck before pushing
and do not guess a different destination. Non-force push only reviewed intended
commits, with compatible installer/Pi identities recorded. Independently query
each remote branch and compare its full hash to the intended commit; a push
success message alone is not parity verification. Do not force-push, rewrite
history, publish unreviewed concurrent work or create a PR. Limit release/tag
operations to the reviewed CI download and removal authority in this prompt.

If Git, permissions or remote state block a push, retain the result and report
the exact remaining step and each repository's actual commit/push state. A
completed software commit must not be described as a successful physical upgrade.

Report delivered standalone/Pi behavior, shared-core/deployment identity,
default latest-CI resolution, public download/release/tag and optional-build
paths, any release removal, supported hosts, settings/secret preservation and
recovery limits, changed files/components, exact checks and physical evidence,
reviewer findings/repairs/retests/final assessment, Documentation Impact, both
commit hashes, push results, independently verified remote hashes and remaining
working-tree/staged state. Do not claim completion while required checks or
actionable findings remain. Stop at P15.18; leave OTA, P15.19 and P15.20 outside this task.
Reprint the canonical Finish now section with current statuses, saved links,
original order and NTP Work grouping, using ✅ finished, ⏳ in flight and
▧ not started.
