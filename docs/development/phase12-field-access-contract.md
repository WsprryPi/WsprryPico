# Phase 12 field-access and security contract

Status: operator-selected on 2026-09-21. The policy is complete. Its portable
access/persistence implementation and candidate BLE, SoftAP, controller-time and
indicator adapters are hardware-free source-complete under the scoped P12.3
review; production service wiring, exact gestures, offline-page qualification
and all physical acceptance remain open.
This document grants no authority to operate hardware, enable a
radio, alter a trust store, flash firmware or emit RF.

This is the canonical product/security decision record for Phase 12. It resolves
the choices that were still open in the [Phase 12 plan](phase12-plan.md).
Contemporaneous P12.1-P12.5 review records remain accurate descriptions of what
was and was not selected at their checkpoints; their old open-decision lists do
not override this later contract.

## Purpose and authority boundary

WsprryPico must remain useful at a field event with one or more Picos, an iPhone
and no infrastructure Wi-Fi or Internet service. BLE is the primary local path
and SoftAP/Safari is an independent fallback. BLE may install the first runtime
profile on a blank generic image. Once a device-bound TLS server identity exists,
either path may replace that profile and offer ordinary local status,
configuration and job control. A provisioned device therefore remains fully
field-controllable through either BLE or SoftAP without infrastructure Wi-Fi.

Provisioning remains outside WTP/1. Field-control operations use the existing
browser/WTP semantics and the single `JobService`; neither adapter may create a
second scheduler, RF authority, ownership model, replay model or timing model.
BLE or SoftAP transport loss has no adapter-specific immediate job/ownership
side effect and never proves output inactive. The ordinary WTP lease state
machine still applies: expiry releases an empty owner, aborts/releases a loaded
job and extends an armed/running job through terminal. Reboot is distinct: after
verified output-off it invalidates ownership, loaded jobs, replay and terminal
records exactly as WTP/1 requires.

## Device identity and names

The canonical short suffix is the final six lowercase hexadecimal characters
of the Wi-Fi station MAC. The station MAC remains the source even when the BLE
or SoftAP interface uses another or randomized address.

For a station MAC ending in `0a:60:df`, the defaults are:

| Purpose | Value |
| --- | --- |
| Short suffix | `0a60df` |
| Certified hostname | `wsprrypico-0a60df.local` |
| BLE advertising name | `WsprryPico-0a60df` |
| SoftAP SSID | `WsprryPico-0a60df` |
| Local-access password | `wspr-0a60df` |

The suffix is a human label and credential input, not an authorization identity
or uniqueness guarantee. Every mutation and control session remains bound to
the full 32-lowercase-hex WTP device ID. A suffix collision, BLE address change
or wrong-device response must fail without mutation.

If the checked station-MAC read is missing or invalid, firmware substitutes no
zero, constant, build-time or remembered suffix. BLE advertising/enrollment and
SoftAP startup fail closed, USB-local status reports an identity fault, and the
adapter may retry the hardware read on a bounded schedule. Local radio access
resumes only after the full device identity and station MAC are both valid.

## Local-access password

One local-access password is shared by SoftAP WPA2 access, SoftAP application
authorization and new BLE-bond application authorization. It is separate from
the upstream station-network password, TLS client identities, TLS server key,
WTP session IDs and Bluetooth bond keys.

The derived `wspr-<suffix>` default is 11 characters and meets the existing
8-63 printable-character Wi-Fi bound. It is observable and predictable. It is
a convenience default that limits mistakes, not a secret. Status and both UIs
must say when the default is active and must not describe it as secure.

The operator may transactionally replace it with a persistent custom password
of 8-63 supported printable characters. A change does not modify the upstream
station-network password. The new password and a monotonically increasing
access epoch commit atomically before the terminal success response. That
response must be delivered before disconnection, or a bounded five-second
delivery timeout must expire; activation then takes effect exactly once.
Activation changes the SoftAP key, closes local sessions and invalidates every
bond or local session from an older access epoch before best-effort physical
bond erasure.

TLS-bundle replacement, local-password change, bond administration and
provisioning reset require fresh entry of the current local-access password;
possession of a retained bond alone is not step-up authorization. While the
derived default is active, those operations additionally require live physical
or explicit USB-local confirmation.

