# Execute the Phase 11.5 memory-pressure repair

## Objective and reviewed baseline

Work only in WsprryPico, branch `devel`, starting from `150fe01` and the five
existing deployment/test-helper changes. Preserve those changes and all failed
evidence. Review README.md, CONTRACT.md, docs/architecture.md and the development
guide. This is a focused repair; it does not close all Phase 11.5 packages.

Current firmware supports 512 events, 32 message characters, 3,600 seconds,
65,536-byte WTP payloads and 32,768-byte HTTP bodies. Preserve these limits,
CRC/schema validation, five-second WTP deadlines, ownership, replay/expiry,
and the 32,768-byte resource acceptance reserve.

Recent repairs page HTTP bodies, stream LOAD replies, avoid duplicate active
replay decoding, separate INFO temporary lifetimes, and share identical retained
adjustments. Native-idlek passed three maximum idle LOADs and replay on 150fe01.
P1i subsequently failed during maximum WTP input with a 512-event RF job and
three retained jobs: heap capacity 218,968, peak 193,448, reserve 25,520 bytes;
24,576 of 65,552 wire bytes written. No allocator/TLS failure was recorded.
Final inventories reported A Complete/inactive/unowned and B Empty/inactive/
unowned; reservation released. Preserve this failure, not as accepted overload.

## Code-review findings to address

1. JobService retains its original event vector during RF even though
   StreamEngine has already built an independent immutable segment plan.
   WorkerEngine completes a synchronous rendezvous and clears its input pointer
   before schedule returns. The original 512-event vector costs 20,480 bytes on
   RP2350. Releasing it requires an explicit engine lifetime contract; generic
   engines must remain conservative by default.
2. Replay and terminal history currently derive their digest from that vector.
   Preserve the original typed digest before any release. Same-job replays,
   changed-job conflicts, ARM replay, abort, failure and terminal expiry must
   continue to work after release without reconstructing the vector.
3. FrameParser admits a complete input allocation against only the acceptance
   reserve. Input residence overlaps INFO formatting and request decoding.
   Account separately for bounded temporary workspace and paged allocation
   overhead; do not treat this workspace as permission to consume the reserve.
4. Monitoring loss followed a resource-triggered stop in P1i. Its exact causal
   relationship is not established. Validate continuous monitoring in the
   affected target retest rather than claiming the source repair proves it.

## Implementation and validation

Implement the smallest justified lifetime and admission repair. Do not alter RF
waveform generation, clocks, sample plans or protocol limits. Define an immutable
engine capability for releasing job input after successful schedule/begin;
default false. Forward it through the worker without cross-core virtual calls
after startup. Release only after acknowledged success, preserving the digest
and metadata needed for authority and completion. Failed/unacknowledged handoff
must not permit early release.

Add behavior-focused host tests for both engine lifetime contracts, local and
foreground launch, failed scheduling, exact/fresh-ID LOAD and ARM replay,
changed-event conflict, abort, completion, unknown output and replacement.
Verify the actual StreamEngine runs from its owned plan after input destruction.
Exercise maximum WTP bytes under modeled concurrent memory, reserve boundaries,
nullable allocation failure, deadline and reconnection behavior. Retain existing
negative tests and explain any newly intentional admission changes.

Run affected core, endpoint, LOAD, RF stream/worker, standalone and network/TLS
checks, then broader regression when source impact warrants it. Build inhibited
and physical 138 MHz/RAM images with the existing pinned SDK/toolchain. Inspect
heap, stack, flash layout and unchanged renderer placement. Host evidence does
not establish target timing or physical acceptance.

## Bounded affected target retest

Use the September 15 standing authorization and exact named lab devices.
Restore the previous finite fixture before starting another; never extend its
deadline. Freeze source/image/helper hashes, observed boots/configuration,
workload, deadlines and restoration before execution. Use A for the repaired
image, keep B inactive with scheduling disabled, and enforce the existing shared
RF reservation. No configuration writes or arbitrary RF retry loops.

Use one justified A deployment and reproduce retained-state pressure explicitly
before one 128-second, 512-event FSKCW job at nominal 135,500 Hz. Include the
native TLS observer, complete maximum WTP input, oversize/recovery and the
affected HTTP boundaries in the declared sequence. Preserve observer cadence
and all original reserve/timing gates. A smaller fresh-boot workload is not a
substitute for the failed retained combination. Freeze any necessary follow-up
packet separately after identifying a concrete failure mechanism.

Independently inspect raw test records on wspr5: full writes, framing/CRC,
responses, actual overlap, original deadlines, resource peaks, RF timing,
ownership/configuration and restoration. Publish sanitized facts and hashes;
exclude credentials and raw authenticated traffic from Git. Preserve failed
records and exact cumulative charges. Claim only assertions actually observed.

## Adversarial review and delivery

Review lifetime safety, cross-core handoff, digest semantics, refusal behavior,
resource accounting, stale/missing observations and unsupported closure claims.
Repair every actionable finding and rerun its affected checks. Repeat the
adversarial assessment until none remains in the repair scope, or document an
external blocker explicitly. Do not substitute threshold changes or rebooted
history for a passing workload.

Update the current progress/matrix without changing immutable historical
results. Save a review and an immutable repair/validation result. Commit the
scoped source, tests, reviewed pending helpers and documentation; push normally
and independently verify the remote branch SHA. Report implemented changes,
host versus target results, unresolved physical gates, final device/fixture
state, commit and actual working-tree/remote state.
