# P15.6 independent consumer sessions

Status: **accepted within the software scope**. Published-head Pi CI passes all
ten jobs; implementation, review and publication are recorded below. Physical phone/Mac
transport, target resource high-water and RF qualification remain open.

The source pair validated by Pi CI is Pico
`792b5b2f60e381a6bd8e7a7726eeffe24fc08519` and Pi
`1090d1af6095757fec039e39e09fc5ad70a5706f`, both on `devel`. Pi's product
implementation is `748cb42cd033cc5daabf5b925235d647044dd149`; its successor
`95b08867e241d2206a2d36e21d2c92a5d62a5e04` only repairs CI browser startup
and records reassessment. The published merge additionally preserves concurrent
RP1 documentation work; P15.6 product, fixture and pin paths are identical to
`95b0886`. Pi's current
fixture pins that exact clean Pico commit. This record's documentation-only
successor does not change the implementation pair or require repointing the pin.
The [companion Pi acceptance record](https://github.com/WsprryPi/WsprryPi/blob/95b08867e241d2206a2d36e21d2c92a5d62a5e04/docs/development/phase15-6-sessions.md)
binds its native-client compatibility and UI component evidence to that source.

Pico's implementation changes the bounded manager in
`src/network/consumer_radio.{hpp,cpp}`, static injection in
`src/standalone/pico/main.cpp`, context refresh in
`src/network/pico/bootstrap_server.cpp`, discovery in `api.cpp`/`management.cpp`,
and the source/generated consumer browser client. Genuine HTTP/crypto, adapter,
discovery and browser fixtures accompany those paths. Pi's production changes are
in `src/wtp_integration/{consumer_radio,configuration}.cpp` and finite feedback in
the first-party `WsprryPi-UI` component; parent interoperability tests, source pins,
CI and documentation accompany them. No reusable transmitter/reference/logging
component was modified. UI component unit and actual-browser checks and parent
integration checks are recorded below.

## Selected design and acceptance assertions

Three fixed session slots support phone, Mac and native Pi simultaneously at the
same station authority. At most one slot may hold a pending login; pending and
active slots together cannot exceed three. A pending login reserves its eventual
active slot. Full capacity returns 409 `radio_session_capacity`; an occupied
pending quota returns 409 `radio_login_pending`. Successful starts remain globally
spaced by one second (429). No eviction or automatic mutation retry occurs.

Each slot owns binding, interface/origin, timestamps, sequence, one outstanding
transaction and a distinct injected crypto object. Production statically constructs
three noncopyable crypto objects; handles are never copied or moved. At most one
ephemeral PSA key is retained, because only pending logins retain one. Active
sessions retain two 32-byte traffic keys and transcript state; PSA lifetime stays
reference counted. Crypto scratch is transient on serialized core 0. The fixed
metadata/crypto size and linked RAM/stack results are recorded below.
No session retains request/response pages: these belong to the unchanged two TCP
tasks. Two large exchanges still require existing memory admission and the 32 KiB
authority reserve; capacity does not promise two maximum-size replies can allocate.

Lookup requires a bounded CR01 header before using its ID as an untrusted selector.
The selected slot must match state, context, sequence and complete AEAD. IDs use
a random prefix and a nonreused boot-local 64-bit serial suffix. Zero, RNG failure,
raw occupied-ID collision and serial exhaustion fail closed without retry loops.
Expiry and every local failure close only the selected slot. Generation, unhealthy
profile and global admission invalidate all affected slots. AP withdrawal and
station address/hostname changes invalidate only the matching interface. Normal
TCP closure leaves login state intact. Nonreused transport transaction identities
route delivery completion across slot reuse, without duplicating board effects.

Management discovery becomes closed `transmitter-management/2`, keeping the old
shape and all old limits except `consumer_sessions:3`, and adding integer
`consumer_pending_logins:1` in limits. Version 1 remains frozen. New Pi accepts
exact versions 1 and 2 with their exact limits/types. Old Pi refuses version 2;
there is no fallback or downgrade. Consumer-Radio/1 bytes/vectors stay unchanged.

Acceptance evidence includes genuine independent crypto handshakes, interleaved
requests, cross-key rejection, isolated failures/expiry/context loss and repeated
reclamation, pending/active quotas, transport ACK/close/timeout isolation, deferred
board-effect isolation, stale configuration conflicts, shared transmitter authority,
native Pi and browser flows, historical exact-source profiles and strict discovery
negatives. Source-pair, sanitizer, cross-link, review and publication results are
recorded below. P15.7 recovery and later roadmap features remain open.

## Review and repair ledger

These are executor adversarial reviews, not independent reviews. The operator's
separate post-execution review remains a distinct gate.

| Severity | Trigger / finding | Affected file | Repair and regression |
| --- | --- | --- | --- |
| P1 | A starts a slow upload, B dispatches a later connection first; a first-draft global transaction-order check rejected A's otherwise valid packet | Pico `src/network/consumer_radio.cpp` | Removed dispatch-order assumption. The unchanged HTTP allocator owns nonreused accept-time IDs; manager checks live duplicate IDs and completion matches the owning slot. Genuine maximum-size slow upload, B login, two retained 32,768-byte ciphertexts and delayed-completion regressions exercise this. |
| P1 | AP withdraws and returns without any HTTP dispatch; the old adapter refreshed session contexts only during dispatch, potentially reviving its old login | Pico `src/network/pico/bootstrap_server.cpp` | Production bootstrap poll refreshes actual AP/station/IP/hostname contexts before session expiry. Compiled actual poll block tests the no-request path; real manager/AEAD tests prove selective AP/station invalidation. |
| P1 | Pi's first version-agreement check indexed a const discovery JSON object before shape validation; a missing schema could abort instead of refusing | Pi `src/wtp_integration/configuration.cpp` | Both configuration and resource coordinators validate the closed document before indexing. Missing schema, array/null documents and valid-but-mismatched version references pass normal and ASan/UBSan regressions. |
| P2 | Old native Pi compared the frozen one-session discovery exactly | Pi `src/wtp_integration/consumer_radio.cpp`; Pico `src/network/management.cpp` | Explicit closed management/2 and exact Pi version-1/version-2 validation; no arbitrary capacity acceptance, downgrade or retry. Historical profiles retain their source identities. |
| P2 | Published CI twice fails before browser assertions because a fresh Chrome debugging endpoint is not ready within ten seconds | Pi `WsprryPi-UI/tests/wtp_network_ui_integration_test.js` and `wtp_pi_fleet_ui_integration_test.js` | Disable first-run/default-browser/background setup and allow a bounded 60 seconds only for initial browser readiness. Workflow assertions retain ten-second deadlines. Both actual local browser workflows and owned-process cleanup regressions pass; successor CI is recorded below. |
| P3 | A fixed manager/crypto object subtotal could be mistaken for its entire retained heap budget | This acceptance record | Name the additional bounded identity/listener/authority string storage, string capacity/allocator overhead and PSA library heap. Bounds were checked against the actual manager and authority validators; target heap high-water remains unmeasured. |

Review also checked header lookup before authentication, nonce/sequence handling,
failed proof/tag/resource cleanup, reference-counted PSA leases, slot reuse,
transaction-specific receipt cancellation, shared revision/owner authority,
profile-generation invalidation, quotas and client-local key cleanup. Sequence
exhaustion closes only its addressed slot. Session and manager objects cannot copy
crypto ownership. Repeating test RNG bytes still produce distinct boot-local IDs.
The final reassessment found no remaining actionable defect in the changed
software scope. Key implementation paths are `src/network/consumer_radio.cpp`,
`src/network/pico/bootstrap_server.cpp` and, in Pi,
`src/wtp_integration/configuration.cpp` and `src/wtp_integration/consumer_radio.cpp`.

Test-controller repairs are evidence limitations, not production defects: bounded
base64 replaces hex control encoding so maximum ciphertext fits the JSON parser;
empty identity bodies are handled explicitly; socket IDs retain the parser's
canonical decimal-string type; profile-generation tests use a fresh request digest
as required by the real journal. Browser fixture script insertion uses a literal
replacement callback. Initial failed logs are retained alongside reruns.
Pi fixture repairs include const-reference iteration under -Werror and waiting
for layout paint before screenshots. Neither changes production validation policy.

## Validation environment and resource budget

Retained Linux image `wsprrypico-p153-env:local` (`c7f2a891a6ff`), GCC 14.2,
CMake 3.31.6 and Node 20.19.2 are reused without network or device mounts. SDK
`079c6f39023649b154152db30f1d781e884879bc`, Mbed TLS
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`, lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95` and Arm GNU 15.3.1 are retained.

The standard and StandaloneRF images cross-link with allocator, topology,
Bluetooth, stack-guard and RF RAM-placement checks. Host metadata is 976 bytes
for the manager, 152 bytes per crypto object and 1,976 bytes for the unchanged
HTTP tasks. Target symbols are manager 864 bytes and all three crypto objects 432 bytes,
1,296 bytes of fixed object storage combined. This subtotal excludes string
backing allocations and PSA library heap. Retained metadata includes the existing
32-character device/boot identities, IPv4 up to 15 characters and canonical
hostname up to 69, plus at most three authority strings up to 72 characters
(hostname and optional `:80`). String capacity and allocator overhead are also
outside that subtotal; this is not a measured whole-manager heap peak. Standard
BSS is 172,572 bytes; StandaloneRF BSS is 328,512 bytes. The linked gaps from
BSS end to heap limit are 302,852 and 146,912 bytes respectively, before runtime
allocations; these are upper bounds, not observed free heap. Manager stack frames
are start 856, finish 584, exchange 1,320 and finish_request 32 bytes. Only one session can retain a private PSA key; active keys
occupy fixed arrays. Target crypto stack-usage entries are create 88, authenticate
544, decrypt 576 and seal 1,784 bytes; main is 4,400 bytes. These are individual
compiler frames, not measured cumulative stack high-water marks.

Worst-case retained session state is fixed; only two HTTP exchanges can own pages.
Two maximum ciphertext uploads occupy 65,536 input bytes plus bounded page/parser
metadata and responses. Building one response can temporarily add envelope and
ciphertext pages and crypto scratch. The existing admission checks preserve the
32 KiB authority reserve and may refuse before both maximum replies fit. Host
large-exchange success does not establish target heap fragmentation or availability.
No on-target heap/stack high-water, phone/Mac transport, timing, GPIO or RF test
has been run or authorized by this software-only prompt.

Actual Chrome 155.0.8059.40 contexts use the shipped page/client against the Linux
HTTP/session/Mbed TLS fixture. Two independent contexts preserve drafts on a stale
save and remain logged in; another context gets finite capacity feedback; logout
releases only that login. Desktop 1280x900 and mobile 390x844 are captured under
light/dark preferences. Pico's incumbent stylesheet explicitly uses light colors
in both preferences; no dark-theme redesign is claimed. Pi's own themed surface
has separate visual checks. No overflow was found in the scoped Pico feedback.

## Documentation Impact and P15.7

The reported physical failed-callsign-save/lost-login observation remains operator
history; no new physical reproduction is claimed. Genuine software tests show a
profile-owned callsign refusal retains both sessions. A deliberately lost encrypted
reply after a durable save clears that client's keys without replay; readback by
another session observes the commit. Relogin can leave an abandoned server slot,
and three occupied slots refuse another login until logout/expiry. This bounded
limit remains; P15.7 broader recovery is open.

Updated: Consumer-Radio session/lifecycle contract, management discovery reference,
architecture, this design/review/acceptance record, browser feedback and Pi
compatibility/fixture references. Considered unchanged: Consumer-Radio/1 vectors,
WTP/1, Config/update schemas, RF/scheduler ownership and historical P15.1-P15.5
acceptance records. Concurrent originating-chat status edits in the existing
handoff, development index and roadmap were preserved during implementation and
integrated into their scoped software-closure update. Pi's unrelated Si5351 work
in parent `f927cfc9f35869ac488f154e853e72b45a9cc123` was preserved, as were
RP1 documentation commit `cdbe74e` and its concurrent merge `1090d1a`.

P15.14 must explain three total sessions, the pending-login quota, one-second
login pacing, independent logout/expiry and abandoned tabs; management/1 versus
management/2 Pi compatibility; retained edits and revision conflicts; readback
after lost replies; saved/active/restart state; and capture final phone/desktop
screenshots once physical concurrency and P15.7 settle. The independent operator
documentation repository is not modified or published by this task.

Concrete operator-doc follow-ups, inspected read-only in WsprryPi-Docs:

- `docs/User_Interface/Setup/Transmitter/index.md#pico-development-controls`:
  connection/session/capacity/conflict/readback workflows and phone/desktop images.
- `docs/Advanced_Operations/ini_configuration/transmitter_backends.md#pico-wtp`:
  WTP transport versus separate management carrier, compatibility and limits.

Shared-passphrase trust, HTTP page substitution and active fake-endpoint offline
guessing remain the existing limitations. This is no general security qualification.

## Software checks and retained evidence

All 13 genuine browser-client/production-HTTP/session/Mbed TLS scenarios pass.
The affected ASan/UBSan run passes 9/9 groups with leak detection, including those
13 scenarios, unchanged vectors, configuration and provisioning delivery tests.
Production adapter regression passes all four compiled branch tests. WTP contract
validation passes 23 schema, seven raw JSON, one framing and eight transition cases.
Both cross-links and the second bounded Chrome workflow pass.

The final serialized complete Pico run passes **190/190**, in 98.55 seconds,
including engineering TLS. Earlier full runs were 189/190 because the unchanged
engineering TLS fixture intermittently lost its worker process. Three isolated
repeats then passed (16.80, 16.86 and 17.12 seconds). The fixture accelerates its
clock fivefold while retaining a 100 ms worker rendezvous deadline (20 ms wall
time); sensitivity to host contention is an inference, not a confirmed root
cause. No production RF/worker deadline was relaxed. Failed earlier runs remain
in the ledger; the clean full result is the later serialized run.

Pi configuration/API checks and 358 simulated production runtime checks pass.
Current native OpenSSL-to-Pico/Mbed TLS station/AP flows, strict discovery,
coordinator shape/version negatives, quota/key/context isolation, durable
journal/readback and all nine shared-resource carrier/state cases pass. Engineering
mTLS loopback passes scheduled 60-second wait, partial I/O, identity/boot failures
and same-request recovery. Two isolated shipped-browser JS contexts also coexist
with the actual native runtime session in one genuine Pico crypto manager;
interleaving, capacity refusal and independent browser/native logout pass with
zero WTP I/O and zero mutations. These are in-process/loopback software tests.

Actual old native `ConsumerRadioClient` source from Pi
`50097e652b4af70d510f4a29d4edf1ffa24d3f0a`, with its unchanged public header,
refuses new discovery with `409 unsupported_management_contract`, logs out its
temporary session, and makes five exchanges with zero mutations or fallback.
The temporary probe's renamed unused main emits a return-type warning. No
production warning policy was weakened; this is not an installed old service test.

| Profile | Exact clean Pico source | Paired Pi result |
| --- | --- | --- |
| legacy | `95aac22bf7cc31b67fe5773761708d743d8a6473` | PASS |
| extended | `dfffdd5220db8b7cf1acf5e74950dbd294283c55` | PASS |
| p152 | `87144d1364f36d04bfe0a714bd1c2f6deb974302` | PASS |
| p153 | `d6208dbc88005383041c5ec306b738db7ec22796` | PASS, genuine station/AP crypto |
| p154 (previous current) | `ddb00dd7960373cec271f7816c0e1b10117416e9` | PASS, genuine station/AP crypto |
| current | `792b5b2f60e381a6bd8e7a7726eeffe24fc08519` | PASS, mixed native/browser and engineering TLS |

Source guards still require exact clean history-bearing checkouts. Local Pi
validation used an isolated base `50097e6` plus the complete scoped overlay;
published-head CI additionally validates the final Pi head including the unrelated
Si5351 parent. All local C++ Pi validation builds ran in Linux, never local macOS;
the existing remote CI retains its macOS portable profile. Affected Pi
ASan/UBSan/leak checks pass for configuration/API, native consumer/coordinator
negatives, mixed native/browser and all nine resource cases after the final repair.
An initial -O1 sanitizer build stopped on GCC's standard-regex maybe-uninitialized
diagnostic; Debug -O0 was used without warning suppression. TLS owner-file rotation
fixtures use Linux tmpfs because overwriting owner-only files on the macOS bind
mount failed. These environment corrections are separate from product changes.

Impeccable context, clarify/craft-floor and scoped detector checks were applied.
Each surface received two bounded actual Chrome workflow passes; both final
detectors report no finding. Pi captures desktop/mobile light/dark, preserved
drafts and failed-save/connection/capacity/pending/rate states. Pico captures three
isolated contexts, stale draft/conflict, independent logout and finite quota
feedback at desktop/mobile sizes; its existing light-only styling is unchanged.

Retained local evidence is outside source control. These files contain no device
capture or deployed firmware evidence:

| Check | Result | Local evidence under `/private/tmp/` |
| --- | --- | --- |
| Pico whole host suite | 190/190 PASS | `wsprrypico-p156/ctest-serial-final.log` |
| Earlier complete runs / TLS diagnosis | 189/190; three isolated repeats PASS | `wsprrypico-p156/ctest.log`, `ctest-final.log`, `tls-repeat.log` |
| Pico real multi-session + sanitizer groups | 13 scenarios; 9/9 groups PASS | `wsprrypico-p156/session-final.log`, `sanitize-tests.log` |
| Production poll adapter / contract / web | PASS | `wsprrypico-p156/adapter-reviewed.log`, `contract.log`, `web-final.log` |
| Both RP2350 cross-links / linked checks | PASS | `wsprrypico-p156/cross-link-reviewed.log` |
| Pico actual browser / detector | PASS; zero findings | `wsprrypico-p156/browser-reviewed.log`, `browser-reviewed/`, `ui-detector.json` |
| Pi config/API / 358 runtime checks | PASS | `wsprrypi-p156/unit.log`, `runtime-recheck.log` |
| Six exact-source profiles | PASS | `wsprrypi-p156/historical-results.log`, `pair-*-test.log`, `current-config-recheck.log` |
| Engineering mTLS / nine resources | PASS | `wsprrypi-p156/current-network.log`, `review-resources.log` |
| Native discovery repair / mixed browsers | PASS | `wsprrypi-p156/review-consumer.log`, `review-mixed.log` |
| Pi affected sanitizer and leak checks | PASS | `wsprrypi-p156/sanitize-unit.log`, `review-sanitize-{consumer,mixed,resources}.log` |
| Old native refusal | PASS within probe boundary above | `wsprrypi-p156/old-native-refusal.log` |
| Pi actual browser / detector | PASS; zero findings | `wsprrypi-p156/browser-reviewed.log`, `pi/src/build/wtp-network/ui/`, `ui-detector.json` |
| Browser startup repair: cleanup / network / Fleet workflows | PASS | `wsprrypi-p156/startup-helper.log`, `startup-network.log`, `startup-fleet.log` |

The retained log filenames document results, not a promise that temporary files
will survive cleanup. The scenarios and reusable fixtures are committed in the
implementation pair.

## Reproduction commands

Linux Pico host checks, with verified pinned local dependency paths:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH="$MBEDTLS_SOURCE" \
  -DWSPRRY_PICO_TEST_LWIP_PATH="$LWIP_SOURCE"
cmake --build build-host --parallel 3
PHASE115_ENDPOINT_DRIVER="$PWD/build-host/endpoint_driver" \
  ctest --test-dir build-host --output-on-failure
python3 tests/phase12_rf_adapter_tests.py
python3 scripts/validate_wtp_contract.py
npm --prefix src/network/bootstrap_web test
npm --prefix src/network/bootstrap_web run build
```

The retained container maps this repository read-only to `/work/pico`, scratch
`/private/tmp/wsprrypico-p156` to `/out`, and its `test-local` subdirectory to
`/work/pico/config/local`. It supplies the Linux `pi` fixture account, no device
mounts and `--network none`. Pinned dependency paths there are
`/work/pico/build/local-sdk-079c6f3/lib/{mbedtls,lwip}`. The successful final whole
suite used `/out/build-host` and was serialized without competing local builds.

The affected sanitizer build adds
`-DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer'` and
`-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined`, with
`ASAN_OPTIONS=detect_leaks=1 UBSAN_OPTIONS=halt_on_error=1`. Its exact CTest
selection is:

```sh
ctest --test-dir build-sanitize --output-on-failure -R '^(consumer_sessions|http_server_tests|consumer_radio_tests|consumer_radio_crypto_tests|bootstrap_slot_tests|bootstrap_join_tests|owner_claim_http_tests|config_updates|management_carrier_tests)$'
```

The existing pinned target configuration was rebuilt with
`cmake --build build/consumer-lan-pico --parallel 3`; it builds both
`WsprryPico` and `WsprryPico-StandaloneRF`. See the log for the actual retained
configuration and linked checks. No image was loaded.

Pi commands run from `src` in Linux, with clean exact Pico and Mbed TLS paths:

```sh
make wtp-config-test wtp-api-test SUDO=
WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 make wtp-network-runtime-test \
  BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= JOBS=2
make wtp-config-interop-test SUDO= \
  PICO_SOURCE="$PICO_SOURCE" MBEDTLS_SOURCE="$MBEDTLS_SOURCE"
make wtp-network-interop-test SUDO= \
  PICO_SOURCE="$PICO_SOURCE" MBEDTLS_SOURCE="$MBEDTLS_SOURCE"
```

The six profile rows use their listed source and explicit `PICO_COMPAT_PROFILE`.
Current `wtp-config-interop-test` includes the native plus two shipped-browser
contexts and nine resource cases. Affected Pi sanitizers use separate build
outputs, Debug -O0, C/C++ instrumentation and matching linker flags. The local
review reran `consumer_interop`, `tests/network/consumer_browser_interop.js` and
`WsprryPi-UI/tests/wtp_resources_interop_test.js` against both normal and sanitized
outputs. No new npm dependency is needed for the self-contained shipped bundle.

Actual browser workflows are opt-in and require existing Chrome and the retained
Linux fixture. From Pico, the final visual run is reproduced with
`node tests/consumer_sessions_browser.mjs /private/tmp/wsprrypico-p156 /private/tmp/wsprrypico-p156/browser-reviewed`.
From Pi's root, run `node WsprryPi-UI/tests/wtp_network_ui_integration_test.js`
after the current resource interoperability test produces its JSON fixtures.
Pi's scoped unit commands are `node WsprryPi-UI/tests/wtp_management_test.js`
and `node WsprryPi-UI/tests/wtp_ui_test.js`. The two-context shipped-bundle test
also runs directly as `node src/tests/network/consumer_browser_interop.js "$PI_NETWORK_BUILD" "$PICO_SOURCE"`.
The startup repair additionally runs `node WsprryPi-UI/tests/browser_fixture_process_test.js`
and `node WsprryPi-UI/tests/wtp_pi_fleet_ui_integration_test.js`. The isolated
local checkout resolves its already-installed `ws` dependency through
`NODE_PATH=/Users/lbussy/GitHub/WsprryPi/WsprryPi-UI/node_modules`; an initial
lookup without that path was blocked before testing. No package was installed.

## Published-head CI and repository state

Initial Pi required CI:
[run 38809630376](https://github.com/WsprryPi/WsprryPi/actions/runs/38809630376),
head `748cb42cd033cc5daabf5b925235d647044dd149`, failed in both attempts.

Attempt 1's current-pair job passed native/Pico interoperability and routing, then
failed before any rendered UI assertion: Chrome's debugging port was still
refusing connections at the fixture's existing ten-second startup deadline, with
the child process still alive. The cause of delayed startup is unconfirmed.
The complete failed job log is retained at
`/private/tmp/wsprrypi-p156/ci-network-failed.log`. This failure is not counted as
a passing browser run. The job rerun was refused while the overall workflow was
in progress. After the release profile passed (15m39s), attempt 1 finished with
nine passing jobs and this one startup failure. A scoped attempt 2 was then
accepted on the identical head and failed at the same startup boundary; its log
is `ci-attempt2-failed.log` beside the first. No source, assertion or startup
timeout was changed before that retry. The repeated failure prompted the bounded
fixture repair in Pi `95b0886`. All product paths and the exact Pico pin compare
identically with `748cb42`; local cleanup/network/Fleet browser checks pass after
the repair. No workflow assertion or production deadline was relaxed.

The fixture-repair head triggered
[run 38813436952](https://github.com/WsprryPi/WsprryPi/actions/runs/38813436952),
head `95b08867e241d2206a2d36e21d2c92a5d62a5e04`. Seven jobs passed; the
three remaining jobs were cancelled when the concurrent RP1 docs merge advanced
`devel`. These cancellations are not passing tests or new assertion failures.
The merge changes only `docs/rp1-gpclk-dkms-installation.md` and
`release_tools/Release Punchlist.md`; P15.6 product, UI, fixtures and pin compare
identically with `95b0886`.

Current published-head Pi CI is
[run 38813894089](https://github.com/WsprryPi/WsprryPi/actions/runs/38813894089),
head `1090d1af6095757fec039e39e09fc5ad70a5706f`: **PASS, all ten jobs**,
completed 2026-10-15 at 22:16:27 UTC.
The verified result is retained at `/private/tmp/wsprrypi-p156/ci-final.json`.
Passing jobs are all five historical compatibility rows, current-pair network
loopback, strict-I2C, broad non-hardware validation, macOS portable and GCC 13
release profiles. The last job ran 15m58s. No cancelled or earlier failed attempt
is substituted for this complete result.
The current-pair network job `116694210211` passes, including the complete
network and Fleet rendered browser workflows after the startup repair. Its log
is `/private/tmp/wsprrypi-p156/ci-network-passed.log`. The delay's original cause
remains unconfirmed; no prior failed or cancelled attempt is relabelled a pass.

Pico's implementation push also completed
[Pages build/deployment run 38808179431](https://github.com/WsprryPi/WsprryPico/actions/runs/38808179431)
successfully at `792b5b2`. This automatic Pages result is not a firmware or host
test CI result; Pico software validation is the local evidence recorded above.

Pico implementation `792b5b2`, Pi implementation `748cb42` and Pi's fixture-only
successor `95b0886` were committed on
their respective `devel` branches, pushed normally to `origin/devel`, and compared
independently with `git ls-remote`. Pi's tree is clean. The Pico closure commit
contains only this record and the three scoped roadmap/index/handoff status
updates. Its final published identity is the documentation commit containing
this section, separate from the tested implementation pin. No PR or release
was created. No other repository was changed.
Pi's current published HEAD additionally includes the preserved concurrent
documentation merge `1090d1a`; that merge is not attributed to this task.
The exact documentation publication SHA is returned with this handoff because a
commit cannot embed its own hash. Final verification compares both local HEADs
against `git ls-remote origin refs/heads/devel` and reports working-tree state.

At the executor handoff, the operator's requested subsequent post-execution
review remained outstanding; the executor's repair/reassessment was not an
independent review. The later originating-conversation assessment follows. No connected
board, flash, GPIO/RF, installed binary or service was touched. Physical phone/Mac
concurrency, target memory high-water/fragmentation and timing/RF acceptance,
P15.7 recovery and all later roadmap slices remain open.


## Separate post-execution review

The originating conversation completed the requested separate adversarial source
and evidence assessment after the operator returned the execution packet. This
is additional to the executor's assessments above. Reviewed published heads were
Pico `b349794119400bc0bbefc6e6fe56c6f85d4d4975` and Pi
`1090d1af6095757fec039e39e09fc5ad70a5706f`, both clean on `devel` and independently
matching their remotes. Production implementation pins remain Pico `792b5b2`
and Pi `748cb42`; the fixture-only Pi repair remains `95b0886`.

The review inspected session/header selection, key and PSA ownership, pending
quota/rate behavior, per-session expiry/context loss, stale delivery callbacks,
global board-effect serialization, management/1 versus management/2 negotiation,
native-client refusal and the changed UI feedback. No actionable production-code
finding was identified. No production, fixture or compatibility-pin changes were
required; the previous implementation pair remains the tested dependency.

One documentation finding was repaired: P15.7 still described the earlier
single-session limit in present tense and requested reproduction before the now
completed P15.5/P15.6 slices. The roadmap now identifies the original observation
as historical, records the current three-session behavior and preserves the
remaining physical reproduction/broader recovery work. Reassessment of the
changed wording and acceptance claims found no remaining actionable finding.
P15.7 remains open.

Fresh checks in this separate review:

| Check | Result / boundary |
| --- | --- |
| Pico focused CTest selection listed above | 9/9 groups pass, including all 13 genuine HTTP/AEAD session scenarios |
| Same selection under ASan/UBSan/leak detection | 9/9 groups pass |
| Additional adversarial probes, normal and sanitized | 88 truncated selectors (lengths 0–43 for finish/request) refuse; an active-session finish packet leaves both active clients usable; a pending login expires at its exact deadline with two healthy sessions preserved; slot reuse/logout reclaim keys and transport state |
| Pi native/crypto and mixed-client refresh | Real OpenSSL/Mbed TLS station/AP/coordinator checks and two browser contexts beside the native runtime pass |
| Pi shared-resource and feedback refresh | All nine carrier/state resource cases and the management feedback/draft tests pass; source unchanged |
| Exact published-head CI | Live `gh run view 38813894089 --repo WsprryPi/WsprryPi --json headSha,status,conclusion,jobs,url` confirms head `1090d1a` and all ten jobs successful; no new CI run was substituted |
| Source identity | Six retained Pi product/fixture/UI source paths were compared byte-for-byte with the published tree before reusing the focused Linux binaries |
| Scoped Impeccable review | Changed feedback source and retained Pico mobile-light/Pi desktop-dark capacity renders inspected; detector reports `[]`; no user-interface change required |

The focused normal and sanitizer commands used the nine-group CTest expression
in the reproduction section, existing `/out/build-host` and `/out/build-sanitize`,
read-only repository mounts and writable scratch outputs. The bounded extra
probes imported the committed `Fixture`/genuine browser crypto helpers, used the
same production HTTP/Mbed TLS drivers and checked healthy clients after rejection
and expiry; they did not substitute a second session implementation.

Fresh logs are `/private/tmp/wsprrypico-p156/post-review-{normal,sanitize,probes,probes-sanitize}.log`
and `/private/tmp/wsprrypi-p156/post-review-{consumer,mixed,resources,ui}.log`.
Live CI metadata and detector output are under `/private/tmp/p156-post-review`.
Initial review commands made CTest and the resource fixture scratch mounts
read-only, causing log/JSON-output write refusals; those environment errors were
corrected before successful reruns. No application assertion or timeout was
relaxed. The failed resource attempt is retained as
`post-review-resources-readonly.log`.

The unchanged whole-suite 190/190, six-profile matrix, 358 runtime checks,
firmware cross-links and full Chrome workflows remain the executor's evidence
above; they were not all rerun for this documentation-only review closure.
The separate pass ran the focused refreshes described here and inspected existing
visual captures rather than claiming another complete browser/render campaign.
Both Pico and Pi repositories were read-only during those software checks; only
Pico development/roadmap documentation is changed for this publication.

Documentation impact: updated this appended assessment, the handoff status and
P15.7's historical/current distinction in the roadmap. Current protocol/API,
implementation, source pins and the independent operator-documentation repository
remain unchanged. The exact P15.14 follow-ups above still apply. No hardware,
flashing, GPIO/RF, installed-service or unrestricted security qualification is
added. Physical qualification, P15.7 and later slices remain open.