Each fresh-password proof and physical/USB confirmation is bound to the full
device ID, authenticated principal, current logical session, exact operation,
request nonce, current/target generations and the exact canonical mutation
parameters. That binding includes the staged-profile/request digest, target
bond identifier, reset level and new-password transaction as applicable. Any
payload, target or level change invalidates the proof. It is single-use and
expires after at most 120 seconds.

A BLE GATT disconnect invalidates its proof. SoftAP carries the freshly entered
password in the exact HTTPS mutation request rather than minting a reusable
password proof; any separate physical/USB confirmation is bound to the logical
cookie session and request digest. Closing the routine one-request TCP connection
after admission does not cancel that request. Cookie-session loss or invalidation,
logout, cancel, reboot, timeout and replay/wrong-operation use invalidate the
corresponding authority. Secret-bearing binding material remains transient and
never appears in logs, status or evidence.

Entered or customized password values must never appear in status, logs, errors,
replay entries, screenshots or maintained evidence. The public derivation rule
and illustrative derived default may be documented. A customized value may be
held in ordinary Pico flash because SoftAP needs the passphrase; Phase 12 claims
no at-rest or physical-extraction resistance.

## BLE association, enrollment and bonds

BLE uses LE Secure Connections with the Bluetooth Just Works association model.
There is no Bluetooth numeric PIN, numeric comparison, QR secret or native
WsprryPico iOS application. The Bluetooth stack generates the encryption and
bond keys; the local-access password is an application credential rather than
a Bluetooth pairing passkey.

A new controller is enrolled only during a 120-second window. While the public
default is active, every window requires live physical or explicit USB-local
confirmation. With a custom password, either a deliberate device-local action
or an already-authorized session with fresh password step-up may open it.
Possession of a retained bond alone cannot open enrollment. Outside the window,
connectable advertising/discoverability may remain available for authorized
returning bonds, but new pairing and enrollment are rejected. Advertising
exposes no secret and grants no principal.

The enrollment flow is:

1. Bluefy connects and iOS completes Just Works pairing.
2. The checked-in page reads and confirms the full device ID.
3. The operator enters the local-access password.
4. The target adapter validates device, session, locality, encrypted-link and
   password assertions.
5. Only successful application authorization promotes the stack bond to an
   authorized principal.

The stack may create a provisional bond before application authorization.
Wrong-password, timeout, disconnect, cancellation and abandoned-enrollment
paths must delete it immediately. Provisional bonds do not consume an
authorized slot. Promotion records the current durable access epoch. If deletion
or epoch persistence cannot be confirmed, all BLE local control fails closed
until physical recovery; the questionable bond is never treated as a principal.

At most four authorized bonds are retained. A returning authorized bond may
perform ordinary local control without re-entering the password. A fifth bond
is rejected clearly; no bond is silently evicted. Explicit bond removal
immediately invalidates the target bond's application principal and future BLE
authentication. If that bond is currently connected and idle-only removal is
admitted, its next application command is rejected; the adapter returns a
bounded revocation result when possible and closes the connection. Removal is
rejected busy while the target principal owns a loaded, armed or running job.
Password change and access/provisioning reset revoke all affected BLE
authentication. If post-commit bond erasure fails, BLE local control remains
disabled rather than accepting an old principal.

Only one encrypted BLE GATT connection is active at a time. Additional
connection attempts receive an explicit busy/retry result when the stack permits
one and never displace the current connection, promote a provisional bond or
evict an authorized bond.

Revocation never directly cancels, releases or changes an already owned, armed
or running WTP job. An admitted idle-only bond removal therefore has no owned
job to cancel; any resulting transport close follows ordinary WTP transport-loss
and lease/lifecycle rules. A separately authorized local safety recovery remains
the only exception already defined by WTP.

Just Works supplies encrypted transport but no authenticated active-MITM proof
during first pairing. With the public default, the physical enrollment window
is the effective proof of possession. This is an accepted experimental-device
limitation.

## SoftAP and field mode

SoftAP is a persistent recovery and field-control path, not a one-time setup
mode. It starts when no station profile exists, an explicit field-mode or
recovery action requests it, an authorized local session requests it, or a
configured station network remains unavailable after a bounded attempt. With
no station profile it may start immediately; otherwise automatic fallback must
be available within 60 seconds.

