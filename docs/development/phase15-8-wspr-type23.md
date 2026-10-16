# P15.8 WSPR Type 2/3 execution record

Status: implementation in progress; no software or physical acceptance claimed.

## Refreshed baseline and authority

Execution requested on 2026-10-16. Pico is on `devel` at
`14478d2b7509b356d1f146bc2f520ac16d188427`; its only initial dirty path is the
operator-supplied, untracked `phase15-8-execution-prompt.md`. Pi is on `devel`
at `a2437d1bf026e91ea95ac7e2a7a0101e3c4f11a1`, with the existing
`release_tools/Release Punchlist.md` modification. Neither initial path may be
silently included or overwritten. No hardware operation is authorized here.

## Selected Pico design

- Automatic planning only. Ordinary calls retain identical Type 1 symbols and
  saved-six/on-air-four locator behavior. Supported compound calls select Type 2
  with four locator characters, or Type 2 followed by Type 3 with six. Explicit
  angle brackets select Type 3 and require six locator characters.
- The persisted callsign token remains bounded to 12 ASCII characters, including
  explicit brackets. Internal pair hashing receives the unbracketed full call
  directly, so it never needs an oversized temporary bracketed string. Legacy
  broadly valid slash identities remain readable even when planning refuses.
- A bounded portable plan owns at most two 162-symbol arrays. Payload packing,
  bytewise unsigned hashing and the existing channel encoder remain independent
  of SDK, transport, storage and RF adapters. Exact existing power values remain.
- A pair uses adjacent even-minute UTC windows, each beginning at +1 second.
  The scheduler freezes both frames but submits two separate 162-event,
  110.592-second jobs through the existing JobService. It retains and renews
  one ownership lease across the 9.408-second RF-off gap. Each frame receives
  the existing independent UTC/holdover launch check. A single 230.592-second
  timeline was considered and rejected: the current engine guards only the
  initial launch, so it cannot recheck second-window UTC after a clock loss.
- Before the first LOAD/ARM, reserve the second window's start in the existing
  durable watermark. This conservatively consumes every competing occurrence
  through that window and prevents either half replaying after reset, ambiguous
  writes or clock rollback. Expiry must cover both complete frames before CLAIM.
  This policy intentionally skips intersecting configured recurrences.
- Continuation is volatile and bounded. Reset never resumes a half-pair. STOP,
  lost ownership, terminal failure, changed configuration generation, missed
  second preparation window, expired configuration or unacceptable clock cancels
  continuation and releases local ownership. No catch-up or automatic retry.
  The frozen identity/frequency never comes from a later editable configuration.
  Pending pair ownership makes ordinary configuration writes busy.

## Pi release coordination — approved scope

Operator approved the proposed companion scope in this executing conversation on
2026-10-16, including feature-branch commits/pushes and existing CI enablement if
needed. Merge or promotion to Pi devel remains separately gated.

Base: `a2437d1bf026e91ea95ac7e2a7a0101e3c4f11a1`. Proposed isolated companion
branch: `codex/p15-8-wspr-type23`. The primary Pi checkout stays on `devel`.

The existing strict application validator accepts only `wspr_type1` and the
existing station/client UI rejects angle brackets. Proposed compatibility is
explicit versioned application/station support alongside frozen legacy
projections: existing Type 1 workflows continue with the unchanged release Pi;
an old client confronted with a newly selected Type 2/3 station must receive a
tested explicit refusal. New clients discover the new format/plan support and
accept both historical and new resource versions. Unknown versions refuse.
WTP/1, management/1 and /2, Consumer-Radio/1 and Consumer-Recovery/1 stay unchanged.
Exact new paths and shapes will be frozen with executable contract vectors.

Proposed companion scope:

| Boundary | Proposed paths and purpose |
| --- | --- |
| Native management | `src/wtp_integration/configuration.cpp` and directly associated declarations: strict version negotiation, new identity read/write validation and explicit old/new refusal |
| Member UI | `WsprryPi-UI/data/wtp-management.js`: capability-aware station editing, saved/draft plan feedback and strict readback |
| Native/UI tests | `src/tests/wtp_configuration_test.cpp`, affected resource/consumer interop fixtures and `WsprryPi-UI/tests/wtp_resources_interop_test.js`: actual old/new payload and carrier coverage |
| Compatibility pins | Existing interop revision table/scripts: retain all seven rows, add historical p157, advance only current to an exact clean Pico implementation commit |
| Contracts/docs | Only affected management/compatibility records and component notices if required; no operator-doc repository writes |
| CI | Run existing required checks on the companion head; a narrowly scoped feature-branch trigger may require approval if current workflow filters prevent it |

No WSPR-Reference or transmitter component repair is proposed. Any independently
reproduced reference defect is recorded separately; adding a necessary repair
requires additional coordination before editing that component.

Publication order: validate and commit scoped Pico implementation locally; test
the exact clean source with the approved companion and unchanged release Pi;
push the approved companion branch and complete its required CI; publish Pico
`origin/devel` only after its compatibility/rollout gates pass. Pi integration
timing is operator-controlled and requires separate explicit authorization.
No merge or push to Pi `devel` is included. If companion changes are deferred,
continue independent Pico work and withhold incompatible publication and joint
completion.

## Required acceptance and evidence

The handoff's complete acceptance matrix applies: Type 1 goldens; pinned Pi and
independent Type 2/3 payload/hash vectors; exact bounds and malformed inputs;
deterministic complete scheduler/flash/STOP/clock/ownership failure paths;
actual resource journals and bootstrap commissioning; P15.7 no-replay recovery;
shipped browser bundle and desktop/mobile light/dark/keyboard inspection;
ordinary host/CI tests, affected ASan/UBSan with leak checks, both firmware
links and resource reports; exact-source old/new Pi compatibility; adversarial
review, repairs and reassessment. Results will be appended only after execution.

