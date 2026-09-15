# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | OPEN — native connection failure | Original RF capacity failure preserved. Later packets stopped before ARM; completed-job storage blocked replacement LOAD under native TLS. Repair needs identified target build and affected retest. [Review](phase11-5-completion-terminal-storage-review.md). |
| 2 | OPEN | Supported simultaneous workload and separate bounded overload. |
| 3 | OPEN | Affected TLS/HTTP and distinct WTP timeouts. |
| 4 | OPEN | Actual USB parser and unread-output pressure. |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN; idle Wi-Fi accepted on source 98f5797 | Two independently audited OFF/ON readiness cycles preserve state/configuration and recover address/clock. Link loss, lease/name change, DNS/SNTP, journal rotation and autonomy remain. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

### Current connection-repair checkpoint

[Immutable results](phase11-5-completion-native-closure-result.json) and
[review](phase11-5-completion-native-closure-review.md). R1/R2 remain closed in
recorded scope; R3-R6 remain open. Idle Wi-Fi recovery retains its accepted
source 98f5797 scope. No new family closes.

A now runs bd16bb1 on boot 3dbf851d7107a714504e5f3dd52df4d9. P1e/P1f each
completed a 128-second maximum-event job, but neither exercised capacity probes.
P1e's new-policy readiness publication was missing; its wait also blocked lease
renewal. P1f repaired those defects and proved replacement maximum LOAD admission,
but the native TLS connection closed with a STATUS reply outstanding. Cached
identity must not be treated as live observer health. All failures are retained.

Latest packet inventories show A and B Empty/inactive/unowned, preserved
configurations and disabled schedules. A retains two Complete records; B is
unchanged. The shared reservation is released. The isolated fixture remains
active within its unchanged supervised deadline. Task charge: three RF jobs /
384 seconds, one A flash, two Wi-Fi cycles and zero configuration writes.

A bounded deferred-decoding repair, stronger native health gate and read-only
WTP close diagnostics pass host checks; they are not yet flashed or physically
accepted. Next: identified build and a zero-RF native connection test before any
further capacity RF packet.

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
