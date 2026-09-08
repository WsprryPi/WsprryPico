# Phase 11.2 concurrency review and software acceptance

Date: 2026-09-08. **11.2 software implemented; target timing acceptance pending.**
This record covers the changes accompanying it on `devel`, starting from clean
`0fd8191c5218d3b5f2da9122a2ae55bf728ae3f2`. The
[execution plan and complete request](phase11-2-plan.md) were saved and opened
before implementation. No board, USB device, debugger, GPIO, RF path, service,
system trust store or production deployment was accessed.

## Result and authority

An authenticated persistent WTP controller and an independently authenticated
HTTPS browser can coexist through simulated Armed and Running states. A browser
can observe the controller's job; it cannot adopt or abort it using another
certificate or session. A browser owning its own job retains status and ABORT
access. Disconnect and link loss leave the complete finite job with the shared
JobService and local execution engine. Configuration, schedules and disruptive
network management remain idle-only.

| Subsystem | Owner and synchronization |
| --- | --- |
| JobService, scheduler, USB Endpoint/Console, browser operations | Core 0, serialized authoritative calls |
| lwIP/CYW43, SNTP, TLS/PSA/RNG, HTTP, certificate-time callback | Core 0 in the supported foreground polling context |
| Physical StreamEngine, PioDmaSink, PicoPioDma, launch/DMA IRQs | Core 1, continuous local servicing |
| RF command/reply | One synchronous release/acquire mailbox; no application mutation queue |
| UTC | Core 0 discipline; copied to separate core 1 discipline under a same-core IRQ mask |
| Flash/journals | Core 0, existing idle admission plus SDK multicore flash lockout |

`WorkerEngine` polls the local engine before checking one mailbox command. The
producer retains immutable borrowed job storage until acknowledgement; no
timeout returns while the consumer can still use it. Reentry/queue overwrite
and a 100 ms missing acknowledgement invoke the nonreturning failure hook.
The physical hook records `RFC1` in watchdog scratch and stops feeding the
existing eight-second watchdog. No hot core reset or abandoned pointer queue is
introduced. Startup publishes the worker only after flash-lockout initialization;
the custom stack and engine live for the application lifetime. Recovery boot
retains the existing unowned, scheduler-stopped, network-free policy.

Core 1 allocates only during prepare/disable while core 0 synchronously waits.
Autonomous execution, refills and IRQ paths allocate nothing. Allocator calls,
RNG, PSA and lwIP therefore do not race between cores. UTC contains 64-bit values,
but the mailbox ownership transfer and worker-local IRQ mask provide a coherent
copy; TLS never reads the worker copy. No RF lock encloses TLS, JSON or I/O.
The portable worker and actual target driver remain separate from JobService.
The standard firmware retains its inhibited engine; both standalone variants
explicitly advertise their active-job connection policy.

Synchronous TLS handshake steps cannot supply a sub-millisecond execution bound.
The pinned source performs crypto inside those calls, so adding cooperative
polls alone was rejected. Isolation removes crypto/parsing from the refill loop;
it does **not** establish a bound on shared SRAM/XIP/bus/IRQ contention.

## Connection lifecycle and security

Two fixed contexts independently own SSL, certificate principal, Endpoint,
HTTP parser, input/output, deadlines and monotonically increasing transaction
generation. Lifecycle is free -> handshake -> authenticated WTP or HTTP -> close
-> free. At most one handshake computes at once, one authenticated WTP stream
is allowed, and one additional TCP connection can wait. Two HTTPS requests may
coexist without WTP. Excess clients and a second WTP stream cannot evict an
established owner. Poll order rotates; each context gets one I/O/parser quantum.
This is fair opportunity on core 0, not a bound on individual crypto calls.

| Limit | Implemented bound |
| --- | --- |
| Active TLS / authenticated WTP / computing handshake / pending TCP | 2 / 1 / 1 / 1 |
| Pending TCP and handshake age | 10 s each; promotion starts the handshake age |
| Total HTTP age | 15 s from activation, including handshake |
| Authenticated progress / WTP partial frame or blocked output | 30 s / 5 s |
| Per-slot ciphertext staging / plaintext staging | 4,096 / 1,024 bytes |
| WTP payload / HTTP body / HTTP headers | 65,536 / 32,768 / 2,048 bytes |
| Endpoint input dispatch / TLS application output per poll | 64 / 1,024 bytes |
| Endpoint output queue | 8 frames, at most 131,072 bytes, also heap-admitted |
| Service sessions / replay entries per session / terminal records | 16 / 8 / 8; existing TTLs preserved |
| RF mailbox | 1 outstanding command; no asynchronous cancellation queue |
| lwIP heap / packet pool / active PCB pool / TCP segments | 32,768 bytes / 8 / 4 / 32 |
| TCP receive/send window per PCB | 2,920 / 5,840 bytes |

