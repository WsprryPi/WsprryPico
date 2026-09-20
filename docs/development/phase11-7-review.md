# Phase 11.7 joint review and scoped Phase 11 closure

Date: 2026-09-20. WsprryPico owns this authoritative joint record. The
machine-readable companion is [phase11-7-result.json](phase11-7-result.json), and
the reproducible mutation assessment is
[phase11-7-adversarial-result.json](phase11-7-adversarial-result.json).

## Disposition

Phase 11.7 is closed. **Phase 11 closed within its documented software, bounded
physical and scoped conducted-RF acceptance.** The fresh host-test, sanitizer,
offline-audit and adversarial loops passed with the platform-specific skips
recorded below.

This review never broadens the accepted evidence. Phase 11 closure means the
documented software scope, the bounded inhibited-device scope, Phase 11.5 at its
recorded 138 MHz/divider-1 configuration and the explicitly reduced Phase 11.6
conducted-RF scope. It is not unrestricted RF qualification, current-device
inventory, acceptance of every supported mode/band/clock, interchangeability of
historical images or release readiness.

## Starting state and reviewed pair

Both repositories were clean on `devel` at the requested starting references:

| Repository | Starting revision | Tested revision | Role |
| --- | --- | --- | --- |
| WsprryPico | `10ea8210ba9bc1d2c50fa9b59bc16767af5c4200` | `95aac22bf7cc31b67fe5773761708d743d8a6473` | Server, firmware and closure authority |
| WsprryPi | `c39fae35a77afb0f9a1fbe741a4f1fbdf9cbdccf` | `2298a268d8139409ed650d2311d794b3813d99ab` | Client, application and network-management counterpart |

Pico's current interoperability gate pins Pi `c39fae35...`; Pi's canonical
Pico pin is `95aac22...`. This is a finite publication sequence, not a reciprocal
latest-HEAD cycle. Pi `2298a26...` differs from `c39fae35...` only in the
host-only interoperability CMake file and Pico pin. The actual WTP client,
backend, scheduler, status, application and transmitter-planning sources are
unchanged. Later Phase 11.7 commits may contain only closure documentation,
auditors, tests and test registration; the offline auditor rejects later
production-runtime drift.

The recorded current Pico A candidate remains source `0e85ff90571c800450073f7b0bfafd70266f1f44`,
UF2 SHA-256 `9ac5a40fe6d9a44a3a0156621b82801488efecafb9f472ba601dbcbb3e138398`,
boot `cab95d7eecad05047fcb1d6806cf9e86`, serial `0BF4B4AEC9FFB344`,
RP2350 Arm Secure, GP2 PIO/DMA, 138 MHz, divider 1 and RAM execution. Those are
recorded identities, not fresh observations. Between that candidate and the
tested Pico revision, the only `CMakeLists.txt`, `firmware`, `src` or `cmake`
changes are the two host interoperability CMake files and three Phase 11.6
host campaign/reconciliation modules. No linked firmware runtime input changed.

The recorded Phase 11.6 Pi companion remains source `c39fae35...` and binary
SHA-256 `b8e63947e2e9780f43dc4247869db138f81cc6e2245c99c1fd02ad9de4b33ff6`.
That identity is also historical, not a live service observation.

## Code and evidence review

The Pico review covered direct reserved browser payload assembly, measurement
before event allocation, the smaller status-read scratch gate with its retained
32 KiB reserve, uniform 32-character counting including spaces, full-job
3,600-second accounting including repetitions/gaps/tail, and the independent
512-event limit. It also covered immutable UTC-start reprojection, bounded
rescheduling without moving the launch deadline, and completion through the
inactive zero-tail/IRQ window. The completion path relies on authoritative
hardware inactive state; a delayed IRQ or a disconnect is not treated as proof
of inactivity.

The Pi review covered paced STATUS monitoring, terminal-event reconciliation,
cleanup-proof reuse, acknowledged RELEASE followed by an inactive successor,
bounded keyed plans with a final off event, QRSS/FSKCW/DFCW CLI and INI paths,
and finite managed WSPR iteration without changing other backends. Cleanup
requires matching job/device evidence, output inactive and no uncertainty or
safety fault. It does not abort a successor's job. Lost acknowledgements,
lease expiry, boot/device changes and disconnection retain output-unknown or
fail closed until authoritative evidence resolves them.

The historical evidence review retained original thresholds, failures,
dispositions, private-evidence references, source identities and hardware
charges. The immutable
[phase11-6-scope-disposition.json](phase11-6-scope-disposition.json),
[phase11-6-matrix.json](phase11-6-matrix.json),
[phase11-6-closure-execution.json](phase11-6-closure-execution.json) and
[phase11-6-closure-execution-results.json](phase11-6-closure-execution-results.json)
remain unchanged and hash-bound by the Phase 11.7 auditor. The same applies to
the Phase 11.5 [completion matrix](phase11-5-completion-matrix.json),
[Retry 4 result](phase11-5-package11-retry4-result.json) and
[adversarial record](phase11-5-package11-retry4-adversarial.json).

