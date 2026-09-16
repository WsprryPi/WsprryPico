# R3 v2 execution progress

R3 is **CLOSED** by [Package 6](phase11-5-package6-review.md). The user accepted R3-COMPLETE-20260913-v2 on September 13,
including implementation, finite RF, recovery, review and commit/push. Exact
acceptance and counters are in phase11-5-r3-v2-campaign.json. Historical packet
approval text is retained as history; v2 is the current standing authority.

## Current four execution groups

The accepted handoff R3-FOUR-GROUP-HANDOFF-20260914-v1 supplies this execution
grouping. It preserves all fourteen normative R3 groups and seven feature checks.
The user has now said Execute. Standing finite approvals remain active.

1. **Controller and lifecycle — CLOSED (checkpoint 043)**
   - 1.1 B7 collected and independently reconciled in checkpoint 035. Its original
     INFO cadence gate remains FAILED. Prospective observer and UI harness
     corrections passed prospectively in B9/N0/N1; the underlying B7 exchange delay
     remains unresolved and its original score is preserved.
   - 1.2 PASS: B9 Running cancellation after at least 120 seconds, checkpoint 039. Reuse
     prior file/Tone, completed FSKCW and Armed-cancellation components only within
     their recorded source-impact scope.
   - 1.3 PASS: native QRSS/FSKCW/DFCW submissions in checkpoints 040–042;
     acknowledged-ARM loss, local completion and original-session reconciliation
     in 043. Original harness failures remain separately recorded.
2. **Capacity and pressure — CLOSED (Packages 1–4 accepted)**
   - 2.1 Individual WTP, HTTP and maximum job capacity is accepted by Package 1.
   - 2.2 Supported combined load, bounded overload and network TLS/HTTP pressure
     are accepted by Packages 2 and 3.
   - 2.3 Network WTP inactivity/input/output progress is accepted by Package 3.
     Package 4 accepts both USB parser pressure and unread-output silence/DTR
     recovery.
3. **Retention and reclamation — CLOSED (Package 5)**
   - 3.1 PASS: measured bounded-overload workload and finite fixture allowance frozen.
   - 3.2 PASS: replay/session/terminal capacity, reuse, eviction and actual expiry.
   - 3.3 PASS: three equivalent cycles on A's same firmware and boot; eight-byte
     post spread under the unchanged 1,024-byte gate.
4. **Closeout — CLOSED (Package 6)**
   - 4.1 PASS: all fourteen R3 groups and twenty-four mandatory rows reconcile
     as accepted/applicable.
   - 4.2 PASS: all seven extended features and current-image `R1.4` applicability
     reconcile through exact source-impact review; no affected physical gap remains.
   - 4.3 PASS: the repaired auditor rejects 24 mutations; Package 6 used no
     hardware or fixture allowance and inherits Package 5's verified restoration.

## Package 3 network pressure and progress result

[Package 3](phase11-5-package3-review.md) accepts current-image TLS handshake,
failed-alert, slot/pending, partial/stalled HTTP, three distinct WTP progress
timeout and affected browser-resource assertions. Four RF jobs / 500 planned
seconds are accepted; three failed RF jobs / 300 seconds remain charged and
receive no credit. Thirty-six evidence mutations are rejected and all intact
packets reverify. Both Picos and the host fixture are restored.

Capacity/pressure is CLOSED after Package 4 and retention/reclamation is CLOSED
after [Package 5](phase11-5-package5-review.md). Package 6 completes the
assertion-level closeout and closes R3. Phase 11.5 remains open at 3/6 families;
Package 7 and R4 are next.

## Package 4 USB result — COMPLETE

[Package 4](phase11-5-package4-review.md) accepts 2.3d with an exact 65,552-byte
USB frame, directly observed equal parser reservation, independent authenticated
network authority, Console observation and both same-connection and DTR
recovery during a 100-second Tone. The evidence auditor reconstructs the raw
network, Console and USB response streams.

