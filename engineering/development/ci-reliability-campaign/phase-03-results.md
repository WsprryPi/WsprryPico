# Phase 03 process ownership

## Reproduced failures and repairs

A real Node fixture returned its final JSON response, then exited 17. The old
`stop()` resolved successfully despite its recorded asynchronous failure. The
new finalizer reports the unexpected exit, including a crash during orderly EOF.
A command failure that has already propagated remains distinct from a new idle
failure. Cleanup failures preserve the operation, exit, and secondary diagnostics.
Every independent stream finalizer is attempted.

The review server registered a driver only after fallible initialization and
installed signal handlers only after all profiles started. Ownership and signal
recovery now precede the first command. Every acquired HTTP server and driver is
registered before its first fallible await. Cleanup attempts all registered
resources, bounds HTTP close, and preserves the initiating error.

Its drivers previously created separate detached groups. A forced owner stop
could therefore strand them. Review-server drivers now inherit that server's
owned group. All Unix browser owners isolate their server/browser groups; a
forced owner stop can recover every native driver in the server group. Direct
`FixtureProcess` users retain their own groups. The choice is explicit and
validated before spawn. No physical device or RF resource is involved.

`cleanupUiProcesses` observes live group membership after signalling; merely
sending SIGKILL cannot authorize deleting a profile. Linux process state and
macOS process-group/state output distinguish live writers from dead zombies.
Permission denial of a signal-zero probe is not treated as death: an independent
permitted process-state read must prove it. Actual signal failure remains a
cleanup failure. Group observation shares the original finite two-signal teardown
budget. Cleanup has its own monotonic scope so an expired operation cannot
prevent recovery.

## Python control fixtures

The six endpoint/TLS/plain fixtures now use `fixture_process.py`. A lexical
`process_scope` owns every child before initialization, restores signal handlers
when acquisition fails, and attempts every finalizer after an exception or
interruption. SIGINT/SIGTERM recover nested owned fixtures. Normal shutdown must
return zero; forced recovery reaps the child but does not manufacture a successful
orderly shutdown. Only retained owned process groups are signalled.

Reads use bounded byte framing and selectors, not blocking `readline()` after
readability. UTF-8 decoding is strict; complete queued lines retain their order.
Writes are bounded as well. Exchanges share one monotonic deadline, capped by the
enclosing test watchdog. A failed/cancelled channel refuses later requests, and
unsolicited buffered or shutdown output cannot qualify a new response. Diagnostics
retain a bounded stderr tail for existing resource assertions; failure messages
expose stage, pending-byte counts, exit, and diagnostic sizes rather than payloads.

The lexical scopes indent existing scenarios without relocating them or replacing
production assertions. AST assertion counts before/after are 66/65 endpoint,
103/103 TLS, 7/7 plain, 17/16 admission, 8/8 Nagle, and 5/5 local WTP. The two
removed assertions were the endpoint zero-exit check and the admission
readability check, now enforced more strictly by the shared ownership/framing
helper. All 204 remaining assertions and their scenarios remain.

## Behavioral checks

- Python ownership regressions: 16 cases cover prior ownership, missing executable,
  partial acquisition rollback, finite watchdogs, malformed stdio selection,
  fragmented UTF-8, queued lines, observed partial data, enclosing deadline,
  invalid encoding, oversized output, stale replies, late shutdown output, EOF,
  final reply/crash, independent finalizers, ignored EOF, descendant-held pipes,
  signal recovery, and denied signals. macOS and Linux runs passed.
- JavaScript process regressions: 21 cases passed on macOS. The combined Linux
  cleanup/startup/contextual-help run passed 34 cases, zero skipped/cancelled/todo.
  Fault entry is observed before triggering a watchdog or recovery. Deadlines
  bound hangs, not functional response speed. Polling intervals only pace state
  observation; they never prove completion.
- The migrated endpoint, TLS, Nagle, local, plain, and admission CTest slice plus
  the helper registration is rechecked against actual compiled Pico handlers.
  The complete native-browser invocation set and both actual production pair
  suites are acceptance gates below.

The campaign's original isolated container used `sleep` as PID 1 and could not
reap deliberately orphaned fault-test processes. Its dependencies and native
builds were retained in a local image, and only that idle campaign container was
recreated with Docker `--init`. The prior container is stopped. Other containers,
repositories, hosts, services, and devices were preserved. Successful fault tests
now use an init reaper as well as verified writer termination.

## Interfaces and remaining adoption

Direct JavaScript fixture owners await `stop()` in finalization and preserve its
failure. The review server may use `processGroup:false` only because its native
drivers remain inside the retained parent group. Python callers enter
`process_scope`, use `line`, `send_line`, or `exchange`, and close through `finish`
with the driver's explicit EOF/TERM policy. Diagnostic text is available only
after teardown. All callers changed together; no wire/control schema changed.

Phases 04/05 adopt these qualified interfaces across the browser lifecycle. They
still own browser/CDP discovery, individual early-startup scopes, HTTP proxy
shutdown, and replacement of duplicated polling/connection implementations. Those
existing browser concerns are not represented as already migrated by this phase.
Windows native fixture/process qualification is not claimed; the campaign's
canonical software baseline is Linux, with these ownership regressions also
exercised on macOS.

## Acceptance

Implementation validation is in progress. Final candidate identity, actual
network/USB results, native-browser results, measured costs, and the final
adversarial reassessment will be recorded before this phase is marked complete.
