# Phase 12 unattended recovery campaign review

Phase 12 remains `OPEN_PARTIAL`. All seventeen named
watchdog-interruption cases passed; their physical acceptance is limited to the
listed durable boundaries and actual seed. Candidate B
only was used; RF jobs/acquisitions are zero for this work. The prior RF ledger
remains 16 acquisitions / 11 jobs. Candidate A and wspr4 were not operated.

## Source and intended scope

The [execution prompt](phase12-recovery-orchestration-prompt.md) implements the
user's explicit authorization for destructive Pico operations without repeated
approval prompts. The new [eleven-image manifest](phase12-recovery-candidates.json)
binds standard restoration and ten RF-inhibited fault stages to clean source
`cc51be4f3f867a3f531a639c911ff44755ea18fe`, firmware `0.0.0-devel`, Pico 2 W / RP2350,
SDK 2.3.1 `079c6f39023649b154152db30f1d781e884879bc`, GNU Arm 15.3.1.
USB host is wspr5, picotool 2.3.0; Candidate B serial is CDDBF8767C506C07 and
application identity is 29f20b7342051ef947aa56cb9d4fab42.

The runner defaults to offline verification. Live execution uses a private plan,
exact device/candidate hashes, board-wide campaign and action locks, local backup
barriers, single-attempt AEAD-protected submissions, a durable hash-chained ledger,
300-second case acceptance bounds and automatic standard-image restoration.
Recovery-only execution restores the verified retained backup and never resumes
an uncertain destructive request. Temporary AP association uses unused wlan2,
static 192.168.4.2/24, no default route and a uniquely named disposable connection.
The management interfaces and unrelated connections remain outside the adapter.

Consumer USB field-access commands are intentionally unavailable. Fault images
therefore have a test-only 120-second AP join-grace window at boot. This uses the
ordinary open consumer AP and encrypted recovery/station-save APIs; it does not
simulate a GPIO press or qualify production button/AP activation. INFO reports
the configured window limit, not remaining availability. Standard restoration
images exclude the fixture and retain ordinary 15-minute idle / 12-hour absolute
session policy.

## Completed physical evidence

The [redacted evidence JSON](phase12-recovery-evidence.json) records exact source,
board, boot, ledger/observer, backup/readback hashes and per-case durations. It
combines fourteen individually accepted reset records from STOPPED campaign 6
with three accepted profile records from PASS_NAMED_SCOPE continuation 7; it
preserves both original campaign dispositions. Final read-only audit revalidated
both hash chains, seventeen unique one-attempt request bindings, all journal and
E10 comparisons, healthy inhibited post-cut telemetry and final firmware bytes.

| Case | Result | Acceptance duration (s) | Observed boots |
| --- | --- | ---: | ---: |
| provisioning-1 | PASS | 102.397 | 2 |
| provisioning-2 | PASS | 102.576 | 2 |
| provisioning-3 | PASS | 103.040 | 2 |
| provisioning-4 | PASS | 102.718 | 2 |
| provisioning-5 | PASS | 102.593 | 2 |
| provisioning-6 | PASS | 102.689 | 2 |
| provisioning-7 | PASS | 101.826 | 2 |
| full-1 | PASS | 102.590 | 2 |
| full-2 | PASS | 102.612 | 2 |
| full-3 | PASS | 102.414 | 2 |
| full-4 | PASS | 102.572 | 2 |
| full-5 | PASS | 102.029 | 2 |
| full-6 | PASS | 102.546 | 2 |
| full-7 | PASS | 101.679 | 2 |
| profile-8 | PASS | 112.594 | 2 |
| profile-9 | PASS | 112.360 | 2 |
| profile-10 | PASS | 112.509 | 2 |

Each duration runs from pre-case backup through accepted post-cut readback and
excludes its separately bounded restoration. These are orchestration durations,
not RF timing or calibrated watchdog measurements.

Final restoration is standard inhibited source `cc51be4f3f867a3f531a639c911ff44755ea18fe`,
profile/access generations 5/1, original reserved settings and byte-identical E10.
The retained final full-flash readback matches every UF2 application payload and
all original reserved bytes. Five stable post-boot samples establish synchronized
network/time, ordinary session policy, zero active/pending transport buffers,
healthy resources, no reset/job/owner/output and disabled scheduling. The private
final readback hash and public boot identity are in the JSON record.

Host cleanup removed the disposable campaign connection. wlan2 is disconnected;
management eth0 and wlan1 remain connected. No device action occurred during the
final read-only artifact audit.

Validation: full host suite **118/118**, observer tests **30/30** normally and with
Python optimization, affected ASan/UBSan suite **4/4**, retained target-host crypto
vectors **2/2**, eleven recovery candidates verified offline, and WTP contracts
(23 schemas, 7 raw JSON cases, 1 framing case, 8 transitions). Independent
adversarial reassessment found no remaining actionable issue in this bounded
source/evidence scope. The separate physical gaps below remain open.

## Adversarial findings and repairs

Independent report-only reviews found and closed the following actionable issues:

- Orphaned remote picotool operations could race restoration after SSH timeout:
  added a separate remote action lock covering complete helper invocations.
- Fault observations were retried as transport errors, and resource faults could
  block emergency restoration: separated unavailable observations from rejected
  evidence and added restoration-only admission requiring exact inactive B.
