# Phase 12 proposed hardware packet

Status: **CURRENT RF-INHIBITED CLOSEOUT AUTHORIZED; PHYSICAL/RF GATES OPEN**.
The current user execution request authorizes B-only backups/readback, inhibited
flashing, simulator jobs, temporary provisioning/reset/credentials/bonds,
restoration, source repairs and scoped commit/push. Earlier preparation-only
restrictions below describe historical packets; they do not revoke this current
approval. RF work still requires a current candidate/setup-bound authorization
and actual operator Ready. Keep all retained finite limits and failures.

Current operator order: finish autonomous validation and restoration first.
Group the phone/iPad, LED observation, physical GP14 and power-interruption
steps at the end. Prepare their exact candidates and finite procedures while
automatic work runs. If the operator is unavailable, retain the prepared
packets and leave B safely inhibited; no waiting interval grants RF readiness.

## Identities, artifacts and authorization

Only Candidate B is eligible: USB serial `CDDBF8767C506C07`, device ID
`29f20b7342051ef947aa56cb9d4fab42`, Pico 2 W / RP2350. Candidate A, wspr4,
router changes and other repositories are excluded. Historical restoration is
inhibited revision `615888e5364b`, profile/access generations 5/1. Historical
station address `192.168.1.53` and boot identity are not current facts.

The current fifteen-variant candidate manifest is private and ignored at
`build/phase12-closeout-candidates-c0d2bd5/candidates.json`, with SHA-256
`13a56b7bf1822050eb022ca2f3d668fff75fc378123b3481bc4da78b17d33d9e`.
It binds firmware source `c0d2bd53e4bde67af64d9528e3ee89efce51b87a` and
artifact root `build/phase12-closeout-candidates-c0d2bd5`. Verify that complete
current manifest and its artifacts before using a current candidate:

```sh
python3 scripts/phase12_candidate_manifest.py \
  build/phase12-closeout-candidates-c0d2bd5/candidates.json \
  --artifact-root build/phase12-closeout-candidates-c0d2bd5
```

The current standard inhibited restore UF2 hash is
`7bf7a2b75795aea27f441f554c7ae15c0ce8c437f847e38a9e23b15a0a34a1f4`.
The current RF packet is prepared for the remaining `long_ap` case only;
its private packet hash is
`b3dd1e9579a90112ec81361353078f07230a3617f1bfb69f6115c1eafc7511ec`.
It has no future boot/address or Ready and does not authorize RF deployment.

The new private RF preparation root on wspr5 now contains the reviewed code/image
and historical evidence bundles, inventory and verifier. Inert assembly and
independent review pass for all 62 assets; no RF image is flashed. The separate
historical evidence bundle has SHA-256
`2fd2d9b2df9e1db1059001c0759216d8f01a01ca1334ead9d462c52ae755df90`.
Automatic approval review initially rejected that transfer because the earlier
grant covered source/tests, inhibited firmware and helpers. The user's direct
2026-10-04 approval now includes these private payloads; the exact bundle transfer
and inert verification succeed. The required original eighty-megabyte historical IQ capture
and its 16/11 accounting remain part of the unchanged finite-budget review.

Completed T5 helper source is separately committed at
`226ce6ca5f4eb674e42bf2c82eb9759ea048c942`; firmware remains bound to
`c0d2bd53e4bde67af64d9528e3ee89efce51b87a`. The new private 372-asset continuation snapshot and seven prepared controllers
record both identities and their exact hashes in the redacted evidence. They
are prepared only; actual target and original host-before admission occurs
before any future child starts. The
reviewed completed T5 continuations use one SNTP job/120 seconds (sixty-second
prerequisite, twenty-five-second completion) and two armed/running invalidation
jobs/180 seconds. The fresh strict SNTP subset is independently accepted;
the two-case armed/running invalidation subset is independently accepted too.
The three separately bound tranches now cover the required automatic T5
assertions. Both new continuations are inhibited; physical RF/timing remains
separate.
The reviewed AP diagnostics make at most one association per explicit mode
without saving settings or submitting a job.

