# WsprryPico Field-GATT/1 protocol and super-user guide

Status: frozen Field-GATT/1 source contract. This document defines the custom
Bluetooth Low Energy interface implemented in `devel`. The checked-in
[conformance vectors](Field-GATT-v1-vectors.json) bind its UUIDs, limits,
profile-apply sequence and provisional-bond expiry policy across firmware,
Bluefy and the native Raspberry Pi client. An incompatible wire change requires
a new Field-GATT protocol version. Phase 12 remains active: this source/host
freeze is not physical interoperability or end-user acceptance.

This document is written for technically experienced operators, client authors
and maintainers. It explains how to identify the correct Pico, establish the
two layers of authorization, exchange field commands, provision a complete
profile and carry WTP/1 over GATT. Normal users should use the checked-in
Bluefy page or the supported Raspberry Pi/Linux client rather than constructing
GATT values by hand.

The words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT** and
**MAY** describe this custom protocol's current conformance requirements.

## 1. Safety and scope

The field GATT service provides local provisioning and management. It does not
create a second scheduler, transmitter owner or RF authority. Its WTP carrier
feeds the same `JobService` used by USB CDC and authenticated TCP. Complete jobs
are loaded before they are armed, and all execution timing remains local to the
RP2350.

Merely connecting, pairing, authorizing, reading status or synchronizing time
does not authorize RF output. The standard Phase 12 image is RF-inhibited.
Phase 13 RF and release qualification remains separate.

Two application streams share one encrypted BLE connection:

1. **Field command/status** carries authorization, controller time, Identify,
   provisioning and field status as bounded JSON messages inside the custom
   framing in section 6.
2. **WTP** carries the unchanged byte stream defined by
   [WTP/1](WTP.md). GATT segmentation is transport fragmentation only and adds
   no WTP operation or ownership rule.

Provisioning is outside WTP/1. The field-access security and recovery policy is
defined separately by the
[Phase 12 field-access contract](../development/phase12-field-access-contract.md).

## 2. Supported clients

### Bluefy on iPhone

Open the repository-owned page from the project-approved HTTPS origin in
Bluefy. The page verifies its release assets before enabling the picker. The
page is the selected iPhone client; there is no native WsprryPico iOS app.

Bluefy uses the field command/status characteristics for authorization,
provisioning and local controls. When the operator requests WTP status, the page
selects a connection-scoped raw-WTP mode on that same characteristic pair. It
does this because the accepted Bluefy path must keep one status listener and one
write characteristic stable for the life of the connection.

### Raspberry Pi or Linux with BlueZ

The native client is `scripts/wsprrypico_ble.py`. Its operator guide is
[Raspberry Pi/Linux BLE local control](../development/raspberry-pi-ble-client.md).
Its identity, authorization, status, Identify, time, dedicated-WTP and profile-
application paths implement the frozen source contract. Profile application
re-prompts for the current local password, performs bound `profile_step_up`,
waits for required USB-local confirmation and reuses the bound request ID for
`apply`. It selects an exact Bluetooth address, verifies the full device ID and
does not set the BlueZ `Trusted` property. Physical native-Pi profile acceptance
remains open.

### Generic GATT tools

A generic browser, phone utility or BLE shell is useful for inspection only if
it supports encrypted bonded access, 128-bit UUIDs, indications, a large enough
ATT MTU and binary writes. Writing plain JSON directly to a characteristic does
not work: field messages require the section 6 frame header. Likewise, WTP
messages use the WTP/1 16-byte header and CRC-32C; they do not use the field
frame header.

## 3. Discovery and exact-device identity

The advertisement contains the custom service UUID. The scan response complete
local name is derived from the last six hexadecimal digits of the checked Wi-Fi
station MAC:

```text
WsprryPico-<station-MAC-suffix>
```

For a station MAC ending in `0a:60:df`, the name is
`WsprryPico-0a60df`. The suffix is a convenience, not a cryptographic identity.
The BLE controller address is also not the WTP device ID.

