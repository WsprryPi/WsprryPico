# Consumer-Radio/1

Current implementation: consumer LAN and AP listeners, with server-side
interface/authority session binding and additive authenticated commissioning
routes. See [consumer access](../development/consumer-lan-access.md) for the
selected lifecycle and current acceptance status. The wire handshake,
cryptographic transcript, packet header and fixed vectors below are unchanged.

Engineering mTLS and Plain LAN WTP retain their
existing contracts. This transport supplies the missing authenticated consumer
radio page and shared Browser API; it does not retain the withdrawn browser
owner keys or change the immediate commissioning transaction.

A healthy source-4 Wi-Fi-only or source-5 consumer profile normally keeps its AP off. No station claim or synchronized UTC is required for browser access or authentication. Open
`http://<current-station-IPv4>/` or `http://<configured-local-hostname>/` on
infrastructure Wi-Fi, or `/radio` on either admitted interface. Log in with
the Pico password. Its default is the Wi-Fi passphrase saved in the selected profile; an independently saved Pico password takes precedence. AP access is temporary
button-requested or automatic unavailable-network fallback. AP association
alone grants no private radio read or mutation. The station listener exposes
only the public radio document/identity and encrypted consumer routes.
Wi-Fi and station identity remain owned by their transactional setup adapters; the
radio configuration API presents their effective values and rejects changes
that the profile would override at restart. Schedules, pins and frequency
opt-ins use the existing configuration journal and admission engine.

Radio management retains LAN access during loaded, armed and running jobs.
Operation-specific BUSY and ownership checks remain authoritative. The AP radio
surface permits unarmed ownership and loaded plans while requested by its lease
or fallback lifecycle.
Commissioning keeps its stricter unowned-only guard. Unknown/active output,
armed, running and failed states withdraw this AP path under the retained RF
connection policy; job execution stays local. Current source-5 consumer and
engineering profiles admit reference USB WTP under local physical authority,
alongside Console and the separately framed
[USB management/time adapter](USB-Management.md). USB management,
Plain LAN WTP and Consumer-Radio keep distinct authority; all job paths share
one JobService and RP2350 execution owner.

The HTTP page-delivery threat boundary remains on AP and LAN: HTTP does not authenticate
the page before password entry. A substituted malicious page can steal entered
credentials. This adapter protects traffic between the genuine page and Pico
against passive observation and rejects peers without the saved passphrase;
it is not a PAKE or a replacement for authenticating the delivered page.
Nothing is retained in browser storage. Private credentials and keys remain
in RAM for the bounded exchange and are never returned by identity/config reads.

## Handshake

All routes use an explicitly interface-classified port-80 listener. Public GET
`/api/consumer/v1/identity` returns version `1`, device/boot lowercase 32-hex IDs,
profile generation as a canonical nonzero decimal string, and authentication
`saved_wifi_passphrase` for the default, or `pico_password` for a separate Pico password. Station Host must be its current IPv4 or exact configured
local hostname; AP Host must be `192.168.4.1`. An explicit `:80` Host is accepted.
Other ports, malformed authorities and wildcard/suffix matches are rejected.
POSTs require Origin `http://<admitted-host-without-default-port>`,
`X-WsprryPico-Radio: 1`, no Cookie, and absent or same-origin
Fetch Metadata. There is no CORS permission or redirect follow.
The server records the actual interface and Host at successful start. Finish
and request must match that context. This is server-side session binding;
it does not add origin bytes to the unchanged cryptographic transcript.

Public GET `/api/consumer/v1/status` returns the closed `transmitter-public-status/1` projection: `schema`, lowercase 32-hex `device_id` and `boot_id`, WTP `state`, Boolean `output_active` and `owned`, `clock_state`, decimal-string `utc_now_ns` (null when unsynchronized), decimal-string `uncertainty_ns`, and `engine`. It follows the same listener, Host, Origin and resource-admission rules as public identity. It does not create or renew a login, claim ownership or alter a job. It exposes no owner ID, job ID, message, settings, credentials or history. This historical projection remains unchanged. Detailed public observations use the independent discovery below; mutations still require authenticated encrypted requests.

### Independent public settings discovery

