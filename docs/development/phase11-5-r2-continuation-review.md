# R2 continuation, upload repair and adversarial review

## Preserved first continuation

The [remaining-mode packet](phase11-5-r2-remaining-packet.json) reused R1 and
three browser Tone jobs on 049cc929, physical 138 MHz/divider 1/RAM/listener on.
Native production QRSS ETE completed its full N300/USB360 audit, bringing the
accepted-job count to 4/7. Its job was `5ad286923dd906190000000000000001`;
launch epoch 1, post-enable observation delay 8 microseconds, 8,688 DMA IRQs
and one tail IRQ. The ordinary production executable owned that job.

The USB packet completed FSKCW and DFCW, then panicked during WSPR LOAD before
any WSPR ARM. Those two completions do not make the interrupted shared N300
interval pass. [The result](phase11-5-r2-remaining-result.json) retains that
failure, successful production audit and raw-evidence hashes.
The recorded panic stage/hash was 5/3833354787, matching `Out of memory` in the
exact failed ELF. The failing individual allocation was not captured.

Fresh inventories established the network-free recovery boot was Empty,
inactive and unowned. [Guarded recovery](phase11-5-r2-oom-recovery.md) restored
the original disabled configuration and inhibited image. Pico A's restored boot
was `03800628f67b8a96a251147b319b2772`; Pico B remained
`feffcd075ab6cb0b74e7e0c2fde6c87f`. Counts reached 32/32 CONFIG writes and six
historical probes. The host cleanup initially timed out waiting for a radio;
its later return was reconciled and idempotent owned cleanup completed. Both
original failed cleanup records remain preserved. Future cleanup now allows
60 seconds for radio return within its existing ten-minute outer bound.

## Repair and change-directed R1 reuse

[The executed repair prompt](phase11-5-r2-upload-repair.md) and
[build identities](phase11-5-r2-upload-builds.json) describe source
2e43110f05304efdc2ae25c298baa0ef6426955b. Frame storage now follows the validated
length; SHA-256 hashes without heap copies; LOAD acknowledgements reserve their
final size without a second full adjustments body. CRC-32C still protects frame
integrity. SHA-256 still provides the existing replay/job-content fingerprint;
neither the digest contract nor frame/job limits changed.

| R1 assertion | Reuse and affected checks |
| --- | --- |
| R1.1 layout/instrumentation | Rebuild selected listener-on physical and inhibited images, inspect linked allocator/guard/renderer checks and exact revision. Physical BSS is unchanged at 276,708 bytes; heap base/limit and both guard allocations are unchanged. Listener-off layouts remain historical evidence, not newly built configurations. |
| R1.2 inhibited regression | Retain 049cc929 N evidence for unchanged inhibited/network semantics. New-image inhibited startup, INFO/STATUS and configuration lifecycle provide targeted regression; no full inhibited interval repeat. |
| R1.3 allocation feasibility/recovery | Retain unchanged allocator-probe implementation and prior success/intentional-NULL/success result. Recheck actual maximum request, heap peak/reserve and zero unexpected failures while the changed WSPR LOAD/response executes under N. The old 18,364-byte probe is a lower bound, not an exact largest free block. |
| R1.4 same-boot retention | Retain the prior matched quiet/cache-expiry comparison: replay/terminal representations, capacities, expiry and ownership did not change. New storage is transient and released; SHA-256 retains no new state. This does not claim another measured quiet comparison on 2e43110. |
| R1.5 measurement cost/stacks | Preserve measurement implementation/semantics; inspect new static frames and recheck observed costs plus both physical stack guards/high-water under the changed workload. SHA frame 360→448 bytes; decode_request 560→848; encode_response 752→760; frame feed remains 96. Individual frames are not whole-stack bounds. |

