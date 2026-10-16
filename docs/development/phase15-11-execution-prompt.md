# P15.11 handoff: Station/Transmission and Wi-Fi/Host organization

Execution is complete within its supported software scope; see the
[acceptance record](phase15-11-page-organization.md). The preparation status,
reviewed pins and implementation instructions below are historical.

Preparation status: **prompt prepared; implementation not executed** at the
source review below.
Prepared on 2026-10-16. The operator has marked P15.11 in progress for handoff
and execution tracking. That status does not establish delivered behavior.
P15.10 is closed within its [supported software acceptance](phase15-10-hostname.md).

## Lead repository and reviewed baseline

**WsprryPico leads.** It owns the embedded pages, HTTP dispatch, AP/station
interface classification, authentication adapters and the configuration/profile
transactions behind these controls. This organization change should be
deliverable in Pico without changing WsprryPi.

| Source | Identity and state observed during preparation |
| --- | --- |
| Pico `devel` | `7cbc9374218fe5d534b067216ca2c555a20240b9`; independently matches remote `refs/heads/devel` |
| Pico worktree | Existing documentation-only roadmap-summary correction from P15.10 closeout; preserved and included in this preparation, without implementation edits |
| Pi `devel`, read-only reference | `a84010d6c16ac416d52989053ac1f273390a8ab5`; locally clean, with Type 2/3 integration and acceptance commits; remote parity was not checked here |

Recent Pico commits are P15.10 implementation `556f19b`, test-boundary repair
`334ea5a`, compatibility-harness repair `ecbe2c4`, and acceptance `7cbc937`.
The acceptance record retains 203 executable host groups, 25 affected sanitizer
checks, genuine browser/crypto workflows, three exact Pi pairs and both firmware
links. Those are **P15.10 historical results**, not P15.11 validation. One
optional schema check was skipped. No Pico CI result is claimed.

At the initial source review, P15.8 and P15.9 were pending their Pi portions
under WsprryPi checklist steps 14 and 15. Subsequent operator acceptance on
2026-10-16 closes P15.8, including WsprryPi step 14. P15.9 remains in progress
pending its Pi step 15 portion. Preserve these current statuses and recheck
source/coordination records rather than inferring completion from commit titles.

## Code review: current capabilities and change boundaries

