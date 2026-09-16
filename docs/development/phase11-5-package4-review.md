# Phase 11.5 Package 4 execution and adversarial review

## Outcome

Package 4 is **COMPLETE**. Assertion **2.3d USB parser pressure** and
assertion **2.3e USB unread-output pressure** are accepted. The original 2.3e
packet and the [first focused retest](phase11-5-package4-unread-retest-result.json)
remain failed evidence. The repaired
[second focused retest](phase11-5-package4-unread-retest2-result.json) ran the
missing same-session silence and DTR recovery sequence during one bounded RF
job and passed independent and adversarial audit.

The executed scope is the [Package 4 prompt](phase11-5-package4-prompt.md). The
[audited result](phase11-5-package4-result.json) binds source
`ca3c5dce4036`, image
`6c7aa0b7df6756e8f248570d682c6af4bbcfc44a5ad67e94d6761709ced0bd59`
and A boot `5e0d6bc3e383b8c1cb4b0db9ed636bf5`. B remained the independently
observed comparator on boot `6684b4b197d80cfa0ce83b3aaf205cb0`.

## Accepted 2.3d evidence

Packet `6de855e36977a824498d920fce9eeff9c4bfd9b087c8964966d93f7daa68522f`
sent the exact 65,536-byte WTP payload, 65,552 bytes including the frame header,
through USB in bounded 512-byte writes during a network-owned 100-second Tone.
Console INFO directly observed `wtp_input_reserved_bytes` reach 65,552. The
maximum request returned the exact Running job and owner, a PING succeeded on
the same USB connection, and a fresh HELLO/STATUS succeeded after DTR recovery.

The independent TLS 1.3 WTP owner and Console observer bracket the USB interval.
The hardened auditor reconstructs 242 raw authenticated network requests, 251
network messages, 324 raw Console INFO exchanges and the raw USB parser reply.
The RF job completed locally with output inactive. Final reconciliation records
both planned Package 4 jobs as complete and returns A to Empty.

## Accepted 2.3e evidence and retained repairs

The accepted retry offered 16,384 bytes containing 94 complete STATUS requests
and performed zero application reads for 12 seconds. It recovered only 11
complete responses plus a bounded 144-byte partial response before closing the
read interval. This establishes the required bounded response deficit while
203 authenticated network STATUS samples and 262 raw Console INFO samples
continued to bracket the exact Running job.

The runner then discarded only the host-side unsent output queue with
`tcflush(TCOFLUSH)` while DTR remained asserted. A PING written on that same
session produced zero bytes for two seconds. After DTR recovery, a fresh USB
HELLO and STATUS succeeded. The 100-second Tone completed locally with output
inactive, allocator failures remained zero, A returned to Empty, B remained
unchanged and the reservation was released.

The earlier failures remain part of the record. The original packet could not
write the silence probe because the host output queue was still full. The first
focused retest reached Running, but stopped before unread pressure because the
network observer was 232 ms ahead of the latest Console sample. The repaired
runner waits up to two seconds for Console to advance from Armed to Running and
performs bounded terminal observation and release after a post-ARM observer
failure. The accepted retry physically exercises both repairs.

## Retained attempts and finite budget

All failed attempts remain evidence and receive no assertion credit.

