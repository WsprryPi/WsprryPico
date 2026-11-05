# Phase 06 Remove scheduler dependent synchronization

Execute only phase 06 when explicitly invoked. Read the complete
[shared execution contract](README.md#shared-execution-contract),
[orientation](orientation.md), phase 01's wait/obligation map, and accepted phase
03/05 lifecycle evidence. Reconcile any newer adapter changes before editing.

## Objective and scope

Replace assumptions about host progress with observed state or controlled logical
time, retaining real transport behavior and production timing. Primary owners are
tests/network_tls_tests.py, network_tls_driver.cpp, network_mock/tcp.cpp, the
plain/local/admission/Nagle fixtures, and hostname_browser_integration.mjs. Inspect
production timing consumers to define semantics, not to relax them for tests.
No product timeout, session policy, wire contract, or hardware behavior change is
an incidental part of this phase.

## Work

1. Classify every relevant sleep, timeout, retry, and timer. Record its owner,
   units, intended state transition, product obligation, and real versus logical
   clock. Separate polling cadence and failure watchdogs from assumptions that a
   write, close, allocation, cancellation, or job transition already completed.
   Keep justified product-expiry and deliberate regression stimuli.
2. Reproduce suspected races using explicit gates at test adapter boundaries.
   Demonstrate the intended pending/paused state before assertions or clock
   advancement. Replace control-write sleeps with correlated acknowledgments or
   actual observable effects. An ACK means the defined effect is visible, not
   merely that the command entered a queue. Refuse unexpected or stale replies.
3. Where accelerated host time currently drives synthetic device deadlines,
   introduce the smallest explicit test clock seam with bounded operations and
   ordered foreground servicing. Preserve production deadline constants, units,
   comparison boundaries, ownership, framing, real TLS/crypto, and actual handler
   execution. Inspect every consumer of the seam, including companion adapters.
   Keep an independent real watchdog for stalled I/O or a frozen logical clock.
   Keep protocol monotonic time, UTC mapping, and certificate-validity time
   distinct. A test clock must not accidentally bypass real certificate expiry,
   restore clock authority, or alter the independently tested crypto boundary.
4. Exercise running, completion, expiry, loss/recovery, and pending-admission
   states deterministically. Do not poll until a transient failure disappears or
   advance beyond the state a test intended to observe. Keep positive progress
   and negative/no-write assertions at the exact meaningful boundaries.
5. Replace the hostname cancellation observation sleep by controlling the existing
   scheduled callback boundary. Execute the relevant timer work and prove no
   additional restart occurs after cancellation; simply stubbing the callback or
   asserting a cancellation flag does not test the product behavior.

## Validation and adversarial assessment

Show correct behavior with delayed command consumption, fragmented I/O, reordered
or withheld acknowledgments, resource release, and cancellation. Sensitivity
experiments must catch deliberately broken admission, timeout comparison,
completion, ownership/no-write, and cancellation behavior. Test just-before,
at-boundary, and just-after logical times where the contract distinguishes them.
Preserve partial frames, withheld first-flight ACK, paused handshake, real
certificate/ALPN rejection, resource retention, and link-loss obligations.

Restore all deliberate defects and run affected fixture/browser/helper tests and
both actual production network and USB suites on the intended source pair. Reject
arbitrary deadline inflation, unconditional retries, permissive stubs, and changed
product timing as repairs. Review, fix, rerun affected checks, and reassess.

## Acceptance and handoff

Deliver the classified wait inventory, removed assumptions and their replacement
oracles, adapter clock/ACK semantics, sensitivity results, source-pair evidence,
and net code/process/runtime budgets. Count new controls and regression work.
Record justified remaining waits and evidence limits explicitly. Phase 09 receives
the actual resource/timing constraints; update phase 06 status only after required
checks pass and stop.
