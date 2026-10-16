# P15.10 handoff: editable hostname and hostname-driven page title

Execution requested on 2026-10-16. See the [execution record](phase15-10-hostname.md)
for current implementation and acceptance. The following preparation status and
reviewed pins are historical.

Preparation status: **prepared; not executed** at the source review below.
This document records a source review and a prompt for a later executing
conversation. Preparation changes documentation only. It does not change
firmware/UI, rename a device, restart/flash hardware or run implementation tests.
The commit/push instructions below apply to the future execution.

## Lead repository, reviewed sources and scope

**WsprryPico leads.** It owns persisted device configuration/profiles, boot
selection, mDNS/DNS-SD, HTTP authority, consumer/TLS admission, embedded pages
and restart control. WsprryPi is a read-only compatibility reference unless
the operator separately coordinates a necessary companion scope. Do not move
device hostname authority into Pi or introduce another protocol repository.

Reviewed on 2026-10-16, with remote heads independently checked:

| Source | Identity and state |
| --- | --- |
| Pico devel | `5c7585c22f7d46e120fc4be4720c84a9e8dbecd6`, clean and remote-matching before preparation |
| Pico tested P15.8 implementation | `804e8a06585ec5a0e650e69fcd71ada398b6cc9f`; subsequent reviewed Pico changes are documentation/test-probe work |
| Pi devel | `af4ce3138177ac488421e7d45808e5c31a54ec4f`, clean and remote-matching at review |
| Unmerged accepted P15.8 Pi companion | `codex/p15-8-wspr-type23`, `6d5e73430bfbacdb8cfc29c3fe41089aa8ae5fcb` |

Pi's current step 14 is Type 2/3 integration; step 15 is P15.9 valid-field
saving. Their prompts are saved in Pi and are not executed by this handoff.
Pico tracks both as in progress pending their Pi portions. Refresh their real
implementation and release states before P15.10 execution. These source pins
are orientation, never instructions to reset or replace ongoing work.

The operator requested editable persistent hostname, LAN/mDNS access and the
hostname first in the browser-tab title. They additionally accepted that a
device restart may be necessary and suggested operator instructions with a
timed/timer reload. Implement an understandable saved/restart/reconnect flow;
elapsed time alone cannot establish that settings applied.

P15.11 page consolidation/connection-specific landing defaults, P15.12 prominent
main-page identity, P15.13 RF/clock qualification and P15.14 final operator docs
remain separate. The tab title is explicitly part of P15.10.

### Source review and implementation implications

These findings describe inspected code, not fresh runtime or physical results.

1. **A strict canonical grammar already exists.**
   `src/network/identity.hpp::canonical_local_hostname` accepts one ASCII LDH
   label of 1–63 characters plus `.local`, lowercases ASCII and accepts one
   final root dot. It rejects extra labels, whitespace/control bytes, wildcard,
   underscore, URL/port syntax and leading/trailing hyphens. It expects the
   `.local` suffix; accepting a bare label in a new editor needs an explicit
   conversion contract. `tests/network_tests.cpp::identities` binds boundaries.
2. **Stable hardware identity differs from an editable deployment name.**
   `default_hostname` derives `wsprrypico-<last-six-station-MAC-hex>.local`.
   `provisioning/access.cpp::derive_local_identity` also derives the AP SSID,
   BLE advertising name and initial password from that suffix. The full WTP
   device ID remains independent. Do not rename all those values by mutating
   LocalIdentity wholesale. `deployment_identity_matches` requires the actual
   device ID and a valid canonical hostname; it does not require a MAC-derived
   hostname, so deliberate aliases are already possible in credential bundles.
3. **The current portable responder is deliberately boot-configured.**
   `src/network/mdns.cpp::configure_hostname` refuses a different name after
   leaving Unconfigured; `tests/mdns_tests.cpp` explicitly tests that refusal.
   Conflict is latched, no automatic suffix is selected, and callback teardown
   is deferred. A restart-based rename fits this architecture and avoids an
   incidental live-responder reconfiguration project.
4. **Station and AP naming use different call sites.**
   `src/standalone/pico/main.cpp` constructs PicoNetwork from selected TLS
   credentials, supplies a MAC-derived hostname for network-only boot, and
   separately supplies `local_identity.hostname` to AP mDNS, local access and
   the consumer claim platform. Consumer TLS materialization and listener
   admission compare names again later. Changing one constructor argument
   leaves inconsistent future setup, AP or preclock paths.
