# P12.7 Safari and SoftAP commissioning proposal

Status: **APPROVED DESIGN; IMPLEMENTATION OPEN** (2026-09-27).
The operator selected **Safari and SoftAP only** as the consumer client for
P12.7–P12.12. Bluefy, BLE ownership and a native app are outside this proposed
consumer path. The operator subsequently approved this complete owner, trust,
reset and provisioned-AP design in the
[P12.7 decision](phase12-7-decision.md). P12.8 implementation and physical
acceptance remain open.

The separately approved [Wi-Fi-only bootstrap](phase12-wifi-only-bootstrap-proposal.md)
is already implemented in source at `fb091f8` and has its own target acceptance
gate. It saves only network credentials. Its open AP, encrypted submission and
one BOOTSEL action are the starting constraints for this proposal, not proof of
an owner or a safe general-purpose management channel. The
[engineering field-access contract](phase12-field-access-contract.md) and
[Field-GATT/1](../protocol/Field-GATT.md) remain the implemented baseline
until a versioned replacement is approved and built.

## Decisions already made and decisions still open

| Topic | Current decision or gate |
| --- | --- |
| Consumer client | Safari on the Pico SoftAP only; no Bluefy, BLE owner bond or native app. |
| Setup code | No per-device code, pairing PIN, QR label, extra password, USB command, PEM or certificate installation in ordinary setup. The ordinary user enters only the home Wi-Fi password. |
| AP association | Blank AP is open. The approved design uses an open provisioned AP too, so owner access does not introduce an AP password. AP/STA target qualification remains open. |
| Claim | One prompted runtime BOOTSEL press/release tied to the displayed board and one pending browser request. Its use beyond the proven blank, RF-inhibited, core-1-absent image needs a hard safety gate. |
| Confidentiality | Fresh browser/Pico key exchange encrypts submitted secrets against passive listeners. HTTP page replacement and active relay can defeat this; the operator accepted the active MITM risk. |
| Server trust | A per-device CA/private key on the Pico is acceptable, including ordinary-flash extraction risk. Safari uses certificate-free AP HTTP; enrolled station clients pin the device CA for mTLS. |
| Browser owner | A Safari-generated private signing key retained on this phone, with only its public key and owner epoch stored on the Pico. This replaces the old BLE owner bond. |
| Full contract | Approved in the P12.7 decision. Shared-origin exposure and the physical/recovery design are accepted, while implementation and target safety gates remain open. |

## Proposed ordinary experience

1. Power on the Pico and join its named **open** Wi-Fi network. iOS may display
   the local captive page automatically. That sheet gives a **Continue in
   Safari** route; the fixed-address Safari fallback remains available. No AP
   password is requested.
2. In Safari, choose **Set up this Pico**. The page reads the full device
   identity internally, shows an identifying LED action, and asks for one
   BOOTSEL tap/release on that board. The user does not type an ID or code.
3. Enter home Wi-Fi name/password and ordinary station callsign, four-character
   locator and WSPR power. Defaults cover time and transport details.
4. Choose **Connect** once. The page shows **Checking setup** through station
   trial, durable commit, response loss and restart. It never blindly retries
   an uncertain write.
5. Show **Setup complete** only after the exact device, retained Safari owner
   public key, committed generation, station association/address, controller
   time and configuration readback agree.

The captive sheet may be ephemeral; it must not create an owner key unless
persistent storage, cryptographic random generation, navigation and return
behavior are proven there. The conservative product flow creates and retains
the owner key in Safari before any owner commit. A failed private-mode or
storage capability check offers an explicit retry in a supported Safari
context before asking for the home Wi-Fi password. The page must never claim
that an automatic captive launch or cross-app storage handoff is guaranteed
without selected-iPhone evidence.

A blank Pico may follow either path:

- **Direct full setup:** generation 0 to full generation 1, if the approved
  consumer transaction can do this atomically.
- **Network-only first:** the existing Wi-Fi-only transaction writes network
  generation 1; later full setup must upgrade atomically to full generation 2.
  Network connected is not Setup complete, and the Wi-Fi-only action does not
  become owner authority retroactively. The current network-only image
  withdraws its AP after acknowledgement or a bounded timeout. A Safari-only
  upgrade would then have no discovery path while station Wi-Fi is healthy.
  The approved design keeps the open, unowned AP available in network-only mode
  until full commissioning or an explicit reset. That is a deliberate change
  to the network-only AP lifetime and needs P12.7 approval plus AP/STA resource
  and channel validation; the earlier Wi-Fi-only target result remains valid
  only for its own recorded image and contract.

## Proposed browser origin and retained owner

The owner credential is a random Safari-generated signing key. Bundle the
signing implementation locally; do not depend on `crypto.subtle` on plain
HTTP. Require `crypto.getRandomValues` and a deterministic implementation
self-test before rendering the form. Persist the private key in Safari's
site storage and read it back **before** the physical claim can commit. Never
send it to the Pico, export it as a file, display it, or place it in a URL or
cookie. Store only the owner public key, owner epoch and bounded revocation
state on the device. Every mutating request carries a signature over method,
path, canonical body digest, full device ID, boot ID, owner epoch, fresh
server nonce and expiry. A challenge is single-use; reconnect and response
loss reconcile by device ID, owner epoch and generation.

