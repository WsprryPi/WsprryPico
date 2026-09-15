# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | OPEN — idle regression passed | Three maximum LOADs and fresh-ID replay pass on b0254c5. Maximum padded STATUS repair passes host checks; RF capacity remains unaccepted. [Review](phase11-5-completion-read-workspace-review.md). |
| 2 | OPEN | Supported simultaneous workload and separate bounded overload. |
| 3 | OPEN | Affected TLS/HTTP and distinct WTP timeouts. |
| 4 | OPEN | Actual USB parser and unread-output pressure. |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN; idle Wi-Fi accepted on source 98f5797 | Two independently audited OFF/ON readiness cycles preserve state/configuration and recover address/clock. Link loss, lease/name change, DNS/SNTP, journal rotation and autonomy remain. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

### Current retained-reply checkpoint

[Immutable results](phase11-5-completion-read-workspace-result.json) and
[review](phase11-5-completion-read-workspace-review.md). R1/R2 retain recorded
closure; R3-R6 remain OPEN. No new normative physical assertion closes.

A runs b0254c5 on boot 4dad3b38c27aad73da01cefc9e857cdb. Three maximum LOADs and
one fresh-ID replay returned all exact adjustments in 2.11-2.61 seconds under
96 native STATUS replies. Peak headroom is 32,800 bytes, only 32 above the gate.
This passes the frozen idle workload; it provides no additional capacity margin
or RF-continuity acceptance. Earlier failures remain failed.

Host tests reproduce maximum padded STATUS decode refusal beside a loaded job.
A targeted bounded-read workspace repair passes red/green tests without changing
new-LOAD admission, the safety reserve or five-second deadlines. Next: reviewed
image deployment and affected maximum-capacity RF test. The completed idle replay
is reused only within its source-impact scope; changed layout is checked anew.

Both boards are Empty/inactive/unowned with schedules disabled and configurations
preserved. Shared reservation RELEASED. The prior fixture session is restored;
the current session is ACTIVE with independent cleanup due at host monotonic
435459994813000 ns. Cumulative charge: three RF jobs / 384 planned seconds,
five A flashes/BOOTSEL transitions, two Wi-Fi cycles, zero configuration writes.

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
