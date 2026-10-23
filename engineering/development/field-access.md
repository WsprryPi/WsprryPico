# Engineering field access and recovery

Engineering BLE and certificate-based local control share the application access
manager and one JobService. Consumer Wi-Fi setup and password-encrypted radio
control use the [consumer access](consumer-lan-access.md) and
[Consumer-Radio/1](../protocol/Consumer-Radio-v1.md) contracts. Their open
Wi-Fi-first setup supersedes read-only blank-AP policy for that consumer surface.
Every AP path, including engineering field and recovery access, remains available while a Wi-Fi client is associated. The final disconnect starts a ten-minute inactivity interval. Initial unjoined access lasts ten minutes, except the Console's two-minute join grace. Browser traffic, authentication slots and stored field intent do not substitute for association or reopen an expired window. USB remains the local recovery transport.

Provisioning remains outside WTP/1. All field job control enters the existing
JobService; transport loss does not prove inactivity or transfer ownership.
Ordinary WTP lease, fault and reset rules remain authoritative.

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

One local-access password is shared by provisioned SoftAP WPA2 access, SoftAP
application authorization and new BLE-bond application authorization. The
unprovisioned read-only captive AP is open and has no application login. The
local-access password is separate from
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
held in ordinary Pico flash because SoftAP needs the passphrase; the implementation claims
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

1. The BLE client connects and its operating system completes Just Works pairing.
2. The client reads and confirms the full device ID.
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

## Offline UTC from the local controller

Every boot starts with UTC unsynchronized. No battery-backed or persisted UTC is
trusted. The preferred source is a reachable configured NTP server,
including a local LAN server that needs no Internet. When none is reachable,
an authenticated, full-device-ID-bound BLE or SoftAP controller supplies an
experimental phone-time observation to the existing UTC discipline.

The exchange uses a fresh nonce and Pico monotonic challenge timestamp. The
controller samples POSIX UTC only after it receives the complete challenge
indication, then returns the exact nonce/session/device binding. Starting the
final challenge-response indication starts the target-side latency interval;
this is the conservative fallback boundary if the controller's submit write
races the later indication-confirmation callback. When the target receives the
successful ATT indication confirmation first, confirmed delivery becomes the
tighter target-observed boundary because the controller cannot sample the UTC
value before it receives the complete challenge. The Pico
computes, rather than accepts from the client, a nonzero uncertainty comprising:

- a fixed 250 ms allowance for unverified iPhone clock error;
- final response delivery plus the controller-sample and submission latency; and
- local serialization, timer-quantization and configured oscillator-growth
  margins.

Stale, replayed, wrong-device, wrong-session, nonmonotonic and over-budget
observations are rejected. Phone UTC must be within the existing 2025-2099
supported era. The existing 500 ms maximum uncertainty and 90-second WTP
source-age admission are not relaxed. Browser controllers request a sample at
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

Enrolled BLE clients, explicit USB-local tooling and the provisioned server-
authenticated pre-clock SoftAP surface can identify and synchronize the device,
but cannot arm a job until the ordinary WTP clock and leap checks pass. Public blank-AP reads grant no controller-time authority; the consumer setup
page uses its independently challenge-bound time adapter. UTC is never restored as valid merely from
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
build bundle. Legacy bootstrap is permitted only before the first versioned
profile/reset adoption. An exactly erased profile journal in a generic image
selects unprovisioned mode at generation zero. An image with a complete,
matching device-bound compiled bundle may retain factory behavior at
generation zero; a partial or wrong-device compiled bundle fails closed.
An explicit build-bundle selection also requires a matching compiled bundle.
An interrupted first source selection fails closed until recovery rather than
appearing erased. Once a runtime profile or unprovisioned tombstone has
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

Three distinct reset levels have separate preservation rules:

1. **Access recovery** clears authorized/provisional BLE bonds and the custom
   local password, increments the access epoch, restores `wspr-<suffix>`, sets
   persistent field mode, opens one physically confirmed 120-second enrollment
   window and forces SoftAP. It preserves the runtime Wi-Fi/TLS profile, station,
   schedules and no-repeat watermark.
2. **Provisioning reset** performs access recovery and transactionally selects
   either an unprovisioned tombstone or, when separately confirmed and valid, the
   device-bound build-bundle mode. It never falls through to legacy standalone
   Wi-Fi or old build trust. Engineering profile replacement uses authenticated BLE or explicit USB-local
   provisioning; consumer network bootstrap uses its separate AP transaction.
   A provisioned server-authenticated SoftAP can also supply the first UTC. Station, schedules
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
remaining reset operations. A cut after intent clear retains the complete post-reset state;
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

The three reset actions are explicitly named and distinct. The normal GP14
button is reset/shutdown/setup access; it is not an implicit full erase.
All reset/recovery mutations are rejected or deferred while ownership exists,
the service is armed/running/failed, output is active or output state is
unknown. They never release an owner or clear a job/fault.

## Persistence, limits and secrecy

The profile journal, local-access/field state and BTstack bonds remain physically
and logically separate from station, schedule, watermark and E10 storage. The
local-access/field journal owns the field password, the separate consumer Pico password, current access epoch,
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

The [flash layout](../../src/standalone/pico/flash_layout.hpp) keeps the access,
BTstack, profile, standalone and E10 regions separate. Linked image checks
enforce the application boundary and journal addresses.

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

## Local clients and offline operation

The native Raspberry Pi/Linux BlueZ command-line client provides local control. It selects an exact Bluetooth
address, verifies the full encrypted device identity, uses the same Just Works
enrollment, retained-bond and application-password policy, and reuses the exact
provisioning and WTP GATT characteristics. It must not set the BlueZ device
globally trusted or accept passwords through arguments/environment variables.
Its host or live-Pi evidence is independent of phone/browser interoperability
and consumer portal offline acceptance.

Offline physical acceptance isolates the Pico field network from Internet,
disables cellular data and proves the device-served setup portal remains
usable. Keep Wi-Fi enabled for the connection to the Pico.
