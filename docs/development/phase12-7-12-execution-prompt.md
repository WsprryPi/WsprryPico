# Phase 12.7-12.12 gated execution prompt

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`. Complete the remaining
Phase 12 consumer commissioning and Stage A work in milestone order. This prompt
is an execution plan, not approval of an unselected security design or standing
authority to operate a device.

On 2026-09-26 the operator paused Bluefy work. References below to a Bluefy
client or a Bluefy-to-Safari handoff describe the earlier draft, not an
approved implementation target. Select the phone client and revise the P12.7
contract and P12.9 scope before implementing those steps. Preserve the
selected certificate-free provisioned SoftAP direction unless the operator
changes it.
The later [Wi-Fi-only network bootstrap proposal](phase12-wifi-only-bootstrap-proposal.md)
is a separate design-only candidate for blank-device station joining through
an open SoftAP. It proposes a best-effort captive-browser launch with a Safari
fallback; only the read-only captive landing is implemented. Its one-purpose
physical and encrypted submission path needs
an explicit P12.7 exception to the current read-only blank-AP and
factory/device-secret rules before any implementation; it does not grant
owner, TLS or job authority and does not close phone commissioning.

## Starting state and source of truth

Inspect branch, HEAD, upstream, worktree status and the complete diff before
editing. Preserve the current uncommitted `docs/development/phase12-plan.md`
roadmap and every unrelated user change; do not reset, stash or overwrite them.
Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `SECURITY.md`,
`docs/architecture.md`, `docs/development/README.md`, the Phase 12 roadmap,
field-access contract, Field-GATT/1 contract and vectors, physical plan, current
Bluefy source and release pipeline, P12.3-P12.6 reviews, and the bounded
Candidate A activation record. Inspect the access/profile/reset journals,
provisioning manager, BLE/GATT admission, TLS validator/server, activation
boundary, LED controller, SoftAP coordinator, `JobService`, WTP transport and
RF-inhibit configuration before designing changes.

Treat `docs/development/phase12-plan.md` as the milestone order. The existing
field-access contract and Field-GATT/1 remain the implemented engineering
baseline until an approved P12.7 contract explicitly supersedes particular
rules. An incompatible GATT wire change needs a new protocol version and
corresponding firmware, client, vector and documentation migration. Preserve
WTP/1 as device-neutral and USB CDC as canonical/reference; authenticated TCP
remains a first-class carrier for the same one `JobService`.

## Authority and stopping rules

P12.7 is design and documentation only. Present the complete state, UX and
security decision for operator approval. Do not implement commissioning until
that approval is recorded. Do not infer approval from this prompt or from an
older engineering password/PEM workflow. If any user-visible ceremony or trust
path remains unresolved, keep P12.8 blocked and report the exact choice.

Hardware-free source edits, deterministic tests and cross-builds are allowed
after P12.7 approval. Before any flash, USB device control, runtime BOOTSEL
sampling, GPIO operation, BLE/Wi-Fi/SoftAP operation, phone trust change, reset
or other live action, obtain explicit authority for that intended action and
record its finite device/image/budget boundary. No Phase 12 step grants RF
output, `LOAD`, `ARM`, Stage B or Phase 13 authority. Never use mock or host
results to close a target-runtime row. Stop immediately on unknown/active
output, unhealthy journals, wrong device/image, unexpected RF, trust
resurrection or an unrecoverable restoration state.

Keep Wi-Fi secrets, key material, cookies, raw access sectors and authenticated
captures out of Git, chat, command history and credential-free evidence. Use
the pinned SDK/toolchain already available; do not download dependencies as an
incidental step. Do not edit another WsprryPi-family repository.

## P12.7: approve the consumer contract before code

Write a decision record and update the roadmap, field-access contract,
Field-GATT compatibility plan, Bluefy screen flow, recovery semantics and
Stage A case list **only after the operator accepts the design**. Before that,
label all proposals plainly and leave the implemented baseline intact. Cover:

1. The five-screen-or-fewer journey: power on, select in Bluefy, physically
   confirm the identifying Pico, enter ordinary Wi-Fi and station settings,
   then see Setup complete only after committed and independently verified
   readback. No MAC-derived password, per-device setup code, QR scan, pairing
   PIN, full device ID, JSON, PEM, USB command, second password or protocol
   session ID in ordinary setup.
2. An exact stock Pico 2 W runtime physical claim gesture. BOOTSEL held during
   boot enters ROM; any runtime BOOTSEL sampler must first prove safe with both
   cores, flash/XIP, journals and radio scheduling. Define press duration,
   debounce, timeout, LED feedback and what an unsafe or unavailable sampler
   does. Bind one gesture to the displayed identity, encrypted connection,
   provisional bond, boot, request nonce and one claimant. Pairing alone is not
   ownership.
3. The minimal Wi-Fi and station fields and defaults. Separate these from
   advanced time, TLS, port and protocol settings. Define validation, no-Wi-Fi
   behavior and retention of existing station/schedule/watermark data.
4. Device TLS key/certificate origin, entropy and clock requirements, renewal,
   replacement and reset lifetime. Define how the first owner and a station
   client authenticate the new server, and how later mTLS clients enroll,
   rotate and revoke, without certificate administration in ordinary setup.
   Do not call self-signed HTTPS silently trusted by Safari/Bluefy.
5. Whether the old application password is retired from consumer authority or
   remains only a hidden bounded implementation proof. Define a high-entropy
   provisioned SoftAP credential and an authenticated browser fallback that
   works under the selected phone trust model; keep blank SoftAP read-only.
   The operator selected certificate-free Safari/HTTP on a device-specific
   WPA2 SoftAP with a BLE-owner-authorized browser session. Before approving
   that path, demonstrate a code-free iPhone WPA2 join from the Bluefy flow
   and an owner-to-Safari session handoff. Migrate the provisioned AP-only
   HTTP policy, cookie and Origin rules and secure-context-dependent browser
   code deliberately; preserve station mTLS/HTTPS and blank read-only HTTP.
   If the join or handoff cannot be demonstrated, return to design rather than
   substituting password entry, a certificate installation or a native app.
6. Retained owner bond reconnect, second-phone admission, deliberate removal,
   four-bond capacity, no silent eviction and lost-owner recovery. Define the
   exact physical actions and independent confirmation for access recovery,
   provisioning reset and full operational erase, including all power-cut
   outcomes and data preserved or erased.
7. Delivery-safe success, retry and unknown-result language before write,
   after commit and after response loss. Define generation readback, reboot,
   station readiness, TLS and owner reconciliation. The UI must never present
   Setup complete on a merely sent request.

Adversarially review the proposed contract for active MITM/relay, wrong-device
claim, same-suffix collision, concurrent claimant, lost owner, rollback,
physical access, public default reuse, untrusted page origin and secret
exposure. Resolve every material user-facing decision with the operator before
P12.8. Document the accepted date and exact contract revision; an agent cannot
self-approve it.

## P12.8: commissioning foundation

After P12.7 approval, implement portable state machines under `src/` and Pico
adapters only where needed. Make a blank device advertise an explicit setup
state without using its name/MAC suffix as identity proof. Admit exactly one
encrypted provisional claimant; bind physical confirmation as approved; promote
the bond to owner only when the claim succeeds durably. Generate or install the
approved per-device identity and authenticated station/client trust without
exposing keys. Validate ordinary settings as one transaction, commit exactly
one new generation, preserve unrelated stores, defer activation past terminal
response delivery or its bounded timeout, and recover after power loss to a
complete generation or fail-closed state. Scrub transient materials on every
terminal path. Keep authorization and journal logic outside the transport and
Pico SDK adapters.

Test wrong device, claimant race, expired/duplicate/replayed press, bond
deletion failure, entropy/clock failure, invalid settings, journal cuts at
every marker, response loss, activity drift, busy/output-unknown refusal,
network activation failure, reboot and secret-free status. Verify the owner
cannot gain WTP/RF authority merely by claiming the device. Run documented
host tests, supported sanitizers, WTP validator and affected target builds;
inspect flash/RAM and linked symbols. Source results do not close physical
gesture, TLS, BLE or network behavior.

## P12.9: guided Bluefy setup

Implement one linear, accessible Bluefy path in `src/provisioning/web`; rebuild
`docs/bluefy` through the repository release script. The chooser filters the
service; the page reads the full identity internally on an encrypted link;
Identify and physical claim refer to that exact device. Connect accepts only
the approved Wi-Fi/station fields and submits the one commissioning transaction.
Setup complete requires exact device, committed generation, reconnect, owner
and network-readiness evidence. Preserve release integrity and offline cache;
no external scripts, analytics or persistent secrets. Clear secrets after
success, cancellation, rejection, expiry, reload and uncertain transport loss.
Do not render internal operations, IDs, PEMs, profile JSON, a default-password
prompt or USB commands in the consumer flow. Keep clearly separated engineering
tools if their continued use is approved.

Test all screen transitions and keyboard/screen-reader behavior, chooser
rejection, wrong device, back/cancel/reload, lost link at each transaction
boundary, unknown result reconciliation, owner reconnect, repeated Connect and
activation failure. Test source and built release assets, hashes and offline
behavior deterministically. Review both firmware and browser state transitions
adversarially, repair and rerun affected checks.

## P12.10: bounded RF-inhibited first-run acceptance

Only under separate exact hardware/phone authority, prepare a clean committed
RF-inhibited image and identify Candidate A by USB serial
`0BF4B4AEC9FFB344`, device ID `fd6127d11d6aca42a9905fa3fb1bf1d5`, current
firmware/UF2 hash, boot ID and engine. Candidate B (`CDDBF8767C506C07`) is
observation-only. Verify inactive output, empty/unowned `JobService`, healthy
journals and restoration plan before each mutation. Record the actual iPhone,
iOS and Bluefy versions and exact release hash rather than reusing historical
versions as current facts.

From a documented blank/no-owner state, prove offline page reuse with Wi-Fi and
cellular disabled, select/Identify/physically claim Candidate A, enter ordinary
settings and commit generation 1 entirely from the iPhone without an operator
console, manual ID, default password, file or certificate. Preserve the terminal
response boundary, reboot/reconnect, owner and generation readback, station
association, DHCP/mDNS, controller time and positive mTLS WTP/HTTPS readback
through the separately documented station-client trust path. Verify preserved
station/schedule/watermark stores and continued RF inhibit/output inactivity.
Candidate A has historical runtime profile generations, so do not assume that
its present state can be called blank or that an ordinary reset yields generation
1. Before the first-run row, document the authorized state-preparation method,
backup and restoration of preserved stores, exact generation semantics and why
it yields a genuinely uncommissioned device. If that cannot be established,
leave the generation-1 row unaccepted.
Run a finite named wrong-device, competing claimant, cancel, response-loss and
power-cut matrix. Retain each failed attempt and its exact firmware/client
identities; do not relabel a retry as the original pass.

## P12.11: ownership, recovery and SoftAP fallback

Implement and accept second-phone enrollment after fresh physical action,
capacity/full-slot behavior, deliberate removal and no silent eviction. Prove
lost-owner access recovery without the old phone. Prove distinct access
recovery, provisioning reset and full erase with correct state preservation,
tombstones, bond revocation, interrupted-reset resume and post-reset
advertisement. Keep blank SoftAP read-only and provisioned SoftAP authenticated
under the approved trust/credential model. Do not treat public bootstrap HTTP
as a credential submission path. A no-BLE commissioning request requires a
separate approved secure-bootstrap design.

## P12.12: Stage A robustness and closure

Complete the remaining finite RF-inhibited acceptance ledger: malformed,
replay, timeout and journal interruption; trust supersession and credential
rotation; BLE/TCP/WTP/HTTPS concurrence with one owner and one `JobService`;
controller-time disagreement; full LED priority and faults; heap, stack,
lwIP/BTstack pools, TLS allocation, flash serialization, reclamation and soak.
Record exact source, image, device, client, clock, mode, setup, case and result
for every accepted row. End disconnected, provisioning closed, SoftAP stopped
when no cause remains, healthy journals, empty/unowned, RF-inhibited and output
inactive; explicitly report any restoration limitation.

Conduct an adversarial source, UX, security, evidence and restoration review.
For each actionable finding: repair, rerun affected tests and physical rows,
then perform another independent adversarial assessment. Do not close Phase 12
while a required Stage A row lacks exact current-image evidence. Stage B RF
coexistence and Phase 13 remain separate.

## Publication

Record accepted design, implementation, tests, failed attempts, physical
evidence, findings, repairs, reassessment and limits in the repository. Run
`git diff --check` and verify changed Markdown links. Review the final diff and
status. Commit only this requested slice on `devel`, push to `origin/devel`,
and verify remote parity. If a milestone is blocked, commit and push only a
truthfully labeled bounded deliverable when requested; report the exact gate
and do not claim P12.7-12.12 or Phase 12 closure.
