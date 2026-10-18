# Shared browser-facing JSON API v1

The independently advertised `transmitter-rf-calibration/1` resource at
`/api/v1/rf-calibration` supports exact-target/revision GET/PUT through admitted
management carriers. It preserves legacy closed config/progress shapes.
`transmitter-ntp-observations/1` at `/api/v1/ntp-observations` binds source-labelled
measurements to member/boot/firmware/clock identity. See the
[NTP work record](development/ntp-work-results.md) for fields, units, authority,
fallback and evidence limits.

The application also exposes these application services through the separately framed
[USB management adapter](protocol/USB-Management.md), under internal local
physical authority. It supports configuration, saved progress, canonical name,
saved Wi-Fi lifecycle, restart and qualified controller UTC without a Pico
network session. USB capability/application views identify `usb_physical` and
discovery selects `transmitter-management/3`; existing network views retain
their prior shapes and carrier schemas. USB grants no transmitter ownership
and uses the same JobService, validators, revisions and journals. See [USB local configuration](development/usb-local-configuration.md) for
configuration and delivery semantics.

The independently versioned [hostname resource](development/hostname.md) is at `GET/PUT /api/v1/hostname`. It preserves Config, application, capabilities and consumer identity v1 shapes. Consumer renames preserve CA/client trust, consume a profile generation and apply on explicit restart; engineering names remain credential-bound. See that record for exact envelopes, readback and recovery.

Main-page presentation uses the existing identity authority: the boot-active hostname is the shared
heading and tab identity. About this Pico / Diagnostics exposes the full stable
device ID and separately labelled boot observation. Public, active, rename-pending,
last-confirmed and unavailable states are explicit. The existing presentation,
identity and hostname API shapes and all carrier/session authorities are unchanged.
See the [device presentation contract](development/device-presentation.md).

The browser provides one control document with reloadable `/station` and
`/wifi-host` areas, retaining `/index.html`, `/radio` and `/owner.html` aliases.
Fresh admitted infrastructure roots select Station/Transmission; accepted AP
roots select Wi-Fi/Host. Consumer field editors retain authenticated setup
transactions. Engineering field saves use advertised config merge with the
existing target/revision, while an unconfigured engineering deployment retains
an explicit initial complete-configuration save. API/schema/authentication and
radio ownership contracts are unchanged. See the [organization record](development/browser-pages.md).

Status: implemented by WsprryPico; compatible WsprryPi adapter adoption is
independently maintained.
`/api/v1/` selects the URL namespace, independently of firmware and WTP/1.
Resource schemas within it are versioned separately: for example,
`/api/v1/application/3` returns `transmitter-application/3`, while Config
content still has `version:1` at `/api/v1/config/3`.
The browser, USB WTP, TCP WTP and standalone scheduler use one JobService.

The [shared transmitter application and fleet contract](transmitter-application-contract.md)
defines the application/configuration model for Pi and Pico members. The
[Pico foundation](development/shared-transmitter-application.md) implements bounded
member, station and hardware resources with independent schema versions; full application parity is not claimed. Existing routes and Config v1 retain their meanings.

## Transport and trust

The Pico serves HTTPS and WTP on an explicitly configured TLS port. In the
engineering profile, station TLS 1.3, client certificate verification and ALPN
are mandatory: `http/1.1` selects this API; `wtp/1` selects the unchanged WTP
frame stream. The normal consumer image defaults to Plain LAN WTP on station TCP port 31417
following infrastructure SNTP; optional TLS-WTP uses TLS 1.3/ALPN `wtp/1` without
client certificates. Neither WTP listener exposes JSON management. Consumer
station/AP port-80 management uses the separately authenticated and encrypted
[Consumer-Radio/1](protocol/Consumer-Radio-v1.md) adapter. Raw `/api/v1/` requests
on consumer HTTP are unavailable. Blank/recovery commissioning keeps its own
bounded AP-only routes and transactional authority. No TLS downgrade or
management-carrier fallback is permitted. The engineering station authenticated principal is the SHA-256
fingerprint of the leaf client certificate. Consumer LAN WTP uses one shared
local-network principal. Device-specific credential setup and renewal are described in
[network control](development/network-control.md).

