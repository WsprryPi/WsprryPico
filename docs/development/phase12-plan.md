# Phase 12 provisioning implementation and acceptance plan

Status: active. P12.1/P12.2 and the bounded hardware-free P12.3–P12.5
infrastructure are implemented and reviewed through the
[P12.5 record](phase12-5-review.md). Authenticated Pico BLE and SoftAP
transports, an actual live-reload platform implementation and all physical
acceptance remain open.
This plan does not authorize target, radio, service, trust-store, certificate-installation or RF
operations.

## Scope and starting point

Phase 12 adds BLE-primary provisioning/local management, a SoftAP fallback and
runtime Wi-Fi/TLS credential lifecycle. The implementation must preserve the
single `JobService` ownership authority, local RP2350 timing, output-state
authority, persistent station/schedule configuration and no-repeat watermark.
Provisioning is not a second job-control protocol and does not change WTP/1.

The reviewed starting point is clean `devel` at
`c3ecc303db9dbcf68214e20c9b93f6889851aa6b`, equal to the local
`origin/devel` reference on 2026-09-20. Phase 11 is closed only within the scope
recorded by the Phase 11.7 joint review. The P12.5 tranche started from clean
`devel` at `2bc90b1fe59b7f2470ddda031fd666af76d91e87`, equal to
`origin/devel`. Phase 13 remains open.

## Source and dependency findings

- The existing `standalone::Store` uses four 4 KiB sectors: two configuration
  banks followed by two watermark banks. Its Pico mapping reserves the final
  16 KiB before the separate RP2350-E10 boot-workaround sector. P12.3 leaves
  those addresses unchanged and reserves the preceding 16 KiB for profiles.
  P12.5 reserves the preceding 8 KiB at `0x3f5000`–`0x3f6fff` for a future
  project-owned BTstack bank and ends linked application FLASH at `0x3f5000`.
- Wi-Fi settings currently live inside the version-1 standalone configuration,
  together with station and schedules. A committed provisioned profile now
  overlays only Wi-Fi fields in RAM and provides stable TLS credential views;
  the persistent standalone configuration is not rewritten.
- Browser mutations already establish useful policy: exact JSON fields,
  bounded bodies, revision preconditions, idempotency keys, same-origin/mTLS
  authority, idle-only persistent changes and explicit reboot requirements.
- The clean retained Pico SDK is 2.3.1 at
  `079c6f39023649b154152db30f1d781e884879bc`. Its CMake files define
  `pico_btstack_ble` and `pico_btstack_cyw43` and require a project-owned
  `btstack_config.h`. The project-local retained SDK checkout has no initialized
  BTstack submodule. A second pre-existing cache contains a clean standalone
  BTstack checkout at the recorded `eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`
  revision, but the parent SDK still reports the submodule uninitialized. P12.5
  does not initialize BTstack or build an adapter; exact source presence is not
  target, authentication, ATT-interoperability or coexistence evidence.
- Existing generated test identities show that a server certificate, private
  key and client CA fit comfortably inside a bounded 7 KiB canonical profile.
  The bound is nevertheless an implementation limit, not a promise that every
  possible PEM encoding is accepted.

## Selected portable contract

These decisions are sufficiently established for hardware-free implementation:

1. Provisioning transports are adapters. A portable state machine owns
   authorization preconditions, device binding, fragmentation, timeouts,
   replay, validation, transactional replacement and resource limits.
2. BLE is the primary adapter and SoftAP is the fallback. Both must present an
   authenticated, confidential, local session to the portable core. Merely
   being nearby or associated with an AP is not authentication.
3. Exactly one provisioning session and one staged profile are admitted. A
   session is bound to the full 32-hex WTP device ID and a nonempty principal.
4. A canonical profile replaces Wi-Fi and the complete TLS server trust bundle
   atomically. A successful new generation immediately supersedes the prior
   client CA; there is no implicit dual-trust grace period. A failed or
   interrupted write leaves the last committed generation authoritative.
5. A corrupted newest committed generation fails closed. It must never revive
   an older superseded trust bundle. An incomplete, never-committed newer slot
   may be ignored after restart.
6. Apply is idle-only: no owner, armed/running/failed state or active/unknown RF
   output. Provisioning never aborts a job and transport loss is not evidence of
   inactive output.
7. The profile journal is physically and logically separate from the existing
   station/schedule/watermark store. The portable slice must prove that those
   records do not change during profile replacement or recovery.
8. Payloads are at most 7,168 bytes, fragments are ordered and bounded, the
   active session times out after 30 seconds without progress, and replay state
   is bounded to eight request digests retained for five minutes.
9. JSON, Wi-Fi/time-server and identity rules reuse the existing parsers and
   validators. A platform credential validator must additionally prove the
   certificate chain, key pair, server purpose, validity, exact hostname SAN,
   device binding and accepted algorithms before a profile can commit.
10. Secrets never appear in status, logs, errors or replay entries. Staged RAM
    is scrubbed on apply, cancel, timeout and terminal failure. Persistence at
    rest is not claimed confidential by the portable implementation.