An authorized transient request keeps a ready AP available for one 120-second
join/login grace. A request while that grace is active returns busy and does not
extend it. Issuing a valid SoftAP token replaces the grace with the token-record
retention rule; selecting field mode uses the persistent rule instead. If grace
expires without a login and station service is already stable with no other AP
cause, the AP stops. Reboot clears this transient cause.

An explicit field-mode selection is persistent across ordinary restart and
power loss and keeps SoftAP active until the operator explicitly exits it. An
inactivity timer must not remove the only field-control path. Automatic
station-failure fallback remains active while the station is unavailable. After
station link and an address remain usable for 30 continuous seconds, fallback
stops only when no live server-side SoftAP token record (including owner-only
grace), join/login grace or reply is active and no no-profile, field-mode or
recovery cause remains. A logical token record, not merely an open TCP connection
or visible page, is the session for this rule.
Station recovery during page suspension cannot stop the AP while that record
owns loaded, armed or running work; loaded work remains subject to ordinary WTP
lease expiry. Ordinary reboot reevaluates station fallback rather than persisting
that runtime cause. Successful provisioning never permanently disables SoftAP
recovery.

SoftAP uses WPA2-Personal or a stronger target-supported mode and the
local-access password. Association alone is not application authorization.
When a valid device-bound TLS server identity exists and usable UTC has been
accepted, normal SoftAP browser control uses server-authenticated HTTPS plus a
password-authenticated SoftAP-only application session. It reuses browser API
schemas and JobService behavior but does not require or create a TLS client
certificate.

A successful password login issues at least 128 random bits of opaque session
token in a Secure, HttpOnly, SameSite=Strict session cookie with no persistent
expiry; the token never appears in a URL or script-readable Web Storage or
IndexedDB. The resulting principal is random per login and bound to the full
device ID, boot ID and current access epoch, so sharing a password does not
share a principal. Its ordinary authority expires after 15 minutes of inactivity
or at a fixed 12-hour absolute deadline, whichever comes first. The inactivity
timer is suspended while that principal's mapped WTP session is armed or running
and restarts at terminal. If the absolute deadline arrives while that exact
session is armed or running, the token enters owner-only grace: it may receive
events, issue STATUS or ABORT for that session and submit controller-time
observations authenticated as the same principal and bound to the same device
and session. Those observations remain subject to the existing nonce,
uncertainty, age and source-arbitration rules; a valid refresh may preserve or
recover time for the already accepted armed job but grants no new ARM or
schedule admission. Grace cannot LOAD, ARM, configure, provision, administer
access or create another WTP session. It ends and the token is invalidated
immediately at terminal. The 12-hour deadline is never reset or extended. A
loaded job is ineligible for grace and retains the ordinary 5–60-second WTP
lease: expiry aborts/releases it.

Each token record holds at most one exact WTP session ID after HELLO. A page
refresh with the same live cookie, including during owner-only grace, reattaches
to that mapped session after authoritative STATUS; it neither chooses nor creates
a replacement session, and grace retains its restricted operations. Thus
suspension longer than 15 minutes can preserve owner control during an armed/
running job, but the authentication token alone never adopts ownership.

A password submission carrying a valid ordinary-authority session is fresh
step-up for that same principal; it never mints or replaces the token. With no
valid cookie, a login creates a new principal only if capacity permits and never
silently replaces another live session, especially one that owns a job. At most
four live SoftAP application sessions are retained. Logged-out, finally expired,
reboot-invalidated and old-access-epoch records are reclaimed before admission;
owner-only grace still consumes its slot. If four live records remain, another
login returns busy and evicts none.

Explicit logout returns busy while that principal owns a loaded, armed or
running job; the operator must first ABORT or reach a releasable terminal state.
A successful logout in a safe state, password change, access/provisioning
recovery or token expiry invalidates the application session but causes no
adapter-specific immediate job transition; the ordinary WTP lease/lifecycle
still governs. Reboot instead follows WTP reset semantics: after output-off is
verified it invalidates the principal mapping, ownership, loaded work, replay
state and terminal records.

