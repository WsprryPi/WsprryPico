# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | OPEN — repair validated on host | Original RF capacity failure preserved. Later packets stopped before ARM; completed-job storage blocked replacement LOAD under native TLS. Repair needs identified target build and affected retest. [Review](phase11-5-completion-terminal-storage-review.md). |
| 2 | OPEN | Supported simultaneous workload and separate bounded overload. |
| 3 | OPEN | Affected TLS/HTTP and distinct WTP timeouts. |
| 4 | OPEN | Actual USB parser and unread-output pressure. |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN; idle Wi-Fi accepted on source 98f5797 | Two independently audited OFF/ON readiness cycles preserve state/configuration and recover address/clock. Link loss, lease/name change, DNS/SNTP, journal rotation and autonomy remain. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

### Current repair checkpoint

[Results and exact hashes](phase11-5-completion-terminal-storage-result.json)
and [adversarial review](phase11-5-completion-terminal-storage-review.md).
R5.wifi is newly accepted within its source 98f5797 idle recovery scope; no
family closes. Cumulative charge: one RF job / 128 seconds, two Wi-Fi cycles,
zero flashes and zero configuration writes. P1b/c/d sent no ARM.

Fresh post-review inventories show both boards Empty/inactive/unowned with
unchanged configurations and disabled scheduling. A's terminal record expired
naturally. Images and boots remain unchanged. Host fixture restoration matches
its baseline; installed WsprryPi PID 1957 is unchanged. The shared RF reservation
is released. The Complete-only event storage repair passes host regression but
has not been flashed or physically accepted.

Original attempt 1 wrote 4,096 of 65,552 maximum-frame bytes during ordinary
HTTPS overlap. Oversize and HTTP capacity probes did not execute. All 300
Console samples were independently decoded. The failure remains failed and
earns no overload credit. Subsequent deadline/guard/admission failures are
retained separately. Next: identified build and bounded affected target tests.

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
