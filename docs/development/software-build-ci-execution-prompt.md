# Software build CI and deployment images

Execute only item 6 of the [Consolidated backlog](consolidated-backlog.md).
Implement and run hardware-free software/build CI, produce usable Pico 2 W
UF2 images with verified version/source identity, SHA-256 checksums and a
validated manifest, and retrieve the actual CI artifacts for decode verification,
the installer's default latest-CI download and publication. Record the result
and evidence closeout, perform independent adversarial review, repair
actionable findings and repeat affected checks/review, then commit and push
the scoped result.

This saved prompt does not implement CI, run checks/builds or produce firmware
merely by being prepared or published. Item 6 stays not started until execution
is requested. Workflow artifacts are the delivery mechanism here; creating a
GitHub release, tag, installer or documentation-site publication is not.

## Entry and execution authority

Work in /Users/lbussy/GitHub/WsprryPico. Read AGENTS.md, README.md, CONTRACT.md,
docs/architecture.md, docs/development/README.md and the consolidated backlog
before implementation. Print the complete Finish now section, preserving its
order and NTP Work grouping, using ✅ finished, ⏳ in flight and ▧ not started.
That document is the sole current/future work list; do not create a parallel
roadmap or pending-work tracker. Mark only item 6 ⏳ when execution begins.

Inspect branch, full HEAD, upstream, live remote devel tip, staged/unstaged/
untracked work and concurrent commits. At preparation, the working tree was
clean and devel/remote devel were 4bcf00a98bfc7bbb1a697c154339eb9049adaefe.
The public repository's default branch was main. Its only registered Actions
workflow was active pages-build-deployment at dynamic/pages/pages-build-deployment;
there was no tracked firmware/software workflow. Refresh these observations.
They are not reset targets or evidence that future CI is absent.

This execution authorizes Pico-only workflow/build/packaging/test/documentation
changes, necessary scoped commits/non-force pushes to devel, corresponding CI
runs/retries and workflow artifact uploads/downloads. Clean CI dependency setup
is part of the task. Do not install a toolchain on the user's Mac incidentally.
Other repositories remain read-only; retrieving an exact existing companion
source for supported interoperability tests does not authorize modifying it.

Do not change repository defaults, permissions, branch protection or release
settings; merge to main; publish a release/tag/site; create a PR; operate boards,
RF, SDR, GPSDO or installed services; or execute another backlog item. No
hardware operation is required for this software/build acceptance. Preserve
user work and historical evidence; do not invoke repository/harness cleanup.

Item 7's installer depends on these verified CI images. Do not make item 6
depend on the installer or item 9's publication, which would create a cycle.
Build from the latest accepted current source without silently claiming
unfinished features are accepted. Preserve completed decode evidence at its
actual source/image scope; new CI bytes do not inherit that physical acceptance.

## Establish the actual build and check contract

Read the [development commands](README.md),
[firmware foundation](firmware-foundation.md),
[accepted normal-target selection](phase15-16-results.md),
[artifact evidence](phase15-16-artifacts.json),
[short Type 2/3 decode handoff](short-wspr-type23-decode-execution-prompt.md),
[completed decode result](short-wspr-type23-decode-results.md),
[USB installer handoff](phase15-18-execution-prompt.md) and
[testing prerelease handoff](phase15-17-execution-prompt.md).
The latter handoff is a downstream consumer, not authorization to execute it.

Inspect CMakeLists.txt, CMakePresets.json, firmware/CMakeLists.txt,
firmware/firmware_identity.hpp.in, cmake/verify_pico_dependencies.cmake,
scripts/build_pico.sh, scripts/check_host.sh, the current image checkers and
candidate-manifest helpers, registered tests and third-party notices.

Retain the accepted target mapping:

- WsprryPico is the normal uninhibited complete PIO/DMA application selected
  by ordinary firmware all, the pico2-w preset and the default build helper.
