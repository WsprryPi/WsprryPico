# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | OPEN — WTP components passed | 2.1a/2.1d/2.1e pass on e64ebb9. P1g later failed observer cadence before HTTP. Repaired same-boot continuation active. [Review](phase11-5-completion-capacity-cadence-review.md). |
| 2 | OPEN | Supported simultaneous workload and separate bounded overload. |
| 3 | OPEN | Affected TLS/HTTP and distinct WTP timeouts. |
| 4 | OPEN | Actual USB parser and unread-output pressure. |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN; idle Wi-Fi accepted on source 98f5797 | Two independently audited OFF/ON readiness cycles preserve state/configuration and recover address/clock. Link loss, lease/name change, DNS/SNTP, journal rotation and autonomy remain. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

### Current retained-reply checkpoint

[Immutable results](phase11-5-completion-capacity-cadence-result.json) and
[review](phase11-5-completion-capacity-cadence-review.md). R1/R2 retain recorded
closure; R3-R6 remain OPEN. Components 2.1a, 2.1d and 2.1e now have current-image
evidence. The prior idle replay pass remains recorded on b0254c5.

A runs e64ebb9 on boot 0a6d95e11cf712a53e97a4c9938614e9. P1g's 512-event job
completed with exact DMA/launch/tail counters and 48,136-byte heap headroom.
The maximum 65,536-byte WTP payload and 65,537-byte rejection/recovery each
completed under independently bracketed native Running observations. Two serial
exchanges in one polling action then missed USB STATUS cadence; HTTP was never
offered. This failure is preserved separately from passing components.

The harness now offers one exchange per polling action. P1h is ACTIVE on the
same source/boot, retaining P1g's Complete job, with one 128-second job allowance,
no flash/configuration writes and the existing fixture deadline. Final P1h state
and actual ARM charges await reconciliation. P1g ended Complete/inactive/unowned,
B remained Empty, both schedules disabled and configurations unchanged; the
original reservation was released before P1h acquired it.

The fixture remains ACTIVE with independent cleanup due at host monotonic
435459994813000 ns. Completed-packet charges: four RF jobs / 512 planned seconds,
six A flashes/BOOTSEL transitions, two Wi-Fi cycles, zero configuration writes.

### Package 0 checkpoint

At P0, both boards retained the recorded
images/boots, Empty/inactive/unowned state and disabled scheduling. Observable
configuration matches component 9. No configuration save, RF, flash or fixture
mutation occurred. Installed WsprryPi PID 1957 and host boot match; no competing
fixture process was found. A is unsynchronized with the fixture down, so ARM
requires fresh time admission after fixture setup.

Review repaired the initial Armed-abort pointer (B5 supplies that evidence) and
explicitly marked R1 retained-lifetime applicability as affected. R1/R2 remain
closed within recorded scope; no current-image retained-resource pass is inferred.
The ordinary R3 suite passed 163 cases with 32 private-evidence skips; all eleven
affected CTest targets pass, including TLS after allowing local loopback access.
