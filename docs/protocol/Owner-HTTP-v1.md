# Owner-HTTP/1: Safari commissioning and AP owner channel

Status: **P12.8 WIRE DESIGN WITH PORTABLE CLAIM AND SIGNING-DIGEST CODE; HTTP/CRYPTO NOT
IMPLEMENTED OR TARGET ACCEPTED** (2026-09-27). This version specifies the approved
[P12.7 Safari/SoftAP design](../development/phase12-7-decision.md) when code
and target gates pass. Until then, the running image offers only the separate
[WiFi-Bootstrap/1](WiFi-Bootstrap-v1-proposal.md) network-only transaction on
the blank AP. This document neither changes Field-GATT/1 nor grants RF output.

## Identity, authority and transport

All owner routes are AP-local HTTP/1.1 at `http://192.168.4.1`. Accept an
owner mutation only from the AP interface with exact `Host: 192.168.4.1`,
`Origin: http://192.168.4.1`, `Content-Type: application/json`, and
`X-WsprryPico-Owner: 1`. Reject duplicated or unknown security headers,
duplicate/unknown JSON keys, ambiguous encodings, pipelining and oversized
bodies. Do not enable CORS, cookies, HTTP Basic authentication, URL bearer
tokens, redirects from an owner route, or station-interface HTTP access.
Responses and the locally bundled page use `Cache-Control: no-store`; the page
uses a restrictive CSP and no remote resources. Ordinary bodies are at most
1,024 bytes; a separately bounded advanced CSR body may be at most 2,048
bytes. Every private request and response is encrypted even though the AP is
open. Public identity/setup-state responses contain no credentials, owner key,
client material, station settings or job state.

The authority identity is the full 16-byte device ID, represented on JSON
wire as exactly 32 lowercase hex digits. `boot_id`, `request_id`, `slot_id`
and browser/Pico nonces are independent random 16-byte values in the same
encoding. The displayed six-character suffix is a label only. The owner
epoch and profile generation are unsigned 64-bit monotonic values, encoded as
decimal strings to avoid JavaScript integer loss. A route compares the full
device ID, current boot ID, owner epoch and current journal generation before
any mutation. A failed comparison never falls back to a suffix or factory
password.

All Pico APs share the same browser origin. Safari stores each owner private
key under a full-device-ID-indexed name and compares the returned device ID,
owner public-key digest and epoch before using it. This prevents accidental
wrong-board selection by honest firmware. A malicious page served by another
AP at the same numeric origin can read the keys; the operator accepted this
active page-substitution risk in P12.7. The protocol does not claim to prevent
an active page replacement or relay.

## Owner key and canonical encodings

Safari generates a random P-256 ECDSA key using the locally bundled crypto
implementation. Its private scalar stays in Safari site storage; a storage
write/readback and self-test must pass before claim. The public key is a
canonical 65-byte SEC1 uncompressed point (`04 || X32 || Y32`). Validate
on-curve and reject infinity, noncanonical encodings and duplicate owner
keys. JSON encodes binary as canonical unpadded base64url. Signatures are
64-byte `r32 || s32` ECDSA-P256/SHA-256 with both scalars in range and low-S
normalization. The Pico verifies the exact 32-byte SHA-256 digest, not an
arbitrary caller-supplied digest. Owner capacity is four; enrollment never
evicts an owner silently. Public owner-key digests are lowercase SHA-256 hex
of the exact 65-byte point.

Canonical signing input uses fixed-order binary fields, never serialized JSON:

```
UTF8("WsprryPico/Owner-HTTP/1\0")
|| u8(operation) || device_id[16] || boot_id[16]
|| u64be(owner_epoch) || u64be(profile_generation)
|| request_id[16] || challenge[16] || u64be(expiry_monotonic_ms)
|| SHA256(method_ascii || 0x00 || path_ascii || 0x00 || body_bytes)
```

