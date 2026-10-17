# Phase 15.3 supported management carriers

Current-policy notice: the historical USB exclusions below are superseded by
[the production USB slice](usb-control-results.md). This record retains its
original implementation and evidence scope; network policies remain unchanged.

Status: complete within the recorded software acceptance. October 15, 2026. P15.1/P15.2 remain closed; P15.4 and later work is excluded.

## Refreshed baseline and source gaps

Both devel working trees were clean before this task. Pico was
`b013504aea54d2f9474da0cbae1678c69fb98def`, including the independently committed
RF-adapter stand-in repair; Pi was `6a39398bb23d69ba0628e1b82171717040115ec8`.
No concurrent fixture change was imported into this task.

Pico `network/consumer_radio.cpp` already dispatches authenticated encrypted
station/AP requests to BrowserApi and owns one volatile session. Its setup
adapters own Wi-Fi/station identity. `network/pico/server.cpp` admits engineering
mTLS HTTP, engineering field HTTPS, and consumer TLS WTP with distinct policies.
Plain LAN WTP has no JSON management. Normal consumer builds select Plain LAN.
`application/resources.cpp` retains legacy `authenticated_https` metadata.

Pi `wtp_runtime_bridge.cpp` rejects all management unless job transport is
`network`; `WtpApplication::idle_management` requires fresh WTP negotiation.
`configuration.cpp` coordinates identity/revision/capability reads and one write,
and strictly validates the application resource. P15.1 added no carrier; P15.2
added that coordinator, safe legacy preservation and four source-pair checks.
The TLS-only loopback fixture does not exercise consumer crypto or interface
admission. These are the implementation gaps selected here.

## Selected contract

Management selection is independent of the configured WTP job transport.
Engineering HTTPS keeps its current default and authentication. The Pi adds an
explicit, volatile Consumer-Radio/1 selection for the configured member's exact
32-hex device ID and operator-entered IPv4 or local hostname. AP authority is
exactly `192.168.4.1`. No Wi-Fi configuration changes, redirect, alternate
address/authority/interface session migration, carrier fallback or write retry
is permitted. USB JSON management is unsupported: no current requirement needs
a second USB configuration protocol. Console commands retain their separate
local policies; WTP reachability grants no JSON administration.

The independently versioned `transmitter-management/1` discovery document
describes the actual selected carrier, target, profile/generation, support,
availability, operation allowlist and budgets. It is separate from closed
application objects; legacy `authenticated_https` remains unchanged. Public
consumer identity is only a handshake hint. The encrypted discovery response
must match the authenticated session before Pi consumes remote capabilities.
Unsupported/malformed advertised versions refuse; absent discovery preserves
only the existing explicitly selected engineering compatibility path.

The Pi host adds `/api/v1/member/management` GET/POST actions: POST carries an explicit `connect` or `disconnect` action;
consumer connect includes carrier (`consumer_station` or `consumer_ap`), exact
host and passphrase. Engineering selection uses an explicit action. This route
uses the existing protected shared API guard, operation mutex and idle admission.
No password enters saved INI, ordinary catalogs, URLs, status or browser storage.
The passphrase exists only during login, then is wiped; only bounded traffic
keys survive in process RAM. Disconnect logs out only the session created by
this client. Busy sessions refuse without logout or eviction. Expiry, rejection
or uncertain delivery clears local session state and requires explicit login
and authoritative settings readback before a subsequent write.

Consumer crypto is trusted local C++ using existing OpenSSL: X25519,
SHA-256/HKDF and ChaCha20-Poly1305, exactly Consumer-Radio/1's unchanged
transcript/header/sequence. No device JavaScript is loaded. Outer HTTP status
never establishes inner API success. Device/boot/generation are authenticated;
Host/Origin plus actual Pico interface remain server-side session bindings.
The shared passphrase identifies a group of holders, not a uniquely authenticated
device. It is not a PAKE and does not resist an active peer who knows that
passphrase. Native local code avoids browser page substitution but does not
upgrade this cryptographic trust model or replace engineering mTLS.

Management-only admission may skip opening WTP only when the existing host
application has no active/waiting/owned/loaded/faulted/uncertain work. It retains
the same application control lock and runtime operation mutex. Authenticated
consumer management provides device/boot identity; remote configuration status
still requires idle/unowned/inactive/nonfaulted state. Previously unresolved
host output cannot be cured by selecting a management carrier.

