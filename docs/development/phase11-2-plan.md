# Phase 11.2 execution plan and initial review

Date: 2026-09-08. Baseline: clean `devel`, refreshed `origin/devel`, both
`0fd8191c5218d3b5f2da9122a2ae55bf728ae3f2`. Implementation has not begun.
Sibling WsprryPi is read-only at `f210e4d165e0e30f94ee9332e70af45e0367e4cb`.
Its acceptance record still requires a subsequent network CI pass; no remote
pass is inferred here. No hardware operation is authorized.

## Source review findings

1. `network/pico/server.cpp`: one active TLS/Endpoint/parser and one pending
   socket; `busy()` rejects physical Armed/Running. Handshake steps call PSA
   crypto synchronously (`ssl_tls13_server.c` in pinned Mbed TLS). Polls around
   those calls cannot bound their internal latency. Cooperative TLS alone is
   therefore insufficient; this plan does not introduce a TLS dependency change.
2. `standalone/pico/main.cpp`: scheduler, network, TLS, USB and request dispatch
   share a foreground loop. Endpoint stages and JSON parsing can also exceed a
   refill interval. Isolating only handshakes would leave this failure path.
3. `rf/pico/pico_pio_dma.cpp`, sink and stream: hardware resources, callbacks,
   launch guard and same-core IRQ mask must stay on their owning core. Refills
   allocate no memory. Prepare copies a job and builds tables while idle.
4. Deferred Wi-Fi completion is global in BrowserApi/PicoNetwork. Every TLS
   close invokes it. Multiple connections require an initiating transaction
   token and an authoritative idle recheck, including cancellation on shutdown.
5. TLS UTC callback reads JobService; leave both on core 0. The RF launch guard
   instead requires an independently owned coherent copy of UTC discipline.
6. Raw TCP error callback means PCB already freed. The sibling MIT host adapter
   repaired ECONNRESET by freeing the PCB before callback; adapt this behavior
   with provenance and exercise resets. Detach callbacks before local abort.
7. Dynamic worst cases matter: two maximum WTP parsers, two TLS sessions and
   RF buffers would exhaust headroom. Restrict the network to one WTP stream,
   two TLS slots and one pending TCP slot. HTTP body remains separately bounded.
   Bound JSON key validation scratch and retain the full WTP payload limit.
8. Browser uses an engine-prefix capability and intentionally pauses after ARM.
   Replace the prefix with explicit execution policy; preserve unsupported-build
   fallback, unknown reads, draft/revision safety and session-owned abort.

## Selected architecture and ownership

| Object or subsystem | Exclusive owner | Boundary |
| --- | --- | --- |
| JobService, scheduler, USB Endpoint/Console | Core 0 | Serialized calls; no application mutation queue |
| lwIP/CYW43 polling, SNTP, TLS/PSA/RNG, HTTP, browser API | Core 0 | Existing supported NO_SYS polling context |
| Store/journals and flash writes | Core 0 | Idle check plus SDK multicore flash lockout |
| Physical StreamEngine, PioDmaSink, PicoPioDma, launch IRQs | Core 1 | Dedicated refill loop, no crypto/JSON/network work |
| RF engine proxy | Core 0 | One synchronous bounded mailbox; caller retains request until acknowledgement |
| UTC discipline | Core 0 authoritative, core 1 independent copy | Copy at mailbox boundary; core 1 IRQ-safe assignment, local aging uses monotonic clock |
| Credentials and static assets | Immutable flash | No runtime provisioning or mDNS change |

Core 1 services RF before processing one command. The mailbox has exactly one
outstanding command, release/acquire ownership and no cancellation that could
release a live payload. Prepare/disable may allocate/free only while core 0 is
waiting and cannot access the allocator. During autonomous execution core 1
performs no allocation. All returned reports and diagnostics are copied before
acknowledgement. No RF-critical mutex covers crypto, serialization or I/O.
Timeout must fail closed without freeing in-use request storage; firmware uses
watchdog recovery rather than returning from an unacknowledged borrowed call.
The default inhibited image need not launch core 1. The physical standalone
image uses the proxy with network enabled or disabled so its policy is explicit.

