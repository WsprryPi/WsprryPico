# Phase 12 P12.1/P12.2 hardware-free implementation review

Status: historical portable-slice checkpoint. P12.1/P12.2 pass their
hardware-free implementation and review scope. The later
[P12.3 hardware-free integration review](phase12-3-review.md) supersedes this
document for current roadmap status; every physical gate remains open.

Date: 2026-09-20

## Authority and source identity

Work began from a clean `devel` checkout. `HEAD` and the local
`origin/devel` reference were both
`c3ecc303db9dbcf68214e20c9b93f6889851aa6b`. At this checkpoint the work was
uncommitted on that branch. No reset, stash, checkout, commit, push or publication had been
performed. No Pico, fixture, radio, service, trust store or other physical
endpoint was contacted or changed, and no host configuration was changed.

The retained Pico SDK used for inspection and cross-building is 2.3.1 at
`079c6f39023649b154152db30f1d781e884879bc`. Its populated Mbed TLS and lwIP
sources correspond to `0bebf8b8c7f07abe3571ded48a11aa907a1ffb20` and
`77dcd25a72509eb83f72b033d219b1d40cd8eb95`. The SDK records BTstack
`eb0bb8b5ea6d234ccb940313b47f7a5c3b4e20ec`, but that source tree is not
populated in the retained checkout. The cross-build used Arm GNU Toolchain
15.3.1 and the SDK-selected picotool revision
`6f6458d792b93685a11423b244a585eaa99eafcf`.

## Implemented hardware-free slice

- `provisioning::Profile` provides exact, bounded JSON parsing and canonical
  serialization for the existing device identity, Wi-Fi/SNTP values, stable
  local hostname, TLS port, server certificate/private key and client CA. It
  reuses existing identity, hostname and standalone Wi-Fi validation.
- `provisioning::ProfileStore` provides a platform-neutral two-slot 16 KiB
  transactional journal. Payload, integrity header and commit marker are
  programmed in that order. An incomplete new slot falls back to the prior
  committed profile; a corrupt newest committed slot fails closed instead of
  reviving superseded trust.
- `provisioning::Manager` provides one BLE- or SoftAP-labelled session with
  authenticated/confidential/local admission, device binding, ordered bounded
  fragments, 30-second timeout, cancel, generation compare-and-swap, eight-entry
  five-minute replay retention and idle-only apply. Owner, armed, running,
  failed, output-active and output-unknown conditions reject apply.
- Staged and superseded credential buffers are explicitly cleared on success,
  failure, cancel, timeout, replacement and destruction. Status and replay
  records contain only identifiers, digests, counts and result metadata.
- The profile journal is separate from the existing 16 KiB station/schedule and
  no-repeat-watermark store. Tests prove that the existing store remains
  byte-for-byte unchanged across two credential generations and reload.

At this checkpoint the slice did not allocate Pico flash, validate through
Mbed TLS, select provisioned Wi-Fi/TLS or expose BLE/SoftAP. The P12.3 review
records the later flash/runtime/Bluefy infrastructure; transports and live
reload remain open.

## Deterministic validation

- The focused provisioning test covers BLE and SoftAP lifecycle labels,
  authentication/confidentiality/locality/principal rejection, wrong device,
  malformed/oversize/out-of-order/incomplete input, invalid cryptographic
  validation, exact duplicate, request-ID misuse, stale generation, timeout,
  cancel, replay capacity/expiry, fragment capacity, concurrent session,
  RF/job busy states, interrupted writes, ambiguous commit, corrupt newest
  commit, superseded-CA removal, resource reclamation and preservation of
  station/schedules/watermark. It passes normally and under AddressSanitizer plus
  UndefinedBehaviorSanitizer. Leak detection is disabled because the Apple
  sanitizer runtime does not supply it.
- The current host suite passes 77/77 tests when the immutable Phase 11.7 closure
  guard is excluded. The guard itself runs four assertions: the two reproducible
  publication assertions correctly fail with `No later Pico production-runtime
  drift`, while its other two assertions pass. The guard was not relaxed and
  no Phase 11 evidence was rewritten.
