# STATUS timing investigation and tooling repairs

The [execution prompt](phase11-5-status-stall-prompt.md) was executed against
the preserved N1u failure. Three supported tooling defects were repaired. The
intermittent target stall remains unresolved; no firmware repair or new
acceptance case is claimed.

## Changes and regression evidence

`audit_phase11_5_load.py` now measures STATUS cadence from native TLS write-entry
timestamps. Previously it used successful write-return timestamps, which can
hide a late next start or falsely report one when a write itself takes time.
Failures now include the worst request pair, timestamps, gap and count. The
two-second maximum, count requirement and five-second response bound are
unchanged. Return-only `P115TLS1` evidence is rejected for this start-cadence
gate instead of being presented as a start measurement. Nine deterministic
tests cover boundaries, missing samples, ordering, window membership and the
full framing/schema audit path.

The Console decoder used by `phase11_5_inventory.py` incorrectly applied WTP's
signed 32-bit numeric rule to Console diagnostics. NETTRACE emits unsigned
packet hashes and native 64-bit counters. Console now admits signed 64-bit and
unsigned 64-bit integers while retaining duplicate-key, floating-point,
non-finite, Unicode and nesting checks. Framed WTP parsing retains its existing
integer restriction. The offline USB observer audit uses the same Console
decoder. Tests reproduce hash `2844794185`, check both numeric boundaries and
prove that the same value remains rejected in framed WTP.

The new diagnostic `phase11_5_trace_reader.py` limits new NETTRACE page starts
to a 50 ms budget per drain and at most sixteen pages. A slow in-flight page
finishes or fails within its existing five-second exchange deadline; remaining
pages resume after the next INFO sample. The initial diagnostic reader drained
up to sixteen pages without a time budget and delayed an INFO cycle by 2.080 s.
Seven tests cover slow-page yielding, fast drain, elapsed-time and page-count
limits, identity/sequence failures, an empty ring and exchange failure without
retry or cursor advancement. This limits additional
observer work; it does not relax INFO's cadence or claim trace collection has
zero timing effect.

These are analysis/diagnostic repairs. They do not establish a cause or repair
for N1u's target latency. No firmware or production-client behavior changed.

## N1u reanalysis

N1u retains its failed outcome and original evidence. The corrected maximum
write-entry gap is **2,696,674,577 ns**; the original reported
**2,696,718,780 ns** measured write returns. Both fail the same two-second gate.
The affected request IDs end in `83` and `84`; N180 contains 179 STATUS starts.
The slow request's write-entry-to-response delay remains 2,592,628,676 ns.

Browser status snapshots around that interval show maximum server-poll duration
473,507 us before and after the stall. USB continued responding. This excludes
one continuous 2.6-second server poll; it does not distinguish delayed input,
several shorter delays or transport retransmission. N1u has no packet capture.

## N1v: packet diagnostic, separate from acceptance

The [frozen packet](phase11-5-status-diagnostic-packet.json) ran one N300 with
USB360 on exact inhibited source `4058d3a4a951`, 150 MHz. It used the unchanged
production binary and browser driver. AP and independent-client captures were
added. This was a diagnostic with no RF jobs, full A2 family or acceptance credit.
Its [result and hashes](phase11-5-status-diagnostic-result.json) retain the details.

- 300 nominal production STATUS starts; maximum start gap 1.093768320 s.
- Maximum native write-entry-to-response delay 0.569649056 s.
- USB: 360 INFO and 72 STATUS/health samples; all original USB checks passed.
- Browser: 60 status and ten requests for each page/asset; all returned HTTP 200.
- Both captures contain 3,727 packets with zero kernel capture drops. Their
  multisets match on the normalized identity fields listed in the result.

The production connection used client TCP port 52816. Six 195-byte client
ciphertext segments repeated the same sequence and payload. The slowest
production response first appeared at the AP 481,240,300 ns after native write
entry, at the client 568,893,300 ns after entry, and in the native read at
569,649,056 ns. This localizes that particular reply's delay; it does not
attribute the absent N1u event.

