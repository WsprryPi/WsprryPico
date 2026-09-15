# Memory-pressure repair review

## Reviewed cause and repair

The [execution prompt](phase11-5-memory-pressure-prompt.md) records the current
capabilities, recent repairs, failed P1i workload and frozen acceptance rules.
The original event list remains allocated beside the independently prepared RF
plan during Armed/Running. It occupies 20,480 bytes for 512 events on RP2350.
P1i's recorded shortfall was 7,248 bytes. This source finding identifies removable
overlap; it does not establish the exact cause of every monitoring timeout.

The engine interface now defaults to retaining input. StreamEngine advertises
an independent execution plan. WorkerEngine captures that immutable capability
before worker startup, and its synchronous schedule call clears the borrowed
input pointer before returning. JobService releases only its event vector after
acknowledged successful local schedule or foreground begin. Identity, duration,
original typed digest and adjustment replies remain. Failed handoff does not
release the input. Default adapters keep the prior lifetime.

The original digest is saved after successful LOAD validation/preparation. LOAD
conflict checks and terminal history use that digest after event release.
Retention counts, expiry, ownership and replay precedence are unchanged.

WTP input admission separately budgets 8,192 temporary bytes plus 1,024 bytes
for page bookkeeping/parser storage, above the unchanged 32,768-byte reserve.
INFO formatting and small-request decoding are serialized on core 0. This
provision exceeds the approximately 8.5 KB observed transient allocation above
the pre-format snapshot; it is a bounded allowance, not a proof for arbitrary
additional clients. Maximum message limits and five-second deadlines remain.

RF plans, renderer, launch guard, refill loops and clock are unchanged. Releasing
memory and storing digests changes allocation/lifetime and foreground work;
current-candidate resource and timing acceptance requires affected target tests.

## Host validation and adversarial assessment

- The handoff matrix checks local/foreground launch, borrowed/owned input,
  completion, abort, uncertain stop and rejected handoff. It verifies actual
  allocation release, cached/fresh/compact LOAD replay, changed-event conflicts,
  ARM replay and replacement jobs.
- The actual StreamEngine produces identical complete output checksums with
  the caller's 512-event job retained or destroyed before subsequent refills;
  execution allocates no additional memory in that test.
- The endpoint/service/stream allocation model handles maximum STATUS and its
  replay during simulated Running with retained history and a 39,576-byte
  background, including 8,192 diagnostic bytes. Every measured exchange retains
  at least 32,768 bytes. This is a host model, not target RF evidence.
- Input admission tests reject both insufficient workspace and size overflow;
  exact maximum bytes still pass with sufficient budget. Existing page-failure,
  framing/CRC, output pressure and reconnect checks remain.
- Stronger admission moves two pressure refusals before decoding. Their tests
  now require immediate closure. Separate endpoint tests introduce competition
  after input admission and retain original 4.999/5.000-second recovery/expiry
  assertions. No timeout or reserve was relaxed.
- Broad regression exposed an outdated synthetic HTTP serializer fixture.
  Rebuilding it with current HTTP paging and browser assets preserves its JSON
  body and status semantics; only CSP asset hashes change. Provenance and bytes
  were regenerated together rather than editing a hash to suppress the failure.
- All 72 configured CTest groups pass across the broad run and affected reruns,
  including local TLS (11.32 seconds). The R3 group runs 228 cases with 48
  private-evidence skips. Twelve reservation/deployment/gate checks pass; RF
  packet checks pass 14 cases with one private-evidence skip.
- Three separately compiled source mutations are rejected: retain the execution
  vector, recompute terminal digest after release, or omit temporary input
  workspace. The intact core binary passes again after those negative checks.

The reviewed five pre-existing helper changes pin the earlier 150fe01 deployment,
native-idlek scope and P1i packet. They do not grant acceptance to P1i or modify
its frozen executed helper copies. The prior finite fixture reports restored,
with no cleanup failures and its protected host snapshot matching its baseline.

