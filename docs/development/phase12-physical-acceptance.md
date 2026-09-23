# Phase 12 finite physical acceptance plan

Status: Stage A partially executed on 2026-09-22 under separate live operator
authority. Candidate identity/adoption, RF-inhibited boot, preserved operational
state and BLE advertising passed on the exact device below. One online
retained-bond Bluefy application-authorization exchange was subsequently
observed on Candidate A after the CCCD repair. Exact iPhone/iOS/Bluefy
versions, offline-cache, provisioning/activation, phone controller-time,
the remaining SoftAP matrix, reset/gesture and soak acceptance remain open. A
bounded native-Pi BLE exercise has separately passed device identity,
controller time, field status
and WTP `HELLO`/`STATUS`; a later native-Pi run passed the bounded provisioned
SoftAP association/DHCP/mDNS/HTTPS/time/status/ownership/reconnect path. Neither
is an iPhone/Bluefy result. Stage B is not authorized. The earlier repaired
clean committed standard image at
`5afe7576f001` passed a serial-targeted load/verify, exact post-boot identity,
preserved-state checks and final RF-inhibited empty/unowned/inactive-output
restoration. That baseline does not accept any newly added BLE operation.

## Purpose and evidence boundary

This procedure qualifies Phase 12 transport and credential behavior only after
the portable implementation, Pico adapters, the selected
[field-access/security policy](phase12-field-access-contract.md) and exact
candidate image have passed hardware-free review. It begins with RF-inhibited firmware.
It does not reopen or silently extend Phase 11.6, and it cannot establish Phase
13 timing, spectrum, band/mode/clock or release qualification.

## Current admission state

The production-integration tranche enables the GATT service, network-only
activation platform and indicator controller in the standard RF-inhibited
image. It retains one CYW43 owner and supplies the repository-owned offline
Bluefy release. Later continuations production-connect authenticated controller
time, Identify/status, an unchanged BLE WTP/1 stream and the independent
SoftAP DHCP/mDNS/HTTP/HTTPS browser/control path. The BLE subset has the bounded
native-Pi evidence described above. SoftAP has hardware-free build/test evidence
plus the bounded native-Pi physical evidence recorded in the
[SoftAP review](phase12-softap-physical-review.md). Credential provisioning and
reset administration are not production-wired.

The operated candidate is Pico 2 W USB serial `0BF4B4AEC9FFB344`, device ID
`fd6127d11d6aca42a9905fa3fb1bf1d5`, station MAC
`88:a2:9e:0a:60:df`, suffix `0a60df`. The comparator
`CDDBF8767C506C07` was identified but not modified. The first candidate build
was based on `7451a4047677-dirty`; its UF2 SHA-256 was
`8ea4121ebf81cccb1cdaeaae61243f092d4e0acbe1fe89f4d24c7acb8232767b`.
The linked application ended exactly at `0x103f3000` with a 16 KiB primary
stack.

The earlier clean restored baseline was source commit
`5afe7576f0016ef3e927090c15232ac5c8daeb4f`, firmware identity
`5afe7576f001`, with UF2 SHA-256
`112f798233e12f2e9b7b049412ab428346b9fb1fc734915e823d1cb84feb7c12`.
Serial-targeted picotool load and verification completed `OK`. Boot ID changed
from `bb9ab0b52c02b3ddde46b5150cadd449` to
`e7e8854f51789fb1aef53281c817d588`; the device again reported
`inhibited-standalone-simulator`, empty/unowned and `output_active=false`.
Access generation 2, factory profile generation 0, station `AA0NT/EM18/20`,
the 120/0 schedule, watermark `1789607761000000000`, configuration journal
sequence 72 and watermark journal sequence 12 were preserved. Storage remained
healthy, BLE was running and disconnected, and all new WTP counters were zero.
This is clean-image identity, preservation and restoration evidence only, not
functional acceptance of controller time, Identify or WTP over BLE.