A lost or cleared cookie and final expiry outside owner-only grace create no
ownership transfer: a new login receives a new principal and cannot resume that
job. If the original principal can no longer abort it, the sole ownership
exception is the existing WTP local trusted safety ABORT through the physical
Console or an explicitly authorized USB-local recovery adapter; it transfers no
ownership and grants no other operation.
Existing Host/Origin equality, content type, explicit
request header and Fetch Metadata mutation checks remain mandatory.

HTTPS reached through the station interface and every raw TLS-WTP connection
retain the existing client-certificate mTLS principal. The SoftAP password
principal grants neither of those authorities. A client certificate may still
use the existing mTLS paths, but the password session is confined to the SoftAP
interface and browser API adapter.

The current mTLS listener is UTC-gated, so SoftAP also requires a separate
bounded pre-clock service. A device-bound build bundle or valid runtime profile
serves restricted server-authenticated HTTPS before device UTC is valid; Safari
validates its CA, exact DNS SAN and validity using iPhone time. Only that
authenticated service may accept local-password login and the controller-time
exchange. Before usable UTC it exposes only full identity, challenge, login,
nonsensitive status and time; it is not browser API v1 and accepts no profile,
password/bond/trust mutation or job LOAD/ARM/control.

A blank generic image has no server identity. Its unauthenticated SoftAP surface
is read-only and exposes only full device identity, build/wire version and
nonsensitive status. It accepts no password, controller-time sample, profile or
job/control mutation, so an evil twin receives no reusable credential. The first
profile arrives through BLE enrollment or explicit USB-local provisioning. After
a device-bound profile commits, first authenticated UTC may arrive through that
BLE/USB-local path or the provisioned pre-clock SoftAP service; the authenticated
SoftAP path then remains available for offline time, control and replacement.

The supported iPhone route is manual Safari, never a captive-sheet credential
flow. SoftAP DHCP supplies a bounded, implementation-recorded local subnet and
mDNS maps `wsprrypico-<suffix>.local` to the Pico without DNS interception. A
blank device's read-only page is
`http://wsprrypico-<suffix>.local/` and visibly unauthenticated. A provisioned
device uses only `https://wsprrypico-<suffix>.local/`; that exact hostname is
the certificate DNS SAN and Host/Origin authority. The captive sheet, if iOS
opens one, accepts no password or control input and directs the operator to
Safari.

Before provisioned SoftAP use, the operator explicitly trusts the public
CA/server identity from the same off-device profile or device-bound bundle;
firmware may show its public fingerprint but may not install trust silently.
Wrong CA, SAN, Host/Origin or any certificate warning stops the flow.

Because automatic SoftAP fallback exposes a derivable default, an operator who
leaves that default active deliberately accepts that a nearby party can derive
it and may obtain ordinary field-control, including RF job authority under the
normal browser/JobService rules. Physical/USB confirmation still protects trust
replacement and reset. Customizing the password reduces casual nearby access
but does not repair BLE Just Works' initial active-MITM limitation. SoftAP
server authentication remains independently required.

## Offline UTC from the local controller

Every boot starts with UTC unsynchronized. No battery-backed or persisted UTC is
trusted. The preferred source remains a reachable configured SNTP server,
including a local LAN server that needs no Internet. When none is reachable,
an authenticated, full-device-ID-bound Bluefy or SoftAP controller supplies an
experimental phone-time observation to the existing UTC discipline.

The exchange uses a fresh nonce and Pico monotonic challenge timestamp. The
controller samples POSIX UTC only after it receives the complete challenge
indication, then returns the exact nonce/session/device binding. Starting the
final challenge-response indication starts the target-side latency interval;
this is a conservative target-observable boundary before the controller can
sample the UTC value and avoids racing its next write against the later
indication-confirmation callback. The Pico
computes, rather than accepts from the client, a nonzero uncertainty comprising:

- a fixed 250 ms allowance for unverified iPhone clock error;
- final response delivery plus the controller-sample and submission latency; and
- local serialization, timer-quantization and configured oscillator-growth
  margins.

Stale, replayed, wrong-device, wrong-session, nonmonotonic and over-budget
observations are rejected. Phone UTC must be within the existing 2025-2099
supported era. The existing 500 ms maximum uncertainty and 90-second WTP
source-age admission are not relaxed. Bluefy and Safari request a sample at
connection and no less often than every 60 seconds while active. If iOS suspends
the page or the connection ends, age and uncertainty continue to grow normally;
new ARM and standalone-schedule admissions eventually fail.

