# Phase 12.3 hardware-free platform integration review

Status: bounded P12.3 infrastructure accepted by source, deterministic host,
sanitizer and cross-build evidence. Authenticated Pico BLE and SoftAP adapters,
idle-only live activation and all physical acceptance remain open. Phase 12 is
not complete.

Date: 2026-09-20

## Authority and evidence boundary

The work started on `devel` at
`c3ecc303db9dbcf68214e20c9b93f6889851aa6b`, initially equal to the local
`origin/devel` reference. The execution brief is
[phase12-3-execution-prompt.md](phase12-3-execution-prompt.md). This review
covers the complete attributable Phase 12 diff from that base; the commit and
remote-parity identities are reported after publication because a Git commit
cannot contain its own hash.

No Pico, fixture, USB device, radio, service, trust store, certificate
installer or physical endpoint was contacted. No host configuration was
changed. No BLE advertisement, SoftAP, Wi-Fi association, flash operation or RF
operation was performed. Source/test/cross-build evidence below is not physical
provisioning, timing, coexistence or RF evidence.

The retained Pico SDK is 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`, with Mbed TLS
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`, lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95` and recorded BTstack
`eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`. BTstack source is not populated
in the retained checkout, so no BLE target can be built from the pinned inputs.
The cross-build used the existing Arm GNU Toolchain 15.3.1 and SDK-selected
picotool `6f6458d792b93685a11423b244a585eaa99eafcf`.

## Implemented boundary

- A centralized 4 MiB layout reserves `0x3f7000`-`0x3fafff` for the two-slot
  profile journal, leaves standalone configuration/watermark records unchanged
  at `0x3fb000`-`0x3fefff`, and leaves the E10 sector at
  `0x3ff000`-`0x3fffff`. Every maintained image links below `0x3f7000`.
- `PicoProfileMedia` bounds all reads, 8 KiB slot erases and 256-byte programs
  to the new region. RF firmware uses SDK safe flash execution; the non-RF
  image retains its existing single-core interrupt exclusion.
- `RuntimeProfile` selects the build bundle only when no committed profile
  exists. A malformed, wrong-device or unhealthy committed profile is a fault;
  it does not restore build-time or older superseded trust. Provisioned Wi-Fi
  overlays only SSID, password and time server in a RAM copy, preserving
  station, schedules, expiry and watermark persistence.
- The TLS server receives stable credential views rather than reading generated
  arrays directly. After UTC synchronizes, the Mbed TLS validator checks exact
  device binding, parse, P-256 keys, SHA-256 signatures, key pair, one leaf and
  one CA, chain/validity, exact DNS SAN and server EKU before listening. Failed
  startup releases PSA, TLS and global listener ownership.
- Network-enabled builds now require a device-bound `.local` DNS identity.
  Manifest-less/IP-only bundles remain inspectable by the lifecycle tool but
  are rejected by the firmware configure gate rather than bypassing the exact
  runtime identity/SAN policy.
- The repository-owned Bluefy page uses fixed project UUIDs, exact
  device/generation identity, cryptographically random request/session IDs,
  64-byte ordered fragments, a 7,168-byte canonical bound, response
  correlation, timeout, cancel and disconnect cleanup. It neither stores nor
  logs credentials and clears displayed secrets on success, cancel and page
  exit.
- Nonsensitive runtime INFO exposes only provisioning source, generation and a
  numeric fault. It never exposes SSID, password, certificate, key or CA.

The page and portable manager deliberately do not fabricate transport
authorization. Target GATT and SoftAP services are absent and disabled. A
previously committed profile is activated at boot; live credential replacement
is not claimed.

## Deterministic validation

- The complete host regression passes 79/79 tests with the existing Xcode SDK
  selected through the process-local `SDKROOT`. The default Command Line Tools
  SDK 27 `.tbd` format is unsupported by the installed linker; selecting the
  already-installed Xcode SDK required no host change.
- The separate immutable Phase 11.7 guard runs four assertions. Its two
  reproducible-publication assertions fail exactly at `No later Pico
  production-runtime drift`; the other two pass. The guard was not relaxed and
  the Phase 11 result was not rewritten.
- AddressSanitizer plus UndefinedBehaviorSanitizer passes the provisioning,
  flash-layout, Web Bluetooth and standalone-image tests 4/4 after repair.
- WTP/1 validation passes 23 schema, seven raw JSON, one framing and eight
  transition cases.
- Mock-GATT tests cover unsupported Web Bluetooth, malformed/wrong identity,
  field and aggregate oversize, ordered fragments, duplicate response,
  non-boolean response, unchanged generation, timeout, cancel, disconnect and
  pending-request reclamation.
- Cross-links pass for `WsprryPico`, `WsprryPico-StandaloneRF`,
  `WsprryPico-RFBench`, `WsprryPico-RFWTP` and `rf_driver_linkcheck`, including
  existing heap-hook, stack-guard and RF-renderer placement checks. Text/BSS
  sizes are respectively 1,113,200/121,160; 1,126,108/276,324;
  192,664/279,012; 286,104/180,568; and 23,720/1,828 bytes.
- Both standard and standalone RF image checkers pass, and all four firmware
  maps report FLASH origin `0x10000000`, length `0x003f7000`.
- `git diff --check` passes. Credential-content scans and the final staged
  inventory are repeated immediately before publication.

## Adversarial findings and repairs

The first P12.3 review pass found and repaired:

1. Malformed identity or GATT setup failure could leave Bluefy connected.
   Connection setup now unwinds notifications, GATT and local state on every
   failure, with a malformed-identity regression.
2. The browser test called a per-field PEM overflow an aggregate-profile
   overflow, and its time-server checks were weaker than the C++ validator.
   Tests now exercise a true in-bound-fields/over-bound-total profile and the
   JavaScript validator rejects noncanonical numeric/multicast forms equally.
3. Page cancellation could race an in-flight provision promise, overwrite the
   cancellation message and re-enable a disconnected form. Completion now
   mutates UI state only for the still-current client.
4. Device responses accepted truthy non-boolean `ok`, and the client rejected
   a legitimate identical-profile no-op generation. Responses now require a
   boolean result and allow the current generation while rejecting rollback.
5. TLS validation/start failure retained global listener and initialized
   crypto ownership until object destruction. Every failed start now performs
   the normal teardown; a bad-then-good server regression proves reuse.
6. Candidate payload and flash-page copies retained avoidable secret bytes.
   Those buffers are explicitly cleared after read/program paths. This remains
   best-effort RAM clearing, not hardware key protection.
7. The journal initially could not distinguish an interrupted two-sector erase
   from a damaged newest commit. Recovery now uses structurally valid sequence
   metadata plus header/payload digest state: incomplete never-committed writes
   retain the prior generation, an older partially erased slot is ignored, and
   loss of the active commit sector fails closed instead of reviving older
   trust. Tests cover partial header, partial erase, commit interruption,
   ambiguous commit and active-commit loss.

The instrumented rerun then exposed an iterator-lifetime error in the new
pending-payload digest comparison. A single retained digest replaced two
temporaries; normal and sanitizer tests were rerun and pass. The final
reassessment found no further actionable defect within the hardware-free
boundary.

## Phase 11 assertion disposition

Phase 11.7 remains authoritative only for its recorded source pair and bounded
scope. This source change does not rewrite or promote that evidence.

| Assertion family | P12.3 impact and required fresh evidence |
| --- | --- |
| 11.1 TLS/browser/WTP | Host behavior passes, but a target candidate needs old/new CA rejection, restart/reload, replay and browser/controller interoperability. |
| 11.2 ownership/concurrency | Job/RF authority code is preserved; target BLE/SoftAP, flash lockout, service-gap, heap/stack/DMA and fault behavior require RF-inhibited repetition. |
| 11.3 identity/trust | Directly affected: repeat exact device/SAN/key/chain/validity, wrong-board, DHCP/mDNS recovery and superseded-client rejection on the operated image. |
| 11.4 inhibited acceptance | Historical only. The changed runtime image/layout needs the finite inhibited matrix and soak in the physical plan. |
| 11.5 resource/contention | Linked text and runtime validation changed. Repeat affected admission, network-loss, storage-lockout and reclamation assertions at the accepted 138 MHz/divider-1 baseline after adapters exist. |
| 11.6 conducted RF | No accepted/excluded row changes. Repeat only source-impact-affected coexistence rows under new finite authority; do not promote excluded rows. |
| 11.7 closure | Its expected drift failure proves it is not current-image evidence. Keep the immutable closure and attach new Phase 12 evidence separately. |

## Retained limitations and open decisions

- BLE proof of possession, bonding lifecycle, CA-rotation authority and
  permitted local-management operations are unselected.
- SoftAP activation/recovery, WPA, naming, timeout, post-success disable and
  captive-origin policy are unselected.
- The Bluefy page origin, release integrity, cache/offline policy and exact
  iPhone/iOS/Bluefy versions are physical acceptance inputs.
- CA/key generation location, private-key-at-rest protection, credential-only
  versus full reset and desktop trust enrollment remain open. Credentials in
  the profile journal are plaintext; the CA private key is not part of the
  profile and must not be placed on the device by default.
- JavaScript immutable strings and garbage collection prevent a guarantee of
  RAM erasure. Typed byte buffers and form fields are cleared best effort; the
  user must close/clear the Bluefy tab after use.
- The pinned BTstack source acquisition rule remains open. Adding it is
  dependency work and supplies no BLE acceptance by itself.
- The build-time `.local` requirement intentionally drops legacy IP-only
  firmware configuration from this candidate. Restoring that mode requires an
  explicit identity/SAN policy rather than a validation bypass.

The remaining gates are the selected security policies, pinned BLE dependency,
authenticated BLE and SoftAP target adapters, idle-only live activation, an
authorized execution of
[phase12-physical-acceptance.md](phase12-physical-acceptance.md), repaired
post-physical adversarial review and the separate Phase 13 qualification.