The latest operated candidate is clean source
`0ecf9c170384fd2cc3ba802515e1d2c1396ab9fa`, firmware identity
`0ecf9c170384`, and UF2 SHA-256
`6261e322884a280afcd997537d6248fbbf0033b879fab1b2a661acd3a3575e23`.
Serial-targeted load/verify passed. This image retained factory profile
generation 0, healthy access generation 3, station `AA0NT/EM18/20`, the 120/0
schedule, watermark `1789607761000000000`, configuration sequence 72 and
watermark sequence 12. The target passed bounded WPA2, DHCP, mDNS, TLS 1.3,
password/origin/cookie, controller-time, status, `HELLO`/`CLAIM`/`RELEASE`,
logout, reconnect and resource-return checks without `LOAD`, `ARM` or RF. The
native-Pi result does not accept any phone-dependent row. After cleanup and
reboot, automatic fallback remained applicable because the preserved factory
station configuration was unavailable; stable-station AP withdrawal remains
open.

On the original dirty production candidate the standard image reported
`inhibited-standalone-simulator`, empty/unowned and
`output_active=false`. USB-local adoption produced healthy access generation
1 with the public default active and enrollment closed. Station
`AA0NT/EM18/20`, the 120-second schedule, and watermark
`1789607761000000000` were preserved. A first advertisement attempt exposed
empty data because BTstack retained pointers to temporary buffers; after moving
those buffers into transport lifetime, a bounded wspr5 scan observed
`WsprryPico-0a60df` with the selected service and public BLE controller
address `88:A2:9E:0A:60:E0`. That failed attempt is retained, not replaced.

The verified online Pages release and one successful application-authorization
exchange are recorded, but the exact iPhone/iOS/Bluefy versions and effective
offline cache remain unverified. No Wi-Fi/TLS profile or other post-selection
mutation was submitted, and broader Bluefy acceptance is still open. The
credential-free result and review are
`phase12-production-acceptance-result.json` and
`phase12-production-acceptance-review.md`.

## Admission record

Before any operation, record and independently verify:

- clean source revision, pinned SDK/toolchain/submodule revisions and complete
  configure options;
- exact board/serial/device ID/station MAC, previous firmware and candidate UF2
  hashes, boot ID and flash-layout report; separately identify and hash every
  noncandidate fault-injection image or harness and its enabled injections;
- exact iPhone model/iOS version, Bluefy App Store identity/version, and the
  Web Bluetooth page origin, revision/hash, delivery mode and effective cache
  state;
- each access sector's erased/nonerased state plus redacted format, generation and
  CRC validity before initialization or reset testing; keep any raw sector hash
  private and outside the credential-free evidence because it can verify a
  guessed password offline;
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

Use the exact candidate standard RF-inhibited image for every claim about
production behavior. A separately built, separately hashed RF-inhibited
fault-injection image or external harness may be used only for named
unreachable storage, identity, timing, output-state and network-activation fault
branches. Record that evidence as fault-path evidence, never as candidate-image
or RF evidence.
Bound each case and retain failures rather than replacing them with retries.

1. Verify full device ID, station-MAC-derived names and the illustrative
   default on the recorded board. With the admitted fault harness, inject a
   missing/invalid MAC read and prove no substitute suffix, BLE advertisement/
   enrollment or SoftAP starts; USB reports the identity fault and a later valid
   checked read recovers. Rotate or randomize the BLE and SoftAP interface
   addresses and prove every suffix/name remains derived from the station MAC
   and an interface-address change never authorizes a mutation. With the admitted
   fault harness, use colliding synthetic suffixes and different full IDs to
   prove cross-device authentication
   and mutation fail. Prove new-bond enrollment is closed outside its 120-second
   window. Under the public default, prove every window is physically or USB
   confirmed. Under a custom password, prove deliberate device-local action or
   an already-authorized session with fresh password step-up may open the window,
   while a retained bond alone cannot. Prove sensitive password/trust/bond/reset
   operations under the public default need fresh physical/USB confirmation and
   under a custom password need fresh step-up. Returning-bond discoverability
   alone grants no principal.
   Verify both UIs and status warn while the public default is active. Accept
   custom-password lengths 8 and 63, reject 7, 64 and unsupported/control
   characters transactionally, never disclose entered/custom values, and prove
   the upstream station-network password remains unchanged.