- WTP/1 validation passes 23 schema, seven raw JSON, one framing and eight
  transition cases.
- Formatting and `git diff --check` pass.
- Release cross-links pass for `WsprryPico`, `WsprryPico-StandaloneRF`,
  `WsprryPico-RFWTP`, `WsprryPico-RFBench` and
  `rf_driver_linkcheck`, including existing heap-hook, stack-guard and
  RF-renderer placement checks. Their text/BSS sizes are respectively
  1,069,360/120,984; 1,081,868/276,148; 286,104/180,568;
  192,664/279,012; and 23,720/1,828 bytes. These are build/layout results, not
  BLE, Wi-Fi, timing or RF evidence.

## Phase 11 evidence disposition

The Phase 11.7 closure remains authoritative for its recorded source and bounded
scope only. The Phase 12 plan records assertion-level impact:

- 11.1 identity/TLS/browser behavior requires fresh old/new-CA, reload and replay
  validation after runtime credential integration.
- 11.2 and 11.5 ownership, service-gap, heap/stack, storage-lockout, network-loss
  and reclamation assertions require fresh inhibited-target work after adapters
  exist.
- 11.3 hostname, SAN, device/key/chain/validity, DHCP/mDNS recovery and
  wrong-board rejection are directly affected.
- 11.4 physical evidence remains historical and is not rebound to new code.
- 11.6 retains all accepted, excluded, failed, blocked and unsupported rows. Only
  source-impact-affected coexistence rows may be repeated under new finite
  authority.
- 11.7 is cited as the historical closure record and is not modified into Phase
  12 evidence.

## Adversarial findings and repairs

1. The first apply-replay digest included transient job/RF activity. An exact
   retry after activity changed could therefore be misclassified as request-ID
   reuse. The digest now covers only client request content; busy-state
   evaluation remains part of first execution, and exact retries return the
   recorded result.
2. Parsed, canonical and persisted credential strings retained avoidable
   temporary or superseded copies. Profile, session, candidate and store
   terminal/destructor paths now clear those buffers, and tests plus sanitizers
   were rerun.

Reassessment found no further actionable defect inside the bounded portable
slice. Best-effort RAM clearing is not hardware key protection, persisted
credentials are not encrypted by this slice, and target resource/coexistence
claims are intentionally withheld until platform integration exists.

## Post-review selected decision

On 2026-09-20, the user selected Bluefy as the iPhone BLE client. Phase 12 will
provide a Web Bluetooth provisioning UI for Bluefy rather than a
WsprryPico-native iOS app. SoftAP remains the independent Safari fallback. The
Web Bluetooth page origin, release integrity and delivery/cache policy remain
acceptance inputs; selecting Bluefy does not implicitly approve an arbitrary
page or expand its access to provisioning secrets.

## Blocking product and security decisions

P12.3 target transports/live activation cannot be completed safely until the project selects:

- BLE proof of possession, bonding retention/deletion and CA-rotation authority;
- BLE local-management operations and their authorization, without creating a
  second job-control authority;
- Web Bluetooth page origin, delivery, release integrity and cache/offline
  behavior for the provisioning UI executed inside Bluefy;
- the SoftAP activation/recovery gesture, timeout, naming, WPA and post-success
  disable policy;
- credential/CA generation location and whether the RP2350 ever receives a CA
  private key;
- private-key-at-rest protection and recovery consequences;
- credential-only versus full-reset gestures, including BLE bond handling while
  preserving station/schedules/watermark by policy;
- operator enrollment and trust-store UX on supported desktop platforms; and
- a pinned BTstack source acquisition rule, because the retained exact SDK
  checkout does not contain that dependency.

## Remaining gates

Implement and review the authenticated Pico BLE and SoftAP adapters and
idle-only live activation. Then execute the finite RF-inhibited-first plan in
`phase12-physical-acceptance.md` under fresh explicit authority. Optional RF
coexistence follows only after source-impact review and a separately authorized
finite budget. Phase 13 qualification remains separate.
