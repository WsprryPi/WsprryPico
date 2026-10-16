# P15.8 WSPR Type 2/3 execution and evidence

Status: **complete within the documented software scope**, accepted by the
operator for P15.8 roadmap closure on 2026-10-16. Final-source implementation
and validation passed, including all 12 companion CI jobs. This is a bounded
Pico/approved-companion result. Pi release integration, the originating
conversation's independent post-execution review and physical acceptance remain
open separately.

The roadmap closeout verified published Pico devel
`4e96f0e71a93a529c01e8ec202a0f39422322c33`, the clean approved Pi companion at
`6d5e73430bfbacdb8cfc29c3fe41089aa8ae5fcb`, and the reported CI run's exact head
and twelve successful jobs. This documentation closeout did not rerun the
implementation tests or perform the pending independent post-execution review.
The tested Pico implementation pin remains `804e8a0` below; later report and
roadmap commits are separate from that tested product source.

## Final identities and authorization

| Purpose | Identity |
| --- | --- |
| Original Pico devel | `14478d2b7509b356d1f146bc2f520ac16d188427` |
| Final Pico implementation/current interop pin | `804e8a06585ec5a0e650e69fcd71ada398b6cc9f` |
| Approved Pi base/reviewed pre-P15.8 native product | `a2437d1bf026e91ea95ac7e2a7a0101e3c4f11a1` |
| Pi native product implementation | `41c1dbd42620da6d5595b3ca0171c15ad6c9ee5f` |
| Published companion/CI head | `6d5e73430bfbacdb8cfc29c3fe41089aa8ae5fcb` |
| Companion branch | `codex/p15-8-wspr-type23` |

The operator executed the handoff on 2026-10-16 and explicitly approved the
companion scope before Pi edits: strict versioned native management/client/UI
support, associated tests/contracts, compatibility pins and existing feature-
branch CI enablement. Commits/pushes were authorized only to that Pi branch;
merge/promotion or a Pi devel push was excluded. Its isolated checkout is
`/private/tmp/wsprrypi-p158/source`. No Pi product code changed after `41c1dbd`;
later companion commits add tests, pins and evidence.

Pico implementation/push is on devel. The final report/probe publication commit
is separate from the implementation pin; its verified full SHA is returned in
the completion message. Intermediate Pico `6bcaf42`, `bcd7f03`, `99ce696` and
`0c02423` are superseded, not the final source pair.

No device, flashing, GPIO, RF, service/install or station-administration action
was performed. No PR/release/firmware publication or other-chat/maintainer
message was created. Operator-docs remained read-only.

## Delivered automatic behavior and bounds

| Stored station input | Selected complete plan |
| --- | --- |
| Ordinary encodable call + four-character locator | Identical existing Type 1 |
| Ordinary call + six-character locator | Type 1 with first four on air; all six retained |
| Supported compound + four-character locator | Type 2 single; no locator in that frame |
| Supported compound + six-character locator | Type 2 then Type 3, requested full identity/power |
| Explicit `<CALL>` + six-character locator | Type 3 single; hash excludes brackets |
| Explicit Type 3 + four characters or unsupported syntax | Explicit refusal before transmitter claim/reservation |

The stored token remains 3–12 ASCII characters, including explicit brackets.
Supported compound prefixes are 1–3 alphanumerics before a valid Type 1 base;
suffixes are one alphanumeric or two decimal digits after a valid base. A
prefix may itself be a base call (`W1A/AA0NT`). Maximum supported compound is ten
characters, or twelve with brackets. Empty/nested/malformed brackets, NUL,
non-ASCII, whitespace, unsupported multiple slashes, impossible base calls and
oversized affixes refuse without truncation/substitution. Existing broadly valid
legacy slash identities remain readable; unchanged identity bytes survive
unrelated complete settings saves even if transmission planning refuses them.