## Findings and bounded repairs

1. The reciprocal interoperability references described historical pairs, not
   the current software. Pico now pins Pi `c39fae35...`; Pi now pins Pico
   `95aac22...`. Both gates reject tracked and nonignored untracked source.
2. Pi's actual-Pico harness did not define the standalone WSPR base frequency
   required by current Pico scheduler source. It now compiles the same default
   `3570100` Hz value as Pico's normal host build.
3. Pico's host-client interoperability assertion still expected the old
   162-event/110.592-second profile. It now verifies the implemented independent
   limits of 512 events and 3,600 seconds.
4. Three Phase 11.5 checks compared historical publications to moving `HEAD`.
   Their reviewed source-impact assertions are now bound to the exact
   `3b8a6535...` Phase 11.6 browser-repair review cutoff. Current applicability
   is checked separately here. Immutable historical auditor hashes were not
   rewritten.
5. README and roadmap summaries mixed current closure state with older open
   checkpoints. Current summaries now point here; older narratives are clearly
   labeled historical rather than deleted.

No actionable defect was found in the reviewed runtime ownership, output
authority, allocation, timing or finite-plan implementations. The repairs above
affect interoperability metadata/tests and documentation, not the linked Pico
runtime or Pi production runtime. They therefore do not invalidate the retained
physical acceptance.

## Assertion-level applicability

The complete machine-readable ledger records owner, supporting artifact, exact
source/configuration, evidence type, subsequent relevant changes, applicability
and limitation for every slice. The disposition is:

| Slice | Owner | Disposition | Evidence boundary |
| --- | --- | --- | --- |
| 11.1 | WsprryPi | Applicable | Fresh actual shared server/client loopback plus historical software review; not physical qualification |
| 11.2 | WsprryPico | Applicable, bounded | Fresh regressions plus exact later 11.5/11.6 physical lineages; not unrestricted timing acceptance |
| 11.3 | Joint | Applicable, bounded | Fresh name/IP/mTLS/rotation/failure checks plus retained target records |
| 11.4 | WsprryPico | Applicable as recorded | Historical inhibited matrix and reviewed eight-hour soak at their exact identities |
| 11.5 | WsprryPico | Applicable, bounded | Closed 6/6 only at 138 MHz/divider 1/GP2 PIO-DMA/RAM/configured listener |
| 11.6 | WsprryPico | Applicable, scoped | Explicit user disposition over exact per-row conducted evidence |
| 11.7 | WsprryPico | Applicable, scoped | Current-source review, regression, reconciliation and two-pass adversarial audit |

## Phase 11.6 accepted scope

The disposition remains `CLOSED_SCOPED`: PASS 13, FAIL 9, BLOCKED 12,
NOT TESTED 31 and UNSUPPORTED_CONFIGURATION 10. No excluded row is promoted.
**No Phase 11.6 WSPR row is accepted.** Earlier independently decoded WSPR
evidence retains its historical scope only.

| Band | Accepted modes | Recorded lineage |
| --- | --- | --- |
| 2200 m | TONE, QRSS | `7068b937...`, boot `a12f61f7...` |
| 630 m | TONE, QRSS | `91933c00...`, boot `ff719d30...` |
| 630 m | FSKCW, DFCW | `91933c00...`, boot `d2f657c2...` |
| 160 m | TONE | `91933c00...`, boot `d2f657c2...` |
| 160 m | QRSS, DFCW | `2eaa9994...`, boot `b72fed2c...` |
| 80 m | TONE, DFCW | `210599d9...`, boot `be52153e...` |
| 60 m | TONE | `210599d9...`, boot `be52153e...` |
| 40 m | TONE | `210599d9...`, boot `e363bf9a...` |

The matrix retains the exact UF2 hashes, paths, sequences and failed attempts.
The 13 accepted rows are not attributed wholesale to the later `0e85ff9`
candidate. Repair requalification jobs do not earn matrix credit.

The final campaign stopped at sequence 177. Sequence 176 completed one
45.000001-second job; sequence 177 failed timing admission before RF. Eighty
jobs were not executed. The campaign authority is consumed and is not reusable.

## Fresh hardware-free validation

| Check | Result |
| --- | --- |
| Pico host CTest | PASS, all 79 groups across the corrected full-suite run and affected reruns |
| Pico WTP contract validator | PASS, 23 schema, 7 raw-JSON, 1 framing and 8 transition cases |
| Pico ASan/UBSan focus | PASS, 14/14 groups; Apple ASan leak detection unavailable as documented below |
| Pi WTP/application suites | PASS: 10,373 protocol; 946 vectors; 1 framing; 3 pins; 2,924 session; 2,644 USB; 1,088 plan; 1,937 frequency vectors; 5,410 backend; 1,514 scheduler; 3,804 status/recovery; 1,337 application; 223 production checks; UI suite passed |
| Pi portable semantics | PASS with `BACKENDS=simulated ANCILLARY_GPIO=0`; expected macOS `/proc/device-tree` diagnostics did not fail the suite |
| Pi HTTP/network policy | PASS, seven guard, policy, transaction, runtime, wiring and administration checks |
| Actual shared Pico/Pi loopback | PASS, 34 TLS cases and the complete current-server/client flow, including finite jobs, replay, ownership, boot/device mismatch and recovery |
| Pi ASan/UBSan focus | PASS, backend, scheduler, status/recovery, application, TLS and network-interoperability groups |
| Phase 11.7 offline audit | PASS, exact 13 rows, zero WSPR rows, immutable historical hashes and current source-pair bindings |
| Adversarial mutations | PASS, 33/33 rejected in each final assessment pass |

