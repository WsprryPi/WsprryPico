# Wi-Fi-only bootstrap adversarial design review

Status: **PROPOSAL REVIEW — NO IMPLEMENTATION OR TARGET ACCEPTANCE**.
This review covers the
[blank-device SoftAP network-only proposal](phase12-wifi-only-bootstrap-proposal.md)
against the current source and [Phase 12 roadmap](phase12-plan.md). It does not
authorize a firmware change, an AP, credential submission or an RF operation.

## Findings and disposition

| Finding | Disposition |
| --- | --- |
| The first draft bound the physical tap to a ciphertext digest that did not exist until after the tap. | Corrected: the browser creates a fresh key and nonce first; the tap binds that public key/nonce to one slot, and the later encrypted submission binds its digest to the slot. |
| Browser page load and submission cannot be assumed to use one TCP connection or stable client address. | Corrected: the contract binds the browser ephemeral key and request nonce, not one socket or IP address. |
| A website already open on the phone could submit to the local AP endpoint during the physical window. | The proposal requires AP-interface-only admission, exact Host/same-Origin checks, JSON plus a non-simple request header and the physically bound ephemeral key. The active evil-page/relay limit remains disclosed. |
| The current all-erased access journal blocks authenticated local access, and a corrupt journal cannot be treated as a factory blank. | An exactly erased journal may expose only the read-only AP after identity/output checks. The proposal requires physical initialization before credential acceptance and fail-closed treatment of invalid non-erased records. The migration and power-cut behavior remain an implementation and test gate. |
| A fully erased generic image currently selects the legacy factory-bundle profile source, rather than explicit unprovisioned mode. The Candidate A physical check required a test-only unprovisioned journal before the blank captive AP appeared. | Deferred cleanup: define the factory-bundle compatibility boundary and a safe first-run source selection for generic images. Test erased, explicit-bundle, valid-tombstone, corrupt-journal and interrupted-selection cases, then repeat the physical blank-device check without journal seeding. See the [physical result](phase12-blank-captive-physical-result.md). |
| The original blank AP was WPA2 with a derived public password and its HTTP server rejects non-GET. | The bounded read-only captive AP now uses open Wi-Fi. The separate proposal still requires a narrowly scoped versioned POST and encrypted station credentials; no existing source path can be called an accepted Wi-Fi-only bootstrap. |
| Plain HTTP on an open AP would disclose the station Wi-Fi password to nearby listeners. | The operator selected ephemeral browser/Pico encryption. X25519, HKDF and AEAD parameters, a locally bundled browser implementation, secure randomness and cross-language vectors must be fixed and tested before code. Active page replacement/relay remains possible and was accepted. |
| `crypto.subtle` cannot be assumed available to a page loaded from the Pico's HTTP address. | The proposal forbids depending on secure-context APIs and requires a reviewed local implementation plus a selected-browser proof. This remains a feasibility gate. |
| Writing the legacy standalone Wi-Fi fields would risk credentials surviving an unprovisioned tombstone; the current runtime overlay needs explicit source review. | The proposal uses a distinct transactional network-only profile source and requires negative reboot/reset tests for legacy credential resurrection. |
| Network-only storage consumes a profile generation and cannot also preserve the old generation-1 full-commissioning claim without a redesign. | The proposal exposes the collision and requires the roadmap and acceptance ledger to state separate exact generation semantics before implementation. |
| Station association could accidentally start listeners, schedules or RF authority while no owner or TLS identity exists. | The proposal explicitly denies those authorities in network-only mode and requires target-side negative assertions. |
| Pico AP and station concurrent operation, channel changes, DHCP and response delivery are not proven by source inspection. | Keep target acceptance open until a finite RF-inhibited run proves trial, commit, AP status, stable withdrawal, fallback and reboot readback on the exact image. |
| The first Wi-Fi-only draft required the user to open Safari and would not attempt an automatic captive screen. | Revised to advertise AP-local DNS, answer bootstrap-AP IPv4 DNS queries with the Pico address, and redirect safe plain-HTTP probes to the local page. The fixed Safari address remains the fallback. This is limited to the blank bootstrap AP; the provisioned AP and station interface keep their existing DNS behavior. |
| Captive detection depends on iOS behavior; a miniature captive browser may close early or lack the page's cryptographic capability. | Automatic launch and form completion are separate target acceptance observations. Feature-detect before exposing the credential form, use the sheet only for directions if the complete encrypted flow cannot run, and keep the AP/status page available through durable commit and browser acknowledgement. Never claim that DNS interception forces iOS to open a sheet. |
| Broad DNS replies and foreign-Host probe redirects could leak into normal network service or admit a credential POST from an unrelated origin. | Bind the DNS and redirect service to the blank bootstrap AP lifetime and interface, do not intercept HTTPS, use a short-lived no-store redirect to the fixed local URL, and retain exact AP-local Host plus same-Origin admission for mutating requests. Add host tests for AP/STA and provisioned-mode isolation. |

## Reassessment

The corrected design is internally coherent as a **network-only** bootstrap:
no setup code, app, certificate or BLE is required for the user to enter
station Wi-Fi, and the ordinary success claim stops at durable network join.
It is not yet an approved exception to the current blank-AP policy. The
remaining hard gates are safe runtime BOOTSEL sampling, browser-side crypto
availability and source provenance, the new journal/runtime migration, AP/STA
behavior on Pico 2 W, full encrypted-form behavior in the captive screen, and
exact user-visible disclosure of active relay risk.
The separate read-only WPA2 physical check observed automatic captive launch
and Safari fallback on one iPhone. The later open AP passed passwordless host
association, and the operator reported passwordless iPhone association and
automatic captive launch. A credential form remains open.
The last risk is a chosen limitation, not evidence of prevention. The
consumer owner/TLS path, broader Stage A ledger and Phase 12 closure remain
open. Stage B RF coexistence is separate and has not been operated.