Locators require A–R, two digits, and optional A–X subsquare. Exact reported
powers remain 0, 3, 7, 10, 13, 17, 20, 23, 27, 30, 33, 37, 40, 43, 47, 50,
53, 57, 60 dBm. Power is message content, independent of RF drive/output.
Only automatic planning is exposed; no ignored preference selector or Type 1/3
pair was added. Host-produced finite WTP jobs remain independently supported.

`/00`–`/09` are supported, matching Pi's ambiguity policy. They share Type 2
bits with `/Q`–`/Z`; `/09` and `/Z` are the same Type 2 payload. The saved call
is unchanged, and paired Type 3 hashes the requested full call. Plan metadata
and UI disclose the alternate spelling/receiver ambiguity. No general receiver
collision/full-call resolution guarantee is claimed.

## Frozen pair and authority contract

A bounded portable plan owns at most two fixed 162-symbol arrays. The existing
JobService receives two separate complete 162-event, 110.592-second jobs in
adjacent even-minute UTC +1-second windows. Both arrays, identity/power and the
original Pico RF base frequency are frozen; there is no second policy decision,
Pi dial offset, per-symbol network dependency or second scheduler.

Nominal start separation is 120 seconds, RF-off gap 9.408 seconds and overall
span 230.592 seconds. Each frame retains its independent local UTC/holdover
launch guard and accepted launch second. Complete-pair expiry preflight includes
the entire final launch second and rejects monotonic/UTC overflow before claim.
These are software timing contracts, not measured physical launch results.

Before first LOAD/ARM, the existing durable watermark reserves through the
second slot's start. All intersecting configured occurrences through that slot
are conservatively consumed. A single 60-second owner lease, renewed every
30 seconds, spans both frames/gap. Configuration writes are busy while owned.
Continuation is volatile: reboot, rollback, STOP, changed generation, loss of
clock quality/ownership, missed preparation, journal/engine/allocation failure
or restart inhibition cannot replay a first half or resume a stray second half.
Failed cutoff retains failed/output-unknown authority for explicit recovery.
No catch-up or automatic retry is introduced. Existing core/RF/frequency/pin/
output-inhibit guards and the 32 KiB authority reserve remain.

A single 324-symbol timeline was rejected because the engine guards only its
initial launch; separate jobs permit the required second-window time check.

## API, station persistence and commissioning

Frozen application/1 and station/1 shapes and `wspr_type1` literal remain.
Existing release-Pi Type 1 workflows work. A selected encodable Type 2/3 station
or bracket form returns explicit `409 unsupported_station_encoding` on those
legacy projections. Unknown new support refuses rather than falling back.

The exact additive `application_resources_v2` descriptor advertises:

| Method | Path | Meaning |
| --- | --- | --- |
| GET | `/api/v1/application/2` | `transmitter-application/2`, station/2, `wspr_type123_auto`, plan |
| GET/PUT | `/api/v1/station/2` | Complete versioned station resource |
| PUT | `/api/v1/config/2` | Config v1 content with explicit new-format admission |
| POST | `/api/v1/config/update/2` | Existing config-update/1 envelope/omission semantics |
| POST | `/api/v1/wspr-plan` | Authenticated, bounded, pure authoritative preview |

The descriptor retains `/api/v1/hardware` and authenticated carrier policy.
`wspr-plan/1` contains supported state, known frame types/count, 120-second slot
separation, bounded rationale and explicit ambiguity/alternate call. Old full
config paths may preserve an unchanged new identity during unrelated edits but
cannot introduce a changed new format. ETags, target/boot binding, idle/storage
checks, password-null preservation, flags, pins, schedules and watermark remain.
`docs/protocol/transmitter-application-2.schema.json` validates actual responses;
legacy schemas are untouched. WTP/1, management/1 and /2, Consumer-Radio/1 and
Consumer-Recovery/1 are unchanged.