At this source checkpoint, no actionable host repair finding remains. Both
linked-image verification and the retained-workload target retest are pending;
Phase 11.5 remains OPEN, with R1/R2 closed only within their recorded scope.
The new source has not yet been flashed at this checkpoint.


## Target outcome and final adversarial reassessment

The [immutable result](phase11-5-memory-pressure-result.json) records clean source
8dd6f0812292e9264c2a72745078a95ee606c191, linked-image checks and the exact
physical UF2/ELF hashes. Both inhibited and physical image layout, heap hooks
and guarded-stack checks pass. The physical RAM renderer remains 660 bytes /
233 checked instructions.

A was flashed once and independently identified at boot
7a04779b8018624574066260fce9d0d8. The first native packet failed its 90-second
network-readiness gate before any LOAD or RF. One separately frozen, justified
OFF/ON cycle recovered its address and clock on the same boot; configuration
was preserved. The failed readiness packet remains recorded with no capacity
credit.

The next packet passed three maximum 512-event LOADs and a fresh-ID replay,
with all four complete replies in 2.04–2.43 seconds. One native TLS connection
remained continuous through the 90-second retained-load observation. Three
Aborted terminal records were independently identified before the RF packet.

The 128-second, 512-event FSKCW job then completed under independent USB INFO,
WTP and native observation. The maximum 65,536-byte WTP payload was completely
written and answered; 65,537 bytes were rejected with same-connection recovery.
The valid 32,768-byte HTTP body returned 200. A declared 32,769-byte body was
rejected at its header with 400, followed by successful authenticated recovery.
The WTP and HTTP capacity exchanges were sequential and overlapped Running;
this does not qualify simultaneous maximum inputs.

The independent raw auditor verifies RF launch/refill/tail counters and timing,
207 INFO samples with a maximum 1.840-second start gap, and one native TLS
connection with 216 STATUS requests. It checks complete writes, responses,
CRC/schema, active RF overlap, original peer/image/boot, exact three retained
seed identities, final ownership/configuration and reservation release.

The same-boot sticky allocator peak is 162,992 bytes against 218,936 bytes of
heap: at least **55,944 bytes remain**, exceeding the unchanged 32,768-byte
reserve by 23,176 bytes. This peak includes the preceding idle test. It is a
conservative bound for this boot, not an instantaneous RF allocation or a
matched-state subtraction from the failed image. No allocator/TLS failure,
watchdog, stack guard failure or engine fault was accepted.

Adversarial review identified that the independent RF auditor previously checked
only retained-record count while the runner checked exact identities. The
auditor now also requires the frozen ordered IDs and inactive Aborted states.
Four altered native evidence sets (write, continuity, peak and publication) and
four altered RF sets (write, HTTP response, native continuity and reservation)
are rejected; intact evidence passes again after each assessment. The final
R3 helper regression passes in 21.01 seconds. The three source mutations listed
above also fail as intended. No actionable issue remains in this repair slice.

The isolated host fixture is restored and independently matches its original
host snapshot, including installed WsprryPi PID 1957. Fresh raw A/B inventories
prove both Empty, inactive, unowned, schedules disabled and configurations
preserved; their boots remain unchanged after the test. The shared RF
reservation is released. This repair used one A flash/BOOTSEL, one justified
Wi-Fi cycle and one 128-second RF job, with no configuration writes or additional
controlled reboot. Cumulative completion charges are seven RF jobs / 896 planned
seconds, nine A flashes/BOOTSEL transitions and three Wi-Fi cycles. The original
P1h unplanned watchdog remains separately recorded.

P1's five affected capacity assertions and authenticated positive controls now
pass on 8dd6f08. P1i's failed evidence is retained. R1/R2 keep their original
scope; R3–R6 and full configuration acceptance remain OPEN. The current matrix
keeps simultaneous load, overload, timeout/USB pressure, retained capacity and
three equivalent reclamation cycles as separate unfinished work.