5. **Persistent schemas do not expose a general editable hostname.**
   Config v1, its allowed merge fields and NetworkProfile do not have one.
   Engineering Profile and ConsumerProfile store a certified hostname in TLS
   material. Store reload and profile parsing are strict. A new setting needs
   one explicit authority, migration, readback and omission/reset semantics;
   a DOM field or a volatile network property is insufficient.
6. **Consumer setup deliberately preserves trust.**
   `consumer_claim_commit.cpp` preserves TLS and retained clients on station
   metadata edits and requires the profile TLS hostname to match the claim
   platform. Pending TLS materialization has the same hostname check.
   `pico/consumer_tls_generator.cpp::generate_consumer_tls` creates a new CA
   and server key/certificate. Calling it blindly for a rename would rotate
   existing trust. `consumer_tls_validator.cpp` checks exact name/SAN, device
   OU, CA/key pairing, validity and bounded sizes. Updating only `tls.hostname`
   cannot create a valid renamed credential set.
7. **HTTP and consumer sessions bind the selected authority.**
   BrowserApi validates canonical Host and same-origin HTTPS against current
   IP and the credential hostname; PicoServer sets its hostname authority from
   credentials. ConsumerRadioApi permits exact station IP/name or fixed AP IP.
   A changed station IP/name closes station sessions and recovery context;
   profile generations and boot changes independently invalidate sessions.
   Rename must not broaden Origin/CORS, authentication or admitted authorities.
8. **Discovery advertises the name and listener together.**
   PicoNetwork registers `_http` for consumer HTTP and `_wtp` for the admitted
   WTP listener, using the chosen hostname label. Port/binding changes use
   bounded withdrawal and reprobe. AP naming has a separate netif record;
   WTP is station-only. Preserve conflict handling, cleanup and single authority.
9. **Pages show a hostname but have generic browser titles.**
   `src/network/web/index.html` has static `WsprryPico · Station control`.
   `web/app.js::refresh` displays configured/advertised diagnostics but never
   assigns document.title. Bootstrap network, owner and recovery pages also
   have static titles. Bootstrap's `page-title` is an H1 changed by setup
   state, not document.title. Preserve that distinction and incumbent styling.
10. **The existing restart flow is reusable but insufficient for rename.**
    `web/app.js` sends one revision-guarded restart, then polls the original
    origin every two seconds for up to 90 seconds and checks a new boot ID.
    Its generic success does not compare the intended hostname. BrowserApi
    defers restart until response completion and rechecks idle; main's callback
    verifies output disable and schedules restart after 250 ms. A lost reply,
    newly acquired owner or an obsolete hostname can leave the result unknown.
11. **Recovery links already depend on the configured hostname.**
    `web/app.js::updateSetupReceipt` constructs an HTTP hostname continuation
    link containing only a nonsecret generation/digest receipt. Old pages,
    new-origin navigation and stale DNS need deliberate reconciliation. Browser
    same-origin rules mean a timer cannot simply fetch arbitrary new aliases
    with the old session; the current radio client is bound to its page origin.
12. **Appending hostname to identity v1 would break real clients.**
    Both `bootstrap_web/radio-client.js::identity` and Pi
    `src/wtp_integration/consumer_radio.cpp::connect` require exactly version,
    device_id, boot_id, generation and authentication. Pi also closes complete
    config/application schemas. Use an additive/versioned resource or a bounded
    device-derived presentation mechanism, preserving frozen response shapes.

Read [network identity](phase11-3-identity.md),
[mDNS implementation](mdns-responder.md),
[consumer LAN acceptance](consumer-lan-access.md),
[configuration updates](configuration-updates.md),
[browser API](../browser-api.md) and
[P15.7 recovery](phase15-7-recovery.md). Historical Phase 11 identity guidance
explicitly says runtime editing was absent and aliases required a new bundle;
update current guidance when delivered, while retaining historical acceptance.

## Prompt for the executing conversation

Implement **P15.10 — Editable hostname and hostname-driven page title** in
WsprryPico on **devel**. Deliver complete persistence, supported networking/UI
behavior, safe restart/reconnect, validation, documentation impact, adversarial
review, repairs, reassessment, scoped commits and push. Do not execute this
prompt merely because it has been saved or printed.

### 1. Refresh dependencies, work state and release scope

