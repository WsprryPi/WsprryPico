# Phase 12 remaining work: gated execution prompt

Status: **EXECUTION RESUMED 2026-09-27; P12.7 DESIGN APPROVED; WI-FI-ONLY
GENERATION-1 READBACK PASSED; P12.8–P12.12 OPEN**. The operator directed resumption of all
Phase 12 milestones. Execute the hardware-free implementation and review gates
continuously. Record each milestone's actual evidence and continue to the next
independent task. A live-device gate needs action-specific authority and cannot
be satisfied by a source build. This prompt is not standing authority for
unspecified live hardware operations.

Work in `/Users/lbussy/GitHub/WsprryPico` on `devel`. Complete the remaining
Phase 12 consumer commissioning and Stage A work in milestone order. The
[P12.7 decision](phase12-7-decision.md) is the accepted consumer design;
this prompt is not standing authority to operate a device.

The operator selected **Safari and SoftAP only** as the consumer client on
2026-09-27 and approved the revised
[P12.7 contract](phase12-7-consumer-commissioning-proposal.md). Preserve the no-code,
no-certificate-installation and physical-claim decisions. The
[Wi-Fi-only bootstrap](phase12-wifi-only-bootstrap-proposal.md) is a separately
approved exception that is now source-implemented on `devel` at `fb091f8`.
Its exact [transaction review](phase12-wifi-only-transaction-review.md) leaves
target acceptance open. It grants network join only, no owner, TLS, station
API, job or RF authority. Candidate A passed the exact `fb091f8`
RF-inhibited transaction image's isolated-Pi open-AP preflight
and selected-iPhone network-only generation-one reboot readback; final phone
page and AP-return rows remain open in the
[target record](phase12-wifi-only-physical-result.md).
Candidate A now retains the newer RF-inhibited `3f56f5e` core-1 BOOTSEL
diagnostic. Its [target result](phase12-8-bootsel-window-target.md) observed
one human press/release, healthy core-1/flash continuity and AP recovery.
The operator removed the timed-hold requirement; the revised source has not
been flashed or integrated with Safari claim.

## Starting state and source of truth

Inspect branch, HEAD, upstream, worktree status and the complete diff before
editing. The original continuation started from `fb091f8`. This execution
resumed from clean, pushed `devel` `040eaee`, after the approved P12.7
decision, inert profile journal, portable claim slot, Owner-HTTP signing
digest, single-use challenge and P-256 verifier. Verify current state before
editing; preserve subsequent changes. Do not reset, stash or overwrite them.
The BOOTSEL diagnostic checkpoint is `3f56f5e`; the physical result and
ordinary press/release correction are committed at `6baef03`, and the
canonical owner-session transcript at `d126c6f`. Current work must be
inspected from the actual `devel` HEAD and worktree, not inferred from those
historical hashes.

The current P12.8 source checkpoint adds a Pico-compatible, device-bound
P-256 CA and separate server certificate generator, plus a persisted-material
validator and host failure tests. It is deliberately disconnected from the
claim route and journal activation. The generator requires a trusted UTC input;
its numerical range check does not itself establish clock trust. Its host
certificates fit the Consumer-Profile/1 TLS cap, and the Pico cross-build
passes. Heap/stack use and generation latency on the exact target remain
unmeasured. See the [TLS checkpoint review](phase12-8-tls-review.md).

## Immediate P12.8 execution packet

1. Close the remaining Owner-HTTP/1 wire ambiguities before enabling a route.
   The operation registry, method/path binding, session-finish transcript,
   challenge consumption and signature vectors are already committed. Freeze
   the claim AEAD transcript, plaintext/defaults and exact encoded versus
   decoded body bounds; generate independent browser/host vectors. Then cover
   altered device, boot, source, generation, slot, key, nonce, request, body,
   sequence and signature cases. Keep owner requests on the AP interface only.
2. Implement the portable admission and one-request state machines with hard
   body/slot/capacity bounds, monotonic deadlines, one claimant, one live owner
   session, duplicate/replay rejection and secret scrubbing. Wire the Pico
   X25519/HKDF/ChaCha20-Poly1305 and P-256 verification adapters to the
   pinned crypto library. No parsed or authenticated result may bypass exact
   current profile/access journal, full identity, inactive output, owner epoch
   and generation checks.
