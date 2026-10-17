# P15.8 handoff for WSPR Type 2 and Type 3 support

Status: **executed in another conversation; software roadmap closure accepted
by the operator on 2026-10-16**. The originating conversation prepared this
source review and prompt without executing it. The
[execution record](phase15-8-wspr-type23.md) retains implementation identities,
executor adversarial review/repairs and validation. Pi release integration,
physical acceptance and the separately requested originating post-execution
review remain open. The baseline and instructions below are the historical
handoff, not a request to execute it again.

## Lead repository and reviewed sources

**WsprryPico leads**, with any WsprryPi changes subject to release coordination
and an approved companion branch. Pico owns its portable encoder, station
validation, standalone recurrence, browser and commissioning paths. Use the
current WsprryPi devel application and UI as the implementation example; its
host planner already supplies complete RF-event jobs to Pico through unchanged WTP/1.

**Release constraint:** WsprryPi is close to release. Its devel branch is a
read-only reference for this handoff, not an implementation/publication target.
Coordinate any proposed Pi edits through the operator before changing Pi
product, tests, pins, CI or documentation. The default proposal is an isolated
feature branch from an agreed current devel commit. Merge or promotion to Pi
devel requires separate explicit authorization. This constraint also applies
to later adversarial-review repairs.

Reviewed on 2026-10-16:

| Repository | Reviewed devel HEAD | Working state |
| --- | --- | --- |
| WsprryPico | 14478d2b7509b356d1f146bc2f520ac16d188427 | Clean; P15.7 implementation 26ae596, acceptance 52f5e29, roadmap/handoff closeout 14478d2 |
| WsprryPi | a2437d1bf026e91ea95ac7e2a7a0101e3c4f11a1 | HEAD and origin/devel agree; unrelated release_tools/Release Punchlist.md edit must be preserved |

Both heads were independently compared with origin/devel using git ls-remote.
These identities are orientation pins, not instructions to reset a checkout.
Refresh the actual branches, dirty paths, remotes and intervening changes before
execution. Pi's exact-current Pico interop pin remains
26ae596b540e92f25da37f978321ba1ec5934bdc, distinct from Pico's later documentation
head.

### Current capabilities and implementation gaps

Paths in this section are relative to the named repository.

1. **Pico stores more identities than it can transmit.** Its
   src/encoding/wspr.{hpp,cpp} saves uppercase callsigns of 3–12 characters with
   nonempty slash segments and valid four/six-character locators. Only Type 1
   packing is implemented. wspr_type1_from_station preserves a saved six-character
   locator but transmits its first four. tests/rf_bench_tests.cpp binds existing
   symbols and that behavior. Preserve this accepted default for existing
   ordinary callsigns.
2. **Pico's standalone scheduler builds one frame per occurrence.**
   src/standalone/scheduler.cpp chooses a UTC period/phase plus one second,
   validates clock/expiry, encodes before CLAIM, durably reserves a watermark
   before LOAD/ARM, and emits 162 events over 110.592 seconds. An unsupported
   compound call currently returns UNSUPPORTED_MODE without claiming or reserving.
   Store has one durable watermark, not a paired-plan journal. A second frame
   cannot be added safely by toggling a global counter.
3. **The Pi reference has a planner, encoder and runtime adapter.**
   src/WSPR-Reference/src/wspr/wspr_ref_plan.{hpp,cpp} selects Type1Single,
   Type2Single, Type3Single or Type2Type3Paired. wspr_ref_api.cpp returns one or
   two 162-symbol streams with per-frame metadata. The
   src/WSPR-Transmitter/src/wspr_reference_adapter.cpp adapter validates symbol
   count/range and builds PreparedWsprTransmission. These are separate from
   scheduler policy.
4. **Pi's application freezes a pair across slots.**
   src/scheduling.cpp configure_current_wspr_transmission,
   slot_plan_for_frame and active_wspr_plan preserve the selected prepared
   identity/frequency entry and supply one frame per execution slot. The second
   frame does not make a new policy decision from current editable settings.
   Auto/PreferPaired/RequirePaired are application choices, not firmware timing
   instructions. Port the behavior appropriate to Pico; do not port Linux
   transmitter, GPIO, thread or service machinery.
5. **Actual Pi planning behavior matters more than broad documentation claims.**
   The reviewed planner selects a Type 2 single for a supported compound call
   with four-character locator, a Type 2 then Type 3 pair for compound plus
   six-character locator under automatic/paired planning, and a Type 3 single
   for explicit angle-bracket form with a six-character locator. RequirePaired
   refuses explicit Type 3 and ordinary Type 1 inputs. Bare noncompound plus
   six-character locator currently refuses in that planner; Pico already
   accepts it as a saved-six/transmitted-four Type 1. Do not import that
   incompatibility incidentally.
