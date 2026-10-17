# P15.7 login and save recovery

Status: **complete within the demonstrated software scope, 2026-10-15**.
The original software run did not establish exact physical incident reproduction,
phone/board transport, target heap/stack high-water or RF acceptance.

**Operator disposition, 2026-10-17:** later ad hoc phone/Mac, recovery and
resource testing is reported complete and accepted. No further physical or
consumer-grade qualification campaign is queued. The exact original incident
is not retroactively claimed reproduced; the earlier pending statements below
are historical evidence limits. See the
[current work record](consolidated-backlog.md).

## Selected design

WsprryPico leads; WsprryPi adopts the same separately versioned
Consumer-Recovery/1 extension. Consumer-Radio/1 traffic, its fixed vectors and
the frozen management/1 and management/2 discovery documents stay unchanged.

Recovery retires one explicitly selected login and never creates a replacement
session or repeats an application request. The operator supplies the current
saved Wi-Fi password for a fresh authenticated exchange. A retained nonsecret
retirement selector identifies the affected login after traffic-key loss; it is
not a retirement credential. It is a domain-separated one-way alias of the
raw traffic ID, device and boot; discovery never publishes traffic IDs. An alias
cannot address an ordinary CR01 request or consume a pending login proof.
With no retained selector (fresh page/process or
lost start reply), public recovery discovery lists occupied selectors and their
interface/authority/state. The UI must show that the selected login could belong
to another operator and require an explicit retirement action. Shared-password
membership cannot identify the original owner. No automatic eviction is allowed.

GET `/api/consumer/v1/recovery` returns closed `consumer-recovery/1` metadata,
current device/boot/generation and at most three occupied selectors. These are
untrusted handshake hints, not authenticated private state. Discovery and
retirement are restricted to the same exact authority and interface as the
victim; IP, hostname and optional `:80` sessions are distinct. The client
compares the grant with its independently selected transport context. POST
`/api/consumer/v1/recovery/start` carries ordinary identity/key/nonce fields,
`version:1` and `target_selector`. The grant additionally binds target, exact
HTTP authority and actual interface. The recovery transcript is the existing
radio transcript followed by NUL-terminated
`WsprryPico/Consumer-Recovery/1`, the SHA256 of target (16 decoded bytes), interface byte
(1 AP, 2 station), authority length (one byte) and ASCII authority. The resulting
SHA256 replaces the ordinary transcript digest; unchanged HKDF labels and AEAD
framing therefore operate in a separate cryptographic domain. No recovery key
can authorize an application request. POST `recovery/finish` authenticates the
sequence-zero proof, seals a sequence-zero acknowledgement identifying the exact
target, then retires that target. Every complete proof consumes its challenge.

One dedicated pending crypto workspace exists outside the three ordinary slots.
It never becomes an active session. It expires absolutely after five seconds;
all admitted starts, including RNG/crypto failure, are spaced at least one second apart. One ordinary pending
login and one recovery proof may coexist (at most two ephemeral PSA handles).
Malformed/failed proofs do not touch victims or their timers. Recovery refuses
wrong Host/Origin/interface, stale identity/generation, oversized/duplicate JSON,
invalid keys and failed RNG/allocation/crypto. All workspace keys are erased on
consumption, expiry or context invalidation. No private application reads occur.

A client retiring its own login clears its traffic state before dispatching
the finish proof. A lost reply retains only the alias and invalidates saving.
A lost recovery reply is reconciled by another explicit authenticated retirement
of the same boot-bound target: an absent target returns an authenticated absent
result. No slot is allocated and nonreused boot-local session IDs prevent a
delayed proof from retiring a new occupant. Abandoned recovery starts can delay
another recovery by at most five seconds with healthy transport and no competing
new starts. Repeated competing traffic can deny service; no availability guarantee
is made against that traffic. No ordinary
five-minute expiry or reboot is required. A complete recovery followed by an
explicit ordinary login requires four POSTs plus discovery/identity reads; the
existing one-second ordinary login pacing still applies. Browser discovery and
identity reads each have a five-second timeout; recovery POSTs each have five
seconds and ordinary login POSTs each have 30 seconds. Native HTTP exchanges each
have an eight-second absolute deadline and check the proof's five-second
pre-finish budget. There is no retry loop. A successful finish retires during
that dispatch within the server proof lifetime; timeout/refusal is reported
explicitly. These are bounded attempts under a healthy transport, not an
availability promise under competing traffic.

