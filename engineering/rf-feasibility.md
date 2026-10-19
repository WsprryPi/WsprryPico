# RF synthesis model and tradeoffs

This hardware-free comparison uses an ideal 150 MHz reference. The normal
application implements that engine at 138 MHz; `WsprryPico-Inhibited` explicitly
selects a simulator. The calculations below are analytical estimates, not
support for every band or a production RF qualification. Si5351 is the optional
external-engine design in the [consolidated backlog](development/consolidated-backlog.md).

## Scope and sources

The [reproducible calculations](rf-calculations.md) cover eight illustrative
lowest RF tones from 3.57 to 28.13 MHz (80, 40, 30, 20, 17, 15, 12 and 10 m).
They are neither dial settings nor operating permissions. They stress a range
of dividers; they do not establish continuous band coverage. No encoder was
extracted or upstream implementation copied.

Analytical inputs:

- [RP2350 datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf),
  build d126e9e, 2025-07-29: sections 8.1, 8.6 and 11, clock divider registers,
  PLL restrictions and PIO. PIO has a 16.8 divider; GPOUT has a 16.16 divider.
  The PLL search uses 12 MHz input, reference division 1 or 2, feedback 16..320,
  VCO 750..1600 MHz, post-dividers 1..7 and output no greater than 150 MHz.
- [Pico 2 W datasheet](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf),
  sections 2 and 3: board pins, 3.3 V GPIO and wireless connections.
