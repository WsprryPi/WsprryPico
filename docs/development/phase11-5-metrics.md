# Phase 11.5 measurement definitions

These are diagnostic observations, not accepted limits. The
[register](phase11-5-register.json) currently accepts no physical configuration.
The [plan](phase11-5-plan.md) defines selected clocks and remaining gates.

## RF owner and timer

The [SRAM remediation candidate](phase11-5-remediation-review.md) reports
`rf_render_in_ram` in Console INFO. Bind that setting with the exact image and
clock; RAM/flash variants are different unaccepted configurations. The linked
renderer check establishes placement, not timing. Other RF/IRQ code can remain
in XIP, and the configured clock is not a measured oscillator calibration.

The physical core owns the driver and its fixed two-entry completion tracker.
Descriptor submission and driver snapshots run under its IRQ mask. An explicit
worker metrics RPC copies a coherent snapshot to core 0. Ordinary poll, output,
prepare, schedule, correction and disable RPCs do not scan the core-1 stack.
`rf_metric_probes` counts explicit probes; `rf_max_probe_ns` includes the driver
snapshot and canary scan, but not the mailbox roundtrip or JSON serialization.

`rf_max_service_gap_ns` is the maximum active worker step-start to step-start
interval; it already includes the previous poll, command and diagnostic probe.
`rf_max_poll_ns` times the poll within a step, including any refill it performs.
Adding these maxima double-counts work. Both are cumulative, not per-job WCET.

All driver and worker nanosecond fields derive from `time_us_64() * 1000`.
Endpoint sampling is quantized to one microsecond. They do not measure oscillator
accuracy or electrical transitions. `system_clock_hz` is the SDK's configured
clock value, not an independent frequency measurement. The driver separately
rejects a configured system clock different from its compiled sample rate.
PIO uses one OUT instruction per cycle, divider 1, 32 packed samples per word.

## Refill, launch and finite tail

`refill_irq_pairs` matches a submitted sequence N with completion IRQ entry for
N-2 in the same epoch. `max_refill_irq_to_ready_ns` ends after configuration and
chain installation; it **omits hardware-completion-to-IRQ-entry latency**. A
missing, overwritten, reused, wrong-epoch or reversed-time match increments
`refill_irq_unpaired` instead of certifying an interval. Initial prefill is
excluded. An IRQ observation alone cannot establish the full deadline margin.

`running_successor_links` counts postlaunch submissions with a predecessor.
After installing the chain, `min_successor_ready_words` samples the predecessor's
remaining DMA transfer count, excluding FIFO/OSR reserve. Zero also increments
`exhausted_successor_links`; do not hide it merely because FIFO reserve prevented
a stall. Data-successor and zero-tail-successor minima are separate. Their names
describe the **new descriptor**, not the length of the predecessor. Short data
blocks can precede either class; a minimum without the exact job/block lengths
does not justify applying a full-block budget. Prelaunch-only and no-predecessor
paths are not counted as running links. Absent observations serialize as null.

`refill_full_predecessor` and `refill_short_predecessor` additionally retain the
worst fractional reserve in each class: remaining and original total words,
observation count, epoch, successor sequence and sample time. Fraction comparison
uses integer cross-products; fewer remaining words need not be a worse fraction.
Each short predecessor has its own interval `total_words * 32 / sample_clock`.
Zero/oversized predecessor lengths or impossible remaining counts increment
`refill_invalid_reserves` without certifying a reserve. The full-word constant
is compile-time checked against the stream buffer size.

`dma_irqs`, `tail_irqs` and `dma_errors` count handled events. The maximum DMA IRQ
interval starts at handler entry and ends after the sink callback, before final
metric bookkeeping and exception return. `alarm_irqs` and `max_alarm_irq_ns`
likewise cover the alarm callback, including its launch guard and timer wait.
The launch alarm is requested up to 200 microseconds early. `launch_observed_ns`
is sampled after enabling PIO; it is not the first electrical edge.
`launch_epoch` and `launch_target_ns` bind that successful launch to the driver's
epoch and requested monotonic timer target, allowing host job/epoch correlation. Counters
remain cumulative across jobs on a boot; compare authoritative per-job deltas.
Internal evidence does not replace Phase 11.6 conducted acceptance.