The repaired [2.3e retest](phase11-5-package4-unread-retest2-result.json)
offered 94 complete STATUS requests with zero application reads for 12 seconds,
then recovered 11 responses plus a bounded partial response. With DTR still
asserted, it flushed only unsent host output and observed two seconds of
same-session silence; fresh HELLO/STATUS succeeded after DTR recovery. Network
and Console observers bracketed Running, the single 100-second Tone completed
inactive, both Picos returned Empty, the reservation was released and the host
fixture was restored.

The failed original attempt and first focused retest remain retained. The first
retest stopped before unread pressure on a 232 ms Console/network transition
race. The repaired retry physically passed the bounded transition wait. Across
the original and separately authorized scopes, Package 4 charged 6 jobs / 600
planned seconds and no flashes, configuration writes, controlled reboots or
Pico Wi-Fi cycles. The acceptance auditor passes, all 13 adversarial mutations
are rejected, and the intact evidence reverifies. Capacity and pressure is
CLOSED; Package 5 retention/reclamation and Package 6 closeout are complete.

## Latest component 9 target result — bounded LOAD/replays CLOSED

[Component 9](phase11-5-r3-v2-component9-review.md) passes the exact primary,
identical replay and fresh-ID LOAD reply on clean `98f5797`, each within five
seconds, with all 512 adjustments and comparable TLS allocation. The complete
90-second observation and four HTTPS status reads pass. Peak allocator headroom
is 36,960 bytes against the unchanged 32,768-byte reserve; no allocation failure,
fault or RF activity occurred. Independent A/B and host restoration is verified.

The bounded retained-state/TLS LOAD-reply regression is CLOSED. Broader Group 2
RF/capacity/timeout/USB-pressure assertions remain OPEN; no maximum simultaneous
workload or RF qualification is inferred. Previous failures remain historical.
The [result](phase11-5-r3-v2-component9-result.json) binds the tested image, boot,
measurements and finite counters.

## Historical component 8 software result

[Component 8](phase11-5-r3-v2-component8-review.md) removes the temporary
512-element JSON-view vector during LOAD decoding. The full production replay
model now passes the unchanged reserve with a fixed calibration; identical and
fresh-ID replies retain all 512 adjustments and do not repeat preparation.
The removed vector is 16,384 bytes on this host and 8,192 bytes by target ABI;
neither is a new physical peak measurement. The stricter uncalibrated TLS-only
model still refuses replay before decoding. Tests and source review pass.

Component 7's physical reserve failure remains unchanged. A new bounded target
run is needed to qualify the rebuilt image, both replay replies and full TLS
observation interval. No device control or RF occurred in component 8. Group 2
remains OPEN.

## Historical component 7 result

[Component 7](phase11-5-r3-v2-component7-review.md) completed the authorized
single Wi-Fi recovery cycle and replacement retained-state preparation. The
exact primary LOAD returned all 512 adjustments in 2.175 seconds under measured
31,384-byte TLS allocation. The first identical replay was fully written, but
the observer stopped before its response completed: allocator peak headroom was
29,288 bytes, below the unchanged 32,768-byte reserve. The fresh-ID replay was
not sent. No allocation failure or RF operation occurred.

The primary response is verified; full LOAD-regression acceptance and Group 2
remain OPEN. Both devices are independently Empty/inactive/unowned, configuration
is preserved, and the host fixture is restored. No firmware changed. The next
software step is to reproduce and reduce the replay-stage memory peak, then
complete the remaining target checks under a subsequent bounded authorization.
See the [result](phase11-5-r3-v2-component7-result.json) for exact identities,
counters and evidence hashes. Prior failed attempts remain historical evidence;
the unrelated external router reset is user-reported context.

## Historical component 6 result

[Component 6](phase11-5-r3-v2-component6-review.md) verified the same installed
image and retained E6 record. The corrected observer passed, but Pico network
readiness remained blocked: firmware reported no IP and CYW43 authentication
failure status -3. No primary LOAD, replay or RF operation ran. Host readiness
and deadline defects are repaired and tested offline; both fixture instances
and independent final A/B state are restored. No new assertion closed. One idle
Pico Wi-Fi recovery cycle is proposed and requires extending the zero-cycle scope.

