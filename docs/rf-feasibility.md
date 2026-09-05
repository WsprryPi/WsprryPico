# RF engine feasibility

Status: initial source-backed investigation. No measurements or supported-band claims.

The RP2350 PIO divider has 16 integer and 8 fractional bits. PIO determinism alone therefore does not establish useful WSPR tone resolution or spectral purity. See the [RP2350 datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf) and [Pico SDK hardware APIs](https://www.raspberrypi.com/documentation/pico-sdk/hardware.html).

For an illustrative two-instruction toggle loop at a fixed 150 MHz system clock:
f = 150,000,000 / (2 D), with adjacent divider settings separated by 1/256.

Near 14 MHz, D is approximately 5.36. The adjacent output-frequency step is roughly 10 kHz, far coarser than the approximately 1.465 Hz WSPR tone spacing. This rules out merely selecting four adjacent static PIO divider values for that example; it does not rule out direct RF using more sophisticated synthesis.

## Compare these candidates

| Candidate | What must be established |
|---|---|
| Static PIO divider | Exact representable frequencies and quantization per requested band |
| PIO/DMA edge or divider sequences | Mean frequency, repeat spurs, phase error, resource use and underrun behavior |
| PLL/peripheral clock output | Legal divider/PLL configurations, routable pins, retune transients and USB/Wi-Fi clock dependencies |
| Optional Si5351 | Variant/reference selection, tuning granularity, update latency, settling, spurs and output disable behavior |

Si5351 is an I2C-programmable clock generator; that capability does not prove suitability for a particular WSPR implementation. See the [manufacturer datasheet](https://www.skyworksinc.com/-/media/Skyworks/SL/documents/public/data-sheets/Si5351-B.pdf).

## Investigation deliverables

1. Select explicit candidate bands/frequencies and derive representable tone frequencies using documented clock limits.
2. Analyze exact symbol duration and cumulative rounding, separately from carrier-frequency accuracy.
3. Model phase-error sequences and spectra for each direct-RF candidate; size worst-case buffers and DMA bandwidth.
4. Identify clock-tree, pin and peripheral conflicts for the actual Pico 2 W board, including SDK wireless use.
5. Specify a comparison measurement plan covering carrier/tone error, start error, symbol timing, spurs, harmonics, drift and transitions.
6. Choose an engine only after comparing calculations and appropriately authorized hardware evidence.

Bench evidence must identify board revision, clock/reference, firmware, pin/engine, filtering and receiver setup. Simulated frequency accuracy does not qualify RF output. No hardware access or transmission is part of this baseline.
