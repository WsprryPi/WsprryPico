# P15.5 concurrent web service

Status: P15.5 complete within the software acceptance recorded below. WsprryPico leads this slice. The
[execution prompt](phase15-5-execution-prompt.md) was written before implementation
and executed in this conversation on `devel`.

## Initial code review

The initial Pico head was `36aca3612af1066d6aed182e303b6f742b70de22`, clean and
tracking `origin/devel`. Pi was inspected read-only at
`50097e652b4af70d510f4a29d4edf1ffa24d3f0a`, with the unrelated
`release_tools/Release Punchlist.md` edit preserved.

P15.3 added versioned carrier discovery and the Pi's native authenticated
Consumer-Radio/1 client. P15.4 added Pi adoption of Pico's existing shared
application/station/hardware/pin resources. Those contracts do not require a
second coordinator, another JSON API, or a Pi implementation change for P15.5.

The bottleneck was `PicoBootstrapServer`: a single TCP client, parser, response,
interface, deadline and transaction prevented a second port-80 client from
progressing. Its receive callback also dispatched application work. Engineering
`PicoServer` already had two bounded cooperative connections, alternating poll
order and per-connection delivery tracking. ConsumerRadioApi intentionally has
one authenticated session and one pending exchange; P15.6 owns increasing that
capacity and P15.7 owns failed-save/session recovery. The documented
`radio_session_busy` observation remains evidence; this software-only task did
not reproduce that physical sequence.

The raw bootstrap completion path also treated peer FIN as delivery in one
branch. Provisioning trials/restarts waited for absence of the singleton TCP
client, and owner-status restart evidence lived in shared dispatch scratch.
Those assumptions required repair when adding concurrent requests.

## Implementation and resource policy

`PicoHttpServer` provides two fixed cooperative connection tasks on core 0.
This implements the roadmap's concurrent-service intent without OS threads or
an RTOS. Raw lwIP callbacks parse/record input and ACKs; foreground polling
dispatches application requests and streams replies. Crypto, BrowserApi,
JobService, the scheduler, revision checks and flash commits retain their one
serialized owner. Core 1 remains dedicated to the RF worker.

| Resource | Bound/behavior |
| --- | --- |
| Port-80 connections | Two across AP and station; excess connections reset without evicting admitted clients |
| Task storage | Compile-time `sizeof(PicoHttpServer) <= 2048`; retained Linux build reports 1976 bytes, excluding dynamic buffers/lwIP |
| HTTP input | Existing 2048-byte headers and 32768-byte body maximum; narrower setup-route limits retained |
| Header admission | Each incomplete-header fragment requires 32768 bytes of shared heap workspace above the existing 32768-byte authority reserve; pressure resets that connection before parser growth |
| Body admission | Existing shared paged-buffer admission; already reserved body pages continue without requiring another header allowance |
| Output | At most one 1024-byte chunk per task per poll; first task alternates each poll; immutable assets borrow flash storage |
| Lifetime | Absolute ten seconds from accept, including partial input and stalled ACKs; traffic does not extend it |
| HTTP exchange | One request/connection, no pipelining or keepalive extension |
| Delivery identity | Monotonic high-bit transaction namespace; stop/start does not reset it; exhaustion fails admission before reuse |
| Other transports | Engineering HTTPS remains two slots; existing aggregate four TCP PCBs, 32 KiB lwIP heap and packet/segment pools remain unchanged |
| Authentication | One consumer session and one pending exchange retained; concurrent transport is not simultaneous authenticated-login acceptance |

The heap figures are an admission policy and compile-time/source bounds, not
measurements of target fragmentation, transient peak heap, stack or RF latency.
The shared lwIP TCP pool, including closing connections, can refuse admission
before the port-80 task limit is reached. No transport is promised a dedicated
PCB under aggregate overload.

Each task owns its parser, response, offsets, pending ACK bytes, interface and
transaction. Teardown detaches callbacks, securely releases parsed input,
releases response/header storage and clears the slot before invoking application
delivery hooks. lwIP error callbacks never free the already-freed PCB. LISTEN
PCBs use `tcp_close`, and receive callbacks return `ERR_ABRT` whenever teardown
actually aborts their PCB, including a failed graceful close after full ACKs.

