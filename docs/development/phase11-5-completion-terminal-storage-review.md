# Completion capacity repair checkpoint

Phase 11.5 remains **OPEN**, with R1/R2 closed in recorded scope and R3–R6
open. [Immutable results](phase11-5-completion-terminal-storage-result.json).

## Evidence and findings

- P1b stopped at fixture deadline admission before device access. The expired
  allowance was not extended. Its first Wi-Fi preparation packet also stopped
  before OFF/ON because the recorded link prerequisite had changed.
- Two separate justified idle Wi-Fi packets each executed exactly one OFF/ON.
  Independent raw Console and WTP audits verify unchanged source, boot,
  configuration, inactive output, disabled scheduling and recovered address and
  synchronized clock. R5.wifi is accepted within that scope on source 98f5797.
  These cycles do not prove a changed lease, certified-name recovery or full R5.
- P1c sent only HELLO/STATUS. Its initial guard incorrectly rejected the declared
  prior Complete job. The guard now accepts that exact inactive, unowned
  predecessor before LOAD; it still rejects foreign jobs, active output and
  predecessor state after LOAD. Offline tests cover those distinctions.
- P1d reached CLAIM/LOAD, but the maximum replacement LOAD returned a framed,
  identity-matched INTERNAL_ERROR. No ARM was sent. Native TLS remained
  connected. The secondary status guard failure after rejected LOAD remains
  recorded; it did not authorize a retry or hide the Console observations.
- Independent USB framing/CRC/schema and native TLS audits establish zero RF
  in P1c/P1d, unchanged launch/DMA/alarm/tail counters, preserved final authority,
  configurations and disabled schedules. Altered request/accounting evidence
  is rejected. The earlier partial-write RF failure remains failed.

## Smallest firmware repair

JobService retained the completed 512-event array (20,480 bytes) after the engine
had stopped. The terminal digest and LOAD/ARM replies were already retained
separately. With native TLS connected, decoding the replacement job left less
than the unchanged 98,304-byte LOAD admission requirement. Source has one
INTERNAL_ERROR return in this LOAD path, at that admission check. Samples around
the failed LOAD support the explanation; they are not a precise minimum-heap
trace or proof of an allocation failure.

Release the event array only after authoritative Complete and after recording
the digest/replies. Preserve identity, duration, terminal history, retention TTL,
capacity, adjustments and replay semantics. Failed/output-unknown retains its
array. No renderer, worker, timing, PIO, clock or advertised limit changes.

The host regression reproduces failed maximum replacement LOAD without the
repair, then passes with it. It also checks Running storage lifetime, uncertain
output retention, exact terminal LOAD/ARM replay, changed-job conflict, unchanged
history and no duplicate engine start. Six affected CTest targets pass, as do
the WTP contract and changed C++ formatting checks. The R3 suite passed 167
tests with 34 private-evidence skips before this firmware-only edit.

## Adversarial reassessment and remaining validation

Status and retention use the retained identity/duration; replay compares the
saved digest before consulting the active job. Engine preparation retains no
reference to JobService's event array, and Complete follows disable/inactive
confirmation. No path needs the completed events after release. Keep
Aborted/Missed/Failed handling unchanged.

This is host validation of a repair, **not a target acceptance result**. Build
identified inhibited/physical images and check linked layout, heap/stack guards
and RF placement. A fresh bounded target packet must prove completed-state
replay and maximum replacement LOAD under native TLS, plus affected capacity
and resource behavior. R1.4/P5 lifetime applicability is affected. Component 9's
closed idle LOAD/Aborted replay path is unchanged and is not rerun merely for
this Complete-only repair. R2 timing evidence retains its recorded scope.

The latest fixture restoration is independently checked against raw cleanup,
host and time.local records. Fresh A/B inventories show both Empty, inactive,
unowned, unchanged configurations and disabled schedules. A's Complete record
expired naturally at its existing TTL. Boots and deployed images are unchanged.
The shared RF reservation is released. Cumulative task charge remains one RF
job / 128 seconds, two Wi-Fi cycles, zero flashes and zero configuration writes.