SNTP is authoritative while its accepted observation is no more than 90 seconds
old; controller samples may be reported but cannot replace or invalidate it.
When no valid SNTP observation exists, a valid controller sample may become
authoritative and records its authenticated principal. While that controller
observation remains valid, only the same principal may refresh it, and the new
interval must overlap the aged authoritative interval. A different principal is
rejected with `time_source_busy` and cannot change or invalidate the clock; it
may become the source after the prior observation ages invalid. A nonoverlapping
same-principal refresh latches `time_disagreement` and invalidates UTC for new
ARM, launch and schedule admission. Recovery requires two consecutive valid,
mutually overlapping controller observations from one authenticated principal;
neither sample may be a replay of the rejected request.

To switch from controller time to SNTP, compare their UTC intervals after aging
both uncertainties to the same monotonic instant. Intervals overlap when the
absolute estimate difference is no greater than the sum of their uncertainties.
An overlapping SNTP observation replaces controller time. A nonoverlapping SNTP
observation latches `time_disagreement`, invalidates UTC for new ARM, launch and
schedule admission, and requires two consecutive valid, mutually overlapping
SNTP observations from the configured peer to recover.
Reboot instead returns to the ordinary unsynchronized state. While SNTP remains
valid, controller observations cannot refresh it, trigger disagreement or take
authority.

A loaded job remains loaded during time invalidation. An armed job that fails
the launch clock gate becomes `missed` with output disabled. A running job
continues on its already selected monotonic schedule. Source switching and
disagreement never reschedule a job, steal/release ownership, clear a fault or
write the no-repeat watermark by themselves. A bad but internally valid first
phone sample cannot be detected without another source and can advance later
schedule reservations; this is an accepted operator-trust limitation, and the
watermark is never rolled back to compensate.

Phone/POSIX time is treated as `leap=normal`; iOS JavaScript supplies no
leap-pending indicator. This is an explicit limitation, not GNSS, authenticated
NTP, calibrated UTC or independently verified phone accuracy. UI and status
report source, sample age, conservative uncertainty and disagreement state.

Enrolled Bluefy, explicit USB-local tooling and the provisioned server-
authenticated pre-clock SoftAP surface can identify and synchronize the device,
but cannot arm a job until the ordinary WTP clock and leap checks pass. Blank
read-only SoftAP cannot synchronize. UTC is never restored as valid merely from
flash, reboot history or a prior browser session.

## Local field-control binding

After authorization, BLE and SoftAP may expose identity/status, station and
schedule configuration, Wi-Fi/TLS provisioning, local-access/bond controls,
field-mode controls and ordinary browser/WTP job operations.

Provisioning retains its existing 512-byte command and 256-byte status bounds.
Those limits are not WTP job capacity. Full BLE job control frames and
reassembles the existing bounded WTP stream, including maximum job payloads,
through a separately bounded GATT transport. SoftAP ordinary control uses the
password-session browser adapter; raw TLS-WTP remains mTLS-only. A BLE bond
principal, SoftAP session-token principal and certificate principal are
different identities supplied to the one `JobService`. They preserve WTP HELLO,
session, lease, replay, terminal and resume rules. Resume requires both the same
authenticated principal and the exact original WTP session. The SoftAP adapter
uses the token record's single mapped session ID; a bond, cookie, certificate or
password by itself adopts nothing. Switching paths never transfers ownership
merely because the same person or password is involved.

Transport/session loss, password change, bond clearing, access recovery and
SoftAP shutdown do not infer output state or cause an adapter-specific immediate
job transition. Ordinary WTP lease expiry still releases empty ownership,
aborts/releases loaded work and carries armed/running work through terminal.
Reboot instead performs the WTP output-off/reset invalidation described above.
Every
persistent profile, password, access-epoch, bond promotion/removal, enrollment
or field-mode mutation and every reset/recovery operation requires no owner, no
armed/running/failed state and authoritatively inactive output; unknown output
also rejects it. Admission is rechecked immediately before flash, bond-store or
radio-restart work. A busy result performs no persistent write and never aborts,
releases or clears another state to become admissible. Opening new enrollment is
also rejected while busy so no provisional bond is created.

