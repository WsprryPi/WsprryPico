# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | OPEN — attempt 1 failed | 512-event job completed; maximum WTP stopped after a partial write during ordinary HTTPS overlap. [Failure and restoration](phase11-5-completion-p1-attempt1-result.json). Prepare sequential individual capacity probes. |
| 2 | OPEN | Supported simultaneous workload and separate bounded overload. |
| 3 | OPEN | Affected TLS/HTTP and distinct WTP timeouts. |
| 4 | OPEN | Actual USB parser and unread-output pressure. |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN | Network recovery; measured journal rotation and autonomous schedule. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

No full physical acceptance assertion closed in P0 or P1 attempt 1. The latter
charged one job / 128 RF seconds, with no firmware, configuration or Wi-Fi
management changes. A completed locally on the same boot and is inactive and
unowned; B is Empty/inactive/unowned. Both schedules remain disabled. Independent
post-restoration inventories preserve both configurations. The host fixture is
restored, and installed WsprryPi PID 1957 and executable hash are unchanged.
The shared RF reservation was released only after fresh A/B authority checks.

P1 attempt 1's failed maximum WTP exchange wrote 4,096 of 65,552 frame bytes;
oversize and HTTP capacity probes did not execute. All 300 Console samples were
independently decoded. Sampled heap and source support an admission refusal
during ordinary HTTPS overlap, but do not directly identify the target branch.
The failure remains a failed supported workload; it earns no overload credit.
See the [review](phase11-5-completion-p1-attempt1-review.md).

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
