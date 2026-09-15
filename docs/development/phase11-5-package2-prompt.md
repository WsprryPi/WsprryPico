# Execute Phase 11.5 Package 2: simultaneous capacity and bounded overload

**Execution record: attempted, OPEN.** See the [result](phase11-5-package2-result.json)
and [review](phase11-5-package2-review.md). The original boot below is historical;
A ended in recovery boot 4768a88991247131bdc7c0fc421dbe8f after a recorded
20,480-byte LOAD allocation failure. Do not rerun this packet as a repair.

## Objective and current evidence

Work in WsprryPico on devel, starting at 14a2ddc. Read README.md, CONTRACT.md,
docs/architecture.md, the development guide, completion authorization and current
matrix. Preserve all existing work and immutable failed evidence. WsprryPi is a
read-only companion dependency for this task; do not modify its source or its
installed service. Complete review, implementation, affected validation, finite
target execution, independent adversarial evidence review, repairs, reassessment,
commit, normal push and independent remote-SHA verification.

Close only Package 2 assertions 2.2a and 2.2b. P1 is accepted on clean firmware
8dd6f0812292e9264c2a72745078a95ee606c191, physical 138 MHz/divider 1/GP2 PIO-DMA,
RAM renderer and listener enabled. A is USB 0BF4B4AEC9FFB344, device
fd6127d11d6aca42a9905fa3fb1bf1d5, last boot 7a04779b8018624574066260fce9d0d8;
B is CDDBF8767C506C07, device 29f20b7342051ef947aa56cb9d4fab42, firmware
8921a7008183, last boot 6684b4b197d80cfa0ce83b3aaf205cb0. Verify these live.
Physical A UF2 SHA256 is ccfdf60b2b927b4a3fd14cc9254a6748334d584ebad0d672771939ab2369b40d.
Do not equate repository HEAD with deployed firmware. Last fixture is restored,
both boards inactive/unowned with schedules disabled, shared RF reservation
released. Verify current state and retain existing terminal records; no reset,
flash or history clearing is needed by this design.

P1 proved sequential independent maxima. Previous supported combined-workload
failures remain failed. The repair releases a 20,480-byte event vector after
acknowledged RF handoff, preserves the original digest and budgets WTP temporary
workspace above the unchanged 32,768-byte acceptance reserve. The preceding
boot-wide peak leaves 55,944 bytes; it is not proof of simultaneous capacity.

## Reviewed mechanism and frozen cases

FrameParser reserves the complete 65,552-byte wire frame after a validated
header needs further growth. Retain an incomplete, valid maximum STATUS request
by withholding its final byte. Continue writes and reads under the original
five-second whole-exchange deadline. Do not convert a timeout into overload.
HttpParser separately budgets body bytes plus 1,024 bookkeeping bytes above its
32,768-byte reserve; exhausted header admission maps to HTTP 503 with
resource_exhausted, before body allocation. A fully authenticated second TLS
context consumes memory independently of the native WTP observer.

Use two separately frozen packets, and independently accept the supported
packet before executing overload. Each has one 512-event, 128-second FSKCW job
at nominal 135,500 Hz with alternate 135,495 Hz events, on A only. Preserve
both-board shared reservation, original RF launch/refill/tail and stack gates,
allocator/TLS-failure baselines, single-flight INFO observation and continuous
native WsprryPi TLS observation. USB owns the job; native and HTTPS observe it.

1. Supported: after authenticated HTTPS establishment, capture a fresh baseline
   INFO. Offer the maximum WTP STATUS wire except its final byte. Require a fresh
   independent INFO sample proving its full input allocation is resident before
   submitting a small, exact, valid HTTP HELLO body. Require HTTP 200 and the
   original device/boot. Only then release the final WTP byte and require the
   complete successful Running/owner-preserving STATUS response within five
   seconds of starting the wire exchange. Perform one separately authenticated
   small HTTP recovery exchange while RF continues.
2. Overload: repeat the frozen WTP residence with a separately declared HTTP
   Content-Length of 32,768 while the native observer and second TLS context
   remain active. Offer the header only. Expect HTTP 503 resource_exhausted from
   admission; no body is sent. Release the WTP final byte only after that response
   and require successful WTP completion within its original deadline. Close
   the refused HTTP connection and perform one authenticated small HELLO recovery.
   The offered unsupported combination is maximum WTP input plus maximum HTTP
   body and two TLS contexts during RF, not an oversized protocol message.

Freeze complete request bytes, unique sessions/request/job IDs, retained records,
source/image/helper/credential hashes, fixture namespaces, owner, overlap markers,
expected responses, deadlines, counts and cleanup before each execution. Require
at least 65,536 additional sampled allocated bytes relative to the warmed TLS
baseline before the HTTP stimulus, and prohibit sending the last WTP byte until
its HTTP response is fully read. Independent auditing must reconstruct those
facts from raw records, including raw INFO, not trust the marker alone. Retained
record count/expiry is recorded, not claimed as full P5 capacity acceptance.
If measurements show the predicted refusal is not applicable, stop and retain
the result; diagnose and review a distinct finite combination before a new packet.

