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
| 1 | Finish the runner, finite test cases, candidate checks and automated evidence collection. | No | Preparation delivered; standalone STOP terminal/job-ID checker findings remain open after live testing |
| 2 | Identify the connected Pico/SDR setup; connect external LED fixtures for both polarities; prepare the physical-stop fixture. | Yes, untimed setup | Onboard visual subset passed: B OFF/ON/OFF, A stayed OFF; ordinary inhibited restoration verified. External LEDs and stop wiring remain pending; operator chose hardware GPIO readback with no camera |
| 3 | Run onboard tests: warmup, all five modes, completion, active abort, armed cancellation and inhibited behavior. | No, after setup | Complete: actual GPIO and independent RF checks passed |
| 4 | Verify onboard TX priority over AP/Identify; external TX-only behavior, both polarities and disabled indication. | No, with fixtures prepared in step 2 | Onboard AP/Identify and disabled passed; both external cases await step-2 fixtures |
| 5 | Exercise standalone STOP, GP14 cutoff and controlled failure cases. | No, with an automated stop stimulus | Controlled write failure passed. Standalone STOP demonstrated ON/abort/OFF with partial RF evidence; full checker acceptance open. GP14 awaits fixture |
| 6 | Restore firmware/settings, assess evidence, repair findings, rerun affected checks and publish closeout. | No under normal conditions | Restoration and available results published; full matrix and standalone checker findings remain open |

Finish engineering preparation before the step-2 session. Prepare both external
polarity fixtures and the automatic GP14 stimulus up front, so later steps need
no rewiring or timed button press. Collect GPIO readback and autonomous SDR evidence for later review. Never require a response within a countdown or leave RF on
while awaiting the operator.

The original seven onboard jobs are only part of the complete closeout matrix.
The [step-1 prompt](phase13-1-step1-prompt.md) prepares the subsequent cases and
their actual adapters. Source, simulated evidence and physical acceptance
remain separate; neither step-1 completion nor connected hardware closes
steps 3–6.

Step 2 has its own [execution prompt](phase13-1-step2-prompt.md),
[untimed operator wiring sheet](phase13-1-step2-operator-setup.md) and
[execution/review record](phase13-1-step2-review.md). Operator confirmations
and external/stop wiring remain pending until actually supplied and checked.
The operator subsequently declined camera setup and selected command results,
actual hardware GPIO reads and autonomous SDR evidence. The [GPIO prompt](phase13-1-gpio-validation-prompt.md)
executes 13 available cases without external fixtures. No camera or further
onboard visual confirmation is required for that functional scope. Optical
edge measurements are outside this selected scope.

The [execution record](phase13-1-gpio-validation-review.md) records twelve full
passes and partial standalone STOP evidence. After the operator raised cost/time
concerns, additional runner development and RF repetition stopped. The remaining
automated findings do not require an operator; external LED and stop-fixture
setup remains the sole normal operator work.