The later explicit journal-stimuli source preparation is committed at `f5f8d86`,
with two independent reviews passing140 normal and140 optimized methods. It
has no live acceptance yet. A subsequent actual-schema diagnostic proves that serial INFO omits owner/job fields. Repair the narrow guard and use explicit CRC WTP ownership observations where that carrier is supported before preparing a new live packet. Keep the original f5 controls and packet immutable. The alternate-radio AP diagnostic stops at its
original parent deadline before association; all completed streams are retained,
and a fresh complete F12 exit passes. Before a future diagnostic child starts,
its full declared execution and cleanup windows must fit the unchanged parent
budget. Preparation repairs must preserve exact source/image bindings.

The initial credential-bearing backup transfer rejection remains historical.
The user's direct approval covers necessary private backup/profile/credential
inputs. One file-only inspection of the exact retained B backup passes within
unchanged limits; no Pico action occurs and the older composition failure's
cause remains unknown. The 2026-10-03 synchronized restored exit is historical:
a fresh 2026-10-04 check initially finds inhibited B unsynchronized and stops
before LAN authority/AP scans. One supported normal reboot recovers trustworthy
time and five quiet samples within 130.643 seconds; the complete fresh exit
observer then passes. Independent review accepts the observation scope; final fixture/lock probes remain separate. Each dependent
campaign still requires fresh admission and complete restoration/exit checks.

### Historical preparation record

The following manifest and commands retain the earlier source-bound preparation;
they do not select the current deployment candidates.

The historical committed [candidate manifest](phase12-test-preparation-candidates.json)
binds clean source, pinned SDK/toolchain, fifteen exact private ELF/UF2/map and
build-evidence records. Artifact root is the ignored
`build/phase12-preparation-candidates`. The later documentation commit is not
an embedded source identity. Its historical verification command was:

```sh
python3 scripts/phase12_candidate_manifest.py \
  docs/development/phase12-test-preparation-candidates.json \
  --artifact-root build/phase12-preparation-candidates
```

The historical build reproduction command used a new private directory, its
clean manifest source and retained tools (no downloads):

```sh
source scripts/xcode_env.sh
python3 scripts/build_phase12_candidates.py --source CLEAN_SOURCE_CHECKOUT \
  --artifact-root NEW_PRIVATE_ARTIFACT_ROOT --sdk build/local-sdk-079c6f3 \
  --picotool-import build/phase12-gp14-continuation-import-picotool.cmake
```

The [observer approval template](phase12-observer-approval-template.json) is
intentionally invalid and unapproved. Finalize it only after separate human
authorization and fresh readback; it must cover the full capture deadline.

The [machine-readable proposed summary](phase12-test-preparation-proposed-packet.json)
binds this manifest and finite bounds with `approved=false` and Ready/backup/
boot fields unset. It is a review aid, not an executable authorization.

The manifest is a content-bound local build record, not signed provenance or
permission. Missing/changed artifacts require rebuilding and a new reviewed
packet; filenames alone do not select images. Standard `restore` has GP14 OFF;
`consumer` has GP14 opt-in ON; `engineering` uses TLS and GP14 OFF; `rf_ap` is
an explicit GP14 acceptance RF image. `session_deadline` is inhibited with
15 s inactivity / 60 s absolute deadlines. `fault_1` through `fault_10` are
separate inhibited, GP14-OFF variants. Ordinary candidates use 15 min / 12 h.
No candidate enables default-on production GP14 as an accepted policy.

B-only RF-inhibited operations are explicitly approved by the current user
request and direct approval replies. Do not request that approval again. Physical
RF requires a current exact candidate, setup and operator Ready; retain the
finite acquisition/job budget. Source/image/wiring changes or exhausted bounds
must be reconciled before a physical RF case proceeds.

## Prerequisites and stop/restoration rules