The standard GAP Device Name characteristic is the generic string
`WsprryPico`. Operating-system settings or a cached bond may therefore display
that generic name even when the live scan-response name includes a suffix. A
client MUST NOT accept either name as exact-device proof.

After the link is encrypted, read the identity characteristic. Its entire value
is a UTF-8 JSON object with exactly these members:

```json
{"device_id":"00112233445566778899aabbccddeeff","generation":0}
```

- `device_id` is exactly 32 lowercase hexadecimal characters.
- `generation` is the current committed provisioning-profile generation.
- No password, Wi-Fi credential, certificate, key or bond identifier is
  returned.

The client MUST compare `device_id` with a value obtained through a trusted
inventory or explicit USB-local inspection. A mismatch is a hard wrong-device
failure. The client SHOULD retain the observed `generation` for optimistic
concurrency during profile replacement.

## 4. Pairing, bonds and application authorization

The Bluetooth layer uses LE Secure Connections, bonding and the Just Works
association model. There is no Bluetooth PIN or numeric comparison. All custom
characteristics require an encrypted link with a 16-byte encryption key.

Just Works encrypts the link but does not authenticate a new peer against an
active man-in-the-middle attack. A new controller can pair only during a
physically or USB-locally opened 120-second enrollment window. On the trusted
USB Console CDC, after verifying that the device is idle and output is inactive,
the operator opens that window with:

```text
ACCESS ENROLL <full-device-id>
```

The BLE client cannot open its own enrollment window. Outside the window, new
pairing fails closed. An authorized retained bond may reconnect without opening
enrollment. At most four authorized bonds are retained; the fifth is rejected
and no existing bond is silently evicted.

Bluetooth pairing alone creates, at most, a provisional bond. The client must
then send the `authorize` operation with the local-access password. On a device
still using the public default, the password is:

```text
wspr-<station-MAC-suffix>
```

For the earlier example it is `wspr-0a60df`. This default is intentionally
public; the physical enrollment window is the proof of possession. A
syntactically valid but incorrect password or a disconnect deletes the
provisional bond. If the enrollment window expires while the provisional link
remains open, the target erases that bond, invalidates the application session
and requests link closure. Erasure failure disables BLE local control. A client
SHOULD still disconnect promptly after an authorization rejection rather than
holding an unusable link until timeout. A successful authorization promotes the
bond to an application-authorized principal.

An already-authorized retained bond is admitted when the encrypted link is
restored. It still sends `authorize` to establish a new field session, but the
current target treats that request's required `password` member as
non-authoritative and does not validate its contents. Bluefy sends an empty
string; the current native client still prompts for and sends a bounded value.
Entering text in this request is not a fresh password proof and MUST NOT be
represented as one. A new or provisional bond still requires the
current nonempty password, and empty-password authorization MUST fail for it.
Sensitive profile application uses the separate fresh `profile_step_up`
exchange in section 9.

Only one BLE connection is admitted at a time. Security loss immediately
revokes application authority, clears queued output and closes the logical WTP
endpoint before the asynchronous disconnect completes.

## 5. Service and characteristics

All UUIDs use the base `xxxxxxxx-5bf1-4f21-a486-3e8f70c12201`.

| Role | UUID | GATT properties | Application use |
| --- | --- | --- | --- |
| Field service | `7d6b0001-5bf1-4f21-a486-3e8f70c12201` | Primary service | Discovery filter and service container |
| Identity | `7d6b0002-5bf1-4f21-a486-3e8f70c12201` | Read, encrypted, 16-byte key | Full device ID and profile generation |
| Field command | `7d6b0003-5bf1-4f21-a486-3e8f70c12201` | Write and Write Without Response, encrypted, 16-byte key | Framed field requests; optionally raw WTP after carrier selection |
| Field status | `7d6b0004-5bf1-4f21-a486-3e8f70c12201` | Indicate, encrypted, 16-byte key | Framed field replies; optionally raw WTP after carrier selection |
| WTP command | `7d6b0005-5bf1-4f21-a486-3e8f70c12201` | Write, encrypted, 16-byte key | Dedicated raw WTP/1 client-to-device bytes |
| WTP status | `7d6b0006-5bf1-4f21-a486-3e8f70c12201` | Indicate, encrypted, 16-byte key | Dedicated raw WTP/1 device-to-client bytes |

