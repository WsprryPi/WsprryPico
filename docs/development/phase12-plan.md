# Phase 12 provisioning implementation and acceptance plan

Status: active and **OPEN_PARTIAL**. P12.1-P12.5 remain accepted within their
documented hardware-free scopes. P12.6 production-enables BLE provisioning,
authenticated controller time, Identify/status, an unchanged WTP/1 stream, the
network-only live activator and indicator, a deterministic offline-capable
Bluefy release, and the production SoftAP path. At that historical checkpoint,
the SoftAP path included the bounded project-owned DHCP server on
`192.168.4.1/24`, AP-interface mDNS, blank read-only HTTP,
provisioned pre-clock/normal HTTPS, password/cookie admission,
controller time and the existing browser/`JobService` API.

**Current continuation (2026-09-27):** the separate approved blank-device
Wi-Fi-only encrypted transaction is implemented on `devel` at `fb091f8` and
its physical iPhone/network target acceptance remains open. The operator
selected Safari and SoftAP only for the proposed P12.7–P12.12 consumer
commissioning path. The historical BLE/Bluefy engineering evidence below
remains valid only within its recorded scope; it does not approve the new
Safari browser-owner contract or alter the current Field-GATT/1 engineering
baseline. The complete revised consumer contract was approved in the
[P12.7 decision](phase12-7-decision.md); implementation and target acceptance
remain open.

Bounded native-Pi target evidence covers BLE identity/time/status and WTP
`HELLO`/`STATUS`, plus the provisioned SoftAP WPA2/DHCP/mDNS/TLS,
password/cookie, time/status/ownership/reconnect/resource-return subset. The
later phone-assisted continuation records an iPhone 17 Pro Max, iOS 27.0 and
Bluefy 3.9.3; one authenticated phone-time exchange, Identify LED and field-
status observation, retained-bond authorization, and Bluefy WTP `HELLO` plus
read-only `STATUS` passed within their recorded limits. The exact final BLE
combination was RF-inhibited firmware `4377d2ded8e3`, boot
`331e555683a5d6c6122735a07883e0a8` and Bluefy release
`e1e6caa574a0e5c75cfd8c0a168c3ec8c2b896322ec7a7acc20d555f357f0625`.
It ended disconnected, empty, unowned and output inactive with healthy journals
and preserved settings.

Those bounded passes do not establish offline page reuse, fresh-password/new-
pairing behavior, full credential provisioning/activation, arbitrary BLE job
control, the broad controller-time/LED matrix, reset/recovery, coexistence or
release acceptance. The SoftAP physical continuation is recorded in the
[RF-inhibited SoftAP review](phase12-softap-physical-review.md). Neither result
is RF or broad interoperability acceptance. The later BLE source boundary is
reviewed in
the [BLE local-control continuation](phase12-ble-local-control-review.md). The
bounded Pi/TCP slice is recorded in the
[Raspberry Pi BLE and first-class TCP/WTP review](phase12-pi-ble-tcp-review.md).
The
revisited P12.3 source slice remains
**CLOSED_SCOPED** by the [P12.3 closeout](phase12-3-review.md); the later
production work does not rewrite that evidence. The operator-selected
[field-access and security contract](phase12-field-access-contract.md) is the
implemented engineering baseline until an approved P12.7 revision supersedes
its consumer rules.
This plan does not authorize target, radio, service, trust-store, certificate-installation or RF
operations.

| Roadmap slice | Current position |
| --- | --- |
| P12.1-P12.2: profile journal and provisioning state machine | Accepted in their hardware-free scope. |
| P12.3: Pico adapter source | **CLOSED_SCOPED** for source, deterministic tests and RP2350 cross-links; not physical acceptance. |
| P12.4-P12.5: commands, delivery-safe activation and admission | Implemented and accepted in their hardware-free scope. |
| P12.6: production integration | **Partial.** BLE provisioning/local control and the SoftAP browser path are production-wired. The Field-GATT/1 source contract is frozen and vector-checked. Candidate A has bounded RF-inhibited native-Pi maximum-profile and repaired Bluefy prepared-file activation evidence through a normal generation-3 restart, BLE readback and positive mTLS/WTP/HTTPS readback. The engineering path works; the consumer commissioning, recovery and broad target-acceptance milestones below remain open. |
| Physical Stage A | **Partial.** Candidate identity, adoption, preserved settings, BLE advertising, exact iPhone/iOS/Bluefy identity, retained-bond authorization, one authenticated phone-time exchange, Identify LED/field status, Bluefy read-only `HELLO`/`STATUS`, native-Pi BLE/SoftAP subsets, and bounded profile activation passed within their recorded limits. Consumer first-run commissioning, offline reuse, owner enrollment/replacement, recovery, broader BLE controls, time/LED, fault/trust/resource/soak and stable-station AP-withdrawal matrices remain open. |
| Physical Stage B / RF output | Not authorized or performed. Phase 13 remains separate. |

