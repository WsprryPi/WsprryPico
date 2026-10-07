# P13.1: command, GPIO and RF validation without a camera

Work on `devel` and honor the fixed steps 1–6. The operator declines recording
setup and accepts the already confirmed onboard OFF/ON/OFF observations plus
command results and hardware GPIO readback as the LED functional evidence.
Do not request camera setup or repeat visual checks. Do not take new backups.
Both named Picos are authorized for this work; use B as DUT and leave A unchanged
unless a prepared physical-stop fixture actually requires it. External LEDs
have not arrived and stop wiring has not been confirmed.

Inspect the pinned SDK's actual read API, distinguish electrical GPIO reads
from the indicator controller's cached last-write state, and expose checked
readback with explicit failure/unknown reporting. Read the onboard CYW43 GPIO;
do not substitute an RP2350 GPIO or mistake an API error for OFF. Validate both
ON and OFF writes against hardware readback before acknowledging launch. Keep
SDK calls on the foreground core, outside the RF core and launch interrupt.
Preserve TX-only external routing, onboard AP/Identify priority, disabled
selection and fail-closed launch/stop behavior. Test read failures, mismatches,
both logical polarities, unknown/uninitialized outputs and gate behavior.

Adapt the runner to select canonical cases independently of whole steps,
require only their applicable fixtures, omit optical capture entirely for the
selected GPIO evidence mode, and reuse verified retained recovery data. Check
current identity, ownership, inactive output, disabled schedules and retained
settings against that data before mutation. Use verified application loads and
bounded verification instead of saving repeated 4 MiB images. Preserve settings
and restore ordinary inhibited firmware after every actual run, including STOP.
Keep serial-selected tooling, source/image binding, managed SDR checks, finite
18-admission/600-second ceilings and durable charge-before-admission accounting.
Never replay an ambiguous ARM or schedule admission.

Run step 3 and the onboard/disabled cases of step 4, plus standalone STOP and
controlled write failure in step 5. Skip both external LED cases and physical
GP14 cutoff until their setup exists. Verify real pin state during Running,
keyed gaps, AP/Identify overlap and terminal cleanup. Use autonomous SDR capture
on the existing receiver for RF evidence; this needs no operator recording
setup. Validate functional ordering through the checked launch handshake and
local engine stop; do not claim optical or calibrated sub-poll edge measurements.

Perform adversarial review, repair actionable findings, rerun affected checks
and assess again. Commit and publish reviewed source, bind clean candidates,
execute available cases and record exact devices, firmware, clocks, outcomes,
scope and restoration. Publish the resulting record. Keep external/physical-stop
rows explicit; recording setup is no longer an operator prerequisite for the
selected functional LED scope. Only an actual physical recovery failure may
require further untimed operator intervention.
