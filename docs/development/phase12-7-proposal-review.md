# P12.7 proposal adversarial review

Status: **DESIGN REVIEW COMPLETE; P12.7 APPROVED AFTER REVIEW**. The first pass below records the
2026-09-26 Bluefy draft; the 2026-09-27 reassessment at the end reviews the
revised [Safari/SoftAP proposal](phase12-7-consumer-commissioning-proposal.md),
[gated execution prompt](phase12-7-12-execution-prompt.md) and
[roadmap](phase12-plan.md). The revised consumer client has been selected,
and the complete contract was later approved in the
[decision record](phase12-7-decision.md). This document does not turn
source/build evidence or the bounded Wi-Fi-only target run into full owner,
RF or Stage A acceptance.

## Source and authority check

The current Bluefy form requires a local-access password, explicit profile
fields and PEMs; default-password profile apply requires USB-local
confirmation. Current `LocalAccessController` grants admission from an adopted
access journal and the current GATT Identify operation requires an authorized
session. The runtime `Profile` carries a server certificate, server private
key and client CA, and the Pico credential validator checks a certificate/key
pair and server chain. The field-access contract keeps the CA private key
off-device and requires explicit Safari trust for provisioned SoftAP. Candidate
A has historical provisioned generations, so a generation-1 blank-device test
requires a separately authorized preparation method.

## Findings and dispositions

| Finding | Disposition |
| --- | --- |
| A pre-owner Identify/claim cannot reuse the currently authorized-only GATT operation unchanged. | The proposal now calls for a restricted pre-owner operation and a protocol/version decision before implementation. |
| The proposed claim initially bound a settings digest before the user had entered settings. | The claim now binds only its own request; the later configuration transaction binds its exact digest to the durable owner/claim epoch. |
| An erased access journal currently fails closed; treating it as open setup would turn corruption into authority. | The proposal requires a distinct healthy-unclaimed state and fault/power-cut migration tests. |
| Candidate A's historical profile generation cannot be labeled blank generation 0 by assumption. | The execution prompt requires explicit preparation, backup, generation semantics and restoration evidence before P12.10. |
| A locally generated server certificate is not automatically trusted by Safari or the station client, and the current validator/off-device CA policy does not accept it as a drop-in profile value. | The operator selected an on-device per-device CA. The proposal defines a policy exception, versioned validator migration, serial CSR/owner/physical enrollment and station CA pin comparison. The operator reopened the Apple SoftAP trust path, which remains a P12.7 design gate. |
| A SoftAP does not inherently need a certificate, but the selected provisioned browser contract does: its HTTPS server identity, Secure cookie, Origin checks and browser secure-context code depend on it. | The accidental publicly trusted per-device certificate option was removed. The operator selected certificate-free provisioned HTTP with AP-only isolation and a BLE-owner session handoff as the direction. Code-free WPA2 iPhone association through Bluefy and a working Safari session remain unproven; contract migration and the loss of server authentication require explicit acceptance before implementation. |
| Stock BOOTSEL polling may interfere with flash/XIP or the other core. | The proposed tap is conditional on a RAM-resident, measured safe sampler; failure returns to design, not a USB substitute. |
| Just Works plus an LED does not cryptographically defeat an active relay. | The proposal states this limitation for explicit operator acceptance. |
| A single encrypted BLE connection cannot carry a station CSR and simultaneous owner-phone approval. | The proposal now uses a serial, bounded four-connection advanced enrollment with one pending CSR, full digest comparison, physical approval and later certificate retrieval. |

## Reassessment of the selected certificate-free SoftAP direction