- Resource/session and restoration checks were incomplete: required allocator,
  TLS, flash, pool and stack-guard telemetry; verified journal generations,
  effective station, ordinary timers, zero transport buffers, network/time and
  stable boot before restoration acceptance.
- Restart evidence was insufficiently durable: added directory fsync, strict JSON,
  campaign-ID checks, verified local backup barriers and recovery-only mode.
- Access-record bond counts did not prove physical credential clearing: inspected
  both physical BTstack banks. The pinned SDK legitimately creates new 16-byte
  SMER/SMIR local roots after reset; the revised observer permits only those fresh
  records, rejects any peer/deleted/unknown record or retained second bank, and
  checks that baseline local roots changed. Format and tags were checked against
  the retained SDK's btstack_tlv_flash_bank.c, le_device_db_tlv.c and sm.c.
- Preservation checks used incomplete JSON projections: compare the complete
  normalized operational configuration and nested consumer network/trust, plus
  exact unrelated access/BLE/operational journal bytes for profile cases.
- Live preflight exposed a stale helper filename, legacy telemetry differences,
  the consumer USB AP gate and an incorrect password-protected AP assumption:
  repaired each without changing production confirmation/security contracts.
- Selected empty profile alone did not prove inactive-bank secret clearing:
  added an exact production-format 16 KiB fresh unprovisioned-journal comparison
  and a stale inactive-bank secret regression. The stronger read-only final audit
  is bound separately to the unchanged live ledger and archived running observer.
- Per-read HTTP timeouts permitted indefinite slow responses, and AP suffixes
  needed validation before SSH/NM interpolation: added a ten-second absolute HTTP
  deadline, bounded serial writes and exact six-character lowercase hex suffix
  admission. Remote action exclusion remains in place; RPC restoration has a
  separate 270-second ceiling. Normal and optimized regression tests cover these
  observer repairs. The already-running observer was archived before changes.
- Synthetic successful runs could claim physical acceptance: hardware access is
  tracked separately, and synthetic test results cannot qualify target behavior.

Every failed attempt remains retained. Campaigns 1–4 submitted no reset/profile
request. Campaign 5 submitted provisioning checkpoint 1 once; the target cut and
resumed correctly, but the original header-only BTstack observer rejected fresh
local roots. Its original STOPPED ledger is unchanged. A separately hashed
observer reassessment passes the retained readback; it does not promote that
failed campaign to acceptance.

Campaign 6 completed fourteen reset cases, then stopped before submitting a
profile save: the helper used the bootstrap marker on the owner-claim start
route, which correctly returned HTTP 400. The runner restored the original
reserved settings and standard inhibited firmware, with five stable samples.
The header repair has a regression test covering both production route markers.
Campaign 6 remains STOPPED; its accepted individual reset records are retained.

A separate three-case `phase12-profile-continuation/1` plan binds the predecessor
ledger, result and baseline hashes, independently reassesses all fourteen actual
reset readbacks, requires verified predecessor restoration and checks its fresh
reserved baseline against that predecessor before deployment. It cannot repeat
reset cases. The continuation uses fresh request bindings. The declared budget
remains eighteen total submitted operations across the retained history: one
observer-failed reset, fourteen accepted resets and three new profile cases.
Uncertain bodies are never resubmitted.

## Physical acceptance limits

The seed contains a populated consumer station and retained network/TLS profile,
but no operational configuration/schedules, a zero watermark and zero peer bonds.
Named tests can prove effective station preservation, reset phase/epoch resume,
empty operational-bank clearing, local security-root replacement, committed
profile selection and retained network/TLS settings. They cannot qualify
populated schedule/nonzero-watermark preservation, erasure of preexisting
operational records or revocation of populated peer bonds. Those physical
fixtures remain open even though host tests cover the corresponding semantics.

Cuts occur at completed durable phase/page boundaries. Arbitrary/in-pulse power
cuts, torn flash writes, consumer phone/offline commissioning, accelerated session
expiry, GPIO/button timing, actual AP withdrawal and RF/release qualification
remain open. Standard restoration's zero sessions/buffers and network recovery
do not prove actual AP adapter withdrawal on the GP14-OFF image.

## Reproduction and retained evidence

Offline candidate verification (no hardware):

```sh
python3 scripts/phase12_candidate_manifest.py \
  docs/development/phase12-recovery-candidates.json \
  --artifact-root build/phase12-recovery-candidates
```

Behavioral/native-reader verification:

```sh
python3 tests/phase12_recovery_orchestration_tests.py \
  build/phase12-gp14-continuation-host/recovery_flash_inspector
python3 -O tests/phase12_recovery_orchestration_tests.py \
  build/phase12-gp14-continuation-host/recovery_flash_inspector
```

Private firmware, build logs, full backups, ledger/request bindings and captures
remain under ignored `build/phase12-recovery-*` and `build/phase12-orchestration-*`
paths with restricted permissions. Credentials and flash contents are not
published. Reusing an existing campaign for destructive execution is refused.
A new explicitly authorized live plan must retain its own finite scope and
identity; recovery-only may restore an existing campaign without repeating cases.

The six concurrent user documents are preserved against the original snapshot
and excluded from commits: README.md, CONTRACT.md, docs/architecture.md,
docs/browser-api.md, docs/pin-assignment-contract.md and
docs/transmitter-application-contract.md.