New accepts bind to the actual receiving netif. Each poll rechecks interface
admission independently. AP drain closes new accepts while allowing admitted
AP replies until withdrawal or deadline. Withdrawing AP leaves a valid station
connection intact. Page Host values do not select the interface.

Provisioning uses one transaction-scoped delivery receipt for network submit,
network ACK, owner submit or committed owner-status replies. While it is
outstanding, competing raw setup/API calls receive `409 setup_response_pending`;
authenticated setup adapters share the same receipt gate. Static pages and
consumer identity routes can still progress. The captured owner commit flag
survives another tab's dispatch. Only matching delivery can release/cancel the
pending effect, and success requires every header/body byte to be queued and
TCP-acknowledged. FIN/RST alone never supplies that proof. Unrelated partial
connections no longer postpone a delivered trial or restart. Network changes
or reboot can still close other requests; clients retain the existing uncertain
write/readback contract.

## Validation

Validation uses the retained `wsprrypico-p153-env:local` Linux arm64 image
`c7f2a891a6ff`, GCC 14.2, CMake 3.31.6, Python 3.13 and existing pinned SDK
libraries. Networking is disabled, source is read-only, and no device mounts
are present. A disposable `pi` account supports existing fixture ownership
assertions, `PHASE115_ENDPOINT_DRIVER` points to the Linux executable, and a
scratch mount replaces `config/local` only inside the container.

From the container, with source `/work/pico` and scratch `/out`:

```sh
cmake -S /work/pico -B /out/build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/work/pico/build/local-sdk-079c6f3/lib/mbedtls \
  -DWSPRRY_PICO_TEST_LWIP_PATH=/work/pico/build/local-sdk-079c6f3/lib/lwip
cmake --build /out/build-host --parallel 3
export PHASE115_ENDPOINT_DRIVER=/out/build-host/endpoint_driver
ctest --test-dir /out/build-host --output-on-failure
python3 /work/pico/scripts/validate_wtp_contract.py
```

Final production source and regression tests are committed as
`9cf5ba2fe92de9abb893d0c6a44fa0a0a96c3794`. The subsequent acceptance/index/roadmap
commit changes documentation only.

Mbed TLS remains `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`; lwIP remains
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`. The actual transport tests use
lwIP boundary doubles and the production HTTP parser. They exercise overlapping
partial headers/uploads, large stalled replies, partial/full ACKs, FIN and RST,
write/close failures, ERR_MEM retry, timeout despite trickling input, capacity,
interface withdrawal/drain, parser/pipeline rejection, header/body admission,
reserved-body continuation and 32 reclamation cycles (64 unique completions).
The adapter tests compile actual dispatch/receipt function bodies and deferred
trial/restart predicates, checking
setup isolation, stale/wrong tokens, exactly-once cancellation and owner-status
evidence retained across another dispatch, and delivered actions independent of
unrelated sockets. These are software boundary tests,
not real phone/Mac or lwIP timing qualification.

Affected ASan/UBSan uses a separate Debug directory with
`-fsanitize=address,undefined -fno-omit-frame-pointer`, the matching executable
linker flag, `ASAN_OPTIONS=detect_leaks=1` and `UBSAN_OPTIONS=halt_on_error=1`.
Targets: `http_server_tests`, `consumer_radio_tests`, `bootstrap_slot_tests`,
`bootstrap_join_tests`, `owner_claim_http_tests`, `config_update_tests`.
CTest names match except `config_updates`.

Both RP2350 images are cross-linked with existing SDK
`079c6f39023649b154152db30f1d781e884879bc` and Arm GNU 15.3.1:

```sh
cmake --build build/consumer-lan-pico \
  --target WsprryPico WsprryPico-StandaloneRF --parallel 3