## Historical bounded Group 2 outcome: component 5

[Component 5](phase11-5-r3-v2-component5-review.md) installed clean `e256633`
and verified the retained E6 preparation. The first INFO sample exposed a host
counter-type bug, so the run stopped before the primary LOAD or either replay.
The observer and cleanup paths are repaired and tested offline; no physical
retry occurred and no new assertion closed. Both devices are independently
Empty/inactive/unowned, and the temporary fixture is restored. A now remains
on `e256633304e0`, boot `11dac3985326cb81c49022efcdceb5d4`; B is unchanged.
The exact LOAD reply under retained state and TLS remains pending. See the
[result](phase11-5-r3-v2-component5-result.json) for counters and evidence hashes.

## Historical bounded Group 2 outcome: component 4

[Component 4](phase11-5-r3-v2-component4-review.md) reproduces C7's exact LOAD
through the production endpoint/service/encoder under modeled reply pressure.
Shared immutable adjustments eliminate duplicate response/history allocations;
the regression passes without lowering memory reserves. Host tests and the
local target cross-build pass. No new physical assertion closed and no hardware
was accessed. C7 remains a historical pre-ARM failure; next is a newly authorized
bounded candidate admission check with retained state and TLS before affected
Group 2 retests. The original finite hardware allowances were not renewed.

## Historical bounded Group 2 outcome: checkpoint 048

C5 closes assertion **2.1d: valid maximum WTP input succeeds during RF** on the
retained diagnostic image. The frozen raw auditor verifies all 65552 frame bytes,
the owned Running STATUS response, continuous independent observations and one
completed 90-second Tone. Ten altered-evidence cases are rejected. No entire
sub-issue closes; 2.1, 2.2 and 2.3 remain OPEN. The full current assertion table is
in `phase11-5-r3-v2-capacity-coordination.md`.

The original allocator failure did not reproduce: zero new failures and all
retained failure metadata stayed zero. No failed PC was available, no allocator
or parser repair was made, and no replacement run occurred. C2/C3 and C4 remain
failed historical results. C4's 25.805 ms time refinement exceeds the recorded
pre-launch uncertainty; replay through the production guard reproduces Missed,
while its unchanged-mapping control launches. That supports the mechanism without
proving the missing interrupt-time branch. R5's exact idle CLAIM/RELEASE preserves
C4's terminal record and returns Empty before C5.

F5 is restored with zero cleanup failures. Final independent A/B inventories
confirm Empty/inactive/unowned, scheduling disabled and unchanged configuration.
A remains source 4da36726ac68, boot 0bd82f1324920c360d796988cf31cb5b; B remains
source 8921a7008183, boot 6684b4b197d80cfa0ce83b3aaf205cb0. Installed WsprryPi
PID/hash and protected host state are unchanged. Period 2 charged one 90-second
job and completed it; zero firmware candidates, flashes, BOOTSEL, extra reboots,
CONFIG writes, Wi-Fi commands or heap probes. Group 3 was not started.

Only host harness/auditor/regression and evidence records changed. The affected
PIO/DMA host replay, RF/clock/admission tests, R5 raw audit and C5 raw mutations
pass; firmware source/build configuration is unchanged and no firmware rebuild
or E5 physical rerun was needed. Checkpoint 048 records exact final checks.

## Historical bounded Group 2 outcome: checkpoint 047

E5 revalidated all seven idle admission assertions on diagnostic source 4da3672.
The sole C4 diagnostic charged one 90-second Tone but reported MISSED_START before
RF launch or capacity input. Zero capacity bytes and zero allocator failures on
this new boot leave C2/C3's original allocation failure unresolved. No repair or
automatic replacement test was attempted. The complete 18-assertion disposition,
identities, source-impact limits and next decision are in
`phase11-5-r3-v2-capacity-coordination.md`.

