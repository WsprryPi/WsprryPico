# Phase 14 evidence retention and storage

The operator requested reduced storage on October 10, 2026. The Mac was down
to about 3.9 GiB free; wspr1, wspr2 and wspr4 use SD cards. This amendment
changes storage and encoding, while retaining the required measurements,
original result records, failed evidence and complete raw sample contents.

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
