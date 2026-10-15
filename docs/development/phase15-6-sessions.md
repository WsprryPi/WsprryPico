# P15.6 independent consumer sessions

Status: implementation in progress; no acceptance or physical qualification yet.

## Selected design and acceptance assertions

Three fixed session slots support phone, Mac and native Pi simultaneously at the
same station authority. At most one slot may hold a pending login; pending and
active slots together cannot exceed three. A pending login reserves its eventual
active slot. Full capacity returns 409 `radio_session_capacity`; an occupied
pending quota returns 409 `radio_login_pending`. Successful starts remain globally
spaced by one second (429). No eviction or automatic mutation retry occurs.

Each slot owns binding, interface/origin, timestamps, sequence, one outstanding
transaction and a distinct injected crypto object. Production statically constructs
three noncopyable crypto objects; handles are never copied or moved. At most one
ephemeral PSA key is retained, because only pending logins retain one. Active
sessions retain two 32-byte traffic keys and transcript state; PSA lifetime stays
reference counted. Crypto scratch is transient on serialized core 0. The fixed
metadata/crypto size and linked RAM/stack results will be recorded after building.
No session retains request/response pages: these belong to the unchanged two TCP
tasks. Two large exchanges still require existing memory admission and the 32 KiB
authority reserve; capacity does not promise two maximum-size replies can allocate.

Lookup requires a bounded CR01 header before using its ID as an untrusted selector.
The selected slot must match state, context, sequence and complete AEAD. IDs must
be nonzero and distinct from occupied slots, with a finite fail-closed RNG attempt.
Expiry and every local failure close only the selected slot. Generation, unhealthy
profile and global admission invalidate all affected slots. AP withdrawal and
station address/hostname changes invalidate only the matching interface. Normal
TCP closure leaves login state intact. Monotonic transport transaction identities
route delivery completion across slot reuse, without duplicating board effects.

Management discovery becomes closed `transmitter-management/2`, keeping the old
shape and all old limits except `consumer_sessions:3`, and adding integer
`consumer_pending_logins:1` in limits. Version 1 remains frozen. New Pi accepts
exact versions 1 and 2 with their exact limits/types. Old Pi refuses version 2;
there is no fallback or downgrade. Consumer-Radio/1 bytes/vectors stay unchanged.

Required evidence includes genuine independent crypto handshakes, interleaved
requests, cross-key rejection, isolated failures/expiry/context loss and repeated
reclamation, pending/active quotas, transport ACK/close/timeout isolation, deferred
board-effect isolation, stale configuration conflicts, shared transmitter authority,
native Pi and browser flows, historical exact-source profiles and strict discovery
negatives. Source-pair, sanitizer, cross-link, review and publication results remain
pending. P15.7 recovery and later roadmap features remain open.

## Review and repair ledger

These are executor adversarial reviews, not independent reviews. The operator's
separate post-execution review remains a distinct gate.

| Severity | Trigger / finding | Repair and regression |
| --- | --- | --- |
| P1 | A starts a slow upload, B dispatches a later connection first; a first-draft global transaction-order check rejected A's otherwise valid packet | Removed dispatch-order assumption. The unchanged HTTP allocator owns nonreused accept-time IDs; manager checks live duplicate IDs and completion matches the owning slot. Genuine maximum-size slow upload, B login, two retained 32,768-byte ciphertexts and delayed-completion regressions exercise this. |
| P1 | AP withdraws and returns without any HTTP dispatch; the old adapter refreshed session contexts only during dispatch, potentially reviving its old login | Production bootstrap poll refreshes actual AP/station/IP/hostname contexts before session expiry. Compiled actual poll block tests the no-request path; real manager/AEAD tests prove selective AP/station invalidation. |
| P2 | Old native Pi compared the frozen one-session discovery exactly | Explicit closed management/2 and exact Pi version-1/version-2 validation; no arbitrary capacity acceptance, downgrade or retry. Historical profiles retain their source identities. |

Review also checked header lookup before authentication, nonce/sequence handling,
failed proof/tag/resource cleanup, reference-counted PSA leases, slot reuse,
transaction-specific receipt cancellation, shared revision/owner authority,
profile-generation invalidation, quotas and client-local key cleanup. Sequence
exhaustion closes only its addressed slot. Session and manager objects cannot copy
crypto ownership. Repeating test RNG bytes still produce distinct boot-local IDs.

Test-controller repairs are evidence limitations, not production defects: bounded
base64 replaces hex control encoding so maximum ciphertext fits the JSON parser;
empty identity bodies are handled explicitly; socket IDs retain the parser's
canonical decimal-string type; profile-generation tests use a fresh request digest
as required by the real journal. Browser fixture script insertion uses a literal
replacement callback. Initial failed logs are retained alongside reruns.

