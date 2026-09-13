# R3 v2 remaining execution design

This is implementation planning under accepted R3-COMPLETE-20260913-v2,
not an executed packet or acceptance result. Freeze exact identities, source,
helper closure, jobs, counts and deadlines before each prospective action.
Preserve checkpoints v2-001 through v2-008 and all failed attempts.

## Preserved mode hours and the active final mode

H0's QRSS hour is validated in checkpoints v2-006/007. Its original HTTPS cadence
failure remains separate. H1a's FSKCW hour is validated in v2-010 from surviving
independent raw Console/native WTP observations and exact DMA/tail completion;
its full USB observer gate remains FAILED. The corrected HTTPS cadence passed.
H2b is running DFCW on the same source/image/boot with the corrected atomic INFO
publication guard. H1, H2 and H2a were retired before execution; do not run them.

Preserve independently validated mode hours across the HTTP-only repair. Complete
the final-image dependency comparison and affected target regression before
applying old-image assertions to final acceptance. Checkpoints v2-009/011 retain
the harness fixes, failed attempts and independently verified idle reconciliation.
A remains on its tested RF image until a demonstrated code defect requires a
repair; there is no routine switch to an inhibited image. The separately accepted
parallel-B plan permits a current-code B image and bounded zero-RF functional
tests after H2b/E1 finish their unchanged-B gates. Subsequent A packets do not
open B or claim it is unchanged; they record the independent B workload.

## Final image and fresh fixture

The HTTP outer-padding admission repair is host-tested and provisionally linked,
but not deployed. Finish review, commit a clean source identity, explicitly
configure CMake again to regenerate the firmware revision, build BOTH firmware
targets, convert the RF ELF with the pinned picotool and check the image. The
firmware output directory is build/phase11-5-r3-v2-firmware/firmware. Merely
building a changed C++ file does not necessarily rerun CMake's Git identity step.
Keep the old deployed ELF/UF2 and each new image in immutable checkpoint copies.

Complete F0's owned cleanup before creating a fresh finite F1 if its unchanged
cleanup deadline cannot cover the remaining work. Do not extend F0 silently.
Admit the new image under a fresh bounded E1 packet, recording the changed boot,
kept test configuration and unchanged B. New B1/T0/T1a/capacity/reclamation packets
must name the actual new source/image/boot and F1 namespace/deadline. Existing
unused staged packets remain immutable; retire them with zero RF credit rather
than editing their staged bytes. No additional user approval is required inside
the accepted work/recovery scope and unchanged wiring.

## Remaining distinct physical mechanisms

- Actual Chromium: reuse the reviewed B1 design through a fresh final-image
  packet. Keep the real 30,000/30,001-byte files, all mode 31/32/33/spaces previews,
  FSKCW completion, Armed QRSS abort and DFCW abort after at least 120 seconds
  Running. Audit target-served asset hashes, actual request/response bodies,
  independent USB authority, exact displayed duration/progress and screenshots.
  An inactive/unowned terminal result may require an explicitly recorded idle
  CLAIM/RELEASE before a later packet requiring Empty.
- Native Pi submission: run the identified bba4024 executable from its isolated
  path, with task-private INIs and no installation/service change. Use actual
  production scheduling/encoding for the mode/path cases. Bind its generated
  session/owner/job/start while Waiting before dispatch, with all independent
  observers ready. One-hour repeat schedules are only a guard against a second
  launch: stop the owned executable after its first finite result. Preserve
  raw native TLS writes and full frames. The old QRSS-ETE-33s helper is too
  restrictive for new plans and must not be reused unchanged.
- TLS/transport: T0's two 100-second Tones and T1a's two 150-second Tones cover
  the ten TLS and fourteen transport cases. T1's earlier 100-second transport
  draft was retired before execution because full permitted case deadlines
  could exceed its RF interval. Preserve server-flight-first, payload-free ACK
  suppression, capture/clock mapping and owned-table cleanup.
- PROGRESS: separate a fully activated WTP connection's 30-second inactivity
  timeout from the five-second partial-frame and endpoint unread-output paths.
  An earlier parser timeout cannot prove output-backpressure expiry. For an
  unread TCP receiver, retain zero-window and target-close evidence, last target
  progress, client nonclosure, timeout counters and authenticated slot reuse.
  This packet cannot also keep a native WTP client in the single WTP slot.
- WTP-MAX: exercise full 65,536-byte STATUS writes and a correctly framed,
  CRC-encoded 65,537-byte request plus same-connection recovery during Running.
  Each large exchange needs its own observer period and full byte accounting.
  Avoid putting two five-second exchanges into one five-second observer cycle.