## Execution boundaries

Use the existing named wspr5 isolated fixture and standing September 15 authority.
Create one fresh bounded fixture with 45 minutes execution and 15 minutes cleanup,
independently supervised; do not extend its deadline. Preserve Ethernet/wlan1
management and installed WsprryPi. Keep raw authenticated evidence on wspr5 or
ignored build/, publish only sanitized facts/hashes, and never publish credentials,
private configuration or raw payloads. Stage only public reviewed helper files. Reference existing wspr5 credential
and production INI files in place with verified hashes; do not duplicate private
files into new packet roots.

Initial budget: two RF jobs / 256 planned seconds, one per packet; each packet
300 seconds observation plus 150 seconds reconciliation. Zero flashes, BOOTSEL,
controlled reboots, configuration saves or diagnostic heap probes. A concrete
addressless-link failure may justify one separately frozen idle Wi-Fi OFF/ON
recovery, under standing authority, before dependent traffic. Do not infer RF-off
from disconnect, timeout or process exit. Failure stops dependent stimuli while
independent observations and bounded reconciliation continue. Do not restart
completed P1/R1/R2 work automatically. Any necessary source repair requires its
own impact assessment, reviewed image/deployment and affected retest packet.

## Validation and adversarial review

Add narrowly scoped combined-load coordination and independent auditing, reusing
existing RF/native/USB/HTTP primitives. Test exact profiles, altered identities,
byte/count/deadline violations, early HTTP stimulation, missing/stale allocation
proof, early last-byte release, wrong rejection and incomplete responses. Keep
original deadlines/reserves; no arbitrary retry loops or weakened thresholds.
Use host tests for helper behavior and all affected regression groups. Firmware
rebuild/flash is unnecessary unless source changes make it necessary.

Audit each target packet independently: raw framing/CRC/schema, complete USB
writes, exact HTTP bytes and TLS peer, allocation residence and ordered overlap,
original deadlines, independent native Running brackets, RF timing and counters,
owner/boot/configuration preservation and both-board reservation release. Test
altered evidence for overlap, bytes, response classification, native continuity
and restoration, then reassess intact evidence. Fix every actionable finding
and rerun affected checks until none remains in this slice.

Restore the host fixture and independently read both boards after execution.
Record actual charges, retained state and source identity. Write the immutable
Package 2 result and review, update current progress/matrix and stale current
summaries, preserving historical evidence. Claim only 2.2a/2.2b when their exact
gates pass; R3 and full Phase 11.5 stay open until their other gates pass. Commit
and push scoped changes; report closure, tests, limitations, restoration and
independently verified repository/remote state.

## Reviewed execution amendment: 32 KiB resident WTP profile

The first packet failed a helper INFO identity lookup before capacity input. Its
128-second job ended Complete/inactive, independently verified. A second packet
stopped before mutation because the helper did not admit the exact inactive
predecessor. Both defects are repaired and regression-tested; preserve their
failed records. A third separately frozen packet established the second TLS
context, then the maximum WTP input stopped after 4,096 host-written bytes, with
no full input allocation observed and no HTTP offered. The original five-second
exchange timed out. This is a failed supported combination, never overload credit.

The warmed allocation was 130,072 of 218,936 bytes. Source admission for a
65,552-byte WTP wire also needs temporary workspace and the 32,768-byte reserve;
that combination cannot fit. Freeze a distinct supported profile: 32,768-byte
valid padded STATUS payload (32,784 wire bytes), retain its final byte, and
require at least 32,768 additional independently sampled allocated bytes before
small authenticated HTTP. The overload packet uses the same resident WTP size
plus a declared 32,768-byte HTTP body, header only, expecting 503
resource_exhausted. All identity, ownership, deadline, RF, reserve, observer,
recovery and raw-audit gates above are unchanged.

Execute the two necessary replacement packets under the existing standing
finite-packet authority after final reconciliation of the failed packet. Charge
every armed job its full 128 seconds; never erase failed attempts or extend the
fixture deadline. The task remains limited to 2.2a/2.2b for the revised declared
profile; it does not promise simultaneous protocol maxima.

## Unresolved execution gate

The amended supported packet failed during its 52,105-byte LOAD, before ARM
or the smaller capacity stimulus. Independent recovery diagnostics record a
20,480-byte failed allocation and watchdog reboot. End this bounded attempt
OPEN, preserve its evidence and independently verify host restoration and both
boards' inactivity. The overload prerequisite remains unmet. A subsequent
source-repair work package must reproduce the failed allocation geometry and
validate affected LOAD/replay/retention behavior before a new reviewed image and
fresh supported/overload packets. Existing P1 evidence retains only its original
exact workload and boot. No target failure is relabeled as accepted overload.