Callbacks are detached before local close/abort; lwIP error callbacks mean the
PCB has already been freed. There is no queued application callback retaining a
slot pointer. Delayed ACK accounting belongs to the PCB and its context. A
64-bit generation is never reused; at exhaustion promotion stops. Link loss
closes every pending/active context without changing job authority. Stop frees
all SSL/config/PSA state and cancels pending mutations; startup failure and
stop/restart are covered by the actual TLS driver.

Deferred Wi-Fi changes carry the initiating generation. Unrelated responses,
closes and obsolete tokens cannot finish them. Transport failure or teardown
cancels the initiating change. Only an acknowledged complete response can apply
it, with another synchronous idle check. A claim arriving before ACK cancels the
change. API status and the UI distinguish a requested change from observed link
state; ambiguous delivery never causes an automatic repeated mutation.

TLS remains 1.3 only, requires verified client certificates and explicit ALPN,
and refuses authentication without usable UTC. Certificate fingerprints remain
principals. No plaintext, TLS downgrade, verification bypass, early data,
resumption or ticket mutation path was added. Strict HTTP framing, Host/Origin,
intent checks, CSP hashes, redaction and revision checks remain in force. WTP
device/session/request/replay/error precedence and normative limits are unchanged.
USB and browser operations use the same service; physical Console ABORT remains
the recovery boundary. Failed output disable remains latched.

## RAM, flash and timing evidence

These are linker measurements from the reviewed source with ephemeral local
certificates, not maximum-runtime measurements. `text` is the GNU size column;
flash span is `__flash_binary_end - 0x10000000`. Static SRAM span includes BSS,
initialized/relocated data and alignment below `__end__`; it is more useful than
BSS alone for heap accounting. All byte counts are decimal.

| Image | Network port | text | Flash span | BSS | Static SRAM span | Heap address space |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| WsprryPico | 0 | 924552 | 906124 | 81868 | 94092 | 413812 |
| WsprryPico-StandaloneRF | 0 | 946556 | 928124 | 267836 | 280388 | 227516 |
| WsprryPico | 18443 | 948232 | 929804 | 81912 | 94152 | 413752 |
| WsprryPico-StandaloneRF | 18443 | 970244 | 951812 | 267880 | 280440 | 227464 |

All four GNU `data` columns are zero. Primary stack is separately reserved at
16,384 bytes. Physical images additionally reserve an aligned 16,384-byte BSS
core 1 stack; the unused SDK default core 1 stack reservation is disabled.
`__HeapLimit` is `0x2007c000`. ELF checks establish nonoverlap; UF2 checks retain
the last 20 KiB journal/boot reservation and the known RP2350-E10 special block.
The firmware RF library now uses function/data sections so the SDK linker can
discard unused diagnostic tables. This removed 34,820 BSS bytes without changing
waveform generation or buffer sizes. Diagnostic RFBench/RFWTP targets also link.

TLS allocations have an 81,920-byte global cap, including custom allocation
metadata, with 16,384-byte incoming and 2,048-byte outgoing record content bounds.
The cap covers shared credential/crypto objects and both sessions together.
The actual host TLS run observed a 66,278-byte peak, 33,930 bytes with a single
HTTP status context, and zero retained TLS allocations after stop. One allocation
failure is deliberately injected at startup. These host figures are not target
allocator or stack measurements.

The shared target admission hook estimates remaining heap from the linker span
and `mallinfo().uordblks`. Growing frames, HTTP bodies, TLS allocations and WTP
output preserve 32 KiB scratch. Endpoint dispatch additionally admits 16 KiB;
browser dispatch admits twice the body plus 16 KiB, assets admit three times
their size, and LOAD admits 64 KiB for preparation after normative validation.
JSON object validation admits key-view growth and two decoded maximum-key
temporaries without imposing new key-count or length limits on WTP JSON.
The existing 65,536-byte document and nesting limits still bound the input.
Failed admission closes an unprocessed WTP
transport, drops advisory output, returns HTTP 503 where possible, or reports
LOAD internal failure before engine preparation. It does not clear an owner.