Retirement cancels only the selected session's still-pending transaction through
the existing false-delivery callback. Already durable settings and accepted jobs
remain. A delayed ACK/FIN/RST cannot deliver that cancelled transaction or a
later board-wide receipt. JobService, STOP, owner, scheduler, journals and RF
authority do not change. Core 0 owns recovery; core 1 timing is unchanged.

## Save reconciliation

Authenticated application refusals preserve authentication and drafts. Transport,
framing and authentication uncertainty clear traffic keys, retain only bounded
nonsecret target/attempt context, and invalidate write eligibility. No request is
replayed. Recovery/login or a healthy status GET alone cannot unlock Save.
Authoritative config/resource readback must acquire fresh exact revisions under
one target context while retaining drafts. The operator reviews saved versus
draft and explicitly enables a new save. Matching current fields prove current
saved state, never attribution of the historical attempt. Credentials stay
volatile and are scrubbed; no recovery material enters persistent storage.

Commissioning keeps its existing sent-once digest/generation receipt and actual
bootstrap dispatch/delivery gates. Failed results retain correctable drafts;
successful readback must preserve unrelated edits. Receipt-only origin
continuations cannot submit. Password changes require an explicit login using
the password valid for the observed profile. No automatic password guesses.

## Acceptance and budget

Required: genuine browser Noble/Pico Mbed TLS/Pi OpenSSL recovery; full pool and
pending recovery without ordinary expiry; pre/post-effect loss; invalid proof,
replay, context, quota and resource failures; peer isolation and delayed delivery;
real bootstrap commissioning trials; draft/revision reconciliation; exact old/new
source pairs; full host, affected sanitizers, both firmware links and bounded
desktop/mobile light/dark visual review. Record counters and original failures.

The additional fixed workspace is one session binding plus one crypto object,
one deadline/rate timestamp and bounded authority storage. Existing two HTTP
tasks/pages and 32 KiB authority reserve remain. Report linked RAM and compiler
stack frames separately from unmeasured target heap/stack high-water. Shared
passphrase trust, unauthenticated HTTP page delivery and active-endpoint offline
password guessing remain explicit limits. No board access or RF is authorized.

The execution evidence below records the implemented software scope. Physical
qualification remains open separately.


## Implementation and evidence

Pico implementation: `26ae596b540e92f25da37f978321ba1ec5934bdc`, on devel.
This is the reviewed clean implementation used by Pi's exact-source guard;
later lead-repository publication adds evidence/documentation and a browser
fixture assertion-order repair, with no production change.
Companion Pi adoption and final publication identities are recorded below.

The reviewed P15.6 real-client/session fixture reproduced an occupied abandoned
login after a lost durable-write reply: no second mutation, healthy peers still
read the saved result, and another login consumed a slot. This is retained in
`/private/tmp/wsprrypico-p157/baseline-sessions.log` (13 scenarios). It does not
reproduce the original physical callsign/save/blocked-login sequence.

Current genuine fixtures separate before-dispatch refusal from after-commit
loss with journal sequence/handler counters. A lost config/update reply results
in one mutation and one authoritative saved-state change. Three active slots
remain occupied until the selected explicit retirement; no ordinary idle expiry
or reboot is used to obtain capacity. Lost start/finish, a pending ordinary
proof, absent-target repeat, authority changes, stale identity, malformed input,
RNG/allocation refusal and repeated cycles preserve other clients. Public-alias
forgeries cannot address ordinary active or pending CR01 sessions. Sixteen
retire/login cycles end with two ordinary sessions, no private PSA key owners,
no connection tasks and zero pending TCP bytes.

`consumer_commissioning.test.mjs` instantiates the actual PicoBootstrapServer,
its decoders, trial gates, Mbed TLS and RAM-backed production profile journals.
Only network/radio, flash media, indicator/time and board-specific validity
boundaries are explicit doubles; existing crypto tests cover actual owner-point
validity. Nine cases exercise lost preparation, delivered/undelivered submit,
retirement and stale ACK, failed network and station trials, corrected explicit
retry before terminal expiry, committed receipt, changed password/profile
activation, and accepted restart before actual reboot. `activate` reloads the
runtime profile in the harness; it does not prove a physical reboot. A manually
acknowledged TCP response still needs the production HTTP poll to finalize
complete delivery before the next trial transition; fixture ordering preserves
that distinction.

