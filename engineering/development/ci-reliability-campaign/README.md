# CI reliability and efficiency campaign

This active plan defines eleven bounded phases for trustworthy, effective, and
efficient WsprryPico CI. Reliability, safety, required coverage, and defect
detection are acceptance gates. Speed and maintenance reductions are optimization
targets within those gates. Improvements may add code or runtime. A 50% reduction
is a feasibility question for each metric, never a completion quota.

The eleven prompts are authorized for sequential execution in this session.
The user's Wsprry Development Session standing authority supersedes the earlier
preparation-only, per-phase invocation, separate routine approval, and no-CI
restrictions in these documents. It covers development, dependencies, Git/CI,
related Docker infrastructure, WsprryPi/WsprryPi-Docs/WsprryPico, wspr4/wspr5, and
Pico C within the assigned campaign. Preserve unrelated data/services and shared
Git history. Identify hardware and verify the actual conducted RF termination
before any transmission; this software campaign requires no RF by default.
Prompt preparation and implementation acceptance remain separate statuses.

## Phase list

All eleven prompts have completed an authoring adversarial review, correction,
and reassessment. Execution is tracked below. The phase numbers match the agreed
campaign and remain stable. Legend: ✅ complete, ⏳ in progress, ▧ not started.

| Phase | Purpose | Saved prompt | Prompt review | Execution |
| --- | --- | --- | --- | --- |
| 01 | Establish the baseline and accounting | [Prompt](phase-01-baseline.md) | Reviewed, findings closed | ✅ Complete |
| 02 | Make CI outcomes enforceable and observable | [Prompt](phase-02-ci-outcomes.md) | Reviewed, findings closed | ✅ Complete |
| 03 | Repair process ownership and failure propagation | [Prompt](phase-03-process-ownership.md) | Reviewed, findings closed | ✅ Complete |
| 04 | Qualify the session browser pilot | [Prompt](phase-04-browser-pilot.md) | Reviewed, findings closed | ✅ Complete |
| 05 | Adopt the qualified browser lifecycle | [Prompt](phase-05-browser-adoption.md) | Reviewed, findings closed | ✅ Complete |
| 06 | Remove scheduler dependent synchronization | [Prompt](phase-06-synchronization.md) | Reviewed, findings closed | ✅ Complete |
| 07 | Close coverage and source pair gaps | [Prompt](phase-07-coverage-and-pair.md) | Reviewed, findings closed | ⏳ In progress |
| 08 | Consolidate demonstrably redundant build work | [Prompt](phase-08-build-consolidation.md) | Reviewed, findings closed | ▧ Not started |
| 09 | Optimize isolated execution scheduling | [Prompt](phase-09-scheduling.md) | Reviewed, findings closed | ▧ Not started |
| 10 | Resolve holds and repair documentation | [Prompt](phase-10-retention.md) | Reviewed, findings closed | ▧ Not started |
| 11 | Perform adversarial acceptance and handoff | [Prompt](phase-11-final-acceptance.md) | Reviewed, findings closed | ▧ Not started |

## Sequence and completion

Execute phases in order under the standing authority, reporting and printing the
updated list after each phase before continuing. Each phase
consumes the accepted implementation evidence and interfaces of its predecessors.
Phase 02's separately pending remote-settings approval may remain outstanding
while independent later implementation proceeds; this does not mark phase 02
complete or waive any local/paired validation gate. Apply the same distinction to
phase 09's separately pending hosted/settings evidence. Do not proceed with work
whose actual correctness prerequisite is unresolved. Phase 11 must report such
pending gates and cannot declare the complete campaign accepted until required
evidence and authority are satisfied.

| Finding or responsibility | Owning phases |
| --- | --- |
| Reproducible inventory, denominators, source identity, and reliability observations | 01; reconciled in every later phase |
| Required merge checks, truthful suite results, and false-green paths | 02, 09, 11 |
| Partial I/O, late child failure, detached descendants, and cleanup ownership | 03; adopted in 04 through 06 |
| Representative session browser and selective-profile interface | 04 |
| Remaining browser lifecycle duplication and excess fixture starts | 05 |
| Arbitrary synchronization, accelerated host time, and cancellation observation | 06 |
| Missing tool-download coverage, optional subcases, and current companion pin | 07 |
| Duplicate client compilation, equivalent firmware work, and verified input reuse | 08 |
| Resource-safe parallelism and trustworthy elapsed-time measurement | 09 |
| Historical fixture holds, prompt retention, references, and current documentation | 10, 11 |
| Final adversarial sensitivity, both production carriers, and honest scorecard | 11 |

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
- Keep implementation within the campaign and its necessary companion slices.
  Companion development is authorized by the session standing authority. Record
  intended paired refs; unavailable credentials or dependencies remain blockers,
  not a deferred requirement behind completion.
- Execute each bounded phase and its required validation under the session
  standing authority, including necessary companion work, dependencies, CI, and
  project settings. Do not repeat routine approval requests already answered.
  Respect higher-priority technical permission boundaries and the user's explicit
  restrictions on protected history, unrelated data, and unverified RF paths.
- Execution uses codex/pico-ci-reliability-campaign and its isolated worktree.
  Validated implementation commits/pushes and necessary CI are now authorized.
  Document-only status/evidence commits may use [skip ci]. Do not rewrite shared
  history or weaken existing branch protections.

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
  skip prerequisite acceptance gates when continuing to the next phase. Update this active plan during authorized execution.
  Retire completed temporary prompts only after consolidating needed instructions
  and repairing references under phase 10 and repository retention rules.

## Execution evidence

[Phase 01 baseline](baseline.md) and [exact inventory](baseline.json) freeze the
original executable inputs and qualified historical measurements. Unknown semantic
denominators remain explicit; later phase costs reconcile against this baseline.

## Preparation review records

[Prompt adversarial reviews](prompt-reviews.md) record authoring findings,
corrections, and reassessment. They are not implementation or runtime evidence.