## Scope and starting point

The initial Phase 12 architecture added BLE-primary provisioning/local
management, a SoftAP fallback and
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

The production SoftAP continuation started from clean `devel` at
`ae21bc7b9dd772b0b37cf52b288a2544e848ea9f`, equal to `origin/devel`. Its
candidate was frozen only after implementation and review at
`b28400e114abb68566eef2154361e7d541069ff0`; no pre-freeze repository drift
sentinel was installed. That clean RF-inhibited image was built and hashed but
not flashed, so it is not physical evidence.

The RF-inhibited SoftAP target continuation started from clean `devel` at
`c84fa157b93493cf0c28fa2e96c30e0beeabe7e2`, equal to `origin/devel`.
Source was again allowed to evolve before each candidate was committed. The
final exact target candidate is `0ecf9c170384fd2cc3ba802515e1d2c1396ab9fa`;
its retained failures, repairs and partial target acceptance are recorded in
the [SoftAP physical result](phase12-softap-physical-result.json).

## Source and dependency findings

- The existing `standalone::Store` still uses four 4 KiB sectors at
  `0x3fb000`–`0x3fefff`, followed by the E10 sector at `0x3ff000`. P12.3 now
  reserves and implements the selected two-sector access journal at
  `0x3f3000`–`0x3f4fff`, retains the BTstack bank at
  `0x3f5000`–`0x3f6fff` and the profile journal at
  `0x3f7000`–`0x3fafff`, and ends application FLASH at `0x3f3000`. Station,
  schedules and watermark addresses are unchanged. Cross-linked image bounds
  and the standalone image checker enforce every boundary.
- Wi-Fi settings currently live inside the version-1 standalone configuration,
  together with station and schedules. A committed provisioned profile now
  overlays only Wi-Fi fields in RAM and provides stable TLS credential views;
  the persistent standalone configuration is not rewritten.
- Browser mutations already establish useful policy: exact JSON fields,
  bounded bodies, revision preconditions, idempotency keys, same-origin/mTLS
  authority, idle-only persistent changes and explicit reboot requirements.
- The clean retained Pico SDK is 2.3.1 at
  `079c6f39023649b154152db30f1d781e884879bc`. Its own BTstack submodule is
  uninitialized, but an existing clean checkout at the exact recorded
  `eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec` revision is available.
  The P12.3 candidate adapter cross-links against that exact checkout. Configure
  rejects a different revision or any tracked/untracked change. This proves
  source compatibility, not live authentication, ATT interoperability or
  coexistence.
- Existing generated test identities show that a server certificate, private
  key and client CA fit comfortably inside a bounded 7 KiB canonical profile.
  The bound is nevertheless an implementation limit, not a promise that every
  possible PEM encoding is accepted.
- The pinned SDK does not enable or supply the CYW43 driver's optional DHCP
  utility. The production SoftAP therefore owns a bounded DHCP server derived
  from the MIT MicroPython implementation carried by Raspberry Pi's
  `pico-examples`; it is AP-netif-bound, checked at startup and covered by
  hardware-free packet, pool-exhaustion and Pico cross-link tests.

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
   atomically. At commit, the new generation immediately supersedes the prior
   client CA and closes network admission; only the applying terminal response
   may complete before exactly-once activation after delivery or five seconds.
   Neither generation admits new network principals in that interval, so there
   is no implicit dual-trust grace period. A failed or interrupted pre-commit
   write leaves the last committed generation authoritative.
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
11. At the P12.6 engineering checkpoint, the selected iPhone BLE client was a
    Web Bluetooth provisioning UI opened in Bluefy. On 2026-09-27 the operator
    selected Safari/SoftAP only for the proposed consumer P12.7–P12.12 path;
    this earlier client rule remains a historical engineering baseline until
    P12.7 approval. Bluefy and the delivered web page were explicit
    provisioning trust dependencies and must be identity/version-bound in
    acceptance evidence. A native Raspberry Pi/Linux BlueZ command-line client
    is an additional supported local/bench client using the same encrypted GATT
    service, full-device-ID binding, application authorization, provisioning
    transaction and unchanged WTP/1 stream. It did not replace or qualify the
    then-selected Bluefy/iOS acceptance path.
