# Portable experimental RF stream

Status: first Step 8 software slice implemented and host-tested. The library
also cross-compiles with the pinned Arm toolchain. **No physical sink, PIO
program, DMA driver or live firmware connection exists.** RP2350 throughput,
launch timing, electrical behavior and RF remain unqualified. The Pico firmware
still uses `InhibitedRfEngine` and its existing unsynchronized clock.

## Implemented scope

`src/rf/waveform.*` plans and generates the four initial 80 m study tones.
`src/rf/stream_engine.*` implements `RfEngine` using an abstract `BlockSink`;
`tests/rf_stream_tests.cpp` supplies the only sink implementation, a host fake.
The C++20 library is a separate CMake target, `wsprrypico_rf`. It is deliberately
not linked into `WsprryPico`, and it adds no WTP capabilities or protocol changes.

The planner accepts `tone` and `wspr` event jobs, at most 162 events and
110.592 seconds. It validates contiguous nonempty events, bounded arithmetic,
job identity, frequency presence/absence and the existing profile. It does not
encode or validate a WSPR message. Four nominal RF frequencies are
3,570,100 Hz plus t*375/256 Hz, t=0..3. These map to the exact 32-bit NCO
increments 102223085, 102223127, 102223169 and 102223211 at 150 MHz.

Nominal frequencies require `allow_frequency_adjustment=true`. Preparation
reports each realized frequency rounded to integer nHz; the underlying waveform
frequency remains the exact sample-rate/increment rational. Sub-nHz report
rounding is below 0.5 nHz. A job requesting one of those realized nHz values
already needs no further adjustment. All other frequencies are rejected.
Calibration and configurable sample clocks are outside this fixed-clock slice.

Event endpoints must encode an exact sample boundary rounded to the nearest
nanosecond: sample=round(ns*3/20), then ns must equal round(sample*20/3).
The planner rejects positive events that collapse to zero samples. Endpoint
error relative to the ideal sample boundary is at most 1/3 ns. This realizes
nearest-nanosecond WSPR cumulative boundaries without inventing a timing
adjustment response. Arbitrary nanosecond jobs may be rejected by this adapter;
its smaller limits would need truthful capability integration before live use.

## Generator and ownership

Output words are LSB-first samples; MSB(phase) is emitted before phase advances.
Phase continues through tone changes and render calls. RF-off samples are zero
and freeze the phase; resuming uses the retained phase. That off policy is an
explicit experimental choice, not qualification of keyed modes. The final word
is zero-padded and the return value states the exact valid sample count.

The generator advances equal-bit runs and segment boundaries. It computes the
next phase crossing with a precomputed reciprocal, a 64-bit multiplication and
one correction, rather than division per sample. The valid four increments
bound this arithmetic. `Waveform::reset` takes a planner-produced `Plan` that
must remain alive and immutable; arbitrary hand-built plans are not supported.
The generator itself allocates no memory.

Preparation validates before replacing accepted state, copies the immutable job,
then generates the first two blocks. Rejected preparation preserves the previous
plan and prefilled data. `begin` requires the identical job; it does not allocate
or regenerate the initial buffers. It stops/releases prior sink work, submits
prefilled blocks and arms with a new epoch and the fixed sample count.

Each 64 KiB block remains owned by the sink until ordered completion. Polling
refills only released slots. The adapter rejects stale epochs, regressing or
impossible counters, progress ahead of time, early completion, missed completion,
starvation, submission/arm failures and time reversal. A failure attempts stop
and latches `Failed`; a failed stop never makes buffers available for preparation
or reuse. Recovery requires successful `disable`, which also invalidates the
prepared job. Stop failure and observed output state propagate through the job
service as `OutputStateUnknown` when appropriate.

The sink is responsible for exact local consumption, finite stopping and an
atomic progress snapshot. `completed_blocks` counts fully consumed submissions;
`consumed_samples` includes the current partial block. Completion requires all
valid samples consumed and observed output inactive. `stop` success means all
spans released synchronously and no future access or output. A physical sink
must fail on an empty queue rather than repeat stale buffers. Epoch handling
must reject stale completions across stop/rearm at the sink boundary too.

Use one serialized owner for all engine calls. Both engine and sink must remain
alive until successful disable; destruction is not an output-stop mechanism.
The interface is not an ISR-safe concurrency implementation. Future interrupt
communication needs explicit atomic/ownership design. The current job service
calls `begin` at the start epoch; that polling path does not establish precise
hardware launch. A physical adapter will need reviewed prearming/local trigger
integration before any start-time claim.