The repository-documented Pico configure/build/CTest sequence and
`python3 scripts/validate_wtp_contract.py` were used. Pi validation used the
documented WTP protocol/vector/session/USB/plan/backend/scheduler/status,
application, production, portable-semantics, TLS/network-interoperability and
HTTP/proxy policy targets. Focused sanitizer builds used isolated build
directories with `-fsanitize=address,undefined`.

The first Pico sanitizer invocation requested `detect_leaks=1`; Apple ASan
reported that leak detection is unsupported and aborted before running tests.
That tooling result is retained. The same 14 groups then passed with
`detect_leaks=0`; no leak-coverage claim is made. The Pi sanitizer run used the
same documented platform limitation.

One consolidated CTest invocation omitted the explicit Xcode 26.5 SDK: 76
groups passed and three compile-in-test groups failed against the malformed
CommandLineTools macOS 27 SDK. With the validated SDK, those three passed; that
sandboxed run then denied two loopback listener starts. Both affected TLS groups
passed outside sandbox socket restrictions with the same validated SDK. These
failed invocations are retained as tooling/environment results rather than
hidden or represented as product failures.

The host cannot bind the test's second IPv4 loopback address, so that one
actual rebind case is `SKIPPED_HOST_UNAVAILABLE`; the injected-address contract
and named/explicit-IP actual TLS paths passed. Linker warnings in the portable
semantics target identified pre-existing cached objects built against macOS 27
while linking with the macOS 26.5 SDK; the isolated WTP and sanitizer builds
were clean and passed. No result is represented as CI, target-timing or RF
qualification.

All fixtures were loopback, synthetic, PTY or ephemeral-credential fixtures.
No test in this review contacted a physical Pico, transmitter or fixture.

## Adversarial assessment

The first post-repair assessment challenged unsupported PASS labels, row/count
drift, WSPR promotion, lineage rebinding, stale pins, consumed authority reuse,
historical hash drift, host-as-target claims, disconnect-as-inactive claims,
silent operator-documentation completion, hardware activity, remote-CI claims
and premature Phase 12/13 closure. All 33 mutations were rejected. A manual
diff and claim review found no runtime or evidence-binding defect. The first
affected closure-test run found that the prose named but did not directly link
the Phase 11.5 completion matrix; the link was added. After that repair and
final record reconciliation, the same 33-mutation assessment and affected
closure checks passed again. The final staged review then found a machine-local
absolute path in the external-documentation record; it was replaced with the
repository name and the affected checks were repeated. The final
machine-readable result is
[phase11-7-adversarial-result.json](phase11-7-adversarial-result.json).

## Operator-documentation follow-up

The `Wsprry_Pi_Docs` repository was inspected read-only on clean `devel` at
`c4cfc4ac9908adcc40a53702bb38803700b8a92e`. Phase 11.7 did not modify it.
The following are nonblocking publication follow-ups, not silently completed
dependencies:

- `docs/Advanced_Operations/ini_configuration/transmitter_backends.md`: network
  keys, protected credentials, rotation and DHCP/mDNS prerequisites.
- `docs/Command_Line_Operations/transmitter_backends.md`: replace USB-only Pico
  guidance with explicit transport selection and bounded finite jobs.
- `docs/User_Interface/Setup/Transmitter/index.md`: network selection, configured
  versus authenticated identity and management readiness.
- `docs/User_Interface/Operations/index.md`: cancellation, output-unknown state
  and explicit reconciliation.
- `docs/Advanced_Operations/rest_api.md`: shared resources, revisions, intent,
  replay and idle-management boundaries.
- `docs/User_Interface/Maintenance/network_safety.md`: retain the existing guard
  policy and add a Pico management cross-link.

## Remaining work and operational statement

Phase 12 remains open for SoftAP/BLE and provisioning. Phase 13 remains open for
the systematic band × mode × clock comparison, final supported configurations,
calibrated timing, spectra, output network/filters, final reliability and a
reproducible release UF2. Selecting another clock requires repeating affected
11.5 checks before acceptance at that clock.

This task performed **no hardware or RF operations**: no flash, reboot, BOOTSEL,
debugger, USB/device control, GPIO, physical endpoint, fixture, service, route,
radio, certificate/trust-store or transmitter operation occurred.
