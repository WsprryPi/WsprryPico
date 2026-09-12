# R3 A1 TLS/slot preparation review — September 12, 2026

**Historical packet/preparation record:** the user approved this packet and it
[failed before RF submission, then restored successfully](phase11-5-r3-tls-failure-review.md).
The packet is consumed; CONFIG is now 36/36. Do not replay it. The preparation
assessment below missed the documented observer-shape defect.

The [next concrete execution packet](phase11-5-r3-tls-execution.md) is prepared.
R3 A1 now has an executor, pressure driver, independent observer integration,
offline audit, staging helper and deterministic tests. **No A1 hardware run or
new staging has occurred.** Phase 11.5 remains **OPEN, 2/6 families closed**;
R1 remains 5/5, R2 remains 7/7, R3 has zero accepted physical assertions and the
accepted-configuration list is empty. P0 remains complete at four read-only
captures; its grant is consumed. CONFIG remains 34/34 and probes six.

Preparation started on clean `devel`: Pico
`fc6a4660544d84abe0b2f3d2f11c2cf92f08ac5a`, Pi
`d44c20af942cbbec3775c8122440b710a9d7aa19`. These are starting checkout identities,
not new publication commits or firmware revisions.

## Implemented scope

A1 has two separately identified 100-second USB-owned Tone jobs at 135,500 Hz.
It covers fresh authenticated HTTPS controls, missing-client-certificate alert
116, silent-handshake timeout plus the target timeout counter, supported and
pending slots with bounded excess rejection, duplicate WTP closure after a
verified handshake, and a fresh HTTPS recovery after each trigger. All triggers
and recoveries require independent owned Running RF evidence.

The actual production WsprryPi client runs RF-off for 300 seconds on its existing
pinned executable and holds one WTP connection/session. Its plaintext TLS audit
retains the accepted single-flight administrative cadence and five-second
transaction bound. The ordinary browser workload is off: the pressure driver
owns its six explicit HTTPS controls. The retained internal `browser_profile=N`
field selects existing helper semantics but does not claim a normal browser run.
INFO/STATUS/host observation lasts 360 seconds. Pressure sends twelve TCP
connections; one missing-certificate attempt is expected to fail with a precise
target alert, and deliberate excess admission must reject without allocator
failure. No connection retry or native controller reconnect can pass.

A new schema explicitly selects the existing sole-endpoint USB actor and raw
observer/auditor. It gates the first job on pressure readiness and the second
on a packet-bound successful first pressure result. The shared finite-job audit
accepts an explicit validator argument; its default remains the old R2 validator.
This preserves R2 scope, request sequencing and acceptance defaults.

The new management scope carries counts 34→36. It allows only one isolated-network
setup CONFIG and the original CONFIG restoration. It rejects heap probes, Wi-Fi
cycling, schedule variants, unknown writes and expanded counts. The prior R2
2e43110 allowance remains capped at 34. The device fixture checks the prior
restored evidence and all operation counts; no old timer, packet or result root
is replayed. Device and host cleanup remain independently owned and bounded.

The single-use stager verifies archive membership, every staged hash and all
nine existing private input hashes before creating its new root. It rejects
traversal, links, duplicate members, changed inputs and an existing root. It
copies no private key off wspr5 and performs no fixture/device operation.

## Evidence reviewed and impact

Read-only SSH verified the existing private input hashes and host boot. The
RF-off INI was read into ignored local preparation storage and its credential
paths were rewritten to the proposed new root. No USB port, service, network
configuration or RF state was changed during this preparation. The most recent
board identity evidence remains [P0](phase11-5-r3-preflight-review.md); initial
A/B identities must be freshly re-established during authorized admission.

`git diff 2e43110 -- src firmware` is empty. Both pinned UF2 files were checked
against the existing [build record](phase11-5-r2-upload-builds.json). No firmware
rebuild is needed. The 110.592-second cap remains global and affects QRSS too;
A1 uses bounded jobs on that candidate. An expanded QRSS duration/event envelope
is still an unresolved product proposal, with no new duration chosen.