12. The [selected field-access contract](phase12-field-access-contract.md)
    defines no-infrastructure operation, Just Works plus application-password
    enrollment, retained bonds, SoftAP field mode, controller-supplied UTC,
    onboard-LED behavior, trust step-up and reset preservation. It does not
    weaken the authorization, confidentiality, locality, job/RF or storage rules
    above.

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

Status: **CLOSED_SCOPED** for hardware-free source, deterministic tests and
RP2350 cross-link evidence. See
[phase12-3-review.md](phase12-3-review.md).

Implemented:

- The access journal, source-mode tombstones and resumable reset coordinator
  occupy the selected disjoint layout and fail closed on unhealthy or pending
  state. Production boot suppresses station startup and schedules until access
  authority is healthy.
- Portable access policy implements the selected password/confirmation,
  enrollment, bond, session, field-mode, SoftAP-cookie, reset, controller-time
  and LED behavior with bounded state and deterministic fault coverage.
- Fixed 64-byte GATT framing and the candidate Pico GATT adapter cross-link
  against the exact clean BTstack revision. The adapter requires encryption,
  application-password promotion, one connection, indication delivery and
  stable stored peer identities.
- The candidate Pico WPA2 SoftAP and onboard-LED adapters cross-link. Portable
  HTTP admission supplies strict same-origin cookie authority and blank,
  pre-clock and normal surfaces without changing the ordinary station-interface
  trust contract.
- The Bluefy page uses the same framing and authorization sequence and covers
  malformed, oversize, wrong-device, replay, timeout, cancel and disconnect
  paths.
- SNTP and authenticated controller observations share one source arbiter;
  source disagreement fails closed.

Not claimed by this scoped closure:

- At the P12.3 checkpoint the production image did not start GATT, SoftAP/HTTPS
  or the indicator controller and had no Pico `ActivationPlatform`. Complete production
  service/activator wiring remains a Phase 12 gate.
- BLE field job control is now production-connected as a separate unchanged
  WTP/1 stream backed by an additional endpoint sharing the one `JobService`.
  Its physical interoperability, complete end-user UI and target resource
  behavior remain open; the provisioning vocabulary is not a second job
  protocol.
- Exact gestures, offline Bluefy origin/integrity/cache behavior, accepted
  iPhone/iOS/Bluefy versions and every live transport/coexistence/resource claim
  require the finite physical plan.

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
- At the P12.4 checkpoint no Pico activator, GATT service, captive HTTPS
  service, radio path or page distribution policy existed. The later scoped
  P12.3 closeout adds cross-linked adapter candidates but still does not enable
  them or connect a production activator.

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
- At the P12.5 checkpoint no production activator or authenticated BLE/SoftAP
  field service was connected. The later P12.3 candidate adapter link and host mocks are not
  evidence of live reload or radio use.

## Deterministic acceptance matrix

### P12.6 Production integration and partial Stage A

- The standard RF-inhibited `WsprryPico` image now owns one CYW43
  initialization, derives checked station-MAC identity before local access,
  constructs the access controller, provisioning manager, strict BLE command
  adapter, credential validator and network-only activation platform, and starts
  the encrypted GATT service only from healthy adopted access state.
- GATT uses fixed bidirectional framing and retains advertisement/scan-response
  storage for BTstack's asynchronous lifetime. ATT indication completion is
  deferred into core-0 polling before activation release. Retained authorized
  bonds treat a repeated page authorization request idempotently.
- BLE profile apply does not inherit ordinary retained-bond authority. The page
  must provide a fresh password proof bound to the final staged digest, exact
  apply request and expected generation. While the public default is active,
  Candidate A must also receive `ACCESS CONFIRM PROFILE <full-device-id>` over
  USB within the same 30-second staging session. Failure, cancellation,
  disconnect or expiry invalidates the one-use proof.
- The checked-in `docs/bluefy` artifact is built deterministically from
  `src/provisioning/web`, contains no candidate identity or credentials, uses
  the Bluefy/Web Bluetooth chooser, reads and displays the full device identity,
  requires a separate confirmation click, verifies release assets and installs
  a release-keyed atomic offline cache.
