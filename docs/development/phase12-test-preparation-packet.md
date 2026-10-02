# Phase 12 proposed hardware packet

Status: **PREPARED / NOT AUTHORIZED / NOT EXECUTED**. This packet prepares the
remaining tests; it does not close Phase 12 or permit any hardware operation.
The [execution prompt](phase12-test-preparation-prompt.md) authorizes source,
offline validation, build, review and commit/push only. The final
[test-preparation review](phase12-test-preparation-review.md) records results.

## Identities, artifacts and authorization

Only Candidate B is eligible: USB serial `CDDBF8767C506C07`, device ID
`29f20b7342051ef947aa56cb9d4fab42`, Pico 2 W / RP2350. Candidate A, wspr4,
router changes and other repositories are excluded. Historical restoration is
inhibited revision `615888e5364b`, profile/access generations 5/1. Historical
station address `192.168.1.53` and boot identity are not current facts.

The committed [candidate manifest](phase12-test-preparation-candidates.json)
binds clean source, pinned SDK/toolchain, fifteen exact private ELF/UF2/map and
build-evidence records. Artifact root is the ignored
`build/phase12-preparation-candidates`. The later documentation commit is not
an embedded source identity. Verify before proposing device work:

```sh
python3 scripts/phase12_candidate_manifest.py \
  docs/development/phase12-test-preparation-candidates.json \
  --artifact-root build/phase12-preparation-candidates
```

Reproduce the build into a new private directory with a clean checkout of the
manifest source, retained SDK and retained picotool import (no downloads):

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

Before execution, obtain human approval naming the exact phases and operations,
board, full source/image hashes, finite cases, physical RF wiring if applicable,
reset levels, credential changes and restoration candidate. Then record a
fresh operator **Ready**. Each destructive case must be explicitly included;
approval for a soak is not approval for reset or credential replacement.
The private observer approval template has `approved=false`; changing JSON is
not authorization. A new packet is required after identity/image/wiring changes,
a cold boot that rearms a fixture, unexpected reset or exhausted budget.

## Prerequisites and stop/restoration rules

1. Under separately authorized USB/readback access, verify exact B serial,
   device/boot identity, version/revision, selected engine/wire mode and all
   allocation, guards, storage, reset-pending and output fields. No queued or
   loaded job, owner, lease, active output, pending reset or scheduler activity.
2. Obtain a fresh recoverable private backup of profile, access, operational
   records, trust/clients/bonds and all reserved sectors, including E10. Record
   region addresses, hashes, generations and source. E10 is the RP2350 boot-ROM
   erratum workaround record, not a user profile. Preserve it byte-for-byte.
   Demonstrate the approved restore/readback procedure before destructive work;
   no test starts with a backup that cannot reconstruct intended settings.
3. Identify phone model/OS/browser and hashes/origins of served local bundles.
   C8 requires a genuinely different phone from historical same-phone evidence.
   Record engineering clients/certificates separately; keep keys/passwords private.
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

## Ordered, separately admitted phases

Every case retains private before/after raw records and wire/phone artifacts;
redacted summaries name hashes, exact candidate and boot. Record durations,
uncertainty, rejection results and cleanup. Waiting for the operator does not
consume an active case timer. Passing a source test does not pass a target row.