F3 and F4 are restored. Independent post-restoration inventories verify A
Missed/inactive/unowned on boot 0bd82f1324920c360d796988cf31cb5b and B unchanged,
Empty/inactive/unowned on boot 6684b4b197d80cfa0ce83b3aaf205cb0. Scheduling is
disabled; installed WsprryPi PID/hash and protected host files are unchanged.
This attempt added one diagnostic flash/BOOTSEL and one 90-second ARM charge,
zero launches, extra reboots, configuration writes, Wi-Fi cycles or probes.
The archived unfinished refactor is withdrawn; both firmware targets build and
all 70 current host CTests pass. Group 1 remains closed on its recorded evidence;
Group 3 was not started. Another work period requires user direction.

## Historical progress through checkpoint 046

The following preserves earlier observations and fixture states. They are not
current admission authority; checkpoints 047 and 048 above supersede them.

## Browser cancellation completed: checkpoint 039

B9 independently passes the remaining Running-cancellation assertion. The real
Chromium UI showed matching job c5ec4d9753d0466c853494c85dd0aa27, Running/Active,
enabled Abort and 79.3 percent estimated progress at 123.624089 seconds. The
captured ABORT followed at least 120 seconds independently observed Running;
raw USB and final inventory prove Aborted/inactive/unowned on the same A boot.
Its full 155.750001-second charge is retained; it is not a completed-duration
job. Ten evidence mutations were rejected. Group 1.3 native execution and audit are active.
B9's unit has stopped. F2 remains under its original cleanup deadline.

## Latest reconciled state

Checkpoint 035 preserves B7's terminal completion with its original failed INFO
cadence and failed cancellation. Checkpoint 036 records W0's one idle Wi-Fi
cycle and unchanged image/boot/configuration/RF counters; the fresh host build
passes all 62 CTest groups. F1 is restored. Fresh F2 is active with its original
absolute deadline 335844710513000 on host boot
220e53ca-ca95-4206-9581-dbe28aa1eeb8; client PID 539659. No old deadline was extended.

Checkpoint 037 preserves B8's one complete DFCW lifecycle and full prospective
900 INFO / 180 STATUS / 180 health observations. Running cancellation FAILED:
the producer asserted on a 6.026-second-old STATUS publication while the next
valid sample arrived 0.101 seconds later. The corrected consumer waits for a
fresh completed sample without enlarging the age limit. The final stopped
browser GET response is absent. Thirteen evidence mutations were rejected.

B8's timing auditor also rejected comparing the original launch target against
later UTC estimates after SNTP refined the clock by about 40 ms. The launch
exactly matches the ARM acknowledgment's monotonic target. Preserve the mapping
rejection pending source-based auditor review; no timing acceptance is assigned.

Checkpoint 038 records R1: one idle CLAIM/RELEASE, preserved terminal record and
RF counters/configuration, final Empty/inactive/unowned. B9 subsequently passed the remaining Running cancellation in checkpoint 039;
its full charge and inactive/unowned Aborted outcome are recorded above. A remains source a740dbb, boot
2b4583bd3d79a38f030a08c82ed96939. B's last refreshed inventory remains
Empty/inactive/unowned on source 8921a70, boot 6684b4b197d80cfa0ce83b3aaf205cb0.

Historical eleven completed RF jobs / 11606.500002 seconds remain separately
qualified. B7 and B8 each charged 155.750001 seconds and have terminal-only
completion credit. B5's 143.250001-second Armed cancellation charge remains
separate with no RF launch. A/B flashes remain six/three; CONFIG saves and heap
probes remain zero; v2 Wi-Fi cycles are now one. B9 is bounded at one additional
155.750001-second charge. All prior failures and the BF1 watchdog event remain.
Native QRSS and FSKCW completed with independent audits (040–041). Each charged
143.250000 seconds; their original producer failures remain preserved. N2
DFCW has charged 155.750000 seconds and is executing its reviewed loss case.

