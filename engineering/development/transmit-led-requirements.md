# Transmit indicators

Whenever the transmitter is hot (RF output active), the selected TX LED must
light solid for the entire active interval. This includes RF-producing warmup,
tones and all supported transmission modes, from output activation until output
is confirmed inactive after completion, stop, abort or failure. Queued, loaded
or armed work alone must not assert the TX indication. Follow actual local
RF-output activity, including any mode gaps that deactivate output, rather than
assuming that a running job is continuously hot.

When onboard TX is selected, solid TX takes priority over AP-ready and Identify
blink patterns; after confirmed inactivity the applicable cue may resume.
A selected external LED is **TX only**:
AP-ready and Identify continue on the onboard LED, never on the external pin.
Without an external selection, the current onboard LED supplies TX indication.
One controller owns both outputs so operational writes cannot blink or extinguish
external TX. The LED reports application/engine output state; it is not an
independent RF measurement. Do not show a simulated or RF-inhibited job as hot.

Preserve the [pin-assignment contract](../pin-assignment-contract.md): onboard
LED by default, configurable external GPIO/polarity, or explicitly disabled.
The solid indication requirement applies when the TX indicator is enabled.

## Local launch and physical inactivity

`WsprryPico-StandaloneRF` now requests a unique indicator acknowledgement only
at a valid local launch attempt. The selected TX output must have a checked
on state before PIO activation. Missing/failed writes keep RF inactive and
expire inside the existing start window. Disabled selection bypasses the gate.
The RF owner never writes CYW43 or waits on USB/network symbol delivery.

The request holds solid TX across the active engine interval and is released
only after checked physical inactivity, including delayed hardware completion
and failed shutdown. The normal onboard cue may resume at the next core-0
poll, so indication can briefly lead activation and lag confirmed inactivity.
Onboard and external checked state/faults are tracked separately; an onboard
AP flash cannot acknowledge external TX. Faults remain latched after retry
recovery. GPIO polarity and requested-level preload are host-tested through
the actual Pico indicator adapter. The standard simulator never requests TX.


The indicator reports application/engine output state, not independent RF
measurement. Functional observations establish no LED timing calibration,
electrical RF cutoff bound, other-band/clock qualification or antenna safety.
Legacy RFBench/RFWTP diagnostic entry points are outside this application
indicator graph. The deterministic field-access, pin and indicator tests cover
priority, disabled selection, separate checked outputs and fault retention.
