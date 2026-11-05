# CI reliability and efficiency campaign

This active plan defines eleven bounded phases for trustworthy, effective, and
efficient WsprryPico CI. Reliability, safety, required coverage, and defect
detection are acceptance gates. Speed and maintenance reductions are optimization
targets within those gates. Improvements may add code or runtime. A 50% reduction
is a feasibility question for each metric, never a completion quota.

The saved prompts are execution instructions for later explicit phase invocation.
Preparing, reviewing, committing, or pushing them does not execute a phase.
Current authorization covers campaign documents only: no product/harness changes,
test runs, dependency installation, hosted CI, hardware, merge, or publication.
Prompt preparation and phase execution have separate status.

## Phase list

Prompts are added below after their individual adversarial reviews close.

| Phase | Purpose | Saved prompt | Prompt review | Execution |
| --- | --- | --- | --- | --- |
| 01 | Establish the baseline and accounting | [Prompt](phase-01-baseline.md) | Reviewed, findings closed | ▧ Not started |
| 02 | Make CI outcomes enforceable and observable | [Prompt](phase-02-ci-outcomes.md) | Reviewed, findings closed | ▧ Not started |
| 03 | Repair process ownership and failure propagation | [Prompt](phase-03-process-ownership.md) | Reviewed, findings closed | ▧ Not started |
| 04 | Qualify the session browser pilot | [Prompt](phase-04-browser-pilot.md) | Reviewed, findings closed | ▧ Not started |
| 05 | Adopt the qualified browser lifecycle | [Prompt](phase-05-browser-adoption.md) | Reviewed, findings closed | ▧ Not started |
| 06 | Remove scheduler dependent synchronization | [Prompt](phase-06-synchronization.md) | Reviewed, findings closed | ▧ Not started |
| 07 | Close coverage and source pair gaps | [Prompt](phase-07-coverage-and-pair.md) | Reviewed, findings closed | ▧ Not started |
| 08 | Consolidate demonstrably redundant build work | [Prompt](phase-08-build-consolidation.md) | Reviewed, findings closed | ▧ Not started |
| 09 | Optimize isolated execution scheduling | [Prompt](phase-09-scheduling.md) | Reviewed, findings closed | ▧ Not started |

## Shared execution contract

Every phase prompt incorporates this contract. Read it, the
[orientation review](orientation.md), and the applicable phase prompt before
executing only that phase. Read root and nested AGENTS.md, README.md, CONTRACT.md,
engineering/architecture.md, engineering/development/README.md, and actual owning
workflow/build definitions. Current instructions and verified sources govern;
historical counts, suspected defects, refs, and prior green results are leads.

### Source identity and scope

- Inspect current branches, staged/unstaged/untracked changes, source identities,
  and ownership before editing. Preserve user work and other worktrees/processes.
  Start from the phase's intended current candidate, recording its relationship
  to current devel; do not silently reset to this campaign's preparation SHA.
- Keep work in WsprryPico. Read affected Pi clients and fixtures as needed.
  Reading them does not authorize companion edits, branches, commits, or pushes.
  Secure explicit companion authority if necessary; unavailable authority or
  dependencies are blockers, not a deferred requirement behind completion.
- An explicit phase invocation authorizes its bounded implementation and local,
  hardware-free validation. It does not authorize unrelated phases, remote
  settings changes, hosted CI dispatch, dependency installation/downloads,
  hardware, service changes, merge, release, or firmware deployment. Use retained
  dependencies; request missing authority after preparing the concrete result.
- This preparation branch is codex/pico-ci-reliability-campaign. Future execution
  must identify its own intended branch/worktree. Do not stage, commit, or push
  implementation unless that execution task authorizes it. Every commit/push in
  the present document-authoring task uses [skip ci]; do not trigger CI indirectly
  through a PR, tag, dispatch, or branch-setting change.

### Efficacy and timing

- Preserve required triggers, frequency, merge gates, carriers, logical cases,
  strict current control validation, real crypto, framing/ACK, journals,
  identity/revision checks, no-write refusals, inhibition, independent expected
  values, artifact provenance, and recovery assets. Retain independently
  versioned WTP, transport, and storage boundaries. Do not add historical control
  views, downgrade fallback, permissive stubs, or fabricated success results.