6. **Pi's UI provides relevant patterns.**
   WsprryPi-UI/data/views/config.php accepts explicit <CALLSIGN>, four/six-character
   locators and Automatic / Prefer paired when available / Require paired.
   data/index.js performs lightweight syntax checks and renders server
   plan_status, rationale and normalized identity, with focused paired-planning
   feedback. src/config_handler.cpp validates the proposed plan before accepting
   a complete WSPR configuration. Use this separation between UI assistance and
   authoritative planning, while retaining Pico's explicit save/recovery workflow.
7. **The Pi reference is not safe to copy without bounds review.**
   wspr_ref_encoder.cpp uses unchecked strcpy into 13-byte call and 7-byte
   locator buffers, and strncpy with slash-position counts. The planner accepts
   broader input than those buffers guarantee. An internally bracketed compound
   call adds two characters; the Pi UI itself allows 32. The encoder also has
   alignment-dependent hash reads and defaults/rounds some invalid inputs.
   These are source-visible hazards, not new runtime reproductions from this
   prompt. Do not carry them into Pico or use invalid reference inputs as a
   trustworthy oracle. Component fix 33b05a60f69f424e764ddb9e8045286f8485b817
   addressed stale callsign bytes; retain repeated long/short encode coverage.
8. **Reference decoder agreement alone is insufficient.**
   WSPR-Reference tests/type2_type3_paired_expected_behavior.cpp explicitly
   expects different decoded hashes for its compound pair, while the current
   correlator requires equality for two messages marked as having hashes.
   run_major_regressions.sh treats two Type 2 matrix observations as non-fatal.
   The reference remains useful for pinned symbol fixtures and implementation
   examples; these tests do not prove general receiver correlation. Do not
   require equality of a derived base-call hash and an on-air full-call hash,
   or waive a real protocol mismatch because this suite labels it expected.
9. **Pico has multiple station-validation boundaries.**
   Trace standalone/config.cpp, provisioning/consumer_profile.cpp,
   network/owner_wire.cpp, bootstrap_web/owner-claim.js and owner-app.js,
   bootstrap_web/owner.html, web/app.js and web/index.html. Owner-claim decoding
   and UI currently bound the stored token to 12 characters and exclude angle
   brackets. Broad storage validity and actual encodability are separate.
   API PUT station additionally enforces wspr_type1_from_station and returns
   unsupported_station_encoding. Consumer profile-owned station fields still
   require transactional setup instead of ordinary config writes.
10. **A capability change needs Pi adoption.**
    Pico application/resources.cpp and
    docs/protocol/transmitter-application-1.schema.json freeze station_encoding
    as wspr_type1. Pi src/wtp_integration/configuration.cpp application_shape
    requires that literal and its station validator excludes bracket forms;
    the management UI also names the Type 1 write path. Merely changing Pico's
    advertised string can break otherwise unrelated resource/config reads.
    Resolve versioning/negotiation and all affected strict validators together.
11. **Recent recovery work must survive this slice.**
    P15.7 adds authenticated retirement, readback/review before another write,
    strict saved-config checking, sent-once commissioning receipts and actual
    PicoBootstrapServer tests. New identity syntax must round-trip through those
    paths without causing a valid response to be called malformed, losing a
    draft, replaying a save or weakening session/target/revision checks.
12. **Operator documentation contains a known scope discrepancy.**
    WsprryPi-Docs/docs/User_Interface/Setup/Signal_Setup/wspr.md describes Type 1/3
    pairing for some bracket/ordinary-call cases. That is not the reviewed Pi
    planner's implemented explicit-Type-3-single behavior. Treat it as guidance
    requiring reconciliation, not proof of an implemented Type 1/3 planner.
    The operator documentation repository remains read-only for this task.

Pi's WSPR-Reference README identifies repository-root MIT coverage; Pico already
retains src/encoding/WsprryPi-LICENSE.md. Verify exact provenance and notices for
every reused portion. Do not bring the desktop decoder, JSON dependency or CLI
into firmware solely to reuse packing code.