Nonsensitive status, an already-authorized returning-bond connection, controller
time observations, Identify and qualified runtime BLE/SoftAP service may coexist
with job states but gain no RF authority. Cancel of an uncommitted provisioning
transaction remains allowed and only scrubs its own staged data.

## TLS credentials and trust replacement

A provisioned profile atomically replaces station Wi-Fi, its time server and the
complete TLS server bundle. At successful commit, the new generation becomes
the sole authorization generation and immediately supersedes the previous
client CA. The target adapter closes its network admission gate, invalidates all
pre-existing network principals except the applying transport's bounded
terminal-response capability, and admits no new old- or new-generation
TLS/HTTP/WTP principal until activation. The old network runtime may remain
allocated during response delivery, but it authorizes no further application
request and, if it carries the applying response, may carry only that terminal
response. Delivery confirmation or the bounded five-second timeout activates
the committed runtime exactly once: generation B is then served and admitted,
and generation A is rejected. There is no interval in which both generations
grant application authority. Interrupted pre-commit writes retain the current
generation. Corruption of the newest committed generation fails closed and
never revives superseded trust.

Every SNTP request, DNS result, observation and completion callback is bound to
the active profile generation and normalized configured time-server peer. A
successful profile commit invalidates superseded-generation SNTP authority,
cancels old requests where possible and ignores every late old-generation DNS
or SNTP completion. A still-valid controller-time source may continue under its
existing principal, age, uncertainty and arbitration rules; without one, UTC
becomes unsynchronized. Only after the new runtime activates may the new peer be
resolved or queried and its observations accepted.

The profile journal also stores a transactional source mode: legacy bootstrap,
runtime profile, unprovisioned tombstone or explicitly selected device-bound
build bundle. Legacy bootstrap is permitted only before the first Phase 12
profile/reset adoption. Once a runtime profile or unprovisioned tombstone has
committed, deleting or corrupting a profile never exposes Wi-Fi credentials from
the standalone version-1 base configuration and never silently selects build
trust. Those legacy Wi-Fi bytes may remain stored but are ignored. Returning to
a valid device-bound build bundle requires the separately confirmed explicit
mode transition; a missing or corrupt newest source-mode record fails closed
without selecting an older mode.

Operator tooling may generate the server key, server certificate and client CA
material off-device. The per-device CA private key must never be installed on
the Pico. The Pico may store its server key, certificate and client CA in
ordinary flash; no secure-element or encrypted-at-rest claim is made.

The local-access credential never becomes a TLS client identity and never
grants TCP WTP trust. Host trust installation/export remains an explicit
operator action; firmware and tooling may not silently install a CA, weaken a
trust scope or bypass a browser warning.

After activation, the Pico serves only the new server certificate and key. It
cannot remove a previously installed public server CA from an iPhone; that CA
remains phone-side trust until the operator separately removes it or it expires
or is revoked. This is not device-side dual authorization, and acceptance
evidence must report Pico credential service, Pico client authorization and
iPhone trust-store state as separate assertions.

## Recovery and reset

Three distinct operations are selected:

1. **Access recovery** clears authorized/provisional BLE bonds and the custom
   local password, increments the access epoch, restores `wspr-<suffix>`, sets
   persistent field mode, opens one physically confirmed 120-second enrollment
   window and forces SoftAP. It preserves the runtime Wi-Fi/TLS profile, station,
   schedules and no-repeat watermark.
2. **Provisioning reset** performs access recovery and transactionally selects
   either an unprovisioned tombstone or, when separately confirmed and valid, the
   device-bound build-bundle mode. It never falls through to legacy standalone
   Wi-Fi or old build trust. A generic image remains limited to bootstrap
   read-only identity/status until its first profile arrives over authenticated
   BLE or explicit USB-local provisioning. After that commit, first UTC may also
   arrive through provisioned server-authenticated SoftAP. Station, schedules
   and watermark remain intact.
3. **Full operational erase** performs provisioning reset and additionally
   clears station, schedules, the no-repeat watermark and the persisted
   field-mode flag. It requires a separately named, physically confirmed action
   and is never an implicit consequence of the first two operations.
   Platform-reserved E10 handling remains governed by its existing recovery
   contract.

Every reset first commits a durable `reset_pending` intent in the access
journal, bound to the full device ID, reset level, target source mode and request
digest. While intent is pending, boot verifies output off and exposes only
physical/USB recovery status: station, BLE, SoftAP, schedules and all job control
remain disabled. The operation is idempotently resumed, never rolled back to an
older authority.

