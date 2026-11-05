# Phase 04 Qualify the session browser pilot

Execute only phase 04 when explicitly invoked. Read the complete
[shared execution contract](README.md#shared-execution-contract),
[orientation](orientation.md), and accepted phase 01/02/03 evidence. Phase 03's
owned-process interfaces and affected checks must be accepted first. This is one
representative production-handler browser suite, not the phase 05 migration.

## Objective and scope

Update tests/session_timeout_browser.mjs and the minimum shared UI fixture
selection needed to run its one profile. Reuse the current chrome_startup,
browser_deadline, fixture_process, and ui_process_cleanup implementations instead
of introducing another independent startup loop. Inspect consumer_sessions.test,
ui_review_fixture, actual shipped session client/page, and every existing fixture
server caller before extending the test-only interface.

## Work

1. Freeze the pilot's existing assertions and context: shipped page and real
   HTTP/AEAD handlers, synthetic board and clock, idle versus absolute expiry,
   nonrenewing public/edit activity, preserved drafts, locked writes, explicit
   readback/review after login, and no unauthorized mutations. Preserve source
   timing semantics; the current 30-minute/eight-hour boundaries are historical
   values to verify, not permission to change product policy.
2. Design explicit selection of named UI fixture definitions. Validate the entire
   selection before spawning; refuse unknown, duplicate, empty, malformed, or
   conflicting selections. Keep original definition identity, authority, profile,
   and port-offset mapping even when intervening definitions are not instantiated.
   Preserve current all-profile opt-in behavior when selection is omitted unless
   a caller audit justifies an explicit coordinated interface change.
3. Request only the pilot's consumer profile. Do not simplify its handlers or
   crypto, instantiate an older fixture, change a carrier, or remove a scenario.
   The ten-to-one driver-start target concerns unused active orchestration, not
   deletion of nine tests. Keep all maintained definitions available elsewhere.
4. Replace separate wall-clock startup/polling and CDP timers with observed
   readiness and propagated monotonic phase budgets. Bound discovery-file reads,
   DevTools fetch/body parsing, WebSocket opening, CDP requests, fixture HTTP
   controls, and finalization. Handle early process/socket exit, reordered replies,
   cancellation, and late success. Retain stage-specific diagnostics and finite
   real watchdogs when either browser or device time is controlled.
5. Adopt phase 03 ownership before fallible initialization; retain primary and
   cleanup errors, and confirm all writers stop before profile removal. If shared
   CDP extraction is necessary, charge moved code, new helpers, caller glue, and
   regressions; importing a helper must not launch another suite as a side effect.

## Validation and adversarial assessment

Prove selected startup count and actual profile routing. Test invalid selections
before any child starts, partial initialization failure, delayed readiness,
partial discovery, stalled fetch/body/socket, malformed replies, early/late exit,
and cleanup denial. Observe fault state before advancing clocks. Deliberately
break expiry, draft preservation, and mutation refusal at bounded seams, and
show the original obligations still detect each defect; restore the candidate
after every sensitivity experiment. Never mutate credentials or physical boards.
Use observed child ownership and handler identity for counts/routing; a selected
name echoed by the wrapper is not evidence that the intended handler executed.

Run the actual pilot, all affected shared-helper/server callers, existing cold
startup and cleanup regressions, and both production network and USB suites on
the intended pair. Compare equivalent source/toolchain/context runs and count
added regression starts separately; ten-to-one is not a whole-CI speedup.
Adversarially review, fix, rerun affected checks, and reassess.

## Acceptance and handoff

Provide the before/after obligation map, startup counts, helper/interface contract,
source-pair results, sensitivity evidence, net code/file/process costs, and timing
limitations. All pilot assertions and original opt-in contexts must remain.
Document the accepted migration pattern and known exceptions for phase 05;
update phase 04 execution status only after required checks pass, then stop.