GET `/api/consumer/v1/read` returns the closed [`pico-public-read/1` descriptor](pico-public-read-1.schema.json): exactly `schema`, `target`, `prefix` and `resources`. Target is exactly `{scope:"member",device_id,boot_id}` with the current device and boot. Prefix is exactly `/api/consumer/v1/read/`; resources is the exact ordered list in that schema, not a pattern or extensible route prefix. The browser validates the complete shape, version, list and target against its fresh identity before reading any resource. Missing, extra, duplicate, unknown or reordered resources and wrong device/boot bindings refuse discovery; no guessed authenticated or older public fallback is selected.

GET of an allowlisted suffix returns the existing resource's redacted read body and ETag, preserving its independently versioned shape and supported-view refusals. This includes current operations, station, config/progress, hardware, frequency, calibration, timeout, hostname, USB/UDP logging and saved CW schedule observations. The Pico-password resource exposes only default/custom status; setup public status exposes redacted saved network context. Passwords, keys, certificate material and raw configuration bodies containing secrets are excluded. Accepted message text, job and owner IDs, frequencies, schedules, SSID, time server, logging destinations and device metadata are deliberately public observations. An inner `writable` flag describes the underlying resource, not public mutation authority.

This adapter fixes the method to GET and forwards no caller body, principal, revision or other headers to its internal read handler. Nonempty GET bodies are refused. Non-GET methods and every suffix outside the fixed list are refused before mutation; HTTP parser refusals remain independently authoritative. Jobs, restart, validators, updates, progress application and test-event submission are absent. It retains consumer listener/interface, exact Host, same-origin Origin/fetch metadata and bounded resource-admission checks. It creates or renews no login, claims no transmitter ownership, changes no saved revision and invokes no RF operation. No CORS access is granted. Discovery/read observations authenticate neither the page nor the claimed device.

The operator page uses these reads while signed out and the existing encrypted reads after login. Saved values populate disabled, dimmed controls; passwords stay empty. Five-second public status polling retains unknown/stale handling and does not renew idle time. Writes are rejected by both the browser access gate and the server's independent authenticated resources. Locking or losing a session preserves drafts and requires readback/review for an uncertain save. Consumer-Radio/1 framing/crypto, historical public status, management descriptors and both carrier policies are unchanged.


Public NTP timeout v2 uses the separate closed [pico-public-read/3 descriptor](pico-public-read-3.schema.json), discovered at `/api/consumer/v1/read/3`, with prefix `/api/consumer/v1/read/3/` and exactly one resource: `ntp-timeout/2`. Its read document follows [transmitter-ntp-timeout/2](transmitter-ntp-timeout-2.schema.json). The historical /1 resource list and amplifier-only /2 descriptor remain unchanged. Unknown versions, extra resources, incorrect target/boot bindings and mutations are refused; the client has no downgrade fallback.

POST `/api/consumer/v1/start`, JSON, exactly:
`version`, `device_id`, `boot_id`, `generation`, `public_key`, `nonce`.
The browser supplies an ephemeral X25519 public key (canonical unpadded
base64url, 32 decoded bytes) and random nonce (16 bytes, lowercase hex).
The Pico verifies current identity/generation, creates an ephemeral X25519 key,
random session and challenge, and returns those bindings plus `login_ms:30000`.
Three independent sessions may coexist, including clients at the same station
origin. At most one is pending, reserving one of those three slots. Successful
starts are spaced at least one second apart; a pending slot expires after 30
seconds. Capacity returns `409 radio_session_capacity`, pending-login quota
`409 radio_login_pending`, and rate limiting `429 radio_login_rate_limited`.
These refusals neither evict a client nor authorize a retry of a mutation.
An abandoned client can occupy a slot until its own idle/absolute expiry.
Session IDs include a nonreused boot-local serial and random bytes; ID lookup
alone grants no authority. RNG failure and serial exhaustion fail closed.
[Management/2](../development/consumer-sessions.md) advertises these bounds;
management/1 remains frozen for historical one-session firmware.

Transcript bytes, in order:

1. UTF-8 `WsprryPico/Consumer-Radio/1` followed by NUL.
2. Device, boot and session IDs, each 16 decoded bytes.
3. Profile generation, unsigned 64-bit big endian.
4. Browser then Pico public keys, each 32 bytes.
5. Challenge then browser nonce, each 16 bytes.