The open AP also exposes HTTP response bodies to passive nearby listeners.
The owner API therefore needs a fresh browser/Pico session key exchange
authenticated by the retained owner signature, with AEAD on private requests
and responses. Public identity/status stays deliberately nonsensitive. The
exact signing algorithm, canonical encoding, session lifetime, sequence
numbers, replay cache, response-loss reconciliation and independent vectors
belong in a new versioned owner-HTTP contract before implementation. A plain
HTTP cookie or request signature alone is insufficient to hide Wi-Fi, trust,
station or job data on an open AP.

The fixed `http://192.168.4.1` Safari origin is shared by every Pico AP.
Safari stores keys indexed by the Pico's **full** device ID, and the page
verifies that ID and the corresponding public key/owner epoch before use.
This prevents accidental cross-board authorization by honest firmware, but
same-origin storage does **not** isolate keys from a malicious page served by
another board at that address. Any such page could read all retained Pico
owner keys. This is a concrete consequence of the operator's accepted active
page-substitution risk and must be included in the P12.7 approval. A short
SSID suffix is never an authority key. Do not claim browser origin isolation
across devices or invent a separate hostname without a new decision.

The active page-substitution/relay risk is accepted: an attacker serving
malicious HTTP JavaScript at the same apparent origin could read the Safari
owner key or trick the user during a BOOTSEL action. Physical confirmation,
signatures and encrypted credential submission block ordinary passive
listeners and accidental wrong-device use; they do not defeat that active
attacker. This limit must be visible in the accepted security contract,
without a code or certificate step added to the consumer flow.

## Proposed claim and configuration transaction

A single pending claim slot binds full device ID, boot ID, browser owner
public key, fresh request nonce, exact page origin and deadline. Identify
starts only for that slot. One ordinary runtime BOOTSEL press and release
within the prompted window grants it once; the user does not time the hold.
The device debounces the edges and bounds a stuck hold. A held-on-boot button, stale
level, timeout, second claimant, wrong board or changed owner key fails
closed. The owner public key commits only after physical confirmation and
a complete journal operation. A claimed but unconfigured owner may return
in a bounded recovery state; it cannot gain station TLS, WTP or RF authority
from the claim alone.

The configuration transaction binds the owner epoch, exact validated Wi-Fi
and station settings digest, fresh request ID and full identity. Reuse the
approved X25519/HKDF/ChaCha20-Poly1305 credential envelope where compatible,
with a separately versioned full-commissioning transcript. Do not extend
WiFi-Bootstrap/1 to mean owner claim. Generate a per-device CA and separate
server key after valid entropy and bounded UTC are available, and commit the
complete profile and trust authority as one versioned source. Station trial,
DHCP and time must be positive before reporting ready. Persist exactly one
new generation, retain unrelated station/schedules/watermark data, deliver a
terminal response before activation/restart when possible, and recover a
power cut to an old complete generation or a fail-closed state. Never mix a
new profile with old CA/client authority or resurrect legacy factory data.

A generation-only status is insufficient to establish success: the browser
must read back its owner public-key digest/epoch and exact request digest,
source mode, full device ID and ready state. Unknown results remain
**Checking setup**. No WTP, station browser API or RF control is admitted
until the full profile and its separate authorization gates are valid.

## Proposed generated trust and station-client enrollment

The Pico creates a per-device P-256 CA and separate TLS server key. The CA
signs only this device's server identity and individually approved client
CSRs. The CA/private server keys remain on the Pico in ordinary flash;
physical extraction resistance is not claimed. The device CA public
certificate may be exported. The server certificate binds the full device
identity and exact station hostname, rotates transactionally before expiry,
and is never treated as publicly trusted by Safari. Station mTLS/HTTPS
remains mandatory and independent of the AP HTTP fallback. A missing
clock, entropy, valid SAN, matching key, complete chain or valid client
allowlist blocks activation. CA rotation needs explicit owner/physical
approval and an old-or-fail-closed migration.

The device CA is proposed to expire after ten years. The server certificate
expires after one year and renews automatically under the same CA in its
last 30 days when valid UTC is available; renewal generates a new server key
and activates only after a complete replacement validates and commits. An
expired server certificate never enables a Safari or station TLS warning
bypass. Client certificates expire after one year and require a fresh
advanced owner/physical approval to renew. A failed renewal keeps the prior
complete still-valid identity or enters fail-closed recovery. A provisioning
reset destroys the per-device CA/server private keys and client allowlist;
access recovery preserves them but revokes browser owners and sessions.

