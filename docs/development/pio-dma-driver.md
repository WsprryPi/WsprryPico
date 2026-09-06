# Experimental Pico PIO/DMA driver

Status: implemented, host-tested and linked against the pinned Pico SDK for
Pico 2 W. No flashing, GPIO operation or SDR capture was performed for this
slice. The standard `WsprryPico` firmware still selects `InhibitedRfEngine`.
This is the second Step 8 software slice, not completed target qualification.

## Wiring and scope

| Connection | Pico signal | Physical header pin |
|---|---|---:|
| RF data | GP2 | 4 |
| Return | GND | 3 |

With USB at the top, these are the fourth and third pins down the left side.
The RF data goes through the chosen output network and attenuation to the SDR
on `wspr5`; return connects to the cable shield. The
[output circuit proposal](rf-output-design.md) and
[measurement plan](rf-measurement-plan.md) describe the pending electrical work.
The operator decides when to transmit and which measurements to perform.

The driver requires a fixed 150 MHz system/sample clock and implements the
[portable stream's](rf-stream.md) four initial 80 m tones, size limits and
zero-padded final word. It does not configure UTC, encode WSPR, change the system
clock, expose new WTP capabilities, or select itself in firmware.

## Peripheral ownership and finite output

`PioDmaSink` is a portable two-slot controller; `PicoPioDma` implements its
peripheral boundary. Construction does not touch hardware. First submission
claims one PIO state machine/program, one DMA channel, one hardware alarm and
exclusive DMA IRQ 3 on the owning core. Open rejects an occupied IRQ, wrong clock
or unavailable resource and unwinds partial claims. Keep these objects on one
core, reserve GP2 and IRQ 3 for their lifetime, and keep the clock fixed while
armed or running. The same-core IRQ mask is not multicore synchronization.

The PIO program executes one `out pins, 1` per cycle, shifts LSB-first and uses
autopull at 32 bits with an eight-word joined TX FIFO. One non-chained DMA
transfer feeds each block. Its completion IRQ starts the next queued block.
There is no circular descriptor or automatic replay. Missing data, DMA errors
and observed TX starvation produce failure and stop output.

The FIFO plus output shift register gives at most 288 sample cycles (1.92 us)
of slack at a block handoff; the actual minimum is smaller and depends on DMA
and interrupt latency. Cross-linking does not establish that the handler meets
this deadline. Target interrupt/refill benchmarks are needed before claiming
continuous output. A detected stall invalidates the run; it cannot undo samples
already emitted. CPU hangs and missed interrupts have no independent watchdog
in this implementation.

After final data DMA, nine repeated zero words are pushed through the same FIFO.
When that DMA completes, all preceding data has left both FIFO and shift
register. The handler forces GP2 low, disables PIO and clears pending work.
Padding/tail zeros carry no RF frequency. Output-active is the commanded PIO
state, not an independent electrical measurement. Final IRQ latency and an
end-boundary foreground poll can still fail the existing strict completion
check; target testing must establish completion behavior as well as steady
streaming. No timing tolerance was added to WTP.

Stop cancels the alarm, forces GP2 low, disables PIO and DMA interrupts, clears
DMA EN before abort (RP2350-E5), waits within the caller's deadline for DMA to
retire, then clears FIFO/shift state and pending DMA status. Failed stop retains
buffer ownership and prevents reuse. Epoch/sequence checks discard stale events. Progress includes a time snapshot
taken under the same IRQ mask, so an alarm between a foreground clock read
and the sink poll does not appear to be an early launch.
`disable` must succeed before destroying engine/sink/clock storage. The hardware
`release` method is for final teardown after successful sink stop; destroy the
sink after release rather than reusing its opened state. Explicit release
unclaims the peripherals. Destruction alone is not an output stop.

## Local launch and clock contract

`JobService` calls `schedule` during ARM for a local engine. The engine submits
its prefilled buffers, loads the stopped FIFO and arms the hardware timer.
Foreground USB polling does not trigger output. The alarm runs up to 50 us early,
rechecks synchronized/holdover state, uncertainty, UTC mapping and leap exclusion,
then waits briefly for the aligned microsecond before enabling PIO. An already
late callback or failed clock check becomes `Missed`; it does not catch up.
Abort/reset cancels local execution before clearing service state.

The supplied clock must have an allocation-free, bounded, IRQ-safe snapshot on
the owning core. The prelaunch guard cannot use a blocking transport or update
its data from another core without its own synchronization. Once running, UTC
updates do not retime the waveform. These are the existing WTP timing semantics,
not a transmission-approval mechanism.

The SDK timer resolves microseconds. This driver rejects non-microsecond-aligned
start epochs. The final software check observes that timer; instruction latency
between the check and the actual pin transition is unmeasured. It does not
establish nanosecond-exact launch or general WTP timing conformance. The guard
can run up to 50 us before output; that interval also needs inclusion in a
future clock uncertainty budget.

## Validation and next work

Run the normal host suite as documented in [development](README.md), including
`pio_dma_tests`. It covers bounded queues, repeated buffer recycling against the
waveform generator, padding, zero tail, stale events, allocation/submission/alarm
failures, missed starts, clock changes, starvation, abort and reset. Peripheral
fakes establish control sequencing, not actual IRQ timing or electrical output.

With the [pinned firmware build](firmware-foundation.md) already configured:

```sh
cmake --build build/pico2-w --target rf_driver_linkcheck --parallel
```

This assembles the PIO program and links the actual driver/peripheral code into
a link-only ELF. It does not generate a test UF2 or run the image. Standard
firmware construction remains separate. Original driver and PIO code are MIT;
the SDK keeps its own licensing and attribution.

Next work is an experimental target runner with honest capabilities and clock
handling, measured generation/IRQ/stack/heap budgets, and operator-directed
transmissions received on `wspr5`. Harness capture and offline analysis can help;
its existing WsprryPi transmitter campaign is not a Pico adapter. Record the
exact firmware, board, output path, receiver and job with those measurements.