2. Exercise LE Secure Connections Just Works, full-device display, default and
   customized passwords, returning bonds, the four-bond limit and revocation.
   Verify the same current local-access password is used for new-bond application
   authorization, SoftAP WPA access and SoftAP application login while remaining
   distinct from station Wi-Fi and TLS identities.
   Prove the one-active-GATT-connection limit returns busy without displacement
   or bond mutation. Prove no silent eviction and that wrong password, timeout,
   disconnect or cancellation deletes a provisional bond. Inject deletion/epoch-
   store failure and prove **all** BLE local control remains disabled until
   physical recovery. Through a separate authorized management path, remove the
   current idle bond and prove its next command is rejected, a bounded revocation
   result is delivered when possible, the connection closes and reconnect is
   rejected. While that bond owns loaded, armed or running work, prove removal
   returns busy with no side effect; transport closure retains ordinary WTP
   lease/lifecycle behavior.
3. Capture the negotiated ATT payload and separately exercise the bounded
   provisioning transaction and full WTP framing/reassembly through maximum
   payloads. Prove the BLE bond principal, SoftAP session-token principal and
   certificate principal remain distinct, all job operations use one JobService,
   and a path change cannot transfer/resume/release ownership without the exact
   original principal/session authority.
   Separately prove one provisioning session/staged profile, 7,168 profile bytes,
   512-byte commands, 256-byte status notifications, ordered fragments, the
   30-second no-progress timeout and eight replay digests retained five minutes.
   Verify staged secrets are scrubbed after every terminal path.
4. With station Wi-Fi and cellular data disabled, load the exact offline Bluefy
   artifact. On the client/evidence side verify its approved origin, hash and
   visible version, absence of unapproved remote scripts/analytics/credential
   services and clearing of temporary secrets; do not claim the Pico can observe
   browser provenance. On the target, reject unsupported wire-protocol versions
   plus wrong suffix/device,
   password, malformed, oversize, duplicate, replay, out-of-order, interrupted,
   timed-out, cancelled and competing requests.
5. Through authenticated BLE and, separately, provisioned pre-clock SoftAP,
   seed UTC from the phone and verify nonce/device/principal/session/monotonic
   binding, the fixed 250 ms phone allowance, full round trip, local margins,
   2025-2099 range, 500 ms maximum uncertainty, refresh no slower than 60 seconds
   and the 90-second ARM-age gate. Reject stale, replayed, wrong-device, wrong-
   session, nonmonotonic and over-budget observations. Suspend/close the page and
   prove age and uncertainty continue growing until new admission fails. Verify
   overlapping same-principal refresh, nonoverlapping same-principal disagreement,
   different-principal `time_source_busy` while the source remains valid, takeover
   only after it ages invalid and two-controller-sample recovery. Verify valid-
   overlap phone-to-SNTP promotion, lower-priority phone noninterference while
   SNTP is valid, nonoverlap disagreement latching, rejection of new ARM/launch/
   schedule admission until two-SNTP-sample recovery, reboot-unsynchronized
   behavior and large forward/backward effects on loaded/armed/running jobs and
   the watermark. Confirm phone time reports `leap=normal` plus source, sample
   age, uncertainty and disagreement state. A correction may revalidate a merely
   loaded job, must make an armed not-yet-active job `missed` with output
   disabled when its launch is no longer valid, and must never retime or stop
   an already running job.
6. From a blank generic image, provision generation A Wi-Fi, time-server and TLS
   material through authenticated BLE (and separately the documented USB-local
   path if admitted). Verify committed source mode, reboot persistence, station
   association, DHCP/mDNS identity and station-interface mTLS WTP/HTTPS. Interrupt
   every profile/source-mode journal stage and prove old-or-fail-closed behavior
   without legacy Wi-Fi, build-trust or superseded-CA resurrection. Inspect the
   admitted bundle/image and prove the per-device CA private key is absent while
   the intended server key/certificate and client CA are present. Starting with
   both access sectors erased, prove identity/MAC/output checks and new live
   physical/USB confirmation precede the first access record and radios. Verify
   the successful record contains the selected format/adoption magic, access
   epoch 1, derived default, empty authorization index, field mode false and no
   reset intent. After customization, erase both sectors and prove the identical
   all-erased state again permits no radio or default until a new confirmation.
   Interrupt each initialization erase/program/commit boundary and prove any
   non-erased invalid remainder latches recovery-only access fault rather than
   being treated as all-erased. Never record secret payloads or private keys.
