# Phase 12 closure matrix

Status: **OPEN_PARTIAL — save/harness repairs reviewed; product decisions pending;
no new physical authority**
(2026-10-02). This is the current reconciliation index. Historical result
records retain their failures, exact candidates and bounded acceptance. A row
below becomes accepted only when its own source and physical evidence establish
the stated outcome. No row is waived by this document.

## Starting point and accepted evidence

The follow-up starts on `devel` at
`be1248246b423a0089d700de2b431ed839a7a301`. Concurrent changes in README,
CONTRACT, architecture, browser API, pin-assignment and transmitter-application
documents are excluded from this slice. The current working tree is not an
exact deployment candidate; deployment images must come from committed scoped
source with retained image hashes.

P12.1–P12.5 retain their hardware-free acceptance; P12.3 is `CLOSED_SCOPED`.
P12.9 remains closed under its selected manual fixed-address exit gate.
The [phone records](phase12-physical-acceptance.md) accept bounded network and
station commissioning and saved station prefill. The
[inhibited GP14 record](phase12-gp14-integrated-acceptance.md) accepts its
documented input, hold, AP, lease and restoration scope. Do not repeat these
without a specific source impact.

The [RF record](phase12-gp14-rf-review.md) accepts five rows: active stop,
armed cancellation, both while core 0 is busy, and quick-release reset.
The last reset used a 328 ms contact and a 39.463 ms conservative cutoff upper
estimate, with declared uncalibrated engineering allowances. It is not broad
RF or calibrated timing qualification. Counts remain **16 acquisitions / 11
charged jobs**, with every failed historical attempt retained. The stopped
17/12 packet grants no standing authority for its unused acquisition/job.

Last verified B restoration is inhibited `615888e5364b`, profile/access
generations 5/1, disabled scheduling, healthy journals, empty/unowned/inactive
authority and synchronized time. This is historical evidence; no live facts
have been refreshed by this software-only follow-up. A and wspr4 are excluded.

## Current assertion groups

Every physical row needs exact source/image/board/boot/client identities,
starting configuration, finite limits, duration and uncertainty, result and
cleanup. Private credentials, full backups, captures and raw traffic stay
ignored. Redacted summaries link their private artifact hashes.