Let `T=SHA256(transcript)` and
`IKM=X25519(shared secret) || SHA256(Pico password ASCII bytes)`.
Reject an invalid/all-zero shared secret. HKDF-SHA256 uses salt `T` and info
`WsprryPico radio login v1` for the 32-byte login key. A separate HKDF with info
`WsprryPico radio traffic v1` produces 64 bytes: browser-request key first,
Pico-response key second. The three keys have distinct roles.

Binary packets have a 28-byte header: ASCII `CR01`, session ID (16 bytes),
sequence (unsigned 64-bit big endian). ChaCha20-Poly1305 uses nonce
`00000000 || sequence`, AAD `T || header`, then ciphertext and a 16-byte tag.
POST `/api/consumer/v1/finish` uses sequence zero and encrypts the 32-byte `T`
with the login key. A complete login attempt consumes the ephemeral Pico key,
including failures. A successful encrypted response, using the response key
and sequence zero, contains `authenticated:true`, exact device and boot IDs.
The saved passphrase is never sent as a plaintext or encrypted login payload.

## Shared API requests and delivery

POST `/api/consumer/v1/request` uses the request key and consecutive sequences
starting at one. Authenticated plaintext is exactly the JSON object
`{method,path,if_match,body}`. Methods are GET/POST/PUT. Path is an existing
`/api/v1/` route; GET body is null, other bodies are objects. `if_match` is null
or the existing quoted revision string. The adapter supplies the authenticated
principal and invokes the same BrowserApi/JobService, preserving revision,
ownership, idle, time, frequency, event, duration and RF safety checks.

The encrypted response uses the response key and same sequence, and contains
`{status,etag,body}` with the actual shared API JSON result. Binary body limit
is 32,768 bytes, leaving 32,724 bytes for plaintext. Input pages are decrypted
in place only with exclusive ownership; no application parse occurs until the
entire tag verifies. Response envelopes and ciphertext use bounded pages.

POST logical `/api/v1/consumer/logout`, body `{}`, closes the volatile session after constructing its encrypted acknowledgement. It does not abort or release a job. Sessions expire after thirty idle minutes or eight total hours and close on profile generation changes, reboot, admission loss or invalid tags. Logout, expiry, invalid tags and sequence exhaustion affect only the addressed session; every session has its own keys, context, timers and exact sequence. Ordinary configuration journal revisions do not expire other logins. Idle time renews only after an authenticated request; public reads, page visibility and form editing do not renew it. The absolute deadline starts at successful authentication and never renews. Management discovery /4 (network) and /5 (USB) advertise `idle_ms:1800000` and `absolute_ms:28800000`; historical /1, /2 and /3 retain five-minute idle and fifteen-minute absolute limits. Consumer-Radio/1 handshake bytes and cryptographic vectors are unchanged. No automatic mutation retry occurs. On a lost response the page clears its keys, preserves edits, and blocks saves until authentication, authoritative saved-state readback and explicit review establish a fresh revision. Status or login alone cannot unlock saving. [Consumer-Recovery/1](Consumer-Recovery-v1.md) adds a separately versioned, password-authenticated retirement proof usable at full ordinary capacity. It lists one-way retirement aliases, never raw traffic IDs, and requires explicit target selection. It creates no replacement session and replays no application request. Deferred restart/network-disable actions execute only after the complete reply has been acknowledged on the matching transport transaction. A lost/partial reply or session expiry cancels only that transaction's still-pending deferred action. A normally acknowledged HTTP connection close leaves the login usable. Already committed settings or accepted WTP operations can remain effective after a lost reply.

DHCP/link/hostname changes close station sessions and cancel pending deferred
actions. AP withdrawal closes AP sessions without closing a healthy LAN session.
An AP session cannot move to LAN or between IP/hostname authorities; log in
again at the intended origin. Session closure never releases or aborts a job.

## Authenticated commissioning routes

The additive logical `/api/v1/consumer/setup/` prefix reuses the same envelope,
sequence, authentication and response rules. The suffix is an existing setup
path, for example `/api/v1/consumer/setup/api/bootstrap/v1/start`. Only these
method/path pairs are forwarded after the complete outer AEAD authenticates:

- GET `/api/bootstrap/v1/status`, `/api/owner/v1/public-status`,
  `/api/owner/v1/claim/status`, `/api/owner/v1/wspr-support`.
