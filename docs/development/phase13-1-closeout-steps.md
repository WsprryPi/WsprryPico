# LED closeout: fixed steps 1–6

Selected by the operator on 2026-10-07. Preserve these step numbers in all
continuations. **Only step 2 requires an operator under normal conditions.**
Both Pico A and Pico B are connected to the SDR and the operator authorized
either or both for testing all six steps. That authorization persists; do not
ask for separate RF or per-job approval. Current identity/setup checks and
finite execution/restoration still apply. Physical recovery assistance is an
exception if automated device control fails, not a scheduled operator step.

| Step | Work | Operator | Status |
| --- | --- | --- | --- |
| 1 | Finish the runner, finite test cases, candidate checks and automated evidence collection. | No | Complete: engineering preparation |
| 2 | Identify the connected Pico/SDR setup; connect external LED fixtures for both polarities; prepare LED recording and the physical-stop fixture. | Yes, one untimed setup session | Pending |
| 3 | Run onboard tests: warmup, all five modes, completion, active abort, armed cancellation and inhibited behavior. | No, after setup | Pending |
| 4 | Verify onboard TX priority over AP/Identify; external TX-only behavior, both polarities and disabled indication. | No, with fixtures prepared in step 2 | Pending |
| 5 | Exercise standalone STOP, GP14 cutoff and controlled failure cases. | No, with an automated stop stimulus | Pending |
| 6 | Restore firmware/settings, assess evidence, repair findings, rerun affected checks and publish closeout. | No under normal conditions | Pending |

Finish engineering preparation before the step-2 session. Prepare both external
polarity fixtures and the automatic GP14 stimulus up front, so later steps need
no rewiring or timed button press. Capture automatically and retain recordings
for later review. Never require a response within a countdown or leave RF on
while awaiting the operator.

The original seven onboard jobs are only part of the complete closeout matrix.
The [step-1 prompt](phase13-1-step1-prompt.md) prepares the subsequent cases and
their actual adapters. Source, simulated evidence and physical acceptance
remain separate; neither step-1 completion nor connected hardware closes
steps 3–6.
