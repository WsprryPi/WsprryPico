# Phase 12 closure matrix

Status: **OPEN_PARTIAL — zero declared automatic workstreams remain**
(updated 2026-10-05). B12J, R11P, B12C and B12R are complete within the
[automatic closeout's reviewed scopes](phase12-orchestratable-closeout-results.md).
Operator commissioning/offline browser, independent indicator/GP14 timing,
physical cuts, peer/fleet interoperability and conditional RF gates remain open.
Historical failed and stopped results stay retained; scoped automatic acceptance
does not grant whole-Phase-12, RF or release qualification. No row is waived.

**Offline scope correction — 2026-10-06:** Bluefy does not maintain an offline
cache. The earlier offline Bluefy requirement is withdrawn as unsupported;
C10O requires only the device-served setup portal without Internet or cellular.
This corrects the required scope and does not claim an offline Bluefy pass.
Earlier plans and historical records retain their original checkpoint wording.

## Current bench policy — 2026-10-05

The operator has withdrawn routine firmware/settings restoration and the
blanket RF-inhibited-image requirement: the Picos are reported attenuated or
directly connected to test rigs. Keep the current candidate and useful test
state installed between tranches and at exit. F12 now means brief current-state
recording and owned-host cleanup, rather than repeated baseline flashes,
full-flash comparisons, reboots, SNTP waits or AP-absence scan campaigns.
End test jobs, prevent unintended schedule launches, close test connections
and release locks. The operator authorizes A and B on the reported connected
SDR rigs, including transmission, and trusts the local wspr hosts and Mac. B
has GP14 wiring. Use the available phone and iPad without another inventory.
Restore only for device recovery or a named assertion that requires it; reuse
compatible backups for destructive cases.

This policy supersedes prospective restoration/inhibition instructions in this
matrix, linked plans and retained prompts. Historical restoration evidence and
image identities stay unchanged. Assertion-specific cold readbacks, restarts,
settings preservation, AP withdrawal and RF cutoff still require their own
evidence. RF-capable images are permitted on the reported rigs; simulator
assertions and physical RF assertions retain their distinct meanings and
intended-test authority/limits. No firmware default or acceptance status is
changed by this policy. Existing runners that force routine restoration or
assume inhibited execution must be adapted before reuse. See the
[updated continuation direction](phase12-remaining-execution-prompt.md#operator-direction-20261005).

## Latest automatic closeout — 2026-10-05

The [completed closeout](phase12-orchestratable-closeout-results.md), published
at `dd419af`, closes the four workstreams left by the
[historical remaining-work review](phase12-remaining-execution-review.md).
**Remaining declared automatic groups: zero.** F12 is the brief current-state
and owned-host cleanup gate; it is excluded from that count.

The reviewed originals include both loaded/armed/running waves, all six
simulator cases, 241 INFO samples over 7,200 seconds, final TLS authority and
later strict quiet state. The producer's immediate post-TLS-close check retained
one connection and reported STOPPED; its later original parent readback passed
all quiet predicates 23.346 seconds later. Independent adjudication preserves
both STOP results and `full_composition_qualified=false`, while accepting the
declared automatic scope. No workload was repeated to obtain that verdict.

The [remaining operator prompt](phase12-remaining-execution-prompt.md) gathers
the physical work at the end. Completed assertions are not a new test queue.

## Historical baseline and accepted evidence

The automatic continuation began on `devel` at merged baseline
`f2dd23d0d95dd8dc846e241ce072195ac19db3df`. Source repair
`ec0f68facb5041e9e1426d20e3c8326567272bb9` supplies the first repaired inhibited
candidates; reviewed follow-up `c0d2bd53e4bde67af64d9528e3ee89efce51b87a`
supplied the earlier fifteen-candidate manifest and verified inhibited B image.
The roadmap and Si5351/indicator backlogs were preserved outside the automatic
closeout commits; this documentation reconciliation now publishes their reviewed
intent. Earlier checkout and document snapshots remain historical evidence.
Images come from committed source and retained content-bound manifests.

The merged closeout repairs the recoverable inhibited scheduler reset latch,
portable populated TLS/config fixtures, exact load-reply allocation boundaries,
BLE lifecycle diagnostics and failure-safe snapshot recovery. Reviewed helpers
also prepare application API and consumer deferred-readiness acceptance.
An earlier independently reviewed complete available Linux selection passes **155/155** at committed host helper
revision `943a7d0` (162 registered, seven context exclusions; zero failures), including
actual Endpoint admission and retained pinned-BTstack delayed-response tests.
The earlier eight optimized Python suites pass **166/166**; the two newly
affected RF suites additionally pass **47/47**. These are source/harness results.
The subsequent narrow actual-serial-schema guard repair at `943a7d0` passes
100 affected normal and 100 optimized checks; its Linux run passes 155 selected
tests with the same seven exclusions. Independent original-log review verifies
all 1,701 committed archive files and 155 actual passing names; remote parity
at `943a7d0` is independently verified.
It changes no production firmware and supplies no live journal acceptance.
That earlier continuation independently validated the three changed native source/test files in a private committed-source archive with reviewed overlays: 155 selected Linux checks pass, 162 remain registered and the same seven context exclusions apply. Its maintained Python suites passed 121 checks per mode across four separate suites, plus 53 composition checks per mode; these source checks grant no additional target acceptance.
The complete-source c0d2bd5 T5 run directly validates the acknowledged-write
backpressure repair, expired loaded ARM refusal and fresh field-time completion.
Its late SNTP prerequisite remains retained and unaccepted. The new strict SNTP
and armed/running invalidation continuations independently supply the remaining
automatic T5 assertions without replaying the accepted cases. The seven host-only staging/readiness changes at `6b35f4c`
again pass the complete available Linux selection **153/153**. The subsequent
`226ce6c` helper repair strictly admits prerequisite and completion outcomes
within their unchanged deadlines and adds explicit one-job SNTP and two-job
armed/running invalidation continuations; independent source reviews pass.
Their required automatic T5 target assertions are now accepted across the three
separately bound tranches; RF and independent physical timing remain separate.
Its latest standard inhibited restoration independently matches all **7,097**
programmed pages and the full original 4 MiB backup, including reserved/E10,
with a complete per-run host comparison. The earlier pre-fixture stop still
lacks its original management-before receipt; that limitation remains specific
to the older run. A five-sample stability receipt ends with retained original INFO confirming
synchronized, connected, disabled/empty/inactive state. The last completed 2026-10-03 exit after
the stopped composition attempt additionally passes six fresh original INFOs,
CRC-valid correlated Plain LAN HELLO/STATUS, two complete fresh AP absence scans,
unchanged management connectivity and independently released B locks. That
checkpoint required repeated exit observations; the current bench policy
supersedes that routine. The 2026-10-03
exit is historical: a fresh 2026-10-04 INFO finds a different B boot, still
inhibited/disabled/empty/inactive with healthy storage and station link, but
zero accepted SNTP and an unsynchronized clock. The fresh exit check stops at
that readiness gate. Its 1,803 query counter records firmware attempts since
boot, including attempts before UDP allocation/send; it is not agent activity
or proof of transmitted packets. One supported normal reboot subsequently
recovers synchronized time and five quiet readiness samples within 130.643 seconds.
Independent review accepts the fresh observer scope; final fixture/lock probes remain separate.
The earlier failure cause remains unknown.

The user has now approved the private backup/profile/credential transfers.
One file-only inspection of the exact retained backup passes within unchanged
limits; it does not explain the older composition failure. The exact historical
RF bundle is transferred and inert assembly independently verifies all 62
assets. No RF image is flashed, and accounting remains 16/11. At that checkpoint, current RF setup approval and operator Ready were still
outstanding. The later bench grant is recorded above; remaining physical
Ready/observation requirements belong to the intended case.

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

The historical standard B restoration was inhibited `cc51be4f3f86`, profile/access
generations 5/1, original reserved settings/E10, disabled scheduling, healthy
journals and empty/unowned/inactive authority across five stable samples.
The historical recovery-only restoration has separate final stable INFO
with station link 3 and synchronized time. Final independently observed AP withdrawal is accepted for this restored
standard inhibited B. The complete network recovery cycle retains its live gate. The [unattended recovery record](phase12-recovery-orchestration-review.md)
and [redacted evidence](phase12-recovery-evidence.json) accept fourteen named reset
checkpoints and three profile-page/commit interruptions. The earlier stopped
campaigns remain retained. That historical campaign excluded A and wspr4 and
added no RF jobs; the current bench scope above permits them.

The [operator-independent execution review](phase12-independent-execution-review.md)
and [redacted evidence](phase12-independent-evidence.json) add the seven
production AP negative paths and bounded consumer control/resource evidence,
including original final same-boot authority. The finite automated tranches
retain their original failed prerequisites and accepted subsets. Deterministic
repairs do not promote missing live acceptance.

The subsequent [product-decision execution review](phase12-product-decisions-review.md)
records offline saves and durable destructive recovery implemented and reviewed,
112/112 host checks, 3/3 sanitizers and three linked firmware variants.
Those results do not close target acceptance.

## Current assertion groups

Record the source/image/board/boot, starting configuration, finite limits,
result and cleanup needed to substantiate each test. Use the available phone
and iPad as the two iOS clients under the current operator direction; no
additional device inventory is required. Private credentials, full backups, captures and raw traffic stay
ignored. Redacted summaries link their private artifact hashes.

| ID / milestone | Required outcome and production path | Prior accepted evidence | Current disposition / remaining work | Finite scope and cleanup |
| --- | --- | --- | --- | --- |
| G7 / P12.7 | `pio-dma-gp2` worker and GP14 policy stop actual RF before one same-boot AP request; latch refuses new output. | Five RF rows above; inhibited hold/AP/lease accepted separately. | Reviewed `long_ap` runner, independent IQ cutoff, real AP association/HTTP, phone observation; operator-dependent. Default-on source/image work is conditional on this pass. | Propose one acquisition/job within cumulative 17/12; one complete 20 s tone, 40 s capture, physical 12–15 s hold, AP proof within 90 s of release. No retries. Retain useful test state; recovery/assertion-specific readback only under current bench policy. |
| C8 / P12.8, P12.10 | Wi-Fi-first and optional station saves through `PicoBootstrapServer`, local bundles and profile journal work from the available phone and iPad. | B bounded same-phone network/station/pre-filled station results. | Second iOS-client commissioning, exact digest/generation after one activation/reboot, saved network prefill and unrelated settings preservation; operator actions plus automated readback. | Two predetermined successful saves, one network and one station, each within 10 min; compare private before/after profile and every unrelated reserved region. |
| C8T / P12.8, P12.10 | Consumer replacement preserves populated supported engineering TLS/client material. | Empty client-list preservation plus actual two-client/TLS byte preservation across one station and one network save; exact request/generation and unrelated operational/E10 bytes verified. | Two ordinary populated station/network saves now pass exact cold6→7→8 trust/client and operational preservation while unsynchronized. The separately reviewed zero-SUBMIT station-generation7 warming now passes original offline/ready observations, trustworthy time recovery and exact cold trust/settings preservation. The separately reviewed network-generation8 warming now also passes with original public/time evidence and exact populated trust/settings preservation. The separately bound absent-TLS seed now passes one target materialization8→9, native TLS/settings preservation and independent restoration/F12. Required automatic preservation/readiness assertions are complete; the pending seed deliberately has zero clients and no engineering client-admission credit. | Accepted offline saves/readiness/materialization are retained; repeat only for demonstrated source impact. |
| C10O / P12.10 | Device-served portal loads and cryptography works without infrastructure Internet or cellular. | Bundled source and browser tests; no full offline phone acceptance. | Phone cellular disabled, isolated field network, AP interface/origin and local asset proof; operator-dependent. Offline Bluefy is unsupported and excluded from the required scope. | One offline portal visit, <=10 min once operator present; no timer while waiting for operator. Restore phone/fixture connectivity afterward. |
| C10N / P12.10, P12.12 | Wrong device, competing/expired/replayed/malformed/cancelled/interrupted requests cannot mutate; uncertain replies reconcile exact durable result. | Seven original production AP claim negatives accepted on fresh inhibited `fault_8` fixtures: wrong device, malformed, competing, expired, replayed, cancelled and interrupted. Independent review verifies 47 HTTP exchanges, cancelled reboot binding and exact reserved/E10 preservation; wrong-password/retry remains accepted under P12.9. | Ordinary populated network save with one semantically discarded delivered response and exact freshboot/cold generation8/request digest now passes. No remaining work in this declared AP failure/reconciliation scope. | One predetermined case per distinct production failure boundary; deterministic exhaustive journal cuts in host and named inhibited fixture, no automatic physical retries. |
| R11A / P12.11 | Station loss for 60 s returns AP; stable station for 30 s withdraws absent lease/transaction/reply; manual lease obeys current contract. | Inhibited manual hold/lease expiry bounded pass. | Actual source-bound B loss/fallback/reconnect now passes: sixty-second loss, real B AP/interface-bound recovery HTTP and synchronized thirty-second stability followed by fresh AP absence. The accepted historical opt-in manual 600-second lease policy remains applicable to byte-identical coordinator/button wiring at c0d; current engineering/restore GP14 triggers are disabled and gain no physical acceptance. The deliberately pending-response criterion now also passes independently: one active AP connection and5840 outbound bytes persist after120-second grace expiry, followed by full same-connection HTTP200/27188-byte digest/drain/close within14seconds and fresh B beacon absence with0active/0pending. The original parent stops on an extra immediate observer-cache check1.12seconds after close; the canonical contract requires bounded beacon absence, so no extra attempt is needed. All declared automatic R11A assertions are complete; current GP14 physical qualification remains separate. | One loss/reconnect cycle <=15 min, existing wspr5 fixture only; preserve management route, restore fixture before proceeding. Do not contact router or unrelated services. |
| R11F / P12.11 | Field-network replacement without SNTP has selected durable settings and readiness behavior without weakened RF time admission. | Network and station offline saves are source-implemented; fresh trustworthy time still gates deferred TLS/readiness and RF admission. | Actual ordinary no-SNTP station/network saves pass with retained two-client trust and exact cold settings. The exact station-generation7 checkpoint now warms with original trustworthy time/readiness proof and unchanged cold trust/settings; the network-generation8 checkpoint now also passes original public/time evidence and exact trust/settings preservation. Separately bound absent-TLS generation8→9 materialization now passes original time/INFO, native TLS/settings and exact restoration/F12 review. These automatic readiness assertions are complete; engineering client admission and physical commissioning retain their own scopes. | Retain the original <=15 min bound without replaying accepted saves; recover trustworthy time, readiness and exact settings. Restore known usable network and synchronized time. |
| R11P / P12.11 | Provisioning reset and full erase have distinct explicit controls, durable intent, correct clearing/preservation and restart recovery. | Fourteen actual provisioning/full reset checkpoints accepted on B; epoch once, both profile banks cleared, local BLE roots replaced, effective station preserved for provisioning and E10 unchanged. Two separately fresh populated two-client/two-schedule/nonzero-watermark stage-1 cases additionally pass with original fresh-watchdog boot and cold readback: provisioning preserves operational state, full clears it. A separately fresh provisioned reset passes native bond storage removal (1→0→0), both local BLE roots rotated and unchanged post-peer reserved bytes. | **Automatic scope closed.** The supported reset cleared both bonds and rotated the security roots; the exact retained wspr4 key was cryptographically rejected twice with PIN_OR_KEY_MISSING and no SMP pairing traffic. Settings, cursor/watermark and E10 were preserved; configuration generation 3→5 is the production save/purge transition. Physical arbitrary/torn-write cuts remain separate. See the [closeout](phase12-orchestratable-closeout-results.md). | Retain the accepted reset/old-peer originals. Named physical cuts retain their finite fixture plan and exact durable-state/E10 proof; use current bench cleanup, not routine restoration. |
| B12J / P12.12 | Journal corruption/cuts never resurrect superseded trust; activation/response loss runs once; time-peer callbacks cannot cross generations. | P12.1–P12.5 host evidence; actual consumer profile payload/header interruptions retain old authority and commit-marker interruption selects exact new request digest. | **Automatic scope closed.** Cases 0, 8, 9 and 10, corruption cases and healthy-C recovery pass original-data review. Stage 9 retained B/generation 3; stage 10 selected C/generation 4, with correct fresh TLS authority and unrelated-state/E10 preservation. Physical arbitrary cuts remain open; this continuation grants no new stale-time-datagram credit. See the [closeout](phase12-orchestratable-closeout-results.md). | Completed finite stage list is retained without replay. Future physical cuts require their named proof and recovery only where the case needs it. |
| B12C / P12.12 | USB, BLE, Plain LAN and explicitly selected engineering TLS/HTTPS share one JobService with principal isolation. | Bounded individual carrier subsets plus ordinary consumer Plain LAN framing, loaded/armed/running simulator ownership, excess-admission refusal and lease reclamation at `1dab547e17cd`; original final same-boot authority is empty/unowned/inactive. | **Declared automatic scope closed.** Engineering API/cold persistence, BLE/TLS disconnect leases, maximum inbound BLE framing and both loaded/armed/running waves pass. All six cases preserve shared authority, foreign refusal, application BUSY/readback and profile BUSY/cancellation. Final raw authority and later quiet state/owned-host cleanup pass. Physical peer/fleet interoperability remains open; no outbound maximum response or RF qualification is claimed. See the [closeout](phase12-orchestratable-closeout-results.md). | Six finite simulator cases, selected descriptor 45 s within the 60 s ceiling, ended through owned ABORT/RELEASE. No natural 45 s completion claim or new RF job. Preserve accepted proofs. |
| B12T / P12.12 | Authenticated time disagreement, age, recovery and launch admission behave under selected policy; browser hints grant no RF authority. | Actual engineering T1–T4 at `1dab547e17cd`: authenticated disagreement, two-sample recovery, exact 89/91/181-second aging and SNTP priority independently verified from original CRC-valid WTP/USB observations. | Current c0d2bd5 original WTP/passive HCI verifies the repaired LOAD/STATUS boundary, expired loaded ARM refusal with unchanged authority and two running-to-complete simulator jobs across three charged cases. The older final SNTP prerequisite exceeds its sixty-second subdeadline and remains retained. The fresh one-job SNTP subset now passes independent original CRC/HCI review: prerequisite validation56.405s<60 and completion validation13.854s<25, with exact restoration/fresh exit. The fresh two-case clock-invalidation subset also passes independent CRC/HCI review: an armed job misses its start with unusable UTC, while a running job retains its owner and selected monotonic end. All required automatic T5 assertions are now accepted across separately bound tranches. Earlier ATT/native-adapter/schema preparation failures stay retained; RF and independent physical timing remain separate. | Named inhibited stimuli; <=5 min per time case; restore real accepted SNTP and unsullied watermark/configuration. |
| B12L / P12.12 | Current AP two-flash cue, Identify priority/nonextension and fault cues have correct timing and no job side effects. | Bounded phone Identify and inhibited GP14 cues. | Independent timing observation and named fault fixture. | One recorded sequence per distinct cue/priority, <=5 min; no RF, restore healthy LED state. |
| B12R / P12.12 | Heap, guarded stacks, lwIP/BTstack pools, TLS allocations, flash serialization and bounded sessions return resources. | Consumer ordinary `cc51be4f3f86` resource subset and fresh `1dab547e17cd` repeat: 241 samples over 7,200 s, six simulator jobs, heap return +864 bytes within the unchanged 1,024-byte bound, measured pool return and minimum guarded stack margin 23,048 bytes. Original final HELLO/STATUS proves same-boot empty/unowned/inactive authority. Accelerated session capacity-four, logout reclamation, 15-second idle and 60-second absolute expiry pass from nineteen original HTTPS pairs and retained zero-session counts. Loaded expired-cookie refusal and armed expired-cookie same-owner STATUS/ABORT pass original age/correlation review, with separately verified correction restoration. | **Declared automatic scope closed.** Engineering 241-sample/7,200 s capture passes: heap 24,920→24,776 bytes, all measured pools returned, guarded stack margin ≥22,128 bytes, controller ACL capacity/free return 8/8 with actual send/completion history. A’s one Save, all 20 STATUS replies, two overlapping intervals and cold preservation pass. Immediate quiet-check STOP remains retained; later strict quiet proof resolves exit within the original allowance. See the [closeout](phase12-orchestratable-closeout-results.md). | Accepted two-hour capture, 30 s cadence, ≤45 s gaps and unchanged 1,024-byte heap-return bound; six simulator cases. No soak replay, flash loops or RF/reliability qualification. |
| F12 / all | Record current candidate/state, end test jobs, prevent unintended launches and clean owned host fixtures; retain useful firmware/configuration. | Historical standard inhibited B readbacks match their 6,879 UF2 programmed pages; their separately retained final AP/authority observation passes. The ec0f68f journal/T5 restorations match 7,092 pages; current c0d2bd5 restoration matches all 7,097 programmed pages, full original flash and reserved/E10, with source-bound five-sample stability and original final connected/synchronized/disabled/empty/inactive INFO. The early pre-fixture stop still lacks its per-run management-before receipt; the later complete-source T5 run has an independent complete management/fixture comparison. Owned host fixtures and passive observers are removed after each completed tranche. Earlier larger-image restorations retain different unused application tails without whole-flash equality claims. | **Latest automatic exit accepted.** Same-boot raw HELLO/STATUS proves empty/null owner/job/inactive output. Later original INFO has zero connections/buffers and returned allocations/pools, with preserved settings and flash erase/program counts zero. Exact owned worker/socket/relay retirement and board-lock-holder cleanup pass. Working A/B test states remain installed; original stopped runs are retained. See the [closeout](phase12-orchestratable-closeout-results.md). | Brief current-state and owned-host cleanup per tranche. No routine reflash, full-flash comparison, reboot, SNTP wait or AP-absence campaign; recovery/assertion-specific proof remains case-dependent. |

The completed automatic resource scope includes the two-hour capture and
bounded readiness/time, inactivity and session-reclamation checks. The accepted
accelerated expiry fixture and ordinary-candidate short-run evidence do not
directly observe the production 12-hour absolute session deadline. These
results do not qualify RF or broad reliability. The historical
[test-preparation packet](phase12-test-preparation-packet.md) retains its proposed
instrumentation, candidates and finite counts; current dispositions are above.

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
| 4 offline/negatives | Consumer local-portal offline proof and applicable negative paths. | Offline Bluefy/cache requirement withdrawn as unsupported; online use cannot replace the consumer portal's offline evidence. |
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

## Selected product decisions and implementation

The operator selected the [offline-save and reset contract](phase12-product-decisions.md)
on 2026-10-02. The [execution prompt](phase12-product-decisions-execution-prompt.md)
authorizes its implementation, deterministic validation, adversarial review and
scoped commit/push on devel. It grants no hardware authority.

- Station details may be saved without SNTP with explicit readiness pending.
  Retained trust/clients remain exact; absent TLS can be materialized only after
  accepted trustworthy time. Job/RF admission is unchanged.
- Provisioning reset clears network/TLS/access/bonds while preserving effective
  station settings, schedules and watermark. Full erase also clears operational
  records. Both preserve the RP2350-E10 boot-workaround sector.
- Separate recovery-page actions require two explicit confirmations and typed
  `reset provisioning` or `erase`. No USB confirmation is required. The open AP
  does not authenticate the operator. Existing GP14 gestures do not erase.

Source implementation and review results are in the
[product-decision execution review](phase12-product-decisions-review.md).
Source repairs alone do not close target reset, offline commissioning, fault,
resource or RF acceptance. The later automatic target scopes are accepted
above; remaining physical cases must name
exact candidates/hashes and the current A/B bench scope, separately named
destructive cases, intended RF limits and available two-iOS-client operator
work. The completed automatic soak is retained; routine restoration is withdrawn.

## Historical review findings and diagnostics

The following findings, test counts and stops describe the earlier preparation
checkpoints. Their originals remain retained. The current automatic disposition
is the closeout and assertion table above; these paragraphs do not reopen it.

Focused independent production review found missing durable network-only
request digest, false definite failure after a possibly durable commit, and
missing production reset-resume integration. A further source check found
station updates could silently discard populated clients when existing TLS
was invalid. The save-path repairs and their deterministic failure tests are
complete at source level. Reset integration is implemented in the product-decision follow-up; target
acceptance remains open. Additional assessment separated durable and attempt digests, added the
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

Historical checks for the preceding save/AP-harness follow-up:

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
  parked without hardware access or a Ready record. At that historical
  checkpoint, controller image/helper files had not been refreshed.

Final independent reassessment found no remaining actionable finding in the
reviewed save and AP-evidence harness repairs. It does not cover the separately reviewed
consumer reset/offline-time implementation, remaining target fixture work or
physical acceptance. No milestone is newly closed by these checks. All named
P12.7/P12.8/P12.10/P12.11/P12.12 gates remain open; P12.9 remains closed.

## Historical test-preparation follow-up

The [comprehensive prompt](phase12-test-preparation-prompt.md) and
[review](phase12-test-preparation-review.md) cover hardware-free telemetry,
named inhibited reset/profile and accelerated-session fixtures, finite
composition capture/audit/normalization and clean candidate manifests.
The [proposed packet](phase12-test-preparation-packet.md) makes each remaining
physical phase reviewable, including destructive boundaries and restoration.
It grants no hardware authority and newly closes no physical row. Exact in-pulse
flash cuts, GP14 erase/program edge coincidence, controller buffer headroom and
physical carrier/phone/RF assertions were gaps at that preparation checkpoint.
The later measured ACL-credit assertion is accepted in the automatic closeout;
it does not claim raw controller-memory occupancy. Remaining physical gaps
retain their own scope.


The later receiver attempt also stops automatically before DHCP/SNTP, after
one owned AP activation and51 original no-address observations. Its exact
restoration and fresh wlan2 F12 exit pass independently; no receiver acceptance
or RF/job count is added. A fresh repaired helper now independently retains an exact three-script
pgrep exit1/no matches and seven host reads within the original25-second limit. A distinct spare-radio beacon diagnostic is preparation only.


The one alternate-radio diagnostic subsequently proves a fresh exact host AP
beacon but still stops at the station deadline. This supplies actual beacon
evidence only; no association or network acceptance. Exact standard inhibited
restoration, host cleanup and final exit are recorded separately. The observed
association failure remained automatic work at that checkpoint, with no concrete
source cause established by the narrow credential/join-path inspection. Later
accepted readiness, recovery and composition evidence is recorded above without
rewriting that stopped diagnostic.
