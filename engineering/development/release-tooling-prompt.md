# Firmware release tooling execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`. Read `AGENTS.md`,
`README.md`, `CONTRACT.md`, `engineering/architecture.md` and the development
guide; inspect and preserve existing changes. Implement and validate this scope,
then commit and push the reviewed work. Do not create or push firmware tags,
create drafts, upload assets, publish releases, advance download bookmarks,
flash devices or emit RF. Disable implicit publication before pushing changes.

## Outcome

Support semantic firmware tags such as `v1.0.0-beta.1` and `v1.0.0` through
build identity, manifest creation/verification, publisher, downloader and USB
installer. Treat version validity, source provenance, selection and publication
authorization as separate requirements. Preserve historical CI/testing downloads.

## Required behavior

1. Use one standard-library semantic-version policy shared by CI and the
   independently distributed installer. Accept SemVer prereleases and final
   versions, including valid build metadata; reject malformed versions,
   leading-zero numeric identifiers, path/control characters and overlong input.
   Keep run-derived CI and historical testing identities explicitly classified.
   Do not infer storage or protocol compatibility from the firmware major number.
2. Build `v<version>` tag refs with the exact peeled source and embedded version.
   Tag builds must use maintained main/devel history and pass the same complete
   checks, image inspection and reproducibility requirements as branch builds.
   Preserve PR preview isolation and main/devel CI artifact/index identities.
3. Extend the canonical manifest without breaking its bounded installer schema
   interpreter or historical manifests. Bind tag/version, channel, source,
   workflow event/ref, run/attempt, asset names and deployment eligibility.
   Preserve all board, flash, storage, output, license and qualification checks.
4. Make publication an explicit manual opt-in, default off, in both firmware
   and installer workflows and their executable entry points. Push, PR and tag
   verification alone must have no release write effects. Beta releases are
   prereleases; final releases are full releases. Prevent mistaken latest-stable
   changes and preserve append-only tag/asset behavior, complete draft auditing,
   exact receipts, retry safety and immutable original archives.
5. Download verified tag artifacts before publication and preserved releases
   afterward, including after Actions expiry. Validate actual job outcomes,
   tag/source and manifest/receipt/archive association. Deliberately skipped
   publication must be compatible with successful read-only validation; failed
   or cancelled jobs must fail closed. Keep legacy CI selection independent.
6. Install an explicitly selected beta/final version through the existing
   preserving-update transaction; support explicit stable selection. Validate
   release classification and exact tag provenance before any USB action.
   Preserve main CI as the ordinary default, explicit devel selection, offline
   bundles, same-board recovery and no silent fallback. Keep the distributed
   installer payload contract usable without edits to another repository.
7. Document current commands, selection/publication policies, compatibility and
   limits. Retain this reusable prompt and a concise result/review record.

## Validation and closure

Add behavioral tests across the complete synthetic release chain for beta,
final, legacy CI/testing, tagged push and manual tag dispatch. Include malicious
or mismatched versions, source/tag/ref/run swaps, metadata/classification
changes, failed/skipped jobs, mutated assets, interrupted drafts, stable
selection, publication authorization and bootstrap/offline compatibility.
Exercise the unchanged bounded schema interpreter. Run affected Python suites,
WTP checks, documentation checks and full Linux CI; do not retry the known-broken
macOS C++ toolchain. No actual release publication is a test prerequisite.

After implementation, perform an adversarial assessment of all changed paths,
especially trust boundaries and automatic side effects. Record findings, repair
each actionable issue, rerun affected checks and repeat the assessment until no
actionable findings remain. Commit and push only this scope on `devel`; verify
remote parity and final CI results. Report changes, checks, review iterations,
limitations, commit and repository state, and confirm no release was published.
