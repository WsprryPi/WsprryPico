# Phase 15.3 supported management carriers

Status: selected design; implementation and acceptance in progress. October 15,
2026. This record does not close P15.3 until the paired checks and independent
review below pass. P15.1/P15.2 remain closed; P15.4 and later work is excluded.

## Refreshed baseline and source gaps

Both devel working trees were clean before this task. Pico was
`b013504aea54d2f9474da0cbae1678c69fb98def`, including the independently committed
RF-adapter stand-in repair; Pi was `6a39398bb23d69ba0628e1b82171717040115ec8`.
No concurrent fixture change was imported into this task.

Pico `network/consumer_radio.cpp` already dispatches authenticated encrypted
station/AP requests to BrowserApi and owns one volatile session. Its setup
adapters own Wi-Fi/station identity. `network/pico/server.cpp` admits engineering
mTLS HTTP, engineering field HTTPS, and consumer TLS WTP with distinct policies.
Plain LAN WTP has no JSON management. Normal consumer builds select Plain LAN.
`application/resources.cpp` retains legacy `authenticated_https` metadata.

Pi `wtp_runtime_bridge.cpp` rejects all management unless job transport is
`network`; `WtpApplication::idle_management` requires fresh WTP negotiation.
`configuration.cpp` coordinates identity/revision/capability reads and one write,
and strictly validates the application resource. P15.1 added no carrier; P15.2
added that coordinator, safe legacy preservation and four source-pair checks.
The TLS-only loopback fixture does not exercise consumer crypto or interface
admission. These are the implementation gaps selected here.

## Selected contract

Management selection is independent of the configured WTP job transport.
Engineering HTTPS keeps its current default and authentication. The Pi adds an
explicit, volatile Consumer-Radio/1 selection for the configured member's exact
32-hex device ID and operator-entered IPv4 or local hostname. AP authority is
exactly `192.168.4.1`. No Wi-Fi configuration changes, redirect, alternate
address/authority/interface session migration, carrier fallback or write retry
is permitted. USB JSON management is unsupported: no current requirement needs
a second USB configuration protocol. Console commands retain their separate
local policies; WTP reachability grants no JSON administration.

A new independently versioned `transmitter-management/1` discovery document
will describe the actual selected carrier, target, profile/generation, support,
availability, operation allowlist and budgets. It is separate from closed
application objects; legacy `authenticated_https` remains unchanged. Public
consumer identity is only a handshake hint. The encrypted discovery response
must match the authenticated session before Pi consumes remote capabilities.
Unsupported/malformed advertised versions refuse; absent discovery preserves
only the existing explicitly selected engineering compatibility path.

The Pi host adds `/api/v1/member/management` GET/POST/DELETE-like actions using
GET/POST only: POST carries an explicit `connect` or `disconnect` action;
consumer connect includes carrier (`consumer_station` or `consumer_ap`), exact
host and passphrase. Engineering selection uses an explicit action. This route
uses the existing protected shared API guard, operation mutex and idle admission.
No password enters saved INI, ordinary catalogs, URLs, status or browser storage.
The passphrase exists only during login, then is wiped; only bounded traffic
keys survive in process RAM. Disconnect logs out only the session created by
this client. Busy sessions refuse without logout or eviction. Expiry, rejection
or uncertain delivery clears local session state and requires explicit login
and authoritative settings readback before a subsequent write.

Consumer crypto is trusted local C++ using existing OpenSSL: X25519,
SHA-256/HKDF and ChaCha20-Poly1305, exactly Consumer-Radio/1's unchanged
transcript/header/sequence. No device JavaScript is loaded. Outer HTTP status
never establishes inner API success. Device/boot/generation are authenticated;
Host/Origin plus actual Pico interface remain server-side session bindings.
The shared passphrase identifies a group of holders, not a uniquely authenticated
device. It is not a PAKE and does not resist an active peer who knows that
passphrase. Native local code avoids browser page substitution but does not
upgrade this cryptographic trust model or replace engineering mTLS.

Management-only admission may skip opening WTP only when the existing host
application has no active/waiting/owned/loaded/faulted/uncertain work. It retains
the same application control lock and runtime operation mutex. Authenticated
consumer management provides device/boot identity; remote configuration status
still requires idle/unowned/inactive/nonfaulted state. Previously unresolved
host output cannot be cured by selecting a management carrier.

## Carrier/access matrix

All JSON mutations retain complete validation, verified atomic journal writes,
exact revisions/target and modern ABA protection, STOP/cursors, member recurrence,
saved/active/restart latches and matching-transaction deferred delivery. All
unsupported combinations refuse without fallback or mutation. Firmware support
is distinct from current listener/profile availability and Pi-client selection.