| Source | Current behavior and significance |
| --- | --- |
| [Station HTML](../../src/network/web/index.html), [script](../../src/network/web/app.js) | One station-control document contains status, `Station & network`, schedules/pins, hostname/restart, consumer Wi-Fi/station setup and message/job entry. The duplication is real, but the editors have different authority. |
| `app.js::fill`, configuration submit handler, `saveConsumer` | In consumer mode, station/Wi-Fi fields in the general configuration editor are read-only. Its save preserves fresh profile-owned values. Editable replacements use separate encrypted consumer setup transactions, rather than an ordinary config PUT. Engineering configuration follows its existing adapter. |
| [Wi-Fi setup](../../src/network/bootstrap_web/index.html), [station setup](../../src/network/bootstrap_web/owner.html), [page guide](../../src/network/bootstrap_web/README.md) | AP commissioning already separates Wi-Fi from optional station setup. `/`, `/index.html`, `/owner.html`, `/radio` and recovery links have existing meanings. The older guide's Type 1-only descriptions must be read alongside P15.8's superseding acceptance. |
| [Portable AP page dispatcher](../../src/network/bootstrap_http.cpp) | Safe captive GETs with a foreign Host redirect to fixed `http://192.168.4.1/`. Setup availability selects Wi-Fi or station content; unavailable recovery has a bounded read-only page. This is separate from station HTTP admission. |
| [Production bootstrap server](../../src/network/pico/bootstrap_server.cpp) | `classify_client` and `dispatch` distinguish accepted AP and station connections. A consumer station GET `/` serves the authenticated radio document; `/radio` serves it on admitted interfaces. Other station requests are refused unless explicitly handled. Raw bootstrap/owner/recovery routes remain AP-only. |
| `PicoBootstrapServer::consumer_setup`, `setup_delivered`, `setup_login_closed` | Authenticated consumer envelopes forward only a closed setup-route set into existing trial/commit handlers. Reply delivery and login closure control deferred effects. Moving a form must preserve this path. |
| [Firmware composition](../../src/standalone/pico/main.cpp) | `ap_interface`/`station_interface` use actual netif/local-address evidence. AP startup, leases, draining, RF guards and consumer station listeners are selected independently. A page URL or hostname is not authority to change those policies. |
| [Consumer adapter](../../src/network/consumer_radio.cpp), [client](../../src/network/bootstrap_web/radio-client.js) | Exact interface/Host/Origin admission, generation-bound volatile sessions and three-session/one-pending-login limits already exist. Reloading pages must not create unnecessary competing logins. Identity/1 has an exact closed key set in the client. |
| [Browser API](../../src/network/api.cpp), [engineering SoftAP adapter](../../src/network/softap_api.cpp) | Engineering pages reuse generated assets with existing mTLS or local-session authority, pre-clock handling and restrictive Host/Origin checks. A consumer navigation change must not strand these surfaces. |
| `app.js` save/readback and hostname sections | Drafts, uncertain writes, explicit readback/review, `#save=` continuation receipts, `#hostname-return=` receipts, saved versus active hostname, one-shot restart and bounded reconnection are implemented. Navigation must preserve their meaning. |
| [Presentation helper](../../src/network/bootstrap_web/presentation.js) | Device-bound, nonsecret presentation supplies hostname-first titles for setup pages. It is not an authentication proof. Do not add navigation fields to frozen identity or presentation schemas without a compatible versioned design. |
| [Asset generator](../../scripts/generate_web_assets.py), [CMake inputs](../../CMakeLists.txt) | HTML/CSS/scripts and CSP hashes are embedded and streamed from flash. Script ordering, closing-tag checks, configure dependencies and individual C++ literal limits matter. A source-file-only mock does not prove the served product works. |
| [Incumbent design](../../src/network/web/DESIGN.md), [CSS](../../src/network/web/style.css) | Existing flat light interface, system fonts, navy header, native controls, visible focus and mobile layout are the visual authority. Organization is the scope; a new visual identity is unnecessary. |

Review conclusion: organize the operator's tasks while retaining their actual
save authorities. Prefer a shared document with two clearly named areas when
that avoids session churn and draft loss; two pages are equally acceptable if
they meet the same navigation, authority and recovery requirements. This is a
recommendation, not a selected route or implemented design. AP provisioning
still needs its profile-appropriate commissioning flow.

Preparation is a static source review. No P15.11 implementation, browser
acceptance, hardware operations or transmission was performed.

## Execution prompt

Use the following as the complete task for the executing conversation.

### 1. Objective and authority

Implement **P15.11** in `/Users/lbussy/GitHub/WsprryPico`, working on **`devel`**.
Remove confusing duplication between Station/Network and Wi-Fi/station setup.
Either consolidate the interface into clear areas, or provide two pages:

- **Station/Transmission:** station identity and WSPR planning, standalone
  schedules, applicable radio hardware/pins, transmitter status, message/job
  preparation, and explicit execution controls.
- **Wi-Fi/Host:** Wi-Fi credentials and time server, hostname/discovery, saved
  versus active network/host state, restart/reconnect, and setup access guidance.

For captive-portal/AP entry, Wi-Fi/Host is the default landing area. For an
infrastructure connection, Station/Transmission is the default. Both areas
must be accessible through clear links in both directions. A consolidated
document may use section links. Preserve explicit deep links and the user's
chosen area instead of continually forcing the connection's default.

Execute implementation, appropriate verification, adversarial review, repairs
and reassessment, then commit and push the authorized Pico changes to
`origin/devel`. Do not stop after drafting another prompt. This execution
authority applies when the operator invokes this prompt; preparation of this
file does not execute it.

### 2. Re-orient before editing

Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `docs/architecture.md`,
`docs/development/README.md`, the P15.11 roadmap entry, relevant browser API and
consumer LAN contracts, and P15.7/P15.8/P15.9/P15.10 records. Inspect current Git
branch, tracked/untracked changes, recent commits and remote head. Record full
source pins. Preserve this handoff and other documentation/user work.

Use current `devel` as the implementation source. Reconcile concurrent updates
without reset, stash, force push or unrelated changes. Do not silently switch
an occupied checkout. Resolve routine implementation choices within scope.

