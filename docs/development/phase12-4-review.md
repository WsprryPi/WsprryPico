# Phase 12.4 portable command and activation review

Status: the bounded P12.4 hardware-free command/activation tranche is implemented,
reviewed and accepted within this record. Phase 12 remains active. No target BLE
or SoftAP adapter, authenticated radio session, Pico live reload or physical
acceptance is claimed.

Date: 2026-09-20

## Authority and source identity

Work began from clean `devel` at
`8644e60f50a796b00768a3a35c40aad9cfb38056`, equal to the local
`origin/devel` reference. The execution contract is retained in
[phase12-4-execution-prompt.md](phase12-4-execution-prompt.md).

The work was limited to source, documentation, deterministic host tests and
cross-builds. No Pico, USB endpoint, BLE/Wi-Fi radio, physical network endpoint
or RF path was contacted. No firmware was flashed. No host radio, service,
trust store or certificate installation was changed.

The retained Pico SDK is 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`. Its Mbed TLS and lwIP
sources are `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` and
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`. The recorded BTstack
revision remains `eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`, but the
submodule is not populated. The cross-build used Arm GNU Toolchain 15.3.1 and
the already retained picotool source at
`6f6458d792b93685a11423b244a585eaa99eafcf`.

## Implemented boundary

- `provisioning::CommandAdapter` is the owned transport-neutral C++ decoder
  for the checked-in Bluefy version-1 `open`, `write`, `apply` and
  `cancel` commands.
- The command object is limited to 512 bytes. It uses closed operation-specific
  fields, raw 32-lowercase-hex identifiers, a signed-32-bit nonnegative wire
  integer bound and canonical base64 fragments decoding to 1 through 64 bytes.
  Escaped alternative spellings are rejected instead of normalized.
- The adapter returns correlated, bounded, nonsensitive version-1 JSON
  notifications. A malformed message without a trustworthy raw request ID gets
  no notification. Its identity value fails closed for an invalid configured
  device ID or an unrepresentable generation.
- Authentication, confidentiality, locality and principal assertions come from
  the future platform adapter. The manager rechecks them on every command and
  binds transport and principal into replay identity. A SoftAP path or another
  authenticated principal cannot continue a BLE session.
- Fragment payload copies are cleared after dispatch. The caller still owns the
  original command buffer; a future GATT/HTTPS adapter must clear its receive
  storage. This is best-effort RAM hygiene, not at-rest key protection.
- `ProfileActivator` is an optional post-commit handoff. It runs only for a
  genuinely new, validated generation after transactional persistence and the
  existing idle/output admission checks.
- Activation failure returns stable `activation_fault`, calls the explicit
  fail-closed hook, terminates and scrubs the session, and leaves the new
  generation authoritative. Replay does not invoke activation twice. An
  identical-profile replacement does not invoke activation.
- With no activator, the existing boot-only application behavior is unchanged.
  No Pico network stop/start/reload implementation is connected.
- A source drift test pins the Bluefy/C++ profile and fragment bounds, fixed
  service/identity/command/status UUIDs, operation names and field vocabulary.
- Host configuration now validates cached generated TLS test credentials and
  regenerates an expired or incomplete fixed-build-directory fixture. Deployment
  certificate validation and expiry policy were not weakened.

## Deterministic coverage

The provisioning tests cover the Bluefy-shaped BLE and SoftAP lifecycle,
identity/response correlation, exact duplicate replay, request-ID conflict,
wrong device, malformed/duplicate/extra/missing fields, wrong scalar types,
unknown operations, noncanonical escaped spellings, invalid identifiers,
command and fragment bounds, canonical base64 padding, offset/generation bounds,
fragment order, all authorization assertions and cross-principal/cross-transport
rejection.

They also retain timeout, cancel, concurrent session, replay capacity/expiry,
transaction interruption/recovery, corrupt-newest fail closed, superseded trust
removal, station/schedule/watermark preservation, owner/armed/running/failed and
output-active/output-unknown rejection, staged-buffer reclamation, activation
success/no-op/failure/fail-closed/replay and authoritative reload after an
activation fault.

## Validation results

- A clean Xcode-SDK-pinned host configure and build succeeded using the retained
  Mbed TLS/lwIP inputs.
- The final host regression run passed 80/80 tests with only the immutable
  Phase 11.7 closure guard excluded.
- The Phase 11.7 guard was run separately. Four assertions ran: its two
  reproducible-publication assertions failed with the expected
  `No later Pico production-runtime drift`; its other two assertions passed.
  The guard and historical result were not relaxed or rewritten.
- AddressSanitizer plus UndefinedBehaviorSanitizer passed the focused
  provisioning, flash-layout, Web Bluetooth, command-contract and standalone
  image checks, 5/5.
- WTP/1 validation passed 23 schema, seven raw JSON, one framing and eight
  transition cases.
