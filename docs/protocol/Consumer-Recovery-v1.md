# Consumer-Recovery/1

This additive extension retires one explicitly selected Consumer-Radio/1 login.
It never creates an active session, repeats an application request, changes a
saved profile, resets Wi-Fi, or controls a job. Consumer-Radio/1 bytes and the
closed transmitter-management/1 and /2 documents remain unchanged.

## Admission and discovery

Use the current admitted consumer AP or station port-80 authority. The exact
Host, Origin, actual receiving interface, Fetch Metadata and cookie prohibition
are the Consumer-Radio POST rules. There are no redirects, cookies or CORS.
Discovery is a public handshake hint; it proves neither identity nor authority.
Native Pi additionally compares the configured full device ID and selected
carrier/authority before producing a password proof.

GET `/api/consumer/v1/recovery` returns exactly these JSON fields:

```json
{"schema":"consumer-recovery/1","device_id":"11111111111111111111111111111111","boot_id":"22222222222222222222222222222222","generation":"139","authority":"192.168.1.53","interface":"station","proof_ms":5000,"sessions":[{"selector":"33333333333333333333333333333333","state":"active"}]}
```

IDs are canonical 32-character lowercase hex; generation is an exact nonzero
uint64 decimal string. Interface is `ap` or `station`. There are at most three
unique retirement selector entries; state is `active` or `pending`. Only occupied logins on the
current exact authority/interface are listed. IP, hostname and optional `:80`
authorities are distinct session contexts. No IP/user agent/tab name identifies
an owner. Public selectors are the first 16 bytes of SHA256 of the
NUL-terminated `WsprryPico/Consumer-Recovery/1/selector` domain, decoded device
ID, decoded boot ID and decoded ordinary traffic session ID, in that order.
They cannot select CR01 traffic or consume another client's pending login proof.
Ambiguous selector collisions refuse without retirement. Raw traffic IDs are
never listed. Existing traffic-header visibility/authentication-failure limits
are unchanged. The UI shows the selected device, authority, state and retirement
impact and requires deliberate operator action.

Unsupported firmware may return 404 or its historical dispatch refusal (403).
Clients report unsupported/unconfirmed recovery without probing destructive
alternatives, weakening authentication or disabling supported reads/saves.

## Fresh proof

POST `/api/consumer/v1/recovery/start`, JSON at most 640 bytes, has exactly:

```json
{"version":1,"device_id":"11111111111111111111111111111111","boot_id":"22222222222222222222222222222222","generation":"139","public_key":"ZLEBsdC-WocEvQePmJUAH8A-jp-VIvGI3RKNmEbUhGY","nonce":"55555555555555555555555555555555","target_selector":"33333333333333333333333333333333"}
```

Key and nonce use the frozen Radio/1 encodings. Unknown/duplicate fields,
oversize/truncated input, stale identity/generation and mismatched victim context
refuse before retirement. An absent target is permitted for safe reconciliation.
One proof workspace exists outside the three ordinary slots and their one
pending-login quota. It never admits application reads or becomes a fourth
active session. Its absolute lifetime is five seconds. Starts are globally
spaced one second apart, including RNG/crypto failure. A pending proof refuses
another start. An abandoned workspace clears within five seconds in the absence
of competing new starts; adversarial traffic can deny service.

The successful grant has Radio/1's exact grant fields, `login_ms:5000`, and one
additional `recovery` object containing exactly `target_selector`, `authority`
and `interface`. Device/boot/generation are current. Its fresh session/challenge
and X25519 key are a proof identity, never an ordinary session identity. The
same nonreused boot-local serial namespace prevents delayed proofs from
selecting a later ordinary occupant. Clients compare all scope fields with the
independently selected transport context and intended target.

Let `R` be Radio/1's unchanged transcript. Define:

```
C = SHA256(target_selector_decoded_16 || interface_byte || authority_length_byte || authority_ASCII)
T = SHA256(R || UTF8("WsprryPico/Consumer-Recovery/1\0") || C)
```

The interface byte is 1 for AP, 2 for station. Authority is the exact admitted
Host (at most 72 ASCII bytes). The domain includes its final NUL. Radio/1 HKDF,
X25519/password IKM, directional keys, CR01 header, nonce and AEAD rules apply
with this separate `T`. Thus recovery proofs and acknowledgements cannot be
substituted for ordinary login/application traffic. This is not a PAKE or
unique-client authentication. Shared-password membership and HTTP page delivery
retain Radio/1's active-endpoint offline-password-guessing/substitution limits.

POST `/api/consumer/v1/recovery/finish` is exactly a 76-byte binary
sequence-zero password proof. Every complete addressed proof consumes the
workspace, including authentication failure. Correct authentication constructs
an encrypted sequence-zero acknowledgement with exactly `retired:true`,
`present` (boolean), `target_selector`, `device_id` and `boot_id`. Only after that
response has been constructed does the manager retire the exact target, if
present. Failure to construct it has no retirement effect. Recovery keys and
PSA handles are erased after this single exchange. No application requests are
ever dispatched with them.

## Results, cleanup and retries

A lost finish reply is unconfirmed. The operator can repeat a fresh authenticated
retirement of the same boot-bound target after any abandoned proof workspace
expires. The acknowledgement reports an absent target safely. This does not
allocate a replacement session or advance ordinary traffic sequences. A new
login remains an explicit operation and keeps ordinary one-second pacing.
No five-minute ordinary expiry or reboot is needed for capacity recovery.

Retirement closes only the selected login's traffic/proof state and invokes
false delivery for its still-pending transaction. The singleton setup authority
also records the login that obtained an unsubmitted preparation grant; closing
that login cancels only that grant. Lost network/station preparation replies
can therefore be corrected after explicit retirement. Acknowledged trials,
durable settings, accepted jobs, STOP, owner, watermarks and scheduler state
survive authentication closure. No per-session provisioning receipts exist.
Delayed ACK/FIN/RST/timeout cannot deliver a cancelled or later transaction.

An authenticated new setup start can replace a failed terminal network/station
attempt after validating current identity/generation and authority. It cannot
replace an active trial, unresolved commit or pending committed restart. This
permits corrected explicit input without waiting for terminal-record expiry.
The durable result receipt retains its original generation/digest semantics.

Ordinary saves have no request-digest receipt. After uncertain delivery, preserve
the draft, invalidate its write eligibility, authenticate/recover and read
current saved configuration/resources and fresh revisions consistently. Display
saved versus draft and saved versus active/null/fault state. Matching fields
prove current state, not attribution to the interrupted attempt. Review and a
new explicit save are required; no save, carrier or authentication retry is
automatic. Commissioning retains its sent-once generation/digest receipt across
login/origin changes. Later generations, unsafe numeric rounding, wrong device,
malformed/different digests and contradictory results remain unconfirmed.

Errors are bounded ordinary HTTP errors. Expected codes include
`invalid_radio_recovery` (400), `radio_recovery_required` /
`radio_recovery_rejected` (401), `forbidden` /
`radio_session_context_mismatch` (403), `radio_recovery_pending` (409),
`radio_body_too_large` (413), `radio_recovery_rate_limited` (429) and
`radio_recovery_unavailable` (503). Unauthenticated outer errors never prove a
save or retirement did not happen. Invalid traffic cannot refresh a victim's
timers, retire it without proof, alter settings or obtain private reads.

The [synthetic vectors](Consumer-Recovery-v1-vectors.json) retain the original
Radio/1 vector format with a `recovery` scope. They bind Noble, Mbed TLS and
OpenSSL results. The [execution record](../development/phase15-7-recovery.md)
separates deterministic software evidence, compiler/link resource bounds and
unperformed physical qualification.
