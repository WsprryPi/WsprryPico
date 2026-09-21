# Phase 12.5 hardware-free activation-safety review

Status: the bounded P12.5 hardware-free activation-safety tranche is
implemented, reviewed and accepted within this record. Phase 12 remains active.
No authenticated Pico BLE or SoftAP transport, production live-reload adapter
or physical acceptance is claimed.

Date: 2026-09-21

## Authority and source identity

Work began from clean `devel` at
`2bc90b1fe59b7f2470ddda031fd666af76d91e87`, equal to the local
`origin/devel` reference. The execution contract is retained in
[phase12-5-execution-prompt.md](phase12-5-execution-prompt.md). This record is
prepared before the resulting commit, so it cannot identify its own final
commit or remote-parity result; those identities must be reported after
publication.

The retained Pico SDK is 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`. The source trees used by the
accepted build correspond to Mbed TLS
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`, lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95` and CYW43 driver
`055d64274b014dd7b1c2fc94d26e8a18face7124`. The SDK records BTstack
`eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`, but its retained BTstack
directory remains unpopulated. P12.5 therefore does not compile or validate a
BLE target.

The target build used Arm GNU Toolchain 15.3.1
(`Arm GNU Toolchain 15.3.Rel1`, build `arm-15.149`, dated 20260627) and the
already retained SDK-selected picotool source
`6f6458d792b93685a11423b244a585eaa99eafcf`. Host and sanitizer builds used
Apple Clang 21.0.0 with the installed MacOSX 26.5 SDK, CMake 4.4.3 and Ninja
1.13.2. The exercised scripts used Python 3.14.7 and Node.js 26.9.0.

All work in this tranche was source inspection, editing, deterministic host
execution and cross-building. No Pico, USB endpoint, debugger, BLE or Wi-Fi
radio, SoftAP, physical network endpoint, fixture or RF path was contacted. No
firmware was flashed, and no host radio, route, service, trust store or
certificate installation was changed.

## Implemented boundary

### Delivery-safe activation

- A transport-neutral `ActivationCoordinator` owns a complete copy of one
  committed profile while its apply response is awaiting a terminal delivery
  event. It never retains the manager's borrowed credential views.
- A genuinely new committed generation is bound to its exact apply request ID
  and generation. The manager returns the complete nonsensitive apply reply
  before a future transport may call `release_activation()`.
- An exact terminal callback releases the action once. Wrong-request,
  wrong-generation, stale and duplicate callbacks cannot repeat it. The
  authoritative apply replay entry is protected from bounded-cache eviction
  while delivery or fail-closed resolution is pending.
- A five-second wrap-safe timeout releases the action when a response or
  acknowledgement is lost. The committed generation remains authoritative;
  timeout cannot retain superseded trust indefinitely.
- Admission is blocked while activation is pending or faulted. Immediately
  before disruptive work, the coordinator samples activity after `prepare()`
  and rejects owner, armed, running, failed, output-active and output-unknown
  states without aborting, releasing or clearing a job or fault.
- The platform sequence is ordered `prepare -> activity recheck -> quiesce ->
  install -> restart`. `quiesce()` and `fail_closed()` are explicitly limited
  to the owned network runtime. Every stage can be failed deterministically.
- A prepare, activity, quiesce, install or restart failure latches only a
  nonsensitive fault and generation, scrubs the staged profile and invokes an
  idempotent fail-closed hook. An unconfirmed fail-closed result is retried by
  polling and at destruction. It never restores the old profile implicitly.
- Successful, failed, timed-out, collided and destroyed paths clear owned
  credential buffers. Existing standalone station, schedule and no-repeat
  watermark media are snapshotted and checked byte-for-byte, then reloaded, in
  the activation success and failure regressions.

This is a portable coordination boundary only. No `ActivationPlatform`
implementation is connected to Pico networking, CYW43, BLE or SoftAP.

### Shared PSA/TLS lifetime

- `PsaCryptoOwner` provides one core-0-serialized shared PSA lifetime for
  `PicoServer` and transient `MbedTlsCredentialValidator` calls. The first
  owner initializes PSA; the last owner frees it. Acquire/release and
  destructor paths are idempotent.
- The TLS server installs its bounded allocator before the first PSA acquire,
  owns a lease across its listener and sessions, and releases it only after
  connections, listener and independently owned certificate, key, RNG and
  entropy contexts have been freed.
- The credential validator owns a nested transient lease. Its certificate and
  key contexts are still private to one validation call and are destroyed
  before its lease is released. No TLS session is shared and the existing
  device, SAN, key-pair, chain, algorithm, validity and server-purpose checks
  are unchanged.
- The pinned-Mbed-TLS host regression exercises invalid startup, competing
  ownership, allocation failure, explicit stop, destructor cleanup, repeated
  restart and alternating valid/invalid validation while a live listener and
  established connection remain usable. Final TLS allocation and PSA owner
  counts return to zero.

The non-atomic owner count is deliberate: the maintained contract requires all
transitions to be serialized on core 0. A future adapter must not call it from
an unsynchronized second core or interrupt context.

### Flash, link retention and bounded ATT values

- The linked application boundary now ends at `0x3f5000`. A project-owned
  future BTstack bank is reserved at `0x3f5000`-`0x3f6fff`; the existing
  profile journal remains `0x3f7000`-`0x3fafff`, standalone records remain
  `0x3fb000`-`0x3fefff`, and the RP2350-E10 sector remains
  `0x3ff000`-`0x3fffff`.
- Every maintained RP2350 image receives fixed
  `PICO_FLASH_BANK_STORAGE_OFFSET=0x3f5000` and
  `PICO_FLASH_BANK_TOTAL_SIZE=0x2000` definitions. Static, host and UF2 checks
  reject overlap or ordinary payload beyond the new application boundary.
- `provisioning_pico_linkcheck` strongly retains the manager, command adapter,
  activation coordinator, Pico credential validator and shared PSA owner in an
  Arm ELF. It is compile/link and layout evidence only, not a working Pico
  provisioning path.
- The C++ and Bluefy command bounds remain 512 bytes and decoded profile
  fragments remain 64 bytes. P12.5 adds a 256-byte status-notification bound,
  enforces both browser-side wire limits, and rejects oversized values. Tests
  prove normal commands and replies exceed a default 20-byte ATT value.
  Therefore a future GATT adapter must provide negotiated capacity or bounded
  framing/reassembly in both directions; the atomic mock characteristic is not
  ATT interoperability evidence.

## Explicitly absent behavior

P12.5 does not add a GATT service, BLE advertising, pairing, bonding, proof of
possession, SoftAP, captive DHCP/DNS/HTTPS service, Wi-Fi reload, live
certificate swap, production network quiesce/restart implementation or reset
gesture. It does not populate BTstack, serve or publish the Bluefy page, select
its origin/cache/integrity policy, install desktop trust, generate a per-device
CA, place a CA private key on the RP2350, or encrypt credentials at rest. It
does not establish target ATT behavior, Wi-Fi coexistence, timing, RF output or
physical acceptance.

## Deterministic validation

| Evidence | Result and boundary |
| --- | --- |
| Host configure/build and aggregate CTest | Corrected MacOSX-26.5-pinned build passed 80/80 tests with only the immutable Phase 11.7 closure guard excluded. This is host evidence. |
| Immutable Phase 11.7 guard | Four assertions were run separately: two passed and the two reproducible-publication assertions produced their expected current-source-drift failure, `No later Pico production-runtime drift`. The guard and historical result were not changed. |
| WTP/1 validator | Passed 23 schema, seven raw-JSON, one framing and eight transition cases. WTP/1 semantics were not changed. |
| Focused browser/contract/layout/image checks | `provisioning_web_tests`, `provisioning_contract_tests`, `flash_layout_tests` and `standalone_image_tests` passed. The maintained standalone image checker also passed against `WsprryPico` and `WsprryPico-StandaloneRF`. |
| Focused ASan/UBSan | Passed 3/3: `provisioning_tests`, `flash_layout_tests` and the real pinned-Mbed-TLS `network_tls_tests`. Leak detection is not claimed beyond the host sanitizer's supported behavior. |
| Shared PSA/TLS regression | Passed with peak nested PSA owners 2, final owners 0, TLS peak allocation 66,372 bytes and final retained allocation 0. Listener and established-session requests passed before and after alternating valid/invalid validation and repeated server cycles. |
| RP2350 cross-build | Passed all six retained targets: `WsprryPico`, `WsprryPico-StandaloneRF`, `WsprryPico-RFBench`, `WsprryPico-RFWTP`, `rf_driver_linkcheck` and `provisioning_pico_linkcheck`. Existing heap-hook, stack-guard, RF-renderer and image checks remained enabled. |
| Maps and flash layout | The four firmware maps and provisioning linkcheck map report FLASH origin `0x10000000`, length `0x003f5000`. Static definitions and image tests cover the sixth link target and reject BTstack/profile/standalone/E10 overlap. |
| Strong symbol retention | The provisioning linkcheck ELF retains `ActivationCoordinator::stage`, `release` and `poll`, `Manager::release_activation`, and `PsaCryptoOwner::acquire` and `release`. |
| Source hygiene | Formatting, Python syntax checks, credential-content/inventory review and `git diff --check` passed for the reviewed tree. |

The first raw aggregate rerun did not propagate the configured SDK to nested
compiler processes: three compile-in-test cases selected the incompatible
Command Line Tools 27.0 SDK, and one transient TLS listener start failed. These
were environmental results, not hidden product passes. All four affected tests
passed 4/4 with the configured MacOSX 26.5 SDK and no listener conflict; the
corrected aggregate result above used that SDK selection for each command.

### Accepted Arm sizes

The accepted pre-existing self-contained `build/phase12-pico2-w` produced:

| Target | Text bytes | Data bytes | BSS bytes |
| --- | ---: | ---: | ---: |
| `WsprryPico` | 1,113,416 | 0 | 121,168 |
| `WsprryPico-StandaloneRF` | 1,126,332 | 0 | 276,332 |
| `WsprryPico-RFBench` | 192,664 | 0 | 279,012 |
| `WsprryPico-RFWTP` | 286,104 | 0 | 180,568 |
| `rf_driver_linkcheck` | 23,720 | 0 | 1,828 |
| `provisioning_pico_linkcheck` | 320,592 | 0 | 11,004 |

These sizes, maps and symbols are cross-build evidence, not runtime resource,
BLE, Wi-Fi, timing or RF qualification.

### Excluded fresh-build incident

A fresh `build/phase12-5-pico2-w` configure was intended to forbid dependency
population, but the supplied CMake override named the wrong variable and was
ignored. At 05:45:36 on 2026-09-21, CMake consequently performed a network
clone from `https://github.com/raspberrypi/picotool.git` and checked out the
exact pinned picotool revision
`6f6458d792b93685a11423b244a585eaa99eafcf`. Although the fetched revision was
the correct pin, the network clone violated the tranche's no-download boundary.
The directory is retained rather than destructively removed, but that build
and every artifact or result from it are excluded from acceptance evidence. No
attempt is made to launder the incident as an accepted clean build. All Arm
results, sizes, maps, image checks and symbols reported above come from the
pre-existing, self-contained `build/phase12-pico2-w` and its already retained
local picotool source.

