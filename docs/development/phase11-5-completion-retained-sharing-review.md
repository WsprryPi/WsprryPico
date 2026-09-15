# Retained adjustment sharing review

Phase 11.5 remains OPEN. This checkpoint repairs a resource lifetime problem
and records a failed target packet. It closes no acceptance family.

## Evidence and diagnosis

Native-idlej ran on A, source 6b7a1b8, boot
1739cc4f28304080ec97e2b228ab2683. It began with two Aborted terminal records.
The first two 512-event LOADs returned complete exact adjustments; the third
wrote all 52,105 bytes but produced no response within five seconds. No replay
or RF occurred. The target remained healthy on the same boot: allocator peak
173,816 / capacity 218,968 bytes, zero allocation/TLS failures and no fault.

The independent [failure audit](phase11-5-completion-retained-sharing-result.json)
decodes framed bytes and inventories, checks exact operations and full writes,
and verifies final inactive authority, configuration and shared reservation.
Altered write, native capture and INFO peak evidence were rejected. The native
process's successful exit after early termination is not a 90-second pass.

Source inspection finds a separate immutable 512-entry adjustment allocation
for each retained job, including jobs whose values are identical. The original
host model reproduces a silent admission timeout on its third series LOAD at
31,384 bytes modeled background. This supports the resource-admission diagnosis;
it does not instrument or prove the exact historical target branch.

## Repair and source impact

After ordinary engine preparation and validation, JobService compares the
complete adjustment sequence against bounded retained jobs. Equal sequences
share their existing immutable storage. Different lengths, event indices or
requested/realized frequencies retain separate values. Job IDs, typed digests,
states, cached responses, ownership and expiry remain independent.

This changes memory lifetime during LOAD and retention. It adds at most eight
bounded list comparisons after preparation. It does not change RF rendering,
launch, refill, advertised limits or the 32,768-byte safety reserve. Earlier
timing evidence retains its recorded applicability; current-candidate resource,
LOAD/retention and combined-load assertions need affected target evidence.

Host checks cover distinct-job replay identity, changed adjustment values,
survival after service reset, exact 512-entry responses, eviction at eight
terminal records and refusal for nonidentical retained lists under pressure.
The sharing model passes eight LOADs at background 31,384 and nine at 18,168.
An exploratory ninth at background 31,384 still returns INTERNAL_ERROR under
the unchanged preparation admission gate. This is an unresolved modeled
combination, not evidence of supported capacity or accepted overload. It must
inform Packages 2 and 5 rather than be omitted from the workload definition.

Nine affected CTest groups passed: core, endpoint, LOAD reply, network,
standalone, RF stream, RF worker, RF worker failure and TLS. The TLS run took
11.41 seconds. Existing allocation-model refusal scenarios now explicitly use
a nonidentical retained list so that they continue exercising refusal after
the intentional sharing optimization. This does not change a target threshold.

## Harness findings and reassessment

- Native-idleg exposed a monitor sampling gap between LOAD and ABORT. The new
  gate waits for two fresh matching Loaded publications at least one second
  apart, retaining the three-second minimum dwell and six-second deadline.
  Native-idlej passed this gate for its first two jobs before the distinct
  third-LOAD failure. It is not a completed native regression pass.
- Native-idleh froze terminal IDs in creation order rather than the actual
  newest-first inventory order. It failed preflight. Its old finally block
  nevertheless attempted cleanup operations without owning the reservation.
  The repaired runner performs mutation cleanup only after acquisition. A
  mocked end-to-end failure test verifies no ABORT/CLAIM/RELEASE or reservation
  acquire/release when admission rejects, including foreign active authority.
- Native-idlei was refused during staging because its cleanup allowance could
  no longer fit. It did not freeze or execute a packet. The old fixture was
  restored; no deadline was extended.
- The independent native-success auditor initially lacked its newly imported
  runner module in the staged review bundle. This produced AUDIT_REJECTED and
  no acceptance. The subsequent failure-review bundle includes its complete
  public import dependencies and audits the failed outcome explicitly.

Twelve reservation/deployment/gate tests and twelve native scheduling/health
tests passed. The old native-idlef positive audit and three altered-evidence
checks still pass. No target resource or family closure is inferred from them.

The reviewed changes have no remaining actionable finding within this host
repair and failure-recording scope. Physical validation and the larger modeled
retained combination remain open. Use a fresh finite deployment/test packet;
preserve the failed packet and all cumulative charges.
