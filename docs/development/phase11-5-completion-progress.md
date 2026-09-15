# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | OPEN — native connection failure | RF failures and three idle attempts preserved. Streamed reply repair is host-validated; retained native/LOAD target check precedes further RF capacity. [Review](phase11-5-completion-streamed-reply-review.md). |
| 2 | OPEN | Supported simultaneous workload and separate bounded overload. |
| 3 | OPEN | Affected TLS/HTTP and distinct WTP timeouts. |
| 4 | OPEN | Actual USB parser and unread-output pressure. |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN; idle Wi-Fi accepted on source 98f5797 | Two independently audited OFF/ON readiness cycles preserve state/configuration and recover address/clock. Link loss, lease/name change, DNS/SNTP, journal rotation and autonomy remain. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

### Current retained-reply checkpoint

[Immutable results](phase11-5-completion-streamed-reply-result.json) and
[review](phase11-5-completion-streamed-reply-review.md). R1/R2 retain recorded
closure; R3-R6 remain OPEN. No new physical family closes.

A runs a9d5610 on boot 8d747e80fa4e2762ba2509b5bb5ecfae. Three zero-RF
packets preserved two native observer guard failures and one maximum LOAD reply
timeout with two aborted records retained. The guard failures are independently
attributed to event refresh and foreign-owner transmission admission. The third
packet's actual native session stayed healthy; USB received no LOAD reply.

The reviewed stream encoder and larger decoding allowance pass host checks but
are not yet built/flashed for target acceptance. Next: recreate the retained
maximum workload on an identified candidate without RF, then affected RF capacity.

Latest inventories: both boards Empty/inactive/unowned, schedules disabled and
configurations preserved; A has three aborted records, B is unchanged. Shared
reservation RELEASED. Fixture ACTIVE within its original supervised deadline.
Cumulative charge: three RF jobs / 384 seconds, two A flashes, two Wi-Fi cycles,
zero configuration writes. Prior RF/idle failures remain failed.

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
