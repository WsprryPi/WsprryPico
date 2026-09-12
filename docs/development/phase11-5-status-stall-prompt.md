# Execute: diagnose and repair the N1u STATUS stall

Own the unresolved production STATUS stall recorded in
[N1u's result](phase11-5-n1u-result.json). Work in WsprryPico and, where the
evidence requires it, WsprryPi. Inspect their current state and project
instructions, preserve existing work and historical evidence, then implement,
validate, adversarially review, commit and push scoped changes to `devel`.

## Concrete failure and evidence

N1u tested inhibited firmware source
`4058d3a4a95110326006a7db6e37eb4b562a500c`, 150 MHz, UF2 SHA-256
`0a7d54673e7171ee10275272701de5fbb3cecdc91c097a18eeae496c0922c7b9`.
One N180 conditioning interval captured 179 production STATUS requests, with a
maximum gap of 2,696,718,780 ns against the unchanged 2 s limit. Maximum native
TLS write-entry-to-response delay was 2,592,628,676 ns. USB observation passed;
browser requests completed, but neither fact waives production cadence.

Use the preserved local evidence under
`build/phase11-5-closure/n1u-preserved-final/phase11-5-n1u-4058d3a` and its
hash-bound public result. The archive SHA-256 is
`636cf62e56264d3856bfe0202772b907e793ba5c28453c7f1800b4e409624d69`.
No packet capture was collected. Therefore aggregate TCP drop counters cannot
establish retransmission, application delay, or a particular connection's loss.
The source change that removed internal status-copy allocations did not establish
a target pass. Retain N1u as FAIL and its dependent full A2/A3 as NOT_RUN.

## Execution

1. Correlate native TLS write-entry/return and response times, browser activity,
   USB health and server transport metrics around the slow request. Compare
   relevant source paths and historical passing evidence without transferring
   acceptance between images. State what the existing evidence cannot resolve.
2. Trace application polling, TLS steps, TCP send/receive buffering and delivery
   of pending input in the pinned SDK. Form explicit hypotheses; implement a
   fix only when a source defect or reproducible behavior supports it. Do not
   guess another allocator or scheduling optimization from timing correlation.
3. Add deterministic regression coverage for supported defects. Instrumentation
   must distinguish waiting for network delivery from delayed firmware service.
   Any new target run must freeze its exact image, helpers, clocks, finite load,
   evidence collection and independent restoration deadline before execution.
   Collect packet evidence on both AP and independent client if the distinction
   requires it, recording capture loss and clock correlation.
4. Use the user's recorded USB/flashing/RF authority and SSH outside the sandbox.
   Keep network/service actions within explicitly authorized scope and lifetime;
   the earlier six-hour N0 deadline is not authority to extend a new fixture.
   Do not silently repeat a frozen failed packet. Prefer inhibited diagnostics
   until the production stall is understood. Preserve both boards' identity,
   original firmware/configuration, installed service, wlan1 and GPSDO settings.
5. Re-run affected host/native TLS checks and contract validation. Review the
   final diff adversarially for causal support, incorrect PASS claims, reduced
   workload, relaxed thresholds, observer distortion, stale image/boot binding,
   incomplete cleanup and regressions. Fix actionable findings and repeat the
   affected checks and adversarial assessment until no actionable finding
   remains. Record unresolved target gates explicitly.
6. Commit and push the scoped implementation, regression tests, prompt and
   findings. Verify remote `devel` parity and report changed behavior, checks,
   actual case counts, restored hardware state or verification limitations, and
   Documentation Impact. Do not count investigation or compile checks as new
   physical acceptance cases.

## Acceptance boundaries

The production STATUS maximum gap remains 2 s, the count at least seconds minus
two, and each observed request at most 5 s. USB INFO starts remain at most 2 s
apart, STATUS/health at most 6 s, browser status at 0.2 Hz with at most 1 s
lateness and all three page/assets per 30 s. Preserve heap/stack, ownership,
fault, finite-job, security and restoration requirements.

Phase 11.5 accepts resource/contention behavior for each selected clock. The
physical candidate remains 138 MHz, PIO divider 1, SRAM renderer; its full-buffer
period is 262144000/69 ns and the 75-percent limit is 2,849,391 ns. Physical
132/150 MHz are untested. Phase 11.6 owns per-band/per-mode conducted RF with
accepted clocks; changing clocks repeats affected 11.5 checks. Phase 13 owns
systematic band × mode × clock comparison, filters and release qualification.
Do not expand this repair into a band/clock sweep.

Starting status: Phase 11.5 is OPEN, with historical A1/A2 closed only for
`8fb3894` (2/20 cases), A3 failed and seventeen cases NOT_RUN. No configuration
is accepted. Closing a source defect requires regression evidence; closing the
target stall additionally requires exact-image target evidence under unchanged
load and thresholds. A clean host test suite alone cannot close that gate.