RF worker, renderer, PIO/DMA, scheduling and waveform compilation are unchanged.
The new remaining-mode run nonetheless measures its own launch, full/short
refill and tail behavior. Old Tone and native QRSS evidence retains its original
049cc929 identity; it is reused through this impact assessment, not relabeled
as measured on 2e43110. Every full-block deadline remains calculated from
138 MHz: 3,799,188.406 ns interval and 2,849,391 ns conservative 75% budget.
Each short predecessor is calculated separately. Physical 132/150 MHz clocks
remain untested; full accepted configurations remain empty pending R3–R6.

## Review findings closed before final assessment

1. WSPR receive storage rounded to 32 KiB. A failing allocation regression now
   passes at the frame's declared size. Maximum-size, fragmented/combined and
   resynchronized frames retain their payloads and bounded allocation behavior.
2. SHA padding copied and expanded the entire input. Allocation-free hashing
   passes independent digest fixtures at empty, 55/56/63/64/65-byte padding
   boundaries, WSPR size and maximum frame size.
3. Adversarial review found the separate LOAD-response growth spike. Its failing
   162-adjustment test now passes below 18,364 bytes, with byte-compatible JSON
   established by an independently generated digest fixture.
4. Incremental target rebuilding initially retained the earlier embedded revision.
   Explicit reconfiguration corrected it before any new image was flashed.
   Superseded images/packet remain private, unexecuted records. The corrected
   [execution packet](phase11-5-r2-upload-execution-packet.json) binds source,
   images and helpers; the user approved 2e43110, the three jobs and writes 32→34.
5. The offline mode audit now binds the job packet to the observer's recorded
   SHA-256. Nine mutations of the successful QRSS evidence were rejected;
   intact evidence passed again. The failed USB interval was rejected.
6. Recovery admission explicitly distinguishes its expected empty runtime MAC
   from persisted hostname/control settings. Exact preserved evidence passes;
   twelve changed identity/state cases fail. The one-shot recovery completed.
7. Future management validation binds the extended write allowance to the frozen
   source. Its added check did not alter running frozen helpers; their recorded
   packet/state source identities match. Old sources retain the 32-write limit.
8. The new production job-binding file is now published by atomic rename, avoiding
   a consumer seeing an incomplete pre-dispatch identity. The executed earlier
   helper and its successful raw binding remain preserved unchanged.

9. Final publication review caught an existing historical result filename. The
   closure now uses its own `phase11-5-r2-closure-result.json`; the historical
   `phase11-5-r2-result.json` was verified byte-for-byte unchanged before staging.

Hardware-free validation: 53 CTest groups, including 29 core assertions; the
Phase 11.5 Python suite (147 discovered, 146 passed, one private-fixture test
skipped locally) and twelve Pi load-helper tests. The private new-image audit
ran on wspr5 as described below.

## Final R2 closure: 7/7 jobs, Phase 11.5 2/6 families

The [closure result](phase11-5-r2-closure-result.json) binds three earlier browser Tone
jobs and native production QRSS on 049cc929 to the affected-check review above,
and three newly measured USB jobs on clean 2e43110. R1 remains 5/5 through this
explicit reuse assessment; it was not rerun wholesale. R3–R6 remain open and the
full accepted-configuration list is empty.

All three new jobs completed during the same full N300/USB360 interval on
Pico A, physical boot `757e37c9681bd12e8065073f513914b1`, at 135.5 kHz through
the confirmed 50-ohm, 60 dB, unfiltered conducted path. The GPSDO settings and
Pico B were unchanged. Exact job IDs, counters and raw hashes are in the result.

| New job | Duration | Post-enable observation delay | Short predecessor | Short 75% budget |
| --- | --- | --- | --- | --- |
| FSKCW | 35 s | 8 µs | 8,092 words | 1,407,304.348 ns |
| DFCW | 17 s | 26 µs | 10,484 words | 1,823,304.348 ns |
| WSPR | 110.592 s | 10 µs | 6,144 words | 1,068,521.739 ns |