Profile-owned station writes remain transactional setup, not ordinary resource
mutation. Existing owner wire/plaintext broad decoding remains readable; the
actual PicoBootstrapServer validates planning before trial/commit. The pure
`/api/owner/v1/wspr-support` descriptor exposes known support through existing
public AP GET or authenticated setup policy. Unknown/old firmware refuses new
setup syntax with an editable preserved draft. P15.7 sent-once receipts,
generation/readback/review, full-capacity recovery and healthy-peer continuity
remain. A status refresh/login never establishes an interrupted save's result.

## Source provenance and independent receiver observations

Packing/hash arithmetic is a bounded adaptation of MIT WSPR-Reference at Pi
`a2437d1`, principally `src/WSPR-Reference/src/wspr/wspr_ref_encoder.cpp`.
Attribution/license are retained in `src/encoding/WsprryPi-LICENSE.md` and
THIRD_PARTY_NOTICES. No desktop reference/decoder, JSON library or Linux hardware
code is linked into firmware. Existing Type 1 channel goldens remain identical;
six fixed Pi Type 2/3 vectors compare every symbol.

The independent oracle is official WSJT-X
`967c85a6119110788b0df3782cf796485b2cee14`, eight `lib/wsprd` source/header files.
Exact SHA-256s, 21 payload/symbol/receiver observations and 33 hash tails are in
`tests/wspr_oracle_vectors.json`. GPL implementation stays in temporary
validation storage; only numeric outputs/provenance are committed. Test-only
instrumentation prints the existing unpk result and supplies its byte parity
table; packing/decoding arithmetic is unchanged. Hash seed is 146 with explicit
15-bit reduction. The upstream empty-input early return is recorded both raw
and reduced; empty input is not a valid station. Tests cover all tail lengths,
unaligned/exact-length views and repeated alternating long/short inputs.

Cold Type 3 observes `<...>`; prior ordinary compound Type 2 resolves the recorded
PJ4 and W1A examples in that independent decoder. `/Z` and `/09` remain an
intrinsic Type 2 ambiguity and have distinct requested-full-call Type 3 hashes.
Pi's own unpacker retains alternates, while its correlator can clear ambiguity
after a base-call-hash pairing. The real compound paired test deliberately
observes different base/full-call hashes. Those reference observations do not
prove general receiver correlation or RF decoding.

Unchanged Pi's one-character prefix encoding (`W/AA0NT`) differs from WSJT-X:
its prefix branch shifts once, leaving space/W/NUL; correct packing needs two
leading spaces. Pico pads by exact prefix length and matches the independent
vector. This reference discrepancy is retained in `pi-one-prefix-rereview.log`;
no WSPR-Reference repair was made. Its reviewed unchecked copies, invalid-input
substitution and aligned-hash hazards were avoided; they are source observations,
not newly claimed runtime reproductions.

## Exact local compatibility pairs

Pi native implementation is `41c1dbd`; the final published/CI head above adds
only tests/pins/evidence. Clean-source and Mbed TLS identity guards remain.

| Row | Exact clean Pico source | Local result |
| --- | --- | --- |
| legacy | `95aac22bf7cc31b67fe5773761708d743d8a6473` | Passed |
| extended | `dfffdd5220db8b7cf1acf5e74950dbd294283c55` | Passed |
| p152 | `87144d1364f36d04bfe0a714bd1c2f6deb974302` | Passed |
| p153 | `d6208dbc88005383041c5ec306b738db7ec22796` | Passed |
| p154 | `ddb00dd7960373cec271f7816c0e1b10117416e9` | Passed |
| p156 | `792b5b2f60e381a6bd8e7a7726eeffe24fc08519` | Passed |
| p157 | `26ae596b540e92f25da37f978321ba1ec5934bdc` | Passed |
| current | `804e8a06585ec5a0e650e69fcd71ada398b6cc9f` | Passed |

All seven historical rows preserve original strict expectations and pass with
the final native client (`final-pairs.log`). Historical `p157` retains
`26ae596...`, including its original recovery/resource/mixed-browser cases;
only current advances. Final-source current TLS, station/AP crypto, actual UI
producers/journals, profile readback/adoption and mixed shipped-browser recovery
pass (`final804e-*` in the companion scratch), including W1A compound/brackets.