- [Model SDK board definition](https://github.com/raspberrypi/pico-sdk/blob/98a542c1a62fb549ffb5d66a3e5892b06276b670/src/boards/include/boards/pico2_w.h),
  [clock routing definitions](https://github.com/raspberrypi/pico-sdk/blob/98a542c1a62fb549ffb5d66a3e5892b06276b670/src/rp2_common/hardware_clocks/include/hardware/clocks.h)
  and [CYW43 PIO driver](https://github.com/raspberrypi/pico-sdk/blob/98a542c1a62fb549ffb5d66a3e5892b06276b670/src/rp2_common/pico_cyw43_driver/cyw43_bus_pio_spi.c).
  These links identify the analytical input revision, not the current firmware
  dependency pin. Its wireless driver claims
  a PIO state machine/program and two DMA channels dynamically.
- [Skyworks Si5351 datasheet](https://www.skyworksinc.com/-/media/Skyworks/SL/documents/public/data-sheets/Si5351-B.pdf),
  Rev. 1.3, and [AN619](https://www.skyworksinc.com/-/media/Skyworks/SL/documents/public/application-notes/AN619.pdf),
  Rev. 0.8: synthesis ratios, register representation and I2C operation.
- [Joe Taylor's WSPR description](https://www.eme2008.org/papers/Digital%20modes/k1jt_EME2008.pdf),
  WSPR section: four tones, spacing 12000/8192 Hz, 162 symbols and
  8192/12000 seconds per symbol.

The calculations describe this model, not manufacturer guarantees, current
firmware resource allocations or protocol changes. Current implementation and
dependency pins are in the [PIO/DMA guide](development/pio-dma-driver.md) and
[firmware foundation](development/firmware-foundation.md).

## Frequency comparison

Let F=150,000,000 Hz, tone t=0..3 and requested frequency
f(t)=base+t*(375/256) Hz. All calculations initially assume ideal references.

| Model | Calculation | Consequence |
|---|---|---|
| Static PIO toggle loop | f=F*256/(2*q), integer q encodes D=q/256 | Reject this simple WSPR implementation: all four tones map to one divider at every study base. This does not reject GPIO synthesis. |
| Static clock output | f=F*65536/q | Reject as a general four-tone solution across this matrix; several tones collapse and maximum errors reach tens of Hz. |
| Retuned PLL plus GPOUT | Enumerate legal parents and nearest 16.16 divider independently per tone | Some combinations give small mean errors, but they do not prove phase continuity, lock time or a usable shared clock tree. Defer. |
| PIO/DMA packed NCO bits | k=round(f*2^32/F); output MSB of an accumulating 32-bit phase at F | Fine mean resolution and continuous phase state. Numerical resolution does not establish generation throughput or unwanted emissions. |
| Si5351A alternative | Fixed 900 MHz PLL; fractional MultiSynth divisor approximates 900 MHz/f | Numerically strong, but needs additional hardware and measured update behavior. No Si5351 engine is implemented. |

The script chooses the closer output frequency of the two neighboring static
dividers, rather than rounding a divisor blindly. NCO error is at most
F/2^33 = 0.017462299 Hz; adjacent-tone error is at most F/2^32. The generated
report includes all 32 tone plans, so representability can be checked directly.
A fine mean frequency does not imply low jitter or low spurs.

For Si5351, the comparison assumes an Si5351A with a 25 MHz crystal, PLL ratio
36, CLK0, R=1, spread spectrum disabled, and a changing fractional output
MultiSynth. The full ratio is reduced to denominator <=1,048,575 using rational
approximation, with all study divisors conservatively between 8 and 900. The
error is below 0.000002 Hz for these points. This is a varying-denominator plan;
fixing the denominator at its maximum does not give the same results. AN619
register arithmetic is checked, but no register writer is implemented. An
eight-register I2C burst needs at least 90 SCL clocks: 225 us at 400 kbit/s or
900 us at 100 kbit/s, excluding overhead and settling. This estimate establishes
neither atomic nor phase-continuous tone changes.

## GPIO phase, spectrum and resource model

In the packed-bit model, phase advances by k modulo 2^32 at every 150 MHz
sample. Preserve the accumulator across tone changes and buffer boundaries.
The mean frequency is exact relative to this model. Ideal half-cycle edge
positions rounded to the next sample have error in [0, 1/F), below 6.667 ns.
The report evaluates 4096 such edges per base, relative to the represented
frequency. Add mean tuning error and reference error separately. At 28.1261 MHz,
one sample is nearly 68 degrees of carrier phase: small time error can still
produce substantial spectral energy.

The NCO sample sequence repeats after N=2^32/gcd(k,2^32) samples. Its spectral
line grid is F/N, not the tone resolution alone. In phase order, the relative
magnitude of odd harmonic m is |sin(pi/N)/sin(pi*m/N)|. Map it to sample bin
(m*k/gcd(k,2^32)) modulo N, fold about Nyquist, and include the zero-order-hold
sinc response. The script evaluates odd orders 3..255 analytically over the
full period, avoiding a short FFT that cannot resolve WSPR tones. A direct DFT
of a small exact-period case independently checks these coefficients.

This is an ideal digital waveform model. It excludes pads, PLL jitter, reference
noise, loading, analog filtering, power supply coupling, transition leakage and
buffer faults. The finite harmonic list is not a bound on every spur. Inspect
both stronger high-frequency harmonics and folded components below the carrier;
a low-pass filter alone cannot suppress the latter. No SDR capture is simulated
or implied.

For static PIO and GPOUT, the same sample-grid edge proxy illustrates timing
quantization, but is not a register-accurate divider jitter model. An ideal
50% square wave already has odd harmonics with amplitudes 1/m (third harmonic
-9.54 dBc before filtering). Actual fractional-divider ordering and duty cycle
can add sidebands. Static tone collapse is sufficient for rejection here, so
there is no claimed exact hardware spectrum for either rejected implementation.
PLL retuning adds unknown lock/phase transients which arithmetic cannot predict.

A model PIO program emits one packed bit per system clock from a FIFO fed
by DMA, at divider 1. The output need not be computed by PIO itself. Bandwidth
is 18.75 MB/s, or 4,687,500 32-bit FIFO writes/s; SRAM read plus peripheral write
traffic is at least 37.5 MB/s before arbitration and generation traffic.
The model's two 64 KiB buffers use 128 KiB and give 3.495253 ms to refill each half. A full
110.592 s WSPR waveform is 2,073,600,000 bytes, so preloading a frame is not a
plausible SRAM strategy. The complete *event job* stays local; waveform blocks
must be generated locally without per-symbol host data.

One word per half-cycle instead requires about 28.56..225.01 MB/s across
the study range, before instruction overhead. These are bandwidth estimates,
not CPU throughput measurements. At 150 MHz the modeled half-buffer refill
period is 3.495253 ms. The implementation's actual buffers, resource claims,
stop handling and measured limits are defined in the
[stream contract](development/rf-stream.md) and
[PIO/DMA driver guide](development/pio-dma-driver.md).

## Timing and clock separation

A symbol lasts 256/375 s and the frame lasts exactly 110.592 s. At the assumed
sample clock a symbol contains exactly 102,400,000 samples, divisible by 32.
Thus this WSPR model can place tone boundaries on packed-word boundaries.
General WTP event times are not guaranteed to align this way; the current
adapter applies its documented sample-grid admission rules.

Schedule absolute deadlines from the job epoch, never by repeatedly sleeping a
rounded symbol interval. Nearest-microsecond boundaries alternate 682666 and
682667 us with error <=0.5 us and exact frame end. Repeating 682667 us creates
54 us of frame error. Nanosecond WTP offsets should likewise be formed from
rounded cumulative rational boundaries, preserving contiguous events. Exact
arithmetic is separate from actual interrupt latency, launch phase and UTC.
Current job launch separately enforces UTC quality, source age and ownership.

A reference error of e ppm causes approximately f*e/1e6 Hz carrier error and
-e*110.592 us frame-duration error. One ppm therefore means 14.0971 Hz at the
20 m study point and about 110.592 us of frame error. RF calibration and UTC
synchronization are separate estimates; an SDR's frequency and sample-rate
errors are separate again. Fine NCO/Si5351 arithmetic cannot calibrate a crystal.
Freeze any accepted correction at LOAD/prepare. WTP/1 already requires explicit
`allow_frequency_adjustment` for unrealizable requested frequencies and reports
the accepted adjustment; preserve that contract rather than silently rounding.
