# Consumer-Radio/1

Status: bounded two-Pico settings validation accepted, 2026-10-14. The earlier
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
Durable retention and final release audits remain open.
Engineering mTLS and Plain LAN WTP retain their
existing contracts. This transport supplies the missing authenticated consumer
radio page and shared Browser API; it does not retain the withdrawn browser
owner keys or change the immediate commissioning transaction.

A healthy source-5 consumer profile keeps the existing open setup AP available.
Open `http://192.168.4.1/radio` on that AP and log in with the Wi-Fi passphrase
saved in the consumer profile. The station interface never exposes the
plaintext radio routes. AP association alone grants no private read or mutation.
Wi-Fi and station identity remain owned by their existing setup pages; the
radio configuration API presents their effective values and rejects changes
that the profile would override at restart. Schedules, pins and frequency
opt-ins use the existing configuration journal and admission engine.

Radio management retains AP access during unarmed ownership and loaded plans.
Commissioning keeps its stricter unowned-only guard. Unknown/active output,
armed, running and failed states withdraw this AP path under the retained RF
connection policy; job execution stays local. A saved source-5 consumer profile
disables USB WTP while retaining USB Console inspection. Consumer job control
uses Plain LAN and the authenticated AP-local radio adapter; engineering
profiles retain the reference USB WTP endpoint. The ownership distinction passed host and bounded physical
settings validation on both Picos.

The existing open-AP setup threat boundary remains: HTTP does not authenticate
the page before password entry. A substituted malicious page can steal entered
credentials. This adapter protects traffic between the genuine page and Pico
against passive observation and rejects peers without the saved passphrase;
it is not a PAKE or a replacement for authenticating the delivered page.
Nothing is retained in browser storage. Private credentials and keys remain
in RAM for the bounded exchange and are never returned by identity/config reads.

## Handshake

All routes are on the AP-only port-80 listener. Public GET
`/api/consumer/v1/identity` returns version `1`, device/boot lowercase 32-hex IDs,
profile generation as a canonical nonzero decimal string, and authentication
`saved_wifi_passphrase`. POSTs require exact Host `192.168.4.1`, Origin
`http://192.168.4.1`, `X-WsprryPico-Radio: 1`, no Cookie, and absent or same-origin
Fetch Metadata. There is no CORS permission or redirect follow.

POST `/api/consumer/v1/start`, JSON, exactly:
`version`, `device_id`, `boot_id`, `generation`, `public_key`, `nonce`.
The browser supplies an ephemeral X25519 public key (canonical unpadded
base64url, 32 decoded bytes) and random nonce (16 bytes, lowercase hex).
The Pico verifies current identity/generation, creates an ephemeral X25519 key,
random session and challenge, and returns those bindings plus `login_ms:30000`.
Only one pending or authenticated session exists. Successful starts are spaced
at least one second apart; a pending slot expires after 30 seconds.

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
No automatic mutation retry occurs. On a lost response the page clears its keys,
preserves edits, and requires login plus status/readback before another action.
Deferred restart/network-disable actions execute only after the complete reply
has been acknowledged on the matching transport transaction. Disconnect or
expiry cancels a still-pending deferred action. Already committed settings or
accepted WTP operations can remain effective after a lost reply.

The [fixed vectors](Consumer-Radio-v1-vectors.json) use synthetic credentials
and compare Noble browser output with the pinned Mbed TLS implementation,
including a maximum-size paged request. Host/vector checks are not target/RF
qualification. Both consumer profiles, native current-cursor preservation,
AP/STA routing and the four smoke screens have bounded independent acceptance.
Consolidated source, retention and release closeout remain required.