The official [WSJT-X protocol documentation](https://raw.githubusercontent.com/WSJTX/wsjtx/master/doc/user_guide/en/protocols.adoc)
describes Type 2 as compound identity/power without a locator and Type 3 as a
15-bit identity hash with a six-character locator and power. All three use the
same 50-bit payload and 162-symbol channel format. This protocol evidence is
distinct from Pi's UI/planner policy and from actual receiver/RF acceptance.

The [P15.7 acceptance record](phase15-7-recovery.md) retains 193/193 host tests,
12 sanitizer groups, seven compatibility rows, firmware links and scoped browser
evidence for its exact source pair. Those results were not rerun here and do
not qualify a future Type 2/3 implementation. The
[Phase 15 checklist](../implementation-plan.md#phase-15-acceptance-record)
keeps saving independently of transmit readiness, hostname/forms and new RF
qualification outside P15.8.

## Prompt for the executing conversation

Implement **P15.8 — WSPR Type 2/3 support in WsprryPico**, using the current
WsprryPi devel application and UI as the source-backed example above.

Use these repository and branch boundaries:

- /Users/lbussy/GitHub/WsprryPico — work on **devel** for portable planning/encoding,
  standalone integration, validation, API/capability contracts, commissioning,
  UI and tests.
- /Users/lbussy/GitHub/WsprryPi — use the existing **devel** application/UI
  read-only as reference. Propose necessary management/client/UI compatibility,
  fixture, pin, CI or documentation changes for release coordination. After
  agreement, implement only that scope in an isolated checkout on the approved
  feature branch, preserving the primary checkout and unrelated release/RP1 work.

Once the operator executes this prompt, implement and validate the feature.
Do not stop at another plan or at unused encoding functions. Complete the
executor's adversarial assessment/repair/reassessment, scoped commits and pushes,
then return the evidence needed for the originating conversation's separately
requested post-execution assessment. All implementation and publication remain
subject to the Pi release boundary below; execution is not permission to alter
Pi devel or merge a companion feature branch.

### 1. Refresh the baseline and define acceptance

Read applicable AGENTS.md files and Pico README.md, CONTRACT.md,
docs/architecture.md, docs/development/README.md, docs/development/standalone.md,
the P15.1–P15.7 contracts/acceptance and shared transmitter application contract.
In Pi read component guidance, the WSPR-Reference API/planner/encoder/tests,
WSPR-Transmitter adapter, scheduling.cpp, config_handler.cpp, config
serialization/deserialization, and the application/UI files listed above.
Inspect docs/simulated-backend.md before application-level simulated tests.

Inspect branches, status, staged/unstaged diffs, remotes and intervening commits.
Preserve all user changes, including the recorded Release Punchlist edit.
Do not reset, stash, force-push or mix unrelated work into a commit. Keep Pico
implementation on devel and Pi implementation, if approved, on its coordinated
feature branch. Do not switch the primary Pi checkout away from its release
work. Isolated historical sources are for validation only.
Verify retained build environments and exact dependency identities before reuse.

#### Coordinate the companion scope before Pi edits

First identify whether P15.8 can preserve current Pi devel behavior without Pi
changes. Produce a concrete compatibility proposal listing affected Pi paths,
why each change is necessary, the exact base commit, proposed branch, test/CI
impact, publication order and intended integration timing relative to release.
The default branch proposal is codex/p15-8-wspr-type23 in an isolated checkout
from the agreed devel base; reuse an existing approved companion branch if one
already serves this work.

Obtain and record the operator's coordination decision before modifying Pi
source, UI, tests, compatibility pins, workflows or documentation. Do not contact
other chats or maintainers unless the operator authorizes that communication.
An approved feature scope permits its implementation, validation, scoped
commits and push to that approved branch; it does not permit merging, rebasing
the release branch, changing release content, or pushing Pi devel. Work directly
on Pi devel only if the operator explicitly approves that exception after
reviewing the release impact.

Continue independent Pico work and read-only Pi review while coordination is
pending. Build/reference validation may use isolated clean copies and external
outputs without changing the release checkout. Do not bypass the boundary by
editing an unapproved Pi copy and treating it as a test fixture. If Pi changes
are unnecessary, demonstrate that using the unchanged release source and
record its exact commit. If they are necessary but deferred, report the remaining
dependency and withhold incompatible publication or joint-completion claims.

Record the selected behavior, limits, plan representation, scheduling/reservation
policy, compatibility design and acceptance matrix in
docs/development/phase15-8-wspr-type23.md before the main implementation.
Make routine bounded design choices and proceed; do not use this planning step
as a substitute for implementing the feature.

The minimum delivered automatic behavior is:

| Station input | Required result |
| --- | --- |
| Ordinary encodable call + four-character locator | Existing Type 1, identical symbols |
| Ordinary encodable call + six-character locator | Preserve Pico's default Type 1 using the first four characters on air; retain all six in settings/readback |
| Supported compound call + four-character locator | Type 2 single; clearly explain that this frame does not carry a locator |
| Supported compound call + six-character locator | Type 2 followed by Type 3, same intended full identity/power and original selected RF frequency |
| Explicit <CALLSIGN> + six-character locator | Type 3 single using the inner full identity for hashing; explain receiver hash-context limits |
| Explicit Type 3 + four-character locator | Clear validation refusal before transmitter claim/reservation |
| Unsupported compound syntax or unencodable identity | Preserve any previously valid stored identity; refuse transmission without stripping/truncating or substituting another station |

Support protocol-valid prefix and suffix forms using Pi's tested examples
AA0NT/1, AA0NT/12, W0/AA0NT, PJ4/AA0NT, AA0NT/P and AA0NT/M, plus explicit
<AA0NT> and <AA0NT/12>. Determine exact legal prefix/suffix grammar from packing
and independent vectors, not a generic slash regex. Reject empty/multiple
unsupported segments, impossible base calls and malformed brackets rather than
silently producing a different identity. Test the /Z and numeric-overlap region
using the actual encoded values; do not copy inaccurate prose examples.

Automatic behavior is required. Pi's paired-preference controls are an example,
not a requirement to add an unrelated configuration system. If explicit planning
preferences are needed or exposed, use Automatic, Prefer paired when available
and Require paired consistently, define their complete matrix, retain a
compatible default for old saved configurations, and carry them through actual
persistence/API/UI/runtime. Never ship a selector whose value the scheduler
ignores. Type 1/3 automatic pairing is outside the reviewed Pi implementation;
do not claim it exists or add it incidentally to this Type 2/3 slice.

### 2. Implement a bounded portable planner and encoder

Keep owned C++ under src/encoding or another justified existing portable layer.
Separate station storage validity, transmission planning, payload packing and
channel encoding. A plan must be bounded to one or two complete fixed-size
162-symbol arrays with explicit type/order and enough diagnostic metadata for
the application. Reject unsupported inputs before side effects. Reuse the
existing convolution/interleave/sync path where correct and keep Type 1 symbols
unchanged.

Adapt reviewed MIT source as appropriate; document source commit/files,
copyright and algorithm provenance. Do not link the complete desktop reference
library, decoder, nlohmann JSON or Linux transmitter into firmware. Do not
silently change the independent WTP/1 wire or add type2/type3 transport modes:
these are different WSPR payloads carried by the same finite RF-event mechanism.

Use explicit lengths and byte operations. Handle the full stored token, inner
call, optional angle brackets and NUL separately; internal pair construction may
need two more characters even when the saved identity fits existing bounds.
Do not copy unchecked strcpy/strncpy, alignment-dependent overreads or aliasing
assumptions from the example. Hash results must be identical for aligned and
unaligned input on host and RP2350, including every tail length. Use specified
unsigned overflow and exact 15-bit hash reduction. Inspect seed, prefix/suffix
packing, locator rotation, power/type fields, zero tail and all 162 symbols.

Define maximum supported identity length across persisted token, profile wire,
API schema, HTML, browser helpers and internal hashing. Prefer preserving
existing stored bounds unless a justified versioned extension is necessary;
never silently truncate a valid saved value to make it fit. Bracket syntax is
a planning request and must not become part of the hashed callsign.

Retain exact accepted WSPR power values 0, 3, 7, 10, 13, 17, 20, 23, 27, 30,
33, 37, 40, 43, 47, 50, 53, 57 and 60 dBm. Do not import Pi's low-level power
rounding/clamping or invalid-locator substitution. Power remains reported message
content, independent of RF drive/output. Require A–R locator fields, numeric
square and A–X subsquare; invalid input never becomes AA00AA on air.

Preserve existing broad storage acceptance for legacy slash identities that
remain unencodable. Do not make a parser change render a previously readable
configuration/profile unusable merely to tighten a new planner. Any necessary
migration must be explicit, lossless and tested under interrupted writes.

### 3. Integrate complete plans into the existing standalone authority

The real standalone scheduler must emit the selected single/pair behavior,
not only bench helpers or a host CLI. Follow Pi's principle of freezing the
selected plan for all its frames. Do not re-read editable identity, power or
frequency when preparing the second half.

Specify pair slots relative to Pico's existing even-minute UTC plus one-second
start, and how pair continuation interacts with its configurable period/phase
recurrences. Match Pi's separate WSPR-window intent; never concatenate 324
symbols into one 110.592-second frame or send the second frame immediately
after the first. Keep 162 symbols, exact existing rational boundaries,
1.464843750 Hz tone spacing, full frame duration and selected RF frequency.
Pico's base frequency is already RF; do not add Pi's dial-to-RF offset again.

Choose and justify the smallest representation through the existing JobService:
one fully loaded finite timeline with an explicit RF-off inter-slot gap, if
all existing semantics permit it, or scheduler-owned bounded continuation
through separate finite jobs. Preserve observable timing/STOP/ownership and
reservation guarantees for the chosen model. Do not introduce a second
scheduler, host dependency, per-symbol network delivery or a new protocol.

Before admitting the first frame, establish that the complete pair can fit the
selected recurrence/expiry policy. Specify:

- Whether a pair consumes adjacent even-minute slots or eligible configured
  occurrences, and how other configured schedules are reserved/skipped without
  overlap or silent frequency/identity changes.
- Durable reservation of every occupied slot, job IDs and at-most-once behavior
  after ambiguous LOAD/ARM, journal failure, process reset and clock rollback.
  A single watermark must not cause a duplicate first half or a stray second
  half after restart. Conservative skipping is acceptable when explicit.
- What happens if the second slot is unavailable, expired, missed, stopped,
  preempted by an external owner or loses acceptable UTC/holdover quality.
  Never run it late as catch-up or restart an uncertain pair automatically.
- How configuration/profile generation, enabled state, STOP, restart inhibition
  and changed pin/network state invalidate pending continuation. No second half
  may use old identity with newly saved metadata or outlive a stop request.
- Complete pair memory/event/duration/ownership budgets and the interaction with
  JobService completion/release. Validate the lease and cleanup model across
  the inter-frame gap, not only while RF is active.

Keep RF local to RP2350/core 1 with networking/flash/crypto on core 0. Preserve
clock, engine limits, frequency policy, opt-ins, STOP/watermarks, output-inhibit
latches and all existing ownership/fault guards. Do not change RF sample clocks,
band qualification or GPIO routing to demonstrate message-format support.
Host-produced Type 2/3 WTP jobs must continue to work independently of the new
Pico-local encoder.

### 4. Align station, setup, capabilities and UI

Trace every station lifecycle, from defaults/parsing through validation,
serialization, journal/profile persistence, API/readback, setup crypto, saved
form population, scheduler and reboot. Required boundaries include:

- Pico Config v1 and settings-preserving update/replacement; Console CONFIG.
- Scoped station resource and application readback, including profile-owned
  refusals and saved versus effective values.
- Consumer profile parsing/serialization, owner-claim wire/plaintext, public
  saved-station prefill and authenticated station commissioning on station/AP.
- Embedded setup/owner pages, shipped radio bundle, standalone web app and the
  P15.7 strict saved-config/draft/readback validators.
- Pi native configuration/resource validators, existing management coordinator,
  consumer station/AP and engineering mTLS paths, and member-management UI.

Broaden only the formats needed for P15.8. Keep consumer profile station writes
under the existing transactional setup authority. Do not enable ordinary
profile-owned station mutation or implement P15.9's separation of valid-field
saves from transmit readiness here.
Preserve P15.1 omission/password-null behavior and P15.7 sent-once save receipts,
session retirement, preserved drafts and fresh readback/review.

Version the capability/schema change deliberately. The current application/1
schema and Pi validator name wspr_type1 exactly and exclude brackets. Define
truthful format/plan support and old/new negotiation; update source contracts,
schemas/vectors, runtime serializers and any approved companion validators as a
coordinated change. Preserve the release Pi's supported existing workflows where
possible, exposing new syntax through explicit negotiated/versioned support.
Do not keep advertising Type 1 only while adding hidden formats, or change a frozen
literal/shape and call it compatible. Preserve management/1 and management/2,
Consumer-Radio/1 and Consumer-Recovery/1 unless a separately demonstrated need
requires independent versioning. WTP/1 remains unchanged.

New Pi must still handle supported old Type-1-only Pico. For old Pi against new
Pico, preserve safe supported behavior or provide a tested explicit refusal
for unsupported new formats under the agreed rollout policy. A change that
breaks existing release-Pi management globally requires explicit coordination
and must not be published before its companion/rollout dependency is resolved.
No silent stripping of brackets/affixes, truncated
locator/power, fallback write strategy or permissive accept-any-capability path.
Read and write validators must agree, so a successfully saved valid Type 3
identity remains readable after refresh/restart.

Use the **Impeccable** skill before UI changes, including Pi's mandatory workflow.
Use current Pi app/UI as the reference for identity syntax, focused rationale
and plan feedback, while preserving Pico's lightweight incumbent design.
Show selected message type, one/two-frame consequence and locator/hash limits
where the operator makes the decision. A Type 3 hash is not a plaintext full-call
announcement and receiver context may be needed; do not promise complete
receiver resolution merely because encoding succeeded.

Keep client syntax assistance separate from authoritative firmware planning.
Errors name the unsupported input and correction, preserve drafts and do not
save another format automatically. Show observed saved plan versus current
draft, and frame progress/cancellation honestly. If an added preview endpoint
is needed, make it bounded, authenticated under the existing carrier policy,
side-effect-free and versioned; no new RF/start control is implied.

Render actual shipped Pico and affected Pi UI at desktop/mobile sizes with
light/dark preferences, plus keyboard and long-error checks. Pico currently
uses light styling for both preferences. Apply bounded Impeccable inspection,
one repair batch and a confirmation pass. Regenerate checked-in bundles using
the existing pinned npm process; retain attribution. Do not consolidate pages,
add hostname editing or alter titles as incidental work.

### 5. Prove symbols, receiver semantics and failure behavior

Add regressions that fail on the reviewed Pico baseline and exercise the actual
planner, encoder, scheduler, stores, handlers, commissioning and browser producer.
Mocks belong at hardware/network boundaries; parser-array or UI-source-string
assertions alone do not prove delivered support.

1. Preserve existing Type 1 golden outputs and standard-call/six-character-locator
   behavior. Compare all 162 symbols for the Pi pinned Type 2/3 golden cases;
   add fixed inputs covering prefix lengths, one-character/numeric suffixes,
   two-digit suffixes, explicit bracket calls and compound/six-character pairs.
2. Use an independently sourced protocol oracle or known-good vectors for
   Type 2/3 payload/hash/receiver cases that the Pi reference does not establish.
   Identify exact source/version/tool, input, hash normalization and expected
   receiver result. A synthetic baseband/WAV decode with a verified existing
   independent decoder is software evidence, not RF qualification. Do not
   download/install unrelated tools without need or copy incompatible-licensed
   upstream code into MIT firmware.
3. Investigate any disagreement among Pi symbols, its unpacker/correlator,
   official protocol and the independent oracle. Record whether it is an
   encoder defect, reference-decoder limitation, ambiguity or product policy.
   Do not silently regenerate goldens, force hash equality, tolerate wrong
   full-call resolution, or label two valid-looking frames a correlated pair.
   Preserve existing reference observations separately from new acceptance.
4. Reject malformed/empty/nested brackets, whitespace/non-ASCII/NUL, overlength
   tokens, empty/multiple slash segments, invalid base calls, unsupported
   prefix/suffix lengths, noncanonical types, invalid locators, unsupported
   powers and overflow. Cover exact maximum lengths with/without brackets and
   internally bracketed maximum compound calls. Reuse encoder instances across
   alternating long/short and Type 1/2/3 inputs; prove no stale-byte dependence.
5. Exercise all selected plan/preferences and complete scheduler behavior under
   deterministic clocks. Check exact event frequencies/durations, RF-off gap,
   pair order, frozen identity, frame count/status, lease/cleanup, expiry before
   and inside the second slot, intersecting recurrences and near-midnight slots.
6. Inject failures before/after each durable reservation, LOAD, ARM, first
   completion, gap and second-frame transition. Cover reboot/rollback, skipped
   slots, missed poll windows, time-quality loss, ownership conflict, allocation/
   engine/flash failure, STOP, profile/config change and restart inhibition.
   Count reservations and engine calls; prove no duplicate, replay, orphan half,
   leaked owner, unauthorized output or changed watermark on pure validation.
7. Drive actual old/new UI-emitted payloads through Pi adapters and Pico journal
   handlers for each supported format and carrier. Verify unchanged unrelated
   fields, extension opt-ins, schedules, credentials and pins. Unknown capability/
   schema/type shapes refuse. A valid changed identity must survive stored
   readback, reboot/profile adoption and strict client parsing.
8. Exercise real PicoBootstrapServer station commissioning, receipt/generation
   checks and profile-owned resource refusal with new formats. Include rejected
   and lost saves, terminal-failure correction, P15.7 full-capacity recovery and
   fresh readback/review. Do not replace this with only direct BrowserApi calls.
9. Use real browser contexts for representative Type 2, Type 3 and pair input,
   invalid-locator feedback, old-firmware refusal, stale/conflicting edits and
   saved-state reconciliation. Verify the shipped generated bundle, clear
   plan/frame feedback, preserved drafts and no automatic transmission/replay.
10. Retain host-generated WTP finite-job, multi-session/concurrent HTTP, recovery,
    clock/STOP/ownership and existing frequency policy regressions. This
    message-format feature cannot redefine Phase 14 support labels.

Reference source hazards discovered outside the necessary Pi adoption scope
must be documented with precise reproduction/impact. Prefer a safe local Pico
adaptation and independent oracle to broad unrequested repairs of WSPR-Reference.
If a companion component repair is actually necessary for this slice, identify
the component boundary, include it in the release-coordination proposal and
obtain the applicable approval before editing. Keep an approved repair on the
approved companion branch and run its standalone plus parent checks.

### 6. Validation environment and source pairing

Use the existing documented hardware-free Linux validation path and verified
pinned dependencies. **Do not attempt local macOS C++ compilation or linking of
WsprryPi** unless the operator explicitly authorizes it or confirms repair of
the local toolchain. No new SDK/tool installation is incidental to this task.
Keep credentials, generated firmware, raw captures and scratch builds out of Git.

Pico examples, with verified local Mbed TLS/lwIP source paths:

    cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
      -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
      -DWSPRRY_PICO_TEST_MBEDTLS_PATH="$MBEDTLS_SOURCE" \
      -DWSPRRY_PICO_TEST_LWIP_PATH="$LWIP_SOURCE"
    cmake --build build-host --parallel 3
    PHASE115_ENDPOINT_DRIVER="$PWD/build-host/endpoint_driver" \
      ctest --test-dir build-host --output-on-failure
    python3 scripts/validate_wtp_contract.py
    npm --prefix src/network/bootstrap_web test
    npm --prefix src/network/bootstrap_web run build

Run the complete candidate host suite and affected ASan/UBSan with leak checks,
including encoder/planner bounds/hash tails, scheduler/storage, API/resources,
consumer profile/setup/claim, actual commissioning, concurrent sessions and
recovery. Add the new tests to ordinary build/CI entry points; do not rely only
on an untracked scratch script for acceptance.

Cross-link WsprryPico and WsprryPico-StandaloneRF using verified pinned SDK/Arm
inputs and retained configuration or documented presets. Keep linked allocator,
stack, core-topology and RF placement checks. Report code/static RAM/stack and
bounded plan/event allocations. Preserve the 32 KiB authority reserve and
cooperative HTTP/crypto service budgets. Distinguish estimates/compiler outputs
from unmeasured target heap/stack high-water and actual RF timing.

For the Pi reference, its existing Linux runner is:

    WSPR_REFERENCE_BUILD_DIR="$REFERENCE_BUILD" \
      bash src/WSPR-Reference/tests/run_major_regressions.sh

Run from an isolated checkout of the agreed Pi source with a verified external
build path. The script configures
and builds the component itself. Supplement its non-fatal observations with
assertions for the exact new acceptance matrix; a green runner alone does not
close the known decoder/correlation limitations. Run relevant paired/scheduler,
configuration and UI tests from the current Makefile and fixtures as well.

Pi examples from src in the isolated approved-branch or unchanged-reference
checkout, on Linux:

    make wtp-config-test wtp-api-test SUDO=
    WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 make wtp-network-runtime-test \
      BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= JOBS=2
    make wtp-config-interop-test SUDO= \
      PICO_SOURCE="$PICO_SOURCE" MBEDTLS_SOURCE="$MBEDTLS_SOURCE"
    make wtp-network-interop-test SUDO= \
      PICO_SOURCE="$PICO_SOURCE" MBEDTLS_SOURCE="$MBEDTLS_SOURCE"

Verify target names/options before invocation. Include affected UI unit/browser
and Pi sanitizer checks. Preserve the existing seven compatibility rows:
legacy, extended, p152, p153, p154, p156 and current. When advancing current,
retain 26ae596b540e92f25da37f978321ba1ec5934bdc as a historical p157 row with
its original strict expectations. Test new Pi against old/new Pico and the
reviewed pre-P15.8 Pi product against new Pico for explicit work/refuse behavior.
Never bypass clean-source guards or repoint every old fixture to the candidate.

Review/test Pico, create an authorized scoped implementation commit on devel,
then use that exact clean source for paired Pi tests. Pi pin updates belong
only to the approved companion branch after coordination, never automatically
to its release devel branch. Preserve unrelated dirty files outside those
validation checkouts.
Any production repair requires a new source identity and affected paired retest.
Record implementation versus later documentation publication SHAs separately.
Check required CI on the actual approved companion branch/head and retain
failure/rerun history without weakening assertions or broadening timeouts to
hide defects. Do not push or merge to Pi devel merely to trigger CI; coordinate
any feature-branch CI enablement instead.

Use retained isolated Linux environments where suitable, no device mounts and
networking disabled during tests where feasible. Supply the existing pi fixture
user, Linux endpoint driver and writable external output/config-local mounts
when required. Revalidate cached binary/source identity before treating an old
fixture executable as current.

No hardware, flashing, GPIO/RF, service/install or station administration is
authorized by this software prompt alone. If the operator supplies a current
connected setup and finite limits, follow that authorization and repository
rules, identify board/firmware/clock/mode/pins/receiver/RF path, preserve/restore
settings and keep acceptance narrowly bound to those actual results. Otherwise
leave target transport, RF decoding, heap/stack high-water and broad band/mode
qualification open. Historical setup descriptions are not a current connection.
P15.13 retains the later band/clock qualification campaign.

### 7. Executor adversarial review and repair

After implementation and normal validation, assess the complete diff and evidence
adversarially. Challenge encoding correctness versus merely matching a related
encoder, hash normalization/collisions, prefix/suffix overlap, maximum lengths,
unaligned/tail reads, signed arithmetic, stale object state and unsupported-input
substitution. Challenge paired UTC policy, reservations, reboot/rollback,
expiry/STOP, ownership, frozen configuration and second-frame failure behavior.

Also challenge every API/UI/profile bound, version/negotiation/refusal path,
readback of new syntax, profile-owned station behavior, preserved unrelated
configuration and P15.7 no-replay recovery. Verify the actual source/bundle/native
binary pair behind each test, the meaning of reference decoder observations and
the separation between software, receiver simulation and physical RF claims.
Audit the release boundary too: no unapproved Pi changes, release-branch push,
pin advancement, workflow modification or merge may be hidden in the feature
or its validation.

Use an independent reviewer/context when available and authorized, and label
self-review honestly. Record each actionable finding with severity, exact trigger,
file/line, repair and regression evidence. Fix findings, rerun affected checks,
and perform another adversarial assessment of the repaired result. Repeat until
no actionable issue remains within the accepted software scope. Do not waive
required software assertions because another large suite passed.

### 8. Documentation and publication

Update current encoding/planning, standalone scheduling/status, station/setup,
API/capability/schema and compatibility records, development indexes and
docs/development/phase15-8-wspr-type23.md. Preserve historical P15.1–P15.7
acceptance and implementation identities. Record deliberate differences from
the Pi example, receiver/hash limitations, any omitted planning preferences,
unresolved reference defects and the exact selected pair reservation policy.

Mark P15.8 complete only for acceptance actually demonstrated. Keep P15.9–P15.14
pending. Inspect /Users/lbussy/GitHub/WsprryPi-Docs and its instructions read-only,
especially docs/User_Interface/Setup/Signal_Setup/wspr.md,
docs/Advanced_Operations/ini_configuration/wspr.md and
docs/User_Interface/Setup/Transmitter/index.md. Record exact P15.14 guidance and
screenshots required, including the documentation/code mismatch, supported
identity lengths, saved-six/on-air-four behavior, Type 3 context and pair timing.
Do not edit/publish the independent operator documentation repository without
explicit authorization.

Review complete and staged diffs, component/UI portions, whitespace and scope.
Commit scoped Pico work on devel and push origin/devel only when its compatibility
and coordinated publication conditions are met. Commit approved Pi work on its
approved companion feature branch and push only that branch. Preserve unrelated
edits and concurrent changes; never force-push. A Pi devel push or feature merge
requires the separate explicit integration authorization recorded above.
Independently verify local HEAD against git ls-remote and report remaining dirty
paths for the exact branches actually pushed. Do not manufacture empty commits,
create PRs/releases or publish firmware.

Return an evidence packet with implemented behavior and exclusions, design and
source/provenance decisions, exact implementation/published SHAs and source pairs,
compatibility rows/pins, commands/results and CI head/run, actual browser/
Impeccable evidence, all findings/repairs/reassessments, documentation impact,
remaining physical/reference limits and branch/worktree/remote state. Include
the Pi coordination decision, feature branch/base, pending integration/rollout
dependencies, and whether the unchanged release Pi remains compatible. Successful
feature-branch checks are not evidence that the Pi release branch adopted the
feature. Do not close joint acceptance while a required compatibility or rollout
gate remains unresolved; report a bounded Pico/companion result instead.

### 9. Originating conversation review after operator execution

The operator will return the completed packet to the originating conversation.
At that point, inspect the actual finished code and evidence afresh and perform
the separately requested adversarial assessment. The executor's review does not
stand in for this later assessment.

If it finds actionable issues, repair them within this slice, rerun affected
checks and exact-source interop/CI as required, then conduct another adversarial
assessment. Repeat until no actionable issues remain. Commit and push scoped
Pico repairs or review/closeout records to Pico devel when its publication gates
are met. Any Pi repairs must retain the recorded release-coordination boundary
and use the approved companion branch; coordinate additional scope before editing
and obtain separate explicit authorization before merge or promotion to Pi devel.
If a companion branch has already been integrated, re-establish its current
release constraints rather than assuming that old approval permits new devel
edits. Independently verify the actual pushed branches, and report findings,
fixes, final validation, documentation impact and retained integration/physical
limitations. Preserve unrelated changes and earlier evidence.
Do not claim that this review occurred while only preparing this prompt.
