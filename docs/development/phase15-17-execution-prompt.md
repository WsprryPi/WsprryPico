# P15.17 GitHub testing prerelease execution prompt

Prepared 2026-10-17. **Saved execution instructions.** Current status and
priority are recorded only in the [Consolidated backlog](consolidated-backlog.md).
Saving or reviewing this prompt does not build, tag, commit, push or publish.
The instructions below apply when the operator invokes it for execution.

## Objective and execution authority

Publish one verified **GitHub testing prerelease** in `WsprryPi/WsprryPico`,
containing the normal uninhibited Pico 2 W firmware, a versioned release
manifest and SHA-256 checksums. Use accepted P15.14 USB control, P15.15 GPIO
drive strength and P15.16 default-build behavior. Finish by verifying the
published tag and downloaded assets, recording the result, and updating the
canonical work list. Execution of this prompt does not execute later items.

When invoked, this prompt authorizes the bounded release preparation, necessary
Pico-only tooling/documentation changes, attributable commits and non-force
pushes to `origin/devel`, a new annotated tag at the exact reviewed firmware
commit, and draft/upload/publish operations for this testing prerelease. It also
authorizes a separate read-only reviewer/subagent for independent adversarial
review and final reassessment. Complete the checks before publication; routine
release actions within this scope need no additional confirmation.

Other family repositories remain read-only. Do not publish a stable release,
change repository settings, create announcements/discussions, implement an
installer or OTA, or start another feature. Do not force-push, move an existing
tag, overwrite published assets, or delete existing releases. Hardware actions
follow current setup statements and `AGENTS.md`; no bench operation is required
merely to publish this software testing prerelease.

## 1. Verify prerequisites and refresh the execution baseline