- WsprryPico-Inhibited is the explicitly selected simulator/diagnostic.
- WsprryPico-StandaloneRF is the existing compatibility RF target.

Do not publish inhibited, RFBench, RFWTP, calibration, fault-fixture, provisioned
or old compatibility images under a normal-firmware label. Product identity
may be shared by variants; verify actual target/engine/linkage, not a filename
or product string alone. Preserve one JobService, USB/network/storage behavior,
normal 138 MHz clock, saved enablement, frequency/ownership/output gates and
GPIO drive behavior.

Preparation pins were Pico SDK 2.3.1 at
079c6f39023649b154152db30f1d781e884879bc, Arm GNU compiler 15.3.1 and picotool
2.3.0 at 6f6458d792b93685a11423b244a585eaa99eafcf. Read current accepted pins,
including SDK networking/USB/Bluetooth submodules and generated source overlays.
Do not downgrade a compiler, replace a dependency or relax verification merely
because a runner's default package differs.

Prove a fresh CI runner can obtain the exact toolchain/SDK/submodules and host
dependencies through verified official artifacts or a documented reproducible
build. Pin toolchain archive/container inputs and validate their real digests;
do not invent URLs or checksums. Record the actual runner image, CMake/Ninja,
host compiler, Python/Node versions and package/lock inputs. A version string
alone is insufficient provenance for an unofficial toolchain. If a required pin
cannot be reproduced, report that concrete blocker rather than silently changing
the product build contract.

## Implement the CI workflow

Create or extend a minimal maintained workflow under .github/workflows and
small reusable helpers under scripts/ or cmake/. Use Linux for hardware-free
checks and RP2350 cross-linking; an unrelated platform matrix is not required.
Keep local reproduction commands aligned with the CI recipe.

Cover pushes to devel and appropriate pull-request checks. Add a bounded manual
entry point where supported, with a validated consumer profile and a unique
version generated from the run and attempt. Record the actual checked-out SHA. PR head, synthetic merge
commit and trusted devel source are different identities; a PR test artifact
must not be advertised as the accepted devel deployment candidate.

The initial devel workflow must have a usable trigger. Do not assume a manual
dispatch becomes available solely because a new file exists on devel while
main remains default. Use the allowed devel push path for bootstrap and verify
actual event behavior rather than changing branch defaults or merging main.
See [GitHub workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch).

