# WiFi-Bootstrap/1 proposed wire contract

## Current UI correction

The [Wi-Fi-first portal correction](../development/phase12-safari-open-setup-revision.md#wi-fi-first-correction)
supersedes this proposal's BOOTSEL and Safari instructions. The encrypted
request format remains version 1. The current source grants one open-AP
transaction without a button, accepts later network-only and consumer Wi-Fi
replacement, and restarts after a saved result. The older sections below are
retained as historical proposal text.

The current `POST start` response has `version`, `device_id`, `boot_id`,
`slot_id`, `pico_public_key` and `slot_expires_in_ms`; it has no tap deadline.
The browser displays Wi-Fi fields immediately, opens a slot only on Save, and
reconciles a verified commit using the exact request digest and next journal
generation. `GET status` may report `consumer` as well as `unprovisioned`,
`network_only` and `fault`. A replacement retains the prior network if the
trial fails. A successful save leaves the open AP available through its terminal
reply and schedules a restart after the ACK is delivered, with a bounded
fallback. After restart, the AP is normally off while saved station Wi-Fi is
usable. It starts immediately with an erased journal, returns after station
loss, or opens after an idle RF-inhibited 10-second BOOTSEL hold and release.
The AP-only request envelope, encrypted plaintext, header checks and one-use
slot remain as specified below; historical press-to-save, blank-only and
generation-1-only statements no longer apply.

The current optional `POST /api/bootstrap/v1/time` route accepts exactly
`version`, `device_id` and decimal-string `utc_ms` under the same AP-local
Host, Origin, content-type and bootstrap-header admission. It replies with
`version` and `state` (`accepted` or `ignored`). The portal sends this hint on
opening and about every 30 seconds; it creates no setup slot and contains no
credentials. The Pico bounds UTC to 2025–2099, assigns one second of
uncertainty, ignores inconsistent browser jumps, and never lets browser time
replace a trusted source. Fresh SNTP remains required for TLS generation.

Status: **DESIGN APPROVED; SOURCE TRANSACTION IMPLEMENTED; TARGET ACCEPTANCE OPEN**. This describes only a
blank-device, network-only bootstrap over the open, AP-local HTTP captive
page. It does not grant an owner, station API, TLS trust, scheduler or RF
authority. The [execution prompt](../development/phase12-wifi-only-contract-execution-prompt.md)
and [product proposal](../development/phase12-wifi-only-bootstrap-proposal.md)
carry the approval and target gates.

The historical [P12.7 Safari/SoftAP contract](../development/phase12-7-decision.md)
changed **AP lifetime only** at that time: a network-only AP remained available
after station join for later full commissioning. The current lifetime is
specified above. The `fb091f8` physical trial used the prior
post-commit withdrawal behavior; its evidence is not rebound to this source
change. The historical withdrawal paragraphs below describe that image.

## Admission and state

The device must be authoritatively unprovisioned at generation 0, with a
healthy or exactly erased access journal, checked full identity and station
MAC, and known inactive output. A damaged/ambiguous journal, pending reset,
factory bundle, runtime profile or output-unknown state rejects every
bootstrap mutation. Exactly erased access storage is initialized durably to a
healthy unclaimed state **after** the valid physical edge and before accepting
credentials. Its interrupted initialization must fail closed on reboot.

There is at most one slot. `POST start` creates a fresh Pico ephemeral X25519
key and a random 128-bit slot ID, binds the browser key, 128-bit request nonce,
full device ID and current 128-bit boot ID, starts Identify, and returns the
slot. A runtime BOOTSEL **press then release** observed within 60 seconds of
start grants that slot once; a boot-held button or stale level never grants.
The slot expires 180 seconds after start. Another start while occupied is
busy. Its encrypted submit consumes the grant exactly once, even if join,
validation or commit later fails. Cancellation, expiry, reboot or any other
source transition destroys the slot and ephemeral secrets, except that a
successful commit may retain only the derived acknowledgement verifier and
request digest for a bounded AP-withdrawal window. The X25519 private key is
cleared after key derivation; plaintext credentials and the AEAD key are
cleared after the trial and terminal commit/failure path. A new attempt uses new keys,
nonce, slot and request ID.

`POST submit` validates the complete envelope and authenticated plaintext in
RAM before a station trial. It records the ciphertext digest for the slot and
rejects a different digest or duplicate submission; a lost response is
reconciled through read-only status rather than resubmission. Trial association
and DHCP must pass before one transactional network-only journal commit.
Commit failure disables the trial link and reports failure. A committed record
is generation 1 from a blank generation 0; after reboot it remains selected
without legacy Wi-Fi fallback. Only a later full-profile upgrade from that
source becomes generation 2. Direct full commissioning from blank can remain
generation 1. `connected` requires durable commit plus observed station
association and address. A disconnect after commit yields a committed but
currently disconnected status, never a rollback claim.

The AP remains available for the terminal response and status reconciliation.
The browser sends an authenticated acknowledgement after it has displayed the
durable result; the device withdraws the AP only when station service is
stable. If acknowledgement is lost, a bounded AP timer may withdraw it only
after stable station service; the AP may reappear read-only if station service
later fails. Replacement credentials require a new physical grant. Unknown
results are displayed as **Checking connection**.

## Encoding and routes

All requests use HTTP/1.1 on the bootstrap AP interface only. Mutating
requests require exact `Host: 192.168.4.1`, exact
`Origin: http://192.168.4.1`, `Content-Type: application/json`, and
`X-WsprryPico-Bootstrap: 1`. Reject duplicate headers, duplicate JSON keys,
unknown keys, transfer encodings not explicitly supported, bodies over 512
bytes, foreign hosts/origins and station/provisioned-interface requests.
Responses use `Cache-Control: no-store`; errors contain no secret. No route
accepts plaintext SSID or password. JSON number `version` is exactly `1`.

| Route | Exact JSON request keys | Exact JSON response keys |
| --- | --- | --- |
| `POST /api/bootstrap/v1/start` | `version`, `device_id`, `browser_public_key`, `request_nonce` | `version`, `device_id`, `boot_id`, `slot_id`, `pico_public_key`, `tap_expires_in_ms`, `slot_expires_in_ms` |
| `POST /api/bootstrap/v1/submit` | `version`, `device_id`, `boot_id`, `slot_id`, `request_id`, `aead_nonce`, `ciphertext`, `tag` | `version`, `state`, `generation`, `request_id_digest` |
| `GET /api/bootstrap/v1/status` | none | `version`, `source`, `generation`, `slot_state`, `slot_id_digest`, `join`, `address_ready`, `request_id_digest` |
| `POST /api/bootstrap/v1/ack` | `version`, `device_id`, `boot_id`, `slot_id`, `request_id`, `ack_tag` | `version`, `state` |

`device_id`, `boot_id`, `slot_id`, `request_nonce` and `request_id` are each
exactly 32 lowercase hexadecimal characters representing 16 bytes. The two
public keys are 32 bytes encoded as unpadded canonical base64url (43
characters). `aead_nonce` is 12 bytes, unpadded canonical base64url (16
characters), drawn fresh by the browser. `ciphertext` and `tag` are separately
unpadded canonical base64url; the tag is exactly 16 bytes (22 characters).
The ciphertext is 11–97 bytes. Reject noncanonical base64url, invalid keys,
low-order/all-zero X25519 shared secrets, stale or reused IDs/nonces and
integers outside their stated domains. `tap_expires_in_ms` is at most 60000
and `slot_expires_in_ms` at most 180000. These are display hints; the device's
monotonic deadlines are authoritative.

The authenticated plaintext is **binary**, not JSON:
`u8(ssid_length) || ssid_ascii || u8(password_length) || password_ascii`.
SSID is 1–32 bytes and password is 8–63 bytes, each printable ASCII `0x20`
through `0x7e`, matching the current station credential validator. This v1
contract deliberately excludes non-ASCII names, open station networks and
64-hex-digit raw PSKs; supporting them requires a new version. The browser
validates before encrypting; the device validates again after authentication.
It never reflects credential bytes in status, diagnostics, logs or errors.

`source` is one of `unprovisioned`, `network_only`, `fault`; `slot_state` is
one of `none`, `identify`, `granted`, `trial`, `terminal`. `slot_id_digest` is
`null` or lowercase SHA-256 hex of the current slot's 16 raw bytes. The page
polls this read-only state and shows the Wi-Fi form only when its own slot
digest matches and has a grant. It must not treat public status as write
authority. `join` is one of
`idle`, `connecting`, `connected`, `disconnected`, `failed`. `address_ready` is
Boolean. `request_id_digest` is either `null` or lowercase SHA-256 hex of
the 16 raw request-ID bytes for the current/last bounded attempt. A status
response never uses a request ID alone as write authority. Terminal result
retention is bounded to one attempt and cleared on acknowledgement, timeout
or reboot; after reboot,
source/generation/join are sufficient to reconcile a durable commit.
The submit response `state` is `checking`, `connected` or `failed`.
`checking` carries the currently durable generation (0 before commit, 1
after commit); `failed` carries generation 0 for a precommit failure;
`connected` carries the durable generation 1. A postcommit disconnect
remains a committed generation-1 status, not a failed transaction. A valid
acknowledgement responds with `state: "accepted"`; invalid or stale
acknowledgements return a generic error without changing authority. All
generation numbers are exact nonnegative JSON integers within the existing
wire-safe range.

## Crypto transcript

Use X25519, HKDF-SHA-256 and ChaCha20-Poly1305 with a 32-byte key, 12-byte
nonce and 16-byte tag. The transcript `T` is the exact byte concatenation:

```
UTF8("WsprryPico/WiFi-Bootstrap/1\0")
|| hex_decode(device_id)          # 16 bytes
|| hex_decode(boot_id)            # 16 bytes
|| hex_decode(slot_id)            # 16 bytes
|| base64url_decode(browser_public_key) # 32 bytes
|| base64url_decode(pico_public_key)    # 32 bytes
|| hex_decode(request_nonce)      # 16 bytes
|| hex_decode(request_id)         # 16 bytes
```

All fields have fixed lengths. `salt = SHA256(T)`, `IKM =
X25519(browser_secret, pico_public_key)`, `key = HKDF-SHA256(IKM, salt,
UTF8("WsprryPico network-only AEAD v1"), 32)`. The Pico computes the
equivalent X25519 secret with its ephemeral private key. ChaCha20-Poly1305
encrypts the binary plaintext with `key`, `aead_nonce` and `AAD = T`.
The AEAD tag authenticates device, boot, slot, both keys and both request IDs
as well as the credentials. After a successful commit, the browser computes
`ack_tag = HMAC-SHA256(key, UTF8("WsprryPico network-only ACK v1") || T)`;
it is sent as 32 bytes of unpadded canonical base64url. An acknowledgement
cannot authorize a second write.

The [synthetic vectors](WiFi-Bootstrap-v1-vectors.json) contain exact public
keys, transcript, salt, derived key, ciphertext, tag and acknowledgement for
one deterministic example. The private keys in that fixture are test-only.
Implementation must independently reproduce the vector in Pico and browser
code, plus rejects for one-bit changes to every bound field, tag and nonce.

The browser page may use `crypto.getRandomValues` after feature detection but
must not assume `crypto.subtle` is available on HTTP. All cryptographic code
must be bundled from a reviewed, pinned, license-attributed local source; no
network import or browser-persistent credential/key is allowed. This prevents
passive AP listeners from reading the submitted credentials. The HTTP page is
not authenticated to the browser, so an active page replacement or relay can
obtain them; that limitation is explicitly accepted by the operator.
