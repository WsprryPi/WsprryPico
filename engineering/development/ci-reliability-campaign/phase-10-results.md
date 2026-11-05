# Phase 10 retention and documentation acceptance

Acceptance binds Pico `1ca46ed1ac16d9c4f9c0c5a3fbac7e0d0a70314c` and Pi
`d3ffc3b26d50f55f205382bb5aac7cdfee054d99` on their campaign feature branches.
Neither branch has been merged. Original checkouts, unrelated worktrees, devices,
services, and recovery/dependency environments were preserved.

The bounded pre-mutation inventory is `/private/tmp/wsprrypico-phase10-action-inventory.json`.
Its final decisions are 18 DELETE, 11 REWRITE, 23 RETAIN, and 28 HOLD entries.
Eighteen exact tracked files were retired after physical-path/regular-file/hash
checks: fourteen completed prompts/intermediate reviews and four obsolete
unregistered pair/producer fixtures. Their logical extent is 80,171 bytes;
filesystem free-space change was not measured. The four unused fixtures receive
zero reduction-goal credit. No external/ignored/container/host deletion occurred.
The exact deletion hashes are `/private/tmp/wsprrypico-phase10-deleted.json`.

Current operating instructions now reside in `software-build-ci.md`, with links
from development and network-control guides. They describe framework completion,
ownership, clocks, resource exclusions, contexts, source-pair commands, image/build
invalidation, strict provenance, merge protection, and honest performance units.
The native scenario matrix was consolidated there before its old handoff was
retired. Operator docs and Read the Docs publishing remain unchanged. Completed
saved prompts remain reachable by immutable Git links, without archive copies.

The old producer emits a bare Config v1 at `/api/v1/config`, without current
control authority. Current tests retain zero/unlimited timeout save/update/reboot
behavior and strict refusal. A private production scheduler mutant losing zero
only on an unrelated update fails the existing independent zero assertion.
A private actual admission-header mutant accepting bare version 1 fails the
new control-authority assertion. Positive checks passed before/after, original
production inputs remained unchanged, and no obsolete positive control view was
activated. The first omit-zero mutant was independently repaired by another
production layer, so it was not credited as a demonstrated zero-loss defect.

Focused CTest verification selected and reconciled exactly eight current tests
with `--no-tests=error`; all passed. An earlier incorrectly named selection found
zero tests, was discarded, and is not success evidence. The final removed-target
and changed-link/anchor audit passed across 122 retained Markdown files. Current
maintained source/build/docs have no callers of the four retired fixture paths.
`git diff --check` passed. Fault, positive, and link-audit proofs are under ignored
`build/campaign-phase10-*`; full source-pair commands are in
`build/campaign-phase10-qualified-pair.sh` and the maintained CI guide.

Active builds, source worktrees, SDKs, node dependencies, verifier venv, immutable
audit/firmware/recovery evidence, and the active/old-owned containers remain held
or retained for final acceptance. Unrelated/original work areas remain outside
this cleanup. wspr5 had only a read-only dependency lookup and no task-created
harness; wspr4 was unused. No external cleanup or physical qualification is claimed.
The final phase consumes the baseline and accepted metrics, consolidates the
requested scorecard, repairs references, and retires the remaining completed
campaign handoffs. No actionable retirement/references finding remains within
this inspected scope after correction and reassessment.

Both full production network and USB recipes passed with explicit Mbed TLS
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` and framework
`dff9da04438d712f7647fd995bc90fadd0c0e2ce`. The container has no remaining test
processes. Canonical hosted run [42130186637](https://github.com/WsprryPi/WsprryPico/actions/runs/42130186637)
passed on attempt 1; verify succeeded and optional publish was skipped. Strict
Pico devel protection was read back successfully. No release/deployment occurred.
