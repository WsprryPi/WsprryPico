# Phase 05 lifecycle adoption results

The [caller matrix](phase-05-contexts.md) reconciles all eleven maintained native
browser entry files and thirteen ordinary invocations, explicit software opt-ins,
source/shipped assets, replacement fixtures, and distinct browser contexts.
No product UI or protocol behavior changed. The session pilot retains its
qualified lifecycle; the other ten entry files now use BrowserHarness adapters
around the same BrowserScope, Chrome startup, CDP, and owned fixture interfaces.

## Reliability and adversarial assessment

- Ownership precedes fallible initialization, including drivers, replacement
  drivers, profiles, servers, browsers, and sockets. Cleanup priorities close
  browser clients, then HTTP queues, then backing drivers, even when a replacement
  driver was acquired last. Default scope ordering remains reverse acquisition.
- CDP retains explicit flattened-session correlation for recovery's three isolated
  contexts. Wrong-session replies fail; event handlers retain their actual session.
  Async event failures and pending event work are finalized rather than abandoned.
- Message-frequency's two sequential surfaces receive independent fresh private
  profiles. Profile reuse is explicitly refused. Each selected review fixture is
  checked against actual OS child PID, executable, parent, and group inventory.
- Readiness uses monotonic enclosing budgets and qualified predicates. A migrated
  hostname predicate initially exposed an undefined busy variable formerly hidden
  by catch-all retries; predicates now require the page variable to exist. This
  was a diagnosed migration failure, not a passing rerun counted as first success.
- Navigation retries only the specific CDP cross-document context-loss states.
  Malformed protocol, syntax errors, assertion failures, other CDP errors, and
  asynchronous handler failures remain failures. Popup disappearance requires the
  exact CDP error code/message and fresh independent confirmation of absence.
- HTTP control status checks moved into a common bounded strict-UTF-8/JSON reader;
  oversized/malformed bodies, held-body cancellation, and missing Chrome acquisition
  have regressions. Primary and reader cleanup failures are preserved. HTTP close,
  queued-work drain, and other independent finalizers are all attempted.
- No-capture retains frequency viewport/overflow assertions. The original caller
  had returned before these assertions; the option now suppresses image writes
  only. Required behavioral assertions remain, with three status=200 checks moved
  into the shared reader rather than removed.

The classified hostname cancellation stimulus remains for phase 06. The operator
runner intentionally serves source HTML with production minified scripts/bundle;
that distinct asset path is retained. Recovery still uses a browser-level socket,
three contexts, dialogs, lost committed replies, and independent session retirement.
No hardware entry point was executed or retired.

## Validation and accounting

Initial migrated direct-fixture and ordinary selective-fixture runs passed with
captures enabled. Explicit first-use USB, overlay, network-backing, refusal, and
field AP software contexts passed. The thirteen ordinary command completion
contracts passed. Final affected checks, candidate identities, both full source-pair
recipes, and independently observed ordinary driver counts are recorded at
acceptance below; no pending result is treated as successful.

Shared native-inventory qualification is extracted from the existing real-driver
regression, not a replacement self-reported count. Its helper, per-start OS scans,
new harness adapters, added regressions, and existing context commands all count
as work. Physical code, file, and process changes are reconciled separately from
logical contexts; no whole-CI speed claim follows from selective startup.

Final local helper checks passed 69 methods with zero skips. All six registered
lifecycle/native suites passed (4.37 seconds locally), and the final thirteen
ordinary completion contracts passed with captures. The final selected inventory
contains seven review-server invocations and exactly eight OS-verified native
drivers, versus seventy baseline starts: 62 fewer (88.6%) in this narrow metric.
All fourteen ordinary browser launches remain; contexts and logical cases are
unchanged. Explicit opt-in runs are additional qualification work.

Executable changes total -29 net physical lines across 23 paths, including three
new helper/regression files. Eight new regression methods and one new CTest
registration are charged; the extracted three native-profile cases remain. Existing
Chrome cold-start regressions and pilot sensitivity cases remain required. OS
inventory scans add work per selected fixture startup. These figures establish
neither a whole-CI speedup nor a 50% physical-code reduction.