The following sections retain campaign history, not live device/fixture claims.

## D0 completed

The frozen D0 packet was staged and executed unchanged. One acknowledged
BOOTSEL and one verified diagnostic flash installed clean source 481da3c3ff17.
A complete 65,552-byte frame carrying a valid 65,536-byte STATUS payload was
written in seventeen bounded writes and answered within its five-second bound.
Final A boot 1271822b30097b5539961a7a2fe49302 is non-recovery, Empty, inactive and
unowned. B retained its boot, source, saved configuration and inactive authority.
There were no RF jobs, Wi-Fi cycles, CONFIG saves or diagnostic heap probes.
The installed wsprrypi service remains PID 1957 with its recorded executable hash.

Raw private archive: build/phase11-5-r3-allocation-d0/evidence.tar, SHA-256
f0ecb9cdd32377100a24d9970f9473a2a49026f349819d5965eceddbd3b5d3f2.
Independent auditor: scripts/audit_phase11_5_r3_d0.py. The intact archive passes;
nine altered/missing-write, image, authority, boot, flash, B, source and fault
variants are rejected, followed by another intact pass. This is fresh-boot
maximum-input evidence, not a C0 repair or final R3 acceptance.

## Allocation mechanism and source repair in progress

Both C0's exact historical ELF and D0's ELF were executed in a hardware-free ARM
model using task-local Unicorn 2.1.4 and pyelftools 0.33. Only serialized allocator
lock/unlock entry points are stubbed. Allocation, free, trim, page-size, sbrk and
initialized allocator data use the linked machine code. No SDK or toolchain was
changed. The model script is scripts/phase11_5_r3_allocator_model.py.

A synthetic history leaves four separated free blocks and a free top chunk.
The allocator returns NULL for 65,552 bytes even though the top plus unextended
heap can satisfy it: this newlib requests a fresh 69,632-byte extension without
subtracting the old top. The extension exceeds the unextended heap. Returning
unused top pages with the linked _malloc_trim_r makes the same request succeed.
C0's recorded arena/top/unextended values are compatible with this mechanism;
its exact failed allocation and full host write remain historically unproven.
The synthetic history is not misrepresented as a replay of C0's exact history.

The source repair introduces a movable, fallibly allocated frame input buffer.
Large target input requests first return unused top pages, then use the nullable
newlib entry point. An unrecoverable NULL closes the input without dispatching
an operation or entering the SDK panic wrapper. Completed frames transfer their
storage to decoding. Fixed waveform buffers, transport limits and reserve gates
are unchanged. Trim attempts/releases are exposed separately in INFO.

Current checks: 41 hardware-free CTest groups passed after the storage-release
adjustment and extended-message/API implementation. Both provisional images
linked after the heap checker was updated to recognize only the new serialized
trim caller; seven checker tests pass, including rejected foreign callers.
The D0 evidence audit and nine mutation cases passed. Physical remediation and
all final-image acceptance remain outstanding. The immutable
phase11-5-r3-v2-validation-001.json checkpoint retains the software results,
logs and binary identities. Later changes require assertion-level impact review,
not resetting all validation to zero.

## Next work

E0a has now deployed and admitted clean source `7d183978d08d` on A, boot
`8e777dadaa81f4618154d84de0df268a`. Seven idle assertions are independently
verified and preserved in checkpoint v2-004. Peak allocator occupancy was
139,924 of 220,908 bytes, with zero allocator failures and valid stack guards.
Final A is Empty/inactive/unowned; the one retained record is the deliberately
aborted Loaded job, not a completed RF job. B and installed Pi service remain
unchanged. E0a used one BOOTSEL and one flash, zero RF/Wi-Fi/CONFIG/heap probes.
See phase11-5-r3-v2-e0a-result.json for raw archive and auditor hashes.

