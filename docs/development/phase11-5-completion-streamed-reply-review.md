# Retained LOAD reply pressure and native observer correction

Phase 11.5 remains **OPEN, 2/6 families closed**. [Immutable result](phase11-5-completion-streamed-reply-result.json).

## Evidence and failure classification

The identified a9d5610 candidate was flashed once to A. Independent inventories
verify source, new boot, 138 MHz/RAM/GP2/listener profile, disabled scheduling,
inactive/unowned output and preserved configuration. B remains unchanged. The
new endpoint page table reduced heap capacity by 704 bytes to 219,008 bytes.

Three fresh zero-RF packets are preserved. The first guard mistook temporary
status invalidation during event reconciliation for a disconnected session. The
second mistook the application's transmission-readiness flag for observer health.
In both cases complete native Loaded/STATUS frames preceded the harness's SIGTERM.
These were harness failures; neither proves a new Pico TLS closure defect. Their
partial USB exchanges and early termination earn no completed-workload acceptance.
The second packet returned its primary 512-adjustment LOAD; its replay intent was
recorded but the guard stopped it before a replay request was sent.

The third packet used the corrected guard. With two aborted jobs retained, it
wrote all 52,105 LOAD bytes and received zero USB reply bytes before the unchanged
five-second deadline. The actual native session remained connected and reported
the new Loaded job. Cleanup aborted it and returned A to Empty. Allocator and TLS
allocation failures remained zero. Post-LOAD available-memory samples were about
85 KiB; a full 54,916-byte reply needs 88,708 bytes including its working allowance
and reserve. The exact historical instruction is not directly instrumented. A
host regression independently reproduces refusal of the full reply at 85,000
available bytes. P1f's earlier historical close branch remains unproved.

## Reviewed repairs

WTP LOAD replies now own the existing immutable adjustment list and one reusable
4 KiB wire page. The encoder computes the original payload length and CRC before
publication, then fills pages as the transport consumes them. The current page
and its address remain stable across partial writes and TLS retries. Reply bytes,
request identities, all adjustment values, framing and replay behavior remain
identical. Disconnect destroys the page and shared reference. The HTTP encoder
retains its existing implementation; this result makes no new HTTP claim.

Stream admission allows 6 KiB for its page, prefix, metadata and formatting work.
The separate 32 KiB safety reserve is unchanged. Testing the smaller output layout
exposed that the old 16 KiB request-decoding allowance could understate a strict
host model's transient demand. It is increased to 32 KiB. The original strict
replay refusal case still refuses before dispatch, at the same five-second limit.
Advertised event, payload, duration and mode limits are unchanged.

The observer now checks session/network readiness, actual identity, uncertainty
and fresh status. WsprryPi bba4024's source explicitly hides status while
`needs_status()` and marks application `ready` false for a foreign-owned job.
A temporary missing status keeps its original six-second deadline and blocks new
LOAD/CLAIM stimuli. A disconnect, changed identity, safety fault or expired
observation still stops the packet. Both captured false failures pass through the
corrected guard offline; altered wire bytes are independently rejected.

## Validation and adversarial reassessment

Seven affected host targets pass: core, endpoint, LOAD reply, standalone, RF
stream, RF worker and the actual TLS server. Red/green testing restores the old
endpoint, observes retained reply-pressure failure, restores the stream and passes.
Direct codec tests cover exact bytes/CRC at 85,000 bytes, shared reply lifetime,
move, repeated reads, 17-byte partial reads across every page boundary, exact
admission boundary and nullable page-allocation failure. Existing failure tests
were adjusted to fail the single reusable page rather than the obsolete seventh
page. Their final ownership and inactive-state checks remain.

The uncalibrated full host/TLS model originally accepted after the layout change
but crossed its reserve. That finding is preserved in the initial test log and
repaired by the larger decoding allowance; its original background and refusal
expectation are retained. No threshold was lowered. Twelve native-guard/scheduling
tests, protocol validation and two private altered-evidence checks pass.

No actionable source finding remains in the reviewed scope. Target resource,
connection continuity and RF-contention acceptance remain OPEN. A fresh identified
candidate must first pass a zero-RF sequence that recreates two retained maximum
jobs, then a replacement maximum LOAD/replay under the real native observer.
Only then may an affected RF capacity packet proceed.

All three idle packets independently reconcile A/B inactive, unowned, schedule
disabled and configuration preserved, with the shared reservation released. The
fixture remains active under its original deadline; restoration is not claimed.
Task charge is three RF jobs / 384 seconds, two A flashes, two Wi-Fi cycles and
zero configuration writes. Generated images, raw captures and private inputs
remain outside Git.
