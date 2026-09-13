# BF1 allocation fault and shared reply repair

R3 remains open. The accepted v2 completion and parallel-B recovery scope cover
this demonstrated defect, its source repair, and subsequent bounded validation.
Do not reflash A or B for routine restoration. No repaired image has yet been
physically validated by this record.

BF0 is a harness error: its oversized Content-Length expectation was 413, while
the existing parser rejects that header before API dispatch with 400 invalid_http.
Four HTTP assertions pass independent review. BF1 corrected that expectation;
all six HTTP assertions passed before a different failure during maximum LOAD.
Original packets, journals and failed summaries are retained, with independent
component checkpoints 015 and 016. BD0 deployment is checkpoint 014.

BF1 wrote all 53,413 bytes of the maximum LOAD frame, then received no response.
The host recorded B's USB disconnect and re-enumeration. A subsequent read-only
inventory independently proves a changed boot, recovery mode, allocation-panic
stage/hash, a failed 54,917-byte allocation, and final Empty/inactive/unowned
state. No ARM was sent. This is a firmware allocation failure, not an observation
expiry or a mere host timeout. Fault PC is zero, so the exact call stack and
pre-fault heap layout were not captured.

The recorded allocation size matches a 54,916-byte maximum LOAD response plus
its string terminator. Source review found that this response still used the
SDK's panic-capable string allocation. Input buffers already used a nullable
allocator with serialized newlib top trimming. The corresponding pinned-newlib
fragmentation mechanism is previously reproduced; BF1's exact allocation history
is not claimed to have been replayed.

The repair uses the existing nullable wire-buffer allocation for successful LOAD
replies, with a 32 KiB reserve and exact response-size bound. WTP moves that buffer
into its output queue and retains separate header/payload framing. If allocation
fails, it closes the endpoint; the service remains available for authoritative
state reconciliation. An accepted LOAD is not falsely changed into a rejected
operation and no ARM is introduced.

Adversarial source review identified the same large-string allocation in the
browser LOAD path and a second full reply copy in HTTP framing. Both are included
in this repair: the browser rewrites the shorter envelope within its owned
buffer, and the TLS server sends HTTP headers and body separately. An unavailable
browser reply returns resource_exhausted; an already accepted job remains inactive
and replayable. Callers still reconcile state before ARM. The small-response and
HTTP status/header formats are unchanged. The firmware HTTP serializer was
rebuilt and its existing fixture's complete wire bytes matched exactly.

Verification covers 512 adjustments with seven-byte partial WTP output, exact
wire equivalence, one nullable payload allocation with no large throwing-string
copy, forced output-allocation failure without service reset, reconnect/STATUS,
browser allocation failure with retained inactive job and successful replay,
and actual pinned TLS HTTP/WTP/configuration-response acknowledgement behavior.
The complete host suite passed 61 groups immediately; its remaining serializer
provenance fixture was regenerated from the changed source with unchanged wire
bytes, and the affected R3 group passed afterward. The earlier unprivileged
loopback bind failure is an environment limitation, not a firmware regression.

The source reassessment checked buffer sizing and moves, shorter-prefix bounds,
borrowed JSON view lifetimes, no second large HTTP copy, partial-write offsets,
TCP acknowledgement accounting, deferred configuration application, endpoint
closure, and replay of an accepted inactive LOAD. These checks are software
validation. B's failing sequence must pass on the identified repaired image
before changing A. A's affected image/resource/transport checks and the full
retention/reclamation campaign remain required. No claim that all memory
combinations are safe is made from this repair alone.

Fresh c5f00b6 pressure packets T2/T3 were prepared but never staged or executed.
They are retired before execution because BF1 demonstrated this shared defect.
Their RF count is zero. F1 remains active under its original immutable cleanup
deadline while the repaired candidate is prepared.