11. The selected iPhone BLE client is a Web Bluetooth provisioning UI opened in
    Bluefy; no WsprryPico-native iOS app is planned. The Safari-only path remains
    the SoftAP fallback. Bluefy and the delivered web page are explicit
    provisioning trust dependencies and must be identity/version-bound in
    acceptance evidence.

## Implementation slices

### P12.1 Portable profile and transactional journal

- Add exact parsing/canonical serialization for Wi-Fi, NTP and the complete TLS
  server bundle.
- Reuse current device-ID, hostname and Wi-Fi/time-server validation.
- Add a two-slot, header-last/commit-last journal with sequence and SHA-256
  integrity. Make interrupted-new-write recovery and newest-corruption
  fail-closed behavior deterministic.
- Keep its media interface independent of Pico flash layout.

### P12.2 Portable provisioning state machine

- Implement authenticated session open, ordered fragments, finalization,
  validate/apply, cancel and timeout.
- Enforce wrong-device, malformed, oversize, out-of-order, duplicate,
  request-ID reuse, concurrent-session, stale-generation and RF-busy failures.
- Bound and report only nonsensitive state, counts and committed generation.

### P12.3 Pico adapters

The bounded hardware-free infrastructure is implemented:

- A disjoint `provisioning::Media` Pico adapter and every maintained linker
  layout reserve `0x3f7000`–`0x3fafff` without moving existing journals.
- Fail-closed boot selection uses a committed profile for runtime Wi-Fi/TLS or
  the device-bound build bundle only when no profile exists. The listener waits
  for synchronized UTC and validates chain, key pair, exact DNS SAN, server EKU,
  validity, device binding and P-256/SHA-256 algorithms through Mbed TLS.
- The repository-owned standalone Web Bluetooth page validates, fragments,
  times out and cancels bounded requests through fixed project UUIDs. Mock GATT
  tests exercise it without contacting Bluefy or a radio.

The remaining P12.3 work is intentionally open:

- Add BLE GATT and SoftAP/captive HTTPS target adapters only after the security and
  recovery choices below are selected.
- Verify the existing browser-side Web Bluetooth provisioning client with an
  exact Bluefy and iOS version, an approved HTTPS origin/integrity policy and
  an authenticated target GATT adapter. Keep SoftAP/Safari independent.
- Connect the P12.5 delivery-safe coordinator to an idle-only target
  activator that stops new TLS sessions and replaces network state without
  altering RF/job authority. The production source still activates a previously
  committed profile at boot only.

The transport authentication, recovery gesture and at-rest key policy still
materially change product security and target behavior and were not invented by
this slice.

### P12.4 Portable command and activation boundary

The next hardware-free boundary is implemented without enabling a radio:

- `provisioning::CommandAdapter` is the single strict C++ decoder for the
  checked-in Bluefy version-1 `open`, `write`, `apply` and `cancel` vocabulary.
  It enforces closed objects, exact device identity, bounded canonical base64
  fragments and correlated nonsensitive replies for BLE or SoftAP labels.
- Authentication, confidentiality, locality and principal identity remain
  assertions supplied by a future platform adapter; transport selection or
  proximity grants no authority. The manager rechecks those assertions for
  every command and binds the principal and transport into replay identity, so
  another authenticated path cannot continue or replay that session.
- The P12.4 synchronous `ProfileActivator` boundary was an intermediate
  hardware-free seam. P12.5 replaces it because a disruptive implementation
  could otherwise destroy its own apply response before delivery.
- No Pico activator, GATT service, captive HTTPS service, radio path or page
  distribution policy is implemented. Without an activator, the existing
  boot-only application behavior is unchanged.

### P12.5 Delivery-safe activation and target admission

The next hardware-free safety boundary is implemented without enabling a radio:

- `ActivationCoordinator` owns one staged committed profile and binds it to the
  apply request and generation. It runs destructive work only after the future
  adapter reports a terminal response boundary or after a five-second timeout.
  Stale callbacks do nothing, exact replay does not restage, and new sessions
  remain blocked while activation is pending or faulted.
- The coordinator orders prepare, final activity recheck, quiesce, owned-profile
  installation and restart. Changed ownership/RF state or any platform failure
  leaves the new generation authoritative, invokes fail-closed behavior and
  scrubs staged secrets. The coordinator has no JobService or RF-owner handle;
  every future platform implementation is contractually forbidden from aborting,
  releasing or clearing job/RF ownership or inferring inactive output.
- `PsaCryptoOwner` shares serialized core-0 PSA lifetime between the TLS server
  and transient credential validator, so validation cannot globally free a
  running listener's crypto state.
- The future BTstack bank is pinned to `0x3f5000`–`0x3f6fff`; layout tests and the
  image checker reject application writes into it while preserving every
  profile, standalone, watermark and E10 address.
- `provisioning_pico_linkcheck` strongly retains the command, manager,
  activation, credential-validation and PSA boundaries in an RP2350 firmware
  link. Bluefy commands remain bounded to 512 bytes and status notifications to
  256 bytes, but both can exceed a default 20-byte ATT value; future GATT code
  must negotiate a sufficient payload or supply bounded bidirectional
  framing/reassembly and prove it on the exact client/target pair.
