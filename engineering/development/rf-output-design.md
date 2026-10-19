# Output loading calculation

The GPIO output is unfiltered. This analytical example describes a resistive
network after a suitably rated external buffer; it is not an assembled circuit,
recommended BOM, receiver protection bound or antenna-ready output design.
Actual voltage, load, attenuation and filter response belong to the identified
RF setup. The [pin contract](../pin-assignment-contract.md) and
[PIO/DMA guide](pio-dma-driver.md) define the firmware output boundary.

## Resistive network example

The example uses a
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

The ideal square wave also contains odd harmonics. Folded digital images can
fall below the carrier, where a low-pass filter cannot remove them. These
calculations supply neither filter component values nor an independent maximum
receiver-input bound. Conducted [band support](band-support.md) establishes no
antenna-ready emissions or calibrated transmitter power.
