# Phase 11.5 Package 4 execution and adversarial review

## Outcome

Package 4 is **PARTIAL and remains OPEN**. Assertion **2.3d USB parser
pressure is accepted**. Assertion **2.3e USB unread-output pressure remains
open** because the retained run did not write its same-session silence probe
and therefore did not establish pre-DTR silence or fresh post-DTR recovery.

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

## Open 2.3e evidence and repair

The unread-output case offered 16,384 bytes containing 94 complete STATUS
requests, performed zero application reads for 12 seconds, then recovered only
7 complete responses plus a bounded 656-byte partial response. This proves that
the deliberate no-read workload created a bounded response deficit while the
network owner and Console observer continued to report the exact Running job.

It does not close 2.3e. The host tty still held unsent request bytes after the
target endpoint stopped consuming input. The file descriptor never became
writable for the same-session PING, so the harness stopped with
`Unread USB silence probe write`. No `usb_unread_silent` or
`usb_unread_recovery` record exists. The later same-job recovery attempt began
after the 100-second Tone had completed and receives no acceptance credit.

The runner now discards only the host-side unsent output queue with
`tcflush(TCOFLUSH)` after the bounded response drain and while DTR remains
asserted. It then sends the proof PING before toggling DTR. This repairs the
harness mechanism that blocked the probe. The fix is covered by source and host
checks but is **not physically retested**, so 2.3e remains open. A future packet
needs one bounded unread-output job that records the same-session silent PING,
fresh post-DTR HELLO/STATUS, continuous independent authority and final
restoration.

## Retained attempts and finite budget

All failed attempts remain evidence and receive no assertion credit.

| Packet | RF charge | Outcome |
| --- | ---: | --- |
| `d09c9a35ce35b00a57004a69290cc6ad39a439e2dcd6c31014da3e88c63f21d8` | 0 | Stopped before RF because A had associated without an address or route. One host AP station eviction restored association; no target write, reboot or Wi-Fi cycle occurred. |
| `8896f2cbf44dff298864600bbcd8656314fc61638f2df71eceaa4221f208b983` | 1 job / 100 s | Console INFO was incorrectly treated as if it contained network job/owner fields. The completed job was reconciled by packet `9f110f5e99f1391102a39afd6741a863377ff949ffa0f59ff4fd75bf9b4d38a9`. |
| `5c999fd00d27f041a79d0991ca1d58e8555b4dc3df5b72911b264958fcd207e4` | 1 job / 100 s | The first case ran, but the second-case gate counted only 45 seconds instead of the preceding 100-second job plus margin. Packet `fbd68f1f4215bbc1d5c136ae1e02809e7bd6013ea2966fef898a4806ee657829` reconciled the completed job. |
| `6de855e36977a824498d920fce9eeff9c4bfd9b087c8964966d93f7daa68522f` | 2 jobs / 200 s | 2.3d passed. 2.3e stopped at the silence-probe write. Zero-RF packet `d0c521b5f4976b9a0af0ed38fc933e07b16a89d4eb7f54e7bd58bc18591e121d` reconciled the second completion and released the reservation. |

The Package 4 campaign reached its absolute ceiling of **4 RF jobs / 400
planned seconds**. It used zero flashes, configuration writes, controlled
reboots or Pico Wi-Fi cycles. No additional RF job was started after the
ceiling was reached.

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

## Restoration

Zero-RF reconciliation left A and B Empty, inactive and unowned, preserved both
configurations and released the durable two-Pico reservation. Fixture cleanup
recorded no failures and restored the exact preflight interfaces and routes,
the protected time service files, and installed WsprryPi PID 1957 on host boot
`220e53ca-ca95-4206-9581-dbe28aa1eeb8`.

Package 5 and Package 6 remain blocked behind completion of 2.3e because
Package 4 has not closed both USB pressure mechanisms. Phase 11.5 therefore
remains open at 2/6 families.