## Carrier/access matrix

All JSON mutations retain complete validation, verified atomic journal writes,
exact revisions/target and modern ABA protection, STOP/cursors, member recurrence,
saved/active/restart latches and matching-transaction deferred delivery. All
unsupported combinations refuse without fallback or mutation. Firmware support
is distinct from current listener/profile availability and Pi-client selection.

| Profile / carrier | Jobs | JSON management / Pi client | Principal and identity | Availability / restrictions / budget | Evidence and limit |
| --- | --- | --- | --- | --- | --- |
| Engineering station mTLS HTTPS | WTP ALPN, same JobService | Existing finite config/schedules/network + coordinated settings; preserved Pi support | Certificate principal; WTP device/boot plus revisions; new authenticated discovery when advertised | Configured credentials, station/TLS clock; existing 2 connections/1 WTP/1 handshake, 32,768 HTTP body; config 1,800/update 2,048 | Exact-source engineering loopback and paired regressions passed; no new physical claim |
| Engineering field HTTPS | Existing admitted browser job operations | Firmware Configure in normal authenticated surface; no Pi field-cookie client selected | Server TLS plus application password/cookie/session; exact device/revision | Blank/preclock Configure refused; current access/ownership/session rules unchanged | Existing firmware/host tests; Pi unsupported explicitly |
| Consumer station Consumer-Radio/1 | Existing encrypted browser jobs | Existing firmware JSON; new explicit Pi client for config/schedules/network + coordinated settings | Saved Wi-Fi-passphrase holder; authenticated device/boot/profile generation, exact station IP/hostname authority | Association+IPv4, no WTP or UTC prerequisite for management; one shared login, 30 s login, 5 min idle/15 min total; mutation idle/unowned/nonfaulted | Actual native OpenSSL/Mbed TLS/BrowserApi software interoperability passed; no bench operation |
| Consumer AP Consumer-Radio/1 | Existing encrypted jobs when admitted | Existing firmware JSON; new explicit Pi client with pre-existing network reachability | Same protocol, exact AP authority and actual AP interface | Temporary AP lease/fallback; RF policy can withdraw AP; no automatic Pi network change; same session/byte limits | Actual AP-classified deterministic interoperability passed; physical routing remains a gate |
| USB WTP / Console, engineering | WTP reference job control; Console local policies | USB JSON unsupported, Pi JSON client unavailable | USB role/identity and existing local policy, no JSON principal | Preserve roles, frames and Console commands; no new parser or framing | Existing tests; no USB JSON qualification |
| USB WTP / Console, consumer | WTP intentionally disabled; Console retained | Unsupported | Existing local Console policy | No implicit administration from USB connectivity | Existing source/tests |
| Plain LAN WTP / optional consumer TLS-WTP | Jobs only | No JSON on either; independent consumer management selection allowed | LAN principal / TLS-WTP's existing principal; WTP IDs only | Plain station port 31417 after SNTP; optional TLS ALPN WTP only; no automatic substitution | Existing WTP tests; no carrier expansion |
| BLE WTP | Existing engineering encrypted local control | JSON unsupported, no Pi JSON client | Existing Field-GATT/password/session identity | Existing field policy and bounds; consumer BLE unselected | Existing tests; WTP/1 unchanged |
| Consumer preclock | WTP clock gate retained | Consumer station/AP JSON available when listener/profile admitted, including without WTP | Authenticated Consumer-Radio identity/generation | Job UTC policy remains; JSON Configure still uses shared idle/health gate | Management-only admission and refusal tests passed |
| Blank / recovery / unavailable profile | Only existing explicitly admitted provisioning/recovery paths | No P15.3 JSON carrier; advertise unavailable only where an authenticated path exists | Public hints authorize nothing | No synthetic authenticated principal, no new recovery authority; fail closed | Negative profile/discovery tests passed; P15.7 redesign excluded |

## Routes and resource budgets

