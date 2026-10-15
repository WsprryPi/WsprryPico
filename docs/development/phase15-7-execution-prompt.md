# P15.7 handoff for login and failed save recovery

Execution evidence is recorded in [P15.7 recovery](phase15-7-recovery.md).
The prepared baseline below remains historical.

Status: **prepared only; not executed**. P15.7 remains pending. This handoff
records a source review and instructions for a separate executing conversation.
It supplies no new implementation, test, target or RF acceptance. The executor
must implement, validate, review, repair, reassess, commit and push the scoped
solution on **devel**.

## Lead repository and current baseline

**WsprryPico leads.** It owns the consumer session table, authentication and
expiry, HTTP delivery, the standalone browser and transactional setup results.
WsprryPi is the coordinated client repository: its native consumer client,
existing management coordinator, UI and compatibility checks must support the
selected recovery contract. A Pi-only change cannot recover an abandoned Pico
session for a standalone browser.

Source review on 2026-10-15 found both checkouts on devel with clean working
trees, and HEAD equal to their local origin/devel tracking refs:

| Repository | Reviewed HEAD | Relevant recent changes |
| --- | --- | --- |
| WsprryPico | fd094b1a8f209036e2656df76577776f60bd1802 | P15.6 implementation 792b5b2f60e381a6bd8e7a7726eeffe24fc08519; acceptance b349794; separate review fd094b1 |
| WsprryPi | 1090d1af6095757fec039e39e09fc5ad70a5706f | P15.6 adoption 748cb42; browser-fixture repair 95b0886; concurrent RP1 documentation merge preserved |

These are orientation identities, not instructions to reset either checkout.
Remote tips were not independently refreshed for this prompt. Recheck actual
branches, remotes, dirty paths and intervening changes before execution.

### Source review findings

1. **P15.6 already supplies independent sessions.**
   Pico src/network/consumer_radio.hpp defines three total slots, one pending
   login, a 30-second handshake, five-minute idle and fifteen-minute absolute
   expiry. consumer_radio.cpp preserves other sessions during logout, expiry,
   context invalidation and addressed failures. Capacity, pending and rate
   refusals have separate codes. Increasing the pool or shortening expiry does
   not satisfy P15.7.
2. **A lost reply can leave an occupied slot without a usable client.**
   bootstrap_web/radio-client.js clears local traffic state on request failure;
   login also clears local state before attempting a new handshake. A normally
   completed HTTP close deliberately preserves the server session. The genuine
   P15.6 regression in tests/consumer_sessions.test.mjs demonstrates one durable
   save, a deliberately lost reply, local key clearing, successful readback by
   another client, and subsequent relogin consuming the third slot. A further
   login then refuses. A lost start or finish reply has a different lifecycle
   and must be traced separately.
3. **Current logout cannot recover a client whose traffic keys are gone.**
   It is an authenticated, consecutively sequenced logical request. The public
   consumer handler currently exposes identity/start/finish/request, with no
   separately authenticated retirement or replacement operation. The session
   ID in the CR01 header is only a selector; it is not proof of authority.
4. **The standalone UI mixes status and save recovery.**
   src/network/web/app.js action catches an error, calls refresh and appends
   generic checked/unknown status wording. refresh normally reads capabilities,
   pins and status, not saved configuration. Login calls refresh(!dirty), so a
   preserved dirty form can retain its old revision without fresh configuration
   readback. Neither a new login nor a healthy status GET proves a save outcome.
   This is a P15.7 workflow gap, not evidence that P15.6's accepted isolation
   failed.
5. **Application rejection and transport uncertainty are different.**
   An authenticated inner 400/409/412 response can leave the client authenticated.
   Outer transport, framing, authentication or response failures clear its keys.
   post and request currently collapse several outer errors into authentication
   required. Preserve useful codes without treating an unauthenticated error
   message as authoritative proof that a write did not occur.
6. **Commissioning already has stronger result receipts.**
   bootstrap_web/radio-setup.js marks a submit sent before dispatch and never
   resends that attempt. checkSetup compares device, generation and request
   digest, including unsafe-number refusal. web/app.js carries only kind, device,
   expected generation and digest in a bounded continuation fragment. The
   current terminal-result UI clears consumerSetupDirty and refreshes the form;
   a failed result needs a draft-preserving path. Keep the encrypted submit
   payload out of continuation URLs and persistent storage.