Checkpoint v2-002 adds 62 passing host groups, Pi compiler/production runtime and
virtual-hour lifecycle checks, and eight reviewed local Chromium captures. The
independent UI review found rounded duration and a missing numerical event
ceiling; both are repaired and its reassessment accepted the scoped UI changes.
Two confirmed harness mistakes are retained with their corrected passing runs.
Physical acceptance remains outstanding. The HTTP body/internal-envelope limit
distinction found in source review now has an exact 32,768/32,769-byte regression.

Complete final repair review, build identified final
images, then execute internally reviewed finite packets under accepted v2.
Do not ask for routine image, Wi-Fi or RF reapproval. Preserve unrelated Pi work
and all prior failures. Run all fourteen final applicable R3 groups and seven
extended-feature checks, affected R1/R2 checks, adversarial repair/reassessment,
then complete the requested non-force commit/push sequence in both repositories.

## Preserved validation and active physical hours

The user's September 13 instruction is explicit: preserve passing tests as
validated so later attempts do not reset progress. Checkpoints v2-001 through
v2-005 are immutable. A new failure affects only assertions whose source,
configuration, workload or observation dependencies it invalidates; preserve
independent passes and every failed attempt. A harness or administrative failure
must not be relabeled as a firmware failure. Scoring remains assertion-specific.

S0's two finite jobs passed their independent raw-wire, resource, cadence and
DMA/launch/tail audit and ten evidence mutations were rejected. Checkpoint
v2-005 retains those results: a ten-second Tone and a 384-event, 32-character
QRSS lasting 143.250001 seconds. Neither is called a one-hour or saturation pass.

H0 completed its actual 3,600-second QRSS job on the same source/image/boot as
E0a/S0. Checkpoint v2-006 preserves the independently verified RF hour, raw USB
observations, resource bounds and final state. The separate strict combined
HTTPS cadence audit found a scheduler defect: 21.714092347 seconds at startup
and 21.002196289 seconds maximum periodic gap exceeded its 21-second bound.
This is retained as H0-HTTPS-SCHEDULE, with no firmware failure inferred.
The finite HTTPS scheduler now runs independently on absolute twenty-second
start deadlines; seven deterministic scheduling checks pass. Actual target
cadence validation remains pending. The QRSS hour will not restart from zero.
H1 and H2 were retired before execution, each with zero RF jobs. Fresh H1a
(FSKCW) and H2a (DFCW) use the corrected observer scheduler. H1a is running
under its independent 3,870-second systemd bound; H2a is staged only. Their exact 3,600-second/384-event plans are generated by the actual
source compile_message function; the same host compiler reproduced H0's frozen
event list byte-for-value. Each successive packet requires prior final-state
reconciliation and enough time before the unchanged fixture cleanup deadline.

The existing Chromium is 151.0.7922.137. The accepted prompt's expressly permitted
libnss3-tools dependency (2:3.110-1+deb13u4) was installed on wspr5, with no service
restarts or unrelated package changes. B0 prepares a private NSS database and
private Chromium policy/configuration copy inside its task root. No global
trust is changed. Preparation is not real-target browser acceptance.

## H1a observer finding preserved

H1a stopped its USB worker after 1,945.418 seconds on the INFO freshness guard.
Independent Console/host/native readers continue under its original deadline;
physical completion is pending raw component audit. Source inspection and a
deterministic test reproduce an unlocked publication race. Checkpoint v2-009
preserves four corrective observer regressions and seven HTTPS scheduler checks.
H2a is retired before execution with zero RF starts; fresh H2b uses the corrected
runner. No earlier scoped pass is discarded, and H1a is not relabeled a full
USB-observation pass. See the H1a observer review for exact timing and limits.

Checkpoint v2-010 preserves H1a's actual complete FSKCW hour. Independent raw
Console, native WTP, native HTTP and HTTPS coverage passed; HTTPS maximum
start gap was 20.000196111 seconds against the unchanged 21-second bound.
Twelve adversarial mutations were rejected and intact evidence passed again.
The original full USB observer gate stays FAILED, with its exact failure
preserved. This is scoped physical-hour credit, not R3 family closure.

