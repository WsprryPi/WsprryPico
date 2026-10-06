# Owner-HTTP/1: Safari commissioning and AP owner channel

**Current-scope notice (2026-09-27):** The retained owner-session and physical
claim design in this document was superseded by the
[immediate Safari setup contract](../development/phase12-safari-open-setup-revision.md).
The source candidate reuses the public status and one-use encrypted
`claim/start` and `claim/submit` wire shapes, plus AP-local `identify`, for an
ephemeral setup transaction. It admits profile source `5` for later changes,
grants the slot without BOOTSEL, has a 60-second submit deadline, and does not
persist the browser's P-256 point as an owner. The response omits
`physical_window_ms`. The owner session, signature, enrollment, physical
approval and reset portions below are historical design only and must not be
read as current consumer requirements or implemented routes. Names containing
`owner` remain internal wire names until a separately reviewed protocol
revision. This notice takes precedence over conflicting statements below.

Status: **P12.8 WIRE DESIGN WITH A SOURCE-LINKED CLAIM CANDIDATE;
OWNER SESSION, POST-CLOCK ACTIVATION AND TARGET ACCEPTANCE OPEN** (2026-09-27).
The candidate connects public claim status/start/submit, Safari sealing,
physical admission and one journal write. It has no authenticated owner
session or final private readback. This version specifies the approved
[P12.7 Safari/SoftAP design](../development/phase12-7-decision.md) as its
implementation gates pass. The source candidate admits both a separate
[WiFi-Bootstrap/1](WiFi-Bootstrap-v1-proposal.md) network-only transaction and
one physically granted owner claim on a healthy blank or network-only AP.
A structurally admitted source-5 profile has public claim status and a local
page, with private owner control still unavailable. This document neither
changes Field-GATT/1 nor grants RF output.

## Identity, authority and transport

All owner routes are AP-local HTTP/1.1 at `http://192.168.4.1`. Accept an
owner mutation only from the AP interface with exact `Host: 192.168.4.1`,
`Origin: http://192.168.4.1`, `Content-Type: application/json`, and
`X-WsprryPico-Owner: 1`. Reject duplicated or unknown security headers,
duplicate/unknown JSON keys, ambiguous encodings, pipelining and oversized
bodies. Do not enable CORS, cookies, HTTP Basic authentication, URL bearer
tokens, redirects from an owner route, or station-interface HTTP access.
Responses and the locally bundled page use `Cache-Control: no-store`; the page
uses a restrictive CSP and no remote resources. A complete raw JSON owner
request is at most 4,096 bytes for ordinary routes and 6,144 bytes for
advanced client enrollment; claim start/submit are at most 1,024 raw bytes
each. Independently, decoded ciphertext plus its 16-byte tag is at most 1,024
bytes for ordinary signed operations and 2,048 for client enrollment. These
are distinct limits because base64url expands the decoded bytes; enforce both
before allocating or authenticating a body. Every private request and response is encrypted even though the AP is
open. Public identity/setup-state responses contain no credentials, owner key,
client material or job state. The consumer setup status additionally exposes
only the saved callsign, four- or six-character grid and power in its `station` field,
as specified below; these three fields are public on the open setup AP.
Wi-Fi credentials and TLS/private client material are never returned by it.

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
signature over the fixed-order finish digest below. The signature
is checked against a committed owner key before the session becomes live.
Both ephemeral private keys are destroyed after derivation or failure. Reject
an all-zero X25519 shared secret.

The canonical start-request digest is
`SHA256(UTF8("WsprryPico/Owner-Session-Start/1\0") || device_id[16] ||
owner_key_sha256[32] || browser_public_key[32] || browser_nonce[16])`.
It binds the decoded fields, independent of JSON property order and
whitespace. The transcript `S` is the fixed-order concatenation of
`UTF8("WsprryPico/Owner-Session/1\0") || device_id[16] || boot_id[16] ||
owner_key_sha256[32] || u64be(owner_epoch) ||
u64be(profile_generation) || session_id[16] || browser_public_key[32] ||
pico_public_key[32] || browser_nonce[16] || pico_challenge[16] ||
u64be(expiry_monotonic_ms)`. The exact 32-byte finish-signature digest is
`SHA256(UTF8("WsprryPico/Owner-Session-Finish/1\0") || S ||
start_request_digest)`. A finish request must match the saved, unexpired
start fields exactly; the first complete finish attempt consumes them before
signature verification. A changed binding or invalid signature fails closed.
The public key and signature encodings are the canonical P-256 forms above.

An independent Python `hashlib`/`struct` vector uses device bytes `00..0f`,
boot `10..1f`, owner-key digest `20..3f`, epoch 5, generation 9,
session `40..4f`, browser public `50..6f`, Pico public `70..8f`, browser
nonce `90..9f`, Pico challenge `a0..af`, and expiry 123456789 ms. Its start,
finish and salt digests are respectively
`d9ae570529415c35a6b879873740fbc6d283202f08191d2d0c7a931307ec4396`,
`3f2463922847a96b5b3e21fbf668203fa54e7ec10a80206452809e34db787131`
and `bea5a3bb64ef326c01a1339bc042f7ea0714f533ec9032d82309e148a047bfdc`.
The portable digest builders and `owner_wire_tests` assert these bytes but do
not create a live session or validate X25519 points.

