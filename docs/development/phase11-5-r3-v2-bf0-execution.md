# R3 v2 BF0 parallel B admission execution

Covered by the accepted parallel B authorization. Retain the verified c5f00b6
image and boot. B only: no A endpoint, ARM, RF, schedules, firmware update,
Wi-Fi cycle or CONFIG save. The independently audited BD0 deployment and exact
source/image/boot are mandatory before opening USB.

Exercise six authenticated HTTPS cases: complete 32768-byte padded HELLO,
exact replay, changed-body replay conflict, 32769 Content-Length headers-only
rejection, malformed JSON and recovery. Then exercise thirteen USB exchanges:
full 65536-byte frame, 65537-byte frame rejection and parser recovery,
513-event rejection, duration over 3600 seconds rejection, accepted 512-event
3600-second inactive LOAD, Loaded ABORT and RELEASE. Fifteen inventory requests
bring the total to 34, six TLS connections and one accepted LOAD. Zero ARM.

Stop on the first failed assertion and preserve raw evidence; no automatic
retry. Execution is capped at 600 seconds plus 150 seconds for final inventory.
Independent audit and evidence mutation checks are required before acceptance.
This is idle B evidence and does not establish A contention or RF acceptance.

- `packet_sha256`: `d9b6db99ad6d491c780a00c6f34a50a47c2be02de5665bab28c78ee0a5af59dd`
- `archive_sha256`: `139f2ee58e89267c5fc7f1c18951ed87e1a0d3e4a0ea424102446639163f9276`
- `root`: `/home/pi/phase11-5-r3-v2-parallel-b-functional-bf0-20260913`
- `stager_sha256`: `03d3f3d5073d49c71fb84da5f4333037c2047c88e443756892fe6a60546b3af3`
- `runner_sha256`: `04baca86282c30185f31d5d66fb80340d9449f935ba1b1bfcb3bfe019e11dfc1`
- `boot_id`: `015443e66990fc72b875e2345160caea`