Consumer transport uses only port 80, GET `/api/consumer/v1/identity` and POST
`/api/consumer/v1/start`, `/finish`, `/request`. Start body <=512 bytes.
No cookies, redirects, CORS, arbitrary URLs or device scripts. Each network
exchange has a finite deadline; login completes inside the 30 s server window.
The encrypted management allowlist is GET capabilities/status/config/schedules/
network/application/management, PUT config/schedules/network, POST config/update,
and client-session logout. No provisioning, restart, hardware editor or job
submission is added to the Pi proxy.

HTTP body is <=32,768 bytes; CR01 header+tag consume 44, leaving 32,724 plaintext
bytes. The inner JSON envelope and escaping count within that limit. The
coordinator's <=2,048-byte body and resulting <=1,800-byte Config remain tighter;
actual serialized envelope size is checked, including path/revision overhead.
Responses authenticate completely before JSON/status/ETag parsing; coordinator
reads remain <=16,384 bytes. No new Pico frame pools or firmware budgets.

## Acceptance and review ledger

Initial acceptance plan (results recorded below): deterministic Linux host/TLS/lwIP and cross-link checks,
actual Pi/OpenSSL-to-Pico/Mbed TLS station/AP integration, negative and lifecycle
coverage, P15.2 four-pair compatibility, UI tests and desktop/mobile light/dark
rendering, independent adversarial review/repair/reassessment, exact clean pins,
CI and independent origin/devel parity. Exact commands/results go here as run.

No physical device, installed service, GPIO or RF operation is authorized or
claimed. Operator documentation in WsprryPi-Docs is read-only; P15.14 retains
final user documentation. Exact P15.14 follow-up is recorded in the companion review: update
`docs/User_Interface/Setup/Transmitter/index.md#pico-development-controls` for
independent carrier selection, expected member ID, authority/reachability,
transient credentials, busy/expiry/readback and saved/active/restart state; review
`docs/Advanced_Operations/ini_configuration/transmitter_backends.md#pico-wtp`
for consistency. No durable secret or WTP/INI credential was added.

An active fake endpoint can choose its own X25519 key, obtain the client's
password-derived finish proof and test password guesses offline against its
known shared secret/transcript. Passive capture alone does not provide that
shared secret. This existing protocol limitation remains; a strong passphrase
and trusted endpoint/network matter. Native local code prevents device-page
execution but does not authenticate a unique device before emitting that proof.

## Independent review round 1 and repairs

The independent read-only reviewer reported five actionable findings, plus the
known test defect below. All were repaired and rechecked before closure:

1. Read authoritative local management state on reload and preserve an existing
   consumer session on an already-selected refusal; disable duplicate Connect.
2. Execute the genuine consumer fixture in the current Make/CI interoperability
   path, retaining historical profiles.
3. Install parsed-password cleansing before endpoint/already-session rejection.
4. Match engineering station availability to TLS admission and synchronized,
   nonzero UTC; distinguish unavailable listener/AP drain and blank source.
5. State active fake-endpoint offline password guessing in both protocol and
   client documentation; do not claim PAKE or unique-device authentication.
6. Replace the faulty lost-reply case with a dropped encrypted mutation response
   after verified journal commit, followed by no replay, expiry/relogin,
   authoritative readback and stale-revision refusal through the coordinator.

Additional author repairs preserve an explicit disconnected selection across
runtime endpoint replacement, erase expired traffic keys from idle polling,
and separate host built-in adapter capability from authenticated remote support.
Impeccable's first visual pass found unreadable dark secondary buttons; scoped
existing-theme colors repair that contrast. The second bounded render pass confirmed the affected layout and feedback.

Preliminary validation: seven focused Pico tests passed; the full Linux suite
passed 187/187 after supplying the required fixture user and Python/retained JS
dependencies. The RP2350 Arm target cross-link passed using retained SDK
`079c6f39023649b154152db30f1d781e884879bc` and Arm GNU 15.3.1. Later metadata
repairs require affected rechecks. Pi configuration/API and UI unit checks and
initial real consumer integration passed; final vector/lost-reply, runtime,
exact-clean source-pair and sanitizer results remain pending.

The second independent read-only assessment found no remaining actionable Pico,
protocol, runtime or UI defect in its bounded pass. It verified reload-state
restoration, disabled duplicate Connect, parsed-password cleanup, carrier/clock
availability, current-profile fixture execution and corrected lost-write
assertions. It approved a provisional Pico dependency commit after affected
checks; this is not joint P15.3 completion. Final evidence reassessment remains.

