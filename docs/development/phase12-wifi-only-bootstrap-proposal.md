# Phase 12 Wi-Fi-only network bootstrap proposal

Status: **DESIGN ONLY — NOT APPROVED FOR IMPLEMENTATION OR HARDWARE**.
On 2026-09-26 the operator chose a first-run path for a blank Pico that uses
its own SoftAP and a browser, without BLE, Bluefy, a native iPhone app, a setup
code, a certificate installation or a USB command. This slice saves only
station Wi-Fi credentials and proves network join. Owner claim, station TLS,
mTLS-client enrollment, scheduling and job control remain later work. The
operator chose fresh Pico/browser encryption for the submitted Wi-Fi password
and accepted the remaining active relay risk.

This is the separate bootstrap design required by the
[Phase 12 roadmap](phase12-plan.md) for commissioning without BLE. It would
replace the [field-access contract](phase12-field-access-contract.md) rule that
blank SoftAP is read-only **only after this proposal is accepted**. The current
read-only implementation, including its best-effort captive landing, remains
the baseline until then. That landing accepts no credential and does not join
station Wi-Fi. It is Stage A
network/provisioning work, not Stage B RF coexistence. The
[adversarial design review](phase12-wifi-only-bootstrap-review.md) records
corrected findings and remaining feasibility gates.

## Intended user experience

1. Power on the blank Pico. Its clearly named **open** SoftAP offers only a
   local identity/status page at first. On joining the AP, the Pico attempts
   to make iOS open its captive browser on the local setup page. This is a
   best-effort convenience, not an acceptance assumption: if the sheet does
   not open or cannot finish setup, the page is also available in Safari at
   `http://192.168.4.1/`. No Internet, app or certificate prompt is needed.
2. Choose **Connect this Pico to Wi-Fi**. The browser creates a fresh key and
   request nonce before the Pico identifies itself through its LED. One short
   runtime BOOTSEL tap binds a bounded request slot to that browser public key
   and nonce. A boot-held button is invalid. The page does not ask for a code
   or display a full device ID.
3. Enter the station SSID and password. The page encrypts both with a fresh
   browser/Pico key exchange before sending them across the open AP. The Pico
   trials station association and DHCP while keeping the AP available.
4. Show **Network connected** only after the exact credentials have committed
   durably and station association plus an address are observed. A failed
   join remains on the AP with a safe retry path; an unknown result says
   **Checking connection** until the device reports the committed state.

The screen must say **Network connected**, not **Setup complete**. It must not
claim an owner, certificate, station API, RF permission or complete consumer
commissioning. A normal browser may show that this AP has no Internet; that
system message is not a Pico failure.

### Captive launch and Safari fallback

The Pico cannot command iOS to open a browser. For the **blank network-only
bootstrap AP only**, advertise `192.168.4.1` as the DNS server in DHCP and add
an AP-interface DNS responder. Answer bounded IPv4 address queries with the AP
address while that AP is active; return a bounded negative answer for other
record types. If iOS then performs a plain-HTTP connectivity probe, return a
`302` redirect to `http://192.168.4.1/` with `Cache-Control: no-store`.
Redirect only safe probe/navigation GET requests;
never intercept HTTPS, impersonate an Internet service, proxy traffic, or
accept credentials on a foreign Host. Keep redirects and DNS answers short
lived, AP-bound and disabled when the bootstrap AP stops. The local setup page
must use an exact AP-local Host; its mutating requests retain the strict
same-origin admission below. A provisioned SoftAP and station interface do
not acquire this DNS behavior.

The captive sheet may be omitted, closed early or re-opened differently by
the phone. It may also lack capabilities needed by the locally bundled
cryptography. The page must feature-detect its cryptographic and random
sources before showing the Wi-Fi form. If the captive sheet cannot run the
complete flow, it shows only concise directions to open the fixed address in
Safari. Never ask for the station password in a page that cannot encrypt it.
Keep the AP available until a durable result and explicit browser
acknowledgement, so a captive sheet disappearing is not mistaken for a
successful join. If iOS offers **Without Internet**, that choice must keep the
phone associated with the Pico AP; the on-page instructions may explain it.

