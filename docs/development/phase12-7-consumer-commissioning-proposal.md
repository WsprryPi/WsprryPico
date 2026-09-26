# P12.7 consumer commissioning decision proposal

Status: **PHONE CLIENT OPEN; BLUEFY WORK PAUSED — FULL CONTRACT NOT APPROVED**. On
2026-09-26 the operator selected a per-device CA key on the Pico with owner and
physical approval for each mTLS client and runtime BOOTSEL subject to a hard
safety gate. The operator selected certificate-free Safari/HTTP on a
device-specific WPA2 SoftAP with BLE-owner browser authorization, subject to a
code-free iPhone join and handoff feasibility gate. The operator also stated
that physical extraction risk for a CA key in ordinary Pico flash is acceptable
for this project. The operator also accepted the residual active MITM/relay
risk of Just Works plus human LED/BOOTSEL confirmation for this project. This
design requires no per-device setup code, QR label, pairing PIN or extra
password. This is a reviewable design,
not a replacement for the [selected engineering field-access contract](phase12-field-access-contract.md),
the frozen [Field-GATT/1 wire contract](../protocol/Field-GATT.md), or authority
to implement commissioning or operate hardware. The
[P12.7-12.12 execution prompt](phase12-7-12-execution-prompt.md) lists the
remaining gates. The [adversarial proposal review](phase12-7-proposal-review.md)
records corrected findings and open approval gates. The uncommitted roadmap
change that introduced P12.7 is preserved separately in
[the Phase 12 plan](phase12-plan.md).

On 2026-09-26 the operator paused Bluefy work. The Bluefy screens and
Bluefy-to-Safari handoff below are retained as a historical draft, not a
selected client implementation. P12.7 must choose and approve a replacement
phone-client path before P12.9 or phone acceptance can begin. The
certificate-free provisioned SoftAP direction remains selected.

## Why a new decision is necessary

Current Bluefy source asks for the local-access password, profile JSON/PEM
material and, for the public default, a USB-local profile confirmation. The
current profile contains Wi-Fi, TLS server private key, certificate and client
CA. The engineering contract makes the default password public, requires an
explicit browser trust installation for provisioned SoftAP, and does not yet
define a safe runtime physical gesture. Those behaviors cannot simply be
hidden by changing labels: they define actual authority and trust. Existing
generation-3 Candidate A activation proves a bounded engineering path, not
blank-device consumer commissioning.

The following product design incorporates those selected options. The complete
state/UX/security contract still needs a single explicit P12.7 acceptance
before P12.8; no code should be written against guessed details.

## Proposed ordinary setup

| Step shown to the user | Exact accepted result |
| --- | --- |
| Power on | A device without an owner or runtime network profile advertises setup availability; previously preserved station/schedule/watermark data may still exist. Its short name is only a chooser hint. |
| Set up WsprryPico | Bluefy filters the GATT service, connects with LE Secure Connections and reads the full encrypted device identity internally. It never asks the user to type an ID. |
| Confirm device | Bluefy starts Identify on that connection. The user observes the selected Pico's LED and gives one short **runtime** BOOTSEL tap while the claim window is active. A hold during power-on/reset is invalid. |
| Connect | The user supplies Wi-Fi name/password and station callsign, four-character locator and WSPR power. Time server and TLS details use approved defaults or a separate advanced path. Bluefy validates and sends one transaction. |
| Setup complete | Only after a durable generation-1 result, normal restart, same full identity and retained owner, station association, address, time and configuration readback are verified. Unknown results show **Checking setup** until reconciled, never a second blind submission. |

The ordinary page must not show a default password, per-device setup code,
QR scan, pairing PIN, ID, JSON, PEM, USB command, session token or certificate
installation. The Wi-Fi password is the only
password the ordinary user enters. The station fields are currently present in
the browser API; final power-field/default behavior needs to match its accepted
validation contract. A no-infrastructure field setup needs a separate stated
flow because P12.10 specifically requires station readback.

The current production boot suppresses local radio service when the access
journal is erased or unhealthy. P12.8 would need a separately bounded healthy
unclaimed state; an erased or faulted journal must never be reinterpreted as
open setup authority. This transition needs explicit migration and power-cut
tests.

## Proposed claim and owner state