A 16,384-word buffer provides `16384*32/138000000 = 3.799188 ms` at 138 MHz.
The prior 1.530 ms refill observation leaves approximately 2.269 ms for detection,
interrupts and contention; it is not evidence for this image. Instrument core 1
service gaps/refill calls and mailbox pressure, TLS durations and memory/stack
usage. XIP, shared SRAM bus and DMA contention still require 11.5/11.6 measurement.
Launch guard and finite hardware tail remain local; failed shutdown still latches.
Core startup precedes JobService construction; watchdog recovery starts unowned
and network-free. Flash lockout occurs only before ARM/after authoritative stop.
Do not reset core 1 while buffers or commands are owned by it.

## Connection state machine and budgets

Two fixed active contexts: free -> handshake -> authenticated WTP or HTTP ->
closing -> free. At most one handshake computes at once; one pending PCB gets
backpressure and an absolute admission deadline. One WTP stream is admitted after
ALPN, leaving browser capacity; two HTTPS requests may compete when no WTP stream
is active. The owner is never evicted to admit an extra client. Poll order rotates;
each slot gets one bounded I/O/parser quantum per turn. TLS steps are not claimed
to be bounded in CPU time, but execute off the RF core. Absolute handshake 10 s,
HTTP 15 s, progress 30 s and WTP partial/write stall 5 s remain bounded.

Each slot owns TLS, principal, parser, endpoint/output, ciphertext/plaintext,
deadlines, response and non-reused transaction generation. Pending and active
callbacks are detached before PCB teardown; no queued raw-pointer tasks survive
slot reuse. Link loss closes all sockets without resetting JobService. A network
mutation is completed/cancelled only by its token; unrelated closes cannot apply
it. Idle check and mutation execute synchronously on core 0 with no interleaved
claim or ARM. A pending mutation is rechecked at completion.

Preliminary physical RAM budget to validate before acceptance: existing image
BSS 279,692 bytes; primary stack 16 KiB; new core stack 16 KiB; second connection
fixed storage about 6 KiB; TLS records/crypto, maximum frame, HTTP body, decoded
job/replay/response scratch and allocation overhead require explicit accounting
against remaining SRAM. Keep max WTP 65,536 and HTTP 32,768. Limit record output,
JSON scratch and retained response storage where necessary, without changing
normative WTP. A link alone cannot close the maximum runtime memory gate.

## Implementation and acceptance sequence

1. Save this review/plan and the complete request below before implementation.
2. Implement bounded connection isolation, token-owned deferred mutations and
   explicit policy; actual TLS tests cover concurrency, ownership and teardown.
3. Implement portable mailbox and RF proxy, target core startup/flash/watchdog
   wiring. Host tests inject delayed owner progress, stale generations, full
   queue and failures; target cross-link validates SDK integration only.
4. Update compact browser lifecycle using Impeccable; inspect desktop/mobile,
   lost reads, active ownership, saturation and draft preservation.
5. Add Pico-owned actual 11.1-client interop with explicit unmodified source pin;
   leave sibling checkout and its reference gate unchanged.
6. Run normal host/TLS/contract, separate C/C++ ASan/UBSan, concurrency tests,
   both images with network off/on and ELF/UF2 layout checks. Record failures,
   repairs, skips and exact resource evidence in `phase11-2-review.md`.
7. Adversarially review source and tests, repair findings, rerun affected checks,
   reassess. Update API/network/architecture/development/roadmap documentation.
8. Stage only scoped files, commit, push `origin/devel`, fetch and verify parity.
   Report software status separately from target timing and RF acceptance.

## Execution amendments

The initial review above is retained as written before implementation. The
[acceptance record](phase11-2-review.md) records the implemented result, repairs,
measured linker budget and remaining target gates. The user supplied companion
CI revision `d333c69edc8a65bf59ae52603110996921f82ce1`; actual client interoperability
uses an isolated clean copy at that pin after the sibling advanced independently.
Runtime admission preserves scratch rather than promising simultaneous maximum
allocations. Unused diagnostic table sections are discarded from physical images.
Deferred mutations now require an acknowledged response; premature termination
cancels them. Actual TLS tests use an explicitly simulated local timer, while
portable driver timing checks and future physical deadline measurements remain
separate evidence.

## Full execution request

The following is the original self-contained implementation and acceptance
brief. Its scope and acceptance requirements govern the work above.

