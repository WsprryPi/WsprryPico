# Phase 11.5 Package 11 Retry 2 review

## Outcome

Package 11 and R6 remain **OPEN**. Retry 2 stopped before the shared RF
reservation and before any ARM. It charged zero RF jobs and zero RF time and
receives no R6 acceptance credit. The immutable aggregate record is
[phase11-5-package11-retry2-result.json](phase11-5-package11-retry2-result.json).

The repaired credential path passed on the live fixture: all six packet-bound
files were securely opened, hash-checked, owned by the root campaign user and
verified at mode `0600`. Both host fixtures reached ready. The next preflight
then sampled free heap 25 times over 360,001,652,399 ns. Available heap rose
from a minimum of 162,400 bytes to a maximum of 164,800 bytes and ended at
164,776 bytes, 224 bytes below the unchanged 165,000-byte gate. Allocator
failures remained zero. The runner stopped with `Memory headroom readiness
deadline` before reservation, capture, warmup or production work.

## Diagnosis

This is a host-fixture sequencing defect, not a demonstrated Pico capacity or
RF failure. Retry 1 had left eight valid, complete, output-inactive terminal
replay records. Firmware retains those records for one hour. Retry 2 began its
fixed 360-second memory window before the rolling retention times had all
expired, so free heap rose as records retired but the last records outlived the
window.

Fresh post-failure reconciliation found four complete, output-inactive records
still retained. The newest had 217,450,415,000 ns left in its one-hour lifetime.
This directly explains why waiting another few minutes would have changed the
preflight state. It does not justify lowering the heap threshold, changing
firmware retention or treating the stopped attempt as an R6 result.

## Accounting and restoration

Attempt 1 charged eight jobs / eight seconds, Retry 1 charged eight jobs /
eight seconds, and Retry 2 charged zero. Cumulative Package 11 use remains 16
jobs / 16 planned RF seconds. Retry 2 performed no flash, BOOTSEL transition,
CONFIG write, controlled reboot, intentional Pico Wi-Fi cycle or allocation
probe.

Fresh serial-bound inventories proved both Picos empty, unowned, schedule
disabled and output-inactive on their original boots. The shared reservation
remained released. Both host fixtures restored with no cleanup failures; the
installed WsprryPi service and both recovery timers are active. The client and
remote captures reported zero kernel drops. No campaign capture existed because
the reservation was never acquired.

## Repair and review

Retry 3 tooling now runs a separate read-only retained-terminal gate after the
installed service is paused and before the unchanged heap gate. Each bounded
USB inventory accepts at most eight unique terminal records, requires every
record to be complete and output-inactive, and refuses ownership, enabled
schedules, active output or more than 600 seconds of remaining retention. The
gate must observe zero terminal records before the original 360-second,
165,000-byte memory check begins. It does not clear records, lower a threshold
or change firmware behavior.

Changing the fixture authorization invalidated the earlier source-bound
credential retest. A second Linux host-only retest passed against fixture source
SHA-256 `fc3ea5e7ff8f4e8c3baa2573218ded881357198159f08482a42a1b2343581fdc`.
It again changed six synthetic files from UID 1000 to UID/GID 0, retained mode
`0600` and content hashes, and accessed no Pico, USB endpoint, network fixture,
service, reservation or RF path.

The stopped-attempt auditor passes. The
[Retry 2 adversarial assessment](phase11-5-package11-retry2-adversarial.json)
rejects all 32 altered claims across identity, dependencies, scope, threshold,
retention diagnosis, accounting, captures, restoration and evidence hashes.
The Retry 3 preflight review records the repair's second source assessment and
hardware-free validation.

## Remaining gate

The next physical action is the separately authorized
[Retry 3 prompt](phase11-5-package11-retry3-prompt.md). It keeps the fresh
campaign ceiling at 16 jobs / 356.8 planned RF seconds and the maximum
cumulative Package 11 total at 32 jobs / 372.8 seconds after a complete run.
A stopped Retry 3 cannot be replayed without new authorization.