1. Under the current approved B-only USB/readback access, verify exact B serial,
   device/boot identity, version/revision, selected engine/wire mode and all
   allocation, guards, storage, reset-pending and output fields. No queued or
   loaded job, owner, lease, active output, pending reset or scheduler activity.
2. Obtain a fresh recoverable private backup of profile, access, operational
   records, trust/clients/bonds and all reserved sectors, including E10. Record
   region addresses, hashes, generations and source. E10 is the RP2350 boot-ROM
   erratum workaround record, not a user profile. Preserve it byte-for-byte.
   Demonstrate the approved restore/readback procedure before destructive work;
   no test starts with a backup that cannot reconstruct intended settings.
3. Use the available phone and iPad as the two iOS clients per current operator
   direction. Record served local assets/origins and test outcomes needed for
   acceptance; no additional model/OS inventory is required. Keep
   keys/passwords private.
4. Select the exact candidate per phase. Verify programmed payload and reserved
   bytes using the approved readback method; do not infer success from a flash
   command. Each boot gets a new identity readback. No RF during inhibited phases.
5. Stop immediately on wrong identity/mode/stage, active output, changed reserved
   bytes, allocation/pool/guard/storage fault, unexpected reboot or resource
   growth outside predeclared tolerance. Retain failure; no automatic retry,
   extended timer, repeated save or fresh acquisition to conceal it.
6. Restore exact `restore` and intended operational configuration after each
   destructive/fault phase and at final exit. Verify healthy journals, cleared
   pending reset, exact station/schedules/watermark/trust/access expectation,
   inactive engine, disabled schedule, empty unowned JobService and ordinary
   session deadlines. Corroborate on USB and the selected LAN where available.
   Observe final stable state for at most five minutes after network/time
   readiness. A disconnect is not proof of restoration.

## Remaining selectors and retained phase procedures

Execute only remaining selectors in the current closure matrix. The table
retains finite procedures for accepted historical cases as well as open work;
an accepted row is not a new campaign instruction. Seven AP negatives, fourteen
reset checkpoints, three profile-page/commit interruptions, populated offline
saves and the ordinary engineering CONFIG/USB-BLE-TLS serialization case are
already accepted under their original bindings. Do not replay those without a
concrete source impact. Deferred-readiness continuation restores the accepted generation-7 station
and generation-8 network checkpoints and warms each with zero SUBMIT attempts.
The separate absent-TLS/materialization path remains required. New phone/iPad commissioning
is a separate physical two-client scope. The consumer ordinary soak is accepted;
the engineering two-hour soak, old-peer cryptographic refusal, A/B/C replacement,
application APIs, running-cookie ownership and explicit SNTP/invalidation
continuations remain automatic where their prerequisites pass.

Every case retains private before/after raw records and wire/phone artifacts;
redacted summaries name hashes, exact candidate and boot. Record durations,
uncertainty, rejection results and cleanup. Waiting for the operator does not
consume an active case timer. Passing a source test does not pass a target row.