The client MUST enable indications by writing little-endian `0x0002` (`02 00`)
to the applicable Client Characteristic Configuration Descriptor before sending
commands. Notifications (`0x0001`) are not accepted. Disabling the active WTP
CCCD closes the logical WTP endpoint. Disabling field-status indications also
resets an incomplete field-message reassembly.

Prepared or queued writes are not supported. Every characteristic write has
offset zero and is an ordinary ATT write request or, where the characteristic
allows it, write command.

The largest characteristic value used by this protocol is 64 bytes. A client
and target pair must negotiate an ATT MTU that can carry the intended value,
including the three-byte ATT overhead. The default 23-byte ATT MTU is not
sufficient for a 64-byte value and is not evidence of full interoperability.

## 6. Field command/status framing

Field JSON is split into one to sixteen GATT values. Each value is between 5 and
64 bytes: a four-byte header followed by 1 to 60 payload bytes.

| Offset | Size | Field | Meaning |
| ---: | ---: | --- | --- |
| 0 | 1 | framing version | Exact value `1` |
| 1 | 1 | flags | Bit 0 `FIRST`; bit 1 `LAST`; all other bits zero |
| 2 | 1 | sequence | Zero-based frame number, strictly increasing, maximum 15 |
| 3 | 1 | payload length | Exact number of following bytes, 1 through 60 |
| 4 | 1–60 | payload | Consecutive message bytes |

The first frame MUST have `FIRST` set and sequence zero. The final frame MUST
have `LAST` set. A one-frame message has both bits set and flags value `3`.
There are no gaps, duplicates, restarts or interleaved messages. Reserved flag
bits, an unexpected sequence, an empty payload, a mismatched length or more than
16 frames invalidates and resets the current reassembly.

The generic frame capacity is 960 bytes, but the application limits are lower:

| Direction | Maximum complete JSON message |
| --- | ---: |
| Client to device | 512 bytes |
| Device to client | 256 bytes |

The payload is exactly one UTF-8 JSON object with no byte-order mark or trailing
data. Request objects are closed: unknown or missing members are invalid. The
device permits only one queued field reply, and a conforming client sends one
field request at a time, correlates the response by `request_id`, and waits for
all response indications to complete before starting an unrelated exchange.

Clients SHOULD use acknowledged writes for field frames. The selected Bluefy
controller-time path may send leading `time_submit` frames without response and
the final frame with response. ATT ordering plus the acknowledged tail preserves
complete-message ordering while staying inside the time-uncertainty budget.
The application response still arrives as one or more indications.

### Example frame

The five-byte value below is a complete one-byte message payload containing
ASCII `{` solely to illustrate the header; it is not valid application JSON:

```text
01 03 00 01 7b
```

## 7. Common JSON rules

Every field request contains:

```json
{
  "version": 1,
  "operation": "operation_name",
  "request_id": "11111111111111111111111111111111",
  "session_id": "22222222222222222222222222222222",
  "device_id": "00112233445566778899aabbccddeeff"
}
```

- `version` is the JSON integer `1`.
- `operation` is one of the exact lowercase names documented below.
- `request_id`, `session_id` and `device_id` are each exactly 32 lowercase
  hexadecimal characters unless a section explicitly describes another bounded
  string.
- The `device_id` in every request MUST match the identity characteristic.
- Integers used by this command vocabulary are non-negative JSON integers no
  greater than 2,147,483,647. Nanosecond quantities that can exceed that range
  are canonical unsigned decimal strings with no sign or leading zero.