Derive 64 bytes with HKDF-SHA-256 using
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
The current consumer setup continuation adds `station` to both public-status
and claim/status: either `null` or exactly `{"callsign":"AA0NT","locator":"EM18","power_dbm":20}`
(the values here are an example). It is `null` for non-consumer/fault/wrong-device
selection and while the boot snapshot has a different generation from the
committed journal. It serializes only those three station fields from the
matching selected runtime profile, without copying or exposing the full
profile or its network/TLS/owner/client data. This is AP-local plaintext public
readback for the requested form prefill; station **changes** remain encrypted.
A source-5 update awaiting activation is unavailable for a new claim, so a
transient null station cannot be mistaken for an empty saved station.

Both endpoints also return `network`: either `null` or an object containing
only `ssid` and `time_server`. Healthy network-only and consumer selections
return these fields only when the runtime device and generation match the
committed journal; other selections return `null`. Passwords, TLS material,
owners and clients are never included. On a fresh Wi-Fi page, one read fills
the saved network name and time server without phone storage or a Save. The
password stays blank. An input event protects the current draft from a late
read; a failed read leaves the form usable. Wi-Fi changes remain encrypted.

On every fresh page, including browser privacy refresh, the form reads those
values from the Pico without phone storage or a Save. Later polling can refresh
an untouched form for a new committed generation. Any input/change protects
the whole current draft from polling; pending submissions and terminal displays
are not replaced by prefill. Non-consumer profiles retain empty station inputs
and the selected new-station default power. A malformed or wrong-device
readback does not populate or enable the form.

`claim_available` reports the current admission gate separately from `source`;
an unsafe or busy output does not relabel a healthy profile as a fault.

`POST /api/owner/v1/claim/start` admits exactly one pending claimant and
returns a random slot ID, Pico ephemeral X25519 public key and a 60-second
physical window. It binds the full ID, boot, browser owner public key,
browser ephemeral X25519 public key, browser nonce, expected source and
generation. The start request carries version `1`, `device_id`,
`owner_public_key` (canonical base64url SEC1 point),
`browser_public_key` (canonical base64url X25519 point), `browser_nonce`,
`profile_source` (integer `0`, `2` or `4`) and `generation` (decimal string).
The response carries exactly `version`, `device_id`, `boot_id`, `slot_id`,
`profile_source`, `generation`, `owner_key_sha256`, `browser_public_key`,
`browser_nonce`, `pico_public_key` and `physical_window_ms`. The owner digest
is SHA-256 of the decoded SEC1 point; the physical window is `60000`.
Source `0` means healthy virgin blank at
generation 0, source `2` means a completed unprovisioned reset tombstone at
nonzero generation and source `4` means network-only at nonzero generation.
Public status includes both its human-readable `source` and the exact numeric
`profile_source`. The browser must compare the exact full ID, source and
generation from public status and claim start, plus its owner-key digest,
browser point and nonce in the start response. Identify LED denotes this one
slot. One fresh runtime BOOTSEL
press/release grants it without asking the user to time the hold; device-side
debounce and stuck-hold bounds still apply. A stale level, held-on-boot press, second
claimant, timeout, changed key/source, output activity or unsafe sampler
cancels it. After the physical grant, the submit deadline is five minutes;
once consumed, the station/commit trial deadline is 90 seconds and the
terminal receipt remains available for 60 seconds. All deadlines use a
monotonic clock. The
provisioned/core-1 safe-sampling gate must pass before this route can be
enabled in consumer firmware.

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
|| u8(callsign_length) || callsign[3..12 uppercase letters/digits/slashes]
|| locator[4 or 6 uppercase Maidenhead] || u8(supported_power_dbm)
```

The plaintext is 20–117 bytes (11–22 bytes for the saved-network marker).
The full callsign may include prefix/suffix segments separated by single
slashes, for example `AA0NT/P`, `PJ4/AA0NT` or `PJ4/AA0NT/P`. It must contain
at least one letter and one digit, with no empty slash segments, whitespace
or punctuation. Saving is independent of WSPR Type 1 encodability. An
extended or non-Type-1 callsign is preserved exactly; the current standalone
encoder reports `UNSUPPORTED_MODE` and creates no job or watermark for it.
Locator format is `[A-R]{2}[0-9]{2}([A-X]{2})?`: the first pair identifies the
field, the digits its square, and the optional last pair its subsquare. There
is no locator-length byte; after the three length-prefixed fields, exactly
five or seven bytes remain (locator plus power). Existing four-character
plaintexts remain byte-for-byte compatible. All six characters are saved and
returned in public station readback. Standalone Type 1 WSPR uses the first
four characters; this does not add Type 3 or a two-message transmission.
No trailing bytes, JSON, time server or
certificate fields are permitted inside it. `time_server` is the firmware's
validated default `pool.ntp.org`, and HTTPS port is 443. These defaults do
not add user input. The portable C++ and browser builders share independent
Python `hashlib`/`struct` transcript and plaintext vectors: network-only
source `4`, generation `1`, device bytes `01..10`, boot `11..20`, slot
`21..30`, P-256 generator point, synthetic browser field bytes `31..50`, Pico field bytes
`51..70`, browser nonce `71..80`, request `81..90`, producing `SHA256(C) =
b13fd05696af4d82e4684aacdde110cefbfe3918a65b3da56dc4451f020d988f`.
For `LabNet`, test-only password `test-only-password`, `K1ABC`, `FN20` and
30 dBm, the plaintext hex is
`064c61624e657412746573742d6f6e6c792d70617373776f7264054b31414243464e32301e`.
The browser-sealed test envelope opens with the pinned Pico Mbed TLS adapter;
altered bindings fail. These builders and the Pico opener now meet in the
bounded claim candidate; their source connection does not qualify physical
claim or active owner control.

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