## Discovery wire document

`GET /api/v1/management` returns exactly `schema`, `target`, `profile`, `preclock`,
`profile_generation`, `selected`, `carriers`, `unsupported`, `operations`, `limits`.
The target is the existing closed member/device/boot object. Profile is one of
`unavailable`, `blank`, `recovery`, `engineering`, `consumer`; generation is a
nonzero canonical uint64 decimal string or null. `preclock` is boolean.
Selected is `engineering_mtls`, `engineering_field`, `consumer_station` or
`consumer_ap`. The carriers array has those four rows in that order, each exactly
`carrier`, boolean `built_in`, boolean `available`. Availability describes the
current profile/listener/admission, including mTLS UTC gating; resource BUSY,
ownership and transient capacity still govern individual operations.

Unsupported is exactly `["usb_json","plain_wtp_json","tls_wtp_json","ble_json"]`.
Operations is the common bounded configuration subset, not an exhaustive list
of every existing BrowserApi/job/setup function:

```json
{"GET":["capabilities","status","config","schedules","network","application","management"],"PUT":["config","schedules","network"],"POST":["config/update"]}
```

Limits is exactly the integer-valued object:

```json
{"http_body":32768,"consumer_plaintext":32724,"config":1800,"update":2048,"login_ms":30000,"idle_ms":300000,"absolute_ms":900000,"consumer_sessions":1}
```

No fields are inserted into the old closed application objects. Pi checks exact
known shape/types, selected availability and authenticated target/profile binding.
Present unsupported discovery refuses; absent discovery is accepted only on the
explicit existing engineering path. Each consumer HTTP exchange has an 8-second
deadline including resolution/connect, and does not follow redirects. Each
coordinated operation is finite; browser timeout remains the existing 180 seconds.

Pico dependency acceptance before paired testing: final Linux host suite passed
187/187 with no skips; WTP validator passed 23 schema, seven raw JSON, one framing
and eight transition cases. Six affected ASan/UBSan checks passed without
sanitizer diagnostics. Final RP2350 target cross-link passed after the admission/
UTC metadata repairs. The exact-source companion pin will reference the reviewed
Pico dependency commit; joint acceptance is still pending, so the roadmap remains
pending in this provisional commit.

## Final local software acceptance (2026-10-15)

The final bounded independent reassessment found no remaining actionable
implementation finding. All six first-round findings were repaired and their
affected checks rerun. It separately verified the exact-source fixture, source
guards, current CI invocation and task-only 289-check runtime result. CI is a
separate acceptance step below.

Exact clean Pico source pairs, with this companion implementation:

| Profile | Pico commit | Result |
| --- | --- | --- |
| current | `d6208dbc88005383041c5ec306b738db7ec22796` | Engineering network/config, modern and unchanged old producer, plus genuine consumer fixture passed |
| P15.2 | `87144d1364f36d04bfe0a714bd1c2f6deb974302` | Original modern/old-producer P15.2 regressions passed |
| extended | `dfffdd5220db8b7cf1acf5e74950dbd294283c55` | Original new-client/extended-server regression passed |
| legacy | `95aac22bf7cc31b67fe5773761708d743d8a6473` | Original new-client/legacy-server regression passed |

The original four P15.2 combinations remain exercised; the current profile adds
new-client/new-discovery and old-client/new-discovery coverage. Clean Pico and
Mbed TLS source guards remain mandatory. The Pi source used for final runtime
validation was baseline `6a39398` plus the explicit task file inventory and only
three task Makefile hunks; concurrent PPM/chrony/scheduling/UI/release work was
excluded from its compiled sources and will remain outside the task commit.

Reproduction commands inside the identified isolated Linux environment (Pico
from its root; Pi from `src`; UI from `WsprryPi-UI`):

