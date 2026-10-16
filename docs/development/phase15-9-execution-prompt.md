# P15.9 handoff: save valid fields independently of transmit readiness

Overall status: **in progress pending its WsprryPi portion under release
checklist step 15**, by operator direction. The originating conversation
prepared this source review and prompt without executing the implementation.
The separately saved WsprryPi-coordinated execution handoff has been withdrawn
by operator direction. This technical review remains a reference; changing the
tracking status does not itself execute implementation or establish acceptance.

## Lead repository and current evidence

**WsprryPi coordinates; WsprryPico leads its implementation.** Pico owns the
browser forms, complete-config validation,
configuration journal, transactional consumer setup, effective profile overlay,
standalone scheduler and local execution admission. Pi already produces partial
edits for existing complete settings; moving this work to Pi would leave the
standalone/captive/browser problem unsolved. Prefer an additive Pico solution
that keeps existing Pi release behavior compatible. Native Pi adoption is a
separate coordinated companion scope if necessary or explicitly selected.

Reviewed on 2026-10-16, with branch heads independently checked by
`git ls-remote`:

| Source | Reviewed identity | State and meaning |
| --- | --- | --- |
| Pico devel | `4e96f0e71a93a529c01e8ec202a0f39422322c33` | Clean before this documentation task; published P15.8 report/probe head |
| P15.8 Pico implementation / interop pin | `804e8a06585ec5a0e650e69fcd71ada398b6cc9f` | Tested product source; later Pico commits through the reviewed head add documentation/probes |
| Pi release devel at initial review | `d93c75c4f1490df9108856403710e692b9c2d3dd` | Read-only reference; matched origin/devel; unrelated release work listed below |
| Approved P15.8 Pi companion | `6d5e73430bfbacdb8cfc29c3fe41089aa8ae5fcb` | Clean isolated checkout at `/private/tmp/wsprrypi-p158/source`; published on `codex/p15-8-wspr-type23`, unmerged |
| P15.8 Pi native product implementation | `41c1dbd42620da6d5595b3ca0171c15ad6c9ee5f` | Companion product changes; later companion commits add tests/pins/evidence |
| Pi companion base / frozen release probe | `a2437d1bf026e91ea95ac7e2a7a0101e3c4f11a1` | Historical accepted comparison, not current Pi devel |

At initial review, primary Pi had an unrelated modified
`release_tools/Release Punchlist.md` and untracked
`docs/development/item13-integrated-impeccable-evidence/` and
`docs/development/item13-integrated-impeccable-review.md`. Other release work
committed them during handoff preparation. At the late publication check,
primary Pi was clean at `e3e5008413c4bdb4e2838c9a17bcd5ad4b37c496`, one commit
ahead of observed origin/devel `b85ba90c9a4c862ad4e89ff1d86b1217342d066a`.
The complete difference from reviewed `d93c75c` contains only release checklist
and review/evidence documentation; the reviewed application code is unchanged.
Nothing in Pi was edited or pushed by this preparation task.

The new Pi release checklist item 14 explicitly retains separately authorized
P15.8 integration, affected UI/documentation review and integrated-head CI before
Beta 1 candidate freeze. It does not authorize P15.9 changes or companion
integration. Preserve that gate and refresh all identities, release decisions
and dirty paths before execution. These are orientation pins, not instructions
to reset or roll back either repository.

