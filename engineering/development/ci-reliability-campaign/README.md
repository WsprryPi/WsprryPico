# CI reliability and efficiency campaign

This eleven-phase campaign treats reliability, safety, complete coverage, and
independent defect detection as acceptance gates. Speed and maintenance reductions
are optimization targets within those gates. A 50% reduction is a feasibility
question for each metric, never a completion quota.

## Phase list

Legend: ✅ complete, ⏳ in progress, ▧ not started. All eleven saved prompts passed
an authoring adversarial review, correction, and reassessment. The first ten
execution slices are accepted. Completed prompts remain accessible at their saved
immutable Git revisions; current operating instructions are consolidated in the
[CI guide](../software-build-ci.md).

| Phase | Purpose | Saved prompt | Execution |
| --- | --- | --- | --- |
| 01 | Establish the baseline and accounting | [Prompt](https://github.com/WsprryPi/WsprryPico/blob/1a383a993833f05ab0ea574286dc5eec8ba4d09b/engineering/development/ci-reliability-campaign/phase-01-baseline.md) | ✅ Complete |
| 02 | Make CI outcomes enforceable and observable | [Prompt](https://github.com/WsprryPi/WsprryPico/blob/1a383a993833f05ab0ea574286dc5eec8ba4d09b/engineering/development/ci-reliability-campaign/phase-02-ci-outcomes.md) | ✅ Complete |
| 03 | Repair process ownership and failure propagation | [Prompt](https://github.com/WsprryPi/WsprryPico/blob/1a383a993833f05ab0ea574286dc5eec8ba4d09b/engineering/development/ci-reliability-campaign/phase-03-process-ownership.md) | ✅ Complete |
| 04 | Qualify the session browser pilot | [Prompt](https://github.com/WsprryPi/WsprryPico/blob/1a383a993833f05ab0ea574286dc5eec8ba4d09b/engineering/development/ci-reliability-campaign/phase-04-browser-pilot.md) | ✅ Complete |
| 05 | Adopt the qualified browser lifecycle | [Prompt](https://github.com/WsprryPi/WsprryPico/blob/1a383a993833f05ab0ea574286dc5eec8ba4d09b/engineering/development/ci-reliability-campaign/phase-05-browser-adoption.md) | ✅ Complete |
| 06 | Remove scheduler dependent synchronization | [Prompt](https://github.com/WsprryPi/WsprryPico/blob/1a383a993833f05ab0ea574286dc5eec8ba4d09b/engineering/development/ci-reliability-campaign/phase-06-synchronization.md) | ✅ Complete |
| 07 | Close coverage and source pair gaps | [Prompt](https://github.com/WsprryPi/WsprryPico/blob/1a383a993833f05ab0ea574286dc5eec8ba4d09b/engineering/development/ci-reliability-campaign/phase-07-coverage-and-pair.md) | ✅ Complete |
| 08 | Consolidate demonstrably redundant build work | [Prompt](https://github.com/WsprryPi/WsprryPico/blob/1a383a993833f05ab0ea574286dc5eec8ba4d09b/engineering/development/ci-reliability-campaign/phase-08-build-consolidation.md) | ✅ Complete |
| 09 | Optimize isolated execution scheduling | [Prompt](https://github.com/WsprryPi/WsprryPico/blob/1a383a993833f05ab0ea574286dc5eec8ba4d09b/engineering/development/ci-reliability-campaign/phase-09-scheduling.md) | ✅ Complete |
| 10 | Resolve holds and repair documentation | [Prompt](phase-10-retention.md) | ✅ Complete |
| 11 | Perform adversarial acceptance and handoff | [Prompt](phase-11-final-acceptance.md) | ⏳ In progress |

## Shared execution contract

The user's Wsprry Development Session standing authority authorizes sequential
execution in this session, including necessary development, dependencies, Git/CI,
and approved enforcement changes in the three Wsprry repositories. It supersedes
preparation-only, separate routine approval, and no-CI clauses in the original
prompts. Continue through accepted phase boundaries without another invocation.
Preserve unrelated work, shared tools, protected history, credentials, and devices.
No merge, publication, release, deployment, service change, or RF test is part of
this software campaign. The independent original Pi checkout can move branches;
explicit campaign worktrees and paired refs determine validation inputs.

- Read the active prompt, current project instructions, owning implementation,
  and [CI execution contract](../software-build-ci.md#execution-completeness-and-local-qualification).
  Inspect and preserve current working changes before mutation.
- Keep the one current settings/control major and strict schema/identity/limit
  checks. WTP, transport, storage, and deployment formats remain independent.
  Preserve crypto, framing/ACK, journals, no-write refusals, inhibition, source/
  shipped browser paths, captures, and independently fresh reproducibility.
- Observe readiness and fault entry before advancing logical clocks. Product
  timing stays intact; finite watchdogs bound hangs. Register owned resources
  before fallible work, preserve primary/cleanup errors, and confirm writer death
  before removing profiles. No blind retries or timeout expansion for a green run.
- Required affected checks must actually pass. Both production network and USB
  suites are required for shared fixture/protocol changes and final acceptance;
  use the [exact paired recipes](../software-build-ci.md#build-reuse-and-source-pairs)
  with identified candidate sources and pinned recursive dependencies. Missing,
  skipped, cancelled, failed, stale, or wrong-source results remain unresolved.
- Reassess deliberate-defect sensitivity after affected changes. Existing proof
  can be reused only for unchanged behavior. Source, run/attempt, workflow/job,
  profile, artifacts, logs, and result counts must agree; producer names alone
  do not establish provenance. Software checks establish no physical timing/RF
  qualification.
- Charge every helper, regression, activated suite, setup/transfer, companion
  change, and retained build context. Keep physical and logical counting units
  separate. Unused fixture retirement earns zero reduction-goal credit.
- Preserve active build/recovery dependencies and user work. Inventory exact
  retirement/retention decisions, consolidate useful current instructions, and
  repair references before removing completed prompts or temporary narratives.
  Keep unfinished handoffs reachable; use no archive copies.
- Commit and push validated slices to the feature branches. Intermediate
  documentation-only status/evidence updates may skip CI. The final candidate
  must have its current required verification and source-bound artifact checks;
  earlier artifacts cannot be relabelled after a source-identity change.
- After each phase, report actual results/limitations, update this list, and
  print all eleven statuses. Do not declare the campaign complete with unresolved
  required checks or missing intended companion refs.

## Acceptance inputs for the final review

The [frozen baseline](baseline.json) and [baseline definitions](baseline.md)
remain active accounting inputs. Accepted evidence is retained for final
reconciliation: [02](phase-02-results.md), [03](phase-03-results.md),
[04](phase-04-results.md), [05](phase-05-results.md), [06](phase-06-results.md),
[07](phase-07-results.md), [08](phase-08-results.md), [09](phase-09-results.md), and [10](phase-10-results.md).
The final review consolidates the necessary scorecard and current limitations
before retiring intermediate evidence narratives. This active plan and the
requested saved-prompt index remain the campaign entry point.
