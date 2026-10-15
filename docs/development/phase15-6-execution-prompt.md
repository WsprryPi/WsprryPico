# P15.6 handoff: independent simultaneous consumer login sessions

Status: **executed within the recorded software scope**. The originating
conversation prepared this source review and prompt; the operator authorized a
separate executing conversation. The [implementation, review and acceptance
record](phase15-6-sessions.md) binds actual source pairs, checks, publication
and exclusions. Physical phone/Mac and target resource/RF acceptance remain open.
P15.5's published closure is unchanged. The operator's requested subsequent
post-execution review has not been claimed by this execution.

## Lead repository and reviewed baseline

**WsprryPico leads**, with coordinated WsprryPi compatibility work. Session
allocation, crypto, replay protection, expiry, interface binding and HTTP
completion belong to Pico. Pi already has a native Consumer-Radio/1 client;
its management discovery validator must evolve with Pico's advertised limits.
Neither another protocol repository nor another application coordinator is needed.

The review was performed on 2026-10-15:

| Repository | Reviewed `devel` head | State and recent work |
| --- | --- | --- |
| WsprryPico | `62b33d9fe5214f2b2319b71e1932bdf88ed0a1ba` | Clean; P15.5 implementation `9cf5ba2fe92de9abb893d0c6a44fa0a0a96c3794`, followed by documentation-only acceptance |
| WsprryPi | `50097e652b4af70d510f4a29d4edf1ffa24d3f0a` | P15.3/P15.4 carrier/shared-resource adoption; unrelated Release Punchlist and Si5351 source/documentation/evidence work is present and must be preserved |

Pico's P15.5 head was independently verified against `origin/devel` before
this handoff. Refresh both repositories' actual state before execution; these
are orientation pins, not permission to reset either checkout to an older head.

### Source-review findings that determine the implementation

1. **Transport concurrency is already present.**
   `src/network/pico/http_server.{hpp,cpp}` owns two cooperative core-0 TCP tasks,
   independent parser/response/ACK state, monotonic high-bit transaction IDs,
   ten-second absolute deadlines and at most 1024 output bytes/task/poll.
   These transient slots are not login identities. Engineering HTTPS already
   has its own bounded two-slot service. Keep that P15.5 foundation.
2. **Consumer authentication is still a singleton by design.**
   `src/network/consumer_radio.hpp:57` describes one session. Its private state
   holds one binding, crypto reference, sequence, pending transaction, authority,
   interface and pair of timestamps. `consumer_radio.cpp:164` rejects start
   whenever that state is occupied; finish/request use the singleton binding.
   Refactor the full lifecycle, not just this busy check.
3. **Crypto and global PSA lifetime need separate ownership.**
   `src/network/pico/consumer_radio_crypto.hpp` holds one private-key handle and
   traffic-key/transcript set; `src/standalone/pico/main.cpp:564` constructs one
   crypto instance. `PsaCryptoOwner` is noncopyable and reference-counts the
   process-global PSA subsystem. Clearing a session must destroy its own keys
   without invalidating another session, engineering TLS or a transient validator.
4. **Some shared state must remain shared.**
   `BrowserApi` has one board-level pending network/restart action and routes
   completion by transaction. `PicoBootstrapServer` has one provisioning receipt,
   captured owner-status commit evidence and shared trial/commit/restart gates.
   Preserve these serialized board effects while making session exchange state
   independent. Per-session state must not duplicate the scheduler or RF owner.
5. **Discovery is a compatibility gate, not cosmetic metadata.**
   `src/network/management.cpp:33` advertises `consumer_sessions:1`.
   `docs/development/phase15-3-management-carriers.md#discovery-wire-document`
   freezes the exact `transmitter-management/1` shape and limits. Pi's
   `src/wtp_integration/consumer_radio.cpp:140` validates that document and
   compares the complete limits object against an exact one-session value.
   Pi uses that validator during login and configuration/resource requests.
   Raising only the Pico number will make the current native Pi client refuse.
6. **Each browser client already has its own volatile state.**
   `src/network/bootstrap_web/radio-client.js` keeps keys, sequence and busy
   state per `RadioClient`; ordinary request failure clears only that object.
   It serializes requests within a client and never automatically repeats a
   mutation. Its generic error handling contributes to the separate P15.7
   recovery issue. Preserve isolation and scope any required feedback changes.
