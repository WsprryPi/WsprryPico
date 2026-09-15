# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | OPEN — WTP components passed | 2.1a/2.1d/2.1e pass on e64ebb9. P1g later failed cadence; P1h failed maximum HTTP with watchdog allocation failure. Paged-body repair has host evidence. [Review](phase11-5-completion-http-pages-review.md). |
| 2 | OPEN | Supported simultaneous workload and separate bounded overload. |
| 3 | OPEN | Affected TLS/HTTP and distinct WTP timeouts. |
| 4 | OPEN | Actual USB parser and unread-output pressure. |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN; idle Wi-Fi accepted on source 98f5797 | Two independently audited OFF/ON readiness cycles preserve state/configuration and recover address/clock. Link loss, lease/name change, DNS/SNTP, journal rotation and autonomy remain. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

### Current retained-state checkpoint

[Immutable result](phase11-5-completion-retained-sharing-result.json) and
[review](phase11-5-completion-retained-sharing-review.md). R1/R2 retain recorded
closure; R3–R6 remain OPEN. P1g's 2.1a/2.1d/2.1e evidence remains on e64ebb9 and
its original boot; the prior idle replay pass remains on b0254c5.

The HTTP paging candidate 6b7a1b8 was built, deployed and independently checked.
After the app-update pause, fresh inventories verified both original boots,
inactive/unowned state, disabled scheduling, unchanged configuration and host
baseline. A retains 6b7a1b8, boot 1739cc4f28304080ec97e2b228ab2683; B retains
8921a7008183, boot 6684b4b197d80cfa0ce83b3aaf205cb0.

Native-idlej wrote three maximum LOADs with the real native observer. The first
two replied completely; the third timed out after a complete 52,105-byte write.
No RF or allocation failure occurred. Independent raw audit verifies cleanup to
Empty/inactive/unowned on both boards, preserved configuration and reservation
release. This failed packet receives no capacity closure credit.

The host model reproduces retained-list pressure. The source repair shares
identical immutable adjustment values across different jobs while preserving
separate identities and replay contracts. Eight maximum LOADs at the larger
modeled background and nine at the smaller background pass. The ninth at the
larger background remains an observed refusal; it is not qualified overload.
Nine affected CTest groups pass, including TLS and core replay/lifetime checks.
Target retest of this new sharing change is pending; no new firmware is deployed
at this checkpoint.

A fresh 45-minute isolated fixture is active, with independent cleanup and its
original fixed deadline. Raw authenticated records remain on wspr5; publication
contains sanitized facts and hashes. No RF/native packet is running at this
checkpoint. Cumulative charges: five RF jobs / 640 planned seconds, seven A
flashes/BOOTSEL transitions, two Wi-Fi cycles, zero configuration writes and
zero additional controlled reboots. One unplanned watchdog reboot remains in
the historical P1h failure record.

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