3. Connect the existing on-device CA/server generator and persisted-material
   validator only after a trusted, bounded UTC reading and measured entropy
   are available. Validate key/cert pairing, SAN, EKU, serial, validity and
   exact device identity before any journal write. Measure generation
   latency, heap and stack on the exact target before making the route live.
   Implement owner/client trust activation from the committed consumer source,
   with all engineering password/GATT/factory mutation authority cut off.
4. Implement one transactional claim: trial Wi-Fi and DHCP, validate ordinary
   station fields, stage owner and TLS materials, commit one consumer generation,
   deliver a terminal result, then activate or safely recover after a cut. On
   unknown result, read back exact request digest, owner key digest, generation,
   station and trust; never retry a consumed mutation.
5. Build the Safari page only after the route and vectors pass. Keep it under
   five screens, offline bundled, full-ID-indexed and free of codes, PEMs,
   certificates and manual protocol fields. Prove persistent owner-key write,
   readback and sign/verify on the selected iPhone before any claim.
6. Carry the observed core-1 physical press/release safety into a Safari
   owner claim without a user-timed hold. The historical short-sample image
   failed; the later whole-gesture diagnostic survived a human press and AP
   recovery. Prove the prompt is delivered before entering the bounded
   flash-safe zone, then prove exact grant/release readback on the later
   implementation image. A source cross-build or the diagnostic alone cannot
   close that end-to-end gate. Request action-specific live authority for each
   later image and retain failed runs. Never perform RF output here.
7. Complete P12.10 phone acceptance, P12.11 owner/recovery lifecycle and
   P12.12 Stage A matrix in milestone order, keeping every exact-image failure
   in the record. Review adversarially, repair actionable findings, rerun
   affected checks, then reassess. Commit and push only truthful validated
   checkpoints to `devel`; never label an intermediate source build Phase 12
   closure.

Work through these gates in order. Continue independent source and documentation
work when a later physical gate is unavailable; report every unsatisfied exit
gate honestly. Do not substitute speculative threat work for the measured
BOOTSEL, AP continuity, transactional activation and iPhone checks. The
operator accepted the P12.7 physical-extraction and active-relay limits.
Read `AGENTS.md`, `README.md`, `CONTRACT.md`, `SECURITY.md`,
`docs/architecture.md`, `docs/development/README.md`, the Phase 12 roadmap,
field-access contract, Field-GATT/1 contract and vectors, physical plan,
current SoftAP/browser source and release pipeline, P12.3-P12.6 reviews, and the bounded
Candidate A activation record. Inspect the access/profile/reset journals,
provisioning manager, BLE/GATT admission, TLS validator/server, activation
boundary, LED controller, SoftAP coordinator, `JobService`, WTP transport and
RF-inhibit configuration before designing changes.

Treat `docs/development/phase12-plan.md` as the milestone order. The existing
field-access contract and Field-GATT/1 remain the implemented engineering
baseline until an approved P12.7 contract explicitly supersedes particular
rules. The approved Wi-Fi-only exception is narrow and source-implemented;
do not misreport its unaccepted physical status or recast it as an owner claim.
An incompatible GATT wire change needs a new protocol version and
corresponding firmware, client, vector and documentation migration. Preserve
WTP/1 as device-neutral and USB CDC as canonical/reference; authenticated TCP
remains a first-class carrier for the same one `JobService`.

## Authority and stopping rules

P12.7 was design and documentation only; its exact Safari/SoftAP decision is
now recorded. P12.8 implementation may proceed only against that contract,
after versioning the [Owner-HTTP/1 wire](../protocol/Owner-HTTP-v1.md) and
[Consumer-Profile/1 storage/migration rules](../protocol/Consumer-Profile-v1.md).
Do not infer
new authority from the older engineering password/PEM workflow. If a hard
provisioned BOOTSEL or Safari feasibility gate fails, return to design.

Hardware-free work on the approved Wi-Fi-only exception and P12.8 design/code
is allowed. Before
any flash, USB device control, runtime BOOTSEL
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

## Separate Wi-Fi-only target result and remaining rows