| ID / milestone | Required outcome and production path | Existing acceptance | Missing work / execution | Proposed finite bounds and restoration |
| --- | --- | --- | --- | --- |
| G7 / P12.7 | `pio-dma-gp2` worker and GP14 policy stop actual RF before one same-boot AP request; latch refuses new output. | Five RF rows above; inhibited hold/AP/lease accepted separately. | Reviewed `long_ap` runner, independent IQ cutoff, real AP association/HTTP, phone observation; operator-dependent. Default-on source/image work is conditional on this pass. | Propose one acquisition/job within cumulative 17/12; one complete 20 s tone, 40 s capture, physical 12–15 s hold, AP proof within 90 s of release. No retries. Restore named inhibited candidate after fresh backup and exact readback. |
| C8 / P12.8, P12.10 | Wi-Fi-first and optional station saves through `PicoBootstrapServer`, local bundles and profile journal work from a genuinely different phone. | B bounded same-phone network/station/pre-filled station results. | New phone identity, exact digest/generation after one activation/reboot, saved network prefill, unrelated settings preservation; operator plus automated readback. | Two predetermined successful saves, one network and one station, each within 10 min; compare private before/after profile and every unrelated reserved region. |
| C8T / P12.8, P12.10 | Consumer replacement preserves populated supported engineering TLS/client material. | Empty client-list preservation only. | Seed a separately authorized populated profile fixture; verify exact retained trust/clients and explicit rejection if retained trust cannot safely be reused. | One prepared populated fixture, one metadata save and one network save; no implicit trust rotation. Restore exact intended profile, not an empty test substitute. |
| C10O / P12.10 | Device-served portal loads and cryptography works without infrastructure Internet or cellular. | Bundled source and browser tests; no full offline phone acceptance. | Phone cellular disabled, isolated field network, AP interface/origin and local asset proof; operator-dependent. Engineering Bluefy offline remains a separate supported-client assertion. | One offline portal visit and one offline-engineering visit, each <=10 min once operator present; no timer while waiting for operator. Restore phone/fixture connectivity afterward. |
| C10N / P12.10, P12.12 | Wrong device, competing/expired/replayed/malformed/cancelled/interrupted requests cannot mutate; uncertain replies reconcile exact durable result. | Portable/browser subsets; accepted wrong-password/retry under P12.9. | Production fault/negative cases and lost-result/reboot proof. Network-only digest and uncertain-commit defects require repair. | One predetermined case per distinct production failure boundary; deterministic exhaustive journal cuts in host and named inhibited fixture, no automatic physical retries. |
| R11A / P12.11 | Station loss for 60 s returns AP; stable station for 30 s withdraws absent lease/transaction/reply; manual lease obeys current contract. | Inhibited manual hold/lease expiry bounded pass. | Controlled saved-network loss, offline portal, reconnect/automatic withdrawal and pending-reply retention. | One loss/reconnect cycle <=15 min, existing wspr5 fixture only; preserve management route, restore fixture before proceeding. Do not contact router or unrelated services. |
| R11F / P12.11 | Field-network replacement without SNTP has selected durable settings and readiness behavior without weakened RF time admission. | Network-only replacement does not require SNTP; station save requires fresh SNTP <=10 s. | Product decision and implementation below, then target test. | One isolated no-SNTP network trial <=15 min. Restore known usable network and synchronized time. |
| R11P / P12.11 | Provisioning reset and full erase have distinct explicit controls, durable intent, correct clearing/preservation and restart recovery. | Portable `ResetCoordinator` tests only; GP14 normal reset preserves settings. | Consumer semantics/control decision; production target erasure/resume integration and named interrupted-intent fixture. | Two explicitly destructive reset levels; fresh recoverable backup before each. No destructive test until its exact operation is approved. Preserve E10; restore intended operational configuration after full erase. |
| B12J / P12.12 | Journal corruption/cuts never resurrect superseded trust; activation/response loss runs once; time-peer callbacks cannot cross generations. | P12.1–P12.5 scoped host evidence and bounded profile activation. | Production engineering credential A/B/C and fault-phase evidence. | Finite declared stage list, one case per stage, RF-inhibited fixture separated from production candidate; restore original trust and settings. |
| B12C / P12.12 | USB, BLE, Plain LAN and explicitly selected engineering TLS/HTTPS share one JobService with principal isolation. | Bounded individual carrier subsets. | Whole supported composition, loaded/armed/running simulator ownership, busy mutation and disconnect/lease evidence. | Complete finite simulated jobs <=60 s each, no RF; one owner and predetermined competing admissions. End empty/unowned with sessions reclaimed. |
| B12T / P12.12 | Authenticated time disagreement, age, recovery and launch admission behave under selected policy; browser hints grant no RF authority. | Scoped controller-time subsets and host arbiter checks. | Target controlled observations, aging, two-sample recovery and loaded/armed/running distinction. | Named inhibited stimuli; <=5 min per time case; restore real accepted SNTP and unsullied watermark/configuration. |
| B12L / P12.12 | Current AP two-flash cue, Identify priority/nonextension and fault cues have correct timing and no job side effects. | Bounded phone Identify and inhibited GP14 cues. | Independent timing observation and named fault fixture. | One recorded sequence per distinct cue/priority, <=5 min; no RF, restore healthy LED state. |
| B12R / P12.12 | Heap, guarded stacks, lwIP/BTstack pools, TLS allocations, flash serialization and bounded sessions return resources. | Historical partial resource results and linked guards. | Target instrumentation/finite pressure cases plus whole-composition soak below. | Proposed 2 h soak after finite cases; no flash loops or autonomous RF; fail on allocation/guard/storage/identity/output fault. Final resource return and disconnected/provisioning-closed state required. |
| F12 / all | Exact approved standard inhibited image and intended settings are restored; no owner/job/output, healthy journals, AP withdrawn where applicable. | Historical B restoration only. | New candidate selection after conditional GP14 enablement and product repairs, fresh backup, programmed payload and reserved-byte validation, USB/LAN corroboration. | <=5 min final stable observation after required reconnect/time readiness. No restoration claim from flash command or disconnect alone. |

The two-hour proposed soak covers repeated 30/60/90-second readiness/time
boundaries, 15-minute inactivity and session reclamation after directed maximum
pressure. It does not measure the 12-hour absolute session deadline; that needs
a separately identified accelerated fixture plus ordinary-candidate short-run
behavior. This proposal is not physical authority or an accepted reliability
claim. Target instrumentation and exact cycle counts must be ready before the
hardware packet is issued.

