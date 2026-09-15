# Native connection failure and bounded workspace repair

Phase 11.5 remains **OPEN**. [Results, accounting and evidence hashes](phase11-5-completion-native-closure-result.json).

## Recorded outcomes

The reviewed bd16bb1 firmware was flashed once to A. Independent raw inventories
confirm its new boot, selected 138 MHz/RAM/GP2/listener configuration, unchanged
retained configuration and inactive/unowned state. B is unchanged. Linked heap
hooks, stack guards, RF placement and journal bounds passed for both built images.

P1e completed its maximum-event job, but a new policy was omitted from the native
readiness publisher. The consumer waited for a file that never appeared. Its
early return also prevented lease renewal, causing the terminal lifecycle guard
to fail after the owner expired. The publisher and consumer now share one policy
predicate, and waiting for readiness no longer skips renewal. No capacity offer
was made. Raw Console/USB/native evidence confirms local finite completion;
the failed packet remains failed.

P1f used the corrected helpers and the same candidate/boot. Its replacement
maximum LOAD succeeded with all 512 exact adjustments while the earlier Complete
record was retained. The new job completed and RELEASE returned A to Empty.
Three renewals succeeded. However, native STATUS request 9 remained outstanding
when the TLS connection closed. Only a complete frame header declaring 255
payload bytes arrived; none of that payload arrived. This is not a valid frame
or successful STATUS response. The ordinary success auditor rejects it.

The native API retained cached device identity after disconnection. The runner
mistook that identity for observer health. Readiness and ongoing health now
require a ready session, matching non-null remote status, matching boot and a
bounded status age. A regression rejects cached identity with disconnected,
unresolved or stale state. No capacity probes ran in P1f, and it earns no
capacity or full native-continuity credit.

## Mechanism, repair and limits of diagnosis

Native closure occurred 2.214868111 seconds after USB LOAD began. The exact
historical close branch is **unproved**. The incomplete header is consistent
in size/checksum with a Loaded event, but its absent payload cannot be accepted
or decoded as that event. Allocator failures and TLS allocation failures stayed
zero. The packet's allocator peak left 42,328 bytes, while complete-request
decoding requires 16,384 bytes plus the unchanged 32,768-byte safety reserve.

A deterministic endpoint regression independently reproduces premature closure
of a complete small STATUS request at 42,000 available bytes. The repair retains
one already-buffered frame for at most 5,000 ms, blocks further input, and retries
decoding only when the original workspace and reserve are available. At the
original deadline it closes and frees the frame. Disconnect or boot replacement
discards the deferred input. No operation or replay entry exists before dispatch.
No reserve, advertised size, ownership or RF timing rule is relaxed.

The endpoint gains one fixed page table and a timestamp. Linked layout and target
resource checks must be repeated; host heap calibration does not measure this
target layout cost. A deferred operation is still validated against live owner,
clock and job state when dispatched. A transport close cannot execute it later.

Read-only INFO adds `network_wtp_close_reason` and signed
`network_wtp_tls_result`. The reason values are 0 other/unclassified, 1 link loss,
2 peer closure, 3 connection lifetime, 4 endpoint closure, 5 TLS write failure,
and 6 TLS read failure. Only an authenticated WTP closure updates these fields;
later HTTP cleanup cannot overwrite them. Zero is not proof that no close occurred.
These diagnostics will distinguish a recurring target failure without altering
the workload to collect it.

## Checks and adversarial reassessment

- Red/green endpoint regression: premature closure before repair; same-connection
  recovery after repair, exact five-second expiry, and deferred mutation discard
  on disconnect.
- Load-reply sensitivity still refuses insufficient workspace. Its old driver
  assumed immediate progress; it now advances a bounded transport clock and
  verifies refusal at exactly 5,000 ms with all input pages reclaimed.
- Seven affected host targets pass: core, endpoint, LOAD reply, standalone, RF
  stream, RF worker and actual TLS server. The TLS test needed localhost socket
  permission; the sandboxed listener-start failure is retained separately.
- Actual TLS server tests verify WTP link-loss diagnosis and preservation across
  subsequent HTTP cleanup. WTP schema/contract checks pass.
- Independent failure auditors bind executed helper hashes, raw Console/USB,
  native certificate identity and incomplete native input. Altering the captured
  incomplete-frame header is rejected. No missing observation is promoted to PASS.

No actionable finding remains in these reviewed host changes. Target validation
is still required. First run a fresh **zero-RF** retained LOAD/native connection
packet on an identified candidate, including the failed overlap mechanism.
Only after its result is understood may a further RF capacity packet proceed.
Component 9 retains its historical closure; the changed endpoint layout and
admission behavior give a specific reason for an affected target check.

The fixture is still active within its original supervised session. Latest A/B
packet inventories are inactive/unowned with scheduling disabled and unchanged
configuration. The shared RF reservation is released. No restoration of the
active fixture is claimed at this checkpoint.
