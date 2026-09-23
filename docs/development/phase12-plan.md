# Phase 12 provisioning implementation and acceptance plan

Status: active. P12.1-P12.5 remain accepted within their documented
hardware-free scopes. P12.6 now production-enables BLE provisioning plus
authenticated controller time, Identify/status and an unchanged WTP/1 stream,
the network-only live activator and indicator construction in the RF-inhibited
standard image, a deterministic offline Bluefy release, and the production
SoftAP path. The SoftAP path includes the bounded project-owned DHCP
server on `192.168.4.1/24`, AP-interface mDNS, blank read-only HTTP, provisioned
pre-clock/normal HTTPS, password/cookie admission, controller time and the
existing browser/`JobService` API. Its final RF-inhibited Candidate A image now
has bounded native-Pi target evidence for WPA2 association, DHCP, mDNS,
device-bound TLS 1.3, wrong-password/cross-origin rejection, correct-password
cookie admission, same-connection controller time, status/capabilities,
`HELLO`/`CLAIM`/`RELEASE`, logout, reconnect and resource return. This is not
iPhone/Safari/Bluefy or credential-provisioning acceptance. Physical BLE
job-control/local-management beyond the bounded Raspberry Pi client exercise,
phone-time behavior, reset/gesture work and most physical acceptance remain
open. The clean committed standard image at
`d52a2fa6a3a3` has passed a serial-targeted load/verify plus an exact
RF-inhibited Candidate A/wspr5 native-client exercise for identity inspection,
authenticated controller time, field status and WTP `HELLO`/`STATUS`. The run
preserved station/schedule/watermark state and ended
empty/unowned/inactive-output. The later SoftAP physical continuation is
recorded in the
[RF-inhibited SoftAP review](phase12-softap-physical-review.md). Neither result
is Bluefy/iOS, RF or broad interoperability acceptance. The later BLE source
boundary is reviewed in
the [BLE local-control continuation](phase12-ble-local-control-review.md). The
bounded Pi/TCP slice is recorded in the
[Raspberry Pi BLE and first-class TCP/WTP review](phase12-pi-ble-tcp-review.md).
The
revisited P12.3 source slice remains
**CLOSED_SCOPED** by the [P12.3 closeout](phase12-3-review.md); the later
production work does not rewrite that evidence. The operator-selected
[field-access and security contract](phase12-field-access-contract.md) is the
controlling policy.
This plan does not authorize target, radio, service, trust-store, certificate-installation or RF
operations.

| Roadmap slice | Current position |
| --- | --- |
| P12.1-P12.2: profile journal and provisioning state machine | Accepted in their hardware-free scope. |
| P12.3: Pico adapter source | **CLOSED_SCOPED** for source, deterministic tests and RP2350 cross-links; not physical acceptance. |
| P12.4-P12.5: commands, delivery-safe activation and admission | Implemented and accepted in their hardware-free scope. |
| P12.6: production integration | **Partial.** BLE provisioning/local control and the SoftAP browser path are production-wired. The basic target SoftAP control path has bounded native-Pi evidence; SoftAP credential provisioning and reset administration are not implemented, and broad target acceptance remains open. |
| Physical Stage A | **Partial.** Candidate identity, adoption, preserved settings, BLE advertising, one online retained-bond Bluefy authorization exchange, a native-Pi BLE identity/time/status/HELLO/STATUS exercise and the bounded native-Pi SoftAP path passed within their recorded limits. Exact iPhone/Bluefy identity, offline reuse, fresh phone password, full credential activation, phone time, LED, reset/fault/trust/soak and stable-station AP-withdrawal rows remain open. |
| Physical Stage B / RF output | Not authorized or performed. Phase 13 remains separate. |

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
11. The selected iPhone BLE client is a Web Bluetooth provisioning UI opened in
    Bluefy; no WsprryPico-native iOS app is planned. The Safari-only path remains
    the SoftAP fallback. Bluefy and the delivered web page are explicit
    provisioning trust dependencies and must be identity/version-bound in
    acceptance evidence. A native Raspberry Pi/Linux BlueZ command-line client
    is an additional supported local/bench client using the same encrypted GATT
    service, full-device-ID binding, application authorization, provisioning
    transaction and unchanged WTP/1 stream. It does not replace or qualify the
    selected Bluefy/iOS acceptance path.
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

## Selected field-access/security policy

The operator selected the complete
[Phase 12 field-access and security contract](phase12-field-access-contract.md)
on 2026-09-21. It resolves the earlier product/security choices: BLE uses Just
Works with no PIN plus application-password enrollment; the shared default is
`wspr-<last-six-station-MAC-hex>` and is explicitly public; four bonds are
retained and revoked on password change; SoftAP remains a field-control and
recovery path; authenticated phone time supplies bounded offline UTC; the
onboard LED identifies a device and shows actual SoftAP readiness; sensitive
trust/reset work requires fresh password step-up and, while the default is
active, physical or USB confirmation; the CA private key stays off-device;
ordinary flash has no confidentiality claim; and every recovery level preserves
station, schedules and watermark unless full operational erase is explicit.

The first profile on a blank generic image is BLE- or explicit USB-local-only;
its SoftAP page is unauthenticated read-only identity/build/wire/status. After
device-bound server trust exists, first authenticated UTC may also arrive
through provisioned pre-clock SoftAP; normal SoftAP is an independent control
and replacement path. The access journal now occupies `0x3f3000`–`0x3f4fff`
and its all-erased, fault and reset-pending states fail closed.

Remaining questions are target integration details, not license to change that
policy:

- the exact safe Pico 2 W gestures for enrollment and the three reset levels;
- physical validation of blank bootstrap HTTP, Safari/Bluefy, cookie/session
  expiry, stable-station AP withdrawal and the broader controller-time/local-
  control matrix; the bounded native-Pi provisioned SoftAP path is accepted
  only as recorded in its physical review;
- a delivery-safe SoftAP provisioning/activation surface if credential transfer
  is to be supported there; the implemented SoftAP browser surface does not
  expose provisioning commands;
- physical validation of the implemented integrity-controlled offline Bluefy
  page-delivery/cache mechanism; and
- target resource, radio-coexistence and indicator scheduling needed to meet the
  selected behavior without weakening job/RF authority.

## Completion boundary

Phase 12 is not complete at the scoped P12.3 source closeout. Completion
requires physical BLE/SoftAP/HTTPS and local-control acceptance conforming to
the selected policy, a connected authenticated idle-only live activator, exact
gesture/reset selection, bounded inhibited-target acceptance, the remaining
authorized physical-plan execution and a repaired post-physical adversarial
reassessment.
Phase 13 RF qualification remains separate.