- HTTP-MAX/JOB-MAX: prove exact 32,768-byte valid padded HELLO and intended HTTP
  rejection of Content-Length 32,769, distinguishing offered body bytes from
  any early server rejection. Exercise an actual 512-event finite RF plan under
  declared contention. Its event maximum is independent of the three mode hours.
  Preserve an ordinary 162-symbol WSPR frame as the affected compatibility path.
- USB: use a separate authoritative network owner/observer while deliberately
  blocking USB output or applying parser pressure. Never duplicate an interface
  opener or claim inactivity from a closed/broken USB connection.

## Capacity, retention and three equivalent reclamation cycles

First measure supported paths. Do not assume that all independent maxima fit
simultaneously. A 512-event loaded job, its adjustment reply, replay copies,
retained terminal replies, a 65 KiB WTP input, a 32 KiB HTTP body and two TLS
contexts are distinct concurrent allocations. Declare each supported combination
and the intended rejection layer of deliberate overload before its packet runs.
An ordinary BUSY response is not successful allocation proof.

A candidate repeated cycle is eight short, genuinely completed finite jobs to
establish an equivalent full terminal set, followed by one 512-event finite job
and the highest measured supported allocation/retention path. Nine jobs fit the
per-packet sixteen-job ceiling. Use enough duration to independently observe
Running; one-second jobs can fall between five-second STATUS samples. The actual
long mode hours cover sustained lifetime; duration does not itself increase the
fixed waveform buffers or prove the highest allocation footprint. Justify reuse
from source and measured live/peak resources instead of adding unnecessary hours.

Logical session and replay tests can use harmless authenticated HELLO operations
through the stateless browser API while the USB/native owner remains fixed.
One session can fill eight request-ID entries, verify conflicts for all eight,
touch the oldest with an exact replay, insert a ninth and prove the correct
victim and retained touched entry. Sixteen logical sessions must include existing
observer/native sessions. A 360-second initial quiet interval with only the
known observers avoids pretending unknown recent sessions are absent. Prove the
sixteenth admission and bounded seventeenth rejection, then actual expiry and
reuse. Do not treat HELLO's automatic session recreation as direct evidence that
a prior session was absent; use a valid non-owning operation whose HELLO_REQUIRED
versus NOT_OWNER result distinguishes those states, and account for any touch
that changes last-seen time.

After the highest-state job completes, use its actual terminal timestamp to wait
through 3,600-second retention. Preserve complete INFO/STATUS/health coverage.
Authenticate reuse within the stated recovery window after expiry. Flush the
known observers' eight cached old STATUS snapshots with at least sixty seconds
of normal empty-state observations. Compare matching post-cache states across
three actual cycles on one image/boot, with exact terminal/session/replay counts,
network/cache phase and TLS allocation state. Prospectively keep the existing
1,024-byte tolerance and no monotonic retained growth. Use current/live allocator
and heap observations, not a cumulative peak as if it could fall after cleanup.
Record the named fragmentation approximation (arena free chunks/top-releasable
space) and prove the largest required supported allocation again in the matched
recovered state. No idle heap probe is permitted while Loaded/Armed/Running.

The whole repeated packet must budget warmup, quiet intervals, all finite jobs,
actual expiry, post-cache observations and cleanup. A 4,000-second hour-runner
limit is insufficient for this cycle; use a separately validated finite cycle
scope rather than weakening or replaying a consumed hour packet. F1's finite
fixture allowance can cover several reviewed packets only while each full
remaining execution and cleanup budget still fits before its original deadline.


## Prospective retention timing preparation

The pure retention-plan helper freezes 39 harmless HTTP HELLO/RENEW exchanges:
14 new logical sessions alongside the two continuously observed WTP sessions,
the seventeenth-session rejection, eight reply entries in one session, conflicts,
LRU touch/eviction, 360 seconds of actual quiet, and expired-session/reply reuse.
Replay entries are filled only after session occupancy is checked. The touched
entry is checked before the evicted entry so the five-minute TTL cannot be
mistaken for LRU eviction at the permitted response deadlines.

The proposed last RF job is a 512-event, 1,020-second FSKCW plan. Thirty-nine
15-second response allowances, the actual 360-second wait and 60 seconds of
observation reserve total 1,005 seconds. This is prospective workload sizing,
not execution or acceptance. The separate repeated-cycle policy drafts eight
ten-second completed warmup jobs, that maximum plan, real terminal expiry and
an inactive maximum LOAD/RELEASE reuse check, within 6,000 seconds plus 150
seconds cleanup. Final selection still depends on measured supported memory
combinations. These pure policy helpers do not implement or authorize an
unreviewed runner. The accepted comprehensive scope remains the authority.