Read applicable AGENTS.md files and Pico README.md, CONTRACT.md,
docs/architecture.md and docs/development/README.md. Review all source seams
above, active P15.8/P15.9 work, profile/access/reset contracts and build inputs.
Inspect full configuration lifecycle and actual schemas before choosing storage.

Refresh branch/status/diffs/remotes and intervening commits. Preserve user and
parallel-chat work; no reset, stash, clean, force-push or incidental refactoring.
Use Pico devel and extend completed P15.9 facilities if they are now present;
do not recreate a competing draft/configuration authority. If P15.9 is still
pending, keep P15.10 independently compatible or record a specific dependency
instead of implementing P15.9 as an incidental prerequisite.

Pi devel, its step 14/15 branches and WsprryPi-Docs are read-only references by
default. Identify necessary Pi changes before editing: affected paths, strict
consumer shapes, source base, release timing, proposed isolated feature branch
(`codex/p15-10-hostname`), tests/pins/CI and publication order. Obtain the
operator's coordination decision unless existing authorization already covers
that exact scope. An approved companion scope permits feature-branch commits/
push, not Pi devel merge/push. Do not move the primary release checkout or
silently stack on/promote step 14/15 work. Do independent authorized Pico work
while coordinating. Do not message another conversation or maintainer without
direct operator authorization.

### 2. Define the name and profile contract

Provide an explicit browser hostname editor, save/readback and intentional
return-to-default action if supported. Reuse one canonical validator. The UI
may accept a bare label and append `.local`, or accept the full name; clearly
document the choice and enforce the same canonical stored value server-side.
Display the complete resulting address and actual supported length.

Keep WTP device ID, station MAC, MAC-derived stable default, editable saved
hostname, active boot hostname and advertised hostname distinct. Editing the
hostname must not rotate the device ID, Wi-Fi password, default password, AP
SSID, BLE advertising identity, client ownership or unrelated settings.

Document source precedence across compiled engineering bundles, engineering
profiles, consumer profiles, network-only state and legacy configurations.
Specify omission-to-preserve, explicit reset/clear, canonical no-op, revisions,
generation consumption, upgrade/rollback and reset-level behavior. Legacy
records must retain their prior effective name and valid access/trust.

Required product path: a normal committed consumer can change its hostname
through both infrastructure HTTP and the available authenticated AP radio
page without a maintainer reflash. Do not require unrelated WSPR/QRSS message
setup or credential replacement just to edit hostname. Address network-only
setup capability explicitly; preserve existing commissioning authority and
do not invent a partial consumer profile or unauthenticated management bypass.

Publish a profile/carrier support matrix before declaring completion. Certified
engineering deployments may require matching replacement credentials through
the established operator workflow. If arbitrary runtime rename cannot preserve
their external certificate authority, refuse it clearly and preserve working
access. Do not claim a universal runtime TLS rename or silently downgrade to
HTTP/Plain LAN. Keep supported consumer behavior complete and engineering
limitations concrete; do not expand into an unrelated certificate-enrollment
or CA-distribution system.

### 3. Implement bounded durable authority and TLS consistency

Use one authoritative persisted hostname selection through existing config/
profile coordination. Prefer a compatible additive resource/descriptor if old
Config/identity shapes cannot express it. Document proposed new routes/schema
names until implemented. Preserve atomic complete requests, unknown/duplicate
field refusal, secret redaction, password-null and unrelated-field preservation.

Include the selected hostname in the correct target/revision context. Require
fresh device/boot/profile/revision binding and idle/unowned/known-inactive,
healthy storage state. Check again at commit/deferred activation where needed.
Preserve STOP, enabled settings, cursors, pin restart/output-inhibition latches,
P15.8 frozen pairs and one JobService. Renaming grants no transmit authority.

Persist and reload without inventing station placeholders. Retain flash region
boundaries and bounded record, certificate, response, heap and stack sizes.
Test reset/purge, torn writes, corrupt records, exhaustion and wrong-device
profiles. If name and credentials span stores, prove their transaction/recovery
coherence; do not leave half-renamed authority after power loss.

For consumer TLS, preserve the established CA and retained client credentials
unless an explicit separately authorized trust replacement is selected.
Regenerate/reissue a matching server leaf safely when required; validate actual
SAN, key, issuer, device identity, validity/time and full serialized size before
commit. Calling the current fresh-CA generator is not a trust-preserving rename.
Retain pending-TLS/preclock handling and ensure later materialization uses the
chosen name rather than reverting to the MAC default. Failures must retain a
coherent previous deployment or explicit recoverable pending state.