7. **Delivery and durable persistence have distinct commit points.**
   src/network/pico/bootstrap_server.cpp starts a setup trial only after the
   matching complete encrypted reply is acknowledged; lost submit delivery
   cancels that pending trial. BrowserApi also has transaction-bound deferred
   restart/network actions. An ordinary configuration save can already be
   durable when its reply is lost. Recovery must handle both situations and
   cannot roll back a committed write by closing a session.
8. **Pi needs coordinated recovery, not another coordinator.**
   src/wtp_integration/consumer_radio.cpp clears native state on uncertainty,
   returns management_outcome_unknown for a mutation and
   consumer_session_unconfirmed for a read, and performs no mutation replay.
   src/wtp_runtime_bridge.cpp serializes management through operation_mutex,
   idle_management and selection identities. Configuration/resource coordinators
   retain exact identity, revisions and mutation_attempted evidence.
9. **Pi already preserves drafts and invalidates editor contexts.**
   WsprryPi-UI/data/wtp-management.js requires loading saved settings/resources
   after uncertain writes, but its capacity feedback still offers another
   client's logout or idle expiry. Browser-to-Pi response loss can leave a
   perfectly usable native session in the runtime; read connection state before
   replacing it. A Pi browser tab is not a separate Pico session identity.
10. **Discovery contracts are strict and versioned.**
    Pico management.cpp advertises transmitter-management/2. Pi validates closed
    management/1 and management/2 documents, exact operations, limits, types,
    identity, carrier and profile generation. Adding fields or operations to
    either frozen shape breaks compatibility. Recovery must also be discoverable
    before ordinary authenticated management can be reached at full capacity.
11. **The original physical observation remains historical.**
    The checklist records an earlier single-session radio_session_busy after a
    blocked callsign save. P15.6's genuine software test shows a profile-owned
    callsign refusal preserves authentication. Do not assert that this explains
    the original physical sequence, or implement callsign-only saving here;
    that separate behavior belongs to P15.9 after P15.8.

