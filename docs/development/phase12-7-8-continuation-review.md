# Phase 12 Safari contract and network-only continuation review

Status: **P12.7 APPROVED DESIGN; NETWORK-ONLY GENERATION-1 TARGET READBACK
PASSED; P12.8 PARTIAL; P12.9–P12.12 OPEN** (2026-09-27).
This is an adversarial review of this bounded continuation, not a Phase 12
closure or RF authorization.

## Exact scope and evidence

The work began from clean, pushed `devel` `fb091f8af5be`. The operator
approved the complete [Safari/SoftAP P12.7 contract](phase12-7-decision.md)
and separately approved one Candidate A USB reboot/readback after the iPhone
network-only trial. The [target record](phase12-wifi-only-physical-result.md)
now proves exact `fb091f8` image, Candidate A full identity, one phone
BOOTSEL-confirmed credential submission, post-reboot `network_only`
generation 1, station address `192.168.1.47`, empty job and inactive output.
It does not prove that the final page displayed **connected**, that AP return
after station loss works, or any consumer owner/trust behavior. No additional
button press, credential submission, flash, RF output or comparator operation
occurred in this continuation.

The source change removes post-commit withdrawal of the network-only AP to
make later Safari commissioning discoverable. The AP request remains gated by
`no_profile`, and the existing AP-interface connection classifier still
restricts the HTTP listener. The acknowledgement remains a bounded receipt
but no longer controls AP lifetime. The stale withdrawal timer was removed
from the join gate. A focused host test checks that `no_profile` keeps AP
requested even with a healthy station. The target build produced an unflashed
UF2 SHA-256
`3be01934bde3c8c337629b964fc76cc0fbc45715b126a25b988d737e17f1efda`.
Candidate A continues to run the older installed UF2 SHA-256
`d262c9a92a0b7ec3be4739e50e39c8b7ac59a80f25863e4bf840e40b38a18ce2`.
The source/link check still finds one SRAM BOOTSEL callback and no linked
core-1 launcher/reader. None of this qualifies AP/STA runtime cost or a
provisioned BOOTSEL action.

[Owner-HTTP/1](../protocol/Owner-HTTP-v1.md) and
[Consumer-Profile/1](../protocol/Consumer-Profile-v1.md) are P12.8 design
artifacts. They specify owner signing/encrypted AP sessions, one physical
claim, composite profile authority, migration and reset gates. They have no
production routes, generated keys, parser, crypto vectors or journal
implementation yet. Field-GATT/1 engineering operation remains the running
baseline.

## First adversarial pass: findings and repairs

| Finding | Repair and disposition |
| --- | --- |
| The roadmap still called the approved P12.7 decisions unresolved proposals. | Corrected the decision/status text and linked the exact approved record. Closed as a documentation defect. |
| A second roadmap checklist still asked whether to use factory trust and whether to retire the password after those choices had been approved. | Replaced it with the selected Safari owner, on-device CA, runtime claim and recovery decisions, while keeping the provisioned/core-1 proof gate explicit. Closed. |
| The historical target record named a build path that a new compile later overwrote with a different UF2. | Separated the installed `d262…` hash from the newer unflashed `3be…` hash and rewrote the execution prompt to prevent an accidental reflash or repeated phone action. Closed. |
| Keeping the AP on only by bypassing a main-loop override left dead withdrawal logic and tests that still modeled the retired policy. | Removed the obsolete timer/service path and revised the focused join test. `field_access_tests` asserts AP request after station join. Closed. |
| Signing serialized JSON would leave ambiguity from key order and whitespace. | Owner-HTTP/1 signs decoded ciphertext plus tag and fixed-order binary identity/operation fields; every mutation carries a fresh signature/challenge. Closed at design level, subject to vectors. |
| Four 512-byte CSRs plus the initial 3,584-byte TLS cap could exceed the 7,168-byte profile slot. | Reduced accepted CSR DER to 320 bytes and TLS aggregate to 2,304 bytes. A pessimistic compact-JSON calculation is 6,457 bytes, leaving 711 bytes. Actual certificate/parser sizing remains an implementation gate. Closed at design-budget level. |
| Legacy password/GATT endpoints might remain usable after a consumer profile is selected. | The storage/wire designs now require denying them before their legacy admission logic and forbid automatic factory migration. Closed at design level, subject to implementation tests. |

## Second adversarial assessment and checks

The second pass traced the no-profile AP decision through `main.cpp`,
`SoftApCoordinator`, the AP-interface classifier, bootstrap status and
post-commit acknowledgement. It found no further actionable defect in the
bounded AP-lifetime source change. The old installed-image withdrawal
observation remains historical evidence; it was not reassigned to the new
source. It also checked that public network-only status cannot become owner,
station API or job authority and that the consumer designs explicitly leave
P12.8 vectors and core-1 safety unaccepted.

- Focused `bootstrap_join_tests` and `field_access_tests`: 2/2 passed after
  the timer cleanup.
- Browser bootstrap tests: 2/2 passed; the owner page is not implemented.
- Full host CTest: 90/93 passed on the first run; three failed because the
  default Command Line Tools SDK linker rejected the installed macOS 27
  `.tbd` architecture. Those exact three passed with the project-required
  Xcode `DEVELOPER_DIR` and macOS 26.5 `SDKROOT`. Aggregate affected suite:
  93/93 passing under the correct SDK environment.
- RF-inhibited Pico 2 W cross-build and linked BOOTSEL topology check passed
  with the pinned SDK/toolchain. This is build evidence only.
- `git diff --check` and changed-document relative links passed.

## Remaining gates

P12.8 still needs an exact owner-route registry and independent Pico/browser
crypto vectors, a consumer profile parser and journal/migration power-cut
tests, safe provisioned BOOTSEL design, generated CA/server credential
lifecycle, station-client enrollment and production authorization wiring.
P12.9 needs a Safari page and selected-iPhone storage/captive handoff proof.
P12.10–P12.12 need separate RF-inhibited target authority and evidence for
full setup, owner/recovery/fallback and Stage A robustness. The failed
historical core-1 physical-press gate remains failed; neither this source
build nor the successful blank single-core iPhone press closes it. Stage B
and Phase 13 remain separate.
