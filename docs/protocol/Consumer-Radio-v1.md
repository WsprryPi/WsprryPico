# Consumer-Radio/1

Current implementation: consumer LAN and AP listeners, with server-side
interface/authority session binding and additive authenticated commissioning
routes. See [consumer access](../development/consumer-lan-access.md) for the
selected lifecycle and current acceptance status. The wire handshake,
cryptographic transcript, packet header and fixed vectors below are unchanged.

Historical Phase 14 evidence: bounded two-Pico settings validation accepted,
2026-10-14. The earlier
encrypted page/read API path passed at `consumer-radio-260445e0582b`.
The uncommitted `consumer-radio-18997499747b` snapshot also passed authenticated
settings changes, unarmed ownership/admission, reboot persistence and original
configuration restoration. The independent review binds 86 complete responses
and full native flash equality after restoration, with both current cursors
preserved. The later consumer-radio-c96eeeeb4871 snapshot passed both Picos'
authenticated page/read API checks and corrected Plain LAN admission during
independent TLS activity. All four final smoke screens are independently
accepted: three retain their actual R189 image identity, and B WSPR uses C96.
Narrow source applicability binds the unchanged RF/runtime implementation.
The later [Phase 14 closeout](../development/phase14-closeout-ledger.md)
completed durable retention and final audits within its recorded scope.
Engineering mTLS and Plain LAN WTP retain their
existing contracts. This transport supplies the missing authenticated consumer
radio page and shared Browser API; it does not retain the withdrawn browser
owner keys or change the immediate commissioning transaction.

A healthy source-5 consumer profile normally keeps its AP off. Open
`http://<current-station-IPv4>/` or `http://<configured-local-hostname>/` on
infrastructure Wi-Fi, or `/radio` on either admitted interface. Log in with
the Wi-Fi passphrase saved in the consumer profile. AP access is temporary
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
[USB management/time adapter](USB-Management.md). The earlier consumer USB-WTP
exclusion belonged to the historical Phase 14 image, superseded by
[production USB control](../development/usb-control-results.md). USB management,
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
`saved_wifi_passphrase`. Station Host must be its current IPv4 or exact configured
local hostname; AP Host must be `192.168.4.1`. An explicit `:80` Host is accepted.
Other ports, malformed authorities and wildcard/suffix matches are rejected.
POSTs require Origin `http://<admitted-host-without-default-port>`,
`X-WsprryPico-Radio: 1`, no Cookie, and absent or same-origin
Fetch Metadata. There is no CORS permission or redirect follow.
The server records the actual interface and Host at successful start. Finish
and request must match that context. This is server-side session binding;
it does not add origin bytes to the unchanged cryptographic transcript.

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
[Management/2](../development/phase15-6-sessions.md) advertises these bounds;
management/1 remains frozen for historical one-session firmware.

Transcript bytes, in order:

1. UTF-8 `WsprryPico/Consumer-Radio/1` followed by NUL.
2. Device, boot and session IDs, each 16 decoded bytes.
3. Profile generation, unsigned 64-bit big endian.
4. Browser then Pico public keys, each 32 bytes.
5. Challenge then browser nonce, each 16 bytes.

Let `T=SHA256(transcript)` and
`IKM=X25519(shared secret) || SHA256(saved passphrase ASCII bytes)`.
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

POST logical `/api/v1/consumer/logout`, body `{}`, closes the volatile session
after constructing its encrypted acknowledgement. It does not abort or release
a job. Sessions expire after five idle minutes or fifteen total minutes and
close on profile generation changes, reboot, admission loss or invalid tags.
Logout, expiry, invalid tags and sequence exhaustion affect only the addressed
session; every session has its own keys, context, timers and exact sequence.
Ordinary configuration journal revisions do not expire other logins.
No automatic mutation retry occurs. On a lost response the page clears its keys,
preserves edits, and blocks saves until authentication, authoritative saved-state
readback and explicit review establish a fresh revision. Status or login alone
cannot unlock saving. [Consumer-Recovery/1](Consumer-Recovery-v1.md) adds a
separately versioned, password-authenticated retirement proof usable at full
ordinary capacity. It lists one-way retirement aliases, never raw traffic IDs,
and requires explicit target selection. It creates no replacement session and
replays no application request.
Deferred restart/network-disable actions execute only after the complete reply
has been acknowledged on the matching transport transaction. A lost/partial reply or
session expiry cancels only that transaction's still-pending deferred action.
A normally acknowledged HTTP connection close leaves the login usable. Already committed settings or
accepted WTP operations can remain effective after a lost reply.

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
qualification. Both consumer profiles, native current-cursor preservation,
AP/STA routing and the four smoke screens have bounded independent acceptance.
The [Phase 14 closeout](../development/phase14-closeout-ledger.md) retains its
completed source/retention audits and bounded physical scope. Later software
extensions do not inherit unrestricted physical or release qualification.

An active fake endpoint can choose its own X25519 key, obtain the client's
password-derived finish proof and test password guesses offline against its
known shared secret/transcript. Passive capture alone does not provide that
shared secret. This existing protocol limitation remains; a strong passphrase
and trusted endpoint/network matter. Native local code prevents device-page
execution but does not authenticate a unique device before emitting that proof.