### Pico checks

Retained `wsprrypico-p153-env:local` image `c7f2a891a6ff`, GCC 14.2,
CMake 3.31.6 and Node 20.19.2; container networking disabled and no devices mounted.
SDK `079c6f39023649b154152db30f1d781e884879bc`, Mbed TLS
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`, lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`, Arm GNU 15.3.1 were reused.
No dependency download or tool installation was performed.

| Check | Result |
| --- | --- |
| Complete host CTest | 193/193, 107.38s, final build; `ctest.log` |
| ASan/UBSan, leak detection | 12/12, 5.23s; `sanitize-tests.log` |
| Existing genuine sessions | 13 scenarios |
| New genuine recovery | 11 scenarios, including pre/post-effect self-retirement loss |
| Production bootstrap commissioning | 9 scenarios |
| Pinned bootstrap browser tests | 16/16; `npm-final.log` |
| WTP contract | 23 schema, 7 raw JSON, 1 framing, 8 transitions |
| Formatting/whitespace | clang-format affected C++ and `git diff --check` |
| Checked-in bundles | regenerated with pinned esbuild; source/bundle agreement checked |
| Standard and StandaloneRF | both cross-linked, linked image/allocator/topology/stack/RF checks pass |

The first final-suite invocation lacked container fixture user `pi` and failed
six Python fixture groups (`ctest-final.log`). The documented user was restored
in the disposable container and the whole suite passed, then the final candidate
was rebuilt and the whole suite and sanitizer group passed again. No assertion,
production timeout or deadline was relaxed. Early compile/test failures and
repaired-fixture logs remain in the scratch directory.

Reproduction, with verified local dependency paths:

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
cmake --build build/consumer-lan-pico --parallel 3 \
  --target WsprryPico WsprryPico-StandaloneRF
