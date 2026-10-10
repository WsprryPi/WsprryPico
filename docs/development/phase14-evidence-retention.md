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