The trigger and full form must be tested on the selected iPhone/iOS version.
The acceptance record separately states whether automatic launch occurred,
whether the captive sheet could complete the encrypted form, and whether the
Safari fallback worked. A missing automatic launch is a usability limitation,
not a false network-join result. The
[Apple captive-network instructions](https://support.apple.com/en-us/102554)
describe the system behavior but do
not guarantee a launch for this device. The standardized DHCP captive-portal
option points to a [Captive Portal API](https://www.rfc-editor.org/rfc/rfc8910)
that requires HTTPS and a validated certificate under
[RFC 8908](https://www.rfc-editor.org/rfc/rfc8908); it is not the chosen
certificate-free mechanism and must not be advertised as implemented.

## Admission and authority

- Only an explicitly unprovisioned device with checked full identity, checked
  station MAC and authoritatively inactive output may expose the bootstrap AP.
  A healthy-unclaimed access record may expose read-only status; an exactly
  all-erased access journal may expose the same read-only page only after those
  checks and must be durably initialized by the later physical action before
  any credential is accepted. An invalid non-erased journal, pending reset,
  ambiguous source mode or output-unknown state fails closed. Erasure alone is
  not proof of factory-virgin status or authority to accept credentials.
- The AP may advertise read-only identity/status before confirmation. A single
  fresh runtime BOOTSEL release edge authorizes only one pending network-only
  transaction, bound to full device ID, boot ID, browser ephemeral public key,
  request nonce and deadline. The later encrypted submission binds its exact
  ciphertext digest to that slot. Browser TCP connections may change between
  page load and submission; no security claim depends on retaining one socket
  or IP address. The gesture does not create an owner or authorize any other
  operation. Competing requests receive busy.
- Require the exact AP-interface Host and same-origin browser POST, an explicit
  JSON content type and request header, bounded body and no cross-origin
  credential submission. The ephemeral key/nonce and physical grant still
  carry authority; HTTP cookies and an IP address do not.
- The selected BOOTSEL sampler remains subject to the P12.7 flash/XIP,
  second-core and radio-scheduling safety gate. No implementation may copy a
  stock polling example and infer safety. If the sampler fails the gate,
  return to design; do not substitute an unconfirmed remote button press.
- The open AP and local HTTP page do **not** authenticate the Pico to the
  browser. An active nearby relay can replace the page or intercept the key
  exchange and obtain Wi-Fi credentials. The operator accepted this risk.
  Physical confirmation limits ordinary nearby write access but does not
  cryptographically defeat a live relay.

## Credential transport

Use a fresh Pico X25519 key pair and browser X25519 key pair for each attempt.
The proposed suite is X25519, HKDF-SHA-256 and ChaCha20-Poly1305 with a
256-bit derived key, 96-bit random AEAD nonce and 128-bit tag. The `start`
request carries the browser's 32-byte public key and 128-bit random request
nonce as unpadded base64url in strict JSON. Its reply carries a one-use slot,
Pico 32-byte public key, boot ID and monotonic deadline. The Pico starts
Identify only for that slot. The physical tap grants it once. The later
`submit` request carries a fresh request ID, AEAD nonce and ciphertext over
the exact `{ssid,password}` JSON. HKDF salt and AEAD associated data bind the
protocol version, full device ID, boot ID, slot, both public keys, request
nonce and request ID in a fixed canonical encoding. A read-only status route
reports only the source mode, generation, join/address state and a request-ID
digest for response-loss reconciliation; no key or password appears there.
Use SHA-256 of that canonical transcript as the HKDF salt and the fixed label
`WsprryPico network-only AEAD v1` as HKDF info; use the transcript itself as
AEAD associated data. The same fixed field order and encoding must appear in
cross-language vectors.
Reject invalid/all-zero shared secrets, reused nonces, wrong device/boot/slot,
stale or replayed requests, invalid tags and any plaintext credential
submission. Scrub transient secrets on every terminal path. Fix exact JSON
field names, byte encoding, bounds and known-answer vectors in a versioned
wire document before implementing the parser or browser page.

The page is served over HTTP, so it cannot assume browser secure-context APIs
such as `crypto.subtle`; the [Web Cryptography specification](https://www.w3.org/TR/WebCryptoAPI/)
marks `subtle` as secure-context-only while separately defining
`getRandomValues`. Browser cryptography must be bundled locally with
reviewed provenance and a compatible license; a cryptographically secure
random source must be demonstrated on the selected browser. No remote script,
analytics, credential service or browser-persistent secret is allowed. This
design protects against passive nearby listening to the credential exchange;
it deliberately does not authenticate the page against active replacement.

## Storage and network activation

- Introduce a versioned **network-only** profile source in the existing
  transactional profile journal, rather than writing the legacy standalone
  Wi-Fi fields. The record contains only full device binding, SSID and password;
  it has no server key, certificate, client CA,
  owner or job principal. Preserve station identity, schedules and watermark
  stores byte-for-byte. A later full profile must replace this source
  transactionally; a tombstone or corrupt newest record must never resurrect
  network credentials from the legacy base configuration.
- Validate the candidate in RAM, trial station association and DHCP, then
  commit the network-only record once. A failed join or cancelled attempt
  writes no new network record. If commit fails, report failure even if the
  transient station link is up, and disable that transient link before retry.
  Response loss is reconciled from journal generation and network state;
  never blindly resubmit.
- Keep the AP and its status page available through the terminal response.
  Withdraw the AP only after positive browser acknowledgement and stable
  station service, with a bounded timeout. If the station later fails, the
  same read-only AP may return; another physical confirmation is required to
  replace credentials. Test AP/STA channel and DHCP coexistence on the target.
- In network-only mode, station DHCP/SNTP may run, but no station TLS/WTP/HTTPS
  listener, browser job API, credential enrollment or scheduler/RF authority
  becomes available as a consequence of this bootstrap. Existing USB-local
  engineering authority is a separate path and gains no new permission.
- This journal write consumes a profile generation. The roadmap's old
  full-commissioning `generation 1` expectation cannot also describe a later
  full profile unless generation numbering is redesigned. Record exact
  network-only and later full-profile generations in the revised plan.

## Expected source changes after approval

| Existing boundary | Required change |
| --- | --- |
| `PicoSoftAp` and `SoftApCoordinator` | Add an explicitly unprovisioned open-AP mode, keep the provisioned WPA2 fallback distinct and bound AP lifetime and AP/STA coexistence. The pinned SDK supports `CYW43_AUTH_OPEN`, but the current adapter always chooses WPA2. |
| AP-local DNS and HTTP captive detection | Extend the read-only captive landing with the later bootstrap page while retaining AP-interface-only DNS answers and safe HTTP GET redirects. Never intercept TLS or enable this on the provisioned AP or station interface. |
| `PicoBootstrapServer` and HTTP parser | Preserve the public GET identity surface; add only the versioned challenge, physically authorized encrypted submission and bounded network status. The current server rejects every non-GET request. |
| Access journal and BOOTSEL adapter | Add healthy-unclaimed initialization and a one-slot physical grant without interpreting erased or corrupt records as general authority. Prove safe runtime BOOTSEL sampling first. |
| Profile journal and runtime source selection | Add network-only source validation, old-or-fail-closed commit and reboot selection. Never expose legacy Wi-Fi under unprovisioned/tombstone mode. |
| Network, scheduler and browser admission | Trial AP/STA networking without station TLS or job authority; preserve the existing one-`JobService` and output gates. |
| Browser artifact | Bundle the reviewed offline page and crypto implementation without external fetches or persistent credentials; test on the selected browser. |

## Required acceptance before implementation and physical work

Approve this bounded change to blank-AP policy, owner semantics, credential
confidentiality limit, storage source and generation meaning in P12.7. Update
the normative field-access/security contract, protocol version, Stage A cases
and user-facing wording together. Hardware-free tests must cover malformed
requests, competing claimants, physical-window expiry, AEAD vectors and
tampering, failed AP/STA coexistence, DHCP timeout, commit interruption,
response loss, reboot selection, legacy-credential nonresurrection, secret
scrubbing, AP-only DNS and redirects, HTTPS non-interception and Safari
fallback. Cross-build the exact RF-inhibited image and verify resource bounds.

Target acceptance requires separate explicit authority for the exact Pico,
flash/BOOTSEL operation, AP and station radio operation, credential use,
duration and restoration. First prove blank read-only admission, then the
physical gate and one network-only join, durable readback after reboot,
wrong-device and failed-join paths, AP withdrawal/fallback and final
empty/unowned, RF-inhibited, output-inactive restoration. Neither source tests
nor native-Pi exercises substitute for the selected phone/browser acceptance.