The [P15.8 record](phase15-8-wspr-type23.md) retains 196 host tests, 27 checks
in the sanitizer build, both firmware links and the successful
[twelve-job companion CI run](https://github.com/WsprryPi/WsprryPi/actions/runs/38950723473).
Preparation verified that run's head is exactly `6d5e734` and all twelve jobs
succeeded. Local implementation results are recorded evidence, not fresh runs
in this preparation task. The operator accepted bounded software roadmap
closure; Pi release integration, physical qualification and the separately
requested originating P15.8 review remain separate. Do not label them complete
as a side effect of P15.9.

### Source review and implications

Paths below are relative to Pico unless prefixed with Pi. These are inspected
source findings, not a reproduction of the operator's original physical failure.

1. **The symptom needs a precise reproduction.**
   `src/network/web/index.html` has separate `config`, consumer network,
   consumer station, `message-form` and raw-job forms. The QRSS/FSKCW/DFCW
   controls are not currently children of the station form. Station/config
   inputs and schedules nevertheless have native required constraints. The
   consumer identity form requires both callsign and locator. Reproduce the
   actual shipped page and distinguish native validation, JavaScript refusal,
   firmware refusal and a lost-session outcome. Do not assume a nested-form bug
   merely from the operator's description of the second block.
2. **Disabled configuration still requires complete station data.**
   `src/standalone/config.cpp:93` requires Config v1's version, enabled, complete
   station, Wi-Fi object and schedule array. `valid_station_details` is required
   even with enabled false. Empty schedules are valid only when disabled;
   schedule overlap/expiry, credentials and complete operational pin plans have
   their own checks. `Config{}` is an internal default, not a persistable blank
   station. Adding placeholders or deleting parser checks would blur storage
   and execution validity.
3. **Partial update already exists, but its result must be complete.**
   `src/application/config_update.cpp` builds a candidate from known changed
   leaves, preserving omitted values, explicit false/zero and password-null
   semantics. `src/network/api.cpp:437` enforces revision, idle and storage
   checks, then complete validation before one scheduler/config journal commit.
   Merge requires an existing configuration. The original paths remain atomic;
   they do not offer per-field partial success or initial incomplete drafts.
   See [P15.1 update semantics](configuration-updates.md).
4. **Storage reload is as strict as save.**
   `src/standalone/storage.cpp:118` parses journal bytes through `parse_config`;
   `Store::save` reserializes and reparses before append. Configuration and the
   consumed-slot watermark use distinct banks. An incomplete record cannot be
   made durable by changing only a web validator. The reset/purge and torn-write
   paths also need coverage if a new bounded draft representation is added.
5. **Consumer identity has a different authority.**
   Ordinary radio config/station writes cannot change profile-owned identity
   or Wi-Fi. `src/provisioning/runtime.cpp:121` overlays profile values, and
   `src/network/api.cpp:596` rejects attempts to bypass that ownership.
   `consumer_profile.cpp` admits a complete station; `bootstrap_server.cpp:885`
   decrypts and plans a complete station before trial/commit. Public AP setup
   and authenticated LAN/AP wrappers are distinct access paths to that same
   transaction. Incomplete progress must not become a partial source-5 profile
   or acquire owner, TLS or scheduler authority.
6. **Browser setup also requires a complete tuple.**
   `src/network/bootstrap_web/owner-claim.js:77` and `radio-setup.js:38` encode
   complete station plaintext. `owner-app.js` uses saved generation/digest
   readback; the radio page's `saveConsumer` performs a complete WSPR preview
   before preparing a transaction. A callsign-only saved draft needs an
   explicit supported path, not an incomplete packet passed through old crypto.
7. **The normal editor serializes the whole form.**
   `src/network/web/app.js:470` parses all schedule lines, constructs a complete
   config and uses PUT. Changed identity is checked through `wspr-plan`; an
   unchanged readable legacy identity is preserved during unrelated saves.
   Consumer identity/network controls in that editor are read-only and fresh
   effective saved values replace stale copies. Dirty-state tracking and
   `fill`/`refresh` currently distinguish only browser drafts and saved config;
   they must not erase a new persisted draft or relabel it active.
8. **Saving can affect future autonomous admissions.**
   `src/standalone/scheduler.cpp:86` polls enabled Store configuration, checks
   clock/readiness, plans before CLAIM and reserves before LOAD/ARM. CONFIG
   changes affect later admissions without reboot; network/pins retain
   saved-versus-active/restart inhibition. A P15.8 pair freezes both frames,
   identity, power, frequency and config generation. Draft saves must not mutate
   that execution snapshot, advance its watermark or resume STOP. Explicitly
   define activation when a previously enabled configuration already exists.
9. **Readiness must be specific to the operation.**
   A pure WSPR preview establishes encodability, not live clock, ownership,
   storage, pin, expiry, RF-engine or restart readiness. `messagePlan` and
   `LOAD_MESSAGE` validate finite Morse jobs independently; raw WTP jobs already
   contain their event plan. Do not introduce a global WSPR-locator requirement
   for otherwise valid QRSS/FSKCW/DFCW or externally encoded WTP jobs.
10. **Recovery is part of the save contract.**
    `app.js` maintains readback/review/ready write states, target/revision context
    and sent-once attempts. `radio-setup.js` keeps nonsecret generation/digest
    receipts. P15.7 retirement, three-session isolation, uncertain saves and
    fresh saved-state review must extend to any new draft or activation write.
    A refreshed login/status, matching values or plan preview does not establish
    which interrupted request committed.
11. **Old/new resource shapes are deliberately strict.**
    P15.8 adds application/2, station/2, config/2, config/update/2 and
    wspr-plan/1 while retaining frozen v1 shapes. `/00`–`/09` are supported with
    ambiguity metadata; paired Type 3 hashes the requested full identity. Keep
    brackets, 3–12-character station-token bounds, full saved locators, exact
    powers and legacy-readable unsupported identities intact. Drafts must not
    masquerade as complete Config v1 or station/1 or station/2 projections.
12. **Pi release and companion are different products today.**
    Pi `src/wtp_integration/configuration.cpp` validates complete responses,
    exact application shapes and existing atomic merge semantics.
    `WsprryPi-UI/data/wtp-management.js::changes` already builds leaf patches
    for complete settings, but scoped station saves remain complete and
    consumer identity is read-only. Release devel remains Type 1 management;
    the unmerged P15.8 companion negotiates Type 2/3 resources. Pi devel's
    `090a15a` changed shared UI/workflow files; `d93c75c` adds a fail-closed
    transmitter-access CI audit. A new companion must preserve these release
    fixes and reconcile any overlap, not quietly promote the older branch.

## Prompt for the executing conversation

Implement **P15.9 — Save valid fields independently of transmit readiness**.
Use **Pico devel**. Complete the implementation, tests, UI validation,
documentation impact, adversarial review, repairs, reassessment, scoped commits
and non-force push when the operator executes this prompt. Until then, this is
prompt writing only. Do not implement P15.10–P15.14 or execute the P15.8 handoff
again.

### 1. Refresh the working state and respect release boundaries

Read applicable AGENTS.md files, Pico README.md, CONTRACT.md,
docs/architecture.md, docs/development/README.md, standalone/configuration-update
contracts, browser API, shared-application contract and P15.6–P15.8 evidence.
Inspect the full persistence lifecycle and relevant tests before editing.
Refresh status, staged/unstaged changes, actual remotes, source identities and
intervening commits in every checkout used. Preserve unrelated work; do not
reset, stash, clean, force-push or switch the primary Pi release checkout.

Repository boundaries:

- `/Users/lbussy/GitHub/WsprryPico`: implement on devel through the existing
  portable/application, platform, storage, browser and provisioning boundaries.
- `/Users/lbussy/GitHub/WsprryPi`: current devel is read-only reference until
  the operator coordinates a concrete companion scope. Reading it authorizes
  no source, UI, test, fixture, CI, compatibility-pin or documentation edit.
- `/private/tmp/wsprrypi-p158/source`: inspect the published P15.8 companion
  read-only. Its earlier authorization does not authorize adding P15.9 changes
  or rebasing/merging that branch.
- `/Users/lbussy/GitHub/WsprryPi-Docs`: inspect read-only for Documentation
  Impact and exact P15.14 follow-ups. Do not modify or publish that repository.

Prefer compatibility without Pi changes. If changes are necessary or desired,
first present the operator with exact affected Pi paths, rationale, current
release head, required P15.8 dependency, proposed base and isolated feature
branch, CI impact, release timing and publication order. The default branch
proposal is `codex/p15-9-valid-field-saves`, from an agreed devel base. If it
needs unmerged P15.8, obtain agreement on a stacked base or other integration
strategy before creating that dependency; do not silently merge/cherry-pick it
into release devel. Continue independent Pico/read-only work while coordinating.

Approval of a Pi feature scope permits its implementation, validation, scoped
commits and push to the approved feature branch. It does not authorize merging,
release promotion, changing Pi devel or pushing Pi devel. Those actions require
separate explicit authorization. These same limits apply during adversarial
repairs and the originating conversation's later assessment. Do not message
other chats or maintainers without direct operator authorization.

### 2. Reproduce the operator workflow and define the state model

The operator wanted to update a callsign in the second setup block without
setting up QRSS messages. Their clarified requirement is broader:

> Allow any valid editable fields to be saved, without confusing saved progress
> with ready to transmit.

Reproduce the shipped-page path with incomplete/invalid unrelated inputs and
record which layer prevents saving. Keep the distinction between this new
reproduction and the original physical board/session incident. Inventory
existing editable settings and their actual persistence/action boundaries.
Cover station identity and the existing configuration controls; a send-only
message form must not block saving settings or silently become a save action.
Do not build a new message library or persistent raw-WTP-job store as incidental
scope.

Write a concise design/acceptance record before implementation. Define:

- Browser edits not yet accepted; valid fields persisted on the Pico; incomplete
  saved draft; complete committed runnable settings; active boot settings;
  explicit schedule enablement/STOP; selected-operation readiness; actual job
  ownership/armed/running/output state. These are distinct observations.
- Which fields can be independently validated; which belong to a coupled unit
  such as a complete pin plan, schedule array or usable network credentials;
  absence, explicit clear, omission, false, zero and null semantics.
- The new request/result schema if needed, field-level outcomes, common target
  and revision binding, storage representation, activation step and backwards
  compatibility. Label new routes/schema names as proposals until implemented.
- What happens when complete already-enabled runnable settings exist beside an
  incomplete draft. Saving progress must not silently replace the live station,
  re-enable a disabled schedule or restart a stopped scheduler. If current
  enabled work continues on its old complete configuration, show that fact
  beside the not-ready draft; do not claim the transmitter is globally stopped.
- A clear explicit apply/enable/start boundary for promoting draft settings.
  Becoming syntactically complete is not itself a trigger. Revalidate the exact
  target, saved draft revision, applicable dependencies and current authority
  at promotion/execution, even if an earlier preview was successful.

Proceed with routine implementation choices within this requirement. Seek
operator input only for a real change to authority, release scope or a product
decision not resolved by this prompt; do useful independent work in parallel.

### 3. Save valid progress without weakening complete operations

Calls, locators and reported power must be independently savable when their
own value is valid. Unrelated blank/invalid message controls, schedule rows,
network controls or station fields must not force valid progress to be lost.
Preserve unchanged saved values. Keep invalid entered values visible and
unsaved, mark them accessibly, and explicitly report which valid fields were
persisted. Never imply that the entire form was saved after only a subset was.

At minimum, cover:

- Callsign-only on a network-only/otherwise incomplete device: persist the
  valid callsign on the device without manufacturing a locator, power choice,
  station profile, schedule, owner or job. Confirm after page reload, session
  turnover and reboot using a freshly constructed runtime and journal reload.
- Locator-only, power-only and unrelated valid settings when other station
  inputs are missing or invalid. Zero dBm is a real valid value, not a missing
  sentinel. HTML number coercion must not turn an empty field into zero.
- Mixed valid/invalid edits: valid independent changes survive, invalid fields
  remain unsaved and visible, and no unchanged saved value disappears.
- Existing complete saved station: callsign-only or locator-only edits preserve
  the other authoritative saved components without requiring the operator to
  re-enter them or replace unrelated Wi-Fi credentials. Existing authentication
  and step-up requirements still apply.
- Dependency conflicts: save only safe independent units and explain why a
  coupled unit remains a draft or unsaved. Do not apply half a pin plan or a
  credential pair merely because its individual fields parse successfully.
- Completing an earlier draft: preserve its values and require the explicit
  apply/enable decision before runnable authority changes. An ordinary refresh,
  authentication, reconnect, reboot or preview cannot make that decision.

Keep the P15.1 and P15.8 atomic update/resource operations atomic. Invalid
members of an old complete request must still reject the entire request with
no partial mutation. If field-level partial success requires a new operation,
advertise/version it explicitly and define its complete per-field result and
revision. Prefer one bounded verified commit of accepted independent progress
over a browser loop that performs many unsynchronized field saves. Do not
silently retry rejected subsets, drop validation failures or replay a mutation.

Retain unknown/duplicate-field rejection, byte/type/number bounds, omit-to-
preserve semantics, explicit resets, secret redaction and unsupported-firmware
behavior. A rejected or unconfirmed operation cannot be described as saved.

### 4. Keep draft storage and profile authority explicit

Where runnable Config v1 or ConsumerProfile cannot represent incomplete work,
add the smallest bounded, versioned durable draft representation through the
existing configuration/provisioning authority. Client memory/localStorage alone
does not satisfy a device save. Do not loosen complete-config/profile parsing,
use fake AA00/callsign/message values, or change an incomplete station into a
valid consumer source merely to satisfy an old schema.

Document exact flash/RAM/response budgets and migration/rollback behavior.
Respect configuration, watermark, profile, access, bond and reset regions. Do
not allocate an unbounded generic key/value store or create a second scheduler
or configuration authority. Draft and committed values need coherent,
identity-bound readback and explicit provenance; old complete projections must
not leak incomplete state or claim it active.

Trace journal commit/reload, CRC/sequence/exhaustion, interrupted erase/program,
storage health, reset/purge/factory restoration, corrupt/newer records and
upgrade from all supported old sources. A fault cannot cause fallback to a
superseded profile or auto-promotion of an old draft. Draft writes must preserve
the consumed-slot watermark and the last known complete runnable settings.

Separate incomplete credential progress from activation of a usable network.
Retain existing trial/commit and response-delivery rules for real Wi-Fi or
profile changes. If credential drafts are necessary, define their bounded
secret storage, authenticated readback/redaction and cleanup explicitly; never
place passwords/keys in browser URLs, receipts, logs, screenshots, error bodies
or persistent browser storage. Existing ordinary flash confidentiality limits
still apply; do not claim encryption at rest without implementation evidence.

Consumer station/network writes retain transactional setup authority. Ordinary
config APIs must not bypass the overlay/profile checks. AP-only public
commissioning must stay AP-only; authenticated station/AP radio and engineering
mTLS/authorized field paths retain their policy. A new draft path must be
explicitly classified/admitted at every dispatch layer; no accidental preclock,
blank, wrong-origin or raw-WTP management access. If incomplete setup needs a
new operation, version its contract instead of sending partial old plaintext.

### 5. Enforce readiness and activation in the backend

Make the backend authoritative for completeness, selected-mode planning and
execution admission. UI state is explanatory and may become stale. Provide
bounded actionable reasons for missing, invalid, unsupported or unknown state
without collapsing saved, ready, enabled, authorized and transmitting.

For local WSPR, reuse P15.8's exact automatic planner, station-token bounds,
four/six-character locator semantics and exact powers. Preserve Type 1 symbols,
compound-four Type 2, compound-six Type 2/3, bracketed-six Type 3, `/00`–`/09`
ambiguity warnings, requested-full-call hashing and unsupported legacy identity
preservation. Do not silently strip affixes/brackets, round power or substitute
identity. Unsupported encodability may be reported separately from otherwise
valid saved progress; it cannot authorize execution.

For QRSS/FSKCW/DFCW and raw jobs, validate the actual operation's requirements,
finite timing/events, message alphabet, frequencies and limits. Do not demand
a WSPR locator just because that mode has a station editor. Preserve existing
WTP/1 messages and complete locally timed jobs.

Readiness also depends on actual storage/access health, selected supported
engine/pins/frequency policy, expiry/schedules, required clock quality,
ownership/busy state, STOP, restart inhibition and unresolved output. Unknown
observations remain unknown and cannot enable an action. An encodable preview
is only a plan preview and never a claim of physical RF qualification.

Saving a field/draft must issue no HELLO/CLAIM/LOAD/LOAD_MESSAGE/ARM, create no
job or owner, clear no STOP/fault, implicitly grant no experimental opt-in,
reset no cursor, switch no RF GPIO and trigger no network activation/restart.
Existing transmissions/pairs remain frozen; retain idle/write/resource
admission. Explicit promotion/enable/start must rerun all required checks
against current identity and revisions. Test direct API/Console/transport
attempts, not just disabled buttons. Keep the one JobService and local RP2350
timing authority.

### 6. Make saved progress understandable in the shipped UI

Use Impeccable for this form/error-state work. Follow the installed skill and
its context/playbook requirements once per executing session. Preserve existing
styling and page structure; P15.10 hostname/title, P15.11 page reorganization
and P15.12 identity presentation remain outside scope.

Use explicit user-facing feedback such as:

- "Callsign saved. WSPR is not ready: grid locator missing."
- "Callsign saved. Locator was not saved: use a valid grid locator."
- "Draft saved. The current enabled schedule still uses the previously applied
  station settings." Only display this when authoritatively true.
- "Save result unconfirmed. Your edits are preserved. Read saved settings
  before sending another save."

Adapt exact wording to the implemented state model. Distinguish a valid field
saved on the device, a browser-only invalid edit, a complete saved draft, the
applied config and the job state. Show the applicable operation/mode in
readiness text. A success notice must not obscure simultaneous unsaved errors.

Avoid global HTML required-field validation that prevents saving independent
valid fields. Do not merely remove required constraints and leave backend
failures unexplained. Maintain real labels, nearby field errors, keyboard
focus, aria-invalid/description/status semantics and usable mobile layouts.
Make intentional clear versus unchanged/omitted actions discoverable. Preserve
draft text during validation, polling, preview, status/readback, login/expiry,
conflicts and switching between relevant setup views. Never overwrite an
operator edit with delayed readback or a stale successful response.

Exercise engineering and consumer radio UI plus public AP setup where it owns
this workflow; rebuild generated bundles through existing scripts and retain
third-party notices. Use genuine served assets and the production bootstrap
fixture for behavior, not only hand-written DOM mocks. Inspect desktop/mobile,
available light/dark preferences, long errors, blank state, mixed save outcomes,
keyboard and 200% zoom in a bounded visual pass; fix observed defects together
and confirm once. Do not claim an unimplemented dark theme or measured contrast
from a regex-only detector. Keep screenshots outside source control.

### 7. Preserve recovery, sessions and stale-context behavior

Extend P15.7's saved-state readback/review state machine and sent-once receipts
to new persistence and activation operations. Preserve browser invalid edits
beside fresh authoritative saved draft/config observations. Distinguish config,
draft and profile revisions if the implementation uses several; prove their
combined coherence before enabling an action.

Require fresh device/boot/profile/target/revision context and a new explicit
save after stale state, lost response, timeout, malformed/truncated JSON,
authentication expiry, retirement or reconnect. Reconcile each field's confirmed
outcome; do not assume a batch failed because its response was lost. No automatic
retry, strategy fallback, implicit promotion, login-as-confirmation or silent
discard. A/B/A writes and same-value writes must not defeat revisions.

Test all three P15.6 sessions, the one pending-login quota and P15.7 full-capacity
retirement with overlapping draft saves/readback. One session's expiry or
retirement must not erase another's draft, abort its job, replay a save or cancel
already committed work. Global mutable callbacks/receipts must not cross-bind
target, session, connection, draft or result. Preserve P15.5 bounded cooperative
request service and core-1 RF isolation.

### 8. Validate the implementation and compatibility

Use existing checked-in commands after inspecting what they execute. Do not
invent targets or reuse a stale build as current-source evidence. Record exact
source pairs, tool/dependency identities, commands, exit results and assertion
counts. No local macOS C++ compilation/linking of WsprryPi: use an identified
Linux environment or Linux CI. Local JS/Python/document checks remain available.

Core commands documented in docs/development/README.md and the P15.8 packet:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF
cmake --build build-host --parallel 3
ctest --test-dir build-host --output-on-failure
python3 scripts/validate_wtp_contract.py
npm --prefix src/network/bootstrap_web test
npm --prefix src/network/bootstrap_web run build
```

Supply verified retained Mbed TLS/lwIP paths using the existing
`WSPRRY_PICO_TEST_MBEDTLS_PATH` and `WSPRRY_PICO_TEST_LWIP_PATH` options when
needed for actual crypto/bootstrap/network coverage. Some finite-job tests use
the documented `PHASE115_ENDPOINT_DRIVER` fixture; inspect test enumeration and
configuration so missing dependencies/skips cannot masquerade as full coverage.
Reconfigure/build from the final relevant source before the final test run.

Extend meaningful behavioral tests, including:

1. Existing complete merge/replace/legacy operations stay atomic and unchanged;
   rejected mixed old requests mutate neither config/profile nor generation.
2. New valid-field saves work with missing/invalid unrelated inputs, preserve
   unchanged state and return accurate field-level outcomes. No implicit empty
   number-to-zero, power default, blanket null deletion or array-index merge.
3. Real journal reload and reconstructed runtime retain incomplete progress;
   crash/tear/CRC/reset/migration cases never turn it runnable or lose the prior
   complete authority. Verify draft byte/field/count/sequence bounds.
4. Explicit promotion rejects incomplete or stale contexts in direct backend
   calls; preview/readback/login/reboot never promotes. Already-enabled old
   configuration, disabled configuration, STOP and pin-restart latches are
   individually tested.
5. P15.8 complete station cases and all ambiguity/hash/locator boundaries remain
   correct. Preserve unsupported unchanged legacy identities on unrelated saves.
   Pair continuation, gap/STOP/reboot/frozen snapshots/watermark remain correct.
6. No mutation/job/lease/flash-cursor/output/network side effect from validation,
   readiness reads or plain draft saves. Message jobs retain mode-specific
   requirements and do not acquire new WSPR dependencies.
7. Genuine crypto/carrier/production PicoBootstrapServer tests cover initial
   incomplete state, consumer profile authority, station/AP origin/Host/CSRF,
   field/preclock denial, sent-once setup, readback and uncertain-write recovery.
8. Actual shipped-page browser interactions cover callsign-only with blank QRSS,
   locator-only, mixed valid/invalid, Enter/click/keyboard/native validation,
   reload/session/recovery, live enabled settings beside a not-ready draft and
   no extra save/job request. DOM mocks alone are insufficient.
9. Three-client contention, revision conflicts, late/out-of-order responses,
   malformed/future capabilities and transport failures preserve drafts and
   reject before unauthorized mutation. A partial-success response must be
   strictly validated; unknown fields/outcomes cannot become assumed success.

Run the full relevant Pico host suite, WTP contract, bootstrap/npm and browser
checks plus affected ASan/UBSan suites. Preserve assertions and deadlines; record
and repair failures rather than weakening tests or counting an unavailable
sanitizer/dependency as a pass. The P15.8 196/27 counts are a baseline, not
preselected counts for this new implementation.

Build/link both standard RF-inhibited and StandaloneRF Pico 2 W images when
firmware changes. Reuse verified retained SDK, Mbed TLS, lwIP, Arm toolchain,
pioasm/picotool rather than installing/fetching dependencies incidentally.
Inspect memory/stack/flash topology, reserved regions and RF resource placement.
Report linked/compile-time budgets separately from physical heap/stack or timing
qualification. No flashing, GPIO, RF, installed-service or board operation is
authorized by this prompt alone; use current operator setup statements and
finite limits if subsequently authorized. P15.13 physical support gates stay open.

Compatibility requirements:

- Keep frozen application/station v1/v2, config-update/1, management/1 and /2,
  Consumer-Radio/1, Consumer-Recovery/1 and WTP/1 semantics unless an explicitly
  justified new version is needed. Add new capability negotiation without
  altering strict old resource shapes. An unsupported old client may lack
  draft features but must retain honest complete-config workflows.
- Test unchanged release Pi against new Pico and the exact approved P15.8
  companion against new Pico. Retain the frozen `a2437d1` release probe and
  separately assess the refreshed release devel (`d93c75c` at review). Do not
  present feature-branch tests as current release integration.
- Preserve all seven historical compatibility profiles and the accepted
  P15.8 current pair. If advancing Pi's current Pico pin, add a frozen `p158`
  historical row at `804e8a06585ec5a0e650e69fcd71ada398b6cc9f`, then add the new
  current source. That is nine total rows; do not rewrite the older expectations
  or retarget historical rows to make changed sources pass.
- If an approved Pi companion is modified, use its actual Linux config/API,
  native carrier, runtime/scheduler and UI producers/tests, relevant sanitizers
  and source-identity guards. Read docs/simulated-backend.md before application
  simulation. Existing `make wtp-config-test wtp-api-test`, per-profile
  `wtp-config-interop-test`, network interop/runtime, scheduler and application
  targets are orientation; inspect current Makefiles and required variables.
- Check CI on the exact pushed approved branch and Pico pin. Preserve release
  devel's newer UI fixes and fail-closed access audit. Reconcile overlapping
  workflows/browser fixtures explicitly; never merge release changes implicitly
  or weaken a guard to get a green feature branch.

### 9. Review documentation impact

Create `docs/development/phase15-9-valid-field-saves.md` with the implemented
state/authority/storage/API model, acceptance criteria, exact commands/source
pairs, outcomes, failure/repair history, screenshots locations and limitations.
Update affected Pico API/schema/configuration/standalone/development guidance
and roadmap status to reflect actual acceptance. Preserve historical evidence
and distinguish proposals from delivered contracts.

Inspect the operator docs read-only, especially:

- `docs/User_Interface/Setup/Signal_Setup/wspr.md` and `cw.md` for saved identity,
  message setup, saved versus applied/draft/ready states and mode-specific rules.
- `docs/User_Interface/Setup/Transmitter/index.md` for member/profile ownership,
  partial-save results, explicit apply/enable and old-firmware behavior.
- `docs/Advanced_Operations/configuration_troubleshooting.md` for invalid-field,
  uncertain-write, login retirement and readback/review recovery.

Record exact P15.14 operator text/screenshot follow-ups without editing the
separate documentation repository. Do not copy Pi autosave behavior into Pico
without a reason; the requested outcome is saving independent valid progress,
not an unrequested autosave redesign.

### 10. Adversarial review, repairs and reassessment

After implementation and affected checks, perform a fresh adversarial review
against the requirements and code paths, not merely a repetition of happy-path
tests. Use a fresh independent reviewer when available; otherwise accurately
label self-review and do not claim independence. Give the reviewer exact
source/dirty diffs, contracts, tests and failure evidence.

Challenge at least:

- A valid field incorrectly marked saved after a failed/ambiguous batch; an
  invalid sibling accidentally persisted; stale readback erasing an edit.
- Incomplete records represented as active Config/Profile; missing power
  coercing to zero; draft promotion through reboot, preview, refresh, old APIs,
  Console, migration, reset fallback or a malicious direct request.
- Save updating a live enabled station, resuming STOP, bypassing profile setup,
  mutating a frozen pair, claiming a transmitter or resetting a watermark.
- Readiness based on WSPR-only rules for other modes, or on an old boot/profile,
  happy preview, unknown output, unavailable engine or stale storage health.
- Multi-client lost updates, A/B/A/same-value revision failures, cross-session
  callback/receipt confusion, replay after expiry and races with setup/restart.
- Secrets or incomplete drafts leaking through public AP, legacy projections,
  errors, receipts, URLs or browser storage; unbounded storage/stack/heap use.
- Changed atomic/legacy semantics, skipped source-pair coverage, wrong current
  pin, CI guard weakening or unauthorized Pi release/companion changes.

For every actionable finding, record severity, trigger, affected source,
repair, meaningful regression and result. Fix findings in scope, rerun affected
checks and reassess the repaired final state. Repeat until no actionable finding
remains; do not label unresolved findings closed with narrative alone. If a
repair needs a new authority/release decision, present the concrete issue and
retain it as open while completing independent authorized repairs.

### 11. Commit, push and return the handoff packet

Once required local checks and review are complete, inspect final diffs and
stage only this slice. Commit/push Pico devel without force. For CI that needs a
fetchable Pico source, publish the validated immutable Pico implementation pin
first, then only the approved Pi feature branch. Record this dependency order;
do not claim CI passed until the exact published head/pin completes. Never
push or merge Pi devel under this prompt's default authorization.

If CI finds an issue, repair it, rerun affected local checks, reassess and push
the scoped follow-up. After final CI, independently verify remote branch hashes
and report staged/unstaged/untracked state in all touched checkouts. Separate
tested implementation commits, documentation/report heads, historical pins,
feature-branch adoption and release integration. No PR/release is required.

Return a self-contained completion report with behavior delivered, lead repo,
branches/source pairs, exact tests and CI, UI/Impeccable evidence, review
findings/repairs/final assessment, commits/push/remote parity, remaining work and
**Documentation Impact** (updated, considered unchanged, still required).
Explicitly retain physical/security/installation and Pi release limitations.

The operator will return that packet to the originating conversation for its
separately requested post-execution adversarial assessment, repairs,
reassessment and scoped commit/push. Include everything needed to reproduce
and inspect the final source. Do not assume that later assessment has happened,
schedule a background follow-up, or send another conversation a message without
operator authorization. This document's preparation does not execute any of
these implementation or publication steps.
