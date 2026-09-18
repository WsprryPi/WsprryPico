# Phase 11.5 Package 11 Retry 1 review

## Outcome

Package 11 and R6 remain **OPEN**. Retry 1 is a preserved host-fixture tooling
failure and receives no R6 acceptance credit. Its immutable aggregate record is
[phase11-5-package11-retry1-result.json](phase11-5-package11-retry1-result.json).

The attempt passed the repaired clock-readiness path, completed all eight
one-second warmup jobs and measured the full 360-second matched baseline at
56,216 allocated bytes. Baseline timing remained inside the fixed 2,849,391 ns
limit: `rf_max_service_gap_ns` was 2,166,000 and
`max_refill_irq_to_ready_ns` was 2,157,000.

Cycle 1 then reached its normal-load start, but WsprryPi exited before readiness
or any production ARM. The six staged credential files were mode `0600` and
owned by `pi`; the systemd campaign ran WsprryPi as root. WsprryPi accepts a
private key only when it is a protected regular file owned by its effective user
or root. The runner therefore reported `Production exited before readiness`,
and WsprryPi reported `TLS credentials require regular protected files; private
key requires owner-only permissions`.

This is a host-fixture defect. It is not a Pico, RF timing, firmware resource or
WTP failure. No production job was armed, no normal cycle or post-N resource
window completed, and neither the baseline resource value nor its timing values
earn R6 credit.

## Accounting and restoration

Retry 1 charged eight RF jobs and 8,000,000,000 planned RF ns, all from the
completed warmups. Together with Attempt 1, cumulative Package 11 use is 16 RF
jobs and 16,000,000,000 planned RF ns. There were no flashes, BOOTSEL
transitions, CONFIG writes, controlled Pico reboots, intentional Pico Wi-Fi
cycles or allocation probes.

Fresh serial-bound inventories proved both Picos Empty, unowned, schedule
disabled and output-inactive on their original boots. The shared reservation
was then released. Both host fixtures restored with no cleanup failures; the
installed WsprryPi service and both recovery timers are active. All three packet
captures reported zero kernel drops.

The Bohica and Bohica-IoT management-router flaps are retained as external
management events. They are not used as product evidence or as the cause of the
credential failure.

## Repair and review

The fixture now binds all six credential contents in the frozen packet. After
arming cleanup and before the first radio mutation, it opens each credential
with symlink refusal, requires a nonempty regular file with link count one,
verifies its packet hash, sets its owner to the effective campaign UID/GID and
mode to `0600`, and verifies the open descriptor. It records only path, hash,
UID/GID and mode.

The Linux host-only retest in
[phase11-5-package11-credential-retest-result.json](phase11-5-package11-credential-retest-result.json)
passed on wspr5: six synthetic files changed from UID 1000 to UID/GID 0 with
mode `0600` and unchanged content hashes. It used no Pico, USB endpoint,
network fixture, service or reservation and charged zero RF.

The independent stopped-attempt auditor passes. The
[adversarial assessment](phase11-5-package11-retry1-adversarial.json) rejects all
31 mutations across identity, dependency hashes, completed scope, timing,
classification, accounting, external-event treatment, capture integrity,
restoration and evidence hashes, then revalidates the intact result.
The subsequent [Retry 2 preflight review](phase11-5-package11-retry2-preflight-review.md)
records the credential parent-directory and repeated-verification auditor fixes,
their affected tests and the clean second adversarial assessment.

## Remaining gate

The next physical action is the separately authorized
[Retry 2 prompt](phase11-5-package11-retry2-prompt.md). It preserves both prior
charges and both repairs, authorizes one fresh 16-job / 356.8-second campaign,
and caps cumulative Package 11 use after a complete run at 32 jobs / 372.8
seconds. Retry 2 has not been authorized or executed by this review.
