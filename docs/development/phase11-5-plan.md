# Phase 11.5 target resources and contention

Status: **OPEN; 1 of 6 acceptance families closed (R1: 5 of 5 assertions).** This
September 12, 2026 documentation revision supersedes the execution organization
of the [preserved original plan](phase11-5-plan-legacy.md). It does not supersede
old measurements, failed limits or evidence identities. The [current ledger](phase11-5-acceptance-ledger.md)
is authoritative for readiness; the old [JSON register](phase11-5-register.json)
and its 20-case validator remain unchanged historical tools, not a six-family
closure mechanism. The [reorganization prompt](phase11-5-test-reorganization-prompt.md)
and [review](phase11-5-test-reorganization-review.md) record this documentation-only change.

No runner, test, validator, firmware, protocol or operational configuration was
changed by that documentation revision. The subsequent [R1 execution](phase11-5-r1-review.md)
closes R1 for the exact e20ae8b physical 138 MHz/divider-1/RAM/listener-on
configuration, while preserving the earlier failed attempts. The later
[049cc929 amended campaign](phase11-5-r2-amended-review.md) also closes R1 5/5
and passes three Tone jobs; R2 is 3/7 jobs complete. R2–R6 remain open.
No hardware execution is authorized by this document. Future packets
must reconcile available tools with this plan before obtaining any missing
bounded hardware/network authority. Old supervisors must not be run under new
labels or modified implicitly to implement this plan.

## Purpose and intended use

Accept the resource and contention envelope of an exact Pico 2 W / RP2350
firmware and selected clock while it performs complete local RF jobs. The
product operates autonomously from saved schedules, as the real WsprryPi
backend, and through direct browser or USB control. RF timing never depends on
per-symbol network/USB delivery. A useful acceptance test establishes that these
paths coexist, reject unsupported load safely and recover without duplicate
transmission, owner loss, false inactivity or resource exhaustion.

Phase 11.4 already established bounded inhibited protocol, certificate and
network behavior. Reuse that evidence for unchanged semantic requirements after
source-impact review; it does not prove physical RF contention on another image.
Prior [certificate](phase11-4-f2-f3-f6-results.md), [lost-response/recovery](phase11-4-g4-g7-results.md)
and [discovery](phase11-4-three-radio-results.md) records remain relevant. Repeat
the changed path and its physical interaction, not the entire earlier matrix.

## Clock acceptance ownership

- **11.5:** memory, both stacks, refill/launch/tail timing and contention at each
  selected PIO clock, bound to actual image, board, boot and clock.
- **11.6:** per-band/per-mode conducted RF at those selected clocks. A newly
  selected clock requires the affected 11.5 checks before acceptance.
- **13:** systematic band × mode × clock comparison, filters, spectra, final
  supported configurations and release firmware.

| Physical PIO clock | Selection | Accepted configuration |
| --- | --- | --- |
| 138 MHz | Selected candidate for 11.6 | None; resource/contention gates open |
| 132 MHz | Not selected | Untested in physical 11.5 |
| 150 MHz | Not selected | Untested in physical 11.5; inhibited evidence is separate |

The current candidate is `e20ae8bea2d5237af017dbd5f73bfe9332ce144e`, divider 1,
RAM renderer, with exact images in the [repair result](phase11-5-status-delivery-result.json).
Its 138 MHz nominal RF-idle diagnostic passed; TX credit-wait/preservation
counters stayed zero. It neither qualifies active RF nor establishes the cause
of historical STATUS stalls. Freeze this candidate unless a demonstrated defect
requires a change. Documentation-only commits do not change its firmware identity.

A full 16,384-word block represents 524,288 samples. Its interval is
3,799,188.406 ns at 138 MHz; the existing conservative 75% execution budget is
2,849,391 ns. Every short predecessor uses its own `words × 32 / clock` interval.
Recalculate all budgets for any newly tested clock. 132/150 MHz calculations are
not evidence of testing those clocks. Preserve the [metric definitions](phase11-5-metrics.md):
IRQ entry is not hardware completion, cumulative maxima are not independent
summable intervals, and microsecond samples do not prove nanosecond precision.

