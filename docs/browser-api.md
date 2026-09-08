# Shared browser-facing JSON API v1

Status: implemented by WsprryPico; Linux adoption remains independent work.
The version is selected by `/api/v1/`, independently of firmware and WTP/1.
The browser, USB WTP, TCP WTP and standalone scheduler use one JobService.

## Transport and trust

The Pico serves HTTPS and WTP on an explicitly configured TLS port. TLS 1.3,
client certificate verification and ALPN are mandatory: `http/1.1` selects this
API; `wtp/1` selects the unchanged WTP frame stream. There is no plaintext
listener, TLS downgrade, anonymous access, CORS, session ticket or early-data
path. The authenticated principal is the SHA-256 fingerprint of the leaf client
certificate. Device-specific credential setup and renewal are described in
[network control](development/network-control.md).

The authority is the current IPv4 address and configured port (omit `:443` for
port 443). `Host` must match exactly, rejecting DNS rebinding aliases. Browser
mutations require all of:

- `Origin: https://<authority>`;
- `Content-Type: application/json`;
- `X-WsprryPico-Request: 1`;
- a non-cross-site Fetch Metadata context when that header is supplied.

Responses use `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, a
restrictive CSP with hashes for embedded styles/scripts, and no referrer. API
keys, passwords and certificates do not belong in URLs. The UI neither stores
credentials in browser storage nor prints Wi-Fi passwords.

## Resources

| Method and path | Behavior |
|---|---|
| GET `/api/v1/capabilities` | `api_version`, WTP service capabilities under `wtp`, implemented management `features`, body/connection limits, `active_job_connections` |
| GET `/api/v1/status` | `job` service status/terminal records, `standalone` config/clock health, `network` state |
| GET `/api/v1/jobs` | Same current/retained job inspection snapshot as status |
| POST `/api/v1/jobs` | Explicit HELLO, CLAIM, RENEW, LOAD, ARM, ABORT or RELEASE through the common service |
| POST `/api/v1/jobs/{id}/abort` | ABORT only; URL ID must match the request body's job ID |
| GET `/api/v1/config` | `{"config": <redacted config or null>}` and ETag |
| PUT `/api/v1/config` | Replace the validated standalone config; requires If-Match; persists and reports `reboot_required:true` |
| GET `/api/v1/schedules` | `{"schedules":[...]}` and ETag |
| PUT `/api/v1/schedules` | Replace only schedules using the same config validator/journal; requires If-Match |
| GET `/api/v1/network` | Initialized/enabled/link/IP, requested enable state, control availability and SNTP counters; ETag |
| PUT `/api/v1/network` | `{"enabled":true|false}`; idle-only volatile change with If-Match |

Static `/`, `/style.css` and `/app.js` require the same authenticated transport.
The document embeds styles and scripts so a browser does not need concurrent
asset connections. The individual asset paths remain available to tooling.

## Configuration and revisions

The configuration schema is the existing [standalone version-1 schema](development/standalone.md).
Passwords are returned as JSON null. A null password in PUT preserves the stored
password; it is rejected when no stored config exists. Supplying a new password
replaces it after full validation. Successful and failed responses never echo it.
The existing station, recurrence, overlap, expiry and storage rules remain in
force, including the fixed standalone WSPR frequency of 3,570,100 Hz. Broader
mode/band configuration remains outside this phase.

ETags are quoted opaque hashes of boot identity, persisted config and successful
network-change revision. Send the exact ETag in `If-Match` for any configuration,
schedule or network PUT. Missing revisions return 428; stale revisions return
412. Console config changes and reboot invalidate relevant saved revisions.
A byte-identical config has the same revision; persistence still returns an
explicit reboot requirement. Failed storage never reports a successful save.
Changes require no owner, no armed/running/output state, and no latched fault.

A network enable/disable request is queued until its HTTP response is acknowledged
or the connection terminates. It is applied only if the service is still idle;
a newly acquired owner cancels the queued change. `requested_enabled` describes
the pending request, while `enabled` describes actual state. This is deliberately
not a persistent Wi-Fi switch. Disabling Wi-Fi requires USB Console `WIFI ON` or
a restart to reconnect. SSID/password/time-server changes use config PUT and
require a restart, preserving the established recovery behavior.

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
locally after a connection closes. A refreshed browser gets a new session and
cannot silently take over the previous session's job.

Nanosecond timestamps, durations, frequencies in nanohertz and other WTP 64-bit
quantities remain decimal strings. JavaScript must use BigInt for exact arithmetic.
Configuration seconds are bounded below 2100 and are safe JSON integers.

## Bounds and errors

HTTP/1.1 accepts GET/PUT/POST, at most 2,048 header bytes and 32,768 body bytes.
Non-GET requests need Content-Length. Duplicate headers, bare LF, folded headers,
ambiguous lengths, Transfer-Encoding, Expect, Upgrade, encoded/query paths and
pipelined bytes in a received request are rejected. Each connection carries one
HTTP request and response and is then closed; later requests require a new
connection. A complete request can be dispatched before future trailing bytes
arrive, but trailing bytes can never dispatch a second request.

One TLS session is active at a time; one TCP connection may wait up to 10 seconds
for handoff. Additional connections are rejected. TLS handshake deadline is 10
seconds, total HTTP deadline is 15 seconds from activation, and an authenticated
WTP connection has a 30-second idle deadline in addition to WTP framing/write
stall limits. WTP still accepts its normative 65,536-byte payload limit; the
smaller browser limit is advertised separately.

Transport/API errors use `{"error":{"code":"..."}}`. Important HTTP statuses:
400 malformed/schema failure; 401 missing transport principal (defensive adapter
gate); 403 host/origin/context rejection; 404 unsupported route; 409 busy or job
service rejection; 412 stale revision; 413 oversized adapter body; 428 missing
revision; 503 storage/network unavailability. Framing errors produce 400 when a
response is possible; TLS authentication failures produce no application response.

For physical RF images, new TLS handshakes are refused while armed/running;
`active_job_connections:false` advertises this restriction. A pre-established WTP
connection can continue servicing its owning controller. Browser ARM therefore
pauses subsequent browser management until terminal state. Physical USB Console
`ABORT` is the local recovery control. Inhibited images allow new connections
through simulated jobs. Live TLS/RF latency and heap behavior remain unqualified.