The sum of the TLS cap, one maximum WTP frame, one maximum HTTP body and the
32 KiB reserve is already 212,992 bytes, leaving only 14,472 bytes of physical
network-image heap address space for other live allocations. Retained jobs,
replay/status, parser/container capacity, temporary serialization, allocator
metadata and fragmentation must also fit. USB can independently contend for a
frame. Thus individual maxima are protocol bounds, **not** a promise that all
simultaneous maxima will be accepted. Admission deliberately rejects pressure;
there is no claim of a fully measured target heap envelope or guaranteed network
availability at exhaustion. Fragmentation can still defeat a total-free estimate;
target allocator and recovery behavior must be measured in 11.5.

At 138 MHz, a 16,384-word successor buffer lasts
`16384 * 32 / 138000000 = 3.799188 ms`. The earlier 1.530 ms refill observation
would leave approximately 2.269 ms for noticing completion, interrupts and
contention. It belongs to an earlier image and is not reused as acceptance here.
The 100 ms mailbox failure threshold and eight-second watchdog are recovery
bounds, not refill deadlines. Finite local DMA tails, launch guards and existing
driver failure latches remain essential.

Console INFO now exposes worker command count, maximum active service gap,
worker poll duration, command roundtrip, DMA IRQ count/duration, launch time,
core 0/core 1 stack canaries, sampled heap peak/current/available and TLS peak.
The old foreground timing observation is accurately named
`max_authority_poll_us`; physical refill timing is `rf_max_poll_ns`. API
`transport` adds active/pending, admissions/rejections/timeouts, handshake/poll
maxima and TLS allocations/failures. Existing watchdog reset/stage/hash/PC
diagnostics remain. Metrics are cumulative observations: sampled heap peaks can
miss short-lived allocations, stack canaries are estimates, and there is no
durable multi-reboot watchdog counter or claim of instrumentation completeness.

## Software validation

Inputs: Pico SDK 2.3.0 at `98a542c1a62fb549ffb5d66a3e5892b06276b670`,
Arm GNU 15.3.1, Mbed TLS at `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`,
138 MHz RF profile. Existing pins were retained; no SDK/tool installation or
download was needed. Host TLS uses the actual server and pinned Mbed TLS with
loopback TCP, injected clock/RNG and an explicitly simulated local-timer engine.
The worker thread advances a complete 512-event job independently of networking.
It exercises the explicit physical concurrency policy; it is not a Pico timing
or physical output test. Actual PIO/sink/stream behavior retains separate host
driver tests and later hardware gates.

| Check | Result and scope |
| --- | --- |
| Debug build and full `build-host` CTest | PASS, 31/31, including actual TLS, actual 11.1 client, browser regressions, RF/standalone/endpoint/core and optional analysis/descriptor checks |
| Separate ASan/UBSan C and C++ build | PASS, 23/23; applicable owned code, host TCP and Mbed TLS instrumented; no reported sanitizer defect |
| Separate ThreadSanitizer worker build | PASS, 2/2; worker ownership/reuse and nonreturning failure tests; not hardware IRQ synchronization validation |
| WTP contract validator | PASS, 23 schema, 7 raw JSON, 1 framing and 8 transition cases |
| Actual Chrome desktop/mobile | PASS at 1280x900 and 390x844; inspected owner-Armed and unavailable screenshots, foreign-Running controls, preserved drafts and no horizontal overflow |
| Four required firmware variants | PASS: standard/physical, network off/on; all four ELF/UF2 layout checks pass |
| Diagnostic firmware links | PASS: RFBench and RFWTP after section-GC change |
| Source formatting and documentation | C/C++ formatting, Markdown links and `git diff --check` checked before commit |

The sanitizer configuration has eight optional analysis/descriptor tests absent:
campaign_adapter_tests, campaign_analysis_tests, campaign_evidence_tests,
campaign_plan_tests, rf_bench_analysis_tests, rf_bench_measurement_tests,
rf_correction_analysis_tests and usb_descriptor_tests. They pass in the normal
31-test build. Prebuilt OpenSSL is not instrumented. ThreadSanitizer covers the
portable worker separately; it does not cover target SDK IRQ/flash mechanisms.
Actual browser rendering uses local HTTP fixtures; real mTLS/CSP are verified
separately by TLS tests, without importing any system certificate.

The expanded actual-TLS suite covers persistent WTP/repeated HTTPS; Armed and
Running observation; browser-owned abort with another slow client; foreign and
same-certificate/different-session rejection; max 65,536-byte WTP plus fragmented
32,768-byte HTTP input; saturation, pending/slow clients, stalled reads/writes;
controller disconnect/link-loss completion; revision races; idle admission
racing CLAIM; UTC loss/recovery; reset/EOF/reconnect and 20 reuse cycles. Delayed
ACK injection proves unrelated responses cannot finish Wi-Fi changes, initiating
failure cancels, a later claim prevents application, and correct completion
applies once. Startup tests exercise competing-server rejection, zero-memory
failure, full stop/free and restart. Adapter tests cover obsolete tokens, USB
claim arbitration, output pressure without authority loss and parser/API/LOAD
exhaustion. Worker tests cover a paused producer, autonomous completion, clock
failure, 1,000 mailbox reuses, failed disable, reentry and absent-consumer abort.

