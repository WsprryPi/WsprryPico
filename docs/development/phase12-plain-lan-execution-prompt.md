# Phase 12 plain LAN WTP execution prompt

Status: operator-approved implementation brief (2026-09-28).

Implement the following on the clean `devel` branches of WsprryPico and
WsprryPi. Keep commits and pushes separate by repository. Do not flash, run RF,
install a Pi service, or change an operator's active configuration in this
source-work turn.

1. Give the consumer Pico firmware an explicit LAN WTP mode: `off`, `plain`, or
   `tls`. Default the standard RF-inhibited consumer build to `plain`. Keep
   engineering mTLS behavior and USB CDC WTP intact. A selection must not
   silently fall back to another mode. Expose the selected mode and live
   readiness in diagnostics.
2. Plain LAN accepts the unchanged WTP/1 frame stream on a documented port
   only after infrastructure Wi-Fi, IPv4, and accepted SNTP. Admit it only on
   the station interface, never on SoftAP. Reuse the one `JobService`, its
   ownership, replay, clock, output, and cancellation rules. Bound connections,
   buffering, stalled peers, and shutdown. Do not generate or require TLS
   material for a Wi-Fi-only profile in plain mode.
3. Keep TLS as an explicitly selected advanced LAN mode. Preserve existing
   engineering mTLS and provisioned SoftAP HTTPS independently of the LAN
   selection. Do not remove application-layer encryption from the open SoftAP
   Wi-Fi setup transaction.
4. Teach WsprryPi to select plain network WTP with Pico host and port only,
   while retaining existing valid TLS configurations. Make plain the new
   operator-facing network default and place certificate settings behind an
   explicit advanced TLS choice. Keep USB as a separate unchanged transport.
   Update the full configuration path and client connection lifecycle, not just
   a form label.
5. Amend the WTP/1 transport-binding contract to describe an explicitly
   selected, local-network plaintext binding and its shared LAN principal.
   Preserve the frame format and all job semantics. Document that any client
   able to reach the plain listener can submit control commands; keep TLS as a
   selectable stronger binding. Update implementation and operator docs without
   claiming physical interoperability.
6. Add focused deterministic tests for mode defaults/validation, plain TCP
   HELLO/STATUS and rejection paths, AP versus station admission, connection
   limits, partial/stalled I/O, retained TLS behavior, and client selection.
   Build the RF-inhibited Pico image using the pinned SDK and run relevant
   WsprryPi portable tests. Review the complete changes adversarially, repair
   findings, rerun affected checks, and reassess before committing and pushing.

Acceptance is source and host-test evidence for both repositories. New-image
Pico-to-WsprryPi physical interoperability and RF behavior remain separate
target gates.