WsprryPi is close to release and is an independent repository. Read it only as
needed for compatibility. No Pi edit, merge, branch publication or message to
another conversation is authorized by this prompt. If a companion change is
actually necessary, first make the Pico result and exact dependency concrete,
then request coordination; a separately authorized Pi feature branch may be
appropriate. Do not make Pico UI organization depend on new Pi behavior.

### 3. Choose and document the organization

Before changing UI, record a concise route/area and field-ownership map in
`docs/development/phase15-11-page-organization.md`. Select one consolidated
document or two pages, explain the choice using session, draft, asset-size and
commissioning constraints, and list which existing routes remain valid.

Inventory every current editable field, summary, action, recovery control and
help link. Assign each to one task area. Give each field one obvious editor per
applicable profile/workflow. A read-only status summary may repeat information,
but must be visibly distinct from an editor. Do not merely move the same
duplicate forms into new containers.

Keep station identity with Station/Transmission and Wi-Fi/time-server/hostname
with Wi-Fi/Host. Explain any shared status or restart control placement. Pin
assignment belongs with the existing radio/hardware work; retain its distinct
save/application semantics. Keep required recovery/status controls reachable
when a write, restart or session failure prevents editing.

Use the available Impeccable skill for implementation and bounded visual review.
Honor the incumbent `src/network/web/DESIGN.md` and CSS and the setup pages'
native controls. Missing root product/design metadata is not authorization for
a rebrand or unrelated collateral repair. Follow applicable skill guidance;
record any unavailable tooling or degraded detector rather than claiming a
pass. Retain legible copy, labels, focus indicators, live status, appropriate
touch targets, long-name wrapping and the existing narrow-screen behavior.

### 4. Connection-specific landing and routing

Build and test an explicit matrix covering blank/unprovisioned, network-only,
committed consumer, consumer TLS-pending, engineering pre-clock/normal,
recovery/reset/fault, and unavailable interfaces. Do not promise a station
control editor to a profile that has no such authority. Show an honest
unavailable state and an applicable next step, without inventing permissions.

- Use actual accepted AP/station connection context for server default routing.
  Do not infer interface authority solely from user agent, DNS suffix, saved
  Wi-Fi state, arbitrary Host/query/hash values or the presence of a private IP.
- A fresh AP/captive root entry lands at Wi-Fi/Host. Preserve existing safe
  captive GET redirects to the fixed AP origin, no-store behavior, encrypted
  setup and regular-browser fallback when captive browser crypto is missing.
  Unsupported methods must not become redirects that replay a mutation.
- A fresh admitted infrastructure root entry lands at Station/Transmission by
  either current IPv4 or configured hostname. Its Wi-Fi/Host link must work on
  the same admitted LAN surface; it must not just send the operator to an
  unreachable `192.168.4.1` address or an AP-only raw setup API.
- Provide the reverse link from Wi-Fi/Host to Station/Transmission. Where a
  profile lacks station authority, explain the existing commissioning step and
  keep navigation useful without granting job control.
- Preserve `/`, `/index.html`, `/owner.html`, `/radio`, recovery and useful
  existing bookmarks through working aliases or clearly documented compatible
  routing. Never redirect API errors into an HTML login page. Avoid redirect
  loops and lost path, return context or CSP assets.
- Explicit area links and reload/back/forward/deep links must keep the chosen
  area. Automatic polling, interface recovery or authentication must not
  unexpectedly switch areas or move keyboard focus.

Choose the smallest safe navigation mechanism. If additional UI metadata is
needed, keep it bounded, nonsecret and versioned. Frozen Consumer-Radio identity,
presentation, configuration and management contracts remain compatible; do not
append fields to closed schemas or treat presentation as authentication.

### 5. Preserve save authority and transmitter behavior

UI grouping does not merge the configuration journal, consumer profile,
bootstrap/claim transactions or their commit ownership. Reuse existing
coordinators/adapters, target identity, profile generation, ETag/If-Match,
same-origin guards, idle/admission checks and delivery-completion semantics.

- Consumer station and Wi-Fi edits continue through authenticated transactional
  setup wrappers on LAN and the existing AP commissioning path where admitted.
  Do not expose raw AP bootstrap/owner/reset endpoints to station clients.
  Engineering edits retain their actual certificate/local-session policy.