Validate minimum and maximum names through real certificate generation,
serialization and reload, not only the string validator. Keep raw CA/private
key material out of public API, logs, errors and evidence artifacts.

### 4. Apply at restart and preserve discovery/admission

A device restart is an accepted application boundary. Prefer using it to keep
the old boot's name/credentials/listeners coherent until the new configuration
is ready. Avoid live rename complexity unless a concrete supported need
justifies and validates it. Save and restart remain clearly distinct actions,
or offer an explicitly labeled Save and restart action with the same guarantees.

Before restart, display saved versus active name and pending restart accurately.
On the next boot select the persisted name consistently for station mDNS,
admitted HTTP/HTTPS authorities, TLS material and applicable AP-local naming/
claim paths. Preserve stable recovery AP SSID/fixed IP and device identity.

Update DNS-SD hostname/SRV target/service instance consistently with the
admitted listeners. Preserve exact Host/Origin checks, same-origin rules,
listener-interface binding, session/generation invalidation and credential
verification. Do not allow arbitrary historical aliases or suffix matches.
An old name must not remain silently authorized indefinitely.

Keep conflict latching and no auto-suffix policy. Report saved/active name even
when advertisement failed; advertised remains empty until actual responder
success. Preserve direct-IP recovery where its carrier/TLS identity permits it,
explicit retry, bounded cleanup/withdrawal and network-off/recovery boot policy.
Discovery is a destination hint, never replacement trust or device identity.

### 5. Drive page titles from confirmed device state

The station-control browser title must begin with the device's authoritative
hostname, for example `pico-a.local - Station control`. It must work when opened
by IP as well as by hostname and distinguish two Picos in separate tabs.
Use validated device state, never the address bar, arbitrary Host header,
discovery label, unsaved input or browser storage as the source of truth.

Define and test title behavior for initial load/login, confirmed save, pending
restart, new boot, failed save, conflict and lost connection. A pending saved
name may be identified explicitly as pending; never imply it is already the
active/discoverable address. Unsaved edits must not change the title. Unknown
state needs an honest fallback; retaining a last-confirmed identity must be
labeled appropriately rather than presented as a fresh observation.

Use the same confirmed name for Wi-Fi/station/recovery page tab titles where
that surface can obtain it, with the relevant function suffix. Preserve their
existing H1/status semantics. P15.12's prominent main-page identity remains
separate. If useful hostname metadata must be available before login, choose
a bounded nonsecret presentation/versioned read mechanism without appending
fields to frozen identity v1; both shipped browser and native Pi reject that.

Use document.title/textContent or equivalent safe text presentation. Retain
static-asset streaming and memory admission; do not copy entire pages into
large per-request heap/stack buffers merely to template a title.

### 6. Deliver clear restart instructions and bounded timed reload

Include operator guidance like: "Hostname saved as pico-a.local. Restart is
required to use the new address. This page may disconnect; sign in again when
the Pico returns." Show the old active address, new saved address, available
same-device recovery route and explicit Restart/Continue actions.

Implement a bounded countdown/reconnect/reload assistance flow. Prefer reusing
the current one-shot restart, response-delivery callback and bounded polling
structure. A countdown describes the next check/navigation attempt, not a
guaranteed boot-ready time. Provide cancellation/manual continuation and
useful timeout/conflict/login guidance. A simple reload of an obsolete hostname
may fail after a successful rename; handle the changed origin deliberately.

Requirements:

- One explicit restart request, fresh revision, deferred completion and final
  idle/output checks. Duplicate clicks, lost acknowledgements, refresh or
  timer expiry must never repeat save or restart.
- Confirm the same full device ID, a changed boot ID and intended applied
  hostname through the appropriate fresh authenticated/validated readback
  before announcing success. A returning page or elapsed timer is insufficient.
- Keep save acceptance, restart requested, restart observed, settings applied,
  mDNS advertisement and browser reachability as separate observations.
- Respect browser origin boundaries. Old encrypted sessions/cookies are not
  portable login state for a new origin. Do not enable CORS, forward credentials
  or automatically reuse passwords to make a timer work.
- If using a navigation receipt, carry only bounded nonsecret expected device/
  name/boot context; validate it on return and gate automatic actions on the
  intended identity. An old alias resolving to a different Pico must not lead
  to automatic login, mutation or a false success notice.
