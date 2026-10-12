# Phase 14 evidence retention and storage

The operator requested reduced storage on October 10, 2026. The Mac was down
to about 3.9 GiB free; wspr1, wspr2 and wspr4 use SD cards. This amendment
changes storage and encoding, while retaining the required measurements,
original result records, failed evidence and complete raw sample contents.

## October 12 failed mixed stage retained intact

The amended mixed workflow and every child are now gone. All eight acquisitions
and both reference batches completed; the completed assessment rejected B's
1,384-byte Tone and 1,704-byte FSKCW equivalent idle growth against the unchanged
1,024-byte screen. The parent failed with evidence preserved and restored its
owned service. No memory stage, archive transfer, raw release or later queue
was dispatched.

All eight mixed raws/58.32 GB and the eight reference raws/128 MB remain at
their original internal paths under clean-root
`build/amended-clean-mixed-20261011T193513`, with all metadata, INFO events,
browser responses, analyses, idle windows, failure logs and closeout controls.
The parent receipt SHA-256 is
`3b0a10cd3687a629473dc61640cac223faa3146f626d4b46b69b52b615e31a32`;
the completed assessment SHA-256 is
`7d538fee857bbdb7b87ac637922bc4a874b25e35d0bc42e61f0985063a61d9e9`.
The metadata-only independent failure reconciliation is retained locally as
`build/phase14-mixed-resource-failure-independent-review-20261012.json` and
identically at clean-root `build/mixed-resource-failure-review-20261012T0610/result.json`,
SHA-256 `f6531bb570f4324fd6318f19893256d58c7ac1c6b283f06327459408add7e8f7`.
It hashes nonraw companions and independently recomputes the failing resource
screen, while reusing completed science raw hashes with current stat checks.
It performs no new raw read, RF test, device request, external transfer or
sample removal and supplies no full-raw or whole RF acceptance.

This closed failure adds no capture or transfer credit. The earlier 25-file
duplicate-only release and its durable retrieval proofs remain unchanged.
Any future archive or duplicate release still requires a separately identified
state-aware workflow and the established full verification/retrieval rules;
no only-copy sample or nonraw companion may be removed. The active-run wording
below records earlier snapshots, not the current closed state.

The separate October 12 [causal plan](phase14-memory-causal-plan.md) retains a
new metadata-only eight-window counter comparison and closed Linux-only WTP
lifetime experiment. Internal clean-root `build/wtp-lifetime-host-20261012`
preserves the completed host build and initial admission refusal;
`build/wtp-lifetime-host-admission-recovery-20261012` preserves corrected
admission, unchanged-binary reuse, verbatim probe log, original plan snapshot,
source manifest and full coordinator closeout. Their unique reservations must
not be repeated. Local receipts
`build/phase14-wtp-lifetime-host-first-refusal-20261012.json`,
`build/phase14-wtp-lifetime-host-admission-20261012.json`,
`build/phase14-wtp-lifetime-host-result-20261012.json` and
`build/phase14-wtp-lifetime-host-result-review-20261012.json` preserve the
refusal and scoped host findings. No target cause, acceptance, capture/transfer
credit, firmware change, external archive or raw removal follows from them.
All failed mixed samples and original companions remain intact.

## October 11 closed reserve release and active mixed acquisition

The full independent source/destination verification completed for all 2,014
closed clock/Tone pairs, 41,826,678,767 bytes and 253 raw pairs. Its immutable
receipt is `build/phase14-clock-reserve-full-audit-complete-20261011.json`,
SHA-256 `2d27bb6f2fb9bf2e77a50f47008d182f5eb3c1c7a1ae49949093b4d88baff06d`.
Its identical durable retrieval is
`/mnt/phase14-testing/phase14-closed-internal-first/reserve-verification-1791744416866697703/retrieval.json`.