The network-only path is an approved exception to the P12.7 commissioning
gate. Candidate A's **historical network-only transaction image** was
`fb091f8`, UF2 SHA-256
`d262c9a92a0b7ec3be4739e50e39c8b7ac59a80f25863e4bf840e40b38a18ce2`.
The selected iPhone made one BOOTSEL-confirmed credential submission, and
the approved single reboot independently selected network-only generation 1,
rejoined at `192.168.1.47`, and reported empty/inactive output. See the
[target record](phase12-wifi-only-physical-result.md). Do not repeat the
flash, button press or credential submission as routine setup.

The later source change keeps the network-only AP available after station
join for Safari owner upgrade. At the pushed P12.7 checkpoint, its unflashed
UF2 was SHA-256
`3be01934bde3c8c337629b964fc76cc0fbc45715b126a25b988d737e17f1efda`.
The current P12.8 structural-source and fail-closed runtime cross-build
produced an unflashed UF2 SHA-256
`d2988dbf3a930b3c60b3f851f13651fa32c0e1812a41c3ae6f3eca0f5121b97f`.
The P12.8 portable-claim build overwrote that build path with an
unflashed UF2 SHA-256
`7849b5b041e3212c032dcef8f65c6223d16c785170f71aceb34924d0c9ca1c39`.
Candidate A now retains the later RF-inhibited `3f56f5e` core-1 diagnostic,
UF2 SHA-256
`03611155a0f7302d5fe4ad069e6a2c18d8872dcd2dc1fd7a0a541400ab428c66`.
Its physical press/release and AP recovery are recorded, while the current
source correction and Safari claim integration remain unflashed and unaccepted.
A future exact new flash or
other live operation requires action-specific authority and fresh device,
source, hash, journal, output and inhibited-engine admission.

The iPhone did not show a final connected screen after switching networks;
the model/iOS build was not reconfirmed and AP return after station loss was
not exercised. Record those as open UX/fallback rows. Do not infer a failed
commit from the stale pre-reboot `INFO` snapshot. Any future failure/retry
test needs a concrete risk and finite authority; avoid repeated button
presses and routine rollback to an older image.

## P12.7: accepted consumer contract

The decision record and roadmap now carry approval. During P12.8 update the
field-access contract, HTTP/Field-GATT compatibility plan, Safari screen flow,
recovery semantics and Stage A case list without rewriting historical
engineering evidence. The accepted contract covers:

1. The five-screen-or-fewer journey: power on, join the open AP and continue in
   Safari, physically confirm the identifying Pico, enter ordinary Wi-Fi and station settings,
   then see Setup complete only after committed and independently verified
   readback. No MAC-derived password, per-device setup code, QR scan, pairing
   PIN, full device ID, JSON, PEM, USB command, second password or protocol
   session ID in ordinary setup.
2. An exact stock Pico 2 W runtime physical claim gesture. BOOTSEL held during
   boot enters ROM; any runtime BOOTSEL sampler must first prove safe with both
   cores, flash/XIP, journals and radio scheduling. Make a normal press and
   release sufficient without asking the user to time it. Define device-side
   debounce, stuck-hold timeout, LED feedback and what an unsafe or unavailable sampler
   does. Bind one gesture to the displayed full identity, AP-local Safari
   origin, browser owner public key, boot, request nonce and one claimant.
   An AP association alone is not ownership.
3. The minimal Wi-Fi and station fields and defaults. Separate these from
   advanced time, TLS, port and protocol settings. Define validation, no-Wi-Fi
   behavior and retention of existing station/schedule/watermark data.
4. Device TLS key/certificate origin, entropy and clock requirements, renewal,
   replacement and reset lifetime. Define how Safari retains an owner key and
   how a station client authenticates the new server and later mTLS clients enroll,
   rotate and revoke, without certificate administration in ordinary setup.
   Do not call a self-signed station certificate silently trusted by Safari.