The selected
[Engineering field-access contract](development/field-access.md)
defines profile-specific local authority.
It adds an interface-scoped engineering SoftAP exception:
server-authenticated
TLS plus a password login issues a random, boot/access-epoch-bound session-cookie
principal. It reuses these API schemas, Origin/Host/Fetch Metadata rules and
JobService semantics without requiring a client certificate. It never applies
to the engineering station browser API or engineering raw TLS-WTP, which retain the
certificate principal above. Before usable device UTC, a provisioned SoftAP permits only local
identity/login/status/controller-time plus API capabilities, status and WTP
HELLO. A blank-device bootstrap adds no API-v1 routes. BLE frames existing WTP
semantics through a separately bounded adapter.

Allowed authorities are the certified deployment hostname and the current IPv4
address, each with the configured port (omit `:443` at port 443). DNS case and a
single terminal root dot canonicalize before validation. Host and any supplied
HTTPS Origin must each be allowed and must match one another; hostname/IP mixing
is cross-origin and rejected. Legacy IP-only bundles admit only current IPv4.
Literal-IP browser access additionally requires a matching IP SAN. See the
[shared identity contract](development/network-identity.md).
Browser mutations require all of:

- `Origin: https://<authority>`;
- `Content-Type: application/json`;
- `X-WsprryPico-Request: 1`;
- a non-cross-site Fetch Metadata context when that header is supplied.

