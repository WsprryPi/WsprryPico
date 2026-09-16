# Phase 11.5 completion progress

**OPEN — 2/6 families closed.** [Current matrix](phase11-5-completion-matrix.md).

| Package | Status | Outcome / next requirement |
| --- | --- | --- |
| 0 | COMPLETE | Fresh named A/B USB inventories independently decoded; source-impact matrix and current summaries reconciled. [Result](phase11-5-completion-package0-result.json). |
| 1 | COMPLETE — individual capacity | 2.1a/2.1d/2.1e/2.1f/2.1g and authenticated controls pass on 8dd6f08 with three retained records, continuous observation and 55,944-byte minimum reserve. Prior P1g/P1h/P1i failures retained. [Review](phase11-5-memory-pressure-review.md). |
| 2 | COMPLETE — simultaneous capacity and overload | 2.2a accepts the declared supported overlap; 2.2b accepts the separate bounded 503 refusal and authenticated recovery. [Review](phase11-5-package2-review.md). |
| 3 | COMPLETE — network timeout and resource recovery | 2.2c–2.2f, 2.3a–2.3c and R3.BROWSER-MAX pass with current-image RF pressure, distinct WTP timeout evidence and browser-source applicability. [Review](phase11-5-package3-review.md). |
| 4 | COMPLETE — USB parser and unread output | 2.3d passes exact maximum USB parser pressure. The repaired 2.3e retest passes bounded unread-output deficit, same-session pre-DTR silence and fresh DTR recovery during RF. [Review](phase11-5-package4-review.md). |
| 5 | OPEN | Retained capacity/eviction/expiry and three equivalent cycles. |
| 6 | OPEN | All R3 groups and extended-feature applicability/closeout. |
| 7 | OPEN | Remaining R4 authority/interruption assertions after reuse. |
| 8 | OPEN; idle Wi-Fi accepted on source 98f5797 | Two independently audited OFF/ON readiness cycles preserve state/configuration and recover address/clock. Link loss, lease/name change, DNS/SNTP, journal rotation and autonomy remain. |
| 9 | OPEN | R6 mixed operation after R1-R5 acceptance. |

### Current Package 4 checkpoint

[Prompt](phase11-5-package4-prompt.md),
[review](phase11-5-package4-review.md),
[original result](phase11-5-package4-result.json) and
[repaired 2.3e result](phase11-5-package4-unread-retest2-result.json). Package 4
is complete on `ca3c5dce4036`, boot
`5e0d6bc3e383b8c1cb4b0db9ed636bf5`.

Assertion 2.3d accepts the exact 65,552-byte USB frame during a 100-second Tone,
directly observed equal parser reservation, independent authenticated network
authority, same-connection recovery and fresh post-DTR recovery.

Assertion 2.3e accepts a separate 100-second Tone. The runner offered 94 complete
STATUS requests while performing zero application reads for 12 seconds and
recovered only 11 responses plus a bounded partial response before close. It
then flushed only unsent host output with DTR asserted, observed two seconds of
same-session silence and recovered with fresh HELLO/STATUS after DTR. Network
and Console observers continuously bracketed Running. The job completed
inactive with zero allocator failures.

The original failed 2.3e attempt and the first focused retest remain retained.
The first retest charged one job but stopped before unread pressure because its
network observer was 232 ms ahead of the latest Console sample. The repaired
retry charged one additional job and physically passed the bounded transition
wait and unread recovery. Package 4 therefore charged 6 jobs / 600 planned
seconds across the original and separately authorized scopes, with zero flashes,
configuration writes, controlled reboots or Pico Wi-Fi cycles.

The [retry audit](phase11-5-package4-unread-retest2-audit-result.json) accepts
2.3e. Its [adversarial result](phase11-5-package4-unread-retest2-adversarial-result.json)
rejects 13 altered-evidence cases and reverifies the intact evidence. Both Picos
are Empty/inactive/unowned, configuration is preserved, the shared reservation
is released, and the host fixture is restored. Capacity and pressure is closed;
Package 5 retention/reclamation and Package 6 R3 closeout remain open. Phase
11.5 remains open at 2/6 families.

### Current Package 3 checkpoint