- Unknown members are rejected. Clients must not use an unknown member as an
  extension mechanism.

There are two session identifiers:

- the **field session** is selected by `authorize` and binds Identify, status,
  time, carrier selection and profile step-up; and
- the **profile session** is selected by `open` and binds `write`, `apply` and
  `cancel` for one staged profile.

They MUST NOT be confused. WTP has its own independent `session_id` inside the
WTP/1 envelope.

### Response families

Authorization replies contain `version`, `request_id`, `ok`, `generation` and,
on failure, `error`.

General field replies contain `version`, `request_id`, `ok` and either the
operation-specific success members or `error`.

Provisioning transaction replies contain:

```json
{
  "version": 1,
  "request_id": "11111111111111111111111111111111",
  "ok": true,
  "generation": 0,
  "accepted_bytes": 0,
  "replayed": false
}
```

An error reply has `ok:false` and adds `error`. Clients MUST correlate by exact
`request_id`, reject malformed or duplicate responses, and treat disconnect or
timeout as an unknown result rather than assuming a persistent operation did or
did not commit.

The profile transaction retains eight request digests for five minutes. An
exact duplicate request ID and identical bound content returns the prior result
with `replayed:true`. Reusing that request ID with different content is a
`replay` failure and terminates the staged transaction. This replay behavior
does not turn the other field operations into generally replayable commands.

## 8. Authorization and field operations

### `authorize`

Request fields are the common fields plus `password`. `session_id` becomes the
new field session.

```json
{
  "version": 1,
  "operation": "authorize",
  "request_id": "11111111111111111111111111111111",
  "session_id": "22222222222222222222222222222222",
  "device_id": "00112233445566778899aabbccddeeff",
  "password": "wspr-0a60df"
}
```

For a new or provisional bond, the password is 8 through 63 printable ASCII
characters and is validated as the application credential. For an already-
authorized retained bond, the member remains syntactically required but its
value is currently ignored. Bluefy sends an empty string; the native client
currently sends its prompted bounded value. Success establishes the field
session and restores field-framed mode. It does not create a fresh password
proof for profile, password, bond, trust or reset mutation.

### `identify`

The request has only the common fields and uses the field session. Success adds:

```json
{"identified":true}
```

The onboard LED runs the bounded Identify pattern. It is an operator aid, not a
safety indicator and not proof of RF state.

### `field_status`

The request has only the common fields and uses the field session. Success adds:

```json
{
  "time_source": "controller",
  "time_age_ns": "0",
  "time_uncertainty_ns": "251050999",
  "time_disagreement": false,
  "indicator": "off",
  "indicator_fault": false
}
```

`time_source` is `none`, `sntp`, `controller` or `disagreement`. `indicator` is
`off`, `softap_ready` or `identify`. Age and uncertainty are canonical decimal
strings. This is nonsensitive status; it contains no credential or BLE
principal.

### Controller time: `time_challenge` and `time_submit`

Controller time is a bound two-message exchange. It is not a claim that the
phone clock was independently calibrated.

The challenge request adds `nonce`. Supported clients use a fresh 32-lowercase-
hex value. The target accepts a nonempty identifier of at most 64 ASCII graphic
characters (`0x21` through `0x7e`); spaces and control characters are rejected.

```json
{
  "version": 1,
  "operation": "time_challenge",
  "request_id": "33333333333333333333333333333333",
  "session_id": "22222222222222222222222222222222",
  "device_id": "00112233445566778899aabbccddeeff",
  "nonce": "44444444444444444444444444444444"
}
```

Success echoes `nonce` and adds target `sampled_monotonic_ns` as a canonical
decimal string. The client MUST sample its UTC only after receiving the complete
challenge reply, then promptly send:

```json
{
  "version": 1,
  "operation": "time_submit",
  "request_id": "55555555555555555555555555555555",
  "session_id": "22222222222222222222222222222222",
  "device_id": "00112233445566778899aabbccddeeff",
  "nonce": "44444444444444444444444444444444",
  "utc_ns": "1800000000000000000"
}
```

