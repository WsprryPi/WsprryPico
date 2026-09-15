# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | OPEN — replay reserve failure | Three complete maximum idle LOADs, then 31,680-byte headroom failure before replay input completed. INFO lifetime repair precedes another affected target check. [Review](phase11-5-completion-info-lifetime-review.md). |
| 2 | OPEN | Supported simultaneous workload and separate bounded overload. |
| 3 | OPEN | Affected TLS/HTTP and distinct WTP timeouts. |
| 4 | OPEN | Actual USB parser and unread-output pressure. |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN; idle Wi-Fi accepted on source 98f5797 | Two independently audited OFF/ON readiness cycles preserve state/configuration and recover address/clock. Link loss, lease/name change, DNS/SNTP, journal rotation and autonomy remain. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

### Current retained-reply checkpoint

[Immutable results](phase11-5-completion-info-lifetime-result.json) and
[review](phase11-5-completion-info-lifetime-review.md). R1/R2 retain recorded
closure; R3-R6 remain OPEN. No new physical assertion closes.

A runs 0001a36 on boot 6213cc6b8d7694082fb804fdf5b121fc. Three maximum LOADs
returned all adjustments; the fresh-ID replay stopped after 49,152 of 52,105
request bytes when peak headroom failed at 31,680 against the 32,768-byte reserve.
The native observer supplied 23 STATUS replies. The workload remains failed.

Active replay decoding remains host-validated but was not reached by this partial
request. INFO now prepares its network snapshot before its outer buffer, avoiding
their formatting overlap. The final acceptance check follows authority cleanup,
so a failed peak cannot block release of an independently reconciled reservation.
Next: exact-image build and the same bounded affected zero-RF target check.

Both boards are Empty/inactive/unowned with schedules disabled and configurations
preserved. Shared reservation RELEASED after fresh authoritative reconciliation.
The prior fixture session is restored; the new one-hour session is ACTIVE with
independent cleanup due at host monotonic 435459994813000 ns.
Cumulative charge: three RF jobs / 384 seconds, four A flashes, two Wi-Fi cycles,
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