7. **The wire already carries a session ID.**
   `docs/protocol/Consumer-Radio-v1.md` specifies the X25519/HKDF/AEAD transcript,
   a `CR01` header with 16-byte session ID and 64-bit sequence, and independent
   direction keys. Session lookup can use the bounded header as an untrusted
   selector, then apply interface/origin, state, sequence and full-tag checks.
   The selector alone grants no authority and must not trigger application work.

These are P15.6 change requirements and compatibility risks, not claims that
current one-session behavior violates its accepted contract. P15.5's historical
results were 189/189 host groups, six affected sanitizer groups, contract checks
and both RP2350 cross-links. They have not been rerun during this prompt-only
preparation and do not qualify a future multi-session implementation.

## Prompt for the executing conversation

Implement **P15.6 — multiple simultaneous login sessions** using this review
as orientation. Work on **`devel` in both affected repositories**:

- `/Users/lbussy/GitHub/WsprryPico` — lead firmware, portable session manager,
  crypto adapter, browser client, protocol/capability documentation and tests.
- `/Users/lbussy/GitHub/WsprryPi` — necessary native-client discovery,
  compatibility fixtures, runtime/UI regressions and documentation only.

Once the operator executes this prompt, complete the implementation, validation,
adversarial review/repair cycles, scoped commits and pushes. Do not stop after
writing another plan. Do not implement later Phase 15 features incidentally.

### 1. Re-establish state and invariants

Read each repository's applicable AGENTS.md and instructions; in Pico read
README.md, CONTRACT.md, docs/architecture.md and docs/development/README.md.
Inspect branch, dirty paths, remotes and recent commits before editing. Preserve
all unrelated work; do not reset, stash or stage it. Keep implementation on
`devel`. Detached historical source checkouts are allowed solely for validation;
retain their history/identity and do not use them as implementation branches.
Do not introduce an unrelated or third protocol repository. Refresh and extend
the source review if intervening changes affect the design. Reuse existing
isolated validation environments when their identity/dependencies can be verified.

Read the P15.1-P15.5 acceptance records and current contracts, including:

- `docs/development/configuration-updates.md`, `issue447-review.md`,
  `phase15-3-management-carriers.md`, `phase15-4-shared-resources.md`,
  `phase15-5-concurrent-web-service.md`, and the Phase 15 checklist.
- `docs/protocol/Consumer-Radio-v1.md`, its fixed vectors, and
  `docs/browser-api.md` management discovery section.
- Pico `consumer_radio`, target crypto/PSA lifetime, `http_server`,
  `bootstrap_server`, BrowserApi and main-loop admission/wiring.
- Pi `src/wtp_integration/consumer_radio.{hpp,cpp}`, `configuration.cpp`,
  `target_runtime.hpp`, `browser_api.cpp`, `src/wtp_runtime_bridge.cpp`
  (`wtp_runtime_management` and its `operation_mutex`), and
  `src/tests/network/CMakeLists.txt` plus pins. The existing
  `src/tests/network/consumer_interop.cpp` already drives native Pi packets into
  real Pico/Mbed TLS; extend it without claiming that its in-process adapter
  alone tests the production TCP/bootstrap dispatch.

Retain one local JobService, scheduler, configuration authority, journal and
transmitter ownership model. Networking/crypto/commits remain serialized on
core 0; RF execution remains local on core 1. Multiple authenticated sessions
never imply multiple RF owners, simultaneous transmissions or replicated
recurrence. Preserve STOP policy, profile-owned station fields, saved/active/null
resource semantics, restart inhibition, revision checks and uncertain-write
readback. USB/raw Plain or TLS WTP/BLE do not gain JSON management or new auth.

### 2. Settle a bounded session and compatibility design

Before modifying the state machine, record the selected design and its exact
acceptance assertions in a new P15.6 implementation/review record. This is a
routine implementation decision within the authorized slice; use measured
budgets and existing contracts to decide it.

- Support **at least two independently authenticated consumer clients** on the
  same Pico, including two station clients at the same authority. A slot per
  interface or per IP is insufficient. Phone and Mac sessions must coexist.
- Select a fixed active-session capacity and a separately stated pending-login
  quota. Evaluate a third active session for native Pi alongside phone/Mac;
  disclose the chosen limit and what happens if Pi already occupies one slot.
  Do not promise a third session without budgeting/testing it. Pending and active
  quotas, TCP capacity and in-flight exchange capacity are different resources.
- Bound metadata, crypto objects/PSA handles, handshake scratch, ciphertext/input
  pages and transient response memory. Keep the existing 32 KiB authority
  reserve and P15.5 header/body admission policy. Recheck worst-case retained
  keys, pending proof plus active sessions, and simultaneous large exchanges.
  No unbounded allocation, silent pool growth or eviction of a healthy session.
