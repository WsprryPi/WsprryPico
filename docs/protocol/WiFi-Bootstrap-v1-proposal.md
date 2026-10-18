# WiFi-Bootstrap/1 network setup

The device-served consumer portal performs one encrypted network transaction
without retaining a phone owner or granting job authority. Public mutations
are restricted to the open setup AP. Authenticated LAN setup uses the separate
[Consumer-Radio/1](Consumer-Radio-v1.md) wrapper. HTTP page delivery is
unauthenticated and remains vulnerable to active page substitution.

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
loss, or opens through the selected GP14 gesture after confirmed shutdown.
The setup transaction requires no runtime BOOTSEL press. Every AP activation
has a non-sliding ten-minute cap; client activity and replies cannot extend it.
The AP-only envelope, encrypted plaintext, header checks and one-use slot are
bounded independently. The sealed plaintext now accepts
an optional one-byte length plus a 1–253-byte time-server name after the Wi-Fi
password. An older plaintext without this suffix uses `pool.ntp.org`. The
browser sends the suffix, and the target validates it before trial or journal
commit. The maximum ciphertext is 351 bytes and the submit body limit is 768
bytes. Network-only journal records with a durable setup result are version 3
and include `time_server` plus `request_sha256`. Version 1 and 2 records remain
readable; they have no durable request identity. A later save writes version 3.
Version 1 records load with the default time server.

Current status separates durable result identity from the pending attempt:
`request_id_digest` comes only from the selected healthy journal and is paired
with that journal's source/generation. `attempt_request_id_digest` is the
volatile slot's request digest, used only to correlate a definite terminal
failure. It must never prove a save. Version 3 retains the durable digest across
ACK, slot expiry and reboot; consumer profiles retain their existing digest.
Exact success needs both the expected next generation and the durable digest.
An uncertain commit blocks new saves, cancellation and ACK, reports unverified
state, and schedules a safe restart for journal reconciliation. It neither
restores the old network nor repeats the write without proof of noncommit.

The current optional `GET /api/bootstrap/v1/time` returns a decimal-string
`challenge_ns` from the Pico monotonic clock. `POST /api/bootstrap/v1/time`
then accepts exactly `version`, `device_id`, decimal-string `utc_ms` and the
challenge under the same AP-local Host, Origin, content-type and bootstrap-
header admission. It replies with `version` and `state` (`accepted` or
`ignored`). A challenge older than 200 ms is ignored. The portal exchanges
time on opening and about every 30 seconds; it creates no setup slot and
contains no credentials. The Pico bounds UTC to 2025–2099, assumes a 250 ms
phone-clock allowance, adds challenge age, ignores inconsistent browser jumps,
and gives SNTP and authenticated controller time priority. Fresh SNTP remains
required for consumer TLS generation. Consumer radio control uses its separate authenticated envelope.

## Admission and one-use state

The access/profile journals and full device identity must be healthy, reset
intent clear, and output known inactive with no conflicting job ownership or
setup transaction. Supported unprovisioned, network-only and consumer states
use the same bounded trial/commit authority. A fault or ambiguous source refuses
mutation; no old credentials or enabled configuration are recovered implicitly.

One slot binds device, boot, browser key, nonce and a checked random slot ID.
It is granted when Save starts and expires after 180 seconds. The first
complete submit consumes it before a station trial. Cancel, expiry, reboot and
failure clear transient keys/credentials. A lost reply never permits replay.
A successful station association/DHCP trial precedes one verified journal
selection. A failed trial preserves the prior selected network. An uncertain
commit blocks new saves and uses restart/readback to resolve authority.

Source, generation and durable request digest must match to prove a save.
Volatile attempt digests can identify a failure but cannot prove commit. The
terminal reply and ACK coordinate restart within bounded deadlines; they do
not extend the AP lifetime. The portal preserves drafts until explicit review.

## Encoding and routes

All requests use HTTP/1.1 on the bootstrap AP interface only. Mutating
requests require exact `Host: 192.168.4.1`, exact
`Origin: http://192.168.4.1`, `Content-Type: application/json`, and
`X-WsprryPico-Bootstrap: 1`. Reject duplicate headers, duplicate JSON keys,
unknown keys, transfer encodings not explicitly supported, bodies over 512
bytes (768 for submit), foreign hosts/origins and station-interface requests.
Responses use `Cache-Control: no-store`; errors contain no secret. No route
accepts plaintext SSID or password. JSON number `version` is exactly `1`.

| Route | Exact JSON request keys | Exact JSON response keys |
| --- | --- | --- |
| `POST /api/bootstrap/v1/start` | `version`, `device_id`, `browser_public_key`, `request_nonce` | `version`, `device_id`, `boot_id`, `slot_id`, `pico_public_key`, `slot_expires_in_ms` |
| `POST /api/bootstrap/v1/submit` | `version`, `device_id`, `boot_id`, `slot_id`, `request_id`, `aead_nonce`, `ciphertext`, `tag` | `version`, `state`, `generation`, `request_id_digest` |
| `GET /api/bootstrap/v1/status` | none | `version`, `source`, `generation`, `slot_state`, `slot_id_digest`, `join`, `address_ready`, `request_id_digest`, `attempt_request_id_digest` |
| `POST /api/bootstrap/v1/ack` | `version`, `device_id`, `boot_id`, `slot_id`, `request_id`, `ack_tag` | `version`, `state` |

`device_id`, `boot_id`, `slot_id`, `request_nonce` and `request_id` are each
exactly 32 lowercase hexadecimal characters representing 16 bytes. The two
public keys are 32 bytes encoded as unpadded canonical base64url (43
characters). `aead_nonce` is 12 bytes, unpadded canonical base64url (16
characters), drawn fresh by the browser. `ciphertext` and `tag` are separately
unpadded canonical base64url; the tag is exactly 16 bytes (22 characters).
The ciphertext is 11–351 bytes. Reject noncanonical base64url, invalid keys,
low-order/all-zero X25519 shared secrets, stale or reused IDs/nonces and
integers outside their stated domains. `slot_expires_in_ms` is at most 180000. These are display hints; the device's
monotonic deadlines are authoritative.

The authenticated plaintext is **binary**, not JSON:
`u8(ssid_length) || ssid_ascii || u8(password_length) || password_ascii`,
optionally followed by `u8(time_server_length) || time_server_ascii` (1–253 bytes).
SSID is 1–32 bytes and password is 8–63 bytes, each printable ASCII `0x20`
through `0x7e`, matching the current station credential validator. This v1
contract deliberately excludes non-ASCII names, open station networks and
64-hex-digit raw PSKs; supporting them requires a new version. The browser
validates before encrypting; the device validates again after authentication.
It never reflects credential bytes in status, diagnostics, logs or errors.

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
Pico/browser conformance tests reproduce these bytes and reject one-bit
changes to bound fields, tags and nonces.

The browser page may use `crypto.getRandomValues` after feature detection but
must not assume `crypto.subtle` is available on HTTP. All cryptographic code
must be bundled from a reviewed, pinned, license-attributed local source; no
network import or browser-persistent credential/key is allowed. This prevents
passive AP listeners from reading the submitted credentials. The HTTP page is
not authenticated to the browser, so an active page replacement or relay can
obtain them; that limitation is explicitly accepted by the operator.