Success adds `"accepted":true`. The target charges a fixed 250 ms allowance,
the target-observed interval from final challenge-reply delivery to submission,
and a bounded local margin against the unchanged 500 ms maximum uncertainty.
The challenge expires after 10 seconds, but a request that consumes the
uncertainty budget fails earlier with `uncertainty`. A nonce is single use;
disconnect cancels an outstanding challenge.

An authoritative valid SNTP observation is not displaced by controller time;
the controller submission is rejected as busy without comparing it for
disagreement. A nonoverlapping same-principal controller refresh, or a later
nonoverlapping SNTP observation against an active controller source, latches
`disagreement` and invalidates usable UTC. A different controller principal is
rejected as busy while the active controller source remains valid. Recovery
from disagreement requires two overlapping observations from the same source
and, for controller time, the same principal.

### `select_wtp_status_carrier`

This operation exists for the Bluefy connection. The request has only the
common fields and uses the field session. Success is:

```json
{
  "version": 1,
  "request_id": "66666666666666666666666666666666",
  "ok": true,
  "carrier": "field_status",
  "command_carrier": "field_command"
}
```

After that reply is completely received, both sides reinterpret the field
command/status characteristic values as raw WTP/1 bytes. The custom four-byte
field header is no longer present. The mode is connection-scoped. To return to
field JSON, deliberately disconnect, reconnect, verify identity and authorize a
new field session. The native BlueZ client does not select this mode; it uses
the dedicated WTP characteristic pair.

## 9. Atomic profile provisioning

A profile replacement is a bounded transaction. It is not a sequence of
partially active settings. The target stages the complete document, validates
it, commits one new generation, returns the nonsensitive apply result and only
then releases network activation after the final response indication is
confirmed.

The transaction permits one active profile session, no more than 7,168 staged
bytes, ordered nonempty fragments and 30 seconds without progress. Because each
fragment contains at least one byte, the byte ceiling also bounds the worst case
to 7,168 fragments; the preferred 64-byte client chunk does not impose a lower
4,096-byte limit. A terminal failure, cancellation or timeout scrubs staged
secrets. A BLE disconnect invalidates the field session and any fresh profile
step-up, but the manager retains an open staged transaction until bounded
cancellation, same-principal/session reconciliation or the 30-second
no-progress timeout. Clients MUST NOT assume that link loss cancelled it. Flash
is not claimed to provide confidentiality against physical extraction.
The 7,168-byte ceiling applies to the complete canonical wire JSON, including
PEM line breaks encoded as the short JSON `\\r` and `\\n` escapes. A valid
document at that boundary must remain storable after target-side validation;
an internal reserialization must not silently lower the effective limit.

### Profile document

The transferred bytes are one canonical version-1 JSON object:

```json
{
  "version": 1,
  "device_id": "00112233445566778899aabbccddeeff",
  "wifi": {
    "ssid": "example-network",
    "password": "replace-this",
    "time_server": "pool.ntp.org"
  },
  "tls": {
    "hostname": "wsprrypico-0a60df.local",
    "port": 443,
    "server_certificate": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n",
    "server_private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
    "client_ca": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----\n"
  }
}
```

The root, `wifi` and `tls` objects are closed. The device ID must match the
connected target. The SSID is 1–32 printable ASCII characters; the Wi-Fi
password is 8–63 printable ASCII characters. The time server is a canonical
unicast IPv4 address or valid DNS name. The hostname is one `.local` label and
is canonicalized to lowercase. The port is 1–65535. Certificates are printable
PEM certificate blocks no larger than 3,072 bytes each. The private key is a
PKCS#8 `PRIVATE KEY` or SEC1 `EC PRIVATE KEY` PEM block no larger than 2,048
bytes. The platform additionally verifies certificate chain, key pair, exact
SAN/device binding, purpose, validity and accepted algorithms.
Certificate validity at apply uses accepted device UTC. A target that has not
yet joined a station network needs authenticated controller time before its
first profile can pass this check.