| Phase / closure rows | Finite actions and expected evidence | Bound |
| --- | --- | --- |
| Consumer / C8, C8T, C10O, R11F | On `consumer`, different phone makes one network save and one station save, including isolated no-SNTP station save. Prove exact digest/generation, one activation/reboot, readiness pending, unchanged populated trust/clients and unrelated records. Seed one separately approved populated supported profile; no implicit trust rotation. Cellular disabled and no infrastructure Internet for one local portal visit. | Two successful saves, each <=10 min; one no-SNTP interval <=15 min; one offline visit <=10 min. Explicitly authorize populated seed and restore. |
| Negatives / C10N | One named request per wrong-device, competing, expired, replayed, malformed and cancelled boundary. Record exact generation/digest/authority unchanged. One deliberate lost-response case reconciles durable result without resubmitting. | Seven cases, <=5 min each; no duplicate POST retry. Lost response is a declared client-side observation/interruption, not arbitrary packet manipulation. |
| Recovery / R11A | One controlled saved-station loss and reconnect using only the approved existing wspr5 fixture. Prove 60 s loss fallback, local offline portal and 30 s stable withdrawal, including one pending reply/transaction retention observation. Keep management route recoverable. | One cycle <=15 min; no router/unrelated network operations. |
| Engineering / B12J, B12C | Use `engineering` with declared authenticated clients; prove USB/BLE/TLS-WTP/HTTPS principals share one JobService, no fallback to plain. One declared credential A→B→C sequence proves obsolete trust cannot resurrect and generation callbacks cannot cross activation. Offline Bluefy visit is separate from consumer portal. | Three explicitly approved credential deployments, <=10 min each; one offline visit <=10 min. Restore original intended trust; no public secrets. |
| Ordinary composition / B12C, B12R | Separate consumer and engineering plans with the [composition procedure](phase12-composition-preparation.md), five directed pressure boundaries plus associated prior fault evidence, maximum framing/session refusal, loaded/armed/running competing admissions, disconnect and provisioning scrub. INFO observer samples exact identity/resources; independently retained wire evidence proves actual carriers. | Two independently admitted 2 h soaks; 241 samples each at 30 s cadence, gap <=45 s, <=12 simulated jobs per composition and <=60 s per job, RF jobs zero, observer flash cycles zero. Reserve 16 min network/BLE quiet and final 20 min disconnect/resource return. |
| Separate ordinary flash/concurrency / B12R | One explicitly approved station metadata save on each selected ordinary image: consumer encrypted portal/profile journal; engineering authenticated HTTPS config PUT/operational journal. Concurrent bounded STATUS observation, exact selected-journal digest/generation/preservation and adapter/resource return. Independently establish overlap; fixture evidence cannot substitute. | At most two separately admitted cases, <=10 min each, one save and <=20 STATUS per carrier at >=100 ms spacing, no retry/RF, then exact original metadata restoration. |
| Absolute deadline / B12R | `session_deadline` on engineering access proves actual INFO 15 s/60 s limits, activity avoids inactivity yet absolute expiry refuses new mutation; active owner gets bounded status/cancel grace, then session reclamation. Return to ordinary candidate and verify 15 min/12 h plus short-run behavior. | One inactivity and one absolute/grace case, <=5 min each. This checks the same admission policy with shorter constants; it does not measure twelve real hours. |
| Time / B12T | On inhibited engineering image, declare authenticated disagreement/age/two-sample recovery observations and loaded/armed/running distinction. Use protocol-valid client time stimuli; no arbitrary firmware clock mutation. Verify accepted SNTP priority and browser hints never grant RF authority. | One case per disagreement, age, recovery and job-state distinction, <=5 min each. Restore actual accepted SNTP and watermark. |
| LED / B12L | Observe current two-flash AP cue, Identify priority/nonextension independently timed and without job changes. LED output-fault cue acceptance requires a separate reviewed adapter-error fixture; reset/profile faults do not substitute. | One sequence per prepared cue/priority, <=5 min each; fault injection remains unprepared pending its fixture, restore healthy state. |
| Resets / R11P, B12J | Two reset levels across stages 1–7, each separately approved and freshly backed up. Two confirmations plus typed `reset provisioning` or `erase`; verify exact clearing/preservation, physical bonds, epoch advances once and E10 unchanged after reboot/resume. | Fourteen cases, one operation and deliberate cut per case, <=5 min, at most two additional resume boots; restore after every case. |
| Profile interruption / C10N, B12J | Stages 8–10, one approved profile save per stage. For 8–9 previous committed authority or fail-closed storage; for 10 exact durable digest/generation reconciliation, no second POST or resurrected old trust. | Three cases, one save/cut each, <=5 min, at most two additional boots; fresh backup and intended-profile restore per case. |
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
then exact restoration. Admit it separately from the soak; actual overlap and
resource acceptance remain pending.

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