Provisioning reset and full erase commit the selected profile source
mode/tombstone before committing the new default password/access epoch. Full
erase then clears station/schedules/watermark. All levels commit the new access
state while intent remains pending, erase physical bonds, verify every target
store, and finally clear intent; only then may the enrollment window and SoftAP
start or a terminal success be reported. A cut before the durable intent commit
retains the complete pre-intent authority. A cut or write/verification failure
after intent commit and before intent clear boots recovery-only and resumes the
remaining phases. A cut after intent clear retains the complete post-reset state;
a lost success response is reconciled from boot/source/access generations and
status rather than by replaying the destructive request. These outcomes never
expose the public default alongside superseded runtime profile/trust. The E10
sector is never part of this coordinator.

The enrollment grant is deliberately volatile and is created only after intent
clear. A cut or reboot after intent clear but before the window starts, or at
any point during its 120 seconds, retains the complete post-reset state with the
window closed. It never reopens automatically; another fresh physical or
USB-local confirmation is required. Persistent field mode may still make the
SoftAP available, but it grants no replacement enrollment authority.

The exact safe Pico 2 W gestures remain target implementation details, but the
three actions must be visibly distinct and resistant to accidental invocation.
All reset/recovery mutations are rejected or deferred while ownership exists,
the service is armed/running/failed, output is active or output state is
unknown. They never release an owner or clear a job/fault.

## Onboard LED contract

One core-0 `IndicatorController` owns the Pico 2 W onboard LED. That LED is
CYW43 wireless GPIO 0, not an RP2350 GPIO. Only the controller performs checked
`cyw43_gpio_set()` operations after CYW43 initialization; callbacks enqueue
requests and no LED write runs on core 1 or in a timing-critical interrupt.
Patterns use monotonic time and need no UTC.

| State | Pattern |
| --- | --- |
| Normal | Off |
| SoftAP actually ready | 200 ms on, 1,800 ms off, repeated while the AP remains ready |
| Identify | Three 150 ms pulses separated by 150 ms, then 1,250 ms off; five two-second cycles (10 seconds) |

An authenticated, full-device-ID-bound BLE, SoftAP or USB-local request may
start Identify. It is transient and nonpersistent, overrides the SoftAP
heartbeat, then recomputes actual AP state and resumes the heartbeat or Off.
An exact duplicate request does not extend it; a concurrent Identify returns
busy. Reboot cancels it. SoftAP requested/starting/failed states do not display
the ready heartbeat.

LED operations never acquire, cancel or release a job and must coexist with all
job states. Write failure is exposed as nonsensitive indicator status but does
not alter SoftAP, job or RF authority. The LED is advisory only: neither its
pattern nor Off state proves AP availability, authentication, clock validity,
RF state, output safety or absence of a fault.

## Persistence, limits and secrecy

The profile journal, local-access/field state and BTstack bonds remain physically
and logically separate from station, schedule, watermark and E10 storage. The
local-access/field journal owns the password state, current access epoch,
authorized-bond epoch index and persistent field-mode flag. Password, bond,
field-mode and profile operations preserve station, schedule and watermark
records unless the explicit full operational erase is selected.

Exactly one exceptional access-store state is initializable without a committed
record: both access sectors completely erased. Erasure alone is never evidence
that the device is factory-virgin; the same state after customization is
indistinguishable. Every such initialization therefore keeps BLE advertising
and SoftAP disabled until firmware validates full identity/station MAC,
authoritatively inactive output and a new live physical or explicit USB-local
confirmation that authorizes restoration of the public default.

Only then may firmware transactionally commit format/adoption magic, access
epoch 1, the derived default, an empty authorization index, field mode false and
no reset intent. An interrupted commit leaves non-erased invalid media, latches
an access fault and exposes USB-local recovery only; it is never reinterpreted
as all-erased. Any other missing/corrupt newest record fails closed rather than
selecting an older password/epoch or regenerating the public default.