The proposed HTTP route closes the Safari certificate-installation problem,
but it does **not** yet close P12.7. Apple's
[Wi-Fi configuration API](https://developer.apple.com/documentation/NetworkExtension/wi-fi-configuration)
is exposed to native apps with a user authorization prompt. Bluefy's
[published capabilities](https://pnnsoft.com/portfolio/detail/bluefy-web-bluetooth-api-solution-for-ios-devices)
describe Web Bluetooth and do not document a web-callable WPA2 join. Inferring
from those sources, a Bluefy page cannot yet be claimed to join a private AP
without showing or entering its passphrase. A manually installed
[Wi-Fi configuration profile](https://support.apple.com/en-gb/102400) would
introduce a Settings ceremony and has not been chosen. This is a hard
feasibility gate, not an implementation detail to defer to P12.11.

The other open gate is browser authority transfer. The BLE owner bond belongs
to Bluefy, while the current Safari API authorizes a separate HTTPS login and
Secure cookie. The selected HTTP route needs a concrete one-time handoff,
expiry/replay protection, wrong-device binding and a decision on whether a
nearby party who knows the AP passphrase can observe and reuse browser
authority. The current cookie, Origin and `crypto.randomUUID()` code cannot be
declared compatible with plain HTTP without migration. An active local
interceptor may impersonate the Pico and solicit or replay ordinary control,
including RF jobs under the browser API; the operator accepted MITM risk, but
this consequence must be explicit in the final contract.

The first four findings and the serial-connection finding were closed in the
proposal and execution prompt, then reassessed against the current source and
roadmap. The operator selected BOOTSEL and the on-device CA architecture on
2026-09-26.
The operator also accepted the device-side CA physical-extraction and Just
Works active-relay limitations, and declined any per-device setup code. The
operator selected certificate-free provisioned SoftAP, but the code-free
iPhone WPA2 join and owner-to-Safari handoff remain unproven. The complete
product contract, that SoftAP feasibility and runtime BOOTSEL feasibility
remain explicit **approval/feasibility gates**, not silently closed defects. No
Stage A physical row is accepted by this review. P12.8-P12.12 and Phase 12
closure remain open until later evidence meets the roadmap. This paragraph
records the preapproval review checkpoint.

## 2026-09-27 Safari/SoftAP adversarial reassessment

The operator selected Safari and SoftAP only. The Bluefy/WPA2 handoff above is
historical and must not be implemented as the consumer path. The new proposal
has one physical Safari owner claim, a browser-retained signing key, an open
provisioned AP with encrypted owner sessions, generated per-device TLS/CA for
station clients, and physical recovery. At this review checkpoint it remained
a proposal; the later [decision](phase12-7-decision.md) approved it.

| Adversarial finding | Revision or remaining gate |
| --- | --- |
| The fixed AP address is one Safari origin for every Pico, so a page served by a malicious or compromised second board can read first-board owner keys. Full-ID indexing only prevents honest cross-board mistakes. | The proposal now states the shared-origin exposure explicitly as part of the accepted active-page-substitution class. The operator must accept this precise consequence with the full P12.7 contract; no origin isolation is claimed. |
| A captive sheet can disappear or use storage separate from Safari; creating the owner key there could strand a newly claimed device. | The proposal requires Safari key generation, persistent storage readback and capability checks before owner commit. Captive UI is only a launch aid. P12.9 must prove first-use on the selected iPhone and fail closed if storage is unavailable. |
| A signed request over open HTTP blocks unauthorized mutation but exposes private request/response data to passive listeners. | The proposal now requires an owner-authenticated ephemeral AEAD session for private reads and writes, with a new versioned wire contract and independent vectors. Public status stays nonsensitive. |
| The existing network-only AP withdraws after join, leaving a healthy network-only device with no Safari discovery path for a later generation-2 upgrade. | The proposal keeps the AP available in network-only mode until full commissioning or explicit reset. This changes the approved network-only AP lifetime and needs explicit P12.7 acceptance plus AP/STA resource validation. |
| Safari/SoftAP is the only proposed owner client. If a healthy provisioned station causes the AP to withdraw, the owner cannot reach the page to enroll clients or manage phones. | The proposal keeps the provisioned AP available in healthy consumer mode as well. This changes the old fallback-only policy and needs explicit approval plus AP/STA and RF coexistence budgets. |
| Runtime BOOTSEL worked only in the RF-inhibited core-1-absent topology; a flash-reading core-1 physical press failed. A provisioned recovery prompt could deadlock or reboot. | The proposal requires a proven parked-core/flash-safe maintenance state before offering provisioned physical actions. No provisioned gesture or reset may ship from the blank-image evidence. |
| Losing Safari site data loses the retained owner credential. | A separately named physical lost-owner recovery revokes old keys and retains operational data. Its two-tap ceremony and power-cut behavior remain design choices for operator approval. |
| The previous mTLS enrollment depended on serial BLE sessions; Safari-only setup cannot use them. | The proposal replaces them with one pending AP-local CSR, owner approval and physical tap, a four-client allowlist and station CA pinning. Phone/station AP concurrency, timeout and wrong-CSR cases remain implementation/target gates. |
| Wi-Fi-only generation 1 and direct full generation 1 are different histories. | The roadmap and prompt now require actual source/generation readback and label a later full upgrade generation 2. No historical read-only or Wi-Fi-only result closes full commissioning. |

After these repairs, the written proposal has no hidden Bluefy handoff or
certificate-installation step. At this checkpoint the remaining **approval** decisions were the
Safari owner-key model, shared-origin exposure, open always-available
provisioned AP, changed network-only AP lifetime, advanced CSR ceremony and
reset levels. The
remaining **proof** gates are selected-iPhone Safari storage/first-use,
provisioned BOOTSEL safety, encrypted owner protocol conformance, AP/STA
capacity and full RF-inhibited activation/readback. The next adversarial
assessment must inspect the accepted contract and source implementation;
the later decision record closes P12.7 design only, not later milestones.

## Second assessment after revisions

The second pass traced both first-run histories (direct full generation 1 and
network-only generation 1 followed by full generation 2), every Safari
access path while station Wi-Fi is healthy or lost, the shared numeric HTTP
origin, key loss/recovery, advanced CSR approval and all three reset levels.
It found the additional healthy-station AP reachability gap above; the
always-available provisioned AP rule closes it in the proposed contract.
No further contradiction was found in the written boundary. This is a
**design-only** reassessment: the open AP resource/RF budget, provisioned
BOOTSEL safety, selected-iPhone key persistence, encrypted owner protocol,
station-client mTLS and physical restoration still need their later gates.
`git diff --check` passed and changed Markdown local-link targets resolved.
