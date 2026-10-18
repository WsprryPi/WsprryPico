# Consumer profile journal payload

`ProfileSource::ConsumerProfile = 5` uses the existing two-slot profile journal.
The canonical UTF-8 JSON payload is at most 7,168 bytes under the committed
header/digest/sequence rules. A missing, unknown-version, noncanonical or invalid
source-5 payload is a fault. A corrupt newer committed slot cannot restore an
older profile or factory trust. The selected sequence is the externally reported
profile generation; it is not a separate claim counter.

Consumer setup uses `owner_epoch:"0"` and `owners:[]`: no phone retains setup
authority. Nonzero-epoch/public-owner records remain parseable legacy formats,
not a current owner-session or administration feature. The
[station setup transaction](Owner-HTTP-v1.md) and
[network setup transaction](WiFi-Bootstrap-v1-proposal.md) retain their own
request, trial, commit and reconciliation boundaries.

## Record versions and fields

| Version | Station and network authority |
| --- | --- |
| 1 | Complete consumer profile with station snapshot and materialized TLS |
| 2 | Complete station snapshot with explicit `tls_pending:true`; trust material is absent until valid materialization |
| 3 | USB-managed profile with explicit boolean `tls_pending`; no station snapshot; standalone Config owns station; Wi-Fi may be explicitly absent |

All versions contain exact `device_id`, `owner_epoch`, `owners`, `network`,
`tls`, `clients` and `request_sha256` fields. Versions 1/2 also contain
`station`; versions 2/3 contain `tls_pending`. Unknown/duplicate keys, trailing
data and noncanonical encodings reject. Serializer/parser equality is checked
before selection. Explicit versioning preserves old records without inferring
missing credentials or station values.

- `device_id` is the full 32-character lowercase hexadecimal ID.
- `owner_epoch` is a uint64 decimal string. Zero requires an empty `owners`
  array; nonzero requires one through four distinct canonical 65-byte P-256
  SEC1 public points. No private owner key is stored.
- `network` contains `ssid`, `password`, `time_server`: 1–32 and 8–63 printable
  ASCII bytes for a configured network, plus a validated hostname up to 253
  bytes. Version 3 permits both SSID/password empty as explicit absence.
- `station` contains callsign, four/six-character Maidenhead locator and supported
  integer `power_dbm` under current station validation. It is absent in version 3.
- `tls` contains canonical hostname, port 443, CA/server certificates and private
  keys, and uint64 decimal-string validity limits. Its serialized aggregate is
  at most 2,560 bytes. A materialized profile validates exact device/SAN, issuer,
  key, purpose and bounded validity. Pending trust requires empty keys/certs,
  zero validity and no clients; it grants no TLS readiness.
- `clients` contains at most four unique entries: printable name up to 32 bytes,
  canonical base64url CSR DER up to 320 bytes, CSR/public-key SHA256, unique
  nonzero uint64 serial and expiry. Public-key digest orders entries. Identity,
  digest, key and client purpose must agree; the complete serialized payload
  must still fit its independent 7,168-byte ceiling.
- `request_sha256` hashes the completing setup request ID's 16 decoded bytes.
  It identifies the durable selected result; a volatile attempted request is
  not proof of commit.

CA/server private keys reside in ordinary Pico flash without a confidentiality
claim. Client private keys stay with the clients. Runtime certificate renewal
preserves the existing CA/server key and cannot silently replace trust. Returned
status never contains passwords, private keys or complete profiles.

## Cross-store authority and interruption

Versions 1/2 supply authoritative profile-owned station fields; standalone
schedules and watermarks remain separate. Version 3 deliberately moves station
authority to the existing Config journal. Its migration saves the complete
effective configuration before selecting version 3; later complete Config
commits cannot combine half of a new station with half of an old configuration.
Saved progress is independent and requires explicit application.

Profile selection happens only under idle, unowned, known-inactive/nonfaulted
admission with the exact target and revision. Deferred restart waits for the
matching response delivery or bounded timeout. Durable saves survive reply
loss and require authoritative readback/review before a new write. Source,
generation and request digest must come from the same selected record.

Engineering password/cookie/BLE credentials are not promoted into consumer
management authority. Deliberate source transitions preserve their exact
identity/reset gates. Provisioning reset writes durable intent and a source
tombstone before exposing the reset authority; interrupted intent resumes in
recovery-only state. Access recovery, provisioning reset and full operational
erase have distinct preservation rules in [field access](../development/field-access.md).
No invalid newer record may resurrect old credentials or enabled settings.

[USB local configuration](../development/usb-local-configuration.md) defines
explicit network deletion, draft credential non-resurrection, supported profile
migration and rollback limits. Older firmware that cannot parse these record
versions fails closed and is not a supported downgrade vehicle.

Source: [consumer_profile.cpp](../../src/provisioning/consumer_profile.cpp),
[local settings](../../src/provisioning/local_settings.cpp) and
[profile journal](../../src/provisioning/profile.cpp).