## First adversarial findings and repairs

The first review pass found and repaired the following actionable issues:

1. Activation originally risked running before its apply response reached a
   terminal delivery boundary. The new coordinator stages after commit, binds
   request and generation, protects the replay entry, releases on an exact
   callback or five-second timeout, and executes at most once.
2. Pending or fault state could be observed before authentication checks, and
   bounded replay pressure could evict the authoritative pending apply reply.
   Authentication/device checks now retain precedence, and eviction skips the
   reply protected by the activation coordinator.
3. Staged credential ownership and fail-closed completion were incomplete on
   partial copy, stage collision, destruction and an initially unsuccessful
   fail-closed hook. Ownership is established before field copies, every
   terminal path scrubs the owned profile, collision records the newly
   committed generation as authoritative, and polling/destruction retry the
   idempotent hook until confirmed.
4. The initial platform interface did not state strongly enough that network
   teardown has no job/RF authority. Its contract now forbids aborting,
   releasing or clearing job/RF ownership or faults, forbids inferring inactive
   output, limits quiesce/fail-closed to the network runtime and rechecks all
   activity dimensions immediately before quiesce.
5. Existing preservation coverage did not snapshot standalone storage across
   every new activation terminal family. Success, timeout, late activity,
   prepare/quiesce/install/restart failure, fail-closed retry, collision and
   destruction cases now compare all 16 KiB byte-for-byte and reload the
   station, schedule and no-repeat watermark.