P15.9–P15.14 remain pending. Physical transport, RF decoding, target heap/stack
high-water and P15.13 band/clock qualification remain open.

## Local implementation gate

The implementation candidate passes the complete deterministic host suite
(196/196, 55.23 seconds) and 15 affected ASan/UBSan groups with leak detection
(15/15, 9.68 seconds). These include complete-pair expiry/overflow, midnight,
clock mapping, lease, journal and failed-cutoff behavior, production resources,
real bootstrap commissioning, concurrent sessions and recovery. Bootstrap npm
tests pass 16/16; WTP validation retains 23 schema, seven raw JSON, one framing
and eight transition cases. Both firmware images linked in the existing pinned
configuration; exact clean-source links and resource figures follow below.

Chrome 155.0.8059.40 exercised the shipped page/generated bundle through the
production HTTP/crypto/bootstrap fixture: Type 2/3/pair drafts, invalid locator,
keyboard Tab, `/09` ambiguity, one real encrypted commissioning transaction,
strict saved readback, old-firmware refusal and preserved draft. Twelve captures
cover desktop/mobile and light/dark preferences. Pico keeps its existing light
styling under both preferences. Batched visual inspection found readable,
wrapping feedback and no horizontal overflow. It also caught a pre-transaction
support refusal being replaced by generic retry copy; that path now retains the
specific message and editable draft without creating a transaction.

Execution logs are retained under `/private/tmp/wsprrypico-p158`: final host
`ctest-final2.log`, `sanitize-tests-final.log`, `npm-test-final.log`,
`browser-first-complete2.log` and `browser-first/`. Compiled/software-fixture
results do not establish physical RF or target runtime high-water acceptance.


## Overlap re-review and independent oracle

The operator asked to re-review the proposed `/00`–`/09` refusal. That proposed
restriction was withdrawn before publication. Pi's current encoder accepts both
forms; its unpacker explicitly retains `/Z` with alternate `/09`, and `/Q` with
alternate `/00`. Exact unchanged Linux CLI reproduction is retained in
`/private/tmp/wsprrypico-p158/pi-overlap-rereview.log`. Pico preserves this
ambiguity policy: both identities are supported, the saved call is unchanged,
and a paired Type 3 hashes that requested full call. Its plan exposes
`type2_ambiguous` and `alternate_callsign`, with receiver limits shown in the UI.
The same Type 2 symbols can represent two identities; they cannot establish
which full call a receiver intended. Tests prove shared Type 2 bits and distinct
full-identity Type 3 symbols without forcing base/full-call hash equality.

The independent oracle is official WSJT-X commit
`967c85a6119110788b0df3782cf796485b2cee14` (`lib/wsprd/wsprsim_utils.c`,
`wsprd_utils.c`, `nhash.c`, `fano.c`, associated headers). Exact source SHA-256s,
19 payload/symbol/receiver observations and 33 hash tails are retained in
`tests/wspr_oracle_vectors.json`, separate from the six unchanged Pi goldens.
Its GPL implementation stays in temporary validation storage. Test-only
instrumentation prints the existing `unpk_` result and supplies the documented
byte parity table; it changes no packing/decoding arithmetic. The empty-input
hash takes an upstream early return before masking; the vector records both
that raw value and the explicit WSPR 15-bit reduction. Empty input is not a
valid station. Cold Type 3 receiver observations remain `<...>`; a prior ordinary
compound Type 2 resolves the recorded `PJ4/AA0NT` pair in the independent decoder.
These are software receiver observations, not conducted RF qualification.

Pi's own `type2_decode_pipeline`/CLI tests retain ambiguity on unpacking but its
correlator can clear that flag after a base-call-hash pairing. The real compound
paired test deliberately observes different decoded base/full-call hashes.
Those reference results remain observations; no general full-call resolution
claim is imported and no component repair is included in the approved scope.

## Operator documentation impact (P15.14; read-only)

Inspected `WsprryPi-Docs/AGENTS.md` and the three requested operator pages. The
repository is on `devel`, with pre-existing edits in
`docs/User_Interface/Setup/Transmitter/index.md`,
`docs/User_Interface/Setup/index.md` and untracked
`maintainer/item12-operator-docs-review.md`; all remain untouched.

- `docs/User_Interface/Setup/Signal_Setup/wspr.md`: reconcile its Type 1/3 and
  bracket-implies-pair examples with actual planner behavior. Pico ordinary
  six-character locators keep Type 1/four on air; explicit brackets select a
  Type 3 single; compound six-character locators select Type 2 then Type 3.
  Distinguish Pi's planning preferences from Pico's automatic-only policy.
- `docs/Advanced_Operations/ini_configuration/wspr.md`: explain that Pico's
  stored token bound is 12 including brackets, supported base/affix grammar,
  locator/power constraints, Type 2 overlap and Type 3 receiver context.
- `docs/User_Interface/Setup/Transmitter/index.md`: add negotiated Type 2/3
  member management, old-firmware/old-client refusal, profile-owned station
  commissioning, 230.592-second pair span/9.408-second RF-off gap, reservation
  skips and STOP/reboot behavior. Existing frequency/qualification labels stay.

Required screenshots: ordinary saved-six/on-air-four, Type 2 without locator,
Type 3 hash-context feedback, two-frame plan and observed frame progress,
ambiguous `/09` versus `/Z` with unchanged saved identity, old-firmware refusal,
and preserved draft/fresh saved-state review on desktop and mobile. No operator
pages or screenshots have been published to that independent repository.
