# Phase 12 Plain LAN WTP source review

Status: source and host checks passed on 2026-09-28. New-image physical
Pico-to-WsprryPi interoperability and RF acceptance remain open.

The [execution brief](phase12-plain-lan-execution-prompt.md) selected a
build-time `off|plain|tls` consumer LAN flag, with `plain` as the standard
RF-inhibited image default. Plain WTP uses station TCP port 31417 after IPv4
and accepted SNTP, the existing WTP/1 frames and `JobService`, and a shared
`local-network` principal. The plain listener rejects SoftAP and HTTP. The
engineering TLS and USB paths remain explicit. WsprryPi's `network_plain`
configuration needs host and port only; its existing `network` value retains
TLS meaning. An optional expected device ID is checked if configured; without
one the first `HELLO` binds the ID for that runtime and later reconnects check
it. Plain LAN does not encrypt or authenticate clients.

## Adversarial assessment and repairs

The first assessment found a shared TLS/plain retry timer, a plain connection
that could pass admission while another WTP connection was still activating,
hidden TLS form fields that could block a Plain LAN draft, absent plain
transport metrics, and the still-required manual device ID on the host. The
rendered UI review also found that host and port appeared below optional
identity and clock fields; they now lead the Plain LAN form. These findings
were repaired before the final checks. The host's legacy TLS selection was
kept distinct so existing configurations cannot silently downgrade.

The second assessment reviewed admission, idle timeouts, partial TCP I/O,
station/AP classification, TLS isolation, first-HELLO identity binding,
configuration persistence, and build-mode separation. It found no remaining
actionable defect in this source slice. The optional experimental
`WsprryPico-StandaloneRF` target was attempted but fails before this feature's
code on a pre-existing missing `btstack.h` include path; it is not the standard
consumer image or evidence for this change. No target was flashed and no RF
operation was performed.

## Checks

- Standard RF-inhibited Pico cross-build with pinned Pico SDK 2.3.1 and Plain
  LAN default; explicit `off` and `tls` variants also compiled.
- Pico host `network_tls_tests`, `network_local_wtp_tests`, and
  `network_plain_wtp_tests`: 3/3 passed after the repairs.
- WsprryPi WTP-Client protocol, vector and session tests passed, including
  first-HELLO ID learning and changed-ID rejection.
- WsprryPi loopback Plain TCP test and combined TLS/Plain LAN/parent runtime
  test passed using the installed full Xcode compiler and macOS SDK 26.5.
- WsprryPi UI validation and loopback integration tests passed; rendered
  desktop/mobile Plain LAN screenshots showed host and port before optional
  identity and no certificate fields. Impeccable detector and both repositories'
  `git diff --check` passed.

Physical station admission, Pico-to-WsprryPi HELLO/STATUS, connection loss and
recovery, and optional RF coexistence require later target evidence. Phase 12
closure is unchanged by these host results.
