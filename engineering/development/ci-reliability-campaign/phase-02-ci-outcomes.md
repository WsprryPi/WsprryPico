# Phase 02 Make CI outcomes enforceable and observable

Execute only phase 02 when explicitly invoked. Read the complete
[shared execution contract](README.md#shared-execution-contract),
[orientation](orientation.md), and phase 01's accepted baseline. Phase 01 must
have reconciled required contexts and identified unresolved measurements first.

## Objective and scope

Make required validation status reflect actual work and prepare enforceable
merge checks without changing validation frequency or publication authority.
Inspect .github/workflows/software-build.yml, scripts/ci/run.py, bundle.py,
download.py, publish.py, tests/ci_bundle_tests.py, and current GitHub branch/rule
settings. Inspect companion status consumers when affected, without assuming
permission to edit WsprryPi. Do not split jobs for speed; phase 09 owns scheduling.

## Work

1. Re-read remote devel protection and applicable rules. Treat a permissions
   failure or ambiguous 404 as unknown, not proof that a branch is unprotected.
   Identify actual status-check names, producers/application identities, events,
   optional jobs, and the installation/publication consumers that trust them.
2. Inventory result handling from process exit to suite report, artifact
   verification, job status, and whole-run eligibility. Address swallowed exits,
   missing tools, empty discovery, required conditional skips, stale/duplicate
   reports, continue-on-error, incomplete aggregation, and optional subcase skips.
   Retain explicit optional classification; do not broadly search arbitrary logs
   for the word SKIP and call that a complete result protocol.
3. Add bounded phase timing and explicit suite/context completion evidence where
   absent. Bind it to the actual candidate, run/attempt when applicable, carrier,
   command, and outcomes. Validate shape before access, enforce exact permitted
   fields, and update serializers, readers, strict validators, and failure tests
   together. Do not change an independently versioned bundle/storage format
   incompatibly or invalidate retained published artifacts as an incidental edit.
4. Keep failed, cancelled, timed-out, missing, or unexpectedly skipped required
   work unsuccessful through every aggregate. A report stamped passed by a
   wrapper cannot substitute for actual completed work. Preserve diagnostic
   failure uploads, exact artifacts, manual publication, PR/trusted-source
   distinctions, and successful-whole-run download eligibility.
   If an aggregator runs after failed dependencies, it must fail closed for
   unknown selection or missing statuses; it must never manufacture success to
   avoid a permanently pending required check.
5. Prepare a concrete minimal branch-rule change: required check identities,
   target branch, present versus proposed settings, bypass/optional behavior,
   effects on existing PRs and skip-ci document commits, and recovery procedure.
   Preserve unrelated protections. Do not enable publication or change settings
   before separate explicit approval of that prepared change.

## Validation and adversarial assessment

Use focused runner/bundle tests and temporary synthetic reports to prove missing,
duplicate, wrong-source, zero-execution, malformed, failed, cancelled, timeout,
and required-skip outcomes refuse. A correctly completed optional publisher skip
must remain distinguishable from skipped verification. Recheck frozen published
bundle verification where format readers change. Test early phase failure and
diagnostic upload failure without allowing either to hide the other.

Run both actual production source-pair suites if their selection, aggregate,
required-status mapping, or protocol-facing consumers change. Hosted run evidence
and remote settings verification require their own authorization; local tests do
not prove remote merge enforcement. Review adversarially, fix actionable findings,
rerun affected checks, and reassess under the shared contract.

## Acceptance and handoff

Deliver the result-path map, exact proposed settings change, negative tests,
phase timing evidence, updated report consumers, and source-pair results when
required. Only after approved application and remote readback may enforcement be
called active. If approval or hosted evidence is unavailable, mark that gate
pending while separately reporting completed code/test work; do not declare the
whole phase complete. Phase 03 may proceed on its independent work with this gate
explicitly outstanding. Report costs against phase 01 and stop.
