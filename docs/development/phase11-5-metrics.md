# Phase 11.5 measurement definitions

These are diagnostic observations, not accepted limits. The
[current ledger](phase11-5-acceptance-ledger.md) accepts no physical configuration;
the [legacy register](phase11-5-register.json) retains historical 20-case records.
The [plan](phase11-5-plan.md) defines selected clocks and remaining gates. Its
six-family reorganization does not change these measurement meanings or convert
older candidate-specific limitations below into current evidence.

## Console INFO and WTP STATUS are different interfaces

Console `INFO` is implementation diagnostic JSON, not a WTP `STATUS` response.
Its nested `status` comes from `standalone::Scheduler::status()`. WTP `STATUS`
comes from `wtp::ServiceStatus` through `status_json()` and the versioned WTP
response schema. Similar field names do not make these objects interchangeable.
The field map below is verified against candidate source `2e43110f0530` and its
recorded responses; it is not an extension to device-neutral WTP/1.

| Evidence | Fields and authority |
| --- | --- |
| Console INFO | `device_id`, `revision`, resource counters and `launch_epoch` are top-level fields. Nested `status` supplies `boot_id`, `state`, `output_active`, clock and standalone scheduler state. It supplies **neither `job_id` nor `owner_id`**, including during Running RF. |
| WTP STATUS response body | Supplies `boot_id`, `state`, `output_active`, nullable `job_id` and `owner_id`, and `terminal_records`. Use this interface for current job/owner authority. |
| HTTPS GET `/api/v1/status` | Its `job` object uses the WTP service-status representation. Its separate `standalone` object uses scheduler status. Neither is the complete Console INFO envelope. |
| Console `status.last_job` | Identifies the standalone scheduler's last job. It may remain empty throughout a USB-owned or network-owned job and is **not** a substitute for WTP `job_id`. |

To correlate contention with a job, require fresh matching boots and Running /
active state in both Console and WTP observations. Bind job and owner through
WTP STATUS and the raw LOAD/ARM lifecycle. Bind Console counters through the
current nonzero `launch_epoch`, require it to advance for the next job and remain
unchanged throughout that job's pressure cases, and verify the epoch against the
per-job timing audit. Missing Console job/owner fields must never be filled with
assumed IDs or treated as evidence of unowned output.

Observer files add their own envelope: `observer-info.json.value.value` is the
Console INFO object; `observer-status.json.value.value` is the WTP STATUS body.
Their packet hash, timestamp and observer PID/start time must also match.
Tests must exercise recorded response shapes, including idle and externally
owned Running states, rather than constructing both interfaces from one schema.

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

The allocator observation cost repair samples after every instrumented malloc,
calloc and realloc, including the nested malloc-before-free in moving realloc.
Free cannot increase allocated occupancy and no longer triggers a redundant
free-list walk. `allocator_peak_bytes` retains those allocation post-states;
every public snapshot refreshes `allocator_live_bytes` under the same recursive
lock, including after frees. The previous 4ca4494 image sampled after free too;
its failed physical browser interval spent 3.414361 of 13.285770064 seconds in
allocator sampling. The repair requires its own exact-image target evidence;
the measured cost does not prove that this change resolves the browser failure.
`allocator_entries` and
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
a successful largest-necessary-allocation probe. The later R1 target evidence
below supplies bounded idle feasibility/recovery and cost measurements; it does
not measure exact fragmentation or qualify active-RF resource behavior.

Both physical stacks reserve 16 KiB. Core-0 canaries are sampled before INFO
serialization; `core0_stack_scan_us` exposes that scan's cost. The explicit
core-1 probe samples its own stack. A canary measures touched words and can miss
unwritten reserved frames and paths not exercised. Combine it with linked
compiler frames, reachable call chains, IRQ/exception nesting and justified
allowances. Append numeric INFO fields one at a time to avoid retaining scores
of temporary strings while observing memory. This reduces compiler frame size;
it does not establish measured headroom or target timing by itself.

### Guarded stack reserve for the closure candidate

The linked audit found that compiler reports cannot be treated as exact stack
pointer bounds: `PioDmaSink::dispatch` reports 56 bytes in `.su`, while its linked
prologue subtracts 8, pushes 36 and subtracts 20 bytes (64 total). Incoming
argument homes and library/assembly paths need accounting beyond a simple sum
of compiler reports. P3's touched extents therefore remain lower bounds.

The next closure candidate uses the SDK's existing RP2350 Arm stack-guard entry
points to install **MSPLIM = allocation bottom + 4,096 bytes**, on core 0 before
the runtime initializers/C++ constructors and on core 1 before its runtime and
RF worker. This retains each 16 KiB allocation and enforces the predeclared
4 KiB reserve for normal privileged MSP execution, including normal interrupt
stacking and unwritten stack-pointer reservations. It does not add a poll or
instrumentation call to the waveform loop. `check_stack_guards.py` verifies both
linked startup routes, the sole MSPLIM writer and register readbacks. The source
and linked constant must also be reviewed; that checker is not a hardware test.

INFO's `core0_stack_guard_bottom`, `core0_stack_guard_limit`,
`core0_stack_guard_valid` and `core0_stack_fault_status` report the local register
check. The explicit worker probe supplies the corresponding `core1_*` fields
from core 1. Validity is numeric 0/1 and requires privileged MSP selection, the
exact allocation bottom, a 4,096-byte limit offset, SP above that limit and no
sticky CFSR.STKOF flag. These readbacks do not clear fault status. Setup failure
retains `STGD` in watchdog scratch and cannot continue into application work.

For this new image, the stack acceptance predicate is valid guard readback on
both executing cores throughout the full matrix, unchanged admitted boots, no
stack fault/reset, and canary/frame/call-path evidence reported alongside it.
This replaces a guessed additive allowance with an enforced numerical reserve;
it does not reduce the 4 KiB requirement or turn unexecuted cases into passes.
The hardware limit is not an MPU memory-corruption guard and does not qualify
HardFault/NMI recovery paths, foreign PSP execution, other images or other clock
configurations. Any guard failure, unexpected boot or missed observation fails
admission/acceptance and blocks dependent actions. P3 does not contain these
guard observations. The later exact-image R1 campaign validates guards in its
idle workload scope; the remaining active-RF matrix is still open.


### R1 target measurements on September 12, 2026

The [R1 result and review](phase11-5-r1-review.md) close 5/5 assertions on source
`e20ae8bea2d5237af017dbd5f73bfe9332ce144e`, physical 138 MHz, divider 1, RAM
renderer and listener on. Inhibited 150 MHz supplies regression only. Four
frozen linked layouts were rechecked and six idle target intervals passed.

Exactly three idle probes returned 18,364-byte success, 218,381-byte NULL, then
18,364-byte success. The successful size is a demonstrated allocatable-block
lower bound, not an exact largest block. Matched quiet heap changed from 16,844
to 16,836 bytes (−8); physical peak 121,780 left at least 96,600 bytes of reserve.
Both 16 KiB stacks maintained valid 4 KiB guards; canary touched extents peaked
at 8,248/544 bytes, with the canary limitations above unchanged.

Physical allocator sampling occupied 13.253–13.845% of observed intervals.
Maximum sample/entry times were 56/153 µs, core-0 scan 124 µs and core-1 probe
316 µs. These costs overlap and are not a full CPU profile. Service timing gates
passed with that instrumentation; the largest USB round trip was 1.165 seconds.
No RF job ran. R2–R6, physical refill/launch acceptance, other clocks and the full
accepted-configuration list remain open/empty. See the review for exact identities,
raw audit hashes, retained failed attempts and restoration evidence.