Read the [P15.6 acceptance and separate review](phase15-6-sessions.md), the
[Consumer-Radio contract](../protocol/Consumer-Radio-v1.md), the
[browser API](../browser-api.md) and the
[Phase 15 checklist](../implementation-plan.md#phase-15-operator-review-punchlist)
alongside this review. Historical pass counts are retained evidence for their
exact sources; they were not rerun to prepare this prompt.

## Prompt for the executing conversation

Implement **P15.7 — recover login cleanly after a failed save or lost session**.
Work on **devel** in /Users/lbussy/GitHub/WsprryPico as the lead repository and
/Users/lbussy/GitHub/WsprryPi for necessary client, coordinator, UI, compatibility
and documentation changes. When this prompt is executed, carry the work through
implementation, tests, adversarial review and repairs, reassessment, scoped
commits, pushes and a final evidence packet. Do not return after another plan
or after changing only error messages.

### 1. Establish the current state and reproduce the failure classes

Read applicable AGENTS.md files in each affected repository. In Pico read
README.md, CONTRACT.md, docs/architecture.md and docs/development/README.md.
Read P15.1 through P15.6's current contracts/acceptance records and Pi's
docs/simulated-backend.md before application-level simulated tests.

Inspect branches, status, staged/unstaged diffs, remotes, recent history and
component instructions before editing. Keep work on devel; preserve unrelated
changes and concurrent commits without reset, stash, destructive cleanup or
force push. Refresh the source review where the baseline has moved. Isolated
historical checkouts are for exact-source validation, not implementation branches.

Start with genuine browser-client/production-HTTP/session/Mbed TLS fixtures.
Demonstrate and record separate cases for:

- Local browser validation failure: no request and no session change.
- Authenticated API rejection or revision conflict: no unintended commit and
  no needless logout.
- Lost start reply, lost finish reply, lost request before dispatch, lost reply
  after dispatch/commit, and malformed or unauthenticated reply.
- Browser-to-Pi loss versus native-Pi-to-Pico loss.
- An abandoned client followed by repeated login until all three slots are
  occupied; repeat with another healthy browser and native Pi still active.
- Pending-login quota, idle/absolute expiry, AP withdrawal, station address or
  authority change, profile-generation change and reboot.

Use counters and authoritative snapshots to establish which calls reached a
handler and which writes committed. Do not simulate an uncertain commit merely
by throwing before the mutation handler. Retain the old physical observation
as history unless a currently authorized physical setup reproduces it.

### 2. Settle and document an authenticated recovery design

Record the selected state machine, wire/discovery policy, resource budget and
acceptance assertions in docs/development/phase15-7-recovery.md before the main
implementation. Prefer the smallest design that satisfies these requirements:

1. Recover the affected login without rebooting, changing saved settings or
   waiting for a five-minute idle expiry. Prove recovery at full active capacity
   and after an abandoned pending handshake. State a finite operation/deadline
   bound under a healthy transport; tests must not advance time to session
   expiry to obtain a free slot.
2. Ordinary application errors retain a healthy session. For uncertain encrypted
   traffic, retire or replace the affected session safely instead of guessing
   whether its next sequence is current. Never reuse a key/nonce pair, rewind
   traffic sequence or replay the interrupted application request.
3. A known lost session should be recoverable without displacing unrelated
   healthy sessions. Consider a narrowly scoped volatile retirement proof or
   a fresh password-authenticated recovery exchange. If separate recovery
   material is retained after traffic keys are cleared, define its independent
   purpose, lifetime, erasure and binding; it cannot authorize application work.
4. Recovery authentication must still be possible when normal session and
   pending quotas are full. A design that logs in normally before reclaiming a
   slot is circular. Any additional proof workspace must be fixed, bounded,
   rate-limited, short-lived and accounted for in target memory and PSA handles.
   It is not a fourth active session or an unbounded recovery queue.
5. Specify the fresh-page/native-process-loss case where every prior volatile
   client secret is gone. The shared Wi-Fi passphrase proves membership, not
   unique ownership of an old tab. If explicit password-authenticated operator
   retirement/replacement of an occupied slot is needed, make its scope visible
   and deliberate, authenticate before altering that slot, and distinguish it
   from automatic self-recovery. Never silently evict an unrelated healthy
   client. Do not claim to identify an abandoned client from an IP address,
   user agent, tab label or public session ID.
6. Failed, malformed, replayed, expired, wrong-password, wrong-device, wrong-boot,
   wrong-generation or wrong-interface recovery attempts cannot clear sessions,
   refresh their timers, alter settings, or gain private reads. Preserve exact
   Host/Origin/interface checks and absence of CORS, cookies and redirect follow.
7. Bind any proof to its exact purpose, current device, boot, profile generation,
   target session/replacement scope, challenge and authority/interface as
   appropriate. Use reviewed primitives and separate key/nonce domains. Consume
   proofs once, bound RNG failures and handle delayed old completions and reuse.
   A public selector or claimed knowledge of a session ID is never authorization.
8. A lost recovery reply is itself uncertain. Define idempotent retirement or
   safe result reconciliation using the same identity; do not leak replacement
   sessions, loop indefinitely or escalate to closing all clients after each
   failed acknowledgement. Test both pre-effect and post-effect response loss.
9. Preserve three total ordinary session slots, active and pending combined,
   with at most one pending login, and the existing expiry policy unless a
   separately justified contract change is required. Increasing capacity,
   shortening timeouts, waiting for another
   operator, suggesting restart, or adding unload best-effort logout alone
   does not meet this slice.

Keep existing Consumer-Radio/1 traffic and vectors compatible where possible.
If recovery adds a wire surface, define its exact schema, admission, proof,
errors, limits and vectors as a separately versioned extension. Do not silently
change existing transcripts or frozen management/1 and management/2 documents.
If discovery must evolve, version it explicitly and update Pi's strict
validators and capability references together. Define a bounded way to discover
recovery support before normal login without trusting public metadata as proof
of device identity or authority.

New clients must retain supported old firmware behavior and state honestly when
that firmware lacks recovery. Do not probe destructive alternatives, downgrade
authentication or blindly switch carriers. Old Pi against new Pico must have
an explicit tested work/refuse result. Unsupported recovery must not disable
otherwise supported old-firmware reads and saves.

Keep shared-passphrase trust, unauthenticated HTTP page delivery and the existing
active-endpoint offline-password-guessing limit explicit. This slice does not
claim a PAKE, unique client identities or unrestricted security qualification.

### 3. Implement session recovery without changing application authority

Retain Pico's one JobService, scheduler, configuration/profile journals,
transmitter owner and serialized mutation authority. Keep core-0 networking
and crypto separate from core-1 RF timing. Reuse P15.5's two bounded HTTP tasks,
absolute deadlines, fair writes and transaction-specific complete-ACK delivery.

Retirement/replacement must reclaim the selected slot's keys, pending proof,
transport/exchange state and deferred effects without touching another session.
Closing authentication never aborts/releases a loaded, armed or running job,
clears STOP/watermarks, resumes recurrence, changes output or bypasses BUSY.
Preserve admission during allowed station operation and the existing AP/RF
guards. Do not use Wi-Fi/profile reset or factory recovery as session cleanup.

Define the race between session retirement and a pending application/setup
reply. A retirement request must not be mistaken for delivery of that reply.
Cancel only still-pending delivery-dependent effects; preserve already durable
settings and already accepted jobs. Prevent stale ACKs, FIN/RST, timeout or an
old recovery proof from acting on a reused slot or a new board-wide receipt.
Retain the single global setup/restart receipt and its existing safe-commit
gates. Do not create per-session copies of board-wide provisioning authority.

Pi must use its existing runtime management operation lock, admission and
selection identities. Preserve its transient credential wiping. On browser-to-Pi
loss, inspect the existing native connection instead of automatically creating
another Pico session. Keep successful native connections usable; coordinate
explicit recovery/disconnect selection with editor-context invalidation.
Management remains independent of WTP connectivity when host admission permits.
Engineering mTLS remains supported; USB, raw Plain/TLS WTP and BLE do not gain
JSON management. Avoid changes to reusable WTP-Client or unrelated components
unless the defect actually belongs there and the approved scope permits it.

### 4. Reconcile saves and preserve drafts

Give the browser and Pi UI explicit states for authenticated, rejected,
connection/session unconfirmed, recovery required/in progress, saved-state
readback required, conflict and ready for a new explicit save. Separate observed
facts from unknown outcomes. Preserve useful typed error codes and safe action
feedback close to login/save/recovery controls; avoid the generic status-unknown
loop. Do not turn every 409/429/503 into a wrong-password diagnosis.

For ordinary config, schedules, station and hardware writes:

- Record a bounded in-memory attempt context before sending: exact target,
  relevant boot/profile/carrier/selection, revision, intended changes and sent
  state. Keep secrets volatile and scrub them according to existing policy;
  preserving a draft does not authorize persisting credentials.
- On ambiguity, send the mutation at most once. Invalidate write eligibility and
  stale revisions/context. A healthy status response or a new login alone cannot
  re-enable Save.
- Authenticate/recover, then read authoritative saved configuration/resources
  and fresh revisions under a consistent target context. Show saved versus draft,
  and saved versus active/null state, without overwriting the draft. Preserve
  P15.1 field preservation, password-null semantics and P15.4 restart/fault rules.
- Do not claim a historic attempt committed merely because current fields match;
  concurrent edits can make attribution unknown. Ordinary writes lack the
  commissioning request-digest receipt. State what the current saved state proves,
  expose conflicts, and require review before a new explicit save.
- Require an explicit operator action for any subsequent mutation with a fresh
  revision. No auto-resubmit, hidden merge, strategy switch, restart, transmission
  or carrier fallback is allowed during recovery.

For authenticated network/station commissioning:

- Reuse the existing sent-once setup attempt and device/generation/request-digest
  receipt. Preserve that receipt through login recovery and an origin transition.
  Never put passwords, keys, revocation proofs, encrypted submissions or arbitrary
  request bodies in URLs, browser storage, cookies or logs.
- Handle loss before submit, lost submit delivery, accepted trial, explicit
  terminal failure, committed profile, restart and changed password separately.
  Authenticate with the credentials valid for the observed profile; never try
  passwords automatically or classify a failed login as a failed save.
- Keep generation comparisons exact for uint64 values. Mismatched device,
  malformed/different digest, unsafe numeric rounding, later generations or
  contradictory evidence remain unconfirmed/conflict as appropriate.
- Terminal failure must leave correctable station/network drafts intact while
  allowing a new explicit attempt. Successful verification may refresh confirmed
  saved values but must not erase unrelated dirty fields. Discard/reload remains
  explicit. Restored receipt-only continuations can check results, not resend.
- A setup result/status request can itself trigger an existing delivery-bound
  restart. Preserve the actual commit/delivery rules; recovery must not invent
  an acknowledgement or label an automatic device transition as a second save.

Do not implement P15.8 WSPR encoding, P15.9 independent identity-field saving,
P15.10 hostname editing, P15.11 form consolidation, P15.12 page titles, P15.13 RF
qualification or P15.14 documentation publication as incidental changes.
Regression coverage may exercise context changes without delivering those features.

Use the available **Impeccable** skill before UI changes, as Pi AGENTS.md
requires. Preserve the incumbent design and use its hardening guidance for
errors, concurrent requests, draft retention, focus and accessibility.
Render the actual shipped Pico and affected Pi UI with desktop/mobile sizes and
light/dark preferences; Pico currently uses light styling in both preferences.
Exercise keyboard operation, readable recovery feedback, disabled write controls,
long errors and overflow. Follow the skill's bounded review/fix/confirmation
passes; do not redesign the applications. Regenerate checked-in bundles with
the pinned build process and verify source/bundle agreement.

### 5. Required adversarial behavior coverage

Add regressions that fail on the reviewed baseline and use real crypto and
production HTTP/bootstrap dispatch for critical cases. Extend the existing
consumer_session_driver, consumer_sessions.test.mjs, browser harness, portable
manager/crypto tests and Pi native/browser interoperability rather than relying
only on mocked UI objects or hand-built happy-path payloads.

The current consumer_session_driver links the real HTTP/session/AEAD/API path
but does not instantiate PicoBootstrapServer or drive its commissioning trials.
Do not describe its ordinary-save coverage as production commissioning
acceptance. Add or extend an appropriate hardware-free harness to exercise the
actual bootstrap/setup dispatcher and delivery/result logic, with explicit
platform-boundary doubles, for the commissioning assertions below.

| Case | Required evidence |
| --- | --- |
| Rejected save | Local validation sends nothing; authenticated server refusal/conflict changes no forbidden state and keeps healthy authentication |
| Lost reply around a durable write | Failure before dispatch and after commit are distinguished by handler counters/readback; one mutation only; drafts survive |
| Full pool recovery | Three occupied slots, including healthy browser/native clients; affected client recovers without reboot/idle-time advance and without silent eviction |
| Lost handshake | Lost start and finish replies, abandoned pending slot and full ordinary quotas; bounded recovery with no orphan accumulation |
| Fresh page or restarted native process | No old volatile secrets available; documented explicit authenticated recovery path, with exact impact visible before retirement |
| Recovery reply loss | Effect not reached versus effect completed; safe repeat/result check; no duplicate replacement session or broad cleanup |
| Authentication attacks | Bad proof/password, guessed selector, replay, unknown/retired ID, cross-client substitution, stale boot/generation, altered scope, wrong Host/Origin/interface and oversized/truncated/duplicate-field input refuse safely |
| Recovery races | Two requests for one target, recovery versus login/logout/expiry, slow earlier upload, slot reuse, delayed ACK/FIN/RST and unrelated successful reply cannot affect a later occupant or board receipt |
| Healthy peers | Other clients keep keys, sequences, timers, pending delivery and admitted reads; invalid attempts cannot prolong victims or refresh global lifetimes |
| Ordinary save reconciliation | Fresh config/resource revisions with draft preserved; stale/conflicting writes refuse; matching current values do not fabricate historical attribution |
| Commissioning reconciliation | Network/station trials and receipts; pre/post-commit loss, terminal failure, generation precision, password change, reboot, AP/station continuation and wrong-device refusal |
| Pi runtime continuity | UI-to-Pi loss with native session alive; Pi-to-Pico loss; explicit selection changes; host busy/unresolved-output refusal; no extra coordinator or automatic reconnect replay |
| Resource failure | Allocation, RNG and crypto failures, repeated recover/logout cycles and quota abuse reclaim buffers/handles; shared PSA/TLS owner survives |
| Job authority | Loaded/armed/running/failed states and unknown output preserve original owner, STOP, journal and scheduler policy; recovery never sends RF/job control |
| Compatibility | Exact old/new source pairs, old firmware without recovery, strict discovery/version negatives and documented old-client work/refuse behavior |

Test genuine crypto proofs across the browser Noble, Pico Mbed TLS and native
Pi OpenSSL implementations for any new extension. Add fixed and negative vectors
when crypto/wire behavior changes; preserve existing Consumer-Radio/1 vectors.
Use deterministic clocks/counters to verify replay/deadline/resource properties
and real browser contexts for the visible workflow. Repeated recovery must stay
bounded in RAM, handles, slots, wire calls and elapsed time.

### 6. Validation and exact source pairs

Use documented deterministic, hardware-free checks. Reuse retained Linux
environments and verified pinned SDK/Mbed TLS/lwIP/Arm dependencies. **Do not
attempt local macOS C++ compilation or linking of WsprryPi** unless the operator
explicitly lifts that restriction. Do not install tools/download an SDK as an
incidental step. Confirm target names/options against the current build files.

Pico host examples from the existing P15.6 record, with verified local dependency
paths supplied and an isolated build directory:

    cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
      -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
      -DWSPRRY_PICO_TEST_MBEDTLS_PATH="$MBEDTLS_SOURCE" \
      -DWSPRRY_PICO_TEST_LWIP_PATH="$LWIP_SOURCE"
    cmake --build build-host --parallel 3
    PHASE115_ENDPOINT_DRIVER="$PWD/build-host/endpoint_driver" \
      ctest --test-dir build-host --output-on-failure
    python3 scripts/validate_wtp_contract.py
    npm --prefix src/network/bootstrap_web test
    npm --prefix src/network/bootstrap_web run build

Run the complete host suite for the candidate and affected ASan/UBSan checks with
leak detection. Include consumer sessions/crypto, HTTP delivery, bootstrap/owner
transactions, management discovery, config updates and application resources,
plus all added recovery tests. Retained P15.6 affected groups include
consumer_sessions, consumer_radio_tests, consumer_radio_crypto_tests,
http_server_tests, bootstrap_slot_tests, bootstrap_join_tests,
owner_claim_http_tests, config_updates and management_carrier_tests.

Cross-link WsprryPico and WsprryPico-StandaloneRF when firmware changes. Reuse
the verified target configuration or the documented pico2-w preset after checking
its actual SDK/profile inputs; preserve RF placement, allocator and linked image
checks. Budget new recovery metadata, retained proof material, transient proof
crypto, simultaneous HTTP pages and the 32 KiB authority reserve. Report static
RAM, stack-usage output and estimated versus measured heap distinctly.

The P15.6 record describes Linux fixture user pi, a Linux endpoint-driver path,
scratch config/local mount and writable external build/log outputs; retain those
requirements. Source mounts can be read-only, but CTest logs, generated fixture
JSON and other declared outputs need writable scratch. Use no device mounts and
disable container networking for tests where feasible. Do not mistake fixture
startup/output-permission failures for assertions or relax deadlines to hide them.

Pi examples from its src directory on Linux:

    make wtp-config-test wtp-api-test SUDO=
    WSPRRYPI_DISABLE_HARDWARE_ACCESS=1 make wtp-network-runtime-test \
      BACKENDS=simulated ANCILLARY_GPIO=0 SUDO= JOBS=2
    make wtp-config-interop-test SUDO= \
      PICO_SOURCE="$PICO_SOURCE" MBEDTLS_SOURCE="$MBEDTLS_SOURCE"
    make wtp-network-interop-test SUDO= \
      PICO_SOURCE="$PICO_SOURCE" MBEDTLS_SOURCE="$MBEDTLS_SOURCE"

Include affected Pi sanitizers, WsprryPi-UI/tests/wtp_management_test.js,
wtp_ui_test.js, wtp_resources_interop_test.js, wtp_network_ui_integration_test.js
and src/tests/network/consumer_browser_interop.js as applicable. Use the existing
opt-in actual-browser fixtures and their documented dependency/output setup;
tests/consumer_sessions_browser.mjs currently assumes a named Linux image and
scratch layout, which must be verified/adapted to the candidate rather than
silently exercising a stale executable.

Preserve the six existing compatibility rows: legacy, extended, p152, p153,
p154 and current. Retain P15.6's clean implementation
792b5b2f60e381a6bd8e7a7726eeffe24fc08519 as a separate historical row when advancing
current to P15.7. Add an explicit profile/pin and retain historical expectations;
do not repoint all rows, skip old cases or weaken exact-source cleanliness guards.
Test new Pi against supported old Pico and new Pico, and the published P15.6 Pi
against new Pico for its documented work/refuse result.

To satisfy clean-source guards, first review/test Pico, make an authorized
provisional scoped implementation commit on devel, then validate Pi against
that exact clean source in an isolated checkout and update pins. Any production
repair requires a new source identity and affected paired retest. Distinguish
tested implementation SHAs from later documentation-only publication heads.
Inspect the required CI configuration and refresh results on the final pushed
Pi head; retain failures and unchanged reruns honestly.

This prompt alone authorizes software work, not board access, flashing,
GPIO/RF, installed-service changes or arbitrary host administration. If the
operator supplies a current connected setup and finite test limits, follow that
authorization and the repositories' hardware rules, identify boards, firmware,
clock, mode and RF path, preserve/restore settings, and keep physical evidence
separate. Without that setup, leave the original physical reproduction, actual
phone/Mac transport, target heap/stack high-water and RF acceptance explicitly
open. Historical bench arrangements do not establish a current setup.

### 7. Adversarial review and repair loop

After implementation and normal validation, perform an adversarial code and
evidence assessment. Challenge whether:

- The recovery proof actually authenticates before reclaiming anything and
  remains usable when the ordinary pool is full.
- A shared-passphrase peer is being misrepresented as the original tab owner.
- New proof keys/nonces, transcript domains, expiry, RNG, allocation and PSA
  ownership fail closed, and rejected traffic cannot revoke or keep victims alive.
- Lost recovery replies, repeated clicks, selection changes and slot reuse can
  leak slots, act on a new occupant, or deliver/cancel the wrong deferred effect.
- A status GET or relogin incorrectly unlocks saving before authoritative
  configuration/receipt reconciliation.
- Drafts, saved/active/null state, conflicts, exact revisions and commissioning
  identity survive the real failure sequence without any mutation replay.
- UI/native bridges obscure error provenance, bypass the existing coordinator,
  weaken old/new compatibility or change RF/job authority.
- Tests use the actual changed client, bundle, native binary, HTTP/bootstrap
  dispatcher and crypto at the recorded source pair, and prove their claims.

Use an independent reviewer/context when available and authorized; clearly label
the executor's own assessment and any independent assessment. Do not describe
self-review as independent. Record each actionable finding with severity, trigger,
file, repair and regression evidence. Fix it, rerun affected checks, then conduct
a new adversarial assessment of the repaired result. Repeat until no actionable
finding remains within the accepted software scope. Do not waive required
software cases merely because a larger suite passed. Keep unperformed physical
qualification explicit instead of treating it as a passing software assertion.

### 8. Documentation, commit, push and final packet

Update current protocol/API/recovery documentation, compatibility records,
development indexes and the Phase 15 checklist. Preserve historical P15.1-P15.6
acceptance claims and original source identities. Mark P15.7 complete only for
the acceptance actually demonstrated, with physical limits alongside it. Leave
P15.8 and later items pending.

Inspect /Users/lbussy/GitHub/WsprryPi-Docs read-only, refresh its actual path and
instructions, and review docs/User_Interface/Setup/Transmitter/index.md,
especially its Pico development controls and standalone settings sections.
These currently retain the earlier engineering-only management instructions.
Record exact P15.14 instructions/screenshots still needed
for rejected/uncertain saves, recovery/retirement impact, old-firmware limits,
draft preservation, fresh readback, password changes and origin continuation.
Do not edit or publish that independent repository without authorization.

Review each affected repository's complete diff, UI/component portions, staged
content and whitespace. Commit only scoped work on devel, preserving unrelated
edits and concurrent changes. Push to each affected origin/devel without force.
Verify local HEAD independently against git ls-remote for each pushed branch,
and report remaining dirty paths. If Pi needs no source/documentation change,
report that evidence and its exact tested revision; do not manufacture an empty
commit. Do not create a PR or release unless separately requested.

Return a self-contained packet containing:

1. Implemented operator behavior, lead/companion responsibilities and the chosen
   authenticated full-capacity recovery policy, including its explicit impact.
2. Exact implementation and published SHAs, tested source pairs, compatibility
   pins/rows, branch/worktree state, push output and independent remote parity.
3. Commands/results, actual suite counts, sanitizers, cross-links, fresh CI
   run/head identity and actual-browser/Impeccable workflows and screenshots.
4. Original failure reproductions, handler/commit counters, saved-state/draft
   evidence, every adversarial finding/repair and final reassessment.
5. A Documentation Impact section listing updated, considered unchanged and
   still-required operator documentation, plus precise limitations.

The operator may return that packet to the originating conversation for a
separate post-execution adversarial review. Supply enough source and evidence to
support it; the executor's completed review does not imply that later review has
already occurred. The later reviewer must inspect the completed changes, repair
actionable findings, rerun affected checks, reassess and commit/push any scoped
repairs before reporting.