- The later BLE local-control continuation routes authenticated controller-time,
  Identify/status and a separate WTP/1 byte stream through the same encrypted,
  application-authorized connection. Its second endpoint shares the one
  `JobService`; fixed ATT segmentation does not define another protocol. The
  extended deterministic Bluefy client is source/test evidence only until the
  physical matrix exercises it.
- The production SoftAP continuation connects the existing coordinator and
  WPA2-AES adapter to the standard image. A blank device exposes only fixed-IP
  read-only HTTP identity/recovery information. A provisioned device uses its
  device-bound TLS server identity for pre-clock login/controller time and the
  normal browser API without a client certificate; station HTTPS and raw WTP
  remain mTLS-only. The SoftAP cookie binds to one exact WTP session only after
  a successful `HELLO`, and absolute-expiry grace permits only STATUS, ABORT
  and controller-time operations for that exact armed/running session.
- AP and station traffic share the one bounded TLS listener and one
  `JobService`. Interface classification selects SoftAP server-auth-only TLS;
  the station path retains client-certificate verification and clock gating.
  Parsed HTTP/password/cookie storage is scrubbed on connection teardown.
- USB-local `ACCESS ADOPT`, `ACCESS ENROLL`, `ACCESS STATUS` and
  `IDENTIFY` are the only implemented physical confirmation/diagnostic
  controls. BOOTSEL-at-boot gestures are not viable because ROM boot selection
  prevents the application from observing the hold; no substitute gesture is
  claimed.
- Partial physical evidence proves the exact RF-inhibited candidate identity,
  healthy adoption, preserved station/schedule/watermark state and repaired BLE
  advertisement. The later native-Pi SoftAP run additionally proves its bounded
  association, DHCP/mDNS, authenticated HTTPS/time/local-control and resource
  rows. It does not prove iPhone/Safari/Bluefy interoperability,
  provisioning/activation, offline reuse, LED waveform, fault/soak coverage or
  broad coexistence.

### P12.6 normative field-GATT protocol contract

Status: **FROZEN_SOURCE**. The
[Field-GATT/1 protocol and super-user guide](../protocol/Field-GATT.md) and
[machine-readable vectors](../protocol/Field-GATT-v1-vectors.json) bind the
custom wire behavior across firmware, Bluefy, the native Raspberry Pi client,
documentation and deterministic tests. Incompatible wire changes require a new
Field-GATT protocol version. This source/host freeze does not close the Phase
12 physical interoperability or end-user acceptance gates.

The frozen authoritative custom BLE wire contract defines:

- protocol scope, versioning, compatibility rules and its separation from
  WTP/1;
- the service and characteristic UUID table, characteristic roles and
  properties, encryption/key-size requirements, CCCD behavior and permitted
  ATT write modes;
- the provisioning command/status frame header byte-for-byte, flags, sequence
  rules, length/count limits, reset/reassembly behavior and UTF-8/JSON encoding;
- request and response envelopes and the complete authorization, controller-
  time, Identify/status, provisioning, access/bond and reset operation schemas;
- session and authorization state transitions, indication-confirmation and
  delivery boundaries, timeouts, disconnect behavior, ATT errors and
  application error codes;
- the exact mapping of the unchanged WTP/1 byte stream onto its GATT
  characteristics, including segmentation, flow control and transport-close
  semantics without defining a second job-control protocol; and
- conformance examples or vectors exercised by the firmware, Bluefy and native
  Raspberry Pi clients so implementation drift is caught by tests after the
  contract is frozen.

The document describes the reviewed implementation rather than declaring an
implementation accident normative. Vector-driven tests enforce agreement after
freeze. No source freeze or drift sentinel substitutes for physical acceptance.

The freeze tranche repaired and retested the three mismatches found by the
initial conformance review:

- the native Raspberry Pi/Linux `provision` path now requires a fresh
  `profile_step_up` bound to the profile session, apply request and generation,
  including bounded USB-confirmation polling;
- the manager admits the complete 7,168-byte profile contract even with
  one-byte fragments, while retaining the 64-byte per-fragment limit; and
- enrollment-window expiry erases an open-link provisional bond, invalidates
  its authority and requests controller link closure.

The checked vectors cover 4,096-, 4,097-, 7,168- and 7,169-byte boundaries,
direct-apply rejection, exact step-up binding, impossible step-up state and
expiry cleanup. Client-side prompt/secret hygiene and cancellation remain part
of the deterministic conformance suite.