6. The ATT warning was one-directional and did not bound C++ replies or Bluefy
   status input. C++ notifications and Bluefy status values now share a
   256-byte maximum, Bluefy enforces the existing 512-byte command maximum,
   oversize tests cover both directions, and drift checks require explicit
   bidirectional framing/reassembly language.
7. The first shared-PSA ordering initialized global crypto before installing
   the server's bounded allocator. Allocator hooks now precede first acquire;
   all start-failure, stop, destructor and nested-validator paths return owner
   and TLS allocation counts to zero without weakening credential checks.
8. The target compiler exposed a `maybe-uninitialized` path while building the
   strong link boundary. The initialization/ownership ordering was made
   explicit and the Arm build was repeated with warnings as errors rather than
   suppressing the diagnostic.

All directly affected host, sanitizer, TLS, web/contract/layout/image and Arm
checks listed above were rerun after these repairs.

## Phase 11 assertion disposition

Phase 11.7 remains authoritative only for its recorded source pair and bounded
scope. P12.5 neither rewrites nor promotes that evidence.

| Assertion family | P12.5 impact and required fresh evidence |
| --- | --- |
| 11.1 TLS/browser/WTP | Shared PSA lifetime, the delivery boundary and bounded status values affect TLS/browser management. Repeat target old/new-CA rejection, exact delivery/timeout/replay behavior, restart/reload and browser/controller interoperability. WTP/1 itself is unchanged. |
| 11.2 ownership/concurrency | The portable platform contract explicitly preserves job/RF authority, but a future BLE/SoftAP/runtime adapter adds real contention. Repeat RF-inhibited service-gap, transport-loss, flash-lockout, heap/stack/DMA, output-unknown and fault behavior before any RF coexistence work. |
| 11.3 identity/trust | Directly affected. Repeat exact device/SAN/key-pair/chain/validity and wrong-board rejection on the candidate, plus DHCP/mDNS recovery, authenticated principal binding and proof that superseded clients are rejected after activation. |
| 11.4 inhibited acceptance | Historical only. The changed flash boundary, crypto lifetime and future activation path require the finite inhibited matrix and soak in the physical plan; no historical image is rebound. |
| 11.5 resource/contention | Linked text, reserved flash, PSA ownership and ATT framing assumptions changed. Repeat target admission/reclamation, storage/network loss, heap/stack/DMA and BLE/Wi-Fi coexistence at the accepted 138 MHz/divider-1 baseline after adapters exist. |
| 11.6 conducted RF | No accepted, failed, blocked, unsupported or excluded row changes, and no WSPR row is promoted. Repeat only source-impact-affected coexistence rows under new finite authority after inhibited acceptance. |
| 11.7 closure | The expected current-source drift is retained and proves the historical closure is not current-image evidence. Attach Phase 12 evidence separately and keep the closure artifacts immutable. |

