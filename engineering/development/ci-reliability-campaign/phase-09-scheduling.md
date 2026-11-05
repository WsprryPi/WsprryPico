# Phase 09 Optimize isolated execution scheduling

Execute only phase 09 when explicitly invoked. Read the complete
[shared execution contract](README.md#shared-execution-contract),
[orientation](orientation.md), phase 01's baseline, and accepted reliability,
coverage, source-pair, and build-graph evidence through phase 08. No scheduling
change may bypass an unresolved safety or execution-completeness gate.

## Objective and scope

Reduce trustworthy-result elapsed time with bounded parallel execution, not less
validation. Inspect current CTest serial/resource properties, scripts/ci/run.py,
setup and bundle readers, workflow dependencies/artifacts, browser fixture ports,
and required-status identities. Preserve the independent reproducibility builds
and the current required source-pair contexts.

## Work

1. Map exclusive and bounded resources: ports, credentials, directories, journals,
   generated files, mutable caches, browser profiles, memory, cores, subprocess
   groups, and artifact names. Derive isolation/locks from ownership evidence;
   do not remove RUN_SERIAL or reuse profiles merely because a trial passed.
2. Pilot a bounded CTest concurrency setting with supported runner resources.
   Keep true exclusions serialized or resource-locked and preserve timeout/error
   propagation. Do not let parallel process count exhaust memory, amplify host
   scheduling races, or turn missing work into retries.
3. Evaluate separate jobs only where the measured graph justifies them. Count
   duplicated setup, downloads, verification, compilation, transfer, aggregation,
   and added helper/regression work. Keep independently fresh build contexts and
   exact source/dependency identities; no object-cache shortcut for reproducibility.
4. Bind artifacts/results to the same candidate, workflow, run/attempt, profile,
   and declared producer. Aggregate exact required contexts only after actual
   success. Missing, duplicate, stale, wrong-source, cancelled, timeout, or failed
   outputs must refuse assembly/publication. Preserve immutable exact-byte bundle
   validation and download consumers; update all affected readers/tests together.
   Verify producer identity against trusted workflow/job provenance rather than
   trusting a producer name inside an uploaded report or artifact filename.
5. Preserve triggers, frequency, logical cases, carriers, source/shipped paths,
   and merge gating. Reconcile renamed/split checks with phase 02's prepared
   required-status configuration; any remote settings transition needs separate
   explicit approval and verified readback. Do not strand a required old check or
   create an interval in which failures are accepted.
6. Predeclare bounded comparable observations and report variability, first-
   attempt outcomes, and rerun burden. Compare immediate prechange versus
   candidate scheduling with identical current coverage/inputs. Separately report
   cumulative campaign change against phase 01; coverage added in phase 07 makes
   unlike whole-run durations observational, not a causal scheduling experiment.

## Validation and adversarial assessment

Exercise lock conflicts, exhausted resource budgets, one slow/stalled worker,
early job failure, cancellation, missing/mismatched artifact, partial upload,
and failed aggregation. Confirm all owned work is reaped and original failures
survive. Verify no false-green status or deployable partial bundle. Run all
affected contexts, bundle/downloader regressions, and both actual production
network and USB suites on the intended source pair.

Collect comparable cold/warm evidence only in authorized environments. Hosted
workflow execution requires explicit authority; local concurrency tests cannot
prove hosted timing, status wiring, or artifact transfer behavior. Never dispatch
CI during document preparation. Review adversarially, fix, rerun affected checks,
and reassess before accepting a new default.

## Acceptance and handoff

Deliver resource/isolation design, completed-context reconciliation, negative
results, source-pair evidence, and absolute before/after elapsed, queue delay,
aggregate spans, invocation counts, and maintenance costs. Assess each 50% target
independently, including remaining gaps. Accept a smaller safe improvement or a
supported no-change decision; never weaken coverage to reach 50%. If required
hosted/settings evidence is unavailable, keep that acceptance gate pending and
report the validated local portion separately. Update truthful status and stop.
