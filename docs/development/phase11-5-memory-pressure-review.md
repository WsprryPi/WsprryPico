# Memory-pressure repair review

## Reviewed cause and repair

The [execution prompt](phase11-5-memory-pressure-prompt.md) records the current
capabilities, recent repairs, failed P1i workload and frozen acceptance rules.
The original event list remains allocated beside the independently prepared RF
plan during Armed/Running. It occupies 20,480 bytes for 512 events on RP2350.
P1i's recorded shortfall was 7,248 bytes. This source finding identifies removable
overlap; it does not establish the exact cause of every monitoring timeout.

The engine interface now defaults to retaining input. StreamEngine advertises
an independent execution plan. WorkerEngine captures that immutable capability
before worker startup, and its synchronous schedule call clears the borrowed
input pointer before returning. JobService releases only its event vector after
acknowledged successful local schedule or foreground begin. Identity, duration,
original typed digest and adjustment replies remain. Failed handoff does not
release the input. Default adapters keep the prior lifetime.

The original digest is saved after successful LOAD validation/preparation. LOAD
conflict checks and terminal history use that digest after event release.
Retention counts, expiry, ownership and replay precedence are unchanged.

WTP input admission separately budgets 8,192 temporary bytes plus 1,024 bytes
for page bookkeeping/parser storage, above the unchanged 32,768-byte reserve.
INFO formatting and small-request decoding are serialized on core 0. This
provision exceeds the approximately 8.5 KB observed transient allocation above
the pre-format snapshot; it is a bounded allowance, not a proof for arbitrary
additional clients. Maximum message limits and five-second deadlines remain.

RF plans, renderer, launch guard, refill loops and clock are unchanged. Releasing
memory and storing digests changes allocation/lifetime and foreground work;
current-candidate resource and timing acceptance requires affected target tests.

## Host validation and adversarial assessment

- The handoff matrix checks local/foreground launch, borrowed/owned input,
  completion, abort, uncertain stop and rejected handoff. It verifies actual
  allocation release, cached/fresh/compact LOAD replay, changed-event conflicts,
  ARM replay and replacement jobs.
- The actual StreamEngine produces identical complete output checksums with
  the caller's 512-event job retained or destroyed before subsequent refills;
  execution allocates no additional memory in that test.
- The endpoint/service/stream allocation model handles maximum STATUS and its
  replay during simulated Running with retained history and a 39,576-byte
  background, including 8,192 diagnostic bytes. Every measured exchange retains
  at least 32,768 bytes. This is a host model, not target RF evidence.
- Input admission tests reject both insufficient workspace and size overflow;
  exact maximum bytes still pass with sufficient budget. Existing page-failure,
  framing/CRC, output pressure and reconnect checks remain.
- Stronger admission moves two pressure refusals before decoding. Their tests
  now require immediate closure. Separate endpoint tests introduce competition
  after input admission and retain original 4.999/5.000-second recovery/expiry
  assertions. No timeout or reserve was relaxed.
- Broad regression exposed an outdated synthetic HTTP serializer fixture.
  Rebuilding it with current HTTP paging and browser assets preserves its JSON
  body and status semantics; only CSP asset hashes change. Provenance and bytes
  were regenerated together rather than editing a hash to suppress the failure.
- All 72 configured CTest groups pass across the broad run and affected reruns,
  including local TLS (11.32 seconds). The R3 group runs 228 cases with 48
  private-evidence skips. Twelve reservation/deployment/gate checks pass; RF
  packet checks pass 14 cases with one private-evidence skip.
- Three separately compiled source mutations are rejected: retain the execution
  vector, recompute terminal digest after release, or omit temporary input
  workspace. The intact core binary passes again after those negative checks.

The reviewed five pre-existing helper changes pin the earlier 150fe01 deployment,
native-idlek scope and P1i packet. They do not grant acceptance to P1i or modify
its frozen executed helper copies. The prior finite fixture reports restored,
with no cleanup failures and its protected host snapshot matching its baseline.

At this source checkpoint, no actionable host repair finding remains. Both
linked-image verification and the retained-workload target retest are pending;
Phase 11.5 remains OPEN, with R1/R2 closed only within their recorded scope.
The new source has not yet been flashed at this checkpoint.