The candidate gesture is **one 100-600 ms BOOTSEL tap after Identify starts and
before a 30-second claim deadline**. It is sampled only while the application
is running. A ROM BOOTSEL entry, reset during the press, missing release,
debounce ambiguity or flash/second-core scheduling conflict fails the attempt
closed. The implementation must first establish an RP2350-safe RAM-resident
sampler and measure its impact on XIP, flash programming, both cores and radio
timing. The SDK's unrelated TinyUSB sample warns that flash access from another
core invalidates its simple polling method; copying it is not sufficient
evidence. If safe sampling cannot be demonstrated, return this gesture for a
new design decision instead of silently substituting USB or a GPIO accessory.

Only the currently selected encrypted BLE connection may request a restricted
pre-owner Identify and hold the one claim slot. This requires a narrowly scoped
change to the current authorized-only Identify rule. Its claim record binds the
full device ID, boot ID, link handle, stable provisional bond identifier,
client nonce, claim request digest and monotonic deadline. A fresh physical
release edge is consumed once and cannot authorize a later connection, another
device or replayed claim. The later configuration request separately binds its
exact settings digest to the durable owner/claim epoch. Competing claimants
receive busy; timeout/disconnect/cancel deletes the provisional bond and clears
transient authority. A bond is promoted to the first owner only after the
claim record commits and physical confirmation succeeds. A claimed but
unconfigured owner may reconnect to finish setup within a bounded recovery
state; the device still exposes no station/TLS service until generation 1
commits.

The retained owner bond authorizes routine BLE reconnect and ordinary local
control under the existing one-`JobService` rules. It does not by itself
authorize adding a phone, replacing trust or erasing data. Up to four authorized
bonds may be retained with no silent eviction. A later phone requires a fresh
owner-approved enrollment and a fresh physical action; removing a bond revokes
its application principal before asynchronous stack erasure. Lost-owner access
recovery requires physical possession and can create a new owner without the
old phone while preserving the operational profile.

The LED plus physical gesture identifies the intended nearby board to a human,
but LE Just Works does not prove absence of an active relay. The operator
accepted this bounded active-MITM limitation for the experimental device on
2026-09-26. Neither a MAC suffix nor the LED is cryptographic anti-relay proof.

The [Bluetooth LE security specification](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v6.3/out/en/host/security-manager-specification.html)
defines the Just Works limitation. This contract accepts it without adding a
user code or changing the five-step setup flow.

## Proposed generated identity and credential lifetime

For a generic UF2, generate a per-device P-256 CA key and separate P-256 TLS
server key on-device after a claimed phone supplies authenticated bounded UTC.
The CA signs only this device's server identity and individually approved client
CSRs. Bind the server certificate to the full device ID and exact `.local`
hostname. Never export the CA or server private key to Bluefy or a station
client. Reject missing entropy, invalid time, malformed SAN, key mismatch and
incomplete storage. Store identity and profile as one versioned transactional
authority so a reboot cannot select new network settings with old trust. The
CA public certificate and server pin may leave the device. This intentionally
changes the engineering policy that keeps the CA private key off-device; the
new private CA key resides in ordinary Pico flash and has no physical
extraction-resistance claim. That exception must be explicit in the accepted
field-access contract and security documentation.

The initial CA certificate is device-scoped and expires after ten years. The
server certificate expires after one year and automatically renews under the
same CA when valid UTC is available within the last 30 days of its term; the
existing server identity remains active until a complete replacement commits
and validates. A new server key is generated for each renewal. An expired
server certificate never triggers a station TLS warning bypass. CA rotation
requires a separately approved owner action and a planned transfer of station
trust; a failed rotation leaves the prior complete generation or a
fail-closed recovery state, never mixed trust. Client certificates expire after
one year and require a fresh advanced enrollment/renewal approval. The exact
certificate-validity and clock-edge tests are P12.8 acceptance items.

The first owner's Bluefy page reads the public CA certificate and server pin
through the physically claimed BLE connection without displaying a fingerprint
or installing an OS trust profile. On later BLE use, the retained iOS bond and
full device ID authenticate the returning device; any available locally stored
public pin must also agree. Public pin storage is allowed, but no private key
or Wi-Fi password is persisted by the page. This is **not** a Safari, system
TLS or station-client trust installation.

Advanced station/mTLS enrollment uses a bounded serial-connection approval
sequence to respect the one-link BLE limit:

1. The retained owner phone opens a named **Add station client** window in
   Bluefy and disconnects. This allows one provisional CSR submission without
   granting BLE job control or mTLS authority.
2. A station client such as `wspr5` generates its own P-256 private key locally
   and submits a bounded CSR, intended client name and nonce through an
   encrypted provisional BLE session. The device retains the pending CSR,
   digest and provisional peer for at most 120 seconds after submission. A
   competing CSR is rejected; the station client disconnects.
