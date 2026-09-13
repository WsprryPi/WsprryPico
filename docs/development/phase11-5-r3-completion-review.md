# R3 execution, causal diagnosis and adversarial assessment

R3 remains **OPEN, zero accepted complete physical pressure assertions**.
The [comprehensive prompt](phase11-5-r3-completion-prompt.md) was rendered and
execution proceeded through A1c, A1e and A1f. The approved A1e Wi-Fi recovery was
executed. Three new 100-second Tones completed across A1e/A1f; no configuration
save, flash, reboot or heap probe occurred. The original A1/A1b failures remain
preserved. Phase 11.5 stays 2/6 closed, R1 5/5 and R2 7/7; the accepted-configuration
list is empty. Completing the full R3 register remains unfinished.

The [A1g proposal](phase11-5-r3-retained-a1g-execution.md) is prepared locally,
unexecuted, and awaits agreement on its explicit prospective observation
criterion. It cannot award retrospective credit to A1f. This is a measurement
policy decision, not an unresolved automatic approval rejection.

## What ran and what failed

| Attempt | Actual execution | Evidence-backed disposition |
| --- | --- | --- |
| A1c | Reconciled the previous completed job, created the retained-input fixture; no new RF | Twenty-five network readiness inventories failed address/clock admission, ending at CYW43 -3. Root cause remains unlocalized. A/B and host cleanup passed. |
| A1d | Staged only, never launched | Automatic review rejected the newly added Wi-Fi OFF/ON action. The assistant had not asked the user. This was not a user refusal. A1e superseded it. |
| A1e | User explicitly approved the recovery packet; one idle OFF/ON cycle; one 100-second Tone | Network/clock admission recovered. Pressure stopped on a valid INFO read in flight. One job completed; the second was never submitted. Observer continued 360 seconds. Confirmed harness defect. |
| A1f | No further Wi-Fi cycle; two 100-second Tones, all ten traffic cases, 300-second production load and 360-second USB observation | All workers exited successfully. The frozen audit failed on a nonzero initial event ID. Offline reconstruction found three audit integration defects and a separate frozen INFO completion-bracket miss. Zero acceptance remains. |

A1c's 30 raw inventories and guarded HELLO/STATUS/CLAIM/RELEASE/STATUS cleanup
prove that the known previous job was cleared without new RF and with terminal
history retained. Identical private input hashes alone did not identify the
network failure's cause. A1e compared the active AP input locally, recording only
`psk_matches_retained=true`, and retained the exact OFF/ON ACKs. Recovery worked;
that does not prove why authentication had previously failed.

### A1e: primary failure and consequences

The pressure tool stopped at host monotonic time 206694063600406 ns because the
previous INFO sample was 2.045480670 seconds old. The replacement INFO request
had already been in flight for 1.338980126 seconds. It completed in
**1.739071744 seconds**, within its five-second deadline. Maximum INFO request
start gap was **1.752339449 seconds**, within the existing two-second cadence.
Both bracketing raw INFO samples proved Running output in the correct epoch.

`Pressure.checkpoint()` omitted the pending-read argument that the shared
`admit_snapshot()` already supports. The repair passes the current raw operation
snapshot and retains its PID/start/hash/operation/deadline checks. It does not
extend a deadline. Load termination followed the pressure stop; the later
“Remaining USB jobs did not finish” referred to the unsubmitted second job.
Those are consequences, not independent target failures. The observer retained
360 INFO, 72 STATUS and 72 host-health samples over 360.015244001 seconds.
Final known Complete/inactive/unowned state was safely reconciled to Empty.

### A1f: audit defects versus a real frozen observation miss

Raw USB events are consecutive IDs **14 through 25**. WTP defines boot-scoped
IDs; `Endpoint::connect()` preserves the counter unless the boot changes
(`src/wtp/endpoint.cpp`). A new capture therefore need not begin at zero.
The auditor now accepts an arbitrary first ID while requiring subsequent IDs
to be consecutive, checking schema/session/boot and independently reconstructing
STATUS, mutation order and the complete job lifecycle. A valid-CRC mutation of
an internal event ID still fails the gap check.

The shared load auditor also retained two R2 assumptions: it rejected R3's
predeclared `single-flight-admin-v1` scope, and expected the R2 coordinator's
`result` envelope instead of the actual R3 `status` envelope with `pressure_exit`.
The adapters now recognize those exact schemas. Failed/missing worker outcomes
still fail. No firmware, workload or transaction deadline changed.

After those repairs, independent raw USB, production TLS wire, both finite job
lifecycles, per-job DMA/refill/launch/tail deltas, resource reserves, full coverage
and final release all pass their component checks. One separate gate remains:
after `recover-slots`, the following INFO reply completed **2.262550925 seconds**
after case completion, exceeding the frozen **two-second completion bracket**.
Its request began 0.656231927 seconds after the case and took 1.606318998 seconds.
The five-second individual read deadline and request cadence both passed.

This demonstrates the distinction the user requested: the frozen observation
criterion was missed, but the evidence does not establish a firmware deadline
violation. All ten pressure cases pass a separately labeled DIAGNOSTIC_ONLY
evaluation with the proposed request-cadence/read-deadline rule. That evaluation
is not acceptance, does not replace the frozen failure, and does not close R3.

## Durable engineering changes

The retained lifecycle reuses the existing test configuration and AP input,
performs no CONFIG/flash, checks frozen identities and manifests, and reconciles
only known authoritative terminal state. It reserves a full observation window
before RF starts and marks the overall result FAILED if required cleanup fails.
A separately scoped Wi-Fi recovery permits at most one OFF/ON with write-ahead
accounting; uncertain ACKs are never retried. That scope was consumed by A1e.

