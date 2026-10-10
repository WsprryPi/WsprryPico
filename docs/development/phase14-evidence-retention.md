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
- Preserve the currently active four-file archive recovery. It already targets
  wspr4/wspr2 under a fixed plan and must finish or report its actual outcome
  before any change to those files. Do not start another archive transfer.
- After that archive is verified, perform the already prepared safe relocation
  to recover wspr5 space. Further storage savings should come from verified
  lossless compaction on wspr5, rather than more SD-card transfers.

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