The separately recorded duplicate-only release removed exactly 24 eligible
internal clock raws/7.590 GB, receipt
`build/phase14-clock-reserve-owned-release-result-20261011.json`, SHA-256
`f53b01f2f04bae5e7aad028ca3f609c04206e35d2cc733a962de56534ce69668`.
Its durable retrieval is
`/mnt/phase14-testing/phase14-closed-internal-first/reserve-release-1791746425065388223/retrieval.json`.
Every sample remains in the original clock archive, with its full source and
destination proof, unchanged source identity before unlink, independently
published per-file retrieval on both filesystems and immediate final full
hash/stat/user checks. The independent post-release review full-hashed all
24 destinations/7.590 GB and 1,758 distinct small companion pairs; it reused the exact
unchanged identities of the remaining 229 raw pairs. Its receipt
`build/phase14-clock-reserve-release-independent-post-review-20261011.json`
has SHA-256 `decbfa28da4889a045f2dca430f5522fa0066ee646501257de15f51acd958aaa`.

The unchanged before/after GPSDO references require another 128 MB of raw
storage. A separate state-aware correction, bound to the accepted 24-file
review, released only one additional 312 MB internal duplicate. The original
release was never repeated. The correction receipt is
`build/phase14-clock-reference-reserve-delta-result-20261011.json`, SHA-256
`0113ba95ef30c44a70d08276bcd34183babf066afb56f7ace5753c5d2732a38c`;
its durable retrieval is
`/mnt/phase14-testing/phase14-closed-internal-first/reserve-release-1791747120324807917/retrieval.json`.
An independent final check full-hashed the new destination, reused the accepted
24-file proof, verified retrieval ordering and retained both releases' complete
closeout controls. The final review SHA-256 is
`4d4dff0dca9e616a6e9fd92e8532f7fa31a11576c4533f326058cf54da5541a8`,
identical in the clean internal root and the correction archive as
`independent-final-reserve-review.json`.

Cumulatively, 25 internal duplicates/7.902 GB were removed. No only-copy sample,
nonraw companion, retained A132 max raw or Tone/reference raw was removed.
The old copy-only zero-removal flags remain immutable historical records; the
separate release receipts identify the actual later source absence. Restore
archived samples to their recorded internal paths and full-hash before reanalysis.
Never rerun helpers that assume all original sources exist; any later release
requires a new ready-stage shortage and state-aware verification.

The actual mixed dispatch rechecked internal/external UUIDs and all four locks,
then 69,384,732,672 bytes free against the complete 69,185,418,240-byte requirement
(58.32 GB mixed raw + 128 MB reference raw + 10 GiB). Coordinator
3233082/start 66510419 is active at clean-root
`build/amended-clean-mixed-20261011T193513/result.json`. No further archive,
raw release or audit may overlap its acquisition/analysis. Memory remains
a separate stage after actual independently accepted eight-job results and
gone processes. Verification and duplicate removal add no capture or transfer
credit and close no original qualification workstream.

The earlier wrong self-hash command argument refused before devices, raw reads,
output or reservation; its corrected probe and original refusal are retained
in `build/phase14-release-self-hash-argument-refusal-20261011.json`. Prepared
`7373e15d`, `151e06bd` and `eceb7c54` entries were never executed on campaign
evidence; their distinct successors and actual receipts supply the evidence above.

## October 11 earlier reserve audit snapshot

The actual ready-stage review demonstrated approximately 7.6 GB of additional
space needed for the eight mixed captures plus the 10 GiB reserve. The new
verifier, helper SHA-256
`0a9e1d49a1206993b7b2defd18585603cf7db664668b0eec2217afa419b91e2d`,
was dispatched exactly once with `--verify` and removes zero files. Its private
receipt is `build/clock-reserve-full-audit-20261011T184656/result.json` under
the clean internal root below. It full-hashes both unchanged sources and durable
destinations for the closed clock and Tone catalogs: 2,014 pairs totaling
41,826,678,767 bytes, including all companion logs and all 253 raw pairs.
All four locks exclude acquisition, analysis and other archival workflows.
This audit is a new mandatory prerequisite for duplicate release, not a repeat
of accepted RF work. Existing copy/audit receipts and every source remain intact.

The release candidate derives its 218 eligible clock raws from the actual
original full clock audit. The copy-only catalog's zero release count stays
zero, and its 49 empty decoder stderr companions remain empty and retained.
Both initial reader refusals, with zero raw reads, removals or reservations,
are preserved in the private preparation receipts.

