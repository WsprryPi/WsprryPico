# Owner-HTTP/1 station setup transaction

The `owner` wire names identify the consumer station-setup transaction. It
retains no phone owner, browser private key or owner session. A transaction
writes `owner_epoch:"0"` with an empty `owners` array. Station radio control
uses [Consumer-Radio/1](Consumer-Radio-v1.md); engineering TLS and BLE retain
their own authority. Portable owner-signature codecs do not expose owner-session,
enrollment or owner-administration HTTP routes.

## Transport and admission

Public requests are AP-local HTTP/1.1 with exact Host `192.168.4.1`.
Mutations require matching `Origin: http://192.168.4.1`, JSON content type and
`X-WsprryPico-Owner: 1`. Duplicate/unknown keys, security-header ambiguity,
cookies, bearer authentication, unsupported transfer encoding and oversized
bodies refuse before mutation. Claim start/submit bodies are at most 1,024
bytes. Responses are noncacheable. Authenticated LAN setup wraps the same
transaction through Consumer-Radio; it does not expose public AP mutations on
station HTTP. HTTP does not authenticate the delivered page.

Healthy unprovisioned, network-only and consumer selections can admit a new
setup transaction only with exact full identity/source/generation, known
inactive output, idle/unowned JobService and no pending reset or conflicting
setup. Busy output does not turn a healthy profile into a fault. Setup pauses
new autonomous launches without interrupting an accepted job or clearing its
watermark. Runtime BOOTSEL or a retained phone key is unnecessary.

## Status and one-use claim

`GET /api/owner/v1/public-status` and `GET /api/owner/v1/claim/status` report
full device/boot identity, source/generation and current readiness. Station
prefill contains only callsign, four/six-character locator and reported power;
network prefill contains only SSID/time server. Neither returns passwords,
TLS private material, owners or clients. Prefill requires matching runtime and
selected journal generation. Status polling never overwrites an edited draft.
The separate `wspr-support` descriptor supplies current station admission.

`POST /api/owner/v1/claim/start` takes version 1, device ID, transient
`owner_public_key` (canonical 65-byte P-256 SEC1 point), X25519
`browser_public_key`, `browser_nonce`, numeric `profile_source` and decimal-string
`generation`. Source values are 0 for virgin blank, 2 for a completed reset
tombstone, 4 for network-only and 5 for consumer. The response binds version,
device/boot/slot IDs, source/generation, owner-key SHA256, browser key/nonce and
Pico ephemeral key. It has no physical-window field. Checked random IDs and
full-device/source binding grant one ephemeral transaction, not ownership.
The open-setup submit deadline is 60 seconds; the consumed station/commit trial
has a separate 90-second bound and the terminal receipt lasts at most 60 seconds.
All deadlines are monotonic. Keys and credentials are cleared on terminal paths.

`POST /api/owner/v1/claim/submit` carries version `1`, full `device_id`,
`boot_id`, `slot_id`, a fresh `request_id`, 12-byte `aead_nonce`, `ciphertext`
and 16-byte `tag`. Binary fields are canonical base64url except the four
IDs, which are lowercase hex. Its single AEAD envelope uses a fresh
X25519/HKDF-SHA-256/ChaCha20-Poly1305 key. The exact AAD transcript `C` is:

```
UTF8("WsprryPico/Owner-Claim/1\0")
|| device_id[16] || boot_id[16] || slot_id[16]
|| UTF8("http://192.168.4.1") || u8(profile_source) || u64be(generation)
|| owner_public_key[65] || browser_public_key[32] || pico_public_key[32]
|| browser_nonce[16] || request_id[16]
```

It is 261 bytes. Derive one 32-byte key with `IKM = X25519(browser_private,
pico_public)`, `salt = SHA256(C)`, and
`info = UTF8("WsprryPico owner claim AEAD v1")`. Reject an all-zero shared
secret. The browser generates a random 12-byte nonce for its one submit; the
slot and ephemeral keys are consumed on the first complete submit even if
authentication fails. The authenticated plaintext is exactly:

```
u8(ssid_length) || ssid[1..32 printable ASCII]
|| u8(password_length) || password[8..63 printable ASCII]
|| u8(callsign_length) || callsign[3..12 bytes; uppercase station syntax, including <CALL> Type 3]
|| locator[4 or 6 uppercase Maidenhead] || u8(supported_power_dbm)
```

The binary plaintext contains length-prefixed SSID/password/callsign, a four-
or six-character locator and supported reported dBm, under its 20–117-byte bound.
A saved-network marker uses the existing profile instead of transferring its
password. The shared station validator and [WSPR planner](../development/wspr-planning.md)
check current Type 1/2/3 syntax before trial; no identity is truncated or
silently converted. Profile-owned station updates are independent of saved
radio/schedule settings and retain their existing transactional authority.

## Commit, delivery and reconciliation

The profile selection commits station, network, trust and request identity
atomically under [Consumer-Profile](Consumer-Profile-v1.md). No phone authority
is persisted. TLS-pending profiles retain explicit readiness until qualified
network time permits materialization. A failed precommit trial leaves the prior
complete profile; torn/ambiguous storage fails closed. A sent write is not proof
of commit. Readback must match the full device, expected generation and exact
request digest. A receipt-only continuation contains no password/key/submit
packet and cannot replay a save.

Terminal delivery releases deferred restart through its exact transport
transaction or bounded timeout. The AP lifetime remains capped independently.
USB-managed profiles use standalone station authority and the supported USB
migration path; older firmware is not a supported rollback after new profile
versions. Existing wire/crypto/journal tests cover canonical encoding, wrong
identity/generation, one-use slots, interruption and no trust resurrection.
These checks establish no physical timing, arbitrary-phone interoperability or
RF qualification.

The authoritative codecs and dispatch are
[owner_claim_http.cpp](../../src/network/owner_claim_http.cpp),
[owner_wire.cpp](../../src/network/owner_wire.cpp) and
[bootstrap_server.cpp](../../src/network/pico/bootstrap_server.cpp).