5. Whether the old application password is retired from consumer authority or
   remains only a hidden bounded implementation proof. Define authenticated
   provisioned SoftAP fallback for Safari, with no setup code,
   manual certificate installation or extra password prompt. The prior
   WPA2 plus BLE-owner handoff is superseded by the Safari-only selection.
   Specify an open, available provisioned AP with full-ID browser-key authority,
   physical gates for sensitive actions and the accepted active-page-replacement
   limit. Record that all Pico APs share the numeric Safari origin and a
   malicious page from one can read other Pico owner keys stored there. Verify
   full-ID indexing and first-use behavior; do not claim origin isolation.
   Preserve station mTLS/HTTPS. Until P12.7 approval and implementation, the
   current blank AP accepts only its approved encrypted Wi-Fi-only transaction,
   never owner, trust, station settings or job commands.
6. Retained Safari owner-key reconnect, second-phone admission, deliberate
   removal, four-key capacity, no silent eviction and lost-owner recovery. Define the
   exact physical actions and independent confirmation for access recovery,
   provisioning reset and full operational erase, including all power-cut
   outcomes and data preserved or erased.
7. Delivery-safe success, retry and unknown-result language before write,
   after commit and after response loss. Define generation readback, reboot,
   station readiness, TLS and owner reconciliation. The UI must never present
   Setup complete on a merely sent request.
8. The network-only upgrade path. The current network-only AP withdraws after
   ACK or a timeout; Safari-only full setup would then be undiscoverable while
   station Wi-Fi is healthy. Decide whether that AP remains available until
   full commissioning, and validate the AP/STA resource and channel cost.
   Record generation 2 for upgrade after network-only generation 1.
9. Provisioned AP availability. Safari/SoftAP is the sole consumer owner
   client, so a fallback-only AP would strand owner management whenever the
   station link is healthy. Select the always-available consumer AP and prove
   its network/resource budget; preserve RF-inhibited Stage A before any
   separately authorized RF coexistence claim.

The [design review](phase12-7-proposal-review.md) adversarially examined the
contract for active MITM/relay, wrong-device
claim, same-suffix collision, shared-IP browser origin, concurrent claimant,
lost owner, rollback, physical access, public default reuse, untrusted page and secret
exposure. The operator accepted the complete contract on 2026-09-27; any
material change to those user-facing terms requires a new design decision.

## P12.8: commissioning foundation

The current source has an inert Consumer-Profile/1 journal format and a
portable one-claim slot plus owner signing/challenge/verification primitives. Their separate
[structural](phase12-8-structural-foundation-review.md) and
[claim-slot](phase12-8-claim-slot-review.md) and
[owner-wire](phase12-8-owner-wire-review.md) reviews keep the HTTP route, full session crypto,
credential activation and physical acceptance explicitly open.

After P12.7 approval, implement portable state machines under `src/` and Pico
adapters only where needed. Make a blank device advertise an explicit setup
state without using its name/MAC suffix as identity proof. Admit exactly one
provisional Safari claimant; bind physical confirmation as approved; promote
its public key to owner only when the claim succeeds durably. Generate or install the
approved per-device identity and authenticated station/client trust without
exposing keys. Validate ordinary settings as one transaction, commit exactly
one new generation, preserve unrelated stores, defer activation past terminal
response delivery or its bounded timeout, and recover after power loss to a
complete generation or fail-closed state. Scrub transient materials on every
terminal path. Keep authorization and journal logic outside the transport and
Pico SDK adapters.

Test wrong device, claimant race, expired/duplicate/replayed press, owner-key
storage/revocation failure, entropy/clock failure, invalid settings, journal cuts at
every marker, response loss, activity drift, busy/output-unknown refusal,
network activation failure, reboot and secret-free status. Verify the owner
cannot gain WTP/RF authority merely by claiming the device. Run documented
host tests, supported sanitizers, WTP validator and affected target builds;
inspect flash/RAM and linked symbols. Source results do not close physical
gesture, TLS or network behavior.

## P12.9: guided Safari/SoftAP setup