The running verifier and its inputs must remain unchanged. Its release entry
is superseded because the mixed coordinator received an additional closeout
guard repair. Once the verification is complete and all processes are gone,
independently review that coordinator successor, then bind a separately
identified release-only helper to the actual completed full audit and current
ready-stage review. Publish retrieval on both filesystems before each unlink,
full-hash the unchanged source and destination immediately, check exact file
identities and active users, remove only redundant internal raw and stop when
the reserve is met. Keep the retained A132 maximum raw, all nonraw companions,
profiles and current cursors. No release or mixed stage is queued.

## October 11 clean candidate staging

The new clean source/tool root is
`/home/pi/phase14-qualification-20261008/build/resume-tools-8538564-clean-internal-first`.
It is on the existing internal NVMe, UUID
`ed6c7f1b-238b-41a1-b4b6-7bcdef3270fe`, device 66306. The 1,825 source/artifact
files and qualified imports were verified; staging receipt SHA-256 is
`4fecf34cd093851a418e4f055224f49f2fd6f1714fd6ff158ebe7dabe42d0358`.
The fresh root retains clean 132/138/150 MHz candidates and the independent
138 MHz rebuild proof. Existing e953 and first 853 staging roots remain
unchanged, including the earlier dirty-identity installation failure.

Current profile/configuration/cursor ROM snapshots for the unarmed admission
checks remain private on wspr5. They contain credentials and are not copied
to the Mac or committed. Small public source/control/result/review receipts
are retained locally. Both installation and B flag checks preserved the current
8 KiB cursor; the B flag experiment independently verified profile bytes and
restored the original configuration. A's refused consumer Console request
left its full 32 KiB region byte-identical.

The four new-image 80 m baselines closed on this internal root with
SDRplay bias-T disabled. All 824 MB of complete raw samples remain internal,
independently full-hashed with their immutable control/decoder companions. They do not start a later queue or permit raw release.
Existing independently verified clock and Tone external archives remain
unchanged, with every internal original retained. Any future reserve release
still requires actual ready-stage shortage, a separately identified state-aware
helper, full source/destination/companion verification and published retrieval
before immediately rechecking each redundant raw file for unlink.

## Storage placement

- Keep new bulk captures on wspr5. Do not copy additional raw recordings to
  the Mac or use the other Pis as routine bulk capture archives.
- Keep source, selected firmware artifacts, hashes, small status/analysis
  summaries and retrieval receipts on the Mac. Remove rebuildable intermediates
  after the relevant build closes; retain source, pinned inputs and final UF2/
  ELF artifacts.
- The fixed four-recording archive on wspr4/wspr2 has completed independent
  destination and unchanged-source verification. Retain all original source
  recordings and every earlier failed-copy receipt. Do not start another
  routine archive transfer.
- The operator subsequently added a 1 TB external SSD to wspr5, then clarified
  that live captures must use the faster internal SSD. Record on wspr5's
  internal NVMe and transfer closed recordings to the external SSD. The previously prepared
  four-file source relocation is no longer needed to make space for the next
  batch; retain those original recordings. Further storage savings, when needed,
  come from verified lossless compaction on wspr5.

## October 10 external SSD

The operator authorized erasing and repartitioning the newly attached USB
WD Black SN770 1 TB, serial `012345678906`, size `1000204886016` bytes.
Its stable device link is
`/dev/disk/by-id/usb-WD_BLACK_SN770_1TB_012345678906-0:0`.
The external disk now has one GPT Linux data partition, formatted as ext4
with label `phase14-testing` and UUID
`d9df35dd-f27b-45e0-9dff-c74e1bbfabe6`.

The filesystem mounts at `/mnt/phase14-testing`. The future tool root's build
directory,
`/home/pi/phase14-qualification-20261008/build/resume-tools-1024529/build`,
is a bind mount of
`/mnt/phase14-testing/phase14-qualification-20261008/resume-tools-1024529/build`.
This preserves the existing capture paths while storing new bulk bytes on the
external SSD. Its existing tool-source verification record was copied and
independently matched before mounting; the internal copy is retained.