- Verify suspected defects with source inspection and an appropriate bounded
  reproduction before repair. Do not force a change when the concern is already
  resolved. A no-change decision requires evidence and obligation reconciliation.
- Classify waits as product timing, logical test time, observed synchronization,
  finite failure watchdog, pacing/retry, diagnostics, or unsupported assumptions.
  Preserve product timing. Observe readiness and fault entry before advancing
  injected clocks. Propagate monotonic enclosing budgets to inner operations;
  reject late success, and retain an independent real watchdog for controlled
  clocks. Sleeps, wider timeouts, retry-until-green, and absent markers are not
  readiness or cleanup evidence.
- Register ownership before fallible work. Bound partial I/O, EOF, child exit,
  cancellation, shutdown, and owned descendant handling. Attempt every finalizer,
  preserve primary and secondary errors, check expected termination, and remove
  private profiles only after writers are confirmed stopped. Never kill unrelated
  processes or expose credentials in diagnostics.

### Validation and adversarial closure

- Derive exact supported commands from current development docs and checked-in
  recipes; do not invent a command or call an opt-in hardware script for discovery.
  Run affected deterministic tests and deliberate-defect sensitivity checks.
  Inspect actual results, registration, execution, and final status propagation.
  Required skipped, failed, cancelled, timed-out, or missing checks stay unresolved.
- For phases changing shared fixtures or behavior, run both production network
  and USB source-pair suites, even when only one carrier appears affected. Phases
  03 through 09 and final phase 11 explicitly require both. Phase 02 also requires
  both if it changes their selection, result handling, or required status mapping.
  Apply the repository gate to any other protocol-facing change regardless of
  this list. Read-only phase 01 and documentation-only phase 10 do not require
  manufacturing test runs when executable inputs remain unchanged.
- Use WsprryPi .github/workflows/debian-non-hardware.yml recipes. Network includes
  wtp-network-runtime-test, wtp-network-interop-test, and wtp-config-interop-test.
  USB includes the actual Pico usb_management_driver, wtp-usb-pair-client-build,
  wtp-usb-management-test, and WsprryPi-UI/tests/wtp_usb_pair_test.js. Exercise
  production clients/coordinators, Pico handlers, real crypto, serialization,
  framing/ACK, and journals. Select exact candidate sources and pinned dependencies
  explicitly, including recursive MbedTLS inputs. Old CI and mocks are insufficient.
- Review each implementation adversarially for lost cases, false-green exits,
  missing tools, empty discovery, optional skips, cleanup races, stale sources,
  self-confirming oracles, hidden costs, and incorrect counts. Fix findings,
  rerun affected checks, then reassess until no actionable findings remain.
  Record unresolved risks without claiming completion.

### Accounting and handoff

- Freeze reproducible baselines. Separate physical code/bytes/files from active
  files, scenarios, assertions, generated/vendor content, and documentation.
  Mark ambiguous embedded orchestration rather than inventing a denominator.
  Count logical coverage separately from process, suite, compiler/linker, job,
  and matrix executions. Unused-test cleanup receives zero reduction credit.
- Charge helpers, relocated code, regressions, companion work, dependencies,
  repeated setup, and transfers. Preserve an independently fresh reproducibility
  build. Compare equivalent source/toolchain/coverage inputs and cold/warm
  observations; distinguish queue delay, elapsed, aggregate job spans, retries,
  cancellations, and failures. Do not label job spans billed cost or sum
  overlapping savings. A passing rerun does not erase the first failure.
- Report changed paths, both candidate identities and uncommitted input hashes,
  commands/results and CI links when applicable, adversarial findings and their
  closure, coverage/context reconciliation, net budgets, limitations, and actual
  Git state. Distinguish local evidence, hosted CI, installed hardware, physical
  USB/network, service, timing, GPIO, and RF qualification.
- Mark a phase complete only after its acceptance gates pass; distinguish a
  separately blocked settings action from completed coding subtasks. Do not
  auto-execute the next phase. Update this active plan during authorized execution.
  Retire completed temporary prompts only after consolidating needed instructions
  and repairing references under phase 10 and repository retention rules.

## Preparation review records

[Prompt adversarial reviews](prompt-reviews.md) record authoring findings,
corrections, and reassessment. They are not implementation or runtime evidence.
