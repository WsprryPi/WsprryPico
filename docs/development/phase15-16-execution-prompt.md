# P15.16 uninhibited default firmware execution prompt

Renumbered 2026-10-17 from P15.15. This is the previously saved default-build
handoff; the new P15.15 is GPIO drive-strength configuration. Original execution
scope, independent-review requirement and commit/push authorization are retained.
The additional prerequisite is acceptance of the new P15.15 before execution.

Preparation status: **saved for future execution; P15.16 has not been executed**.
Preparing this handoff changes documentation only. The implementation,
independent review, repair, retest, commit and push instructions below apply
when the operator invokes this prompt for execution.

## Objective and execution authorization

Implement **P15.16 — Make the default firmware build uninhibited** in
`/Users/lbussy/GitHub/WsprryPico` on `devel`, after P15.14 USB control and
P15.15 GPIO drive strength are complete and accepted. Deliver the bounded
implementation and documentation, validate them, obtain an independent
adversarial review, repair and retest findings,
and obtain a clean reassessment. Then commit only attributable Pico changes,
non-force push the exact reviewed commit to `origin/devel`, independently
verify remote parity, and report the result.

This execution prompt explicitly authorizes a separate reviewer/subagent for
the independent adversarial review. It does not authorize edits in other
WsprryPi-family repositories, GitHub release/tag publication, or starting
P15.17, P15.18 or P15.19. Hardware authority follows current setup statements
and `AGENTS.md`; historical bench records are not standing authorization.