## User clarification: retain the tested image

Keep current good code on A and leave it deployed. Change its image only for a
demonstrated defect, then retain and test the repaired image. Do not alternate
RF/inhibited images or restore A to an inhibited image between tests. B stays
read-only. A has remained source 7d183978 throughout H0/H1a/H2b; the inhibited
image mentioned in R0a diagnosis belongs to B and was not flashed or changed.
The independently reproduced HTTP outer-padding admission defect is a concrete
reason for the pending repaired image; normal test cleanup alone is not.

Checkpoint v2-011 preserves the independently verified R0a idle release and
A/B final state, six evidence-removal checks, three recovery unit tests, and
62 passing host test groups. R0's missing schema and R0a's inhibited-comparator
field mistake retain their original failed summaries. Neither warrants another
RF job or image change. H2b started on unchanged 7d183978 with a fresh guarded
observer; its own final audit remains pending.


## Accepted parallel B work

The user accepted the [parallel B plan](phase11-5-r3-v2-parallel-b-authorization.md)
with “Approve parallel B plan”; the separate acceptance JSON binds its unchanged
SHA-256. This supersedes earlier read-only-B wording for subsequent packets.
H2b and E1 still require their original unchanged B and must finish before B
is repurposed. A remains the RF/resource/reclamation target. B has no RF, ARM
or scheduling authority and does not replace A's under-contention evidence.

B's dedicated clean c5f00b6109cc standalone RF-capable image has been built with
its existing device-specific TLS identity and passed the linked-image checker.
Its ELF, map, UF2 and build/check logs are copied into the private immutable
`build/phase11-5-r3-v2-checkpoints/parallel-b-image-c5f00b6/` directory. The UF2
SHA-256 is b36f8d524cb0659107e82a41a3f8d15973fda80b843ef6909fe1a448b6ff3c6b.
This is preparation, not deployment or physical acceptance.

The B-only deployment helper admits one flash after both predecessor audits and
stopped supervisors are verified. The separate functional runner freezes six
HTTPS requests and thirteen USB requests, plus three five-request inventories.
Its single maximum LOAD remains inactive and is aborted/released without ARM.
Eight deterministic guard/plan tests pass. Independent raw-wire auditors are
prepared; actual B evidence and evidence-mutation validation remain pending.
New A packets explicitly declare B as independent and never open its endpoints.
Old staged and consumed A packets retain their original comparator checks.

## Native FSKCW preserved — checkpoint 041

N1 completed the actual 383-event, 143.250000-second native FSKCW job. Raw TLS
proves exactly one CLAIM/LOAD/ARM/RELEASE; 600 INFO, 120 STATUS and 120 host
health samples passed. Final A is Empty/inactive/unowned on the unchanged image
and boot. Nine missing-evidence mutations reject and intact evidence passes.
The original producer failure remains: it missed a transient host Complete
state before the next hourly Waiting plan. The durable last_report proves the
first job completed; the next dispatch remained outside the packet. The next
prospective guard uses that durable report. Group 1.3 remains open for DFCW with
acknowledged transport loss, local completion and same-session reconciliation.

## Native DFCW and failed loss — checkpoint 042

N2 completed its actual 383-event production DFCW job, with 600 INFO / 120 STATUS /
120 health observations and final Empty/inactive/unowned. Full charge remains
155.750000 seconds. Socket destruction returned EINVAL despite exit zero and did
not disconnect the task socket: transport loss FAILED, no reconciliation credit.
The direct compiler export also omitted the production INI double-to-nanosecond
conversion: each of 31 character gaps was one nanosecond shorter. The real
production request builder reproduces all raw LOAD fields exactly (duration
155749999969 ns); the unchanged waveform absolute-boundary conversion yields
21493499996 samples and the exact timing/counter audit passes. Original template
and integer-only sample expectations remain FAILED. Nine missing-evidence
mutations reject. N3 was retired before execution; N4 will freeze the actual
production template and reviewed pidfd socket shutdown. No QRSS/FSKCW or physical
hour rerun is needed. Group 1 remains open only for loss and reconciliation.