- Moving/removing fields must not cause a full config PUT to erase unseen
  fields or save stale profile-owned values. Preserve schedules, pins, flags,
  expiry, station data, credentials/TLS/client trust and watermark/cursors.
  Use existing scoped-update semantics where applicable; never fabricate
  defaults to satisfy a reorganized form.
- Avoid HTML validation dependencies across unrelated editors. A Wi-Fi or
  hostname save must not require a message, frequency, schedule or station
  field from another area. Preserve current independent valid-field/readiness
  behavior; inspect the actual P15.9 implementation before assuming it exists.
  Do not implement deferred P15.9 semantics or weaken backend admission as an
  incidental layout repair. Record any concrete prerequisite separately.
- Saved settings, active state, restart required and readiness to transmit
  remain visibly distinct. Navigation, login, polling or Save must never load,
  arm, enable or submit a radio job. Explicit existing execution controls and
  the single JobService/scheduler/ownership authority remain unchanged.
- Busy/owned/armed/running/failed/unknown-output states retain their refusals.
  Keep the applicable Abort/Release and recovery guidance accessible. Do not
  open AP access or abort an existing job merely to satisfy a navigation link.
- Retain engineering certificate-bound read-only hostname behavior. Consumer
  hostname rename must preserve CA/client trust and the active-boot identity.

### 6. Drafts, sessions, receipts and restart

Keep unsaved station, Wi-Fi, schedule, pin, hostname and message drafts across
same-document navigation, relogin, readback and recoverable failure. A page
transition that discards work requires an explicit choice before leaving.
Do not retain passwords, session keys/tokens or sensitive drafts in URLs,
browser storage or a service worker. Clear password visibility/content at
existing security boundaries; do not add silent background logins.

Preserve P15.6's three sessions/one pending login and P15.7's deliberate login
retirement. Changing areas should not allocate another session. If a real
navigation requires fresh authentication, make that consequence clear and
handle old login capacity without automatic retirement of another client.

Navigation hashes must coexist with `#save=` and `#hostname-return=` receipts.
Do not overwrite, misparse or replay them as section names. Preserve the
bounded expected device/generation/digest/boot/name context, verify target
identity before credentials or mutation, and handle same-document receipt
changes as carefully as full navigation. Test browser back/forward and stale
receipts after another client changes profile/name state.

Uncertain/refused writes preserve drafts and require fresh saved-state readback
and explicit review before a new explicit save. Area switches, page reloads,
reconnection timers and login completion must not retry an earlier mutation.

Retain P15.10's hostname-first function-specific titles, including IP access,
last-confirmed/unknown state and saved versus boot-active name. A Wi-Fi/Host
suffix may differ from Station control, but the confirmed active hostname
remains first. Do not pull in P15.12's prominent main-page identity redesign.

Save and Restart remain separate. Keep exactly one explicit revision-guarded
restart, the existing bounded 90-second observation/cancel/manual continuation
flow and fresh readback. Success still requires the same full device ID, a
new boot and the intended saved/active hostname. Do not copy credentials across
origins, bypass TLS verification, auto-downgrade, auto-resend restart or mistake
a countdown/DNS response for success. Preserve IP/AP recovery and explicit
handling of conflicting names, stale destinations and unrelated unsaved work.

### 7. Firmware and asset constraints

Preserve two bounded cooperative port-80 tasks, bounded TLS contexts, serialized
application commits, fixed session budgets and local core-1 RF timing. No new
threads, full-page heap copies or unbounded polling are justified by navigation.

Update the asset generator, route tables, configure dependencies and original
web sources together. Regenerate checked-in bundles when their sources change;
retain pinned dependencies/licenses and crypto-first execution order. Verify
the generated served documents, exact Content-Length, complete streaming,
CSP hashes and script loading. Keep each generated C++ literal within the
toolchain limit; do not suppress overlength warnings to hide an asset problem.
No runtime CDN, external font or internet requirement for AP setup.

Do not change WTP/1, radio encoding, RF clock/band policy, storage layout or
certificate policy for this organization task. Hardware/physical captive
portal behavior remains a separate evidence class from host/browser results.