[Prompt](phase11-5-package3-prompt.md),
[review](phase11-5-package3-review.md) and
[result](phase11-5-package3-result.json). Assertions 2.2c–2.2f, 2.3a–2.3c and
R3.BROWSER-MAX are accepted on `ca3c5dce4036`, boot
`5e0d6bc3e383b8c1cb4b0db9ed636bf5`.

Two 100-second TLS-pressure jobs pass ten cases; two 150-second transport jobs
pass fourteen cases. Native and authenticated HTTP observation remained
continuous, raw captures dropped no packets, all four jobs completed and no
allocation counter increased. The zero-RF progress packet separately verifies
the 30-second drained inactivity path, five-second incomplete-frame path and
five-second no-output-progress path, including authenticated recovery and final
Empty state.

The current and accepted actual-browser sources contain the same `app.js` blob.
The current-image stalled page response supplies the affected allocation and
reclamation check, so the existing browser file/message/progress/cancellation
evidence remains applicable.

The adversarial assessment rejected 36 altered-evidence cases and reverified
all intact packets after strengthening raw peer, frame, HTTP, timeout and final
authority bindings. Failed attempts remain retained and receive no credit.
Package 3 charged seven RF jobs / 800 planned seconds: four accepted jobs / 500
seconds and three failed jobs / 300 seconds. It used no flashes, configuration
writes, controlled reboots or Pico Wi-Fi cycles.

A and B are independently Empty/inactive/unowned, configuration is preserved,
the host fixture is restored and the shared reservation is released. Package 4
subsequently accepted 2.3d and 2.3e. Package 5 retained reclamation and Package
6 R3 closeout remain open. R3 and full Phase 11.5 remain open at 2/6 families.

### Current Package 2 checkpoint

[Prompt](phase11-5-package2-prompt.md), [review](phase11-5-package2-review.md),
[current result](phase11-5-event-pages-result.json), and historical
[failed result](phase11-5-package2-result.json). Assertions 2.2a and 2.2b are
accepted on `ca3c5dce4036`, boot `5e0d6bc3e383b8c1cb4b0db9ed636bf5`.
The supported packet held 32,784 WTP parser bytes while authenticated HTTP
returned 200; the separate overload packet returned bounded 503
`resource_exhausted` and recovered on the same authenticated path. Both
128-second RF jobs completed with continuous native observation.

The event-storage repair first passed maximum 52,105-byte LOAD and replay with
zero RF. A failed proof packet is retained: its RF job completed, but an
aggregate heap-delta gate prevented HTTP stimulation. Direct WTP reservation
reporting repaired that evidence gate. Five altered raw-evidence cases were
rejected for each accepted packet.

A and B are independently Empty/inactive/unowned, configuration is preserved,
the host fixture is restored and the shared reservation is released. Package 2
charged two controlled flashes and three 128-second RF jobs, with no
configuration writes, controlled reboots or Wi-Fi cycles. Package 3 subsequently
accepted assertions 2.2c–2.2f. R3–R6 and full Phase 11.5 remain open.

### Historical memory-pressure checkpoint

[Prompt](phase11-5-memory-pressure-prompt.md),
[review](phase11-5-memory-pressure-review.md) and
[immutable result](phase11-5-memory-pressure-result.json).
The repair releases the 20,480-byte event vector only after acknowledged
independent engine handoff and preserves its original digest for replay. Input
admission now budgets temporary processing memory above the unchanged reserve.

A retains 8dd6f08, boot 7a04779b8018624574066260fce9d0d8; B retains 8921a7008183,
boot 6684b4b197d80cfa0ce83b3aaf205cb0. Both are independently Empty, inactive,
unowned and schedule-disabled, with configurations preserved. The host fixture
is restored and the shared reservation is released. No packet is running.
Three retained maximum LOADs plus replay and one 128-second RF capacity job pass
independent raw audit. First-attempt network readiness failure and its justified
single Wi-Fi recovery are preserved separately.

All 72 configured host test groups pass across the broad run and affected
reruns; three source mutations and eight altered evidence cases are rejected.
Final intact reassessment passes. Cumulative charges: seven RF jobs / 896
planned seconds, nine A flashes/BOOTSEL transitions, three Wi-Fi cycles, zero
configuration writes and zero additional controlled reboots. One historical
unplanned watchdog remains in P1h. P2–P9 remain open; no family or full
configuration acceptance is added.

### Historical retained-state checkpoint

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