## Memory and processing budget

For the pinned Arm GCC 15.3.1 ABI, the cross-build inspection gives:

| Item | Bytes / boundary |
|---|---:|
| Two waveform buffers, included in engine | 131072 |
| Complete `StreamEngine` object | 133896 |
| `Plan`, included in engine | 2608 |
| Copied event payload at 162 events, additional heap | 6480 |
| Generator's compiler-reported local stack frame | 80 |
| Planner / prepare local frames | 2688 / 2696 |

Stack values are per function, not a maximum call-chain bound. Planner and
prepare frames can coexist. Job strings, allocation overhead, frequency-adjustment
vectors, retained service/replay data, driver descriptors, endpoint queues,
other stacks and wireless memory are additional. Put a future engine in owned
long-lived storage, not a small interrupt stack. Static assertions cap the
engine object at 140 KiB and the plan at 4 KiB; these do not establish total
firmware fit. The physical integration needs a final map and heap/stack
high-water validation under the largest accepted job and replay load.

The stream needs 18.75 MB/s of packed data. Each half-buffer provides
3.495253 ms. The proposed target generation budget remains <=1.747626 ms per
half-buffer under the declared competing load. A host benchmark is only a
reproducible workload and regression aid. It renders a full 162-symbol,
four-tone synthetic job locally, consumes the output checksum, and reports
elapsed and maximum block-render time. Host wall-clock maxima include scheduling
and cannot establish RP2350 deadlines. Cross-compilation establishes neither
cycle counts nor hardware timing.

## Recorded host workload

On 2026-09-05, the macOS arm64 Release build with AppleClang 21.0.0 rendered
31,641 blocks for the full four-tone job in 7.90991 s including checksum work.
Maximum measured render-call time was 1800.67 us and the checksum was
9349730822126155465. This host maximum is above the study's proposed 1747.626 us
comparison target; it is neither a real-time guarantee nor a Pico result.
The actual RP2350 refill performance remains unknown. Benchmark output is
expected to vary with host load; use the command below to obtain a fresh result.

## Validation commands

Normal checks include the new stream tests:

```sh
cmake -S . -B build-host -DCMAKE_BUILD_TYPE=Debug -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build build-host --parallel
ctest --test-dir build-host --output-on-failure
```

For a host Release workload:

```sh
cmake -S . -B build/rf-release -G Ninja -DCMAKE_BUILD_TYPE=Release -DWSPRRY_PICO_BUILD_TESTS=ON
cmake --build build/rf-release --parallel
ctest --test-dir build/rf-release --output-on-failure
build/rf-release/rf_stream_tests --benchmark
```

For address/undefined-behavior checks:

```sh
cmake -S . -B build/rf-sanitize -G Ninja -DCMAKE_BUILD_TYPE=Debug \
  -DWSPRRY_PICO_BUILD_TESTS=ON \
  -DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -fno-omit-frame-pointer'
cmake --build build/rf-sanitize --parallel
ctest --test-dir build/rf-sanitize --output-on-failure
```

With the already configured pinned Pico build inputs:

```sh
cmake --build build/pico2-w --target wsprrypico_rf --parallel
```

A fresh checkout must first follow the [firmware foundation](firmware-foundation.md)
configuration instructions. The RF target builds a static library only. It does
not flash, access hardware or select this engine in firmware.

Tests compare output against a per-sample accumulator oracle with varied chunks,
events inside words, tone changes, off intervals and tails; check a full-frame
plan; test invalid inputs and atomic rejection; and cover sink lifecycle/faults
and real `JobService` integration. An allocation counter covers begin, refill,
completion and disable with the fake sink. A physical sink must independently
honor the allocation and timing constraints.

## Remaining Step 8 work

Review the [output/inhibit proposal](rf-output-design.md), implement the physical
sink and precise local launch path, prove generation/resource budgets on the
specified target. The operator decides when to transmit and which parts of the
[conducted measurement plan](rf-measurement-plan.md) to use. Output circuitry,
filtering and target timing remain engineering work; independent stop circuitry
is an optional design choice, not a transmission prerequisite. This software slice
does not complete Step 8 or qualify any engine/mode/band combination.