## 1. Verify USB/drive-strength acceptance and the working state

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/development/README.md` and the current Phase 15 checklist in
`docs/implementation-plan.md` before implementation.

Do not start implementation until P15.14 USB control and P15.15 GPIO drive
strength are complete and accepted. Read the P15.15 acceptance record linked
from the current checklist, including its exact Pico/Pi source pair, persisted
field/schema, 4 mA default, 2/4/8/12 mA choices and saved-versus-active restart
semantics. Preserve the accepted setting on every normal/inhibited target and
all existing management/UI paths. The P15.15 feature must not be reimplemented
or renumbered by this task.
Read the final P15.14 acceptance record and protocol, including
`docs/development/usb-control-results.md`,
`docs/development/usb-local-configuration.md` and
`docs/protocol/USB-Management.md`. Verify the final Pico source identity,
supported Pi companion revision, acceptance scope and remaining limitations.
A plan, implementation commit or successful build alone does not establish
P15.14 completion.

At preparation on 2026-10-17, Pico HEAD was
`100e749c815f7485d5097c9086852d3b97adca9f`
(`Enable full USB management and bounded AP lifetime`), and the checkout was
clean. The roadmap still described P15.14 as in progress. The earlier
`9dee1ff177e65738d0e15e8b7ee35bd5ea8f400f` commit established the checklist
order only. Refresh the actual state when executing this prompt; neither
preparation snapshot substitutes for accepted USB-control evidence.

Inspect branch, HEAD, upstream and all tracked, untracked and staged work.
Preserve existing changes. Do not reset, stash, delete build evidence or absorb
unrelated changes. Record the accepted baseline before editing.

If P15.14 or P15.15 is not accepted, report that prerequisite and stop without
implementation edits.

## 2. Deliver the selected default and inhibited variant

The canonical `WsprryPico` firmware target must produce the RF-capable normal
application. The `pico2-w` preset, ordinary firmware build, maintained build
helpers and documented production/release build recipe must select that same
application. Changing only the preset to select `WsprryPico-StandaloneRF` while
leaving `WsprryPico` inhibited does not satisfy this requirement.

Keep an explicitly selected RF-inhibited application variant for tests and
diagnostics. Give its target and artifact an unambiguous identity. Preserve
existing `WsprryPico-StandaloneRF` build compatibility where practical;
document any necessary command or artifact-name transition.

Keep the host-only development default intact. The uninhibited default applies
when building Pico firmware; ordinary host tests must not acquire a firmware
SDK dependency.

RF capability must preserve existing configuration, timing, ownership,
frequency-policy, fault and output-admission controls. It does not enable
transmission independently of those controls.

## 3. Keep implementation within P15.16

Reuse the existing normal PIO/DMA application and accepted P15.14/P15.15 functionality.
Retain the normal 138 MHz clock and current renderer, worker, stack and memory
configuration.

Do not change waveform generation, mode/band support, timing limits, resource
reserves, pin assignments, saved defaults or configuration authority merely
to make the new target build. Record the accepted P15.14 numeric limits and
reserves before editing; no smaller advertised capacity or relaxed timing
admission is an acceptable substitute for correct target wiring.

Preserve accepted USB Console, USB WTP, USB management and USB-time behavior,
alongside standalone scheduling, Wi-Fi and existing network management. Keep
one JobService and scheduling authority.

Preserve all persistent formats and flash addresses, including saved progress,
GPIO drive strength, profiles, access/Bluetooth state, standalone configuration, transmission
watermarks and the E10 reservation. Do not add installer maintenance state
or upgrade migrations in this slice.

Do not implement OTA, repartition flash, split Wi-Fi firmware, compress web
assets, implement an installer or publish a GitHub release. P15.17 handles the
testing prerelease; P15.18 handles the installer. Other WsprryPi-family
repositories remain read-only unless separately authorized.

## 4. Review the build graph before editing

Inspect at least:

- `CMakeLists.txt`, `CMakePresets.json` and `firmware/CMakeLists.txt`.
- `firmware/firmware_identity.hpp.in` and `scripts/build_pico.sh`.
- `cmake/verify_pico_dependencies.cmake` and
  `cmake/standalone_link/memory_flash.incl`.
- `src/standalone/pico/main.cpp` and
  `src/standalone/pico/flash_layout.hpp`.
- `tests/firmware_profile_tests.cpp`, `tests/standalone_image_tests.py`,
  `tests/endpoint_capacity_tests.cpp` and the accepted P15.14 USB tests.
- Applicable post-build hooks and linked-image checks:
  `scripts/check_endpoint_image.py`, `scripts/check_standalone_image.py`,
  `scripts/check_rf_renderer.py`, `scripts/check_gp14_rf_image.py`,
  `scripts/check_stack_guards.py`, `scripts/check_heap_hooks.py` and
  `scripts/check_btstack_pool_hooks.py`.

Search maintained callers of `WsprryPico` and `WsprryPico-StandaloneRF`,
particularly candidate builders, inhibited fixtures and diagnostic runners.
Before editing, briefly record the intended target/artifact mapping and which
existing checks or fixtures depend on the old mapping. Then implement the
bounded change.

## 5. Implement coherent target and artifact selection

Make `WsprryPico` construct the complete existing RF application: correct
engine, worker, libraries, compile definitions, renderer placement, stack
reservations and post-build checks. Simply removing `RF_OUTPUT_DISABLED` is
insufficient.

Keep shared application wiring centralized enough that normal and inhibited
variants cannot silently diverge in accepted USB/network/storage features.
Avoid unrelated CMake restructuring.

Make both the ordinary firmware `all` build and `pico2-w` build preset select
the intended normal application. Keep inhibited and deliberate fault images
explicitly selected.

Audit fixtures that build `WsprryPico` while expecting inhibition. Update
maintained callers to request the inhibited variant or fail clearly. The
default change must not silently turn an inhibited test into an RF runner.

Audit filename-dependent image checks. For example,
`check_endpoint_image.py` currently derives a stack expectation partly from
the ELF basename. Preserve actual stack, heap, worker and flash assertions
when names or roles change; do not weaken checks to accommodate a rename.

Keep product, variant, engine and build identity truthful. Do not assign a
release version or reuse a historical qualified image identity.

Use fresh task-specific build directories and preserve existing outputs.
Ensure stale simulator artifacts cannot be mistaken for the new normal image.

## 6. Validate behavior and linked artifacts

Use the current development guide and accepted P15.14 reproduction commands.
Existing entry points at preparation include:

```sh
cmake --preset host-debug
cmake --build --preset host-debug --parallel
ctest --preset host-debug
python3 scripts/validate_wtp_contract.py
cmake --preset pico2-w
cmake --build --preset pico2-w
```

Use the repository's platform helper when required by the local environment.
Run fresh configurations in task-specific directories; check a controlled
reconfiguration transition without destroying an existing user build.
Document and execute the explicit inhibited-build command introduced by this
slice rather than assuming an existing command.

Retain verified dependency pins. At preparation they were:

- Pico SDK 2.3.1, commit `079c6f39023649b154152db30f1d781e884879bc`.
- Arm GCC 15.3.1.
- picotool 2.3.0, commit `6f6458d792b93685a11423b244a585eaa99eafcf`.

Recheck against the accepted P15.14 baseline. Do not silently relax pins or
upgrade dependencies.

Acceptance must establish:

- Fresh ordinary firmware configuration, default build, preset and maintained
  helper produce the RF-capable normal application.
- The explicit inhibited variant still uses the inhibited lifecycle and cannot
  select the physical RF execution path.
- Both variants retain accepted P15.14 management, transport and time features,
  capacities and timing/resource reserves, plus P15.15 drive-strength storage,
  4 mA default, all four choices and restart/status behavior. Use the accepted
  P15.15 source pair and configuration as the immediate feature baseline.
- Actual linked images satisfy applicable flash/UF2, stack, heap, worker,
  renderer and instrumentation checks.
- Current host regressions and affected compatibility checks against the exact
  accepted Pi companion pass. Read-only Pi compatibility testing does not
  authorize Pi source changes.
- Normal-image resource usage is compared with the accepted pre-change RF
  application, rather than only with the smaller inhibited image.
- Unsupported target/fixture combinations fail clearly instead of producing
  an unintended image.

Prefer checks of generated targets and linked artifacts over tests that merely
search CMake text. Add focused regressions only where they protect the
normal/inhibited distinction or a concrete failure path.

Do not flash or operate devices based on historical bench records. Follow
current setup authorization and `AGENTS.md` if hardware validation is available.
Otherwise complete hardware-free work and identify untested device/RF behavior
explicitly. Linking and host tests do not establish RF qualification.

## 7. Update current documentation and acceptance evidence

Update current instructions and contracts for the normal default and explicit
inhibited variant. Review `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/development/README.md`, `docs/development/firmware-foundation.md`,
`docs/development/standalone.md`,
`docs/development/phase15-13-support-policy.md` and
`docs/implementation-plan.md`.

Correct current statements that the standard image is inhibited. Preserve
historical validation records, original image identities and qualification
limits; do not rewrite history through global terminology replacements.

Record implementation, exact validation commands, artifact identities,
resource comparisons, review findings and repairs, reassessments and remaining
limitations in a focused P15.16 development record. Keep generated firmware,
credentials and raw device captures out of source control.

Prepare the P15.16 acceptance record and checklist changes before the final
independent reassessment. They must reflect the actual result and remaining
limits, and be included in the reviewed diff.

## 8. Obtain independent adversarial review and close findings

After implementation and required validation, use a separate reviewer/subagent
that did not implement the changes. Supply the accepted P15.14/P15.15 baseline, full
P15.16 diff, requirements, actual final build/variant mapping, validation
results and image/resource evidence. The reviewer is read-only and must not
operate devices, modify Git state or publish anything.

Require an adversarial assessment of the complete delivered result, including:

- Accidental RF selection in inhibited fixtures or diagnostic workflows.
- Missing RF worker, compile definitions, libraries, stack reservations or
  post-build checks in the canonical normal target.
- Disagreement among ordinary builds, presets, helpers and documented recipes.
- Stale or incorrectly labelled artifacts and filename-dependent checks that
  fail to validate the actual variant.
- Lost P15.14 functionality, reduced capacities or relaxed timing/resource
  admission.
- Changes to persistent state, default enablement or configuration authority.
- Misleading documentation, unsupported compatibility claims or inherited RF
  qualification claimed for a new source/image without sufficient evidence.

For every actionable finding within P15.16, record the finding, implement the
repair and rerun the affected checks. Then return the revised result to an
independent reviewer for a fresh assessment. Repeat fix, retest and reassess
until no actionable findings remain and all required checks pass on the final
source. Do not substitute the implementer's self-review for independence.

Broaden or repeat validation only when a repair, failure or unresolved concern
justifies it. Bind the final review to the final source/artifacts after the last
repair. Report genuine out-of-scope blockers without expanding the task or
silently treating them as closed. If independent review or a required check
cannot be completed, report the gap and do not claim complete acceptance.

## 9. Commit and push the completed Pico slice

After required checks and the independent reassessment are clean, verify that
the P15.16 acceptance record and checklist reflect the reviewed result and limits.
Leave P15.17 prerelease publication, P15.18 installer implementation and P15.19
user documentation separate.

Inspect the final diff and run `git diff --check`. Review the exact files and
content selected for commit. Commit only attributable P15.16 changes, including
this saved handoff and its checklist link if they are still uncommitted and
belong to the final slice. Preserve unrelated tracked, staged and untracked
work; do not use blanket staging or absorb concurrent work.

If any substantive source or documentation changes follow the final review,
rerun affected checks and obtain an independent reassessment before committing.

Commit on `devel` with a description of the final implementation. Non-force
push the exact reviewed commit to `origin/devel`. Never force-push or publish
unreviewed concurrent commits. Independently query the remote branch and
compare its full hash with the intended pushed commit; a successful push
message alone is not independent parity verification.

If a genuine Git, permission or remote-state blocker prevents publication,
retain the work and report the exact blocker, commit state and remaining step.
Do not claim a push succeeded when it did not. Do not create a tag, GitHub
prerelease, release asset or PR as an incidental step.

## 10. Report the completed work

Report the accepted starting Pico/Pi identities, final target/preset/artifact
mapping, changed files and reasons, exact checks and results, normal/inhibited
image hashes, resource comparisons and remaining physical/environmental limits.
Summarize independent reviewer findings, repairs, affected retests and final
reassessment. Include the commit hash, push result, independently verified
remote hash and actual repository/staged state.

Do not mark P15.16 complete while required validation or actionable review
findings remain unresolved. Stop at the P15.16 boundary after reporting.