```

The retained local build selects consumer Plain LAN and the 138 MHz RAM RF
renderer. Its cached version label is historical; these are compile/link checks,
not deployed or released firmware identities. Linked topology/heap/Bluetooth
checks and the standalone RF RAM placement check run as part of the build.

Initial failed attempts are retained under `/private/tmp/wsprrypico-p155`:
`ctest-first.log` (seven environment failures: missing fixture account and a
macOS endpoint executable), `ctest-final.log` (one remaining read-only
`config/local` fixture failure), and a final run with a scratch-only fixture write mount. The initial sanitizer
attempt also selected nonexistent `owner_claim_tests`; it was corrected to
`owner_claim_http_tests`, and the reused sanitizer log now contains the final
attempt. That command failure is recorded here. Source was not changed to
suppress fixture failures.

## Adversarial assessment and repairs

The executing conversation performed the source assessments; no independent
reviewer or physical review is claimed.

1. Review of singleton assumptions repaired shared delivery scratch, FIN-as-ACK,
   global connection gates on trial/restart and receipt overwrite exposure.
   Regression tests exercise actual receipt/dispatch branches.
2. The first adversarial pass identified a graceful-close fallback returning the
   wrong lwIP callback code, and admission classifying a null/error accept.
   Teardown now reports actual abort, invalid accepts are rejected before
   classification, and tests cover both paths and exactly-once delivery.
3. The resource pass identified header-map/string growth preceding the existing
   body admission gate. Added per-fragment header workspace admission without
   denying already-reserved body continuation. Added separate header-pressure,
   body-pressure and continuation cases, plus the fixed task-size assertion.
4. Reassessment inspected callback ownership, transaction reuse, partial ACKs,
   error-after-free, pipelined prefixes, interface withdrawal, receipt capture,
   configuration serialization and the P15.6 boundary. No actionable software
   findings remained after repairs and the final affected checks passed.

## Acceptance boundaries and documentation impact

P15.1-P15.4 normative schemas, carrier matrix, journal/revision behavior and
historical acceptance remain intact. Pi and the operator-documentation
repository were left unchanged. No Pi compatibility pin is silently advanced;
Pi's recorded P15.4 source pair remains its accepted pair. Existing Pico
consumer, configuration/resource, actual crypto, engineering TLS/WTP and
browser tests are rerun; no Pi CI or end-to-end Pi/new-Pico source pair is
claimed by this slice.

P15.6 must add independent sessions, expiry/logout, replay/sequence state and
bounded pending exchanges without sharing these transport task slots as session
identity. P15.7 still needs the precise failed-save/login-loss reproduction and
recovery behavior. P15.14 must document concurrency capacity, overload/retry,
setup-response serialization, uncertain writes, and the distinction between
concurrent requests and simultaneous logins; update phone/Mac screenshots when
P15.6/P15.7 workflows settle. No UI changed in P15.5.

Physical phone/Mac concurrency, target heap/stack/fragmentation, installed-service
behavior, conducted RF under contention and unrestricted security remain
unqualified. Historical Phase 11.5/Phase 14 measurements do not qualify this
changed firmware/allocator layout. No bench, flashing, USB control, GPIO or RF
operation occurred. No PR or release is created by this task.

## Software closure

| Check | Final result | Local evidence |
| --- | --- | --- |
| Full Pico host suite | 189/189 CTest groups passed, 110.91 seconds | `/private/tmp/wsprrypico-p155/ctest-reviewed.log` |
| Final actual-source adapter checks | 3/3 tests passed, including deferred-action predicates | `/private/tmp/wsprrypico-p155/adapters-reviewed.log` |
| WTP/1 validator | 23 schema, 7 raw JSON, 1 framing and 8 transition cases passed | `/private/tmp/wsprrypico-p155/contract-reviewed.log` |
| Affected ASan/UBSan | 6/6 groups passed, leak detection enabled | `/private/tmp/wsprrypico-p155/sanitize-tests.log` |
| RP2350 cross-link | Both firmware targets and their linked checks passed | `/private/tmp/wsprrypico-p155/cross-link-reviewed.log` |
| Formatting/patch hygiene | clang-format dry run and `git diff --check` passed | Checked before publication |
| Final adversarial assessment | No remaining actionable software findings | Assessment and repairs above |

CTest counts are groups, not a claim that every conditional live-evidence test
ran. Local scratch logs are evidence locations on the executing workstation,
not repository dependencies. Final scope is software implementation, host
regressions and target compile/link acceptance. P15.6/P15.7 and physical
qualification remain open. This repository has no configured CI workflow;
no new CI result is claimed. Publication is to `origin/devel`; the final report
records the independently verified pushed head.

Concurrent unrelated Pi Si5351 work appeared during validation in addition to
the Release Punchlist edit. This task did not edit, stage or commit those paths.