The selected target layout adds an 8 KiB project-owned local-access/field journal
at `0x3f3000`–`0x3f4fff`, comprising two alternating 4 KiB erase sectors, and
moves the linked application FLASH end down to `0x3f3000`. The existing future
BTstack bank remains `0x3f5000`–`0x3f6fff`; the profile, standalone and E10
regions retain their existing addresses. This reservation and linker change are
selected requirements, not present in the current P12.5 image, and must pass all
maintained layout/image checks and target cross-links before adapter integration.

The source mode and unprovisioned tombstone commit inside the profile journal's
versioned transactional envelope rather than the local-access journal, so a
profile generation and the rule selecting or suppressing it cannot tear into
contradictory states. The BTstack bank may retain physical bond material, but
only the access journal's current-epoch authorization index grants application
authority.

Password change and access recovery commit the new password state and incremented
epoch atomically before activation. Every authorized bond is accepted only when
its application authorization index matches the current epoch; a stale stack
bond therefore has no authority even if power fails before physical erasure.
Power loss before commit retains the complete old password/epoch; power loss
after commit selects the complete new password/epoch and rejects all older
bonds. A missing or corrupt newest access record latches an access fault and
never falls back to an older password or epoch. Post-commit bond-erasure failure
keeps all BLE local control disabled until physical recovery.

Explicit field-mode entry sets its journaled flag and explicit exit clears it.
Password/profile replacement preserves the flag. Access and provisioning reset
set it so their forced SoftAP survives reboot. Full operational erase clears it,
although the resulting no-profile state may independently start bootstrap
SoftAP. Corrupt newest field state fails closed rather than selecting an older
mode.

The existing portable bounds remain: one provisioning session, one staged
profile, 7,168 profile bytes, ordered fragments, 30 seconds without progress,
eight replay digests for five minutes and full device/principal/transport
binding. Staged secrets are scrubbed after apply, cancel, timeout and every
terminal failure. Persistent flash is not claimed confidential.

## Bluefy page and offline operation

The repository-owned Web Bluetooth page is the selected iPhone client and no
native app is planned. Its version/integrity identity must be visible; it may
not load unapproved remote scripts, analytics or credential services. It must
clear temporary secrets and work from an integrity-controlled offline delivery
or cache on the accepted Bluefy/iOS pair.

The repository also supplies a native Raspberry Pi/Linux BlueZ command-line
client as an additional local/bench controller. It selects an exact Bluetooth
address, verifies the full encrypted device identity, uses the same Just Works
enrollment, retained-bond and application-password policy, and reuses the exact
provisioning and WTP GATT characteristics. It must not set the BlueZ device
globally trusted or accept passwords through arguments/environment variables.
Its host or live-Pi evidence is independent of, and cannot substitute for, the
selected Bluefy/iOS offline acceptance rows.

Physical acceptance disables infrastructure Wi-Fi and cellular data and proves
the exact page remains usable. If reliable offline delivery cannot be proven,
BLE is not accepted as the sole field path; the independent SoftAP/Safari path
must still work. Selecting Bluefy does not authorize host trust-store changes.

## Accepted limitations and completion gate

The operator accepts that the derived default is public, Just Works lacks
initial active-MITM authentication, phone time has a declared rather than
measured accuracy allowance, ordinary flash is extractable and the LED is not a
safety indicator. A blank generic image cannot use SoftAP alone to install its
first server identity; that requires BLE or explicit USB-local provisioning.
WsprryPico remains an experimental amateur-radio device, not an enterprise
security appliance.

Implementation must still prove MAC-read/suffix-collision/wrong-device failure,
bond promotion/deletion/capacity/epoch/revocation, default/custom password and
step-up behavior, SoftAP session-token expiry/resume, offline Bluefy, limited
generic bootstrap and 60-second fallback, phone refresh/source disagreement,
page suspension, profile-source tombstones, trust replacement, all three reset
levels, exact LED patterns/priority, full WTP framing, resource reclamation and
job/RF noninterference. See the
[finite physical plan](phase12-physical-acceptance.md). Host tests and Arm links
alone do not close these gates.

The remaining implementation details are the exact physical gestures,
production GATT/SoftAP/HTTPS/local-control and live-activation wiring, the
offline page delivery mechanism and target resource/coexistence tuning. The
exact pinned BTstack source now cross-links the candidate adapter, but that is
not physical interoperability evidence. Remaining work may not weaken this
contract; a discovered incompatibility returns for an explicit policy decision.