The UUID and bind mount are saved in `/etc/fstab`, with the original file
backed up as `/etc/fstab.phase14-ssd-20261010.bak`. Both entries passed a real
unmount/remount through fstab, and their generated systemd mount units reached
`active/mounted`. A flushed 4 MiB write/read hash check passed through the
actual future capture directory. Available space was about 927.30 GiB.
The system remains booted from `/dev/nvme0n1p2`.

### Internal recording amendment

The initial storage setup bound the future tool root's build directory directly
to the external SSD. The operator subsequently rejected direct external writes
during acquisition because the external disk is slower. That acquisition route
is superseded; its existing mount and evidence remain intact.

New live acquisition uses the separate tool root
`/home/pi/phase14-qualification-20261008/build/resume-tools-1024529-internal-first`.
Its `build` directory resolves to `/dev/nvme0n1p2`, UUID
`ed6c7f1b-238b-41a1-b4b6-7bcdef3270fe`, filesystem device 66306, distinct
from the external device 2049. All 1,812 pinned tool-source files and the three
ordinary firmware candidates were copied and independently hash-verified.
A flushed 4 MiB write/read check passed, with about 117.90 GiB free.
No firmware, sample format, rate, duration or acceptance rule changed.

Use the external SSD for completed evidence at
`/mnt/phase14-testing/phase14-closed-internal-first`. Copy only after acquisition
and analysis have closed and their exact processes have ended. Do not overlap
the external transfer with a live capture. Independently hash the full destination
and unchanged source, retain every metadata/control/decoder/analysis record,
and publish durable retrieval locations. Free internal space only after those
checks by removing a redundant representation; never remove the only retained
sample bytes. Maintain enough internal reserve for the next finite stage and
one largest recording, and restore archived recordings to internal storage
before reanalysis when necessary.

The former external-acquisition clock, Tone and reliability wrappers are
superseded and must not be invoked for new recordings. The old clock campaign
ended independently with preserved failure evidence before this change.
Its historical external files remain untouched. Small preparation receipts are
`build/phase14-internal-workspace-preparation-20261010.json` locally and
`build/internal-workspace.json` under the new host root.

### October 11 upper-band exclusion and diagnostic retention

The latest operator amendment excludes 4 m and 2 m for all five modes after
failed required WSPR decoding without synthesis-preventing faults. See
[phase14-band-support.json](phase14-band-support.json). Preserve every original
successful/failed capture, metadata, control, decoder, analysis and flag; this
support decision removes no evidence and changes no historical result.

Four separate synthetic audio controls have closed, with steady-carrier decodes
and negative observed-trajectory controls at both bands. Their actual result is
retained internally at
`build/synthetic-carrier-controls-20261011T1521/result.json` under the current
tool root, SHA-256
`9447089103621853a3638aeba7e7032fdbd91336bcb8bdd4123eeb2de57608ba`.
Keep all four synthetic WAV/stdout/stderr files and the original small-file/
raw-identity bindings. The byte-identical independent review is
`build/upper-band-synthetic-independent-review-20261011T1534.json`, SHA-256
`59463f0c9a1fff724d0cc5512807791f76d1511b1c5f71e3fe39b54889bdb1e4`.
No retained IQ/audio was edited or copied to the Mac, no new RF ran, and no
qualification/capture credit follows. Do not repeat these decoder controls.

The native nineteen-job archive remains unexecuted and unqueued. Its new
preparation encountered a zero-ended-time guard refusal before copying; retain
that refusal and correct/review a separately identified successor before any
copy. No source bytes were removed. Clock/Tone archive credits remain unchanged.

The former positive 4 m prerequisite is superseded by the operator exclusion.
Mixed reliability still requires reviewed amended admission and enough internal
reserve before launch. Any redundant raw release needs its own guarded helper,
actual next-stage shortage, independent durable/source/companion verification
and retrieval publication; no release is currently armed. The checkpoint below
records the earlier support boundary and is preserved as history.

### October 11 14:28 UTC closed Tone and reference archive

The accepted post-clock Tone archive and its independent full review are
closed. All acquisition, analysis, decoder and audit predecessors had ended
before copying. Workflow and all three bench locks covered the copy; actual
internal/external UUIDs and distinct devices 66306/2049 were checked. No
external transfer overlapped acquisition or analysis.

