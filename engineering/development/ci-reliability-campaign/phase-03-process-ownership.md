# Phase 03 Repair process ownership and failure propagation

Execute only phase 03 when explicitly invoked. Read the complete
[shared execution contract](README.md#shared-execution-contract),
[orientation](orientation.md), and accepted phase 01/02 evidence. Phase 01 must
be complete; phase 02 result-handling changes must be reconciled. Pending remote
merge-rule approval is not authority to bypass tests and need not block this
independent implementation.

## Objective and scope

Establish bounded operation and teardown for every affected owned subprocess,
without rewriting product behavior or reducing scenario assertions. Inspect
tests/fixture_process.mjs, browser_deadline.mjs, ui_process_cleanup.mjs,
consumer_sessions.test.mjs, ui_review_fixture.mjs, endpoint_tests.py, the TLS/plain/
local/admission/Nagle Python fixtures, and all imported callers before changing
interfaces. Inspect Pi process adapters only as affected companion inputs.

## Work

1. Trace ownership from spawn through registration, initialization, commands,
   EOF/exit, and finalization. Inventory descendants, including detached fixture
   groups that do not belong to the parent's process group. Define which resource
   owner must confirm each writer's termination and what orderly termination
   means for each fixture. Register it before the first fallible await.
2. Reproduce the suspected late-failure path: a last response can succeed before
   an unexpected child exit or recorded asynchronous failure. Ensure finalization
   cannot report success merely because subsequent cleanup succeeds. Preserve
   intentional orderly EOF and caller-requested termination semantics.
3. Bound JSON/control-line reads with framing, byte limits, partial-read state,
   monotonic enclosing deadlines, and early error/EOF/exit handling. A selector
   becoming readable does not make a following blocking readline safe. Preserve
   UTF-8, queued/reordered replies, request correlation, serialization, and
   cancellation; cancelled replies cannot satisfy a later command.
4. Make cleanup idempotent and finite for already-exited children, simultaneous
   exit, ignored EOF/SIGTERM, failed signals, and descendants retaining pipes.
   Observe graceful completion, escalate only owned resources, reap children, and
   distinguish expected shutdown from a crash. Do not globally accept arbitrary
   exit codes or insist every intentional signal shutdown return zero.
5. Attempt all independent finalizers even after one fails. Preserve primary and
   secondary errors; do not silently lose asynchronous cleanup failures. Do not
   remove profiles while writers remain, or expose withheld fixture secrets to
   obtain better diagnostics. Preserve stage, pending bytes, exit/signal, resource
   ownership, and finite watchdog diagnostics without disclosing sensitive data.
   Treat failure to confirm teardown as a failed result, not permission to delete
   a live profile. Restore deliberately faulted test resources through their
   retained ownership handles and report any unresolved residue explicitly.

## Validation and adversarial assessment

Add behavior regressions for failure before ownership registration, partial JSON/
control line, malformed/oversized data, EOF before reply, spawn error, last-reply
then crash, already-exited child, cancellation with a late reply, ignored shutdown,
signal denial, and one finalizer failing while others still run. Use observable
fault-entry handshakes before advancing logical clocks; retain finite independent
real watchdogs. Confirm no owned processes, pipes, timers, listeners, or profile
writers survive successful cleanup, without scanning/killing unrelated resources.

Run the affected existing native-browser and fixture tests, including current
startup/cleanup regressions, then both actual production network and USB suites
on the intended candidate sources. Confirm ordinary functional failures and
combined cleanup failures reach required CI outcomes. Review adversarially, fix,
rerun affected checks, and reassess; green happy paths alone are insufficient.

## Acceptance and handoff

Supply the ownership map, reproduced versus disproved concerns, exact expected
shutdown contracts, regression results, source-pair evidence, and net maintenance/
execution cost. No scenario or negative oracle may disappear during extraction.
Publish the helper/caller interfaces for phases 04/05/06, reconcile phase 02 result
reporting, update phase status only after all required checks pass, and stop.
