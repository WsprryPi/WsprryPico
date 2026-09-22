# Phase 12.3 hardware-free platform integration review

Status: **CLOSED_SCOPED** on 2026-09-21 for the hardware-free source,
deterministic-test and RP2350 cross-link boundary described here. The access
policy core, persistence, framing and candidate Pico BLE/SoftAP/indicator
adapters are implemented. They are not enabled as a production field-access
path. Live activation, complete target service wiring, exact physical gestures,
offline-page qualification and all physical acceptance remain Phase 12 gates.

## Authority and evidence boundary

This closeout resumed clean `devel` at
`cf6792258de2d2d1060a6ca9e22ac79f866ac06b`, initially equal to
`origin/devel`, while preserving the operator-selected field-contract
documentation already present in the working tree. The execution brief is
[phase12-3-closeout-execution-prompt.md](phase12-3-closeout-execution-prompt.md).
The selected policy is
[phase12-field-access-contract.md](phase12-field-access-contract.md).

No Pico, fixture, USB device, radio, service, trust store or physical endpoint
was contacted. No firmware was flashed; no BLE advertisement, SoftAP, Wi-Fi
association, certificate installation or RF operation was performed. The
results below are source, host-test, sanitizer, static-linked-image and
cross-build evidence only.

The cross-build used the retained Pico SDK 2.3.1 checkout at
`079c6f39023649b154152db30f1d781e884879bc`, the clean exact BTstack revision
`eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`, the already-retained picotool
source and the existing Arm GNU toolchain. The configure gate rejects a wrong
BTstack revision and any tracked or untracked BTstack worktree change.

## Accepted source boundary

P12.3 now contains the following hardware-free implementation:

- A portable local-access controller derives the public
  `wspr-<station-MAC-suffix>` default, owns single-use request-bound password
  and confirmation proofs, a 120-second enrollment window, one encrypted BLE
  connection, four retained authorized bonds, four SoftAP sessions, password
  replacement, epoch invalidation and persistent field mode. Strict station
  MAC parsing, full device binding, bounded values and fail-closed storage
  health are enforced.
- A two-sector, commit-last access journal occupies
  `0x3f3000`-`0x3f4fff`; BTstack owns `0x3f5000`-`0x3f6fff`; the profile
  journal remains `0x3f7000`-`0x3fafff`; standalone configuration,
  schedules and watermark remain `0x3fb000`-`0x3fefff`; and E10 remains
  `0x3ff000`. Every affected map ends application FLASH at `0x3f3000`.
- Profile persistence now records explicit legacy, runtime, unprovisioned and
  build-bundle source modes. Reset intent is durable and resumable across
  source selection, access reset, optional operational erase and verified bond
  erasure. A pending/corrupt/erased access record boots fail closed with station
  startup and scheduling suppressed until an authorized recovery path
  completes.
- Access recovery resets only access authority; provisioning reset additionally
  selects the requested profile tombstone/source; full reset additionally
  erases operational station/schedule/watermark state. Successful retry after a
  bond-erasure fault re-enables BLE only after the bond database verifies empty.
- The fixed 64-byte GATT frame format provides bounded bidirectional
  fragmentation/reassembly. The BLE command session requires encrypted admission
  and application-password promotion before it delegates to the existing strict
  provisioning command adapter. Delivery callback or the exported poll hook
  advances the P12.5 exactly-once activation timeout.
- The Pico GATT candidate uses one BLE connection, Secure Connections Just Works,
  bonding, 16-byte encryption keys, indication delivery and a stable peer token
  derived from the stored identity address/type rather than a reusable database
  slot.
- The SoftAP policy core supplies random boot/epoch-bound HttpOnly Secure
  cookies, idle/absolute expiry, one-session binding, owner-only terminal grace,
  strict Host/Origin/Fetch Metadata checks and the blank/pre-clock/normal
  admission surfaces. The Pico candidate supplies WPA2 SoftAP start/stop/readiness.
- The controller-time arbiter accepts bounded authenticated challenge inputs,
  computes uncertainty from the target monotonic bracket, arbitrates controller
  observations with SNTP and latches disagreement. Production SNTP observations
  now pass through that arbiter.
- The indicator controller implements authenticated, device-bound Identify and
  lower-priority slow SoftAP-ready blink patterns; the Pico candidate drives the
  onboard wireless LED.
- The repository-owned Bluefy page authorizes with the local password, frames
  commands, reassembles notifications, correlates responses, bounds input,
  handles timeout/cancel/disconnect and clears credential fields.
- The production image instantiates the access media/store and controller-time
  arbiter. Its boot gate uses access health and reset intent to suppress station
  startup and scheduled work fail closed.

## Deliberately unclaimed boundary

P12.3 does not claim an end-user path yet:

- The production image does not instantiate or start the candidate GATT,
  SoftAP/HTTPS admission or indicator controllers. The linkcheck proves exact
  source and dependency compatibility, not live service behavior.
- The P12.5 `ActivationPlatform` still has no production Pico implementation;
  live network quiesce/install/restart is not enabled.
- Full BLE field management through the existing WTP/browser job semantics and
  the SoftAP HTTPS listener/captive/pre-clock handoff still require production
  service wiring. The provisioning command vocabulary remains separate and has
  not been enlarged into a second job protocol.
- Exact safe gestures for enrollment and all three reset levels remain
  deliberately unselected implementation details.
- Offline Bluefy origin, integrity/cache behavior and the accepted
  iPhone/iOS/Bluefy versions require explicit physical acceptance.
- No BLE, Wi-Fi, controller-time accuracy, coexistence, resource-reclamation or
  RF assertion has physical evidence from this work.

Those items are Phase 12 integration and physical-acceptance gates; they do not
reopen this closed hardware-free P12.3 source slice.