One browser request took **3.982752259 s**. In TCP flow 54422, the Pico
acknowledged the complete ClientHello at 0.828381 s after request start, while
the first captured ServerHello appeared at 3.331710 s. The 2.503329 s gap lacks
a matching long server poll. Captures at the host cannot tell whether the Pico
submitted an earlier packet that failed to reach the AP. Kernel capture drops
are distinct from network loss; successful device submission is also distinct
from over-air delivery. The additional internal-trace diagnostic addresses
this remaining observation gap.

N1v restored A to original inhibited revision `802c91a7b86e-dirty`, boot
`9e5c43eb460df5b08ec2b15affee5134`, empty/inactive/unowned. B stayed unchanged.
The host fixture was restored, installed service PID 1957 remained unchanged,
and cumulative configuration writes reached twelve. The private archive is
`phase115-n1v-preserved-final.tar.gz`, SHA-256
`da75bb226615736e16eb23e415d72db5de0232c9abd2e6c8a9b77bff6bbc4c48`.

## N1w: trace-reader startup failure retained

The [trace packet](phase11-5-status-trace-packet.json) added bounded reads of the
existing inhibited NETTRACE through the observer's exclusively held Console
endpoint. It failed before production/browser load startup when the old decoder
rejected unsigned hash `2844794185`. No RF job or nominal interval ran. Both
packet captures contain zero packets, not evidence of a successful load.

A and the host were restored. A's restored boot was
`5bdde6480aedb5ffa5e130faa82b7f8c`; cumulative configuration writes reached
fourteen. Archive SHA-256:
`819ae8b4f6515d6bf8b66185f350b3979c095a93f88d26e9f1b0eb334d7dfb04`.
The Console parsing repair above was regression-tested before preparing
[the corrected N1x packet](phase11-5-status-trace-corrected-packet.json).

## N1x: internal trace identifies a delivery gap

The corrected decoder collected 568 consecutive internal trace events. The
additional trace-page burst then delayed an INFO cycle by 2.079526285 s and
triggered the original sampling gate. The supervisor stopped the load about
37.638 s after nominal start. This is a failed, shortened diagnostic, not a
completed N300 or acceptance pass. Device and host restoration succeeded;
A's restored boot was `5e8159e91b23e66e2cb8d0306103f7fa`, with sixteen cumulative
configuration writes. Archive SHA-256:
`9a054fc2a7bc5a5c258f0950e8f6edb595e5fcb9bf72914fd88b1e1f91fbe0af`.

Both host captures contain 562 packets and report zero kernel capture drops.
In browser TCP flow 47282, internal event 452 records a successful outbound
submission at device time 73,025,801 us: TCP sequence 10240, length 315 bytes,
IPv4 ID 219. That packet is absent from both host captures. Event 456 submits
the same TCP sequence/length at 74,451,604 us; this retransmission appears in
both captures and is acknowledged through sequence 10555. The interval between
the two submissions is **1,425,803 us**. The complete TCP flow lasts 2.780208 s.

This localizes that browser delay to delivery after successful device submission.
It does not identify whether the driver, radio path or AP discarded the packet,
and it does not retroactively establish the cause of N1u's uncaptured STATUS
stall. Host capture loss, RF-path loss and target service time remain distinct.

The trace-reader burst defect was fixed and regression-tested before preparing
[the budgeted N1y packet](phase11-5-status-trace-budgeted-packet.json).

## N1y: complete trace diagnostic and restored setup

[The final result](phase11-5-status-trace-result.json) records a completed
N300/USB360 on the same inhibited image, with bounded NETTRACE reads. Independent
audits passed: 300 production STATUS starts, maximum start gap 1.090124856 s,
maximum native write-to-response delay 0.821016690 s, and 360 INFO samples with
maximum start gap 1.186896401 s. STATUS/health each supplied 72 samples within
their original bounds. Browser status/page counts were 60/10/10/10; maximum
browser request duration was 3.033977811 s. No allocation failure or output fault
was observed. These results validate the repaired diagnostic within its scope;
additional trace traffic prevents treating it as the frozen A2 workload.