Implement one linear, accessible Safari path with locally bundled Pico-served
assets at the fixed AP-local origin. Prove full-device-ID key indexing,
persistent owner-key storage/readback and capability checks before claim on
the selected iPhone.
The captive sheet may guide Safari launch but may not silently hold an owner
credential. The page reads the full identity internally; Identify and physical
claim refer to that exact device. Connect accepts only
the approved Wi-Fi/station fields and submits the one commissioning transaction.
Setup complete requires exact device, committed generation, reconnect, owner
and network-readiness evidence. Preserve release integrity and offline cache;
no external scripts, analytics or persistent Wi-Fi/transient secrets. Retain
only the accepted Safari owner key in site storage. Clear other secrets after
success, cancellation, rejection, expiry, reload and uncertain transport loss.
Do not render internal operations, IDs, PEMs, profile JSON, a default-password
prompt or USB commands in the consumer flow. Keep clearly separated engineering
tools if their continued use is approved.

Test all screen transitions and keyboard/screen-reader behavior, Safari
storage failure, wrong device/origin, back/cancel/reload, lost link at each
transaction boundary, unknown result reconciliation, owner reconnect,
repeated Connect and activation failure. Test source and built release assets,
hashes and offline behavior deterministically. Review firmware/browser states
adversarially, repair and rerun affected checks.

## P12.10: bounded RF-inhibited first-run acceptance

Only under separate exact hardware/phone authority, prepare a clean committed
RF-inhibited image and identify Candidate A by USB serial
`0BF4B4AEC9FFB344`, device ID `fd6127d11d6aca42a9905fa3fb1bf1d5`, current
firmware/UF2 hash, boot ID and engine. Candidate B (`CDDBF8767C506C07`) is
observation-only. Verify inactive output, empty/unowned `JobService`, healthy
journals and restoration plan before each mutation. Record the actual iPhone,
iOS and Safari versions and exact page/firmware hashes rather than reusing historical
versions as current facts.

From a documented blank/no-owner state, prove the locally bundled Safari page
works without infrastructure Wi-Fi or cellular, Identify/physically claim
Candidate A, enter ordinary settings and commit the actual generation entirely
from the iPhone without an operator
console, manual ID, default password, file or certificate. Preserve the terminal
response boundary, reboot/reconnect, Safari owner and generation readback, station
association, DHCP/mDNS, controller time and positive mTLS WTP/HTTPS readback
through the separately documented station-client trust path. Verify preserved
station/schedule/watermark stores and continued RF inhibit/output inactivity.
Candidate A has historical runtime profile generations. The separate
Wi-Fi-only bootstrap, if accepted first on the same board, creates a
network-only generation 1. A later full commissioning upgrade is then
generation 2; do not label it a blank-device generation-1 full commission.
Before the first-run row, document the authorized state-preparation method,
preservation of unrelated stores, exact generation semantics and why it yields
a genuinely uncommissioned device. If that cannot be established, leave the
blank generation-1 row unaccepted and report the actual upgrade generation.
Run a finite named wrong-device, competing claimant, cancel, response-loss and
power-cut matrix. Retain each failed attempt and its exact firmware/client
identities; do not relabel a retry as the original pass.

## P12.11: ownership, recovery and SoftAP fallback

Implement and accept second-phone owner-key enrollment after fresh physical action,
capacity/full-slot behavior, deliberate removal and no silent eviction. Prove
lost-owner access recovery without the old phone. Prove distinct access
recovery, provisioning reset and full erase with correct state preservation,
tombstones, key revocation, interrupted-reset resume and post-reset
advertisement. Preserve the versioned Wi-Fi-only route as network-only while
adding the separately approved full Safari commissioning route; never let a
Wi-Fi-only slot authorize owner, station settings, TLS, WTP or job commands.
Provisioned SoftAP must enforce the approved browser owner-key model.

## P12.12: Stage A robustness and closure

Complete the remaining finite RF-inhibited acceptance ledger: malformed,
replay, timeout and journal interruption; trust supersession and credential
rotation; BLE/TCP/WTP/HTTPS concurrence with one owner and one `JobService`;
controller-time disagreement; full LED priority and faults; heap, stack,
lwIP/BTstack pools, TLS allocation, flash serialization, reclamation and soak.
Record exact source, image, device, client, clock, mode, setup, case and result
for every accepted row. End disconnected, provisioning closed, the approved
consumer AP available, healthy journals, empty/unowned, RF-inhibited and
output inactive; explicitly report any restoration limitation. Roll forward
with a verified image; do not routinely restore an older UF2.

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
