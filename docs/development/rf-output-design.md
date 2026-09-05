# Proposed output network and stop options

Status: engineering options for the initial 80 m candidate. The operator decides
when to transmit, which hardware to use and which measurements to run. This
proposal creates no transmission permission mechanism or mandatory interlock.
No circuit has been assembled or measured; the schematic/BOM and actual filter
response are unresolved engineering work.

## Signal path

```text
GP2 (proposed PIO data)
  -> suitable output buffer
  -> series DC isolation
  -> current-limiting resistive output network
  -> characterized 80 m band-pass filter
  -> attenuation / measurement point
  -> SDR input
```

The buffer, coupling and filtering choices affect GPIO loading, output level,
receiver input and unwanted emissions. Their actual ratings and behavior belong
in the setup record so the operator can assess them.

## Optional independent stop circuitry

A normally-disabled buffer controlled by an operator stop is one design option
for suppressing output if the CPU or DMA becomes stuck. A progress watchdog
could deassert that enable after missing new consumed-block heartbeats; 5 ms is
an initial timing proposal compared with the 3.495 ms half-buffer period.
A separate duration timer is another option. These are optional hardware design
choices for the operator, not prerequisites imposed by this project study.

If any option is selected, evaluate its default state, timing tolerances,
brownout/reset behavior, stuck-high inputs, gate leakage and startup impulses.
A cyclic DMA descriptor can repeat old RF data, so a watchdog fed by that same
cycle would not detect producer starvation. The software adapter's job-end,
cancellation and fault handling still stops consumption and releases buffers;
those ordinary lifecycle operations add no RF-authorization policy.

## Initial output-network calculation

A reviewable passive starting point after a suitably rated gate/buffer is a
1 kohm series resistor followed by a 51 ohm shunt resistor, then a nominal
50 ohm filter/input. With an ideal 3.3 V logic swing and that termination:

- Load at the divider is 51 || 50 = 25.248 ohm.
- Maximum high-state source current is about 3.219 mA.
- Delivered swing is about 81.27 mV peak-to-peak; source impedance looking back
  through the network is approximately 1000 || 51 = 48.525 ohm.
- The ideal AC square-wave power into 50 ohm is about -14.81 dBm; its fundamental
  is about -15.72 dBm before filtering. These are calculations, not measured
  source power or receiver protection limits.

This deliberately trades level for load control. Verify actual buffer current,
voltage, leakage, output resistance and resistor tolerances before retaining
these values. The series resistor dissipates about 10.36 mW in the ideal high
state; final ratings must include supply extremes and faults. DC isolation must
be selected for the actual impedance, frequency, voltage and self-resonance;
its startup transient must be included in the receiver-protection calculation.
Do not assume that this network alone makes a direct Pico/SDR connection safe.

The filter needs documented insertion loss at all four tones and enough
rejection of the modeled 3.5143 MHz image (about -32.67 dBc unfiltered) to meet
the provisional -40 dBc screen with uncertainty margin. Set an initial design
target of at least 15 dB *relative* rejection there and at least 40 dB relative
rejection at the approximately 10.7103 MHz third harmonic. Check both sides of
the passband, other modeled images, impedance variation and transition behavior.
A simple low-pass filter cannot meet the below-carrier requirement. Filter
order, resonators and actual component values remain open pending realizability
and loss analysis; no ideal filter simulation is presented as assembled evidence.

Use the measurement plan's independent maximum-power/attenuation calculation
with the identified SDR's documented limits. The illustrative output estimate
must not replace that bound, particularly for buffer faults and transients.

## Further design work

Resolve buffer ratings, coupling, filter realizability and the actual receiver
connection with the operator's chosen setup. Hardware measurements can establish
what the calculations cannot. The
[portable stream contract](rf-stream.md) defines buffer ownership and ordinary
job lifecycle behavior; the [measurement plan](rf-measurement-plan.md) provides
suggested measurements and comparison targets for operator use.