## Workload profiles and pass rules

The following profiles are prospective test definitions, not changes to product
behavior or claims of measured capacity. Each executable packet must freeze its
exact action list, timestamps/durations, principal/client count, job bytes,
transport, rates, repetition count, expected outcomes and cleanup before running.
Missing definitions mean NOT READY, not permission to improvise during a run.

| Profile | Purpose and required distinction |
| --- | --- |
| N — normal operation | Real WsprryPi policy with one persistent logical session, plus one sequential browser operator. Load the actual page and its API initialization, perform status/control actions, and reload once during a long job. For a 300-second browser interval, include at least six explicit Refresh actions distributed across the interval; shorter job intervals must still include interaction while Armed/Running. Freeze the action schedule without silently skipping late actions. |
| S — declared stress | Repeated fresh HTTPS, periodic polling, direct asset requests and connection churn beyond N. The old N workload (0.2 Hz HTTPS status, page plus separate CSS/JS every 30 seconds) belongs here. Preserve its original counts, one-second browser lateness limit and old results when repeating it. A stress profile claimed as supported must satisfy its declared service criteria. |
| O — deliberate overload | Invalid credentials/input, slow or excess clients, capacity boundaries and unread outputs. Expected bounded rejection is permissible only for predeclared unsupported load. The supported owner, RF engine and recovery path must remain correct. Never relabel a nominal failure as overload after observing it. |
| M — measurement | Independent USB/network/host evidence with measured cost and no hidden client/session churn. Retain current INFO at 1 Hz and USB STATUS/health at 0.2 Hz where used; a future lower-overhead method needs prior validation and explicit coverage, not missing observations relabeled as success. |

Source inspection shows [asset generation](../../scripts/generate_web_assets.py)
embeds CSS/JS into `/`; [the browser](../../src/network/web/app.js) refreshes on
initialization/operator actions and has a separate restart-recovery loop. Direct
CSS/JS endpoint checks remain useful, but separately fetching them on every page
reload is additional stress. N must include the page's capabilities/status/config
initialization, not just a synthetic status GET. Do not change browser code here.

Keep persistent authenticated STATUS/abort confirmation within 5 seconds and
fresh HTTPS requests including handshake within 15 seconds. These are campaign
service targets; authoritative output-disable requirements remain separate and
unchanged. Record whole user-action latency as well as each constituent request.

Keep the 1 Hz offered idle-controller profile's at-least `seconds − 2` requests
and maximum 2-second request-start gap. Future-start scheduler waits have a
different existing policy (the reviewed Pi path sends five-second keepalives);
freeze and verify the actual source-bound state policy rather than imposing
idle cadence on every state. A packet must state the maximum permitted start gap
for each such state before execution; unknown state-specific limits block that
packet. Report native write-start response latency separately from scheduling
latency. N has no invented automatic browser poller or one-second browser
freshness promise. Its predeclared actions and per-request deadlines still must
complete; S retains its distinct cadence criteria. Earlier failures keep their
original classifications and do not become passes under N.

## Six acceptance families

Each family contains independently scored subcases. A shared run can cover
several assertions only when its predeclared evidence actually observes each;
a representative case cannot erase a distinct resource or failure path.