- Choose a crypto construction/injection model that gives every occupied slot
  its own ephemeral/traffic key state. Account for noncopyable PSA ownership;
  do not copy raw handles or rely on movable/assignable objects that are not.
  Reuse the portable/target separation and existing dependency test pattern.
- Keep login rate limiting bounded and intentional. Simultaneous legitimate
  starts may receive a documented finite rate/capacity refusal; one pending
  unauthenticated login must not clear or replace active sessions. Avoid an
  unbounded retry queue or weakening anti-abuse controls to make a test pass.
- Keep the Consumer-Radio/1 transcript, algorithms, header and vectors unchanged
  unless an incompatibility is demonstrated. A session table alone should not
  require changing these bytes. If a wire change is necessary, independently
  version it and test the supported old/new combinations.
- Resolve discovery evolution explicitly. The existing management/1 limits are
  frozen and old Pi compares exact values. Select and document a version or
  capability-evolution policy; do not silently change a frozen value, advertise
  one session while providing more, or accept arbitrary limits by ignoring the
  validator. Keep strict field/type/identity/carrier checks. Negative, zero,
  boolean, fractional, excessive and unsupported-version inputs must refuse.
- New Pi must retain supported one-session firmware behavior. Old Pi against
  new Pico must either work through a deliberately supported path or fail
  explicitly under the documented compatibility policy. No authentication
  downgrade, carrier fallback or mutation retry may hide incompatibility.

### 3. Implement independent lifecycles and safe delivery routing

Each occupied slot owns its state, ID/binding, crypto, session authority and
actual interface, handshake/idle/absolute deadlines, next request sequence and
at most one outstanding application exchange. Preserve the existing 30-second
login, five-minute idle and fifteen-minute absolute limits unless a documented,
compatibly advertised requirement makes a change necessary.

Route finish/request by a bounded, validated packet header, then check the
selected slot's context and authenticate the entire message before parsing or
acting on plaintext. Reject unknown, malformed, stale and wrong-context packets
without mutating another slot. Keep request/response keys separate, sequence-zero
login semantics, exact sequence enforcement and exclusive in-place input-page
ownership. Protect against active session-ID collisions and stale-slot reuse;
RNG failure must fail closed rather than loop indefinitely. Reset timers only
on the documented authenticated activity, not rejected or unrelated traffic.

Poll expiry and reclaim each slot independently. Logout, failed proof, invalid
tag handling, crypto/resource failure, or timeout in A must never clear B's keys,
sequence or deferred transaction. Any retained invalid-tag closure policy applies
only to the addressed session, never the whole table. AP withdrawal invalidates
AP sessions while valid station sessions survive; station DHCP/hostname changes
invalidate affected station contexts while a valid AP session survives. Reboot,
profile generation/credential changes, unhealthy profile or global admission loss
legitimately invalidate all affected sessions. Document and test that distinction.

Do not equate an HTTP connection with a session: every ordinary port-80 request
currently closes its TCP connection. A normal successful TCP close must leave
the authenticated session usable on its next connection. For a lost/partial
reply, cancel only that transaction's delivery-dependent effect, reclaim its
transport buffers, and preserve other sessions. Already committed configuration
or accepted jobs remain subject to readback; session closure cannot undo them.

Route `finish_request(transaction, apply)` to the owning session/exchange and
retain a nonreused transaction identity across slot reuse. A delayed ACK/error
or expiry for an old occupant cannot complete/cancel a new occupant's work.
Session A's completion, close or logout cannot touch B's pending response.
Retain P15.5's complete-header/body TCP-ACK proof; FIN is not acknowledgement.

Keep board-wide provisioning and BrowserApi restart/network effects serialized
under their existing global receipt/gate. Do not duplicate them per session or
let B overwrite A's receipt. While one protected board effect is pending, other
sessions can use admitted reads/logout; conflicting writes refuse under the
existing revision/busy rules. Committing a new consumer profile can invalidate
all old-generation sessions, but must still respect matching-reply delivery,
restart/readback and no-rollback rules. Ordinary Config revisions must not
unnecessarily log out every other session.

Each browser/native client keeps its own volatile keys and local request queue.
No session state, password or private key belongs in cookies, local/session
storage, continuation URLs, logs or capability responses. Keep the Pi runtime's
existing operation/management lock and coordinator; this feature needs neither
multiple Pi session identities for one client nor a second runtime authority.

### 4. Prove behavior across sessions, carriers and revisions