```sh
cmake -S . -B build/p153 -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/deps/mbedtls -DWSPRRY_PICO_TEST_LWIP_PATH=/deps/lwip
cmake --build build/p153 --parallel 2
ctest --test-dir build/p153 --output-on-failure
python3 scripts/validate_wtp_contract.py
make wtp-config-test wtp-api-test SUDO= WTP_NETWORK_BUILD_DIR=/tmp/p153-config-final
WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 make -j2 wtp-network-runtime-test \
  BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= WTP_NETWORK_BUILD_DIR=/tmp/p153-network
make wtp-network-interop-test SUDO= WTP_NETWORK_BUILD_DIR=/tmp/p153-current \
  PICO_SOURCE=/work/pico-current MBEDTLS_SOURCE=/deps/mbedtls
make wtp-config-interop-test SUDO= WTP_NETWORK_BUILD_DIR=/tmp/p153-current \
  PICO_SOURCE=/work/pico-current MBEDTLS_SOURCE=/deps/mbedtls
# For each legacy/extended/p152: configure/build the same CMake fixture with
# PICO_COMPAT_PROFILE and that exact clean source, then run the same Node driver:
node ../WsprryPi-UI/tests/wtp_configuration_interop_test.js /tmp/p153-p152 p152 /work/pico-p152
npm test
node tests/wtp_network_ui_integration_test.js
```

Results: full Pico host suite **187/187, no skips**; seven focused Pico checks;
unchanged WTP validator **23 schema, 7 raw JSON, 1 framing, 8 transition**;
Pi configuration/API checks; task-only production runtime **289 checks**; all
four exact-source profiles above; UI unit and browser integration checks passed.
Initial full-suite failures were missing Python fixtures/fixture user and were
rerun successfully after environment repair. The earlier RF-adapter stand-in
failure is fixed by the pre-existing baseline commit, not this task.

Six affected Pico tests and Pi config/API tests passed ASan/UBSan using
`-fsanitize=address,undefined -fno-omit-frame-pointer`. Retained lwIP is
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`, Mbed TLS is
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`. The existing RP2350 cross-link
`cmake --build build/consumer-lan-pico --parallel 2 --target WsprryPico`
passed with retained SDK `079c6f39023649b154152db30f1d781e884879bc` and Arm GNU
15.3.1, including post-link topology, pool/heap-hook and stack-guard checks. This was a cross-build; no
local native macOS C++ application build or physical firmware load occurred.

Impeccable was used before and during UI changes. Two bounded visual batches
covered desktop/mobile light/dark entry, connected and busy states. The first
found dark secondary-button contrast; scoped existing-theme colors repaired it.
The second confirmed the affected layout and feedback, with no horizontal
overflow. Reload restoration, duplicate Connect, session-busy, draft preservation
and management selection independent of WTP were exercised. Screenshots are
generated test artifacts under `src/build/wtp-network/ui`; they use a mocked
backend and do not establish an installed service or physical routing.

Local evidence logs are retained outside version control in
`/private/tmp/wsprrypico-p153`: `pico-final-full.log`, `pico-sanitize.log`,
`wtp-contract.log`, `pico-arm-format.log`, `pi-final-focused.log`,
`pi-sanitize.log`, `pi-task-only-runtime.log`, `pair-current-network.log`,
`pair-current-config.log`, `pair-{legacy,extended,p152}-test.log`,
`ui-final-unit.log` and `ui-final-browser.log`. These temporary files are
supporting local evidence; the committed commands, pins and assertions are the
reproducible record.

The actual native consumer/OpenSSL-to-Pico crypto/coordinator integration also
passed ASan/UBSan without diagnostics, including fixed vectors and all fixture
negative cases (`consumer-sanitize.log`). The isolated task-only UI `npm test`
passed after reusing retained `ws` and other JavaScript dependencies; its initial
missing-module failure was environmental and was rerun.

## Final evidence-review repairs

The final documentation review clarified that no **local** native macOS C++
application build ran; the unchanged hosted macOS CI profile is separate.

Independent CI evidence review found a pre-existing packet-capture drain race in
`src/tests/wtp_pi_reply_routing_test.py`. Parent run 38760244313 completed real
HELLO/STATUS exchanges but retained only an incoming SYN before immediate
capture shutdown. The repair enables tcpdump immediate mode and observes the
whole capture until a bounded quiet interval (minimum 0.5 seconds elapsed,
0.25 seconds quiet, maximum 3 seconds), then retains capture statistics.
It never stops at the first matching reply. The baseline `wifi0` requirement
and exact fixed `{'eth0'}` assertion are unchanged; production routing is unchanged.

The independent reassessment found no actionable issue in the repair. Python
syntax and whitespace checks passed. Three finite actual namespace regressions
passed in network-disabled disposable Linux with private namespace capabilities:

```sh
make wtp-pi-routing-probe BACKENDS=simulated ANCILLARY_GPIO=0 SUDO=
python3 tests/wtp_pi_reply_routing_test.py --probe build/wtp_pi_routing_probe
```

All three runs reproduced baseline `wifi0` and fixed `eth0` replies; each fixed
capture had 39 packets captured/received and zero kernel drops. Tools were
iproute2 6.15.0-1 and tcpdump 4.99.5-2 in the disposable container, with no host
installation or hardware mounts. Initial read-only container sysctls prevented
the fixture before packet execution; allowing the fixture's private sysctls
resolved that environment limitation. Evidence is retained as
`routing-check-{1,2,3}.json`, `routing-check.log` and `routing-probe-build.log`
in the local temporary evidence directory. This validates software routing and
capture behavior only. Required CI is rerun after this harness repair; final
joint outcome remains in the lead acceptance record.

## Exact affected sanitizer commands

Pico (the retained C Mbed TLS library and system OpenSSL are not a fully
sanitized dependency build; owned C++ adapters/coordinator paths are instrumented):

```sh
cmake -S /work/pico -B /work/pico/build/p153-sanitize -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/deps/mbedtls \
  '-DCMAKE_CXX_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer' \
  '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined'
cmake --build /work/pico/build/p153-sanitize --parallel 2 --target \
  management_carrier_tests config_update_tests consumer_radio_tests softap_api_tests \
  application_resource_tests consumer_radio_crypto_tests
ctest --test-dir /work/pico/build/p153-sanitize --output-on-failure \
  -R '^(management_carrier_tests|config_updates|consumer_radio_tests|softap_api_tests|application_resources|consumer_radio_crypto_tests)$'
# Pi, from src:
make wtp-config-test wtp-api-test SUDO= WTP_NETWORK_BUILD_DIR=/tmp/p153-sanitize \
  WTP_NETWORK_CXXFLAGS='-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer' \
  WTP_NETWORK_LDFLAGS='-fsanitize=address,undefined'
```

The actual native crypto/coordinator fixture used this additional compile/run
command in the isolated Linux source copy (development sanitizer fixture,
separate from the mandatory clean-source CMake interoperability guards):

```sh
#!/bin/sh
set -eu
cd /work/pi/src
make wtp-config-client-build SUDO= > /work/pi-client-build.log 2>&1
c++ -std=c++20 -pthread -Wall -Wextra -Wpedantic -Werror -UNDEBUG -DWSPRRYPI_CONSUMER_CRYPTO_TEST -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer \
  -I. -IWTP-Client/include -I/work/pico/src -I/work/pico/tests -I/deps/mbedtls/include \
  '-DMBEDTLS_CONFIG_FILE="/work/pico/src/network/pico/mbedtls_config.h"' \
  tests/network/consumer_interop.cpp wtp_integration/consumer_radio.cpp wtp_integration/configuration.cpp \
  wtp_integration/browser_api.cpp wtp_integration/network_http.cpp wtp_integration/plain_tcp.cpp wtp_integration/tls.cpp \
  wtp_integration/application.cpp wtp_integration/status.cpp wtp_integration/scheduler.cpp wtp_integration/backend.cpp \
  wtp_integration/execution_plan.cpp WSPR-Transmitter/src/execution_plan_compiler.cpp WSPR-Transmitter/src/transmission_controller.cpp \
  /work/pico/src/network/pico/consumer_radio_crypto.cpp /work/pico/src/network/pico/psa_lifetime.cpp \
  /work/pico/build/p153-sanitize/libwsprrypico_core.a /work/pico/build/p153-sanitize/mbedtls/libmbedcrypto.a \
  build/wtp-network/client/libwtp_client.a -lssl -lcrypto -o /work/consumer-sanitize
/work/consumer-sanitize /work/pico/docs/protocol/Consumer-Radio-v1-vectors.json
```

All six Pico targets, Pi focused checks and the actual consumer fixture passed
without sanitizer diagnostics. These are bounded software checks, not a full
cryptographic library audit.


## Joint software closure and publication