## Historical Stage A disposition

The [historical fourteen-row matrix](phase12-physical-acceptance.md#stage-a-rf-inhibited-first-functional-matrix)
contains supported engineering requirements and superseded consumer ceremony.
The [selected revision](phase12-safari-open-setup-revision.md) and physical
plan's current consumer continuation explicitly replace consumer BLE/password/
retained-owner requirements. The engineering source, identity, storage,
activation, time, ownership and RF boundaries remain required where supported.

| Historical row | Still applicable assertions | Explicitly superseded consumer assertions / replacement |
| --- | --- | --- |
| 1 identity/enrollment | Full identity, MAC naming, missing/colliding identity fail closure, secrets; engineering enrollment/password limits. | Default-password/confirmation/bond ceremony for saving. Consumer full identity is bound internally to one encrypted request. |
| 2 BLE security | Supported engineering LE security, four bonds, one GATT connection, revocation/cleanup and busy behavior. | Consumer onboarding through bonds/AP passwords; destination Wi-Fi password is the sole ordinary password. |
| 3 framing/ownership | Maximum supported framing, transaction bounds, timeout/replay/scrubbing, separate principals and one JobService. | Retained consumer cookie/bond/certificate owner; fresh request keys hold no durable authority. |
| 4 offline/negatives | Engineering offline Bluefy plus separate consumer local-portal offline proof and applicable negative paths. | Engineering cache/origin ceremony as consumer setup; online use cannot replace offline evidence. |
| 5 time | Authenticated engineering bindings, age/uncertainty/disagreement/recovery, SNTP priority and launch rules. | Consumer login/HTTPS/BLE prerequisites for network save. Browser hints remain lower confidence. |
| 6 provisioning/journals | Supported engineering bundle replacement/adoption, consumer separate saves, durable readback and old-or-fail-closed interruption. | BLE/USB first-profile ceremony for generic consumer commissioning. |
| 7 SoftAP | Local portal identity/origin/device checks, DHCP/captive routing; engineering TLS rejection where exposed. | Blank read-only-only HTTP, no captive DNS, mandatory Safari/CA installation/AP password. Open AP accepts encrypted save under selected active-page/relay risk. |
| 8 sessions | Supported engineering cookies/grace/ownership/expiry/CSRF; consumer request/lease/reply retention and reclamation. | Consumer password login/retained cookie owner. Deferred operational AP page adds no commissioning gate. |
| 9 fallback | Immediate blank AP, 60 s loss, 30 s stable withdrawal, current manual lease, runtime/reboot causes; engineering field mode where supported. | Consumer authenticated field-mode/token workflow. |
| 10 LED | Current readiness pattern, Identify timing/priority/busy/nonextension, faults, checked core-0 writes and no RF side effects. | Old 200 ms/1800 ms AP heartbeat; current two short flashes every 2 s replaces it. |
| 11 trust/activation | Engineering trust replacement/revocation, exact generations, one activation and failure recovery; consumer populated-data preservation and unknown-result reconciliation. | Consumer password/physical/retained-owner step-up and phone trust-store administration. |
| 12 reset | Supported engineering epoch/bond/password faults; consumer distinct destructive levels, pending intent/resume, exact clearing/preservation and E10. | Consumer default-owner recovery/enrollment and three destructive physical gestures. Selected GP14 gestures never erase settings. |
| 13 activity | Final busy/output/ownership checks, bounded status/time/Identify/cancel, normal WTP leases and reboot invalidation. | Inventing consumer password/bond/enrollment mutation interfaces. |
| 14 resources | Whole supported carrier composition, one authority, pressure/pool/stack/TLS/flash/session return, finite soak/restoration. | Treating consumer password sessions as its commissioning model or historical subsets as whole-composition proof. |

Exact GP14 edge coincidence with erase/program remains **unmeasured and
undispositioned**. Extended flash-safe pause overlap is accepted only in its
recorded narrower scope. Closure needs either exact independent evidence under
a named inhibited fixture or explicit evidence-backed operator disposition;
an idle flash test does not resolve it.

## Product decisions required before dependent implementation

These recommendations are proposals, not selected contracts:

1. **Offline station details:** permit a durable settings-only save without
   SNTP, with TLS generation/validation and service readiness explicitly pending
   trustworthy time. Preserve existing populated trust/client material. Do not
   make unauthenticated browser time trusted, activate unvalidated TLS or relax
   WTP launch admission. Decide the pending profile/schema and user result before
   implementation; a successful network-only save does not resolve this policy.
2. **Destructive controls:** provisioning reset clears network/consumer/TLS
   provisioning and engineering access/bonds while preserving operational
   station/schedules/watermark; full erase additionally clears those operational
   records. Preserve the effective saved station values even when they currently
   live in the consumer profile being removed; preserving only the unrelated
   standalone store is insufficient. Preserve E10 for both. Recommend separate
   recovery-page actions with two explicit confirmations and a one-use USB-local
   confirmation bound to the exact device, boot, reset level and request. This
   avoids granting destructive authority merely by joining the open AP. Ordinary
   commissioning still needs no USB step. Require idle/inactive authority and
   durable intent/resume.
   Do not assign either action to existing GP14 gestures. Select the consumer
   control/confirmation mechanism together with the preservation semantics.

No hardware approval packet can truthfully name final reset/offline images
until those decisions are selected and their dependent code is built/reviewed.
All independent repairs and deterministic validation proceed first. The later
single hardware packet must name exact committed candidates/hashes, B-only
flash/reset/network/credential/fault operations, destructive cases separately,
RF 17/12 limits, second-phone need, finite soak and final restoration image.

## Review findings and current result

Focused independent production review found missing durable network-only
request digest, false definite failure after a possibly durable commit, and
missing production reset-resume integration. A further source check found
station updates could silently discard populated clients when existing TLS
was invalid. The save-path repairs and their deterministic failure tests are
complete at source level. Reset integration remains dependent on the decision
above. Additional assessment separated durable and attempt digests, added the
production-used commit lifecycle gate and preserved encrypted attempt evidence
through uncertain status/reboot without resubmitting. These repairs need target
acceptance and do not close the physical milestones.

Focused RF harness review found telemetry-only long-AP acceptance, missing
12–15 s duration/event checks and missing latch refusal. Its repairs must keep
actual AP-interface/phone proof explicitly pending until separately collected
within the same admitted window. The separate read-only AP collector binds the
same campaign lock, host boot/monotonic release bracket, before/after USB boot
and health, observed Wi-Fi association and interface-bound fixed-address HTTP.
It configures no network and keeps phone proof pending. No RF has been performed
by this follow-up.

Current checks:

- `bash scripts/check_host.sh`: baseline **92/92 passed**.
- Full retained-Mbed-TLS/lwIP Xcode build: **109/109 passed**, including the
  registered AP collector and actual TLS/Plain LAN tests. Its three socket
  tests initially failed listener startup in the restricted sandbox, then
  passed with localhost access; final full suite also had localhost access.
- Final affected host checks after the last production status wiring fix:
  **7/7 passed**. The browser initially retained encrypted reconciliation
  evidence while production failed to emit its new state; independent review
  caught the mismatch, the source was repaired and an integration invariant
  added. Gate/browser behavioral regressions accompany that invariant.
- Focused ASan/UBSan `bootstrap_join_tests`, `provisioning_tests` and
  `consumer_claim_commit_tests`: **3/3 passed** after the lifecycle refactor.
  An old sanitizer build cache lacked a newer target; a fresh ignored build
  with the documented sanitizer flags superseded it.
- RF orchestration **19/19**, AP collector **12/12**, both normally and under
  `python3 -O`; WTP validator's 23 schema, seven raw JSON, framing and eight
  transition cases pass. Python compilation, C++ format and whitespace pass.
- Default inhibited, GP14 opt-in inhibited, normal RF and explicit RF
  acceptance development builds pass with the retained pinned SDK/toolchain.
  Linked BOOTSEL absence, allocator/guard/resource checks and normal/acceptance
  control separation pass. An initial inhibited compile caught a missing
  forward declaration for the new scrub call; repaired before final builds.
  These working-tree builds are not approved deployment candidates.
- Offline long-AP preparation validates the retained ledger at **16/11** and
  parks without hardware access or a Ready record. Image/helper files on the
  controller have not been refreshed or claimed ready.

Final independent reassessment found no remaining actionable finding in the
reviewed save and AP-evidence harness repairs. It does not cover unimplemented
consumer reset/offline-time decisions, the remaining target fixture work or
physical acceptance. No milestone is newly closed by these checks. All named
P12.7/P12.8/P12.10/P12.11/P12.12 gates remain open; P12.9 remains closed.