The complete internal trace contains sequences 1 through 3846 without gaps.
AP/client captures contain 3816/3820 packets, each with zero kernel capture
drops. Two further browser response segments were submitted successfully at
the Pico boundary but absent from both captures until retransmission:

| Client port | First trace event | TCP sequence / bytes | First IPv4 ID | Retransmission event | Submission gap |
| --- | --- | --- | --- | --- | --- |
| 54096 | 1077 | 11633 / 315 | 518 | 1082 | 1,465,136 us |
| 41190 | 1168 | 11934 / 315 | 561 | 1172 | 1,444,763 us |

Four outgoing client packets were present in the client capture but absent at
both the AP capture and the continuous DUT input boundary: three ACK-only
packets and one 1142-byte TLS segment. This also locates delivery gaps between
observed boundaries; it does not identify the precise driver/radio/AP component.
The original N1u STATUS stall was not reproduced and remains unattributed.
No firmware or production-client repair is supported by these observations.

A is restored to original inhibited revision `802c91a7b86e-dirty`, boot
`bbabf4bdffb92c6bb0f04f11929c2262`, with original configuration verified and
fresh Empty/inactive/unowned STATUS. B remains original inhibited revision
`dbf1d86f0885-dirty`, boot `4e2fb851c08b278dd4b977104d2c2aaa`, also
Empty/inactive/unowned. Host networking and the recovery timer are restored;
installed service PID remains 1957. Cumulative configuration writes are
eighteen, with zero Wi-Fi cycles, heap probes or RF jobs in these diagnostics.
Final private archive SHA-256:
`b7308d25a27ee1abd511120a18a33201961a9667bb261c823df0964749570269`.

All private archives have hash-verified local copies under
`build/phase11-5-closure`. The local analysis companion
`phase115-status-stall-analysis.tar.gz` has SHA-256
`3d475491002c54dead27cf0f9e975463a734e5bf4f26c635fd33551922b650bb`.
From the repository root, its `trace_boundary.py` takes an extracted diagnostic
root and reconstructs packet/trace matches using the existing trace validator.
Raw captures, credentials, firmware and generated analysis remain outside Git.

## Scope and review

All diagnostic packets retain N1u's original absolute host-cleanup limit,
123801490692568 host-monotonic ns. They do not extend the earlier network
authorization. Each uses independent device and host restoration and retains
prior operation counts. Additional NETTRACE reads change observer traffic;
trace diagnostics cannot be relabeled as the frozen A2 nominal workload.

Adversarial review found the return-only observer fallback, the Console/WTP
parser mismatch and the unbudgeted trace burst. Corrections were followed by
affected checks and another assessment. The final assessment found no further
actionable defect in these changes; it retains the original STATUS investigation
and physical acceptance gates as unresolved. No thresholds were relaxed and
no failed run was replaced by a later passing diagnostic.

The complete 57-test host suite passed in 20.11 s. The final additional
exchange-failure regression passed in the affected trace-reader suite. WTP
contract validation passed (23 schema, 7 raw JSON, 1 framing and 8 transition
cases), as did whitespace checks. Re-auditing all six historical N1t controller,
nominal and conditioning intervals with the corrected start-time audit passed;
those results remain bound to `8fb3894`. N1u still fails under the corrected
audit. N1v and N1y independently pass their declared diagnostic observations.

Phase 11.5 remains OPEN: historical A1/A2 for `8fb3894` are 2/20 cases; no
configuration is accepted. Selected physical 138 MHz / divider 1 / SRAM rendering
remains subject to affected A2/A3 checks. Physical 132/150 MHz remain untested.
Changing clocks in 11.6 repeats affected 11.5 checks; systematic band/mode/clock
and filter qualification remain Phase 13 work.

Documentation Impact: development tooling, diagnostic evidence and review in
the two authorized repositories. Operator settings and workflow are unchanged;
no change to the separate operator-documentation repository is required.