Work from `/Users/lbussy/GitHub/WsprryPico`. Read `AGENTS.md`, `README.md`,
`CONTRACT.md`, `docs/architecture.md`, `docs/development/README.md`, the current
[Consolidated backlog](consolidated-backlog.md), the
[acceptance record](../implementation-plan.md#phase-15-acceptance-record),
[USB acceptance](usb-control-results.md), and the actual P15.15/P15.16
acceptance records linked there. Their saved prompts alone are
not acceptance records.

Confirm the earlier Finish Now items are accepted, including CI deployment
images and the short WSPR Type 2/3 decode. Verify their exact source and image
applicability; if release preparation changes firmware, reconcile that evidence
before publication. Confirm P15.14, P15.15 and P15.16 are complete, including the
exact Pico/Pi source pair, drive-strength persistence/compatibility and normal versus
inhibited target mapping. If any prerequisite is incomplete, report it and
stop before release preparation or publication. Do not implement the missing
phase inside P15.17.

Inspect branch, full HEAD, upstream, staged/unstaged/untracked work, remotes,
remote `devel`, remote tags, releases/drafts, authentication and repository
rules. Record the latest stable release ID/tag, or its confirmed absence, for
the post-publication comparison. Fetch current `origin/devel` and start from
its current accepted tip; record the full SHA. Preserve unrelated work and
concurrent commits. Use an
isolated clean checkout if needed; never reset, stash or clean the user's work.
Do not assume the default branch is `devel` or let it select the release commit.

Preparation snapshot only: Pico `devel` was
`2aef1edeca30e86deb412f4bbb59ec53462bee78`; GitHub release inventory was empty;
P15.15/P15.16 were not started. There was no dedicated checked-in firmware
release workflow. Refresh all of this at execution. Do not treat this snapshot
as the future release baseline or invent a firmware-test CI pass.

## 2. Select a unique testing version and freeze the source

Inspect current version/tag conventions first. Follow an established testing
series if one exists. Otherwise use `v0.1.0-testing.1` for the first testing
tag and `0.1.0-testing.1` as the embedded firmware version. Increment the testing
number for a new candidate when that identity is already occupied; never reuse
an identity for different bytes. An existing draft from this same execution may
be resumed only after its tag, source, assets and ownership are reconciled.

Record the repository, tag, embedded version, accepted prerequisite commits,
exact source commit and asset names before building. The currently available
CMake identity input is `WSPRRY_PICO_FIRMWARE_VERSION`; recheck it against
P15.16. Use the supported release-version override, not a renamed development
UF2. Inspect the generated header and linked image metadata: version, product,
board and source revision must agree, with no `dirty`, `unknown` or development
fallback identity. Record the full source SHA even if firmware embeds 12 digits.

If packaging helpers, a manifest validator or release documentation are needed,
keep them narrowly within this phase. Test meaningful packaging failure paths,
review and commit those changes before freezing the firmware source commit
`F`. Non-force push it and independently verify its remote identity. Build only
from clean committed `F`, containing accepted P15.14–P15.16. A dirty-tree build
is never a release candidate. Check untracked inputs and dependency overrides;
Git's tracked-file dirty flag alone is insufficient.

Later evidence-only commit `E` may record the publication outcome. The release
tag, embedded revision and manifest source must continue to identify `F`,
not `E`. Do not put `F`'s own hash inside tracked source at `F` or create a
self-referential manifest/hash cycle.

## 3. Produce and retrieve fresh CI images

Use new task-specific ignored build/output directories and the accepted P15.16
build recipe through the accepted software/build CI workflow at exact clean
commit `F`. Build the normal `WsprryPico` target as the release candidate and
the explicit inhibited variant as a regression check. Do not publish an
RFBench, RFWTP, fault-fixture, calibration, provisioned or inhibited image as
the normal firmware. Retain accepted USB/network/storage behavior, the normal
138 MHz clock and GPIO drive choices of 2/4/8/12 mA with a 4 mA default.
Download the successful CI run's normal UF2, source/version manifest and
checksums. Verify run, commit, target and hashes; publish those exact CI-produced
bytes. Local builds may provide additional checks but do not replace the
selected CI deployment image. Missing or failed firmware CI blocks publication.

Recheck pinned SDK, picotool, compiler and linked SDK submodules; record exact
versions/revisions, CMake/Ninja versions, build type, target, flags and commands.
At preparation the pins were SDK 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`, Arm GCC 15.3.1, and picotool
2.3.0 at `6f6458d792b93685a11423b244a585eaa99eafcf`. Use actual accepted
pins at execution; do not upgrade dependencies or relax checks to package.

Use a generic consumer build without device credentials, certificates/private
keys, station identity, saved settings, bench fixtures or local provisioning
headers. Inspect actual generated inputs and build flags. Keep local SDK paths,
credentials, raw logs and generated firmware out of tracked source. Sanitized
build recipes must still be reproducible using documented dependency variables.

Preserve ELF/map and build logs locally for audit. Verify RP2350 board/family,
normal engine, linked worker and all maintained flash/UF2, renderer, stack,
heap and pool checks. Inspect UF2 payload extents against the current flash
layout, including the pinned RP2350 workaround treatment. The ordinary update
must not carry saved-progress/access/bond/profile/configuration/watermark bank
payloads or require a whole-flash erase. Determine storage compatibility from
the final source and P15.15 evidence; do not copy stale addresses or promise
untested migration/downgrade preservation.

## 4. Validate the exact candidate

Run current documented host regressions, WTP contract checks and affected
packaging/identity/manifest tests from `F`. Existing entry points include:

```sh
bash scripts/check_host.sh
python3 scripts/validate_wtp_contract.py
```

Use the platform-appropriate host path; the maintained alternative is
`cmake --preset host-debug`, `cmake --build --preset host-debug --parallel`,
then `ctest --preset host-debug`. Inspect current recipes before running them.
Build firmware with the accepted P15.16 recipe and explicit version override;
do not blindly reuse an older inhibited helper or existing build cache.

Retain P15.15/P15.16 compatibility, USB/time/AP, configuration, drive-strength
and resource assertions. If release changes affect a companion contract,
validate the exact supported Pi pair read-only; a broken prerequisite blocks
publication rather than authorizing unrelated Pi implementation. Do not attempt
Pi C++ compilation on macOS without explicit repaired-toolchain authorization.

Record pass/fail/skip, command, source, artifact and relevant numeric resource
results. Repeat checks after repairs where affected. Reconcile CI by exact
commit/workflow: Pages success is not firmware-test CI. Missing CI is reported
truthfully and blocks publication until the selected firmware CI passes.

No new all-band, alternate-clock, dual-board or WSPR Type 2/3 RF campaign is
part of this publication task. Preserve historical evidence and its source
applicability. New host checks, release metadata and compilation do not renew
RF qualification. If a connected-device smoke is separately warranted and
currently authorized, bound it first, preserve settings and restore the setup;
record that evidence separately without making it an implicit release gate.

## 5. Assemble the release assets and manifest

Use versioned, predictable names and an explicit upload allowlist. Required
assets are:

- `WsprryPico-<version>-pico2_w.uf2`: the exact validated normal image.
- `release-manifest.json`: the machine-readable, independently versioned
  release manifest.
- `SHA256SUMS`: SHA-256 entries for the UF2 and manifest, plus any deliberately
  attached notices. It must not contain itself.

Define and validate manifest schema version 1 in this slice; do not claim an
installer already consumes it. Include product, firmware version/tag, testing
channel/prerelease status, repository/full source SHA, board/processor/family,
normal uninhibited variant, engine/clock, nominal drive choices/default,
protocol/API/storage versions and supported exact Pi pair. Include pinned build
inputs and reproducible commands/options, UF2 basename/size/SHA-256, reserved
storage/update/downgrade policy, validation results and qualification limits,
and source/evidence/license references pinned to relevant commits.

Keep asset names as safe basenames with no absolute paths, traversal, shell
syntax or ambiguous duplicates. Validate required fields, types, lengths,
version/tag/source agreement, hashes and actual file sizes. The manifest lists
payload assets, not its own digest or the checksum file's digest; SHA256SUMS
covers the manifest. Calculate checksums after content is final. Keep expected
local hashes as an independent comparison baseline for remote downloads.

Review `LICENSE.md`, `THIRD_PARTY_NOTICES.md` and exact linked dependencies for
binary redistribution obligations. Include required notices/license material
as explicit assets or an appropriate bundle, recording it in the checksum
inventory; a release note link is sufficient only where the license permits.
Do not ship device-specific credentials or unpublished captures in any asset.
Checksums establish byte integrity; do not call them a signature or attestation.

## 6. Prepare complete testing release notes

Write the exact release body to a maintained Markdown file, such as
`docs/development/phase15-17-release-notes.md`, and use `--notes-file`.
Include:

- Testing status, exact tag/source, board, asset names and verification steps.
- Delivered USB management/time, GPIO drive setting and uninhibited default;
  RF capability still follows saved configuration and local admission rules.
- Exact compatible Pi revision(s), protocol/storage compatibility, normal
  preserving-update procedure and honest downgrade/recovery restrictions.
- Supported mode/band/clock dispositions and links to original evidence.
  P15.13 covers its exact 40.001/60.001 MHz, GP2, 138 MHz Pico A points, with
  receiver-audio translation/compact-job conditions. Preserve current 6 m/4 m/
  2 m dispositions; do not infer whole-band, LPF, calibrated-power, alternate-
  clock or antenna-ready qualification from those points.
- Actual checks and known limitations. Installer and final user docs remain
  future items. Testing is selected explicitly; stable remains the eventual
  ordinary installer default. If no stable release exists, say so without
  silently substituting this prerelease.

Use exact release/tag asset URLs for testing, not `/releases/latest/download`.
Document checksums before flashing. Publishing alone does not validate an
installer, device upgrade or new RF behavior.

## 7. Obtain independent review and close findings

Give a separate read-only reviewer the complete P15.17 diff, prerequisites,
clean commit `F`, build commands/log summaries, ELF/UF2 evidence, asset hashes,
manifest, notes and proposed release operations. Require an adversarial review
of source/artifact identity, wrong-target substitution, credentials, license
obligations, reserved flash, false compatibility/RF/CI claims, version collision,
latest/stable behavior and interrupted-publication recovery.

Record actionable findings, repair them, rerun affected checks and obtain a
fresh independent reassessment until none remain. A substantive source repair
requires a new clean `F` and fresh affected builds; packaging/notes repairs
require regenerated checksums and renewed review. Bind approval to exact final
source, asset hashes and notes. Do not publish while required checks or review
findings remain unresolved. Do not describe self-review as independent.

## 8. Push the exact tag and verify a complete draft

After the review passes, create a new annotated tag explicitly at `F` and push
only that tag. Independently query the remote tag object and its peeled commit;
an annotated tag's object SHA differs from its commit SHA. Confirm the peeled
commit equals `F`, `F` is in accepted remote `devel` ancestry, and no concurrent
change has been silently included. Do not tag a moving branch name or let
GitHub create a tag from its default branch.

Use the authenticated GitHub CLI or equivalent explicit API. Recheck installed
help and repository rules, including immutable-release behavior. Create a
**draft prerelease** with an explicit file allowlist, notes file, remote-tag
verification and latest disabled, following the
[official create command](https://cli.github.com/manual/gh_release_create).
With resolved shell variables, the shape is:

```sh
gh release create "$release_tag" \
  "$release_dir/$firmware_name" \
  "$release_dir/release-manifest.json" "$release_dir/SHA256SUMS" \
  --repo WsprryPi/WsprryPico --verify-tag --draft --prerelease \
  --latest=false --title "WsprryPico $firmware_version — testing" \
  --notes-file "$release_notes"
```

Add any required notice assets explicitly. Assign all variables from validated
values, quote paths, and never upload a wildcard directory. Query the draft by
tag/release ID, enumerate assets, confirm complete uploaded states/names/sizes,
download to a separate directory and verify hashes against both SHA256SUMS and
the independent local baseline. Inspect downloaded UF2 identity and manifest
again. Check [API asset digests](https://docs.github.com/en/rest/releases/assets)
where available; never rely on metadata alone.

For an interrupted or uncertain call, inspect actual remote state before
retrying. Resume only the matching draft and missing assets from this execution;
never use `--clobber` or create a duplicate release blindly. Preserve an
unexpected existing draft/release and report the conflict. A different candidate
needs a new identity and review, not a moved tag or replaced published binary.

## 9. Publish and independently audit the public result

After the complete draft and final review agree, publish with prerelease true
and latest false, retaining the verified tag and assets. Recheck the
[official edit command](https://cli.github.com/manual/gh_release_edit):

```sh
gh release edit "$release_tag" --repo WsprryPi/WsprryPico \
  --verify-tag --draft=false --prerelease --latest=false
```

Read the published release afresh. Require `draft=false`, `prerelease=true`,
the intended tag, publication timestamp, exact notes and complete asset set.
Independently verify remote tag resolution to `F` again. Download every asset
from its published URL into a fresh directory, preferably anonymously for this
public repository, and compare bytes/hashes with the frozen local baseline.
Validate the downloaded manifest, UF2 metadata and checksum inventory again.
Record release/asset IDs, names, sizes, URLs and digests.

Confirm the stable/latest selection is unchanged. If there is no published
stable release, a missing latest-full-release result is expected; investigate
authentication/network errors rather than treating every failure as that case.
Check the release list and full-release API semantics, not just the title or
position on the releases page, using the
[official latest-full-release API](https://docs.github.com/en/rest/releases/releases#get-the-latest-release).
No implicit stable fallback is permitted.

If publication or the public audit fails, record the exact partial state and
leave P15.17 incomplete. Do not conceal failure by deleting releases, moving
tags or changing published bytes. Resolve within the authorized scope or report
the concrete blocker. A successful CLI exit alone does not close this item.

## 10. Record acceptance, commit evidence and hand off

Create `docs/development/phase15-17-results.md` with baseline and frozen `F`,
version/tag, build/artifact identities, checks, reviewer findings/repairs/final
reassessment, publication and remote/download verification, storage/compatibility
policy, limitations and any hardware/restoration state. Keep raw firmware and
local capture/log data ignored. Record the release manifest and final checksums
in durable source evidence without a source-hash cycle.

Only after every publication audit passes, mark P15.17 **Complete**, link its
results and public release, and synchronize the development/prompt indexes.
Keep P15.18–P15.20 **Not started** and provide the installer with explicit
testing tag/asset selection, manifest version, checksum policy and stable-default
behavior. Do not implement the installer.

Have the independent reviewer reassess the final evidence/checklist changes
and public audit. Repair findings and repeat affected checks. If a repair changes
release inputs, create a newly reviewed candidate identity; do not rewrite the
published one. Commit only attributable evidence as `E`, non-force push and
independently verify remote branch parity. Distinguish `E` from tagged `F`.

Report the release URL, version/tag, full `F`, evidence commit `E`, UF2 SHA-256,
asset URLs, actual validation/review results and remaining limits, remote tag
and branch verification, and real working-tree/index state. Stop at P15.17.