7. With no infrastructure network, prove a blank generic SoftAP bootstrap exposes
   only read-only full identity, build/wire version and nonsensitive status at
   `http://wsprrypico-<suffix>.local/`; it accepts no password, controller time,
   first-profile upload or job/control mutation. Verify DHCP and mDNS reach that
   exact manual-Safari route without DNS interception; any captive sheet accepts
   no credential and only directs the operator to Safari. After a valid device-
   bound TLS identity exists and public server trust is explicitly enrolled,
   verify `https://wsprrypico-<suffix>.local/` provides provisioned pre-clock
   server authentication, password login and controller time without a client
   certificate, while station HTTPS and raw TLS-WTP still require mTLS. Reject
   wrong CA, DNS SAN, Host/Origin and every certificate warning. Prove a same-
   suffix evil twin obtains no reusable credential, WPA association alone grants
   no application status/control principal, and the provisioned pre-clock
   service rejects profile/password/bond/trust mutation and all job control
   until ordinary authenticated services admit them.
8. For the SoftAP login, prove at least 128 random token bits, Secure/HttpOnly/
   SameSite=Strict session-cookie delivery, no URL or script-readable-storage
   exposure, per-login principal separation, 15-minute inactivity and the fixed
   12-hour ordinary-authority deadline, same-token reconnect, and invalidation on
   successful logout, password change, recovery and reboot. At the deadline,
   prove an empty/loaded token expires normally; an armed/running exact session
   enters owner-only grace permitting only event delivery, STATUS, ABORT and
   same-principal controller-time observations bound to the same device/session.
   With an accelerated deadline and an already armed future launch, prove valid
   refresh no slower than 60 seconds preserves the 90-second source-age rule and
   permits the already admitted launch; reject wrong-principal, wrong-session,
   stale and replayed observations without admitting a new ARM or schedule.
   Reject LOAD, ARM, configuration, provisioning, access administration and new
   WTP sessions during grace, then invalidate immediately at terminal. After
   HELLO, prove a token maps to one exact WTP session; a refresh, including
   during owner-only grace, reattaches only after authoritative STATUS and never
   creates or chooses a replacement session. Prove valid-session
   password step-up retains its token/principal and cannot silently replace an
   owner-bearing session. Fill all four session slots, prove a fifth returns busy
   without eviction, and prove reclamation after every invalidation path. Before
   the absolute deadline, suspend the page beyond 15 minutes during an armed/
   running job and prove same-token resume; at terminal prove the inactivity
   timer restarts and expires the token after 15 minutes idle. A merely loaded
   job still expires and aborts/releases under its ordinary 5–60-second WTP lease.
   Prove logout returns busy while loaded, armed
   or running and succeeds only after ABORT or a releasable terminal state. Then
   lose the cookie and prove the job follows ordinary WTP lease/lifecycle without
   ownership transfer and only the existing local trusted safety ABORT through
   the physical Console or explicitly authorized USB-local recovery adapter can
   stop it. Repeat Host/Origin, content type, request-header, Fetch Metadata,
   wrong-token, cross-principal, CSRF and replay negatives.
9. Exercise immediate no-profile SoftAP, at-most-60-second station fallback and
   explicit field mode. From an authorized non-SoftAP session, request the AP and
   prove one 120-second ready-state join/login grace; a duplicate returns busy
   without extension, login replaces it with token retention, expiry stops the AP
   only when station is stable and no other cause remains, and reboot clears it.
   Prove fallback remains while station is unavailable and stops only after 30
   seconds of usable station service, no live ordinary/owner-grace token, join
   grace or reply, and no other AP cause. Recover station while a
   page is suspended and prove its valid owner token retains the AP through
   loaded/armed/running work; loaded work still follows its ordinary WTP lease.
   Prove the runtime fallback cause is reevaluated rather than persisted at
   reboot. Prove field mode has no inactivity expiry, persists across reboot until
   explicit exit, and other no-profile/recovery causes still control AP state.