- No production activator or authenticated BLE/SoftAP adapter is connected.
  Firmware links and host mocks are not evidence of live reload or radio use.

## Deterministic acceptance matrix

The portable slice must cover:

| Area | Required assertions |
| --- | --- |
| Lifecycle | BLE and SoftAP session open, fragmented receive, finalize, validate, apply and committed reload |
| Authentication/identity | unauthenticated, non-confidential, nonlocal, empty-principal and wrong-device rejection |
| Input | malformed JSON/PEM, unsupported version, invalid Wi-Fi/time server/hostname/port, oversize and out-of-order fragments |
| Idempotency | exact duplicate returns the original result; same request ID with different content terminates the session; stale generation conflicts |
| Interruption | partial transfer timeout, explicit cancel, pre-commit write failure and commit-marker interruption reclaim memory and retain the last committed generation |
| Trust replacement | successful generation N+1 supersedes N; corrupt committed N+1 fails closed instead of selecting N |
| Existing data | station, schedules and watermark survive provisioning success, cancellation, interruption and reload unchanged |
| RF/ownership | owner, armed, running, failed, output-active and output-unknown states reject apply without abort/release side effects |
| Activation | reply precedes release; exact callback or five-second timeout executes once; stale callbacks do nothing; activity drift and injected prepare/quiesce/install/restart faults fail closed |
| Target admission | server survives nested valid/invalid credential validation; PSA last-owner release is balanced; BTstack/profile/standalone/E10 ranges do not overlap; strong linkcheck retains P12.5 symbols |
| Resources | one session, fragment-count/payload/replay bounds, secret-free status and RAM reclamation after every terminal path |

Run the documented host configure/build/CTest suite, the WTP contract validator,
focused sanitizer checks when the host supports them, and all firmware target
cross-links using only the retained pinned dependencies. Inspect linked flash/RAM
layout; a cross-build is not BLE, Wi-Fi, timing or RF evidence.

## Phase 11 assertion impact and revalidation

| Phase 11 assertion | Portable-slice impact | Required revalidation before target acceptance |
| --- | --- | --- |
| 11.1 shared TLS/browser software | New credential source and management path are affected | Host TLS/browser/WTP interoperability, old/new CA rejection matrix, reload and replay |
| 11.2 concurrent management | State-machine-only slice is additive; later radio adapters affect coexistence | Host ownership/fault suites, target service-gap/heap/stack/DMA checks and RF-inhibited contention first |
| 11.3 identity/trust | Directly affected by runtime hostname/certificate/device binding | Exact SAN/device/keypair/chain/validity checks, wrong-board rejection, DHCP/mDNS recovery and client trust replacement |
| 11.4 inhibited physical acceptance | Historical evidence remains immutable and is not rebound | New inhibited BLE/SoftAP matrix and soak; no reuse as current target evidence |
| 11.5 resource/contention | Portable code adds linked text; adapters/TLS reload add runtime resources | Repeat affected admission, heap/stack, TLS, storage, network-loss and reclamation assertions at 138 MHz/divider 1 |
| 11.6 conducted RF | No row is changed or promoted by host work | After adapters, repeat only source-impact-affected coexistence rows under new finite authority; preserve all excluded rows |
| 11.7 closure | Remains the Phase 11 record, not Phase 12 evidence | New Phase 12 review and ledger must cite, not rewrite, Phase 11 artifacts |

## Open product and security decisions

These choices block Pico transport adapters but not the portable slices:

- BLE proof of possession: numeric comparison/passkey, QR/out-of-band secret,
  USB-established bootstrap secret or another explicit mechanism.
- Whether BLE bonding is retained, how it is deleted and whether a bonded
  principal may rotate the client CA without a second local proof.
- The BLE local-management surface and authority: read-only status versus
  allowed mutations, without creating a second job-control authority.
- SoftAP activation and recovery gesture, timeout, SSID naming, WPA policy and
  whether the fallback is disabled after successful provisioning.
- Where the per-device CA and server private key are generated, and whether the
  RP2350 ever receives a CA private key. The current per-device CA private key
  must not be placed on the device by default.
- Private-key-at-rest policy: plaintext flash (matching the present embedded-key
  exposure), OTP-derived wrapping or external secure storage, including recovery
  and replacement consequences.
- Factory reset/recovery semantics and the physical action required to erase
  Wi-Fi, TLS credentials and BLE bonds without erasing station/schedules or the
  no-repeat watermark unintentionally.
- The Web Bluetooth page origin, delivery, release integrity, update/cache and
  offline policy. Selecting Bluefy resolves the iPhone client choice, not the
  provenance of the provisioning page it executes.
- Operator-client enrollment and trust-store UX for Windows/macOS/Linux. Device
  provisioning must not silently install host trust or bypass warnings.

## Completion boundary

Phase 12 is not complete at the hardware-free P12.5 checkpoint. Completion
requires selected security policies, implemented BLE and SoftAP adapters, a
connected authenticated idle-only live activator, bounded inhibited-target
acceptance, an authorized physical-plan execution and repaired adversarial
reassessment.
Phase 13 RF qualification remains separate.