The durable location is
`/mnt/phase14-testing/phase14-closed-internal-first/post-tone-rc3-1791728421022595521`.
It contains 288 evidence files/2,739,943,875 bytes, including 26 accepted Tone
raws/2,600,000,000 bytes and eight closed GPSDO reference raws/128,000,000 bytes.
Metadata, control, decoder, analysis, close-in, original flags, source and
audit companions are retained. The previous clock copy's full closeout
controls and this copy's own full closeout controls are also durable.
The successful local receipt is
`build/phase14-closed-tone-copy-result-20261011.json`, SHA-256
`b4f46fe8689731f9dcffe5f9301575ac447e454d11d71885dbb2ca6a2cc3b00d`;
the archive's `retrieval-1791728421022595521.json` has identical bytes.

The copier independently verified full destination and unchanged source
contents and flushed the archive. A separate review then full-hashed every
source/destination evidence pair, verified retrieval and companion bindings,
recorded exact identities for all 34 raw pairs, and checked live restored
boards/settings/current cursors/GPSDO. Its local receipt is
`build/phase14-closed-tone-copy-independent-review-20261011.json`, SHA-256
`77b7340d1052af48ec0ad86d1bd74211751c95d648a7a53168663c6130f9a6a3`;
identical review bytes are retained internally and in the archive.

The earlier catalog refusal omitted eight reference companion raws and is
preserved; it stopped before samples, devices, copy or reservation. The
corrected copy includes those exact closed companions. Thirty-nine Linux
refusal checks passed before the actual copy. Preparation alone supplied no
archive proof; the closed copy and independent review supply that proof now.
Neither copy nor review may be repeated. All internal originals remain, with
zero bytes removed and no release entry.

The independently verified Tone transfer credits 2.6 GB once, leaving 72.9 GB
of unrecorded core transfer. The 128 MB reference retention remains inside the
existing other-work allowance and adds no capture credit. The separately
closed A carrier-search diagnostic remains negative and changes no original
acceptance flag. Final process/four-lock/UUID checks found no active campaign
or later queue, with about 58.584 GiB internal free. Mixed reliability remains
blocked by 4 m acceptance and requires more reserve; do not release raws now.
Any later redundant release still requires its own guarded, state-aware
operation, full durable verification and retrieval records before each unlink.

### October 11 13:27 UTC closed comparison and independent audit

The B-only continuation and all acquisition/analysis processes have ended.
Both normal-connection comparison frames retain their actual false expected
decodes, passing resources and zero receiver overflow/clipping. The independent
auditor has also ended after full-hashing only B's new 312,000,000 bytes and
reusing A's completed 312,000,000-byte independent audit with unchanged exact
source identities. Its receipt is
`build/phase14-action-prefix-independent-closed-audit-20261011.json`, SHA-256
`650c20dd93ecbdd22b4856afb7864a9238e031577fab3071cda829e9c0b7b90e`.
All raw/control/metadata/analysis/decoder/audio and original failed records
remain on internal NVMe; no raw was removed or transferred during this work.

Fresh process and four-lock closure checks passed with the actual internal
and external UUIDs and devices 66306/2049. The comparison adds 624 MB once to
pending finite retention, now 19.288 GB within the existing allowance. Its
full integrity audit creates no 4 m acceptance, capture credit or raw-removal
authority. Preserve the separate original failed reader, A audit, continuation
and whole audit; none may be blindly rerun. Any later archive still requires
its own guarded closed-evidence catalog, full durable-copy/source verification
and retrieval records. The verified 38.720 GB clock transfer credit and every
internal original remain unchanged. Mixed reliability remains blocked by
4 m acceptance; no long queue or raw-release operation is armed.

### October 11 13:11 UTC retained A and active B-only comparison

