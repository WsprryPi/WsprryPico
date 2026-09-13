# R3 v2 optional Pico B parallel-work authorization

This is an additive proposal, not executed authorization. The existing accepted
R3-COMPLETE-20260913-v2 keeps B read-only. A's work and preserved evidence continue
while this proposal awaits a decision.

## Exact target and purpose

Repurpose Pico B, USB serial CDDBF8767C506C07, device
29f20b7342051ef947aa56cb9d4fab42, MAC 88:a2:9e:0a:9d:89,
wsprrypico-0a9d89.local. Its recorded initial image is inhibited
`dbf1d86f0885-dirty`, boot feffcd075ab6cb0b74e7e0c2fde6c87f. It is
Empty/inactive/unowned with scheduling disabled and its existing Wi-Fi
configuration on 192.168.1.53. Refresh identity before any operation.

Use the same current reviewed source as A's pending HTTP repair,
`c5f00b6109cc1c692b3f6bf258c1a77dadef6639`, initially. Build its RF-capable
standalone variant at 138 MHz with B's existing device-specific TLS credentials,
then keep that image deployed. Do not alternate inhibited/RF images. Building
B-specific credentials into the image changes image identity; record that hash
separately. The existing server certificate fingerprint is
9cc4967f0a263b4aa94069674837ddcdb8c1946f5a5b407584ce7eee6298cfac and
its server/controller certificates are valid through September 10, 2027.
No credential contents enter Git or user-visible logs.

B is an independent functional test device, not an unchanged comparator once
repurposed. Do not mutate it until H2b finishes and the existing A/E1 packets
that require unchanged B have completed. Freeze new subsequent A/B packets with
independent ownership and evidence. Each process opens only its own board's
USB endpoints. Never add B work retroactively to a consumed A packet's workload.

## Authorized actions if accepted

- Build, stage, hash-check and perform one serial-specific BOOTSEL/verified
  firmware flash on B. Preserve and read back B's saved configuration, disabled
  scheduling, actual image/boot and device identity. Keep the new image afterward.
- Run bounded USB and authenticated TLS/HTTP functional tests against B only:
  valid/oversized framing, exact HTTP body limits, malformed request rejection,
  request replay/session semantics, harmless browser previews and 31/32/33-character
  admission, and maximum 512-event/3600-second LOAD with inactive Loaded ABORT
  and RELEASE. A complete loaded plan is never armed on B.
- Permit HELLO/CAPS/STATUS/clock/diagnostic reads, CLAIM/RENEW/LOAD, Loaded ABORT
  and RELEASE. At most 16 accepted LOADs per packet; at most 256 requests,
  32 TLS connections and 3600 seconds execution plus 150 seconds cleanup per
  packet. Freeze exact bytes, operations, counts and expected responses first.
- Use fresh, supervised task-owned roots under /home/pi/phase11-5-r3-v2-parallel-b-*.
  Existing B Wi-Fi and trust remain in place. No AP/client-namespace change,
  CONFIG save, allocation panic probe, OS installation or management-service
  change is included. TLS fault injections remain on A's isolated fixture.
- A failed packet stops further mutation, preserves evidence and receives an
  independent diagnosis. Fresh corrected zero-RF test packets are authorized
  within these limits. Another B flash requires a demonstrated source defect
  and a reviewed repaired image, with at most one flash per new packet.
- Repair necessary B-specific tooling and add independent audits/mutation tests.
  Commit and push attributable changes with the already authorized R3 work.

There are **zero ARM commands, zero RF starts, zero schedules and zero RF
permission on B**. No B RF wiring is assumed. Check authoritative inactive output
and absence of launch/DMA/alarm/tail activity after every LOAD/release group and
at completion. An ambiguous or unexpectedly active state stops testing and
requires reconciliation; it cannot be labeled inactive from a disconnected USB
port or process exit.

## Credit and timing limits

B can independently validate functional behavior and diagnose a regression while
A continues RF/resource tests. Its results retain B's actual source/image/boot
and workload. B does not replace A's under-RF contention gates, physical mode
hours or three equivalent reclamation cycles. Those cycles remain on one A
image/boot with matched state. This parallel work is intended to uncover issues
sooner; it does not promise to halve the remaining acceptance time.

Acceptance: “I approve the parallel Pico B plan, including its firmware update
and bounded zero-RF tests. Keep the tested images on both boards.”
