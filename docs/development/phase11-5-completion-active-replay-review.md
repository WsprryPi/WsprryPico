# Active LOAD replay reserve repair

Phase 11.5 remains **OPEN, 2/6 families closed**. [Immutable result](phase11-5-completion-active-replay-result.json).

## Target failure and restoration

A's identified d674dc6 firmware returned three complete maximum LOAD replies,
each with all 512 exact adjustments. A fresh-ID replay then wrote all 52,105
request bytes but returned no completed response. The raw INFO observer found
31,200 bytes of peak allocator headroom, below the unchanged 32,768-byte gate.
No ARM, RF launch, allocation failure or firmware fault occurred. The independent
native connection supplied 21 STATUS responses; its incomplete observation
window is not credited as a 90-second pass. This failure remains failed.

Cleanup incorrectly reused the acceptance health gate and stopped before its
ABORT command. The original reservation stayed HELD. Later raw A/B inventories
proved Empty, inactive, unowned and scheduling disabled after A's lease expiry.
A guarded reconciliation released that same packet's reservation; no additional
ABORT, CLAIM or RELEASE was sent. It requires fresh proof, matching host/board
boots, revisions and packet identity. It does not clear uncertainty on process
exit or transfer a held reservation to another packet.

The temporary fixture was restored before its fixed independent cleanup start.
Fresh post-restoration inventories confirm both boards inactive and their
configurations preserved. A retains d674dc6 on boot
d76d4e540ddafff6622513596125c58c; B retains 8921a7008183 on its original boot.
Installed WsprryPi PID 1957 and management connectivity were preserved. Cumulative
task charges are three RF jobs / 384 planned seconds, three A flashes/BOOTSEL
transitions, two Wi-Fi cycles and zero configuration writes.

## Repair and source impact

An active same-job LOAD replay now validates each JSON event and builds the
existing typed SHA-256 identity without allocating another 512-event vector.
Dispatch still checks session replay, schema, ownership and live state, then
compares the complete job digest. The compact internal body cannot create a new
job. Changed frequency, duration or mode remains JOB_ID_CONFLICT; malformed
fields remain invalid; output-active and expired-owner paths remain rejected.
If the job becomes terminal during decoding, its retained digest supplies the
same identity check. Unknown jobs use the original full decoder.

The endpoint keeps a 32 KiB decoding allowance for other requests. Recognized
active replays use a 6 KiB allowance, separately from the unchanged 32 KiB reserve.
Pending admission retains its original five-second deadline. Identifier and
uint64 strings are bounded before allocation using their existing semantic
limits, including fully escaped JSON. This prevents a malformed long scalar
from defeating the smaller replay workspace. INFO reserves its normal 6 KiB
string capacity once to avoid simultaneous old and doubled growth buffers.
This INFO change is source-reviewed; its target peak benefit is not yet measured.

Cleanup now checks board/boot/scheduling identity independently of resource
acceptance, so a failed peak cannot prevent its already-authorized safety abort.
Final inventory still must establish authority before reservation release.

These changes affect decoding allocation, stack use, retained replay timing and
INFO peak memory. They do not change RF rendering, PIO/DMA, mode compilation,
512-event/32-character/3,600-second limits, output authority or the wire schema.
Historical R1/R2 evidence retains its recorded applicability. Current resource,
contention and timing acceptance remains open and requires affected target work.

## Review and validation

Seven affected host targets pass: core, endpoint, LOAD reply, standalone,
RF stream, RF worker and actual TLS. Tests verify exact 512-adjustment replies,
byte-identical and fresh-ID replay, no second preparation/start, bounded replay
allocation, escaped scalar equivalence, changed fields, foreign ownership,
Armed replay, unknown compact jobs, real lease expiry and oversized malformed
scalars. The canonical digest is also checked against an independently computed
fixed value. The unchanged protocol validator passes all 39 cases.

The old endpoint fails the stricter host replay success gate; restoring the
repair passes. Its 31,384-byte background now retains 49,391 bytes of headroom
because the event copy was removed. A separately declared 48,000-byte background
still refuses at five seconds with 33,543 bytes of headroom. No threshold was
lowered and neither host model predicts whole-target resource behavior.

The R3 suite passes 172 tests, with 42 private-evidence cases skipped. Seven
reservation/cleanup tests and two supplied private failure-audit tests pass;
mutated reply bytes, fabricated peaks and changed reservation identity are
rejected. The independent failure audit handles event frames spanning USB
exchange labels, rather than treating labels as stream boundaries.

Review found and repaired a missing compact-body dispatch type check and long
scalar allocation exposure. Initial failing checks and the initial red-build
header mismatch are retained privately. Final source reassessment has no
remaining actionable finding in this repair scope. This is not target closure:
next is a fresh identified image and the same three-LOAD/replay workload under
the real native observer, followed by the still-missing RF capacity assertions.