Add behavior tests against the actual manager/crypto/HTTP implementation. Do not
stop at two mocked `RadioClient` objects or an array-size assertion. At minimum:

1. Two independent genuine handshakes and traffic-key sets coexist; interleave
   each client's sequence 1, 2, 3, and prove replies cannot be opened by the
   other key/session. Exercise two station clients at the same origin and an
   admitted AP/station pair. Test IPv4 and hostname contexts without rebinding.
2. During A's pending handshake, active session and unacknowledged response, B
   can progress within the selected pending/rate quotas and ultimately log in
   and use allowed resources without displacing A. If starts are serialized,
   prove the documented finite retry path and continued active-session access. A slow upload or reader occupies only
   its P15.5 transport slot. Exercise production dispatch through PicoHttpServer,
   ConsumerRadioApi and BrowserApi, including real AEAD on the critical path.
3. Logout, idle expiry, absolute expiry, handshake expiry, bad password, invalid
   tag, wrong sequence, unknown ID and allocation failure for A leave B usable.
   Use per-session clocks/activity; B's traffic must not refresh A. Include
   clock regression, sequence exhaustion, multiple normal TCP closes, FIN/RST,
   partial ACKs and timeout cleanup. Cover slot reuse and delayed old completions.
4. Fill pending/active quotas; one more start fails predictably without eviction
   or leaked handles/pages. Reclaim repeatedly by logout/expiry/failure and show
   capacity returns. Test a failed/abandoned login without clearing healthy
   clients. Do not invent unauthenticated "clear all sessions" recovery.
5. A and B read one revision, A saves, B's stale save receives the documented
   conflict with no journal/field/cursor change, then B reads the new revision
   and can submit an explicit fresh save. Both remain authenticated for ordinary
   config updates. Check complete station/hardware resources, profile-owned
   refusals and preservation of untouched settings under P15.1/P15.4.
6. A's deferred network/restart/setup response is unacknowledged. B reads, logs
   out, completes another reply or disconnects; none of those can deliver,
   replace or cancel A's receipt. Reverse the roles, including slot reuse.
   Cover global profile-generation invalidation and uncertain durable writes.
7. Sessions have distinct principals but share one transmitter authority. An
   owner/job held by A constrains B under existing claim/BUSY/STOP rules. A's
   logout or expiry does not abort or release that job or its scheduler state.
8. Actual native Pi traffic interoperates with the new Pico, and a browser can
   remain logged in beside the Pi session within the advertised capacity.
   Exercise engineering mTLS and consumer station/AP paths, strict discovery,
   fresh target/boot/generation binding and no fallback on refusal. Add all
   new capacity/version negatives to Pi configuration/runtime tests.
9. Two browser contexts use real session flows and conflicting-edit/readback
   behavior. Preserve each client's edits when the other changes configuration.
   If UI changes are needed, test desktop/mobile light/dark and apply the
   available Impeccable workflow. Keep source and generated radio bundle in
   sync using the existing pinned package/build process.

Capture the existing P15.7 failed-save/lost-session software sequence if it can
be reproduced with current fixtures, and retain the reported physical observation
without fabricating another live reproduction. P15.6 includes the independent
logout/expiry/capacity feedback required to make its feature usable. Leave broader
failed-save recovery, hostname persistence, settings consolidation and later
roadmap features separate. An abandoned client may consume a bounded session
until expiry under the selected policy; document that limit without silently
claiming P15.7 is closed.

### 5. Validation environment and exact-source compatibility

Use the documented retained Linux environment for C++ host checks; **do not
attempt local macOS C++ compilation/linking of WsprryPi**. Do not install an SDK
or tools as an incidental step. Reuse verified pinned Mbed TLS/lwIP/Arm tooling.
P15.5's record documents the Linux `pi` fixture account, Linux endpoint-driver
path and scratch `config/local` mount needed to avoid environment-only failures.
Keep containers hardware-free and networking disabled during tests where feasible.

Existing Pico commands, with valid local dependency paths supplied:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH="$MBEDTLS_SOURCE" \
  -DWSPRRY_PICO_TEST_LWIP_PATH="$LWIP_SOURCE"
cmake --build build-host --parallel 3
PHASE115_ENDPOINT_DRIVER="$PWD/build-host/endpoint_driver" \
  ctest --test-dir build-host --output-on-failure