| Packet | RF charge | Outcome |
| --- | ---: | --- |
| `d09c9a35ce35b00a57004a69290cc6ad39a439e2dcd6c31014da3e88c63f21d8` | 0 | Stopped before RF because A had associated without an address or route. One host AP station eviction restored association; no target write, reboot or Wi-Fi cycle occurred. |
| `8896f2cbf44dff298864600bbcd8656314fc61638f2df71eceaa4221f208b983` | 1 job / 100 s | Console INFO was incorrectly treated as if it contained network job/owner fields. The completed job was reconciled by packet `9f110f5e99f1391102a39afd6741a863377ff949ffa0f59ff4fd75bf9b4d38a9`. |
| `5c999fd00d27f041a79d0991ca1d58e8555b4dc3df5b72911b264958fcd207e4` | 1 job / 100 s | The first case ran, but the second-case gate counted only 45 seconds instead of the preceding 100-second job plus margin. Packet `fbd68f1f4215bbc1d5c136ae1e02809e7bd6013ea2966fef898a4806ee657829` reconciled the completed job. |
| `6de855e36977a824498d920fce9eeff9c4bfd9b087c8964966d93f7daa68522f` | 2 jobs / 200 s | 2.3d passed. 2.3e stopped at the silence-probe write. Zero-RF packet `d0c521b5f4976b9a0af0ed38fc933e07b16a89d4eb7f54e7bd58bc18591e121d` reconciled the second completion and released the reservation. |
| `10fe965e5ac0e15d58226aaab598ca9671ed0d5009149e5f737b26f6499607ba` | 1 job / 100 s | User-authorized focused 2.3e retest. The Tone completed, but a 232 ms Console/network transition race stopped the harness before unread pressure. No 2.3e credit. Zero-RF recovery released Complete to Empty and reconciled the reservation. |
| `e948cff5ab87532ebb35e3956613fda0b2b2748e7f077f4177b9a7c9b7f59816` | 1 job / 100 s | User-authorized repaired 2.3e retest. The complete unread-pressure, same-session silence and fresh DTR recovery sequence passed; the Tone completed inactive and independent audit accepted 2.3e. |

The original Package 4 campaign reached its absolute ceiling of **4 RF jobs /
400 planned seconds**. Two separately authorized focused retest packets each
charged **1 RF job / 100 planned seconds**. Across all scopes Package 4 charged
6 jobs / 600 planned seconds and used zero flashes, configuration writes,
controlled reboots or Pico Wi-Fi cycles.

## Adversarial review

The first review found that the auditor used incorrect staged source paths,
compared the string-valued launch epoch as an integer without conversion, and
required an observer sample inside every short pressure interval instead of
binding the measured adjacent-sample cadence. Those defects were repaired. The
auditor was then strengthened to reconstruct the raw network stream, every raw
Console INFO response and the raw parser response instead of trusting decoded
summaries.

The [final adversarial result](phase11-5-package4-adversarial-result.json)
rejects all 13 mutations: packet identity, staged source, TLS peer, raw network,
raw Console, parser length, raw parser response, parser recovery, fabricated
unread proof, changed failure reason, result overclaim, reconciliation state and
reservation identity. The intact evidence then passed again as
`PACKAGE4_PARTIAL_VERIFIED`. No actionable auditor finding remains.

The focused retest's acceptance auditor correctly rejects the failed packet.
Its separate [failure audit](phase11-5-package4-unread-retest-audit-result.json)
reconstructs 25 raw network requests, 28 network messages, 34 raw Console INFO
exchanges, the 232 ms Armed-to-Running observer gap, the local inactive
completion, zero-RF Complete-to-Empty release, reservation reconciliation and
host restoration. The [failure adversarial result](phase11-5-package4-unread-retest-adversarial-result.json)
rejects all 10 mutations and reverifies the intact failure evidence.

The repaired retry's
[acceptance audit](phase11-5-package4-unread-retest2-audit-result.json)
reconstructs the exact offered stream, delayed response capture, same-session
silent probe, fresh recovery, independent Running brackets, one completed RF
launch, final A/B state, reservation lifecycle and fixture restoration. During
review, the first final-state mutation was found to alter a non-authoritative
duplicate record. The mutation was corrected to alter the authoritative final
STATUS. The full
[adversarial assessment](phase11-5-package4-unread-retest2-adversarial-result.json)
then rejected all 13 altered-evidence cases and reverified the intact evidence
as `PACKAGE4_2_3E_VERIFIED`. No actionable finding remains.

## Restoration

Zero-RF reconciliation left A and B Empty, inactive and unowned, preserved both
configurations and released the durable two-Pico reservation. Fixture cleanup
recorded no failures and restored the exact preflight interfaces and routes,
the protected time service files, and installed WsprryPi PID 1957 on host boot
`220e53ca-ca95-4206-9581-dbe28aa1eeb8`.

Both focused retests independently reached the same restored state after their
single Tones completed: both Picos Empty/inactive/unowned, reservation Released,
fixture cleanup with no failures, exact preflight interfaces/routes and the
same installed PID 1957.

Package 4 is complete and the capacity-and-pressure execution group is closed.
Package 5 retention/reclamation and Package 6 R3 closeout remain open. Phase
11.5 remains open at 2/6 families.