- POST `/api/bootstrap/v1/start`, `/api/bootstrap/v1/submit`,
  `/api/bootstrap/v1/ack`, `/api/owner/v1/claim/start`,
  `/api/owner/v1/claim/submit`, `/api/owner/v1/claim/progress/start`.

Their existing bodies, trials, exact-generation/request-digest reconciliation,
journals, UTC requirements and safe-commit gates remain authoritative. The
trusted adapter supplies the legacy inner AP authority and setup request
headers; that inner authority is not a plaintext LAN admission mechanism.
Recovery/reset and arbitrary HTTP routes are not forwarded. The corresponding
public plaintext setup routes remain AP-only.
While a setup slot or its activation/restart is pending, ordinary radio
mutations return `409 setup_pending`; reads and logout remain available.
Competing Plain LAN WTP admission and new scheduled launches pause until
the explicit setup completes or expires. No accepted job is interrupted:
starting setup requires idle, unowned authority.

A network or station trial begins only after the matching encrypted submit
reply is completely acknowledged. A lost reply cancels the pending trial;
neither an unrelated transaction nor a delayed old acknowledgement may start
it. A profile commit invalidates old-generation radio sessions. After restart,
authenticate again and compare the durable generation/request digest; do not
replay the old submit. A station-only change reuses a healthy saved association.
The UI may carry a bounded, nonsecret receipt in a continuation URL fragment:
change kind, device ID, expected generation and request digest only. It carries
no credentials, keys or mutation payload. On a new origin it authorizes no
operation; the user authenticates again and performs a read-only result check.
The restored receipt cannot be submitted as a mutation.

The [fixed vectors](Consumer-Radio-v1-vectors.json) use synthetic credentials
and compare Noble browser output with the pinned Mbed TLS implementation,
including a maximum-size paged request. Host/vector checks are not target/RF
qualification. Physical peer/board behavior and release qualification are independent of
source/vector conformance.

An active fake endpoint can choose its own X25519 key, obtain the client's
password-derived finish proof and test password guesses offline against its
known shared secret/transcript. Passive capture alone does not provide that
shared secret. This existing protocol limitation remains; a strong passphrase
and trusted endpoint/network matter. Native local code prevents device-page
execution but does not authenticate a unique device before emitting that proof.

## Pico password settings

Inside an authenticated Consumer-Radio envelope, `GET /api/v1/consumer/password` returns schema `pico-password/1`, the member target `{scope, device_id, boot_id}`, Boolean `wifi_default`, and `saved:true`, with an ETag. It returns no password or verifier. The independent public read surface exposes this same redacted GET only. The ordinary API, public setup interface, engineering transport and Plain LAN WTP do not expose its mutation route.

`PUT` on the same logical route requires `If-Match` from that read and exactly `{schema, target, password}`. The schema and exact member device/boot must match. A password is 8–63 printable ASCII characters; JSON null explicitly selects the saved Wi-Fi default and is refused when no Wi-Fi password exists. The caller must be authenticated, the transmitter idle and unowned, and no setup/configuration mutation may be pending. There is no implicit retry. Responses use `428 revision_required`, `412 revision_conflict`, `400 invalid_password`, `409 busy`, `409 setup_pending`, `409 wifi_password_unavailable` or `503 password_save_unconfirmed` as applicable.

The access journal stores the separate Pico password independently of network and station profiles. Its legacy version-2 payload remains valid; version 3 adds a length-prefixed password at byte 160, with at most 63 following bytes and zero padding. Journal framing, slots, commit/readback and fault behavior are unchanged. Creating this record for browser settings keeps BLE disabled and field mode off. Other access-journal writes preserve the separate Pico password; browser logins are invalidated only when that password changes, not when unrelated access metadata changes.

The Pico verifies the journal save and seals the response before retiring all browser sessions and pending recovery proofs, including the initiating session. A lost response does not undo a committed password change. The operator signs in with the new password, or tries the previous password if the new one is refused, then reads the setting before another explicit save. Wi-Fi, station, schedule, watermark and job ownership are unchanged. Restart preserves the password; access/provisioning/full-settings resets clear it. Wi-Fi updates preserve an explicit Pico password, while default-mode login follows the newly saved Wi-Fi passphrase.
