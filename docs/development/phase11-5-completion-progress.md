# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | OPEN — replay reserve failure | Three complete maximum idle LOADs, then 31,200-byte headroom failure. Compact active replay repair is host-validated; target check precedes RF capacity. [Review](phase11-5-completion-active-replay-review.md). |
| 2 | OPEN | Supported simultaneous workload and separate bounded overload. |
| 3 | OPEN | Affected TLS/HTTP and distinct WTP timeouts. |
| 4 | OPEN | Actual USB parser and unread-output pressure. |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN; idle Wi-Fi accepted on source 98f5797 | Two independently audited OFF/ON readiness cycles preserve state/configuration and recover address/clock. Link loss, lease/name change, DNS/SNTP, journal rotation and autonomy remain. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

### Current retained-reply checkpoint

[Immutable results](phase11-5-completion-active-replay-result.json) and
[review](phase11-5-completion-active-replay-review.md). R1/R2 retain recorded
closure; R3-R6 remain OPEN. No new physical assertion closes.

A runs d674dc6 on boot d76d4e540ddafff6622513596125c58c. Its fresh zero-RF
packet returned three complete 512-adjustment LOAD replies. A fully written
fresh-ID replay had no completed reply when peak allocator headroom failed at
31,200 bytes against the unchanged 32,768-byte reserve. Native observation
provided 21 complete STATUS replies, but the full workload remains failed.

The active-replay decoder now avoids a duplicate event array; INFO avoids normal
geometric string growth. Seven affected host targets and adversarial replay,
ownership, scalar and evidence checks pass. Target behavior remains unvalidated.
Next: a fresh reviewed image and the same finite three-LOAD/replay workload.

Both boards are Empty/inactive/unowned with schedules disabled and configurations
preserved. Shared reservation RELEASED after fresh authoritative reconciliation.
The temporary host fixture is RESTORED before its fixed cleanup deadline.
Cumulative charge: three RF jobs / 384 seconds, three A flashes, two Wi-Fi cycles,
zero configuration writes. All earlier failed workloads remain failed.

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