The original connection-action comparison is closed with its host INFO-prefix
reader failure preserved. A's acquisition and analysis completed; B had not
started. Its original zero-observation/error receipt remains unchanged. A's
separate independent audit full-hashed 312,000,000 unchanged bytes and bound
the original control, metadata, decoder/audio/stdout, resource and receiver
records. The audit process ended, and its receipt is
`build/phase14-action-a-prefix-independent-audit-20261011.json`, SHA-256
`b0094111e10601e62f91c40331e5d9bf9aaf85c8c509cc2655a1479cc080b520`.
The actual expected decode remains false. Preserve all original records;
this audit authorizes integrity reuse without mode acceptance or raw removal.

A separately identified continuation is active exactly once as
PID 3123957/start ticks 64186195, helper `a097f0b0`. It retains A's full audit
and acquires only the missing B recording/312 MB on internal NVMe. At the
13:11 UTC snapshot B is in its minimum 350-second idle period, and no new
observation has closed. All four locks, actual UUIDs and distinct devices
66306/2049 were checked at the preceding quiet boundary. No archive transfer
or source removal may overlap this acquisition or analysis.

The additional closed A recording adds 312 MB once to finite retention,
now 18.976 GB within the existing allowance. Add B's new 312 MB only after
its actual capture closes. A later independent recovered-comparison audit
is prepared but unqueued; it reuses unchanged A full-hash identities and
independently hashes only the new B recording after actual whole closure
and process termination. Neither integrity closure nor a diagnostic contrast
permits automatic 4 m acceptance or redundant raw removal. The verified clock
archive, its 38.720 GB transfer credit and every internal original remain
unchanged. Mixed reliability is still blocked by 4 m acceptance.

### October 11 12:49 UTC verified closed-clock archive

The copy-only `7b0e63a0` operation is now `INDEPENDENT_CLOSED_CLOCK_COPY_VERIFIED`.
Exact PID 3103666/start ticks 63759990 and its verification process have ended.
All 219 closed clock raws/38.720 GB and required companions, 1,726 files and
39,086,734,892 total bytes, have full independent destination and unchanged-source
hash verification and durable retrieval. The archive location is
`/mnt/phase14-testing/phase14-closed-internal-first/clock-rc3-1791719809192454023`.
Its `retrieval-1791719809192454023.json` is byte-identical to the terminal status,
SHA-256 `44efa33e035f255ac928afebc9e635ce41dc25fd31a1bd949b0dc17ee4bdf132`.
All internal sources remain; removals are zero.

The separate actual closure review is
`build/phase14-clock-copy-independent-closure-review-v3-20261011T1245.json`.
It reuses the completed raw hashes with unchanged exact source identities,
independently rehashes the 1,507 small companions/366,734,892 bytes, and validates
the actual compact inventory through stored full INFO/WTP control records.
Preserve its earlier inventory-wrapper and STATUS-field parser refusals. They
changed no archive, raw or original result. The copy's own full closeout-control
files remain retained internally and must accompany any later durable catalog
before redundant raw release.

The 38.720 GB closed core transfer is now credited once; pending core transfer
is 75.5 GB, including unrecorded mixed/memory captures and closed post-clock Tone.
No raw release is armed. Future release still requires a separately guarded,
state-aware operation, demonstrated reserve shortage, durable retrieval and
full independent archive/source/companion checks before each eligible unlink.
Mixed reliability remains blocked by 4 m acceptance.

After actual copy closure and fresh quiet checks, the bounded two-slot
connection-action comparison was dispatched once on internal NVMe as
PID 3117468/start ticks 64055343. No external transfer or source removal may
overlap its acquisition or analysis. Original failed settling recordings and
their independent audit remain unchanged; no automatic later queue exists.

### October 11 12:18 UTC closed-clock copy checkpoint

The copy-only `7b0e63a0` helper is now executing once, after the two-slot idle
diagnostic and its independent 624 MB audit closed and all acquisition/analysis
processes ended. Exact coordinator PID 3103666/start ticks 63759990 holds
workflow and all three bench locks. It copies the 219 closed clock raw files,
38.720 GB, and their original control/metadata/decoder/analysis/source/audit/
retune/review companions to
`/mnt/phase14-testing/phase14-closed-internal-first/clock-rc3-1791719809192454023`.
Both filesystems were verified as the recorded internal/external UUIDs and
distinct devices 66306/2049. Every internal original remains; the helper has no
raw-release entry.