### 8. Verification and acceptance matrix

Add behavioral regressions appropriate to the changed paths; do not merely
assert new label text or mirror a routing implementation. At minimum prove:

| Case | Required evidence |
| --- | --- |
| Blank and network-only AP | Wi-Fi/Host default, working optional station link, preserved commissioning prerequisite/crypto fallback; no job authority |
| Committed consumer AP | Wi-Fi/Host default, explicit Station/Transmission link and return, current authentication and safe AP lifecycle |
| Consumer LAN by IP and hostname | Station/Transmission default, working authenticated Wi-Fi/Host area and return; no raw AP API exposure |
| Both interfaces admitted | Correct default per accepted interface; a station hostname reached through AP follows the approved fixed-AP redirect/refusal and cannot masquerade as LAN authority |
| Engineering normal/pre-clock | Existing mTLS/local authorization and clock gates, usable navigation, certificate-bound hostname refusal |
| Recovery, fault or withdrawn AP | Honest unavailable/read-only state, applicable recovery link, no authority or lease bypass |
| Editor ownership | One obvious editor per field/workflow; saves preserve unrelated config/profile fields and reject stale revisions |
| Independent forms | No hidden required message/station/network field blocks an unrelated valid save; saving never starts RF |
| Drafts and navigation | Edits survive both directions; discard is explicit where needed; back/forward/deep links and focus work |
| Sessions and concurrent clients | One browser changing areas does not allocate/leak sessions or disturb a phone/native Pi client; generation/expiry recovery preserved |
| Uncertain writes and receipts | Dropped reply before/after commit, relogin/readback/review, both receipt types and no automatic resubmission |
| Hostname/restart | Distinct titles for two devices; pending/active/stale states, cancel/timeout, wrong-device refusal and verified new boot |
| Actual served assets | Full production route/HTML/CSP/bundle path works in a real browser; no mocked route substitution hides dispatch failures |
| Resources and accessibility | Complete streamed documents, bounded connections, keyboard/labels/status, mobile/desktop, 200% zoom and long hostname/callsign |

Use existing test foundations: `tests/bootstrap_http_tests.cpp`,
`tests/network_browser_tests.js`, `tests/softap_api_tests.cpp`,
`tests/consumer_radio_tests.cpp`, bootstrap web Node tests,
`tests/consumer_commissioning.test.mjs`, `tests/consumer_sessions.test.mjs`,
`tests/consumer_recovery.test.mjs`, `tests/hostname_sessions.test.mjs`,
`tests/hostname_browser_integration.mjs`, and the production dispatcher fixture
in `tests/consumer_session_driver.cpp`. Verify filenames and test registration
at execution time. `consumer_bootstrap_driver` is built from that shared driver
with production bootstrap-server code; the session-only driver cannot serve
all page routes. Extend the correct fixture rather than accepting its 403 as
a product pass. Keep transport/board doubles explicit.

Commands below are existing starting points, **not preparation results**. Read
current development instructions and caches before using local dependency
paths. Use retained SDK/Mbed TLS/lwIP and locked Node dependencies. On macOS,
the P15.10 record used full Xcode via `scripts/xcode_env.sh` for host linking.

```sh
source scripts/xcode_env.sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF \
  -DWSPRRY_PICO_TEST_MBEDTLS_PATH=/Users/lbussy/GitHub/pico-sdk/lib/mbedtls
cmake --build build-host --parallel 3
ctest --test-dir build-host --output-on-failure
python3 scripts/validate_wtp_contract.py
npm --prefix src/network/bootstrap_web test
npm --prefix src/network/bootstrap_web run build
node tests/network_browser_tests.js
node tests/hostname_browser_integration.mjs build-host/consumer_bootstrap_driver \
  build/phase15-11-browser
```

Adapt/extend the real-browser workflow to cover the new organization; hostname
coverage alone cannot establish the entire matrix. Confirm actual fixture
routes and run in a bounded, isolated browser profile. Record screenshots of
both landing defaults, reciprocal navigation, key refusal/recovery states and
mobile/desktop rendering under light/dark preferences. The incumbent is a light
design; testing dark preference is not a claim that a dark theme exists. Use
Impeccable's bounded review/detector workflow and record tool limitations.