The maintained `tests/release_pi_compatibility/` probe verifies exact clean Pi
`a2437d1`, Pico `804e8a0` and Mbed TLS `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`.
It compiles unchanged release Pi product files, reuses only original test doubles
and links the freshly built current Pico fixture. Twelve real station/AP cases
pass: Type 1 read plus unrelated save works with saved-six/watermark preserved;
Type 2, explicit Type 3, PJ4/W1A prefixes and ambiguous pairs explicitly refuse
with zero mutation (`final804e-release-test.log`). No brackets/affixes are stripped.

## Validation and target resource evidence

Linux Docker `wsprrypico-p153-env:local`, image `c7f2a891a6ff`, GCC 14.2,
CMake 3.31.6 and Node 20.19.2 supplies all Pi C++ compilation. Networking is
disabled/no devices mounted; the full Pico fixture supplies user pi and writable
external outputs/config-local. No local macOS Pi C++ compilation/linking occurred.

| Final-source check | Result/evidence |
| --- | --- |
| Complete Pico host CTest | 196/196, 57.57s; `final804e-ctest.log` |
| Affected sanitizer-build selection | 27/27, 13.40s; native/native-driven C++ uses ASan/UBSan and leak checks; scripts/JS use their own runtimes |
| Pinned bootstrap npm | 16/16; generated bundles rebuilt with existing esbuild and attribution |
| WTP contract | 23 schema, seven raw JSON, one framing, eight transition cases |
| Pi native/API/UI units and final sanitized producers | Passed; `sanitize-final-native.log`, `final804e-sanitize-*` |
| Pi runtime/scheduler/application | 34 TLS cases, 358 production runtime, 1514 scheduler, 1337 application checks; `runtime-localfs.log` |
| Actual Pico shipped-page browser | Chrome 155.0.8059.40, Node 26.12.0; new W1A preview, Type 2/3/pair, ambiguity, genuine commissioning, old-firmware refusal, preserved draft/no replay; 12 captures |
| Actual Pi PHP/JS rendered browser | Source-paired JSON mocked only at HTTP; keyboard, invalid locator, recovery/drafts, Type 2/3/ambiguous pairs; 20 captures |
| Standard and StandaloneRF firmware | Both clean-source links pass allocator/topology/stack/RF placement checks; no flash |
| Format/scope | clang-format affected C++; git diff --check; scoped commits exclude user edits |

