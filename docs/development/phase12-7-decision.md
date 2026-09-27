# P12.7 Safari/SoftAP consumer contract decision

Status: **APPROVED DESIGN; IMPLEMENTATION AND TARGET ACCEPTANCE OPEN**
(2026-09-27).

The operator approved the complete
[Safari/SoftAP proposal](phase12-7-consumer-commissioning-proposal.md)
after its [adversarial reassessment](phase12-7-proposal-review.md). This
decision closes **P12.7 design approval only**. It does
not assert that Safari owner keys, generated certificates, a provisioned open
AP, client enrollment, reset ceremonies or RF-safe provisioned BOOTSEL are
implemented or physically accepted.

## Accepted consumer contract

- Safari and SoftAP are the only consumer commissioning client. The open AP
  needs no AP password, per-device code, QR, PIN, native app, Bluefy or manual
  certificate installation. The home Wi-Fi password is the sole ordinary
  password entry.
- One prompted runtime BOOTSEL press/release claims the exact Pico for one
  pending Safari owner key. Safe provisioned/core-1 sampling is a hard
  implementation and target gate; the blank inhibited result cannot qualify
  it.
- Safari generates and retains an owner signing key. The Pico stores its
  public key/epoch, requires owner-authenticated encrypted sessions for private
  AP traffic, and keeps the station mTLS/HTTPS principal separate.
- All Pico APs share Safari's numeric HTTP origin. Full-ID-indexed storage
  prevents honest wrong-board selection but does not isolate keys from a
  malicious page served by another Pico AP. The operator accepted this
  concrete active page-substitution consequence.
- The Pico generates a per-device CA and server key in ordinary flash.
  Physical key extraction risk is accepted. Owner and physical approval are
  required for each advanced station-client CSR; consumers do not manage PEM
  files during setup.
- The network-only AP remains available for a later full setup. The
  provisioned AP remains available while station Wi-Fi is healthy because
  Safari/SoftAP is the sole owner path. Both are changes from the older
  AP-withdrawal/fallback policy and need AP/STA resource and channel evidence.
- Distinct second-phone, lost-owner access recovery, network reset and full
  erase actions use fresh bound physical confirmation. No Wi-Fi-only
  transaction grants owner, station, job or RF authority. Direct blank full
  setup may commit generation 1; full upgrade after network-only generation 1
  commits generation 2.

## Boundaries before code and acceptance

On 2026-09-27, the operator clarified that a person must never time a
BOOTSEL hold. The approved physical action is an ordinary press and release
once when prompted. The original proposal's 100–600 ms acceptance band is
superseded. Device-side debounce, a bounded prompt window and stuck-hold
recovery remain implementation safeguards. The
[core-1 target diagnostic](phase12-8-bootsel-window-target.md) observed one
702 ms press/release without fault or reboot; the installed diagnostic
rejected it solely under the superseded duration rule. This clarification
does not approve or imply an implemented consumer claim route.

P12.8 must first version the owner-HTTP wire and storage schema, specify
canonical crypto encodings/vectors and migration from the engineering
password/PEM model, then implement the exact accepted state machine. The
[Owner-HTTP/1 design](../protocol/Owner-HTTP-v1.md) is an initial P12.8
wire artifact with a separate
[Consumer-Profile/1 storage design](../protocol/Consumer-Profile-v1.md),
not a completed implementation or vector review. The
existing Field-GATT/1 engineering path remains versioned and operational
until a deliberate compatibility decision; this approval does not redefine
that wire. P12.9 must prove Safari storage, captive handoff, offline page,
unknown-result reconciliation and no-code flow on the selected iPhone.
P12.10–P12.12 require separate exact hardware authority and RF-inhibited
evidence. Stage B RF coexistence and Phase 13 release qualification remain
separate. The [execution prompt](phase12-7-12-execution-prompt.md) orders
those gates.