`operation` is a versioned registry value, never inferred from a path;
`method_ascii` is uppercase and `path_ascii` is the exact matched route.
`body_bytes` are the decoded ciphertext followed by the decoded 16-byte tag;
the outer JSON's property order and whitespace have no authority. The
operation's plaintext includes the exact target object and proposed value,
and the route must agree with the signed operation number. Every mutation,
including one inside an already authenticated encrypted session, carries a
fresh owner signature over this input. The device issues a fresh single-use challenge with a
monotonic deadline of at most 30 seconds. A challenge is bound to one owner
key, operation, request ID, boot, epoch and generation and is consumed before
an authorized operation is attempted. An expired, duplicate or unknown
challenge fails. Time for challenge expiry is monotonic and does not depend
on UTC. Resend after an unknown result opens a new read-only reconciliation
session; it never reuses a mutation challenge.
The pending challenge also binds the current encrypted session ID. The first
complete decrypted attempt consumes it before ECDSA verification, including
an invalid signature or changed binding. A monotonic rollback cancels it.
Issuing a challenge requires an existing consumer profile generation above
zero and a nonzero owner epoch; the Pico supplies every random field from
checked entropy. The portable slot does not generate randomness or check
the current journal on its own.

The Owner-HTTP/1 signed-operation registry is fixed below. All entries use
`POST` so the encrypted request body, including private readback, is carried
with one exact route. The client and handler must reject a numeric operation
whose method or path differs from its row, including extra slashes, query
strings or case changes. Session start/finish and the public claim routes are
outside this registry and have separate transcripts and authority checks.

| Hex operation | Exact path |
| --- | --- |
| `10` | `/api/owner/v1/readback` |
| `11` | `/api/owner/v1/owners/propose` |
| `12` | `/api/owner/v1/owners/approve` |
| `13` | `/api/owner/v1/owners/remove` |
| `20` | `/api/owner/v1/clients/enroll` |
| `21` | `/api/owner/v1/clients/revoke` |
| `30` | `/api/owner/v1/network/replace` |
| `31` | `/api/owner/v1/trust/renew` |
| `40` | `/api/owner/v1/reset/intent` |

The portable digest builder enforces the registry and decoded sealed-body
sizes: 16–1,024 bytes for ordinary operations and 16–2,048 bytes for client
enrollment. An independent SHA-256 vector uses operation `30`, device bytes
`00..0f`, boot `10..1f`, epoch 5, generation 9, request `20..2f`, challenge
`30..3f`, expiry 123456789 ms, and body
`01020304a0a1a2a3a4a5a6a7a8a9aaabacadaeaf`.
Its body digest is
`d5862faec4476b11187e16e8ddd7e9806d6978e62c2248c361c719ce9806aebb`;
the complete signing digest is
`2d7abd422c7760352607cf9521a840535e4610b19f11536c0fbfde7338dc337f`.
These bytes were calculated independently with Python `hashlib` and `struct`
and are asserted by `owner_wire_tests`. A fixed test P-256 scalar of one has
SEC1 public point
`046b17d1f2e12c4247f8bce6e563a440f277037d812deb33a0f4a13945d898c2964fe342e2fe1a7f9b8ee7eb4a7c0f9e162bce33576b315ececbb6406837bf51f5`
and a low-S raw signature over that digest:
`089f7a5717765e2149dcbddbc8064b1adf91b177180675b574b15f03bd95a59815ed308ef6e56ed09ddafffa114a046e197434d6be77001c6cd43d86e75d0d81`.
The signature was independently generated with the pinned Noble P-256
implementation and checked by the pinned Mbed TLS PSA verifier in host
tests. These portable components do not yet authorize an owner or expose an
HTTP route; journal and session admission remain P12.8 gates.

## Encrypted owner session

`POST /api/owner/v1/session/start` receives the device ID, owner-key digest,
browser ephemeral X25519 public key and a browser nonce. The Pico permits at
most one pending session, returns current boot/epoch/generation, a random
session ID, fresh challenge, its ephemeral X25519 public key and an expiry.
`POST /api/owner/v1/session/finish` supplies the owner's canonical P-256
signature over those values and the session-start body digest. The signature
is checked against a committed owner key before the session becomes live.
Both ephemeral private keys are destroyed after derivation or failure. Reject
an all-zero X25519 shared secret.

