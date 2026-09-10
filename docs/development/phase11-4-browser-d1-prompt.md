# D1 native Linux browser completion

Continue from WsprryPico devel `ca62733f258a202fdabd5bf203a5c9c0d31b3b36`.
Read the project contract, architecture, current acceptance procedure and the
[corrected-firmware DHCP results](phase11-4-radio-results.md). Preserve the
modified shutdown record and untracked soak document/script byte-for-byte.
Do not edit sibling repositories. Retain private diagnostics; publish the
working setup, measured results and actual limitations. Commit and push the
reviewed owned records after adversarial assessment.

## Approved scope

The user directed execution of the remaining browser test, then selected
wspr5's browser instead of the Mac. D1's native browser acceptance therefore
uses Linux/Chromium on the independent wireless client. Record that platform
explicitly; do not claim macOS compatibility from Linux evidence. The Mac stays
on its ordinary network, and Ethernet provides independent wspr5 management.
No router changes, forwarding, NAT, bridge, host reboot or firmware flash is
needed. Use temporary AP/client roles only, with automatic restoration armed
before network or Pico configuration changes.

Use Pico A only: serial `0BF4B4AEC9FFB344`, device
`fd6127d11d6aca42a9905fa3fb1bf1d5`, MAC `88:a2:9e:0a:60:df`, hostname
`wsprrypico-0a60df.local`, port 18443. Require the approved standard inhibited
image `802c91a7b86e-dirty`, healthy storage, disabled schedules and authoritative
empty/unowned/inactive state. Its programmed UF2 SHA-256 is
`25e177071f770976f8f5877a6c008e226f6bd776be859fde74f2f9f98c332e10`.
B remains a read-only comparator. Do not LOAD/ARM jobs or enable physical RF.

## Execution

1. Bind AP/client interfaces to their actual MAC addresses. Use one role file
   for both controller and namespace child. Verify the management profile,
   BSSID, power setting, time service and existing WsprryPi service. Arm a
   bounded independent restoration timer. Validate physical association and
   native Avahi/NSS in the isolated wireless client before configuring A.
2. Use the installed native Chromium executable, with an isolated browser home,
   existing Pico A CA/client identity and a private namespace-scoped certificate
   selection policy limited to the exact hostname. Do not alter system trust,
   bypass certificate validation, inject DNS, flush resolver caches or proxy the
   browser through an HTTP preview. Keep exported credentials owner-only.
3. Start AP/client packet captures. Temporarily configure A onto the controlled
   AP, with the initial MAC-specific lease `10.77.14.10`. A setup reboot is
   permitted and recorded; the subsequent DHCP transition must keep that boot.
   Verify native Linux resolution and authenticated WTP/HTTPS. Capture actual
   Chromium page navigation, rendered DOM, screenshot, remote IP, secure TLS,
   server fingerprint and live API status. Bound each browser observation to
   55 seconds, with 15-second browser-control commands; retain all outcomes.
4. Observe the actual installed WsprryPi production client at the certified
   hostname, with transmission disabled and no GPIO actions. Audit its plaintext
   TLS observation for exactly HELLO/STATUS/CAPS/STATUS/STATUS and zero LOAD/ARM.
5. Admit the DHCP mutation only after successful reference, Chromium and
   production baselines. Change only A's binding to `10.77.14.20`; require a
   captured matching DHCP REQUEST/ACK, unchanged boot/name/certificate/config,
   current native resolution and positive cache-flush advertisements of `.20`.
6. Keep Chromium running and reload the same tab at the same hostname. Require
   actual secure responses from `.20`, live empty/inactive status and the same
   boot. Reconnect the actual production client and audit its identity and wire
   operations again. Do not replace a failed deadline with an eventual pass.
7. Stop owned browser/controller processes, restore A to Bohica-IoT, remove
   temporary AP/namespace/time allowance, and verify original interface roles,
   management profile/power, services and fresh A/B USB status. Cancel restoration
   only after verification. Keep private raw evidence and hashes.

## Review and acceptance

Adversarially assess actual packet origin, DHCP transaction pairing, unchanged
identity, native resolver destination, real browser responses versus cached DOM,
certificate validation, same-tab/process continuity, no hidden mutation and
cleanup completeness. Challenge altered identity/address/trust, incomplete
captures, missing browser response evidence and missing cleanup. Fix actionable
observer/report defects and reassess the original evidence.

Close D1 for the user-selected native Linux/Chromium scope only if the full
transition passes. Preserve B2/D2 repeatability and the eight-hour soak as
separate open work. Record macOS as untested compatibility, not as a substitute
for the browser test the user selected. Update the joint matrix, development
index, working-results record and sanitized evidence manifest; commit, push and
verify origin/devel parity.
