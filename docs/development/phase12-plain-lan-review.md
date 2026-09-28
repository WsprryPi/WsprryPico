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

## Subsequent two-board flash and listener repair (2026-09-28)

The operator authorized flashing both USB-identified Pico 2 W boards on
`wspr5`. A fresh standard, RF-inhibited `devel` build for Pico 2 W/RP2350 Arm
secure used pinned SDK 2.3.1, Release mode and Plain LAN. It was verified by
SHA-256 and flashed with serial-targeted picotool verification.
Candidate A (`0BF4B4AEC9FFB344`) retained its consumer pre-clock generation-2
profile at `192.168.1.47`; Candidate B (`CDDBF8767C506C07`) had an older PIO
image and booted the standard image unprovisioned. Both were idle with output
inactive before and after flashing.

The first flashed image exposed a target-only resource defect: A reported
accepted SNTP and synchronized UTC but `lan_wtp_ready=false`, and port 31417
refused a connection. The lwIP configuration reserved one listening PCB even
though the standard firmware can open separate captive HTTP, HTTPS, and Plain
LAN listeners. Raising that pool to three allowed A's Plain LAN listener to
start. The static transport contract check was updated for the explicit
Plain LAN binding and listener budget. Its check, `git diff --check`, and the
corrected Pico 2 W Release cross-build passed.

The corrected UF2 SHA-256 is
`87e6cdc55f0226a85dd0ec78ef431d6d27c41298b70920aa0063e36cc33a524c`.
It embeds revision `abd0e75b0436-dirty` because the listener repair was in
the working tree at build time. Both ROM chip IDs were checked, and both
`picotool load -v -x` operations reported verified `OK` and rebooted. Final
USB `INFO` returned that revision and each expected device ID, a 150 MHz system
clock, empty service, the `inhibited-standalone-simulator` engine and inactive
output. Both reported valid core-0 stack guards, zero allocator failures and
zero fault status. A retained
station IP `192.168.1.47`, synchronized UTC, `lan_wtp_mode=plain`, port 31417
and `lan_wtp_ready=true`; a TCP connection to that port succeeded. Port 443
also accepted TCP, while station-side port 80 was closed. B reported
unprovisioned generation 0 with no station address or synchronized clock, so
it has no LAN listener until Wi-Fi setup. Neither board was rolled back.

This is image delivery and A listener reachability evidence. A WTP
`HELLO`/`STATUS` exchange, B commissioning, reconnect behavior, phone UI and
RF qualification were not exercised by this flash request.