```

The Linux fixture requires user `pi`, writable build/log outputs and a writable
scratch `config/local` mount. The actual invocations and preserved scripts/logs
are under `/private/tmp/wsprrypico-p157`; sanitizer flags were
`-fsanitize=address,undefined -fno-omit-frame-pointer`, with
`ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1`. Full host and
sanitizer runs were sequential. No Pi C++ was compiled or linked on the local
Mac; companion native/runtime checks used Linux Docker. The existing macOS CI
portable profile is a separate automated check.

### Target resource bounds

Clean implementation-linked images identify revision `26ae596b540e` and firmware
`0.1.0-rc.3-p157-candidate`, Pico2W, 138 MHz RAM renderer, consumer Plain LAN,
configured GP14 default. They were not loaded onto a board.
Standard text/BSS are 2,071,600/172,980 bytes; StandaloneRF are
2,087,108/328,920 bytes (`arm-none-eabi-size`, data reported zero because of the
linked section layout). Gaps from BSS end to heap limit are 302,444 and 146,504
bytes before runtime allocations, not measured available heap. Fixed target
manager object is 1,256 bytes; four crypto objects total 576 bytes. Compared with
the recorded P15.6 object subtotal, this adds 536 bytes; the bootstrap singleton
also adds a 16-byte originating-login association. String backing allocations,
allocator overhead and PSA heap are outside those fixed subtotals.

Compiler stack frames: ordinary start 848, finish 584, exchange 1,320;
recovery start 1,304 and finish 768; crypto begin 80, authenticate 360, open 80,
seal 1,776; main 4,400 bytes. These are individual compiler frames, not cumulative
or measured high-water. Two maximum ciphertext uploads still occupy 65,536 bytes
plus parser/page metadata, temporary envelope/ciphertext pages and crypto work.
Existing admission reserves 32 KiB for authority. One ordinary pending proof and
one recovery proof may own ephemeral PSA handles simultaneously; shared TLS PSA
ownership is retained. Software loops/leak checks do not establish target heap
fragmentation, stack high-water, long endurance or availability at arbitrary load.

### Browser and Impeccable

Impeccable context/hardening guidance was applied without redesign. Actual
Chrome 155.0.8059.40 runs the shipped page and checked-in bundle against the Linux
production HTTP/session/Mbed TLS fixture. Three independent contexts plus an
independent Noble peer cover stale-save draft preservation, full capacity,
after-commit response loss, known-selector and fresh-page explicit retirement,
healthy peers, login/readback/review gating, password visibility/scrubbing,
keyboard activation and three native impact-confirmation dialogs. A lost
self-retirement reply clears authentication and blocks Save while keeping the
draft. The proxy substitutes only the explicit fixture transport authority;
it does not replace crypto or production client code. Native Pi interoperability
is a separate genuine OpenSSL fixture, not this Noble peer.

Eight captures cover desktop 1280x900 and mobile 390x844, each light/dark preference,
for saved-state review and full-capacity retirement. Pico intentionally retains
its incumbent light styling in both preferences. An asynchronous busy state can
disable a keyboard-activated button and clear focus. The harness now asserts focus before activation and waits for actual
discovery afterward; it does not require disabled-button focus. The failed
assertion log is retained. Initial review found stale login-status wording; it
was repaired, and confirmation passes show no overflow in the scoped workflow. Representative [desktop saved review](phase15-7-assets/pico-desktop-saved-review.png)
and [mobile capacity recovery](phase15-7-assets/pico-mobile-capacity.png) are
retained in this repository. All eight originals and workflow JSON are in
`/private/tmp/wsprrypico-p157/browser-confirmation` and its adjacent log.

The Pico detector ran once on affected components and reported DEGRADED because
optional HTML parsers were absent; fallback regex undercounts structural checks.
Its incumbent palette/type advisories were reviewed. Scoped CSS adds wrapping
and width constraints, no new palette or type system. No dependencies were
installed to alter the detector result. Pi's affected surface has its own
rendering and detector evidence below. Review used an initial visual pass and
confirmation, with no redesign/polish loop.

## Companion validation and exact source pairs

Pi implementation is `a6e5137a19f50f9b469dafaf18098bdaf400e44e` on devel. Its tested
production/test files were byte-matched to the actual authorized working tree,
then the committed source pair was checked again. Pico fixtures are exact clean
sources; existing guards and historical expectations were never weakened.

| New Pi against Pico profile | Exact Pico SHA | Result |
| --- | --- | --- |
| legacy | `95aac22bf7cc31b67fe5773761708d743d8a6473` | PASS |
| extended | `dfffdd5220db8b7cf1acf5e74950dbd294283c55` | PASS |
| p152 | `87144d1364f36d04bfe0a714bd1c2f6deb974302` | PASS |
| p153 | `d6208dbc88005383041c5ec306b738db7ec22796` | PASS, native consumer included |
| p154 | `ddb00dd7960373cec271f7816c0e1b10117416e9` | PASS, native consumer included |
| p156 | `792b5b2f60e381a6bd8e7a7726eeffe24fc08519` | PASS, native three-session consumer included |
| current P15.7 | `26ae596b540e92f25da37f978321ba1ec5934bdc` | PASS, native recovery + mixed clients + 9 resource rows |

Published P15.6 Pi `1090d1af6095757fec039e39e09fc5ad70a5706f` against new Pico
`26ae596b540e92f25da37f978321ba1ec5934bdc`: **WORK** for ordinary login,
private reads, explicit settings/coordinator writes and logout. Its unchanged
product lacks recovery UI/API support. This is actual old native product source,
not a new-client approximation or the older `50097e6` management/2 refusal probe.
A clean old Pi checkout and separately guarded external CMake probe compile all
old product translation units/headers. The copied old test driver only injects
a fourth Pico proof workspace so the new recovery surface is enabled. The new
Pico fixture/Mbed libraries and unchanged WTP-client archive are reused; no old
Pi product file or existing compatibility pin/guard is modified. Probe and
source-guard logs are in `/private/tmp/wsprrypi-p157/published-p156-*`.

Pi results under retained Linux:

- Configuration/API units and UI producer/negotiation pass; exact-current actual
  UI/protected routing/runtime/HTTPS/Pico journal interoperability passes.
- All nine shared-resource combinations pass: engineering mTLS, consumer station
  and consumer AP, each normal/storage failure, output-disable failure and blank/
  null-active observations. These are deterministic RAM journals and engine doubles.
- Genuine native OpenSSL/Mbed recovery and both frozen/recovery vectors pass,
  including five board job-authority and seven host-admission variants. Owner,
  STOP, scheduler, journals, engine calls and unknown-output policy remain intact.
- One real manager holds a native runtime and two shipped Noble VM contexts.
  After a post-handler lost read, a fresh context retires the retained alias at
  full capacity, both healthy peers continue, and explicit login reclaims one
  slot. Persistent bytes/generation, WTP I/O and application mutations stay
  unchanged. These VM contexts are distinct from the actual Chrome workflows.
- Network interop passes five process cases and real TLS address/identity, idle
  status, 60-second scheduled wait, uncertain results without replay and identity
  recovery.
- Simulated runtime passes 34 actual TLS cases and 358 production checks, plus
  plain TCP and TLS resolver/fingerprint contracts.
- ASan/UBSan with leak detection passes affected units, production client,
  native recovery, all nine resources and mixed recovery; no diagnostics.

The two initial new native-test failures were fixture teardown assumptions:
one attempted to clear the production unsafe latch, another assumed it would
become replaceable. Seven unsafe admission variants now run in isolated children
and assert the latch remains. A runtime attempt failed Docker bind-filesystem
`copy_file` behavior for mode 0200 `rotation.crt`; copying that incomplete file
also refused. The passing retry regenerated fixtures in container-local `/tmp`.
No production safety gate or assertion was relaxed. All attempt logs remain.

Pi browser producer and WTP UI unit tests pass independently. Actual
Chrome 155.0.8059.40 renders the shipped PHP/JS with mocked HTTP responses and
current exact-pair resource JSON. Eight desktop 1280x900/mobile 390x844 captures
cover light/dark readback and retirement error states. Draft `MYDRAFT` survives,
readback shows saved `AA0NT`, declining review or retirement sends nothing,
passwords clear, Save disables after uncertainty, keyboard inspection works,
and long errors wrap without horizontal overflow. Initial mobile capture raced
viewport layout; confirmation waits for settled layout and asserts the intended
readback control is visible. No product styling changed. Representative
[Pi desktop retirement](phase15-7-assets/pi-desktop-retirement.png) and
[Pi mobile readback](phase15-7-assets/pi-mobile-readback.png) are retained here.
The detector ran once and returned `[]`. The saved opt-in regression is
`WsprryPi-UI/tests/wtp_recovery_ui_integration_test.js`:

```sh
WSPRRYPI_RUN_RECOVERY_BROWSER=1 node \
  WsprryPi-UI/tests/wtp_recovery_ui_integration_test.js \
  /path/to/current-interop-build /path/to/screenshots