3. The owner phone reconnects through its retained bond, checks the displayed
   client name and the **full CSR SHA-256 digest** against the station CLI in
   an advanced **Approve client** screen, and starts a fresh Identify. The owner
   physically taps runtime BOOTSEL in the bound window. Both owner bond and
   physical action are required. The device signs only the exact pending CSR,
   commits its public-key digest to a separate bounded client allowlist, and
   records one issuance generation.
4. The station client reconnects to the same provisional peer and receives
   only its signed client certificate and the public device CA certificate.
   It verifies chain, exact device ID and CSR key match. The station CLI and
   owner Bluefy advanced screen display the same **full CA SHA-256 fingerprint**
   for human comparison before the station pins it for TLS. Its private key
   remains on the station host. The provisional BLE bond is then deleted; it
   never becomes a phone owner or local WTP principal. The device admits a
   client only when both its certificate chains to this device CA and its
   public-key digest is in the current allowlist; revocation removes the
   allowlist entry before any asynchronous connection close. Limit the
   allowlist to four independent clients with no silent eviction.

Every pending CSR, owner approval and physical edge binds full device ID, boot,
CSR digest, nonce and enrollment generation. Disconnect before a complete CSR,
timeout, owner change, wrong CSR and storage failure clear pending authority;
planned disconnects between the four steps preserve only the one bounded
pending CSR or issued public certificate. A lost approval response is
reconciled by issuance generation and public-key digest; it never signs a
different CSR on replay. An owner-approved credential is an advanced service
step after the five-step phone commissioning path, never a normal setup field.
P12.10 may use an enrolled `wspr5` fixture for its independent mTLS readback
after the iPhone alone has committed generation 1. The fixture enrollment and
its separate physical action must be recorded and must not be counted as part
of the five-step consumer flow.

This path needs a versioned profile/validator migration: the current profile
requires externally supplied server certificate, server private key and client
CA, while the current validator checks the server certificate against that CA.
The new generated identity/allowlist cannot be implemented by merely filling
the old fields with a self-signed certificate. The old engineering profile path
must be explicitly separated or migrated; it must never overwrite the
consumer CA/private key or silently restore superseded client trust. A
Field-GATT/2 design must specify the new commissioning and client-enrollment
operations while preserving Field-GATT/1 for the documented engineering path
only until a deliberate compatibility retirement.

## Proposed password and SoftAP policy

Recommend retiring the public `wspr-<suffix>` password from **consumer**
authorization after claim. The first claim depends on physical confirmation
plus the resulting retained owner bond, not knowledge of that public value.
Generate a random, device-specific provisioned SoftAP passphrase and rotate it
on access recovery or explicit owner request. Never display it during ordinary
setup. Its owner-authorized service reveal/copy action, if retained, is not
the accepted iPhone fallback join path. A blank device's public SoftAP remains
identity/status read-only and accepts no Wi-Fi, owner, time, trust or job input.