```text
Implement Phase 11.2 — Concurrent browser management in WsprryPico.

Work in /Users/lbussy/GitHub/WsprryPico on devel. Begin with a code review,
render and save a comprehensive execution prompt/plan, then implement it.
Perform adversarial review, repair actionable findings, rerun affected checks,
and repeat the assessment until those findings are closed. Commit and push
the completed WsprryPico work to origin/devel, verify parity, then report.

This task authorizes the necessary Pico application, network, RF-servicing,
build, test, browser and documentation changes within this repository.
Preserve user changes and existing architecture boundaries. Other repositories
are read-only. No live hardware operation is authorized.

1. Objective and roadmap context

Phase 11.1 is implemented in WsprryPi. Its implementation commit is
690a0692cd6cd62c99b89a0f1983d73c01624b47. It provides TLS 1.3/mTLS transport,
USB/network configuration, credential rotation checks, shared browser API,
network-management UI, and actual Pico-server interoperability.

At handoff preparation:
- WsprryPico was clean on devel at
  0fd8191c5218d3b5f2da9122a2ae55bf728ae3f2.
- WsprryPi was clean on devel at f210e4d, following 690a069 with CI checkout
  changes. Reinspect its current acceptance record; do not infer remote CI
  success from local tests or workflow changes.

Phase 11.2 must remove the Pico server’s practical restriction that a persistent
WTP controller monopolizes network access and physical armed/running jobs reject
all new TLS handshakes.

Required operator behavior:

- An established authenticated WTP controller can retain its connection and
  ownership while an independently authenticated browser connects and reads
  current Pico status.
- Browser access works during a future arming interval and during local job
  execution under the supported, bounded connection policy.
- A browser controlling its own job can refresh status and request its
  owner-authorized abort.
- A browser observing a WsprryPi-owned job cannot steal ownership or abort it
  through a different principal/session.
- Network traffic cannot make RF timing depend on packet arrival or silently
  starve waveform servicing.
- Slow, failing or extra clients are bounded and cannot corrupt another
  connection’s state.

A second connection slot alone is insufficient if TLS computation still blocks
the RF servicing path.

Remaining roadmap:
11.3 — DHCP/mDNS, hostname certificates and joint name-resolution acceptance.
11.4 — Inhibited physical-device acceptance.
11.5 — Target resource/contention measurements.
11.6 — Conducted RF acceptance.
11.7 — Final joint review and Phase 11 closure.

Implement and instrument 11.2 now. Keep physical deadline/RF qualification
explicitly pending where it requires those later authorized acceptance steps.
Do not describe host tests or cross-linking as measured RP2350 timing evidence.

2. Review before implementation

Read AGENTS.md, README.md, CONTRACT.md, docs/architecture.md,
docs/development/README.md and applicable nested instructions.

Inspect branch, tracked/untracked changes and staged/unstaged diffs. Refresh
origin/devel and advance safely. Do not reset, stash, overwrite or discard work.

Review these Pico files and their dependencies:

- src/network/pico/server.{hpp,cpp}
- src/network/pico/mbedtls_config.h
- src/network/api.{hpp,cpp}
- src/network/http.{hpp,cpp}
- src/network/web/index.html
- src/network/web/app.js
- src/network/web/style.css
- src/standalone/pico/main.cpp
- src/standalone/pico/adapters.{hpp,cpp}
- src/standalone/pico/lwipopts.h
- src/standalone/scheduler.{hpp,cpp}
- src/standalone/storage.{hpp,cpp}
- src/standalone/wtp_profile.hpp
- src/wtp/job_service.{hpp,cpp}
- src/wtp/endpoint.{hpp,cpp}
- src/wtp/frame_parser.{hpp,cpp}
- src/rf/stream_engine.{hpp,cpp}
- src/rf/pio_dma_sink.{hpp,cpp}
- src/rf/pico/pico_pio_dma.{hpp,cpp}
- firmware/CMakeLists.txt
- cmake/network.cmake
- cmake/network_host_tests.cmake
- cmake/verify_pico_dependencies.cmake
- tests/network_tests.cpp
- tests/network_tls_tests.py
- tests/network_tls_driver.cpp
- tests/network_support.hpp
- tests/network_mock/
- tests/network_browser_tests.js
- relevant RF, endpoint, standalone and core tests

Read:
- docs/protocol/WTP.md
- docs/browser-api.md
- docs/development/network-control.md
- docs/development/phase11-review.md
- docs/development/pio-dma-driver.md
- docs/development/rf-stream.md
- relevant current RF/UTC acceptance records
- docs/implementation-plan.md

In sibling /Users/lbussy/GitHub/WsprryPi, inspect read-only:
- docs/development/phase11-1-review.md
- docs/wtp-network.md
- docs/wtp-browser-api.md
- src/wtp_integration/tls.{hpp,cpp}
- src/wtp_integration/network_http.{hpp,cpp}
- src/wtp_integration/application.cpp
- src/wtp_runtime_bridge.cpp
- src/tests/network/CMakeLists.txt
- src/tests/network/pico_tls_server.cpp
- src/tests/network/tcp.cpp
- src/tests/wtp_network_interop_test.{cpp,py}

Record source-backed findings and the intended architecture before editing.
Continue with routine implementation choices within this scope; do not stop
after producing only a plan.

3. Current constraints requiring an architectural solution

The current PicoServer owns one TLS context, one WTP Endpoint, one HTTP parser,
one active TCP connection and one pending connection. Its busy() policy rejects
new handshakes for physical Armed/Running states.

The firmware services RF and network work on the foreground path. Calls around
mbedtls_ssl_handshake_step do not establish that the cryptographic work inside
one step fits an RF deadline.

The PIO/DMA implementation currently requires its engine/sink/peripheral objects
to remain on one owning core. Its same-core interrupt mask is not multicore
synchronization. Existing documented successor-buffer time is only a few
milliseconds; derive the actual budget from current buffer size, sample clock,
refill cost and launch/interrupt requirements.

The current BrowserApi/NetworkControl deferred Wi-Fi change is global:
finish_request() can apply or cancel pending state. Under multiple connections,
an unrelated connection’s shutdown must not complete another request’s mutation.

The TLS certificate-time callback currently reads the shared JobService clock.
Any multicore design must provide coherent time/UTC observations and preserve
certificate validation without unsafe shared-state access.

The WsprryPi application intentionally keeps remote configuration/schedule/network
management idle-only. Preserve that policy. This task enables concurrent Pico
connections and observations; it does not authorize remote configuration changes
during jobs or changes to WsprryPi’s ownership model.

4. Select and document a bounded execution architecture

Before implementing, produce:

- An ownership map for JobService, scheduler, RF engine, USB, lwIP/CYW43,
  TLS contexts, HTTP processing, UTC snapshots and persistent storage.
- A connection/state-machine design with explicit limits.
- A scheduling design showing how RF servicing remains available while
  cryptography, parsing or another client is busy.
- A RAM/stack/queue budget for the physical image.
- A shutdown/failure design.

Evaluate cooperative/restartable TLS work, appropriate isolation of networking
or cryptographic work, and any narrowly necessary RF-servicing changes against
the actual SDK/library implementation. Do not assume a TLS “step,” a byte limit,
a thread or a second core automatically supplies a usable latency bound.

If using RP2350’s second core:
- Keep lwIP/CYW43 calls on their supported execution context.
- Retain one owner for JobService and RF state.
- Communicate using bounded messages, immutable snapshots and explicit lifetime
  rules; do not share mutable JSON/string/span objects unsafely.
- Handle 64-bit time snapshots coherently.
- Account for allocator, RNG/crypto, shared peripheral, interrupt and XIP/flash
  contention.
- Define queue-full behavior, stale-message rejection, core startup/shutdown,
  watchdog recovery and flash-operation coordination.
- Never hold an RF-critical lock while doing crypto, allocating, waiting on
  network I/O or serializing a large response.

Keep original contributions under the project license and preserve upstream
notices. Retain pinned SDK/toolchain/TLS inputs unless a justified dependency
change is necessary and separately documented. Do not download dependencies
as an incidental formatting or exploration step.

5. Connection isolation, fairness and bounds

Support at least the required persistent WTP-controller plus independent HTTPS
browser case. Choose exact active/pending/handshake limits from the memory and
servicing budget; advertise them accurately.

Each connection needs isolated:
- TLS session and authenticated principal.
- WTP framing/session/output state when ALPN selects wtp/1.
- HTTP parser, request/response buffers and progress.
- Receive/send accounting and deadlines.
- Closure/error state and connection generation identity.

Shared immutable credentials/configuration are acceptable where the TLS library
supports them. Mutable shared RNG/crypto state needs an explicit safe design.

ALPN selects wtp/1 or http/1.1 after the appropriate TLS negotiation.
Unauthenticated client input must not obtain privileged scheduling or ownership.

Define:
- Fair progress among admitted clients.
- Bounded unauthenticated handshake admission.
- Absolute handshake/request deadlines and stall limits.
- Backpressure and connection-capacity exhaustion behavior.
- Protection of an established owner from unrelated client failure.
- Safe callback/context lifetime across close, abort, errors and slot reuse.
- Handling of delayed acknowledgments and stale queued work.
- Link-loss cleanup across every active/pending connection.

Preserve WTP’s 65,536-byte frame payload limit and the separately advertised
HTTP bound. Account for simultaneous maximum requests, parser/container overhead,
response construction, endpoint queues, TLS allocations and TCP pools.

Do not multiply the existing per-connection worst case without checking total
physical-image headroom. A successful link is not a maximum-runtime-memory test.

6. Preserve application authority and security

Keep one authoritative JobService across USB, WTP/TCP, browser and standalone
execution. Complete jobs remain local after ARM.

Preserve:
- TLS 1.3, mandatory client authentication and certificate principals.
- Mandatory ALPN, existing certificate verification and usable-UTC requirements.
- No plaintext/downgrade, verification bypass, early-data mutation or implicit
  session resumption.
- Strict HTTP framing, Host/Origin/intent checks, CSP and password redaction.
- WTP device/session/request identity, replay and ownership semantics.
- USB canonical transport and physical Console ABORT recovery.
- Failure latching when output shutdown cannot be established.
- Persistent schedules, watermark and reboot/recovery behavior.

Read-only status must remain possible during admitted jobs. Configuration,
schedule persistence, Wi-Fi disable and other disruptive management mutations
remain idle-only.

Make mutation execution atomic with the state/ownership check on the authority
owner. A request that was idle when received must not execute after another
client has acquired ownership or armed a job.

Bind deferred network changes to the initiating request/connection or a clearly
defined transaction token. An unrelated response, disconnect or slot reuse must
not trigger them. Recheck idle state at application time and preserve truthful
requested-versus-actual status.

Cross-connection cancellation must cancel only that connection’s unfinished work.
Disconnecting one browser must not reset the WTP owner, clear another response,
erase replay history or imply RF shutdown.

7. Browser/API behavior and compatibility

Update capabilities and documentation to reflect the implemented connection
model. Preserve existing API schemas where possible and document additive
fields. Do not silently alter normative WTP.

The current active_job_connections capability is derived from an engine-name
prefix. Replace that assumption with an explicit, truthful capability/policy
derived from the implemented servicing architecture.

Update the embedded browser so successful ARM does not intentionally disable
all subsequent management when concurrent access is supported. Keep a truthful
unavailable/degraded state for saturation, connection loss or unsupported builds.

Preserve:
- Timestamped observations and unknown state after failed reads.
- Unsaved config/password drafts and revision-conflict behavior.
- Owner-aware abort/release controls.
- No automatic repeated LOAD/ARM after an ambiguous result.
- No new ability to abort a WsprryPi-owned job from an unrelated direct browser.

Use the Impeccable skill for UI changes, preserving the existing compact operator
interface. Inspect applicable desktop/mobile layouts and lifecycle/error states.
Do not broaden this into a visual redesign.

The user’s accepted future network requirement is DHCP plus mDNS with a stable
.local name, optional explicit IP connections and no IP reservations.
Do not implement mDNS or certificate provisioning in 11.2, but avoid introducing
IP-only architectural assumptions that obstruct 11.3.

8. Deterministic and actual-TLS acceptance tests

Add behavior tests using the actual server and TLS implementation, covering:

- Persistent authenticated WTP connection plus repeated HTTPS status requests.
- Browser connection establishment while a job is Armed and Running.
- A simulated engine/profile exercising the physical-policy branch; an
  inhibited-only test must not bypass the very restriction being removed.
- Local execution continuing through browser traffic and controller disconnect.
- Owner-authorized ABORT while another connection is slow or incomplete.
- Foreign-principal/session CLAIM/ABORT/RELEASE attempts rejected correctly.
- Same certificate with different sessions, and different client certificates.
- Concurrent config revisions: exactly the intended mutation wins.
- Management admitted while idle but racing a subsequent claim/ARM.
- Deferred Wi-Fi disable: correct response/request ownership and idle recheck.
- Fragmented and maximum requests on competing connections.
- Saturation, slow handshakes, stalled writes and bounded resource exhaustion.
- One connection failing while others continue correctly.
- TCP EOF/reset, delayed callbacks, reconnect and context-slot reuse.
- Link loss, clock-state changes, shutdown and startup failure.
- Repeated connection cycles without retained-resource growth.
- USB and network arbitration through the same service.
- Browser draft/status/control regressions.

For scheduling architecture, test bounded queues, starvation prevention,
cancellation, stale generations and failure paths with injected delays.
Do not relabel a desktop elapsed-time measurement as an RP2350 deadline result.

Add appropriate sanitizer coverage. If introducing concurrency, exercise its
synchronization with suitable host testing where supported and report limits.

Use valid WTP identities in strict-client interoperability. The original Pico
network_tls_driver’s “test-device” placeholder is not a valid 32-hex device ID.
WsprryPi’s 11.1 harness demonstrates a valid-identity arrangement.

WsprryPi’s checked-in network harness pins Pico to clean revision 0fd8191.
It will intentionally reject a modified/new Pico checkout. Do not bypass that
gate or edit the sibling repository. Add a Pico-owned interoperability target
using reviewed, unmodified WsprryPi client sources and an explicit source pin,
or record the precise companion pin-update follow-up. Ensure meaningful
11.1-client interoperability is tested against this implementation.

Inspect WsprryPi’s repaired host TCP glue for its ECONNRESET cleanup lesson.
Review any necessary adaptation and license provenance rather than copying
unexamined test code.

9. Build, resource evidence and reproducibility

Use the documented current build commands. Baseline host workflow:

cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/path/to/pico-sdk/lib/mbedtls
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
python3 scripts/validate_wtp_contract.py

Use a separate ASan/UBSan build directory and instrument applicable C and C++
sources. Add documented targets/options for new acceptance tooling.

Cross-build both WsprryPico and WsprryPico-StandaloneRF:
- Network disabled.
- Network enabled with ephemeral local test credentials.

Run the current endpoint/standalone ELF and UF2 layout checks. Update checks
if a legitimate architecture change introduces new stack/queue reservations.

Report:
- Flash, static RAM and stack reservations.
- Per-connection and total dynamic-memory budget.
- Maximum bounded queue/buffer capacities.
- The RF refill deadline calculation and assumptions.
- Instrumentation for actual service gaps, queue pressure, handshake duration,
  heap/stack high-water marks and watchdog/failure counters.

Keep network control disabled by default and the standard image RF-inhibited.
No credential-bearing build artifact belongs in source control or public releases.

10. Hardware and repository boundaries

No flashing, USB device control, debugger access, GPIO changes, RF operation,
production deployment, service manipulation or system trust changes are
authorized by this prompt.

Prepare opt-in target procedures and instrumentation for later acceptance.
Do not execute them. Earlier RF evidence does not qualify this changed network
architecture, even if the mode, clock or board appears unchanged.

WsprryPi and Wsprry_Pi_Docs remain read-only. List any required follow-up with
exact files, API compatibility implications and revised reference pins.
Do not send messages or create work in those repositories automatically.

11. Adversarial review, documentation and completion

Save the execution plan and an 11.2 review/acceptance record in
docs/development/. Update the API/network guides, architecture, development
baseline and roadmap where affected.

Review the final implementation adversarially for:
- RF starvation hidden inside crypto or parsing.
- Unbounded memory, queues, connections or cancellation.
- Cross-core data races and unsafe shared peripheral/library state.
- Callback use-after-free and stale-slot reuse.
- Cross-client identity, ownership or response leakage.
- Deferred mutation races.
- Duplicate execution after ambiguous results.
- Clock, flash and watchdog interactions.
- Misleading capabilities or UI status.

Repair actionable findings, rerun affected checks, and repeat the assessment.
Retain failed attempts and distinguish them from passing acceptance runs.

After successful software review and checks, commit only the scoped WsprryPico
changes, push origin/devel and verify parity.

Report:
- What concurrent behavior now works.
- The selected execution/ownership architecture and its resource bounds.
- Exact tests, builds, sanitizer and browser checks with pass/fail/skip results.
- Review findings and closure evidence.
- Documentation changes and companion-repository follow-up.
- Commit, push result and actual working-tree state.
- Remaining target measurements and physical acceptance.

Use an evidence-bound status such as “11.2 software implemented; target timing
acceptance pending” when hardware verification has not occurred. Do not mark
all of Phase 11 complete or claim measured RF servicing guarantees from host
simulation and cross-linking alone.
```
