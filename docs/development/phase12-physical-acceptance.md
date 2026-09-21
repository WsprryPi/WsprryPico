# Phase 12 finite physical acceptance plan

Status: plan only; unexecuted. No authority to contact a Pico, fixture, radio,
service or physical endpoint is granted by this document.

## Purpose and evidence boundary

This procedure qualifies Phase 12 transport and credential behavior only after
the portable implementation, Pico adapters, security policy and exact candidate
image have passed hardware-free review. It begins with RF-inhibited firmware.
It does not reopen or silently extend Phase 11.6, and it cannot establish Phase
13 timing, spectrum, band/mode/clock or release qualification.

## Current admission state

The [P12.3 hardware-free review](phase12-3-review.md) supplies candidate source
for the disjoint profile layout, boot-time runtime selection, Mbed TLS validator
and Bluefy page. It does not admit this procedure. The retained SDK checkout has
no populated BTstack source; authenticated target BLE/SoftAP adapters, live
activation and the listed security/recovery policies remain open. No exact
operated UF2, device, iPhone/Bluefy combination, page origin or physical budget
has been authorized or recorded. Stage A therefore remains wholly unexecuted.

## Admission record

Before any operation, record and independently verify:

- clean source revision, pinned SDK/toolchain/submodule revisions and complete
  configure options;
- exact board/serial/device ID/station MAC, previous firmware and candidate UF2
  hashes, boot ID and flash-layout report;
- exact iPhone model/iOS version, Bluefy App Store identity/version, and the
  Web Bluetooth page origin, revision/hash, delivery mode and effective cache
  state;
- explicit authorization for the named device, BLE and Wi-Fi radio operation,
  SoftAP creation, credentials, trust-store actions, reboot/flash actions and
  finite duration;
- authoritative inactive output, empty/unowned job state, disabled schedules,
  healthy configuration/profile/watermark journals and backed-up recoverable
  nonsecret metadata;
- a credential-free evidence directory and a cleanup/restoration plan armed
  before the first mutation.

Any missing identity, unknown output state, unhealthy store, unexpected running
service, source drift or unapproved trust/radio action stops the procedure.

## Stage A: RF-inhibited-first functional matrix

Use the standard RF-inhibited image. Bound each case and retain failures rather
than replacing them with retries.

1. Confirm no provisioning advertisement/SoftAP outside its selected activation
   policy. In the exact recorded Bluefy/iOS combination, load the identity-bound
   Web Bluetooth page and exercise authorized BLE activation, exact identity
   display and authenticated connection.
2. Provision Wi-Fi plus generation A TLS credentials through Bluefy. Verify committed
   generation, reboot persistence, station association, DHCP/mDNS identity,
   mTLS WTP/HTTPS and browser API behavior. Never record secret payloads.
3. Repeat negative BLE cases: wrong device, wrong proof, malformed, oversize,
   duplicate, replay, interruption, timeout, cancel, competing session and
   rejected unapproved page origin/version.
4. Exercise the SoftAP/Safari fallback only through its authorized recovery
   trigger. Repeat the positive and negative core cases, captive-flow origin/authority checks,
   radio timeout and cleanup. Confirm the AP is gone after exit/reboot policy.
5. Replace generation A with B under the selected policy. Prove B works and A is
   rejected for both controller and browser principals. Interrupt a B-to-C
   replacement at each journal stage and prove the documented old-or-fail-closed
   result without trust resurrection.
6. During external ownership, loaded, armed, running-simulated, failed and
   output-unknown states, attempt apply/cancel/recovery. Prove provisioning never
   aborts, releases, clears a fault or infers inactive output.
7. Verify station, schedules and no-repeat watermark before and after success,
   cancel, timeout, failed write, reboot and recovery. Exercise the selected
   credential-only and full-reset gestures separately.
8. Run bounded concurrency and soak with BLE advertising/management, station
   association, SNTP, mDNS, TLS WTP and HTTPS. Record heap, largest allocation,
   stack guards, lwIP/BTstack pools, TLS allocation, flash operations, session
   counts, timeouts and resource return.

Stage A must end with RF inhibited, output authoritatively inactive, no owner,
provisioning closed, SoftAP stopped, intended network/trust state restored and
all journals healthy. A disconnect or reboot is not restoration evidence.

## Stage B: separately authorized RF coexistence

Stage B is optional and requires new explicit RF authority plus a source-impact
assessment against Phase 11.5/11.6. Use the accepted 138 MHz/divider-1/GP2
configuration first. Freeze RF path, attenuation, receiver settings, credentials,
network and clock for comparison.

- Repeat the affected Phase 11.5 admission, service-gap, poll, heap/stack,
  TLS/network-loss, storage-lockout and resource-return assertions with BLE idle,
  BLE management active and the bounded SoftAP fallback state selected by policy.
- Exercise only predetermined finite inhibited/simulated cases before any finite
  RF job. Provisioning writes remain rejected while RF is owned/armed/running.
- If finite RF is authorized, cap jobs and RF seconds in advance, use accepted
  rows only for coexistence comparison, preserve failures and stop on timing,
  underrun, output-authority, memory, trust or restoration failure.
- Do not promote excluded Phase 11.6 rows or claim a new clock/mode/band. Any
  timing-path, allocator/layout or clock change triggers the documented wider
  revalidation instead of evidence reuse.

## Pass and stop rules

Pass only when every admitted assertion has identity-bound evidence, no secret
material entered the repository/evidence, all resource limits return within the
predeclared gates, superseded trust stays rejected, persistent noncredential
state is preserved and final output/network/provisioning state is authoritative.

Stop immediately for output-unknown, unexpected RF, wrong device/boot/image,
storage ambiguity, trust resurrection, memory/stack/DMA fault, unauthorized
radio/trust action or exhausted finite budget. Preserve the failed attempt and
restore only through the preauthorized path.

## Required result artifacts

Publish a credential-free machine-readable result plus adversarial review with
the exact source/image/dependency/board/boot/configuration identities, authorized
budget, every attempt and failure, journal generations, resource extrema,
restoration evidence and the Phase 11 assertions considered applicable or
requiring repetition. Credentials, Wi-Fi secrets, private keys, raw authenticated
traffic and trust-store exports remain private and out of Git.
