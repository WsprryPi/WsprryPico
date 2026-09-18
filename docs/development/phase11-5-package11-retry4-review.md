# Phase 11.5 Package 11 Retry 4 execution and adversarial review

## Decision

**PASS — R6 and Phase 11.5 are closed for the recorded 138 MHz/divider-1
configuration.** The independently audited Retry 4 result is
[`phase11-5-package11-retry4-result.json`](phase11-5-package11-retry4-result.json),
SHA-256 `ecb31bd3518de8831a44b57347363fb2aa65398027bc1df072ae92c5823377fe`.
The adversarial result is
[`phase11-5-package11-retry4-adversarial.json`](phase11-5-package11-retry4-adversarial.json),
SHA-256 `45fb2ce999493cc09606e1f45ff7c67251855f06d1c898926570be2fe98dbe5c`.
Raw journals, packet captures, credentials and authenticated payloads remain in
the private wspr5 evidence root; the repository contains aggregates and hashes.

The executed authorization was
[`phase11-5-package11-retry4-prompt.md`](phase11-5-package11-retry4-prompt.md).
It allowed one fresh run, at most 16 jobs and 480 planned RF seconds, with no
flash, BOOTSEL, CONFIG write, controlled Pico reboot, intentional Pico Wi-Fi
cycle or allocation probe. The frozen packet SHA-256 is
`9d2a7ad0893a8ad5968de5cab99313229f14bb7e78a15afd670c31e946b0a5fb`.

## Physical result

Retry 4 completed the exact 16-job workload and charged 356.8 planned RF
seconds: three production-class normalizers, five maximum-class normalizers,
one matched baseline, three native 114.6-second WsprryPi production jobs, five
maximum-class refresh jobs and final Q. The three 600-second normal intervals
totaled 1,800 seconds and produced 48 browser actions, 84 successful GETs and
three independently observed USB lifecycles through `complete`, terminal
retention and owner release.

The matched allocated-heap windows were 56,984 bytes at baseline; 57,080,
57,128 and 56,608 bytes after N1-N3; and 57,032 bytes at final Q. Every delta
was within the unchanged 1,024-byte limit. The post-N span was 520 bytes and
was not monotonically increasing. Peak allocation was 166,840 of 218,808 bytes,
leaving 51,968 bytes, above the 32,768-byte reserve. Core stack use was 8,600
and 900 bytes with valid guards. Maximum refill latency was 2,157,000 ns and
maximum RF service gap was 2,185,000 ns, both below 2,849,391 ns. Allocation,
TLS allocation, DMA, refill pairing, invalid-reserve, engine and recorded-fault
counts remained zero. Both captures reported zero kernel drops.

The run finished with Pico A empty, unowned and output-inactive on its frozen
boot; Pico B remained empty and inactive on its frozen boot. The shared RF
reservation was released. wspr4 and wspr5 restored their management links,
fixture state, recovery timers and installed WsprryPi service. Router address
flapping observed after capture did not occur inside the accepted evidence and
is not assigned a product cause.

## Preserved failures and accounting

Attempt 1 remains stopped after 8 jobs/8 seconds, Retry 1 after 8 jobs/8
seconds, Retry 2 before reservation at 0/0, and Retry 3 after 9 jobs/122.6
seconds. Their clock-poll, credential-owner, retained-terminal/memory and USB
event-reducer findings remain bound to the final result with their zero-RF
repairs. Retry 4 brings cumulative Package 11 accounting to 41 jobs and 495.4
planned RF seconds. Earlier Package 9 resource failure and Package 10 fixture
blocker remain historical failures; they were not relabeled as passes.

## Audit repair and adversarial assessment

The first independent audit correctly stopped on a stale Package 10 source
baseline inherited by the Package 11 adapter. Continuing the audit exposed
three more parent-auditor defects: Python tuple/list inequality for an otherwise
exact JSON browser schedule, journal emission timestamps used instead of the
resource window's measured bounds, and an assumption that both capture files
used the Package 10 one-host names and text format. The final source review also
found that capture summaries did not independently require nonempty bound pcap
files or reconcile the AP JSON kernel count. The audit repair:

- validates the exact Retry 4 repository baseline and source-impact decision;
- compares browser actions in their JSON list representation;
- verifies quiet duration from the bound measurement start/end fields; and
- accepts an explicit separate AP capture root, name and JSON summary while
  requiring reconciled positive packet counts, zero drops and nonempty bound
  pcap files.

The repaired auditor ran from a separate audit-only directory. It did not edit
the packet or private evidence. The frozen staging hashes still bind the exact
runner inputs; the published result binds the repaired auditor and raw-audit
hashes.

The final adversarial assessment rejected all 67 mutations. It covers closure
status, candidate and host identity, source impact, fixture separation,
authorization and dependency hashes, all prior and cumulative charges,
workload/lifecycle counts, replay classes, quiet and resource gates, timing,
captures, reservation and restoration. A second local execution reproduced the
same adversarial JSON byte-for-byte. No actionable finding remains.

## Accepted configuration and boundary

Phase 11.5 accepts Pico A source `91933c00970939e366d1bfcf3c1956b59be8f6c5`,
image `5da240aacf20e27db79126a7bff2be18e4ece849a608fa439f4e0c577659f446`,
boot `ff719d304f1ba4ac23fddd93561b26f0`, RP2350 Arm at 138 MHz, divider 1,
GP2 PIO/DMA, RAM rendering and the configured network listener. Phase 11.5 does
not qualify another clock. Selecting one during Phase 11.6 requires the affected
11.5 checks. Per-band/per-mode conducted RF acceptance remains Phase 11.6; the
broad clock, band, filter and spectral matrix remains Phase 13.
