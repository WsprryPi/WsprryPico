# R3 v2 execution progress

R3 remains OPEN. The user accepted R3-COMPLETE-20260913-v2 on September 13,
including implementation, finite RF, recovery, review and commit/push. Exact
acceptance and counters are in phase11-5-r3-v2-campaign.json. Historical packet
approval text is retained as history; v2 is the current standing authority.

## Latest state: BF1 repair in progress

H2b's DFCW hour passed its complete independent RF/contention audit and ten
mutations (checkpoint 012). E1 deployed c5f00b6 on A and passed all seven idle
boundaries plus ten mutations (checkpoint 013). Both checkpoints also pass with
isolated frozen audit dependencies. These passes remain preserved.

B's authorized c5f00b6 deployment passed (014). BF0's four HTTP assertions pass
independently; its 413 expectation error remains classified as a harness defect
(015). BF1's six HTTP assertions pass independently, but its maximum LOAD caused
a confirmed firmware allocation panic, followed by authoritative inactive
recovery-boot reconciliation (016). B received no ARM or RF command. See the
[BF1 repair review](phase11-5-r3-v2-bf1-repair-review.md) for the exact evidence,
shared WTP/browser output-buffer repair, tests and physical limitations.

A remains c5f00b6, boot a0badc7b54480767c3d3f907e0962dc7, inactive/unowned with
schedules disabled. F0's owned restoration passed and F1 is active with client
PID 491605 and unchanged cleanup deadline 306202695885000 host-monotonic ns.
A rejoined and synchronized without a Wi-Fi cycle or CONFIG save. T2/T3 were
retired before staging/execution after the demonstrated BF1 defect. The next
firmware admission is on B first; A's good mode-hour results do not restart.

The remaining sections record the campaign history; this latest-state section
supersedes older statements that an already completed tranche is still pending.

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
