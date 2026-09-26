# P12.7 proposal adversarial review

Status: **DESIGN REVIEW ONLY — P12.7 OPEN**. This review covers the
[consumer commissioning proposal](phase12-7-consumer-commissioning-proposal.md)
and [gated execution prompt](phase12-7-12-execution-prompt.md), including the
uncommitted [roadmap](phase12-plan.md) change. It does not review an
implementation, a live device, RF behavior or the final Stage A ledger.
The operator paused Bluefy work on 2026-09-26. The earlier Bluefy-specific
join and handoff findings remain historical design evidence; choosing the
replacement phone client is now the first unresolved product decision.

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
Stage A physical
row is accepted by this review. P12.8-P12.12 and Phase 12 closure remain
blocked until P12.7 is accepted and later evidence meets the roadmap.