The final required [Pi CI run](https://github.com/WsprryPi/WsprryPi/actions/runs/38766594946)
at `61542aff2e6965b8773053a2429f9b42b863bf98` passed all eight jobs, including
current engineering network/config interoperability and actual native consumer
fixture execution, all three historical profiles, UI, strict I2C, semantics/
simulation, the existing macOS CI profile and all six GCC 13 release profiles.
The first attempt passed seven jobs and the full actual carrier/routing
checks, then failed at Chrome debugging-port startup before UI rendering.
Only that failed job was rerun on a fresh hosted runner. Earlier passes are
retained; no partial, failed or cancelled result is described as a full pass.
The original run at
`a5605c5` had five successful jobs and three cancelled jobs when concurrent
`c605142` advanced devel; its successor was superseded by the final record-only
publication. Run 38765432377 at record-only `9b4d78f` was likewise
superseded by the independent reviewer's local-versus-hosted macOS wording
correction; that run was then superseded by the reviewed routing capture
repair. No cancelled result is counted as final CI acceptance.

Accepted pair: Pico implementation dependency
`d6208dbc88005383041c5ec306b738db7ec22796` with Pi final companion revision
`61542aff2e6965b8773053a2429f9b42b863bf98`. Pi implementation is
`a5605c54630d501dc84b51ea7834f59768a250ef`; the final companion revision also
retains independent Chrony commit `c605142`, acceptance-record updates and
the independently reviewed CI capture-drain repair described above.
The [companion record](https://github.com/WsprryPi/WsprryPi/blob/61542aff2e6965b8773053a2429f9b42b863bf98/docs/development/phase15-3-management-carriers.md)
contains exact historical pins, commands, credential rules and operator-doc follow-up.

Pico's later closure commit changes only this record, the development index and
P15.3 roadmap status/summary references. It does not change the implementation
source used by the exact-clean fixture and does not replace the explicit
reviewed dependency pin. Independent ls-remote verified the pushed companion
revision. Final Pico parity and its configured Pages CI are checked after this
record-only publication; local Linux and cross-link evidence remains as above.

All references to avoiding native macOS builds concern the shared local Mac.
The unchanged required GitHub workflow ran its existing hosted macOS simulated
profile; local C++ validation used Linux or the supported Arm cross-toolchain.

P15.3 is complete within this deterministic software acceptance. P15.1/P15.2
closures are preserved. P15.4 remains unimplemented and next: shared application,
station and hardware resource adoption. No P15.5+ work was started.

### Documentation Impact

Updated: browser API and independently versioned carrier discovery, access
matrix/security/credentials, Pi adapter/UI compatibility, shared contract and
USB references, development/review indexes and P15.3 roadmap status.
Considered unchanged: WTP/1, Config v1 storage/Console policy, profile/setup
authority, recurrence/STOP/cursors and P15.1/P15.2 closure records.
Still required in P15.14: the exact operator-manual routes and screenshot
follow-up listed above; Wsprry_Pi_Docs was inspected read-only and not changed.

The physical gate remains a finite identified Pico 2 W firmware/profile and Pi
service/client test over actual station/AP interfaces and exact authorities,
with session/busy/expiry/lost-reply behavior and setup restoration recorded.
No bench, physical USB, installed service, GPIO or RF operation occurred here.
Shared-passphrase impersonation, active fake-endpoint offline password guessing,
one session, temporary AP availability and operator-established AP reachability
remain explicit protocol/product limits; no unrestricted security qualification
is claimed.

The final evidence reassessment also confirmed the browser startup log could
not establish a Chrome failure cause; no OOM/profile/sandbox diagnosis is
inferred. The unchanged failed-job rerun succeeded on a fresh hosted runner.

Final hosted routing evidence retains three kernel drops in the deliberately
misrouted baseline capture; that capture still records `wifi0` replies. The fixed
capture records 39 captured/received packets with zero kernel drops and only
`eth0` replies. No loss-free baseline-capture or physical-network claim is made.

Final independent reassessment verified the accepted CI head/attempt, all eight
successful conclusions, pins, retry accounting and unchanged P15.4+ entries; it
reported no remaining actionable findings and supported this bounded closure.

Target cross-link identity: `pico2_w`, `rp2350-arm-s`; the retained cache carries
historical version label `0.1.0-rc.3-password-eye-7bff45c`. This source cross-link
is not a newly labelled release artifact or deployed-image qualification.
