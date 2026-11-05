# Phase 04 browser pilot results

## Implementation and obligation reconciliation

The session pilot still exercises the shipped page, actual HTTP/AEAD handlers,
idle expiry at 30 minutes, absolute expiry at eight hours, nonrenewing public
and edit activity, preserved drafts, locked writes, explicit post-login review,
and refusal of unauthorized writes. Its four desktop/mobile expiry captures
remain. A new independent persisted-journal comparison strengthens the existing
request-log refusal assertion; it does not replace it.

Named profile selection is validated before spawning. Omitted selection retains
all ten definitions; sparse selection preserves original authority, identity,
and port offsets. The pilot selects consumer-lan only. Three native tests inspect
actual driver executable, ownership, and public handler identity/configuration
for one, sparse two, and default ten profiles. Echoed profile names alone are not
the routing oracle.

Pure CDP transport, owned fixture startup, and BrowserScope modules now provide
correlated commands, bounded discovery/fetch/body/socket operations, enclosing
monotonic budgets, independent cleanup watchdogs, cancellation, late-exit refusal,
and ownership before awaiting initialization. Chrome startup retains its qualified
cold-start allowance and observed 21-second regression. Grace periods and polling
pacing are failure recovery/readiness mechanisms, not functional assertions.
All independent finalizers run and preserve primary and secondary errors. Private
profiles are removed after writers stop. CI locates required Chrome before CTest,
where native sensitivity coverage now runs; missing Chrome fails explicitly.

## Adversarial findings and closure

- Strict owner-exit checking exposed whole-group SIGTERM racing the review
  server's own driver finalizers. Graceful termination now targets the owner;
  forced recovery still targets and verifies the complete owned group. The
  signal-denial regression targets the actual retained process handle.
- Discovery reads require a bounded regular file, strict UTF-8, complete metadata,
  and a qualified live page. Stalled bodies, malformed envelopes, cancelled/late
  replies, reordered correlations, and early/late process exits have regressions.
- Expiry sensitivity freezes both test clocks after observed control ACK; draft
  sensitivity corrupts the actual clear path; mutation sensitivity performs an
  actual host-test journal save. Each requires fault-entry evidence, its intended
  assertion failure, completed cleanup, no success result, dead owned process
  groups, and removed browser profiles. The mutation seam is compile-guarded
  host-only code and never modifies firmware or physical devices.
- A fourth sensitivity case signals the pilot only after observing initialization
  and ownership. It verifies independent cleanup during partial acquisition.

Reassessment found no remaining actionable pilot issue. Remaining browser callers
still use their original lifecycle until phase 05; this phase does not claim their
migration. CDP session support for multiple recovery contexts must be preserved
when that caller migrates. Phase 07 must qualify inner framework discovery/skips
inside CTest, in addition to existing exact registered CTest result enforcement.

## Validation and costs

Final affected checks: 56 Node helper/startup/cleanup methods passed, zero skips;
five registered CTest suites passed, including three real native profile cases
and four pilot sensitivity cases. All thirteen production browser invocations
passed their existing completion contracts. Execution's 12 methods and bundle's
59 methods passed. The positive pilot retained four captures and passed the added
persisted-journal assertion. Ignored build/campaign-phase04-* logs retain details.
Both production carrier results and committed source identities are recorded
below after candidate validation; they remain mandatory acceptance gates.

Regular review-server startup demand is 70 baseline native drivers across seven
calls versus 61 after this pilot's ten-to-one selection. Native selection tests
add 13 starts, deliberate browser faults add three starts, and initialization
signal recovery is additional work. Five new Chrome regression methods create
six fake Chrome children. These costs are charged separately; no whole-CI process
or runtime reduction is claimed. Helpers and regressions increase physical code.

A single warm, same-container comparison with fresh profiles/journals and captures
passed: old pilot 2.6194 seconds, new pilot 2.5537 seconds. Both used the current
production driver and shared server; the new pilot additionally checks journals.
This is neither equivalent cold-CI evidence nor an attributed speed improvement.
The independent fresh reproducibility build remains required.