The transcript `S` is the fixed-order concatenation of the prefix
`WsprryPico/Owner-Session/1\0`, full device ID, boot ID, owner epoch,
profile generation, session ID, browser and Pico X25519 public keys, browser
nonce and Pico challenge. Derive 64 bytes with HKDF-SHA-256 using
`IKM = X25519(...)`, `salt = SHA256(S)` and
`info = UTF8("WsprryPico owner AP traffic v1")`. The first 32 bytes are the
browser-to-Pico ChaCha20-Poly1305 key, the next 32 the Pico-to-browser key.
Use a 96-bit nonce of four zero bytes plus a 64-bit big-endian sequence,
starting at one in each direction. The exact AAD is `S || u8(direction) ||
u64be(sequence) || method || 0x00 || path`, with direction 0 for requests and
1 for responses. Each direction has a strict next-sequence counter and one
in-flight request. Any gap, duplicate, wrap, wrong route, tag failure or
expired session closes and scrubs the session. Session lifetime is at most
five minutes or until AP loss, boot, epoch/generation change, owner removal,
reset or activity-safety change. Do not log plaintext, session keys or tags.

All private route bodies, including status and errors, are encrypted within
this session. The outer JSON has only `version`, `device_id`, `boot_id`,
`session_id`, `sequence`, `ciphertext`, `tag`, and, for mutations,
`request_id`, `challenge`, `expiry_monotonic_ms`, `operation`, `signature`.
The deterministic nonce is not transmitted. The response uses its own
direction key and counter. Public
status must never be mistaken for an authenticated private readback.

## First claim and full setup

Public `GET /api/owner/v1/public-status` returns full identity, boot, current
source (`unprovisioned`, `network_only`, `consumer`, or `fault`), generation,
whether an owner exists, and nonsensitive link/clock readiness. A source
other than healthy unprovisioned or healthy network-only cannot begin a
consumer claim. Network-only association grants no owner or station control.

`POST /api/owner/v1/claim/start` admits exactly one pending claimant and
returns a random slot ID, Pico ephemeral X25519 public key and a 60-second
physical window. It binds the full ID, boot, browser owner public key,
browser ephemeral X25519 public key, browser nonce, expected source and
generation. Identify LED denotes this one slot. One fresh runtime BOOTSEL
press/release grants it without asking the user to time the hold; device-side
debounce and stuck-hold bounds still apply. A stale level, held-on-boot press, second
claimant, timeout, changed key/source, output activity or unsafe sampler
cancels it. After the physical grant, the submit deadline is five minutes;
once consumed, the station/commit trial deadline is 90 seconds and the
terminal receipt remains available for 60 seconds. All deadlines use a
monotonic clock. The
provisioned/core-1 safe-sampling gate must pass before this route can be
enabled in consumer firmware.

`POST /api/owner/v1/claim/submit` carries one AEAD envelope under a fresh
X25519/HKDF-SHA-256/ChaCha20-Poly1305 key with a domain-separated
`WsprryPico/Owner-Claim/1\0` transcript of every bound field plus a new
request ID. Its authenticated plaintext contains exactly the validated Wi-Fi
SSID/password and callsign, four-character locator, and supported WSPR power.
The public owner key is bound in AAD. The browser never sends its private
owner key. A slot and its key are consumed on the first complete submit,
whether the station trial or later commit succeeds. The Pico trials
association/DHCP, establishes bounded UTC, generates per-device CA and
server key/certificate, validates the complete consumer profile, and commits
owner, Wi-Fi, station and trust data as **one** profile-journal generation.
No owner credential is committed earlier. An interrupted, unconfigured claim
simply expires and can be retried with a new slot. A direct virgin-blank
commit is generation 1; upgrade from network-only generation 1 is generation
2. A completed reset tombstone at generation N may be claimed at N+1 after
reset intent completes. `request_sha256` hashes the 16 **decoded** bytes of
the completing request ID.