The [read-only diagnostic tool](phase11-5-failure-triage.md) now reconstructs
A1, A1b, A1c, A1e and A1f before assigning cause. It separates execution,
acceptance, attribution, completed RF, final output authority, uncertainties and
next actions. An unknown packet or altered raw evidence cannot acquire firmware
or assistant blame from an exception string. The [diagnosis register](phase11-5-r3-diagnosis.json)
preserves these distinctions and never initiates a retry.

Offline audit can read a relocated baseline only after checking its frozen
content hash. Cleanup reconstruction now permits a partial asynchronous event
suffix after a complete response, matching the actual USB peer's framing behavior;
it still requires every frame, response and event to be fully consumed and valid.

## Adversarial iterations and validation

The first review fixed exact private/production helper sets, distinct principals,
terminal eligibility and bounded operation checks. The next review fixed fixture
lifetime admission and cleanup-failure disposition before A1e. Physical A1e then
exposed the missing in-flight admission argument, repaired before A1f. The A1f
raw integration review found and repaired the event-counter and R2 adapter
assumptions described above. Historical claims that an earlier local review had
found no more defects were insufficient; complete recorded integration is now
part of validation.

The final adversarial pass covered misleading failure text, raw CRC/schema and
summary disagreement, valid-CRC internal event gaps, unknown observation policy,
late request starts, expired/negative reads, stale boundary reads, partial
asynchronous cleanup framing, forbidden cleanup operations, changed RF output,
boot/epoch/peer identities, worker status, evidence truncation and false host
restoration. Intact evidence reconstructs again after each mutation. Older
packets retain strict completion brackets; the proposed policy cannot grant
A1f acceptance. That pass then found a remaining USB actor freshness consumer and a blocking
1.5-second completion-INFO wait. The R3 actor now uses bounded in-flight admission,
defers release until the current launch's completed INFO is available, and
publishes STATUS before subsequent mutation. Tests preserve the sampled status
when a later actor operation fails and prevent mutation after a read/log failure.
The unexecuted first A1g draft was retained and superseded with the final hashes.
A repeated assessment found no further actionable defect in these checked paths.

Validation: **198 Phase 11.5 tests, 196 passed, two unrelated private fixtures
skipped**. All five R3 raw attempt archives were supplied. This includes 22 new
A1e/A1f evidence mutations, the valid-CRC event-gap regression and prospective
policy boundary tests, in addition to the existing A1/A1b/A1c checks. Source
identity, frozen archive/hash completeness, JSON, relative links and whitespace
were checked. No C++ or Pi runtime implementation changed, so no firmware build,
CTest or Pi runtime suite was rerun. Passing tooling tests is not physical R3
acceptance; the new observation policy remains unexecuted.

## Evidence and last verified state

| Attempt | Packet SHA-256 | Collected archive SHA-256 | Files / bytes |
| --- | --- | --- | --- |
| A1c | `3167ff5d4c9e58b908ed0d5fcb64a278454a236857f5442ec0662e1e66fc5156` | `b5db3b325cc0b695eb99812241e7b6bddf6c38d9124b8356305c6be1f032a45f` | 143 / 2,058,240 |
| A1e | `27cd914815b8af8933fb134b44a923add1f09c8748afd0082115e4b1f202a518` | `ff602a675d1fc887cd8306025103b675238366f3608635ce2361352729bb073e` | 135 / 8,058,880 |
| A1f | `cc557f977c655ac974c60c8343f1e8ba52dbd40b7837fdac9eb8561a63910236` | `78c8005e7e2d94b2db9f222e46772e9801f6fd47da23ccb747f7f7fc5633b363` | 117 / 9,369,600 |

Private raw copies remain ignored under `build/phase11-5-r3-retained-a1{c,e,f}/evidence`.
Credentials and private configurations were excluded. A first sandboxed A1f
collection failed name resolution and left an empty archive; it was retained.
The successful read-only collection used `evidence-retry.tar`. This collection
failure caused no device action and is not a target-test failure.

At A1f cleanup, A was Empty/inactive/unowned on unchanged boot
`9c5aec394269e0b57ca16d73ad3d12b6`, physical source `2e43110f0530`,
138 MHz/divider 1/RAM/listener on. B retained inhibited boot
`feffcd075ab6cb0b74e7e0c2fde6c87f` and configuration. Host interfaces, routes,
installed PID 1957 and permanent time.local were restored. The test configuration
remains the user's baseline; actual cumulative CONFIG saves remain 37 and heap
probes six. A1e used one OFF/ON cycle; A1c/A1f used none. Fresh reads are still
required before future action because terminal retention expires normally.

Remaining R3 work includes the initial tranche's acceptance, distinct failed-TLS
and pending-expiry lifetimes, partial HTTP and stalled I/O, real job/frame/body/
browser boundaries, simultaneous overload, USB pressure, retained-state capacity
and expiry, and three equivalent repetitions of the measured highest-resource
path. R4–R6, Phase 11.6 and Phase 13 remain outside this work. The complete mandatory
register is preserved in the completion prompt; an A1g pass alone cannot close it.

Documentation Impact: updated Pico's prompt, ledger/index, execution history,
causal review/result and triage policy/register; updated only the Pi companion
report in `docs/development/phase11-5-review.md`. No firmware, protocol, UI,
installed application or excluded operator-manual repository changed.