Run affected ASan/UBSan groups, using a separately configured sanitizer build
as documented in P15.10. macOS leak detection was unavailable there: record
the actual options and do not claim a leak check from `detect_leaks=0`.
Run the full executable host suite after the final repairs and report optional
skips explicitly. Use the retained pinned firmware setup to cross-link both
`WsprryPico` and `WsprryPico-StandaloneRF` and report size/resource deltas.
Do not install an SDK/toolchain incidentally. No physical operation is required
for this software slice; follow current operator setup/limits if separately
authorized hardware testing is requested, and record identity/restoration.

For supported Pi compatibility, inspect which adapters/contracts actually
changed. Preserve and exercise relevant exact source pairs from P15.10 using
the Pico-owned harness, unchanged Pi sources, real crypto and original fixed
vectors; record commands and scope. Do not retarget historical pins or claim
new Pi hostname UI support. Native Pi C++ validation belongs on an identified
Linux host/container or Linux CI; do not attempt macOS Pi C++ builds. If only
page layout changes, explain the bounded compatibility checks chosen; if API
or session behavior changes, run the affected genuine interoperability matrix.

### 9. Adversarial review, repairs and reassessment

After implementation and initial checks, perform a fresh adversarial code and
behavior review against the operator requirements and the acceptance matrix.
Use an independent reviewer when available and authorized; otherwise identify
the separate review pass honestly. Do not equate UI polish or a passing test
suite with adversarial assessment.

Try specifically to falsify the result through: AP-versus-LAN route confusion;
raw setup exposed to LAN; engineering auth bypass; duplicate/stale editors;
hidden-field browser validation; full PUT erasure of unseen values; profile
generation change mid-edit; two clients saving; session capacity churn from
page links; receipt/hash collisions; wrong-device navigation; lost commit
reply; cross-origin credential forwarding; automatic mutation/restart replay;
unreachable recovery/control; captive-browser missing crypto; redirect loops;
script/CSP/streaming failure; oversized literals; and RF/lease/admission changes.

For each actionable finding, record severity, exact location, reproducer,
impact, repair and regression. Fix it, rerun affected checks, then perform
another adversarial assessment of the repaired source. Repeat for substantive
findings until none remain actionable within the authorized scope. Do not
silently downgrade a failing test or weaken a production safety/deadline guard
to obtain a pass. Separate pre-existing limitations and explicitly deferred
work from repaired defects, with rationale. Keep visual polishing bounded;
functional/security repairs still require affected verification/reassessment.

### 10. Documentation, commit and push

Complete `docs/development/phase15-11-page-organization.md` with exact source
identities, selected route/ownership map, commands, failures/skips, repairs,
reassessment, screenshots, resource results and remaining physical limits.
Include **Documentation Impact** identifying Pico documents changed and exact
P15.14 operator instructions/screenshots still needed. Inspect the independent
operator-doc repository read-only as useful; do not edit/publish it here.

Update current browser/setup guidance, asset/design records where affected,
development index and roadmap to match delivered behavior. Keep historical
acceptance records intact and clearly identify supersession. Preserve P15.8's
operator-accepted closure, P15.10's scoped closure and P15.9's pending status. P15.12 main
identity, P15.13 RF/clock work and P15.14 publication remain separate.

Review final diff and `git diff --check`; stage only authorized Pico paths.
Commit on `devel` with a concrete description, then non-force push to
`origin/devel`. If concurrent remote commits exist, inspect and integrate
without discarding either contribution, rerun checks affected by integration,
then push. Independently verify the full remote SHA and report actual worktree
state, including preserved unrelated changes. Do not create a release, tag or
PR as a side effect. Report a blocked push honestly instead of claiming parity.

### 11. Final report

Report the selected organization and default behavior, lead repository, exact
implementation/tested/published pins, validation and limitations, adversarial
findings/repairs and final reassessment, documentation impact, push/parity and
worktree state. Link the complete evidence record. Mark P15.11 complete only
when its supported software acceptance is actually established; otherwise leave
it in progress with concrete remaining work. Do not claim physical captive
portal, Wi-Fi/RF qualification or independent Pi release completion from mocks,
browser emulation, source review or firmware cross-links.
