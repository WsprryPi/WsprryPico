# Maximum WTP components and observer cadence repair

**Phase 11.5 OPEN, 2/6 families closed.** [Result](phase11-5-completion-capacity-cadence-result.json).

P1g on clean e64ebb9 and A boot 0a6d95e11cf712a53e97a4c9938614e9 independently
supports 2.1a, 2.1d and 2.1e. The 512-event, 128-second job completed with the
expected 33,693 DMA interrupts, one launch and one tail interrupt; no duplicate
execution occurred. The 65,536-byte WTP payload wrote its complete 65,552-byte
frame and returned owned Running STATUS. The 65,537-byte declared payload and
following recovery wrote 65,748 bytes, returned one INVALID_FRAME event and a
successful same-session PING. Native Running replies independently bracket both
exchanges; 300 raw INFO samples cover the full observation and final completion.
Peak headroom was 48,136 bytes against the unchanged 32,768-byte reserve.

The full packet remains failed. Both exchanges were placed in one STATUS polling
action and took 3.055484557 and 3.508646855 seconds, excluding the small gap.
The next five-second polling start consequently missed its one-second allowance.
The HTTP worker's stale-observer guard stopped it before any HTTP request. Native
capture contains 86 successful STATUS replies but ends before full RF completion;
no full native/HTTP workload acceptance is claimed. RF completed locally despite
the failed USB observer. Final raw inventories prove A Complete/inactive/unowned,
B Empty, both schedules disabled, configuration preservation and reservation
release. No inactivity was inferred from the observer exit or expired owner lease.

The repaired harness performs exactly one bounded capacity exchange per polling
action. It keeps the existing individual exchange deadlines and observer rates,
and starts HTTP only after both successful WTP exchanges. Tests verify one wire
exchange per call, the measured durations fitting separate five-second intervals,
exact requests and the failure guard preventing a retry. Thirteen RF tooling tests,
twelve nominal-schedule tests and eight reservation tests pass. Two private audit
tests preserve component acceptance and reject incomplete writes, altered ARM
summaries and truncated native captures. The strict component auditor also checks
raw CRC/schema, exact adjustments, ARM identity/mapping, resource/timing gates,
configuration and shared reservation evidence independently of runner summaries.

P1h is a fresh bounded affected harness retest and HTTP continuation on the same
source/boot, preserving the one Complete record. Its one 128-second RF allowance
requires no flash, reset or configuration write. The full workload/cadence claim
requires a successful continuation; P1g's failed outcome will remain unchanged.
The fixed fixture cleanup deadline is not extended. No final P1h restoration or
phase/family closure is claimed in this checkpoint.