Responses use `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, a
restrictive CSP with hashes for embedded styles/scripts, and no referrer. API
keys, passwords and certificates do not belong in URLs. The UI neither stores
credentials in script-readable Web Storage/IndexedDB nor prints Wi-Fi passwords.
The engineering SoftAP bearer is instead an opaque Secure, HttpOnly
session cookie that page script cannot read.

## Resources

| Method and path | Behavior |
|---|---|
| GET `/api/v1/capabilities` | `api_version`, WTP service capabilities under `wtp`, implemented management `features`, body/connection limits, `active_job_connections` |
| GET `/api/v1/management` | `transmitter-management/2` on network carriers; `/3` on USB. Support, availability and selected authenticated context; see [current carrier policy](#management-carrier-discovery). |
| GET `/api/v1/status` | `job` service status/terminal records, `standalone` config/clock health, `network` state |
| GET `/api/v1/jobs` | Same current/retained job inspection snapshot as status |
| POST `/api/v1/jobs` | Explicit HELLO, CLAIM, RENEW, LOAD, LOAD_MESSAGE, ARM, ABORT or RELEASE through the common service |
| POST `/api/v1/jobs/{id}/abort` | ABORT only; URL ID must match the request body's job ID |
| GET `/api/v1/config` | `{"config": <redacted config or null>}` and ETag |
| PUT `/api/v1/config` | Save required Config v1 fields, preserving omitted optional settings from existing configuration; requires If-Match |
| POST `/api/v1/config/update` | Advertised atomic merge or explicit replacement, with exact member target and If-Match |
| GET/PUT `/api/v1/config/2` | Config v1 content; explicit Type 1/2/3 admission on writes; legacy redacted read shape |
| POST `/api/v1/config/update/2` | `transmitter-config-update/1`; Type 1/2/3 admission |
| GET/PUT `/api/v1/config/3` | Config v1 content with effective `gpio_drive_ma`, including default 4; Type 1/2/3 admission |
| POST `/api/v1/config/update/3` | `transmitter-config-update/2`; drive-aware merge/replacement |
| GET/PUT `/api/v1/config/4`, POST `/api/v1/config/update/4` | Amplifier-aware Config v1; update uses `transmitter-config-update/3`; preserves Type 1/2/3 and drive support |
| GET `/api/v1/application/4`, GET/PUT `/api/v1/hardware/3` | `transmitter-application/4`, `transmitter-hardware/3`; explicit amplifier pin/polarity plus drive |
| GET `/api/v1/pins/2`, POST `/api/v1/pins/validate/2` | Negotiated amplifier choices/active plan and nonmutating validation |
| GET `/api/v1/progress/3`, POST `/api/v1/progress/update/3`, POST `/api/v1/progress/apply/3` | `transmitter-progress/3`; amplifier-aware independent drafts and explicit application |
| GET `/api/v1/application`, `/api/v1/application/2`, `/api/v1/application/3` | `transmitter-application/1`, `/2`, `/3`; embedded station/1 + hardware/1, station/2 + hardware/1, station/2 + hardware/2 respectively |
| GET/PUT `/api/v1/station`, `/api/v1/station/2` | `transmitter-station/1` Type 1, or `/2` Type 1/2/3; scoped complete station replacement |
| GET/PUT `/api/v1/hardware` | `transmitter-hardware/1`; scoped complete pin-plan replacement |
| GET `/api/v1/hardware/2` | `transmitter-hardware/2`; adds nested drive resource; write pins through hardware/1 or drive through its dedicated route |
| GET `/api/v1/pins` | Eligible choices and boot-selected active plan |
| POST `/api/v1/pins/validate` | Nonmutating complete candidate pin-plan review |
| GET/PUT `/api/v1/gpio-drive` | `transmitter-gpio-drive/1`; separate saved/boot/pad observations and idle-only saved drive update |
| GET/PUT `/api/v1/hostname` | `transmitter-hostname/1`; profile-owned saved/active/default names; save applies on explicit restart |
| GET `/api/v1/progress`, `/api/v1/progress/2` | `transmitter-progress/1` or drive-aware `/2`; independent saved draft |
| POST `/api/v1/progress/update`, `/api/v1/progress/update/2` | Matching progress schema; save valid units with per-field outcomes, without applying them |
| POST `/api/v1/progress/apply`, `/api/v1/progress/apply/2` | Matching progress schema; explicit saved revision/domain application through complete config authority |
| POST `/api/v1/wspr-plan` | Side-effect-free `wspr-plan/1` preview; no target or If-Match required |
| GET `/api/v1/schedules` | `{"schedules":[...]}` and ETag |
| PUT `/api/v1/schedules` | Replace only schedules using the same config validator/journal; requires If-Match |
| GET `/api/v1/network` | Initialized/enabled/link/IP, requested enable state, control availability and SNTP counters; ETag |
| PUT `/api/v1/network` | `{"enabled":true|false}`; idle-only volatile change with If-Match |
| POST `/api/v1/restart` | Empty object `{}`; idle-only, If-Match; returns 202 before deferred restart |

This is the shared handler inventory, not a promise that every carrier admits
every route. Optional progress/hostname/restart adapters must be present.
Engineering field HTTPS classifies configuration reads, pin review and writes
as Configure and denies them before clock qualification. Its current allowlist
also excludes hostname and GET config/2; use its admitted config or config/3
view. Consumer station identity/Wi-Fi remain transactional setup operations.
USB-only Wi-Fi, AP and time routes are listed in
[USB-Management/1](protocol/USB-Management.md); public commissioning and
Consumer-Recovery retain their separate contracts.

Static `/`, `/style.css` and `/app.js` require station mTLS or the provisioned
SoftAP's server-authenticated TLS transport. SoftAP API calls additionally
require the HttpOnly application cookie.
The document embeds styles and scripts so a browser does not need concurrent
asset connections. The individual asset paths remain available to tooling.

## Configuration and revisions

The configuration schema is the existing [standalone version-1 schema](development/standalone.md).
On initial setup or explicit replacement, omitted `wifi.ntp_ipv4` uses
`pool.ntp.org`; ordinary API PUT preserves the saved value. An explicit hostname or IPv4
address is preserved, and invalid/empty values are rejected. The browser prefills
the same default for a new configuration.
Passwords are returned as JSON null. A null password in PUT preserves the stored
password; it is rejected when no stored config exists. Supplying a new password
replaces it after full validation. Successful and failed responses never echo it.
The existing station, recurrence, overlap, expiry and storage rules remain in
force. Autonomous WSPR requires an explicitly saved runtime base frequency;
firmware images select none. Config v1 has no per-schedule frequency/mode
field. The independently versioned `transmitter-standalone-frequency/1`
resource at `/api/v1/standalone-frequency` owns the shared standalone WSPR
frequency. GET reports whole-Hz `frequency_hz` (null when unset), `configured`,
`allowed`, target identity and storage health with the current ETag. PUT uses
that schema, the exact member/boot target and an integer `frequency_hz`, with
If-Match and idle authority. All four WSPR tones must pass the current engine
limits and saved frequency permissions. A first frequency selection leaves
schedules disabled until explicitly enabled; later changes apply to future
jobs. Legacy config/progress routes preserve the selection without exposing
it in their closed schemas. Legacy application recurrence uses `"0"` for an
unset frequency; the dedicated resource is authoritative. See the
[resource schema](protocol/transmitter-standalone-frequency-1.schema.json).
Complete job routes support the advertised modes/frequencies, subject to frequency policy
and engine admission. Type 1/2/3 station admission requires the explicit
versioned routes below; its software acceptance does not close the separate
captured-RF decode item in the [backlog](development/consolidated-backlog.md).

Optional top-level `allow_unqualified_frequency` and
`allow_non_amateur_frequency` booleans are advanced, persisted settings. Both
default to false; non-amateur operation requires both true. Ordinary config PUT,
station/hardware/schedule updates and browser saves preserve omitted flags.
Explicit false or explicit replacement can reset them. False values are omitted from the
canonical config response; status reports both booleans. They take effect on
subsequent admissions while idle, without reboot. See the
[frequency policy](development/standalone.md) for failed/untested bands,
per-event checks and the hardware limits that neither setting overrides.

The [configuration-update contract](development/configuration-updates.md) defines
the intentional change from reset-by-omission PUT policy, exact merge/replace
envelopes, target/revision checks and bounds. Console CONFIG and durable decoding
retain complete replacement and existing defaults. No PATCH is added.

ETags are quoted opaque hashes of device/boot identity, persisted config and
journal sequence, network-change/restart revision, and attached profile,
hostname/local-settings and progress revision contexts. Send the exact ETag in `If-Match` for any configuration,
schedule or network PUT, and restart POST. Missing revisions return 428; stale revisions return
412. Console config changes and reboot invalidate relevant saved revisions.
Identical saves consume a journal generation and invalidate the revision; persistence still returns an
explicit reboot requirement. Station and schedule changes apply to subsequent
admissions without reboot unless another restart latch blocks admission. Pins
and drive latch restart/output inhibition, including A/B/A saves; a return to
boot values cannot clear that latch. A saved SSID, password or time-server difference from
the boot configuration requires restart; subsequent station-only saves cannot
hide that pending difference. STOP remains suspended and the watermark is preserved. Failed storage never reports a successful save.
Changes require no owner, no armed/running/output state, and no latched fault.

A network enable/disable request is queued until its HTTP response is acknowledged.
Termination before the complete HTTP response is acknowledged cancels it. A
FIN or reset after that acknowledgement does not undo the accepted action;
acknowledgement of the later TLS close notification is not required. A monotonically increasing connection
transaction token binds completion; an unrelated response or close cannot apply
or cancel it. Link loss/server shutdown cancels it. It is applied only if the service is still idle;
a newly acquired owner cancels the queued change. `requested_enabled` describes
the pending HTTP request, while `enabled` describes applied network availability.
On an orderly disable, availability becomes false immediately.
`withdrawal_pending:true` identifies a bounded one-second interval in which the
station remains associated and polled so its already-submitted mDNS goodbye has
a transmission opportunity. No mDNS replies or network reconnects are initiated
during that interval; physical link loss can end it early. `link_status` can
therefore still report the physical link up while `enabled` is false. A rapid
Console ON sets `resume_after_withdrawal:true` and waits for the original deadline
before recreating the station; repeated OFF cancels that resume without extending
the interval. These diagnostics do not assert over-air delivery. This is deliberately
not a persistent Wi-Fi switch. Disabling Wi-Fi requires USB Console `WIFI ON` or
a restart to reconnect. SSID/password/time-server changes use config PUT and
require a restart. Adapters advertising `features.restart:true` accept a browser
restart through the authenticated endpoint above, without USB access. Restart uses
the same acknowledgement/transaction cancellation rules, consumes its revision
and blocks other pending management mutations. The application stops local
scheduling, verifies engine disable and rechecks unowned/inactive/nonfaulted state
immediately before reset. Browser restart cannot recover a latched RF fault.
The UI sends one restart request and waits up to 90 seconds for authenticated
status with a different boot identity. An interrupted or unconfirmed request is
never automatically repeated. Incorrect Wi-Fi or unreachable time-server settings
can still require physical recovery if authenticated networking cannot return.

## Jobs and exact numbers

POST body:

```json
{
  "session_id": "11111111111111111111111111111111",
  "request_id": "22222222222222222222222222222222",
  "operation": "HELLO",
  "body": {
    "versions": ["WTP/1"],
    "client_name": "Example browser",
    "client_version": "1"
  }
}
```

The `body` uses the operation's normative [WTP/1 schema](protocol/WTP.md), including
complete `rf-events/1` LOAD jobs. LOAD's body is the job itself. The API constructs
its internal WTP envelope and uses the existing strict codec, replay cache,
leases, validation and RF lifecycle. A successful response is
`{"ok":true,"request_id":"...","result":{...}}`; a rejected service operation
returns HTTP 409 and `{"ok":false,"request_id":"...","error":{...}}`.
There is no network-accessible physical Console abort operation.

Use a fresh random 32-character lowercase hexadecimal session per controller and
request ID per new operation. Retry the same logical request with the same ID
and identical body; do not generate a new LOAD or ARM after an ambiguous failure
without reconciling status. Claims last 5–60 seconds; RENEW is explicit. A browser
must HELLO, CLAIM, LOAD and ARM; it may ABORT only its own job. RELEASE is rejected
while armed/running/failed or output remains active. Complete job timing continues
locally after a connection closes. Under the current mTLS browser behavior, a
refreshed page gets a new WTP session and cannot silently take over the previous
session's job. The engineering SoftAP same-token reconnect preserves the
authentication principal only; owner resume must also recover the original WTP
session and satisfy its replay rules. The password token alone adopts nothing.

Nanosecond timestamps, durations, frequencies in nanohertz and other WTP 64-bit
quantities remain decimal strings. JavaScript must use BigInt for exact arithmetic.
Configuration seconds are bounded below 2100 and are safe JSON integers.

### QRSS, FSKCW and DFCW messages

Firmware advertising `message_jobs.operation: "LOAD_MESSAGE"` in browser
capabilities accepts compact message bodies through the same jobs route.
The capability also declares `max_characters:32`, `tail_ns:"1000"`,
`max_repeat_count:512` and the three supported mode names. This is an additive
browser operation; WTP/1 continues to use complete `rf-events/1` LOAD jobs.
Older firmware without this capability keeps the message form disabled.

Example body for `operation: "LOAD_MESSAGE"`:

```json
{
  "job_id": "33333333333333333333333333333333",
  "mode": "qrss",
  "message": "TEST",
  "frequency_nhz": "135500000000000",
  "space_frequency_nhz": "0",
  "timing": {
    "dot_ns": "3000000000",
    "dash_ns": "9000000000",
    "intra_gap_ns": "3000000000",
    "character_gap_ns": "9000000000",
    "word_gap_ns": "21000000000"
  },
  "repeat_count": 1,
  "repeat_gap_ns": "0",
  "allow_frequency_adjustment": true
}
```

The limit is 32 ASCII characters including spaces; no silent truncation or
splitting occurs. Alphabet: A–Z, 0–9 and `/?.,-+=`, with ASCII case folding.
ASCII whitespace counts toward length; consecutive whitespace forms one word
gap, and leading/trailing whitespace produces no extra RF interval. A message
must contain a Morse character. Timing fields are positive integer nanoseconds.
FSKCW uses `frequency_nhz` for marks and a lower positive
`space_frequency_nhz` for spaces. DFCW uses those two distinct frequencies for
dots and dashes; both marks have `dot_ns` duration. QRSS and DFCW gaps are RF-off.

The server expands the complete finite message before ordinary LOAD validation;
it does not emit RF until the subsequent ARM succeeds. HELLO, CLAIM, ownership,
lease, replay and ABORT rules apply unchanged. Replay identity binds the entire
original compact request, including text, timing and repetition.

The maximum total duration is the smaller of advertised WTP CAPS and 3,600
seconds, including repetitions, inter-message RF-off gaps and a final 1,000 ns
RF-off tail. A repeat count above one requires a positive repeat gap. Expanded
events must fit both actual CAPS and the 512-event profile ceiling; 512 repeats
is a count bound, not a promise that every message can repeat that many times.
The worst supported single 32-character message uses 384 events including its
tail. The raw job-file path separately permits at most 30,000 file bytes and
checks actual event/duration CAPS; arbitrary raw jobs have no inferred text limit.

Message compilation errors return HTTP 400. Duration and event errors include
`calculated_duration_ns`, `max_job_duration_ns`, `calculated_events` and
`max_events`, allowing the interface to explain the actual exceeded bound.
Memory admission can return HTTP 503 without loading or arming a job.

The browser calculates duration before submission. For a job it armed in this
session, it refreshes status every five seconds while connected and shows
estimated elapsed progress from device UTC. Only authoritative job status
establishes completion: reaching 100% does not override Running, an unavailable
connection leaves output unknown, and a different boot/job clears old progress.
Timer throttling or closing the page cannot change the Pico's local job timing.
These source behavior contracts establish no physical timing, broader
mode/band/clock or release qualification.

## Bounds and errors

HTTP/1.1 accepts GET/PUT/POST, at most 2,048 header bytes and 32,768 body bytes.
Non-GET requests need Content-Length. Duplicate headers, bare LF, folded headers,
ambiguous lengths, Transfer-Encoding, Expect, Upgrade, encoded/query paths and
pipelined bytes in a received request are rejected. Each connection carries one
HTTP request and response and is then closed; later requests require a new
connection. A complete request can be dispatched before future trailing bytes
arrive, but trailing bytes can never dispatch a second request.

Two TLS sessions may be active, with at most one authenticated WTP stream. This
leaves a slot for an independent HTTPS browser while a WTP controller retains
its connection. Without WTP, two HTTPS requests may compete. One additional TCP
connection may wait; at most one TLS handshake computes at a time. Further TCP
connections and a second WTP stream are rejected without evicting the owner.
Connections progress in rotating order. Pending/handshake deadlines are 10 seconds,
total HTTP deadline is 15 seconds from activation, and an authenticated WTP
connection has a 30-second progress deadline in addition to 5-second WTP
framing/write stall limits. HTTP remains one request per connection.

Capabilities add `max_wtp_connections:1`, `max_pending_connections:1` and
`max_handshakes:1`; `max_network_connections` is now 2. Status adds `transport`
with current/peak admission, timeout and TLS allocation/latency diagnostics.
64-bit durations remain decimal strings. These are observations, not measured
RP2350 timing guarantees. The full WTP 65,536-byte payload and separate HTTP
32,768-byte body limits remain. Shared-heap admission can reject a request or
connection under pressure before its individual maximum: body/frame bounds are
not promises that every simultaneous maximum allocation will fit.

Transport/API errors use `{"error":{"code":"..."}}`. Important HTTP statuses:
400 malformed/schema failure; 401 missing transport principal (defensive adapter
gate); 403 host/origin/context rejection; 404 unsupported route; 409 busy or job
service rejection; 412 stale revision; 413 oversized adapter body; 428 missing
revision; 503 storage/network unavailability. Framing errors produce 400 when a
response is possible; TLS authentication failures produce no application response.

`active_job_connections` is now an explicit application policy. The maintained
application images set it true: normal and compatibility RF images isolate
waveform servicing on core 1; the explicit inhibited image simulates execution.
The browser continues
status refresh and owner-authorized abort after ARM. Configuration, persistent
schedules and disruptive Wi-Fi changes remain idle-only. A different certificate
or WTP session cannot adopt or abort the controller's job. The current mTLS UI
creates a new WTP session on page refresh, even with the same client certificate.
The selected SoftAP adapter may reauthenticate the same principal with its live
cookie, including restricted owner-only grace for STATUS, ABORT and same-
principal controller-time refresh, but owner resume still requires the original
WTP session.

A failed read makes state/output/clock/owner/network unknown and disables controls;
unsaved drafts remain. Capacity exhaustion may require retrying a read. No LOAD
or ARM is automatically retried after an ambiguous outcome. Unsupported adapters
leave `active_job_connections:false` and retain the existing pause/recovery UI.
Resource admission and physical timing/RF qualification remain separate.

## Discovery status

`network` adds `station_mac`, `stable_hostname`, `configured_hostname`, `advertised_hostname`,
`deployment_identity_matches`, `mdns_state` and `mdns_reason`. Advertisement is
empty until active. `station_mac` is the station address read by the device
after Wi-Fi initialization; `stable_hostname` uses its last six hex digits. Both
are empty before a valid read and do not change the certified deployment name.
States are `unconfigured`, `waiting_address`, `probing`,
`active`, `withdrawing`, `conflict` and `failed`. Reasons distinguish name conflict, initialization,
registration, probe timeout and wrong-board deployment failures. Bounded counters
report registrations, conflicts, failures, address changes, goodbye attempts/
failures and rejected packets. A sent goodbye is not proof of peer receipt.
Discovery failures neither alter WTP identity/ownership nor report inactive RF.

## Network memory and time lookup diagnostics

`network.memory` reports lwIP's dedicated heap (bytes), TCP PCB/segment and packet
pools (objects): `used`, `capacity`, `peak` and cumulative allocation `errors`.
An uninitialized pool is null. These supplement general heap and TLS allocator
measurements; a peak or occupied live connection is not by itself a leak.
USB INFO exposes the same network counters plus current TLS allocation/failures.

`ntp_server`, `ntp_address`, `ntp_resolution` and `ntp_resolution_failures` describe
the configured/canonical name, selected IPv4 peer, lookup state and failed
lookups. They do not certify clock synchronization; use the clock state and age.
`power_save` reports read-back radio sleep mode (null if unavailable), and
`packets` reports ARP/IPv4/TCP/UDP received, sent and dropped counters. Counters
show lwIP activity; they do not prove that an access point forwarded a frame.

## Pin allocation extension

The [pin allocation guide](development/pin-allocation.md) defines authenticated
GET `/api/v1/pins`, nonmutating POST `/api/v1/pins/validate`, and the optional
`pins` member of Config v1. Operational pin changes require restart and inhibit
new RF admissions until then. Read saved versus active plans separately.

## Management-carrier discovery

Capabilities add a top-level `management_carriers` reference with
`path:"/api/v1/management"` and schema `transmitter-management/2` on network
carriers or `transmitter-management/3` on USB. This is
outside the closed `application_resources` and application capability objects;
their legacy `authenticated_https` value is retained on network projections
for strict legacy compatibility. USB-selected views instead identify `usb_physical`.
The selected authenticated carrier serves the discovery document. Public
consumer identity/discovery cannot authorize reads or writes. Unsupported
versions/types, unavailable selected carriers and identity/profile-generation
mismatches must refuse without another-carrier retry. The full wire shape,
operation list, profile matrix and budget interpretation are in the
[carrier contract](development/management-carriers.md), with the
explicit [version-2 session contract](development/consumer-sessions.md).
Version 2 preserves the closed shape and all version-1 limits except integer
`consumer_sessions:3`, adding integer `consumer_pending_logins:1` to limits.
Updated Pi accepts each version's exact limits; old Pi refuses version 2.
No fallback, downgraded authentication or mutation retry is added.

USB version 3 adds the fifth `usb_physical` carrier row, selects it and removes
`usb_json` from `unsupported`. Network version 2 deliberately retains its four
rows and legacy `usb_json` exclusion; it is a projection, not a global statement
that current firmware lacks USB management. Version 1 remains the legacy
one-session shape. The common `operations` subset is not an exhaustive route
allowlist: station, hardware, hostname, progress, drive, jobs and USB-specific
resources retain their independent descriptors/contracts.

The accepted [USB projection](development/usb-local-configuration.md)
keeps application schema names but substitutes `usb_physical` for the embedded
`management_carrier` and removes `usb_json_management` from its unavailable
list. The unchanged application/1, /2 and /3 schema files still encode the
network `authenticated_https` capability definitions; those definitions do not
validate USB application readbacks unchanged. USB projection validation follows
its explicit contract and [local-management tests](../tests/usb_local_management_tests.cpp).
This accepted carrier extension does not relax network schemas or authorize
unknown future shapes. No schema artifact is changed by this reconciliation.


## Login retirement and uncertain saves

[Consumer-Recovery/1](protocol/Consumer-Recovery-v1.md) is a separate public
recovery discovery/proof surface, available before ordinary login. It does not
change either frozen management discovery shape. Three ordinary slots and one
pending ordinary login remain; one five-second password-proof workspace can
retire a deliberately selected login even at full capacity. Public selectors
are one-way aliases and authorize nothing. Saved Wi-Fi password membership
cannot identify an old tab's owner. Another operator's selected login may end.

Ordinary API rejection retains healthy authentication. An uncertain encrypted
exchange clears traffic keys; no application mutation is repeated. Preserve the
draft, disable saving, authenticate/recover and read fresh saved configuration
and application resources consistently. Display saved versus draft and
saved/active/null/fault state. Explicit review adopts fresh revisions for a new
operator save; matching values do not attribute a past uncertain write.
Commissioning retains its separate sent-once device/generation/request-digest
receipt across authentication and origin changes. Failed terminal attempts can
be corrected explicitly; active trials and unresolved/committed restarts remain
blocked. See the [execution evidence](development/session-recovery.md).


## Versioned local WSPR planning

The additive `capabilities.application_resources_v2` descriptor advertises
`transmitter-application/2` at `GET /api/v1/application/2`, station version 2 at
`GET/PUT /api/v1/station/2`, Config v1 content at `PUT /api/v1/config/2`, and the
unchanged `transmitter-config-update/1` envelope at `POST /api/v1/config/update/2`.
These explicit admission routes permit Type 1/2/3 station changes. Their existing
authentication, target, ETag, idle/unowned, body bounds, preservation and journal
rules apply. Consumer profile identity remains owned by transactional setup.
The version-2 [closed schema](protocol/transmitter-application-2.schema.json)
adds the `wspr_type123_auto` capability and an observed `wspr-plan/1` projection.

Frozen version-1 application/station resources retain Type 1 management. A saved
Type 2/3 plan returns explicit `unsupported_station_encoding` from those legacy
reads. Legacy config writes cannot introduce a changed Type 2/3 identity; an
unchanged stored identity can be preserved while unrelated settings change.
New clients must strictly discover version 2; absent support preserves old
Type 1 workflows, while unknown advertised versions refuse. WTP/1, management/1
and /2, Consumer-Radio/1 and Consumer-Recovery/1 are unchanged.

Authenticated `POST /api/v1/wspr-plan` accepts exactly `callsign`, `locator`,
`power_dbm` within 1,024 bytes. It returns supported/refused planning, ordered
frame types/count, fixed 120-second slot separation, rationale, Type 2 ambiguity
and alternate full identity. It never claims, reserves, saves, changes GPIO or
starts a transmission. Invalid station syntax/types/power return `invalid_station`.
Supported storage syntax that cannot be encoded returns `supported:false`.
The setup page discovers the independent, side-effect-free `wspr-support/1`
record at `GET /api/owner/v1/wspr-support`, under the existing AP-local public
GET policy or authenticated consumer setup wrapper. Commissioning validates
actual encoding before any profile trial/commit; wire/storage decoding remains
broad enough to read legacy identities.

A reported power is message content, not an RF drive setting. Type 1 retains a
saved six-character locator but sends four. Type 2 omits the locator. Type 3
carries the exact inner identity hash and six locator characters; receiver
context/collisions remain limitations. Type 2 `/Q`–`/Z` and `/00`–`/09` expose
both interpretations without replacing the saved call. A two-frame local plan
uses separately armed finite jobs; see [standalone behavior](development/standalone.md).

## Independent saved progress

The additive `transmitter-progress/1` resource persists valid independent fields
without applying configuration or establishing transmit readiness. See the
[saved progress contract](development/saved-progress.md) for field, storage, authority,
explicit application and recovery semantics. Existing complete configuration,
profile and WTP contracts remain atomic and do not consume drafts.

## GPIO-drive discovery and bounds

The top-level `capabilities.gpio_drive` descriptor negotiates
`transmitter-gpio-drive/1`, legal values `[2,4,8,12]`, explicit default 4 mA,
restart activation and all extended routes in the inventory. It selects
config/3, config-update/2 on update/3, hardware/2, application/3 and progress/2.
The existing `application_resources`, `application_resources_v2`,
`configuration_updates` and `saved_progress` descriptors retain their closed
legacy shapes. The embedded application capabilities retain their old
unavailable `drive` entry; the independent descriptor governs current drive
support. Absence of that descriptor means no observed drive support/default.
See [GPIO drive](development/gpio-drive.md) for saved, boot selection, nullable
ARM-time cached pad verification, restart latches and downgrade limitations.

Scoped station/hardware/drive writes and WSPR preview are bounded to 1,024
bytes; hostname to 512; Config input/candidate content to 1,800; config-update and
progress-update to 2,048; progress-apply to 512. Application resource validation
uses a 4,096-byte response budget. All byte bounds include whitespace and retain
the separate transport/memory limits above. Legacy config routes reject an
explicit drive member while preserving an omitted saved drive. Only deliberate
replacement resets omitted drive to 4; complete atomic saves and independent
valid-field progress saves have distinct rejection rules.

Source authority: [BrowserApi dispatch and revisions](../src/network/api.cpp),
[descriptors](../src/application/resources.cpp),
[merge/replacement](../src/application/config_update.cpp),
[carrier projection](../src/network/management.cpp) and
[field allowlist](../src/network/softap_api.cpp). Existing
[resource tests](../tests/application_resource_tests.cpp),
[WSPR tests](../tests/wspr_resource_tests.cpp),
[drive tests](../tests/gpio_drive_tests.cpp) and the linked acceptance records
bound these descriptions; no runtime or version change is made here.