Advanced **Add station client** runs through the provisioned AP while the
owner's Safari key is present. A station client such as `wspr5` generates its
private key locally and submits a bounded CSR and friendly name; only one
pending CSR exists. The owner sees that exact request in Safari, approves it
with a fresh BOOTSEL action, and the Pico signs only that CSR and commits its
public-key digest to a four-client allowlist. The station client retrieves
only its signed certificate and public device CA, then pins the CA and exact
device identity for TLS. A replay, wrong CSR, changed owner epoch, timeout,
interrupted commit or lost response cannot sign another request. Revocation
removes the allowlist entry before asynchronous connection closure. This
advanced service sequence is separate from the five-step consumer setup and
must be tested for simultaneous phone and station-client AP association;
it may not require manual certificate administration from an ordinary user.

## Proposed provisioned SoftAP fallback

The provisioned AP is open and AP-local HTTP remains certificate-free. Because
Safari/SoftAP is the **only** consumer owner client, the provisioned AP remains
available while the device is healthy, including when station Wi-Fi works;
otherwise the owner could not reach the page to enroll a station client,
manage another phone or initiate recovery. This is a deliberate change to the
old fallback-only/AP-withdrawal policy. Resource, channel, station coexistence
and RF scheduling effects are hard Stage A and later Stage B gates. It may
expose read-only identity/status before authentication. Every mutation
requires a live Safari owner-key challenge/signature and encrypted session,
exact AP-local Host, full device ID, body digest, expiry/replay protection,
AP-interface isolation and per-operation authorization. Private reads use
the same authenticated, encrypted session. Sensitive trust, new-phone, reset and erase
actions also require a fresh physical gesture. No public default application
password, AP passphrase or BLE bond grants consumer authority. Station
mTLS/HTTPS and WTP use their own principals and the same one `JobService`;
AP control cannot silently inherit a USB or station session.

AP DNS and captive redirects are bounded to the AP interface and must not
intercept HTTPS or proxy traffic. Across station loss and return, the owner
Safari page must still find the same numeric origin and full-ID-indexed key.
A blank AP retains only its separately approved encrypted Wi-Fi-only
write surface and read-only status; it accepts no owner, trust, station fields,
WTP or job commands until this full commissioning contract is implemented
and accepted. Test wrong-device, cross-board same suffix, cross-origin,
unauthorized read/write, page replacement limit, replay and captive-sheet
behavior on the actual iPhone.

## Proposed phone lifecycle and reset levels

A second phone generates and retains its own Safari key on the exact
device-specific origin. The first owner opens one named enrollment window;
the second phone presents its public key; the first owner approves the exact
pending key with one fresh physical tap. Capacity is four owner keys with no
silent eviction. Removal revokes application authority before connection
teardown. Losing the Safari site data is equivalent to losing that phone's
owner credential; it must not be silently repaired from a cookie, Wi-Fi
association or another board's origin.

**Recover access** is a distinct physical-possession path that works without
the old phone. A new Safari instance shows an explicit warning and binds a
fresh owner key to one recovery request; two separately prompted runtime taps
within bounded windows revoke all old owner keys and access sessions, rotate
the owner epoch and grant the new owner while preserving the full operational
profile, station, schedules and watermark. **Reset network setup** requires
an authenticated owner, explicit preservation summary and two separate
prompted taps; it revokes network/owner trust and commits an unprovisioned
tombstone while preserving station/schedules/watermark. **Erase all operational
data** additionally requires an on-screen erase confirmation and a third
separate tap; it clears those stores too. Presses alone never start any reset.
Loaded, owned, armed, running, failed, active-output or unknown-output states
reject every reset. The existing `reset_pending` intent remains the power-cut
rule: before intent old authority remains; after intent only recovery service
runs; after completion only the new selected state is authoritative. Bond
language in the old proposal is superseded by browser-key revocation.

The runtime BOOTSEL sampler is currently evidenced only on a **blank,
RF-inhibited, core-1-absent** image. A separate core-1 flash-reader physical
probe failed. P12.7 acceptance must require a concrete parked-core and
flash/XIP/radio-safe mechanism for provisioned actions, or narrow them to an
explicitly entered maintenance state with a proven path from an idle device.
The device must not enable a recovery/erase prompt it cannot safely sample.
This is a hard design and target gate, not a reason to reuse the failed
core-1 behavior.

## Approval and implementation gate

P12.7 approved the owner-key model, shared-origin exposure, open
always-available AP, network-only AP lifetime change, generated CA, advanced
client enrollment and distinct reset ceremonies. The exact
versioned owner-HTTP wire protocol, journal schema/migration and Pico/browser
cryptographic vectors are P12.8 design artifacts that must be complete and
reviewed before corresponding source implementation. First-use Safari storage,
safe provisioned BOOTSEL, AP/client concurrency and positive station-client
readback are later target acceptance gates; failure returns to the contract
instead of silently adding a code, certificate or app. Adversarially review passive exposure,
active page replacement, wrong-device claim, origin collision, replay,
competing owners, storage loss, power cuts, trust resurrection, RF authority
and restoration. Record the accepted revision/date and all deliberate limits.

Update the normative field-access/security contract, Phase 12 roadmap,
Stage A case list and any affected wire version together during P12.8.
WiFi-Bootstrap/1 remains network-only. Do not claim Safari owner or
full-profile commissioning acceptance from this design approval.