| Profile / carrier | Jobs | JSON management / Pi client | Principal and identity | Availability / restrictions / budget | Evidence and limit |
| --- | --- | --- | --- | --- | --- |
| Engineering station mTLS HTTPS | WTP ALPN, same JobService | Existing finite config/schedules/network + coordinated settings; preserved Pi support | Certificate principal; WTP device/boot plus revisions; new authenticated discovery when advertised | Configured credentials, station/TLS clock; existing 2 connections/1 WTP/1 handshake, 32,768 HTTP body; config 1,800/update 2,048 | Existing source/loopback; rerun paired regressions; no new physical claim |
| Engineering field HTTPS | Existing admitted browser job operations | Firmware Configure in normal authenticated surface; no Pi field-cookie client selected | Server TLS plus application password/cookie/session; exact device/revision | Blank/preclock Configure refused; current access/ownership/session rules unchanged | Existing firmware/host tests; Pi unsupported explicitly |
| Consumer station Consumer-Radio/1 | Existing encrypted browser jobs | Existing firmware JSON; new explicit Pi client for config/schedules/network + coordinated settings | Saved Wi-Fi-passphrase holder; authenticated device/boot/profile generation, exact station IP/hostname authority | Association+IPv4, no WTP or UTC prerequisite for management; one shared login, 30 s login, 5 min idle/15 min total; mutation idle/unowned/nonfaulted | New actual crypto/BrowserApi integration required; no bench operation |
| Consumer AP Consumer-Radio/1 | Existing encrypted jobs when admitted | Existing firmware JSON; new explicit Pi client with pre-existing network reachability | Same protocol, exact AP authority and actual AP interface | Temporary AP lease/fallback; RF policy can withdraw AP; no automatic Pi network change; same session/byte limits | New AP-classified deterministic integration; physical routing remains a gate |
| USB WTP / Console, engineering | WTP reference job control; Console local policies | USB JSON unsupported, Pi JSON client unavailable | USB role/identity and existing local policy, no JSON principal | Preserve roles, frames and Console commands; no new parser or framing | Existing tests; no USB JSON qualification |
| USB WTP / Console, consumer | WTP intentionally disabled; Console retained | Unsupported | Existing local Console policy | No implicit administration from USB connectivity | Existing source/tests |
| Plain LAN WTP / optional consumer TLS-WTP | Jobs only | No JSON on either; independent consumer management selection allowed | LAN principal / TLS-WTP's existing principal; WTP IDs only | Plain station port 31417 after SNTP; optional TLS ALPN WTP only; no automatic substitution | Existing WTP tests; no carrier expansion |
| BLE WTP | Existing engineering encrypted local control | JSON unsupported, no Pi JSON client | Existing Field-GATT/password/session identity | Existing field policy and bounds; consumer BLE unselected | Existing tests; WTP/1 unchanged |
| Consumer preclock | WTP clock gate retained | Consumer station/AP JSON available when listener/profile admitted, including without WTP | Authenticated Consumer-Radio identity/generation | Job UTC policy remains; JSON Configure still uses shared idle/health gate | New management-only tests required |
| Blank / recovery / unavailable profile | Only existing explicitly admitted provisioning/recovery paths | No P15.3 JSON carrier; advertise unavailable only where an authenticated path exists | Public hints authorize nothing | No synthetic authenticated principal, no new recovery authority; fail closed | Negative profile/discovery tests; P15.7 redesign excluded |

## Routes and resource budgets

Consumer transport uses only port 80, GET `/api/consumer/v1/identity` and POST
`/api/consumer/v1/start`, `/finish`, `/request`. Start body <=512 bytes.
No cookies, redirects, CORS, arbitrary URLs or device scripts. Each network
exchange has a finite deadline; login completes inside the 30 s server window.
The encrypted management allowlist is GET capabilities/status/config/schedules/
network/application/management, PUT config/schedules/network, POST config/update,
and client-session logout. No provisioning, restart, hardware editor or job
submission is added to the Pi proxy.

HTTP body is <=32,768 bytes; CR01 header+tag consume 44, leaving 32,724 plaintext
bytes. The inner JSON envelope and escaping count within that limit. The
coordinator's <=2,048-byte body and resulting <=1,800-byte Config remain tighter;
actual serialized envelope size is checked, including path/revision overhead.
Responses authenticate completely before JSON/status/ETag parsing; coordinator
reads remain <=16,384 bytes. No new Pico frame pools or firmware budgets.

## Acceptance and review ledger

Pending: implementation, deterministic Linux host/TLS/lwIP and cross-link checks,
actual Pi/OpenSSL-to-Pico/Mbed TLS station/AP integration, negative and lifecycle
coverage, P15.2 four-pair compatibility, UI tests and desktop/mobile light/dark
rendering, independent adversarial review/repair/reassessment, exact clean pins,
CI and independent origin/devel parity. Exact commands/results go here as run.