Real profiles contain private material. Keep them outside Git, do not paste
them into issue reports or logs, and clear the Bluefy form/tab after use.

### Step 1: `open`

Choose a fresh profile-session ID. The request has only the common fields, with
that profile session in `session_id`. Success reports the current `generation`.

### Step 2: ordered `write`

Split the canonical profile bytes into nonempty chunks of at most 64 bytes.
Each `write` request adds:

```json
{
  "offset": 0,
  "final": false,
  "payload": "eyJ2ZXJzaW9uIjoxLCJkZXZpY2VfaWQiOiIwMDE="
}
```

`payload` is canonical base64 and decodes to 1–64 bytes. `offset` is the exact
cumulative byte count before this chunk. Set `final:true` only on the last
chunk. Success reports cumulative `accepted_bytes`. A gap, overlap, duplicate
fragment, write after final or mismatched session is rejected.

### Step 3: `profile_step_up`

Profile application never inherits ordinary retained-bond authority. After the
last `write`, re-enter the current local password and bind it to the exact
staged digest, profile session, apply request and observed generation:

```json
{
  "version": 1,
  "operation": "profile_step_up",
  "request_id": "77777777777777777777777777777777",
  "session_id": "22222222222222222222222222222222",
  "device_id": "00112233445566778899aabbccddeeff",
  "profile_session_id": "88888888888888888888888888888888",
  "apply_request_id": "99999999999999999999999999999999",
  "expected_generation": 0,
  "password": "wspr-0a60df"
}
```

Here `session_id` is the field session, while `profile_session_id` is the
transaction opened in step 1. The future `apply` request MUST use
`apply_request_id` as its request ID. Success adds the two booleans below. Their
values reflect the current password mode and confirmation state; this example
shows the public-default case before USB-local confirmation:

```json
{"confirmation_required":true,"ready":false}
```

When a custom password is active, a valid idle request can be ready immediately.
While the public default password is active, exact-device USB-local confirmation
is additionally required during the same staged transaction:

```text
ACCESS CONFIRM PROFILE <full-device-id>
```

The client polls readiness with `profile_step_up_status`, using the field
session and the bound `apply_request_id`:

```json
{
  "version": 1,
  "operation": "profile_step_up_status",
  "request_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "session_id": "22222222222222222222222222222222",
  "device_id": "00112233445566778899aabbccddeeff",
  "apply_request_id": "99999999999999999999999999999999"
}
```

Success again reports `confirmation_required` and `ready`. The target must be
idle, unowned, not armed/running/failed, with output known inactive. The page
uses a bounded 25-second confirmation wait so the complete operation remains
inside the provisioning session's 30-second no-progress limit.

### Step 4: `apply`

Only after step-up is ready, send the profile-session request:

```json
{
  "version": 1,
  "operation": "apply",
  "request_id": "99999999999999999999999999999999",
  "session_id": "88888888888888888888888888888888",
  "device_id": "00112233445566778899aabbccddeeff",
  "expected_generation": 0
}
```

The target rechecks authorization, exact staged content, generation and idle/
output state immediately before committing. Success returns the new generation.
The reply is intentionally delivered before disruptive network activation is
released. A disconnect after a successful commit is therefore expected during
runtime replacement, but a missing reply alone is never proof of success or
failure; reconnect and inspect the generation.

### `cancel`

`cancel` uses a fresh request ID and the profile session. It has no fields beyond
the common fields. It scrubs only that staged transaction. A supported client
attempts bounded cancellation after a post-`open` failure, but cancellation is
best effort if the link has already disappeared.

## 10. WTP/1 over GATT

WTP uses the complete byte stream defined in [WTP/1](WTP.md), including the
16-byte `WTPF` header, UTF-8 JSON payload and CRC-32C. GATT does not add another
message envelope or checksum.

### Dedicated carrier

After field authorization:

1. Enable indications on WTP status (`7d6b0006...`).
2. Split the WTP byte stream into nonempty values no larger than 64 bytes and no
   larger than the negotiated ATT value capacity.
3. Write those bytes in order to WTP command (`7d6b0005...`) with response.
4. Concatenate WTP status indications in order and feed them to the WTP/1 frame
   parser.

The first WTP request on a new logical endpoint is `HELLO`, exactly as required
by WTP/1. Its device ID and boot ID must be checked. Field authorization grants
access to the transport; it does not bypass WTP session, claim, lease, replay,
clock, output or lifecycle rules.

### Bluefy field-carrier mode

After successful `select_wtp_status_carrier`, use the same steps but substitute
field command (`7d6b0003...`) and field status (`7d6b0004...`). Values on those
characteristics are then raw WTP bytes, not section 6 frames. Deliberate
reconnect and reauthorization restores field JSON mode.

In either carrier, the device emits at most one outstanding indication and does
not consume the corresponding WTP output bytes until the indication completion
succeeds. A failed completion or inability to continue sending closes the BLE
connection rather than silently dropping protocol bytes.

## 11. Errors

### Application errors

| Error | Meaning for an operator or client |
| --- | --- |
| `invalid_request` | JSON, fields, types, identifiers, version or operation are invalid |
| `authentication_required` | Application authorization, current field session or fresh profile step-up is missing or invalid |
| `wrong_device` | A request or profile names a different full device ID |
| `session_busy` | Another provisioning or activation session owns the bounded slot |
| `session_not_found` | The named profile session is absent, expired or already terminal |
| `out_of_order` | Profile offset/final state or another ordered input is wrong |
| `incomplete` | `apply` arrived before the final profile fragment |
| `oversize` | A message, decoded fragment, staged profile or bounded count is too large |
| `malformed` | The complete staged profile is not the closed version-1 profile format |
| `credential_invalid` | Certificate/key/CA/device/hostname validation failed |
| `conflict` | Generation, bound digest, request binding or current state changed |
| `busy` | Job/RF/output or another exclusive runtime condition blocks the operation |
| `capacity` | The authorized bond store is full |
| `replay` | A retained request ID was reused with different bound content, or a one-use value was reused |
| `timeout` | The transaction, proof, challenge or session exceeded its bound |
| `uncertainty` | Controller-time latency or value cannot satisfy the UTC uncertainty contract |
| `storage_fault` | Durable profile/access storage is not trustworthy |
| `activation_fault` | The committed network-runtime transition failed or became unsafe |

The access-policy layer also has internal `confirmation_required`, `expired`
and `bond_erase_fault` states. The current GATT adapter maps them to
`authentication_required`, `timeout` or `storage_fault` as applicable; clients
MUST NOT depend on the internal names appearing as JSON error strings.

Treat unknown error strings as a device rejection. Do not display a returned
payload as trusted prose and never include secrets in diagnostics.

### ATT errors

The target can reject a characteristic operation before producing a JSON reply:

| ATT outcome | Typical cause |
| --- | --- |
| Write not permitted | Wrong characteristic or no current connection owner |
| Request not supported | Prepared/queued transaction mode was attempted |
| Invalid offset | A long-write or nonzero attribute offset was attempted |
| Invalid attribute value length | Empty/oversize WTP value, malformed CCCD, or oversized field frame |
| Value not allowed | Unsupported CCCD value or invalid field frame/order |
| Insufficient authentication | Link/admission is absent, or a WTP write lacks application authorization |
| Insufficient resources | Required indications are disabled, a response is already queued, a malformed command produced no bounded reply, or WTP backpressure prevents input |

An unparseable request or one without a usable `request_id` cannot be correlated
to a JSON error reply and currently reaches the last ATT outcome above. A
well-formed request with a usable ID receives `invalid_request` when its closed
schema, version, operation or fields are invalid.

A browser may collapse one of these or a link loss to `operation_failed`. That
string is not a target application error and does not identify the cause by
itself.