## Deterministic validation

- The host build completes. The current suite passes **81/81** tests when the
  already-installed Xcode 26.5 SDK is selected through process-local
  `SDKROOT`; no host configuration is changed.
- The immutable Phase 11.7 guard runs four assertions: the two historical-record
  assertions pass and the two reproducibility assertions fail exactly at
  `No later Pico production-runtime drift`. The guard and closure record were
  not relaxed.
- The focused ASan/UBSan suite passes **6/6**:
  provisioning, field access, flash layout, Bluefy web behavior, provisioning
  contract and standalone image checks.
- WTP/1 validation passes 23 schema, seven raw JSON, one framing and eight
  transition cases.
- Bluefy browser tests pass independently. Both linked standalone image checks
  report application FLASH ending at `0x103f3000` with access, BTstack,
  profile, standalone and boot regions protected.
- Cross-builds pass for `WsprryPico`, `WsprryPico-StandaloneRF`,
  `WsprryPico-RFBench`, `WsprryPico-RFWTP`, `rf_driver_linkcheck`,
  `provisioning_pico_linkcheck` and `field_access_pico_linkcheck`.
- Text/BSS sizes in that order are
  1,130,304/121,580; 1,143,132/276,744;
  192,664/279,012; 286,592/180,568; 23,720/1,828;
  321,312/11,004; and 664,992/29,148 bytes.
- Symbol inspection proves the field link retains GATT start/poll, stable bond
  identity, SoftAP start, LED write, SoftAP HTTP login and controller-time
  submission. The production image retains Pico access read/erase/program and
  controller-time observation.
- `git diff --check` passes.

## Adversarial findings and repairs

The first review pass repaired these actionable issues:

1. A new SoftAP login could reclaim an active job owner's session. Reclamation
   now protects the active principal.
2. Custom-password enrollment accepted password only. It now accepts the
   selected fresh password **or** physical/USB confirmation model.
3. A completed Identify request could be replayed to restart its pattern.
   Completed request IDs now remain idempotent without restarting.
4. Access recovery initially stopped listener admission but could still start
   station networking. Erased, corrupt or reset-pending access state now
   suppresses station and scheduler startup.
5. A failed bond erase set `ble_disabled`, but a later verified reset retry
   did not clear it. Successful verified retry now clears the flag atomically.
6. Station-MAC parsing accepted unseparated and hyphenated values. It now accepts
   only the checked colon-delimited form and rejects multicast/zero identities.
7. A random SoftAP token collision could duplicate authority. Collision now
   fails closed without allocating another session.
8. SoftAP HTTP admission did not bind a cookie to one WTP session. First use now
   binds it and conflicting reuse is rejected.
9. Field-mode mutation accepted a broad Boolean authentication claim. It now
   consumes the same exact request-bound fresh proof/confirmation required by
   sensitive access mutations.
10. Controller-time challenge fields could allocate without bound. Principal,
    session and nonce values now have explicit printable 64-byte ceilings.
11. A lost apply indication or stopped GATT transport had no target poll seam to
    fire the activation timeout. BLE and GATT now export and retain that poll
    path independently of radio-running state.
12. The BTstack cleanliness gate ignored untracked files. It now requires an
    empty porcelain status in addition to the exact revision.
13. The standalone image checker still used the older `0x3f5000` boundary.
    It now rejects application content starting at the access journal boundary,
    `0x3f3000`.
14. Adding a SoftAP cookie to the general HTTP serializer changed immutable
    Phase 11 source evidence. Cookie emission was isolated in the new SoftAP
    response wrapper, restoring the Phase 11 serializer byte for byte.
15. Portable request, BLE link and SoftAP WTP-session identifiers were only
    nonempty before being copied. Printable 64-byte ceilings (32 bytes for the
    operation name) now bound those allocations, with oversize regressions.

The second assessment found that stored BLE authorization used a BTstack
database slot number, which can be reused for another peer. Authorization now
stores an identity-address/type token; deletion searches for that identity and
verifies the database count changed. The first rebuild then found one missing
adapter include, which was repaired. The full target set, host suite and
sanitizers were rerun. The final reassessment found no further actionable defect
inside the scoped hardware-free boundary.

## Phase 11 evidence disposition

| Assertion family | Disposition |
| --- | --- |
| 11.1 TLS/browser/WTP | Host regressions pass. Target old/new CA rejection, live reload and client interoperability require fresh Phase 12 evidence. |
| 11.2 ownership/concurrency | The single JobService/RF authority is unchanged. Live BLE/SoftAP contention and service-gap behavior require inhibited target evidence. |
| 11.3 identity/trust | Directly affected; repeat exact SAN/device/key/chain/validity, wrong-board, DHCP/mDNS and superseded-client rejection on the operated image. |
| 11.4 inhibited acceptance | Historical only. The changed runtime/layout requires the finite Phase 12 inhibited matrix and soak. |
| 11.5 resources | Host bounds pass and image sizes are recorded. Runtime heap/stack/session/reclamation and radio coexistence require target evidence. |
| 11.6 conducted RF | No row is promoted or changed. Repeat only source-impact-affected coexistence rows under fresh finite authority. |
| 11.7 closure | Remains immutable historical evidence; its expected drift failure is recorded, not suppressed. |

## Remaining Phase 12 gates

Phase 12 remains active. Closing it requires production service/activator wiring,
exact gesture selection, an integrity-controlled offline Bluefy delivery
mechanism, an exact candidate revision/UF2, and authorized execution of the
[RF-inhibited-first physical plan](phase12-physical-acceptance.md). Physical
results must then receive their own adversarial assessment. Phase 13 release,
timing, spectrum and broad RF qualification remain separate.