- Generate URLs from canonical confirmed names and supported scheme/port.
  Preserve TLS verification. Direct-IP browser recovery requires valid IP SAN
  where HTTPS applies; an unusable certificate is not permission to downgrade.
- Preserve unrelated unsaved drafts. Avoid automatic navigation that discards
  them or persists secrets; require a clear operator choice where preservation
  cannot safely cross an origin. Cancel stale timers/requests on new edits,
  changed target, logout, cancellation or page lifecycle transitions.
- Use finite deadlines/backoff, one bounded navigation/reload strategy and
  visible manual links. No endless meta-refresh, background restart loop,
  blocking sleep or polling that monopolizes the bounded web service.

Retain P15.7 sent-once receipts, fresh readback/review, uncertain outcomes and
full-capacity login recovery. Do not infer that a save failed because a restart
closed the connection. Reconcile first, then permit a new explicit mutation.

### 7. UI, regression and compatibility validation

Use Impeccable for the hostname field, errors, saved/active feedback and restart
countdown. Follow installed skill setup once per executing session, preserve
incumbent styling and use its bounded visual workflow. Do not restyle/reorganize
pages or implement P15.11/P15.12 as incidental work.

Inspect existing development/test commands before running them. Pico's ordinary
host commands are:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON -DWSPRRY_PICO_BUILD_FIRMWARE=OFF
cmake --build build-host --parallel 3
ctest --test-dir build-host --output-on-failure
python3 scripts/validate_wtp_contract.py
npm --prefix src/network/bootstrap_web test
npm --prefix src/network/bootstrap_web run build
```

Supply verified retained Mbed TLS/lwIP paths with the existing CMake options
for genuine crypto, production bootstrap and actual responder coverage; inspect
test enumeration so missing dependencies/skips cannot look like full coverage.
Read the mDNS guide for `mdns_tests`, `mdns_lwip_tests` and
`network_adapter_tests`. Reuse maintained real served-page/production-driver
fixtures and extend them for this behavior instead of relying on mock DOM alone.

Required tests include:

1. Canonical label/full-name policy, case/root dot, 1/63/64 boundaries, invalid
   labels, URL/IP/port/whitespace/control/non-ASCII input and injection attempts;
   no truncation or unrelated-field changes.
2. Verified save/reload/reboot, defaults/source precedence, reset levels,
   corrupt/torn/exhausted storage, wrong device, stale/missing revisions,
   A/B/A and same-value writes, duplicate or malformed fields.
3. Consumer station/AP changes, supported network-only/setup cases, frozen
   engineering deployment behavior and profile-owned write refusal.
4. Actual old-CA/client-trust continuity, regenerated leaf SAN/key/name,
   certificate size/time boundaries, pending materialization, crypto failures
   and rollback/reconcile after each commit boundary.
5. Boot selection across all hostname call sites, real pinned responder packets,
   DNS-SD target/instance, AP/station distinction, conflicts, address changes,
   withdrawal/cleanup and memory/resource refusal.
6. Old/new Host and Origin matrices, IP/name cross-alias refusals, DNS rebinding,
   session closure/relogin, generation/boot binding and three-client contention.
7. Real document.title on IP/name access, two device contexts, unsaved/failed/
   confirmed saves, pending restart, reconnect and stale/malicious metadata;
   frozen identity responses still accepted by unchanged browser/Pi clients.
8. One-shot restart and canceled delivery, ownership acquired before callback,
   lost acknowledgement, timeout, no new boot, wrong returning device, new IP,
   stale/conflicting DNS, certificate failure, canceled countdown, reload/back/
   pagehide and preserved drafts. Assert no extra POST/job/reset from timers.
9. No change to STOP, scheduler enablement, pins, experimental flags, watermark,
   P15.8 plans/pair continuation, RF timing ownership or unrelated credentials.

Run full relevant host/regression suites, affected ASan/UBSan and actual browser
flows. Inspect desktop/mobile, supported light/dark preferences, keyboard,
200% zoom, max-length names, long errors, countdown/cancel/manual recovery and
two-tab titles. Fix observed defects in a bounded batch and confirm once.
Keep screenshots/secrets outside Git; a source assertion is not a visual check.

Cross-link both standard RF-inhibited and StandaloneRF Pico 2 W images using
retained pinned SDK/toolchain inputs. Check flash topology, certificate/profile
limits, stack/heap budget and core-0/cooperative-service/RF-core isolation.
Report compile/link budgets separately from measured target timing/memory.

Test unchanged release Pi and the actual approved/current Type 2/3 companion
against the new Pico: existing reads/saves/login must remain compatible, new
unsupported operations must refuse explicitly, and destination/expected TLS
identity/device ID must stay distinct. Preserve historical compatibility rows;
freeze any superseded accepted current source rather than retargeting history.
If approved Pi edits are needed, inspect its current Makefiles and simulated
backend contract and use an identified Linux environment or Linux CI for C++
validation; do not retry local macOS Pi C++ compilation/linking. Local JS/Python/
docs remain available.

Pico currently has no checked-in Actions workflow, only a PR template. Run
applicable existing cross-repository CI only within approved companion scope;
do not invent a passed Pico CI run or silently add a new pipeline. Verify any
claimed CI on its exact pushed source pair/head and retain strict audits.

Default acceptance is hardware-free. No flashing, GPIO, RF, installation or
service operation is authorized by prompt execution alone. Follow current
operator setup statements/finite limits if separately authorized. Separate
software mDNS packets, actual browser navigation, operational LAN resolution,
physical restart/transport and RF qualification in the report.

### 8. Documentation and adversarial assessment

Create docs/development/phase15-10-hostname.md with the implemented name/source/
profile/TLS/activation model, exact commands/source pairs, results, resource
limits, failures/repairs, browser evidence and remaining acceptance. Update
current API/config/standalone/identity/mDNS guidance and roadmap accurately;
retain historical contracts/evidence with clear supersession notes.

Inspect WsprryPi-Docs read-only, especially Transmitter setup's Pico settings,
saved/restart/network sections, configuration troubleshooting and network
safety. Record exact P15.14 operator text/screenshots: choose a name, saved vs
active, restart countdown, new address/login, timeout, duplicate name, IP/AP
recovery and engineering certificate limitations. Do not edit that independent
repository without coordinated authorization. Final user-facing instructions
belong there; keep development repair narration in the acceptance record.

After implementation and affected checks, perform a fresh adversarial review.
Use an independent reviewer when available; label self-review accurately if
that is the actual method. Supply exact source/diffs, requirements and evidence.

Challenge name authority and storage/profile/TLS atomicity; CA/client trust
rotation; delayed materialization restoring a default; stale admitted aliases;
wrong-board credentials; Host/Origin relaxation; frozen identity shape breaks;
title spoofing; partial-success wording; unbounded resource use; concurrent
save/restart/owner races; stale timers; cross-origin credential leakage;
unsaved-draft loss; obsolete-name reload; returning wrong device; premature
success from countdown; and accidental job/STOP/cursor/release-scope changes.

Record severity, trigger, code, repair and meaningful regression for each
actionable finding. Repair within scope, rerun affected checks and reassess
the repaired final state. Repeat until no actionable findings remain. Preserve
unresolved authority/release decisions as open; narrative alone cannot close a
finding or turn missing physical/CI evidence into acceptance.

### 9. Commit, push and return the evidence packet

When the operator executes this prompt and implementation/checks/review are
complete, inspect final diffs, stage only P15.10 work, commit and push Pico devel
without force. Publish validated immutable dependency pins before approved
companion CI needs to fetch them. Commit/push only explicitly approved Pi
feature branches; no Pi devel merge/push or operator-docs publication under
default authorization. No release/tag/PR is required.

If applicable CI finds a defect, repair it, rerun affected checks, reassess and
push scoped follow-ups. Independently compare remote hashes and inspect every
touched checkout's staged/unstaged/untracked state. Distinguish implementation
pins, later documentation heads, branch tests and release integration.

Report delivered behavior, lead repo/branches/source pairs, name/profile support,
restart/countdown/reconnect semantics, tests/skips/CI, Impeccable/browser evidence,
adversarial findings/repairs/final reassessment, commits/push/parity, actual dirty
state and limitations. Include Documentation Impact: updated, considered
unchanged and still required. Do not mark P15.10 complete until its supported
software acceptance is satisfied; retain explicit engineering/physical gates.

Provide the packet for any separately requested originating post-execution
assessment. Do not claim that later review happened, message another chat or
schedule background continuation without operator authorization. Preparing or
reading this handoff does not execute it.