The small checkpoint
`build/phase14-clock-companion-copy-live-20261011T1218.json`, SHA-256
`89068a4f928bdcb6dbe5afc46dc88749a694d9fdc2d1fafef1ba33d7e310f198`,
records 192 independently verified partial entries/33.468 GB, no errors and
zero removals. Whole-archive verification and durable retrieval publication
remain pending. Do not duplicate the copy or credit partial bytes as a closed
archive. No RF capture or analysis overlaps this transfer. The two failed idle
diagnostic recordings add 624 MB to pending finite retention within the existing
allowance; neither their complete raw audit nor their failed decode results
authorize sample removal or qualification acceptance.

Any subsequent RF stage requires this copy's actual successful terminal and
retrieval hashes, ended process and fresh ownership/storage checks. A future
redundant raw release still needs a separately identified guarded operation,
independent durable-copy checks and a demonstrated next-stage reserve shortage.
The mixed stage remains blocked by 4 m acceptance; no source removal or later
queue is armed.

### RC3 closed-clock companion preparation at 11:25 UTC

The current RC3 root is
`/home/pi/phase14-qualification-20261008/build/resume-tools-e95334a-internal-first`.
Its closed clock evidence includes 218 new recordings/38.374 GB and the
separately retained new A132 max-contention recording/346 MB. The latter was
omitted from the preceding transfer estimate; pending closed-clock raw is
38.720 GB. Including closed post-clock Tone and unrecorded mixed/memory raw,
pending core transfer is 114.220 GB. This corrects retention accounting without
adding capture credit or claiming any completed copy.

The original unexecuted `d54a18f6` copy helper omits the separately accepted
receiver-retune/review companions and retained max-job evidence. It remains
preserved; its copy entry is superseded by a copy-only helper `7b0e63a0`, SHA-256
`7b0e63a0290399819f79fde069039cd2d2deda8a6f523f3bb65129d05bb8a23d`.
The successor includes the closed full-audit directory, original successful
A4m receiver-only diagnostic, separately reviewed clock reconciliation and
retained max-job raw/control/analysis records. Eighteen isolated Linux guards
and 29 actual companion layouts/353,807,381 bytes were checked without campaign
IQ reads, device access, transfer or removal. Its positive campaign copy path
remains unexecuted and unvalidated.

Any later copy requires every acquisition, analyzer, audit and workflow process
to have ended, workflow/all three bench locks, actual idle RC3/138 MHz boards,
the actual internal/external UUIDs and sufficient external reserve. Independent
full destination and unchanged-source hashes, fsync and durable retrieval
records are required. The existing exclusive clock-copy reservation prevents
old/new helper duplicates. This successor has no raw-release entry and removes
no source files. A future redundant raw release requires a separately guarded
operation after an actual verified copy and demonstrated next-stage reserve
shortage, with durable retrieval locations and full independent checks before
each unlink. Do not transfer while the active two-slot settling diagnostic or
any later acquisition/analysis uses the bench. Current clock/Tone/finite copied
and removed bytes remain zero.

Three subsequent 156-second GPSDO-only captures on internal NVMe completed
with zero overflow/clipping and restored reference/USB-idle state. After their
process ended, 17 closed files/936,191,802 bytes were copied and independently
hash-verified on the external SSD in 32.19 seconds. All internal originals
remain. The external location is
`/mnt/phase14-testing/phase14-closed-internal-first/receiver-internal-20261010T2045`,
with a durable `retrieval.json` record. The local summary is
`build/phase14-internal-first-storage-result-20261010.json`. This validates the
storage workflow without identifying the earlier receiver/control failures.

The preceding external-aware wrappers required the external UUID and a
filesystem distinct from the system disk. Those acquisition wrappers are now
historical. Future acquisition checks require the recorded internal UUID;
closed-file archival checks independently require the external UUID.
Provisioning changed no active archive, RF settings or retained sample bytes.

Private receipts and prepared tooling are:

- `build/phase14-external-ssd-provision-20261010.json`
- `build/phase14-external-ssd-mount-verification-20261010.json`
- `build/phase14-ssd-staged-helper-verification-20261010.json`
- `build/phase14-next-clock-ssd-stage-prepared.py`
- `build/phase14-post-clock-tone-ssd-prepared.py`

