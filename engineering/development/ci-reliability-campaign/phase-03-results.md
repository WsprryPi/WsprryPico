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

The accepted implementation candidate is Pico
`5f85c3b08c8559c1939979b55c9eba6f412417de`, paired with clean Pi devel
`1e15b2485ac6e1b9cbb6ff435afc0f0232528804`. No source edits occurred during
its final pair run. The MbedTLS dependency remains the clean exact
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` with its required recursive inputs.

All affected local gates passed:

- 16 Python ownership methods on macOS and Linux; 21 process methods on macOS;
  all 34 Linux process/startup/contextual-help cases with no skips/cancellations.
- The seven affected CTest registrations passed in 18.43 seconds. Commands:
  `ctest --test-dir build/campaign-host -R
  "^(fixture_process_tests|endpoint_tests|network_tls_tests|network_tls_nagle_tests|network_local_wtp_tests|network_plain_wtp_tests|network_plain_admission_tests)$"
  --output-on-failure` and the direct Python/Node commands above.
- All 13 native production browser invocations passed with the final group
  topology. Their final log slices and result files were independently rechecked
  with the strict execution verifier. Receipts identify the prior documentation
  HEAD `a872f42e` plus the then-tested uncommitted implementation, subsequently
  committed unchanged as `5f85c3b0`; the final macOS runs and pair run use that
  committed candidate directly.
- Network recipe: `make -C <Pi>/src wtp-network-runtime-test BACKENDS=simulated
  ANCILLARY_GPIO=0 SUDO= WTP_NETWORK_BUILD_DIR=/home/campaign/pair-network`, then
  `make -C <Pi>/src wtp-network-interop-test wtp-config-interop-test SUDO=
  PICO_SOURCE=<campaign Pico> MBEDTLS_SOURCE=/deps/mbedtls-pinned
  WTP_NETWORK_BUILD_DIR=/home/campaign/pair-network`. All runtime, TLS,
  configuration, production UI/coordinator, resource, journal, and both native
  browser-crypto-context assertions passed.
- USB recipe: `make -C <Pi>/src wtp-usb-pair-client-build
  wtp-usb-management-test SUDO=`, the actual `wtp_usb_settings_test.js`, and
  `WSPRRYPI_GPIO_DRIVE_REQUIRED=1 node <Pi>/WsprryPi-UI/tests/wtp_usb_pair_test.js
  <Pi>/src/build/wtp-network/wtp_usb_pair_client
  <Pico>/build/campaign-host/usb_management_driver`. The real Pico driver was
  built from this candidate worktree. All production UMP framing/ACK, settings,
  blank/create/replace/delete/recreate, progress, station, time, and GPIO cases
  passed. The complete sequential pair command returned zero.

Detailed local logs remain under ignored `build/campaign-phase03-*` and
`build/campaign-native-audit-phase03-final`. Final process inspection in the
init-enabled validation container found only its init/idle command and the
inspection itself, with no surviving test processes, zombies, or profile writers.
No devices were programmed and no hardware, installation, service, timing, or RF
qualification is claimed.

Canonical [Pico run 42070500676](https://github.com/WsprryPi/WsprryPico/actions/runs/42070500676)
passed for the immutable implementation candidate, with publication intentionally
skipped. It covers the complete software, firmware, image, provenance, and fresh
reproducibility gates in addition to the exact local source-pair results above.
Final campaign acceptance still requires successful canonical validation for the
final campaign candidate.

Final adversarial reassessment found no unresolved issue in this phase's shared
ownership/framing slice. The observation-file race in the new fault tests was
reproduced under Linux; atomic rename now publishes complete state, without a
sleep or a permissive JSON retry. Late-exit assertions accept either event order
and require the actual nonzero exit diagnostic. Additional browser/CDP lifecycle
adoption remains explicitly assigned to phases 04/05 above.

The executable/test slice adds two files and 653 net physical lines across
23 changed paths, including the helpers and regressions. Indentation changes
inside lexical ownership scopes receive no reduction credit. These are
correctness costs, not savings. The local affected slice and cold-start suite
measurements are observations, not whole-CI speed claims. Phase 03 is complete;
phase 04 is in progress.