Phase 12 completion evidence must cover:

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
| Protocol documentation | one normative `docs/protocol/Field-GATT.md` defines the complete custom GATT wire contract; firmware, Bluefy and native-Pi behavior and conformance vectors agree with it |
| Future target admission | server survives nested valid/invalid credential validation; PSA last-owner release is balanced; access/BTstack/profile/standalone/E10 ranges do not overlap; app ends at `0x3f3000`; updated strong linkcheck retains the provisioning/activation symbols inherited from P12.5 |
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

## Remaining Phase 12 roadmap

The existing
[field-access and security contract](phase12-field-access-contract.md) remains
the implemented engineering baseline until the first milestone below replaces
its user-facing commissioning rules. Its fail-closed storage, identity,
ownership, transactional activation and RF-authority boundaries remain in
force. The roadmap does not expose those mechanisms as an acceptable consumer
workflow.

The disconnect-related timeout observed during physical work is closed as a
non-qualifying test run. It is not an open device defect or a Phase 12
implementation milestone.

| Milestone | Status | Outcome required to advance |
| --- | --- | --- |
| P12.7 — Consumer commissioning contract | **APPROVED DESIGN** | The [decision](phase12-7-decision.md) accepts the Safari/SoftAP experience, physical claim, browser owner model, generated credential lifecycle and recovery contract. |
| P12.8 — Commissioning foundation | **IN PROGRESS — IMPLEMENTATION OPEN** | Finish and vector-review [Owner-HTTP/1](../protocol/Owner-HTTP-v1.md) and [Consumer-Profile/1](../protocol/Consumer-Profile-v1.md), then implement the approved device-side claim, owner, identity-generation and atomic configuration/activation state machines with deterministic failure coverage. |
| P12.9 — Guided Safari/SoftAP setup | **BLOCKED ON P12.8** | Deliver one simple Safari setup flow that hides protocol, certificate and journal mechanics from the user. |
| P12.10 — RF-inhibited commissioning acceptance | **BLOCKED ON P12.9** | Commission Candidate A from the selected iPhone, reboot and prove Safari-owner plus station-side readback without RF. Record the actual generation: direct full commissioning from blank can be generation 1; an upgrade after the separate Wi-Fi-only bootstrap would be generation 2. |
| P12.11 — Ownership, recovery and fallback | **BLOCKED ON P12.10** | Accept additional-phone enrollment, owner loss, access recovery, provisioning reset, full erase and provisioned SoftAP fallback with unambiguous physical controls. |
| P12.12 — Stage A robustness and closure | **BLOCKED ON P12.11** | Close the remaining fault, trust, resource, concurrency, soak, controller-time, LED and restoration rows and complete the final adversarial review. |

### P12.7 Consumer commissioning contract

This milestone was discussion and documentation only. The operator approved
the complete [P12.7 decision](phase12-7-decision.md) on 2026-09-27, selecting
Safari and SoftAP only for consumer commissioning. P12.8 may now implement
that design, subject to its wire/storage and safety gates.
The operator previously approved a separate
[Wi-Fi-only network bootstrap design](phase12-wifi-only-bootstrap-proposal.md)
for a blank device on 2026-09-26. The [version-1 wire contract](../protocol/WiFi-Bootstrap-v1-proposal.md)
and [implementation prompt](phase12-wifi-only-implementation-prompt.md)
specify its network-only exception. Its first journal commit would be
generation 1; upgrading that device later to a full profile would be
generation 2. The devel source now includes the encrypted AP transaction and
network-only commit. The exact `fb091f8` image was flashed to Candidate A
and passed isolated-Pi open-AP preflight and selected-iPhone network-only
generation-one reboot readback on 2026-09-27; final phone-page and AP-return
rows remain open in the
[target record](phase12-wifi-only-physical-result.md). The later working
source keeps that AP available for Safari upgrade after station join; its
target AP/STA continuity is not covered by the installed-image result. This
exception does not close the consumer owner,
credential and recovery decisions in P12.7 or authorize P12.8–P12.12.
The [gated execution prompt](phase12-7-12-execution-prompt.md),
[Owner-HTTP/1 design](../protocol/Owner-HTTP-v1.md),
[Consumer-Profile/1 storage design](../protocol/Consumer-Profile-v1.md) and
[consumer contract proposal](phase12-7-consumer-commissioning-proposal.md)
record the accepted trust and recovery decisions. The
[decision record](phase12-7-decision.md) closes this design milestone, while
implementation and target acceptance remain open.
The [revised P12.7 proposal](phase12-7-consumer-commissioning-proposal.md)
replaces the Bluefy/BLE-owner draft with the approved Safari owner-key design.
It is not implementation or physical acceptance evidence.