## Controller and lifecycle closed — checkpoint 043

N4 passes the remaining acknowledged-ARM loss, local completion and explicit
same-session reconciliation assertions. One native DFCW job was charged
155.750000 seconds; no repeated physical hour or second dispatch occurred. All
600 INFO, 120 STATUS and 120 health observations pass. Final independent state
is Complete/inactive/unowned on the retained A image and boot. Sixteen evidence
mutations reject, and intact evidence passes.

The original producer and observer remain FAILED: the harness incorrectly
required process exit zero after deliberate transport failure. The unchanged Pi
scheduling loop retains its failure flag through successful WTP reconciliation
and returns exit one on shutdown. The corrected future expectation is tested;
N4 component acceptance depends on full wire, timing, terminal and recovery
evidence, never process exit alone. No RF rerun is needed. Actual Pico planner
exports also match all 383 sample boundaries in each native mode.

Group 1 closes using checkpoints 035–043. B7 retains its original failed cadence
score and unlocalized exchange delay; the operational observer expectation was
corrected prospectively and passed subsequent runs. Group 2 is next. R3 remains
OPEN until capacity, pressure, retention, reclamation and closeout are complete.

## Group 2 scope correction and fixture recovery — checkpoint 044

The user rejected the unnecessary replacement runner. C0 is retired before
execution, with zero RF charge. Its 19 untracked implementation/auditor/test
files were archived and removed from proposed repository changes. Group 2 uses
the established RF observer, nominal load and pressure tools.

F3 is active after verified F2 restoration. W1 stopped before OFF/ON because
the addressless link changed to terminal failure. Its zero-command failure is
preserved. W2 performed exactly one idle OFF/ON; the independent audit confirms
unchanged launch/DMA counters, same A image and boot, unchanged configuration,
restored IP and synchronized clock, and Empty/inactive/unowned output.

C1 has started one 512-event, 384-second FSKCW job with existing native WTP and
HTTPS load. Full RF charge is recorded. An old two-second freshness guard failed
while a valid 1.368612098-second INFO exchange was in flight. Further control
actions stopped while independent readers continued. The original failure is
retained; the existing guard is corrected prospectively using the already tested
completed-or-bounded-inflight helper. No C1 completion or Group 2 closure is yet
claimed. The active staged C1 source is unchanged.

## Maximum-event completion preserved — checkpoint 045

C1 independently verifies one 512-event FSKCW completion over 384 seconds with
472 INFO, 96 USB STATUS, 96 host-health, 484 authenticated native STATUS and
24 HTTPS observations. Exact DMA/refill/tail deltas pass; allocation failures
and DMA errors remain zero. Peak allocator use is 181580 bytes; maximum sampled
heap use is 169396 bytes. Final authority is Complete/inactive/unowned on the
same image and boot. Twelve altered-evidence cases reject and intact evidence
passes again. The original age-guard and final-Empty expectation failures remain
FAILED; no RF rerun is needed for this component. Three nullable native host HTTP
job publications are recorded without host-HTTP authority credit; raw native WTP
and independent USB/Console supply that authority. Group 2 remains IN PROGRESS.

## C2 supported-capacity attempt failed

C2 charged one 180-second Tone. Its first maximum WTP frame wrote only 4096
bytes before input stopped; one allocator failure was recorded, with zero TLS
allocation failures and zero DMA errors. The existing observers stopped on that
failed gate; no HTTP body cases ran. Final independently decoded inventory
confirms Complete/inactive/unowned on the same image and boot. This is not full
WTP-write, supported-capacity, overload or continuous-observation acceptance.
The exact failed allocation remains unresolved; contiguous frame storage is
the current source-backed diagnostic hypothesis. Future packets may carry this
explicitly recorded historical failure count but must reject any new undeclared
increment. The original C2 expectation and result remain unchanged.