## Preliminary evidence and resource budget

Retained Linux image `wsprrypico-p153-env:local` (`c7f2a891a6ff`), GCC 14.2,
CMake 3.31.6 and Node 20.19.2 are reused without network or device mounts. SDK
`079c6f39023649b154152db30f1d781e884879bc`, Mbed TLS
`0bebf8b8c7f07abe3571ded48a11aa907a1ffb20`, lwIP
`77dcd25a72509eb83f72b033d219b1d40cd8eb95` and Arm GNU 15.3.1 are retained.

The standard and StandaloneRF images cross-link with allocator, topology,
Bluetooth, stack-guard and RF RAM-placement checks. Host metadata is 976 bytes
for the manager, 152 bytes per crypto object and 1,976 bytes for the unchanged
HTTP tasks. Target symbols are manager 864 bytes and all three crypto objects 432 bytes,
1,296 bytes combined, plus at most three bounded authority strings. Standard
BSS is 172,572 bytes; StandaloneRF BSS is 328,512 bytes. The linked gaps from
BSS end to heap limit are 302,852 and 146,912 bytes respectively, before runtime
allocations; these are upper bounds, not observed free heap. Manager stack frames
are start 856, finish 584, exchange 1,320 and finish_request 32 bytes. Only one session can retain a private PSA key; active keys
occupy fixed arrays. Target crypto stack-usage entries are create 88, authenticate
544, decrypt 576 and seal 1,784 bytes; main is 4,400 bytes. These are individual
compiler frames, not measured cumulative stack high-water marks.

Worst-case retained session state is fixed; only two HTTP exchanges can own pages.
Two maximum ciphertext uploads occupy 65,536 input bytes plus bounded page/parser
metadata and responses. Building one response can temporarily add envelope and
ciphertext pages and crypto scratch. The existing admission checks preserve the
32 KiB authority reserve and may refuse before both maximum replies fit. Host
large-exchange success does not establish target heap fragmentation or availability.
No on-target heap/stack high-water, phone/Mac transport, timing, GPIO or RF test
has been run or authorized by this software-only prompt.

Actual Chrome 155.0.8059.40 contexts use the shipped page/client against the Linux
HTTP/session/Mbed TLS fixture. Two independent contexts preserve drafts on a stale
save and remain logged in; another context gets finite capacity feedback; logout
releases only that login. Desktop 1280x900 and mobile 390x844 are captured under
light/dark preferences. Pico's incumbent stylesheet explicitly uses light colors
in both preferences; no dark-theme redesign is claimed. Pi's own themed surface
has separate visual checks. No overflow was found in the scoped Pico feedback.

## P15.7 and documentation impact

The reported physical failed-callsign-save/lost-login observation remains operator
history; no new physical reproduction is claimed. Genuine software tests show a
profile-owned callsign refusal retains both sessions. A deliberately lost encrypted
reply after a durable save clears that client's keys without replay; readback by
another session observes the commit. Relogin can leave an abandoned server slot,
and three occupied slots refuse another login until logout/expiry. This bounded
limit remains; P15.7 broader recovery is open.

Updated: Consumer-Radio session/lifecycle contract, management discovery reference,
architecture, this design/review/acceptance record, browser feedback and Pi
compatibility/fixture references. Considered unchanged: Consumer-Radio/1 vectors,
WTP/1, Config/update schemas, RF/scheduler ownership and historical P15.1-P15.5
acceptance records. Concurrent originating-chat edits to the existing handoff,
development index and roadmap are preserved separately.

P15.14 must explain three total sessions, the pending-login quota, one-second
login pacing, independent logout/expiry and abandoned tabs; management/1 versus
management/2 Pi compatibility; retained edits and revision conflicts; readback
after lost replies; saved/active/restart state; and capture final phone/desktop
screenshots once physical concurrency and P15.7 settle. The independent operator
documentation repository is not modified or published by this task.

## Candidate validation before paired source pin

All 13 genuine browser-client/production-HTTP/session/Mbed TLS scenarios pass.
The affected ASan/UBSan run passes 9/9 groups with leak detection, including those
13 scenarios, unchanged vectors, configuration and provisioning delivery tests.
Production adapter regression passes all four compiled branch tests. WTP contract
validation passes 23 schema, seven raw JSON, one framing and eight transition cases.
Both cross-links and the second bounded Chrome workflow pass.

The latest complete host run is 189/190: the unchanged engineering TLS test
intermittently loses its host worker process. A focused rerun passed; repeated
isolated diagnosis is recorded separately below. This fixture accelerates its
clock fivefold while retaining the worker's 100 ms rendezvous deadline (20 ms
wall time). No production RF/worker deadline was relaxed. Do not interpret a
failed full run as a clean 190/190 result. Paired Pi source tests and final
publication remain pending at this candidate commit.