No physical device, installed service, GPIO or RF operation is authorized or
claimed. Operator documentation in WsprryPi-Docs is read-only; P15.14 retains
final user documentation. Exact follow-up will be recorded after implementation.

An active fake endpoint can choose its own X25519 key, obtain the client's
password-derived finish proof and test password guesses offline against its
known shared secret/transcript. Passive capture alone does not provide that
shared secret. This existing protocol limitation remains; a strong passphrase
and trusted endpoint/network matter. Native local code prevents device-page
execution but does not authenticate a unique device before emitting that proof.

## Independent review round 1 and repairs

The independent read-only reviewer reported five actionable findings, plus the
known test defect below. All are being repaired and rechecked before closure:

1. Read authoritative local management state on reload and preserve an existing
   consumer session on an already-selected refusal; disable duplicate Connect.
2. Execute the genuine consumer fixture in the current Make/CI interoperability
   path, retaining historical profiles.
3. Install parsed-password cleansing before endpoint/already-session rejection.
4. Match engineering station availability to TLS admission and synchronized,
   nonzero UTC; distinguish unavailable listener/AP drain and blank source.
5. State active fake-endpoint offline password guessing in both protocol and
   client documentation; do not claim PAKE or unique-device authentication.
6. Replace the faulty lost-reply case with a dropped encrypted mutation response
   after verified journal commit, followed by no replay, expiry/relogin,
   authoritative readback and stale-revision refusal through the coordinator.

Additional author repairs preserve an explicit disconnected selection across
runtime endpoint replacement, erase expired traffic keys from idle polling,
and separate host built-in adapter capability from authenticated remote support.
Impeccable's first visual pass found unreadable dark secondary buttons; scoped
existing-theme colors repair that contrast. The second render pass is pending.

Preliminary validation: seven focused Pico tests passed; the full Linux suite
passed 187/187 after supplying the required fixture user and Python/retained JS
dependencies. The RP2350 Arm target cross-link passed using retained SDK
`079c6f39023649b154152db30f1d781e884879bc` and Arm GNU 15.3.1. Later metadata
repairs require affected rechecks. Pi configuration/API and UI unit checks and
initial real consumer integration passed; final vector/lost-reply, runtime,
exact-clean source-pair and sanitizer results remain pending.

The second independent read-only assessment found no remaining actionable Pico,
protocol, runtime or UI defect in its bounded pass. It verified reload-state
restoration, disabled duplicate Connect, parsed-password cleanup, carrier/clock
availability, current-profile fixture execution and corrected lost-write
assertions. It approved a provisional Pico dependency commit after affected
checks; this is not joint P15.3 completion. Final evidence reassessment remains.

## Discovery wire document

`GET /api/v1/management` returns exactly `schema`, `target`, `profile`, `preclock`,
`profile_generation`, `selected`, `carriers`, `unsupported`, `operations`, `limits`.
The target is the existing closed member/device/boot object. Profile is one of
`unavailable`, `blank`, `recovery`, `engineering`, `consumer`; generation is a
nonzero canonical uint64 decimal string or null. `preclock` is boolean.
Selected is `engineering_mtls`, `engineering_field`, `consumer_station` or
`consumer_ap`. The carriers array has those four rows in that order, each exactly
`carrier`, boolean `built_in`, boolean `available`. Availability describes the
current profile/listener/admission, including mTLS UTC gating; resource BUSY,
ownership and transient capacity still govern individual operations.

Unsupported is exactly `["usb_json","plain_wtp_json","tls_wtp_json","ble_json"]`.
Operations is the common bounded configuration subset, not an exhaustive list
of every existing BrowserApi/job/setup function:

```json
{"GET":["capabilities","status","config","schedules","network","application","management"],"PUT":["config","schedules","network"],"POST":["config/update"]}
```

Limits is exactly the integer-valued object:

```json
{"http_body":32768,"consumer_plaintext":32724,"config":1800,"update":2048,"login_ms":30000,"idle_ms":300000,"absolute_ms":900000,"consumer_sessions":1}
```

No fields are inserted into the old closed application objects. Pi checks exact
known shape/types, selected availability and authenticated target/profile binding.
Present unsupported discovery refuses; absent discovery is accepted only on the
explicit existing engineering path. Each consumer HTTP exchange has an 8-second
deadline including resolution/connect, and does not follow redirects. Each
coordinated operation is finite; browser timeout remains the existing 180 seconds.

Pico dependency acceptance before paired testing: final Linux host suite passed
187/187 with no skips; WTP validator passed 23 schema, seven raw JSON, one framing
and eight transition cases. Six affected ASan/UBSan checks passed without
sanitizer diagnostics. Final RP2350 target cross-link passed after the admission/
UTC metadata repairs. The exact-source companion pin will reference the reviewed
Pico dependency commit; joint acceptance is still pending, so the roadmap remains
pending in this provisional commit.