The selected end-user journey must be no more complicated than:

1. Power on an uncommissioned WsprryPico.
2. Join its open SoftAP and choose **Set up this Pico** in Safari.
3. Confirm the physical device once when its LED identifies it.
4. Enter ordinary Wi-Fi and station settings and choose **Connect**.
5. Wait for **Setup complete** after activation and verified readback.

Ordinary commissioning must not ask the user for a MAC-derived password, full
device ID, USB-console command, PEM certificate, private key, profile JSON,
protocol session identifier or second password entry. Advanced service tooling
may retain explicit forms of those mechanisms, but it does not define the
consumer path.

The approved P12.7 contract selects:

- one prompted runtime BOOTSEL press/release, with no timed hold required of a
  person, bound to full device
  ID, exact Safari origin, browser owner key, boot and one request; the
  provisioned/core-1 safety proof remains a hard implementation gate;
- ordinary Wi-Fi and station fields, with advanced time, trust and protocol
  settings outside the five-step consumer flow;
- a per-device CA and server key generated on the Pico after checked entropy
  and UTC, with separately approved station-client CSRs and no user PEM work;
- a retained Safari owner key as consumer authority; the old application
  password and BLE bond do not become consumer ownership;
- an always-available open AP in network-only and consumer modes, encrypted
  owner traffic, one physical second-phone approval, explicit access recovery
  and distinct network/full reset ceremonies; and
- **Checking setup** through unknown results, with **Setup complete** only
  after exact owner, profile generation, station and trust readback.

The design exit gate is closed by the [P12.7 decision](phase12-7-decision.md).
The wire, storage, source, target and Stage A proof gates remain in the later
milestones; no user-visible security ceremony is left to implementation choice.

### P12.8 Commissioning foundation

The bounded [structural profile review](phase12-8-structural-foundation-review.md)
records a canonical parser, size and write-cut tests, and an inert journal
source that cannot grant legacy job control. It does not close this milestone;
owner routes, cryptographic validation, generated trust and safe provisioned
BOOTSEL remain open.
The [portable claim-slot review](phase12-8-claim-slot-review.md) adds one
physically bound claim state machine and completed-reset tombstone progression;
it is not connected to HTTP or target BOOTSEL sampling.
The [owner-wire review](phase12-8-owner-wire-review.md) adds a fixed signing
registry, one-use challenge, P-256 verifier and canonical session-finish
transcript with independent vectors. These remain disconnected from firmware
owner routes and do not close P12.8.
The [claim-wire review](phase12-8-claim-wire-review.md) freezes the claim AEAD
AAD/plaintext and distinct wire/decoded body limits. A browser-sealed vector
opens with the pinned Pico Mbed TLS adapter in host tests. The browser helper
is not yet served by the captive page, and the Pico opener is not yet called
by an owner HTTP route.
The [TLS material review](phase12-8-tls-review.md) adds on-device P-256
CA/server generation and persisted-material validation with host failure
tests and a Pico cross-build. Trusted-UTC admission, target resource and
latency measurements, claim-route use, journal commit and consumer activation
remain open.
The [claim admission and commit review](phase12-8-claim-admission-commit-review.md)
adds strict owner-request bounds and a disconnected, source-checked single
consumer-generation commit boundary. Live AP dispatch, trusted clock and
station adapters, source-5 boot activation and target acceptance remain open.
The [consumer pre-clock boot review](phase12-8-consumer-preclock-review.md)
records same-device source-5 structural selection, station time acquisition,
read-only AP recovery and explicit legacy transport/schedule denial. It does
not enable owner routes, validate persisted cryptography or activate source 5.
The [whole-gesture BOOTSEL source review](phase12-8-bootsel-window-review.md)
adds an opt-in RF-inhibited core-1 diagnostic and a bounded SRAM window. The
[target record](phase12-8-bootsel-window-target.md) observes a physical
press/release with core 1 active and AP recovery. The human press lasted
702 ms; its rejection by the installed image's 600 ms cutoff was a design
mistake, now removed in source. This is not yet wired to Safari or owner
claim; the older short-sample core-1 failure remains historical evidence.
The later [live claim preparation](phase12-8-live-claim-preparation.md) links
the AP claim route and local Safari page in source, with a bounded RF-inhibited
image and host/browser checks. No new Candidate A or iPhone acceptance is
recorded there; post-clock owner activation and private readback remain open.

Implement only the accepted P12.7 contract. The device must:

- advertise a clear uncommissioned/setup state without treating a name or MAC
  suffix as identity proof;
- bind one physical claim to the exact Safari origin, browser public key and
  request, then retain that key as owner only after the claim succeeds;
- create or install its device-specific TLS identity without asking the user to
  handle certificate or key material;
- establish the selected station-server trust and bounded advanced-client
  enrollment path without making certificate handling part of ordinary setup;
- accept the minimal user configuration as one validated transaction, preserve
  station/schedule/watermark data outside its scope and activate exactly once
  after the terminal response boundary;
- report an unambiguous committed generation and survive reboot selecting only
  the new complete generation or a fail-closed recovery state; and
- scrub transient Wi-Fi and cryptographic material on success, rejection,
  cancellation, timeout, disconnect and reboot.

Existing low-level passwords, proofs or profile records may remain internal
implementation details only if they add no user step and cannot grant authority
beyond the physically claimed browser owner. Hardware-free acceptance must cover
wrong-device, competing claimant, expired gesture, replay, interrupted journal,
activation failure, response-loss reconciliation and secret-free diagnostics.

### P12.9 Guided Safari/SoftAP setup

Safari must present one linear product flow rather than a protocol console:

- **Select device** joins the open AP and verifies the full device identity
  internally before using its full-ID-indexed owner key at the AP-local origin;
- **Confirm device** runs Identify and waits for the selected physical claim;
- **Connect** requests only the accepted Wi-Fi/station fields, validates them
  locally and submits the single commissioning transaction; and
- **Setup complete** appears only after generation, reboot/reconnect, device
  identity and network-readiness checks succeed.

The page must never display internal operation names or tell a normal user to
enter a default password, profile JSON, PEM data or USB command. It must use
locally bundled assets and persist only the proposed Safari owner private key
after its storage/readback gate; Wi-Fi and transient crypto secrets are cleared
on every terminal path. It must distinguish retryable transport loss from
committed-but-not-yet-reconciled state. The captive sheet may be a launch aid
but must not silently become the owner credential store.

Exit gate: deterministic browser/device conformance tests and an adversarial
review cover the happy path, every screen transition, back/cancel/reload,
Safari storage failure, wrong device/origin, gesture expiry, connection loss at each
transaction boundary, activation failure and safe retry.

### P12.10 RF-inhibited commissioning acceptance

Using a clean committed RF-inhibited image on Candidate A and the recorded
iPhone/iOS/Safari combination:

1. Start from the documented blank/uncommissioned state with no retained owner.
2. Verify the exact locally bundled Safari page and phone capability, then
   prove offline page use with infrastructure Wi-Fi and cellular disabled.
3. Select and Identify the exact device, perform the physical claim and complete
   setup without a console, manual identifier, default-password prompt, file
   import or certificate handling.
4. Enter ordinary Wi-Fi/station settings, commit the actual generation (1 for
   direct blank full setup or 2 after network-only generation 1) and preserve
   the terminal response before activation.
5. Reboot/reconnect and verify the same device, generation and retained owner;
   station association, DHCP/mDNS, controller time and positive mTLS WTP/HTTPS
   readback must agree with the committed configuration.
6. Confirm RF remains inhibited, the job service is empty/unowned, output is
   inactive and all unrelated journals and settings are preserved.

Repeat only the predetermined negative and interruption cases needed to prove
wrong-device rejection, competing claim exclusion, safe cancellation,
unknown-result reconciliation and old-or-fail-closed activation behavior.
Retain failures instead of rewriting them with retries.

### P12.11 Ownership, recovery and fallback

Finish the consumer lifecycle after first setup:

- enroll a second phone only after a fresh physical action and prove a nearby
  unconfirmed phone cannot claim or displace the owner;
- define bounded owner-key capacity, deliberate removal and replacement without
  silent eviction;
- recover from a lost phone without requiring the old phone, while preserving
  the operational profile during access recovery;
- make provisioning reset and full operational erase visibly distinct,
  resistant to accidental invocation and power-loss safe;
- verify post-reset advertisement, owner state, settings preservation/clearing
  and RF-inhibited restoration exactly match the selected reset level; and
- retain only the approved encrypted Wi-Fi-only mutation and read-only
  identity/status on the current blank AP until the approved P12.7 owner
  routes are implemented and independently accepted. Provisioned owner-control
  AP surfaces still need physical acceptance. Station TLS identity does not
  make Safari trust an AP certificate automatically.

