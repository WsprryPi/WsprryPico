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

### Current HTTP allocation checkpoint

[Immutable results](phase11-5-completion-http-pages-result.json) and
[review](phase11-5-completion-http-pages-review.md). R1/R2 retain recorded closure;
R3-R6 remain OPEN. P1g's 2.1a/2.1d/2.1e evidence remains on e64ebb9 and its original
boot. The idle replay pass remains on b0254c5.

P1h fully wrote the supported 32,768-byte HTTP body during Running, but received
no response. The board entered a watchdog recovery boot with a recorded failed
32,769-byte allocation. This packet receives no HTTP or RF-completion credit.
The parser's contiguous body allocation is replaced by nullable 4 KiB pages;
maximum-body, page failure/lifetime, replay and configuration tests pass.
Seven affected CTest groups, TLS and two altered-evidence tests pass. Target
retest and candidate resource/layout applicability remain outstanding.

A retains e64ebb9, boot cb429dd3964439e66e03bb0d93a9863b, Empty/inactive/unowned
in recovery mode, with networking intentionally off. B retains 8921a7008183,
boot 6684b4b197d80cfa0ce83b3aaf205cb0, Empty/inactive/unowned. Fresh post-restoration
raw inventories confirm disabled scheduling and preserved visible saved
configuration. The shared reservation is RELEASED. Fixture cleanup completed
at host monotonic 435282842781484 ns, before its independent deadline; protected
files, services, management interfaces, time service and installed PID 1957
were restored. There is no active fixture.

Cumulative charges: five RF jobs / 640 planned seconds, six A flashes/BOOTSEL
transitions, two Wi-Fi cycles, zero configuration writes and zero additional
controlled reboots. One unplanned watchdog reboot is recorded separately.

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