| Family | Required coverage and reason | Completion evidence |
| --- | --- | --- |
| R1 — resources and baseline | Four network off/on × inhibited/physical linked layouts; current physical idle, controller-only and N comparisons; short inhibited regression for changed shared paths. | Exact allocator/layout/stack/flash identities, valid guards, measured observer cost and comparable before/after resource state. Reuse unchanged build evidence after identity review. Full inhibited repetition is required only where change impact or diagnosis justifies it. |
| R2 — normal RF execution | Complete Tone, QRSS, FSKCW, DFCW and WSPR jobs at 138 MHz with N/M; Loaded/Armed/Running transitions, sustained refill, full and short predecessors, launch and zero tail. Include actual production-owned, browser-owned and USB-reference submission paths across the campaign; ownership is sequential, never concurrent. | Start with three complete finite Tone jobs, then one complete job in each of the other four modes: seven jobs minimum. Cover each distinct timing path and exact job/epoch; repeat the measured demanding paths through R6. Generic mode equivalence needs source evidence; a missing path remains open. No band sweep or independent RF decode here. |
| R3 — saturation and reclamation | Valid/failed TLS lifetimes, slow handshake, partial HTTP header/body, stalled reader/writer, slot overflow, maximum valid jobs/frames/bodies, USB pressure and retained-state capacity. | Distinguish each timeout/allocation/slot/parser path, bounded classified rejection and authenticated recovery. One complete trigger/recovery per distinct path, then three equal-state reclamation cycles of the representative highest-resource path. Increase repetitions only for an identified mechanism or unresolved intermittent result; this is finite evidence, not a reliability probability. |
| R4 — authority and interruption | Foreign CLAIM/ABORT/RELEASE and forbidden writes while owned, owner abort Armed/Running, disconnect after ARM and lost LOAD/ARM/ABORT replies. | Preserve state/owner/replay precedence, no forbidden flash write, no duplicate execution, local completion through transport loss and authoritative reconciliation. Cover browser and production owner aborts in both Armed and Running at least once each; cover each lost-operation class once, with correct same-session replay. Retain distinct TCP reset/EOF and resolver-failure assertions through targeted current regressions or reviewed unchanged prior evidence. |
| R5 — network, storage and autonomous lifecycle | External link loss during a finite RF job, a lease/address change with certified name recovery, idle Wi-Fi OFF/ON, config persistence and journal rotation, DNS/SNTP competition and an actual standalone-scheduled job. | One bounded cycle per distinct lifecycle; normal service restored with correct identity/config/watermark. A saved autonomous schedule must actually trigger preparation and complete local RF while N/M compete; external LOAD is not a substitute. Cover time-validity admission without assuming PPS or SDR frequency calibration. Restore disabled schedules and original config under the shared write budget. |
| R6 — sustained mixed operation | After R1-R5 pass, 30 cumulative minutes of N with finite jobs totaling at most 20 minutes RF, plus interleaved quiet observations and final equivalent quiet comparison. | At least three comparable post-warm-up resource windows and repeated demanding launches. Zero unexplained reset/corruption/deadlock/DMA/TXSTALL/owner error; no monotonic retained growth across the three windows and difference within 1,024 bytes of the matched post-cache baseline. This is not another eight-hour idle soak or release reliability qualification. |

R3 target boundary work must include the CAPS maximum valid finite job, individual
advertised WTP 65,536-byte payload and HTTP 32,768-byte body limits, and an
explicitly unsupported simultaneous combination if it exceeds admission capacity.
These transport bounds do not promise that every JSON body is a valid job or
that all individual maxima fit together. Browser file admission is narrower;
exercise that real limit through the browser path. Keep rejection at the intended
layer. Test retained terminal, replay and session limits from current source/CAPS
(the legacy values were 8 terminal records, 8 replay entries/session and 16
sessions). Distinguish ordinary session reuse from intentional exhaustion.

Run the network/USB saturation and reclamation cases while the physical RF
worker executes a predeclared finite job, not solely on an idle or inhibited
image. Where a mutation is forbidden during ownership, establish its valid
capacity/admission result while idle first, then exercise the permitted competing
traffic under RF. An expected BUSY response cannot prove maximum-job allocation
or capacity. Destructive allocation probes remain idle-only; distinguish their
evidence from actual under-RF high-water/continuity observations.

For failed TLS paths, retain a current valid positive control and one negative
per distinct target handshake/reclamation path. Exhaustive wrong CA/name/client
semantic combinations remain in the referenced functional evidence/regressions;
20 repeats of each are no longer a separate physical 11.5 gate. Wrong server-name
validation at the client is not interchangeable with target-side client-certificate
rejection. Slow handshake/header/body/read/write cases are not interchangeable.
Retain the existing relevant 10/15/30-second deadline plus 2 seconds observation
allowance, and fresh authenticated recovery within 15 seconds after reclamation.
An expected overload rejection does not permit reboot, corruption, RF starvation,
owner loss or false inactivity. Allocation failure is acceptable only in the
predeclared overload path with those invariants and bounded recovery preserved.

