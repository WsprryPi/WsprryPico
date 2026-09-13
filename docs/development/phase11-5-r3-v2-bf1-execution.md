# R3 v2 BF1 parallel B admission execution

Covered by the accepted parallel B authorization. Retain the verified c5f00b6
image and boot. B only: no A endpoint, ARM, RF, schedules, firmware update,
Wi-Fi cycle or CONFIG save. The independently audited BD0 deployment and exact
source/image/boot are mandatory before opening USB.

Exercise six authenticated HTTPS cases: complete 32768-byte padded HELLO,
exact replay, changed-body replay conflict, 32769 Content-Length headers-only
400 invalid_http rejection, malformed JSON and recovery. Then exercise thirteen USB exchanges:
full 65536-byte frame, 65537-byte frame rejection and parser recovery,
513-event rejection, duration over 3600 seconds rejection, accepted 512-event
3600-second inactive LOAD, Loaded ABORT and RELEASE. Fifteen inventory requests
bring the total to 34, six TLS connections and one accepted LOAD. Zero ARM.

Stop on the first failed assertion and preserve raw evidence; no automatic
retry. Execution is capped at 600 seconds plus 150 seconds for final inventory.
Independent audit and evidence mutation checks are required before acceptance.
This is idle B evidence and does not establish A contention or RF acceptance.


BF0 stopped on a harness expectation error: src/network/http.cpp rejects an
oversized declared body before API dispatch, and pico/server.cpp maps that
parser failure to 400 invalid_http. BF0 raw responses preserve three passing
HTTP assertions and the actual correct oversized rejection. Its original
packet and failed result remain unchanged. BF1 corrects only the expected
HTTP status and parser-error envelope handling, retaining the same B boot.
The incomplete admission family is repeated with fresh request identities.
No firmware change or flash is involved.

- `packet_sha256`: `87032853b769c077555d6869aac10c642d1442c8205809d8b7ac299bddab9bb3`
- `archive_sha256`: `a65c88b5f9bec0a497e1acba0397ef99008070c35897fbe337d605e02e41e376`
- `root`: `/home/pi/phase11-5-r3-v2-parallel-b-functional-bf1-20260913`
- `stager_sha256`: `03d3f3d5073d49c71fb84da5f4333037c2047c88e443756892fe6a60546b3af3`
- `runner_sha256`: `b39b8a48c4ceb4f094cee93f60edb19163449964083d75b55aad08a512c922fc`
- `boot_id`: `015443e66990fc72b875e2345160caea`