All expected per-job DMA/refill/launch/tail deltas passed. The cumulative worst
short reserve remains the FSKCW observation (7,775/8,092 words); it is not a
separate DFCW or WSPR maximum. Full-block worst refill-to-ready was 2,121,000 ns,
within its 2,849,391 ns budget. Heap peak was 146,716 of 218,284 bytes, leaving
71,568 bytes; the largest successful request was 18,364 bytes. Unexpected
allocator/TLS failures were zero. Core 0/1 observed stack use was 8,248/5,620
bytes and both guards remained valid. Software observations do not qualify
an electrical edge's UTC accuracy, RF decoding, SDR calibration or spectra.

## Explicit administrative STATUS amendment

All three jobs completed, but the original coordinator marked the interval
failed because STATUS request starts were 2.322236389 seconds apart. The earlier
request's valid response took 2.218080153 seconds, within the existing five-second
response deadline. The next request started 104.156236 milliseconds after that
reply. This is administrative network observation; the jobs' event timing is
local to the Pico. The evidence does not localize the delay to Wi-Fi or firmware;
the packet captures cover mDNS/NTP, not TCP.

After that distinction was explained, the user accepted the proposed rule with
“That sounds fine”: maintain one-Hz polling while no request is outstanding,
keep the five-second response deadline, and retain longer in-flight start gaps
as telemetry. The amended assessment is explicitly named `single-flight-admin-v1`.
It preserves the existing one-second offer tolerance beyond the nominal polling
period, checks single-flight request/reply binding and interval boundaries, and
adjusts the minimum request count only for measured in-flight time beyond the
one-second poll period. It does not excuse late requests when the host is free
to send. The implementation is opt-in for R2 USB contention; legacy audit defaults
and the native QRSS scheduler policy are unchanged. Future packets must name
their applicable policy explicitly.

The complete amended audit passed: 317 STATUS starts in N300, maximum eligible
offer delay 105.183828 ms, one connection/session, all eight browser actions and
14 GETs. The actual 2.322-second start gap remains in telemetry. The frozen
`modes-result.json` remains FAILED and the earlier diagnostic remains
`FAIL_CADENCE_OTHER_CHECKS_PASSED`; separate `usb/amended-audit.json` and
`usb/amended-adversarial-review.json` record the new assessment. No raw capture,
executed helper or packet was changed. No additional RF or flashing ran for
this amendment.

## Final adversarial assessment and restoration

The [offline review helper](../../scripts/phase11_5_r2_admin_review.py) runs against
the preserved evidence root and a separate review checkout containing the amended
auditors. Reproduce on wspr5 with `python3 scripts/phase11_5_r2_admin_review.py
/home/pi/phase11-5-r2-upload-2e43110 REVIEW_REPO` (root access is needed to read
the private campaign). It preserves the original strict failure, audits intact
evidence, rejects nine temporary-copy mutations, audits intact evidence again,
and writes only separate derived reports. Mutations cover frozen packet duration,
source, job duration, extra fields, coordinator failure, tail/launch evidence,
allocator failures and a stack guard. The prior QRSS review independently rejected
nine mutations. Seventeen deterministic cadence tests include the newly permitted
pending-reply case and rejected deadline, overlap, missing reply, sparse sampling,
late eligible poll and missing boundary coverage. The final repeat assessments
found no remaining actionable R2 findings. R3–R6 are separate unfinished families.

Pico A returned to original inhibited `802c91a7b86e-dirty`, boot
`587c672d4267e467649bb43765542284`; Pico B remained `dbf1d86f0885-dirty`, boot
`feffcd075ab6cb0b74e7e0c2fde6c87f`. Final authoritative inventories showed both
Empty, inactive and unowned, with original configurations matched. Host cleanup
completed with no failures; original interfaces/routes, installed WsprryPi PID
1957, permanent time.local files and active chrony/GPS-PPS/Avahi were verified.
Chrony remained stratum 1/PPS. CONFIG accounting is **34/34**, with six historical
heap probes and no new probes. Future writes need a new bounded allowance.
The WsprryPi changes are confined to the opt-in production load helper, its tests
and companion review; the installed production executable was unchanged.