R4 keeps host coverage of the complete operation/state/principal matrix. On the
physical candidate, demonstrate foreign control and forbidden storage requests
in claimed-but-empty, Loaded, Armed and Running states where prohibited by the
actual contract, plus the owner abort combinations
above. Reduction removes repeated identical physical trials, not authority rules.
A disconnect after ARM may also cover R5 external link loss if both the local-job
and network-recovery assertions are independently observed in that same run.

R5 retains actual flash journal rotation as a distinct path, not a write-endurance
test. Read existing journal position and plan the smallest bounded sequence that
crosses one rotation. If the remaining approved writes cannot cover rotation and
restoration, leave that assertion OPEN and report the needed bounded follow-up;
do not erase the journal, reset the counter or claim config persistence proves
rotation. An idle OFF/ON cycle complements external link loss: intentional
management and involuntary connectivity loss exercise different paths.

## Traceability from the preserved 20 cases

The change is prospective. The disposition column names execution changes, not
new pass results. Source-impact review determines whether referenced functional
evidence is still applicable; exact-image RF/resource evidence cannot transfer.

| Legacy case | New coverage | Disposition and preserved assertion |
| --- | --- | --- |
| A1 | R1 | Keep four linked layouts; avoid rebuilds for documentation-only changes. |
| A2 | R1 | Keep matched physical idle/controller/N comparisons; replace automatic full inhibited family with change-directed regression. |
| A3 | R2 | Keep all states and three launches overall; share jobs with mode/contention coverage. |
| B1 | R2, R6 | Merge repetitive nominal runs into mode and endurance runs; retain persistent owner plus actual browser behavior. Old synthetic asset/poll stress remains S. |
| B2 | R3 | Keep distinct valid/failed target lifetimes; reuse unchanged certificate semantics and remove blanket 20-fold physical repetition. |
| B3 | R3 | Keep every distinct slow/partial/stalled timeout and its recovery; remove uniform triplication of identical paths. |
| B4 | R3 | Keep supported slots, pending and excess-client rejection; repeat reclamation cycles rather than 20 identical sets. |
| C1 | R3 | Keep real job/frame/body boundaries individually and classified simultaneous overload. |
| C2 | R3 | Keep parser/unread-output pressure with independent owner observation and actual RF; integrate representative repeats into reclamation cycles. |
| C3 | R3 | Keep terminal/replay/session capacity, normal reuse, overflow and measured expiry. |
| C4 | R4 | Keep foreign-owner precedence in distinct states; share state setup with E2/F2. |
| D1 | R4 | Keep local completion after acknowledged ARM/disconnect and same-session reconciliation. |
| D2 | R4 | Keep lost LOAD/ARM/ABORT effects and replay; targeted TCP/resolver regression plus RF interaction. |
| D3 | R5 | Keep actual lease change, native name recovery, external loss and DNS/SNTP competition; share one link-loss execution with D1 where valid. |
| D4 | R5 | Keep one idle OFF/ON and bounded recovery; exhaustive independent-cache/goodbye permutations stay in 11.4 regression scope. |
| E1 | R5 | Keep persistence, watermark, actual rotation and physical-worker flash lockout; no endurance writes. |
| E2 | R4 | Keep rejected storage mutations and absence of writes/job disruption in prohibited states. |
| F1 | R2 | Keep every exposed mode and distinct full/short/tail/launch path; replace three per mode with path-directed repetition in R6. |
| F2 | R4 | Keep browser/production owner abort in Armed and Running; eliminate repeated state setup. |
| G1 | R6 | Keep the bounded mixed run and equal-state memory/expiry assessment after prerequisite passes. |

Standalone scheduler preparation under contention is made explicit in R5/R6;
it was not adequately demonstrated by externally submitted jobs in the old table.
No band/mode/clock qualification moves from Phase 13, and no 11.6 RF gate moves here.

## Resource gates, comparisons and evidence reuse