| Change | Invalidated assertions | Applicable evidence | Targeted verification |
| --- | --- | --- | --- |
| New R3 schema, pressure driver and audit | None of R1/R2; new R3 assertions have no existing physical credit | Pinned image, prior resource/stack bounds, existing WTP/TLS semantics | Frozen-job/CAPS tests, response framing, target alert/counters, independent RF overlap and failures |
| Explicit R3 observer/USB selection and finite-audit validator | No firmware assertion; helper changes need regression validation | Original R2 defaults and amended cadence remain distinct | Existing R2 tests plus a fresh offline audit of preserved 2e43110 three-job evidence |
| Specific CONFIG 34→36 scope and new-root stager | No prior physical assertion; no authority granted by source fields | Previous counters, original image/config, independent restoration ownership | Old-cap exhaustion, new-cap reserve, unsupported-operation/unknown-write rejection, staging mutation tests |
| Documentation and prepared packet | None | P0 4/4, R1 5/5, R2 7/7 and all failures remain unchanged | Link/JSON/hash/whitespace review and full local archive/manifest validation |

## Adversarial assessment and checks

The first review found that target recovery-counter checks were initially only
offline. They now also gate the live driver before first-job success can admit
another job. The review also tightened recovery timing to include cleanup delay
within fifteen seconds from the preceding trigger, preserved the distinction
between target certificate alerts and EOF, and made a final cumulative-count
failure prevent successful restoration reporting.

The next assessment checked new-schema dispatch, unchanged old defaults,
private helper identity sets, source-bound slot/timeout counters, RF overlap,
process identity/freshness, job gates, finite ownership/release, terminal history,
restoration limits and replay refusal. A pending socket may be promoted during
client teardown; admission delta two or three is recorded for that one case.
It is never labeled pending expiry or a deterministic internal ordering.

Validation performed:

- `python3 -m unittest discover -s tests -p '*phase11_5*tests.py' -v`:
  **169 discovered, 167 passed, two private-fixture tests skipped** because their
  opt-in fixture environment variables were not supplied.
- The twelve new R3 tests include fourteen corrupted pressure-evidence cases,
  six observer identity/freshness/state mutations, exact missing-certificate
  alert handling, malformed HTTP framing, exact CAPS/jobs, old/new write limits,
  pressure-gated USB submission, no-run behavior and staging integrity/replay.
  Intact synthetic evidence passes again after mutations.
- The modified common helpers freshly re-audited preserved R2 2e43110 USB
  FSKCW/DFCW/WSPR evidence: **PASS, three jobs** with the separately accepted
  `single-flight-admin-v1` policy. Read-only path mapping located the copied
  evidence without rewriting its packet or raw bytes. Historical strict-gap
  failure remains preserved.
- Pi: `python3 src/tests/phase115_production_load_tests.py`: **12 passed**.
  The staged RF-off INI also passed the production helper's existing validator.
- Full staged helper manifests, archive member set, image/source hashes, JSON,
  relative links and `git diff --check` passed. C++ tests were not repeated:
  firmware, portable C++ implementation and Pi production implementation did
  not change.

The final bounded source assessment found no remaining actionable defect in
this prepared A1 tooling. These are deterministic/source/evidence-replay checks,
not a claim that the new live executor or target pressure assertions have passed.
Hardware execution, restoration verification and raw-evidence audit remain the
next required acceptance steps after approval.

## Remaining R3 work

A1 is a subset of the TLS/slot tranche. It does not close R3, even if execution
passes. Still required: other distinct failed TLS lifetimes and alert-wait paths,
pending expiry, partial HTTP headers/bodies, stalled reader/writer progress,
CAPS maximum valid allocation, WTP/HTTP/browser boundaries, USB pressure,
replay/terminal/session capacity and expiry, ordinary reuse, and three equivalent
reclamation cycles of the measured highest-resource path. R4–R6 remain unrun.
Do not infer the highest-resource path from this preparation.

## Documentation Impact

Updated: this review, the concrete execution packet and prepared result, current
Pico ledger/index and Pi companion report. Considered unchanged: WTP/browser API
contracts, firmware and Pi production implementation, operator UI and historical
results. No UI or UI-depicting documentation changed, so no Impeccable workflow
applies. Separate operator manuals remain outside the authorized repositories;
the follow-up paths already listed in the Phase 11.5 plan still require measured
accepted limits. Longer QRSS documentation requires a resolved duration envelope.