Reproduce host, sanitizers, client and browser checks using the
[network guide](network-control.md#phase-112-reproducibility). The local run used
`build/phase11-2-client`, an ignored detached clean clone of the companion at
`d333c69edc8a65bf59ae52603110996921f82ce1`; the checker validates tracked cleanliness
and revision at configuration. Reconfigure after changing that source input.
The installed OpenSSL root was `/opt/homebrew/opt/openssl@3`. Generated credentials,
binaries and screenshots stay ignored; logs are in each build's
`Testing/Temporary/LastTest.log`, with optional screenshots in `build/phase11-2-ui`.

Firmware reproduction, with an already installed pinned SDK/toolchain:

```sh
cmake --preset pico2-w -DWSPRRY_PICO_NETWORK_PORT=0
cmake --build build/pico2-w --target WsprryPico WsprryPico-StandaloneRF --parallel
cmake -S . -B build/pico2-w-network -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DWSPRRY_PICO_BUILD_FIRMWARE=ON -DWSPRRY_PICO_BUILD_TESTS=OFF -DPICO_BOARD=pico2_w \
  -DWSPRRY_PICO_NETWORK_PORT=18443 \
  -DWSPRRY_PICO_NETWORK_CREDENTIAL_DIR="$PWD/build-host/network-test-credentials"
cmake --build build/pico2-w-network --target WsprryPico WsprryPico-StandaloneRF --parallel
python3 scripts/check_standalone_image.py build/pico2-w/firmware/WsprryPico.elf
python3 scripts/check_standalone_image.py build/pico2-w/firmware/WsprryPico-StandaloneRF.elf
python3 scripts/check_standalone_image.py build/pico2-w-network/firmware/WsprryPico.elf
python3 scripts/check_standalone_image.py build/pico2-w-network/firmware/WsprryPico-StandaloneRF.elf
```

Generate one-day ephemeral host credentials first as documented in the network
guide. Network-bearing images contain private test credentials and must not be
published. Network control remains disabled by default.

## Adversarial findings, repairs and failed attempts

| Finding | Repair and closure evidence |
| --- | --- |
| Crypto/JSON can starve foreground refills | Dedicated RF owner; delayed-producer worker test and target links pass; contention measurement remains open |
| Shared deferred state could be applied by another close | Generation binding, cancellation, acknowledgement and idle recheck; obsolete-token and delayed-ACK TLS tests pass |
| Shared TLS global hook could be cleared by a rejected second instance's destructor | Owner-scoped teardown; competing-instance startup test passes |
| TCP error/reset lifetime differed from lwIP | Reviewed MIT sibling free-before-error pattern; adapted mock, reset/reconnect and ASan checks pass |
| Multiplying parsers/TLS could exhaust physical heap | One WTP, 80 KiB TLS cap, shared growth/dispatch admission, bounded JSON scratch and unused-table GC; forced exhaustion and maximum-input tests pass |
| Generic memory rejection altered WTP error precedence | Guard moved after LOAD normative validation; low-memory unknown-operation and LOAD tests pass |
| Fixed JSON key scratch limits could narrow otherwise valid bodies before operation selection | Replaced with heap admission for key views and decoded-key comparisons; many/long-key unknown-operation decoding regression passes |
| Browser failure retained apparently live values and Wi-Fi wording implied observed disconnect | Unknown state with timestamped last observation, drafts retained, requested wording; browser tests and two render/inspection passes pass |
| Reused pointer or timed-out borrowed job could outlive storage | One non-abandonable rendezvous, nonreturning failure, owner-local peripherals; TSan/reuse/failure tests pass |

Failed attempts are retained here rather than replaced by the final pass:

- Initial TLS startup failed with error `-1` because sandbox loopback bind was
  denied. The authorized socket tests passed with local socket access.
- An initial test fixture reset boot identity twice and correctly entered a
  fault state. The fixture now supplies its boot identity at construction.
- A missing FrameParser include caused a build failure; one subsequent test
  invocation encountered the stale binary. The include was fixed and both full
  configurations rebuilt before accepting results.
- Tests originally reused one session across different certificate principals
  and repeated CLAIM. The service correctly rejected these operations; tests
  now use valid distinct identities and one claim per ownership acquisition.
- The added output-pressure test initially omitted the typed request digest and
  was rejected as invalid. It now supplies a nonzero digest and observes a loaded
  job transition, exercising advisory-output admission without authority loss.
- The new many-key decoding test initially held a view of a temporary wire
  string. The decoding assertion failed; the fixture now owns that string for
  the complete parse/decode lifetime and passes normally and under ASan/UBSan.
- The short/accelerated DryRun timing fixture could miss the intended Running
  observation under sanitizer load. It was replaced by an explicit elapsed-time
  local-timer simulation and a longer bounded job. No production timing limit
  or target RF acceptance threshold was relaxed.
- The sibling advanced independently to `088869722b9c064058a13f84bcb20c3ccbb76f54`.
  The explicit client-pin gate rejected that checkout. An isolated clean clone
  of the requested `d333c69` input resolved it without editing the sibling.
- Expected subprocess aborts in worker failure tests are assertions of the
  fail-closed software path, not unexpected runtime crashes.

The final reassessment found no remaining actionable software finding within
this slice after the listed repairs and affected-check reruns. It does not close
target resource/deadline, RF, physical recovery or joint acceptance gates.

## Companion follow-up and unexecuted target acceptance

The read-only WsprryPi acceptance record at `0888697` records
[CI run 34268677261](https://github.com/WsprryPi/WsprryPi/actions/runs/34268677261)
at `d333c69edc8a65bf59ae52603110996921f82ce1` as passing all five jobs, including
network/UI. That is the companion's recorded remote result, not a new remote run
performed here. Pico-owned `network_11_1_interop` builds and runs the reviewed
unmodified d333 client/application/TLS/HTTP sources against this server using
valid 32-hex device identities and the companion's original restart orchestrator.

Required WsprryPi follow-up: replace the old Pico pin
`0fd8191c5218d3b5f2da9122a2ae55bf728ae3f2` with the commit containing this record in
`src/tests/network/CMakeLists.txt` and `.github/workflows/debian-non-hardware.yml`,
then run its original clean-reference gate and CI. Update
`docs/development/phase11-1-review.md`, `docs/wtp-network.md` and
`docs/wtp-browser-api.md` with the concurrent Pico policy and new evidence.
API changes are additive apart from the advertised connection count; WTP remains
unchanged. Preserve the WsprryPi application's idle-only remote management policy.
The user-facing documentation follow-up belongs in Wsprry_Pi_Docs, starting with
`docs/User_Interface/Maintenance/network_safety.md`: document separate browser
identity/session, bounded capacity, unknown observations and required recovery.
Neither companion repository was edited or assigned work automatically.

Later work requires explicit hardware authorization and an exact recorded board,
firmware commit/hash, engine, 138 MHz clock, mode/job, certificate identity,
network, receiver and conducted RF path. Do not reuse earlier RF acceptance for
this changed architecture. Prepare and execute these gates only when authorized:

1. **11.3:** DHCP plus stable mDNS `.local` name, hostname certificates, optional
   explicit IP and joint resolution tests; no reservation requirement. This slice
   leaves name discovery and provisioning unimplemented.
2. **11.4:** Inhibited physical board validation of simultaneous WTP/HTTPS,
   strict certificates/UTC, saturation, delayed/lost responses, USB arbitration,
   flash lockout, startup failure and watchdog recovery. Observe actual output
   state; disconnect is not evidence of inhibition.
3. **11.5:** Run maximum retained job/session/replay and competing input workloads
   on the exact physical build. Capture INFO/transport before, during and after
   valid/invalid/slow handshakes, browser reads, maximum frames, no-reader peers,
   reconnect/reset/link loss and authorized idle flash writes. Measure both
   stacks, fragmentation/largest allocation, true allocation peaks, service-gap,
   refill/launch/IRQ timing and XIP/SRAM contention. Compare worst service gap
   plus refill against the 3.799188 ms buffer interval with a justified margin;
   preserve every overrun, failure latch and watchdog event. Do not substitute
   the 100 ms mailbox timeout for the RF deadline or call sampled peaks exact.
4. **11.6:** Controlled conducted capture with the recorded immutable RF path,
   repeat mode/job/network pressure cases and independently assess timing,
   spectral behavior and shutdown. Retain failed captures and unknown output
   until authoritative status and the measurement establish the result.
5. **11.7:** Joint clean-pin host/Pico/UI review, companion CI, documented physical
   limits and final Phase 11 disposition. Phase 11 is not complete here.