Keep both 16 KiB stacks with at least 4,096 bytes guarded reserve; verify exact
MSPLIM/allocation identity, unchanged admitted boot and zero stack faults alongside
canary and linked-frame/call-path evidence. Canary use is a lower bound, not a
maximum stack-pointer proof. Keep the general heap recovery reserve of 32,768
bytes and evidence of the largest necessary allocation, fragmentation or a named
supported approximation, failure recovery and allocator/observer overhead.
TLS allocation is part of that heap; lwIP fixed pools and static RF memory are
separate. Allocation probes are idle-only, never during owned/Armed/Running work.

Keep the 75% RF critical-path budget and at least 25% full/short predecessor
reserve, with valid matched observations and no ignored IRQ-entry latency.
Launch guard, tail completion, TXSTALL and authoritative shutdown remain separate
requirements. The 100 ms mailbox and eight-second watchdog are recovery bounds,
not usable RF timing margins. No STATUS success substitutes for these gates.

Use Q (360 seconds) before/after a resource family when needed to expire the
300-second idle replay/session lifetime. Share Q only when image/clock, warm-up,
observer phase, network/cache state, job/history cardinality and retained resources
are equivalent and documented. An intentional capacity test needs its own
post-expiry check. Terminal records last 3,600 seconds: preserve equal cardinality
or schedule an explicit 3,660-second comparison; never hide that wait in a short
packet. Do not compare a fresh reboot against a warm retained state as leak proof.

R6 quiet periods are additional to its 30 minutes of N. Three five-minute quiet
observations plus a final six-minute Q imply at least 51 minutes before setup
and restoration; extend an observation to Q when expiry needs it. Five minutes
alone must not be assumed to expire every cache/session or yield equal state.
A shared earlier Q is reusable only under the equivalence rules above. Freeze
the full wall-clock budget, including any extra expiry/quiet time, in the packet.

Reuse a reviewed run for multiple assertions only with matching source/image,
clock, board, workload and state coverage. A new boot may have its own admitted
baseline; no counter delta or memory comparison crosses boots. Record exact
source-change impact per assertion: allocator/TLS/driver changes usually affect
resource/contention gates broadly, while documentation changes do not. Prior
functional evidence supports unchanged semantics but cannot supply new physical
heap, stack, refill or launch measurements.

Keep USB INFO start gaps at most 2 seconds, USB STATUS/host health at most 6
seconds for their five-second sampling, and bounded individual request deadlines.
Missing critical observations, truncated wire data, dead observers or capture
loss invalidate the relevant evidence. Independent USB observation must survive
network failure; do not infer inactivity from disconnects or labels. Match raw
wire records to summaries and explicitly report measurement perturbation.

## Small execution packets and restoration

Prepare and audit one bounded packet at a time. Suggested sequence:

### Reuse evidence between fixes

Do not restart R1 or earlier families automatically after a fix. Before another
hardware packet, record the source/configuration difference, the specific
assertion IDs invalidated by that difference, and the evidence retained with a
reason. A new firmware revision requires this impact assessment, not an automatic
full-family replay. Preserve exact original evidence identities when documenting
why an unaffected assertion remains applicable.

- Documentation, offline auditors and host helper changes retain the existing
  frozen firmware. Run affected deterministic tests and re-audit existing raw
  evidence; repeat target measurements only if the measurement itself changed
  or the existing evidence is insufficient.
- Static firmware state/layout changes require new linked layout/headroom checks
  and affected guard/address or measurement checks. They do not automatically
  invalidate every idle interval, TLS allocation probe or unchanged network path.
- Allocation-path, library, stack-use or resource-lifetime changes require the
  corresponding physical R1 assertions. Reuse unaffected R1 assertions explicitly.
- RF launch/refill changes require the affected R2 timing/lifecycle evidence.
  Revalidate resource assertions only where the source/layout impact warrants it.
- A new selected clock requires recalculated deadlines and affected resource and
  contention checks bound to that clock; never transfer timing results by label.

The full R1 repeat during the 049cc929 amended launch campaign was a conservative
execution choice, broader than the requirement to repeat affected checks. It
does not establish a rule to rerun R1 after every firmware or tooling fix.