`GET /api/owner/v1/claim/status` is public but returns only source,
generation, request-ID digest, slot-ID digest and readiness flags. It never
returns credentials or keys. After a completed claim, Safari must establish
an authenticated encrypted owner session and read back the exact device ID,
owner-key digest/epoch, request digest, generation, station address/time,
station settings digest and TLS trust digest. It shows **Setup complete** only
when those values and the persisted profile agree. If the AP or iOS captive
sheet disappears, it shows **Checking setup** and asks the user to reconnect
to the Pico AP in Safari. A network-only result is never full setup success.

## Owner operations and recovery

Every owner operation uses a new single-use challenge and the encrypted
session: private readback, second-phone proposal/approval, owner removal,
station-client CSR enrollment/revocation, network replacement, server renewal
and reset intent. A second phone has a separate Safari key and request slot;
the existing owner approves the exact proposed key with a fresh physical
gesture. Client enrollment binds the exact CSR hash and friendly name, owner
epoch and generation; one pending CSR exists, four client keys fit the
allowlist, and a fresh physical gesture is required before signing. A lost
reply is reconciled by the committed CSR/key digest; replay cannot sign a
different CSR. Revocation commits before connection teardown.

Access recovery without the old owner uses two independently prompted,
request-bound physical gestures and a fresh Safari key; it increments owner
epoch and revokes every old owner/session while preserving the operational
profile. Network reset needs an authenticated owner, preservation summary and
two fresh gestures. Full erase additionally needs an on-screen erase
confirmation and a third gesture. A press alone never starts a reset. Loaded,
owned, armed, running, failed, active-output or unknown-output states reject
every reset. The access journal's durable reset intent gates boot: before
intent old authority is valid; after intent only recovery service runs; after
completion only the selected new state is valid. Reset never falls back to a
legacy factory bundle or old owner key.

## Persistence, migration and activation

Add the versioned [Consumer-Profile/1](Consumer-Profile-v1.md) source to the existing two-slot profile
journal. Its single bounded payload contains the owner epoch and up to four
full public keys, network and station settings, per-device CA and server
private keys/certificates, exact client allowlist, trust metadata and the
committed request digest. The complete payload must fit one slot and pass
parse, cryptographic and resource validation before commit. In consumer mode
the embedded station fields are authoritative; stale standalone station
fields cannot override them. Schedules and watermarks remain in their
existing stores. Existing engineering `RuntimeProfile`, `NetworkOnly`,
`BuildBundle`, and Field-GATT/1 payloads retain their versioned meanings.
Engineering password/BLE authority is never silently promoted into consumer
owner authority. In `ConsumerProfile` mode, all legacy password, cookie,
Field-GATT and factory-bundle mutation routes are denied before their old
admission code runs; only the versioned owner AP routes and separately enrolled
station mTLS principals may mutate. A deliberate physical adoption transaction
is required to replace an old runtime/factory source. Unknown profile versions or torn
commits fail closed; an older complete consumer or factory record cannot be
resurrected after a newer invalid committed record. Reset writes a tombstone
before erasing old key-bearing slots and resumes erasure after a power cut.

Commit occurs only with known inactive output and no job owner, loaded,
armed, running or failed state. The terminal response is delivered before
activation where possible, with a bounded delivery timeout. On restart,
profile, owner, station and trust must all resolve from the same committed
generation; a mismatch disables station APIs, mTLS, AP private operations and
RF admission. The AP remains open and available in network-only and consumer
modes while station Wi-Fi is healthy; its channel/resource and RF coexistence
cost is a target gate. The existing network-only image still withdraws its AP
and remains a separate, historically recorded source result until replaced.

## Required vectors and acceptance before production enablement

P12.8 must add independent browser and Pico/host vectors for P-256 public
key/signature canonicalization, the session transcript/HKDF/AEAD in both
directions, claim envelope, wrong-device/boot/epoch/generation and replay
rejection. Power-cut tests must cover every profile commit and reset-intent
marker, old-source migration, CA renewal and no trust resurrection. P12.9
must prove Safari storage and captive handoff on the selected iPhone. P12.10
must prove direct/upgrade generation and station readback with RF inhibited.
P12.11–P12.12 must close physical owner/recovery/resource/fault cases.
