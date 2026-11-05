# Phase 05 lifecycle adoption results

The [caller matrix](../software-build-ci.md#native-scenario-obligations) reconciles all eleven maintained native
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

## Source-pair acceptance

Both complete production recipes passed with committed Pico
540dc6bdbff6edfae54e9e933809520886dcf90e and selected Pi
1e15b2485ac6e1b9cbb6ff435afc0f0232528804, recursive MbedTLS
0bebf8b8c7f07abe3571ded48a11aa907a1ffb20. The candidate tree was clean;
no uncommitted input was tested in the pair acceptance run. The actual
usb_management_driver was confirmed current at that commit before its pair ran.

Commands follow the explicit phase 03 recipe: network-runtime-test (916 checks),
wtp-network-interop-test, wtp-config-interop-test, wtp-usb-pair-client-build,
wtp-usb-management-test, wtp_usb_settings_test.js, and wtp_usb_pair_test.js with
WSPRRYPI_GPIO_DRIVE_REQUIRED=1. The network runtime target's full name is
wtp-network-runtime-test; PICO_SOURCE, MBEDTLS_SOURCE, and native build selection
were explicit. Ignored build/campaign-phase05-network.log and
campaign-phase05-usb.log retain complete output. Hardware access was disabled;
these results do not qualify physical USB, installation, timing, or RF.

[Canonical phase 05 run](https://github.com/WsprryPi/WsprryPico/actions/runs/42086214552)
completed successfully after local acceptance. Its actual GitHub merge source
1ba1de9e23b8a1d0954b793d62b561d475716896 has parents c9fd28ef and
540dc6bd, checked through the commit API. Audit artifact 13445680442 and
firmware artifact 13443683497 were produced. Independent verification accepted
all 28 receipts, exact log digests, completion facts, and all 226 registered
CTest suites without failures or skips. Aggregate command elapsed was
1261.781 seconds; no causal whole-CI speed claim is made.
The prior phase 04 canonical run is independently verified in its result record.
Final reassessment found no remaining actionable migration finding. Phase 06 owns
the documented TLS synchronization and hostname timer work; phase 07 owns inner
CTest framework discovery/skip qualification. Phase 09 owns scheduling. No merge,
release, deployment, or product timing change was performed.