### Packet order

1. R1 artifact/measurement admission, then a physical baseline packet. Reuse the
   latest idle diagnostic only for the assertions it actually measured; it lacks
   matched quiet/controller-only comparisons and active RF evidence.
2. R2 short Tone/state/three-launch packet as the first active RF gate; follow
   with remaining modes without repeating an unchanged full R1 family.
3. Separate R3 resource subcases, R4 authority/interruption subcases and R5
   lifecycle subcases. Shared setup is useful; simultaneous unrelated fault
   injections are not a substitute for attributable results.
4. R6 only after all preceding mandatory assertions pass, then final review.

Aim for roughly 20–40 minutes of hardware work per ordinary packet, not a promise
of preparation or total family duration. Split a longer family; do not shorten
required jobs, expiry waits or repetitions to meet that target. R6 and any
3,660-second retained-history check are explicitly longer packets. Freeze exact
limits before execution. Finish raw audit and publish `passed/failed/not-run`
subcase counts after each packet, separately from family completion counts.

A test packet is not necessarily a fresh fixture session. Neighboring packets
may share a bounded authorized session and unchanged boot with safe explicit
handoffs and sufficient restoration time. Last recorded configuration count is
30/32; reserve R5 rotation, schedule changes and final restoration before further
writes. Separate setup/restoration per packet would exhaust this budget. Never
reset an administrative counter to manufacture capacity. Preserve prior attempts.

Every future session binds actual board/boot/image, radio MAC/roles, finite RF
jobs and current 50-ohm/attenuation/filter/instrument wiring, with exclusive USB
endpoints, independent local supervision and bounded guarded restoration. Keep
Pico B read-only, and protect the installed WsprryPi process, Ethernet, wlan1 and
GPSDO unless separately authorized otherwise. Reuse existing authorization only
within its actual bounds; this planning task does not activate a session.

Stop dependent actions on unexpected faults or failed cleanup. Preserve unknown
output and failed evidence; do not automatically reboot/reflash/retry/clear it.
Other independent work may proceed only after safe admission, with the failed
gate still open. Restore original approved inhibited image/config and host state
after authoritative checks; independent host cleanup cannot reset an unknown Pico.

## Closure and implementation readiness

Closure requires all mandatory R1-R6 assertions on the accepted exact physical
configuration, reviewed source/functional dependencies, all resource/timing gates,
bounded recovery, complete evidence and restoration. Any missing rotation,
allocation, mode/path, standalone, authority or timing assertion remains OPEN.
No six-family pass count is a substitute for that assertion checklist. Publish
accepted configurations only with source/ELF/UF2, board/boot/clock, workload and
gate evidence. **The accepted configuration list is currently empty.**

R1 now has an explicit executor, N workload and raw auditor; all five assertions
passed the bounded time.local campaign, as recorded in the [R1 review](phase11-5-r1-review.md).
Other family runners still implement the old matrix, and the existing
validator requires all 20 legacy cases PASS. A later explicitly code-authorized
slice must support N/S/O/M profiles, independent subcase reporting/reuse, standalone
coverage and the revised ledger/closure predicate without weakening safeguards.
Specify source-bound controller cadence and freeze concrete executable packets
there. R1 is executable and closed in its recorded scope; the remaining families
are prospective requirements, not an implemented six-family campaign. Do not
bypass the old validator or mark deferred breadth PASS. Keep it available for historical records and compatibility review.

Documentation Impact: coordinating plan, current ledger, development/review
pointers and companion development review change. WTP, browser API, architecture,
firmware and operator behavior are unchanged. Wsprry_Pi_Docs remains outside
scope; after measured acceptance, publish applicable limits in
`docs/Advanced_Operations/ini_configuration/transmitter_backends.md`,
`docs/Command_Line_Operations/transmitter_backends.md`,
`docs/User_Interface/Setup/Transmitter/index.md`, `docs/User_Interface/Operations/index.md`,
`docs/Advanced_Operations/rest_api.md` and
`docs/User_Interface/Maintenance/network_safety.md`. No unmeasured limit is ready
for operator publication from this documentation revision.