Give jobs only needed permissions, use reviewed full commit SHAs for actions,
and keep build/setup inputs pinned. Do not expose privileged credentials to
untrusted PR code or use a privileged trigger to execute it. Validate workflow
inputs before invoking tools and pass them as data rather than shell source.
See [GitHub secure use guidance](https://docs.github.com/en/actions/reference/security/secure-use).

Use explicit timeouts and concurrency behavior, with no indefinite retries.
Cache only suitable dependency inputs with keys covering their exact pins,
runner/toolchain/profile and relevant build inputs. A cache hit cannot replace
source/pin verification or a fresh image check. Keep profile/build directories
separate so stale CMake state cannot substitute another engine or frequency.

Inventory actual registered tests and required dependencies. Node/browser
tests may disappear from registration when Node is absent; schema checks may
skip when Python packages are missing. CI must verify its expected suite is
present and required checks ran, rather than treating a smaller all-pass list
as full coverage. Supply pinned required host/JS/Python/crypto dependencies and
retained-SDK descriptor/network inputs where appropriate.

Run the current host suite, contract/schema checks, browser logic and relevant
SDK-backed host tests. Existing entry points include:

    bash scripts/check_host.sh
    python3 scripts/validate_wtp_contract.py

The platform-appropriate maintained alternative uses host-debug configure,
build and CTest presets. Read actual commands and registration before running;
do not freeze historical test counts or invent targets. Check out sufficient
history/refs for existing history-dependent tests rather than hiding them in
a shallow clone. Use separate host and firmware build trees. On Linux include
required loopback/TLS fixtures and exact
approved companion checks when part of the documented supported suite; keep
all fixture hardware access disabled. Do not compile Pi C++ on the user's Mac.

Report selected tests, pass/fail/skip and reasons. Missing required tooling or
fixtures must not become silent success. Retain meaningful packaging/identity
failure tests without adding tests that merely mirror helper implementation.
Never suppress a product failure, reduce capacities or bypass guards to make
CI green. A newly exposed product defect outside CI scope is a reported blocker.

Gate deployable artifacts on all required software/build/image checks. Failed,
cancelled or incomplete runs may retain clearly named diagnostic logs, but
must not export an apparently verified deployment bundle. A Pages success is
not software-test or firmware-build CI acceptance.

## Freeze source, version and profiles

Freeze a clean committed source F containing the workflow and reviewed build/
packaging implementation before qualifying deployment bytes. Necessary scoped
source commits/pushes are allowed to exercise CI; final evidence can be recorded
in a later documentation-only commit E. F, the actual artifact source and E
must remain distinct. Never construct a self-referential source/manifest hash.

Validate embedded firmware version/source/board/variant against the generated
header and actual linked ELF/picotool identity. Require an intentional version
and real clean source identity, never dirty/unknown fallback labels. Keep full
source SHA in the manifest even when firmware embeds a short revision. Check
untracked credential headers, dependency overrides and generated build inputs;
Git's tracked dirty flag alone is not a complete input audit.

Use the unique embedded development version `0.1.0-ci.<run-id>.<attempt>`,
selected before building. Do not accept version overrides or reuse an identity
for different deployment bytes. Later installer/prerelease publication uses
those exact embedded versions and may prefix them with `v` for a unique
pre-1.0.0 tag. CI itself creates no tag or release. Changing identity after
qualification requires a new image and reassessment.

Produce one generic, uninhibited consumer deployment image: `WsprryPico`,
Pico 2 W, normal 138 MHz PIO/DMA application. Do not make deployment builds
for individual bands. The firmware contains no selected transmit frequency,
station identity, credentials or enabled schedule. Operators configure these
at runtime; preserve explicitly saved settings on upgrades. Standalone WSPR
with no explicitly saved frequency must remain nontransmitting, including old
records that previously depended on a compile-time base. A first saved
frequency does not implicitly enable an inherited schedule.

Build `WsprryPico-Inhibited` as a software/build regression only. Exclude its
UF2 from the deployment bundle. Build/check the compatibility RF target when
needed to validate shared wiring; it is not a consumer download asset.

Downstream decode and publication must use the exact normal CI-produced bytes.
Changing embedded version, source or other build inputs after qualification
requires a new image and reassessment. Item 2's recorded 80 m image and evidence
retain their exact historical scope and are not relabelled as CI acceptance.

## Validate actual linked images and UF2 payloads

Cross-build the selected profiles using the accepted firmware recipe and exact
pins. All existing heap, stack/guard, flash, BOOTSEL/GP14, pool, renderer and
linked-engine checks remain mandatory where applicable. Preserve the pinned
RP2350 workaround treatment and current journal reservations.

Verify physical engine/worker/renderer presence for normal images and absence
for inhibited images using actual linked ELF evidence. Verify normal clock,
runtime frequency-selection contract, target/variant, version, product, board/processor/family and
compile definitions. Wrong-role, mixed or incomplete images must fail packaging
even if their names or sidecar metadata look correct.

Verify UF2 structure, supported family, block numbering/addresses, payload
association with the hashed ELF and application extent from the actual linked
flash layout. Any RP2350 workaround exception must match the exact supported
contents/metadata, not allow arbitrary reserved-memory payloads. Do not rely
on an older fixture helper's historical default flash limit for the current
saved-progress image. Ordinary updates must not overwrite profile/configuration/
progress/bond/watermark banks or require a whole-flash erase.

Use generic images: no saved station identity, Wi-Fi credentials, certificates/
private keys, local provisioning headers, fault flags or test-enabled schedules.
Preserve production defaults; do not claim RF enablement from an uninhibited
engine. Check source path normalization and actual asset contents for accidental
local/private data. Retain hashed ELF/map, compile commands and build logs in
a separately identified downloadable audit artifact; the downloaded payload
must remain verifiable against its exact linked ELF after the runner exits.

Where practical compare two fresh builds with identical declared inputs/version
to detect nondeterminism. Investigate differences and state reproducibility
limits honestly; an input manifest alone does not prove identical builds.
Do not confuse a fresh local build with the actual CI-produced deployment bytes.

## Manifest, checksums and downloadable artifacts

Define one independently versioned canonical manifest/schema for these firmware
bundles and downstream prerelease/installer consumption. Reconcile the planned
release-manifest.json contract with the existing prerelease handoff rather than
creating competing formats. The old phase12-candidates schema is fixture-specific;
do not relabel its historical evidence as a deployment manifest.

Include at least product/version/channel intent; repository and full source F;
source cleanliness/input digest; build profile, target, board/processor/family,
uninhibited/inhibited role, engine, clock and runtime frequency-selection contract; exact SDK/
toolchain/picotool/submodule/overlay inputs; runner/build type/options; workflow
path/revision, event, run ID/attempt/URL; actual checks/results/skips; payload
basenames/sizes/SHA-256s; update/storage/rollback constraints; and evidence/
license references. Distinguish supported software contracts from unmeasured
physical boot, USB, RF, timing, power and interoperability claims.

Use explicit safe profile/versioned basenames and an upload allowlist. Reject
missing/extra/duplicate files, wrong sizes/hashes/identities, unsupported schema
versions, unsafe paths/symlinks and mismatched profile/engine/frequency. Test
tampered payload, swapped inhibited/normal metadata, wrong source/version and
incomplete-check cases. Validate what is actually hashed and packaged, not
untrusted sidecar claims. Use bounded structured parsing and tool arguments.

The manifest lists payload assets without hashing itself. SHA256SUMS covers
the final UF2s, manifest and deliberately distributed notices, not itself.
Calculate hashes only after content is final. Keep the workflow archive digest
distinct from the contained UF2/manifest hashes. Checksums provide integrity,
not a cryptographic signature or independent qualification.

Inspect LICENSE.md, THIRD_PARTY_NOTICES.md and exact linked component licenses;
include required notices/materials in an explicit checked bundle. CI artifacts
are distributed binaries too. Do not silently strip attribution or assume
the project's MIT license covers all linked dependencies.

Use workflow artifacts with explicit names, retention and failure-on-missing
outputs. Document expiry and how to retain selected validated bytes locally
until later publication. Record artifact IDs as well as names; never resolve
only a mutable latest-successful label. Keep post-upload artifact IDs/archive
digests in the closeout evidence rather than rewriting an archived manifest
to insert metadata that could not exist before upload. See
[GitHub artifact guidance](https://docs.github.com/en/actions/tutorials/store-and-share-data).
Do not let a successful upload substitute for successful validation.

Define a maintained identity/discovery contract for item 7's default latest-CI
selection: trusted canonical devel workflow, required successful checks, source
ordering, run/attempt/profile and immutable artifact hashes. An older-source
rerun or release re-upload must not become a newer source candidate. Keep normal
deployment unambiguous and support resolving one complete immutable bundle per
installation. A mutable channel pointer is a locator, never sufficient identity.
Use the same canonical manifest across CI, the installer and item 9.

Workflow artifacts remain this task's delivery mechanism. Item 7 may publish
the verified bytes as public installer download prereleases and create unique
pre-1.0.0 tags if public downloads require it; item 9 is not a prerequisite for
that limited publication. Do not execute those release/tag operations in this
CI-only task or require an end-user GitHub token as the installer's default.

After CI passes, download the exact selected run/attempt artifacts to a new
ignored local directory. Independently verify run source/workflow/profile,
manifest schema, checksums, file sizes, actual UF2/ELF association and required
checks. Make content/hash mismatches hard failures; do not rely on a platform
warning alone. Prove the download contains the usable normal default image and
each selected profile, and that inhibited assets cannot be mistaken for them.

Document concrete retrieval and verification commands using real run/artifact
identities once available. Preserve verified downloads and hashes for item 7,
later item 9 and any separately selected decode verification. Those consumers
must use the same selected UF2 bytes; if assets expire or a candidate changes,
report the need for affected reassessment rather than silently rebuilding or
changing version. Do not reopen or relabel item 2's completed evidence here.

## Run evidence and adversarial review

Exercise CI on actual pushed committed F. Record remote job IDs, conclusions,
commands, selected tests and every build profile; a local all-pass result or
unrelated workflow badge does not establish this run. Wait for required jobs
to complete. Preserve first failures and repair logs; do not count a rerun at
another source SHA as evidence for F.

Write software-build-ci-results.md with a sanitized evidence manifest linking
the exact source/run/attempt/artifact identities, check coverage/skips, image
and dependency verification, download validation, version/profile decisions,
retention/retrieval and downstream image handoff. Keep generated binaries,
bulk logs, private fixture material and dependency caches untracked. Update
maintained development/build instructions without duplicating the backlog.

Use a separate read-only adversarial reviewer for workflows, helpers/tests,
manifest, actual downloaded binaries, remote results and completion wording.
Challenge missing/conditionally omitted tests; untrusted trigger/input/cache
paths; wrong or drifting pins; dirty/untracked inputs; default-branch bootstrap;
wrong engine/frequency; stale flash limits; unsafe packaging; identity/hash
cycles; partial-run artifacts; unverified downloads; and version/profile changes
that would invalidate downstream decode, installer selection or exact-byte
publication.

Repair all actionable in-scope findings, rerun affected checks and get a fresh
independent assessment of the repaired final result. Iterate until no actionable
finding remains. Any source/build/packaging-input repair invalidates affected
artifact claims: commit a new source F, run fresh CI and re-download/reverify
its outputs. An evidence-only E must not relabel earlier firmware as built from
E or demand a self-referential firmware rebuild.

If an external account/runner/pin prerequisite blocks the workflow, finish
unaffected preparation, report the exact blocker and retain ⏳. Do not change
repository settings or another product to evade the boundary. Successful build
CI here does not close item 2's RF decode or item 9's publication.

## Commit, push and closeout

Set only item 6 ✅ after the required final-source CI passes, all selected image
profiles/bundles are verified after download, evidence is durable and independent
review is clear. Preserve its saved-prompt link, every other status and the NTP
grouping. A missing/failed required check or unavailable deployment bundle keeps
item 6 ⏳ with the concrete unresolved acceptance result.

Inspect final and staged diffs and run scoped git diff --check plus
git diff --cached --check. Stage only attributable workflow/build/packaging/
test/documentation/evidence and item 6 changes, partially staging shared files
when needed. Commit and non-force push to origin/devel; source and final evidence
commits are authorized without another routine confirmation. Preserve concurrent
work/commits; do not reset, stash, clean, force push or absorb unrelated changes.

If the final evidence-only push triggers more required CI, wait for its actual
status or report it pending; never claim E passed based on F's run. A build
trigger/path policy must account for every real product/build/schema input
without causing an endless evidence-commit/rebuild/manifest rewrite cycle.
Keep the selected qualified artifact's source F and bytes explicit.

Independently query remote devel and compare local HEAD/upstream after push.
Report actual source F and evidence E, what changed, tests/skips and remote
CI/run/artifact results, review repairs, downloaded paths/hashes, limitations,
commit/push/parity and working-tree state. Reprint the complete canonical
punchlist using ✅/⏳/▧. Stop after item 6; no decode, flashing or release is
performed by this task.