- Cross-links passed for `WsprryPico`, `WsprryPico-StandaloneRF`,
  `WsprryPico-RFBench`, `WsprryPico-RFWTP` and
  `rf_driver_linkcheck`. Their text/BSS sizes were respectively
  1,113,200/121,160; 1,126,108/276,324; 192,664/279,012;
  286,104/180,568; and 23,720/1,828 bytes.
- Standard and standalone semaphore/UF2 image checks passed. All four firmware
  maps retained FLASH origin `0x10000000` and length `0x003f7000`.
- The initial aggregate host run omitted the SDK environment for tests that
  spawn their own compilers; three tests then selected incompatible newer
  Command Line Tools metadata. Exporting the configured Xcode SDK to child
  processes produced the clean 80/80 result. No source change or host
  configuration change was used to mask that toolchain selection.
- `git diff --check` passed. The staged inventory and credential-content scan
  are repeated immediately before publication.

These results are host and cross-build evidence only. They are not BLE, SoftAP,
Wi-Fi coexistence, live credential activation, timing, spectral or RF evidence.

## Adversarial findings and repairs

The first review pass found and repaired:

1. Canonical one-byte padded base64 such as `Zg==` was rejected. The decoder
   now accepts valid one- and two-pad endings while retaining pad-bit and
   placement checks.
2. Invalid base64 could leave a partially decoded secret buffer allocated, and
   the decoded base64 string copy was not explicitly cleared. Both paths now
   clear and release their temporary buffers.
3. An expired or incomplete cached generated TLS fixture could prevent a
   deterministic host rebuild. Configure now validates and regenerates only
   that fixed build-directory fixture; production validity checks remain intact.

The next adversarial pass found and repaired:

4. After `open`, later commands were not re-bound to the opening transport and
   principal. Every write/apply/cancel admission and replay digest now includes
   the supplied authorization and transport. Regressions cover unauthenticated,
   cross-principal and cross-transport attempts without state mutation.
5. The general JSON parser could decode escaped field, operation or identifier
   spellings into the accepted vocabulary. The provisioning wire adapter now
   requires the one raw canonical spelling and has explicit escape regressions.
6. An invalid configured device ID could still be serialized by the identity
   accessor. Identity now fails closed, and the fixed UUID and integer bounds
   are covered by the drift guard.

All affected normal, sanitizer, aggregate host, cross-link and image checks were
rerun after the repairs. The final reassessment found no further actionable
defect inside the bounded hardware-free P12.4 scope.

## Phase 11 assertion disposition

Phase 11.7 remains authoritative only for its recorded source pair and bounded
scope. This work does not promote or rewrite that evidence.

| Assertion family | P12.4 impact and required fresh evidence |
| --- | --- |
| 11.1 TLS/browser/WTP | The credential command and activation boundary are affected. Repeat old/new-CA rejection, reload/restart, replay and browser/controller interoperability on a target candidate. |
| 11.2 ownership/concurrency | Portable job/RF admission is retained. Target adapters require RF-inhibited service-gap, flash-lockout, heap/stack/DMA, transport-loss and fault checks. |
| 11.3 identity/trust | Directly affected. Repeat exact device/SAN/key/chain/validity, wrong-board, DHCP/mDNS recovery, principal binding and superseded-client rejection. |
| 11.4 inhibited acceptance | Historical only. The changed candidate needs the finite inhibited matrix and soak in the physical plan. |
| 11.5 resource/contention | Portable resource bounds pass. Repeat target admission, reclamation, storage/network loss and coexistence at the accepted 138 MHz/divider-1 baseline. |
| 11.6 conducted RF | No accepted, excluded or unsupported row changes. Repeat only source-impact-affected coexistence rows under new finite authority. |
| 11.7 closure | The expected drift failure proves it is not current-image evidence. Keep it immutable and attach Phase 12 evidence separately. |

## Open decisions and remaining gates

The following remain product/security inputs, not implementation details to
invent in this tranche:

- BLE proof of possession, bonding retention/deletion, recovery and CA-rotation
  authority;
- permitted BLE local-management operations without a second job-control
  authority;
- SoftAP activation/recovery gesture, timeout, naming, WPA and post-success
  disable policy;
- Bluefy page origin, release integrity, cache/offline policy and exact
  iPhone/iOS/Bluefy acceptance versions;
- CA/key generation location, private-key-at-rest protection and whether the
  RP2350 ever receives a CA private key;
- credential-only/full-reset behavior, bond deletion and preservation of
  station, schedules and the no-repeat watermark;
- desktop operator enrollment and trust-store UX; and
- a pinned BTstack acquisition rule.

Remaining implementation and evidence gates are the authenticated Pico BLE GATT
adapter, independent SoftAP/captive HTTPS fallback, a connected idle-only target
activator, an authorized RF-inhibited-first physical acceptance run, repaired
post-physical adversarial reassessment and the separate Phase 13 qualification.