## Open product and security decisions

The following remain explicit inputs rather than implementation choices made by
this tranche:

- BLE proof of possession; bonding retention/deletion; recovery and CA-rotation
  authority;
- the BLE local-management surface and authorization without creating a second
  job-control authority;
- SoftAP activation/recovery gesture, timeout, SSID naming, WPA policy and
  post-success disable behavior;
- Bluefy page origin, delivery, release integrity, update/cache/offline policy
  and the accepted iPhone, iOS and Bluefy versions;
- per-device CA and server-key generation location, whether the RP2350 ever
  receives a CA private key, and private-key-at-rest protection;
- credential-only versus full reset, BLE-bond deletion and explicit
  preservation of station, schedules and no-repeat watermark;
- desktop operator enrollment and trust-store UX; and
- the rule for acquiring and pinning the absent BTstack source.

## Remaining implementation and physical gates

Remaining implementation is an authenticated Pico BLE GATT adapter with real
bounded long-write/notification handling, an independent SoftAP/captive HTTPS
fallback and an owned `ActivationPlatform` that performs the selected
network-only quiesce/install/restart policy. These require the unresolved
security decisions above and another source/adversarial review.

With a committed target candidate and fresh explicit authority, execute the
finite RF-inhibited-first plan in
[phase12-physical-acceptance.md](phase12-physical-acceptance.md): establish
exact board/firmware/tool/page identities; verify BLE and SoftAP
authentication, wrong-device and malformed/oversize/replay behavior; exercise
reply/disconnect/timeout activation; prove old/new trust replacement and
recovery; inspect heap, stack, DMA, flash and storage reclamation; preserve
station/schedules/watermark; and run the bounded inhibited soak. Any RF
coexistence work follows only after source-impact review and a separately
authorized finite budget. Phase 13 remains separate.

No part of the present host or Arm evidence satisfies these physical gates.

## Final adversarial reassessment

The post-repair assessment repeated the source, test and claim review against
delivery ordering, replay and timeout behavior, activity races, platform
authority, secret ownership, fail-closed retry, shared PSA balance, ATT bounds,
flash overlap, standalone-byte preservation, link retention and evidence
provenance. It found no further actionable defect within the bounded
hardware-free P12.5 scope. The corrected host suite passed 80/80, the focused
sanitizer set passed 3/3, all six accepted Arm targets rebuilt, the two
maintained image checks passed and the final map/size/symbol observations match
this record. The unintended fresh-build network clone remains disclosed and
excluded rather than treated as evidence.