10. Verify the slow SoftAP heartbeat (200 ms on, 1800 ms off) and authenticated
    Identify pattern (three 150 ms pulses followed by 1250 ms off, repeated five
    times). Prove Identify priority, duplicate nonextension, concurrent busy,
    core-0-only checked LED writes and error reporting without RF/job side effects.
    Prove reboot cancels Identify, requested/starting/failed SoftAP never shows the
    ready heartbeat, and completion recomputes actual AP readiness before choosing
    heartbeat or Off.
11. Replace generation A with B under fresh-password step-up. Prove every proof
    and physical/USB confirmation is device/principal/session/operation/nonce
    bound and also binds the exact canonical operation parameters, current
    profile/access generations, staged-profile digest, bond/reset/password target
    and boot ID. Prove it is single-use and at most 120 seconds. A BLE GATT
    disconnect must invalidate it. For SoftAP, prove the fresh password travels
    in the exact mutation request, a separate confirmation binds to the logical
    cookie session/request digest, routine one-request TCP close does not cancel
    an admitted mutation, and cookie loss/logout/cancel/reboot/timeout/replay or
    wrong-operation use invalidates authority. Under the public default, reject
    missing confirmation; under a custom password accept fresh entry but reject
    a retained bond alone. Hold response delivery pending after commit and prove
    the admission gate accepts no new A- or B-generation network principal,
    invalidates other existing network principals and permits only the applying
    transport's terminal response. Drop that response and prove one activation
    after the five-second timeout. After activation, prove B client credentials
    are accepted, A client credentials are rejected and the Pico serves only B's
    server certificate/key. Record separately that the iPhone may still trust
    A's public server CA until independently authorized removal, expiry or
    revocation; do not report that phone-side state as Pico dual trust. Replace
    time peer A with B, prove commit invalidates A's observation, DNS result and
    pending callback, ignore delayed A traffic, retain a valid controller source
    under its normal rules or become unsynchronized, and accept B observations
    only after activation. Interrupt B-to-C before commit and prove B remains the
    current generation while A never revives. After C commits, inject target
    prepare, final activity-recheck, quiesce, install and restart failures. For
    each failure, prove C remains the sole authoritative generation, admission
    stays closed to all network principals until idempotent recovery succeeds,
    late A/B SNTP and DNS callbacks remain rejected, staged secrets are scrubbed,
    and reboot/status recovery never revives A or B.
12. Change the local password and interrupt every password/access-epoch/bond-store
    stage. Prove pre-commit reboot retains the complete old epoch, post-commit
    reboot selects the new epoch and immediately rejects old bonds, and newest-
    record corruption fails closed. With successful delivery, prove the terminal
    response precedes exactly-once activation/erasure; drop that response and
    prove exactly-once activation follows only after the bounded five-second
    timeout. Verify the WPA key changes, every old local session closes, old-epoch
    bonds/tokens fail, and the new password works without changing the upstream
    station password. Bond-erasure failure must disable BLE. Prove password/
    profile replacement preserves the field-mode flag and a corrupt newest
    field-state record fails closed without selecting an older flag.

    Verify access recovery clears authorized/provisional bonds and the custom
    password, increments the epoch, restores the public default, sets persistent
    field mode, opens one confirmed 120-second enrollment window and forces
    SoftAP while preserving profile, station, schedules and watermark. Verify
    provisioning reset produces those access-recovery end effects and additionally
    selects either the unprovisioned tombstone or a separately confirmed valid
    build-bundle mode without legacy resurrection. Verify full operational erase
    additionally clears station, schedules, watermark and the field-mode flag
    while leaving platform-reserved
    E10 handling under its existing contract. Prove the three chosen physical
    gestures are distinct and resistant to accidental invocation.
    At every reset phase, cut power and prove one mutually exclusive outcome:
    complete pre-intent authority; recovery-only with `reset_pending`, output
    verified off and all radios/schedules/jobs disabled while idempotently
    resuming; or, after final intent-clear commit, the complete post-reset state.
    Drop the terminal response after intent clear and prove the client reconciles
    boot/source/access generations and status without replaying the destructive
    request. Cut once after intent clear but before enrollment starts and once
    during the 120-second window; after each reboot prove the complete post-reset
    state remains, the enrollment window is closed, it does not reopen
    automatically and fresh physical/USB-local confirmation is required. Prove
    source-mode/tombstone commits before public-default activation, every target
    store verifies before intent clear, no mixed old/new authority is exposed,
    E10 is untouched, and enrollment/SoftAP begins only after clear.