| Phase / closure rows | Finite actions and expected evidence | Bound |
| --- | --- | --- |
| Consumer / C8, C8T, C10O, R11F | Physical phone/iPad commissioning is distinct from accepted populated offline saves. For automatic deferred readiness, restore the accepted generation-7 station and generation-8 network checkpoints and warm each without another SUBMIT; separately prove absent-TLS materialization. Prove exact digest/generation, readiness transition and unchanged populated trust/clients and unrelated records. Cellular-disabled offline portal/Bluefy observation remains a separate operator case. | Remaining physical commissioning: two saves, each <=10 min; checkpoint warming uses its existing bounded automatic runner with zero saves; offline visit <=10 min. |
| Historical accepted negatives / C10N | Do not replay: one named request per wrong-device, competing, expired, replayed, malformed and cancelled boundary. Record exact generation/digest/authority unchanged. One deliberate lost-response case reconciles durable result without resubmitting. | Seven cases, <=5 min each; no duplicate POST retry. Lost response is a declared client-side observation/interruption, not arbitrary packet manipulation. |
| Recovery / R11A | One controlled saved-station loss and reconnect using only the approved existing wspr5 fixture. Prove 60 s loss fallback, local offline portal and 30 s stable withdrawal, including one pending reply/transaction retention observation. Keep management route recoverable. | One cycle <=15 min; no router/unrelated network operations. |
| Engineering / B12J, B12C | Use `engineering` with declared authenticated clients; prove USB/BLE/TLS-WTP/HTTPS principals share one JobService, no fallback to plain. One declared credential A→B→C sequence proves obsolete trust cannot resurrect and generation callbacks cannot cross activation. Offline Bluefy visit is separate from consumer portal. | Three approved inhibited credential deployments, <=10 min each; one offline visit <=10 min. Restore original intended trust; no public secrets. |
| Remaining engineering composition / B12C, B12R | The consumer ordinary soak is accepted without replay. Separate consumer and engineering plans with the [composition procedure](phase12-composition-preparation.md), five directed pressure boundaries plus associated prior fault evidence, maximum framing/session refusal, loaded/armed/running competing admissions, disconnect and provisioning scrub. INFO observer samples exact identity/resources; independently retained wire evidence proves actual carriers. | Remaining engineering soak: 2 h; 241 samples at 30 s cadence, gap <=45 s, <=12 simulated jobs per composition and <=60 s per job, RF jobs zero, observer flash cycles zero. Reserve 16 min network/BLE quiet and final 20 min disconnect/resource return. |
| Ordinary flash/concurrency / B12R | Engineering CONFIG/USB-BLE-TLS serialization is accepted under its original binding and is not replayed. Consumer encrypted-portal/profile-journal save with concurrent STATUS remains open; prove original overlap, exact digest/generation/preservation and adapter/resource return. Offline populated-save preservation does not qualify concurrent overlap. | Remaining consumer case: one save, <=10 min, <=20 STATUS per carrier at >=100 ms spacing, no retry/RF, then exact metadata restoration. |
| Remaining running-cookie / B12R | Accelerated inactivity/absolute expiry and loaded/armed owner grace are accepted without replay. Prove expired-cookie ownership behavior during one running inhibited job, including bounded same-owner STATUS/cancel grace and authority/resource reclamation. | One 45 s job in a 260 s body, RF zero; retain existing 15 s/60 s fixture limits, then restore ordinary 15 min/12 h settings. This does not measure twelve real hours. |
| Accepted automatic time / B12T | Required T5 assertions are accepted across the separately bound loaded/fresh-field, strict SNTP and armed/running invalidation tranches. Preserve original source and count boundaries; no replay is pending. | Six charged case reservations, four actual completions; five case charges and three completions accepted. Older late-SNTP completion remains unaccepted. RF and independent physical timing remain separate. |
| LED / B12L | Observe current two-flash AP cue, Identify priority/nonextension independently timed and without job changes. LED output-fault cue acceptance requires a separate reviewed adapter-error fixture; reset/profile faults do not substitute. | One sequence per prepared cue/priority, <=5 min each; fault injection remains unprepared pending its fixture, restore healthy state. |
| Historical accepted reset checkpoints / R11P, B12J | Do not replay: two reset levels across stages 1–7, freshly backed up under existing B operation approval. Two confirmations plus typed `reset provisioning` or `erase`; verify exact clearing/preservation, physical bonds, epoch advances once and E10 unchanged after reboot/resume. | Fourteen cases, one operation and deliberate cut per case, <=5 min, at most two additional resume boots; restore after every case. |
| Historical accepted profile interruption / C10N, B12J | Do not replay: stages 8–10, one approved profile save per stage. For 8–9 previous committed authority or fail-closed storage; for 10 exact durable digest/generation reconciliation, no second POST or resurrected old trust. | Three cases, one save/cut each, <=5 min, at most two additional boots; fresh backup and intended-profile restore per case. |
| Remaining RF/AP / G7 | Exact `rf_ap` and conducted `pio-dma-gp2` setup, local complete Tone job, physical long hold, actual RF cutoff then same-boot AP; latch refuses later output. Independent IQ/edge evidence plus real association/interface-bound HTTP and phone proof in the admitted window. | Exactly one acquisition/job: 20 s tone, 40 s IQ, 12–15 s physical hold, AP proof <=90 s after release; cumulative ceiling17 acquisitions/12 jobs from16/11. No retries. Restore `restore` and exact settings. |