python3 scripts/validate_wtp_contract.py
npm --prefix src/network/bootstrap_web test
```

Confirm the current target configuration and reuse or create an isolated firmware
build with the pinned SDK. Cross-link `WsprryPico` and `WsprryPico-StandaloneRF`;
retain the linked topology, RF placement and allocator checks. Run affected
ASan/UBSan with leak detection, including real multi-session crypto, the HTTP
transport, provisioning delivery and configuration paths. Report static RAM,
stack-usage output and estimated/observed heap honestly; a host pass or free-heap
estimate does not establish target fragmentation, RF timing or availability.

Existing Pi commands from its `src` directory on Linux:

```sh
make wtp-config-test wtp-api-test SUDO=
WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 make wtp-network-runtime-test \
  BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= JOBS=2
make wtp-network-interop-test SUDO= \
  PICO_SOURCE="$PICO_SOURCE" MBEDTLS_SOURCE="$MBEDTLS_SOURCE"
make wtp-config-interop-test SUDO= \
  PICO_SOURCE="$PICO_SOURCE" MBEDTLS_SOURCE="$MBEDTLS_SOURCE"
```

Recheck target names/options against the current Makefile before using them;
add appropriate UI/browser tests and affected Pi sanitizers. The variables above
must identify verified local sources, not unspecified dependencies to download.

Preserve all existing compatibility profiles (`legacy`, `extended`, `p152`,
`p153`) and retain the old published-current Pico pin
`ddb00dd7960373cec271f7816c0e1b10117416e9` as an explicit
historical regression row when adding the P15.6 current pin. Preserve P15.5
transport regressions and its exact implementation applicability. Run new Pi
against supported older single-session firmware and the new multi-session source;
exercise actual old Pi against new discovery for the documented work/refuse case.
Keep exact clean source guards and historical expectations. Do not repoint every
fixture to the new source or turn unsupported rows into silent skips.

For clean-source pin guards, first review/test the candidate, create an authorized
provisional Pico commit on `devel`, then use that exact clean commit for paired
Pi validation/pin updates. Preserve unrelated dirty work outside isolated test
checkouts rather than bypassing guards. Any later production-code repair needs
a new pin and affected paired retest. Record each tested pair; documentation-only
successors may be assessed separately and must not masquerade as a new tested
implementation pair. Refresh required Pi CI on the actual pushed head.

No connected board, GPIO/RF, flashing or installed-service work is authorized by
this software-only handoff alone. If the operator supplies a current connected
setup and finite limits, follow that authorization and repository hardware rules,
record exact identity/settings/firmware/clock/mode/RF path, and restore the setup.
Otherwise leave physical phone/Mac concurrency and target resource/RF acceptance
explicitly open. Historical P15.5/Phase 11.5/Phase 14 results do not qualify the
new session/allocator layout. Keep shared-passphrase trust, HTTP page substitution
and active-endpoint offline-guessing limits explicit; no general security
qualification or protocol redesign is implied.

### 6. Adversarial review, repair, reassessment and publication

After implementation and normal validation, switch to an adversarial assessment.
Try to break session isolation, slot reuse, crypto/PSA lifetime, rate/quota
admission, global delivery serialization, authenticated identity, malformed
header selection, sequence/nonces, scope invalidation, conflicting writes,
API/management version handling and the test/evidence claims themselves.

Record each actionable finding with severity, actual trigger, affected file,
repair and regression evidence. Fix findings, rerun affected checks, and conduct
another assessment. Repeat until no actionable finding remains within the
accepted software scope. Distinguish the executor's own review from independent
review; do not call a self-review independent. Do not label an unrun physical
case a passing test or silently waive a required software assertion.

Update a durable P15.6 acceptance record, current API/protocol/session/capability
documentation, compatibility matrix and development indexes. Keep historical
acceptance files bound to their original results. Mark P15.6 complete only for
the proven scope; leave P15.7 and later roadmap items open. Record concrete
P15.14 operator-doc and screenshot follow-ups; do not publish to the independent
operator-documentation repository incidentally.

Commit only scoped changes in each affected repository on `devel`, push to each
`origin/devel`, and independently compare local HEAD with `git ls-remote`.
Preserve unrelated edits and concurrent work. Report actual CI/check results,
remaining exclusions, dirty paths and remote state. Do not create a PR or release
unless the operator separately requests one.

Return a handoff packet to the operator containing exact implementation and
published SHAs for both repositories, source-pair/pin/CI identities, commands and
results, all findings/repairs/reassessments, documentation impact and limitations.
The operator will bring that packet back to the originating conversation for
its requested post-execution adversarial review. That follow-up review must
inspect the actual completed code/evidence, repair any actionable findings,
rerun affected checks and reassess, then commit/push its scoped repairs before
reporting. This prompt's preparation does not claim that later review occurred.