Firmware source is clean `804e8a0`, revision label `804e8a06585e`, version
`0.1.0-rc.3-p158-candidate`, Pico2W, 138 MHz RAM renderer, consumer Plain LAN,
GP14 default runtime button. Reused pinned SDK
`079c6f39023649b154152db30f1d781e884879bc`, Mbed TLS above, lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`, Arm GNU 15.3.1 (20260627), picotool
`6f6458d792b93685a11423b244a585eaa99eafcf` and cached SDK pioasm.

| Compiler/linker output | Standard | StandaloneRF |
| --- | ---: | ---: |
| Text bytes | 2,110,592 | 2,126,116 |
| Data bytes (linked section layout) | 0 | 0 |
| BSS bytes | 173,444 | 329,384 |
| BSS-end to heap-limit gap before runtime allocations | 301,980 | 146,040 |
| Core 0 stack reservation | 32,768 | 32,768 |
| Individual main compiler frame | 4,400 | 4,560 |

Target compile-only size probe: frame 184, plan 392, scheduler 616, RF event 40,
event-list metadata 104 bytes. The plan has no heap allocation. Each job owns
three existing 64-event pages, 7,680 bytes for 162 events/192 capacity. Old and
incoming jobs can briefly coexist while loading frame two: 15,360 event-page
bytes plus existing metadata, not a new 324-event buffer. Existing engine and
HTTP/crypto budgets/reserve remain. Individual frames: planner 1008, compound
264, hash 40, scheduler poll 1560, prepare_frame 1840, poll_pair 784, plan JSON
1328 bytes. These are not cumulative stack bounds, measured high-water or
available-runtime-heap qualification. Physical timing/memory acceptance is open.

Impeccable was used before UI work, preserving incumbent styling. Representative
desktop/mobile light/dark, keyboard and long-error states were inspected in a
bounded visual pass and confirmation; later functional repairs reran behavior
without restyling. Pico intentionally keeps its existing light styling under
both preferences. The one detector scan returned [] but degraded to regex
because optional HTML parser modules were absent; computed contrast/full HTML
analysis is not claimed. Pi capture framing now waits for layout and asserts
fields/feedback are visible below the existing fixed header.

## Executor adversarial review and repairs

This is executor self-review, not the originating conversation's later review.

| Severity/trigger | Repair/location at final source | Regression/reassessment |
| --- | --- | --- |
| P1 complete pair past expiry/representability | `src/standalone/scheduler.cpp:115`, final launch-second tail and UTC/monotonic preflight | Expiry boundaries/overflow/midnight; no claim/watermark change on refusal |
| P1 clock mapping jump or failed cutoff | scheduler lines 177/196; actual uncertainty bounds and retained failed/output-unknown authority | Clock/STOP/ownership/engine/journal/allocation fault injections; no orphan/replay |
| P2 wrong numeric-suffix policy | `/00`–`/09` restored; alternate metadata and requested full-call hash | Same Type 2/distinct Type 3 independent vectors, native/commissioning/browser paths |
| P2 valid prefix also a base call | `src/encoding/wspr_plan.cpp:49`, suffix branch requires right-hand suffix grammar before returning | Exact old 0c binary refused W1A pair/bracket; Pi and WSJT-X agree on all 162 repaired symbols; resources/real commissioning/native carriers pass |
| P2 incomplete carrier adoption | Pi TLS/consumer explicit outbound pairs and Pico engineering-field Configure classification | Actual source-paired TLS/consumer plus field auth/preclock refusal |
| P2 malformed versioned support could fall back | Pi `configuration.cpp:97` plan types/null/ambiguity/integer checks, line 213 orphan descriptor refusal | Nine native malformed-context regressions reject before mutation |
| P2 old-firmware error hidden by setup catch | `src/network/bootstrap_web/owner-app.js:262` preserves specific refusal/editable draft before transaction | Real shipped page: no profile write/replay |
| P2 empty plan falsely labeled Type 1 only | `src/network/web/app.js:139` says no identity configured on application/2 | Behavioral null-plan/readback regression |
| P2 unchanged legacy identity blocked unrelated save | web app line 495 validates changed identity, preserves unchanged bytes | Unencodable legacy save works; old firmware still refuses changed new format |
| P2 draft hid ambiguity warning | Pi `wtp-management.js` keeps ambiguity/full-hash consequence | Shipped UI and keyboard/invalid-locator/long-error confirmations |

Reviewed bounds/tails/alignment/unsigned arithmetic, independent payloads, all
prefix/suffix grammar classes, Type 1 goldens, frozen pair reservation/lease/
reboot/failure paths, all station persistence/adoption boundaries, strict old/new
negotiation, profile ownership, sent-once recovery and release scope. No
remaining actionable issue was identified in this bounded software review.

## Failure/rerun history and limitations

All logs remain in `/private/tmp/wsprrypico-p158` and
`/private/tmp/wsprrypi-p158/results`; captures stay outside Git. Relevant retained
history: initial broad owner-wire rejection broke old fixtures (decoder restored;
planning enforced at actual commissioning); browser mock now models separate
input listeners; historical CMake appends planner only when present. No assertion,
production deadline, test deadline or CI timeout was weakened.

Permission-sensitive Linux TLS rotation first failed on a macOS bind mount;
the unchanged suite passed on native Linux filesystem. A real-time host network
run at intermediate 99ce conservatively refused launch during concurrent builds
(elapsed 158668 ns/allowance 1 ms; UTC mapping error not logged). The unchanged
quiet rerun passed, including a 60-second scheduled wait and recovery. These
are host timing observations, not RP2350 qualification. Final-pin CI exercises
network interoperability afresh.

Fresh SDK configuration attempted a default picotool fetch and failed without
network; fresh host pioasm hit the known macOS linker issue. Explicit existing
pinned local helpers completed the links; no SDK/tool installation/download
occurred. Oracle source retrieval was separate, bounded protocol validation.
Automatic permission review once timed out before a scoped commit; its single
allowed retry succeeded. Nothing remains blocked by approval review.

Physical transport, RF decoding, general hash collision resolution, long
endurance and target heap/stack high-water remain open; Phase 14 support labels
and later P15.13 band/clock qualification are unchanged.

## Pi release state and publication/CI

Local old/new gates passed before staged publication. Pico's tested immutable
source was pushed first so cross-repository CI could fetch it, followed by only
the approved Pi feature branch. The implementation push was independently verified at Pico devel `804e8a0`
and the companion at `6d5e734`. The operator subsequently published the
source-equivalent c0e17b4 documentation commit described below. Final report
publication is another separate commit; its full verified branch-head SHA is
returned in the completion message, while CI/current remain pinned to 804e8a0.

Initial CI [38948276130](https://github.com/WsprryPi/WsprryPi/actions/runs/38948276130)
passed all 12 jobs at superseded head `28ee735`/pin `0c02423`; it does not qualify
the prefix repair. Final CI
[38950723473](https://github.com/WsprryPi/WsprryPi/actions/runs/38950723473)
is bound to exact head `6d5e73430bfbacdb8cfc29c3fe41089aa8ae5fcb` and pin
`804e8a06585ec5a0e650e69fcd71ada398b6cc9f`.

Final result: **12/12 jobs passed**, completed 2026-10-16 19:09:25 UTC. This
includes macOS portable/simulated, Linux non-hardware validation, strict I2C,
all seven historical compatibility rows, current TLS/consumer/browser/routing
interoperability and GCC 13 release profiles. Metadata is retained in
`/private/tmp/wsprrypi-p158/final-ci-run.json`; the superseded green run is
`ci-superseded.json`. No CI assertion or timeout was weakened.

The operator independently advanced Pi devel first to `587c7b1` (Punchlist only)
and then `090a15a93cc2f98545615b5d9b59baeae173a4de` (integrated console review).
The latter changes CSS/templates, UI tests and workflow as well as Punchlist;
native management/WSPR product sources are unchanged from the tested a243 base.
It then advanced to `d93c75c4f1490df9108856403710e692b9c2d3dd`, adding a
fail-closed CI transmitter-access trace audit/workflow regression. This task
did not move/rebase/merge/push Pi devel. Final companion UI/CI evidence belongs
to its approved a243 base, not an integrated d93c console/audit. Integration must
preserve that newer audit and reconcile overlapping workflow and
`wtp_recovery_ui_integration_test.js` changes, then rerun affected UI/CI after
separate authorization. A green feature branch does not establish release
adoption or close that rollout gate.

## Documentation Impact

Updated Pico README, architecture, browser API, development index, standalone
behavior and shared-application version note; added application/2 schema, numeric
oracle vectors, ordinary planner/resource/schema tests, maintained browser and
unchanged-release probes and this packet. Approved Pi documentation is its
configuration compatibility contract and companion record. Historical
P15.1–P15.7 evidence and frozen schemas remain untouched.

Read-only WsprryPi-Docs review found:

- `docs/User_Interface/Setup/Signal_Setup/wspr.md`: reconcile Type 1/3/bracket
  pairing prose with actual ordinary-six Type 1, explicit Type 3 single and
  compound-six Type 2/3 behavior; distinguish Pi preferences from Pico automatic.
- `docs/Advanced_Operations/ini_configuration/wspr.md`: document total token bound,
  base/affix grammar, exact locator/power, suffix ambiguity and hash context.
- `docs/User_Interface/Setup/Transmitter/index.md`: version negotiation, profile
  ownership, nominal pair timing, reservation skips and STOP/reboot rules.

P15.14 screenshots still need real operator examples of saved-six/on-air-four,
Type 2 no locator, Type 3 hash context, pair/frame progress, /09 ambiguity,
old-firmware refusal and preserved draft/fresh readback on desktop/mobile.
That repo's pre-existing Setup-page edits/maintainer review were not changed
by this task; its operator-updated b377bc4 checkout is clean at final inspection. No hostname/title/consolidated-form/preference or P15.9
partial-progress/draft-state field-saving workflow was implemented. Preserving
an unchanged, previously readable legacy identity in a complete update retains
the existing compatibility rule; it does not separate new incomplete/invalid
field drafts from transmit readiness or implement later P15.9–P15.14 work.

The initially untracked Pico handoff and concurrent roadmap edit were excluded
from this task's commits. During CI, the operator independently published
`c0e17b42b7f88c9ea6c4f0c606d363229af9baaf` (handoff/checklist tracking), then
`d5fe087` (P15.9 saving/readiness clarification) and `4188001` (hostname/setup
defaults clarification). Git diff from 804e8a0 through 4188001 contains only
handoff/roadmap documentation. Those commits and further working edits are preserved; final Git state is reported in the
completion message. The separate roadmap may still say in progress. Primary Pi is d93c75c with its dirty `release_tools/Release Punchlist.md` and
untracked `docs/development/item13-integrated-impeccable-evidence/` and
`docs/development/item13-integrated-impeccable-review.md`; all remain outside
this task. The approved companion checkout is clean and remote-parity verified. Validation worktrees/scratch evidence are retained. The originating
independent post-execution review remains pending.

## Reproduction

Ordinary Pico commands (verified local dependency sources, separate host build):

```sh
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
```

Sanitizers use `-fsanitize=address,undefined -fno-omit-frame-pointer`,
`ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1`. Firmware links use
verified pinned SDK/Arm inputs and cached local picotool/pioasm; full flags and
logs are in the scratch firmware cache and `firmware-final804e.log`.

From approved Pi src, Linux only: existing `make wtp-config-test wtp-api-test`,
`wtp-config-interop-test` with each exact `PICO_COMPAT_PROFILE`/clean Pico source,
`wtp-network-interop-test`, and hardware-disabled `wtp-network-runtime-test
wtp-scheduler-test wtp-application-test BACKENDS=simulated ANCILLARY_GPIO=0 SUDO=`.
Retained `run-final804e.sh` supplies actual source/output mounts. Guards must not
be bypassed. Permission fixtures require native Linux filesystem semantics.

After building the fresh current pair, the maintained old-release probe is:

```sh
cmake -S "$REPORT_SOURCE/tests/release_pi_compatibility" -B "$PROBE_BUILD" \
  -DOLD_PI="$CLEAN_PI_A2437D1" -DPICO_SOURCE="$CLEAN_PICO_804E8A0" \
  -DMBEDTLS_SOURCE="$MBEDTLS_SOURCE" -DPAIR_BUILD="$CURRENT_PAIR_BUILD"
cmake --build "$PROBE_BUILD" --parallel 2
"$PROBE_BUILD/release_p158"
```

Only its original test main is renamed/returned explicitly; old product files
are untouched. The opt-in Pico browser command is `node
tests/wspr_browser_integration.mjs "$CONSUMER_BOOTSTRAP_DRIVER" "$OUTPUT"`
(Node 20 needs --experimental-websocket). The driver is the production Linux
bootstrap fixture; HTTP/crypto are genuine. Pi's opt-in command is
`WSPRRYPI_RUN_RECOVERY_BROWSER=1 node
WsprryPi-UI/tests/wtp_recovery_ui_integration_test.js "$CURRENT_PAIR_BUILD"
"$OUTPUT"`; PHP/JS are real, source-paired JSON is mocked at HTTP. Final captures
are `browser-final804e` under each repository's scratch root.