## 12. Troubleshooting checklist

### The device appears as generic `WsprryPico`

That can be the GAP Device Name or a cached operating-system bond. Use a live
service-filtered scan, prefer the `WsprryPico-<suffix>` scan-response name, then
verify the encrypted identity characteristic. Never authorize based on the
display name alone.

### Pairing or the first connection fails

Verify the exact BLE address and full device ID, open the 120-second enrollment
window, confirm that fewer than four authorized bonds exist and ensure no other
BLE controller is connected. Do not mark the peer globally trusted or weaken
the target policy as a workaround. If application authorization is rejected,
disconnect promptly. An otherwise abandoned provisional link is erased and
closed by the target when the enrollment window expires.

### Field commands time out

Confirm that field-status indications are enabled with CCCD `0x0002`, the ATT
MTU carries the emitted frame size, only one request is outstanding, every
frame sequence is contiguous and the response request ID matches. On the USB
Console, `ACCESS STATUS` exposes nonsensitive BLE counters useful for separating
missing writes, reassembly failures, queued responses and indication failures.

### Controller time reports `uncertainty`

The complete challenge response must arrive before the controller samples UTC,
and submission must follow promptly. Use the supported client, keep the same
connection and do not perform interactive work between the two messages.
`uncertainty` is a deliberate accuracy rejection, not permission to enlarge the
500 ms bound.

### Field commands stop working after WTP status

Bluefy deliberately selected raw-WTP mode on the field characteristics. That
mode lasts until disconnect. Reconnect, re-read identity and authorize a new
field session before sending framed field commands.

### Profile apply is rejected

Check, in order: exact device ID; profile generation; complete ordered transfer;
fresh current password; `profile_step_up` binding; required USB-local
confirmation while the public default is active; idle/unowned/output-inactive
state; and certificate/key/device validation. Do not retry `apply` with a new
request ID until the commit generation is known. If the link was lost after
`open`, reconnect the same authorized bond, establish a new field session and
either cancel the recorded profile session or wait for its 30-second
no-progress expiry. Do not assume disconnect discarded the staged transaction.

## 13. Currently absent GATT administration

The current GATT vocabulary does not expose password change, arbitrary bond
removal, enrollment opening, field-mode administration or the three reset
levels. Those controls remain governed by the Phase 12 field-access contract and
the accepted USB-local/physical recovery boundary until explicit GATT schemas
and production surfaces are implemented. A client MUST NOT invent operation
names for them or treat `invalid_request` as evidence that a reset occurred.

## 14. Implementation and evidence boundary

The wire behavior is implemented by:

- `src/provisioning/pico/field_access.gatt` for the attribute schema;
- `src/provisioning/gatt_framing.*` for field segmentation;
- `src/provisioning/command.*` and `src/provisioning/ble_session.*` for the JSON
  vocabulary and authorization state;
- `src/provisioning/pico/gatt_transport.*` for BTstack transport behavior;
- `src/provisioning/web/bluefy.js` for the selected iPhone client; and
- `scripts/wsprrypico_ble.py` for the supported BlueZ client.

Those files are implementations, not an excuse to leave behavior undocumented.
The machine-readable [Field-GATT/1 vectors](Field-GATT-v1-vectors.json) and
deterministic firmware, Bluefy and native-Pi tests enforce the frozen constants,
profile sequence, 7,168-byte transfer boundary, bound step-up/apply behavior and
provisional-bond expiry cleanup. If code, vectors and this contract disagree,
the change is not conforming. Compatible clarifications must update all affected
artifacts; incompatible wire behavior requires a new protocol version.

Host tests and cross-links establish source behavior only. The current physical
acceptance state is maintained in the
[Phase 12 plan](../development/phase12-plan.md) and
[production acceptance review](../development/phase12-production-acceptance-review.md).
Neither this guide nor a successful GATT exchange proves iPhone offline-page
support, complete physical interoperability, RF behavior or release readiness.