SoftAP itself requires no certificate. The selected engineering contract puts
the provisioned browser API behind HTTPS so Safari can authenticate the Pico
server and protect the browser password, cookie and control traffic after the
phone joins Wi-Fi. The operator asked to revise that Apple workflow. A
self-generated CA read by Bluefy over BLE cannot silently establish Safari
system trust. Apple's
[certificate deployment guidance](https://support.apple.com/en-gb/guide/deployment/dep91d2eb26/web)
recommends avoiding manual root-certificate installation for ordinary users.
The selected direction is Safari over HTTP on the provisioned, device-specific
WPA2 SoftAP, with a short-lived owner-authorized browser session issued through
the retained BLE bond. This selection needs an explicit change to the existing
HTTPS-only field contract, strict AP-interface isolation, a session handoff
that does not ask the user to type a code, and changes to the current Secure
cookie, HTTPS Origin rules and browser code that uses secure-context APIs.
HTTP does not authenticate the Pico to Safari or protect traffic from a party
that knows the SoftAP passphrase. The operator accepted that local
interception risk for this fallback.

The iPhone join remains a hard feasibility gate. Apple's
[Wi-Fi configuration API](https://developer.apple.com/documentation/NetworkExtension/wi-fi-configuration)
is for native apps and requires an explicit user authorization. Bluefy's
[published feature description](https://pnnsoft.com/portfolio/detail/bluefy-web-bluetooth-api-solution-for-ios-devices)
documents Web Bluetooth, not a web-callable WPA2 join API. Thus a code-free
WPA2 join from Bluefy alone is **unproven**; that conclusion is an inference
from the published APIs, not a live iPhone result. A manual passphrase entry
does not satisfy the selected code-free requirement. A Wi-Fi configuration
profile would add a separate Settings installation ceremony and is not part
of this proposal. If the iPhone join or owner-to-Safari session handoff cannot
be demonstrated, P12.7 returns to design instead of substituting a password,
certificate installation or native client without operator approval.

The generated SoftAP passphrase remains owner-only. Blank SoftAP remains
read-only; no credential may cross its public HTTP surface or a certificate
warning. P12.11 cannot be accepted for Apple users until one route has an
exact implementation, first-use, authorization, wrong-device and recovery
test plan.

## Proposed recovery semantics

All recovery starts from a named Bluefy screen bound to the encrypted current
link and full device identity. The selected action drives a distinct LED
pattern and uses a new physical press edge; no gesture is interpreted from
BOOTSEL held at boot. Access recovery can be requested by an unowned/new phone
through a narrowly scoped recovery-only GATT admission path; merely pairing or
requesting the screen grants no control. It needs one short runtime tap after a
prominent **Recover access** warning.
It clears owner/provisional bonds and local-access credentials, rotates the
SoftAP passphrase and access epoch, then offers a 120-second new-owner window.
It preserves the runtime TLS/Wi-Fi profile, station, schedules and watermark.

Provisioning reset is available only after owner recovery or owner admission.
The owner chooses **Reset network setup**, confirms its preservation/clearing
summary, then gives two separate short taps in two prompted LED windows. It
commits an unprovisioned source tombstone and revokes network trust while
preserving station, schedules and watermark. Full operational erase is named
**Erase all operational data** and requires an additional explicit on-screen
confirmation plus a third separate tap/window. It also clears station,
schedules and watermark. Presses alone, without an exact pending operation and
its bound nonce/level, cannot start any reset. All levels reject loaded,
owned, armed, running, failed, active-output or unknown-output states.

The existing durable `reset_pending` protocol remains the power-cut rule:
before intent commit, old authority is intact; after intent commit, only
recovery-only service runs until completion; after intent clear, the selected
new state is authoritative. A lost success reply is reconciled by exact boot,
source, access epoch and generation readback, never by blind replay. Any bond
erasure failure leaves BLE local control disabled. The physical gestures and
LED patterns above are proposals until the safe sampler and UX are accepted.

## Proposed disconnect language

| Boundary | Bluefy wording | Device/client action |
| --- | --- | --- |
| Before any validated transaction | **Connection lost. Reconnect to try setup.** | No commit; clear input secrets and provisional authority. |
| Validation or durable commit in progress | **Checking setup. Keep this Pico powered on.** | Reconnect to the same full identity and query generation/owner/boot; do not send another transaction. |
| Committed generation, activation pending | **Finishing setup. Reconnecting...** | Wait for terminal response release/restart and verify the exact generation. |
| Readback proves generation and readiness | **Setup complete.** | Clear all temporary Wi-Fi and cryptographic buffers. |
| Readback proves no commit or fail-closed fault | **Setup did not finish.** | Offer an explicit safe retry or a named recovery path; preserve diagnostics without secrets. |

## Approval decisions and exit gate

The operator has selected the BOOTSEL, device-CA and certificate-free SoftAP
directions. The operator must
approve or revise this complete product contract, especially:

1. Runtime BOOTSEL as the stock-board claim/recovery input, with the proposed
   tap windows and a hard safety-validation gate.
2. The on-device per-device CA/private-key exception to the current off-device
   CA rule, the serial CSR/owner/physical enrollment, the four-client
   allowlist and station-side pinning path.
3. The provisioned HTTP/SoftAP route, including a demonstrated code-free WPA2
   join, owner-to-Safari handoff and explicit replacement of the current
   HTTPS-only browser security rules without changing station TLS.
4. Retirement of the public default from consumer authority and the proposed
   owner, second-phone and three reset ceremonies. The operator has accepted
   the CA-key extraction and Just Works active-relay limitations; the
   acceptance record must retain them without describing either as prevented.

After approval, update the normative field-access contract, the versioned
GATT decision, Bluefy UX specification, roadmap and Stage A cases together.
If approval changes the wire contract, version it before P12.8. Until these
choices are accepted, P12.7 stays open, P12.8-P12.12 stay blocked and no
commissioning implementation or live reset is authorized.