```

Final saved harness confirmation passed with screenshot capture disabled;
the scoped visual pass had eight captures. Browser/CLI orchestration uses Mac
Node 26.11.1; Linux fixture Node is 20.19.2. This does not exercise an installed Pi
service or physical phone. The committed exact pair is Pico `26ae596b540e92f25da37f978321ba1ec5934bdc`
and Pi `a6e5137a19f50f9b469dafaf18098bdaf400e44e`. All companion scripts/logs are retained in
`/private/tmp/wsprrypi-p157`; source-pair results are `remaining-pairs-results.log`,
`pair-*-test.log`, `current-pair-repaired.log`, `current-network.log`,
`current-runtime-localfs-attempt2.log`, `current-mixed-recovery-attempt1.log`,
`current-sanitize-*-attempt1.log`, and `ui-review-final.log`.

## Adversarial review and repair ledger

Two independent reviewer contexts assessed implementation and evidence; the
executor also reviewed the final production diff. Every actionable issue below
was repaired and affected checks rerun. Reviewers distinguished production
failures, design clarifications and test-fixture defects.

| Severity / trigger | Affected files | Repair and regression |
| --- | --- | --- |
| P1: public listing initially exposed raw CR01 IDs; frozen bad-tag policy could close victims | Pico `src/network/consumer_radio.cpp`, `bootstrap_web/shared/crypto.js`; Pi `src/wtp_integration/consumer_radio.cpp` | Domain-separated one-way retirement aliases; genuine forged active/pending alias tests keep both victims usable. Browser/Mbed/OpenSSL derivations agree. |
| P2: commissioning evidence only exercised direct radio API | Pico `src/network/pico/bootstrap_server.cpp`, `tests/consumer_commissioning.test.mjs` | Added real PicoBootstrapServer fixture; it exposed extra wrapper headers rejected by closed owner decoders. Wrapper now emits exactly the route marker. Nine production-dispatch cases pass. |
| P2: lost preparation stranded board-wide grant | Pico `src/network/pico/bootstrap_server.{cpp,hpp}` | Associate only unsubmitted grant with originating login; selected close cancels that grant, acknowledged trial/commit survives. Lost network/station preparation tests pass. |
| P2: malformed save response could overwrite draft or leave Save ready | Pico `src/network/web/app.js` | Validate consumed saved-config fields before fill; malformed JSON/expiry/pins/null preserve draft, invalidate revision and require readback/review. |
| P2: validator incorrectly copied a 2038 cutoff | Pico `src/network/web/app.js` | Match existing firmware zero or 2025–2099 contract; valid 2040/2099 load and reconciliation tests pass. |
| P2: failed terminal setup prevented corrected retry; invalid owner key could erase evidence | Pico `src/network/pico/bootstrap_server.cpp` | Validate current identity/key, clear only eligible failure, then test busy. Real failed station/network trial then immediate corrected retry passes. Committed/unresolved restart remains blocked. |
| P2: lost self-retirement reply left browser/native falsely authenticated | Pico `src/network/bootstrap_web/radio-client.js`; Pi `src/wtp_runtime_bridge.cpp` | Invalidate matching traffic immediately before finish dispatch; retain alias only, tag uncertainty and block saving. Genuine before/after-effect loss and actual Chrome checks pass. |
| P2: native self-clear initially preceded local validation/start | Pi `src/wtp_runtime_bridge.cpp` | Move invalidation into existing proof transport at finish dispatch; invalid local input/start failure retains native traffic. Native/runtime regressions included. |
| P2: RNG exception could leave busy set or an X25519 secret unwiped | Pico `src/network/bootstrap_web/shared/crypto.js`, `radio-client.js`, `radio-setup.js` | Guard begin/finally; own secret before Noble keygen (which itself uses RNG blinding), wipe on blinding/nonce failure. Four independent reproductions and browser tests pass. Initial incomplete repair failed its regression and was corrected. |
| P2: oversized grant retained unbounded selector | Pico `src/network/bootstrap_web/radio-client.js` | Validate exact 16-byte raw grant ID before deriving bounded alias; malformed grant leaves no retained selector. |
| P2: endpoint edit left Pi retirement inspection actionable | Pi `WsprryPi-UI/data/wtp-management.js` | Clear cached inspection/credentials and show exact host/carrier in explicit confirmation; selection identity rejects stale mutation. |
| Workflow: authenticated browser hid retirement password | Pico `src/network/web/index.html`, `app.js` | Dedicated visible password field with existing show/scrub behavior; actual browser checks authenticated and fresh-page states. |
| Design clarification: transcript, exact context and bound | Pico `docs/protocol/Consumer-Recovery-v1.md`, shared crypto; Pi native crypto | Document inner context SHA256, exact authority/interface isolation and five-second abandonment bound only absent competing new starts; vectors and context negatives enforce it. |
| P2 test fixture: new review dialog stalled existing Chrome CI | Pi `WsprryPi-UI/tests/wtp_network_ui_integration_test.js` | Enable Page events; validate exact confirmation type/text, accept expected dialogs, fail unexpected dialogs and require a real confirmation. Original desktop/mobile workflow passes with five dialogs; no deadline increase or production change. Independent reassessment is clear. |

Final independent Pico reassessment found no remaining actionable production
issue after the RNG repair. Final companion reassessment found no remaining actionable issue. Exact test
evidence is recorded above and publication confirmation below. A later operator-requested post-execution review remains a
separate review, not already performed by these execution reviewers.

## Documentation Impact

Updated: Consumer-Recovery/1 contract and synthetic vectors; Consumer-Radio/1
recovery/readback cross-reference; browser API; architecture; development index;
this design/evidence record; Phase 15 checklist; companion native/client/UI and
compatibility documentation. Historical P15.1–P15.6 acceptance records and exact
source identities remain unchanged. WTP/1, reusable WTP-Client, RP1 DKMS and
other WsprryPi-family implementation are unchanged.

Read-only operator review used actual `/Users/lbussy/GitHub/WsprryPi-Docs` and its
AGENTS.md plus `docs/User_Interface/Setup/Transmitter/index.md`. P15.14 must:

- Replace engineering-only Pico management guidance with consumer station/AP
  selection while preserving engineering mTLS and explicit carrier choice.
- Explain three ordinary sessions, one pending login, full-capacity recovery,
  shared-password membership versus tab ownership, explicit selection and the
  effect on another operator's login/undelivered effects. Jobs/durable writes stay.
- Show rejected versus uncertain saves, preserved draft, read saved state,
  saved/active/null/fault status, explicit review and a new save with fresh revision.
- State old-firmware recovery limitations without disabling supported reads/saves.
- Explain commissioning sent-once receipts, explicit current-password login,
  changed-password/origin continuation, and uncertain versus confirmed results.
- Replace/extend desktop and phone screenshots for login/capacity/retirement,
  failed-save draft/readback/review, and commissioning continuation. Use final
  P15.11–P15.12 forms/titles when those later slices are accepted.

That independent operator-doc repository was neither edited nor published.
P15.8–P15.14 features/publication remain pending. This software scope does not
establish the original physical reproduction, actual phone/Mac transport,
on-target heap/stack high-water, installed-service behavior, RF timing or output.
No physical Pi/Pico, flashing, GPIO, RF or installed-service operation occurred.


## Publication and final CI

The tested implementation identities remain Pico
`26ae596b540e92f25da37f978321ba1ec5934bdc` and Pi
`a6e5137a19f50f9b469dafaf18098bdaf400e44e`. The clean committed pair was run
again successfully (`committed-current-pair.log` and `committed-sources.json`).
The published Pi head is `37b41bb20b9d3824c9a555cd730b5361bd085954`;
its only follow-up changes are the network Chrome fixture and its evidence note.
`git diff a6e5137 HEAD -- src WsprryPi-UI/data` is empty.
The lead publication adds documentation/screenshots and the reviewed focus
assertion-order repair. `git diff 26ae596 -- src cmake` is empty, so the clean
implementation pin remains valid for all paired results.

Pushes were non-force on devel. Initial outputs were
`fd094b1..26ae596 devel -> devel` (Pico),
`1090d1a..a6e5137 devel -> devel` (Pi), and
`a6e5137..37b41bb devel -> devel` (Pi fixture repair). Independent
`git ls-remote origin refs/heads/devel` confirmed each implementation push and
now confirms the exact Pi publication head.

The initial [Pi run 38831224836](https://github.com/WsprryPi/WsprryPi/actions/runs/38831224836)
was cancelled by the configured newer-push concurrency policy after nine jobs
had passed and the original browser fixture stalled on an unhandled real review
confirmation. It is not a passing run. The affected original Chrome workflow
passed after repair with five expected confirmations, screenshots disabled,
and unchanged assertions/deadlines (`network-browser-dialogs-unsandboxed.log`).
The first local sandbox attempt could not bind localhost (`EPERM`); the required
outside-sandbox retry supplied the passing run, without changing test behavior.
Independent review cleared both final test-only fixture repairs.

Final published-head [Pi run 38833224809](https://github.com/WsprryPi/WsprryPi/actions/runs/38833224809)
**passed 11/11 jobs** for exact head
`37b41bb20b9d3824c9a555cd730b5361bd085954`. This includes six historical
compatibility rows, current network/runtime/browser interoperability, macOS
portable semantics, strict I2C, Debian non-hardware checks and GCC 13 release.
The release job builds six serial warnings-as-errors backend profiles:
rpi-gpio, rp1-gpclk, si5351, simulated, si5351+simulated and all four together.
Its existing timeout is 30 minutes. No CI timeout was increased for this slice.
WsprryPico has no configured GitHub Actions workflow; its local Linux host,
sanitizer and pinned target-link checks are recorded above.
Final independent reassessment found no actionable issue within this software
scope. P15.7 is closed for that scope; physical limits and P15.8–P15.14 remain
open. The final lead publication contains only this evidence, the checklist,
representative browser images and the focus assertion-order repair. Both
repositories remain on devel, with no unrelated dirty paths. Final publication
SHAs, actual lead push output and independent remote parity are returned in the
execution response; this document retains the exact tested implementation pair.
CI metadata is retained as `final-ci-{run,jobs}.json` in the companion scratch.
No PR or release was created. The independent operator-doc repository is clean
and unchanged.