The older relocation and clock/Tone wrappers remain historical prepared tools.
Both copy attempts closed with preserved timeout receipts. The separate
`9770a57e` verification-only recovery completed both full destination and
unchanged-source rehashes, retrieval publication and guard release at October
10 18:48:58 UTC. Its immutable final receipt is
`build/phase14-archive-verification-final-1791658138038212000.json`, SHA-256
`05e818ccbd9ed3dc6779bf5e6d90f5fe7af1d1b3b63500200eb0ec4398412058`.
It copied and removed no recordings. All source originals remain, and no source
relocation is needed. The stopped clock campaign stored its captures on
the external SSD. Subsequent live capture uses internal NVMe under the
operator amendment above; see the current [results](phase14-results.md). Receiver
continuity failures remain separate from filesystem capacity or verified
archive integrity. Original capture settings, failed flags and historical
recordings remain unchanged.

## Lossless raw retention

Use gzip for closed captures after their analyses and independent raw audit
have completed. Keep capture metadata, physical/control records, decoder
receipts, original failure flags and analysis results unchanged. Do not compact
files that an active acquisition, analyzer, verifier or relocation operation
still requires.

For each eligible raw file:

1. Check the declared complete capture, raw byte count and original SHA-256.
2. Compress into a separate temporary file while hashing the original bytes.
3. Independently decompress the temporary file and require the original byte
   count and SHA-256. Also check that the original file and metadata are unchanged.
4. Save and flush the compressed file and a retrieval record before removing
   the redundant uncompressed representation. The record contains both hashes,
   both sizes, the codec, original path and an exact restoration command.
5. Preserve every original receipt. A missing uncompressed filename is resolved
   through its retention record; it is not relabeled as an acquisition failure.

This is bit-for-bit retention. It does not change sampling rate, sample format,
recording duration, mode settings, accepted observations or thresholds. Reanalysis
can restore one recording at a time from its gzip file, verify the original
hash, run the original analyzer and remove only that temporary restored copy.

Maintain a working-space reserve for compression/restoration. Never remove
raw data before independent decompression verification and durable location
publication. A failed compaction leaves the original recording available and
requires inspecting the preserved partial output before retry.

## October 10 cleanup

The Mac's private project build directory occupied about 69.4 GiB. Removal of
109,424 CMake object/dependency intermediates recovered 5.72 GiB. Removal of
1,706 generated static-library, Ninja and disassembly outputs recovered another
10.86 GiB; corresponding CMake input and ELF files were retained. Initial Mac
free space rose from 3.93 to 20.75 GiB, without deleting captures, firmware,
source, SDKs or result records. Reconfigure these historical CMake directories before rebuilding; their
removed files are generated again. This cleanup does not install or rebuild
anything.

A separate compaction plan covers 267 complete historical Mac captures,
22.72 GiB in total, dated before October 8. The private helper is
`build/phase14-lossless-compact-closed.py`, identified by SHA-256
`b689e27618294bde16e42d58394e21814f466302e7499a84e4c0d5b677667e00`.
Its lossless round-trip, incorrect-hash preservation and symlink rejection
fixtures passed. Every actual conversion independently verifies full decoded
bytes and records the new representation beside the unchanged metadata.

Private receipts are:

- `build/phase14-mac-generated-intermediate-cleanup-20261010.json`
- `build/phase14-mac-generated-output-cleanup-20261010.json`
- `build/phase14-mac-lossless-compaction-20261010.json`

The compaction receipt records actual completion and freed bytes; prepared
work or an active compression is not counted as completed savings. No ongoing
RF job or the independent archive recovery is changed by this local cleanup.

All 267 planned historical captures completed verified lossless compaction,
recovering 10.53 GiB. Together with generated-file cleanup, the measured
reclaimed total is 27.11 GiB; Mac free space is about 30.94 GiB. Every original
capture metadata file still matches its retained hash, and all compressed
representations and restoration records are present. Firmware UF2 and ELF
counts and byte totals are unchanged. The final private summary is
`build/phase14-storage-reduction-summary-20261010.json`.
