# Consumer-Profile/1 journal payload

Status: **P12.8 STRUCTURAL PARSER AND INERT JOURNAL SOURCE IMPLEMENTED;
CONSUMER ACTIVATION NOT IMPLEMENTED OR ACCEPTED** (2026-09-27). This payload
is the intended atomic authority record for
[Owner-HTTP/1](Owner-HTTP-v1.md). Existing engineering profile formats and
[WiFi-Bootstrap/1](WiFi-Bootstrap-v1-proposal.md) retain their meanings.

## Slot and source contract

`ProfileSource::ConsumerProfile = 5` uses the existing two-slot profile
journal, with a version-1 UTF-8 JSON payload of at most 7,168 bytes under
the existing committed slot header/digest/sequence rules. A consumer source
passes journal selection only when its complete payload parses canonically;
source 5 with an absent, unknown-version, noncanonical or structurally invalid
payload is a fault,
not a legacy profile. A newer corrupt committed slot prevents rollback to an
older owner or factory authority. Unknown selection values remain faults.
The journal sequence is the externally reported profile generation; it is
not a separate claim counter. A direct virgin-blank commit selects generation 1;
network-only generation 1 upgrades to consumer generation 2. A completed
unprovisioned reset tombstone at generation N may be claimed at N+1 after
the access reset intent has completed. Later owner,
trust or network replacements advance the sequence exactly once each.

The version-1 JSON object has **exactly** these keys in this serialization
order, with no duplicate keys or trailing data:

| Key | Value and bound |
| --- | --- |
| `version` | Integer `1`. |
| `device_id` | Exact 32-character lowercase full device ID. |
| `owner_epoch` | Nonzero unsigned 64-bit decimal string. |
| `owners` | Array of one to four unique, canonical base64url 65-byte uncompressed on-curve P-256 public points. First owner is the claim key. |
| `network` | Object with exactly `ssid` (1–32 printable ASCII bytes), `password` (8–63 printable ASCII bytes) and `time_server` (validated hostname, maximum 253 bytes). |
| `station` | Object with exactly `callsign`, four-character `locator` and integer `power_dbm`; validate through the existing WSPR type-1 encoder rules. |
| `tls` | Object with exactly `hostname`, `port`, `ca_certificate`, `ca_private_key`, `server_certificate`, `server_private_key`, `ca_not_after_utc`, and `server_not_after_utc`. Hostname is the exact derived local hostname; port is 443; private keys are P-256 and the certificates are P-256/SHA-256 with exact SAN/device identity and purpose. Dates are UTC seconds encoded as decimal strings. The aggregate serialized `tls` object is at most 2,304 bytes. |
| `clients` | Array of zero to four unique client entries; each entry has exactly `name` (1–32 printable bytes), `csr_der` (canonical base64url of 1–320 DER bytes), `csr_sha256`, `public_key_sha256` (both 64 lowercase hex characters), `serial` (unique nonzero unsigned 64-bit decimal string) and `not_after_utc` (UTC seconds decimal string). The CSR must parse, bind the stored public key and digest, and be client-auth-only. Entries are sorted by public-key digest. |
| `request_sha256` | Lowercase 64-character SHA-256 hex of the completing claim or replacement request ID's 16 decoded bytes. |

Within objects, keys use the table order and the nested order shown above.
JSON strings use the project canonical serializer, not arbitrary caller
whitespace or escapes. Round-trip serialize/parse equality and exact
re-serialization must pass before committing. The payload budget includes
JSON escaping; fitting four owner keys and four maximum accepted CSRs with
the maximum accepted TLS aggregate is a required deterministic test. If the
budget cannot support all four clients, reduce individual input bounds
before production rather than silently reducing the promised capacity.
An initial pessimistic compact-JSON size check using four 87-character owner
points, four 427-character maximum CSR encodings, 32-character names with
worst-case JSON escaping, 20-digit counters and expiry values, a 253-byte
time server, maximally escaped SSID/password and the 2,304-byte TLS cap
totals **6,457 bytes**. That leaves 711 bytes under the slot payload cap;
the structural parser's four-owner/four-client boundary test confirms the
7,168-byte payload and 2,304-byte TLS limits with maximum CSR DER and JSON
escaping. The P12.8 host generator now confirms that its actual CA/server PEM
material fits the TLS cap; target resource and activation checks remain open.

The device stores only public owner keys; Safari holds the private owner
keys. The CA and server private keys are in ordinary Pico flash, as accepted
in P12.7. The client private key stays with the client. The persisted CSR,
serial and validity interval allow the Pico to regenerate a signed client
certificate for the exact same approved public key after an HTTP response
loss. A second approval is required for any changed CSR or public key.
Signed certificate bytes may differ on regeneration because ECDSA signing is
randomized; the allowed public key, serial and expiry may not change. The
station client pins the device CA and exact device ID before trusting it.

## Cross-store authority and activation

This one payload is authoritative for owner, network, station and TLS data
in consumer mode. The old access journal remains a reset-intent and legacy
engineering record; its password, field-mode flag and BLE bonds grant no
consumer authority. Existing standalone schedules and watermarks remain
unchanged. Consumer station fields override any stale standalone station
fields on every boot and API read. A firmware path that cannot make the
consumer station view authoritative must fail closed rather than activate a
mixed profile. Successful journal commit is followed by terminal response
delivery or a bounded timeout, then activation; restart reads all authority
from the same generation. A link/address/time/credential-validation failure
before commit leaves the previous complete source selected, or a fault if
storage is ambiguous. Never report setup complete from a sent write alone.

On migration, `LegacyBootstrap`, `RuntimeProfile`, `BuildBundle` and
`NetworkOnly` retain their existing parser and authority rules. Only a
healthy virgin blank, completed unprovisioned reset tombstone or the approved
network-only source may enter the ordinary consumer claim route. Adopting an
engineering runtime/factory source needs an explicit
separate physical transaction that revokes its password/BLE sessions and
trust; there is no automatic migration or factory-bundle fallback.
Consumer mode denies legacy password, cookie, GATT and factory-bundle
mutations **before** those adapters check their old credentials. Reset first
commits durable intent in the access journal, then writes an unprovisioned
tombstone, erases old key-bearing profile slots and advances the intent
phases. A power cut after intent boots only recovery service until erasure
finishes. A completed access recovery instead rewrites the full consumer
payload with a new owner epoch/key and unchanged operational fields.

## Implementation gates

The source 5 journal reader and writer enforce canonical **structural** form,
source transitions and same-device upgrade. Runtime loading now selects a
same-device source 5 record into a restricted pre-clock state. That state may
join station for UTC and serve a read-only AP recovery page; it has no owner,
TLS, legacy job, BLE or autonomous schedule authority. Cryptographic boot
validation and consumer authority remain disconnected. A structurally valid
record is not an activated profile.

Before enabling source 5 in production, complete exact identity/certificate
checks, old-source migration, reset-intent recovery, and no trust resurrection.
The current host test cuts every journal write page; broader access-journal
and activation cuts remain open. Cross-builds do not qualify flash timing,
provisioned BOOTSEL, AP/STA concurrency or RF.