The accelerated fixture exercises **engineering** access; its plain consumer
LAN selection is irrelevant to the authenticated engineering SoftAP session
policy. Never use it for an ordinary soak. Fault image entry also requires a
healthy stable profile with no pending deferred TLS materialization: otherwise
an unplanned boot save may consume stages8–10. Before the approved save,
`phase12_fault_consumed` must be false. Unexpected consumption is a stop, not a
successful case. See [fault fixture details](phase12-fault-fixtures.md).

The associated `flash_serialization` artifact is prior fixture evidence, not
proof of simultaneous flash and ordinary-carrier composition. No image change
or fault reboot is allowed within a soak. The composition procedure defines a separate ordinary-image one-save
concurrency case: at most one per composition, ten minutes, one approved
station metadata save and at most twenty STATUS requests per selected carrier,
then exact restoration. The engineering ordinary CONFIG serialization case is accepted under its
retained binding. Consumer ordinary save/STATUS overlap and the separate
engineering soak resource acceptance remain pending.

See [concrete time/LED cases](phase12-time-led-preparation.md) for supported
request paths, stimuli and timing. Unavailable physical fault injections remain
separate prerequisites rather than an implicit runtime command.

## Boundaries that remain separate

The ten reset/profile fixtures interrupt after completed physical pages or
durable phases. They do not perform arbitrary corruption or in-pulse power cuts.
Existing host byte-cut/corruption evidence is retained; exact physical torn-write
qualification needs its own reviewed fixture/approval. Exact GP14 edge coincidence
with erase/program remains unmeasured and needs independent evidence or an
explicit evidence-backed operator disposition; these GP14-OFF fixtures do not
resolve it. Time/LED and credential A/B/C cases use named supported stimuli and
independent observers, rather than an invented runtime fault switch. Controller
buffers and largest contiguous allocation remain unmeasured; the new telemetry
measures project adapters and named lwIP/BTstack host API pools only.

The stopped historical RF packet supplies no remaining standing authority.
No new RF trial or conditional default-on change occurs in this preparation.
After all separately admitted rows pass, assess the new source impact and prepare
any conditional default-on candidate with fresh hashes before claiming closure.
Final acceptance must account for every applicable row in the
[closure matrix](phase12-closure-matrix.md), including gaps above. No physical row
is waived by this packet or an offline tool result.


The actual-serial-schema repair at `943a7d0` passes100 affected normal and100
optimized controls, independent source review and155 selected Linux tests with
the same seven exclusions. It is pushed with independently verified remote
parity. All271 production files remain unchanged. Create a new immutable
journal-stimuli preparation from this repair; the old f5 packet remains
historical and has no live acceptance. Source-zero fault ownership remains
unobserved through INFO, with native configuration/seed and carrier gates
separate.


The distinct USB-radio observer now independently completes the standard
inhibited exit after the receiver pre-child stop, with unchanged finite limits.
A fresh943a journal-stimuli packet passes149 normal/optimized preparation
controls and independent review; host-before/future boot are null and no
campaign runs. Preserve the original f5 packet and all stopped attempts.


The reviewed receiver now reaches one owned host AP activation but stops at
the unchanged station-observation limit with no matching SSID and no address.
Its standard inhibited restoration and fresh complete wlan2 exit pass. The
single previously inert wlan0 AP/wlan2-observer packet has now run: an actual
fresh beacon passes, but station association stops at its original deadline.
No further variant is prepared; timers and acceptance requirements remain. The separately repaired raw-process helper now independently passes with
seven retained host reads and one exact three-script pgrep exit1/no matches;
its scope excludes unrelated host processes.