Full Safari/SoftAP owner commissioning has the approved P12.7 design but still
requires P12.8–P12.12 implementation and acceptance. The separately approved
Wi-Fi-only network join does not
grant an owner, station trust, job control or RF authority; it protects the
submitted Wi-Fi credentials against passive AP listeners with a fresh key
exchange and accepts active page replacement/relay risk.
The [Wi-Fi-only network bootstrap proposal](phase12-wifi-only-bootstrap-proposal.md)
is the approved exception for the narrower task of joining a blank Pico to a
station network without an app or setup code. It does not establish owner, TLS
or job authority. The candidate attempts an
AP-local captive-browser launch on iPhone, with a fixed-address Safari
fallback; neither an automatic launch nor captive-sheet crypto capability is
assumed without target evidence. Implementation is approved subject to the
hard runtime BOOTSEL gate; target operations need separate exact authority.
The [Candidate A gate record](phase12-wifi-only-bootsel-gate.md) now includes a
failed physical press while core 1 continuously reads flash: USB/AP service
was lost and the RF-inhibited device rebooted into recovery. Credential POST
remains disabled. A later no-flash run on the standard image passed physical
press/release with concurrent AP traffic while core 1 was absent. The
physical-claim design is now narrowed to blank, RF-inhibited, core-1-absent
operation. The fail-closed source/link guards cross-build and are reviewed;
the later `fb091f8` guarded image was flashed for the bounded 2026-09-27
open-AP preflight, but its live physical press remains untested. The failed
core-1 row is not accepted.
The operator directed future image testing to
roll forward rather than routinely restoring an older UF2.
The next [source-only delivery review](phase12-wifi-only-foundation-review.md#source-only-asset-delivery-continuation-2026-09-26)
embeds the local browser bundle and streams its static assets in bounded
chunks. At that checkpoint the setup document and credential POST remained
disabled. The subsequent [transaction source review](phase12-wifi-only-transaction-review.md)
records their source implementation and remaining target gate. The later
`fb091f8` image passed the separate open-AP preflight, not the phone join.

The separate [blank read-only captive landing review](phase12-blank-captive-landing-review.md)
records a source-tested, RF-inhibited-image implementation of AP-only DNS and
safe HTTP redirection. It adds no credential input or station-join authority;
one Candidate A/iPhone run observed automatic launch and Safari fallback for
the original WPA2 read-only page. The later open-AP image passed passwordless
host association, and the operator reported passwordless iPhone association
and automatic captive launch. AP/STA behavior and the full Wi-Fi-only form
remain unaccepted target gates.

**Generic first-run cleanup:** the
[Candidate A blank-AP physical check](phase12-blank-captive-physical-result.md)
showed that an all-erased generic Pico selects the legacy factory-bundle source
and cannot expose the blank captive page until an explicit unprovisioned
selection is written. The
[bounded cleanup execution](phase12-generic-first-run-execution-prompt.md)
now selects generation-zero unprovisioned mode for an erased profile
journal in a generic image; matching device-bound compiled bundles retain
factory behavior, while mismatched or incomplete bundles and interrupted
first selections fail closed. Host tests and an RF-inhibited cross-build cover
this rule. The [Candidate A full-erase result](phase12-generic-first-run-physical-result.md)
accepted generation-zero unprovisioned selection and the passwordless
read-only AP without a seeded journal. The
[adversarial review](phase12-generic-first-run-review.md) records the repaired
findings and evidence limits. The later operator approval of the Wi-Fi-only
design does not make that earlier read-only image credential-capable or close P12.7.

### P12.12 Stage A robustness and closure

Complete the remaining RF-inhibited matrix after the consumer flow is stable:

- malformed, replayed, timed-out and interrupted requests at every transaction
  and journal boundary;
- superseded-trust rejection, credential replacement and reboot recovery;
- broader BLE control, TCP/WTP/HTTPS concurrency and one-`JobService` ownership;
- controller-time disagreement/recovery and complete LED priority/fault timing;
- heap, stack, lwIP/BTstack pools, TLS allocation, flash serialization, session
  reclamation and bounded soak; and
- final disconnected, provisioning-closed, SoftAP-stopped where applicable,
  empty/unowned, RF-inhibited, output-inactive and healthy-journal restoration.

Phase 12 closes only after the acceptance ledger maps every required Stage A
row to exact source, image, device, client and result evidence and a final
adversarial review finds no actionable issue. Stage B RF coexistence remains
separately authorized work, and Phase 13 remains the separate broad
band-by-mode-by-clock RF qualification phase.
