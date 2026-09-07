# Portable experimental RF stream

Status: portable Step 8 stream and [PIO/DMA sink](pio-dma-driver.md) implemented
and host-tested; the SDK driver also cross-links with the pinned Arm toolchain.
Bounded RP2350 refill and conducted tone measurements are recorded in the
[bench guide](rf-bench.md); general timing and RF qualification remain open.
The standard Pico firmware still uses `InhibitedRfEngine` and its existing
unsynchronized clock.

## Implemented scope

`src/rf/waveform.*` plans and generates direct-baseband tone/event jobs.
The bench retains its original four-tone 80 m workload.
`src/rf/stream_engine.*` implements `RfEngine` using an abstract `BlockSink`;
`src/rf/pio_dma_sink.*` supplies its peripheral controller, with the Pico SDK
port under `src/rf/pico/`. Tests also use deterministic fake hardware.
The C++20 library is a separate CMake target, `wsprrypico_rf`. It is deliberately
not linked into the inhibited `WsprryPico` image. The explicit `WsprryPico-RFWTP`
image advertises the experimental frequency range and all five campaign modes;
WTP/1 itself is unchanged.

The planner accepts `tone`, `wspr`, `qrss`, `fskcw` and `dfcw` event jobs,
with at most four distinct NCO increments, 162 events and
110.592 seconds. It validates contiguous nonempty events, bounded arithmetic,
job identity, frequency presence/absence and the existing profile. It does not
encode or validate a WSPR message. Four nominal RF frequencies are
3,570,100 Hz plus t*375/256 Hz, t=0..3. These map to the exact 32-bit NCO
increments 111112049, 111112094, 111112140 and 111112186 at the default
138 MHz. The 150 MHz baseline uses 102223085, 102223127, 102223169 and 102223211.

Nominal frequencies require `allow_frequency_adjustment=true`. Preparation
reports each realized frequency rounded to integer nHz; the underlying waveform
frequency remains the exact sample-rate/increment rational. Sub-nHz report
rounding is below 0.5 nHz. A job requesting one of those realized nHz values
already needs no further adjustment. The generalized planner accepts requests
from 100 kHz through one Hz below half the selected sample rate, rejecting any
corrected increment at or above Nyquist. Binary long division calculates the
rounded increment from requested nHz and corrected sample rate without 128-bit
arithmetic. An adjustment-free job must match the reported realized frequency.
The [band campaign](band-campaign.md) covers the new experimental range.
The bench supports volatile frequency correction and three explicit build-time
clock profiles; production calibration and capability integration remain open.

Event endpoints must encode an exact sample boundary rounded to the nearest
nanosecond: sample=round(ns*sample_rate/1e9), then ns must equal
round(sample*1e9/sample_rate). Reduced integer ratios avoid overflow.
The planner rejects positive events that collapse to zero samples. Endpoint
error relative to the ideal sample boundary is at most 0.5 ns. This realizes
nearest-nanosecond WSPR cumulative boundaries without inventing a timing
adjustment response. Arbitrary nanosecond jobs may be rejected by this adapter;
its smaller limits would need truthful capability integration before live use.

## Generator and ownership

Output words are LSB-first samples; MSB(phase) is emitted before phase advances.
Phase continues through tone changes and render calls. RF-off samples are zero
and freeze the phase; resuming uses the retained phase. That off policy is an
explicit experimental choice, not qualification of keyed modes. The final word
is zero-padded and the return value states the exact valid sample count.

The generator uses exact phase-indexed word tables. Each tone has 64 sorted
phase boundaries and 1024 buckets containing a base word and its boundary range.
Lookup applies XOR toggles for crossings inside the bucket. Full words advance
phase in batches; partial words and event edges retain per-sample handling.
Each waveform owns 34,816 bytes of tables, rebuilt during reset when its
planned increments change; rendering never rebuilds them. There is no approximation of output bits.
`Waveform::reset` takes a planner-produced `Plan` that must remain alive and
immutable; arbitrary hand-built plans are unsupported. The generator allocates
no heap memory. Tests compare all table/bucket edges against a per-sample oracle.

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
The concrete PIO/DMA controller serializes same-core IRQ and foreground access.
The job service prearms engines advertising local scheduling during ARM; the
local alarm rechecks the immutable clock conditions before launch. Legacy and
inhibited engines retain their foreground `begin` path. The clock snapshot must
be IRQ-safe and outlive the active engine. The bench timer observations do not establish physical pin-edge accuracy.

## Memory and processing budget

The engine has two 64 KiB waveform buffers. Static assertions cap the complete
engine object at 180 KiB (including its tables) and its plan at 4 KiB. The bench
has another 64 KiB CPU-test buffer and a separate 34,816-byte table set. Job copies, strings,
USB queues, allocator overhead and stack are additional. The bench reserves a
16 KiB primary stack and reports a canary estimate; its observed maximum was
9,848 bytes in the latest recorded workload. This is not a maximum-job call-chain proof.
`heap_free_bytes` is free space in the allocator arena, not all unallocated SRAM.
The standard firmware's memory-layout checks remain separate.

The stream needs 18.75 MB/s of packed data. Each half-buffer provides
3.495253 ms. The proposed target generation budget remains <=1.747626 ms per
half-buffer under the declared competing load. A host benchmark is only a
reproducible workload and regression aid. It renders a full 162-symbol,
four-tone synthetic job locally, consumes the output checksum, and reports
elapsed and maximum block-render time. Host wall-clock maxima include scheduling
and cannot establish RP2350 deadlines. Cross-compilation establishes neither
cycle counts nor hardware timing.

## Recorded target workload

On the recorded Pico 2 W at 150 MHz, `BENCH 128` changed from a worst render call
of 22.092 ms with the original generator to 1.507 ms with exact word lookup and
removal of redundant buffer clearing. Both produced checksum 4503602371141397.
The latter is below the proposed 1.747626 ms half-buffer budget for this measured
workload. It is not a maximum-load or full-frame guarantee. See the
[image hashes, setup and limitations](rf-bench.md).

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

The experimental target runner and initial measurements now exist. Remaining
work includes calibrated frequency and spectra, full-frame/mode workloads,
output circuit/filter characterization and UTC/WTP integration. The operator
decides when to transmit and which measurements to perform. Independent stop
circuitry remains an optional design choice. These bounded results do not
complete Step 8 or qualify an engine/mode/band combination.

See the [correction and alias record](rf-correction-validation.md) for the
volatile correction interface, measured effect and remaining settling/alias work.

The [clock comparison](rf-clock-validation.md) adds build-selected 132/138 MHz
experiments alongside the default 138 MHz profile. NCO increments, timestamp
conversion, progress checks and sample bounds all use the selected rate. The
150 MHz figures above remain tied to that profile. The engine permits at most
100 microseconds for asynchronous final-data/zero-tail acknowledgement after
the nominal end, only when all samples are generated/submitted and no more than
the final block remains unacknowledged. IRQ-driven sink reports snapshot time,
state and output activity together, avoiding a stale pre-launch report being
compared with post-launch GPIO activity. Missing acknowledgement still fails and stops
the sink; it does not extend the planned waveform or change SDR diagnostic
thresholds.
