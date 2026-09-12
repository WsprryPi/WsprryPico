# Phase 11.5 documentation-only reorganization prompt

Reorganize and right-size the Phase 11.5 tests into six acceptance families for
the actual Pico use cases. Execute this prompt, perform an adversarial review,
fix documentation findings, repeat the assessment, commit and push the reviewed
documentation, and report exact repository state and remaining implementation.

## Scope and starting point

Work on the clean `devel` checkouts of WsprryPico and its WsprryPi companion.
The coordinating checkout starts at Pico
`5a0cf4be287ef9cc3142b2d831f06d44f30862b8`. Inspect both working trees and local
instructions; preserve user work. The user's September 12 instruction authorizes
**documentation only**. Do not change firmware, application code, tests, runners,
validators, schemas, generated artifacts or operational configuration. Do not
run builds, hardware tests, SSH campaigns, flashing, RF, network fixtures or
service operations in this task. Git commit/push is explicitly authorized.

Read README, CONTRACT, architecture, the current Phase 11.5 plan/metrics/register,
the latest STATUS repair result, the actual browser asset/polling sources and
the relevant Phase 11.4 certificate, recovery and discovery acceptance records.
Treat source reads as evidence, not permission to edit code. Pi owns production
client/load behavior; Pico owns the joint resource/timing plan and evidence.

## Required result

1. Preserve the complete old plan as a historical document. Retain original
   A1-G1 IDs, attempts, failures, thresholds, exact-image qualifications and
   their 2/20 historical count. Do not edit past result JSON or silently convert
   the legacy executable register into a new schema.
2. Publish one authoritative prospective plan with six families: baseline;
   nominal RF execution; resource saturation/reclamation; authority/interruption;
   network/configuration/standalone lifecycle; sustained mixed operation.
   Map all 20 legacy cases exactly, explaining retained assertions, consolidated
   executions, selective prior-evidence reuse and any explicitly deferred breadth.
3. Justify each family against autonomous scheduling, the real WsprryPi backend,
   direct browser control or USB reference/recovery. Cover actual physical
   execution and local completion independent of transport. Keep simulated,
   source, physical-idle, RF-contention and conducted RF evidence distinct.
4. Separate normal operator behavior, a declared heavier supported workload,
   deliberate overload and measurement traffic. Verify the served page embeds
   CSS/JS and normally refreshes on operator actions. Do not call repeated
   separate asset fetches normal page behavior. Preserve old stress results.
5. Preserve RF timing, both stack reserves, allocator recovery reserve, authority,
   shutdown, observation correctness and bounded recovery requirements. Explain
   request cadence versus response latency and state-dependent controller policy.
   Do not relax old failed gates retrospectively or hide a nominal failure under
   an overload label. Freeze future workload and limits before measurement.
6. Replace unjustified uniform repetitions with distinct-path coverage and
   repeated lifecycle/retention cycles. Keep separate timeout/resource classes,
   LOAD/ARM/ABORT uncertainty, Armed/Running aborts, full/short/tail RF paths and
   all exposed modes. Add explicit autonomous scheduling coverage within the
   existing lifecycle/endurance work. Keep journal rotation distinct from endurance.
7. Retain equal-state quiet comparisons and explicit expiry accounting without
   mechanically repeating long idle waits before every subcase. Explain what can
   share a fixture, boot or observation and what changes invalidate reuse.
   Respect the last recorded 22/32 configuration-write budget and reserve
   restoration writes before allocating E1/lifecycle work.
8. Publish a current Markdown ledger. The candidate is source
   `e20ae8bea2d5237af017dbd5f73bfe9332ce144e`, physical 138 MHz; the latest bounded
   nominal idle check passed but exercised no credit wait. Historical STATUS
   causes and active RF contention remain unresolved. No new family is closed
   by documentation; no clock configuration is accepted. Mark 132/150 MHz
   physical clocks untested and require affected 11.5 checks if 11.6 selects another.
9. Explain small independently audited execution packets, prerequisite gates,
   source-change impact review, failure isolation and per-packet progress counts.
   Do not present elapsed setup/preparation time as measurement duration or
   promise a full six-family run in one short session.
10. Identify the precise runner/validator adaptation still needed under a later
    code-authorized task. Existing hardcoded A2/A3/all-case runners are not
    implementations of this plan. Do not bypass their guards, disable the old
    validator or mark removed assertions PASS to obtain closure.

## Review and publication

Review all 20 case mappings, cross-repository consistency, evidence identities,
historical preservation, workload realism, closure predicates, clock deadlines,
write/restoration budgets and implementation-readiness claims. Repair actionable
documentation findings and reassess. Validate local links, preserved artifact
hashes, numerical clock calculations and whitespace. Existing read-only register
validation may run after inspection; it proves only the unchanged legacy format.
No runtime test or new acceptance is claimed.

Update the development index, coordinating plan, current ledger/review pointers
and companion development review. Leave normative WTP/browser/architecture and
operator documentation unchanged unless a real contract change is required;
this task changes test organization, not product behavior. Record documentation
impact and any future operator follow-up. Commit only scoped Markdown changes
in each changed repository, push `origin/devel`, verify clean trees and live
remote parity, and report remaining work honestly.