These aggregates have no allocated event log or intentional sampling drops.
They still have explicit coverage gaps: delayed IRQ entry, simultaneous pending
completions, failed submission, unobserved electrical output, and independent correlation
of those epoch/sequence minima with host job identities. Preserve external start/end identities,
all failed attempts and coverage limitations. No accepted margin is published
until the remaining observations and overhead are reviewed on the actual target.

## Application heap and stack

The linked Arm GNU 15.3.1 newlib allocator uses `_malloc_r`/`_free_r` and
`_sbrk`. The SDK outer malloc/calloc/realloc/free wrappers retain their mutex and
panic-on-null policy. Newlib stdio and nested calloc/realloc can call reentrant
entries directly; the linked newlib retarget lock hooks are no-ops. The closure
candidate therefore serializes all four inner entry points and mallinfo under a
project-owned recursive SDK mutex. No allocator implementation is replaced.
`check_heap_hooks.py` rejects direct-call bypasses in the actual ELF, including
nested realloc and stdio paths. It does not prove arbitrary function-pointer
provenance or hardware timing. These hooks are not an interrupt allocation API.

INFO still takes one `mallinfo` sample before formatting: allocated bytes,
allocator arena, arena-free bytes, free-chunk count and top releasable space.
Capacity is `__HeapLimit - __end__`; available remains capacity minus allocated,
clamped to zero. This includes uncommitted linker heap and is **not** the largest
allocatable block. `heap_sample_observed_us` and `heap_sample_cost_us` identify
that sample. The legacy `heap_sampled_peak_bytes` remains a sampled lower bound.

The closure candidate additionally reports `allocator_live_bytes` and
`allocator_peak_bytes` from every instrumented entry's post-state, including the
nested malloc-before-free in moving realloc. `allocator_entries` and
`allocator_failures` count entry invocations, including nested invocations; they
are not independent application requests. `allocator_largest_request_bytes`
includes failed requests, whereas `allocator_largest_successful_request_bytes`
excludes them. Both include deliberate probes, so necessary workload allocations
must be distinguished using the campaign's probe intervals and raw records.
`allocator_sample_time_us` sums individual mallinfo observation costs;
`allocator_max_sample_us` and `allocator_max_entry_us` retain maxima. Nested
entry times overlap and must not be summed. `allocator_max_depth` exposes nesting.
Entry duration starts after lock acquisition and does not include lock waiting.
These instrumentation costs are part of the candidate image's contention load.

TLS's existing null-handling path uses a separately named nullable inner calloc
entry, with the same lock and observation coverage. Ordinary SDK/C++ allocation
still has fail-fast behavior. Host null/overflow/concurrency tests do not qualify
arbitrary exhaustion recovery on the board. TLS counters include their wrapper
metadata and are a subset of the general heap. Fixed lwIP pools, static RF
buffers and reserved stacks are separate.

`HEAP PROBE <bytes>` performs one nullable allocation/free only after idle
admission, for 1 through linked capacity plus one byte. It reports an allocation
result, retains no block, and rejects malformed, oversized or non-idle requests
before invoking the allocator. It can change allocator arena/bin state; compare
quiet windows after matched warm-up. An oversized failure probe is distinct from
a successful largest-necessary-allocation probe. No such probe has yet run on a
device. Transient peak, fragmentation, necessary allocation, actual failure
recovery and measured overhead gates remain OPEN until target evidence passes.

Both physical stacks reserve 16 KiB. Core-0 canaries are sampled before INFO
serialization; `core0_stack_scan_us` exposes that scan's cost. The explicit
core-1 probe samples its own stack. A canary measures touched words and can miss
unwritten reserved frames and paths not exercised. Combine it with linked
compiler frames, reachable call chains, IRQ/exception nesting and justified
allowances. Append numeric INFO fields one at a time to avoid retaining scores
of temporary strings while observing memory. This reduces compiler frame size;
it does not establish measured headroom or target timing by itself.