13. During external ownership, loaded, armed and running-simulated states in the
    exact candidate, plus failed, output-active and output-unknown states in the
    admitted fault harness, prove profile, password, epoch, bond, enrollment,
    field-mode and reset mutations return busy with no write after a final
    activity recheck. Prove status, returning-bond service, controller-time,
    Identify and transaction cancel retain their bounded nonauthoritative
    behavior. Transport loss or revocation causes no adapter-specific job
    transition: an empty session releases, a loaded job follows its 5–60-second
    lease and aborts/releases on expiry, and armed/running work continues to its
    normal terminal state. Separately prove reboot verifies output off and then
    invalidates the WTP principal mapping, ownership, loaded work, replay state
    and terminal records.
14. Run bounded concurrency and soak with BLE advertising/management, station
    association, controller time/SNTP arbitration, mTLS WTP/HTTPS, SoftAP password
    sessions and LED indication. Record heap, largest allocation, stack guards,
    lwIP/BTstack pools, TLS allocation, flash operations, session counts, timeouts
    and complete resource return. Prove one active BLE connection, four SoftAP
    sessions and deterministic rejection plus reclamation at each bound.

Before Stage A admission, confirm that the candidate reserves the selected
`0x3f3000`–`0x3f4fff` two-sector access journal, moves the linked application
end to `0x3f3000`, leaves every later reserved bank unchanged and rejects UF2
payloads in all reserved ranges. Interrupt both access-journal sectors at every
erase/program/commit boundary with the admitted fault image/harness and retain
old-or-fail-closed evidence. Those injections qualify recovery branches only;
the standard candidate must separately demonstrate normal adoption, persistence,
replacement and boot selection.

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
  BLE management active, LED off/heartbeat/Identify, and the bounded SoftAP
  fallback state selected by policy.
- Exercise only predetermined finite inhibited/simulated cases before any finite
  RF job. Provisioning writes remain rejected while RF is owned/armed/running.
- If finite RF is authorized, first establish a genuinely output-active state,
  cap jobs and RF seconds in advance, use accepted rows only for coexistence
  comparison, preserve failures and stop on timing,
  underrun, output-authority, memory, trust or restoration failure.
- Do not promote excluded Phase 11.6 rows or claim a new clock/mode/band. Any
  timing-path, allocator/layout or clock change triggers the documented wider
  revalidation instead of evidence reuse.

## Pass and stop rules

Pass only when every admitted assertion has identity-bound evidence, no secret
material entered the repository/evidence, all resource limits return within the
predeclared gates, superseded trust stays rejected and final output/network/
provisioning state is authoritative. Persistent noncredential state must be
preserved except during the separately confirmed full operational erase; that
case must record the intended clearing and subsequent authorized restoration
rather than being treated as preservation evidence.

An unexpected output-unknown state stops the procedure immediately. A predeclared
fault-harness output-unknown case may record only the expected fail-closed
rejection and then stops that case before any further operation. Unexpected RF,
wrong device/boot/image, storage ambiguity, trust resurrection, memory/stack/DMA
fault, unauthorized radio/trust action or exhausted finite budget also stops the
procedure. Preserve every failed attempt and restore only through the
preauthorized path.

## Required result artifacts

Retain a credential-free machine-readable result plus adversarial review locally
with the exact source/image/dependency/board/boot/configuration identities,
authorized budget, every attempt and failure, journal generations, resource
extrema, restoration evidence and the Phase 11 assertions considered applicable
or requiring repetition. Commit, push, publish or otherwise distribute those
artifacts only under separate explicit authority. Credentials, Wi-Fi secrets,
private keys, raw authenticated traffic and trust-store exports remain private
and out of Git.
